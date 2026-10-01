# -*- coding: utf-8 -*-
"""
game_logic/skills.py —— 技能系统

设计原则（按你的要求）：技能靠升级解锁，但**不额外加按键**。
贪吃蛇的核心乐趣是「只操控方向」，多一套技能键会毁掉这个纯度。
所以这里所有技能都是「被动 / 自动触发」：

    dash    樱花冲锋   移动时碾过相邻小怪
    spike   荆棘尾     撞到身体的小怪也受伤
    thorn   蔓生荆棘   走过的地面留下伤害地形
    shield  星辉护盾   周期性自动无敌
    storm   樱花风暴   周期性周身范围伤害

SkillEngine 负责记账：计时器、冷却、以及"这一帧该触发什么"。
真正的伤害施加在 scenes/battle.py 里做，因为那里才拿得到小怪列表。
"""

import json
import math
import os

import settings as S


# ======================================================================
#  技能展示信息（名字 / 说明 / 颜色）
#  从 data/skills.json 读，读不到就用下面这份兜底，保证界面不会开天窗。
# ======================================================================
_FALLBACK_INFO = {
    "dash":   {"name": "樱花冲锋", "color": (255, 150, 190), "desc": "移动时碾过身旁的小怪"},
    "spike":  {"name": "荆棘尾",   "color": (180, 120, 255), "desc": "小怪撞上尾椎也会受伤"},
    "shield": {"name": "星辉护盾", "color": (130, 210, 255), "desc": "周期性获得无敌护盾"},
    "thorn":  {"name": "蔓生荆棘", "color": (140, 220, 140), "desc": "走过的地面留下伤害荆棘"},
    "storm":  {"name": "樱花风暴", "color": (255, 200, 120), "desc": "周身掀起范围伤害风暴"},
}

_info_cache = None


def skill_info(sid):
    """取技能的展示信息。返回 dict，字段：name / color / desc / unlock_level"""
    global _info_cache
    if _info_cache is None:
        _info_cache = dict(_FALLBACK_INFO)
        try:
            path = os.path.join(S.DATA_DIR, "skills.json")
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw.get("skills", []):
                sid_key = item.get("id")
                if not sid_key:
                    continue
                COLORS = item.get("color") or [255, 255, 255]
                info = _info_cache.setdefault(sid_key, {})
                info["name"] = item.get("name", info.get("name", sid_key))
                info["color"] = tuple(COLORS[:3])
                info["desc"] = item.get("desc", info.get("desc", ""))
                info["detail"] = item.get("detail", "")
                info["unlock_level"] = item.get("unlock_level")
        except (IOError, json.JSONDecodeError, KeyError, TypeError):
            _info_cache = dict(_FALLBACK_INFO)
    info = dict(_info_cache.get(sid, {"name": sid, "color": (255, 255, 255), "desc": ""}))
    info.setdefault("name", sid)
    info.setdefault("color", (255, 255, 255))
    info.setdefault("desc", "")
    info["unlock_level"] = S.SKILL_UNLOCK.get(sid, info.get("unlock_level", 1))
    return info


def all_skill_ids():
    """所有技能 id，按解锁等级排序"""
    return sorted(S.SKILL_UNLOCK.keys(), key=lambda s: S.SKILL_UNLOCK[s])



class Thorn:
    """蔓生荆棘留在场上的一块地形"""

    def __init__(self, cell):
        self.cell = cell
        self.life = S.THORN_LIFE
        self.max_life = S.THORN_LIFE
        self.hit_cd = {}          # {小怪 id: 剩余冷却}，避免同一只怪被连续扣血

    def update(self, dt):
        self.life -= dt
        for k in list(self.hit_cd):
            self.hit_cd[k] -= dt
            if self.hit_cd[k] <= 0:
                del self.hit_cd[k]
        return self.life > 0

    def ready_for(self, mob_key):
        return self.hit_cd.get(mob_key, 0.0) <= 0.0

    def mark(self, mob_key):
        self.hit_cd[mob_key] = S.THORN_TICK

    @property
    def alpha_ratio(self):
        """用来做淡出。最后 1.5 秒开始变淡。"""
        if self.life > 1.5:
            return 1.0
        return max(0.0, self.life / 1.5)


