# -*- coding: utf-8 -*-
"""
settings.py —— 全局配置
想改玩法数值，基本都在这个文件里改，不用动逻辑代码。

坐标系说明（重要）：
    本作已从「网格贪吃蛇」改为「大地图自由移动动作生存」。
    · 世界尺寸 = WORLD_SCREENS_X * 窗口宽 × WORLD_SCREENS_Y * 窗口高（世界像素）
    · 所有实体位置用「世界像素」表示，绘制时减去摄像机偏移 cam
    · 下面标注 (设计像素) 的常量都是 scale=1（1080p 基准）下的值，
      运行时由 battle 乘以 self.S 换算成当前分辨率的真实像素。
    · CELL_SIZE 仅作为「实体尺寸单位」保留（Boss 体型 / 弹幕半径仍按格算），
      不再代表玩家移动的网格。
"""

import os

# ==================== 路径配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
SAVES_DIR = os.path.join(BASE_DIR, "saves")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")

# ==================== 音频配置 ====================
AUDIO_ENABLED = True            # 总开关：关掉后 AudioManager 整体静默
AUDIO_CHANNELS = 16             # 同时可叠加的 SFX 通道数
BGM_FADE_MS = 600               # BGM 切换淡入淡出时长（毫秒）
# 调试用音量热键：作用于“上一次用鼠标点选的那个音量”（音乐 or 音效）。
# ↑/→ 增大、↓/← 减小，每按一下 ±VOLUME_HOTKEY_STEP（0~100 刻度）。
# 战斗进行中方向键要留给移动，此时热键自动让路；暂停菜单/其它界面才生效。
VOLUME_HOTKEY_STEP = 10
# 长按连续调节：按住超过 VOLUME_REPEAT_DELAY_MS 毫秒后开始自动连发，
# 之后每 VOLUME_REPEAT_INTERVAL_MS 毫秒 ±一格，方便快速大幅调节音量。
VOLUME_REPEAT_DELAY_MS = 1000
VOLUME_REPEAT_INTERVAL_MS = 70

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

# ==================== 尺寸单位 ====================
# CELL_SIZE 现在只作「实体尺寸单位」（Boss 体型、弹幕半径按格算），
# 不再是玩家移动的网格。运行时由 game.py 按缩放更新。
CELL_SIZE_BASE = 64
CELL_SIZE = 64
GRID_COLOR = (30, 30, 50)
# GRID_COLS / GRID_ROWS 保留给 Boss 逻辑做默认边界兜底（真实世界尺寸见下方自由移动段）。
GRID_COLS = 26
GRID_ROWS = 13

# ==================== 世界 / 自由移动 ====================
# 世界大小 = 屏数 × 当前窗口尺寸（世界像素）。做大地图靠这里。
WORLD_SCREENS_X = 3             # 世界宽 = 3 屏
WORLD_SCREENS_Y = 2             # 世界高 = 2 屏
CAM_LERP = 6.0                  # 摄像机跟随平滑系数（越大越跟手）

# ---- 玩家移动 / 闪避（设计像素）----
PLAYER_SPEED = 320              # 基础移动速度（设计像素/秒），运行时 ×scale
PLAYER_RADIUS = 24              # 玩家碰撞半径（设计像素）
DODGE_DIST = 210                # 闪避瞬移距离（设计像素）
DODGE_CD = 1.3                  # 闪避冷却（秒）
DODGE_IFRAME = 0.34             # 闪避无敌帧（秒）
DODGE_TIME = 0.12               # 闪避位移过程时长（秒，做拖影用）

# ---- 自动普攻（始终开启，向最近的怪发射弹丸）----
ATK_INTERVAL_BASE = 0.55        # 1 级时的攻击间隔（秒）
ATK_INTERVAL_PER_LEVEL = 0.012  # 每级减少多少攻击间隔（攻速随等级成长）
ATK_INTERVAL_MIN = 0.16         # 攻击间隔下限
ATK_RANGE = 460                 # 索敌半径（设计像素），超出则不打
ATK_BULLET_SPEED = 820          # 普攻弹丸速度（设计像素/秒）
ATK_BULLET_LIFE = 1.1           # 弹丸存活秒数
ATK_BULLET_RADIUS = 8           # 弹丸半径（设计像素）

# ---- 装饰性蛇尾（纯视觉，不再参与碰撞）----
SNAKE_LEN = 10                  # 尾椎节数
BODY_SEG_LEN = 26               # 每节尾椎间距（设计像素）
BODY_SCALE_HEAD = 0.92          # 靠头那节的粗细（相对 CELL）
BODY_SCALE_TAIL = 0.20          # 尾尖那节的粗细

