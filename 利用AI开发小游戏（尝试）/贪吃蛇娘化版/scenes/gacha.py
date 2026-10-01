# -*- coding: utf-8 -*-
"""
scenes/gacha.py —— 抽卡

货币用「星尘」（战斗掉落）。
保底规则写在 data/gacha.json 里，改配置就能调平衡，不用动代码。

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
    "SR": (200, 100, 255),
    "R": (100, 150, 255),
    "N": (180, 180, 180),
}

DEFAULT_RATES = {"R": 0.78, "SR": 0.18, "SSR": 0.04}
COST_SINGLE = 60
COST_TEN = 540


class GachaScene(Scene):
    """抽卡场景"""

    def enter(self):
        self.assets = self.game.assets
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
        """卡池：按稀有度分组。配置在 data/gacha.json"""
        path = os.path.join(DATA_DIR, "gacha.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[卡池读取失败] {e}，改用内置默认池")
        return {
            "rates": DEFAULT_RATES,
            "pool": {
                "R":   ["lamia_mint"],
                "SR":  ["lamia_tide"],
                "SSR": ["sakura"],
            },
            "pity": {"sr_guarantee": 10, "ssr_guarantee": 60},
        }

    # ---------------------------------------------------------------- 抽卡
    def _pull(self, times):
        save = self.game.save_manager
        cost = COST_SINGLE * times if times == 1 else COST_TEN
        currency = save.get("currency", 0)
        if currency < cost:
            self.msg = f"星尘不足（需要 {cost}，当前 {currency}）"
            self.msg_timer = 2.4
            return

        save.data["currency"] = currency - cost

        rates = self.pool.get("rates", DEFAULT_RATES)
        pool = self.pool.get("pool", {})
        pity = self.pool.get("pity", {})
        sr_need = pity.get("sr_guarantee", 10)
        ssr_need = pity.get("ssr_guarantee", 60)

        results = []
        for i in range(times):
            counter = save.data.setdefault("gacha_pity", {"count": 0, "since_sr": 0, "since_ssr": 0})
            counter["count"] += 1
            counter["since_sr"] += 1
            counter["since_ssr"] += 1

            rarity = self._roll_rarity(rates, counter, sr_need, ssr_need)
            candidates = pool.get(rarity) or ["sakura"]
            char_id = random.choice(candidates)

            if counter["since_ssr"] >= ssr_need:
                pass
            results.append((char_id, rarity, i))

            if rarity in ("SSR", "SR"):
                counter["since_sr"] = 0
            if rarity == "SSR":
                counter["since_ssr"] = 0

            if char_id not in self.owned:
                self.owned.add(char_id)
                save.data.setdefault("owned_characters", []).append(char_id)
                save.data.setdefault("character_data", {})[char_id] = {
                    "level": 1, "exp": 0, "skill_points": 0
                }

        save.save()                   # 即时写盘，防刷卡
        self.result = results
        self.result_timer = 4.0
        self.msg = ""
        best = min(results, key=lambda r: {"SSR": 0, "SR": 1, "R": 2, "N": 3}.get(r[1], 9))
        self.msg = f"抽到 {best[1]} · {self._display_name(best[0])}" if best else ""
        self.msg_timer = 3.0

    def _roll_rarity(self, rates, counter, sr_need, ssr_need):
        """按概率抽稀有度，同时处理两种保底"""
        if counter["since_ssr"] >= ssr_need:
            return "SSR"
        r = random.random()
        acc = 0.0
        # 从高到低判定
        for rarity in ("SSR", "SR", "R"):
            acc += rates.get(rarity, 0.0)
            if r < acc:
                chosen = rarity
                break
        else:
            chosen = "R"
        # 10 抽内必出 SR+
        if chosen == "R" and counter["since_sr"] >= sr_need:
            chosen = "SR"
        return chosen

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
        t = self.font_small.render("战斗掉落星尘 · 集齐更多蛇娘", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.s(132))))

        self._draw_up_character()

        # 卡池信息
        save = self.game.save_manager.data
        counter = save.get("gacha_pity", {"count": 0, "since_sr": 0, "since_ssr": 0})
        ssr_need = self.pool.get("pity", {}).get("ssr_guarantee", 60)
        left = max(0, ssr_need - counter.get("since_ssr", 0))
        info = (f"星尘 {save.get('currency', 0)}    "
                f"已抽 {counter.get('count', 0)} 次    "
                f"距离 SSR 保底还有 {left} 抽")
        t = self.font_body.render(info, True, COLOR_GOLD)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.H - self.s(210))))

        # 保底进度条
        bw = self.s(560)
        bx = self.W // 2 - bw // 2
        by = self.H - self.s(182)
        pygame.draw.rect(screen, (26, 22, 36), (bx, by, bw, self.s(12)), border_radius=6)
        ratio = 1.0 - left / max(1, ssr_need)
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

    def _draw_up_character(self):
        """UP 角色展示"""
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

        img = self.assets.get_scaled("characters/sakura/head.png", height=self.s(330))
        import math
        k = 1.0 + math.sin(self.time * 1.6) * 0.015
        img = pygame.transform.smoothscale(
            img, (int(img.get_width() * k), int(img.get_height() * k)))
        screen.blit(img, img.get_rect(center=(cx, cy - self.s(20))))

        t = self.font_sub.render("樱落 · SSR", True, COLOR_GOLD)
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
        cw, ch = self.s(190), self.s(230)
        gap = self.s(24)
        rows = (n + cols - 1) // cols
        total_w = cols * cw + (cols - 1) * gap
        x0 = (self.W - total_w) // 2
        y0 = self.s(230)

        for i, (char_id, rarity, _) in enumerate(self.result):
            c, r = i % cols, i // cols
            rect = pygame.Rect(x0 + c * (cw + gap), y0 + r * (ch + gap), cw, ch)
            color = RARITY_COLORS.get(rarity, (150, 150, 150))
            pygame.draw.rect(screen, (36, 32, 48), rect, border_radius=12)
            pygame.draw.rect(screen, color, rect, 3, border_radius=12)

            img = self.assets.get_scaled("characters/sakura/head.png", height=self.s(110))
            screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + self.s(78))))

            t = self.font_body.render(self._display_name(char_id), True, color)
            screen.blit(t, t.get_rect(center=(rect.centerx, rect.y + self.s(168))))
            t = self.font_small.render(rarity, True, color)
            screen.blit(t, t.get_rect(center=(rect.centerx, rect.y + self.s(200))))

        t = self.font_small.render("按任意方向键关闭", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.H - self.s(90))))

    def _on_back(self):
        self.game.change_scene("main_menu")
