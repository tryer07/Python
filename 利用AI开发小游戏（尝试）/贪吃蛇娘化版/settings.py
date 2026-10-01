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
# 设计基准分辨率（UI 布局以这个为参考）
DESIGN_WIDTH = 1920
DESIGN_HEIGHT = 1080

# 实际渲染分辨率（运行时由 game.py 根据窗口大小动态设置）
# 以下值为默认初始值，程序启动后会被覆盖
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
# 设计基准格子大小（运行时会根据 scale 自动调整）
CELL_SIZE_BASE = 64
CELL_SIZE = 64                  # 实际使用的值（由 game.py 动态更新）
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

# ==================== 技能（按等级自动解锁） ====================
# 设计原则：不额外加按键，保持"只操控方向"的操作纯度。
# 升级解锁后技能自动生效，玩家要做的只是走位。
# 改这里的数字就能调技能强度，不用碰逻辑代码。
SKILL_UNLOCK = {
    "dash":   2,    # 樱花冲锋：移动时碾过身旁小怪，造成撞击伤害
    "spike":  4,    # 荆棘尾：撞到你身体（尾椎）的小怪也会掉血
    "shield": 6,    # 星辉护盾：每 N 秒自动获得一段无敌
    "thorn":  8,    # 蔓生荆棘：移动路径上留下伤害地形
    "storm":  10,   # 樱花风暴：定期清一圈周身范围伤害
}
# [平衡记录] 初版解锁等级是 3/6/9/12/15，但实测玩家平均只活到 8~9 级，
# 导致 Lv12 的蔓生荆棘和 Lv15 的樱花风暴几乎永远见不到 —— 等于白写。
# 下调到 2/4/6/8/10，保证一局（约 100 秒）能完整走完技能树，成长感才成立。

# --- 樱花冲锋 ---
# [平衡记录] 三轮调整的最终形态：
#   1) 初版"无冷却永续 AOE" → 独占 68% 击杀，把核心撞怪操作挤成 0%
#   2) 改成充能制 + 不补刀（只削到剩 1 血）→ 掉到 2.6%，又太弱
#   3) 现在：充能制 + 允许补刀，但充能是"全局节流"而非"按怪计算"，
#      所以它清群效率有上限，不会变成绞肉机。
DASH_DMG = 14                   # 碾压伤害（独立于 PLAYER_ATK，避免叠加过强）
DASH_BONUS_PER_LEVEL = 2        # 每级额外加成
DASH_CHARGES = 3                # 充能数：连续能碾几只
DASH_RECHARGE = 2.2             # 每充能恢复时间（秒）
DASH_SPARK = 6
DASH_FINISH = True              # True = 冲锋可以补刀收尾

# --- 荆棘尾 ---
# [平衡记录] 它靠"怪自己撞上来"触发，不需要玩家付出任何操作，
# 是六个技能里最容易吃满伤害的。初版每只怪 1.1 秒冷却，实测独占 70% 击杀。
# 最终方案：不只是"每只怪有冷却"，再加一道"全局节流"——
# 无论多少只怪同时撞上来，每 SPIKE_GLOBAL_CD 秒总共只结算一次。
# 这样它保留"护身"的定位，但不会变成一台被动绞肉机。
SPIKE_DMG = 10
SPIKE_TICK = 1.4                # 同一只怪被尾椎刺的间隔
SPIKE_GLOBAL_CD = 0.55          # 全局触发间隔：多只怪同时撞也只结算一次

# --- 星辉护盾 ---
# [平衡记录] 初版 12 秒 1.6 秒无敌，配合高击杀几乎不会死。
# 改成更长的间隔，让它更像"救命符"而不是"常驻免伤"。
SHIELD_INTERVAL = 22.0
SHIELD_TIME = 1.6

# --- 蔓生荆棘 ---
# [平衡记录] 它靠"怪自己踩上来"触发，比冲锋的"我主动贴上去"容易得多，
# 实测独占 42% 击杀。所以给它加了两个限制：铺设间距拉大、存在时间缩短。
THORN_LIFE = 3.5                # 荆棘存在时长（原 5.0，太久了等于铺满地图）
THORN_DMG = 9                   # 小怪踩到荆棘的伤害
THORN_TICK = 0.5                # 对同一只怪的伤害间隔
THORN_MAX = 26                  # 场上荆棘数量上限
THORN_SPACING = 3.0             # 每隔几格留一个（原 1.6，铺太密了）

# --- 樱花风暴 ---
STORM_INTERVAL = 9.0            # 触发间隔
STORM_RADIUS = 3                # 影响半径（格）
STORM_DMG = 26                  # 伤害

# ---- 技能系统的难度补偿 ----
# [平衡记录] 初版补偿远远不够：满技能下 5 局全部 300 秒通关（等级 17-18）。
# 调了两轮后得到的教训是：不能只靠"怪变多/变硬"，因为技能越强，
# 玩家清怪越快，反而更安全。真正有效的是下面这条"时间压力"。
MOB_SPAWN_INTERVAL_SKILLED = 1.6    # 解锁 2 个技能后，刷怪间隔基准
MOB_HP_GROWTH_SKILLED = 0.34        # 解锁技能后的血量成长
MOB_MAX_ALIVE_SKILLED = 24          # 解锁技能后同屏怪上限
MOB_CHASE_MAX = 0.9                 # 追击概率上限

# ---- 时间压力：无条件的强度爬升 ----
# 这是唯一能兜住所有打法的曲线。没有它，只要玩家的清怪速度超过了刷怪速度，
# 局面就会永久稳定下来 —— 不管技能怎么削都救不回来。
# TIME_PRESSURE_START 秒之前不生效（给玩家建立优势的时间），之后线性加压。
TIME_PRESSURE_START = 90.0      # 从几秒开始加压
TIME_PRESSURE_RAMP = 0.14       # 每秒加压多少（同时作用于血量、速度、追击）
TIME_PRESSURE_MAX = 3.0         # 加压倍数上限

# ---- 反制正反馈：击杀给的经验随时间衰减 ----
KILL_EXP_BASE = 18              # 一只怪的基础经验
KILL_EXP_FLOOR = 0.25           # 经验衰减下限系数
KILL_EXP_DECAY_START = 30.0     # 从第几秒开始衰减
KILL_EXP_DECAY_RATE = 0.011     # 每秒衰减多少系数

# ==================== 掉落概率 ====================
DROP_EXP = 0.55                 # 经验果
DROP_CRYSTAL = 0.22             # 能量结晶
DROP_STARDUST = 0.13            # 星尘（抽卡材料）
DROP_HEART = 0.10               # 爱心（回血）
