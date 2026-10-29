# 3D迷宫探索 —— ursina 第一人称迷宫逃脱
#
# 运行方式：直接 Run 本文件（main.py），会弹出一个 3D 窗口。
# 操作：按【空格】开始并锁定鼠标 → WASD 移动 / Shift 奔跑 / 移动鼠标转视角
#       找到全部 5 把金色钥匙，走到绿色出口即可逃脱；
#       R 随机换一局新迷宫，Esc 在未开始时退出、游戏中释放鼠标。
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
    color,
    camera,
    scene,
    mouse,
    window,
    held_keys,
    destroy,
    application,
)

from maze_generator import FLOOR, WALL, farthest_cell, floor_cells, generate_maze

# ---------------- 全局可调参数 ----------------
CELL = 4.0            # 每个网格对应世界的单位（即通道宽度）
COLS = 21             # 迷宫列数（奇数）
ROWS = 21             # 迷宫行数（奇数）
WALL_HEIGHT = 4.0     # 墙高
EYE_HEIGHT = 1.7      # 视点离地高度
PLAYER_RADIUS = 0.7   # 玩家碰撞半径（必须小于 CELL/2，否则卡在通道里）
WALK_SPEED = 6.0      # 步行速度（单位/秒）
RUN_SPEED = 10.5      # 奔跑速度（单位/秒）
MOUSE_SENS = 35.0     # 鼠标灵敏度（对齐 ursina FirstPersonController 量级）
KEY_COUNT = 5         # 需要收集的钥匙数量


