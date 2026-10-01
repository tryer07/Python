# -*- coding: utf-8 -*-
"""
game_logic/skills.py —— 主动技能系统（自由移动版）

设计变更（相较旧网格版）：
  · 技能不再是「升级自动解锁的被动」，而是**主动释放**：按键 1-6。
  · 技能通过「升级选卡」获得；按获得顺序绑定键位 1/2/3/4/5/6。
  · 每个技能有独立冷却与等级（1..SKILL_MAX_LEVEL），升级选到同名技能卡即强化。
  · SkillEngine 只管：解锁/等级/冷却计时、以及持续型效果的状态（荆棘地形、
    荆棘尾光环）。瞬发效果通过 cast() 返回一个「事件字典」，由 battle 落地
    （施加伤害 / 位移 / 生成弹丸），这样技能逻辑可单测、不依赖 battle 内部。

坐标系：荆棘地形 pos 用世界像素，与实体一致。
"""

import json
import math
import os
import random

import settings as S


# ======================================================================
#  技能展示信息（名字 / 说明 / 颜色 / 键位）
# ======================================================================
_FALLBACK_INFO = {
    "dash":   {"name": "樱花冲锋", "color": (255, 150, 190), "desc": "向前突进碾过敌人"},
    "spike":  {"name": "荆棘尾",   "color": (180, 120, 255), "desc": "周身荆棘光环持续刺伤"},
    "shield": {"name": "星辉护盾", "color": (130, 210, 255), "desc": "获得一段无敌护盾"},
    "thorn":  {"name": "蔓生荆棘", "color": (140, 220, 140), "desc": "地面催生伤害荆棘"},
    "storm":  {"name": "樱花风暴", "color": (255, 200, 120), "desc": "周身范围爆发伤害"},
    "bloom":  {"name": "月华绽放", "color": (200, 170, 255), "desc": "绽射穿透弹贯穿群敌"},
}

_info_cache = None


def skill_info(sid):
    """取技能的展示信息。返回 dict：name / color / desc / detail / key"""
    global _info_cache
    if _info_cache is None:
        _info_cache = {k: dict(v) for k, v in _FALLBACK_INFO.items()}
        try:
            path = os.path.join(S.DATA_DIR, "skills.json")
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw.get("skills", []):
                sid_key = item.get("id")
                if not sid_key:
                    continue
                colors = item.get("color") or [255, 255, 255]
                info = _info_cache.setdefault(sid_key, {})
                info["name"] = item.get("name", info.get("name", sid_key))
                info["color"] = tuple(colors[:3])
                info["desc"] = item.get("desc", info.get("desc", ""))
                info["detail"] = item.get("detail", "")
                info["key"] = item.get("key")
        except (IOError, json.JSONDecodeError, KeyError, TypeError):
            _info_cache = {k: dict(v) for k, v in _FALLBACK_INFO.items()}
    info = dict(_info_cache.get(sid, {"name": sid, "color": (255, 255, 255), "desc": ""}))
    info.setdefault("name", sid)
    info.setdefault("color", (255, 255, 255))
    info.setdefault("desc", "")
    return info


def all_skill_ids():
    """全部主动技能 id，按键位顺序（1-6）"""
    return list(S.SKILL_ORDER)


def skill_key(sid):
    """技能默认展示键位（1-6）。实际绑定以引擎获得顺序为准。"""
    try:
        return S.SKILL_ORDER.index(sid) + 1
    except ValueError:
        return skill_info(sid).get("key") or 0


# 各技能基础冷却（秒），集中在此便于查
_BASE_CD = {
    "dash": lambda: S.DASH_CD,
    "spike": lambda: S.SPIKE_CD,
    "shield": lambda: S.SHIELD_CD,
    "thorn": lambda: S.THORN_CD,
    "storm": lambda: S.STORM_CD,
    "bloom": lambda: S.BLOOM_CD,
}


