"""全局常量：窗口尺寸、地宫规格、玩家初始数值。所有模块从这里取参数。"""

# ---------- 地图规格 ----------
MAP_W = 40            # 地图格宽（格数）
MAP_H = 24            # 地图格高（格数）
TILE = 20             # 每格像素
PANEL_W = 400         # 右侧信息面板宽度
MARGIN = 10           # 地图区外边距

WIN_W = MAP_W * TILE + PANEL_W + MARGIN * 2   # 1220
WIN_H = MAP_H * TILE + MARGIN * 2             # 500

FPS = 60

# ---------- 玩法规格 ----------
MAX_DEPTH = 5         # 下到第 5 层再走一步即通关
DEPTH_HEAL = 4        # 每下多层：生命上限加成
DEPTH_ATK = 1         # 每下多层：攻击力加成

PLAYER_HP = 24        # 初始生命上限
PLAYER_ATK = 5        # 初始攻击
POTION_HEAL = 7       # 药水回复量

# ---------- 瓦片类型（dungeon.map 里存的就是这些整数） ----------
TILE_WALL = 0
TILE_FLOOR = 1
TILE_STAIRS = 2

# ---------- 颜色 (R, G, B) ----------
COL_BG = (12, 11, 16)             # 背景即墙色，与地板拉开对比
COL_WALL = (46, 42, 58)
COL_FLOOR = (50, 48, 66)          # 地板比背景亮一档，房间轮廓才能一眼看出
COL_FLOOR_LINE = (40, 38, 54)     # 地板网格线，提示「这是一格一格走的」
COL_STAIRS = (222, 190, 92)
COL_POTION = (96, 205, 120)
COL_PLAYER = (92, 188, 255)
COL_ENEMY = (228, 96, 88)
COL_ENEMY_BOSS = (255, 150, 40)
COL_TEXT = (210, 208, 220)
COL_TEXT_DIM = (130, 126, 142)
COL_HP_GOOD = (110, 220, 130)
COL_HP_LOW = (230, 90, 80)
