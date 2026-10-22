# -*- coding: utf-8 -*-
"""全局配置：分辨率、帧率、路径、字体等"""
import os
import sys

# ---------- 窗口 ----------
SCREEN_W = 800
SCREEN_H = 600
FPS = 60
GAME_TITLE = "植物大战僵尸·改版"

# ---------- 路径 ----------
# PyInstaller 单文件打包后，资源解压到临时目录 sys._MEIPASS；开发时直接用项目目录
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
BG_DIR = os.path.join(ASSET_DIR, "backgrounds")
UI_DIR = os.path.join(ASSET_DIR, "ui")

# ---------- 字体（Windows 系统中文字体，找不到会自动回退） ----------
_FONT_CANDIDATES = [
    os.path.join(ASSET_DIR, "fonts", "simhei.ttf"),  # 项目内置字体优先
    "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
    "C:/Windows/Fonts/simhei.ttf",  # 黑体
]


def find_font() -> str:
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None  # 回退到 pygame 默认字体


FONT_PATH = find_font()

# ---------- 配色（贴合原版的暖色调） ----------
COLOR_TITLE = (255, 242, 153)       # logo 文字黄色
COLOR_TITLE_EDGE = (107, 62, 35)    # logo 描边棕色
COLOR_TEXT = (60, 40, 20)           # 普通深棕文字
COLOR_CARD = (198, 156, 109)        # 按钮卡片底色（木牌棕）
COLOR_CARD_EDGE = (121, 85, 53)     # 卡片描边
COLOR_CARD_HOVER = (224, 184, 130)  # 卡片悬停提亮
COLOR_LOCKED = (130, 130, 130)      # 未解锁关卡灰
