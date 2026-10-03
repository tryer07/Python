# -*- coding: utf-8 -*-
"""
core/controls.py —— 按键绑定管理（可在游戏内修改）

设计目标：
  · 技能释放默认 1-6，护盾默认鼠标左键；玩家可在游戏内改成顺手的键位。
  · 绑定存机器级 config.controls（跨存档槽共享，见 SaveManager.CONFIG_KEYS）。
  · 提供把 pygame 键码 / 鼠标键翻译成人看得懂的名字，供 UI 显示。

只依赖 pygame，不含任何场景/绘制逻辑，纯数据 + 命名工具。
"""

import pygame

# 鼠标键编号 -> 中文名（pygame: 1左 2中 3右 4滚轮上 5滚轮下）
_MOUSE_NAMES = {
    1: "鼠标左键", 2: "鼠标中键", 3: "鼠标右键",
    4: "滚轮上", 5: "滚轮下",
}

# 常见键的中文名兜底（pygame.key.name 拿到的是英文小写标识）
_CN_KEY = {
    "space": "空格", "escape": "ESC", "return": "回车", "enter": "回车",
    "backspace": "退格", "tab": "Tab", "delete": "Del", "insert": "Ins",
    "home": "Home", "end": "End", "pageup": "PgUp", "pagedown": "PgDn",
    "up": "↑", "down": "↓", "left": "←", "right": "→",
    "lshift": "左Shift", "rshift": "右Shift",
    "lctrl": "左Ctrl", "rctrl": "右Ctrl",
    "lalt": "左Alt", "ralt": "右Alt",
    "capslock": "CapsLock", "comma": ",", "period": ".", "slash": "/",
    "semicolon": ";", "apostrophe": "'", "leftbracket": "[",
    "rightbracket": "]", "backslash": "\\", "minus": "-", "equals": "=",
    "grave": "`",
}


def describe_key(code):
    """把 pygame 键盘键码翻译成显示名（优先中文，退化成大写标识）。"""
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "?"
    try:
        name = pygame.key.name(code)
    except Exception:
        return str(code)
    if not name:
        return str(code)
    low = name.lower()
    if low in _CN_KEY:
        return _CN_KEY[low]
    # 单字符（字母/数字）直接大写显示；多字符标识原样返回
    return name.upper() if len(name) == 1 else name


def describe_mouse(button):
    """把鼠标键编号翻译成显示名。"""
    try:
        button = int(button)
    except (TypeError, ValueError):
        return "鼠标?"
    return _MOUSE_NAMES.get(button, f"鼠标键{button}")


def describe_shield(shield):
    """护盾绑定的显示名：可能是鼠标键，也可能是键盘键。"""
    if not isinstance(shield, dict):
        return "鼠标左键"
    if shield.get("type") == "key":
        return describe_key(shield.get("key", 0))
    return describe_mouse(shield.get("button", 1))


class Controls:
    """按键绑定管理器。绑定即时落盘（config.controls），跨存档槽共享。"""

    SKILL_SLOTS = 6
    # 默认：技能 1-6 用数字键，护盾用鼠标左键
    DEFAULT_SKILL_KEYS = [
        pygame.K_1, pygame.K_2, pygame.K_3,
        pygame.K_4, pygame.K_5, pygame.K_6,
    ]
    DEFAULT_SHIELD = {"type": "mouse", "button": 1}

    def __init__(self, save_manager):
        self.sm = save_manager
        self.skill_keys = list(self.DEFAULT_SKILL_KEYS)
        self.shield = dict(self.DEFAULT_SHIELD)
        self.reload()

    # ---------------- 读写 ----------------
    def reload(self):
        """从 config.controls 载入绑定；缺失/损坏的字段回退默认。"""
        cfg = self.sm.get("controls", {}) or {}
        self.skill_keys = list(self.DEFAULT_SKILL_KEYS)
        sk = cfg.get("skill_keys")
        if isinstance(sk, list):
            for i in range(min(len(sk), self.SKILL_SLOTS)):
                try:
                    self.skill_keys[i] = int(sk[i])
                except (TypeError, ValueError):
                    pass
        self.shield = dict(self.DEFAULT_SHIELD)
        # 兼容旧配置键名 "dodge"（闪避已改为护盾）
        dg = cfg.get("shield") or cfg.get("dodge")
        if isinstance(dg, dict) and dg.get("type") in ("mouse", "key"):
            if dg["type"] == "mouse":
                try:
                    self.shield = {"type": "mouse", "button": int(dg.get("button", 1))}
                except (TypeError, ValueError):
                    pass
            else:
                try:
                    self.shield = {"type": "key", "key": int(dg.get("key", 0))}
                except (TypeError, ValueError):
                    pass

    def save(self):
        self.sm.set("controls", {
            "skill_keys": [int(k) for k in self.skill_keys],
            "shield": dict(self.shield),
        })

    def reset(self):
        """一键恢复初始按键设置。"""
        self.skill_keys = list(self.DEFAULT_SKILL_KEYS)
        self.shield = dict(self.DEFAULT_SHIELD)
        self.save()

    # ---------------- 战斗侧查询 ----------------
    def skill_map(self):
        """{pygame 键码: 技能槽位(1..6)}。同一键冲突时靠前的槽位优先。"""
        m = {}
        for i, k in enumerate(self.skill_keys):
            m.setdefault(int(k), i + 1)
        return m

    def shield_is_mouse(self):
        return self.shield.get("type") == "mouse"

    def shield_mouse_button(self):
        return int(self.shield.get("button", 1))

    def shield_key(self):
        return int(self.shield.get("key", 0))

    # ---------------- 改键侧写入 ----------------
    def set_skill(self, slot, code):
        if 0 <= slot < self.SKILL_SLOTS:
            self.skill_keys[slot] = int(code)
            self.save()

    def set_shield_mouse(self, button):
        self.shield = {"type": "mouse", "button": int(button)}
        self.save()

    def set_shield_key(self, code):
        self.shield = {"type": "key", "key": int(code)}
        self.save()
