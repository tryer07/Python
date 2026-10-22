# -*- coding: utf-8 -*-
"""原版风格"木牌卡片"按钮：梯形圆角卡片 + 描边 + 悬停提亮"""
import math

import pygame

import settings
from core.assets import get_font


class CardButton:
    """模拟 PvZ 主菜单的模式选择卡片。

    shape: "trapezoid" 上窄下宽的木牌（主菜单用）；"rect" 普通圆角卡片（选关/返回用）
    """

    def __init__(self, text: str, rect: pygame.Rect, onclick=None,
                 shape: str = "trapezoid", font_size: int = 30,
                 disabled: bool = False, sub_text: str = ""):
        self.text = text
        self.sub_text = sub_text
        self.rect = rect
        self.onclick = onclick
        self.shape = shape
        self.font_size = font_size
        self.disabled = disabled
        self.hover = False
        self.bounce = 0.0  # 悬停时的轻微上下浮动动画计时

    # ---------- 交互 ----------
    def handle_event(self, event) -> bool:
        """返回是否消耗了事件"""
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos) and not self.disabled
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hover and self.onclick:
                self.onclick()
                return True
        return False

    # ---------- 绘制 ----------
    def draw(self, surface: pygame.Surface, dt: float):
        self.bounce += dt * 4
        # 悬停时轻微上下浮动
        offset = -3 + int(1.5 * (1 + math.sin(self.bounce))) if self.hover else 0
        rect = self.rect.move(0, offset)

        base = settings.COLOR_CARD_HOVER if self.hover else settings.COLOR_CARD
        if self.disabled:
            base = tuple((c + 130) // 2 for c in base)

        if self.shape == "trapezoid":
            inset = rect.width // 10
            points = [
                (rect.left + inset, rect.top),
                (rect.right - inset, rect.top),
                (rect.right, rect.bottom),
                (rect.left, rect.bottom),
            ]
            pygame.draw.polygon(surface, base, points)
            pygame.draw.polygon(surface, settings.COLOR_CARD_EDGE, points, width=3)
        else:
            pygame.draw.rect(surface, base, rect, border_radius=10)
            pygame.draw.rect(surface, settings.COLOR_CARD_EDGE, rect, width=3, border_radius=10)

        # 主文字
        font = get_font(settings.FONT_PATH, self.font_size)
        txt = font.render(self.text, True, settings.COLOR_TEXT)
        surface.blit(txt, txt.get_rect(center=rect.center))
        # 副文字（如"敬请期待"）
        if self.sub_text:
            sub_font = get_font(settings.FONT_PATH, max(14, self.font_size - 14))
            sub = sub_font.render(self.sub_text, True, settings.COLOR_TEXT)
            surface.blit(sub, sub.get_rect(midbottom=(rect.centerx, rect.bottom - 6)))
