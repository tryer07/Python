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
import sys

# ==================== SDL 音频驱动（必须在 pygame 导入前设置） ====================
# 本机实测：SDL 默认 WASAPI 驱动打开音频设备要 4~14 秒（设备被占/驱动枚举慢时
# 更久），且 pygame.mixer.init 全程持有 GIL——放后台线程也会把主线程一起冻住，
# 这是启动间歇卡 ~10s 的真凶。directsound 驱动实测 0.04s 打开，音质功能无差别。
if sys.platform == "win32":
    os.environ.setdefault("SDL_AUDIODRIVER", "directsound")

# ==================== 路径配置 ====================
# 打包成 exe（PyInstaller onefile）后：
#   · 只读资源（assets/data）被解压到临时目录 sys._MEIPASS，从那里读；
#   · 存档等可写内容放在 exe 所在目录旁边，保证退出后还在。
# 源码方式运行时，两者都是项目根目录，行为不变。
if getattr(sys, "frozen", False):
    RES_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    RES_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = RES_DIR
ASSETS_DIR = os.path.join(RES_DIR, "assets")
DATA_DIR = os.path.join(RES_DIR, "data")
SAVES_DIR = os.path.join(BASE_DIR, "saves")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")

# ==================== 音频配置 ====================
AUDIO_ENABLED = True            # 总开关：关掉后 AudioManager 整体静默
AUDIO_CHANNELS = 16             # 同时可叠加的 SFX 通道数
BGM_FADE_MS = 600               # BGM 进出场景的基础淡入淡出时长（毫秒）
# 战斗内 BGM 轮换：让长时间战斗不单调。切换用较长的交叉淡入淡出，衔接不生硬。
BGM_SWITCH_MS = 2600            # 战斗内切歌的交叉淡入淡出时长（毫秒，渐进过渡）
BGM_SWITCH_INTERVAL = 180.0     # 每过多少秒切一首（3 分钟）
# 无尽模式：前 BGM_ENDLESS_LATE_START 秒和场景一样按轮换走，之后每 BGM_SWITCH_INTERVAL
# 秒从下面这么多首「后期高强度」曲子里随机切一首。
BGM_ENDLESS_LATE_START = 900.0  # 15 分钟后进入后期随机曲库
BGM_ENDLESS_POOL = 5            # 后期随机曲库的曲子数量
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
GAME_TITLE = "鳞光纪"

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

# ---- 玩家移动 / 护盾（设计像素）----
PLAYER_SPEED = 320              # 基础移动速度（设计像素/秒），运行时 ×scale
PLAYER_RADIUS = 24              # 玩家碰撞半径（设计像素）
# 左键护盾（取代旧闪避）：吸收池 + 时限，打空或到期即消失。
SHIELD_POOL = 45                # 护盾可吸收的伤害总量
SHIELD_TIME = 2.2               # 护盾持续秒数（到期剩余吸收量失效）
SHIELD_CD = 4.0                 # 护盾冷却（秒）

# ---- 自动普攻（始终开启，向最近的怪发射弹丸）----
ATK_INTERVAL_BASE = 0.55        # 1 级时的攻击间隔（秒）
ATK_INTERVAL_PER_LEVEL = 0.012  # 每级减少多少攻击间隔（攻速随等级成长）
ATK_INTERVAL_MIN = 0.16         # 攻击间隔下限
ATK_RANGE = 460                 # 索敌半径（设计像素），超出则不打
ATK_BULLET_SPEED = 820          # 普攻弹丸速度（设计像素/秒）
ATK_BULLET_LIFE = 1.1           # 弹丸存活秒数
ATK_BULLET_RADIUS = 8           # 弹丸半径（设计像素）

# ---- 近战爪风连击（薄荷普攻重制：无武器 3 段连击、贴身站桩不位移）----
# 仅对配了普攻姿势立绘的角色生效（assets/characters/{id}/atk_*.png，
# 见 battle._atk_pose_paths）；其他角色仍走上面的弹丸普攻，零影响。
# 节拍：3 段循环 MELEE_COMBO_LOOP 秒，第 3 段强化收尾（倍率 + 小击退）；
# 循环结束后的收势段复用 atk_interval（等级成长 + 攻速卡都压缩它）。
MELEE_COMBO_RANGE = 240         # 近战索敌/命中半径（设计像素；薄荷手感反馈偏短，原值 120 翻倍）
MELEE_COMBO_LOOP = 0.5          # 单次 3 段循环时长（秒）
MELEE_COMBO_HIT_MULT = 0.8      # 每段伤害倍率（贴身爆发溢价由此配平弹丸普攻）
MELEE_COMBO_FINISHER_MULT = 1.3 # 收尾段（第 3 段）伤害倍率，相对循环内单段
MELEE_COMBO_FINISHER_KNOCK = 200  # 收尾段小击退强度

