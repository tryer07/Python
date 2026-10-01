# -*- coding: utf-8 -*-
"""
scenes/character_detail.py —— 角色详情页

点选角页的已拥有角色进入。这里可以：
  1. 切换 4 个场景背景，看该角色在场景中的完整样子（全身立绘，蛇尾与身体一体）
  2. 点击立绘的头 / 身 / 尾触发彩蛋（台词气泡 + 音效 + 轻微动作）
  3. 查看角色背景故事 / 设定
  4. 查看强化层数（0-15，重复抽卡叠层）
  5. 设为出战 / 返回选角页
"""

import json
import math
import os

import pygame

from core.scene import Scene
from ui.button import Button
from settings import (
    DATA_DIR,
    COLOR_BG, COLOR_ACCENT, COLOR_BG_LIGHT, COLOR_GOLD, COLOR_TEXT, COLOR_TEXT_DIM,
    FONT_SIZE_TITLE, FONT_SIZE_SUBTITLE, FONT_SIZE_BODY, FONT_SIZE_SMALL
)


class CharacterDetailScene(Scene):
    """角色详情场景"""

    def enter(self):
        self.assets = self.game.assets
        self.game.audio.play_bgm("menu")
        self.font_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)
        self.font_sub = self.assets.get_font(self.s(FONT_SIZE_SUBTITLE))
        self.font_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.font_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))

        save = self.game.save_manager
        self.owned = save.get("owned_characters", [])
        char_id = getattr(self.game, "pending_char_id", None) \
            or save.get("selected_character", "sakura")
        self.char = self._load_char(char_id)
        self.char_id = self.char.get("id", "sakura")
        self.is_owned = self.char_id in self.owned

        self.scenes = self._load_scenes()
        cur_scene = save.get("selected_scene", "campus_garden")
        self.scene_idx = 0
        for i, sc in enumerate(self.scenes):
            if sc.get("id") == cur_scene:
                self.scene_idx = i

        self.time = 0.0
        self.egg = None            # {"region","text","timer"}
        self.pulse = 0.0           # 点击后的动作脉冲
        self._regions = {}         # 彩蛋热区

        self._build_buttons()

    def exit(self):
        pass

    # ---------------------------------------------------------------- 配置
    @staticmethod
    def _read_json(filename):
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def _load_char(self, char_id):
        for ch in self._read_json("characters.json"):
            if isinstance(ch, dict) and ch.get("id") == char_id:
                return ch
        return {"id": char_id, "name": char_id, "head": "characters/sakura/head.png"}

    def _load_scenes(self):
        data = self._read_json("scenes.json")
        return [s for s in data if isinstance(s, dict) and s.get("id")] or \
            [{"id": "campus_garden", "name": "校园庭院",
              "bg": "backgrounds/campus_garden.png"}]

    # ---------------------------------------------------------------- 布局
    def _build_buttons(self):
        # 场景切换 tab（左下一排）
        self.tab_btns = []
        n = len(self.scenes)
        tw, th = self.s(150), self.s(44)
        gap = self.s(14)
        total = n * tw + (n - 1) * gap
        x0 = self.s(60)
        y = self.H - self.s(96)
        for i, sc in enumerate(self.scenes):
            b = Button(sc.get("name", "?"), x0 + i * (tw + gap), y, tw, th,
                       font_size=self.s(FONT_SIZE_SMALL - 2),
                       on_click=lambda idx=i: self._pick_scene(idx))
            self.tab_btns.append(b)

        # 右侧操作按钮
        pw = self._panel_rect().w
        px = self._panel_rect().x
        bw, bh = self.s(200), self.s(54)
        by = self.H - self.s(96)
        self.deploy_btn = Button(
            "设为出战", px + self.s(24), by, bw, bh,
            font_size=self.s(FONT_SIZE_BODY), on_click=self._on_deploy)
        self.back_btn = Button(
            "返回", px + self.s(24) + bw + self.s(20), by, bw, bh,
            font_size=self.s(FONT_SIZE_BODY), on_click=self._on_back)

    def _panel_rect(self):
        pw = self.s(620)
        return pygame.Rect(self.W - pw - self.s(40), self.s(120),
                           pw, self.H - self.s(240))

    def _pick_scene(self, idx):
        self.scene_idx = idx
        self.game.audio.play("ui_click")

    def _on_deploy(self):
        if not self.is_owned:
            return
        self.game.save_manager.set("selected_character", self.char_id)
        self.game.audio.play("ui_click")
        self.game.change_scene("character_select")

    def _on_back(self):
        self.game.change_scene("character_select")

    # ---------------------------------------------------------------- 输入
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._on_back()
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for region, rect in self._regions.items():
                    if rect and rect.collidepoint(event.pos):
                        self._trigger_egg(region)
                        break
            for b in self.tab_btns:
                b.handle_event(event)
            self.deploy_btn.handle_event(event)
            self.back_btn.handle_event(event)

    def _trigger_egg(self, region):
        lines = (self.char.get("egg_lines") or {}).get(region) or []
        if not lines:
            return
        import random
        text = random.choice(lines)
        self.egg = {"region": region, "text": text, "timer": 2.6}
        self.pulse = 1.0
        self.game.audio.play("eat_heart")

    def update(self, dt):
        self.time += dt
        self.pulse = max(0.0, self.pulse - dt * 2.2)
        if self.egg:
            self.egg["timer"] -= dt
            if self.egg["timer"] <= 0:
                self.egg = None

    # ---------------------------------------------------------------- 绘制
    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)

        sc = self.scenes[self.scene_idx]
        bg_path = sc.get("bg") or "backgrounds/campus_garden.png"
        bg = self.assets.get_scaled(bg_path, width=self.W)
        screen.blit(bg, (0, self.s(-40)))
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((14, 12, 22, 178))
        screen.blit(veil, (0, 0))

        # 标题
        t = self.font_title.render(self.char.get("name", "?"), True, COLOR_ACCENT)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.s(70))))
        t = self.font_small.render(
            f"{sc.get('name', '')} · 点击她的头 / 身 / 尾试试", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.s(112))))

        self._draw_pose(screen)
        self._draw_panel(screen)
        self._draw_egg(screen)

        for b in self.tab_btns:
            b.draw(screen)
        self.deploy_btn.draw(screen)
        self.back_btn.draw(screen)

    # ---- 全身立绘展示：蛇尾与身体一体，无拼接缝 ----
    def _draw_pose(self, screen):
        pose_cx = int(self.W * 0.30)
        anchor_bottom = int(self.H * 0.86)

        path = self.char.get("full") or self.char.get("head") \
            or "characters/sakura/head.png"
        img = self.assets.get_scaled(path, height=self.s(680))
        # 点击脉冲：轻微放大 + 摆动
        if self.pulse > 0:
            k = 1.0 + math.sin(self.pulse * math.pi) * 0.03
            img = pygame.transform.smoothscale(
                img, (int(img.get_width() * k), int(img.get_height() * k)))
        bob = math.sin(self.time * 1.6) * self.s(4)
        rect = img.get_rect(center=(pose_cx, int(anchor_bottom - img.get_height() // 2 + bob)))
        screen.blit(img, rect)

        # 彩蛋热区：全身立绘竖直三等分 = 头 / 身 / 尾
        third = rect.height // 3
        self._regions = {
            "head": pygame.Rect(rect.x, rect.y, rect.w, third),
            "body": pygame.Rect(rect.x, rect.y + third, rect.w, third),
            "tail": pygame.Rect(rect.x, rect.y + third * 2,
                                rect.w, rect.height - third * 2),
        }

    # ---- 右侧信息面板 ----
    def _draw_panel(self, screen):
        pr = self._panel_rect()
        panel = pygame.Surface((pr.w, pr.h), pygame.SRCALPHA)
        panel.fill((*COLOR_BG_LIGHT, 226))
        screen.blit(panel, pr.topleft)
        pygame.draw.rect(screen, COLOR_ACCENT, pr, 2, border_radius=self.s(14))

        x = pr.x + self.s(28)
        y = pr.y + self.s(30)
        w = pr.w - self.s(56)

        rarity = self.char.get("rarity", "N")
        t = self.font_sub.render(
            f"{self.char.get('name', '?')}  ·  {rarity}  ·  "
            f"{self.char.get('element', '无')}", True, COLOR_GOLD)
        screen.blit(t, (x, y))
        y += self.s(40)

        t = self.font_small.render(self.char.get("title", ""), True, COLOR_TEXT_DIM)
        screen.blit(t, (x, y))
        y += self.s(34)

        t = self.font_small.render(
            f"技能 · {self.char.get('skill', '-')}    成长 · {self.char.get('growth', '-')}",
            True, COLOR_ACCENT)
        screen.blit(t, (x, y))
        y += self.s(40)

        # 背景故事
        t = self.font_body.render("背景故事", True, COLOR_TEXT)
        screen.blit(t, (x, y))
        y += self.s(32)
        for line in self._wrap(self.char.get("story", ""), self.font_small, w):
            t = self.font_small.render(line, True, COLOR_TEXT_DIM)
            screen.blit(t, (x, y))
            y += self.s(26)
        y += self.s(14)

        # 强化层数
        layer = self.game.save_manager.get_enhance(self.char_id)
        t = self.font_body.render(f"强化层数  {layer} / 15", True, COLOR_GOLD)
        screen.blit(t, (x, y))
        y += self.s(34)
        pip = self.s(26)
        gap = self.s(8)
        for i in range(15):
            rx = x + i * (pip + gap)
            rect = pygame.Rect(rx, y, pip, self.s(14))
            if i < layer:
                pygame.draw.rect(screen, COLOR_GOLD, rect, border_radius=4)
            else:
                pygame.draw.rect(screen, (60, 56, 80), rect, border_radius=4)
        y += self.s(30)
        t = self.font_small.render(
            "重复抽到该角色 +1 层（加外观与数值）· 满 15 层后返还星尘",
            True, COLOR_TEXT_DIM)
        screen.blit(t, (x, y))
        y += self.s(30)

        if not self.is_owned:
            t = self.font_small.render("尚未解锁 · 前往抽卡获得", True, (230, 110, 120))
            screen.blit(t, (x, y))

    def _draw_egg(self, screen):
        if not self.egg:
            return
        head_rect = self._regions.get("head")
        if not head_rect:
            return
        text = self.egg["text"]
        # 气泡
        pad = self.s(18)
        surf = self.font_body.render(text, True, COLOR_TEXT)
        bw = surf.get_width() + pad * 2
        bh = surf.get_height() + pad * 2
        bx = head_rect.centerx - bw // 2
        by = max(self.s(140), head_rect.top - bh - self.s(20))
        bubble = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bubble.fill((250, 244, 250, 236))
        self.screen.blit(bubble, (bx, by))
        pygame.draw.rect(self.screen, COLOR_ACCENT, (bx, by, bw, bh), 2,
                         border_radius=self.s(10))
        self.screen.blit(surf, (bx + pad, by + pad))

    # ---------------------------------------------------------------- 工具
    @staticmethod
    def _wrap(text, font, max_w):
        """中文按字换行"""
        lines = []
        cur = ""
        for ch in text:
            if font.size(cur + ch)[0] <= max_w:
                cur += ch
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
        return lines
