# 3D迷宫探索 —— ursina 第一人称迷宫逃脱
#
# 运行方式：直接 Run 本文件（main.py），会弹出一个 3D 窗口。
# 操作：开场有新手引导；点【开始】按钮或按【空格】进入（自动锁定鼠标）
#       → WASD 移动 / Shift 奔跑 / 移动鼠标转视角；
#       集齐 5 把金色发光钥匙、碰到绿色门柱即逃脱；Esc 暂停，R 换局。
#
# 依赖：pip install ursina （本项目已安装，兼容 Python 3.14）
#
# 说明：移动与碰撞用「网格数学」自行实现，不依赖 ursina 的物理/射线碰撞，
#       因此在不同 ursina 版本上行为都稳定可控。

import math
import random
import time
from pathlib import Path

from ursina import (
    Ursina,
    Entity,
    Vec3,
    Text,
    Audio,
    Button,
    color,
    camera,
    scene,
    mouse,
    window,
    held_keys,
    destroy,
    application,
    time as ursina_time,   # 帧间隔 dt 在 ursina 的 time 模块里，不是标准库 time！
)

from maze_generator import FLOOR, WALL, farthest_cell, floor_cells, generate_maze
from footstep_sfx import ensure_footstep_sfx

# ---------------- 全局可调参数 ----------------
CELL = 4.0            # 每个网格对应世界的单位（即通道宽度）
COLS = 21             # 迷宫列数（奇数）
ROWS = 21             # 迷宫行数（奇数）
WALL_HEIGHT = 4.0     # 墙高
EYE_HEIGHT = 1.7      # 视点离地高度
PLAYER_RADIUS = 0.7   # 玩家碰撞半径（必须小于 CELL/2，否则卡在通道里）
WALK_SPEED = 5.0      # 步行速度（单位/秒）
RUN_SPEED = 8.5       # 奔跑速度（单位/秒）
MOUSE_SENS = 35.0     # 鼠标灵敏度（对齐 ursina FirstPersonController 量级）
KEY_COUNT = 5         # 需要收集的钥匙数量

# 脚步声：每走过这么多个世界单位踩一步
STEP_LEN_WALK = 2.2
STEP_LEN_RUN = 1.5
# 小地图：每格在屏幕 UI 空间的尺寸与右上角位置（UI：屏幕高=1，x 范围±0.889）
MINIMAP_CELL = 0.010
MINIMAP_POS = (0.76, 0.36)