# ---- 装饰性蛇尾（纯视觉，不再参与碰撞）----
SNAKE_LEN = 10                  # 尾椎节数
BODY_SEG_LEN = 26               # 每节尾椎间距（设计像素）
BODY_SCALE_HEAD = 0.92          # 靠头那节的粗细（相对 CELL）
BODY_SCALE_TAIL = 0.20          # 尾尖那节的粗细

# ==================== 成长（等级 / 伤害） ====================
# 每级所需经验 = EXP_PER_LEVEL + (当前等级-1) × EXP_GROWTH_PER_LEVEL。
# 两者一起决定升级快慢：调大 => 到 40 级更慢（当前配平目标：即使全程猛叠
# 经验卡，也要 10 分钟以后才摸到 40 级，避免开局几分钟就成长到顶）。
EXP_PER_LEVEL = 100             # 升一级基础经验
EXP_GROWTH_PER_LEVEL = 54       # 每级递增的经验（等级越高越难升）
LEVEL_MAX = 40
ATK_BASE = 12                   # 1 级攻击力（普攻弹丸伤害）
ATK_PER_LEVEL = 3               # 每级加多少攻击力

# ==================== 战斗 / 玩家承伤 ====================
# 生命改为「单条血条」：HP_MAX 是基准最大生命（可被卡牌/强化层继续放大），
# 不再有离散的「几条命」。所有承伤数值都按这个 100 制重新配平。
HP_MAX = 100                    # 血条基准最大生命
IFRAME_TIME = 1.1               # 受伤后无敌时间（秒）
PLAYER_ATK = 20                 # 撞击小怪 / Boss 造成多少伤害

# ==================== 小怪（自动索敌、随时间变强） ====================
MOB_HP = 26                     # 小怪基础血量（上调，逼玩家走位而非站撸）
MOB_TOUCH_DAMAGE = 11           # 小怪碰到你扣多少血（会随时间成长，见 MOB_ATK_GROWTH）
MOB_RADIUS = 24                 # 小怪碰撞半径（设计像素）
MOB_SPEED_BASE = 118            # 小怪基础速度（设计像素/秒）
MOB_SPEED_GROWTH = 0.04         # 每 30 秒速度 +4%（成长放缓：升级变慢后同步拉长难度爆升）
MOB_SPEED_MAX_MULT = 1.9        # 速度最多涨到基础值的几倍
MOB_ATK_GROWTH = 0.8            # 每 60 秒碰触伤害 +0.8（拉长后的后期压力）
MOB_SPAWN_INTERVAL = 1.6        # 初始刷怪间隔（秒）
MOB_SPAWN_MIN = 0.6             # 刷怪间隔下限
MOB_SPAWN_RAMP = 0.05           # 每 10 秒刷怪间隔缩短多少
MOB_HP_GROWTH = 0.18            # 每 30 秒小怪血量 +18%（升级变慢后同步放缓，避免玩家被时间轴压死）
MOB_HP_MAX_MULT = 10.0          # 小怪血量最多涨到基础值的几倍
MOB_MAX_ALIVE = 45              # 同屏小怪上限（数量上去）
MOB_SPAWN_OFFSCREEN_MARGIN = 90 # 屏幕外刷怪的额外距离（设计像素）
MOB_ALWAYS_CHASE = True         # 小怪始终索敌跟随玩家

# ---- 时间压力：无条件的强度爬升（作用于血量/速度/追击）----
# 升级节奏拉长后，时间压力也同步放缓/延后，保证玩家仍能在关卡末尾成长到 40 级。
TIME_PRESSURE_START = 110.0     # 从几秒开始加压（延后，给慢成长留出空间）
TIME_PRESSURE_RAMP = 0.08       # 每秒加压多少（放缓）
TIME_PRESSURE_MAX = 3.0         # 加压倍数上限

# ==================== 地图道具（只给经验 + 随时间升档） ====================
# 道具只承担「经验」职能，强度成长全部交给升级选卡，避免双轨正反馈。
ITEM_SPAWN_INTERVAL = 5.5       # 地图随机刷新道具的间隔（秒，拉开避免遍地道具）
ITEM_MAX_ON_MAP = 14            # 场上道具上限
ITEM_MAGNET_RADIUS = 140        # 磁吸半径（设计像素），进入即飞向玩家
ITEM_PICKUP_RADIUS = 34         # 拾取判定半径（设计像素）
ITEM_TIER_TIME = 55.0           # 每过这么多秒，刷新出的道具品质升一档
ITEM_TIER_MAX = 4               # 最高品质档
ITEM_EXP_BASE = 18              # 一档经验果的基础经验
ITEM_TIER_EXP_MULT = 1.7        # 每升一档，经验值乘以这个倍率
# 怪物死亡掉落：先过 DROP_CHANCE 概率门，命中后再按下面四类分配。
# 小怪不再 100% 掉落（场景已随机刷道具，双轨爆表会让玩家原地挂机）。
DROP_CHANCE = 0.45              # 小怪死亡掉落物品的总概率
DROP_EXP = 0.62                 # 经验果
DROP_CRYSTAL = 0.16             # 能量结晶（给分）
DROP_STARDUST = 0.12            # 星尘（抽卡材料）
DROP_HEART = 0.10               # 爱心（回血）

