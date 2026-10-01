# -*- coding: utf-8 -*-
"""
scenes/battle.py —— 战斗场景

一局的完整过程都在这里：
    蛇娘移动 → 捡掉落物 → 升级 / 回血 / 攒星尘 → 小怪越来越多越来越硬 → 撞怪扣血 → 结算

按你的设定：
    · 蛇身长度固定，吃东西不变长
    · 成长走「等级 → 伤害提升」，技能后续接入
    · 难度靠小怪变强（血厚）+ 变多（刷得快）
"""

import math
import random

import pygame

from core.scene import Scene
from game_logic.entities import Drop, Mob, SnakeGirl
from settings import (
    COLOR_ACCENT, COLOR_ACCENT_DARK, COLOR_BG, COLOR_BG_LIGHT, COLOR_DANGER,
    COLOR_EXP, COLOR_GOLD, COLOR_GOOD, COLOR_HP, COLOR_TEXT, COLOR_TEXT_DIM,
    FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_SUBTITLE, FONT_SIZE_TITLE,
    GRID_COLS, GRID_COLOR, GRID_ROWS, HP_MAX, RENDER_HEIGHT, RENDER_WIDTH,
    CELL_SIZE,
)

GRID_PX_W = GRID_COLS * CELL_SIZE
GRID_PX_H = GRID_ROWS * CELL_SIZE


