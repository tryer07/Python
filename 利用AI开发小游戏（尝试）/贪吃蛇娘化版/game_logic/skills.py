# -*- coding: utf-8 -*-
"""
game_logic/skills.py —— 角色专属技能包（多主动 + 连招）

设计（相较旧「单主动 + 选卡解锁」版）：
  · 每名角色拥有一套「专属技能包」：5 个主动（绑 1-5 键，各自冷却）+ 1 个常驻被动。
      - key1 = 角色专属大招（petal_slash / gale_dash / tide_surge / ember_lash /
               star_chain / moon_ward，六选一，行为各异）；
      - key2-5 = 共享的连招组件（mark 标记 / pull 聚怪 / burst 引爆 / rally 鼓舞），
        各角色只是配色、命名、图标不同，机制一致，方便玩家自己开发连招。
  · 连招链示例：标记(2) 让敌人易伤 → 聚怪(3) 把敌人拉到一起并减速 →
    引爆(4) 按敌人身上的状态数量追加伤害；鼓舞(5) 短时提升自身攻击攻速。
  · 技能 id / 名字 / 颜色 / 特效 / 按键 全部走 data/characters.json 的 kit.actives，
    数值走 settings.py（COMBO_* 与各专属常量）。
  · SkillEngine 只管：当前角色 kit、每个主动的冷却计时、少量持续态（薄荷移速爆发）。
    瞬发效果通过 cast() 返回「事件字典」，由 battle._apply_skill_event 落地。
  · 减速 / 灼烧 / 标记 等持续状态挂在 Mob 上（见 entities.py），引擎不持有；
    鼓舞(rally)增益挂在 battle 场景上（self.rally_*）。

坐标系：与实体一致，世界像素。
"""

import json
import math
import os

import settings as S

_KIT_CACHE = None      # {char_id: {"actives": [...], "active": {...}, "passive": {...}}}
_INFO_CACHE = None     # {sid: {name,color,desc,vfx,key,kind}}


def _load_kits():
    """读 data/characters.json，构建 角色->kit 与 sid->展示信息 两张表。"""
    global _KIT_CACHE, _INFO_CACHE
    if _KIT_CACHE is not None:
        return _KIT_CACHE, _INFO_CACHE
    kits, info = {}, {}
    try:
        path = os.path.join(S.DATA_DIR, "characters.json")
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        items = raw.get("characters", raw) if isinstance(raw, dict) else raw
        for ch in items:
            if not isinstance(ch, dict):
                continue
            cid = ch.get("id")
            kit = ch.get("kit")
            if not cid or not isinstance(kit, dict):
                continue
            passives = kit.get("passives")
            # 向后兼容：没有 passives 列表就退回旧的单个 passive
            if not isinstance(passives, list) or not passives:
                one = kit.get("passive") or {}
                passives = [one] if one else []
            passives = [p for p in passives if isinstance(p, dict) and p.get("id")]
            passive = passives[0] if passives else {}
            actives = kit.get("actives")
            # 向后兼容：没有 actives 就退回旧的单个 active
            if not isinstance(actives, list) or not actives:
                one = kit.get("active") or {}
                actives = [one] if one else []
            actives = [a for a in actives if isinstance(a, dict) and a.get("id")]
            kits[cid] = {"actives": actives, "passives": passives, "passive": passive,
                         "active": actives[0] if actives else {},
                         "element": ch.get("element", ""),
                         "role": ch.get("role", "hybrid")}
            for a in actives:
                info[a["id"]] = {
                    "name": a.get("name", a["id"]),
                    "color": tuple((a.get("color") or [255, 255, 255])[:3]),
                    "desc": a.get("desc", ""),
                    "vfx": a.get("vfx", ""),
                    "key": a.get("key", 1),
                    "kind": "active",
                }
            for p in passives:
                info[p["id"]] = {
                    "name": p.get("name", p["id"]),
                    "color": tuple((p.get("color") or [255, 255, 255])[:3]),
                    "desc": p.get("desc", ""),
                    "vfx": p.get("vfx", ""),
                    "key": 0,
                    "kind": "passive",
                }
    except (IOError, json.JSONDecodeError, KeyError, TypeError, AttributeError):
        kits, info = {}, {}
    _KIT_CACHE, _INFO_CACHE = kits, info
    return kits, info


def kit_of(char_id):
    """取某角色的技能包 {"actives":[...], "passives":[...], "active":..., "role":...}。"""
    kits, _ = _load_kits()
    return kits.get(char_id) or {"actives": [], "passives": [], "active": {},
                                 "passive": {}, "role": "hybrid"}


def skill_info(sid):
    """取技能（主动或被动）的展示信息。返回 dict：name/color/desc/vfx/key/kind。"""
    _, info = _load_kits()
    got = info.get(sid)
    if got:
        return dict(got)
    return {"name": sid, "color": (255, 255, 255), "desc": "", "vfx": "",
            "key": 0, "kind": "active"}


# 各主动技能「类型」的基础冷却（秒）。type 决定冷却与行为，id 只用于展示/配色。
_BASE_CD = {
    "petal_slash": lambda: S.PETAL_SLASH_CD,
    "gale_dash": lambda: S.GALE_DASH_CD,
    "tide_surge": lambda: S.TIDE_SURGE_CD,
    "ember_lash": lambda: S.EMBER_LASH_CD,
    "star_chain": lambda: S.STAR_CHAIN_CD,
    "moon_ward": lambda: S.MOON_WARD_CD,
    "mark": lambda: S.COMBO_MARK_CD,
    "pull": lambda: S.COMBO_PULL_CD,
    "burst": lambda: S.COMBO_BURST_CD,
    "rally": lambda: S.COMBO_RALLY_CD,
    "dash2": lambda: S.DASH2_CD,
    "detonate": lambda: S.DETONATE_CD,
    "gather": lambda: S.GATHER_CD,
    "blade": lambda: S.BLADE_CD,
    "channel": lambda: S.CHANNEL_CD,
    # 潮汐切人五技能（水属性坦克，围绕切人联动，各自独立冷却）
    "tide_handoff": lambda: S.TIDE_HANDOFF_CD,
    "tide_zone": lambda: S.TIDE_ZONE_CD,
    "tide_vortex": lambda: S.TIDE_VORTEX_CD,
    "tide_contract": lambda: S.TIDE_CONTRACT_CD,
    "tide_domain": lambda: S.TIDE_DOMAIN_CD,
    # 樱落种花闭环五技能（樱属性刺客，数值固定不吃职业系数）
    "sakura_dash2": lambda: S.SAKURA_DASH2_CD,
    "sakura_detonate": lambda: S.SAKURA_DETONATE_CD,
    "sakura_gather": lambda: S.SAKURA_GATHER_CD,
    "sakura_blade": lambda: S.SAKURA_BLADE_CD,
    "sakura_channel": lambda: S.SAKURA_CHANNEL_CD,
    # 绯焰灼烧引爆闭环五技能（火属性法师，数值固定不吃职业系数）
    "flare_scatter": lambda: S.FLARE_SCATTER_CD,
    "flare_trail": lambda: S.FLARE_TRAIL_CD,
    "flare_fuse": lambda: S.FLARE_FUSE_CD,
    "flare_ring": lambda: S.FLARE_RING_CD,
    "flare_burst": lambda: S.FLARE_BURST_CD,
    # 星璃连星成轨闭环五技能（星属性游侠，数值固定不吃职业系数）
    "stella_place": lambda: S.STELLA_PLACE_CD,
    "stella_link": lambda: S.STELLA_LINK_CD,
    "stella_well": lambda: S.STELLA_WELL_CD,
    "stella_shower": lambda: S.STELLA_SHOWER_CD,
    "stella_constellation": lambda: S.STELLA_CONST_CD,
    # 月见月相盈亏五技能（月属性坦克，数值固定不吃职业系数）
    "luna_phase_dash": lambda: S.LUNA_DASH_CD,
    "luna_arc": lambda: S.LUNA_ARC_CD,
    "luna_pull": lambda: S.LUNA_PULL_CD,
    "luna_crescent": lambda: S.LUNA_BLADE_CD,
    "luna_fullmoon": lambda: S.LUNA_FULL_CD,
}