# ==================== 升级选卡（肉鸽式成长） ====================
CARD_CHOICES = 3                # 每次升级弹出几张卡供选择
# --- 局内技能强化：升级卡池会混入「强化·<技能>」卡，每张把对应主动升 1 级 ---
SKILL_ENH_MAX = 3               # 每个主动技能局内最多强化到几级（满级解锁小机制）
SKILL_ENH_DMG_PER_LV = 0.22     # 每级技能伤害 +22%
SKILL_ENH_CD_PER_LV = 0.08      # 每级技能冷却 -8%
SKILL_ENH_AREA_PER_LV = 0.10    # 每级作用范围/数量类字段 +10%
# 被动卡每选一次的数值步长（可重复选、效果叠加）
CARD_ATK_STEP = 0.14            # 攻击力 +14%
CARD_SPEED_STEP = 0.08          # 移速 +8%
CARD_ATKSPD_STEP = 0.10         # 攻速 +10%（缩短普攻间隔）
CARD_CDR_STEP = 0.10            # 技能冷却缩减 +10%
CARD_PICKUP_STEP = 0.30         # 拾取范围 +30%
CARD_HP_STEP = 18               # 最大生命 +18 并回满（血条上限成长）
# --- 扩充卡池：以下属性卡让每次升级的可选更多样（共 13 张）---
CARD_EXP_STEP = 0.06            # 经验获取 +6%（大幅下调，防止猛叠经验卡把升级拉回失控）
CARD_ARMOR_STEP = 0.08          # 伤害减免 +8%（受伤更少）
CARD_REGEN_STEP = 1.4           # 生命再生：每秒回复 1.4 HP（血条制下才有意义）
CARD_SKILLDMG_STEP = 0.15       # 技能伤害 +15%（专属大招与连招组件）
CARD_RANGE_STEP = 0.15          # 普攻索敌范围 +15%
CARD_LIFESTEAL_STEP = 0.04      # 吸血：触发时把伤害的 4% 转化为生命（概率触发，见下；再削弱）
CARD_SHIELD_STEP = 0.15         # 左键护盾：吸收量与持续时间 +15%（取代旧闪避冷却卡）
# 递减型属性的上限，避免无限叠加导致无敌/零冷却
ARMOR_CAP = 0.60                # 伤害减免最多 60%
LIFESTEAL_CAP = 0.24            # 吸血转化率最多 24%（再削弱，防站撸回满）
SHIELD_STAT_CAP = 1.0           # 护盾加成最多 +100%（吸收量/时限翻倍）
# 吸血改为「概率触发」：每次造成伤害只有一定概率吸血，避免配合受击保护
# 无脑站撸回满。触发时吸血量放大 PROC_BONUS 倍作为补偿，总体续航大幅下调。
LIFESTEAL_PROC_CHANCE = 0.25    # 每次造成伤害触发吸血的概率
LIFESTEAL_PROC_BONUS = 1.5      # 触发时的吸血量倍率（补偿概率；再削弱后净续航约为满配的 9%）
# 回血数值（血条制）：爱心掉落 / 花守被动每次触发
HEART_HEAL = 15                 # 吃爱心回复的生命
PASSIVE_BLOOM_HEAL = 5          # 花守被动触发时回复的生命

# ==================== 角色强化养成（抽到重复角色叠层，无氪金可玩满） ====================
# 重复抽到同一角色 = 该角色 +1 强化层；首次获得记 0 层；满层后再抽返还星尘。
# 强化同时加外观与战斗数值。无氪金，玩久人人可满，属公平养成而非付费碾压。
ENHANCE_MAX_LAYER = 15          # 强化层数上限
ENHANCE_ATK_PER_LAYER = 0.02    # 每层攻击 +2%（满层 +30%）
ENHANCE_SPEED_PER_LAYER = 0.006 # 每层移速 +0.6%（满层 +9%）
ENHANCE_ATKSPD_PER_LAYER = 0.01 # 每层攻速 +1%（满层 +15%）
ENHANCE_CDR_PER_LAYER = 0.006   # 每层冷却缩减 +0.6%（满层 +9%）
ENHANCE_PICKUP_PER_LAYER = 0.01 # 每层拾取 +1%（满层 +15%）
ENHANCE_HP_PER_LAYER = 0.02     # 每层最大生命 +2%（满层 +30%）

# ==================== 双人出战 / 人形态彩蛋 ====================
# 一局最多可选几名蛇娘出战；战斗内 Q 键 / 鼠标滚轮循环切换。
PARTY_MAX = 2                   # 一局最多出战蛇娘数
SWITCH_CD = 3.0                 # 战斗内切换人物的冷却（秒）
SWITCH_IFRAME = 0.5             # 切换/阵亡接管后新上场者的无敌帧（秒）
STANDBY_REGEN_MULT = 0.5        # 待命者生命再生倍率（相对自身再生属性）
# 人形态解锁门槛：强化层数达到该值即解锁，之后玩家可自由切换形态
# （角色详情页「形态」按钮 / 战斗内 V 键，两处共用存档偏好 form_prefs）
HUMAN_FORM_ENHANCE_REQ = 5

