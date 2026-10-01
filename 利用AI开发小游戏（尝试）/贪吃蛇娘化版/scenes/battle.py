# -*- coding: utf-8 -*-
"""
scenes/battle.py —— 战斗场景

一局的完整过程都在这里：
    蛇娘移动 → 捡掉落物 → 升级 / 回血 / 攒星尘 → 小怪越来越多越来越硬 → 撞怪扣血 → 结算

按你的设定：
    · 蛇身长度固定，吃东西不变长
    · 成长走「等级 → 伤害提升 → 技能解锁」
    · 难度靠小怪变强（血厚）+ 变多（刷得快）+ 时间压力兜底

导入约定（重要）：本项目 settings 的常量有两种访问方式，
    · 顶部 `from settings import XXX` 拿的是「设计基准值」
    · `import settings as S` 下的 `S.XXX` 拿的是「同一份值」
    两者数值相同，但**网格尺寸必须用实例上的 self.CELL / self.GRID_PX_W / self.GRID_PX_H**
    （enter() 里按当前缩放算好的），不要再用模块级的 CELL_SIZE 裸名，
    否则窗口一缩放，网格和内容就会错位。
"""

import json
import math
import os
import random

import pygame

import settings as S
from core.scene import Scene
from game_logic.entities import Drop, Mob, SnakeGirl
from game_logic.skills import SkillEngine, all_skill_ids, skill_info
from settings import (
    COLOR_ACCENT, COLOR_ACCENT_DARK, COLOR_BG, COLOR_BG_LIGHT, COLOR_DANGER,
    COLOR_EXP, COLOR_GOLD, COLOR_GOOD, COLOR_HP, COLOR_TEXT, COLOR_TEXT_DIM,
    FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_SUBTITLE, FONT_SIZE_TITLE,
    GRID_COLS, GRID_COLOR, GRID_ROWS, HP_MAX,
)


