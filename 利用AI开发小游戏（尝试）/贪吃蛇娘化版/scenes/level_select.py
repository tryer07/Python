# -*- coding: utf-8 -*-
"""
scenes/level_select.py —— 关卡选择

上半部：4 个剧情关卡卡（按存档 story_unlocked 显示 锁定 / 可玩 / 已通关），
        点击可玩关卡 -> 设 game.pending_run={"mode":"story","level":N} 进入 battle。
下半部：无尽模式入口 -> 进入 scene_select 选图（选图后以 endless 模式开战）。

关卡表读 data/levels.json，场景缩略图 / 名称读 data/scenes.json。
"""

import json
import os

import pygame

from core.scene import Scene
from ui.button import Button
from ui.suspend_prompt import SuspendPrompt
from settings import (
    DATA_DIR, ASSETS_DIR,
    COLOR_BG, COLOR_ACCENT, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_GOLD,
    COLOR_GOOD, COLOR_DANGER,
    FONT_SIZE_TITLE, FONT_SIZE_SUBTITLE, FONT_SIZE_BODY, FONT_SIZE_SMALL,
)

CARD_W, CARD_H = 430, 236
CARD_GAP = 34


class LevelSelectScene(Scene):
    """关卡选择：剧情序列 + 无尽入口"""

    def enter(self):
        self.assets = self.game.assets
        self.game.audio.play_bgm("menu")
        self.font_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)
        self.font_sub = self.assets.get_font(self.s(FONT_SIZE_SUBTITLE))
        self.font_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.font_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))

        self.levels = self._load_levels()
        self.scenes = {s["id"]: s for s in self._load_scenes()}
        prog = self.game.save_manager.get_story_progress()
        self.unlocked = int(prog.get("unlocked", 1))
        self.cleared = set(prog.get("cleared", []))

        bw, bh = self.s(240), self.s(58)
        cx = self.W // 2
        self.endless_btn = Button(
            "无尽模式", cx - bw - self.s(16), self.H - self.s(96), bw, bh,
            font_size=self.s(FONT_SIZE_BODY),
            bg_color=(48, 40, 66), hover_color=(70, 58, 96),
            on_click=self._go_endless)
        self.back_btn = Button(
            "返回主菜单", cx + self.s(16), self.H - self.s(96), bw, bh,
            font_size=self.s(FONT_SIZE_BODY),
            on_click=self._on_back)
        self.hover_index = None
        self.time = 0.0
        # 「检测到未完成对局」弹窗（按 剧情+场景 各自独立检测）
        self.suspend_ui = SuspendPrompt(self)

    def exit(self):
        pass

    # ---------------------------------------------------------------- 数据
    def _load_levels(self):
        path = os.path.join(DATA_DIR, "levels.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data.get("levels", data) if isinstance(data, dict) else data
                if isinstance(items, list) and items:
                    return [lv for lv in items if isinstance(lv, dict)]
            except (json.JSONDecodeError, IOError) as e:
                print(f"[关卡表读取失败] {e}")
        return []

    def _load_scenes(self):
        path = os.path.join(DATA_DIR, "scenes.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
            except (json.JSONDecodeError, IOError):
                pass
        return []

    @staticmethod
    def _asset_exists(rel_path):
        return bool(rel_path) and os.path.exists(
            os.path.join(ASSETS_DIR, rel_path.replace("/", os.sep)))

    # ---------------------------------------------------------------- 布局
    def _cards(self):
        n = len(self.levels)
        cw, ch = self.s(CARD_W), self.s(CARD_H)
        cg = self.s(CARD_GAP)
        cols = 2 if n > 1 else 1
        rows = (n + cols - 1) // cols
        total_w = cols * cw + (cols - 1) * cg
        total_h = rows * ch + (rows - 1) * cg
        x0 = (self.W - total_w) // 2
        y0 = self.s(168)
        # 垂直居中于标题与底部按钮之间
        avail_top = self.s(168)
        avail_bot = self.H - self.s(120)
        if avail_bot - avail_top > total_h:
            y0 = avail_top + (avail_bot - avail_top - total_h) // 2
        out = []
        for i, lv in enumerate(self.levels):
            c, r = i % cols, i // cols
            rect = pygame.Rect(x0 + c * (cw + cg), y0 + r * (ch + cg), cw, ch)
            out.append((i, rect, lv))
        return out

    def _status(self, lv):
        idx = int(lv.get("index", 0))
        if idx in self.cleared:
            return "cleared"
        if idx <= self.unlocked:
            return "open"
        return "locked"

    @staticmethod
    def _fit(font, text, max_w):
        """超宽截断加省略号，保证描述文字不溢出卡片。"""
        if max_w <= 0 or font.size(text)[0] <= max_w:
            return text
        while text and font.size(text + "…")[0] > max_w:
            text = text[:-1]
        return text + "…"

    # ---------------------------------------------------------------- 输入
    def handle_events(self, events):
        # 挂起弹窗为模态：开着时把全部事件交给它，屏蔽卡片/按钮
        if self.suspend_ui.active:
            for event in events:
                self.suspend_ui.handle_event(event)
            return
        cards = self._cards()
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._on_back()
                return
            if event.type == pygame.MOUSEMOTION:
                self.hover_index = None
                for i, rect, _lv in cards:
                    if rect.collidepoint(event.pos):
                        self.hover_index = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect, lv in cards:
                    if rect.collidepoint(event.pos):
                        self._on_card_click(lv)
                        return
            self.endless_btn.handle_event(event)
            self.back_btn.handle_event(event)

    def update(self, dt):
        self.time += dt

    def _on_card_click(self, lv):
        status = self._status(lv)
        if status == "locked":
            self.game.audio.play("gacha_error", throttle=0.1)
            return
        idx = int(lv.get("index", 1))
        scene_id = lv.get("scene", "campus_garden")
        # 该「剧情+场景」若有保存的挂起进度，先问玩家继续还是重开
        if self.suspend_ui.open_if_exists(
                "story", scene_id, on_new=lambda i=idx: self._start_story(i)):
            return
        self._start_story(idx)

    def _start_story(self, idx):
        self.game.pending_run = {"mode": "story", "level": idx}
        self.game.change_scene("battle")

    def _go_endless(self):
        self.game.change_scene("scene_select")

    def _on_back(self):
        self.game.change_scene("main_menu")

    # ---------------------------------------------------------------- 绘制
    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)
        bg = self.assets.get_scaled("backgrounds/campus_garden.png", width=self.W)
        screen.blit(bg, (0, self.s(-40)))
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((14, 12, 22, 208))
        screen.blit(veil, (0, 0))

        title = self.font_title.render("关卡选择", True, COLOR_ACCENT)
        screen.blit(title, title.get_rect(center=(self.W // 2, self.s(66))))
        sub = self.font_small.render(
            "剧情关卡：撑过 15 分钟并击败 Boss 通关，解锁下一关    ·    无尽模式：纯生存刷分",
            True, COLOR_TEXT_DIM)
        screen.blit(sub, sub.get_rect(center=(self.W // 2, self.s(116))))

        for i, rect, lv in self._cards():
            self._draw_card(screen, i, rect, lv)

        self.endless_btn.draw(screen)
        self.back_btn.draw(screen)
        self.suspend_ui.draw(screen)

    def _draw_card(self, screen, index, rect, lv):
        status = self._status(lv)
        hovered = self.hover_index == index
        pygame.draw.rect(screen, (34, 30, 46), rect, border_radius=self.s(12))

        # 缩略图
        preview = pygame.Rect(rect.x + self.s(14), rect.y + self.s(14),
                              rect.w - self.s(28), self.s(120))
        sc = self.scenes.get(lv.get("scene", ""), {})
        bg_path = sc.get("bg", "")
        if self._asset_exists(bg_path):
            img = self.assets.get_scaled(bg_path, width=preview.w)
            # 居中裁剪到预览框；宽高都钳到实际表面内，避免 get_scaled 取整差 1
            # 像素导致 subsurface 越界（ValueError: ... outside surface area）。
            iw, ih = img.get_size()
            cw, ch = min(preview.w, iw), min(preview.h, ih)
            if cw < iw or ch < ih:
                img = img.subsurface(pygame.Rect((iw - cw) // 2, (ih - ch) // 2,
                                                 cw, ch)).copy()
            screen.blit(img, preview.topleft)
        else:
            accent = sc.get("accent", [120, 110, 150])
            pygame.draw.rect(screen, tuple(accent), preview, border_radius=self.s(8))

        ov = pygame.Surface(preview.size, pygame.SRCALPHA)
        ov.fill((0, 0, 0, 60 if status != "locked" else 150))
        screen.blit(ov, preview.topleft)

        # 序号角标
        badge = pygame.Rect(preview.x + self.s(10), preview.y + self.s(10),
                            self.s(56), self.s(30))
        pygame.draw.rect(screen, (20, 18, 30, 200), badge, border_radius=self.s(8))
        bt = self.font_small.render(f"第 {lv.get('index', '?')} 关", True, COLOR_TEXT)
        screen.blit(bt, bt.get_rect(center=badge.center))

        # 名字
        name_color = COLOR_TEXT_DIM if status == "locked" else COLOR_TEXT
        t = self.font_sub.render(lv.get("name", "???"), True, name_color)
        screen.blit(t, t.get_rect(midleft=(rect.x + self.s(18), rect.y + self.s(156))))

        # 状态标签
        if status == "cleared":
            label, lc = "已通关", COLOR_GOLD
        elif status == "open":
            label, lc = "可挑战", COLOR_GOOD
        else:
            label, lc = "未解锁", COLOR_DANGER
        st = self.font_small.render(label, True, lc)
        screen.blit(st, st.get_rect(midright=(rect.right - self.s(18), rect.y + self.s(156))))

        # 描述 / 解锁提示：截断到卡宽内，避免文字溢出卡片压到隔壁
        desc = lv.get("desc", "") if status != "locked" else lv.get("unlock_hint", "尚未解锁")
        desc = self._fit(self.font_small, desc, rect.w - self.s(36))
        dt = self.font_small.render(desc, True, COLOR_TEXT_DIM)
        screen.blit(dt, dt.get_rect(midleft=(rect.x + self.s(18), rect.y + self.s(192))))

        meta = f"场景：{sc.get('name', lv.get('scene', ''))}    ·    时长 15 分钟    ·    精英 ×4"
        mt = self.font_small.render(self._fit(self.font_small, meta, rect.w - self.s(36)),
                                    True, (120, 116, 150))
        screen.blit(mt, mt.get_rect(midleft=(rect.x + self.s(18), rect.y + self.s(216))))

        if status != "locked":
            border = COLOR_ACCENT if hovered else (90, 84, 116)
            bw = max(1, self.s(3)) if hovered else max(1, self.s(2))
        else:
            border, bw = (56, 52, 72), max(1, self.s(2))
        pygame.draw.rect(screen, border, rect, bw, border_radius=self.s(12))