# ==================== 角色专属技能包（每人 1 主动 + 1 被动，固定，无共通技能） ====================
# 主动绑 1 键释放；被动常驻。技能 id / 展示文案见 data/characters.json 的 kit。
# 数值集中在这里，改数字即可调平衡。
# --- 樱落 · 落樱绯斩（前冲斩 + 短护盾）---
PETAL_SLASH_CD = 6.0
PETAL_SLASH_DIST = 340          # 突进距离（设计像素）
PETAL_SLASH_DMG = 95            # 冲刺路径伤害（提伤后更值得主动用）
PETAL_SLASH_SHIELD = 0.9        # 释放后护盾秒数（护盾=泡泡，不再闪烁）
# --- 薄荷 · 疾风连闪（三段突进 + 移速爆发）---
GALE_DASH_CD = 5.0
GALE_DASH_COUNT = 3             # 连闪段数
GALE_DASH_DIST = 180            # 每段距离
GALE_DASH_DMG = 30              # 每段路径伤害
GALE_SPEED_MULT = 1.25          # 爆发期移速倍率
GALE_SPEED_TIME = 3.0           # 爆发持续秒数
# --- 潮汐 · 沧澜涌潮（环形水浪 击退+减速+伤害）---
TIDE_SURGE_CD = 8.0
TIDE_SURGE_RADIUS = 260         # 影响半径（设计像素）
TIDE_SURGE_DMG = 40
TIDE_SLOW_MULT = 0.5            # 减速后速度倍率
TIDE_SLOW_TIME = 2.5
TIDE_KNOCK = 260                # 击退强度
# --- 绯焰 · 燎原火鞭（扇形火焰鞭 + 灼烧）---
EMBER_LASH_CD = 7.0
EMBER_LASH_RANGE = 320          # 鞭及距离（设计像素）
EMBER_LASH_ANGLE = 0.7          # 扇形半角（弧度）
EMBER_LASH_DMG = 50
EMBER_BURN_DPS = 12             # 灼烧每秒伤害
EMBER_BURN_TIME = 3.0
# --- 星璃 · 星陨链（多枚追踪星弹）---
STAR_CHAIN_CD = 9.0
STAR_CHAIN_COUNT = 6            # 星弹数
STAR_CHAIN_DMG = 35
STAR_CHAIN_SPEED = 700          # 星弹速度（设计像素/秒）
STAR_CHAIN_LIFE = 1.6
# --- 月见 · 月华结界（穿透月光束 + 护盾）---
MOON_WARD_CD = 12.0
MOON_WARD_LEN = 520             # 光束长度（设计像素）
MOON_WARD_WIDTH = 90            # 光束宽度
MOON_WARD_DMG = 70
MOON_WARD_SHIELD = 1.5          # 护盾无敌秒数

# --- 被动数值 ---
PASSIVE_BLOOM_HEAL_CHANCE = 0.12   # 花守：击杀回血概率
PASSIVE_GALE_SPEED = 1.12          # 御风：常驻移速倍率
PASSIVE_COLD_SLOW = 0.7            # 寒流：普攻减速倍率
PASSIVE_COLD_TIME = 1.2
PASSIVE_EMBER_BURN_DPS = 4         # 余烬：普攻灼烧每秒
PASSIVE_EMBER_BURN_TIME = 2.0
PASSIVE_STARLIGHT_CDR = 0.3        # 星辉：击杀减主动冷却秒
PASSIVE_NIGHT_REDUCE = 0.85        # 静夜：受伤倍率

# ==================== 元素对怪效果（属性 proc） ====================
# 不同元素的蛇娘命中敌人时按概率触发各自的对怪效果，让属性有实际意义：
# 樱=叠花瓣标记满层绽放 / 风=击退+减速 / 水=减速+概率冻结 /
# 火=灼烧+概率爆燃 / 星=概率贯穿次近目标 / 月=概率削弱+自身减伤。
ELEMENT_PROC_CHANCE = 0.30      # 每次命中触发元素效果的概率
# --- 樱：叠花瓣标记，满层绽放小范围伤害 ---
ELEMENT_SAKURA_AMP = 0.12       # 每层花瓣标记易伤
ELEMENT_SAKURA_TIME = 4.0       # 花瓣标记持续秒
ELEMENT_SAKURA_STACKS = 3       # 叠满几层触发绽放
ELEMENT_SAKURA_BLOOM = 26       # 绽放范围伤害
ELEMENT_SAKURA_RADIUS = 90      # 绽放半径（设计像素）
# --- 风：击退 + 短时减速 ---
ELEMENT_WIND_KNOCK = 180        # 击退强度
ELEMENT_WIND_SLOW = 0.7         # 减速倍率
ELEMENT_WIND_TIME = 1.0         # 减速秒数
# --- 水：减速 + 概率冻结（极强减速）---
ELEMENT_WATER_FREEZE_CHANCE = 0.35
ELEMENT_FREEZE_MULT = 0.15      # 冻结时速度倍率（几乎定身）
ELEMENT_FREEZE_TIME = 0.8       # 冻结秒数
# --- 火：灼烧 + 概率小爆燃 ---
ELEMENT_FIRE_BLAST_CHANCE = 0.30
ELEMENT_FIRE_BLAST_RADIUS = 70  # 爆燃半径（设计像素）
# --- 星：概率贯穿，对次近敌人追加伤害 ---
ELEMENT_STAR_PIERCE = 18
# --- 月：概率削弱该怪攻击 + 自身短时减伤 ---
ELEMENT_MOON_WEAKEN = 0.6       # 削弱后碰触伤害倍率
ELEMENT_MOON_TIME = 2.0         # 削弱秒数
ELEMENT_MOON_WARD = 1.2         # 自身减伤持续秒
ELEMENT_MOON_WARD_MULT = 0.8    # 减伤期间受伤倍率

