# -*- coding: utf-8 -*-
"""
scenes/battle.py —— 战斗场景（大地图自由移动动作生存）

一局的完整过程：
    WASD 自由移动 → 自动普攻索敌 → 左键闪避 → 1-6 主动技能 → 捡道具升级选卡
    → 小怪越来越多越来越硬 → 生存到阈值触发 Boss → 击败结算 / 阵亡结算

坐标系（重要）：
    · 世界尺寸 = WORLD_SCREENS_X * 窗口宽 × WORLD_SCREENS_Y * 窗口高（世界像素）
    · 所有实体 pos 都是世界像素；绘制时用 wx()/wy() 减去摄像机 self.cam
    · 标注 (设计像素) 的常量按 self.S 缩放成当前分辨率的真实像素
    · Boss 复用 boss.py：pos_cells 用「世界格」（世界像素 / CELL），
      ctx 传 world_cols / world_rows / CELL，Boss 弹幕天然运作在世界坐标
"""

import json
import math
import os
import random

import pygame

import settings as S
from core.scene import Scene
from game_logic.entities import Drop, Mob, PlayerBullet, SnakeGirl
from game_logic.boss import Boss, boss_trigger_met, load_boss_cfg
from game_logic.skills import SkillEngine, all_skill_ids, skill_info
from ui.button import Button
from settings import (
    COLOR_ACCENT, COLOR_ACCENT_DARK, COLOR_BG, COLOR_BG_LIGHT, COLOR_DANGER,
    COLOR_EXP, COLOR_GOLD, COLOR_GOOD, COLOR_HP, COLOR_TEXT, COLOR_TEXT_DIM,
    FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_SUBTITLE, FONT_SIZE_TITLE,
)

# 数字键 1-6 -> 技能键位
_NUM_KEYS = {
    pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3,
    pygame.K_4: 4, pygame.K_5: 5, pygame.K_6: 6,
}


def _seg_dist(px, py, x1, y1, x2, y2):
    """点 (px,py) 到线段 (x1,y1)-(x2,y2) 的最短距离。冲锋路径伤害用。"""
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 <= 1e-6:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / L2
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (x1 + dx * t), py - (y1 + dy * t))