# ---------------------------------------------------------------- 数值展示
# 技能介绍面板 / 战斗 tooltip 用：把事件字典里的关键字段翻译成中文标签。
# 顺序即展示顺序；字段不在事件里（如非风系没有 knock）就自动跳过。
def _f_int(v):
    return str(int(round(v)))


def _f_sec(v):
    return f"{v:.1f}s"


def _f_mult(v):
    return f"×{v:.2f}"


def _f_pct(v):
    return f"+{int(round(v * 100))}%"


_STAT_FIELDS = {
    "dash2": [("dmg", "二段伤害", _f_int), ("radius", "爆炸范围", _f_int),
              ("dist", "突进距离", _f_int), ("expire_dmg", "四散伤害", _f_int),
              ("mark_t", "实体存续", _f_sec), ("knock", "击退", _f_int)],
    "detonate": [("dmg", "引爆伤害", _f_int), ("radius", "作用范围", _f_int),
                 ("per_stack", "每层标记", _f_pct)],
    "gather": [("dmg", "聚怪伤害", _f_int), ("radius", "作用范围", _f_int),
               ("strength", "拉拽强度", _f_int), ("slow_time", "减速时长", _f_sec)],
    "blade": [("count", "飞刃数量", _f_int), ("dmg", "单刃伤害", _f_int),
              ("speed", "飞行速度", _f_int), ("life", "存续", _f_sec)],
    "channel": [("time", "读条", _f_sec), ("buff_time", "增益", _f_sec),
                ("atk", "攻击", _f_mult), ("atkspd", "攻速", _f_mult),
                ("speed", "移速", _f_mult)],
    # --- 潮汐切人五技能：介绍面板数值与实战同源（走 _raw_event→_scale_event）---
    "tide_handoff": [("shield_pct", "吸收(最大生命)", _f_pct),
                     ("time", "护盾", _f_sec), ("transfer", "切走转移", _f_pct)],
    "tide_zone": [("radius", "水域半径", _f_int), ("time", "持续", _f_sec),
                  ("enemy_slow", "敌减速后", _f_mult),
                  ("ally_reduce", "己方减伤", _f_pct),
                  ("ally_speed", "己方移速", _f_pct)],
    "tide_vortex": [("time", "引导", _f_sec), ("radius", "聚怪范围", _f_int),
                    ("dmg", "引爆伤害", _f_int)],
    "tide_contract": [("time", "契约", _f_sec), ("atk_ratio", "水柱(攻击)", _f_pct),
                      ("inner_cd", "内置CD", _f_sec)],
    "tide_domain": [("time", "领域", _f_sec), ("wet_amp", "湿身易伤", _f_pct),
                    ("slow_mult", "减速后", _f_mult)],
    # --- 樱落种花闭环五技能：数值与实战同源（伤害按面板算，此处只展机制参数）---
    "sakura_dash2": [("dist", "突进距离", _f_int), ("plant_cap", "沿途种花上限", _f_int),
                     ("shield_pct", "护盾(最大生命)", _f_pct),
                     ("shield_time", "护盾", _f_sec), ("iframe", "无敌帧", _f_sec)],
    "sakura_detonate": [("radius", "引爆半径", _f_int), ("per_stack", "每层标记", _f_pct),
                        ("delay", "二次跳延迟", _f_sec), ("delay_pct", "二次跳伤害", _f_pct)],
    "sakura_gather": [("radius", "花圃半径", _f_int), ("time", "持续", _f_sec),
                      ("tick", "叠层间隔", _f_sec)],
    "sakura_blade": [("range", "射程", _f_int), ("width", "刃宽", _f_int),
                     ("mult", "每段倍率", _f_mult), ("trips", "往返趟数", _f_int),
                     ("marked_bonus", "对标记者", _f_pct)],
    "sakura_channel": [("time", "花期", _f_sec), ("stack", "每段叠层", _f_int),
                       ("bloom_mult", "绽放半径", _f_mult)],
    # --- 绯焰灼烧引爆闭环五技能：伤害按面板算，此处只展机制参数 ---
    "flare_scatter": [("range", "扇形射程", _f_int), ("angle", "半角(度)", lambda v: _f_int(math.degrees(v))),
                      ("count", "火星枚数", _f_int), ("mult", "伤害倍率", _f_mult)],
    "flare_trail": [("length", "火径长", _f_int), ("width", "火径宽", _f_int),
                    ("time", "烙地", _f_sec), ("tick", "叠层间隔", _f_sec),
                    ("tick_mult", "每跳倍率", _f_mult)],
    "flare_fuse": [("range", "点刺射程", _f_int), ("mult", "烙印倍率", _f_mult),
                   ("delay", "自动引爆", _f_sec), ("det_mult", "引爆倍率", _f_mult)],
    "flare_ring": [("radius", "火环半径", _f_int), ("time", "环绕", _f_sec),
                   ("tick", "叠层间隔", _f_sec), ("slow", "减速后", _f_mult),
                   ("amp", "引爆增伤", _f_pct)],
    "flare_burst": [("mult", "引爆倍率", _f_mult), ("refund", "逐人返CD", _f_sec)],
    # --- 星璃连星成轨闭环五技能：事件带 dmg 绝对值，数值与实战同源 ---
    "stella_place": [("dist", "闪现距离", _f_int), ("window", "二段窗口", _f_sec),
                     ("det_radius", "引爆半径", _f_int),
                     ("det_dmg", "二段引爆伤害", _f_int)],
    "stella_link": [("dmg", "单条爆发伤害", _f_int)],
    "stella_well": [("radius", "引力井半径", _f_int), ("time", "持续", _f_sec),
                    ("strength", "拉扯强度", _f_int), ("stun", "眩晕", _f_sec)],
    "stella_shower": [("count", "流星枚数", _f_int), ("dmg", "单枚伤害", _f_int),
                      ("speed", "弹速", _f_int), ("life", "存续", _f_sec)],
    "stella_constellation": [("time", "吟唱", _f_sec), ("dmg", "每条星轨伤害", _f_int),
                             ("max_lines", "星轨上限", _f_int),
                             ("window", "自动连线窗口", _f_sec)],
    # --- 月见月相盈亏五技能：伤害按面板算（mult），此处只展机制参数 ---
    "luna_phase_dash": [("dist", "前冲距离", _f_int), ("iframe", "无敌帧", _f_sec),
                        ("mark_t", "月痕残留", _f_sec),
                        ("field_radius", "二段场半径", _f_int),
                        ("burst_mult", "满月二段倍率", _f_mult),
                        ("heal_pct", "下弦二段治疗", _f_pct)],
    "luna_arc": [("radius", "引爆半径", _f_int), ("mult", "基础倍率", _f_mult),
                 ("per_stack", "每层标记", _f_mult)],
    "luna_pull": [("radius", "拉拽半径", _f_int), ("time", "持续", _f_sec),
                  ("strength", "拉拽强度", _f_int),
                  ("shield_pct", "每拉中护盾", _f_pct)],
    "luna_crescent": [("count", "刃数", _f_int), ("mult", "单刃倍率", _f_mult),
                      ("speed", "弹速", _f_int), ("life", "存续", _f_sec)],
    "luna_fullmoon": [("time", "吟唱", _f_sec), ("lock_time", "满月锁定", _f_sec),
                      ("weaken_tick", "削弱间隔", _f_sec),
                      ("reduce", "自身减伤", _f_pct),
                      ("dmg", "每次月爆伤害", _f_int),
                      ("burst_cap", "月爆上限", _f_int)],
}