class MazeGame:
    def __init__(self) -> None:
        self._setup_font()
        self.grid: list[list[int]] = []
        self.nodes: list[Entity] = []       # 本局生成的场景实体，换局时销毁
        self.keys: list[Entity] = []        # 尚未被收集的钥匙
        self.map_nodes: list[Entity] = []   # 小地图上的 UI 实体
        self.map_keys: list[Entity] = []    # 与 self.keys 一一对应的小地图钥匙标记
        self.map_player: Entity | None = None
        self.map_facing: Entity | None = None
        self.exit_cell: tuple[int, int] = (0, 0)
        self.total_keys = KEY_COUNT
        self.collected = 0
        self.state = "start"                # start / playing / won
        self._step_dist = 0.0               # 脚步声：累计行走距离

        # 玩家位姿（网格平面坐标 + 视角）
        self.px = 0.0
        self.pz = 0.0
        self.yaw = 0.0
        self.pitch = 0.0

        # 注意：ursina 的 color.rgb() 不做 0-255 换算（超 1 会被钳成纯白），
        # 0-255 色值必须用 rgb32/rgba32
        scene.clear_color = color.rgb32(12, 14, 22)
        camera.clip_plane_far = 200
        mouse.locked = False

        self._setup_audio()
        self._build_ui()
        self.new_maze()
        self._refresh_start_overlay()   # 开场必须把新手引导面板亮出来

    # ---------------- 中文字体 ----------------
    def _setup_font(self) -> None:
        # ursina 默认字体不含中文；fonts/simhei.ttf 存在时切换为黑体，否则原样运行
        font_file = Path(__file__).resolve().parent / "fonts" / "simhei.ttf"
        if font_file.exists():
            Text.default_font = "simhei.ttf"
            Text.default_monospace_font = "simhei.ttf"

    # ---------------- 脚步声 ----------------
    def _setup_audio(self) -> None:
        # 首次运行会把 wav 合成到 assets/；无音频设备时静默降级，不影响游戏
        self.sfx: dict[str, Audio] = {}
        try:
            assets_dir = str(Path(__file__).resolve().parent / "assets")
            paths = ensure_footstep_sfx(assets_dir)
            # 必须传 Path 对象：ursina 的 Audio 对 str 会拿它当 glob 模式去搜文件，
            # 绝对路径永远搜不到（只有 Path 才走直接加载分支）
            self.sfx["walk"] = Audio(Path(paths["walk"]), volume=0.5, autoplay=False, auto_destroy=False)
            self.sfx["run"] = Audio(Path(paths["run"]), volume=0.55, autoplay=False, auto_destroy=False)
        except Exception as e:  # noqa: BLE001  （音频失败不应阻断游戏启动）
            print("脚步声初始化失败，已禁用音效:", e)
            self.sfx = {}

    # ---------------- 网格 <-> 世界坐标 ----------------
    def cell_to_world(self, c: int, r: int) -> tuple[float, float]:
        x = (c - COLS / 2) * CELL
        z = (r - ROWS / 2) * CELL
        return x, z

    def world_to_cell(self, x: float, z: float) -> tuple[int, int]:
        # 一个世界点落在哪个格子：格 (c) 占据 [X_c-CELL/2, X_c+CELL/2]
        c = int(x / CELL + COLS / 2 + 0.5)
        r = int(z / CELL + ROWS / 2 + 0.5)
        return c, r

    def is_blocked(self, x: float, z: float) -> bool:
        """把玩家当成小方块，采样其周围 8 个点；任一点落在墙上即视为阻挡"""
        offsets = [
            (PLAYER_RADIUS, 0), (-PLAYER_RADIUS, 0),
            (0, PLAYER_RADIUS), (0, -PLAYER_RADIUS),
            (PLAYER_RADIUS, PLAYER_RADIUS), (-PLAYER_RADIUS, -PLAYER_RADIUS),
            (PLAYER_RADIUS, -PLAYER_RADIUS), (-PLAYER_RADIUS, PLAYER_RADIUS),
        ]
        for ox, oz in offsets:
            c, r = self.world_to_cell(x + ox, z + oz)
            if c < 0 or c >= COLS or r < 0 or r >= ROWS:
                return True
            if self.grid[r][c] == WALL:
                return True
        return False

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        # 注意：ursina 的 Text.size 是 UI 世界单位（屏幕高=1），默认 0.025；
        # 传像素值（如 20）会把文字/背景板放大几十倍盖住整屏
        self.hud = Text(
            text="", position=(-0.85, 0.47), origin=(-0.5, 0.5),
            color=color.white, size=0.03,
        )
        self.help_bar = Text(
            text="W/A/S/D 移动     鼠标 转视角     Shift 跑     Esc 暂停",
            position=(0, 0.47), origin=(0, 0.5),
            color=color.rgb32(205, 210, 230), size=0.024, background=True,
        )
        self.message = Text(
            text="", position=(0, -0.42), origin=(0, 0.5),
            color=color.gold, size=0.035,
        )
        # 开场/胜利弹窗：全屏遮罩 + 说明文字 + 大大的开始按钮
        self.overlay_bg = Entity(
            parent=camera.ui, model="quad",
            color=color.rgba32(6, 9, 16, 246), scale=(3, 3),
        )
        self.overlay = Text(
            text="", position=(0, 0.16), origin=(0, 0.5),
            color=color.white, size=0.035,
        )
        self.start_button = Button(
            text="点 我 开 始", position=(0, -0.30), origin=(0, 0),
            scale=(0.4, 0.09), color=color.rgb32(72, 96, 176),
            highlight_color=color.rgb32(96, 124, 210), text_size=1.4,
            on_press=self._begin,
        )
        self.overlay_parts = [self.overlay_bg, self.overlay, self.start_button]
        # 新手引导字幕：进入游戏后按节奏逐条弹出（不用 background：
        # 背景板在空文本时创建，后续不会随文字变宽，会残留错位黑块）
        self.coach = Text(
            text="", position=(0, -0.30), origin=(0, 0),
            color=color.rgb32(255, 214, 100), size=0.032,
        )
        self.coach.visible = False
        self._msg_timer = 0.0
        self._coach_queue: list[tuple[float, str]] = []
        self._coach_timer = 0.0

    def _set_overlay(self, show: bool, with_button: bool = True) -> None:
        self.overlay_bg.visible = show
        self.overlay.visible = show
        self.start_button.visible = show and with_button

    def _flash(self, text: str, ttl: float = 2.0) -> None:
        """在屏幕下方闪一条提示，ttl 秒后自动消失"""
        self.message.text = text
        self._msg_timer = ttl

    def _refresh_start_overlay(self) -> None:
        self.overlay.text = (
            "【 3D 迷宫逃脱 · 新手指南 】\n\n"
            "■ 目标：迷宫里藏着 5 个漂浮的金色发光方块(钥匙)，全部拿到，\n"
            "    再碰到绿色发光门柱，就逃脱成功！\n"
            "■ 操作：W 前进　S 后退　A/D 横移；移动鼠标转视角；按住 Shift 奔跑\n"
            "■ 右上角小地图：白点是你，红线是朝向，金点=钥匙，绿点=出口\n\n"
            "按空格键，或点下方按钮开始游戏"
        )
        self._set_overlay(True)

    def _begin(self) -> None:
        self.state = "playing"
        self._set_overlay(False)
        # 三段式新手引导：(停留秒数, 文案)，按顺序逐条弹出
        self._coach_queue = [
            (4.0, "先试试按 W 向前走，A/D 调整方向，拖动鼠标看看四周"),
            (5.0, "找到漂浮的金色发光方块，走过去就能捡到钥匙（看小地图金点）"),
            (5.0, "集齐 5 把后，去小地图绿点处的门柱 = 逃脱成功，加油！"),
        ]
        self._coach_timer = 0.6
        self.coach.visible = True
        mouse.locked = True

    # ---------------- 生成新的一局 ----------------
    def new_maze(self) -> None:
        for node in self.nodes:
            destroy(node)
        self.nodes.clear()
        self.keys.clear()
        for node in self.map_nodes:
            destroy(node)
        self.map_nodes.clear()
        self.map_keys.clear()
        self.map_player = None
        self.map_facing = None
        self.collected = 0
        self._step_dist = 0.0
        self.message.text = ""
        self._msg_timer = 0.0
        self.coach.visible = False
        self._coach_queue = []

        seed = random.randint(0, 10 ** 9)
        self.grid = generate_maze(COLS, ROWS, seed=seed)
        self._build_maze_geometry()
        self._place_player_and_items()
        self._update_hud()

    def _build_maze_geometry(self) -> None:
        # 地板 + 天花板（把整个迷宫封闭起来，无需天空盒）
        floor = Entity(
            model="quad", color=color.rgb32(64, 68, 92),
            rotation_x=90, scale=(COLS * CELL, ROWS * CELL), position=(0, 0, 0),
        )
        ceiling = Entity(
            model="quad", color=color.rgb32(38, 42, 60),
            rotation_x=-90, scale=(COLS * CELL, ROWS * CELL), position=(0, WALL_HEIGHT, 0),
        )
        self.nodes.extend([floor, ceiling])

        # 墙体：每个 WALL 格放一个立方体（纯视觉，碰撞走网格逻辑）
        wall_color = color.rgb32(136, 124, 162)
        for r, row in enumerate(self.grid):
            for c, val in enumerate(row):
                if val != WALL:
                    continue
                x, z = self.cell_to_world(c, r)
                block = Entity(
                    model="cube", color=wall_color,
                    position=(x, WALL_HEIGHT / 2, z),
                    scale=(CELL, WALL_HEIGHT, CELL),
                )
                self.nodes.append(block)

    def _place_player_and_items(self) -> None:
        cells = floor_cells(self.grid)
        start_cell = (1, 1)
        self.exit_cell = farthest_cell(self.grid, start_cell)

        sx, sz = self.cell_to_world(*start_cell)
        self.px, self.pz = sx, sz
        # 出生朝向对准开口方向，避免一进场就面对墙不知所措
        # （yaw=0 看 +Z 即 grid[2][1] 格；yaw=90 看 +X 即 grid[1][2] 格）
        self.yaw, self.pitch = (90.0 if self.grid[1][2] != WALL else 0.0), 0.0

        # 出口：发光的绿色门柱
        ex, ez = self.cell_to_world(*self.exit_cell)
        pillar = Entity(
            model="cube", color=color.rgb32(60, 235, 140),
            position=(ex, WALL_HEIGHT / 2, ez), scale=(CELL * 0.5, WALL_HEIGHT, CELL * 0.5),
        )
        glow = Entity(
            model="cube", color=color.rgb32(140, 255, 190),
            position=(ex, WALL_HEIGHT / 2, ez), scale=(CELL * 0.85, WALL_HEIGHT, CELL * 0.85),
        )
        self.nodes.extend([pillar, glow])
        self.exit_glow = glow

        # 钥匙：在离出生点足够远的通路格里随机挑选
        candidates = [
            (c, r) for (c, r) in cells
            if (c, r) != start_cell
            and math.dist((c, r), start_cell) > 6
            and (c, r) != self.exit_cell
        ]
        random.shuffle(candidates)
        for c, r in candidates[: self.total_keys]:
            x, z = self.cell_to_world(c, r)
            key = Entity(
                model="cube", color=color.rgb32(255, 205, 60),
                position=(x, 1.4, z), scale=(0.9, 0.9, 0.9),
            )
            # 钥匙顶天光柱：让玩家在长廊远处就能瞄到
            Entity(
                parent=key, model="cube", color=color.rgba32(255, 215, 90, 80),
                position=(0, 1.0, 0), scale=(0.3, 3.2, 0.3),
            )
            key.rotation_y = random.uniform(0, 360)
            self.keys.append(key)
            self.nodes.append(key)

        self._build_minimap()

    # ---------------- 小地图（屏幕右上角 UI 层）----------------
    def _cell_to_map(self, gx: float, gz: float) -> tuple[float, float]:
        # 连续网格坐标 -> 小地图局部 UI 坐标（+z 向下）
        return (gx - COLS / 2) * MINIMAP_CELL, -(gz - ROWS / 2) * MINIMAP_CELL

    def _build_minimap(self) -> None:
        cs = MINIMAP_CELL
        self.minimap = Entity(parent=camera.ui, position=MINIMAP_POS)
        self.map_nodes.append(self.minimap)
        # 背景遮板（先创建，序在最底）
        bg = Entity(
            parent=self.minimap, model="quad",
            color=color.rgba32(8, 10, 18, 200),
            scale=(COLS * cs + 0.01, ROWS * cs + 0.01), position=(0, 0, 1),
        )
        self.map_nodes.append(bg)

        # 墙体：每个 WALL 格一个小方块
        for r, row in enumerate(self.grid):
            for c, val in enumerate(row):
                if val != WALL:
                    continue
                lx, ly = self._cell_to_map(c, r)
                dot = Entity(parent=self.minimap, model="quad", color=color.rgb32(150, 158, 190), scale=cs, position=(lx, ly))
                self.map_nodes.append(dot)

        # 出口：绿色标记
        ex, ey = self._cell_to_map(*self.exit_cell)
        exit_dot = Entity(parent=self.minimap, model="quad", color=color.rgb32(40, 220, 120), scale=cs * 1.6, position=(ex, ey))
        self.map_nodes.append(exit_dot)

        # 钥匙：金色标记（与 self.keys 同序，便于拾取时同步移除）
        self.map_keys = []
        for key in self.keys:
            kc = self.world_to_cell(key.x, key.z)
            kx, ky = self._cell_to_map(*kc)
            kd = Entity(parent=self.minimap, model="quad", color=color.gold, scale=cs * 1.3, position=(kx, ky))
            self.map_keys.append(kd)
            self.map_nodes.append(kd)

        # 玩家：白点 + 朝向短红线（最后创建，序在最顶）
        self.map_player = Entity(parent=self.minimap, model="quad", color=color.white, scale=cs * 1.4, position=(0, 0))
        self.map_facing = Entity(parent=self.minimap, model="quad", color=color.red, scale=(cs * 3.0, cs * 0.5), origin=(-0.5, 0), position=(0, 0))
        self.map_nodes.extend([self.map_player, self.map_facing])
        self._update_minimap()

    # ---------------- 每帧更新（由全局 update 调用）----------------
    def update(self) -> None:
        # 出口门柱自转，保持一点生气
        if hasattr(self, "exit_glow"):
            self.exit_glow.rotation_y += 40 * ursina_time.dt

        if self.state != "playing":
            self.message.text = ""
            return

        # 未锁定鼠标视为暂停：冻结视角与移动，避免光标飞出后拖拽视角、误以为失控
        if not mouse.locked:
            self.message.text = "已暂停 —— 点击画面或按空格继续"
            return

        # 底部临时消息：计时到点自动清除
        if self._msg_timer > 0:
            self._msg_timer -= ursina_time.dt
            if self._msg_timer <= 0:
                self.message.text = ""

        # 新手引导：按时间逐条弹出提示
        if self._coach_queue:
            self._coach_timer -= ursina_time.dt
            if self._coach_timer <= 0:
                dur, tip = self._coach_queue.pop(0)
                self.coach.text = tip
                self._coach_timer = dur
        elif self.coach.visible:
            self.coach.visible = False

        # 视角：鼠标速度是每帧归一化位移，乘以灵敏度
        # 实测确认（截图验证）：ursina 相机 rotation=(pitch, yaw, 0)，
        #   rotation.x 正值朝下看；pitch 定义为鼠标上移为正，直接传入即可
        vel = mouse.velocity
        self.yaw += vel[0] * MOUSE_SENS
        self.pitch -= vel[1] * MOUSE_SENS
        self.pitch = max(-80.0, min(80.0, self.pitch))
        camera.rotation = Vec3(self.pitch, self.yaw, 0)

        yaw_rad = math.radians(self.yaw)
        forward = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad))
        right = Vec3(math.cos(yaw_rad), 0, -math.sin(yaw_rad))

        # 注意：held_keys 是 defaultdict，按键松开后条目仍在字典里（值为 0），
        # 必须按键取值判真值，绝不能用 `"w" in held_keys`（按过一次就永远为 True）
        move = Vec3(0, 0, 0)
        if held_keys["w"]:
            move += forward
        if held_keys["s"]:
            move -= forward
        if held_keys["d"]:
            move += right
        if held_keys["a"]:
            move -= right

        length = math.hypot(move.x, move.z)
        if length > 0:
            running = bool(held_keys["left shift"] or held_keys["right shift"])
            speed = RUN_SPEED if running else WALK_SPEED
            step_x = move.x / length * speed * ursina_time.dt
            step_z = move.z / length * speed * ursina_time.dt
            old_x, old_z = self.px, self.pz
            # 分轴推进 → 贴墙时能顺着墙滑行，不会被卡死
            if not self.is_blocked(self.px + step_x, self.pz):
                self.px += step_x
            if not self.is_blocked(self.px, self.pz + step_z):
                self.pz += step_z
            # 脚步声：按实际移动距离累计，跨过一个步幅阈值踩一步
            moved = math.hypot(self.px - old_x, self.pz - old_z)
            if moved > 0 and self.sfx:
                self._step_dist += moved
                step_len = STEP_LEN_RUN if running else STEP_LEN_WALK
                if self._step_dist >= step_len:
                    self._step_dist -= step_len
                    self.sfx["run" if running else "walk"].play()

        camera.position = Vec3(self.px, EYE_HEIGHT, self.pz)
        self._update_minimap()

        # 钥匙自转 + 上下浮动 + 拾取判定
        for i, key in enumerate(list(self.keys)):
            key.rotation_y += 120 * ursina_time.dt
            key.y = 1.4 + 0.15 * math.sin(time.time() * 2.5 + i * 1.7)
            if math.dist((key.x, key.z), (self.px, self.pz)) < CELL * 0.45:
                idx = self.keys.index(key)
                self.keys.remove(key)
                self.nodes.remove(key)
                destroy(key)
                # 同步移除小地图上的金色标记
                if 0 <= idx < len(self.map_keys):
                    marker = self.map_keys.pop(idx)
                    self.map_nodes.remove(marker)
                    destroy(marker)
                self.collected += 1
                self._update_hud()
                self._flash(f"捡到钥匙！  {self.collected} / {self.total_keys}", 2.0)

        # 到达出口：集齐钥匙则通关，否则提示还差多少
        if math.dist((self.exit_pos_x(), self.exit_pos_z()), (self.px, self.pz)) < CELL * 0.6:
            if self.collected >= self.total_keys:
                self._win()
            else:
                remain = self.total_keys - self.collected
                self._flash(f"出口还锁着 —— 还差 {remain} 把钥匙", 0.5)
        elif self._msg_timer <= 0:
            self.message.text = ""

    def exit_pos_x(self) -> float:
        return self.cell_to_world(*self.exit_cell)[0]

    def exit_pos_z(self) -> float:
        return self.cell_to_world(*self.exit_cell)[1]

    def _update_hud(self) -> None:
        if self.collected >= self.total_keys:
            goal = "钥匙齐了！去碰绿色门柱就逃脱"
        else:
            goal = "找漂浮的金色发光方块（小地图金点）"
        self.hud.text = f"钥匙 {self.collected} / {self.total_keys}\n{goal}"

    def _update_minimap(self) -> None:
        # 把玩家连续坐标映到小地图，并旋转朝向短线
        if self.map_player is None:
            return
        gx = self.px / CELL + COLS / 2
        gz = self.pz / CELL + ROWS / 2
        lx, ly = self._cell_to_map(gx, gz)
        self.map_player.position = (lx, ly)
        if self.map_facing is not None:
            # 视线 (sin yaw, cos yaw) 映射到小地图：地图 +x 右、+y 上（对应世界 -z）
            yaw_rad = math.radians(self.yaw)
            angle = math.degrees(math.atan2(-math.cos(yaw_rad), math.sin(yaw_rad)))
            self.map_facing.position = (lx, ly)
            self.map_facing.rotation_z = angle

    def _win(self) -> None:
        self.state = "won"
        mouse.locked = False
        self.hud.text = ""
        self.message.text = ""
        self.coach.visible = False
        self.overlay.text = (
            "★  你逃出了迷宫！  ★\n\n"
            f"共收集 {self.collected} 把钥匙\n\n"
            "R  再来一局随机迷宫        Esc  退出游戏"
        )
        self._set_overlay(True, with_button=False)

    # ---------------- 键盘输入（由全局 input 调用）----------------
    def input(self, key: str) -> None:
        if key == "space" and self.state == "start":
            self._begin()
        elif key in ("space", "left mouse down") and self.state == "playing" and not mouse.locked:
            mouse.locked = True           # 从暂停中继续
        elif key == "r":
            self.state = "start"
            self.new_maze()
            self._refresh_start_overlay()
            mouse.locked = False
        elif key == "escape":
            if self.state == "playing":
                mouse.locked = False        # 暂停并释放鼠标
            else:
                application.quit()


# 全局实例与 ursina 约定的全局回调函数（ursina 每帧调用 __main__.update / __main__.input）
game: MazeGame | None = None


def update() -> None:
    if game is not None:
        game.update()


def input(key: str) -> None:  # noqa: A001  （ursina 约定：主脚本里定义 input 接收按键）
    if game is not None:
        game.input(key)


if __name__ == "__main__":
    # development_mode=False：关掉右上角红X/fps/实体计数等开发调试件，正式游玩界面不需要
    app = Ursina(title="3D 迷宫逃脱", borderless=False, fullscreen=False,
                 development_mode=False)
    window.size = (1280, 720)
    game = MazeGame()
    app.run()
