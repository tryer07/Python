import pygame
from core.scene import Scene
from ui.button import Button
from ui.slider import Slider
from settings import (
    COLOR_BG, COLOR_ACCENT, COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_BUTTON_BG, FONT_SIZE_TITLE, FONT_SIZE_BODY, FONT_SIZE_SMALL
)


class DisplaySettingsScene(Scene):
    """显示设置场景：选择分辨率和窗口模式"""

    def enter(self):
        self.assets = self.game.assets
        self.game.audio.play_bgm("menu")
        self.font_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)
        self.font_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.font_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))

        center_x = self.W // 2

        self.back_btn = Button(
            "返回主菜单", self.s(30), self.H - self.s(80), self.s(200), self.s(50),
            font_size=self.s(FONT_SIZE_SMALL), on_click=self._on_back
        )

        # 窗口模式选择
        self.mode_buttons = []
        modes = [("windowed", "窗口模式"), ("borderless", "无边框窗口"), ("fullscreen", "全屏")]
        mode_start_x = center_x - self.s(350)
        for i, (mode_id, mode_name) in enumerate(modes):
            btn = Button(
                mode_name, mode_start_x + i * self.s(240), self.s(220),
                self.s(220), self.s(55),
                font_size=self.s(FONT_SIZE_SMALL),
                on_click=lambda m=mode_id: self._set_mode(m)
            )
            self.mode_buttons.append((mode_id, btn))

        # 分辨率选择
        self.res_buttons = []
        available = self.game.get_available_resolutions()
        res_start_x = center_x - (len(available) * self.s(170)) // 2
        for i, (w, h, label) in enumerate(available):
            btn = Button(
                f"{label} ({w}x{h})", res_start_x + i * self.s(175), self.s(400),
                self.s(165), self.s(55),
                font_size=self.s(14),
                on_click=lambda r=(w, h): self._set_resolution(r)
            )
            self.res_buttons.append(((w, h), btn))

        # 音量滑块：拖动即时生效（不写盘），松手才落盘一次，避免高频 IO
        st = self.game.save_manager.get("settings", {}) or {}
        slider_w, slider_h, slider_y = self.s(430), self.s(44), self.s(520)
        self.bgm_slider = Slider(
            "音乐", center_x - self.s(455), slider_y, slider_w, slider_h,
            value=float(st.get("bgm_volume", 0.7)), font_size=self.s(FONT_SIZE_SMALL),
            on_change=lambda v: self.game.audio.set_bgm_volume(v, persist=False),
            on_release=self.game.audio.save_volumes, focus_key="bgm",
        )
        self.sfx_slider = Slider(
            "音效", center_x + self.s(25), slider_y, slider_w, slider_h,
            value=float(st.get("sfx_volume", 0.8)), font_size=self.s(FONT_SIZE_SMALL),
            on_change=lambda v: self.game.audio.set_sfx_volume(v, persist=False),
            on_release=self.game.audio.save_volumes, focus_key="sfx",
        )

        # 恢复默认
        self.apply_default_btn = Button(
            "恢复默认（自动适配）", center_x - self.s(160), self.s(600),
            self.s(320), self.s(55),
            font_size=self.s(FONT_SIZE_SMALL), on_click=self._reset_default
        )

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._on_back()
            self.back_btn.handle_event(event)
            self.apply_default_btn.handle_event(event)
            for _, btn in self.mode_buttons:
                btn.handle_event(event)
            for _, btn in self.res_buttons:
                btn.handle_event(event)
            self.bgm_slider.handle_event(event)
            self.sfx_slider.handle_event(event)

    def update(self, dt):
        pass

    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)

        center_x = self.W // 2

        title = self.font_title.render("显示设置", True, COLOR_ACCENT)
        screen.blit(title, title.get_rect(center=(center_x, self.s(60))))

        # 当前状态
        current_mode = self.game.display_mode
        current_res = self.game.display_resolution
        mode_names = {"windowed": "窗口模式", "borderless": "无边框窗口", "fullscreen": "全屏"}
        res_text = f"{current_res[0]}x{current_res[1]}" if current_res != (0, 0) else "自动适配"
        status = (f"当前: {mode_names.get(current_mode, current_mode)}  |  "
                  f"分辨率: {res_text}  |  "
                  f"窗口: {self.game.window_width}x{self.game.window_height}")
        status_surf = self.font_small.render(status, True, COLOR_TEXT_DIM)
        screen.blit(status_surf, status_surf.get_rect(center=(center_x, self.s(130))))

        mode_label = self.font_body.render("【窗口模式】", True, COLOR_TEXT)
        screen.blit(mode_label, mode_label.get_rect(center=(center_x, self.s(190))))

        for mode_id, btn in self.mode_buttons:
            if mode_id == current_mode:
                btn.bg_color = (0, 100, 80)
                btn.accent_color = COLOR_ACCENT
            else:
                btn.bg_color = COLOR_BUTTON_BG
                btn.accent_color = COLOR_ACCENT
            btn.draw(screen)

        res_label = self.font_body.render("【窗口分辨率】（仅窗口模式生效）", True, COLOR_TEXT)
        screen.blit(res_label, res_label.get_rect(center=(center_x, self.s(360))))

        for res, btn in self.res_buttons:
            if res == current_res:
                btn.bg_color = (0, 100, 80)
            else:
                btn.bg_color = COLOR_BUTTON_BG
            btn.draw(screen)

        audio_label = self.font_body.render("【音频音量】", True, COLOR_TEXT)
        screen.blit(audio_label, audio_label.get_rect(center=(center_x, self.s(488))))
        # 方向键热键在主循环里改的是 AudioManager 的值，这里让滑块跟随显示，
        # 避免“按了热键音量变了、滑块却停在原位”。拖拽中的滑块不覆盖，免得打架。
        a = self.game.audio
        if not self.bgm_slider.dragging:
            self.bgm_slider.value = a.bgm_volume
        if not self.sfx_slider.dragging:
            self.sfx_slider.value = a.sfx_volume
        self.bgm_slider.draw(screen)
        self.sfx_slider.draw(screen)

        self.apply_default_btn.draw(screen)

        hint = self.font_small.render(
            "提示: 鼠标点选滑块后，↑/→ 增大、↓/← 减小（±10，长按连调）  |  拖动即时保存  |  ESC 返回  |  F11 全屏",
            True, COLOR_TEXT_DIM
        )
        screen.blit(hint, hint.get_rect(center=(center_x, self.s(690))))

        self.back_btn.draw(screen)

    def _set_mode(self, mode):
        self.game.set_display(mode=mode)

    def _set_resolution(self, resolution):
        self.game.set_display(mode="windowed", resolution=resolution)

    def _reset_default(self):
        self.game.set_display(mode="windowed", resolution=(0, 0))

    def _on_back(self):
        self.game.change_scene("main_menu")