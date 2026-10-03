# -*- coding: utf-8 -*-
"""
ui/keybind_panel.py —— 可复用的「改键面板」

被两处复用：
  · scenes/control_settings.py（主菜单 → 操作设置，整屏）
  · scenes/battle.py 暂停菜单里的「按键设置」浮层（真正在游戏内改键）

职责单一：只管 6 个技能槽 + 护盾这几行的显示与「点击进入监听→按键写入」。
标题、恢复默认、返回等按钮由各自的宿主场景画，面板不掺和。
"""

import pygame

from core.controls import describe_shield, describe_key
from settings import COLOR_BG_LIGHT, COLOR_GOLD, COLOR_GOOD, COLOR_TEXT, COLOR_TEXT_DIM

# 技能槽的展示标签（键1位移/键2引爆/键3聚怪/键4飞行物/键5吟唱，键6备用）
_SKILL_LABELS = [
    "技能 1 · 位移",
    "技能 2 · 引爆",
    "技能 3 · 聚怪",
    "技能 4 · 飞行物",
    "技能 5 · 吟唱",
    "技能 6 · 备用",
]


class KeybindPanel:
    """改键面板：点击某一行进入监听，再按任意键/鼠标键完成绑定。"""

    ROW_H = 54          # 每行设计高度（宿主用 s() 缩放）
    ROW_GAP = 8         # 行间距（设计）

    def __init__(self, game):
        self.game = game
        self.listening = None       # 正在等待输入的行索引，None=未监听
        self.message = ""           # 底部提示（冲突/已更新等）
        self._row_rects = []
        self._rows = self._build_rows()

    def _build_rows(self):
        rows = [{"kind": "skill", "slot": i, "label": lab}
                for i, lab in enumerate(_SKILL_LABELS)]
        rows.append({"kind": "shield", "slot": -1, "label": "护盾"})
        return rows

    # ---------------------------------------------------------------- 布局
    def height(self, s):
        """面板总高（含底部提示行），供宿主居中排版。"""
        n = len(self._rows)
        return n * (s(self.ROW_H) + s(self.ROW_GAP)) + s(34)

    def _binding_text(self, row):
        ctrl = self.game.controls
        if row["kind"] == "skill":
            return describe_key(ctrl.skill_keys[row["slot"]])
        return describe_shield(ctrl.shield)

    # ---------------------------------------------------------------- 事件
    def handle_event(self, event):
        """消费返回 True。监听态吞掉一切输入；非监听态只在点到行时响应。"""
        ctrl = self.game.controls
        if self.listening is not None:
            row = self._rows[self.listening]
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.listening = None
                    self.message = "已取消"
                    return True
                self._assign(row, "key", event.key)
                return True
            # 只有护盾允许绑鼠标键；技能行遇到鼠标点击继续等待键盘
            if event.type == pygame.MOUSEBUTTONDOWN and row["kind"] == "shield":
                self._assign(row, "mouse", event.button)
                return True
            return True     # 监听态吞掉其余所有事件

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self._row_rects):
                if r.collidepoint(event.pos):
                    self.listening = i
                    self.message = "按下想绑定的按键…（ESC 取消）"
                    try:
                        self.game.audio.play("ui_click", throttle=0.05)
                    except Exception:
                        pass
                    return True
        return False

    def _assign(self, row, kind, code):
        ctrl = self.game.controls
        if row["kind"] == "skill":
            if kind != "key":
                self.message = "技能只能绑定键盘按键"
                return
            # 冲突检测：同一键不能同时绑给别的技能或护盾
            for j, k in enumerate(ctrl.skill_keys):
                if k == code and j != row["slot"]:
                    self.message = f"「{describe_key(code)}」已被 技能{j + 1} 占用"
                    self.listening = None
                    return
            if ctrl.shield.get("type") == "key" and ctrl.shield.get("key") == code:
                self.message = f"「{describe_key(code)}」已绑定给 护盾"
                self.listening = None
                return
            ctrl.set_skill(row["slot"], code)
        else:
            if kind == "mouse":
                ctrl.set_shield_mouse(code)
            else:
                for j, k in enumerate(ctrl.skill_keys):
                    if k == code:
                        self.message = f"「{describe_key(code)}」已被 技能{j + 1} 占用"
                        self.listening = None
                        return
                ctrl.set_shield_key(code)
        self.message = "已更新"
        self.listening = None
        try:
            self.game.audio.play("ui_click", throttle=0.05)
        except Exception:
            pass

    # ---------------------------------------------------------------- 绘制
    def draw(self, surf, x, y, w, s, font_body, font_small):
        """在 (x,y) 处按宽度 w 画出所有行。s 为宿主的缩放函数。"""
        ctrl = self.game.controls
        self._row_rects = []
        row_h = s(self.ROW_H)
        gap = s(self.ROW_GAP)
        cap_w = min(s(200), int(w * 0.34))

        for i, row in enumerate(self._rows):
            ry = y + i * (row_h + gap)
            rect = pygame.Rect(x, ry, w, row_h)
            self._row_rects.append(rect)
            listening = (self.listening == i)

            pygame.draw.rect(surf, (58, 52, 40) if listening else COLOR_BG_LIGHT,
                             rect, border_radius=s(8))
            border = COLOR_GOLD if listening else (80, 80, 120)
            pygame.draw.rect(surf, border, rect, width=s(2), border_radius=s(8))

            lab = font_body.render(row["label"], True, COLOR_TEXT)
            surf.blit(lab, lab.get_rect(midleft=(rect.left + s(16), rect.centery)))

            # 右侧按键帽
            cap_h = row_h - s(14)
            cap = pygame.Rect(0, 0, cap_w, cap_h)
            cap.midright = (rect.right - s(14), rect.centery)
            pygame.draw.rect(surf, (28, 28, 46), cap, border_radius=s(6))
            cap_col = COLOR_GOLD if listening else COLOR_GOOD
            pygame.draw.rect(surf, cap_col, cap, width=s(2), border_radius=s(6))
            cap_txt = "请按键…" if listening else self._binding_text(row)
            ct = font_body.render(cap_txt, True, cap_col)
            surf.blit(ct, ct.get_rect(center=cap.center))

        # 底部提示
        if self.message:
            msg = font_small.render(self.message, True, COLOR_TEXT_DIM)
            surf.blit(msg, msg.get_rect(
                midtop=(x + w // 2, y + len(self._rows) * (row_h + gap) + s(4))))
