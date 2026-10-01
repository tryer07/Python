# -*- coding: utf-8 -*-
"""
scenes/character_select.py —— 娘化角色选择

角色表从 data/characters.json 读。
以后你出了新图，只要：
    1. 图片放到 assets/characters/<id>/ 下
    2. 在 data/characters.json 里加一条记录
这里就会自动多出一张卡，不用改代码。
"""

import json
import os

import pygame

from core.scene import Scene
from ui.button import Button
from settings import (
    DATA_DIR,
    COLOR_BG, COLOR_ACCENT, COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_BG_LIGHT, COLOR_GOLD,
    FONT_SIZE_TITLE, FONT_SIZE_SUBTITLE, FONT_SIZE_BODY, FONT_SIZE_SMALL
)

RARITY_COLORS = {
    "SSR": (255, 200, 50),
    "SR": (200, 100, 255),
    "R": (100, 150, 255),
    "N": (180, 180, 180),
}


class CharacterSelectScene(Scene):
    """角色选择场景"""

    def enter(self):
        self.assets = self.game.assets
        self.font_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)
        self.font_sub = self.assets.get_font(self.s(FONT_SIZE_SUBTITLE))
        self.font_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.font_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))

        self.back_btn = Button(
            "返回主菜单", self.s(30), self.H - self.s(80), self.s(200), self.s(50),
            font_size=self.s(FONT_SIZE_SMALL), on_click=self._on_back
        )

        self.CARD_W = self.s(260)
        self.CARD_H = self.s(400)
        self.CARD_GAP = self.s(40)

        self.characters = self._load_characters()
        save = self.game.save_manager.data
        self.owned = save.get("owned_characters", [])
        self.selected = save.get("selected_character", self.characters[0]["id"])
        self.hover_index = -1
        self.time = 0.0

    def exit(self):
        pass

    # ------------------------------------------------------------ 读角色表
    def _load_characters(self):
        path = os.path.join(DATA_DIR, "characters.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    return data
            except (json.JSONDecodeError, IOError) as e:
                print(f"[角色表读取失败] {e}，改用内置默认表")
        # 兜底：保证游戏一定能跑
        return [{
            "id": "sakura",
            "name": "樱落",
            "rarity": "SSR",
            "title": "樱花神域的守护者",
            "element": "樱",
            "head": "characters/sakura/head.png",
            "tint": [255, 200, 220],
        }]

    # ---------------------------------------------------------------- 布局
    def _cards(self):
        n = max(1, len(self.characters))
        total = n * self.CARD_W + (n - 1) * self.CARD_GAP
        x0 = (self.W - total) // 2
        y0 = self.s(210)
        out = []
        for i, ch in enumerate(self.characters):
            out.append((i, pygame.Rect(x0 + i * (self.CARD_W + self.CARD_GAP), y0,
                                       self.CARD_W, self.CARD_H), ch))
        return out

    # ---------------------------------------------------------------- 输入
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._on_back()
                return
            if event.type == pygame.MOUSEMOTION:
                self.hover_index = -1
                for i, r, _ in self._cards():
                    if r.collidepoint(event.pos):
                        self.hover_index = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r, ch in self._cards():
                    if r.collidepoint(event.pos) and ch["id"] in self.owned:
                        self.selected = ch["id"]
                        self.game.save_manager.set("selected_character", ch["id"])
            self.back_btn.handle_event(event)

    def update(self, dt):
        self.time += dt

    # ---------------------------------------------------------------- 绘制
    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)

        bg = self.assets.get_scaled("backgrounds/campus_garden.png", width=self.W)
        screen.blit(bg, (0, self.s(-40)))
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((14, 12, 22, 202))
        screen.blit(veil, (0, 0))

        title = self.font_title.render("选择你的蛇娘", True, COLOR_ACCENT)
        screen.blit(title, title.get_rect(center=(self.W // 2, self.s(90))))

        t = self.font_small.render("不同角色拥有不同的成长曲线与技能", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.s(148))))

        for i, rect, ch in self._cards():
            self._draw_card(screen, rect, ch,
                            i == self.hover_index,
                            ch["id"] == self.selected,
                            ch["id"] in self.owned)

        self.back_btn.draw(screen)

    def _draw_card(self, screen, rect, ch, hovered, selected, owned):
        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        panel.fill((*COLOR_BG_LIGHT, 232) if owned else (28, 26, 38, 210))
        screen.blit(panel, rect.topleft)

        rarity = ch.get("rarity", "N")
        rc = RARITY_COLORS.get(rarity, (150, 150, 150))
        if selected:
            border, bw = COLOR_ACCENT, self.s(4)
        elif hovered:
            border, bw = (140, 130, 180), self.s(3)
        elif owned:
            border, bw = rc, self.s(3)
        else:
            border, bw = (62, 58, 82), self.s(2)
        pygame.draw.rect(screen, border, rect, bw, border_radius=self.s(14))

        # 稀有度角标
        badge = pygame.Rect(rect.x + self.s(14), rect.y + self.s(14), self.s(64), self.s(30))
        pygame.draw.rect(screen, rc, badge, border_radius=self.s(8))
        tb = self.font_small.render(rarity, True, (30, 24, 38))
        screen.blit(tb, tb.get_rect(center=badge.center))

        if owned:
            img = self.assets.get_scaled(ch.get("head", "characters/sakura/head.png"),
                                         height=self.s(200))
            if selected:
                import math
                k = 1.0 + math.sin(self.time * 2.4) * 0.02
                img = pygame.transform.smoothscale(
                    img, (int(img.get_width() * k), int(img.get_height() * k)))
            screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + self.s(168))))
        else:
            ph = pygame.Rect(rect.x + self.s(30), rect.y + self.s(70),
                             rect.w - self.s(60), self.s(196))
            pygame.draw.rect(screen, (44, 40, 60), ph, border_radius=self.s(10))
            t = self.font_body.render("?", True, (90, 86, 110))
            screen.blit(t, t.get_rect(center=ph.center))

        # 名字
        name_color = COLOR_TEXT if owned else (110, 106, 130)
        t = self.font_sub.render(ch.get("name", "???"), True, name_color)
        screen.blit(t, t.get_rect(center=(rect.centerx, rect.y + self.s(296))))

        t = self.font_small.render(ch.get("title", ""), True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(rect.centerx, rect.y + self.s(334))))

        t = self.font_small.render(f"属性 · {ch.get('element', '无')}", True, COLOR_ACCENT)
        screen.blit(t, t.get_rect(center=(rect.centerx, rect.y + self.s(366))))

        if not owned:
            t = self.font_small.render("未解锁 · 前往抽卡", True, (230, 110, 120))
            screen.blit(t, t.get_rect(center=(rect.centerx, rect.bottom - self.s(26))))
        elif selected:
            t = self.font_body.render("已出战", True, COLOR_GOLD)
            screen.blit(t, t.get_rect(center=(rect.centerx, rect.bottom - self.s(26))))

    def _on_back(self):
        self.game.change_scene("main_menu")