class SkillEngine:
    """角色专属技能状态机（多主动）。挂在战斗场景上，每帧 update 一次。"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.char_id = None
        self.actives = []           # [{...active dict...}, ...] 按 key 升序
        self.active_sids = []       # [sid, ...]
        self._sid_type = {}         # {sid: type}
        self.passive = {}           # 首个被动 dict（兼容旧接口）
        self.passives = []          # 被动列表（原被动 + 标记被动）
        self.passive_id = None
        self.passive_kinds = set()  # 所有被动 vfx 集合
        self.has_mark_passive = False  # 是否带「技能叠标记满层自爆」被动
        self.role = "hybrid"        # 职业 tank/mage/assassin（hybrid 为兜底）
        self.element = ""           # 角色元素（樱/风/水/火/星/月），决定连招副效果与特效
        self.cds = {}               # {sid: 剩余冷却秒}
        self.levels = {}            # {sid: 局内强化等级 0..SKILL_ENH_MAX}
        self.gale_left = 0.0        # 薄荷「疾风连闪」移速爆发剩余秒
        self.newly_unlocked = []    # 兼容旧接口（固定包不再解锁，恒为空）

    # ------------------------------------------------------------ kit 装载
    def load_kit(self, char_id):
        """按角色装载专属技能包。战斗 reset 时调用。"""
        self.reset()
        self.char_id = char_id
        kit = kit_of(char_id)
        self.passives = kit.get("passives") or []
        self.passive = self.passives[0] if self.passives else {}
        self.passive_id = self.passive.get("id")
        self.passive_kinds = {p.get("vfx", "") for p in self.passives}
        self.has_mark_passive = "markstack" in self.passive_kinds
        self.role = kit.get("role", "hybrid") or "hybrid"
        self.element = kit.get("element", "") or ""
        actives = kit.get("actives") or []
        self.actives = sorted(actives, key=lambda a: int(a.get("key", 1)))
        self.active_sids = [a.get("id") for a in self.actives if a.get("id")]
        for a in self.actives:
            sid = a.get("id")
            if sid:
                self._sid_type[sid] = a.get("type") or sid
                self.cds[sid] = 0.0
                self.levels[sid] = 0

    @property
    def active(self):
        """兼容旧接口：首个主动（角色专属大招）。"""
        return self.actives[0] if self.actives else {}

    @property
    def active_sid(self):
        """兼容旧接口：首个主动的 sid。"""
        return self.active_sids[0] if self.active_sids else None

    @property
    def passive_kind(self):
        """当前被动的 vfx 标记（battle 用来施加常驻效果/普攻附加）。"""
        return self.passive.get("vfx") or ""

    # ------------------------------------------------------------ 查询
    def has(self, sid):
        return sid in self.active_sids or sid == self.passive_id

    @property
    def count(self):
        """已装载的主动技能数量。"""
        return len(self.active_sids)

    def _type_of(self, sid):
        return self._sid_type.get(sid, sid)

    def _active_by_key(self, key):
        for a in self.actives:
            if int(a.get("key", 1)) == int(key):
                return a
        return None

    def _active_by_sid(self, sid):
        for a in self.actives:
            if a.get("id") == sid:
                return a
        return None

    def cooldown_at(self, sid, lv, cdr=0.0):
        """指定强化等级 lv 下的冷却秒数（数值表/介绍面板用）。
        职业系数：法师技能贵（CD ×1.30）、刺客技能勤（CD ×0.82）。"""
        base = _BASE_CD.get(self._type_of(sid), lambda: 6.0)()
        # 樱落/绯焰/星璃/月见专属五技能：CD 按规格固定，不吃职业系数（会破坏闭环节奏）
        stype = self._type_of(sid)
        role_cd = 1.0 if (stype.startswith("sakura_") or stype.startswith("flare_")
                          or stype.startswith("stella_")
                          or stype.startswith("luna_")) \
            else S.ROLE_CD_MULT.get(self.role, 1.0)
        cd = (base * role_cd * (1.0 - min(0.75, cdr))
              * (1.0 - S.SKILL_ENH_CD_PER_LV * lv))
        return max(0.3, cd)

    def cooldown_max(self, sid=None, cdr=0.0):
        sid = sid or self.active_sid
        if not sid:
            return 0.0
        return self.cooldown_at(sid, self.levels.get(sid, 0), cdr)

    def cooldown_left(self, sid=None):
        sid = sid or self.active_sid
        return self.cds.get(sid, 0.0)

    def cd_ratio(self, sid=None, cdr=0.0):
        """冷却进度 0(刚放)..1(就绪)，供 HUD 转圈。"""
        sid = sid or self.active_sid
        total = self.cooldown_max(sid, cdr)
        if total <= 0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - self.cds.get(sid, 0.0) / total))

    def ready(self, sid=None, cdr=0.0):
        sid = sid or self.active_sid
        return bool(sid) and self.cds.get(sid, 0.0) <= 0.0

    @property
    def gale_active(self):
        return self.gale_left > 0.0

    # ------------------------------------------------------------ 每帧
    def update(self, dt):
        for sid in list(self.cds):
            if self.cds[sid] > 0:
                self.cds[sid] = max(0.0, self.cds[sid] - dt)
        if self.gale_left > 0:
            self.gale_left = max(0.0, self.gale_left - dt)

    def reduce_cd(self, amount):
        """星璃「星辉」被动：击杀缩短所有主动冷却。"""
        for sid in list(self.cds):
            if self.cds[sid] > 0:
                self.cds[sid] = max(0.0, self.cds[sid] - amount)

    def reduce_cd_frac(self, frac):
        """按当前剩余冷却的比例缩减（星元素鼓舞副效果）。"""
        frac = max(0.0, min(1.0, float(frac)))
        for sid in list(self.cds):
            if self.cds[sid] > 0:
                self.cds[sid] = max(0.0, self.cds[sid] * (1.0 - frac))

    # ------------------------------------------------------------ 数值展示
    def stat_lines(self, sid, lv=None, cdr=0.0):
        """返回 [(标签, 数值字符串), ...]：技能 sid 在强化等级 lv 下的关键数值。

        走与实战完全相同的 _raw_event→_apply_element→_scale_event 管线，
        保证介绍里写的数字和局内真实生效的数值一致。lv 默认取当前等级。"""
        if not sid:
            return []
        if lv is None:
            lv = self.levels.get(sid, 0)
        stype = self._type_of(sid)
        ev = self._raw_event(stype, (0, 0))
        if ev is None:
            return []
        self._apply_element(ev, stype)
        self._apply_role(ev, stype)
        if lv > 0:
            self._scale_event(ev, stype, lv)
        # 职业伤害系数由 battle.cast_skill 落地，这里同步乘上，
        # 保证介绍里写的伤害与局内真实生效值一致。
        sd = S.ROLE_SKILLDMG_MULT.get(self.role, 1.0)
        if sd != 1.0 and "dmg" in ev:
            ev["dmg"] = ev["dmg"] * sd
        out = [("冷却", _f_sec(self.cooldown_at(sid, lv, cdr)))]
        for field, label, fmt in _STAT_FIELDS.get(stype, []):
            if field in ev:
                out.append((label, fmt(ev[field])))
        if ev.get("hp_cost"):
            out.append(("生命代价", f"-{ev['hp_cost'] * 100:.1f}%"))
        return out

    def stat_columns(self, sid):
        """返回 [(标签, [Lv0值, Lv1值, ..., 满级值]), ...]，供介绍面板按行展示全等级数值。"""
        table = [self.stat_lines(sid, lv) for lv in range(0, S.SKILL_ENH_MAX + 1)]
        labels = []
        for lines in table:
            for label, _ in lines:
                if label not in labels:
                    labels.append(label)
        cols = []
        for label in labels:
            vals = []
            for lines in table:
                vals.append(dict(lines).get(label, "-"))
            cols.append((label, vals))
        return cols

    # ------------------------------------------------------------ 释放
    def cast(self, pos, key=1, cdr=0.0):
        """
        尝试释放绑定到 key(1-5) 的主动。成功返回事件字典并进入冷却，
        失败（无此键/冷却中）返回 None。pos = 玩家世界像素位置。
        """
        a = self._active_by_key(key)
        if not a:
            return None
        sid = a.get("id")
        if not sid or not self.ready(sid, cdr):
            return None
        stype = a.get("type") or sid
        lv = self.levels.get(sid, 0)
        ev = self._build_event(stype, pos, lv)
        if ev is None:
            return None
        self.cds[sid] = self.cooldown_max(sid, cdr)
        ev["color"] = tuple((a.get("color") or [255, 255, 255])[:3])
        ev["name"] = a.get("name", sid)
        ev["sid"] = sid
        ev["lv"] = lv
        return ev

    def _build_event(self, stype, pos, lv=0):
        """构造技能事件并按局内强化等级 lv 放大数值 / 追加满级小机制。"""
        ev = self._raw_event(stype, pos)
        if ev is None:
            return None
        if stype in ("mark", "pull", "burst", "rally",
                     "dash2", "detonate", "gather", "blade", "channel"):
            self._apply_element(ev, stype)
            self._apply_role(ev, stype)
        if lv > 0:
            self._scale_event(ev, stype, lv)
        return ev

    def _apply_role(self, ev, stype):
        """按职业把「手长 / 近战、消耗 / 爆发」的手感差异落到事件数值上。

        法师：射程远、范围略大、读条久、伤害型技能附带生命代价（手长消耗多）；
        刺客：射程短、位移更远、范围小、读条快（近战高爆发，伤害靠
              battle 的 ROLE_SKILLDMG_MULT 放大）；
        坦克：范围最大、拉拽更狠、冷却略短（罩场开团）。
        调用时机：_apply_element 之后（元素副效果先定型）、_scale_event 之前
        （局内强化按职业调整后的基数放大）。hybrid / 未知职业原样返回。
        """
        role = self.role or "hybrid"
        if role not in ("tank", "mage", "assassin"):
            return ev
        # 潮汐切人五技能 / 樱落种花五技能 / 绯焰灼烧引爆五技能 / 星璃连星成轨五技能
        # / 月见月相盈亏五技能：数值按规格固定，不吃职业范围/射程/读条系数
        # （局内强化仍由 _scale_event 统一放大）。
        if (stype.startswith("tide_") or stype.startswith("sakura_")
                or stype.startswith("flare_") or stype.startswith("stella_")
                or stype.startswith("luna_")):
            return ev
        area = S.ROLE_AREA_MULT.get(role, 1.0)
        for k in ("radius", "range", "length", "width"):
            if k in ev:
                ev[k] = ev[k] * area
        if stype in ("blade", "star_chain"):
            life = S.ROLE_PROJ_LIFE_MULT.get(role, 1.0)
            if "life" in ev:
                ev["life"] = ev["life"] * life
        if stype in ("dash2", "gale_dash", "petal_slash"):
            dist = S.ROLE_DASH_DIST_MULT.get(role, 1.0)
            if "dist" in ev:
                ev["dist"] = ev["dist"] * dist
        if stype in ("gather", "pull") and "strength" in ev:
            ev["strength"] = ev["strength"] * area
        if stype in ("channel", "rally") and "time" in ev:
            ev["time"] = ev["time"] * S.ROLE_CHANNEL_MULT.get(role, 1.0)
        cost = S.ROLE_HPCOST.get(role, 0.0)
        if cost > 0 and stype in ("dash2", "detonate", "gather", "blade"):
            ev["hp_cost"] = cost
        return ev

    def _apply_element(self, ev, stype):
        """按角色元素给连招组件（mark/pull/burst/rally）附加差异化副效果。

        框架仍是「标记/聚怪/引爆/鼓舞」四件套，但不同元素的副效果与特效
        各异，避免全员换皮：风=击退/减速、水=冻结、火=灼烧、星=落星/眩晕、
        月=削弱/护盾/回血、樱=绽放。battle 按这些字段落地状态与 VFX。
        """
        el = self.element
        ev["element"] = el
        if not el:
            return ev
        if stype == "mark":
            if el == "风":
                ev.setdefault("slow_mult", 0.7)
                ev.setdefault("slow_time", 1.5)
            elif el == "水":
                ev.setdefault("freeze_time", 0.6)
            elif el == "火":
                ev.setdefault("burn_dps", S.EMBER_BURN_DPS * 0.6)
                ev.setdefault("burn_time", 2.0)
            elif el == "月":
                ev.setdefault("weaken_mult", 0.8)
                ev.setdefault("weaken_time", 2.0)
            elif el == "星":
                ev["amp"] = ev.get("amp", S.COMBO_MARK_AMP) * 1.2
        elif stype == "pull":
            if el == "风":
                ev.setdefault("knock", S.TIDE_KNOCK)
            elif el == "水":
                ev.setdefault("freeze_time", 0.8)
            elif el == "火":
                ev.setdefault("burn_dps", S.EMBER_BURN_DPS * 0.6)
                ev.setdefault("burn_time", 2.0)
            elif el == "星":
                ev.setdefault("stun_time", 0.5)
            elif el == "月":
                ev.setdefault("shield", 1.0)
        elif stype == "burst":
            if el == "风":
                ev.setdefault("knock", S.TIDE_KNOCK * 1.3)
            elif el == "水":
                ev.setdefault("freeze_time", 1.0)
            elif el == "火":
                ev.setdefault("burn_dps", S.EMBER_BURN_DPS)
                ev.setdefault("burn_time", 3.0)
            elif el == "星":
                ev.setdefault("starfall", 1)
            elif el == "月":
                ev.setdefault("weaken_mult", 0.7)
                ev.setdefault("weaken_time", 3.0)
            elif el == "樱":
                ev.setdefault("bloom", 1)
        elif stype == "rally":
            if el == "风":
                ev.setdefault("speed_bonus", 0.15)
            elif el == "水":
                ev.setdefault("shield", 1.5)
            elif el == "火":
                ev.setdefault("burn_aura", True)
            elif el == "星":
                ev.setdefault("cdr_bonus", 0.15)
            elif el == "月":
                ev.setdefault("heal", 0.15)
                ev.setdefault("armor_bonus", 0.15)
        elif stype == "dash2":
            if el == "风":
                ev.setdefault("knock", S.TIDE_KNOCK)
            elif el == "水":
                ev.setdefault("freeze_time", 0.6)
            elif el == "火":
                ev.setdefault("burn_dps", S.EMBER_BURN_DPS * 0.6)
                ev.setdefault("burn_time", 2.0)
            elif el == "星":
                ev.setdefault("starfall", 1)
            elif el == "月":
                ev.setdefault("shield", 1.0)
            elif el == "樱":
                ev.setdefault("bloom", 1)
        elif stype == "detonate":
            if el == "风":
                ev.setdefault("knock", S.TIDE_KNOCK * 1.2)
            elif el == "水":
                ev.setdefault("freeze_time", 1.0)
            elif el == "火":
                ev.setdefault("burn_dps", S.EMBER_BURN_DPS)
                ev.setdefault("burn_time", 3.0)
            elif el == "星":
                ev.setdefault("starfall", 1)
            elif el == "月":
                ev.setdefault("weaken_mult", 0.7)
                ev.setdefault("weaken_time", 3.0)
                ev.setdefault("shield", 1.0)
            elif el == "樱":
                ev.setdefault("bloom", 1)
        elif stype == "gather":
            if el == "风":
                ev.setdefault("knock", S.TIDE_KNOCK)
            elif el == "水":
                ev.setdefault("freeze_time", 0.8)
            elif el == "火":
                ev.setdefault("burn_dps", S.EMBER_BURN_DPS * 0.6)
                ev.setdefault("burn_time", 2.0)
            elif el == "星":
                ev.setdefault("stun_time", 0.5)
            elif el == "月":
                ev.setdefault("shield", 1.0)
            elif el == "樱":
                ev.setdefault("bloom", 1)
        elif stype == "blade":
            if el == "风":
                ev.setdefault("knock", S.TIDE_KNOCK * 0.6)
            elif el == "水":
                ev.setdefault("slow_mult", 0.7)
                ev.setdefault("slow_time", 1.5)
            elif el == "火":
                ev.setdefault("burn_dps", S.EMBER_BURN_DPS * 0.6)
                ev.setdefault("burn_time", 2.0)
            elif el == "星":
                ev.setdefault("pierce", 1)
            elif el == "月":
                ev.setdefault("weaken_mult", 0.8)
                ev.setdefault("weaken_time", 2.0)
            elif el == "樱":
                ev.setdefault("bloom", 1)
        elif stype == "channel":
            if el == "风":
                ev.setdefault("speed_bonus", 0.15)
            elif el == "水":
                ev.setdefault("shield", 1.5)
            elif el == "火":
                ev.setdefault("burn_aura", True)
            elif el == "星":
                ev.setdefault("cdr_bonus", 0.15)
            elif el == "月":
                ev.setdefault("heal", 0.15)
                ev.setdefault("armor_bonus", 0.15)
            elif el == "樱":
                ev.setdefault("atk_bonus", 0.10)
        return ev

    def _scale_event(self, ev, stype, lv):
        """通用强化缩放：伤害 ×(1+0.22lv)、范围/数量 ×(1+0.10lv)，满级再加大招小机制。"""
        dmg_mult = 1.0 + S.SKILL_ENH_DMG_PER_LV * lv
        area_mult = 1.0 + S.SKILL_ENH_AREA_PER_LV * lv
        if "dmg" in ev:
            ev["dmg"] = int(round(ev["dmg"] * dmg_mult))
        for k in ("radius", "range", "length", "width"):
            if k in ev:
                ev[k] = ev[k] * area_mult
        if "count" in ev:
            ev["count"] = max(1, int(round(ev["count"] * area_mult)))
        if lv >= S.SKILL_ENH_MAX:
            self._max_bonus(ev, stype)

    def _max_bonus(self, ev, stype):
        """满级（Lv.SKILL_ENH_MAX）小机制：每个技能类型各加一点质变。"""
        if stype == "petal_slash":
            ev["double"] = True                                # 斩击打两次（第二段半伤）
        elif stype == "gale_dash":
            ev["count"] = ev.get("count", 3) + 1               # 多一段突进
        elif stype == "tide_surge":
            ev["slow_mult"] = ev.get("slow_mult", 0.5) * 0.8   # 减速更狠
        elif stype == "ember_lash":
            ev["burn_time"] = ev.get("burn_time", 3.0) + 1.5   # 灼烧更久
            ev["angle"] = ev.get("angle", 0.7) * 1.25          # 扇形更宽
        elif stype == "star_chain":
            ev["count"] = ev.get("count", 6) + 2               # 多两枚星弹
            ev["pierce"] = ev.get("pierce", 1) + 1             # 穿透 +1
        elif stype == "moon_ward":
            ev["shield"] = ev.get("shield", 1.5) + 0.5         # 护盾更久
        elif stype == "mark":
            ev["max_stacks"] = ev.get("max_stacks", 3) + 1     # 可叠 4 层
        elif stype == "pull":
            ev["root_mult"] = 0.2                              # 附带定身（减速到 0.2）
            ev["root_time"] = 0.5
        elif stype == "burst":
            ev["per_stack"] = ev.get("per_stack", 0.30) + 0.10  # 每层标记加成更高
            ev["radius"] = ev.get("radius", 300) * 1.15         # 范围更大
        elif stype == "rally":
            ev["armor_bonus"] = 0.20                           # 增益期内额外 20% 减伤
        elif stype == "dash2":
            ev["radius"] = ev.get("radius", 150) * 1.2         # 二段 AoE 更大
        elif stype == "detonate":
            ev["per_stack"] = ev.get("per_stack", 0.35) + 0.10  # 每层标记加成更高
            ev["radius"] = ev.get("radius", 300) * 1.15
        elif stype == "gather":
            ev["root_mult"] = 0.2                              # 附带定身
            ev["root_time"] = 0.5
        elif stype == "blade":
            ev["count"] = ev.get("count", 4) + 2               # 多两道飞行物
        elif stype == "channel":
            ev["armor_bonus"] = 0.20                           # 增益期内额外减伤
        elif stype == "tide_handoff":
            ev["transfer"] = min(0.90, ev.get("transfer", 0.60) + 0.15)  # 切走转移 75%
        elif stype == "tide_zone":
            ev["time"] = ev.get("time", 8.0) + 3.0             # 水域更久
        elif stype == "tide_vortex":
            ev["dmg"] = int(round(ev.get("dmg", 200) * 1.3))    # 引爆更痛
        elif stype == "tide_contract":
            ev["time"] = ev.get("time", 8.0) + 3.0             # 契约更久
        elif stype == "tide_domain":
            ev["wet_amp"] = ev.get("wet_amp", 0.20) + 0.10      # 湿身易伤更高
        elif stype == "stella_place":
            ev["det_radius"] = ev.get("det_radius", 130) * 1.2  # 二段引爆范围更大
        elif stype == "stella_link":
            ev["dmg"] = int(round(ev.get("dmg", 120) * 1.25))   # 单条爆发更痛
        elif stype == "stella_well":
            ev["stun"] = ev.get("stun", 0.6) + 0.3              # 眩晕更久
        elif stype == "stella_shower":
            ev["count"] = ev.get("count", 6) + 2                # 多两枚流星
        elif stype == "stella_constellation":
            ev["max_lines"] = ev.get("max_lines", 15) + 5       # 星座更密
        elif stype == "luna_phase_dash":
            ev["iframe"] = ev.get("iframe", 0.35) + 0.15        # 无敌帧更久
        elif stype == "luna_arc":
            ev["per_stack"] = ev.get("per_stack", 0.35) + 0.15  # 每层标记加成更高
        elif stype == "luna_pull":
            ev["shield_pct"] = ev.get("shield_pct", 0.04) * 1.5  # 每拉中护盾更厚
        elif stype == "luna_crescent":
            ev["count"] = ev.get("count", 3) + 2                # 多两道月刃
        elif stype == "luna_fullmoon":
            ev["burst_cap"] = ev.get("burst_cap", 12) + 4       # 月爆上限更高
        # 元素副效果满级质变：把该元素的招牌副效果再放大一档
        el = self.element
        if el == "水" and "freeze_time" in ev:
            ev["freeze_time"] = ev["freeze_time"] * 1.5
        elif el == "火" and "burn_time" in ev:
            ev["burn_time"] = ev["burn_time"] + 1.0
        elif el == "风" and "knock" in ev:
            ev["knock"] = ev["knock"] * 1.3
        elif el == "月" and "weaken_time" in ev:
            ev["weaken_time"] = ev["weaken_time"] + 1.0
        elif el == "星" and ev.get("starfall"):
            ev["starfall"] = ev["starfall"] + 1
        elif el == "樱" and ev.get("bloom"):
            ev["bloom"] = ev["bloom"] + 1

    def _raw_event(self, stype, pos):
        """按技能类型构造基础事件字典（数值全部取自 settings，未强化）。"""
        if stype == "petal_slash":
            return {"type": "petal_slash",
                    "dist": S.PETAL_SLASH_DIST, "dmg": S.PETAL_SLASH_DMG,
                    "shield": S.PETAL_SLASH_SHIELD}
        if stype == "gale_dash":
            self.gale_left = S.GALE_SPEED_TIME
            return {"type": "gale_dash",
                    "count": S.GALE_DASH_COUNT, "dist": S.GALE_DASH_DIST,
                    "dmg": S.GALE_DASH_DMG}
        if stype == "tide_surge":
            return {"type": "tide_surge",
                    "radius": S.TIDE_SURGE_RADIUS, "dmg": S.TIDE_SURGE_DMG,
                    "slow_mult": S.TIDE_SLOW_MULT, "slow_time": S.TIDE_SLOW_TIME,
                    "knock": S.TIDE_KNOCK}
        if stype == "ember_lash":
            return {"type": "ember_lash",
                    "range": S.EMBER_LASH_RANGE, "angle": S.EMBER_LASH_ANGLE,
                    "dmg": S.EMBER_LASH_DMG,
                    "burn_dps": S.EMBER_BURN_DPS, "burn_time": S.EMBER_BURN_TIME}
        if stype == "star_chain":
            return {"type": "star_chain",
                    "count": S.STAR_CHAIN_COUNT, "dmg": S.STAR_CHAIN_DMG,
                    "speed": S.STAR_CHAIN_SPEED, "life": S.STAR_CHAIN_LIFE}
        if stype == "moon_ward":
            return {"type": "moon_ward",
                    "length": S.MOON_WARD_LEN, "width": S.MOON_WARD_WIDTH,
                    "dmg": S.MOON_WARD_DMG, "shield": S.MOON_WARD_SHIELD}
        if stype == "mark":
            return {"type": "mark",
                    "radius": S.COMBO_MARK_RADIUS, "dmg": S.COMBO_MARK_DMG,
                    "amp": S.COMBO_MARK_AMP, "time": S.COMBO_MARK_TIME,
                    "max_stacks": S.COMBO_MARK_MAX_STACKS}
        if stype == "pull":
            return {"type": "pull",
                    "radius": S.COMBO_PULL_RADIUS, "strength": S.COMBO_PULL_STRENGTH,
                    "dmg": S.COMBO_PULL_DMG, "slow_mult": S.COMBO_PULL_SLOW_MULT,
                    "slow_time": S.COMBO_PULL_SLOW_TIME}
        if stype == "burst":
            return {"type": "burst",
                    "radius": S.COMBO_BURST_RADIUS, "dmg": S.COMBO_BURST_DMG,
                    "status_bonus": S.COMBO_BURST_STATUS_BONUS,
                    "per_stack": S.COMBO_BURST_PER_STACK,
                    "time_bonus": S.COMBO_BURST_TIME_BONUS,
                    "mark_time_full": S.COMBO_MARK_TIME}
        if stype == "rally":
            return {"type": "rally",
                    "time": S.COMBO_RALLY_TIME, "atk": S.COMBO_RALLY_ATK,
                    "atkspd": S.COMBO_RALLY_ATKSPD}
        if stype == "dash2":
            return {"type": "dash2",
                    "dist": S.DASH2_DIST, "dmg": S.DASH2_DMG,
                    "radius": S.DASH2_RADIUS, "mark_t": S.DASH2_MARK_T,
                    "expire_dmg": S.DASH2_EXPIRE_DMG}
        if stype == "detonate":
            return {"type": "detonate",
                    "radius": S.DETONATE_RADIUS, "dmg": S.DETONATE_DMG,
                    "per_stack": S.DETONATE_PER_STACK,
                    "max_stacks": S.MARKPASSIVE_STACKS}
        if stype == "gather":
            return {"type": "gather",
                    "radius": S.GATHER_RADIUS, "strength": S.GATHER_STRENGTH,
                    "dmg": S.GATHER_DMG, "slow_mult": S.GATHER_SLOW_MULT,
                    "slow_time": S.GATHER_SLOW_TIME,
                    "max_stacks": S.MARKPASSIVE_STACKS}
        if stype == "blade":
            return {"type": "blade",
                    "count": S.BLADE_COUNT, "dmg": S.BLADE_DMG,
                    "speed": S.BLADE_SPEED, "life": S.BLADE_LIFE,
                    "max_stacks": S.MARKPASSIVE_STACKS}
        if stype == "channel":
            return {"type": "channel",
                    "time": S.CHANNEL_TIME, "buff_time": S.CHANNEL_BUFF_TIME,
                    "atk": S.CHANNEL_ATK, "atkspd": S.CHANNEL_ATKSPD,
                    "speed": S.CHANNEL_SPEED}
        # ---- 潮汐切人五技能（数值全部取自 settings，未强化）----
        if stype == "tide_handoff":
            return {"type": "tide_handoff",
                    "shield_pct": S.TIDE_HANDOFF_SHIELD_PCT,
                    "time": S.TIDE_HANDOFF_TIME,
                    "transfer": S.TIDE_HANDOFF_TRANSFER}
        if stype == "tide_zone":
            return {"type": "tide_zone",
                    "radius": S.TIDE_ZONE_RADIUS, "time": S.TIDE_ZONE_TIME,
                    "enemy_slow": S.TIDE_ZONE_ENEMY_SLOW,
                    "ally_reduce": S.TIDE_ZONE_ALLY_REDUCE,
                    "ally_speed": S.TIDE_ZONE_ALLY_SPEED}
        if stype == "tide_vortex":
            return {"type": "tide_vortex",
                    "time": S.TIDE_VORTEX_TIME, "radius": S.TIDE_VORTEX_RADIUS,
                    "strength": S.TIDE_VORTEX_STRENGTH,
                    "tick_dmg": S.TIDE_VORTEX_TICK_DMG,
                    "dmg": S.TIDE_VORTEX_DETONATE_DMG}
        if stype == "tide_contract":
            return {"type": "tide_contract",
                    "time": S.TIDE_CONTRACT_TIME,
                    "atk_ratio": S.TIDE_CONTRACT_ATK_RATIO,
                    "inner_cd": S.TIDE_CONTRACT_INNER_CD}
        if stype == "tide_domain":
            return {"type": "tide_domain",
                    "time": S.TIDE_DOMAIN_TIME, "wet_amp": S.TIDE_DOMAIN_WET_AMP,
                    "slow_mult": S.TIDE_DOMAIN_SLOW,
                    "shield_per_sec": S.TIDE_DOMAIN_SHIELD_PER_SEC}
        # ---- 樱落种花闭环五技能（不带 dmg，伤害由 battle._sakura_skill_dmg 按面板算）----
        if stype == "sakura_dash2":
            return {"type": "sakura_dash2",
                    "dist": S.SAKURA_DASH2_DIST, "time": S.SAKURA_DASH2_TIME,
                    "plant_step": S.SAKURA_DASH2_PLANT_STEP,
                    "plant_cap": S.SAKURA_DASH2_PLANT_CAP,
                    "shield_pct": S.SAKURA_DASH2_SHIELD_PCT,
                    "shield_time": S.SAKURA_DASH2_SHIELD_TIME,
                    "iframe": S.SAKURA_DASH2_IFRAME}
        if stype == "sakura_detonate":
            return {"type": "sakura_detonate",
                    "radius": S.SAKURA_DETONATE_RADIUS,
                    "per_stack": S.SAKURA_DETONATE_PER_STACK,
                    "delay": S.SAKURA_DETONATE_DELAY,
                    "delay_pct": S.SAKURA_DETONATE_DELAY_PCT}
        if stype == "sakura_gather":
            return {"type": "sakura_gather",
                    "radius": S.SAKURA_GATHER_RADIUS, "time": S.SAKURA_GATHER_TIME,
                    "tick": S.SAKURA_GATHER_TICK}
        if stype == "sakura_blade":
            return {"type": "sakura_blade",
                    "range": S.SAKURA_BLADE_RANGE, "width": S.SAKURA_BLADE_WIDTH,
                    "mult": S.SAKURA_BLADE_MULT, "trips": S.SAKURA_BLADE_TRIPS,
                    "marked_bonus": S.SAKURA_BLADE_MARKED_BONUS}
        if stype == "sakura_channel":
            return {"type": "sakura_channel",
                    "time": S.SAKURA_CHANNEL_TIME, "stack": S.SAKURA_CHANNEL_STACK,
                    "bloom_mult": S.SAKURA_CHANNEL_BLOOM_MULT}
        # ---- 绯焰灼烧引爆闭环五技能（不带 dmg，伤害由 battle._flare_skill_dmg 按面板算）----
        if stype == "flare_scatter":
            return {"type": "flare_scatter",
                    "range": S.FLARE_SCATTER_RANGE, "angle": S.FLARE_SCATTER_ANGLE,
                    "count": S.FLARE_SCATTER_COUNT, "mult": S.FLARE_SCATTER_MULT}
        if stype == "flare_trail":
            return {"type": "flare_trail",
                    "length": S.FLARE_TRAIL_LEN, "width": S.FLARE_TRAIL_WIDTH,
                    "time": S.FLARE_TRAIL_TIME, "tick": S.FLARE_TRAIL_TICK,
                    "tick_mult": S.FLARE_TRAIL_TICK_MULT}
        if stype == "flare_fuse":
            return {"type": "flare_fuse",
                    "range": S.FLARE_FUSE_RANGE, "mult": S.FLARE_FUSE_MULT,
                    "delay": S.FLARE_FUSE_DELAY, "det_mult": S.FLARE_FUSE_DET_MULT}
        if stype == "flare_ring":
            return {"type": "flare_ring",
                    "radius": S.FLARE_RING_RADIUS, "time": S.FLARE_RING_TIME,
                    "tick": S.FLARE_RING_TICK, "slow": S.FLARE_RING_SLOW,
                    "amp": S.FLARE_RING_AMP}
        if stype == "flare_burst":
            return {"type": "flare_burst",
                    "mult": S.FLARE_BURST_MULT, "refund": S.FLARE_BURST_REFUND}
        # ---- 星璃连星成轨闭环五技能（带 dmg 绝对值，走 cast_skill/_scale_event 缩放）----
        if stype == "stella_place":
            return {"type": "stella_place",
                    "dist": S.STELLA_PLACE_DIST, "window": S.STELLA_PLACE_WINDOW,
                    "det_radius": S.STELLA_PLACE_DET_RADIUS,
                    "det_dmg": S.STELLA_PLACE_DET_DMG}
        if stype == "stella_link":
            return {"type": "stella_link", "dmg": S.STELLA_LINK_BURST_DMG}
        if stype == "stella_well":
            return {"type": "stella_well",
                    "radius": S.STELLA_WELL_RADIUS, "time": S.STELLA_WELL_TIME,
                    "strength": S.STELLA_WELL_STRENGTH, "stun": S.STELLA_WELL_STUN}
        if stype == "stella_shower":
            return {"type": "stella_shower",
                    "count": S.STELLA_SHOWER_COUNT, "dmg": S.STELLA_SHOWER_DMG,
                    "speed": S.STELLA_SHOWER_SPEED, "life": S.STELLA_SHOWER_LIFE}
        if stype == "stella_constellation":
            return {"type": "stella_constellation",
                    "time": S.STELLA_CONST_TIME, "dmg": S.STELLA_CONST_DMG,
                    "max_lines": S.STELLA_CONST_MAX_LINES,
                    "window": S.STELLA_CONST_WINDOW}
        # ---- 月见月相盈亏五技能（伤害按面板算 mult，仅望月带 dmg 绝对值供缩放）----
        if stype == "luna_phase_dash":
            return {"type": "luna_phase_dash",
                    "dist": S.LUNA_DASH_DIST, "time": S.LUNA_DASH_TIME,
                    "iframe": S.LUNA_DASH_IFRAME, "mark_t": S.LUNA_DASH_MARK_T,
                    "field_radius": S.LUNA_DASH_FIELD_RADIUS,
                    "field_time": S.LUNA_DASH_FIELD_TIME,
                    "speed_mult": S.LUNA_DASH_SPEED_MULT,
                    "burst_mult": S.LUNA_DASH_BURST_MULT,
                    "heal_pct": S.LUNA_DASH_HEAL_PCT,
                    "shield_pct": S.LUNA_BOON_SHIELD_PCT,
                    "shield_time": S.LUNA_BOON_SHIELD_TIME}
        if stype == "luna_arc":
            return {"type": "luna_arc",
                    "radius": S.LUNA_ARC_RADIUS, "mult": S.LUNA_ARC_MULT,
                    "per_stack": S.LUNA_ARC_PER_STACK,
                    "max_stacks": S.MARKPASSIVE_STACKS}
        if stype == "luna_pull":
            return {"type": "luna_pull",
                    "radius": S.LUNA_PULL_RADIUS,
                    "strength": S.LUNA_PULL_STRENGTH,
                    "time": S.LUNA_PULL_TIME,
                    "shield_pct": S.LUNA_PULL_SHIELD_PCT,
                    "shield_time": S.LUNA_PULL_SHIELD_TIME}
        if stype == "luna_crescent":
            return {"type": "luna_crescent",
                    "count": S.LUNA_BLADE_COUNT, "mult": S.LUNA_BLADE_MULT,
                    "speed": S.LUNA_BLADE_SPEED, "life": S.LUNA_BLADE_LIFE,
                    "max_stacks": S.MARKPASSIVE_STACKS}
        if stype == "luna_fullmoon":
            return {"type": "luna_fullmoon",
                    "time": S.LUNA_FULL_TIME, "lock_time": S.LUNA_FULL_LOCK_TIME,
                    "weaken_tick": S.LUNA_FULL_WEAKEN_TICK,
                    "reduce": S.LUNA_FULL_REDUCE,
                    "dmg": S.LUNA_FULL_BURST_DMG,
                    "burst_cap": S.LUNA_FULL_BURST_CAP}
        return None
