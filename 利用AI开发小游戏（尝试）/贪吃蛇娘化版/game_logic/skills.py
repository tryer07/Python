# -*- coding: utf-8 -*-
"""
game_logic/skills.py —— 角色专属技能包（固定，无共通技能）

设计变更（相较旧「共通技能 + 选卡解锁」版）：
  · 每名角色拥有自己的一套「专属技能包」：1 个主动（绑 1 键，有冷却）+ 1 个常驻被动。
  · 技能不再通过升级选卡获得；选卡只给通用属性。技能 id / 名字 / 颜色 / 特效
    全部走 data/characters.json 的 kit 字段，数值走 settings.py。
  · SkillEngine 只管：当前角色 kit、主动冷却计时、以及少量持续态（薄荷移速爆发）。
    瞬发效果通过 cast() 返回「事件字典」，由 battle 落地（施加伤害/位移/生成弹丸/
    附加减速灼烧），这样技能逻辑可单测、不依赖 battle 内部。
  · 减速 / 灼烧等持续状态挂在 Mob 上（见 entities.py），引擎不持有。

坐标系：与实体一致，世界像素。
"""

import json
import os

import settings as S

_KIT_CACHE = None      # {char_id: {"active": {...}, "passive": {...}}}
_INFO_CACHE = None     # {sid: {name,color,desc,vfx,key}}


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
            active = kit.get("active") or {}
            passive = kit.get("passive") or {}
            kits[cid] = {"active": active, "passive": passive}
            if active.get("id"):
                info[active["id"]] = {
                    "name": active.get("name", active["id"]),
                    "color": tuple((active.get("color") or [255, 255, 255])[:3]),
                    "desc": active.get("desc", ""),
                    "vfx": active.get("vfx", ""),
                    "key": active.get("key", 1),
                    "kind": "active",
                }
            if passive.get("id"):
                info[passive["id"]] = {
                    "name": passive.get("name", passive["id"]),
                    "color": tuple((passive.get("color") or [255, 255, 255])[:3]),
                    "desc": passive.get("desc", ""),
                    "vfx": passive.get("vfx", ""),
                    "key": 0,
                    "kind": "passive",
                }
    except (IOError, json.JSONDecodeError, KeyError, TypeError, AttributeError):
        kits, info = {}, {}
    _KIT_CACHE, _INFO_CACHE = kits, info
    return kits, info


def kit_of(char_id):
    """取某角色的技能包 {"active":..., "passive":...}，取不到返回空 dict 结构。"""
    kits, _ = _load_kits()
    return kits.get(char_id) or {"active": {}, "passive": {}}


def skill_info(sid):
    """取技能（主动或被动）的展示信息。返回 dict：name/color/desc/vfx/key/kind。"""
    _, info = _load_kits()
    got = info.get(sid)
    if got:
        return dict(got)
    return {"name": sid, "color": (255, 255, 255), "desc": "", "vfx": "",
            "key": 0, "kind": "active"}


# 各专属主动的基础冷却（秒），集中在此便于查
_BASE_CD = {
    "petal_slash": lambda: S.PETAL_SLASH_CD,
    "gale_dash": lambda: S.GALE_DASH_CD,
    "tide_surge": lambda: S.TIDE_SURGE_CD,
    "ember_lash": lambda: S.EMBER_LASH_CD,
    "star_chain": lambda: S.STAR_CHAIN_CD,
    "moon_ward": lambda: S.MOON_WARD_CD,
}


class SkillEngine:
    """角色专属技能状态机。挂在战斗场景上，每帧 update 一次。"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.char_id = None
        self.active = {}            # 主动 dict（来自 kit）
        self.passive = {}           # 被动 dict（来自 kit）
        self.active_sid = None
        self.passive_id = None
        self.cds = {}               # {active_sid: 剩余冷却秒}
        self.gale_left = 0.0        # 薄荷「疾风连闪」移速爆发剩余秒
        self.newly_unlocked = []    # 兼容旧接口（固定包不再解锁，恒为空）

    # ------------------------------------------------------------ kit 装载
    def load_kit(self, char_id):
        """按角色装载专属技能包。战斗 reset 时调用。"""
        self.reset()
        self.char_id = char_id
        kit = kit_of(char_id)
        self.active = kit.get("active") or {}
        self.passive = kit.get("passive") or {}
        self.active_sid = self.active.get("id")
        self.passive_id = self.passive.get("id")
        if self.active_sid:
            self.cds[self.active_sid] = 0.0

    @property
    def passive_kind(self):
        """当前被动的 vfx 标记（battle 用来施加常驻效果/普攻附加）。"""
        return self.passive.get("vfx") or ""

    # ------------------------------------------------------------ 查询
    def has(self, sid):
        return sid in (self.active_sid, self.passive_id)

    @property
    def count(self):
        """兼容旧接口：固定包视为已拥有 1 个主动。"""
        return 1 if self.active_sid else 0

    def cooldown_max(self, sid=None, cdr=0.0):
        sid = sid or self.active_sid
        if not sid:
            return 0.0
        base = _BASE_CD.get(sid, lambda: 6.0)()
        return max(0.3, base * (1.0 - min(0.75, cdr)))

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
        """星璃「星辉」被动：击杀缩短主动冷却。"""
        if self.active_sid and self.cds.get(self.active_sid, 0.0) > 0:
            self.cds[self.active_sid] = max(
                0.0, self.cds[self.active_sid] - amount)

    # ------------------------------------------------------------ 释放
    def cast(self, pos, cdr=0.0):
        """
        尝试释放当前角色专属主动。成功返回事件字典并进入冷却，
        失败（无主动/冷却中）返回 None。pos = 玩家世界像素位置。
        """
        sid = self.active_sid
        if not sid or not self.ready(sid, cdr):
            return None
        self.cds[sid] = self.cooldown_max(sid, cdr)

        if sid == "petal_slash":
            return {"type": "petal_slash",
                    "dist": S.PETAL_SLASH_DIST, "dmg": S.PETAL_SLASH_DMG,
                    "shield": S.PETAL_SLASH_SHIELD}
        if sid == "gale_dash":
            self.gale_left = S.GALE_SPEED_TIME
            return {"type": "gale_dash",
                    "count": S.GALE_DASH_COUNT, "dist": S.GALE_DASH_DIST,
                    "dmg": S.GALE_DASH_DMG}
        if sid == "tide_surge":
            return {"type": "tide_surge",
                    "radius": S.TIDE_SURGE_RADIUS, "dmg": S.TIDE_SURGE_DMG,
                    "slow_mult": S.TIDE_SLOW_MULT, "slow_time": S.TIDE_SLOW_TIME,
                    "knock": S.TIDE_KNOCK}
        if sid == "ember_lash":
            return {"type": "ember_lash",
                    "range": S.EMBER_LASH_RANGE, "angle": S.EMBER_LASH_ANGLE,
                    "dmg": S.EMBER_LASH_DMG,
                    "burn_dps": S.EMBER_BURN_DPS, "burn_time": S.EMBER_BURN_TIME}
        if sid == "star_chain":
            return {"type": "star_chain",
                    "count": S.STAR_CHAIN_COUNT, "dmg": S.STAR_CHAIN_DMG,
                    "speed": S.STAR_CHAIN_SPEED, "life": S.STAR_CHAIN_LIFE}
        if sid == "moon_ward":
            return {"type": "moon_ward",
                    "length": S.MOON_WARD_LEN, "width": S.MOON_WARD_WIDTH,
                    "dmg": S.MOON_WARD_DMG, "shield": S.MOON_WARD_SHIELD}
        self.cds[sid] = 0.0
        return None
