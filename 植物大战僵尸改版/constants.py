# -*- coding: utf-8 -*-
"""全局常量集中定义。

工程约定第 4 条：所有数值集中在本文件，禁止散落在业务代码里。
本批（STEP 1）用到的只有窗口/缩放/FPS/素材路径，
其余关卡数值先按提示词【数值表】原样登记，后续步骤接线使用。
"""

# ---------- 窗口与渲染 ----------
SCREEN_W = 1600              # 内部渲染分辨率宽（原版 800 的 2 倍）
SCREEN_H = 900               # 内部渲染分辨率高（原版 600 的 1.5 倍，按提示词指定）
ASSET_SCALE = 2.0            # 素材放大倍率，以后换 AI 超分素材只改这一个常量
FPS = 60                     # 固定时间步频率（逻辑 60Hz，渲染每帧一次）

# ---------- 草坪网格 ----------
LAWN_ROWS = 5                # 草坪行数
LAWN_COLS = 9                # 草坪列数
GRID_W = 80                  # 格子宽（原版值，后续按素材反推校准）
GRID_H = 100                 # 格子高（原版值，后续按素材反推校准）

# ---------- 阳光 ----------
START_SUN = 50               # 关卡初始阳光
SUN_VALUE = 25               # 每个阳光的价值
SUN_FALL_INTERVAL = 10.0     # 天降阳光间隔（秒）

# ---------- 豌豆射手 ----------
PEASHOOTER_COST = 100        # 豌豆射手阳光花费
PEASHOOTER_COOLDOWN = 7.5    # 卡片冷却（秒）
SHOOT_INTERVAL = 1.4         # 射击间隔（秒）
PEA_DAMAGE = 20              # 豌豆伤害

# ---------- 僵尸 ----------
ZOMBIE_HP = 270              # 普通僵尸血量
ZOMBIE_SPEED = 22            # 移动速度 px/s（原版值，使用时需乘 ASSET_SCALE）
ZOMBIE_EAT_DPS = 100         # 啃食伤害（每秒）

# ---------- 素材目录（已解包，禁止联网下载） ----------
ASSETS_DIR = r"D:\PVZ改版（自己尝试）\PVZ全部贴图\PVZ全部贴图"   # 贴图 PNG/JPG
REANIM_DIR = r"D:\PVZ改版（自己尝试）\PVZ原版_解包\reanim"        # 骨骼动画 .reanim
SOUNDS_DIR = r"D:\PVZ改版（自己尝试）\PVZ原版_解包\sounds"        # 音效 .ogg