class MazeGame:
    def __init__(self) -> None:
        self._setup_font()
        self.grid: list[list[int]] = []
        self.nodes: list[Entity] = []       # 本局生成的所有实体，换局时销毁
        self.keys: list[Entity] = []        # 尚未被收集的钥匙
        self.exit_cell: tuple[int, int] = (0, 0)
        self.total_keys = KEY_COUNT
        self.collected = 0
        self.state = "start"                # start / playing / won

        # 玩家位姿（网格平面坐标 + 视角）
        self.px = 0.0
        self.pz = 0.0
        self.yaw = 0.0
        self.pitch = 0.0

        scene.clear_color = color.rgb(12, 14, 22)
        camera.clip_plane_far = 200
        mouse.locked = False

        self._build_ui()
        self.new_maze()

    # ---------------- 中文字体 ----------------
    def _setup_font(self) -> None:
        # ursina 默认字体不含中文；fonts/simhei.ttf 存在时切换为黑体，否则原样运行
        font_file = Path(__file__).resolve().parent / "fonts" / "simhei.ttf"
        if font_file.exists():
            Text.default_font = "simhei.ttf"
            Text.default_monospace_font = "simhei.ttf"

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
        self.hud = Text(
            text="", position=(-0.48, 0.46), origin=(-0.5, 0.5),
            color=color.white, size=20, background=True,
        )
        self.message = Text(
            text="", position=(0, -0.42), origin=(0, 0.5),
            color=color.gold, size=22,
        )
        self.overlay = Text(
            text="", position=(0, 0), origin=(0, 0),
            color=color.white, size=30, background=True,
        )

    def _refresh_start_overlay(self) -> None:
        self.overlay.enabled = True
        self.overlay.text = (
            "【 3D 迷宫逃脱 】\n\n"
            "找到 5 把金色钥匙，再冲向绿色出口即可逃脱\n\n"
            "空格 开始        WASD 移动\n"
            "Shift 奔跑       鼠标 转视角\n"
            "R 换一局迷宫     Esc 释放鼠标 / 退出"
        )

    # ---------------- 生成新的一局 ----------------
    def new_maze(self) -> None:
        for node in self.nodes:
            destroy(node)
        self.nodes.clear()
        self.keys.clear()
        self.collected = 0

        seed = random.randint(0, 10 ** 9)
        self.grid = generate_maze(COLS, ROWS, seed=seed)
        self._build_maze_geometry()
        self._place_player_and_items()
        self._update_hud()

    def _build_maze_geometry(self) -> None:
        # 地板 + 天花板（把整个迷宫封闭起来，无需天空盒）
        floor = Entity(
            model="quad", color=color.rgb(45, 48, 66),
            rotation_x=90, scale=(COLS * CELL, ROWS * CELL), position=(0, 0, 0),
        )
        ceiling = Entity(
            model="quad", color=color.rgb(22, 24, 34),
            rotation_x=-90, scale=(COLS * CELL, ROWS * CELL), position=(0, WALL_HEIGHT, 0),
        )
        self.nodes.extend([floor, ceiling])

        # 墙体：每个 WALL 格放一个立方体（纯视觉，碰撞走网格逻辑）
        wall_color = color.rgb(96, 84, 118)
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
        self.yaw, self.pitch = 0.0, 0.0

        # 出口：发光的绿色门柱
        ex, ez = self.cell_to_world(*self.exit_cell)
        pillar = Entity(
            model="cube", color=color.rgb(40, 220, 120),
            position=(ex, WALL_HEIGHT / 2, ez), scale=(CELL * 0.5, WALL_HEIGHT, CELL * 0.5),
        )
        glow = Entity(
            model="cube", color=color.rgb(80, 255, 150),
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
                model="cube", color=color.gold,
                position=(x, 1.2, z), scale=(0.7, 0.7, 0.7),
            )
            key.rotation_y = random.uniform(0, 360)
            self.keys.append(key)
            self.nodes.append(key)

    # ---------------- 每帧更新（由全局 update 调用）----------------
    def update(self) -> None:
        # 出口门柱自转，保持一点生气
        if hasattr(self, "exit_glow"):
            self.exit_glow.rotation_y += 40 * time.dt

        if self.state != "playing":
            self.message.text = ""
            return

        # 视角：鼠标速度是每帧归一化位移，乘以灵敏度
        vel = getattr(mouse, "velocity", Vec3(0, 0, 0))
        self.yaw += vel[0] * MOUSE_SENS
        self.pitch -= vel[1] * MOUSE_SENS
        self.pitch = max(-80.0, min(80.0, self.pitch))
        camera.rotation = Vec3(self.pitch, self.yaw, 0)

        # 朝向：直接用 camera 的世界前/右向量拍平到水平面，规避朝向约定问题
        f = camera.forward
        r = camera.right
        forward = Vec3(f.x, 0, f.z)
        right = Vec3(r.x, 0, r.z)

        move = Vec3(0, 0, 0)
        if "w" in held_keys:
            move += forward
        if "s" in held_keys:
            move -= forward
        if "d" in held_keys:
            move += right
        if "a" in held_keys:
            move -= right

        length = math.hypot(move.x, move.z)
        if length > 0:
            speed = RUN_SPEED if "shift" in held_keys else WALK_SPEED
            step_x = move.x / length * speed * time.dt
            step_z = move.z / length * speed * time.dt
            # 分轴推进 → 贴墙时能顺着墙滑行，不会被卡死
            if not self.is_blocked(self.px + step_x, self.pz):
                self.px += step_x
            if not self.is_blocked(self.px, self.pz + step_z):
                self.pz += step_z

        camera.position = Vec3(self.px, EYE_HEIGHT, self.pz)

        # 钥匙自转 + 拾取判定
        for key in list(self.keys):
            key.rotation_y += 120 * time.dt
            key.rotation_x += 60 * time.dt
            if math.dist((key.x, key.z), (self.px, self.pz)) < CELL * 0.45:
                self.keys.remove(key)
                self.nodes.remove(key)
                destroy(key)
                self.collected += 1
                self._update_hud()

        # 到达出口：集齐钥匙则通关，否则提示还差多少
        if math.dist((self.exit_pos_x(), self.exit_pos_z()), (self.px, self.pz)) < CELL * 0.6:
            if self.collected >= self.total_keys:
                self._win()
            else:
                remain = self.total_keys - self.collected
                self.message.text = f"出口还锁着 —— 还差 {remain} 把钥匙"
        else:
            self.message.text = ""

    def exit_pos_x(self) -> float:
        return self.cell_to_world(*self.exit_cell)[0]

    def exit_pos_z(self) -> float:
        return self.cell_to_world(*self.exit_cell)[1]

    def _update_hud(self) -> None:
        self.hud.text = f"钥匙  {self.collected} / {self.total_keys}"

    def _win(self) -> None:
        self.state = "won"
        mouse.locked = False
        self.hud.text = ""
        self.message.text = ""
        self.overlay.enabled = True
        self.overlay.text = (
            "★  你逃出了迷宫！  ★\n\n"
            f"共收集 {self.collected} 把钥匙\n\n"
            "R 再来一局        Esc 退出"
        )

    # ---------------- 键盘输入（由全局 input 调用）----------------
    def input(self, key: str) -> None:
        if key == "space" and self.state == "start":
            self.state = "playing"
            self.overlay.enabled = False
            mouse.locked = True
        elif key == "r":
            self.state = "start"
            self.new_maze()
            self._refresh_start_overlay()
            mouse.locked = False
        elif key == "escape":
            if self.state == "playing":
                mouse.locked = False        # 释放鼠标好退出/调试
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
    app = Ursina(title="3D 迷宫逃脱", borderless=False, fullscreen=False)
    window.size = (1280, 720)
    game = MazeGame()
    app.run()