class BattleScene(Scene):
    """战斗场景（自由移动版）"""

    # ================================================================ 生命周期
    def enter(self):
        self.assets = self.game.assets
        self._setup_view()
        self.reset()

    def on_resize(self):
        """拖拽改变窗口大小：重算字体/世界尺寸/摄像机，绝不重置战斗进度"""
        self._bg_surf = None          # 背景缓存失效（世界尺寸变了）
        self._setup_view()
        self._clamp_cam()

    def _setup_view(self):
        """按当前窗口尺寸/缩放重算字体、世界几何与暂停按钮布局"""
        self.f_tiny = self.assets.get_font(self.s(FONT_SIZE_SMALL - 2))
        self.f_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))
        self.f_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.f_sub = self.assets.get_font(self.s(FONT_SIZE_SUBTITLE))
        self.f_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)

        # ---- 世界几何：一律现取 S.XXX，避免导入快照幽灵 bug ----
        self.CELL = S.CELL_SIZE
        self.world_w = max(self.W, S.WORLD_SCREENS_X * self.W)
        self.world_h = max(self.H, S.WORLD_SCREENS_Y * self.H)
        self.world_cols = self.world_w / max(1, self.CELL)
        self.world_rows = self.world_h / max(1, self.CELL)

        # ---- 暂停菜单按钮（居中竖排）----
        bw, bh = self.s(300), self.s(58)
        bx = self.W // 2 - bw // 2
        by = self.H // 2 - self.s(30)
        gap = bh + self.s(14)
        self.resume_btn = Button("继续  (ESC)", bx, by, bw, bh,
                                 font_size=self.s(FONT_SIZE_BODY),
                                 on_click=self._toggle_pause)
        self.restart_btn = Button("重开本局", bx, by + gap, bw, bh,
                                  font_size=self.s(FONT_SIZE_BODY),
                                  on_click=self.reset)
        self.quit_btn = Button("返回主菜单", bx, by + gap * 2, bw, bh,
                               font_size=self.s(FONT_SIZE_BODY),
                               on_click=lambda: self.game.change_scene("main_menu"))

    def exit(self):
        pass

    def wants_movement_keys(self):
        """只有「进行中」才占用方向键（移动）；暂停 / 结算 / 选卡时让给音量热键。"""
        return not self.paused and not self.finished and not self.card_overlay

    # ================================================================ 重置
    def reset(self):
        self.game.audio.play_bgm("battle")
        char_id = self.game.save_manager.get("selected_character", "sakura")
        self.scene_id = self.game.save_manager.get("selected_scene", "campus_garden")
        self.snake_name, self.snake_rarity = self._char_label(char_id)
        self._load_skin(char_id, self.scene_id)

        # ---- 玩家：世界正中出生 ----
        self.snake = SnakeGirl(char_id, start_pos=(self.world_w / 2, self.world_h / 2))
        self.snake.radius = self.s(S.PLAYER_RADIUS)
        self.snake.seg_len = self.s(S.BODY_SEG_LEN)
        self.snake._init_path()
        self.snake.facing_update()
        self.snake.on_level_up_cb = self._on_level_up

        # ---- 成长：被动乘区 + 主动技能引擎 ----
        self.stats = {"atk": 1.0, "speed": 1.0, "atkspd": 1.0,
                      "cdr": 0.0, "pickup": 1.0}
        self.skills = SkillEngine()
        self.skill_toast = []
        self._cards_cache = None

        # ---- 实体容器 ----
        self.drops = []
        self.mobs = []
        self.bullets = []          # 玩家普攻 / 大招弹
        self.projectiles = []      # Boss 弹幕
        self.particles = []
        self.floaters = []

        # ---- 计时 / 计分 ----
        self.elapsed = 0.0
        self.score = 0
        self.stardust = 0
        self.kills = 0
        self.mob_spawn_timer = 1.4
        self.item_spawn_timer = S.ITEM_SPAWN_INTERVAL
        self.shake = 0.0
        self.flash = 0.0
        self.finished = False
        self.paused = False
        self.victory = False

        # ---- 升级选卡 ----
        self.pending_cards = 0
        self.card_overlay = None
        self.card_rects = []

        # ---- Boss 战状态 ----
        self.boss_cfg = load_boss_cfg(self.scene_id)
        self.boss = None
        self.boss_spawned = False
        self.boss_hit_cd = 0.0
        self.boss_banner = 0.0

        # ---- 摄像机 ----
        self.cam = [self.snake.pos[0] - self.W / 2, self.snake.pos[1] - self.H / 2]
        self._clamp_cam()
        self._bg_surf = None

        # 开局先撒一批道具，免得前期空手
        for _ in range(6):
            self._spawn_item(near_player=False)

    # ================================================================ 外观 / 配置
    def _char_label(self, char_id):
        try:
            path = os.path.join(S.DATA_DIR, "characters.json")
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            items = raw.get("characters", raw) if isinstance(raw, dict) else raw
            for c in items:
                if c.get("id") == char_id:
                    name = c.get("name", char_id)
                    rarity = c.get("rarity", "")
                    return name, f"{name} · {rarity}" if rarity else name
        except (IOError, json.JSONDecodeError, AttributeError, TypeError):
            pass
        return char_id, char_id

    def _load_skin(self, char_id, scene_id):
        default_head = "characters/sakura/head.png"
        default_body = "characters/sakura/body_seg.png"
        default_tail = "characters/sakura/tail_tip.png"
        default_bg = "backgrounds/campus_garden.png"

        char = self._find_in_json("characters.json", "characters", char_id)
        rarity = char.get("rarity", "")
        if rarity:
            self.snake_rarity = f"{self.snake_name} · {rarity}"
        self.char_head = char.get("head") or default_head
        self.char_body = char.get("body_seg") or default_body
        self.char_tail = char.get("tail_tip") or default_tail

        scene = self._find_in_json("scenes.json", "scenes", scene_id)
        self.scene_bg = scene.get("bg") or default_bg

    @staticmethod
    def _find_in_json(filename, wrap_key, want_id):
        try:
            path = os.path.join(S.DATA_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            items = raw.get(wrap_key, raw) if isinstance(raw, dict) else raw
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict) and it.get("id") == want_id:
                        return it
        except (IOError, json.JSONDecodeError, AttributeError, TypeError):
            pass
        return {}

    def _card_pool(self):
        """读 data/cards.json 卡池（缓存）。"""
        if self._cards_cache is None:
            self._cards_cache = []
            try:
                path = os.path.join(S.DATA_DIR, "cards.json")
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                items = raw.get("cards", raw) if isinstance(raw, dict) else raw
                for c in items:
                    if isinstance(c, dict) and c.get("id"):
                        self._cards_cache.append(c)
            except (IOError, json.JSONDecodeError, AttributeError, TypeError):
                self._cards_cache = []
        return self._cards_cache

    # ================================================================ 派生属性
    @property
    def player_speed(self):
        return S.PLAYER_SPEED * self.S * self.stats["speed"]

    @property
    def player_damage(self):
        return max(1, int(round(self.snake.attack * self.stats["atk"])))

    @property
    def atk_interval(self):
        base = S.ATK_INTERVAL_BASE - (self.snake.level - 1) * S.ATK_INTERVAL_PER_LEVEL
        base = max(S.ATK_INTERVAL_MIN, base)
        return base / max(0.2, self.stats["atkspd"])

    @property
    def magnet_radius(self):
        return S.ITEM_MAGNET_RADIUS * self.S * self.stats["pickup"]

    @property
    def pickup_radius(self):
        return S.ITEM_PICKUP_RADIUS * self.S

    # ---- 世界 <-> 屏幕 ----
    def wx(self, x, sx=0.0):
        return x - self.cam[0] + sx

    def wy(self, y, sy=0.0):
        return y - self.cam[1] + sy

    def _clamp_cam(self):
        self.cam[0] = min(max(self.cam[0], 0.0), max(0.0, self.world_w - self.W))
        self.cam[1] = min(max(self.cam[1], 0.0), max(0.0, self.world_h - self.H))

    # ================================================================ 难度曲线
    def _time_pressure(self):
        if self.elapsed <= S.TIME_PRESSURE_START:
            return 1.0
        t = (self.elapsed - S.TIME_PRESSURE_START) * S.TIME_PRESSURE_RAMP
        return min(S.TIME_PRESSURE_MAX, 1.0 + t)

    def _mob_speed(self):
        base = S.MOB_SPEED_BASE * self.S
        mult = min(S.MOB_SPEED_MAX_MULT, 1.0 + S.MOB_SPEED_GROWTH * (self.elapsed / 30.0))
        tp = self._time_pressure()
        return base * mult * (1.0 + (tp - 1) * 0.25)

    def _mob_atk(self):
        return max(1, int(S.MOB_TOUCH_DAMAGE + (self.elapsed / 60.0) * S.MOB_ATK_GROWTH))

    def _mob_hp_mult(self):
        tp = self._time_pressure()
        return min(S.MOB_HP_MAX_MULT, 1.0 + S.MOB_HP_GROWTH * (self.elapsed / 30.0)) * tp

    def _spawn_interval(self):
        v = S.MOB_SPAWN_INTERVAL - S.MOB_SPAWN_RAMP * (self.elapsed / 10.0)
        v /= self._time_pressure() ** 0.6
        return max(S.MOB_SPAWN_MIN * 0.6, v)

    def _item_tier(self):
        return max(1, min(S.ITEM_TIER_MAX, 1 + int(self.elapsed / S.ITEM_TIER_TIME)))

    # ================================================================ 生成
    def _offscreen_pos(self):
        """在当前摄像机视野外一圈取一个刷怪点（保证不在玩家眼前凭空出现）。"""
        m = S.MOB_SPAWN_OFFSCREEN_MARGIN * self.S
        left, top = self.cam[0] - m, self.cam[1] - m
        right, bottom = self.cam[0] + self.W + m, self.cam[1] + self.H + m
        side = random.randint(0, 3)
        if side == 0:
            x, y = left, random.uniform(top, bottom)
        elif side == 1:
            x, y = right, random.uniform(top, bottom)
        elif side == 2:
            x, y = random.uniform(left, right), top
        else:
            x, y = random.uniform(left, right), bottom
        x = min(max(x, 0.0), self.world_w)
        y = min(max(y, 0.0), self.world_h)
        return (x, y)

    def _spawn_mob(self):
        pos = self._offscreen_pos()
        self.mobs.append(Mob(
            pos,
            hp_mult=self._mob_hp_mult(),
            speed=self._mob_speed(),
            atk=self._mob_atk(),
            radius=self.s(S.MOB_RADIUS),
        ))

    def _roll_kind(self):
        r = random.random()
        if r < S.DROP_EXP:
            return "exp"
        if r < S.DROP_EXP + S.DROP_CRYSTAL:
            return "crystal"
        if r < S.DROP_EXP + S.DROP_CRYSTAL + S.DROP_STARDUST:
            return "stardust"
        return "heart"

    def _spawn_item(self, near_player=True):
        if len(self.drops) >= S.ITEM_MAX_ON_MAP:
            return
        if near_player:
            px, py = self.snake.pos
            span = math.hypot(self.W, self.H)
            dist = random.uniform(0.5, 1.4) * span
            ang = random.random() * math.tau
            x = min(max(px + math.cos(ang) * dist, 40), self.world_w - 40)
            y = min(max(py + math.sin(ang) * dist, 40), self.world_h - 40)
        else:
            x = random.uniform(40, self.world_w - 40)
            y = random.uniform(40, self.world_h - 40)
        self.drops.append(Drop(self._roll_kind(), (x, y), tier=self._item_tier()))

    def _drop_from_mob(self, m):
        self.drops.append(Drop(self._roll_kind(), (m.pos[0], m.pos[1]),
                               tier=self._item_tier()))

    # ================================================================ 主更新
    def update(self, dt):
        if self.finished or self.paused or self.card_overlay:
            return

        self.elapsed += dt

        self._update_player(dt)
        self.snake.update_path(dt)
        self.snake.facing_update()
        self.skills.update(dt)

        self._auto_attack(dt)
        self._update_bullets(dt)
        self._update_mobs(dt)
        self._update_items(dt)
        self._update_skill_fields(dt)
        self._handle_mob_contact()
        self._update_boss(dt)

        self.shake = max(0.0, self.shake - dt * 3.2)
        self.flash = max(0.0, self.flash - dt * 2.4)

        self.particles = list(self._tick_particles(dt))
        self.floaters = list(self._tick_floaters(dt))
        for t in self.skill_toast:
            t["life"] -= dt
        self.skill_toast = [t for t in self.skill_toast if t["life"] > 0]

        self._update_cam(dt)

        # 升级选卡：攒着的卡在这里弹出（可能一次升多级）
        if self.pending_cards > 0 and self.card_overlay is None:
            self._open_card_overlay()

        if not self.snake.alive:
            self.finished = True
            self.game.audio.play("gameover")
            self.game.audio.play_bgm("gameover")
            self.game.save_manager.add_stardust(self.stardust)
            self.game.save_manager.record_run(self.score, self.snake.level, self.kills)

    # ------------------------------------------------------------ 玩家
    def _update_player(self, dt):
        keys = pygame.key.get_pressed()
        dx = (1 if keys[pygame.K_d] else 0) + (1 if keys[pygame.K_RIGHT] else 0) \
            - (1 if keys[pygame.K_a] else 0) - (1 if keys[pygame.K_LEFT] else 0)
        dy = (1 if keys[pygame.K_s] else 0) + (1 if keys[pygame.K_DOWN] else 0) \
            - (1 if keys[pygame.K_w] else 0) - (1 if keys[pygame.K_UP] else 0)
        move = [float(dx), float(dy)]
        self.snake.update(dt, self.world_w, self.world_h, move,
                          self.player_speed, dodge_dist=self.s(S.DODGE_DIST))
        # 静止时朝向最近的敌人，立绘/普攻方向更自然
        if dx == 0 and dy == 0 and self.snake.dodge_t <= 0:
            tgt = self._nearest_target()
            if tgt is not None:
                _kind, obj = tgt
                tx, ty = obj.pos[0], obj.pos[1]
                ax, ay = tx - self.snake.pos[0], ty - self.snake.pos[1]
                d = math.hypot(ax, ay) or 1.0
                self.snake.aim_dir = [ax / d, ay / d]

    def _nearest_target(self, max_range=None):
        px, py = self.snake.pos
        best = None
        bd = float("inf")
        for m in self.mobs:
            if not m.alive:
                continue
            d = math.hypot(m.pos[0] - px, m.pos[1] - py)
            if d < bd:
                bd = d
                best = ("mob", m)
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            d = math.hypot(bx - px, by - py)
            if d < bd:
                bd = d
                best = ("boss", self.boss)
        if best is None:
            return None
        if max_range is not None and bd > max_range:
            return None
        return best

    def try_dodge(self, mouse_pos):
        """左键闪避：朝当前移动方向（静止时朝鼠标）瞬移。"""
        mv = self.snake.move_dir
        if abs(mv[0]) > 1e-6 or abs(mv[1]) > 1e-6:
            dirn = (mv[0], mv[1])
        else:
            wxp = mouse_pos[0] + self.cam[0]
            wyp = mouse_pos[1] + self.cam[1]
            dirn = (wxp - self.snake.pos[0], wyp - self.snake.pos[1])
        if self.snake.start_dodge(dirn):
            self.game.audio.play("dodge", throttle=0.05)
            self._burst(self.snake.pos[0], self.snake.pos[1], (180, 220, 255), 14)

    # ------------------------------------------------------------ 自动普攻
    def _auto_attack(self, dt):
        self.snake.atk_timer -= dt
        if self.snake.atk_timer > 0:
            return
        tgt = self._nearest_target(max_range=S.ATK_RANGE * self.S)
        if tgt is None:
            self.snake.atk_timer = 0.06
            return
        self.snake.atk_timer = self.atk_interval
        _kind, obj = tgt
        tx, ty = obj.pos[0], obj.pos[1]
        px, py = self.snake.pos
        dx, dy = tx - px, ty - py
        d = math.hypot(dx, dy) or 1.0
        spd = S.ATK_BULLET_SPEED * self.S
        self.bullets.append(PlayerBullet(
            (px, py), (dx / d * spd, dy / d * spd), self.player_damage,
            self.s(S.ATK_BULLET_RADIUS)))
        self.game.audio.play("shoot", throttle=0.05)

    def _update_bullets(self, dt):
        for b in self.bullets:
            b.update(dt, self.world_w, self.world_h)
        self._bullet_vs_mobs()
        self._bullet_vs_boss()
        self.bullets = [b for b in self.bullets if b.alive]

    def _bullet_vs_mobs(self):
        for b in self.bullets:
            if not b.alive:
                continue
            for m in self.mobs:
                if not m.alive or m.uid in b.hit_ids:
                    continue
                if math.hypot(b.pos[0] - m.pos[0], b.pos[1] - m.pos[1]) <= b.radius + m.radius:
                    b.hit_ids.add(m.uid)
                    self._hurt_mob(m, b.dmg, m.pos[0], m.pos[1], color=b.color, spark=6)
                    if b.pierce <= 0:
                        b.alive = False
                        break
                    b.pierce -= 1
        self.mobs = [m for m in self.mobs if m.alive]

    def _bullet_vs_boss(self):
        if self.boss is None or not self.boss.alive:
            return
        bx, by = self.boss.pos
        r = self.boss.radius_px
        for b in self.bullets:
            if not b.alive:
                continue
            if math.hypot(b.pos[0] - bx, b.pos[1] - by) <= b.radius + r:
                b.alive = False
                self._damage_boss(b.dmg, color=b.color)

    # ------------------------------------------------------------ 小怪
    def _update_mobs(self, dt):
        self.mob_spawn_timer -= dt
        if self.mob_spawn_timer <= 0:
            interval = self._spawn_interval()
            if self.boss is not None:
                interval *= S.BOSS_MOB_SPAWN_SCALE
            self.mob_spawn_timer = interval
            self._spawn_mob()

        for m in self.mobs:
            m.update(dt, self.snake.pos, self.world_w, self.world_h, mobs=self.mobs)

        cap = S.MOB_MAX_ALIVE
        overflow = len(self.mobs) - cap
        if overflow > 0:
            px, py = self.snake.pos
            self.mobs.sort(key=lambda m: -math.hypot(m.pos[0] - px, m.pos[1] - py))
            self.mobs = self.mobs[overflow:]

    def _handle_mob_contact(self):
        px, py = self.snake.pos
        pr = self.snake.radius
        for m in self.mobs:
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - px, m.pos[1] - py) <= pr + m.radius:
                m.knockback(self.snake.pos, 180.0)
                if self.snake.take_damage(m.atk):
                    self._on_hurt()

    # ------------------------------------------------------------ 道具
    def _update_items(self, dt):
        self.item_spawn_timer -= dt
        if self.item_spawn_timer <= 0:
            self.item_spawn_timer = S.ITEM_SPAWN_INTERVAL
            self._spawn_item(near_player=True)
        mr, pr = self.magnet_radius, self.pickup_radius
        px, py = self.snake.pos
        for d in self.drops:
            if d.update(dt, self.snake.pos, mr, pr):
                d.alive = False
                self._apply_drop(d, px, py)
        self.drops = [d for d in self.drops if d.alive]

    def _apply_drop(self, d, hx, hy):
        self.game.audio.play(f"eat_{d.kind}")
        if d.kind == "exp":
            val = d.exp_value()
            gained = self.snake.gain_exp(val)
            self.score += val * 2
            self._float(f"+{val} EXP", hx, hy, COLOR_EXP)
            if gained:
                self._burst(hx, hy, (255, 226, 140), 24)
                self._float(f"LEVEL {self.snake.level}", hx, hy - self.s(46),
                            COLOR_GOLD, 34)
        elif d.kind == "crystal":
            self.score += 45 * d.tier
            self._float("+能量", hx, hy, (140, 224, 214))
            self._burst(hx, hy, (140, 224, 214), 12)
        elif d.kind == "stardust":
            self.stardust += d.tier
            self.score += 120
            self._float(f"+{d.tier} 星尘", hx, hy, (206, 168, 255))
            self._burst(hx, hy, (206, 168, 255), 16)
        elif d.kind == "heart":
            if self.snake.hp < self.snake.hp_max:
                self.snake.hp += 1
                self._float("+1 HP", hx, hy, COLOR_HP)
            else:
                self.score += 80
                self._float("+80", hx, hy, COLOR_GOLD)
            self._burst(hx, hy, (255, 130, 160), 14)

    # ------------------------------------------------------------ 技能释放
    def cast_skill(self, key):
        sid = self.skills.sid_at_key(key)
        if sid is None:
            return
        cdr = self.stats["cdr"]
        if not self.skills.ready(sid, cdr):
            return
        ev = self.skills.cast(sid, self.snake.pos, cdr)
        if ev:
            self._apply_skill_event(ev)

    def _apply_skill_event(self, ev):
        t = ev["type"]
        px, py = self.snake.pos
        if t == "dash":
            dist = ev["dist"] * self.S
            dx, dy = self.snake.aim_dir
            x2 = min(max(px + dx * dist, self.snake.radius), self.world_w - self.snake.radius)
            y2 = min(max(py + dy * dist, self.snake.radius), self.world_h - self.snake.radius)
            self.game.audio.play("skill_dash")
            self._damage_segment(px, py, x2, y2, ev["dmg"], (255, 150, 190))
            self.snake.pos[0], self.snake.pos[1] = x2, y2
            self._burst(x2, y2, (255, 150, 190), 22)
            self.shake = max(self.shake, 0.3)
            self._float("樱花冲锋", px, py - self.s(50), (255, 150, 190), 30)
        elif t == "spike":
            self.game.audio.play("skill_spike")
            self._float("荆棘尾", px, py - self.s(50), (180, 120, 255), 30)
            self._burst(px, py, (180, 120, 255), 18)
        elif t == "shield":
            self.snake.invincible = max(self.snake.invincible, ev["time"])
            self.game.audio.play("skill_shield")
            self._float("护盾", px, py - self.s(54), (130, 210, 255), 30)
            self._burst(px, py, (130, 210, 255), 24)
        elif t == "thorn":
            scaled = ev["radius"] * self.S
            n = len(ev["positions"])
            for th in self.skills.thorns[-n:]:
                th.radius = scaled
            self.game.audio.play("skill_thorn")
            self._float("蔓生荆棘", px, py - self.s(50), (140, 220, 140), 30)
        elif t == "storm":
            r = ev["radius"] * self.S
            self.game.audio.play("skill_storm")
            self._float("樱花风暴", px, py - self.s(60), (255, 200, 120), 34)
            self._burst(px, py, (255, 200, 120), 48)
            self.shake = max(self.shake, 0.45)
            for m in list(self.mobs):
                if m.alive and math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                    self._hurt_mob(m, ev["dmg"], m.pos[0], m.pos[1],
                                   color=(255, 200, 120), spark=8)
            self.mobs = [m for m in self.mobs if m.alive]
            if self.boss is not None and self.boss.alive:
                bx, by = self.boss.pos
                if math.hypot(bx - px, by - py) <= r + self.boss.radius_px:
                    self._damage_boss(ev["dmg"], color=(255, 200, 120))
        elif t == "bloom":
            n = ev["count"]
            spd = ev["speed"] * self.S
            for i in range(n):
                ang = i * math.tau / n
                self.bullets.append(PlayerBullet(
                    (px, py), (math.cos(ang) * spd, math.sin(ang) * spd),
                    ev["dmg"], self.s(11), life=ev["life"],
                    color=(210, 180, 255), pierce=ev["pierce"]))
            self.game.audio.play("skill_bloom")
            self._float("月华绽放", px, py - self.s(64), (200, 170, 255), 36)
            self._burst(px, py, (200, 170, 255), 40)
            self.shake = max(self.shake, 0.4)

    def _damage_segment(self, x1, y1, x2, y2, dmg, color):
        reach = self.s(18)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if _seg_dist(m.pos[0], m.pos[1], x1, y1, x2, y2) <= m.radius + reach:
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=8)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if _seg_dist(bx, by, x1, y1, x2, y2) <= self.boss.radius_px + reach:
                self._damage_boss(dmg, color=color)

    def _update_skill_fields(self, dt):
        """荆棘尾光环 + 蔓生荆棘地形：每帧对范围内敌人结算伤害。"""
        px, py = self.snake.pos
        if self.skills.spike_active:
            r = self.skills.spike_radius * self.S
            for m in list(self.mobs):
                if not m.alive:
                    continue
                if math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                    if self.skills.spike_ready(m.uid):
                        self.skills.mark_spike(m.uid)
                        self.game.audio.play("skill_spike", throttle=0.12)
                        self._hurt_mob(m, self.skills.spike_dmg, m.pos[0], m.pos[1],
                                       color=(180, 120, 255), spark=6)
            self.mobs = [m for m in self.mobs if m.alive]
            if self.boss is not None and self.boss.alive:
                bx, by = self.boss.pos
                if (math.hypot(bx - px, by - py) <= r + self.boss.radius_px
                        and self.skills.spike_ready("boss")):
                    self.skills.mark_spike("boss")
                    self.game.audio.play("skill_spike", throttle=0.12)
                    self._damage_boss(self.skills.spike_dmg, color=(180, 120, 255))

        if self.skills.thorns:
            for m in list(self.mobs):
                if not m.alive:
                    continue
                dmg = self.skills.thorn_damage_at(m.pos, m.uid, extra=m.radius * 0.5)
                if dmg > 0:
                    self.game.audio.play("skill_thorn", throttle=0.12)
                    self._hurt_mob(m, dmg, m.pos[0], m.pos[1],
                                   color=(140, 220, 140), spark=5)
            self.mobs = [m for m in self.mobs if m.alive]
            if self.boss is not None and self.boss.alive:
                dmg = self.skills.thorn_damage_at(self.boss.pos, "boss",
                                                  extra=self.boss.radius_px * 0.5)
                if dmg > 0:
                    self.game.audio.play("skill_thorn", throttle=0.12)
                    self._damage_boss(dmg, color=(140, 220, 140))

    # ------------------------------------------------------------ 伤害结算
    def _hurt_mob(self, m, dmg, mx, my, color=COLOR_GOLD, spark=0):
        killed = m.take_damage(dmg)
        m.knockback(self.snake.pos, 120.0)
        self._float(f"-{dmg}", mx, my, color, 22)
        if spark:
            self._burst(mx, my, color, spark)
        if killed:
            self._on_mob_killed(m, mx, my)

    def _on_mob_killed(self, m, mx, my):
        self.kills += 1
        self.game.audio.play("kill", throttle=0.04)
        self.score += 60
        self._burst(mx, my, (200, 130, 255), 20)
        self._drop_from_mob(m)

    def _on_hurt(self):
        self.game.audio.play("hurt")
        self.shake = 0.6
        self.flash = 0.5
        px, py = self.snake.pos
        self._float("-HP", px, py - self.s(30), COLOR_DANGER, 32)
        self._burst(px, py, (255, 90, 110), 20)

    def _on_level_up(self, level, gained):
        self.pending_cards += gained
        self.game.audio.play("level_up")
        self.flash = max(self.flash, 0.3)

    # ================================================================ Boss 战
    def _update_boss(self, dt):
        if self.boss_hit_cd > 0:
            self.boss_hit_cd -= dt
        if self.boss_banner > 0:
            self.boss_banner -= dt

        if (self.boss is None and not self.boss_spawned and self.boss_cfg
                and boss_trigger_met(self.boss_cfg, self.elapsed,
                                     self.snake.level, self.kills)):
            self._spawn_boss()

        if self.boss is None:
            return
        if not self.boss.alive:
            self._on_boss_defeated()
            return

        snake_cell = (self.snake.pos[0] / self.CELL, self.snake.pos[1] / self.CELL)
        ctx = {"cols": self.world_cols, "rows": self.world_rows, "cell_px": self.CELL}
        events = self.boss.update(dt, snake_cell, ctx)

        for name in events.get("sfx", []):
            self.game.audio.play(name, throttle=0.05)
        self.projectiles.extend(events.get("bullets", []))
        for _ in range(events.get("summon", 0)):
            self._spawn_mob()
        for eff in events.get("effects", []):
            if eff.get("type") == "slam_burst":
                self._resolve_slam(eff)

        for p in self.projectiles:
            p.update(dt, self.world_cols, self.world_rows, self.CELL)
        self.projectiles = [p for p in self.projectiles if p.alive]

        self._handle_projectile_hits()
        self._handle_boss_contact()

        if not self.boss.alive:
            self._on_boss_defeated()

    def _spawn_boss(self):
        px = self.snake.pos[0]
        cx = self.world_cols - 4 if px < self.world_w / 2 else 3
        cy = self.world_rows / 2
        self.boss = Boss(self.boss_cfg, (cx, cy), lambda: self.CELL)
        self.boss_spawned = True
        self.projectiles = []
        self.boss_banner = 2.6
        self.shake = max(self.shake, 0.6)
        self.flash = max(self.flash, 0.5)
        self.game.audio.play_bgm("boss")
        self.game.audio.play("boss_appear")

    def _resolve_slam(self, eff):
        ex, ey = eff["pos"]
        r = eff["radius_px"]
        self._burst(ex, ey, (255, 200, 120), 30)
        self.shake = max(self.shake, 0.5)
        px, py = self.snake.pos
        if math.hypot(px - ex, py - ey) <= r + self.snake.radius:
            if self.snake.take_damage(1):
                self._on_hurt()

    def _handle_projectile_hits(self):
        if not self.projectiles:
            return
        px, py = self.snake.pos
        pr = self.snake.radius
        for p in self.projectiles:
            if not p.alive:
                continue
            if math.hypot(p.pos[0] - px, p.pos[1] - py) <= p.radius + pr:
                p.alive = False
                self._burst(p.pos[0], p.pos[1], (255, 120, 150), 8)
                if self.snake.take_damage(p.damage):
                    self._on_hurt()
        self.projectiles = [p for p in self.projectiles if p.alive]

    def _handle_boss_contact(self):
        if self.boss is None or not self.boss.alive:
            return
        px, py = self.snake.pos
        bx, by = self.boss.draw_pos
        if math.hypot(px - bx, py - by) > self.boss.radius_px + self.snake.radius:
            return
        if self.boss.charge_active:
            if self.snake.take_damage(1):
                self._on_hurt()
                self.shake = max(self.shake, 0.5)
            return
        if self.boss_hit_cd > 0:
            return
        self.boss_hit_cd = S.BOSS_HIT_CD
        self._damage_boss(S.PLAYER_ATK, color=COLOR_GOLD)

    def _damage_boss(self, amount, color=COLOR_GOLD):
        if self.boss is None or not self.boss.alive:
            return
        bx, by = self.boss.draw_pos
        self.boss.take_damage(amount)
        self.game.audio.play("boss_hit", throttle=0.04)
        self._float(f"-{amount}", bx, by - self.boss.radius_px * 0.6, color, 26)
        self._burst(bx, by, color, 10)

    def _on_boss_defeated(self):
        if self.victory:
            return
        self.victory = True
        self.finished = True
        self.projectiles = []
        bx, by = self.boss.draw_pos
        self._burst(bx, by, (255, 220, 140), 60)
        self.shake = max(self.shake, 0.8)
        self.flash = max(self.flash, 0.6)
        self.score += 1000
        self.game.audio.play("boss_defeat")
        self.game.audio.play("victory")
        self.game.save_manager.add_stardust(self.stardust + S.BOSS_REWARD_STARDUST)
        self.game.save_manager.record_victory(
            self.scene_id, self.score, self.snake.level,
            self.kills, int(self.elapsed))

    # ================================================================ 摄像机
    def _update_cam(self, dt):
        tx = self.snake.pos[0] - self.W / 2
        ty = self.snake.pos[1] - self.H / 2
        k = 1.0 - math.exp(-S.CAM_LERP * dt)
        self.cam[0] += (tx - self.cam[0]) * k
        self.cam[1] += (ty - self.cam[1]) * k
        self._clamp_cam()

    # ================================================================ 特效
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

    def _tick_particles(self, dt):
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 280 * dt * self.S
                yield p

    def _tick_floaters(self, dt):
        for f in self.floaters:
            f["life"] -= dt
            f["y"] -= 48 * dt * self.S
            if f["life"] > 0:
                yield f

    # ================================================================ 升级选卡
    def _roll_cards(self):
        pool = self._card_pool()
        candidates = []
        for c in pool:
            if c.get("type") == "skill":
                sid = c.get("ref")
                if self.skills.has(sid):
                    w = 3 if self.skills.level(sid) < S.SKILL_MAX_LEVEL else 0
                else:
                    w = 6 if self.skills.count < 6 else 0
            else:
                w = 2
            if w > 0:
                candidates.append((c, w))
        result = []
        while len(result) < S.CARD_CHOICES and candidates:
            total = sum(w for _c, w in candidates)
            r = random.random() * total
            acc = 0.0
            for i, (c, w) in enumerate(candidates):
                acc += w
                if r <= acc:
                    result.append(c)
                    candidates.pop(i)
                    break
            else:
                break
        return result

    def _layout_card_rects(self):
        n = len(self.card_overlay)
        cw, ch = self.s(220), self.s(300)
        gap = self.s(28)
        total = cw * n + gap * (n - 1)
        x0 = self.W // 2 - total // 2
        y0 = self.H // 2 - ch // 2
        self.card_rects = [pygame.Rect(x0 + i * (cw + gap), y0, cw, ch)
                           for i in range(n)]

    def _open_card_overlay(self):
        cards = self._roll_cards()
        if not cards:
            self.pending_cards = 0
            self.card_overlay = None
            return
        self.card_overlay = cards
        self._layout_card_rects()

    def _choose_card(self, index):
        if self.card_overlay is None:
            return
        if index < 0 or index >= len(self.card_overlay):
            return
        card = self.card_overlay[index]
        if card.get("type") == "skill":
            sid = card.get("ref")
            self.skills.unlock(sid)
            self.game.audio.play("skill_unlock")
            self.skill_toast.append({"sid": sid, "life": 3.0})
            self.flash = max(self.flash, 0.35)
        else:
            self._apply_passive(card.get("stat"))
            self.game.audio.play("card_pick")
        self.pending_cards = max(0, self.pending_cards - 1)
        self.card_overlay = None
        self.card_rects = []

    def _apply_passive(self, stat):
        px, py = self.snake.pos
        if stat == "atk":
            self.stats["atk"] += S.CARD_ATK_STEP
            self._float("攻击强化", px, py - self.s(50), (255, 120, 120), 28)
        elif stat == "speed":
            self.stats["speed"] += S.CARD_SPEED_STEP
            self._float("移速强化", px, py - self.s(50), (140, 220, 255), 28)
        elif stat == "atkspd":
            self.stats["atkspd"] += S.CARD_ATKSPD_STEP
            self._float("攻速强化", px, py - self.s(50), (255, 200, 120), 28)
        elif stat == "cdr":
            self.stats["cdr"] = min(0.75, self.stats["cdr"] + S.CARD_CDR_STEP)
            self._float("冷却缩减", px, py - self.s(50), (180, 160, 255), 28)
        elif stat == "pickup":
            self.stats["pickup"] += S.CARD_PICKUP_STEP
            self._float("拾取强化", px, py - self.s(50), (200, 160, 255), 28)
        elif stat == "hp":
            self.snake.hp_max += S.CARD_HP_STEP
            self.snake.hp = self.snake.hp_max
            self._float("生命上限 +1", px, py - self.s(50), COLOR_HP, 28)
        self._burst(px, py, (255, 226, 140), 20)

    # ================================================================ 渲染
    def draw(self):
        screen = self.screen
        sx = sy = 0.0
        if self.shake > 0:
            sx = random.uniform(-1, 1) * self.shake * self.s(14)
            sy = random.uniform(-1, 1) * self.shake * self.s(14)

        self._draw_background(screen, sx, sy)
        self._draw_world_border(screen, sx, sy)
        self._draw_thorns(screen, sx, sy)
        self._draw_boss_telegraph(screen, sx, sy)
        self._draw_drops(screen, sx, sy)
        self._draw_mobs(screen, sx, sy)
        self._draw_boss(screen, sx, sy)
        self._draw_bullets(screen, sx, sy)
        self._draw_snake(screen, sx, sy)
        self._draw_projectiles(screen, sx, sy)
        self._draw_particles(screen, sx, sy)
        self._draw_floaters(screen, sx, sy)

        if self.flash > 0:
            veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            veil.fill((255, 70, 100, int(70 * self.flash)))
            screen.blit(veil, (0, 0))

        self._draw_hud()
        self._draw_boss_banner()
        self._draw_skill_toast()

        if self.card_overlay:
            self._draw_card_overlay()
        elif self.finished:
            self._draw_gameover()
        elif self.paused:
            self._draw_pause()

    def _draw_background(self, screen, sx, sy):
        screen.fill(COLOR_BG)
        if (self._bg_surf is None
                or self._bg_surf.get_size() != (self.world_w, self.world_h)):
            base = self.assets.get_image(self.scene_bg)
            self._bg_surf = pygame.transform.smoothscale(
                base, (max(1, self.world_w), max(1, self.world_h)))
        screen.blit(self._bg_surf, (int(self.wx(0, sx)), int(self.wy(0, sy))))
        # 压一层暗纱，让实体在花纹背景上更跳出来
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((14, 12, 22, 70))
        screen.blit(veil, (0, 0))

    def _draw_world_border(self, screen, sx, sy):
        rect = pygame.Rect(int(self.wx(0, sx)), int(self.wy(0, sy)),
                           self.world_w, self.world_h)
        pygame.draw.rect(screen, COLOR_ACCENT_DARK, rect, max(2, self.s(3)))

    def _draw_thorns(self, screen, sx, sy):
        for t in self.skills.thorns:
            cx = self.wx(t.pos[0], sx)
            cy = self.wy(t.pos[1], sy)
            r = max(4, int(t.radius))
            a = int(210 * t.alpha_ratio)
            if a <= 0:
                continue
            layer = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            mid = r + 2
            pygame.draw.circle(layer, (70, 130, 80, int(a * 0.32)), (mid, mid), r)
            for k in range(7):
                ang = k * math.tau / 7
                tip = (mid + math.cos(ang) * r * 0.9, mid + math.sin(ang) * r * 0.9)
                b1 = (mid + math.cos(ang + 2.2) * r * 0.34,
                      mid + math.sin(ang + 2.2) * r * 0.34)
                b2 = (mid + math.cos(ang - 2.2) * r * 0.34,
                      mid + math.sin(ang - 2.2) * r * 0.34)
                pygame.draw.polygon(layer, (150, 220, 150, a), (tip, b1, b2))
            screen.blit(layer, layer.get_rect(center=(int(cx), int(cy))))

    def _draw_drops(self, screen, sx, sy):
        for d in self.drops:
            size = max(8, self.s(d.size))
            img = self.assets.get_scaled(d.asset, height=size)
            x = self.wx(d.draw_pos[0], sx)
            y = self.wy(d.draw_pos[1], sy)
            glow = pygame.Surface((size + self.s(26), size + self.s(26)), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*d.color, 62),
                               (glow.get_width() // 2, glow.get_height() // 2),
                               size // 2 + self.s(10))
            screen.blit(glow, (x - glow.get_width() / 2, y - glow.get_height() / 2))
            screen.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))
            # 品质档标记：高档道具下方点几颗小星
            if d.tier > 1:
                for i in range(d.tier - 1):
                    px = x - (d.tier - 2) * self.s(5) + i * self.s(10)
                    pygame.draw.circle(screen, COLOR_GOLD,
                                       (int(px), int(y + size / 2 + self.s(6))),
                                       max(1, self.s(2)))

    def _draw_mobs(self, screen, sx, sy):
        for m in self.mobs:
            size = max(12, int(m.radius * 2.2))
            img = self.assets.get_scaled("characters/mob_shadow.png", height=size)
            x = self.wx(m.pos[0], sx)
            y = self.wy(m.pos[1], sy)
            bob = math.sin(m.t) * self.s(3)
            rect = img.get_rect(center=(int(x), int(y + bob)))
            sh = pygame.Surface((size, max(3, size // 3)), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 95), sh.get_rect())
            screen.blit(sh, sh.get_rect(center=(rect.centerx, rect.bottom - self.s(4))))
            screen.blit(img, rect)
            if m.hit_flash > 0:
                fl = img.copy()
                fl.fill((255, 255, 255, int(190 * (m.hit_flash / 0.18))),
                        special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(fl, rect)
            if m.hp < m.hp_max:
                bw, bh = max(16, int(size * 0.9)), self.s(5)
                bx = rect.centerx - bw / 2
                by = rect.top - self.s(10)
                pygame.draw.rect(screen, (30, 20, 40), (bx, by, bw, bh), border_radius=2)
                pygame.draw.rect(screen, COLOR_DANGER,
                                 (bx, by, bw * m.hp / m.hp_max, bh), border_radius=2)

    def _draw_bullets(self, screen, sx, sy):
        for b in self.bullets:
            x = self.wx(b.pos[0], sx)
            y = self.wy(b.pos[1], sy)
            r = max(2, int(b.radius))
            glow = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*b.color, 70), (r * 2 + r // 2, r * 2 + r // 2), r * 2)
            screen.blit(glow, glow.get_rect(center=(int(x), int(y))))
            pygame.draw.circle(screen, b.color, (int(x), int(y)), r)
            pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), max(1, r // 2))

    def _draw_snake(self, screen, sx, sy):
        sn = self.snake
        # 闪避拖影
        if sn.dodge_t > 0:
            a = int(120 * (sn.dodge_t / max(1e-6, S.DODGE_TIME)))
            trail = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            pygame.draw.line(trail, (180, 220, 255, a),
                             (self.wx(sn.dodge_from[0], sx), self.wy(sn.dodge_from[1], sy)),
                             (self.wx(sn.pos[0], sx), self.wy(sn.pos[1], sy)),
                             max(2, self.s(6)))
            screen.blit(trail, (0, 0))

        # 装饰尾椎：沿路径反向排布
        pts = sn.sample_tail_points()
        n = max(1, len(pts))
        for i, (tx, ty, ang, scale) in enumerate(pts):
            seg_h = max(6, int(self.CELL * scale))
            img = self.assets.get_rotated(self.char_body, ang + 180)
            w, h = img.get_size()
            if h > 0:
                ratio = seg_h / h
                img = pygame.transform.smoothscale(img, (max(1, int(w * ratio)), seg_h))
            shade = 1.0 - (i / n) * 0.35
            if shade < 0.99:
                img = img.copy()
                img.fill((int(255 * shade), int(255 * shade), int(255 * shade), 255),
                         special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(img, img.get_rect(center=(int(self.wx(tx, sx)),
                                                  int(self.wy(ty, sy)))))
        if pts:
            tx, ty, ang, _ = pts[-1]
            tip = self.assets.get_rotated(self.char_tail, ang)
            th = max(8, int(self.CELL * 0.30))
            if tip.get_height() > 0:
                r = th / tip.get_height()
                tip = pygame.transform.smoothscale(
                    tip, (max(1, int(tip.get_width() * r)), th))
            screen.blit(tip, tip.get_rect(center=(int(self.wx(tx, sx)),
                                                  int(self.wy(ty, sy)))))

        base_x = self.wx(sn.pos[0], sx)
        base_y = self.wy(sn.pos[1], sy)
        # 影子
        sh_w, sh_h = self.s(72), self.s(22)
        sh = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 115), sh.get_rect())
        screen.blit(sh, sh.get_rect(center=(int(base_x), int(base_y + self.s(24)))))

        # 上半身立绘
        sn.bob_t += 0.045
        bob = math.sin(sn.bob_t) * self.s(3)
        alpha = 255
        if sn.invincible > 0 and int(sn.invincible * 14) % 2 == 0:
            alpha = 105
        head = self.assets.get_scaled(self.char_head, height=int(self.CELL * 1.9))
        if sn.aim_dir[0] < 0:
            head = pygame.transform.flip(head, True, False)
        head = head.copy()
        head.set_alpha(alpha)
        screen.blit(head, (base_x - head.get_width() / 2,
                           base_y - head.get_height() * 0.74 + bob))

    def _draw_projectiles(self, screen, sx, sy):
        for p in self.projectiles:
            x = self.wx(p.pos[0], sx)
            y = self.wy(p.pos[1], sy)
            r = max(2, int(p.radius))
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*p.color, 70), (r * 2, r * 2), r * 2)
            screen.blit(glow, glow.get_rect(center=(int(x), int(y))))
            pygame.draw.circle(screen, p.color, (int(x), int(y)), r)
            pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), max(1, r // 2))

    def _draw_particles(self, screen, sx, sy):
        for p in self.particles:
            a = max(0, int(255 * (p["life"] / p["max_life"])))
            r = p["r"]
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p["color"], a), (r, r), r)
            screen.blit(s, (self.wx(p["x"], sx) - r, self.wy(p["y"], sy) - r))

    def _draw_floaters(self, screen, sx, sy):
        for f in self.floaters:
            a = max(0, min(255, int(255 * (f["life"] / 0.9))))
            font = self.assets.get_font(f["size"], bold=True)
            t = font.render(f["text"], True, f["color"])
            t.set_alpha(a)
            screen.blit(t, t.get_rect(center=(int(self.wx(f["x"], sx)),
                                              int(self.wy(f["y"], sy)))))

    def _draw_boss_telegraph(self, screen, sx, sy):
        if self.boss is None:
            return
        for tg in self.boss.telegraphs:
            prog = max(0.0, min(1.0, tg.get("progress", 0.0)))
            a = int(70 + 150 * prog)
            if tg["type"] == "charge":
                x0 = self.wx(tg["from"][0], sx)
                y0 = self.wy(tg["from"][1], sy)
                x1 = self.wx(tg["to"][0], sx)
                y1 = self.wy(tg["to"][1], sy)
                w = max(2, int(tg["width_px"]))
                pygame.draw.line(screen, (255, 90, 90, 255), (x0, y0), (x1, y1), w)
                pygame.draw.line(screen, (255, 220, 120, a), (x0, y0), (x1, y1),
                                 max(1, w // 3))
            elif tg["type"] == "slam":
                cx = self.wx(tg["pos"][0], sx)
                cy = self.wy(tg["pos"][1], sy)
                r = max(2, int(tg["radius_px"] * (0.5 + 0.5 * prog)))
                ring = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(ring, (255, 120, 80, a), (r + 2, r + 2), r, 3)
                pygame.draw.circle(ring, (255, 200, 120, int(a * 0.25)), (r + 2, r + 2), r)
                screen.blit(ring, ring.get_rect(center=(int(cx), int(cy))))

    def _draw_boss(self, screen, sx, sy):
        b = self.boss
        if b is None:
            return
        bx = self.wx(b.draw_pos[0], sx)
        by = self.wy(b.draw_pos[1], sy)
        r = max(6, int(b.radius_px))
        sh = pygame.Surface((r * 2, max(4, int(r / 1.6)) + 2), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 100), sh.get_rect())
        screen.blit(sh, sh.get_rect(center=(int(bx), int(by + r * 0.85))))

        if b.sprite:
            img = self.assets.get_scaled(b.sprite, height=r * 2)
            rect = img.get_rect(center=(int(bx), int(by)))
            screen.blit(img, rect)
            if b.hit_flash > 0:
                fl = img.copy()
                fl.fill((255, 255, 255, int(190 * (b.hit_flash / 0.16))),
                        special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(fl, rect)
            return

        tint = b.tint
        dark = tuple(max(0, int(c * 0.55)) for c in tint)
        light = tuple(min(255, int(c + 60)) for c in tint)
        spike = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        sc = r + 4
        n_sp = 10
        for k in range(n_sp):
            ang = k * math.tau / n_sp + b.t * 0.15
            tip = (sc + math.cos(ang) * (r + 4), sc + math.sin(ang) * (r + 4))
            b1 = (sc + math.cos(ang + 0.28) * r * 0.85,
                  sc + math.sin(ang + 0.28) * r * 0.85)
            b2 = (sc + math.cos(ang - 0.28) * r * 0.85,
                  sc + math.sin(ang - 0.28) * r * 0.85)
            pygame.draw.polygon(spike, (*dark, 255), (tip, b1, b2))
        screen.blit(spike, spike.get_rect(center=(int(bx), int(by))))
        pygame.draw.circle(screen, tint, (int(bx), int(by)), r)
        pygame.draw.circle(screen, light, (int(bx), int(by)), r, max(2, r // 8))
        pygame.draw.circle(screen, (*light, 120),
                           (int(bx - r * 0.25), int(by - r * 0.3)), max(2, int(r * 0.3)))
        ex = math.cos(b.t * 0.5) * r * 0.2
        ey = math.sin(b.t * 0.5) * r * 0.2
        for sgn in (-1, 1):
            cx = int(bx + ex + sgn * r * 0.32)
            cy = int(by + ey - r * 0.1)
            pygame.draw.circle(screen, (255, 255, 255), (cx, cy), max(2, int(r * 0.18)))
            pygame.draw.circle(screen, (30, 10, 20), (cx, cy), max(1, int(r * 0.09)))
        if b.hit_flash > 0:
            fl = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            aa = int(200 * (b.hit_flash / 0.16))
            pygame.draw.circle(fl, (255, 255, 255, aa), (r + 2, r + 2), r)
            screen.blit(fl, fl.get_rect(center=(int(bx), int(by))))

    # ================================================================ HUD
    def _draw_hud(self):
        screen = self.screen
        self._draw_topleft_status(screen)
        self._draw_topcenter_info(screen)
        self._draw_minimap(screen)
        self._draw_skill_bar(screen)
        self._draw_dodge_indicator(screen)
        self._draw_boss_bar()

    def _draw_topleft_status(self, screen):
        sn = self.snake
        pad = self.s(12)
        x, y = pad, pad
        panel_w = self.s(280)
        t = self.f_sub.render(self.snake_name, True, COLOR_ACCENT)
        screen.blit(t, (x, y))
        lv = self.f_sub.render(f"Lv.{sn.level}", True, COLOR_GOLD)
        screen.blit(lv, (x + panel_w - lv.get_width(), y))
        y += t.get_height() + self.s(4)

        # 生命（心）
        r = self.s(11)
        step = min(self.s(34), panel_w / max(1, sn.hp_max))
        for i in range(sn.hp_max):
            color = COLOR_HP if i < sn.hp else (56, 48, 66)
            cx = int(x + r + i * step)
            pygame.draw.circle(screen, color, (cx, int(y + r)), r)
            pygame.draw.circle(screen, (255, 255, 255), (cx, int(y + r)), r, 1)
        y += r * 2 + self.s(6)

        # 经验条
        bw = panel_w
        bh = self.s(12)
        pygame.draw.rect(screen, (24, 20, 34), (x, y, bw, bh), border_radius=bh // 2)
        need = sn.exp_needed()
        ratio = min(1.0, sn.exp / need) if need else 1.0
        if ratio > 0:
            pygame.draw.rect(screen, COLOR_EXP, (x, y, int(bw * ratio), bh),
                             border_radius=bh // 2)
        pygame.draw.rect(screen, (90, 80, 110), (x, y, bw, bh), 1, border_radius=bh // 2)
        y += bh + self.s(2)
        t = self.f_tiny.render(f"EXP {sn.exp} / {need}   攻击 {self.player_damage}",
                               True, COLOR_TEXT_DIM)
        screen.blit(t, (x, y))

    def _draw_topcenter_info(self, screen):
        txt = f"{int(self.elapsed)}s    击杀 {self.kills}    得分 {self.score}"
        t = self.f_body.render(txt, True, COLOR_TEXT)
        x = self.W // 2 - t.get_width() // 2
        bg = pygame.Surface((t.get_width() + self.s(24), t.get_height() + self.s(8)),
                             pygame.SRCALPHA)
        bg.fill((*COLOR_BG_LIGHT, 150))
        screen.blit(bg, (x - self.s(12), self.s(8)))
        screen.blit(t, (x, self.s(12)))
        tp = self._time_pressure()
        if tp > 1.05:
            w = self.f_tiny.render(f"压力 x{tp:.1f}", True, COLOR_DANGER)
            screen.blit(w, (self.W // 2 - w.get_width() // 2,
                            self.s(12) + t.get_height() + self.s(4)))

    def _draw_minimap(self, screen):
        pad = self.s(12)
        mw = self.s(180)
        mh = max(1, int(mw * self.world_h / max(1, self.world_w)))
        mx = self.W - mw - pad
        my = pad + self.s(46)
        bg = pygame.Surface((mw, mh), pygame.SRCALPHA)
        bg.fill((16, 14, 26, 170))
        screen.blit(bg, (mx, my))
        pygame.draw.rect(screen, COLOR_ACCENT_DARK, (mx, my, mw, mh), 2)
        kx = mw / max(1, self.world_w)
        ky = mh / max(1, self.world_h)
        # 摄像机可视区
        view = pygame.Rect(mx + self.cam[0] * kx, my + self.cam[1] * ky,
                           self.W * kx, self.H * ky)
        pygame.draw.rect(screen, (255, 255, 255, 90), view, 1)
        # 道具
        for d in self.drops:
            pygame.draw.circle(screen, d.color,
                               (int(mx + d.pos[0] * kx), int(my + d.pos[1] * ky)),
                               max(1, self.s(2)))
        # 小怪
        for m in self.mobs:
            pygame.draw.circle(screen, COLOR_DANGER,
                               (int(mx + m.pos[0] * kx), int(my + m.pos[1] * ky)),
                               max(1, self.s(2)))
        # Boss
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            pygame.draw.circle(screen, COLOR_GOLD,
                               (int(mx + bx * kx), int(my + by * ky)), max(2, self.s(4)))
        # 玩家
        pygame.draw.circle(screen, (120, 255, 160),
                           (int(mx + self.snake.pos[0] * kx),
                            int(my + self.snake.pos[1] * ky)), max(2, self.s(3)))
        fps = self.game.clock.get_fps()
        color = COLOR_GOOD if fps > 55 else (COLOR_GOLD if fps > 40 else COLOR_DANGER)
        t = self.f_tiny.render(f"{fps:.0f} FPS", True, color)
        screen.blit(t, (mx + mw - t.get_width(), my + mh + self.s(2)))

    def _draw_skill_bar(self, screen):
        slot = self.s(58)
        gap = self.s(8)
        n = 6
        total = slot * n + gap * (n - 1)
        x0 = self.W // 2 - total // 2
        y0 = self.H - slot - self.s(16)
        cdr = self.stats["cdr"]
        for i in range(n):
            key = i + 1
            sid = self.skills.sid_at_key(key)
            rect = pygame.Rect(x0 + i * (slot + gap), y0, slot, slot)
            pygame.draw.rect(screen, (26, 22, 38, 210), rect, border_radius=self.s(8))
            if sid is None:
                pygame.draw.rect(screen, (70, 66, 86), rect, 2, border_radius=self.s(8))
                num = self.f_small.render(str(key), True, (110, 106, 126))
                screen.blit(num, num.get_rect(center=rect.center))
                continue
            info = skill_info(sid)
            color = info["color"]
            pygame.draw.rect(screen, color, rect, 2, border_radius=self.s(8))
            self._draw_skill_icon(screen, sid, rect.centerx, rect.centery - self.s(4),
                                  color, slot * 0.62)
            # 冷却遮罩（从顶部往下盖，就绪时不盖）
            ratio = self.skills.cd_ratio(sid, cdr)
            if ratio < 1.0:
                cover = pygame.Surface((slot, int(slot * (1.0 - ratio))), pygame.SRCALPHA)
                cover.fill((10, 8, 16, 165))
                screen.blit(cover, (rect.x, rect.y))
                left = self.skills.cooldown_left(sid)
                if left > 0.05:
                    cd = self.f_tiny.render(f"{left:.0f}", True, COLOR_TEXT)
                    screen.blit(cd, cd.get_rect(center=rect.center))
            # 键位数字
            num = self.f_tiny.render(str(key), True, COLOR_TEXT_DIM)
            screen.blit(num, (rect.x + self.s(4), rect.y + self.s(2)))
            # 等级小点
            lv = self.skills.level(sid)
            for k in range(lv):
                pygame.draw.circle(screen, COLOR_GOLD,
                                   (rect.x + slot - self.s(8) - k * self.s(7),
                                    rect.bottom - self.s(7)), max(1, self.s(2)))

    def _draw_dodge_indicator(self, screen):
        sn = self.snake
        pad = self.s(16)
        x = pad
        y = self.H - self.s(52)
        w, h = self.s(120), self.s(12)
        ready = sn.dodge_cd <= 0 and sn.dodge_t <= 0
        ratio = 1.0 if ready else max(0.0, 1.0 - sn.dodge_cd / max(1e-6, S.DODGE_CD))
        label = self.f_tiny.render("闪避 (左键)", True,
                                   COLOR_GOOD if ready else COLOR_TEXT_DIM)
        screen.blit(label, (x, y - label.get_height() - self.s(2)))
        pygame.draw.rect(screen, (24, 20, 34), (x, y, w, h), border_radius=h // 2)
        col = COLOR_GOOD if ready else (120, 180, 220)
        if ratio > 0:
            pygame.draw.rect(screen, col, (x, y, int(w * ratio), h), border_radius=h // 2)
        pygame.draw.rect(screen, (90, 80, 110), (x, y, w, h), 1, border_radius=h // 2)

    def _draw_skill_icon(self, screen, sid, cx, cy, color, size=None):
        r = (size or self.s(44)) * 0.5
        cx, cy = int(cx), int(cy)
        if sid == "dash":
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
        elif sid == "bloom":
            for k in range(8):
                a = k * math.tau / 8
                pygame.draw.line(screen, color, (cx, cy),
                                 (cx + math.cos(a) * r * 0.9, cy + math.sin(a) * r * 0.9),
                                 max(1, int(r * 0.16)))
            pygame.draw.circle(screen, (255, 250, 235), (cx, cy), max(1, int(r * 0.28)))
        else:
            # 被动卡 / 未知图标：菱形宝石
            k = r * 0.75
            pygame.draw.polygon(screen, color, [(cx, cy - k), (cx + k, cy),
                                                (cx, cy + k), (cx - k, cy)])

    def _draw_skill_toast(self):
        if not self.skill_toast:
            return
        screen = self.screen
        for i, item in enumerate(self.skill_toast[:3]):
            info = skill_info(item["sid"])
            life = item["life"]
            if life > 2.75:
                a = (3.0 - life) / 0.25
            elif life < 0.5:
                a = life / 0.5
            else:
                a = 1.0
            a = max(0.0, min(1.0, a)) * 255
            w, h = self.s(430), self.s(70)
            x = self.W // 2 - w // 2
            y = self.s(70) + i * (h + self.s(10))
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            panel.fill((*COLOR_BG_LIGHT, int(220 * a / 255)))
            pygame.draw.rect(panel, (*info["color"], int(a)), panel.get_rect(),
                             self.s(3), border_radius=self.s(12))
            screen.blit(panel, (x, y))
            pad = self.s(14)
            t1 = self.f_tiny.render("获得/强化技能", True, COLOR_TEXT_DIM)
            t1.set_alpha(int(a))
            screen.blit(t1, (x + pad, y + pad))
            self._draw_skill_icon(screen, item["sid"], x + pad + self.s(10),
                                  y + h - self.s(24), info["color"], self.s(40))
            t2 = self.f_body.render(info["name"], True, info["color"])
            t2.set_alpha(int(a))
            screen.blit(t2, (x + pad + self.s(36),
                             y + h - self.s(24) - t2.get_height() / 2))

    def _draw_boss_bar(self):
        b = self.boss
        if b is None:
            return
        screen = self.screen
        w = int(self.W * 0.6)
        h = self.s(18)
        x = self.W // 2 - w // 2
        y = self.s(52)
        bar = pygame.Surface((w, h), pygame.SRCALPHA)
        bar.fill((20, 14, 26, 210))
        screen.blit(bar, (x, y))
        ratio = b.hp_ratio()
        fill_w = int(w * ratio)
        if fill_w > 0:
            grad = pygame.Surface((fill_w, h), pygame.SRCALPHA)
            grad.fill((*b.tint, 235))
            screen.blit(grad, (x, y))
        pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(x, y, w, h), 2,
                         border_radius=self.s(4))
        for ph in b.phases:
            below = float(ph.get("below", 1.0))
            if 0.0 < below < 1.0:
                mx = x + int(w * below)
                pygame.draw.line(screen, (255, 255, 255), (mx, y), (mx, y + h), 1)
        name = self.f_small.render(b.name, True, COLOR_TEXT)
        screen.blit(name, (x, y - name.get_height() - self.s(2)))
        hp_txt = self.f_tiny.render(f"{int(b.hp)} / {b.hp_max}", True, COLOR_TEXT_DIM)
        screen.blit(hp_txt, (x + w - hp_txt.get_width(),
                             y - hp_txt.get_height() - self.s(2)))

    def _draw_boss_banner(self):
        if self.boss_banner <= 0 or self.boss is None:
            return
        screen = self.screen
        total = 2.6
        life = self.boss_banner
        if life > total - 0.4:
            a = (total - life) / 0.4
        elif life < 0.6:
            a = life / 0.6
        else:
            a = 1.0
        a = max(0.0, min(1.0, a))
        cx = self.W // 2
        cy = int(self.H * 0.32)
        tint = self.boss.tint
        band = pygame.Surface((int(self.W * 0.6), self.s(64)), pygame.SRCALPHA)
        band.fill((10, 8, 16, int(190 * a)))
        pygame.draw.rect(band, (*tint, int(230 * a)), band.get_rect(), self.s(3),
                         border_radius=self.s(8))
        screen.blit(band, band.get_rect(center=(cx, cy)))
        warn = self.f_tiny.render("强敌登场", True, (*tint,))
        warn.set_alpha(int(255 * a))
        screen.blit(warn, warn.get_rect(center=(cx, cy - self.s(16))))
        nm = self.f_sub.render(self.boss.name, True, COLOR_TEXT)
        nm.set_alpha(int(255 * a))
        screen.blit(nm, nm.get_rect(center=(cx, cy + self.s(12))))

    # ================================================================ 选卡界面
    def _draw_card_overlay(self):
        screen = self.screen
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((8, 6, 14, 200))
        screen.blit(veil, (0, 0))
        title = self.f_title.render("选择强化", True, COLOR_GOLD)
        screen.blit(title, title.get_rect(center=(self.W // 2,
                                                  self.card_rects[0].top - self.s(60))))
        hint = self.f_small.render("鼠标点击 或 按 1 / 2 / 3 选择", True, COLOR_TEXT_DIM)
        screen.blit(hint, hint.get_rect(center=(self.W // 2,
                                                self.card_rects[0].bottom + self.s(40))))
        for i, card in enumerate(self.card_overlay):
            rect = self.card_rects[i]
            color = tuple(card.get("color", [255, 255, 255])[:3])
            panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            panel.fill((*COLOR_BG_LIGHT, 235))
            screen.blit(panel, rect.topleft)
            pygame.draw.rect(screen, color, rect, self.s(3), border_radius=self.s(14))
            # 图标
            icon_id = card.get("ref") if card.get("type") == "skill" else card.get("icon")
            self._draw_skill_icon(screen, icon_id, rect.centerx,
                                  rect.top + self.s(84), color, self.s(90))
            # 类型标签
            tag = "技能" if card.get("type") == "skill" else "被动"
            tt = self.f_tiny.render(tag, True, color)
            screen.blit(tt, tt.get_rect(center=(rect.centerx, rect.top + self.s(24))))
            # 名称
            nm = self.f_body.render(card.get("name", ""), True, COLOR_TEXT)
            screen.blit(nm, nm.get_rect(center=(rect.centerx, rect.top + self.s(156))))
            # 描述（自动换行）
            self._draw_wrapped(screen, card.get("desc", ""), self.f_small,
                               COLOR_TEXT_DIM, rect.centerx, rect.top + self.s(196),
                               rect.width - self.s(32))
            # 序号
            idx = self.f_small.render(str(i + 1), True, COLOR_TEXT_DIM)
            screen.blit(idx, (rect.x + self.s(12), rect.y + self.s(10)))

    def _draw_wrapped(self, screen, text, font, color, cx, top_y, max_w):
        lines = []
        cur = ""
        for ch in text:
            if font.size(cur + ch)[0] <= max_w:
                cur += ch
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
        y = top_y
        for ln in lines[:4]:
            t = font.render(ln, True, color)
            screen.blit(t, t.get_rect(midtop=(cx, y)))
            y += t.get_height() + self.s(2)

    # ================================================================ 结算
    def _draw_gameover(self):
        screen = self.screen
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((10, 8, 16, 195))
        screen.blit(veil, (0, 0))
        cx, cy = self.W // 2, self.H // 2
        title = "胜利!" if self.victory else "战斗结束"
        title_color = COLOR_GOLD if self.victory else COLOR_ACCENT
        t = self.f_title.render(title, True, title_color)
        screen.blit(t, t.get_rect(center=(cx, cy - self.s(250))))
        rows = [
            ("最终得分", f"{self.score}", COLOR_TEXT),
            ("抵达等级", f"Lv.{self.snake.level}", COLOR_GOLD),
            ("获得技能", f"{self.skills.count} / {len(all_skill_ids())}", (255, 150, 190)),
            ("击杀小怪", f"{self.kills}", COLOR_DANGER),
            ("存活时间", f"{int(self.elapsed)} 秒", (120, 210, 200)),
            ("获得星尘", f"{self.stardust}", (206, 168, 255)),
        ]
        if self.victory:
            boss_name = self.boss.name if self.boss else "Boss"
            rows.insert(0, ("击败 Boss", boss_name, title_color))
            rows.append(("通关奖励", f"+{S.BOSS_REWARD_STARDUST} 星尘", (206, 168, 255)))
        y = cy - self.s(180 if self.victory else 140)
        for label, value, color in rows:
            lt = self.f_body.render(label, True, COLOR_TEXT_DIM)
            vt = self.f_body.render(value, True, color)
            screen.blit(lt, lt.get_rect(midright=(cx - self.s(24), int(y))))
            screen.blit(vt, vt.get_rect(midleft=(cx + self.s(24), int(y))))
            y += self.s(50)
        t = self.f_small.render("按 R 再来一局    ·    按 ESC 返回主菜单", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(cx, cy + self.s(220))))

    # ================================================================ 暂停
    def _toggle_pause(self):
        self.paused = not self.paused
        if not self.paused:
            self.game.flush_audio()

    def _pause_vol_layout(self):
        cx = self.W // 2
        cy = self.H // 2 - self.s(92)
        w, h = self.s(240), self.s(50)
        bgm_rect = pygame.Rect(0, 0, w, h)
        bgm_rect.center = (cx - self.s(150), cy)
        sfx_rect = pygame.Rect(0, 0, w, h)
        sfx_rect.center = (cx + self.s(150), cy)
        return bgm_rect, sfx_rect

    def _draw_pause(self):
        screen = self.screen
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((10, 8, 16, 190))
        screen.blit(veil, (0, 0))
        cx, cy = self.W // 2, self.H // 2
        t = self.f_title.render("已暂停", True, COLOR_ACCENT)
        screen.blit(t, t.get_rect(center=(cx, cy - self.s(150))))
        a = self.game.audio
        bgm = int(round(a.bgm_volume * 100))
        sfx = int(round(a.sfx_volume * 100))
        bgm_rect, sfx_rect = self._pause_vol_layout()
        for rect, label, val, key in (
            (bgm_rect, "音乐", bgm, "bgm"),
            (sfx_rect, "音效", sfx, "sfx"),
        ):
            focused = (a.volume_focus == key)
            color = COLOR_ACCENT if focused else COLOR_TEXT
            txt = self.f_body.render(f"{label} {val}", True, color)
            screen.blit(txt, txt.get_rect(center=rect.center))
            if focused:
                ul = pygame.Rect(0, 0, rect.width - self.s(70), 2)
                ul.center = (rect.centerx, rect.bottom - self.s(8))
                pygame.draw.rect(screen, COLOR_ACCENT, ul)
        hint = self.f_small.render(
            "鼠标点选 音乐/音效 后：↑/→ 增大  ↓/← 减小（±10，长按连调）", True,
            COLOR_TEXT_DIM)
        screen.blit(hint, hint.get_rect(center=(cx, cy + self.s(150))))
        self.resume_btn.draw(screen)
        self.restart_btn.draw(screen)
        self.quit_btn.draw(screen)

    # ================================================================ 输入
    def handle_events(self, events):
        # ---- 选卡态：鼠标点击 / 数字键选卡 ----
        if self.card_overlay:
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, r in enumerate(self.card_rects):
                        if r.collidepoint(event.pos):
                            self._choose_card(i)
                            return
                elif event.type == pygame.KEYDOWN and event.key in _NUM_KEYS:
                    idx = _NUM_KEYS[event.key] - 1
                    if idx < len(self.card_overlay):
                        self._choose_card(idx)
                        return
            return

        # ---- 结算态：R 重开 / ESC 回主菜单 ----
        if self.finished:
            for event in events:
                if event.type != pygame.KEYDOWN:
                    continue
                if event.key == pygame.K_ESCAPE:
                    self.game.change_scene("main_menu")
                    return
                if event.key == pygame.K_r:
                    self.reset()
            return

        # ---- 暂停态：鼠标点按钮/音量块 + ESC/P 继续 ----
        if self.paused:
            bgm_rect, sfx_rect = self._pause_vol_layout()
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                    self._toggle_pause()
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if bgm_rect.collidepoint(event.pos):
                        self.game.audio.volume_focus = "bgm"
                    elif sfx_rect.collidepoint(event.pos):
                        self.game.audio.volume_focus = "sfx"
                self.resume_btn.handle_event(event)
                self.restart_btn.handle_event(event)
                self.quit_btn.handle_event(event)
            return

        # ---- 进行中：左键闪避 / 1-6 技能 / ESC-P 暂停（移动靠轮询）----
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.try_dodge(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_p):
                    self._toggle_pause()
                    return
                if event.key in _NUM_KEYS:
                    self.cast_skill(_NUM_KEYS[event.key])
