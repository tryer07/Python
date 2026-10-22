# -*- coding: utf-8 -*-
"""主菜单：草坪大背景 + 顶部 logo + 底部模式选择卡片（还原原版布局）"""
import pygame

from .. import settings
from ..core.scene import Scene
from ..core.assets import load_image, get_font
from ..ui.button import CardButton


class MainMenuScene(Scene):
    def on_enter(self):
        self.bg = load_image("main_menu_bg.png", (settings.SCREEN_W, settings.SCREEN_H))
        # 原版四个模式卡片：冒险 / 小游戏 / 禅境花园 / 生存，本改版暂只开放冒险
        card_w, card_h, gap = 160, 110, 20
        total = card_w * 4 + gap * 3
        start_x = (settings.SCREEN_W - total) // 2
        y = settings.SCREEN_H - card_h - 40
        specs = [
            ("冒险模式", False, self._to_level_select),
            ("小游戏", True, None),
            ("禅境花园", True, None),
            ("生存模式", True, None),
        ]
        self.buttons = []
        for i, (text, disabled, cb) in enumerate(specs):
            rect = pygame.Rect(start_x + i * (card_w + gap), y, card_w, card_h)
            sub = "" if not disabled else "敬请期待"
            self.buttons.append(CardButton(text, rect, onclick=cb,
                                           disabled=disabled, sub_text=sub))

    def _to_level_select(self):
        from .level_select_scene import LevelSelectScene
        self.game.change_scene(LevelSelectScene(self.game))

    def handle_event(self, event):
        for btn in self.buttons:
            btn.handle_event(event)

    def update(self, dt):
        self.dt = dt
        for btn in self.buttons:
            btn.bounce += dt * 4

    def draw(self, surface):
        if self.bg:
            surface.blit(self.bg, (0, 0))
        else:  # 兜底：手绘蓝天 + 草坪
            sky = pygame.Surface((settings.SCREEN_W, 260))
            sky.fill((135, 206, 235))
            surface.blit(sky, (0, 0))
            grass = pygame.Surface((settings.SCREEN_W, settings.SCREEN_H - 260))
            grass.fill((106, 168, 79))
            surface.blit(grass, (0, 260))

        from .loading_scene import _draw_title
        _draw_title(surface, settings.SCREEN_W // 2, 110)

        for btn in self.buttons:
            btn.draw(surface, 0.0)

        # 顶部提示
        font = get_font(settings.FONT_PATH, 18)
        tip = font.render("点击「冒险模式」开始游戏", True, (255, 255, 240))
        shadow = font.render("点击「冒险模式」开始游戏", True, (60, 40, 20))
        rect = tip.get_rect(center=(settings.SCREEN_W // 2, 200))
        surface.blit(shadow, rect.move(2, 2))
        surface.blit(tip, rect)