# ==================== 场景渐进难度 ====================
# scenes.json 的 enemy_density / hp_growth 由 battle 读取并应用：
# 后解锁的场景刷怪更密、怪血更厚、精英/Boss 更强，形成渐进式难度。
SCENE_DENSITY_DEFAULT = 1.0     # 场景刷怪密度默认值
SCENE_HP_GROWTH_DEFAULT = 0.18  # 场景怪血成长默认值（同 MOB_HP_GROWTH）

# ==================== 性能保护 ====================
# 怪潮/卡顿尖峰时的两道保险，保证手感稳定不掉帧、不穿模。
DT_MAX = 0.05                   # 单帧 dt 上限（秒）：卡顿尖峰时钳制，防物理穿模/数值爆炸
PARTICLE_MAX = 420              # 同屏粒子上限：超出丢弃最旧的，防怪潮时绘制爆量

# ==================== 剧情关卡节奏 ====================
STORY_DURATION = 900          # 一关时长（秒）= 15 分钟
ELITE_INTERVAL = 150          # 精英怪间隔（秒）= 2.5 分钟
ELITE_HP_MULT = 26.0          # 精英血量倍率（大幅上调，让精英有存在感）
ELITE_SIZE_MULT = 2.0         # 精英体型倍率
ELITE_SPEED_MULT = 1.0        # 精英速度倍率（不再慢于小怪）
ELITE_ATK = 22                # 精英碰触伤害
ELITE_DROPS = 3               # 精英死亡掉落数（掉落总量靠概率下调，精英略降避免爆表）

# ==================== 连招系统（key2-5 通用机制，数据驱动） ====================
# 每名角色 key1 是专属大招，key2-5 是共享的连招组件：
#   标记(2) -> 让敌人易伤；聚怪(3) -> 拉拢+减速；引爆(4) -> 消费标记/减速/灼烧爆发；鼓舞(5) -> 攻击攻速增益。
# 连招链示例：标记(2) 让怪易伤 -> 聚怪(3) 把怪拉到一起并减速 -> 引爆(4) 按身上状态数追加伤害。
# --- 花印 / 标记：范围内敌人易伤 ---
COMBO_MARK_CD = 7.0
COMBO_MARK_RADIUS = 300         # 作用半径（设计像素）
COMBO_MARK_DMG = 18             # 标记时的即时伤害
COMBO_MARK_AMP = 0.28           # 每层标记的易伤加成（受伤 +28%/层）
COMBO_MARK_TIME = 6.0           # 标记持续秒数
COMBO_MARK_MAX_STACKS = 3       # 标记最多叠几层（重复标记叠加易伤，连招核心）
# --- 引 / 聚怪：把范围内敌人拉向自己并减速 ---
COMBO_PULL_CD = 9.0
COMBO_PULL_RADIUS = 340
COMBO_PULL_STRENGTH = 420       # 拉拽强度（负击退=拉向玩家）
COMBO_PULL_DMG = 20
COMBO_PULL_SLOW_MULT = 0.55     # 拉拽后减速倍率
COMBO_PULL_SLOW_TIME = 2.0
# --- 爆 / 引爆：消费敌人身上的状态，按状态数量追加伤害 ---
COMBO_BURST_CD = 10.0
COMBO_BURST_RADIUS = 300
COMBO_BURST_DMG = 55
COMBO_BURST_STATUS_BONUS = 0.5  # 每命中一个状态（标记/减速/灼烧）额外 +50% 伤害
COMBO_BURST_PER_STACK = 0.30    # 每层标记额外 +30% 基础伤害（叠满 3 层 +90%）
COMBO_BURST_TIME_BONUS = 0.25   # 按标记剩余时间最多再 +25%（越早引爆加成越高）
# --- 鼓舞 / 增益：短时间内提升自身攻击与攻速 ---
COMBO_RALLY_CD = 14.0
COMBO_RALLY_TIME = 6.0
COMBO_RALLY_ATK = 1.35          # 攻击 ×1.35
COMBO_RALLY_ATKSPD = 1.30       # 攻速 ×1.30（缩短普攻间隔）

