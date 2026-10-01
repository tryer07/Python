# -*- coding: utf-8 -*-
"""
scenes/scene_select.py —— 场景选择

场景表从 data/scenes.json 读。
每个场景有自己的背景贴图、小怪强度、危险等级。
目前只有「校园庭院」有真实贴图，其余用色块占位，等你出图。
"""

import json
import os

import pygame

from core.scene import Scene
from ui.button import Button
from settings import (
    DATA_DIR, RENDER_WIDTH, RENDER_HEIGHT,
    COLOR_BG, COLOR_ACCENT, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_GOLD,
    FONT_SIZE_TITLE, FONT_SIZE_SUBTITLE, FONT_SIZE_BODY, FONT_SIZE_SMALL
)

CARD_W, CARD_H = 380, 240
CARD_GAP = 36

DIFF_COLORS = {
    "入门": (120, 210, 150),
    "普通": (110, 180, 240),
    "困难": (245, 170, 90),
    "噩梦": (235, 95, 120),
}

FALLBACK = [
    {"id": "campus_garden", "name": "校园庭院", "desc": "樱花纷飞的校园后院",
     "difficulty": "入门", "bg": "backgrounds/campus_garden.png",
     "accent": [222, 118, 158]},
    {"id": "neon_night", "name": "霓虹夜市", "desc": "人潮与灯牌之间的追逐",
     "difficulty": "普通", "bg": "", "accent": [150, 110, 240]},
    {"id": "deep_sea", "name": "深海遗迹", "desc": "视野受限，尖刺密布",
     "difficulty": "困难", "bg": "", "accent": [80, 180, 210]},
    {"id": "sakura_realm", "name": "樱花神域", "desc": "活动区域会逐渐收窄",
     "difficulty": "噩梦", "bg": "", "accent": [230, 130, 190]},
]


class SceneSelectScene(Scene):
    """场景/地图选择"""

    def enter(self):
        self.assets = self.game.assets
        self.font_title = self.assets.get_font(FONT_SIZE_TITLE, bold=True)
        self.font_sub = self.assets.get_font(FONT_SIZE_SUBTITLE)
        self.font_body = self.assets.get_font(FONT_SIZE_BODY)
        self.font_small = self.assets.get_font(FONT_SIZE_SMALL)

        self.back_btn = Button(
            "返回主菜单", 30, RENDER_HEIGHT - 80, 200, 50,
            font_size=FONT_SIZE_SMALL, on_click=self._on_back
        )
        self.scenes = self._load_scenes()
        self.selected_scene = self.game.save_manager.get("selected_scene", "campus_garden")
        self.hover_id = None
        self.time = 0.0

    def exit(self):
        pass

    def _load_scenes(self):
        path = os.path.join(DATA_DIR, "scenes.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    return data
            except (json.JSONDecodeError, IOError) as e:
                print(f"[场景表读取失败] {e}，改用内置默认表")
        return FALLBACK

    # ---------------------------------------------------------------- 输入
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._on_back()
                return
            if event.type == pygame.MOUSEMOTION:
                self.hover_id = None
                for _, rect, sc in self._cards():
                    if rect.collidepoint(event.pos):
                        self.hover_id = sc["id"]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for _, rect, sc in self._cards():
                    if rect.collidepoint(event.pos):
                        self.selected_scene = sc["id"]
                        self.game.save_manager.set("selected_scene", sc["id"])
                        return
            self.back_btn.handle_event(event)

    def update(self, dt):
        self.time += dt

    def _cards(self):
        n = len(self.scenes)
        cols = 2
        rows = (n + cols - 1) // cols
        total_w = cols * CARD_W + (cols - 1) * CARD_GAP
        total_h = rows * CARD_H + (rows - 1) * CARD_GAP
        x0 = (RENDER_WIDTH - total_w) // 2
        y0 = (RENDER_HEIGHT - total_h) // 2 + 40
        out = []
        for i, sc in enumerate(self.scenes):
            c, r = i % cols, i // cols
            rect = pygame.Rect(x0 + c * (CARD_W + CARD_GAP),
                               y0 + r * (CARD_H + CARD_GAP),
                               CARD_W, CARD_H)
            out.append((i, rect, sc))
        return out

    @staticmethod
    def _asset_exists(rel_path):
        """检查 assets 下这张图在不在"""
        from settings import ASSETS_DIR
        return os.path.exists(os.path.join(ASSETS_DIR, rel_path.replace("/", os.sep)))

    # ---------------------------------------------------------------- 绘制
    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)

        bg = self.assets.get_scaled("backgrounds/campus_garden.png", width=RENDER_WIDTH)
        screen.blit(bg, (0, -40))
        veil = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT), pygame.SRCALPHA)
        veil.fill((14, 12, 22, 206))
        screen.blit(veil, (0, 0))

        title = self.font_title.render("选择作战场景", True, COLOR_ACCENT)
        screen.blit(title, title.get_rect(center=(RENDER_WIDTH // 2, 78)))
        t = self.font_small.render("不同场景的敌人配置与危险程度不同", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(RENDER_WIDTH // 2, 130)))

        for _, rect, sc in self._cards():
            self._draw_card(screen, rect, sc)

        self.back_btn.draw(screen)

    def _draw_card(self, screen, rect, sc):
        selected = sc["id"] == self.selected_scene
        hovered = self.hover_id == sc["id"]

        pygame.draw.rect(screen, (34, 30, 46), rect, border_radius=12)

        # ---- 预览图 ----
        preview = pygame.Rect(rect.x + 14, rect.y + 14, rect.w - 28, 138)
        bg_path = sc.get("bg", "")
        if bg_path and self._asset_exists(bg_path):
            img = self.assets.get_scaled(bg_path, width=preview.w)
            if img.get_height() >= preview.h:
                top = (img.get_height() - preview.h) // 2
                img = img.subsurface(pygame.Rect(0, top, preview.w, preview.h)).copy()
            screen.blit(img, preview.topleft)
        else:
            accent = sc.get("accent", [120, 110, 150])
            pygame.draw.rect(screen, tuple(accent), preview, border_radius=8)
            t = self.font_small.render("[ 场景贴图待补 ]", True, (255, 255, 255))
            screen.blit(t, t.get_rect(center=preview.center))

        # 预览图压暗
        ov = pygame.Surface(preview.size, pygame.SRCALPHA)
        ov.fill((0, 0, 0, 60))
        screen.blit(ov, preview.topleft)

        # 难度角标
        diff = sc.get("difficulty", "普通")
        dc = DIFF_COLORS.get(diff, (150, 150, 150))
        badge = pygame.Rect(preview.x + 10, preview.y + 10, 76, 28)
        pygame.draw.rect(screen, dc, badge, border_radius=8)
        t = self.font_small.render(diff, True, (26, 22, 34))
        screen.blit(t, t.get_rect(center=badge.center))

        # ---- 名字与描述 ----
        t = self.font_sub.render(sc.get("name", "???"), True, COLOR_TEXT)
        screen.blit(t, t.get_rect(midleft=(rect.x + 20, rect.y + 182)))

        t = self.font_small.render(sc.get("desc", ""), True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(midleft=(rect.x + 20, rect.y + 214)))

        if selected:
            t = self.font_body.render("已选择", True, COLOR_GOLD)
            screen.blit(t, t.get_rect(midright=(rect.right - 20, rect.y + 182)))

        border = COLOR_ACCENT if selected else ((130, 120, 170) if hovered else (60, 56, 78))
        pygame.draw.rect(screen, border, rect, 4 if selected else 2, border_radius=12)

    def _on_back(self):
        self.game.change_scene("main_menu")
