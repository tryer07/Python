# -*- coding: utf-8 -*-
"""
settings.py —— 全局配置
想改玩法数值，基本都在这个文件里改，不用动逻辑代码。
"""

import os

# ==================== 路径配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
SAVES_DIR = os.path.join(BASE_DIR, "saves")

# ==================== 分辨率配置 ====================
# 渲染分辨率：所有游戏逻辑按这个尺寸画
RENDER_WIDTH = 1920
RENDER_HEIGHT = 1080

# 窗口大小将在运行时根据屏幕自动计算（见 core/game.py）
# 以下为最大窗口比例（占屏幕的百分比）
WINDOW_SCALE = 0.9

# 是否全屏。想要"4K 满屏"体验就设 True（配合下面的 4K 预设）
FULLSCREEN = False

# [4K 预设] 想试真 4K，把上面三行改成：
#   RENDER_WIDTH, RENDER_HEIGHT = 3840, 2160
#   WINDOW_SCALE = 1.0
#   FULLSCREEN = True
# 核显可能吃不消，跑起来先看主菜单右上角的帧率显示。

# 显示模式（显示设置场景用）
DISPLAY_MODES = ("windowed", "borderless", "fullscreen")

# 可选分辨率列表（宽, 高, 说明）
RESOLUTION_OPTIONS = [
    (1280, 720, "720p"),
    (1600, 900, "900p"),
    (1920, 1080, "1080p"),
    (2560, 1440, "2K"),
    (3840, 2160, "4K"),
]

# ==================== 游戏配置 ====================
FPS = 60
GAME_TITLE = "贪吃蛇娘化版"

# ==================== 颜色定义 ====================
COLOR_BG = (20, 20, 35)
COLOR_BG_LIGHT = (35, 35, 55)
COLOR_TEXT = (255, 255, 255)
COLOR_TEXT_DIM = (160, 160, 180)
COLOR_ACCENT = (222, 118, 158)          # 樱粉，主色
COLOR_ACCENT_DARK = (150, 70, 105)
COLOR_DANGER = (255, 80, 80)
COLOR_GOOD = (126, 206, 130)
COLOR_GOLD = (255, 200, 50)
COLOR_PURPLE = (180, 100, 255)
COLOR_BUTTON_BG = (50, 50, 80)
COLOR_BUTTON_HOVER = (70, 70, 110)
COLOR_BUTTON_ACTIVE = (90, 90, 140)
COLOR_HP = (226, 84, 110)
COLOR_EXP = (240, 186, 96)

# ==================== 字体配置 ====================
FONT_NAME = "Microsoft YaHei"
FONT_SIZE_TITLE = 64
FONT_SIZE_SUBTITLE = 36
FONT_SIZE_BODY = 24
FONT_SIZE_SMALL = 18

# ==================== 网格配置 ====================
CELL_SIZE = 64                  # 每格像素（4K 下建议 96~128）
GRID_COLOR = (30, 30, 50)
GRID_COLS = 26                  # 26 * 64 = 1664
GRID_ROWS = 13                  # 13 * 64 = 832

# ==================== 蛇（娘化角色） ====================
# 按你的要求：蛇身长度固定，不再靠吃东西变长
SNAKE_LEN = 10                  # 固定身长（含头）
MOVE_INTERVAL = 0.16            # 每走一格的间隔（秒），越小越快
BODY_SEG_LEN = 30               # 每节尾椎显示长度（屏幕像素）
BODY_SCALE_HEAD = 0.92          # 靠头那节的粗细（相对格子）
BODY_SCALE_TAIL = 0.20          # 尾尖那节的粗细

# ==================== 成长（等级 / 伤害） ====================
EXP_PER_LEVEL = 60              # 升一级需要的经验
LEVEL_MAX = 30
ATK_BASE = 12                   # 1 级攻击力
ATK_PER_LEVEL = 3               # 每级加多少攻击力

# ==================== 战斗 ====================
HP_MAX = 3                      # 初始血量
IFRAME_TIME = 1.5               # 受伤后无敌时间（秒）
WALL_IFRAME = 1.2               # 撞墙后的额外保护，避免贴墙反复扣血
PLAYER_ATK = 20                 # 撞一次小怪造成多少伤害

MOB_HP = 14                     # 小怪基础血量
MOB_TOUCH_DAMAGE = 1            # 小怪碰到你扣多少血
MOB_SPAWN_INTERVAL = 3.2        # 初始刷怪间隔（秒）
MOB_SPAWN_MIN = 0.85            # 刷怪间隔下限
MOB_SPAWN_RAMP = 0.075          # 每 10 秒刷怪间隔缩短多少（难度增长）
MOB_HP_GROWTH = 0.22            # 每 30 秒小怪血量 +22%（难度增长）
MOB_HP_MAX_MULT = 6.0           # 小怪血量最多涨到基础值的几倍
MOB_MAX_ALIVE = 14              # 同屏小怪上限（不然满屏都是怪，根本没法玩）

# ==================== 掉落概率 ====================
DROP_EXP = 0.55                 # 经验果
DROP_CRYSTAL = 0.22             # 能量结晶
DROP_STARDUST = 0.13            # 星尘（抽卡材料）
DROP_HEART = 0.10               # 爱心（回血）
