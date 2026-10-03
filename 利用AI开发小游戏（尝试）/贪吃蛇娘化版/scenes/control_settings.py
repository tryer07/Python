# -*- coding: utf-8 -*-
"""
scenes/control_settings.py —— 操作设置（按键绑定）

主菜单入口。玩家在这里改技能 1-6 与护盾的热键，或一键恢复默认。
绑定即时写入 config.controls（跨存档槽共享），战斗中同样可暂停改键。
"""

import pygame

from core.scene import Scene
from ui.button import Button
from ui.keybind_panel import KeybindPanel
from settings import (
    COLOR_ACCENT, COLOR_BG, COLOR_TEXT, COLOR_TEXT_DIM,
    FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
)


class ControlSettingsScene(Scene):
    """操作设置场景：改键 + 恢复默认。"""

    def enter(self):
        self.assets = self.game.assets
        self.game.audio.play_bgm("menu")
        # 确保处于纯按键捕获态（关掉可能残留的文本输入/输入法），
        # 否则中文输入法会拦截数字/字母键，导致改键收不到 KEYDOWN。
        try:
            self.game.set_text_input(False)
        except Exception:
            pass

        self.font_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)
        self.font_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.font_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))

        self.panel = KeybindPanel(self.game)
        self._layout()

    def _layout(self):
        cx = self.W // 2
        self.panel_w = min(self.s(680), int(self.W * 0.86))
        self.panel_x = cx - self.panel_w // 2
        self.panel_y = self.s(150)

        btn_y = self.panel_y + self.panel.height(self.s) + self.s(24)
        self.restore_btn = Button(
            "恢复默认按键", cx - self.s(330), btn_y, self.s(300), self.s(56),
            font_size=self.s(FONT_SIZE_SMALL), on_click=self._restore)
        self.back_btn = Button(
            "返回主菜单", cx + self.s(30), btn_y, self.s(300), self.s(56),
            font_size=self.s(FONT_SIZE_SMALL), on_click=self._on_back)

    def exit(self):
        self.game.input_capture = False

    def handle_events(self, events):
        # 面板在监听按键时，把输入捕获标志打开，让全局音量热键让路
        self.game.input_capture = self.panel.listening is not None
        for event in events:
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                    and self.panel.listening is None):
                self._on_back()
                continue
            if self.panel.handle_event(event):
                continue
            self.restore_btn.handle_event(event)
            self.back_btn.handle_event(event)

    def update(self, dt):
        pass

    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)
        cx = self.W // 2

        title = self.font_title.render("操作设置", True, COLOR_ACCENT)
        screen.blit(title, title.get_rect(center=(cx, self.s(66))))
        sub = self.font_small.render(
            "点击某一行后按下新按键即可改键（护盾也可绑鼠标键）· 绑定全局生效 · ESC 返回",
            True, COLOR_TEXT_DIM)
        screen.blit(sub, sub.get_rect(center=(cx, self.s(112))))

        self.panel.draw(screen, self.panel_x, self.panel_y, self.panel_w,
                        self.s, self.font_body, self.font_small)
        self.restore_btn.draw(screen)
        self.back_btn.draw(screen)

    def _restore(self):
        self.game.controls.reset()
        self.panel.message = "已恢复默认按键"
        self.panel.listening = None

    def _on_back(self):
        self.game.input_capture = False
        self.game.change_scene("main_menu")
