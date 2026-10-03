# -*- coding: utf-8 -*-
"""
scenes/main_menu.py —— 主菜单
"""

import math
import os
import random

import pygame

from core.scene import Scene
from ui.button import Button
from settings import (
    ASSETS_DIR, COLOR_BG, COLOR_ACCENT, COLOR_TEXT, COLOR_TEXT_DIM,
    FONT_SIZE_TITLE, FONT_SIZE_SUBTITLE, FONT_SIZE_BODY, FONT_SIZE_SMALL
)


class MainMenuScene(Scene):
    """主菜单场景"""

    def enter(self):
        self.assets = self.game.assets
        self.game.audio.play_bgm("menu")
        self.font_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)
        self.font_subtitle = self.assets.get_font(self.s(FONT_SIZE_SUBTITLE))
        self.font_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.font_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))

        cx = self.W // 2
        btn_w, btn_h = self.s(320), self.s(64)
        start_y = self.s(408)
        gap = self.s(76)

        self.buttons = [
            Button("开始游戏", cx - btn_w // 2, start_y,
                   btn_w, btn_h, on_click=lambda: self._go("level_select")),
            Button("角色选择", cx - btn_w // 2, start_y + gap,
                   btn_w, btn_h, on_click=lambda: self._go("character_select")),
            Button("蛇娘召集", cx - btn_w // 2, start_y + gap * 2,
                   btn_w, btn_h, on_click=lambda: self._go("gacha")),
            Button("显示设置", cx - btn_w // 2, start_y + gap * 3,
                   btn_w, btn_h, on_click=lambda: self._go("display_settings")),
            Button("操作设置", cx - btn_w // 2, start_y + gap * 4,
                   btn_w, btn_h, on_click=lambda: self._go("control_settings")),
            Button("存档管理", cx - btn_w // 2, start_y + gap * 5,
                   btn_w, btn_h, on_click=lambda: self._go("save_manager")),
            Button("退出游戏", cx - btn_w // 2, start_y + gap * 6,
                   btn_w, btn_h, on_click=self._on_quit),
        ]

        self.time = 0.0

        # 角色名 / 场景名一次性读进缓存，避免 draw() 每帧重复 open() 而泄漏文件句柄
        self._char_names = self._load_names("characters.json")
        self._scene_names = self._load_names("scenes.json")
        self._bg_cache = None      # 标题底图 contain+垫边 图层缓存（按屏幕尺寸）
        self._bg_cache_key = None
        # 粒子动效（夜祭灯笼暖光 + 水母冷光 + 樱瓣飘落）：贴图走旋转步 /
        # 透明度档缓存，不每帧 rotozoom / set_alpha 重采样。
        self._fx = []
        self._fx_sprites = {}
        self._seed_fx()
        # 静态文案进场景时渲染一次每帧复用（font.render 单次 0.1~0.4ms，
        # 逐帧累积是隐蔽掉帧源）；存档信息在菜单停留期间不会变。
        save = self.game.save_manager.data
        char_id = save.get("selected_character", "sakura")
        scene_id = save.get("selected_scene", "campus_garden")
        char_name = self._char_names.get(char_id, char_id)
        scene_name = self._scene_names.get(scene_id, scene_id)
        slot_name = getattr(self.game.save_manager, "active_slot_name", "")
        p = save.get("progress", {})
        self._t_title = self.font_title.render("鳞光纪", True, COLOR_ACCENT)
        self._t_title_shadow = self._t_title.copy()
        self._t_title_shadow.fill((0, 0, 0, 170),
                                  special_flags=pygame.BLEND_RGBA_MULT)
        self._t_subtitle = self.font_subtitle.render(
            "六元素蛇娘 · 动作生存肉鸽", True, COLOR_TEXT_DIM)
        self._t_slot = self.font_small.render(
            f"存档：{slot_name}    ·    出战角色：{char_name}    ·    当前场景：{scene_name}",
            True, COLOR_TEXT_DIM)
        self._t_info = self.font_small.render(
            f"星尘 {save.get('currency', 0)}    |    "
            f"角色 {len(save.get('owned_characters', []))}    |    "
            f"最高分 {p.get('best_score', 0)}    |    "
            f"总击杀 {p.get('total_kills', 0)}    |    "
            f"游玩 {p.get('total_runs', 0)} 局", True, COLOR_TEXT_DIM)
        self._t_ver = self.font_small.render("v0.1.0  ·  F11 全屏", True, (92, 92, 118))

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game.running = False
            for b in self.buttons:
                b.handle_event(event)

    def update(self, dt):
        self.time += dt
        self._update_fx(dt)

    # ---------------------------------------------------------------- 绘制
    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)
        self._draw_background(screen)
        self._draw_fx(screen)

        cx = self.W // 2
        screen.blit(self._t_title_shadow,
                    self._t_title.get_rect(center=(cx + 3, self.s(168) + 4)))
        screen.blit(self._t_title, self._t_title.get_rect(center=(cx, self.s(168))))
        screen.blit(self._t_subtitle,
                    self._t_subtitle.get_rect(center=(cx, self.s(244))))

        pygame.draw.line(screen, COLOR_ACCENT,
                         (cx - self.s(200), self.s(300)),
                         (cx + self.s(200), self.s(300)), 2)

        screen.blit(self._t_slot, self._t_slot.get_rect(center=(cx, self.s(336))))

        for b in self.buttons:
            b.draw(screen)

        screen.blit(self._t_info,
                    self._t_info.get_rect(center=(cx, self.H - self.s(44))))
        screen.blit(self._t_ver,
                    self._t_ver.get_rect(midleft=(self.s(20), self.H - self.s(24))))

    def _draw_background(self, screen):
        # 初始界面专用底图：优先 backgrounds/title_bg.png（用户指定封面插画），
        # 缺文件回退校园庭院图。比例调整红线（用户指定）：只允许等比缩放 /
        # 补边 / 居中裁切，不得异向拉伸、不得损坏画面内容与人物身材比例。
        # 故主层 contain 等比完整居中（封面六人全员可见）；留边分两档：
        # 窄边（<=6%，16:9 宽图在 16:9 屏的常态）用主层边缘像素拉伸补边，
        # 每帧省一次全屏垫底 blit；宽边（超宽/超窄窗口）回退同图 cover+
        # 强模糊垫底慢漂移，任何窗口比例 / 全屏都不出现死黑块。
        # 压暗纱在缓存构建时烘进各层（旧写法每帧建全屏半透明画布再 blit，
        # 是已知的隐蔽掉帧源）。
        key = (self.W, self.H)
        if self._bg_cache_key != key or self._bg_cache is None:
            rel = "backgrounds/title_bg.png"
            if not os.path.exists(os.path.join(ASSETS_DIR, rel.replace("/", os.sep))):
                rel = "backgrounds/campus_garden.png"
            base = self.assets.get_image(rel)
            w, h = base.get_size()
            k = min(self.W / w, self.H / h)
            sharp = pygame.transform.smoothscale(
                base, (max(1, round(w * k)), max(1, round(h * k))))
            rect = sharp.get_rect(center=(self.W // 2, self.H // 2))
            strips = self._edge_strips(sharp, rect)
            under = None if strips is not None else self._blur_under(base, w, h)
            self._bake_veil(sharp, 150)
            if under is not None:
                self._bake_veil(under, 150)
            else:
                for surf, _r in strips:
                    self._bake_veil(surf, 150)
            self._bg_cache = (under, strips, sharp, rect)
            self._bg_cache_key = key
        under, strips, sharp, rect = self._bg_cache
        if under is not None:
            mx = (under.get_width() - self.W) // 2
            my = (under.get_height() - self.H) // 2
            ox = int(math.sin(self.time * 0.10) * mx * 0.8)
            oy = int(math.cos(self.time * 0.07) * my * 0.8)
            screen.blit(under, (-mx + ox, -my + oy))
        else:
            for surf, r in strips:
                screen.blit(surf, r)
        screen.blit(sharp, rect)

    def _blur_under(self, base, w, h):
        """宽留边垫底：同图 cover 裁切 + 两级缩放当强模糊，比屏幕大 12% 供慢漂移。"""
        tw, th = int(self.W * 1.12), int(self.H * 1.12)
        ku = max(tw / w, th / h)
        under = pygame.transform.smoothscale(
            base, (max(1, round(w * ku)), max(1, round(h * ku))))
        under = under.subsurface(pygame.Rect(
            (under.get_width() - tw) // 2, (under.get_height() - th) // 2,
            tw, th)).copy()
        under = pygame.transform.smoothscale(under, (tw // 8, th // 8))
        return pygame.transform.smoothscale(under, (tw, th))

    def _edge_strips(self, sharp, rect):
        """窄留边补边：主层上下（或左右）边缘像素条拉伸铺满留边区（补边不碰
        画面内容）。留边超过 6% 时拉伸观感差，返回 None 由调用方回退模糊垫底。"""
        sw, sh = sharp.get_size()
        strips = []
        if rect.height < self.H:
            top, bot = rect.y, self.H - rect.bottom
            if max(top, bot) > self.H * 0.06:
                return None
            src_h = max(2, sh // 64)
            if top > 0:
                strips.append((self._soft_strip(pygame.transform.smoothscale(
                    sharp.subsurface(pygame.Rect(0, 0, sw, src_h)), (sw, top))),
                    pygame.Rect(rect.x, 0, sw, top)))
            if bot > 0:
                strips.append((self._soft_strip(pygame.transform.smoothscale(
                    sharp.subsurface(pygame.Rect(0, sh - src_h, sw, src_h)), (sw, bot))),
                    pygame.Rect(rect.x, rect.bottom, sw, bot)))
        elif rect.width < self.W:
            left, right = rect.x, self.W - rect.right
            if max(left, right) > self.W * 0.06:
                return None
            src_w = max(2, sw // 64)
            if left > 0:
                strips.append((self._soft_strip(pygame.transform.smoothscale(
                    sharp.subsurface(pygame.Rect(0, 0, src_w, sh)), (left, sh))),
                    pygame.Rect(0, rect.y, left, sh)))
            if right > 0:
                strips.append((self._soft_strip(pygame.transform.smoothscale(
                    sharp.subsurface(pygame.Rect(sw - src_w, 0, src_w, sh)), (right, sh))),
                    pygame.Rect(rect.right, rect.y, right, sh)))
        return strips

    @staticmethod
    def _soft_strip(surf):
        """补边条两级缩放柔化（免单向拉伸出现条纹感），缓存时一次性。"""
        w, h = surf.get_size()
        d = pygame.transform.smoothscale(surf, (max(1, w // 4), max(1, h // 4)))
        return pygame.transform.smoothscale(d, (w, h))

    @staticmethod
    def _bake_veil(surf, alpha):
        """压暗纱烘进图层（缓存构建时一次性），取代每帧全屏半透明 blit。"""
        veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        veil.fill((14, 12, 22, alpha))
        surf.blit(veil, (0, 0))

    # ---------------------------------------------------------------- 粒子动效
    def _seed_fx(self):
        """夜祭氛围粒子：樱瓣飘落（摇摆+自旋）+ 灯笼暖光 / 水母冷光上浮闪烁。"""
        self._fx = []
        for _ in range(22):
            self._fx.append({
                "kind": "petal",
                "x0": random.uniform(0, self.W),
                "y": random.uniform(-self.H * 0.1, self.H),
                "vy": random.uniform(0.05, 0.11) * self.H,
                "amp": random.uniform(0.01, 0.035) * self.W,
                "freq": random.uniform(0.5, 1.2),
                "phase": random.uniform(0, 6.283),
                "rot": random.uniform(0, 360),
                "vr": random.uniform(-40, 40),
                "size": random.choice((self.s(12), self.s(18), self.s(24))),
                "color": (255, 186, 205),
            })
        for _ in range(20):
            self._fx.append({
                "kind": "glow",
                "x": random.uniform(0, self.W),
                "y": random.uniform(self.H * 0.2, self.H),
                "vy": random.uniform(0.02, 0.06) * self.H,
                "freq": random.uniform(0.8, 1.6),
                "phase": random.uniform(0, 6.283),
                "size": random.choice((self.s(10), self.s(16), self.s(22))),
                "color": random.choice(((255, 205, 130), (255, 205, 130),
                                        (150, 220, 255))),
            })

    def _update_fx(self, dt):
        """推进粒子；出界从另一侧回填，数量恒定不增不减。"""
        for p in self._fx:
            if p["kind"] == "petal":
                p["y"] += p["vy"] * dt
                p["rot"] = (p["rot"] + p["vr"] * dt) % 360.0
                if p["y"] > self.H + self.s(30):
                    p["y"] = -self.s(30)
                    p["x0"] = random.uniform(0, self.W)
            else:
                p["y"] -= p["vy"] * dt
                if p["y"] < self.H * 0.15:
                    p["y"] = self.H * 1.02
                    p["x"] = random.uniform(0, self.W)

    def _draw_fx(self, screen):
        for p in self._fx:
            if p["kind"] == "petal":
                x = p["x0"] + math.sin(self.time * p["freq"] + p["phase"]) * p["amp"]
                spr = self._fx_sprite_rot(p["size"], p["color"],
                                          int(p["rot"] // 15) % 24)
                screen.blit(spr, spr.get_rect(center=(int(x), int(p["y"]))))
            else:
                level = int(1.5 + 1.5 * math.sin(
                    self.time * p["freq"] + p["phase"]))
                spr = self._fx_sprite_alpha(p["size"], p["color"],
                                            max(0, min(3, level)))
                screen.blit(spr, spr.get_rect(center=(int(p["x"]), int(p["y"]))))

    def _fx_sprite(self, kind, size, color):
        """动效基础贴图（缓存）：glow=径向柔光斑，petal=椭圆花瓣。"""
        size = max(4, int(size))
        key = (kind, size, color)
        hit = self._fx_sprites.get(key)
        if hit is not None:
            return hit
        if kind == "glow":
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            r = size // 2
            for i in range(r, 0, -1):
                a = int(150 * (i / r) ** 2)
                pygame.draw.circle(surf, (*color, a), (r, r), i)
        else:
            w, h = size, max(3, int(size * 0.62))
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (*color, 200), (0, 0, w, h))
            pygame.draw.ellipse(surf, (255, 255, 255, 90),
                                (w // 4, h // 4, w // 2, h // 2))
        if len(self._fx_sprites) > 256:
            self._fx_sprites.clear()
        self._fx_sprites[key] = surf
        return surf

    def _fx_sprite_rot(self, size, color, step):
        """花瓣旋转步贴图（15° 一步缓存）：避免每帧 rotozoom 重采样掉帧。"""
        key = ("petal_rot", int(size), color, step)
        hit = self._fx_sprites.get(key)
        if hit is not None:
            return hit
        spr = pygame.transform.rotozoom(self._fx_sprite("petal", size, color),
                                        step * 15, 1.0)
        self._fx_sprites[key] = spr
        return spr

    def _fx_sprite_alpha(self, size, color, level):
        """光斑透明度档贴图（4 档缓存）：闪烁靠换档，不靠每帧 set_alpha。"""
        key = ("glow_a", int(size), color, level)
        hit = self._fx_sprites.get(key)
        if hit is not None:
            return hit
        spr = self._fx_sprite("glow", size, color).copy()
        spr.set_alpha(80 + level * 30)
        self._fx_sprites[key] = spr
        return spr

    # ---------------------------------------------------------------- 工具
    @staticmethod
    def _load_names(filename):
        """从 data/<filename> 一次性读出 {id: name} 映射。

        旧写法在 draw() 里每帧 open() 且不关闭，会持续泄漏文件句柄；
        改为进入场景时读一次缓存起来。兼容 json 为列表或 {"characters": [...]} 字典。"""
        import json
        import os
        from settings import DATA_DIR
        result = {}
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data.get("characters", data) if isinstance(data, dict) else data
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict) and "id" in it:
                            result[it["id"]] = it.get("name", it["id"])
            except (json.JSONDecodeError, IOError, AttributeError, TypeError):
                pass
        return result

    # ---------------------------------------------------------------- 回调
    def _go(self, scene_name):
        self.game.change_scene(scene_name)

    def _on_quit(self):
        self.game.running = False