# ==================== 成长（等级 / 伤害） ====================
EXP_PER_LEVEL = 55              # 升一级基础经验
LEVEL_MAX = 40
ATK_BASE = 12                   # 1 级攻击力（普攻弹丸伤害）
ATK_PER_LEVEL = 3               # 每级加多少攻击力

# ==================== 战斗 / 玩家承伤 ====================
HP_MAX = 3                      # 初始血量（卡牌可提升上限）
IFRAME_TIME = 1.2               # 受伤后无敌时间（秒）
PLAYER_ATK = 20                 # 撞击小怪 / Boss 造成多少伤害

# ==================== 小怪（自动索敌、随时间变强） ====================
MOB_HP = 14                     # 小怪基础血量
MOB_TOUCH_DAMAGE = 1            # 小怪碰到你扣多少血（会随时间成长，见 MOB_ATK_GROWTH）
MOB_RADIUS = 24                 # 小怪碰撞半径（设计像素）
MOB_SPEED_BASE = 112            # 小怪基础速度（设计像素/秒）
MOB_SPEED_GROWTH = 0.12         # 每 30 秒速度 +12%
MOB_SPEED_MAX_MULT = 2.8        # 速度最多涨到基础值的几倍
MOB_ATK_GROWTH = 0.55           # 每 60 秒碰触伤害 +0.55（累计到阈值就 +1 点伤害）
MOB_SPAWN_INTERVAL = 2.2        # 初始刷怪间隔（秒）
MOB_SPAWN_MIN = 0.7             # 刷怪间隔下限
MOB_SPAWN_RAMP = 0.06           # 每 10 秒刷怪间隔缩短多少
MOB_HP_GROWTH = 0.22            # 每 30 秒小怪血量 +22%
MOB_HP_MAX_MULT = 6.0           # 小怪血量最多涨到基础值的几倍
MOB_MAX_ALIVE = 32              # 同屏小怪上限
MOB_SPAWN_OFFSCREEN_MARGIN = 90 # 屏幕外刷怪的额外距离（设计像素）
MOB_ALWAYS_CHASE = True         # 小怪始终索敌跟随玩家

# ---- 时间压力：无条件的强度爬升（作用于血量/速度/追击）----
TIME_PRESSURE_START = 75.0      # 从几秒开始加压
TIME_PRESSURE_RAMP = 0.12       # 每秒加压多少
TIME_PRESSURE_MAX = 3.0         # 加压倍数上限

# ==================== 地图道具（只给经验 + 随时间升档） ====================
# 道具只承担「经验」职能，强度成长全部交给升级选卡，避免双轨正反馈。
ITEM_SPAWN_INTERVAL = 2.4       # 地图随机刷新道具的间隔（秒）
ITEM_MAX_ON_MAP = 22            # 场上道具上限
ITEM_MAGNET_RADIUS = 170        # 磁吸半径（设计像素），进入即飞向玩家
ITEM_PICKUP_RADIUS = 34         # 拾取判定半径（设计像素）
ITEM_TIER_TIME = 45.0           # 每过这么多秒，刷新出的道具品质升一档
ITEM_TIER_MAX = 4               # 最高品质档
ITEM_EXP_BASE = 16              # 一档经验果的基础经验
ITEM_TIER_EXP_MULT = 1.7        # 每升一档，经验值乘以这个倍率
# 怪物死亡掉落概率（沿用）
DROP_EXP = 0.60                 # 经验果
DROP_CRYSTAL = 0.16             # 能量结晶（给分）
DROP_STARDUST = 0.12            # 星尘（抽卡材料）
DROP_HEART = 0.12               # 爱心（回血）

# ==================== 升级选卡（肉鸽式成长） ====================
CARD_CHOICES = 3                # 每次升级弹出几张卡供选择
SKILL_MAX_LEVEL = 3             # 单个主动技能最多升到几级
# 被动卡每选一次的数值步长（可重复选、效果叠加）
CARD_ATK_STEP = 0.14            # 攻击力 +14%
CARD_SPEED_STEP = 0.08          # 移速 +8%
CARD_ATKSPD_STEP = 0.10         # 攻速 +10%（缩短普攻间隔）
CARD_CDR_STEP = 0.10            # 技能冷却缩减 +10%
CARD_PICKUP_STEP = 0.30         # 拾取范围 +30%
CARD_HP_STEP = 1                # 最大生命 +1 并回满

# ==================== 主动技能（1-6 键释放，选卡解锁/升级） ====================
# 技能键位按「获得顺序」绑定 1/2/3/4/5/6。数值集中在这里，改数字即可调平衡。
SKILL_ORDER = ["dash", "spike", "shield", "thorn", "storm", "bloom"]

