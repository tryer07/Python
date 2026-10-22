# -*- coding: utf-8 -*-
"""启动加载页：深色底 + 标题 logo + 进度条，加载完自动进入主菜单（原版开局即进入菜单界面）"""
import pygame

from .. import settings
from ..core.scene import Scene
from ..core.assets import load_image, get_font


class LoadingScene(Scene):
    DURATION = 2.2  # 假装加载的时长（秒），后续接入真实资源加载可改为按完成度推进

    def on_enter(self):
        self.progress = 0.0
        self.done_time = 0.0
        self.bg = load_image("loading_bg.png", (settings.SCREEN_W, settings.SCREEN_H))

    def handle_event(self, event):
        # 点击可跳过加载
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.progress = 1.0

    def update(self, dt):
        if self.progress < 1.0:
            self.progress = min(1.0, self.progress + dt / self.DURATION)
        else:
            self.done_time += dt
            if self.done_time > 0.4:
                from .main_menu_scene import MainMenuScene
                self.game.change_scene(MainMenuScene(self.game))

    def draw(self, surface):
        # 背景：有图用图，没图用深棕色渐变兜底
        if self.bg:
            surface.blit(self.bg, (0, 0))
        else:
            surface.fill((35, 28, 20))
            for i in range(0, settings.SCREEN_H, 4):
                r = int(35 + 25 * i / settings.SCREEN_H)
                g = int(28 + 18 * i / settings.SCREEN_H)
                b = int(20 + 12 * i / settings.SCREEN_H)
                pygame.draw.line(surface, (r, g, b), (0, i), (settings.SCREEN_W, i))

        # 标题 logo（描边大字）
        cx = settings.SCREEN_W // 2
        _draw_title(surface, cx, 150)

        # 进度条
        bar_w, bar_h = 360, 26
        bar_x = cx - bar_w // 2
        bar_y = 420
        pygame.draw.rect(surface, (70, 55, 38), (bar_x - 3, bar_y - 3, bar_w + 6, bar_h + 6),
                         border_radius=8)
        pygame.draw.rect(surface, (30, 24, 16), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        fill_w = int(bar_w * self.progress)
        if fill_w > 0:
            pygame.draw.rect(surface, (126, 200, 80), (bar_x, bar_y, fill_w, bar_h),
                             border_radius=6)
        font = get_font(settings.FONT_PATH, 18)
        tip = font.render("正在加载资源…（点击跳过）", True, (200, 190, 160))
        surface.blit(tip, tip.get_rect(center=(cx, bar_y + bar_h + 26)))


def _draw_title(surface, cx, cy):
    """加载页与主菜单共用的 logo 标题绘制"""
    font = get_font(settings.FONT_PATH, 58)
    title = "植物大战僵尸"
    # 8 方向描边模拟原版立体字
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx or dy:
                t = font.render(title, True, settings.COLOR_TITLE_EDGE)
                surface.blit(t, t.get_rect(center=(cx + dx, cy + dy)))
    t = font.render(title, True, settings.COLOR_TITLE)
    surface.blit(t, t.get_rect(center=(cx, cy)))
    sub_font = get_font(settings.FONT_PATH, 22)
    sub = sub_font.render("—— 改 版 ——", True, (230, 220, 180))
    surface.blit(sub, sub.get_rect(center=(cx, cy + 52)))