class SkillEngine:
    """技能状态机。挂在战斗场景上，每帧 update 一次。"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.unlocked = []              # 已解锁技能 id，按解锁顺序
        self.thorns = []
        self.shield_timer = S.SHIELD_INTERVAL
        self.storm_timer = S.STORM_INTERVAL
        self.last_thorn_cell = None

        # ---- 樱花冲锋的充能 ----
        # 这是整个技能系统里最强的一个，必须有刹车。
        # 只有有充能时才能碾怪，碾死一只扣一格，扣完进冷却。
        self.dash_charges = S.DASH_CHARGES
        self.dash_recharge_t = 0.0
        self.dash_ready_flash = 0.0     # 刚回满时闪一下，给玩家反馈

        # ---- 荆棘尾的每怪冷却 + 全局节流 ----
        self.spike_cd = {}              # {小怪 uid: 剩余秒数}
        self.spike_global_cd = 0.0      # 全局闸门：多只怪同时撞也只结算一次

        # 一次性事件标志：本帧是否触发了某个需要外部响应的效果
        self.pending_shield = False
        self.pending_storm = False
        self.newly_unlocked = []        # 本帧新解锁的技能（给界面弹提示用）

    # ------------------------------------------------------------ 解锁
    def sync_unlock(self, level):
        """按当前等级同步解锁状态。返回本次新解锁的技能 id 列表。"""
        gained = []
        for sid, need in S.SKILL_UNLOCK.items():
            if level >= need and sid not in self.unlocked:
                self.unlocked.append(sid)
                gained.append(sid)
        # 按解锁等级排序，界面上显示顺序才稳定
        self.unlocked.sort(key=lambda s: S.SKILL_UNLOCK.get(s, 99))
        if gained:
            self.newly_unlocked.extend(gained)
        return gained

    def has(self, sid):
        return sid in self.unlocked

    @property
    def count(self):
        return len(self.unlocked)

    # ------------------------------------------------------------ 每帧
    def update(self, dt, snake, grid_cols, grid_rows):
        """推进计时器与地形。不直接造成伤害，只负责记"该触发了"。"""
        self.pending_shield = False
        self.pending_storm = False

        # ---- 樱花冲锋充能 ----
        if self.has("dash"):
            if self.dash_charges < S.DASH_CHARGES:
                self.dash_recharge_t += dt
                if self.dash_recharge_t >= S.DASH_RECHARGE:
                    self.dash_recharge_t -= S.DASH_RECHARGE
                    self.dash_charges += 1
                    if self.dash_charges >= S.DASH_CHARGES:
                        self.dash_recharge_t = 0.0
                        self.dash_ready_flash = 0.6
            if self.dash_ready_flash > 0:
                self.dash_ready_flash -= dt
        if self.spike_cd:
            for k in list(self.spike_cd):
                self.spike_cd[k] -= dt
                if self.spike_cd[k] <= 0:
                    del self.spike_cd[k]
        if self.spike_global_cd > 0:
            self.spike_global_cd -= dt

        # ---- 护盾 ----
        if self.has("shield"):
            self.shield_timer -= dt
            if self.shield_timer <= 0:
                self.shield_timer = S.SHIELD_INTERVAL
                self.pending_shield = True

        # ---- 樱花风暴 ----
        if self.has("storm"):
            self.storm_timer -= dt
            if self.storm_timer <= 0:
                self.storm_timer = S.STORM_INTERVAL
                self.pending_storm = True

        # ---- 蔓生荆棘：按间距铺在走过的格子上 ----
        if self.has("thorn"):
            cell = (round(snake.grid_pos[0]), round(snake.grid_pos[1]))
            if cell != self.last_thorn_cell and self._spaced_enough(cell):
                self.thorns.append(Thorn(cell))
                self.last_thorn_cell = cell
                if len(self.thorns) > S.THORN_MAX:
                    self.thorns = self.thorns[-S.THORN_MAX:]

        self.thorns = [t for t in self.thorns if t.update(dt)]

    def _spaced_enough(self, cell):
        """和已有荆棘别挤在一起，不然一条路上全是刺，视觉很脏"""
        for t in self.thorns:
            if abs(t.cell[0] - cell[0]) + abs(t.cell[1] - cell[1]) < S.THORN_SPACING:
                return False
        return True

    # ------------------------------------------------------------ 伤害查询
    def dash_ready(self):
        return self.dash_charges > 0

    def consume_dash(self):
        """用掉一格冲锋充能"""
        if self.dash_charges <= 0:
            return False
        self.dash_charges -= 1
        return True

    def spike_ready(self, mob_uid):
        """荆棘尾要同时过两道闸：全局闸（防多只怪一起刷）和每怪闸（防单只怪连吃）"""
        return (self.spike_global_cd <= 0.0
                and self.spike_cd.get(mob_uid, 0.0) <= 0.0)

    def mark_spike(self, mob_uid):
        self.spike_cd[mob_uid] = S.SPIKE_TICK
        self.spike_global_cd = S.SPIKE_GLOBAL_CD

    def thorn_damage_at(self, cell, mob_key):
        """
        某只怪站在某格上，是否吃到荆棘伤害。
        返回伤害值（0 表示没有）。
        """
        for t in self.thorns:
            if t.cell != cell:
                continue
            if t.ready_for(mob_key):
                t.mark(mob_key)
                return S.THORN_DMG
        return 0

    def dash_damage(self, level):
        return S.DASH_DMG + (level - 1) * S.DASH_BONUS_PER_LEVEL

    def storm_cells(self, snake_cell):
        """樱花风暴覆盖的格子集合"""
        sx, sy = snake_cell
        r = S.STORM_RADIUS
        return {(x, y) for x in range(sx - r, sx + r + 1)
                for y in range(sy - r, sy + r + 1)
                if 0 <= x < S.GRID_COLS and 0 <= y < S.GRID_ROWS}

    # ------------------------------------------------------------ 展示用
    def next_unlock(self, level):
        """下一个要解锁的技能，返回 (技能id, 还差几级) 或 None"""
        rest = [(sid, need) for sid, need in S.SKILL_UNLOCK.items() if need > level]
        if not rest:
            return None
        sid, need = min(rest, key=lambda kv: kv[1])
        return sid, need - level