# --- 樱花冲锋：向前突进一段，路径上的怪受伤 ---
DASH_CD = 4.0
DASH_DIST = 260                 # 突进距离（设计像素）
DASH_TIME = 0.18                # 突进过程时长（秒）
DASH_DMG = 26                   # 路径伤害
DASH_DMG_PER_LV = 14            # 每级技能追加伤害

# --- 荆棘尾：周身光环持续一段时间，靠近的怪持续受伤 ---
SPIKE_CD = 8.0
SPIKE_DURATION = 3.0            # 光环持续秒数
SPIKE_RADIUS = 130              # 光环半径（设计像素）
SPIKE_DMG = 12                  # 每次结算伤害
SPIKE_DMG_PER_LV = 7
SPIKE_TICK = 0.5                # 对同一只怪的伤害间隔

# --- 星辉护盾：获得一段无敌 ---
SHIELD_CD = 12.0
SHIELD_TIME = 2.0               # 无敌秒数
SHIELD_TIME_PER_LV = 0.6        # 每级追加无敌时长

# --- 蔓生荆棘：在当前位置放置伤害地形 ---
THORN_CD = 3.0
THORN_LIFE = 5.0                # 荆棘存在时长
THORN_DMG = 16                  # 踩到伤害
THORN_DMG_PER_LV = 8
THORN_TICK = 0.5                # 对同一只怪的伤害间隔
THORN_RADIUS = 78               # 荆棘判定半径（设计像素）
THORN_MAX = 30                  # 场上荆棘上限
THORN_CHARGES = 3               # 一次释放铺几个（围绕身位散布）

# --- 樱花风暴：周身范围爆发伤害 ---
STORM_CD = 9.0
STORM_RADIUS = 210              # 影响半径（设计像素）
STORM_DMG = 40
STORM_DMG_PER_LV = 22

# --- 月华绽放（大招）：向多个方向发射穿透弹 ---
BLOOM_CD = 16.0
BLOOM_COUNT = 12                # 发射多少道
BLOOM_DMG = 34
BLOOM_DMG_PER_LV = 18
BLOOM_BULLET_SPEED = 620        # 穿透弹速度（设计像素/秒）
BLOOM_BULLET_LIFE = 1.3
BLOOM_PIERCE = 4                # 每道弹可穿透几只怪

# ==================== Boss 战 ====================
# 生存到场景阈值后，专属 Boss 登场，击败它即通关结算。
# Boss 的具体数值走 data/bosses.json（数据驱动），这里只放全局参数。
BOSS_ENABLED = True             # 总开关：关掉后退回纯无尽生存
# 玩家撞击 Boss 身体 -> Boss 掉 PLAYER_ATK，玩家不掉血（伤害模型的关键）。
# BOSS_HIT_CD 给撞击限流，防止贴脸瞬间把 Boss 秒掉。
BOSS_HIT_CD = 0.3
BOSS_MOB_SPAWN_SCALE = 1.8      # Boss 登场后普通刷怪间隔放大倍数（放慢但不完全停）
BOSS_REWARD_STARDUST = 30       # 通关额外奖励的星尘

# ---- 弹幕（速度/半径按“格”计，乘 CELL 得到分辨率无关的像素值）----
# 自由移动模式下玩家移速远快于网格版，弹幕速度相应上调，保证仍有威胁。
BOSS_BULLET_SPEED_CELLS = 4.2   # 弹幕飞行速度（格/秒）
BOSS_BULLET_DAMAGE = 1          # 弹幕命中扣多少血
BOSS_BULLET_RADIUS_CELLS = 0.22 # 弹幕判定半径（格）
BOSS_BULLET_LIFE = 4.0          # 弹幕存活秒数（超时或越界即销毁）

# ---- 弹幕模式参数 ----
RADIAL_COUNT = 12               # 环形：一圈发多少颗
AIMED_COUNT = 5                 # 瞄准扇形：发多少颗
AIMED_SPREAD = 0.5              # 瞄准扇形：总张角（弧度）
SPIRAL_ARMS = 3                 # 螺旋：几条臂
SPIRAL_RATE = 16                # 螺旋：每次连发的旋转步长（度）
WALL_COUNT = 12                 # 弹墙：一排多少颗
WALL_GAP = 3                    # 弹墙：留几个缺口（供玩家穿行）

# ---- Boss 技能参数 ----
BOSS_SUMMON_COUNT = 3           # 召唤：一次召几只小怪
BOSS_CHARGE_SPEED_CELLS = 16    # 冲撞：高速直线冲刺速度（格/秒）
BOSS_CHARGE_TELEGRAPH = 1.0     # 冲撞：预警线显示时长（秒），结束后才结算伤害
BOSS_SLAM_RADIUS_CELLS = 3.0    # 震击：范围伤害半径（格）
BOSS_SLAM_TELEGRAPH = 1.0       # 震击：预警圈显示时长（秒），结束后才结算伤害
