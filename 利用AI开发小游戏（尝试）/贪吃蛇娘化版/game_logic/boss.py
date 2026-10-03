# -*- coding: utf-8 -*-
"""
game_logic/boss.py —— Boss 与弹幕

设计要点：
  · 数据驱动：Boss 的血量 / 体型 / 阶段 / 攻击表全走 data/bosses.json，
    这里只提供行为实现，改数值不用碰代码。
  · 分辨率无关：所有速度 / 半径都按「格」存，用到像素时再乘 battle 传入的
    cell_px（= battle 的 self.CELL），窗口缩放也不会错位。
  · 伤害模型（关键）：玩家撞击 Boss 身体 -> Boss 掉血、玩家不掉血（见 battle
    的 _handle_boss_contact）；Boss 只通过弹幕 / 冲撞 / 震击 / 召唤的小怪伤人。

坐标系（自由移动版）：pos_cells 用「世界格」——battle 传入的 cell_px = self.CELL，
cols/rows = 世界像素 / CELL。因此 Boss.pos（= pos_cells * cell_px + cell_px/2）
直接就是世界像素，弹幕 pos 同理，绘制时由 battle 统一减去摄像机偏移 cam。
"""

import json
import math
import os
import random

import settings as S


# ======================================================================
#  弹幕
# ======================================================================
class Projectile:
    """一颗 Boss 弹幕。pos/vel 用网格相对像素，radius 用像素。"""

    def __init__(self, pos, vel, radius_px, damage, color, kind="bullet", life=None):
        self.pos = [float(pos[0]), float(pos[1])]
        self.vel = [float(vel[0]), float(vel[1])]
        self.radius = float(radius_px)
        self.damage = damage
        self.color = color
        self.kind = kind
        self.life = S.BOSS_BULLET_LIFE if life is None else float(life)
        self.alive = True
        self.t = random.random() * 6.28

    def update(self, dt, cols, rows, cell_px):
        """推进一帧。超时或飞出网格（留一格余量）即销毁。"""
        self.t += dt * 6.0
        self.life -= dt
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        if self.life <= 0:
            self.alive = False
            return
        max_x = cols * cell_px
        max_y = rows * cell_px
        if (self.pos[0] < -cell_px or self.pos[0] > max_x + cell_px
                or self.pos[1] < -cell_px or self.pos[1] > max_y + cell_px):
            self.alive = False