# ==================== 通用技能骨架（dash2/引爆/聚怪/飞行物/吟唱） ====================
# 六角色 key1-5 统一骨架，数值集中在此；元素差异化副效果在 skills._apply_element。
# --- key1 二段位移 dash2：一段前冲+落点元素实体；再按瞬移实体处 AoE；到期实体自爆 ---
DASH2_CD = 6.0
DASH2_DIST = 300                # 一段前冲距离（设计像素）
DASH2_DMG = 45                  # 二段瞬移 AoE 伤害
DASH2_RADIUS = 150              # 二段 AoE 半径（设计像素）
DASH2_MARK_T = 2.2              # 一段落点实体存活秒数（到期自爆小伤害）
DASH2_EXPIRE_DMG = 25           # 实体到期四散/引爆伤害
DASH2_WIND_SPEED = 620          # 风系 dash2：实体风前飞速度（设计像素/秒）
DASH2_WIND_SCRAPE = 0.4         # 风实体沿途刮伤占二段 AoE 伤害的比例
# --- key2 引爆 detonate：消费标记按层追加；无标记者叠 1 层 ---
DETONATE_CD = 8.0
DETONATE_RADIUS = 300
DETONATE_DMG = 50
DETONATE_PER_STACK = 0.35       # 每层标记追加基础伤害
# --- key3 聚怪 gather：拉向玩家+减速+叠 1 层标记 ---
GATHER_CD = 9.0
GATHER_RADIUS = 340
GATHER_STRENGTH = 420
GATHER_DMG = 20
GATHER_SLOW_MULT = 0.55
GATHER_SLOW_TIME = 2.0
GATHER_WIND_SPEED = 720       # 风系聚怪：阵风实体前飞速度（设计像素/秒）
GATHER_WIND_SCRAPE = 0.4      # 阵风沿途刮伤占聚怪伤害的比例
# --- key4 飞行物 blade：N 枚元素弹，命中叠标记+伤害 ---
BLADE_CD = 5.0
BLADE_COUNT = 4
BLADE_DMG = 30
BLADE_SPEED = 760
BLADE_LIFE = 1.2
# --- key5 吟唱 channel：可移动读条，结束施加增益 ---
CHANNEL_CD = 14.0
CHANNEL_TIME = 1.2              # 读条时长（秒）
CHANNEL_BUFF_TIME = 6.0         # 增益持续秒
CHANNEL_ATK = 1.30
CHANNEL_ATKSPD = 1.25
CHANNEL_SPEED = 1.15

# ==================== 潮汐 · 切人五技能（水属性坦克，全部围绕「切人」设计） ====================
# 双人编队但场上同时只有一名角色；潮汐靠切人联动打循环。数值集中在此，改数字即可调平衡。
# 「米」按设计像素映射（水域半径 8m≈340 设计像素，与聚怪/引爆半径同量级）。
# --- ① 潮汐交接：护盾，吸收量=潮汐最大生命 12%，持续 10s；切走时剩余盾量 60% 转移给登场角色 ---
TIDE_HANDOFF_CD = 14.0
TIDE_HANDOFF_SHIELD_PCT = 0.12   # 吸收量 = 施放者（潮汐）最大生命 ×12%
TIDE_HANDOFF_TIME = 10.0         # 护盾持续秒
TIDE_HANDOFF_TRANSFER = 0.60     # 切走时转移给登场角色的剩余盾量比例
# --- ② 涌潮：半径 8m 水域 8s，敌减速 30%，己方减伤 15%+移速 20%；不随切人消失（全链地基）---
TIDE_ZONE_CD = 12.0
TIDE_ZONE_RADIUS = 340           # 水域半径（设计像素，≈8m）
TIDE_ZONE_TIME = 8.0             # 水域持续秒
TIDE_ZONE_ENEMY_SLOW = 0.70      # 水域内敌人减速后速度倍率（-30%）
TIDE_ZONE_ALLY_REDUCE = 0.15     # 水域内己方受伤减免
TIDE_ZONE_ALLY_SPEED = 0.20      # 水域内己方移速加成
# --- ③ 漩涡：引导 2.5s 聚怪；结束时身处水域上则引爆整片水域（主要输出）；引导中切走即中断 ---
TIDE_VORTEX_CD = 16.0
TIDE_VORTEX_TIME = 2.5           # 引导读条秒
TIDE_VORTEX_RADIUS = 360         # 聚怪作用半径（设计像素）
TIDE_VORTEX_STRENGTH = 460       # 聚怪拉拽强度
TIDE_VORTEX_TICK_DMG = 12        # 引导期间每次聚怪 tick 的小额伤害
TIDE_VORTEX_DETONATE_DMG = 200   # 引爆单片水域的伤害（主要输出）
# --- ④ 潮汐契约：8s 内出战角色普攻命中触发水柱追击（潮汐攻击力 40%，内置 CD 0.5s）；切后台也持续 ---
TIDE_CONTRACT_CD = 18.0
TIDE_CONTRACT_TIME = 8.0         # 契约持续秒
TIDE_CONTRACT_ATK_RATIO = 0.40   # 水柱伤害 = 潮汐攻击力 ×40%
TIDE_CONTRACT_INNER_CD = 0.5     # 水柱内置冷却秒
# --- ⑤ 潮汐领域（大招）：全场湿身（受水伤+20%）减速 40% 持续 10s，刷新所有水域，契约剩余时长转全队护盾 ---
TIDE_DOMAIN_CD = 40.0
TIDE_DOMAIN_TIME = 10.0          # 领域持续秒
TIDE_DOMAIN_WET_AMP = 0.20       # 湿身：受到的伤害 +20%（水域体系视作水伤放大）
TIDE_DOMAIN_SLOW = 0.60          # 全场敌人减速后速度倍率（-40%）
TIDE_DOMAIN_SHIELD_PER_SEC = 9.0 # 契约每剩余 1s 转成的护盾吸收量（全队每人）
# --- 被动：后浪（潮汐在后台时出战角色免伤）/ 踏浪登场（在水域上切人，登场角色增益）---
PASSIVE_BACKWAVE_REDUCE = 0.15       # 后浪：出战角色免伤 15%
PASSIVE_BACKWAVE_REDUCE_UP = 0.20    # 后浪（强化达标）：免伤 20%
PASSIVE_BACKWAVE_UP_LAYER = 8        # 潮汐强化层数达到此值，后浪升到 20%
PASSIVE_WAVE_LANDING_TIME = 2.0      # 踏浪登场：增益持续秒
PASSIVE_WAVE_LANDING_SPEED = 0.20    # 踏浪登场：移速 +20%
PASSIVE_WAVE_LANDING_REDUCE = 0.10   # 踏浪登场：减伤 10%