class Thorn:
    """蔓生荆棘留在场上的一块地形（世界像素坐标）"""

    def __init__(self, pos, radius, dmg):
        self.pos = (float(pos[0]), float(pos[1]))
        self.radius = float(radius)
        self.dmg = dmg
        self.life = S.THORN_LIFE
        self.max_life = S.THORN_LIFE
        self.hit_cd = {}          # {key: 剩余冷却}

    def update(self, dt):
        self.life -= dt
        for k in list(self.hit_cd):
            self.hit_cd[k] -= dt
            if self.hit_cd[k] <= 0:
                del self.hit_cd[k]
        return self.life > 0

    def ready_for(self, key):
        return self.hit_cd.get(key, 0.0) <= 0.0

    def mark(self, key):
        self.hit_cd[key] = S.THORN_TICK

    def contains(self, pos, extra=0.0):
        return math.hypot(pos[0] - self.pos[0], pos[1] - self.pos[1]) <= self.radius + extra

    @property
    def alpha_ratio(self):
        if self.life > 1.5:
            return 1.0
        return max(0.0, self.life / 1.5)


class SkillEngine:
    """主动技能状态机。挂在战斗场景上，每帧 update 一次。"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.order = []                 # 已获得技能 id，按获得顺序（index=键位-1）
        self.levels = {}                # {sid: 1..SKILL_MAX_LEVEL}
        self.cds = {}                   # {sid: 剩余冷却秒}
        self.thorns = []                # [Thorn]
        # 荆棘尾光环（持续型）
        self.spike_left = 0.0           # 光环剩余秒数
        self.spike_radius = 0.0
        self.spike_dmg = 0
        self.spike_cd = {}              # {mob_uid: 剩余结算冷却}
        self.pending_shield = 0.0       # 本帧要给的无敌时长（battle 消费）
        self.newly_unlocked = []

    # ------------------------------------------------------------ 解锁 / 查询
    def unlock(self, sid):
        """获得技能（首次）或升级（已拥有）。返回本次操作后的键位（1-based）；
        已达满级返回其键位但不升级。"""
        if sid not in self.order:
            if len(self.order) >= 6:
                return None
            self.order.append(sid)
            self.levels[sid] = 1
            self.cds[sid] = 0.0
            self.newly_unlocked.append(sid)
        else:
            if self.levels.get(sid, 1) < S.SKILL_MAX_LEVEL:
                self.levels[sid] = self.levels.get(sid, 1) + 1
        return self.order.index(sid) + 1

    def has(self, sid):
        return sid in self.order

    def level(self, sid):
        return self.levels.get(sid, 0)

    @property
    def count(self):
        return len(self.order)

    def key_of(self, sid):
        """技能当前绑定的键位（1-based），未获得返回 0"""
        return self.order.index(sid) + 1 if sid in self.order else 0

    def sid_at_key(self, key):
        """键位（1-based）对应的技能 id，没有返回 None"""
        idx = key - 1
        if 0 <= idx < len(self.order):
            return self.order[idx]
        return None

    def cooldown_max(self, sid, cdr=0.0):
        """技能冷却总时长（含冷却缩减）"""
        base = _BASE_CD.get(sid, lambda: 6.0)()
        return max(0.3, base * (1.0 - min(0.75, cdr)))

    def cooldown_left(self, sid):
        return self.cds.get(sid, 0.0)

    def cd_ratio(self, sid, cdr=0.0):
        """冷却进度 0(刚放)..1(就绪)，供 HUD 转圈"""
        total = self.cooldown_max(sid, cdr)
        if total <= 0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - self.cds.get(sid, 0.0) / total))

    def ready(self, sid, cdr=0.0):
        return self.has(sid) and self.cds.get(sid, 0.0) <= 0.0

    # ------------------------------------------------------------ 每帧
    def update(self, dt):
        """推进冷却、荆棘地形、荆棘尾光环。不直接造成伤害。"""
        for sid in list(self.cds):
            if self.cds[sid] > 0:
                self.cds[sid] = max(0.0, self.cds[sid] - dt)
        if self.spike_left > 0:
            self.spike_left = max(0.0, self.spike_left - dt)
            for k in list(self.spike_cd):
                self.spike_cd[k] -= dt
                if self.spike_cd[k] <= 0:
                    del self.spike_cd[k]
        self.thorns = [t for t in self.thorns if t.update(dt)]

    # ------------------------------------------------------------ 释放
    def cast(self, sid, pos, cdr=0.0):
        """
        尝试释放技能。成功返回事件字典并进入冷却，失败（未拥有/冷却中）返回 None。
        pos = 玩家当前世界像素位置（荆棘尾/蔓生荆棘布点用）。
        """
        if not self.ready(sid, cdr):
            return None
        lv = self.level(sid)
        self.cds[sid] = self.cooldown_max(sid, cdr)

        if sid == "dash":
            return {"type": "dash",
                    "dist": S.DASH_DIST, "time": S.DASH_TIME,
                    "dmg": S.DASH_DMG + S.DASH_DMG_PER_LV * (lv - 1)}
        if sid == "spike":
            self.spike_left = S.SPIKE_DURATION
            self.spike_radius = S.SPIKE_RADIUS * (1.0 + 0.12 * (lv - 1))
            self.spike_dmg = S.SPIKE_DMG + S.SPIKE_DMG_PER_LV * (lv - 1)
            self.spike_cd.clear()
            return {"type": "spike", "radius": self.spike_radius,
                    "duration": S.SPIKE_DURATION, "dmg": self.spike_dmg}
        if sid == "shield":
            t = S.SHIELD_TIME + S.SHIELD_TIME_PER_LV * (lv - 1)
            self.pending_shield = t
            return {"type": "shield", "time": t}
        if sid == "thorn":
            dmg = S.THORN_DMG + S.THORN_DMG_PER_LV * (lv - 1)
            radius = S.THORN_RADIUS
            n = S.THORN_CHARGES + (lv - 1)
            placed = []
            for i in range(n):
                ang = random.random() * math.tau if i == 0 else (i / n) * math.tau
                dist = 0 if i == 0 else radius * 1.1
                p = (pos[0] + math.cos(ang) * dist, pos[1] + math.sin(ang) * dist)
                self.thorns.append(Thorn(p, radius, dmg))
                placed.append(p)
            if len(self.thorns) > S.THORN_MAX:
                self.thorns = self.thorns[-S.THORN_MAX:]
            return {"type": "thorn", "positions": placed, "radius": radius, "dmg": dmg}
        if sid == "storm":
            return {"type": "storm",
                    "radius": S.STORM_RADIUS * (1.0 + 0.15 * (lv - 1)),
                    "dmg": S.STORM_DMG + S.STORM_DMG_PER_LV * (lv - 1)}
        if sid == "bloom":
            return {"type": "bloom",
                    "count": S.BLOOM_COUNT + 2 * (lv - 1),
                    "dmg": S.BLOOM_DMG + S.BLOOM_DMG_PER_LV * (lv - 1),
                    "speed": S.BLOOM_BULLET_SPEED, "life": S.BLOOM_BULLET_LIFE,
                    "pierce": S.BLOOM_PIERCE + (lv - 1)}
        self.cds[sid] = 0.0
        return None

    # ------------------------------------------------------------ 持续效果查询
    @property
    def spike_active(self):
        return self.spike_left > 0

    def spike_ready(self, key):
        return self.spike_cd.get(key, 0.0) <= 0.0

    def mark_spike(self, key):
        self.spike_cd[key] = S.SPIKE_TICK

    def thorn_damage_at(self, pos, key, extra=0.0):
        """某个单位站在 pos，是否踩到荆棘。返回伤害值（0 表示没有）。"""
        for t in self.thorns:
            if t.contains(pos, extra) and t.ready_for(key):
                t.mark(key)
                return t.dmg
        return 0
