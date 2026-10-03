# -*- coding: utf-8 -*-
"""
ui/suspend_prompt.py —— 「检测到未完成对局，是否继续」模态弹窗（可复用）

在选关(level_select) / 选图(scene_select) 点下某个「模式+场景」时使用：
若该 (mode, scene_id) 存有挂起进度（战斗里按 ESC → 返回主菜单时保存），
就弹出这个模态框问玩家「继续这份进度」还是「重新开始」。
重新开始需二次确认（提示会清除已保存进度）。

不同模式 / 不同场景各自独立存储，互不干扰（见 SaveManager 的 suspend 接口）。
弹窗为模态：active 时宿主场景应把全部事件交给 handle_event，并屏蔽自身其余输入。
"""

import json
import os

import pygame

from ui.button import Button
from settings import (
    COLOR_ACCENT, COLOR_BG_LIGHT, COLOR_TEXT, COLOR_TEXT_DIM, FONT_SIZE_SMALL,
)


class SuspendPrompt:
    """挂起进度询问弹窗。宿主场景持有一个实例，按需 open_if_exists。"""

    def __init__(self, host):
        self.host = host                 # 宿主 Scene（提供 s/W/H/game/字体）
        self.active = False
        self.confirm = False             # 是否处于「确认重开」二次确认态
        self.info = None
        self.mode = None
        self.scene_id = None
        self._on_new = None
        self._char_names = self._load_names("characters.json", "characters")
        self._scene_names = self._load_names("scenes.json", "scenes")

    # ---------------------------------------------------------------- 数据
    @staticmethod
    def _load_names(filename, key):
        from settings import DATA_DIR
        result = {}
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data.get(key, data) if isinstance(data, dict) else data
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict) and "id" in it:
                            result[it["id"]] = it.get("name", it["id"])
            except (json.JSONDecodeError, IOError, AttributeError, TypeError):
                pass
        return result

    # ---------------------------------------------------------------- 打开
    def open_if_exists(self, mode, scene_id, on_new):
        """若 (mode, scene_id) 存在挂起进度就弹窗并返回 True；否则返回 False。

        on_new：玩家确认「重新开始」后调用（由宿主决定怎么开一局新的）。"""
        sm = self.host.game.save_manager
        try:
            data = sm.load_suspend(mode, scene_id)
        except Exception:
            data = None
        if not data:
            return False
        self.mode = mode
        self.scene_id = scene_id
        self.info = data
        self._on_new = on_new
        self.active = True
        self.confirm = False
        self._layout()
        return True

    def _layout(self):
        s = self.host.s
        cx = self.host.W // 2
        cy = self.host.H // 2
        bw, bh = s(240), s(56)
        gap = s(24)
        y = cy + s(70)
        fs = s(FONT_SIZE_SMALL)
        self.cont_btn = Button("继续这份进度", cx - bw - gap // 2, y, bw, bh,
                               font_size=fs, on_click=self._on_continue)
        self.new_btn = Button("重新开始", cx + gap // 2, y, bw, bh,
                              font_size=fs, on_click=self._ask_new)
        self.yes_btn = Button("确认重开", cx - bw - gap // 2, y, bw, bh,
                              font_size=fs, on_click=self._on_confirm_new)
        self.no_btn = Button("取消", cx + gap // 2, y, bw, bh,
                             font_size=fs, on_click=self._cancel_new)

    # ---------------------------------------------------------------- 输入
    def handle_event(self, event):
        """active 时消费所有事件（模态）。返回是否已消费。"""
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.confirm:
                self.confirm = False
            else:
                self.active = False      # 直接关闭：留在选关/选图界面，什么都不做
            return True
        if self.confirm:
            self.yes_btn.handle_event(event)
            self.no_btn.handle_event(event)
        else:
            self.cont_btn.handle_event(event)
            self.new_btn.handle_event(event)
        return True

    # ---------------------------------------------------------------- 绘制
    def draw(self, screen):
        if not self.active:
            return
        host = self.host
        s = host.s
        veil = pygame.Surface((host.W, host.H), pygame.SRCALPHA)
        veil.fill((8, 6, 14, 214))
        screen.blit(veil, (0, 0))
        cx = host.W // 2
        cy = host.H // 2
        w, h = s(660), s(360)
        panel = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(screen, COLOR_BG_LIGHT, panel, border_radius=s(14))
        pygame.draw.rect(screen, COLOR_ACCENT, panel, width=s(3), border_radius=s(14))

        f_title = getattr(host, "font_title", None) or getattr(host, "font_sub", None)
        f_body = getattr(host, "font_body", None) or f_title
        f_small = getattr(host, "font_small", None) or f_body

        if self.confirm:
            t = f_title.render("重新开始这一局？", True, COLOR_ACCENT)
            screen.blit(t, t.get_rect(center=(cx, panel.top + s(78))))
            l1 = f_body.render("已保存的这份进度将被清除，且无法恢复。", True, COLOR_TEXT)
            screen.blit(l1, l1.get_rect(center=(cx, panel.top + s(168))))
            self.yes_btn.draw(screen)
            self.no_btn.draw(screen)
            return

        t = f_title.render("检测到未完成的对局", True, COLOR_ACCENT)
        screen.blit(t, t.get_rect(center=(cx, panel.top + s(62))))
        info = self.info or {}
        char_id = info.get("char_id", "sakura")
        char_name = self._char_names.get(char_id, char_id)
        scene_name = self._scene_names.get(self.scene_id, self.scene_id)
        mode = info.get("mode", self.mode)
        if mode == "story":
            mode_txt = f"剧情 · 第{info.get('level_index', 1)}关 · {scene_name}"
        else:
            mode_txt = f"无尽 · {scene_name}"
        snake = info.get("snake", {}) or {}
        lines = [
            f"角色：{char_name}",
            f"{mode_txt}",
            f"已生存 {int(info.get('elapsed', 0))} 秒    ·    "
            f"Lv.{snake.get('level', 1)}    ·    得分 {info.get('score', 0)}",
        ]
        y = panel.top + s(120)
        for ln in lines:
            t = f_body.render(ln, True, COLOR_TEXT)
            screen.blit(t, t.get_rect(center=(cx, y)))
            y += s(38)
        hint = f_small.render("继续这份进度可接着打；重新开始会丢弃已保存进度",
                              True, COLOR_TEXT_DIM)
        screen.blit(hint, hint.get_rect(center=(cx, y + s(4))))
        self.cont_btn.draw(screen)
        self.new_btn.draw(screen)

    # ---------------------------------------------------------------- 回调
    def _on_continue(self):
        sm = self.host.game.save_manager
        try:
            data = sm.load_suspend(self.mode, self.scene_id)
        except Exception:
            data = None
        self.active = False
        self.confirm = False
        if not data:
            # 读不到（文件损坏等）就退回开新局，绝不卡死
            if self._on_new:
                self._on_new()
            return
        # 不在这里删文件：保留作为崩溃兜底。战斗中阵亡/通关会清，
        # 再次返回主菜单会覆盖，选「重新开始」会清。
        self.host.game.pending_run = {
            "mode": data.get("mode", self.mode),
            "level": data.get("level_index", 1),
            "scene": data.get("scene_id", self.scene_id),
            "char_id": data.get("char_id"),
        }
        self.host.game.pending_suspend = data
        self.host.game.change_scene("battle")

    def _ask_new(self):
        self.confirm = True

    def _on_confirm_new(self):
        try:
            self.host.game.save_manager.clear_suspend(self.mode, self.scene_id)
        except Exception:
            pass
        self.active = False
        self.confirm = False
        if self._on_new:
            self._on_new()

    def _cancel_new(self):
        self.confirm = False
