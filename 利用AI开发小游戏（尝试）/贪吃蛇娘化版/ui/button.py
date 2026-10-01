import pygame
from settings import (
    COLOR_BUTTON_BG, COLOR_BUTTON_HOVER, COLOR_BUTTON_ACTIVE,
    COLOR_TEXT, COLOR_ACCENT, FONT_SIZE_BODY
)


class Button:
    """可复用的 UI 按钮"""

    def __init__(self, text, x, y, width=280, height=60, font_size=FONT_SIZE_BODY,
                 bg_color=COLOR_BUTTON_BG, hover_color=COLOR_BUTTON_HOVER,
                 text_color=COLOR_TEXT, accent_color=COLOR_ACCENT, on_click=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.active_color = COLOR_BUTTON_ACTIVE
        self.text_color = text_color
        self.accent_color = accent_color
        self.on_click = on_click

        self.font = pygame.font.SysFont("Microsoft YaHei", font_size, bold=True)
        self.is_hovered = False
        self.is_pressed = False

    def handle_event(self, event):
        # 延迟 import，避免 ui -> core -> ui 的循环依赖；取不到时返回 no-op 替身。
        from core.audio_manager import get_audio
        audio = get_audio()

        if event.type == pygame.MOUSEMOTION:
            was = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            # 只在"刚移入"的边沿播一次，并节流，避免在按钮上滑动时哒哒响
            if self.is_hovered and not was:
                audio.play("ui_hover", throttle=0.08)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed and self.is_hovered:
                self.is_pressed = False
                audio.play("ui_click")
                if self.on_click:
                    self.on_click()
                return True
            self.is_pressed = False
        return False

    def draw(self, surface):
        if self.is_pressed:
            color = self.active_color
        elif self.is_hovered:
            color = self.hover_color
        else:
            color = self.bg_color

        pygame.draw.rect(surface, color, self.rect, border_radius=10)

        border_color = self.accent_color if self.is_hovered else (80, 80, 120)
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=10)

        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)