# ==================== 樱落 · 种花闭环五技能（樱属性刺客，sakura_* 自定义 type） ====================
# 核心＝「种花→催放→绽放」：花瓣标记满 3 层立即绽放（范围伤害＋回血）。
# 普攻段3 是种花主手段，五技能负责补种、提前引爆与放大收割；开局弱、收网重。
# 数值按规格固定，不吃职业范围/冷却系数（见 skills.cooldown_at 与 _apply_role 的 sakura_ 豁免）。
# --- 1 花信（sakura_dash2）：突进留分身，路径种花，落地短盾 + 起手无敌 ---
SAKURA_DASH2_CD = 9.0
SAKURA_DASH2_DIST = 240          # 突进距离（设计像素）
SAKURA_DASH2_TIME = 0.18         # 突进耗时（秒）
SAKURA_DASH2_PLANT_STEP = 60     # 路径每 60 距离种 1 层
SAKURA_DASH2_PLANT_CAP = 2       # 单次突进补种上限（层）
SAKURA_DASH2_SHIELD_PCT = 0.08   # 落地盾 = 最大生命 8%
SAKURA_DASH2_SHIELD_TIME = 1.2   # 落地盾持续秒
SAKURA_DASH2_IFRAME = 0.15       # 起手无敌秒
# --- 2 催放（sakura_detonate）：提前引爆全场标记 + 延迟二次跳 ---
SAKURA_DETONATE_CD = 7.0
SAKURA_DETONATE_RADIUS = 160     # 引爆半径（设计像素）
SAKURA_DETONATE_PER_STACK = 0.55 # 每层标记 ×0.55 追加
SAKURA_DETONATE_DELAY = 1.0      # 引爆后二次跳延迟（秒）
SAKURA_DETONATE_DELAY_PCT = 0.15 # 二次跳 = 引爆伤害 15%
# --- 3 落樱引（sakura_gather）：地面圆形花圃，圃内周期叠层 ---
SAKURA_GATHER_CD = 14.0
SAKURA_GATHER_RADIUS = 180       # 花圃半径（设计像素）
SAKURA_GATHER_TIME = 6.0         # 花圃持续秒
SAKURA_GATHER_TICK = 0.8         # 圃内叠层周期（秒）
# --- 4 回旋花刃（sakura_blade）：花刃轮往返 2 趟，命中叠层、打标记目标加伤 ---
SAKURA_BLADE_CD = 11.0
SAKURA_BLADE_RANGE = 620         # 单趟射程（设计像素）
SAKURA_BLADE_WIDTH = 40          # 刃轮宽度（设计像素）
SAKURA_BLADE_MULT = 0.42         # 每段伤害倍率
SAKURA_BLADE_TRIPS = 2           # 往返趟数
SAKURA_BLADE_MARKED_BONUS = 0.20 # 命中带标记目标伤害 +20%
# --- 5 花期（sakura_channel）：增益期普攻每段叠 2 层、绽放半径 +50% ---
SAKURA_CHANNEL_CD = 20.0
SAKURA_CHANNEL_TIME = 6.0        # 增益持续秒
SAKURA_CHANNEL_STACK = 2         # 增益期普攻每段叠层数
SAKURA_CHANNEL_BLOOM_MULT = 1.5  # 增益期绽放半径倍率
# --- 结算 / 被动·花守 ---
SAKURA_BLOOM_PER_STACK = 0.35    # 绽放伤害 = 基础 ×(1+0.35×层数)
SAKURA_BLOOM_BED_MULT = 1.2      # 目标站在花圃内再 ×1.2
SAKURA_BLOOM_CD = 0.3            # 同一目标不重复绽放间隔（秒）
SAKURA_BLOOM_HEAL = 5            # 花守：每次绽放回血
SAKURA_GUARD_MAX = 5             # 花护上限层数
SAKURA_GUARD_REDUCE = 0.02       # 花护每层减伤

