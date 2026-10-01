# -*- coding: utf-8 -*-
"""
scenes/main_menu.py —— 主菜单
"""

import pygame

from core.scene import Scene
from ui.button import Button
from settings import (
    COLOR_BG, COLOR_ACCENT, COLOR_TEXT, COLOR_TEXT_DIM,
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
        start_y = self.s(400)
        gap = self.s(82)

        self.buttons = [
            Button("开始战斗", cx - btn_w // 2, start_y,
                   btn_w, btn_h, on_click=lambda: self._go("battle")),
            Button("角色选择", cx - btn_w // 2, start_y + gap,
                   btn_w, btn_h, on_click=lambda: self._go("character_select")),
            Button("场景选择", cx - btn_w // 2, start_y + gap * 2,
                   btn_w, btn_h, on_click=lambda: self._go("scene_select")),
            Button("蛇娘召集", cx - btn_w // 2, start_y + gap * 3,
                   btn_w, btn_h, on_click=lambda: self._go("gacha")),
            Button("显示设置", cx - btn_w // 2, start_y + gap * 4,
                   btn_w, btn_h, on_click=lambda: self._go("display_settings")),
            Button("退出游戏", cx - btn_w // 2, start_y + gap * 5,
                   btn_w, btn_h, on_click=self._on_quit),
        ]

        self.time = 0.0

        # 角色名 / 场景名一次性读进缓存，避免 draw() 每帧重复 open() 而泄漏文件句柄
        self._char_names = self._load_names("characters.json")
        self._scene_names = self._load_names("scenes.json")

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

    # ---------------------------------------------------------------- 绘制
    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)
        self._draw_background(screen)

        cx = self.W // 2

        title = self.font_title.render("贪吃蛇娘化版", True, COLOR_ACCENT)
        self._shadowed(screen, title, title.get_rect(center=(cx, self.s(168))))

        subtitle = self.font_subtitle.render("娘化贪吃蛇 · 成长对战", True, COLOR_TEXT_DIM)
        screen.blit(subtitle, subtitle.get_rect(center=(cx, self.s(244))))

        pygame.draw.line(screen, COLOR_ACCENT,
                         (cx - self.s(200), self.s(300)),
                         (cx + self.s(200), self.s(300)), 2)

        # 当前出战角色
        save = self.game.save_manager.data
        char_id = save.get("selected_character", "sakura")
        scene_id = save.get("selected_scene", "campus_garden")

        char_name = self._char_names.get(char_id, char_id)
        scene_name = self._scene_names.get(scene_id, scene_id)
        t = self.font_small.render(
            f"出战角色：{char_name}    ·    当前场景：{scene_name}", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(cx, self.s(336))))

        for b in self.buttons:
            b.draw(screen)

        p = save.get("progress", {})
        info_text = (
            f"星尘 {save.get('currency', 0)}    |    "
            f"角色 {len(save.get('owned_characters', []))}    |    "
            f"最高分 {p.get('best_score', 0)}    |    "
            f"总击杀 {p.get('total_kills', 0)}    |    "
            f"游玩 {p.get('total_runs', 0)} 局"
        )
        t = self.font_small.render(info_text, True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(cx, self.H - self.s(44))))

        t = self.font_small.render("v0.1.0  ·  F11 全屏", True, (92, 92, 118))
        screen.blit(t, t.get_rect(midleft=(self.s(20), self.H - self.s(24))))

    def _draw_background(self, screen):
        bg = self.assets.get_scaled("backgrounds/campus_garden.png", width=self.W)
        screen.blit(bg, (0, self.s(-30)))
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((14, 12, 22, 186))
        screen.blit(veil, (0, 0))

        grid_color = (34, 32, 52)
        step = self.s(60)
        for x in range(0, self.W, step):
            pygame.draw.line(screen, grid_color, (x, 0), (x, self.H))
        for y in range(0, self.H, step):
            pygame.draw.line(screen, grid_color, (0, y), (self.W, y))

    @staticmethod
    def _shadowed(screen, surf, rect):
        shadow = surf.copy()
        shadow.fill((0, 0, 0, 170), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(shadow, rect.move(3, 4))
        screen.blit(surf, rect)

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
