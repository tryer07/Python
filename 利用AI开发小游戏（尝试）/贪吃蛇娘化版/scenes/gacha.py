# -*- coding: utf-8 -*-
"""
scenes/gacha.py —— 抽卡

货币用「星尘」（战斗掉落）。
无氪金设计：全角色同 SSR、强度一致，抽卡 = 等概率纯收集；
重复抽到返还星尘。规则写在 data/gacha.json，改配置不用动代码。

抽卡结果会即时写盘，防止关掉游戏刷卡。
"""

import json
import os
import random

import pygame

from core.scene import Scene
from ui.button import Button
from settings import (
    DATA_DIR,
    COLOR_BG, COLOR_ACCENT, COLOR_BG_LIGHT, COLOR_GOLD, COLOR_TEXT, COLOR_TEXT_DIM,
    FONT_SIZE_TITLE, FONT_SIZE_SUBTITLE, FONT_SIZE_BODY, FONT_SIZE_SMALL
)

RARITY_COLORS = {
    "SSR": (255, 200, 50),
}

# 无氪金设计：全角色同 SSR。抽卡 = 等概率纯收集 + 强化养成：
# 首次获得记 0 层；重复抽到同一角色 = 该角色 +1 强化层（上限 max_layer），
# 强化同时加外观与战斗数值；已满层后再抽则返还星尘。规则在 data/gacha.json。
DEFAULT_POOL = ["sakura", "lamia_mint", "lamia_tide",
                "lamia_flare", "lamia_stella", "lamia_luna"]
DEFAULT_DUP_REFUND = 40
DEFAULT_MAX_LAYER = 15
COST_SINGLE = 60
COST_TEN = 540


