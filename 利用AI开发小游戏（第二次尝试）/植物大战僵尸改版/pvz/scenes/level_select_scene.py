# -*- coding: utf-8 -*-
"""冒险模式选关：原版共 5 章×10 关（1-1 ~ 5-10），画成草坪上的关卡格子。
当前进度：仅 1-1 解锁，其余显示墓碑（ locked ）。"""
import pygame

from .. import settings
from ..core.scene import Scene
from ..core.assets import load_image, get_font
from ..ui.button import CardButton

ROWS, COLS = 5, 10
UNLOCKED = 1  # 已解锁的关卡总数（后续接入存档）


class LevelSelectScene(Scene):
    def on_enter(self):
        self.bg = load_image("level_select_bg.png", (settings.SCREEN_W, settings.SCREEN_H))
        self.toast = ""
        self.toast_time = 0.0

        # 返回按钮
        self.back_btn = CardButton("返回", pygame.Rect(15, 12, 90, 44),
                                   shape="rect", font_size=24,
                                   onclick=self._to_menu)
        # 关卡格子区域
        self.tile_w, self.tile_h = 62, 76
        gap_x, gap_y = 8, 10
        grid_w = COLS * self.tile_w + (COLS - 1) * gap_x
        self.grid_x = (settings.SCREEN_W - grid_w) // 2
        self.grid_y = 150
        self.gap_x, self.gap_y = gap_x, gap_y

    def _to_menu(self):
        from .main_menu_scene import MainMenuScene
        self.game.change_scene(MainMenuScene(self.game))

    def _tile_rect(self, index: int) -> pygame.Rect:
        row, col = divmod(index, COLS)
        x = self.grid_x + col * (self.tile_w + self.gap_x)
        y = self.grid_y + row * (self.tile_h + self.gap_y)
        return pygame.Rect(x, y, self.tile_w, self.tile_h)

    def handle_event(self, event):
        if self.back_btn.handle_event(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(ROWS * COLS):
                if self._tile_rect(i).collidepoint(event.pos):
                    if i < UNLOCKED:
                        self._show_toast(f"关卡 {i // COLS + 1}-{i % COLS + 1}：战斗场景开发中…")
                    else:
                        self._show_toast("该关卡尚未解锁（先通过前面的关卡）")
                    break

    def _show_toast(self, text):
        self.toast = text
        self.toast_time = 2.0

    def update(self, dt):
        if self.toast_time > 0:
            self.toast_time -= dt

    def draw(self, surface):
        if self.bg:
            surface.blit(self.bg, (0, 0))
        else:  # 兜底：整屏浅草坪
            surface.fill((110, 170, 80))
            for r in range(10):  # 深浅条纹模拟草坪
                if r % 2 == 0:
                    pygame.draw.rect(surface, (122, 182, 92),
                                     (0, r * 60, settings.SCREEN_W, 60))

        font = get_font(settings.FONT_PATH, 40)
        title = font.render("选择关卡", True, settings.COLOR_TITLE)
        trect = title.get_rect(center=(settings.SCREEN_W // 2, 60))
        edge = get_font(settings.FONT_PATH, 40).render("选择关卡", True, settings.COLOR_TITLE_EDGE)
        surface.blit(edge, trect.move(2, 2))
        surface.blit(title, trect)

        self.back_btn.draw(surface, 0.0)

        for i in range(ROWS * COLS):
            self._draw_tile(surface, i, i < UNLOCKED)

        # 底部提示条
        font = get_font(settings.FONT_PATH, 20)
        tip = font.render("提示：每章第 5、10 关为 Boss 关（后续开放）", True, (245, 245, 220))
        shadow = font.render("提示：每章第 5、10 关为 Boss 关（后续开放）", True, (50, 40, 20))
        rect = tip.get_rect(center=(settings.SCREEN_W // 2, settings.SCREEN_H - 34))
        surface.blit(shadow, rect.move(1, 2))
        surface.blit(tip, rect)

        # 临时提示 toast
        if self.toast_time > 0:
            font = get_font(settings.FONT_PATH, 22)
            t = font.render(self.toast, True, (255, 255, 255))
            bg = pygame.Surface((t.get_width() + 30, t.get_height() + 16), pygame.SRCALPHA)
            bg.fill((0, 0, 0, int(160 * min(1.0, self.toast_time))))
            rect = bg.get_rect(center=(settings.SCREEN_W // 2, 120))
            surface.blit(bg, rect)
            surface.blit(t, t.get_rect(center=rect.center))

    def _draw_tile(self, surface, index, unlocked):
        rect = self._tile_rect(index)
        if unlocked:
            # 已解锁：绿色草地卡片 + 关卡号
            pygame.draw.rect(surface, (90, 150, 70), rect, border_radius=8)
            pygame.draw.rect(surface, (60, 110, 50), rect, width=3, border_radius=8)
        else:
            # 未解锁：灰色墓碑（原版用墓碑表示）
            tomb = rect.inflate(-8, -4)
            pygame.draw.rect(surface, (150, 150, 150),
                             (tomb.x, tomb.y + 12, tomb.w, tomb.h - 12), border_radius=4)
            pygame.draw.rect(surface, (150, 150, 150),
                             (tomb.x + 8, tomb.y, tomb.w - 16, 24), border_radius=12)
            pygame.draw.rect(surface, (110, 110, 110),
                             (tomb.x, tomb.y + 12, tomb.w, tomb.h - 12), width=2, border_radius=4)
        label = f"{index // COLS + 1}-{index % COLS + 1}"
        font = get_font(settings.FONT_PATH, 22 if unlocked else 18)
        color = (255, 255, 230) if unlocked else (90, 90, 90)
        txt = font.render(label, True, color)
        surface.blit(txt, txt.get_rect(center=(rect.centerx, rect.centery + (0 if unlocked else 8))))
