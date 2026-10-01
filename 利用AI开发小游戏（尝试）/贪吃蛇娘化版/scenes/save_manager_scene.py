# -*- coding: utf-8 -*-
"""
scenes/save_manager_scene.py —— 存档管理

多存档槽管理界面：列出所有本地存档，支持新建、切换、重命名、删除。
底部返回主菜单。

命名支持「自由键盘输入」（含中文：进入命名态时临时恢复输入法关联，
收 pygame.TEXTINPUT 事件），也提供一排预设名 chips 一键填入；
离开命名态立即重新禁用输入法，避免打字候选框挡住游戏。
"""

import json
import os

import pygame

from core.scene import Scene
from ui.button import Button
from settings import (
    DATA_DIR,
    COLOR_BG, COLOR_ACCENT, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_GOLD,
    COLOR_DANGER, COLOR_GOOD,
    FONT_SIZE_TITLE, FONT_SIZE_SUBTITLE, FONT_SIZE_BODY, FONT_SIZE_SMALL,
)

PRESET_NAMES = [
    "存档 1", "存档 2", "存档 3", "存档 4", "存档 5",
    "樱花之旅", "霓虹夜行", "深海远征", "神域传说", "新的开始",
]
NAME_MAX_LEN = 12


class SaveManagerScene(Scene):
    """存档槽管理场景"""

    def enter(self):
        self.assets = self.game.assets
        self.game.audio.play_bgm("menu")
        self.font_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)
        self.font_sub = self.assets.get_font(self.s(FONT_SIZE_SUBTITLE))
        self.font_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.font_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))

        self.sm = self.game.save_manager
        self.char_names = self._load_char_names()

        # 交互状态：list（列表）| naming（新建命名）| renaming（重命名）| confirm_delete
        self.mode = "list"
        self.text_buffer = ""
        self.rename_target = None
        self.delete_target = None
        self.time = 0.0

        self._rebuild()

    def exit(self):
        # 离开场景时务必关掉文本输入态，免得输入法关联残留到别的场景
        self.game.set_text_input(False)

    # ---------------------------------------------------------------- 数据
    def _load_char_names(self):
        result = {}
        path = os.path.join(DATA_DIR, "characters.json")
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

    def _rebuild(self):
        """刷新槽列表与按钮（任何增删改切换后调用）。"""
        self.slots = self.sm.list_slots()
        self.active_id = self.sm.active_slot
        self._build_buttons()

    def _card_metrics(self):
        n = max(1, len(self.slots))
        card_w = self.s(820)
        gap = self.s(14)
        y0 = self.s(176)
        avail = self.H - y0 - self.s(120)
        card_h = self.s(92)
        if n * card_h + (n - 1) * gap > avail:
            card_h = max(self.s(58), (avail - (n - 1) * gap) // n)
        x0 = (self.W - card_w) // 2
        return x0, y0, card_w, card_h, gap

    def _card_rects(self):
        x0, y0, cw, ch, gap = self._card_metrics()
        return [pygame.Rect(x0, y0 + i * (ch + gap), cw, ch)
                for i in range(len(self.slots))]

    def _build_buttons(self):
        self.buttons = []
        self.overlay_buttons = []

        rects = self._card_rects()
        for rect, slot in zip(rects, self.slots):
            sid = slot["id"]
            is_active = (sid == self.active_id)
            bh = min(self.s(40), rect.h - self.s(16))
            by = rect.centery - bh // 2
            # 从右往左排：删除、重命名、切换
            del_w = self.s(72)
            ren_w = self.s(88)
            sw_w = self.s(96)
            margin = self.s(16)
            gapb = self.s(10)

            del_x = rect.right - margin - del_w
            self.buttons.append(Button(
                "删除", del_x, by, del_w, bh, font_size=self.s(FONT_SIZE_SMALL),
                bg_color=(70, 40, 50), hover_color=(110, 55, 65),
                text_color=COLOR_DANGER,
                on_click=lambda s=sid: self._ask_delete(s)))

            ren_x = del_x - gapb - ren_w
            self.buttons.append(Button(
                "重命名", ren_x, by, ren_w, bh, font_size=self.s(FONT_SIZE_SMALL),
                on_click=lambda s=sid: self._start_rename(s)))

            if not is_active:
                sw_x = ren_x - gapb - sw_w
                self.buttons.append(Button(
                    "切换", sw_x, by, sw_w, bh, font_size=self.s(FONT_SIZE_SMALL),
                    bg_color=(40, 62, 50), hover_color=(55, 92, 70),
                    text_color=COLOR_GOOD,
                    on_click=lambda s=sid: self._do_switch(s)))

        # 底部：新建存档 / 返回主菜单
        bw, bh = self.s(220), self.s(54)
        by = self.H - self.s(86)
        self.buttons.append(Button(
            "＋ 新建存档", (self.W - bw) // 2 - bw - self.s(20), by, bw, bh,
            font_size=self.s(FONT_SIZE_BODY),
            on_click=self._start_create))
        self.buttons.append(Button(
            "返回主菜单", (self.W - bw) // 2 + self.s(20), by, bw, bh,
            font_size=self.s(FONT_SIZE_BODY),
            on_click=self._on_back))

    # ---------------------------------------------------------------- 输入
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.mode == "naming" or self.mode == "renaming":
                    if event.key == pygame.K_ESCAPE:
                        self._cancel_overlay()
                        continue
                    if event.key == pygame.K_BACKSPACE:
                        self.text_buffer = self.text_buffer[:-1]
                        continue
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self._confirm_name()
                        continue
                elif self.mode == "confirm_delete":
                    if event.key == pygame.K_ESCAPE:
                        self.mode = "list"
                        self.delete_target = None
                        continue
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self._do_delete()
                        continue
                else:  # list
                    if event.key == pygame.K_ESCAPE:
                        self._on_back()
                        return

            active_buttons = self.overlay_buttons if self.mode != "list" else self.buttons
            for b in active_buttons:
                b.handle_event(event)
            # 自由输入：IME 提交的文本（含中文）走 TEXTINPUT 事件
            if event.type == pygame.TEXTINPUT and self.mode in ("naming", "renaming"):
                for ch in event.text:
                    if len(self.text_buffer) >= NAME_MAX_LEN:
                        break
                    if ch.isprintable():
                        self.text_buffer += ch

    def update(self, dt):
        self.time += dt

    def wants_movement_keys(self):
        # 命名态占用键盘：让全局音量热键别来抢按键
        return self.mode in ("naming", "renaming")

    # ---------------------------------------------------------------- 回调
    def _on_back(self):
        self.game.change_scene("main_menu")

    def _start_create(self):
        self.mode = "naming"
        self.text_buffer = ""
        self._build_overlay_buttons()
        self.game.set_text_input(True)

    def _start_rename(self, slot_id):
        self.mode = "renaming"
        self.rename_target = slot_id
        # 输入框预填该槽当前名字，改起来更顺手
        self.text_buffer = next((s["name"] for s in self.slots if s["id"] == slot_id), "")
        self.text_buffer = self.text_buffer[:NAME_MAX_LEN]
        self._build_overlay_buttons()
        self.game.set_text_input(True)

    def _confirm_name(self):
        name = self.text_buffer.strip()
        if self.mode == "naming":
            self.sm.create_slot(name or f"存档 {len(self.slots) + 1}", activate=True)
        elif self.mode == "renaming" and self.rename_target:
            if name:
                self.sm.rename_slot(self.rename_target, name)
        self._cancel_overlay()
        self._rebuild()

    def _ask_delete(self, slot_id):
        self.mode = "confirm_delete"
        self.delete_target = slot_id
        self._build_overlay_buttons()

    def _do_delete(self):
        if self.delete_target:
            self.sm.delete_slot(self.delete_target)
        self.mode = "list"
        self.delete_target = None
        self._rebuild()

    def _do_switch(self, slot_id):
        self.sm.switch_slot(slot_id)
        self._rebuild()

    def _cancel_overlay(self):
        self.mode = "list"
        self.rename_target = None
        self.delete_target = None
        self.game.set_text_input(False)

    def _fill_preset(self, name):
        """点预设名 chip：直接填入输入框（仍可继续手打修改）。"""
        self.text_buffer = name[:NAME_MAX_LEN]
        self.game.audio.play("ui_click")

    def _build_overlay_buttons(self):
        self.overlay_buttons = []
        pw, ph = self.s(820), self.s(430)
        px, py = (self.W - pw) // 2, (self.H - ph) // 2

        if self.mode in ("naming", "renaming"):
            # 预设名 chips：5 个一行，点击填入输入框
            cols = 5
            gap = self.s(12)
            chip_w = (pw - self.s(80) - (cols - 1) * gap) // cols
            chip_h = self.s(44)
            for i, nm in enumerate(PRESET_NAMES):
                c, r = i % cols, i // cols
                self.overlay_buttons.append(Button(
                    nm, px + self.s(40) + c * (chip_w + gap),
                    py + self.s(200) + r * (chip_h + gap), chip_w, chip_h,
                    font_size=self.s(FONT_SIZE_SMALL - 2),
                    on_click=lambda n=nm: self._fill_preset(n)))
            bw, bh = self.s(150), self.s(52)
            by = py + ph - self.s(76)
            self.overlay_buttons.append(Button(
                "确认", px + pw // 2 - bw - self.s(12), by, bw, bh,
                font_size=self.s(FONT_SIZE_BODY),
                bg_color=(40, 62, 50), hover_color=(55, 92, 70), text_color=COLOR_GOOD,
                on_click=self._confirm_name))
            self.overlay_buttons.append(Button(
                "取消", px + pw // 2 + self.s(12), by, bw, bh,
                font_size=self.s(FONT_SIZE_BODY),
                on_click=self._cancel_overlay))
        elif self.mode == "confirm_delete":
            bw, bh = self.s(150), self.s(54)
            by = py + ph - self.s(84)
            self.overlay_buttons.append(Button(
                "删除", px + pw // 2 - bw - self.s(12), by, bw, bh,
                font_size=self.s(FONT_SIZE_BODY),
                bg_color=(70, 40, 50), hover_color=(110, 55, 65), text_color=COLOR_DANGER,
                on_click=self._do_delete))
            self.overlay_buttons.append(Button(
                "取消", px + pw // 2 + self.s(12), by, bw, bh,
                font_size=self.s(FONT_SIZE_BODY),
                on_click=self._cancel_overlay))

        self._overlay_rect = pygame.Rect(px, py, pw, ph)

    # ---------------------------------------------------------------- 绘制
    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)

        bg = self.assets.get_scaled("backgrounds/campus_garden.png", width=self.W)
        screen.blit(bg, (0, self.s(-40)))
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((14, 12, 22, 210))
        screen.blit(veil, (0, 0))

        title = self.font_title.render("存档管理", True, COLOR_ACCENT)
        screen.blit(title, title.get_rect(center=(self.W // 2, self.s(72))))
        cur = self.font_small.render(
            f"当前存档：{self.sm.active_slot_name}    ·    共 {len(self.slots)} 个存档槽",
            True, COLOR_TEXT_DIM)
        screen.blit(cur, cur.get_rect(center=(self.W // 2, self.s(126))))

        rects = self._card_rects()
        for rect, slot in zip(rects, self.slots):
            self._draw_card(screen, rect, slot)

        if self.mode == "list":
            for b in self.buttons:
                b.draw(screen)
        else:
            # 列表按钮淡出，绘制浮层
            for b in self.buttons:
                b.draw(screen)
            dim = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 150))
            screen.blit(dim, (0, 0))
            self._draw_overlay(screen)
            for b in self.overlay_buttons:
                b.draw(screen)

    @staticmethod
    def _fit(font, text, max_w):
        """超宽就截断加省略号，保证文字不出安全区、不互相遮挡。"""
        if max_w <= 0 or font.size(text)[0] <= max_w:
            return text
        while text and font.size(text + "…")[0] > max_w:
            text = text[:-1]
        return text + "…"

    def _draw_card(self, screen, rect, slot):
        is_active = slot["id"] == self.active_id
        pygame.draw.rect(screen, (34, 30, 46), rect, border_radius=self.s(12))

        # 右侧按钮区预留：名字 / 信息行都截断到这个安全宽度内
        btn_zone = self.s(200) if is_active else self.s(300)
        text_max_w = rect.w - self.s(44) - btn_zone

        name_color = COLOR_GOLD if is_active else COLOR_TEXT
        name = self.font_body.render(self._fit(self.font_body, slot["name"], text_max_w),
                                     True, name_color)
        screen.blit(name, name.get_rect(midleft=(rect.x + self.s(22), rect.y + self.s(30))))

        # 「使用中」标记跟在名字同一行后面，不再压到下面的信息行
        if is_active:
            tag = self.font_small.render("● 使用中", True, COLOR_GOOD)
            screen.blit(tag, tag.get_rect(
                midleft=(rect.x + self.s(22) + name.get_width() + self.s(16),
                         rect.y + self.s(32))))

        char_name = self.char_names.get(slot["selected_character"], slot["selected_character"])
        cleared = len(slot.get("story_cleared", []) or [])
        info = (f"出战 {char_name}    ·    进度 第{slot['story_unlocked']}关"
                f"    ·    通关 {cleared}    ·    星尘 {slot['currency']}"
                f"    ·    {slot['total_runs']} 局")
        t = self.font_small.render(self._fit(self.font_small, info, text_max_w),
                                   True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(midleft=(rect.x + self.s(22), rect.y + rect.h - self.s(28))))

        border = COLOR_ACCENT if is_active else (60, 56, 78)
        bw = max(1, self.s(3)) if is_active else max(1, self.s(2))
        pygame.draw.rect(screen, border, rect, bw, border_radius=self.s(12))

    def _draw_overlay(self, screen):
        rect = getattr(self, "_overlay_rect", None)
        if rect is None:
            return
        pygame.draw.rect(screen, (28, 26, 42), rect, border_radius=self.s(14))
        pygame.draw.rect(screen, COLOR_ACCENT, rect, max(1, self.s(2)), border_radius=self.s(14))

        if self.mode in ("naming", "renaming"):
            head = "新建存档" if self.mode == "naming" else "重命名存档"
            t = self.font_sub.render(head, True, COLOR_ACCENT)
            screen.blit(t, t.get_rect(center=(rect.centerx, rect.y + self.s(44))))

            # 输入框：显示已输入内容 + 闪烁光标
            ib = pygame.Rect(rect.x + self.s(40), rect.y + self.s(84),
                             rect.w - self.s(80), self.s(64))
            pygame.draw.rect(screen, (20, 18, 30), ib, border_radius=self.s(10))
            pygame.draw.rect(screen, COLOR_ACCENT, ib, max(1, self.s(2)),
                             border_radius=self.s(10))
            if self.text_buffer:
                shown = self._fit(self.font_body, self.text_buffer, ib.w - self.s(32))
                ts = self.font_body.render(shown, True, COLOR_GOLD)
                screen.blit(ts, ts.get_rect(midleft=(ib.x + self.s(16), ib.centery)))
                if int(self.time * 2) % 2 == 0:
                    cx = ib.x + self.s(16) + ts.get_width() + self.s(4)
                    pygame.draw.rect(screen, COLOR_TEXT,
                                     (cx, ib.y + self.s(12), max(1, self.s(2)),
                                      ib.h - self.s(24)))
            else:
                ph_t = self.font_small.render("直接键盘输入名称（支持中文）",
                                               True, (110, 106, 130))
                screen.blit(ph_t, ph_t.get_rect(midleft=(ib.x + self.s(16), ib.centery)))

            lab = self.font_small.render("预设名（点击填入）：", True, COLOR_TEXT_DIM)
            screen.blit(lab, (rect.x + self.s(40), rect.y + self.s(168)))

            hint = self.font_small.render(
                "直接打字命名    ·    Backspace 删除    ·    Enter 确认    ·    Esc 取消",
                True, COLOR_TEXT_DIM)
            screen.blit(hint, hint.get_rect(center=(rect.centerx, rect.y + self.s(322))))
        elif self.mode == "confirm_delete":
            nm = next((s["name"] for s in self.slots if s["id"] == self.delete_target), "")
            t = self.font_sub.render("确定删除存档？", True, COLOR_DANGER)
            screen.blit(t, t.get_rect(center=(rect.centerx, rect.y + self.s(56))))
            t2 = self.font_body.render(f"「{nm}」", True, COLOR_GOLD)
            screen.blit(t2, t2.get_rect(center=(rect.centerx, rect.y + self.s(110))))
            t3 = self.font_small.render("此操作不可撤销", True, COLOR_TEXT_DIM)
            screen.blit(t3, t3.get_rect(center=(rect.centerx, rect.y + self.s(150))))