class GachaScene(Scene):
    """抽卡场景"""

    def enter(self):
        self.assets = self.game.assets
        self.game.audio.play_bgm("gacha")
        self.font_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)
        self.font_sub = self.assets.get_font(self.s(FONT_SIZE_SUBTITLE))
        self.font_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.font_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))

        self.back_btn = Button(
            "返回主菜单", self.s(30), self.H - self.s(80), self.s(200), self.s(50),
            font_size=self.s(FONT_SIZE_SMALL), on_click=self._on_back
        )
        self.btn_single = Button(
            f"单抽 ({COST_SINGLE} 星尘)", self.W // 2 - self.s(330), self.H - self.s(150),
            self.s(300), self.s(64), font_size=self.s(FONT_SIZE_BODY),
            on_click=lambda: self._pull(1)
        )
        self.btn_ten = Button(
            f"十连 ({COST_TEN} 星尘)", self.W // 2 + self.s(30), self.H - self.s(150),
            self.s(300), self.s(64), font_size=self.s(FONT_SIZE_BODY),
            on_click=lambda: self._pull(10)
        )

        self.pool = self._load_pool()
        self.result = []              # 本次抽卡结果
        self.result_timer = 0.0
        self.owned = set(self.game.save_manager.get("owned_characters", []))
        self.msg = ""
        self.msg_timer = 0.0
        self.time = 0.0

    def exit(self):
        pass

    # ---------------------------------------------------------------- 配置
    def _load_pool(self):
        """卡池：一个扁平的角色 id 列表（等概率）。配置在 data/gacha.json"""
        path = os.path.join(DATA_DIR, "gacha.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data.get("pool"), list) and data["pool"]:
                    return data
            except (json.JSONDecodeError, IOError) as e:
                print(f"[卡池读取失败] {e}，改用内置默认池")
        return {"pool": list(DEFAULT_POOL), "dup_refund": DEFAULT_DUP_REFUND}

    def _roster(self):
        """卡池角色 id 列表"""
        return self.pool.get("pool", DEFAULT_POOL)

    # ---------------------------------------------------------------- 抽卡
    def _pull(self, times):
        save = self.game.save_manager
        cost = COST_SINGLE * times if times == 1 else COST_TEN
        currency = save.get("currency", 0)
        if currency < cost:
            self.game.audio.play("gacha_error")
            self.msg = f"星尘不足（需要 {cost}，当前 {currency}）"
            self.msg_timer = 2.4
            return

        save.data["currency"] = currency - cost

        roster = self._roster()
        refund = int(self.pool.get("dup_refund", DEFAULT_DUP_REFUND))
        overflow = int(self.pool.get("overflow_refund", DEFAULT_DUP_REFUND))
        results = []
        refund_total = 0
        got_new = False
        gained_layers = 0
        for i in range(times):
            char_id = random.choice(roster)
            if char_id not in self.owned:
                self.owned.add(char_id)
                save.data.setdefault("owned_characters", []).append(char_id)
                save.data.setdefault("character_data", {})[char_id] = {
                    "level": 1, "exp": 0, "skill_points": 0, "enhance": 0
                }
                got_new = True
                results.append((char_id, "SSR", i, False, 0, False))
            else:
                # 重复抽到 = 强化 +1 层；已满层则返还星尘
                layer, maxed = save.add_enhance(char_id)
                if maxed:
                    refund_total += overflow
                else:
                    gained_layers += 1
                results.append((char_id, "SSR", i, True, layer, maxed))

        save.data["currency"] += refund_total
        save.save()                   # 即时写盘，防刷卡
        self.result = results
        self.result_timer = 4.0
        new_n = sum(1 for r in results if not r[3])
        parts = []
        if new_n:
            parts.append(f"新角色 {new_n} 个")
        if gained_layers:
            parts.append(f"强化 +{gained_layers} 层")
        if refund_total:
            parts.append(f"满层返还星尘 {refund_total}")
        self.msg = " · ".join(parts) if parts else "都是已拥有的伙伴"
        self.msg_timer = 3.0
        self.game.audio.play("gacha_pull")
        if got_new:
            self.game.audio.play("gacha_ssr")

    def _display_name(self, char_id):
        path = os.path.join(DATA_DIR, "characters.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for ch in json.load(f):
                        if ch.get("id") == char_id:
                            return ch.get("name", char_id)
            except (json.JSONDecodeError, IOError):
                pass
        return {"sakura": "樱落", "lamia_mint": "薄荷", "lamia_tide": "潮汐"}.get(char_id, char_id)

    # ---------------------------------------------------------------- 更新
    def update(self, dt):
        self.time += dt
        if self.result_timer > 0:
            self.result_timer -= dt
        if self.msg_timer > 0:
            self.msg_timer -= dt

    # ---------------------------------------------------------------- 输入
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._on_back()
                return
            self.back_btn.handle_event(event)
            self.btn_single.handle_event(event)
            self.btn_ten.handle_event(event)

    # ---------------------------------------------------------------- 绘制
    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)

        bg = self.assets.get_scaled("backgrounds/campus_garden.png", width=self.W)
        screen.blit(bg, (0, -self.s(40)))
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((14, 12, 22, 208))
        screen.blit(veil, (0, 0))

        # 标题
        t = self.font_title.render("蛇娘召集", True, COLOR_GOLD)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.s(80))))
        t = self.font_small.render("战斗掉落星尘 · 集齐蛇娘 · 重复抽卡叠强化层", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.s(132))))

        self._draw_up_character()

        # 收集信息（无保底、无概率差：纯收集进度）
        save = self.game.save_manager.data
        roster = self._roster()
        owned_n = sum(1 for c in roster if c in self.owned)
        max_layer = int(self.pool.get("max_layer", DEFAULT_MAX_LAYER))
        info = (f"星尘 {save.get('currency', 0)}    "
                f"收集 {owned_n}/{len(roster)}    "
                f"重复抽卡 = 强化层（上限 {max_layer}）")
        t = self.font_body.render(info, True, COLOR_GOLD)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.H - self.s(210))))

        # 收集进度条
        bw = self.s(560)
        bx = self.W // 2 - bw // 2
        by = self.H - self.s(182)
        pygame.draw.rect(screen, (26, 22, 36), (bx, by, bw, self.s(12)), border_radius=6)
        ratio = owned_n / max(1, len(roster))
        if ratio > 0:
            pygame.draw.rect(screen, (206, 168, 255),
                             (bx, by, int(bw * ratio), self.s(12)), border_radius=6)

        self.btn_single.draw(screen)
        self.btn_ten.draw(screen)
        self.back_btn.draw(screen)

        if self.msg_timer > 0 and self.msg:
            t = self.font_body.render(self.msg, True, COLOR_ACCENT)
            screen.blit(t, t.get_rect(center=(self.W // 2, self.H - self.s(250))))

        if self.result_timer > 0:
            self._draw_result()

    def _char_by_id(self, char_id):
        path = os.path.join(DATA_DIR, "characters.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for ch in json.load(f):
                        if ch.get("id") == char_id:
                            return ch
            except (json.JSONDecodeError, IOError):
                pass
        return {"id": char_id, "name": char_id, "head": "characters/sakura/head.png"}

    def _draw_up_character(self):
        """轮换展示卡池角色（全 SSR，无 UP 概念）"""
        screen = self.screen
        cx = self.W // 2
        cy = self.s(400)
        gsize = self.s(520)
        glow = pygame.Surface((gsize, gsize), pygame.SRCALPHA)
        for i in range(7):
            r = self.s(200) - i * self.s(22)
            pygame.draw.circle(glow, (255, 200, 120, 10),
                               (gsize // 2, gsize // 2), max(10, r))
        screen.blit(glow, (cx - gsize // 2, cy - gsize // 2))

        roster = self._roster()
        ch = self._char_by_id(roster[int(self.time / 2.0) % max(1, len(roster))])
        head = ch.get("head") or "characters/sakura/head.png"
        img = self.assets.get_scaled(head, height=self.s(330))
        import math
        k = 1.0 + math.sin(self.time * 1.6) * 0.015
        img = pygame.transform.smoothscale(
            img, (int(img.get_width() * k), int(img.get_height() * k)))
        screen.blit(img, img.get_rect(center=(cx, cy - self.s(20))))

        t = self.font_sub.render(
            f"{ch.get('name', '?')} · SSR · {ch.get('element', '')}", True, COLOR_GOLD)
        screen.blit(t, t.get_rect(center=(cx, cy + self.s(190))))

    def _draw_result(self):
        screen = self.screen
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((10, 8, 16, 216))
        screen.blit(veil, (0, 0))

        n = len(self.result)
        t = self.font_sub.render("抽卡结果", True, COLOR_TEXT)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.s(160))))

        cols = min(5, n)
        cw, chh = self.s(190), self.s(230)
        gap = self.s(24)
        rows = (n + cols - 1) // cols
        total_w = cols * cw + (cols - 1) * gap
        x0 = (self.W - total_w) // 2
        y0 = self.s(230)

        for i, (char_id, rarity, _, dup, layer, maxed) in enumerate(self.result):
            c, r = i % cols, i // cols
            rect = pygame.Rect(x0 + c * (cw + gap), y0 + r * (chh + gap), cw, chh)
            color = RARITY_COLORS.get(rarity, (150, 150, 150))
            pygame.draw.rect(screen, (36, 32, 48), rect, border_radius=12)
            pygame.draw.rect(screen, color, rect, 3, border_radius=12)

            ch = self._char_by_id(char_id)
            img = self.assets.get_scaled(ch.get("head") or "characters/sakura/head.png",
                                         height=self.s(110))
            screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + self.s(78))))

            t = self.font_body.render(self._display_name(char_id), True, color)
            screen.blit(t, t.get_rect(center=(rect.centerx, rect.y + self.s(168))))
            if dup:
                label = "已满层 · 返还星尘" if maxed else f"强化 +1 → Lv{layer}"
                label_color = (160, 160, 180)
            else:
                label = rarity
                label_color = color
            t = self.font_small.render(label, True, label_color)
            screen.blit(t, t.get_rect(center=(rect.centerx, rect.y + self.s(200))))

        t = self.font_small.render("按任意方向键关闭", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.H - self.s(90))))

    def _on_back(self):
        self.game.change_scene("main_menu")
