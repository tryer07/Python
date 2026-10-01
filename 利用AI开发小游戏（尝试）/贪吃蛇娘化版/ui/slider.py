# -*- coding: utf-8 -*-
"""
ui/slider.py —— 可拖拽的水平滑块控件

用于显示设置里的音量调节。风格复用 Button 的配色，构造方式也尽量对齐，
方便在场景里按 self.s() 缩放后直接摆放。
"""

import pygame

from settings import (
    COLOR_ACCENT, COLOR_BUTTON_BG, COLOR_TEXT, COLOR_TEXT_DIM, FONT_SIZE_BODY,
)


class Slider:
    """横向滑块：左边标签、中间轨道+滑块、右边百分比。value 取值 0.0~1.0。"""

    def __init__(self, label, x, y, width, height, value=0.5,
                 font_size=FONT_SIZE_BODY, on_change=None, on_release=None,
                 focus_key=None):
        self.label = label
        self.rect = pygame.Rect(x, y, width, height)
        self.value = max(0.0, min(1.0, float(value)))
        self.on_change = on_change
        self.on_release = on_release
        # focus_key（"bgm"/"sfx"）：鼠标点本滑块时，把热键调节目标切到自己。
        self.focus_key = focus_key
        self.dragging = False

        self.font = pygame.font.SysFont("Microsoft YaHei", font_size, bold=True)

        # 轨道区：标签占左侧一段，百分比占右侧一段，中间是轨道
        self._label_w = int(width * 0.24)
        self._value_w = int(width * 0.16)

    # ------------------------------------------------------------ 几何
    @property
    def _track_rect(self):
        left = self.rect.x + self._label_w
        right = self.rect.right - self._value_w
        cy = self.rect.centery
        th = max(4, int(self.rect.height * 0.18))
        return pygame.Rect(left, cy - th // 2, max(10, right - left), th)

    def _value_from_x(self, mx):
        tr = self._track_rect
        t = (mx - tr.left) / max(1, tr.width)
        return max(0.0, min(1.0, t))

    def _set_value(self, v):
        v = max(0.0, min(1.0, float(v)))
        if abs(v - self.value) < 1e-4:
            return
        self.value = v
        if self.on_change:
            self.on_change(self.value)

    # ------------------------------------------------------------ 事件
    def handle_event(self, event):
        from core.audio_manager import get_audio

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 点一下先把“热键调节目标”切到这个滑块（音乐 or 音效）
            if self.focus_key and self.rect.collidepoint(event.pos):
                get_audio().volume_focus = self.focus_key
            # 命中整个控件高度范围即可开始拖拽（比只命中细轨道好点）
            hit = self._track_rect.inflate(0, self.rect.height)
            if hit.collidepoint(event.pos):
                self.dragging = True
                self._set_value(self._value_from_x(event.pos[0]))
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_value(self._value_from_x(event.pos[0]))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            get_audio().play("ui_click")
            if self.on_release:
                self.on_release()
        return False

    # ------------------------------------------------------------ 绘制
    def draw(self, surface):
        from core.audio_manager import get_audio
        tr = self._track_rect

        # 被选中（热键当前调的就是它）时，标签变主色并加个◀ 标记
        focused = (self.focus_key is not None
                   and get_audio().volume_focus == self.focus_key)
        lab_color = COLOR_ACCENT if focused else COLOR_TEXT_DIM
        lab_text = ("◀ " + self.label) if focused else self.label
        lab = self.font.render(lab_text, True, lab_color)
        surface.blit(lab, lab.get_rect(midleft=(self.rect.x, self.rect.centery)))

        # 轨道底
        pygame.draw.rect(surface, COLOR_BUTTON_BG, tr,
                         border_radius=max(2, tr.height // 2))
        # 已填充段
        fill_w = int(tr.width * self.value)
        if fill_w > 0:
            fill = pygame.Rect(tr.x, tr.y, fill_w, tr.height)
            pygame.draw.rect(surface, COLOR_ACCENT, fill,
                             border_radius=max(2, tr.height // 2))

        # 滑块圆点
        kx = tr.x + int(tr.width * self.value)
        kr = max(7, int(self.rect.height * 0.28))
        pygame.draw.circle(surface, COLOR_ACCENT, (kx, tr.centery), kr)
        pygame.draw.circle(surface, COLOR_TEXT, (kx, tr.centery), kr, 2)

        # 百分比
        vt = self.font.render(f"{int(round(self.value * 100))}%", True, COLOR_TEXT)
        surface.blit(vt, vt.get_rect(midleft=(self.rect.right - self._value_w + 6,
                                             self.rect.centery)))