# ==================== 标记被动（全员：技能叠标记，满 3 层自爆） ====================
MARKPASSIVE_STACKS = 3          # 标记最多叠几层
MARKPASSIVE_TIME = 6.0          # 标记持续秒
MARKPASSIVE_AMP = 0.20          # 每层易伤
MARKPASSIVE_EXPLODE_DMG = 60    # 满层自爆范围伤害
MARKPASSIVE_EXPLODE_RADIUS = 130  # 自爆半径（设计像素）

# ==================== 职业（法师/刺客/坦克） ====================
# 三档定位：法师=手长消耗多、刺客=近战爆发高、坦克=血多抗性高。
# hybrid 是兜底档（全 1.0），未知 role / 旧存档走它。
# 落地位置：血量/技能伤害/免伤在 battle（_activate 与 cast_skill），
#          射程/范围/冷却/读条/生命代价在 skills（_apply_role 与 cooldown_at）。
ROLE_HP_MULT = {"tank": 1.40, "mage": 0.78, "assassin": 0.92, "hybrid": 1.00}
ROLE_SKILLDMG_MULT = {"tank": 0.88, "mage": 1.22, "assassin": 1.32, "hybrid": 1.00}
ROLE_ARMOR = {"tank": 0.18, "mage": 0.00, "assassin": 0.04, "hybrid": 0.00}
ROLE_NAMES = {"tank": "坦克", "mage": "法师", "assassin": "刺客", "hybrid": "全能"}
# 详情页用的一句职业说明（把取舍讲清楚，免得玩家只看数字）
ROLE_HINTS = {
    "tank": "坦克：血厚、免伤高、技能范围大，但伤害偏低",
    "mage": "法师：射程远、范围大，但冷却长、读条久，伤害型技能要消耗生命",
    "assassin": "刺客：贴身爆发高、位移远、冷却短，但射程短、血偏薄",
    "hybrid": "全能：各项均衡，无明显短板",
}
# 冷却倍率：法师技能贵、刺客技能勤
ROLE_CD_MULT = {"tank": 0.95, "mage": 1.30, "assassin": 0.82, "hybrid": 1.00}
# 飞行物存续倍率：射程 = speed × life，弹速不变只改存续，射程线性可控
ROLE_PROJ_LIFE_MULT = {"tank": 1.00, "mage": 1.50, "assassin": 0.55, "hybrid": 1.00}
# 位移距离倍率：刺客冲得更远，法师不贴脸
ROLE_DASH_DIST_MULT = {"tank": 1.00, "mage": 0.85, "assassin": 1.25, "hybrid": 1.00}
# AoE / 聚怪半径倍率：坦克罩得住场，刺客只打身边
ROLE_AREA_MULT = {"tank": 1.25, "mage": 1.10, "assassin": 0.88, "hybrid": 1.00}
# 吟唱读条倍率：法师读条久（风险即代价），刺客读条快
ROLE_CHANNEL_MULT = {"tank": 1.10, "mage": 1.40, "assassin": 0.80, "hybrid": 1.00}
# 法师「消耗多」：伤害型技能附带自身生命代价（占最大生命比例，不会自杀）
ROLE_HPCOST = {"tank": 0.0, "mage": 0.035, "assassin": 0.0, "hybrid": 0.0}

# ==================== 新手指引 ====================
# 新存档首局按顺序播放的提示文案（定时浮层）
TUTORIAL_HINTS = [
    "WASD / 方向键 移动你的蛇娘",
    "点击 或 按住左键 张开护盾（吸收伤害，有冷却）",
    "按 1-5 释放技能：位移(1)→引爆(2)→聚怪(3)→飞行物(4)→吟唱(5)，技能命中叠标记，满 3 层自爆",
    "吃地上的道具升级，升级后选一张强化卡",
    "剧情目标：撑到时间结束并击败 Boss！",
]
TUTORIAL_HINT_DURATION = 4.5    # 每条新手指引浮层停留时长（秒）

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
BOSS_BULLET_DAMAGE = 12         # 弹幕命中扣多少血
BOSS_SLAM_DAMAGE = 20           # 震击命中扣多少血
BOSS_CHARGE_DAMAGE = 26         # 冲撞命中扣多少血
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