class BattleScene(Scene):
    """战斗场景"""

    def enter(self):
        self.assets = self.game.assets
        self.f_tiny = self.assets.get_font(FONT_SIZE_SMALL - 2)
        self.f_small = self.assets.get_font(FONT_SIZE_SMALL)
        self.f_body = self.assets.get_font(FONT_SIZE_BODY)
        self.f_sub = self.assets.get_font(FONT_SIZE_SUBTITLE)
        self.f_title = self.assets.get_font(FONT_SIZE_TITLE, bold=True)

        self.offset_x = (RENDER_WIDTH - GRID_PX_W) // 2
        self.offset_y = (RENDER_HEIGHT - GRID_PX_H) // 2

        self.reset()

    def exit(self):
        pass

    # ---------------------------------------------------------------- 重置
    def reset(self):
        self.snake = SnakeGirl("sakura", start_cell=(6, GRID_ROWS // 2), direction=(1, 0))
        self.snake.facing_update()

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

    def _spawn_mob(self):
        """刷小怪——难度成长的所有通道都在这里"""
        from settings import (MOB_HP_GROWTH, MOB_HP_MAX_MULT,
                              MOB_SPAWN_MIN)
        hp_mult = min(MOB_HP_MAX_MULT, 1.0 + MOB_HP_GROWTH * (self.elapsed / 30.0))
        speed_mult = min(1.7, 1.0 + 0.05 * (self.elapsed / 30.0))
        # 追击欲望随时间上升：前期散步，后期成群追人
        chase = min(0.75, 0.10 + 0.16 * (self.elapsed / 30.0))

        cells = self._free_cells()
        sx, sy = self.snake.grid_pos
        far = [c for c in cells if abs(c[0] - sx) + abs(c[1] - sy) > 4]
        cells = far or cells
        if not cells:
            return
        self.mobs.append(Mob(random.choice(cells), hp_mult=hp_mult,
                             speed_mult=speed_mult, chase=chase))

    def _spawn_interval(self):
        from settings import MOB_SPAWN_INTERVAL, MOB_SPAWN_MIN, MOB_SPAWN_RAMP
        v = MOB_SPAWN_INTERVAL - MOB_SPAWN_RAMP * (self.elapsed / 10.0) - self.kills * 0.012
        return max(MOB_SPAWN_MIN, v)

    # ---------------------------------------------------------------- 更新
    def update(self, dt):
        if self.finished:
            return

        self.elapsed += dt
        self.snake.update(dt, GRID_COLS, GRID_ROWS)
        self.snake.facing_update()
        self.snake.update_path(dt)

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
        from settings import MOB_MAX_ALIVE
        overflow = len(self.mobs) - MOB_MAX_ALIVE
        if overflow > 0:
            # 从离玩家最远的开始移除，界面上的感觉是"怪走远了"
            sx, sy = self.snake.grid_pos
            self.mobs.sort(key=lambda m: -(abs(m.cell[0] - sx) + abs(m.cell[1] - sy)))
            self.mobs = self.mobs[overflow:]

        if len(self.drops) < 5:
            self._spawn_drop()

        self._handle_pickups()
        self._handle_mob_collision()
        self._handle_self_collision()

        self.shake = max(0.0, self.shake - dt * 3.2)
        self.flash = max(0.0, self.flash - dt * 2.4)

        self.particles = [p for p in self._tick_particles(dt)]
        self.floaters = [f for f in self._tick_floaters(dt)]

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
        hx = head[0] * CELL_SIZE + CELL_SIZE / 2
        hy = head[1] * CELL_SIZE + CELL_SIZE / 2

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
                self.kills += 1
                self.score += 200
                self.shake = 0.5
                self._burst(mx, my, (200, 130, 255), 26)
                self._float("+200", mx, my, COLOR_GOLD)
                r = random.random()
                mc = (round(m.cell[0]), round(m.cell[1]))
                self.drops.append(Drop("stardust" if r < 0.55 else ("exp" if r < 0.9 else "heart"), mc))
            else:
                self.shake = max(self.shake, 0.22)
                self._burst(mx, my, (255, 140, 180), 10)

            if self.snake.take_damage(MOB_TOUCH_DAMAGE):
                self._on_hurt()

        self.mobs = [m for m in self.mobs if m.alive]

    def _handle_self_collision(self):
        if self.snake.is_self_hit() and self.snake.take_damage(1):
            self._on_hurt()

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
            sp = random.uniform(70, 330)
            self.particles.append({
                "x": x, "y": y,
                "vx": math.cos(a) * sp, "vy": math.sin(a) * sp - 60,
                "life": random.uniform(0.28, 0.7), "max_life": 0.7,
                "color": color, "r": random.randint(2, 5),
            })

    def _float(self, text, x, y, color, size=26):
        self.floaters.append({"text": text, "x": x, "y": y,
                              "color": color, "life": 0.9, "size": size})

    # ================================================================ 渲染
    def draw(self):
        screen = self.screen
        sx = sy = 0.0
        if self.shake > 0:
            sx = random.uniform(-1, 1) * self.shake * 14
            sy = random.uniform(-1, 1) * self.shake * 14

        self._draw_background(screen, sx, sy)
        self._draw_drops(screen, sx, sy)
        self._draw_mobs(screen, sx, sy)
        self._draw_snake(screen, sx, sy)
        self._draw_particles(screen, sx, sy)
        self._draw_floaters(screen, sx, sy)
        self._draw_hud()

        if self.flash > 0:
            veil = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT), pygame.SRCALPHA)
            veil.fill((255, 70, 100, int(70 * self.flash)))
            screen.blit(veil, (0, 0))

        if self.finished:
            self._draw_gameover()

    def _draw_background(self, screen, sx, sy):
        screen.fill(COLOR_BG)
        # 背景铺满整个画面（不只网格区），避免两侧留黑边
        bg = self.assets.get_scaled("backgrounds/campus_garden.png",
                                    width=RENDER_WIDTH)
        by = -(bg.get_height() - RENDER_HEIGHT) / 2
        screen.blit(bg, (sx * 0.3, by + sy * 0.3))

        veil = pygame.Surface((GRID_PX_W, GRID_PX_H), pygame.SRCALPHA)
        veil.fill((14, 12, 22, 96))
        screen.blit(veil, (self.offset_x, self.offset_y))

        grid = pygame.Surface((GRID_PX_W, GRID_PX_H), pygame.SRCALPHA)
        for x in range(GRID_COLS + 1):
            pygame.draw.line(grid, (*GRID_COLOR, 95),
                             (x * CELL_SIZE, 0), (x * CELL_SIZE, GRID_PX_H))
        for y in range(GRID_ROWS + 1):
            pygame.draw.line(grid, (*GRID_COLOR, 95),
                             (0, y * CELL_SIZE), (GRID_PX_W, y * CELL_SIZE))
        screen.blit(grid, (self.offset_x, self.offset_y))

        pygame.draw.rect(screen, COLOR_ACCENT_DARK,
                         pygame.Rect(self.offset_x - 2, self.offset_y - 2,
                                     GRID_PX_W + 4, GRID_PX_H + 4), 3, border_radius=4)

    def _draw_drops(self, screen, sx, sy):
        for d in self.drops:
            img = self.assets.get_scaled(d.asset, height=d.size)
            x, y = d.draw_pos
            glow = pygame.Surface((d.size + 26, d.size + 26), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*d.color, 62),
                               (glow.get_width() // 2, glow.get_height() // 2),
                               d.size // 2 + 10)
            screen.blit(glow, (self.offset_x + x - glow.get_width() / 2 + sx,
                               self.offset_y + y - glow.get_height() / 2 + sy))
            screen.blit(img, (self.offset_x + x - img.get_width() / 2 + sx,
                              self.offset_y + y - img.get_height() / 2 + sy))

    def _draw_mobs(self, screen, sx, sy):
        for m in self.mobs:
            size = 52
            img = self.assets.get_scaled("characters/mob_shadow.png", height=size)
            x, y = m.draw_pos
            bob = math.sin(m.t) * 3
            rect = img.get_rect(center=(self.offset_x + x + sx,
                                        self.offset_y + y + bob + sy))
            sh = pygame.Surface((size, size // 3), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 95), sh.get_rect())
            screen.blit(sh, sh.get_rect(center=(rect.centerx, rect.bottom - 4)))
            screen.blit(img, rect)

            if m.hit_flash > 0:
                fl = img.copy()
                fl.fill((255, 255, 255, int(190 * (m.hit_flash / 0.18))),
                        special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(fl, rect)

            if m.hp < m.hp_max:
                bw, bh = 44, 5
                bx = rect.centerx - bw / 2
                by = rect.top - 12
                pygame.draw.rect(screen, (30, 20, 40), (bx, by, bw, bh), border_radius=2)
                pygame.draw.rect(screen, COLOR_DANGER,
                                 (bx, by, bw * m.hp / m.hp_max, bh), border_radius=2)

    def _draw_snake(self, screen, sx, sy):
        sn = self.snake
        px, py = sn.draw_pos
        base_x = self.offset_x + px + sx
        base_y = self.offset_y + py + sy

        # ----- 下半身：沿路径摆尾椎 -----
        # 注意：body_seg 贴图是「左粗右细」，而这里 ang 表示"从尾巴指向头"的方向，
        # 所以实际贴图角度要加 180 度，让粗的那端朝着身体前方。
        pts = sn.sample_tail_points()
        n = max(1, len(pts))
        for i, (tx, ty, ang, scale) in enumerate(pts):
            seg_h = max(6, int(CELL_SIZE * scale))
            img = self.assets.get_rotated("characters/sakura/body_seg.png", ang + 180)
            w, h = img.get_size()
            ratio = seg_h / h
            img = pygame.transform.smoothscale(img, (max(1, int(w * ratio)), seg_h))
            shade = 1.0 - (i / n) * 0.35
            if shade < 0.99:
                img.fill((int(255 * shade), int(255 * shade), int(255 * shade), 255),
                         special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(img, img.get_rect(center=(self.offset_x + tx + sx,
                                                  self.offset_y + ty + sy)))

        if pts:
            tx, ty, ang, _ = pts[-1]
            tip = self.assets.get_rotated("characters/sakura/tail_tip.png", ang)
            th = max(8, int(CELL_SIZE * 0.30))
            r = th / tip.get_height()
            tip = pygame.transform.smoothscale(tip, (max(1, int(tip.get_width() * r)), th))
            screen.blit(tip, tip.get_rect(center=(self.offset_x + tx + sx,
                                                  self.offset_y + ty + sy)))

        # ----- 影子 -----
        sh = pygame.Surface((72, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 115), sh.get_rect())
        screen.blit(sh, sh.get_rect(center=(base_x, base_y + 24)))

        # ----- 上半身：人物立绘 -----
        sn.bob_t += 0.045
        bob = math.sin(sn.bob_t) * 3
        alpha = 255
        if sn.invincible > 0 and int(sn.invincible * 14) % 2 == 0:
            alpha = 105

        head = self.assets.get_scaled("characters/sakura/head.png",
                                      height=int(CELL_SIZE * 1.7))
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
            screen.blit(s, (self.offset_x + p["x"] - r + sx,
                            self.offset_y + p["y"] - r + sy))

    def _draw_floaters(self, screen, sx, sy):
        for f in self.floaters:
            a = max(0, min(255, int(255 * (f["life"] / 0.9))))
            font = self.assets.get_font(f["size"], bold=True)
            t = font.render(f["text"], True, f["color"])
            t.set_alpha(a)
            screen.blit(t, t.get_rect(center=(self.offset_x + f["x"] + sx,
                                              self.offset_y + f["y"] + sy)))

    # ---------------------------------------------------------------- HUD
    def _draw_hud(self):
        screen = self.screen
        sn = self.snake
        panel_w = self.offset_x - 52
        lx, ly = 26, self.offset_y

        panel = pygame.Surface((panel_w, GRID_PX_H), pygame.SRCALPHA)
        panel.fill((*COLOR_BG_LIGHT, 175))
        screen.blit(panel, (lx, ly))
        pygame.draw.rect(screen, COLOR_ACCENT_DARK,
                         pygame.Rect(lx, ly, panel_w, GRID_PX_H), 2, border_radius=10)

        py = ly + 24
        t = self.f_sub.render("樱落", True, COLOR_ACCENT)
        screen.blit(t, (lx + 22, py)); py += 46
        t = self.f_tiny.render("Sakura · SSR", True, COLOR_TEXT_DIM)
        screen.blit(t, (lx + 22, py)); py += 30

        head = self.assets.get_scaled("characters/sakura/head.png", height=128)
        screen.blit(head, (lx + panel_w / 2 - head.get_width() / 2, py))
        py += 144

        t = self.f_sub.render(f"Lv.{sn.level}", True, COLOR_GOLD)
        screen.blit(t, (lx + 22, py)); py += 42

        bw = panel_w - 44
        pygame.draw.rect(screen, (24, 20, 34), (lx + 22, py, bw, 14), border_radius=7)
        need = sn.exp_needed()
        ratio = min(1.0, sn.exp / need) if need else 1.0
        if ratio > 0:
            pygame.draw.rect(screen, COLOR_EXP,
                             (lx + 22, py, int(bw * ratio), 14), border_radius=7)
        py += 22
        t = self.f_tiny.render(f"{sn.exp} / {need}", True, COLOR_TEXT_DIM)
        screen.blit(t, (lx + 22, py)); py += 38

        t = self.f_body.render("生命", True, COLOR_TEXT)
        screen.blit(t, (lx + 22, py)); py += 32
        for i in range(HP_MAX):
            color = COLOR_HP if i < sn.hp else (56, 48, 66)
            cx = lx + 34 + i * 40
            pygame.draw.circle(screen, color, (cx, py), 14)
            pygame.draw.circle(screen, (255, 255, 255), (cx, py), 14, 1)
        py += 44

        t = self.f_body.render(f"攻击 {sn.attack}", True, (120, 210, 200))
        screen.blit(t, (lx + 22, py)); py += 34
        t = self.f_tiny.render(f"击杀 {self.kills}", True, COLOR_TEXT_DIM)
        screen.blit(t, (lx + 22, py))

        # ---------- 右侧 ----------
        rx = self.offset_x + GRID_PX_W + 26
        rw = RENDER_WIDTH - rx - 26
        panel = pygame.Surface((rw, GRID_PX_H), pygame.SRCALPHA)
        panel.fill((*COLOR_BG_LIGHT, 175))
        screen.blit(panel, (rx, ly))
        pygame.draw.rect(screen, COLOR_ACCENT_DARK,
                         pygame.Rect(rx, ly, rw, GRID_PX_H), 2, border_radius=10)

        py = ly + 26
        for label, value, color in (
            ("得分", f"{self.score}", COLOR_TEXT),
            ("星尘", f"{self.stardust}", (206, 168, 255)),
            ("存活", f"{int(self.elapsed)}s", (120, 210, 200)),
            ("威胁", f"{len(self.mobs)}", COLOR_DANGER),
        ):
            t = self.f_body.render(label, True, COLOR_TEXT_DIM)
            screen.blit(t, (rx + 22, py)); py += 30
            t = self.f_sub.render(value, True, color)
            screen.blit(t, (rx + 22, py)); py += 54

        fps = self.game.clock.get_fps()
        color = COLOR_GOOD if fps > 55 else (COLOR_GOLD if fps > 40 else COLOR_DANGER)
        t = self.f_tiny.render(f"{fps:.0f} FPS", True, color)
        screen.blit(t, (rx + 22, ly + GRID_PX_H - 40))

    def _draw_gameover(self):
        screen = self.screen
        veil = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT), pygame.SRCALPHA)
        veil.fill((10, 8, 16, 195))
        screen.blit(veil, (0, 0))

        cx, cy = RENDER_WIDTH // 2, RENDER_HEIGHT // 2
        t = self.f_title.render("战斗结束", True, COLOR_ACCENT)
        screen.blit(t, t.get_rect(center=(cx, cy - 220)))

        rows = [
            ("最终得分", f"{self.score}", COLOR_TEXT),
            ("抵达等级", f"Lv.{self.snake.level}", COLOR_GOLD),
            ("击杀小怪", f"{self.kills}", COLOR_DANGER),
            ("存活时间", f"{int(self.elapsed)} 秒", (120, 210, 200)),
            ("获得星尘", f"{self.stardust}", (206, 168, 255)),
        ]
        y = cy - 120
        for label, value, color in rows:
            lt = self.f_body.render(label, True, COLOR_TEXT_DIM)
            vt = self.f_body.render(value, True, color)
            screen.blit(lt, lt.get_rect(midright=(cx - 24, y)))
            screen.blit(vt, vt.get_rect(midleft=(cx + 24, y)))
            y += 54

        t = self.f_small.render("按 R 再来一局    ·    按 ESC 返回主菜单", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(cx, cy + 200)))

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