class BattleScene(Scene):
    """战斗场景"""

    def enter(self):
        self.assets = self.game.assets

        # 字体全部按当前缩放取（self.s 是 Scene 基类给的缩放换算）
        self.f_tiny = self.assets.get_font(self.s(FONT_SIZE_SMALL - 2))
        self.f_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))
        self.f_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.f_sub = self.assets.get_font(self.s(FONT_SIZE_SUBTITLE))
        self.f_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)

        # ---- 网格几何 ----
        # 【重要】必须走 S.XXX 实时取值，不能用 from settings import 抓来的常量。
        # 原因：settings.py 会在运行时改写自己的 CELL_SIZE / RENDER_WIDTH
        # （按屏幕尺寸算出实际值）。from import 抓的是**导入那一刻**的快照，
        # 后续 settings 改了它不会跟着变 —— 谁先 import 谁就拿到旧值，
        # 这类"幽灵 bug"极难排查。所有几何量一律现取现用。
        self.CELL = S.CELL_SIZE
        self.GRID_PX_W = S.GRID_COLS * self.CELL
        self.GRID_PX_H = S.GRID_ROWS * self.CELL
        self.offset_x = (self.W - self.GRID_PX_W) // 2
        self.offset_y = (self.H - self.GRID_PX_H) // 2

        # ---- 左右 HUD 面板宽度 ----
        # 不要把这里的数字拍脑袋写死 —— 用"最长的一行内容实际有多宽"来定。
        # 左面板一行技能 = 图标 + 技能名 + 状态（Lv.x 或 ◆◆◆），三者都要放得下。
        pad = self.s(10)
        icon_w = self.s(30)
        name_w = max(self.f_tiny.size(skill_info(s)["name"])[0] for s in all_skill_ids())
        state_w = self.f_tiny.size("Lv.10")[0]
        skill_row_w = icon_w + name_w + state_w + self.s(24)
        # 右面板一行 = 大号数字，留足余量
        num_w = self.f_sub.size("99999")[0] + pad * 2
        content_min = max(skill_row_w, num_w)

        side_gap = (self.W - self.GRID_PX_W) // 2
        side = max(content_min, side_gap - self.s(8))
        # 上限：两块面板最多各占窗口 19%，给网格留足空间
        side = min(side, int(self.W * 0.19))
        self.panel_w = max(self.s(96), int(side))
        self.left_panel_x = self.s(4)
        self.right_panel_x = self.W - self.panel_w - self.s(4)
        self.panel_h = self.GRID_PX_H

        # 网格区居中：如果面板太宽挤到了网格，把网格重新居中到剩余空间
        free_left = self.left_panel_x + self.panel_w + self.s(6)
        free_right = self.right_panel_x - self.s(6)
        self.grid_x = max(free_left, self.offset_x)
        self.grid_y = self.offset_y

        # ---- 布局自检 ----
        # 文字被裁、面板跑到屏幕外这类问题，肉眼不一定第一眼发现，
        # 但用代码判一下就是确定的。窗口太小时自动把面板压到可接受范围。
        self._fit_layout(free_left, free_right)

        self.reset()

    def _fit_layout(self, free_left, free_right):
        """
        保证「左面板 | 网格 | 右面板」三段互不重叠、且都在屏幕内。

        窗口小的时候真正会出问题的是网格：GRID_COLS * CELL_SIZE 是死的，
        窗口一缩，网格比可用空间还宽，就会压到面板上。这时把 CELL 缩小，
        让网格重新塞得进可用空间 —— 而不是让面板被挤没、文字被裁掉。
        """
        avail = self.W - self.left_panel_x - self.panel_w - self.s(8) \
            - self.panel_w - self.s(8)
        if avail <= 0:
            return
        if self.GRID_PX_W > avail:
            # 按可用空间反推格子尺寸（取整，避免出现半像素）
            new_cell = max(8, int(avail / S.GRID_COLS))
            self.CELL = new_cell
            self.GRID_PX_W = S.GRID_COLS * self.CELL
            self.GRID_PX_H = S.GRID_ROWS * self.CELL
        self.grid_x = self.left_panel_x + self.panel_w + self.s(8) \
            + max(0, (avail - self.GRID_PX_W) // 2)
        self.grid_y = max(self.s(8), (self.H - self.GRID_PX_H) // 2)
        self.panel_h = min(self.GRID_PX_H, self.H - self.grid_y - self.s(8))

    def exit(self):
        pass

    # ---------------------------------------------------------------- 重置
    def reset(self):
        # 角色 / 场景从存档里取，这样"角色选择""场景选择"才真的生效
        char_id = self.game.save_manager.get("selected_character", "sakura")
        self.scene_id = self.game.save_manager.get("selected_scene", "campus_garden")
        self.snake_name, self.snake_rarity = self._char_label(char_id)

        self.snake = SnakeGirl(char_id, start_cell=(6, GRID_ROWS // 2), direction=(1, 0))
        self.snake.facing_update()

        # 技能引擎：挂在蛇的升级回调上，升级即解锁
        self.skills = SkillEngine()
        self.skill_toast = []                   # 解锁提示，[{sid, life, ...}]
        self.skills.sync_unlock(self.snake.level)
        self.skills.newly_unlocked.clear()
        self.snake.on_level_up_cb = self._on_snake_level_up

        self.drops = []
        self.mobs = []
        self.particles = []
        self.floaters = []

        self.elapsed = 0.0
        self.score = 0
        self.stardust = 0
        self.kills = 0
        self.mob_spawn_timer = 1.4
        self.shake = 0.0
        self.flash = 0.0
        self.finished = False

        for _ in range(6):
            self._spawn_drop()

    def _on_snake_level_up(self, level, gained):
        """蛇升级了 → 同步技能解锁，并弹提示"""
        newly = self.skills.sync_unlock(level)
        for sid in newly:
            self.skill_toast.append({"sid": sid, "life": 3.0})
            self.flash = max(self.flash, 0.4)

    # -------------------------------------------------------- 技能系统辅助
    def _char_label(self, char_id):
        """
        从 data/characters.json 取角色的显示名和稀有度。
        取不到就用 id 兜底，绝不因为配置缺字段就崩掉。
        """
        try:
            path = os.path.join(S.DATA_DIR, "characters.json")
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            items = raw.get("characters", raw) if isinstance(raw, dict) else raw
            for c in items:
                if c.get("id") == char_id:
                    name = c.get("name", char_id)
                    rarity = c.get("rarity", "")
                    return name, f"Sakura · {rarity}" if rarity else "Sakura"
        except (IOError, json.JSONDecodeError, AttributeError, TypeError):
            pass
        return char_id, "Sakura"

    @property
    def skilled(self):
        """是否已经解锁到会影响难度的程度（≥2 个技能）"""
        return self.skills.count >= 2

    # ------------------------------------------------------------ 生成逻辑
    def _free_cells(self):
        used = set(self.snake.cells)
        for m in self.mobs:
            used.add((round(m.cell[0]), round(m.cell[1])))
        return [(x, y) for x in range(GRID_COLS) for y in range(GRID_ROWS)
                if (x, y) not in used]

    def _spawn_drop(self, kind=None):
        cells = self._free_cells()
        if not cells:
            return
        from settings import DROP_CRYSTAL, DROP_EXP, DROP_HEART, DROP_STARDUST
        cell = random.choice(cells)
        if kind is None:
            r = random.random()
            if r < DROP_EXP:
                kind = "exp"
            elif r < DROP_EXP + DROP_CRYSTAL:
                kind = "crystal"
            elif r < DROP_EXP + DROP_CRYSTAL + DROP_STARDUST:
                kind = "stardust"
            else:
                kind = "heart"
        self.drops.append(Drop(kind, cell))

    def _time_pressure(self):
        """
        时间压力系数。

        这是整套难度里唯一"无条件"上升的东西，也是兜底机制。
        别的难度通道（怪变多、怪变硬）都有个致命弱点：技能越强，
        玩家清怪越快，局面反而更安全。只有时间压力不管你怎么打都在涨。
        没有它，只要清怪速度超过刷怪速度，局面就会永久稳定，怎么削技能都没用。
        """
        if self.elapsed <= S.TIME_PRESSURE_START:
            return 1.0
        t = (self.elapsed - S.TIME_PRESSURE_START) * S.TIME_PRESSURE_RAMP
        return min(S.TIME_PRESSURE_MAX, 1.0 + t)

    def _spawn_mob(self):
        """刷小怪——难度成长的所有通道都在这里"""
        # 玩家点了技能之后，怪也得跟上，否则难度直接崩
        growth = S.MOB_HP_GROWTH_SKILLED if self.skilled else S.MOB_HP_GROWTH
        tp = self._time_pressure()
        hp_mult = min(S.MOB_HP_MAX_MULT,
                      1.0 + growth * (self.elapsed / 30.0)) * tp
        speed_mult = min(2.1, 1.0 + 0.05 * (self.elapsed / 30.0)) * (1.0 + (tp - 1) * 0.25)
        # 追击欲望随时间上升：前期散步，后期成群追人
        chase = min(S.MOB_CHASE_MAX, 0.10 + 0.16 * (self.elapsed / 30.0) + (tp - 1) * 0.2)

        cells = self._free_cells()
        sx, sy = self.snake.grid_pos
        far = [c for c in cells if abs(c[0] - sx) + abs(c[1] - sy) > 4]
        cells = far or cells
        if not cells:
            return
        self.mobs.append(Mob(random.choice(cells), hp_mult=hp_mult,
                             speed_mult=speed_mult, chase=chase))

    def _spawn_interval(self):
        base = S.MOB_SPAWN_INTERVAL_SKILLED if self.skilled else S.MOB_SPAWN_INTERVAL
        v = base - S.MOB_SPAWN_RAMP * (self.elapsed / 10.0) - self.kills * 0.012
        # 时间压力：后期刷怪间隔继续压缩，压缩比例随加压系数走
        v /= self._time_pressure() ** 0.6
        return max(S.MOB_SPAWN_MIN * 0.6, v)

    def _kill_exp_mult(self):
        """击杀经验的衰减系数。

        没有这个刹车的话，"杀得快 -> 升级快 -> 更强 -> 杀得更快"
        会形成正反馈，20 秒就冲到满级，游戏直接失去节奏。
        """
        if self.elapsed <= S.KILL_EXP_DECAY_START:
            return 1.0
        t = (self.elapsed - S.KILL_EXP_DECAY_START) * S.KILL_EXP_DECAY_RATE
        return max(S.KILL_EXP_FLOOR, 1.0 - t)

    # ---------------------------------------------------------------- 更新
    def update(self, dt):
        if self.finished:
            return

        self.elapsed += dt
        self.snake.update(dt, GRID_COLS, GRID_ROWS)
        self.snake.facing_update()
        self.snake.update_path(dt)
        self.skills.update(dt, self.snake, GRID_COLS, GRID_ROWS)
        self._apply_skill_events()

        for d in self.drops:
            d.update(dt)

        avoid = {(round(m.cell[0]), round(m.cell[1])) for m in self.mobs}
        player_cell = (round(self.snake.grid_pos[0]), round(self.snake.grid_pos[1]))
        for m in self.mobs:
            m.update(dt, GRID_COLS, GRID_ROWS, avoid, player_cell)

        # ---- 刷怪 ----
        self.mob_spawn_timer -= dt
        if self.mob_spawn_timer <= 0:
            self.mob_spawn_timer = self._spawn_interval()
            self._spawn_mob()

        # ---- 小怪数量上限：太多了会满屏堵死，反而没法玩 ----
        cap = S.MOB_MAX_ALIVE_SKILLED if self.skilled else S.MOB_MAX_ALIVE
        overflow = len(self.mobs) - cap
        if overflow > 0:
            # 从离玩家最远的开始移除，界面上的感觉是"怪走远了"
            sx, sy = self.snake.grid_pos
            self.mobs.sort(key=lambda m: -(abs(m.cell[0] - sx) + abs(m.cell[1] - sy)))
            self.mobs = self.mobs[overflow:]

        if len(self.drops) < 5:
            self._spawn_drop()

        self._handle_pickups()
        self._handle_mob_collision()
        self._handle_skill_damage()
        self._handle_self_collision()

        self.shake = max(0.0, self.shake - dt * 3.2)
        self.flash = max(0.0, self.flash - dt * 2.4)

        self.particles = [p for p in self._tick_particles(dt)]
        self.floaters = [f for f in self._tick_floaters(dt)]
        for t in self.skill_toast:
            t["life"] -= dt
        self.skill_toast = [t for t in self.skill_toast if t["life"] > 0]

        if not self.snake.alive:
            self.finished = True
            self.game.save_manager.add_stardust(self.stardust)
            self.game.save_manager.record_run(self.score, self.snake.level, self.kills)

    def _tick_particles(self, dt):
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 280 * dt
                yield p

    def _tick_floaters(self, dt):
        for f in self.floaters:
            f["life"] -= dt
            f["y"] -= 48 * dt
            if f["life"] > 0:
                yield f

    # ------------------------------------------------------------ 拾取判定
    def _handle_pickups(self):
        head = self.snake.cells[0]
        hx = head[0] * self.CELL + self.CELL / 2
        hy = head[1] * self.CELL + self.CELL / 2

        for d in self.drops:
            if d.alive and d.cell == head:
                d.alive = False
                self._apply_drop(d, hx, hy)

        self.drops = [d for d in self.drops if d.alive]

    def _apply_drop(self, d, hx, hy):
        if d.kind == "exp":
            gained = self.snake.gain_exp(18)
            self.score += 60
            self._float("+18 EXP", hx, hy, COLOR_EXP)
            if gained:
                self._burst(hx, hy, (255, 226, 140), 28)
                self._float(f"LEVEL {self.snake.level}", hx, hy - 46, COLOR_GOLD, 36)
                self.flash = 0.32
        elif d.kind == "crystal":
            self.score += 45
            self._float("+能量", hx, hy, (140, 224, 214))
            self._burst(hx, hy, (140, 224, 214), 14)
        elif d.kind == "stardust":
            self.stardust += 1
            self.score += 120
            self._float("+1 星尘", hx, hy, (206, 168, 255))
            self._burst(hx, hy, (206, 168, 255), 18)
        elif d.kind == "heart":
            if self.snake.hp < HP_MAX:
                self.snake.hp += 1
                self._float("+1 HP", hx, hy, COLOR_HP)
            else:
                self.score += 80
                self._float("+80", hx, hy, COLOR_GOLD)
            self._burst(hx, hy, (255, 130, 160), 16)

    # ------------------------------------------------------------ 战斗判定
    def _handle_mob_collision(self):
        from settings import MOB_TOUCH_DAMAGE, PLAYER_ATK
        head = self.snake.cells[0]
        px, py = self.snake.draw_pos

        for m in self.mobs:
            if not m.alive:
                continue
            if (round(m.cell[0]), round(m.cell[1])) != head:
                continue

            mx, my = m.draw_pos
            killed = m.take_damage(PLAYER_ATK)
            m.knockback((px, py), 0.7)
            self._float(f"-{PLAYER_ATK}", mx, my, COLOR_GOLD, 26)

            if killed:
                self._on_mob_killed(m, mx, my)
            else:
                self.shake = max(self.shake, 0.22)
                self._burst(mx, my, (255, 140, 180), 10)

            if self.snake.take_damage(MOB_TOUCH_DAMAGE):
                self._on_hurt()

        self.mobs = [m for m in self.mobs if m.alive]

    def _handle_self_collision(self):
        if self.snake.is_self_hit() and self.snake.take_damage(1):
            self._on_hurt()

    # ====================================================== 技能伤害结算
    def _apply_skill_events(self):
        """处理 SkillEngine 报上来的"本帧该触发"的事件"""
        # ---- 星辉护盾：直接给无敌 ----
        if self.skills.pending_shield:
            self.snake.invincible = max(self.snake.invincible, S.SHIELD_TIME)
            px, py = self.snake.draw_pos
            self._float("护盾", px, py - 54, (130, 210, 255), 30)
            self._burst(px, py, (130, 210, 255), 24)

        # ---- 樱花风暴：周身范围伤害 ----
        if self.skills.pending_storm:
            self._cast_storm()

    def _cast_storm(self):
        sx, sy = self.snake.grid_pos
        cx = sx * S.CELL_SIZE + S.CELL_SIZE / 2
        cy = sy * S.CELL_SIZE + S.CELL_SIZE / 2

        self._float("樱花风暴", cx, cy - 70, (255, 200, 120), 34)
        self._burst(cx, cy, (255, 200, 120), 54)
        self.shake = max(self.shake, 0.45)

        area = self.skills.storm_cells((round(sx), round(sy)))
        for m in self.mobs:
            if not m.alive:
                continue
            if (round(m.cell[0]), round(m.cell[1])) in area:
                mx, my = m.draw_pos
                self._hurt_mob(m, S.STORM_DMG, mx, my)

    def _handle_skill_damage(self):
        """
        冲锋 / 荆棘尾 / 蔓生荆棘 —— 这三件事都要在"每帧"基础上判定，
        放在这里统一处理，逻辑集中好调。
        """
        if not self.skills.unlocked:
            return

        head = self.snake.cells[0]
        hx, hy = head
        px, py = self.snake.draw_pos
        body_cells = set(self.snake.cells[1:])

        for m in list(self.mobs):
            if not m.alive:
                continue
            mc = (round(m.cell[0]), round(m.cell[1]))
            mx, my = m.draw_pos

            # ---- 樱花冲锋：头旁边的小怪被碾。有充能才碾得动 ----
            if self.skills.has("dash") and self.skills.dash_ready():
                if abs(mc[0] - hx) <= 1 and abs(mc[1] - hy) <= 1 and mc != head:
                    if not self.skills.consume_dash():
                        continue
                    dmg = self.skills.dash_damage(self.snake.level)
                    if not S.DASH_FINISH and m.hp <= dmg:
                        # 冲锋不补刀：只削到剩 1 血，最后一击留给玩家自己撞。
                        # 否则冲锋会抢光击杀，把核心操作挤没。
                        dmg = max(1, m.hp - 1)
                        self._hurt_mob(m, dmg, mx, my, color=(255, 150, 190),
                                       spark=S.DASH_SPARK)
                        self._float("残", mx, my - 26, (255, 190, 220), 22)
                    else:
                        self._hurt_mob(m, dmg, mx, my, color=(255, 150, 190),
                                       spark=S.DASH_SPARK)
                    continue

            # ---- 荆棘尾：撞到身体中后段的怪受伤（每只怪有独立冷却） ----
            if self.skills.has("spike") and mc in body_cells:
                if self.skills.spike_ready(m.uid):
                    self.skills.mark_spike(m.uid)
                    self._hurt_mob(m, S.SPIKE_DMG, mx, my,
                                   color=(180, 120, 255), spark=8)
                    continue

            # ---- 蔓生荆棘：踩到地上荆棘的怪持续受伤 ----
            if self.skills.has("thorn"):
                dmg = self.skills.thorn_damage_at(mc, m.uid)
                if dmg > 0:
                    self._hurt_mob(m, dmg, mx, my, color=(140, 220, 140), spark=5)
        self.mobs = [m for m in self.mobs if m.alive]

    def _hurt_mob(self, m, dmg, mx, my, color=COLOR_GOLD, spark=0):
        """对一只小怪结算伤害。统一走这里，方便保证击杀特效一致。"""
        killed = m.take_damage(dmg)
        m.knockback((self.snake.draw_pos[0], self.snake.draw_pos[1]), 0.35)
        self._float(f"-{dmg}", mx, my, color, 24)
        if spark:
            self._burst(mx, my, color, spark)
        if killed:
            self._on_mob_killed(m, mx, my)

    def _on_mob_killed(self, m, mx, my):
        self.kills += 1
        self.score += 200
        self.shake = max(self.shake, 0.45)
        self._burst(mx, my, (200, 130, 255), 26)
        self._float("+200", mx, my, COLOR_GOLD)
        r = random.random()
        mc = (round(m.cell[0]), round(m.cell[1]))
        kind = "stardust" if r < 0.55 else ("exp" if r < 0.9 else "heart")
        self.drops.append(Drop(kind, mc))

        # 击杀直接给经验，但随时间衰减 —— 这是阻止"越杀越强"正反馈的刹车。
        # 不衰减的话，20 秒就能冲到满级，后半程毫无张力。
        exp = int(S.KILL_EXP_BASE * self._kill_exp_mult())
        if exp > 0 and self.snake.gain_exp(exp):
            self._float(f"LEVEL {self.snake.level}", mx, my - 34, COLOR_GOLD, 30)

    def _on_hurt(self):
        self.shake = 0.6
        self.flash = 0.5
        px, py = self.snake.draw_pos
        self._float("-1 HP", px, py - 30, COLOR_DANGER, 34)
        self._burst(px, py, (255, 90, 110), 22)

    # ---------------------------------------------------------------- 特效
    def _burst(self, x, y, color, n):
        for _ in range(n):
            a = random.random() * 6.283
            sp = random.uniform(70, 330) * self.S
            self.particles.append({
                "x": x, "y": y,
                "vx": math.cos(a) * sp, "vy": math.sin(a) * sp - 60 * self.S,
                "life": random.uniform(0.28, 0.7), "max_life": 0.7,
                "color": color, "r": random.randint(self.s(2), self.s(5)),
            })

    def _float(self, text, x, y, color, size=26):
        self.floaters.append({"text": text, "x": x, "y": y,
                              "color": color, "life": 0.9, "size": self.s(size)})

    # ================================================================ 渲染
    def draw(self):
        screen = self.screen
        sx = sy = 0.0
        if self.shake > 0:
            sx = random.uniform(-1, 1) * self.shake * self.s(14)
            sy = random.uniform(-1, 1) * self.shake * self.s(14)

        self._draw_background(screen, sx, sy)
        self._draw_thorns(screen, sx, sy)
        self._draw_drops(screen, sx, sy)
        self._draw_mobs(screen, sx, sy)
        self._draw_snake(screen, sx, sy)
        self._draw_particles(screen, sx, sy)
        self._draw_floaters(screen, sx, sy)
        self._draw_hud()

        if self.flash > 0:
            veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            veil.fill((255, 70, 100, int(70 * self.flash)))
            screen.blit(veil, (0, 0))

        if self.finished:
            self._draw_gameover()

    def _draw_thorns(self, screen, sx, sy):
        """蔓生荆棘：画在地上的刺，用几何图形拼，不需要额外贴图"""
        if not self.skills.thorns:
            return
        for t in self.skills.thorns:
            cx = self.grid_x + t.cell[0] * self.CELL + self.CELL / 2 + sx
            cy = self.grid_y + t.cell[1] * self.CELL + self.CELL / 2 + sy
            a = int(210 * t.alpha_ratio)
            if a <= 0:
                continue

            layer = pygame.Surface((self.CELL, self.CELL), pygame.SRCALPHA)
            mid = self.CELL / 2
            # 中心一圈暗底，让刺在浅色背景上也看得清
            pygame.draw.circle(layer, (70, 130, 80, int(a * 0.35)), (mid, mid), self.CELL * 0.42)
            for k in range(6):
                ang = k * math.pi / 3
                tip = (mid + math.cos(ang) * self.CELL * 0.36,
                       mid + math.sin(ang) * self.CELL * 0.36)
                b1 = (mid + math.cos(ang + 2.2) * self.CELL * 0.14,
                      mid + math.sin(ang + 2.2) * self.CELL * 0.14)
                b2 = (mid + math.cos(ang - 2.2) * self.CELL * 0.14,
                      mid + math.sin(ang - 2.2) * self.CELL * 0.14)
                pygame.draw.polygon(layer, (150, 220, 150, a), (tip, b1, b2))
                pygame.draw.polygon(layer, (60, 110, 70, a), (tip, b1, b2), 1)
            screen.blit(layer, layer.get_rect(center=(cx, cy)))

    def _draw_background(self, screen, sx, sy):
        # ① 先铺一层纯色底：整个窗口都铺满，避免两侧留出黑边
        screen.fill(COLOR_BG)

        # ② 左右面板区的"遮底"。
        #    背景图是铺满整屏的，如果不先压一层，樱花树会从半透明面板后面
        #    透出来，面板上的字（尤其是右面板的白字）直接糊掉看不清。
        #    这里用不透明的深色块先把两侧压住，再让背景只在网格区域露出来。
        left_cover = pygame.Rect(0, 0, self.left_panel_x + self.panel_w + self.s(8), self.H)
        right_cover = pygame.Rect(self.right_panel_x - self.s(8), 0,
                                  self.W - self.right_panel_x + self.s(8), self.H)
        screen.fill(COLOR_BG, left_cover)
        screen.fill(COLOR_BG, right_cover)

        # ③ 背景图只在网格区域显示，按网格区域裁切后居中放置
        bg = self.assets.get_scaled("backgrounds/campus_garden.png",
                                    width=self.GRID_PX_W)
        if bg.get_height() < self.GRID_PX_H:
            bg = self.assets.get_scaled("backgrounds/campus_garden.png",
                                        height=self.GRID_PX_H)
        by = self.grid_y - (bg.get_height() - self.GRID_PX_H) // 2
        # 用子区域把图限制在网格范围内，shift 时也不会溢到面板上
        area = pygame.Rect(self.grid_x, self.grid_y, self.GRID_PX_W, self.GRID_PX_H)
        screen.set_clip(area)
        screen.blit(bg, (self.grid_x + sx * 0.3, by + sy * 0.3))
        screen.set_clip(None)

        # ④ 网格上压一层暗色薄纱，让人物和掉落在花纹背景上更跳出来
        veil = pygame.Surface((self.GRID_PX_W, self.GRID_PX_H), pygame.SRCALPHA)
        veil.fill((14, 12, 22, 96))
        screen.blit(veil, (self.grid_x, self.grid_y))

        grid = pygame.Surface((self.GRID_PX_W, self.GRID_PX_H), pygame.SRCALPHA)
        for x in range(GRID_COLS + 1):
            pygame.draw.line(grid, (*GRID_COLOR, 95),
                             (x * self.CELL, 0), (x * self.CELL, self.GRID_PX_H))
        for y in range(GRID_ROWS + 1):
            pygame.draw.line(grid, (*GRID_COLOR, 95),
                             (0, y * self.CELL), (self.GRID_PX_W, y * self.CELL))
        screen.blit(grid, (self.grid_x, self.grid_y))

        pygame.draw.rect(screen, COLOR_ACCENT_DARK,
                         pygame.Rect(self.grid_x - 2, self.grid_y - 2,
                                     self.GRID_PX_W + 4, self.GRID_PX_H + 4), 3, border_radius=4)

    def _draw_drops(self, screen, sx, sy):
        for d in self.drops:
            size = self.s(d.size)
            img = self.assets.get_scaled(d.asset, height=size)
            x, y = d.draw_pos
            glow = pygame.Surface((size + self.s(26), size + self.s(26)), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*d.color, 62),
                               (glow.get_width() // 2, glow.get_height() // 2),
                               size // 2 + self.s(10))
            screen.blit(glow, (self.grid_x + x - glow.get_width() / 2 + sx,
                               self.grid_y + y - glow.get_height() / 2 + sy))
            screen.blit(img, (self.grid_x + x - img.get_width() / 2 + sx,
                              self.grid_y + y - img.get_height() / 2 + sy))

    def _draw_mobs(self, screen, sx, sy):
        for m in self.mobs:
            size = self.s(52)
            img = self.assets.get_scaled("characters/mob_shadow.png", height=size)
            x, y = m.draw_pos
            bob = math.sin(m.t) * self.s(3)
            rect = img.get_rect(center=(self.grid_x + x + sx,
                                        self.grid_y + y + bob + sy))
            sh = pygame.Surface((size, size // 3), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 95), sh.get_rect())
            screen.blit(sh, sh.get_rect(center=(rect.centerx, rect.bottom - self.s(4))))
            screen.blit(img, rect)

            if m.hit_flash > 0:
                fl = img.copy()
                fl.fill((255, 255, 255, int(190 * (m.hit_flash / 0.18))),
                        special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(fl, rect)

            if m.hp < m.hp_max:
                bw, bh = self.s(44), self.s(5)
                bx = rect.centerx - bw / 2
                by = rect.top - self.s(12)
                pygame.draw.rect(screen, (30, 20, 40), (bx, by, bw, bh), border_radius=2)
                pygame.draw.rect(screen, COLOR_DANGER,
                                 (bx, by, bw * m.hp / m.hp_max, bh), border_radius=2)

    def _draw_snake(self, screen, sx, sy):
        sn = self.snake
        px, py = sn.draw_pos
        base_x = self.grid_x + px + sx
        base_y = self.grid_y + py + sy
    
        # 下半身：沿路径摆尾椎
        pts = sn.sample_tail_points()
        n = max(1, len(pts))
        for i, (tx, ty, ang, scale) in enumerate(pts):
            seg_h = max(6, int(self.CELL * scale))
            img = self.assets.get_rotated("characters/sakura/body_seg.png", ang + 180)
            w, h = img.get_size()
            ratio = seg_h / h
            img = pygame.transform.smoothscale(img, (max(1, int(w * ratio)), seg_h))
            shade = 1.0 - (i / n) * 0.35
            if shade < 0.99:
                img.fill((int(255 * shade), int(255 * shade), int(255 * shade), 255),
                         special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(img, img.get_rect(center=(self.grid_x + tx + sx,
                                                  self.grid_y + ty + sy)))
    
        if pts:
            tx, ty, ang, _ = pts[-1]
            tip = self.assets.get_rotated("characters/sakura/tail_tip.png", ang)
            th = max(8, int(self.CELL * 0.30))
            r = th / tip.get_height()
            tip = pygame.transform.smoothscale(tip, (max(1, int(tip.get_width() * r)), th))
            screen.blit(tip, tip.get_rect(center=(self.grid_x + tx + sx,
                                                  self.grid_y + ty + sy)))
    
        # 影子
        sh_w, sh_h = self.s(72), self.s(22)
        sh = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 115), sh.get_rect())
        screen.blit(sh, sh.get_rect(center=(base_x, base_y + self.s(24))))
    
        # 上半身：人物立绘
        sn.bob_t += 0.045
        bob = math.sin(sn.bob_t) * self.s(3)
        alpha = 255
        if sn.invincible > 0 and int(sn.invincible * 14) % 2 == 0:
            alpha = 105
    
        head = self.assets.get_scaled("characters/sakura/head.png",
                                      height=int(self.CELL * 1.7))
        if sn.direction[0] < 0:
            head = pygame.transform.flip(head, True, False)
        head = head.copy()
        head.set_alpha(alpha)
        screen.blit(head, (base_x - head.get_width() / 2,
                           base_y - head.get_height() * 0.74 + bob))

    def _draw_particles(self, screen, sx, sy):
        for p in self.particles:
            a = max(0, int(255 * (p["life"] / p["max_life"])))
            r = p["r"]
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p["color"], a), (r, r), r)
            screen.blit(s, (self.grid_x + p["x"] - r + sx,
                            self.grid_y + p["y"] - r + sy))

    def _draw_floaters(self, screen, sx, sy):
        for f in self.floaters:
            a = max(0, min(255, int(255 * (f["life"] / 0.9))))
            font = self.assets.get_font(f["size"], bold=True)
            t = font.render(f["text"], True, f["color"])
            t.set_alpha(a)
            screen.blit(t, t.get_rect(center=(self.grid_x + f["x"] + sx,
                                              self.grid_y + f["y"] + sy)))

    # ---------------------------------------------------------------- HUD
    def _draw_skill_panel(self, screen, lx, py, panel_w, bottom):
        """
        技能区。已解锁的亮着，未解锁的显示成灰色 + 需要等级，
        让玩家一眼知道"下一级会解锁什么"，这是成长感的来源。

        bottom 是可用底边 —— 按钮高度会按剩余空间自适应，
        窗口小的时候自动压扁，而不是溢出到面板外面。
        """
        head_h = self.f_tiny.get_height() + self.s(4)
        t = self.f_tiny.render("技能", True, COLOR_TEXT_DIM)
        screen.blit(t, (lx, py))
        nxt = self.skills.next_unlock(self.snake.level)
        if nxt:
            sid, gap = nxt
            tip = self.f_tiny.render(f"下个 Lv.{self.snake.level + gap}", True, COLOR_TEXT_DIM)
            screen.blit(tip, (lx + panel_w - tip.get_width(), py))
        py += head_h

        ids = all_skill_ids()
        avail = bottom - py
        gap = self.s(4)
        row_h = int((avail - gap * (len(ids) - 1)) / max(1, len(ids)))
        row_h = max(self.s(22), min(self.s(46), row_h))   # 夹在设计区间里

        for sid in ids:
            info = skill_info(sid)
            unlocked = self.skills.has(sid)
            need = info["unlock_level"]
            color = info["color"] if unlocked else (78, 74, 92)

            box = pygame.Rect(lx, py, panel_w, row_h)
            pygame.draw.rect(screen, (30, 26, 42) if unlocked else (24, 22, 32),
                             box, border_radius=self.s(8))
            pygame.draw.rect(screen, color, box, 2, border_radius=self.s(8))

            ic = box.x + row_h * 0.5
            self._draw_skill_icon(screen, sid, ic, box.centery, color, row_h)

            name_color = color if unlocked else (120, 116, 136)
            t = self.f_tiny.render(info["name"], True, name_color)
            screen.blit(t, (box.x + row_h + self.s(6),
                            box.centery - t.get_height() / 2))

            if unlocked:
                # 解锁后显示最有用的那个状态：冲锋看充能、护盾/风暴看倒计时
                if sid == "dash":
                    sub = "◆" * self.skills.dash_charges + "◇" * (S.DASH_CHARGES - self.skills.dash_charges)
                elif sid == "shield":
                    sub = f"{self.skills.shield_timer:.0f}s"
                elif sid == "storm":
                    sub = f"{self.skills.storm_timer:.0f}s"
                elif sid == "thorn":
                    sub = f"{len(self.skills.thorns)}"
                else:
                    sub = ""
                if sub:
                    st = self.f_tiny.render(sub, True, COLOR_TEXT_DIM)
                    screen.blit(st, (box.right - self.s(6) - st.get_width(),
                                     box.centery - st.get_height() / 2))
            else:
                st = self.f_tiny.render(f"Lv.{need}", True, (110, 106, 126))
                screen.blit(st, (box.right - self.s(6) - st.get_width(),
                                 box.centery - st.get_height() / 2))

            py += row_h + gap

    def _draw_skill_icon(self, screen, sid, cx, cy, color, size=None):
        """技能图标：樱花/尖刺/盾牌/荆棘/风，全部用绘图指令画，省贴图"""
        r = (size or self.s(44)) * 0.5
        cx, cy = int(cx), int(cy)
        if sid == "dash":
            # 樱花：五瓣
            for k in range(5):
                a = k * 2 * math.pi / 5 - math.pi / 2
                px = cx + math.cos(a) * r * 0.52
                py = cy + math.sin(a) * r * 0.52
                pygame.draw.circle(screen, color, (int(px), int(py)), max(2, int(r * 0.42)))
            pygame.draw.circle(screen, (255, 240, 220), (cx, cy), max(1, int(r * 0.24)))
        elif sid == "spike":
            k = r * 0.8
            pygame.draw.polygon(screen, color, [(cx, cy - k), (cx - k, cy + k * 0.7),
                                                (cx + k, cy + k * 0.7)])
        elif sid == "shield":
            k = r * 0.9
            pts = [(cx, cy - k), (cx + k * 0.8, cy - k * 0.45), (cx + k * 0.8, cy + k * 0.2),
                   (cx, cy + k), (cx - k * 0.8, cy + k * 0.2), (cx - k * 0.8, cy - k * 0.45)]
            pygame.draw.polygon(screen, color, pts)
            pygame.draw.polygon(screen, (255, 255, 255), pts, 1)
        elif sid == "thorn":
            k = r * 0.8
            pygame.draw.line(screen, color, (cx - k, cy + k), (cx + k, cy - k), 2)
            for d in (-r * 0.4, 0, r * 0.4):
                pygame.draw.line(screen, color, (cx + d, cy - d),
                                 (cx + d + r * 0.45, cy - d - r * 0.2), 2)
        elif sid == "storm":
            for k, rr in enumerate((r * 0.85, r * 0.58, r * 0.3)):
                rect = pygame.Rect(cx - rr, cy - r * 0.55 + k * r * 0.5,
                                   rr * 2, max(3, int(r * 0.5)))
                pygame.draw.arc(screen, color, rect, math.pi * 0.15, math.pi * 0.95, 2)

    def _draw_skill_toast(self):
        """解锁提示：屏幕中上方滑出的一条横幅"""
        if not self.skill_toast:
            return
        screen = self.screen
        for i, item in enumerate(self.skill_toast[:3]):
            info = skill_info(item["sid"])
            life = item["life"]
            # 淡入 0.25s / 淡出 0.5s
            if life > 2.75:
                a = (3.0 - life) / 0.25
            elif life < 0.5:
                a = life / 0.5
            else:
                a = 1.0
            a = max(0.0, min(1.0, a)) * 255

            w = self.s(430)
            h = self.s(70)
            x = self.W // 2 - w // 2
            y = self.s(60) + i * (h + self.s(10))
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            panel.fill((*COLOR_BG_LIGHT, int(220 * a / 255)))
            pygame.draw.rect(panel, (*info["color"], int(a)), panel.get_rect(),
                             self.s(3), border_radius=self.s(12))
            screen.blit(panel, (x, y))

            pad = self.s(14)
            t1 = self.f_tiny.render("解锁技能", True, COLOR_TEXT_DIM)
            t1.set_alpha(int(a))
            screen.blit(t1, (x + pad, y + pad))

            self._draw_skill_icon(screen, item["sid"], x + pad + self.s(10),
                                  y + h - self.s(24), info["color"], self.s(40))

            t2 = self.f_body.render(info["name"], True, info["color"])
            t2.set_alpha(int(a))
            screen.blit(t2, (x + pad + self.s(36), y + h - self.s(24) - t2.get_height() / 2))

            t3 = self.f_tiny.render(info["desc"], True, COLOR_TEXT)
            t3.set_alpha(int(a * 0.8))
            screen.blit(t3, (x + pad + self.s(36) + t2.get_width() + self.s(10),
                             y + h - self.s(24) - t3.get_height() / 2))

    def _draw_hud(self):
        screen = self.screen
        sn = self.snake

        pad = self.s(10)                 # 面板内部统一内边距
        lx = self.left_panel_x
        ly = self.grid_y
        panel_w = self.panel_w
        panel_h = self.panel_h

        # ---------------- 左侧面板 ----------------
        self._panel(screen, lx, ly, panel_w, panel_h)

        py = ly + pad
        t = self.f_sub.render(self.snake_name, True, COLOR_ACCENT)
        screen.blit(t, (lx + pad, py)); py += t.get_height() + self.s(4)
        t = self.f_tiny.render(self.snake_rarity, True, COLOR_TEXT_DIM)
        screen.blit(t, (lx + pad, py)); py += t.get_height() + self.s(8)

        # 立绘：高度按面板宽度推，保证不同窗口尺寸下都放得下
        head_h = int(min(panel_w * 0.75, panel_h * 0.22))
        head = self.assets.get_scaled("characters/sakura/head.png", height=head_h)
        screen.blit(head, (lx + (panel_w - head.get_width()) / 2, py))
        py += head_h + self.s(6)

        t = self.f_sub.render(f"Lv.{sn.level}", True, COLOR_GOLD)
        screen.blit(t, (lx + pad, py)); py += t.get_height() + self.s(6)

        # 经验条
        bw = panel_w - pad * 2
        bh = self.s(12)
        pygame.draw.rect(screen, (24, 20, 34), (lx + pad, py, bw, bh), border_radius=bh // 2)
        need = sn.exp_needed()
        ratio = min(1.0, sn.exp / need) if need else 1.0
        if ratio > 0:
            pygame.draw.rect(screen, COLOR_EXP,
                             (lx + pad, py, int(bw * ratio), bh), border_radius=bh // 2)
        py += bh + self.s(4)
        t = self.f_tiny.render(f"{sn.exp} / {need}", True, COLOR_TEXT_DIM)
        screen.blit(t, (lx + pad, py)); py += t.get_height() + self.s(8)

        # 生命
        t = self.f_body.render("生命", True, COLOR_TEXT)
        screen.blit(t, (lx + pad, py)); py += t.get_height() + self.s(4)
        r = self.s(11)
        step = min(self.s(38), (panel_w - pad * 2) / max(1, HP_MAX))
        for i in range(HP_MAX):
            color = COLOR_HP if i < sn.hp else (56, 48, 66)
            cx = int(lx + pad + r + i * step)
            pygame.draw.circle(screen, color, (cx, py + r), r)
            pygame.draw.circle(screen, (255, 255, 255), (cx, py + r), r, 1)
        py += r * 2 + self.s(8)

        t = self.f_body.render(f"攻击 {sn.attack}", True, (120, 210, 200))
        screen.blit(t, (lx + pad, py)); py += t.get_height() + self.s(4)
        t = self.f_tiny.render(f"击杀 {self.kills}", True, COLOR_TEXT_DIM)
        screen.blit(t, (lx + pad, py)); py += t.get_height() + self.s(10)

        # ---------- 技能列表 ----------
        self._draw_skill_panel(screen, lx + pad, py, panel_w - pad * 2, ly + panel_h - self.s(8))

        # ---------------- 右侧面板 ----------------
        rx = self.right_panel_x
        self._panel(screen, rx, ly, panel_w, panel_h)

        py = ly + pad
        for label, value, color in (
            ("得分", f"{self.score}", COLOR_TEXT),
            ("星尘", f"{self.stardust}", (206, 168, 255)),
            ("存活", f"{int(self.elapsed)}s", (120, 210, 200)),
            ("威胁", f"{len(self.mobs)}", COLOR_DANGER),
        ):
            t = self.f_tiny.render(label, True, COLOR_TEXT_DIM)
            screen.blit(t, (rx + pad, py)); py += t.get_height() + self.s(2)
            t = self.f_sub.render(value, True, color)
            screen.blit(t, (rx + pad, py)); py += t.get_height() + self.s(10)

        # 难度加压提示：让玩家知道"不是我变菜了，是游戏在加压"
        tp = self._time_pressure()
        if tp > 1.05:
            t = self.f_tiny.render(f"压力 x{tp:.1f}", True, COLOR_DANGER)
            screen.blit(t, (rx + pad, py))

        fps = self.game.clock.get_fps()
        color = COLOR_GOOD if fps > 55 else (COLOR_GOLD if fps > 40 else COLOR_DANGER)
        t = self.f_tiny.render(f"{fps:.0f} FPS", True, color)
        screen.blit(t, (rx + pad, ly + panel_h - t.get_height() - pad))

        self._draw_skill_toast()

    def _panel(self, screen, x, y, w, h):
        """统一的半透明面板样式"""
        p = pygame.Surface((w, h), pygame.SRCALPHA)
        p.fill((*COLOR_BG_LIGHT, 180))
        screen.blit(p, (x, y))
        pygame.draw.rect(screen, COLOR_ACCENT_DARK,
                         pygame.Rect(x, y, w, h), 2, border_radius=self.s(10))

    def _draw_gameover(self):
        screen = self.screen
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((10, 8, 16, 195))
        screen.blit(veil, (0, 0))

        cx, cy = self.W // 2, self.H // 2
        t = self.f_title.render("战斗结束", True, COLOR_ACCENT)
        screen.blit(t, t.get_rect(center=(cx, cy - 250)))

        rows = [
            ("最终得分", f"{self.score}", COLOR_TEXT),
            ("抵达等级", f"Lv.{self.snake.level}", COLOR_GOLD),
            ("解锁技能", f"{self.skills.count} / {len(all_skill_ids())}", (255, 150, 190)),
            ("击杀小怪", f"{self.kills}", COLOR_DANGER),
            ("存活时间", f"{int(self.elapsed)} 秒", (120, 210, 200)),
            ("获得星尘", f"{self.stardust}", (206, 168, 255)),
        ]
        y = cy - 140
        for label, value, color in rows:
            lt = self.f_body.render(label, True, COLOR_TEXT_DIM)
            vt = self.f_body.render(value, True, color)
            screen.blit(lt, lt.get_rect(midright=(cx - 24, y)))
            screen.blit(vt, vt.get_rect(midleft=(cx + 24, y)))
            y += 50

        t = self.f_small.render("按 R 再来一局    ·    按 ESC 返回主菜单", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(cx, cy + 220)))

    # ---------------------------------------------------------------- 输入
    def handle_events(self, events):
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                self.game.change_scene("main_menu")
                return
            if self.finished:
                if event.key == pygame.K_r:
                    self.reset()
                continue
            k = event.key
            if k in (pygame.K_UP, pygame.K_w):
                self.snake.set_direction((0, -1))
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.snake.set_direction((0, 1))
            elif k in (pygame.K_LEFT, pygame.K_a):
                self.snake.set_direction((-1, 0))
            elif k in (pygame.K_RIGHT, pygame.K_d):
                self.snake.set_direction((1, 0))