# ======================================================================
#  Boss
# ======================================================================
class Boss:
    """
    单个 Boss 的行为状态机。

    update() 不直接改 battle 的东西，而是返回一个「本帧事件」字典，由 battle
    去落地（生成弹幕 / 召唤小怪 / 结算伤害 / 播音效）。这样 Boss 逻辑可单测，
    也不依赖 battle 的内部结构。
    """

    def __init__(self, cfg, spawn_cell, cell_px_provider):
        self.cfg = cfg or {}
        self.id = self.cfg.get("id", "boss")
        self.name = self.cfg.get("name", "Boss")
        self.sprite = self.cfg.get("sprite") or ""
        tint = self.cfg.get("tint") or [230, 130, 190]
        self.tint = tuple(int(c) for c in list(tint)[:3])

        self.hp_max = max(1, int(self.cfg.get("hp", 1200)))
        self.hp = self.hp_max
        self.size_cells = max(1.0, float(self.cfg.get("size", 2.4)))
        self.speed = max(0.2, float(self.cfg.get("speed", 1.5)))   # 格/秒

        phases = self.cfg.get("phases") or [
            {"below": 1.0, "attacks": ["radial"], "interval": 2.4}
        ]
        # 按 below 升序：命中时取「第一个 ratio <= below」的阶段，即最紧的那档
        self.phases = sorted(phases, key=lambda p: float(p.get("below", 1.0)))

        self._cell_px_provider = cell_px_provider

        # 位置用「格」（浮点，Boss 中心），像素按需换算，天然分辨率无关
        self.pos_cells = [float(spawn_cell[0]), float(spawn_cell[1])]
        self.hit_flash = 0.0
        self.t = random.random() * 6.28
        self.alive = True
        self.intro = 1.1                 # 登场演出：期间不开火、缓慢浮现
        self.attack_timer = 1.4          # 登场后给点缓冲再开火
        self.spiral_angle = 0.0

        # 技能状态机
        self.charge = None               # {"phase","timer","dir"}
        self.slam = None                 # {"phase","timer","pos"}
        self.telegraphs = []             # 供 battle 绘制的预警（每帧重建）

        # 标记（花印）易伤：让连招对 Boss 也有存在感
        self.mark_t = 0.0
        self.mark_amp = 0.0
        self.mark_stacks = 0
        # 湿身（潮汐领域）易伤：期间受到的伤害放大 wet_amp
        self.wet_t = 0.0
        self.wet_amp = 0.0
        # 余烬（绯焰灼烧引爆闭环）：叠层 DOT，自然衰减可被引信烙印冻结，
        # DOT 由 battle._update_flare 结算（同 Mob）
        self.ember_stacks = 0
        self.ember_decay = S.FLARE_EMBER_DECAY
        self.ember_decay_t = 0.0
        self.ember_acc = 0.0
        self.ember_frozen = 0.0

    # ------------------------------------------------------------ 几何
    @property
    def cell_px(self):
        return self._cell_px_provider()

    @property
    def radius_cells(self):
        return self.size_cells / 2.0

    @property
    def radius_px(self):
        return self.radius_cells * self.cell_px

    @property
    def cell(self):
        return (int(round(self.pos_cells[0])), int(round(self.pos_cells[1])))

    @property
    def pos(self):
        """网格相对像素（Boss 中心）"""
        cp = self.cell_px
        return (self.pos_cells[0] * cp + cp / 2, self.pos_cells[1] * cp + cp / 2)

    @property
    def draw_pos(self):
        px, py = self.pos
        return (px, py + math.sin(self.t) * self.cell_px * 0.05)

    @property
    def charge_active(self):
        """冲刺进行中（此刻撞上玩家要造成伤害）"""
        return self.charge is not None and self.charge["phase"] == "dash"

    # ------------------------------------------------------------ 血量 / 阶段
    def hp_ratio(self):
        return max(0.0, self.hp / self.hp_max) if self.hp_max else 0.0

    def current_phase(self):
        r = self.hp_ratio()
        for ph in self.phases:
            if r <= float(ph.get("below", 1.0)):
                return ph
        return self.phases[-1]

    def take_damage(self, amount):
        """掉血。返回是否被这一击打死。"""
        if not self.alive:
            return True
        # 被标记（花印）时受到的伤害放大，连招核心
        if self.mark_t > 0:
            amount = amount * (1.0 + self.mark_amp)
        # 湿身（潮汐领域）时受到的伤害再放大
        if self.wet_t > 0:
            amount = amount * (1.0 + self.wet_amp)
        self.hp -= amount
        self.hit_flash = 0.16
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def apply_mark(self, amp, time, max_stacks=1):
        """被标记：叠加层数（每层提升易伤 amp），刷新持续时间。"""
        max_stacks = max(1, int(max_stacks))
        self.mark_stacks = min(max_stacks, self.mark_stacks + 1)
        self.mark_amp = amp * self.mark_stacks
        self.mark_t = max(self.mark_t, time)

    def clear_mark(self):
        """引爆后清空标记状态。"""
        self.mark_t = 0.0
        self.mark_amp = 0.0
        self.mark_stacks = 0

    def apply_wet(self, amp, time):
        """被湿身（潮汐领域）：期间受到的伤害放大 amp，刷新持续时间。"""
        if self.wet_t <= 0 or amp > self.wet_amp:
            self.wet_amp = amp
        self.wet_t = max(self.wet_t, time)

    def add_ember(self, stacks=1):
        """叠余烬层（绯焰专属）：封顶 FLARE_EMBER_MAX，新叠层重置衰减计时。"""
        self.ember_stacks = min(S.FLARE_EMBER_MAX, self.ember_stacks + stacks)
        self.ember_decay_t = 0.0
        return self.ember_stacks >= S.FLARE_EMBER_MAX

    def freeze_ember(self, time):
        """引信烙印：冻结余烬自然衰减 time 秒（等自动引爆）。"""
        self.ember_frozen = max(self.ember_frozen, time)

    def consume_ember(self):
        """引爆结算：取走当前层数并清空余烬状态，返回被引爆的层数。"""
        n = self.ember_stacks
        self.ember_stacks = 0
        self.ember_decay_t = 0.0
        self.ember_acc = 0.0
        self.ember_frozen = 0.0
        return n

    # ------------------------------------------------------------ 每帧
    def update(self, dt, snake_cell, ctx):
        """
        推进 Boss。返回事件字典：
            {"bullets": [Projectile...], "summon": int,
             "effects": [ {...} ], "sfx": [name...] }
        """
        cols = ctx.get("cols", S.GRID_COLS)
        rows = ctx.get("rows", S.GRID_ROWS)
        cell_px = ctx.get("cell_px", self.cell_px)
        events = {"bullets": [], "summon": 0, "effects": [], "sfx": []}

        self.t += dt * 2.0
        if self.hit_flash > 0:
            self.hit_flash -= dt
        # 标记（易伤）状态到期自动清除
        if self.mark_t > 0:
            self.mark_t = max(0.0, self.mark_t - dt)
            if self.mark_t <= 0:
                self.mark_amp = 0.0
                self.mark_stacks = 0
        # 湿身（易伤）状态到期自动清除
        if self.wet_t > 0:
            self.wet_t = max(0.0, self.wet_t - dt)
            if self.wet_t <= 0:
                self.wet_amp = 0.0

        # 余烬：非冻结期间按周期自耗一层，层数归零后清空（同 Mob）
        if self.ember_frozen > 0:
            self.ember_frozen = max(0.0, self.ember_frozen - dt)
        elif self.ember_stacks > 0:
            self.ember_decay_t += dt
            while self.ember_decay_t >= self.ember_decay and self.ember_stacks > 0:
                self.ember_decay_t -= self.ember_decay
                self.ember_stacks -= 1
            if self.ember_stacks <= 0:
                self.ember_decay_t = 0.0
                self.ember_acc = 0.0

        if self.intro > 0:
            self.intro -= dt
            self.telegraphs = []
            return events

        # 冲撞 / 震击期间不追击（位移交给技能本身）
        if self.charge is None and self.slam is None:
            self._chase(dt, snake_cell, cols, rows)

        if self.charge is not None:
            self._update_charge(dt, cols, rows, cell_px, events)
        elif self.slam is not None:
            self._update_slam(dt, cell_px, events)
        else:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                ph = self.current_phase()
                self.attack_timer = float(ph.get("interval", 2.4))
                attacks = ph.get("attacks") or ["radial"]
                self._do_attack(random.choice(attacks), snake_cell,
                                cols, rows, cell_px, events)

        self._rebuild_telegraphs(cell_px)
        return events

    # ------------------------------------------------------------ 移动
    def _chase(self, dt, snake_cell, cols, rows):
        dx = snake_cell[0] - self.pos_cells[0]
        dy = snake_cell[1] - self.pos_cells[1]
        d = math.hypot(dx, dy)
        if d < 0.001:
            return
        step = self.speed * dt
        nx = self.pos_cells[0] + dx / d * step
        ny = self.pos_cells[1] + dy / d * step
        margin = max(0.6, self.radius_cells * 0.7)
        lo_x, hi_x = margin, max(margin, cols - 1 - margin)
        lo_y, hi_y = margin, max(margin, rows - 1 - margin)
        self.pos_cells[0] = min(max(nx, lo_x), hi_x)
        self.pos_cells[1] = min(max(ny, lo_y), hi_y)

    # ------------------------------------------------------------ 攻击分发
    def _do_attack(self, kind, snake_cell, cols, rows, cell_px, events):
        if kind == "radial":
            self._atk_radial(cell_px, events)
        elif kind == "aimed":
            self._atk_aimed(snake_cell, cell_px, events)
        elif kind == "spiral":
            self._atk_spiral(cell_px, events)
        elif kind == "wall":
            self._atk_wall(cols, rows, cell_px, events)
        elif kind == "summon":
            events["summon"] += S.BOSS_SUMMON_COUNT
            events["sfx"].append("boss_shoot")
        elif kind == "charge":
            self._start_charge(snake_cell)
        elif kind == "slam":
            self._start_slam(cell_px)
        else:
            self._atk_radial(cell_px, events)

    # ------------------------------------------------------------ 弹幕工具
    def _bullet_color(self):
        r, g, b = self.tint
        return (min(255, r + 45), min(255, g + 45), min(255, b + 45))

    def _make_bullet(self, angle, cell_px, color=None):
        sp = S.BOSS_BULLET_SPEED_CELLS * cell_px
        px, py = self.pos
        return Projectile(
            pos=(px, py),
            vel=(math.cos(angle) * sp, math.sin(angle) * sp),
            radius_px=S.BOSS_BULLET_RADIUS_CELLS * cell_px,
            damage=S.BOSS_BULLET_DAMAGE,
            color=color or self._bullet_color(),
            kind="bullet",
        )

    def _atk_radial(self, cell_px, events):
        n = max(1, S.RADIAL_COUNT)
        off = random.random() * math.tau
        for i in range(n):
            events["bullets"].append(self._make_bullet(off + i * math.tau / n, cell_px))
        events["sfx"].append("boss_shoot")

    def _atk_aimed(self, snake_cell, cell_px, events):
        px, py = self.pos
        tx = snake_cell[0] * cell_px + cell_px / 2
        ty = snake_cell[1] * cell_px + cell_px / 2
        base = math.atan2(ty - py, tx - px)
        n = max(1, S.AIMED_COUNT)
        spread = S.AIMED_SPREAD
        for i in range(n):
            frac = 0.0 if n == 1 else i / (n - 1)
            events["bullets"].append(
                self._make_bullet(base - spread / 2 + spread * frac, cell_px))
        events["sfx"].append("boss_shoot")

    def _atk_spiral(self, cell_px, events):
        arms = max(1, S.SPIRAL_ARMS)
        self.spiral_angle = (self.spiral_angle + math.radians(S.SPIRAL_RATE)) % math.tau
        for k in range(arms):
            events["bullets"].append(
                self._make_bullet(self.spiral_angle + k * math.tau / arms, cell_px))
        events["sfx"].append("boss_shoot")

    def _atk_wall(self, cols, rows, cell_px, events):
        """从随机一侧推来一排弹墙，留几个缺口供玩家穿行。"""
        n = max(2, S.WALL_COUNT)
        gaps = max(1, min(S.WALL_GAP, n - 1))
        side = random.randint(0, 3)          # 0左 1右 2上 3下
        gap_idx = set(random.sample(range(n), gaps))
        sp = S.BOSS_BULLET_SPEED_CELLS * cell_px
        horizontal = side in (0, 1)
        for i in range(n):
            if i in gap_idx:
                continue
            if horizontal:
                pos = ((0.0 if side == 0 else cols) * cell_px,
                       (i + 0.5) / n * rows * cell_px)
                vel = ((sp if side == 0 else -sp), 0.0)
            else:
                pos = ((i + 0.5) / n * cols * cell_px,
                       (0.0 if side == 2 else rows) * cell_px)
                vel = (0.0, (sp if side == 2 else -sp))
            events["bullets"].append(Projectile(
                pos=pos, vel=vel,
                radius_px=S.BOSS_BULLET_RADIUS_CELLS * cell_px,
                damage=S.BOSS_BULLET_DAMAGE,
                color=self._bullet_color(), kind="wall"))
        events["sfx"].append("boss_shoot")

    # ------------------------------------------------------------ 冲撞
    def _start_charge(self, snake_cell):
        dx = snake_cell[0] - self.pos_cells[0]
        dy = snake_cell[1] - self.pos_cells[1]
        d = math.hypot(dx, dy) or 1.0
        self.charge = {
            "phase": "telegraph",
            "timer": S.BOSS_CHARGE_TELEGRAPH,
            "dir": (dx / d, dy / d),
        }

    def _update_charge(self, dt, cols, rows, cell_px, events):
        c = self.charge
        c["timer"] -= dt
        if c["phase"] == "telegraph":
            if c["timer"] <= 0:
                c["phase"] = "dash"
                c["timer"] = 0.55
                events["sfx"].append("boss_charge")
            return
        # dash：高速直线冲刺
        dx, dy = c["dir"]
        self.pos_cells[0] += dx * S.BOSS_CHARGE_SPEED_CELLS * dt
        self.pos_cells[1] += dy * S.BOSS_CHARGE_SPEED_CELLS * dt
        margin = 0.5
        hit_wall = not (margin <= self.pos_cells[0] <= cols - 1 - margin
                        and margin <= self.pos_cells[1] <= rows - 1 - margin)
        if hit_wall:
            self.pos_cells[0] = min(max(self.pos_cells[0], margin), cols - 1 - margin)
            self.pos_cells[1] = min(max(self.pos_cells[1], margin), rows - 1 - margin)
        if c["timer"] <= 0 or hit_wall:
            self.charge = None

    # ------------------------------------------------------------ 震击
    def _start_slam(self, cell_px):
        self.slam = {
            "phase": "telegraph",
            "timer": S.BOSS_SLAM_TELEGRAPH,
            "pos": self.pos,                 # 预警圈固定在此，Boss 期间不移动
        }

    def _update_slam(self, dt, cell_px, events):
        s = self.slam
        s["timer"] -= dt
        if s["timer"] <= 0:
            events["effects"].append({
                "type": "slam_burst",
                "pos": s["pos"],
                "radius_px": S.BOSS_SLAM_RADIUS_CELLS * cell_px,
            })
            events["sfx"].append("boss_slam")
            self.slam = None

    # ------------------------------------------------------------ 预警重建
    def _rebuild_telegraphs(self, cell_px):
        tg = []
        if self.charge is not None and self.charge["phase"] == "telegraph":
            px, py = self.pos
            dx, dy = self.charge["dir"]
            length = max(cell_px, 1) * 60
            total = S.BOSS_CHARGE_TELEGRAPH or 1.0
            tg.append({
                "type": "charge",
                "from": (px, py),
                "to": (px + dx * length, py + dy * length),
                "width_px": self.radius_px * 2,
                "progress": 1.0 - max(0.0, self.charge["timer"]) / total,
            })
        if self.slam is not None:
            total = S.BOSS_SLAM_TELEGRAPH or 1.0
            tg.append({
                "type": "slam",
                "pos": self.slam["pos"],
                "radius_px": S.BOSS_SLAM_RADIUS_CELLS * cell_px,
                "progress": 1.0 - max(0.0, self.slam["timer"]) / total,
            })
        self.telegraphs = tg


# ======================================================================
#  配置载入
# ======================================================================
def load_boss_cfg(scene_id):
    """按场景 id 从 data/bosses.json 取 Boss 配置，取不到（或总开关关）返回 None。
    兼容 json 为列表或 {"bosses": [...]} 两种写法，任何异常都不崩。"""
    if not S.BOSS_ENABLED:
        return None
    try:
        path = os.path.join(S.DATA_DIR, "bosses.json")
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        items = raw.get("bosses", raw) if isinstance(raw, dict) else raw
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and it.get("scene") == scene_id:
                    return it
    except (IOError, json.JSONDecodeError, AttributeError, TypeError):
        pass
    return None


def boss_trigger_met(cfg, elapsed, level, kills):
    """判断 Boss 登场条件是否满足。mode: time / level / kills，默认 time。"""
    trig = (cfg or {}).get("trigger") or {"mode": "time", "value": 60}
    mode = trig.get("mode", "time")
    value = float(trig.get("value", 60))
    if mode == "level":
        return level >= value
    if mode == "kills":
        return kills >= value
    return elapsed >= value
