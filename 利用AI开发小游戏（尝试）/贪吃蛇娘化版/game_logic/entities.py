# -*- coding: utf-8 -*-
"""
game_logic/entities.py —— 游戏里的所有实体

设计要点（按你的要求）：
  · 蛇身长度固定，不随吃东西变长
  · 成长体现在等级、伤害、技能解锁上
  · 难度靠小怪变强变多，不靠蛇变长
"""

import math
import random

import pygame

import settings as S
from core.asset_manager import angle_between


# ======================================================================
#  娘化角色蛇
# ======================================================================
class SnakeGirl:
    """
    蛇娘本体。

    身体分成两部分画：
      · 上半身 = 一张人物立绘，贴在蛇头位置
      · 下半身 = 一串「尾椎」贴图，沿蛇头走过的路径反向排布
                越靠近头越粗，越靠尾越细（靠贴图本身缩放实现）
    """

    def __init__(self, char_id="sakura", start_cell=(6, 6), direction=(1, 0)):
        self.char_id = char_id
        self.grid_pos = [float(start_cell[0]), float(start_cell[1])]   # 逻辑格子坐标（浮点，便于插值）
        self.prev_grid_pos = list(self.grid_pos)
        self.direction = direction                                     # 当前方向
        self.next_direction = direction
        self.move_timer = 0.0

        # ---- 成长属性 ----
        self.level = 1
        self.exp = 0
        self.hp = S.HP_MAX
        self.invincible = 0.0
        self.alive = True

        # ---- 路径历史：记录蛇头经过的点，用来摆放尾椎 ----
        self.path = []                                                 # [(x, y), ...] 屏幕像素
        self.body_length = S.SNAKE_LEN                                 # 固定身长
        self.cells = []                                                # 当前占据的所有格子（含头）

        # ---- 视觉 ----
        self.facing_angle = 0.0                                        # 立绘朝向
        self.bob_t = random.random() * 6.28                            # 呼吸浮动相位

        self._rebuild_cells()
        self._init_path()

    # ------------------------------------------------------------ 初始化
    def _init_path(self):
        """初始路径：沿身体反方向铺一条直线，免得开局尾椎全挤在头上"""
        hx, hy = self.grid_pos
        total = S.BODY_SEG_LEN * (self.body_length + 2)
        self.path = []
        for i in range(total, -1, -1):
            self.path.append((hx * S.CELL_SIZE + S.CELL_SIZE / 2 - self.direction[0] * i,
                              hy * S.CELL_SIZE + S.CELL_SIZE / 2 - self.direction[1] * i))

    def _rebuild_cells(self):
        """
        根据当前格子位置，重建身体占据的格子列表（用于碰撞与渲染定位）。

        注意：沿移动方向反推格子时要做去重。
        如果不去重，转弯瞬间会出现两个身体节指向同一格，
        导致 is_self_hit() 误判成"撞到自己"，白扣血。
        """
        self.cells = []
        seen = set()
        cx, cy = round(self.grid_pos[0]), round(self.grid_pos[1])
        dx, dy = self.direction
        for i in range(self.body_length):
            cell = (cx - dx * i, cy - dy * i)
            if cell in seen:
                continue
            seen.add(cell)
            self.cells.append(cell)

    # ---------------------------------------------------------------- 移动
    def set_direction(self, nd):
        """设置方向。禁止 180 度掉头（会直接撞死自己）"""
        if (nd[0] == -self.direction[0] and nd[1] == -self.direction[1]):
            return
        self.next_direction = nd

    def update(self, dt, grid_cols, grid_rows):
        """每帧更新：按固定节奏走格子，同时把路径点记下来"""
        if not self.alive:
            return
        if self.invincible > 0:
            self.invincible -= dt

        self.prev_grid_pos = list(self.grid_pos)
        self.move_timer += dt

        while self.move_timer >= S.MOVE_INTERVAL:
            self.move_timer -= S.MOVE_INTERVAL
            self.direction = self.next_direction
            nx = self.grid_pos[0] + self.direction[0]
            ny = self.grid_pos[1] + self.direction[1]

            if nx < 0 or ny < 0 or nx >= grid_cols or ny >= grid_rows:
                self._on_wall_hit(grid_cols, grid_rows)
                # 撞完墙这一 tick 不再前进，避免连撞
                continue

            self.grid_pos = [float(nx), float(ny)]
            self._rebuild_cells()

    def _on_wall_hit(self, cols, rows):
        """
        撞墙处理。

        踩过的坑：不能简单掉头，否则下一 tick 立刻撞上对面的墙，
        每 0.16 秒掉 1 血，两秒就死了。
        正确做法是原地改成「沿墙」方向，把玩家留在墙边安全走。
        """
        self.take_damage(1)

        cx = min(max(round(self.grid_pos[0]), 0), cols - 1)
        cy = min(max(round(self.grid_pos[1]), 0), rows - 1)
        self.grid_pos = [float(cx), float(cy)]

        # 优先挑一个「能走出去」的方向：排除掉头，也排除会立刻再次撞墙的
        back = (-self.direction[0], -self.direction[1])
        safe = []
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            if (dx, dy) == back:
                continue
            px, py = cx + dx, cy + dy
            if 0 <= px < cols and 0 <= py < rows:
                safe.append((dx, dy))

        if safe:
            # 优先往「离墙更远」的方向走，避免贴着墙来回蹭
            def dist_to_wall(d):
                px, py = cx + d[0], cy + d[1]
                return min(px, py, cols - 1 - px, rows - 1 - py)
            turn = [d for d in safe if d != self.direction] or safe
            self.direction = max(turn, key=dist_to_wall)
        else:
            self.direction = back          # 极端情况兜底

        self.next_direction = self.direction
        # 撞墙后给一段短暂保护，防止玩家贴墙时被连续扣血扣死
        self.invincible = max(self.invincible, S.WALL_IFRAME)
        self._rebuild_cells()
        self._init_path()                  # 路径重建，尾椎别挂在墙外

    def is_self_hit(self):
        """头撞到自己身体"""
        head = self.cells[0]
        return head in self.cells[1:]

    def take_damage(self, amount):
        if self.invincible > 0 or not self.alive:
            return False
        self.hp -= amount
        self.invincible = S.IFRAME_TIME
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return True

    # ---------------------------------------------------------------- 成长
    def gain_exp(self, amount):
        """加经验，可能连升多级。返回升了几级。"""
        if self.level >= S.LEVEL_MAX:
            return 0
        self.exp += amount
        gained = 0
        while self.exp >= self.exp_needed() and self.level < S.LEVEL_MAX:
            self.exp -= self.exp_needed()
            self.level += 1
            gained += 1
        if gained:
            self.on_level_up(gained)
        return gained

    def exp_needed(self):
        return S.EXP_PER_LEVEL + (self.level - 1) * 12

    def on_level_up(self, gained):
        """升级奖励：这里先只加伤害，技能解锁留给下一阶段"""
        pass

    @property
    def attack(self):
        return S.ATK_BASE + (self.level - 1) * S.ATK_PER_LEVEL

    # ------------------------------------------------------------ 渲染坐标
    @property
    def draw_pos(self):
        """
        渲染位置 = 上一格和当前格之间插值。
        不做插值的话，蛇会一格一格瞬移，4K 下观感很廉价。
        """
        t = min(1.0, self.move_timer / S.MOVE_INTERVAL)
        cx = (self.prev_grid_pos[0] + (self.grid_pos[0] - self.prev_grid_pos[0]) * t) * S.CELL_SIZE + S.CELL_SIZE / 2
        cy = (self.prev_grid_pos[1] + (self.grid_pos[1] - self.prev_grid_pos[1]) * t) * S.CELL_SIZE + S.CELL_SIZE / 2
        return cx, cy

    def update_path(self, dt):
        """把渲染位置追加进路径，并裁掉过长的部分"""
        px, py = self.draw_pos
        if not self.path or math.hypot(px - self.path[-1][0], py - self.path[-1][1]) > 1.5:
            self.path.append((px, py))
        max_pts = S.BODY_SEG_LEN * (self.body_length + 3)
        if len(self.path) > max_pts:
            self.path = self.path[-max_pts:]

    def sample_tail_points(self):
        """
        沿路径反向均匀采样，得到每节尾椎的位置。
        返回 [(x, y, angle, scale), ...]，从靠近头到靠近尾。
        """
        if len(self.path) < 2:
            return []
        pts = []
        seg_len = S.BODY_SEG_LEN
        n = self.body_length
        # 从路径末端（也就是蛇头）往回走
        for i in range(1, n + 1):
            dist = seg_len * i
            p = self._point_at_distance_from_head(dist)
            if p is None:
                break
            nx, ny = self._point_at_distance_from_head(dist + 6) or p
            ang = angle_between((nx, ny), p)
            t = (i - 1) / max(1, n - 1)
            scale = S.BODY_SCALE_HEAD + (S.BODY_SCALE_TAIL - S.BODY_SCALE_HEAD) * t
            pts.append((p[0], p[1], ang, scale))
        return pts

    def _point_at_distance_from_head(self, dist):
        """从蛇头沿路径往回数 dist 像素，返回那个点"""
        if not self.path:
            return None
        acc = 0.0
        cur = self.path[-1]
        for i in range(len(self.path) - 2, -1, -1):
            prev = self.path[i]
            d = math.hypot(cur[0] - prev[0], cur[1] - prev[1])
            if acc + d >= dist:
                ratio = (dist - acc) / d if d > 1e-6 else 0.0
                return (cur[0] + (prev[0] - cur[0]) * ratio,
                        cur[1] + (prev[1] - cur[1]) * ratio)
            acc += d
            cur = prev
        return None

    def facing_update(self):
        self.facing_angle = angle_between(
            (0, 0), (self.direction[0], self.direction[1])
        )


# ======================================================================
#  掉落物
# ======================================================================
class Drop:
    """地上可以捡的东西：经验果 / 能量结晶 / 星尘 / 爱心"""

    KINDS = {
        "exp":      {"asset": "items/exp_berry.png",      "size": 44, "color": (240, 186, 96)},
        "crystal":  {"asset": "items/energy_crystal.png", "size": 44, "color": (120, 210, 200)},
        "stardust": {"asset": "items/energy_crystal.png", "size": 36, "color": (200, 160, 255)},
        "heart":    {"asset": "items/exp_berry.png",      "size": 40, "color": (226, 84, 110)},
    }

    def __init__(self, kind, cell):
        self.kind = kind
        self.cell = cell
        self.alive = True
        cfg = self.KINDS[kind]
        self.asset = cfg["asset"]
        self.size = cfg["size"]
        self.color = cfg["color"]
        self.t = random.random() * 6.28
        cx = cell[0] * S.CELL_SIZE + S.CELL_SIZE / 2
        cy = cell[1] * S.CELL_SIZE + S.CELL_SIZE / 2
        self.pos = (cx, cy)

    def update(self, dt):
        self.t += dt * 2.6

    @property
    def draw_pos(self):
        """上下浮动，看起来像在呼吸"""
        return (self.pos[0], self.pos[1] + math.sin(self.t) * 4)


# ======================================================================
#  小怪
# ======================================================================
class Mob:
    """
    小怪。会走动，也会追人。
    碰到玩家扣血，被玩家撞也会掉血。

    难度成长体现在三处：
      1. 血量变厚
      2. 数量变多
      3. 追击欲望变强（chase 概率随时间提升）
    """

    def __init__(self, cell, hp_mult=1.0, speed_mult=1.0, chase=0.0):
        self.cell = [float(cell[0]), float(cell[1])]
        self.prev_cell = list(self.cell)
        self.target = list(self.cell)
        self.hp_max = int(S.MOB_HP * hp_mult)
        self.hp = self.hp_max
        self.alive = True
        self.move_timer = 0.0
        self.interval = 0.62 / speed_mult
        self.hit_flash = 0.0
        self.knock = (0.0, 0.0)
        self.t = random.random() * 6.28
        self.chase = chase                      # 0~1，越高越倾向朝玩家走

    def pick_target(self, cols, rows, avoid, player_cell=None):
        """
        选下一个目标格。
        chase 概率决定"追玩家"还是"随机游走"。
        """
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        cx, cy = round(self.cell[0]), round(self.cell[1])

        if player_cell is not None and random.random() < self.chase:
            # 追击：朝玩家方向挑一个能走的格子
            px, py = player_cell
            dx = 0 if px == cx else (1 if px > cx else -1)
            dy = 0 if py == cy else (1 if py > cy else -1)
            prefer = []
            if abs(px - cx) >= abs(py - cy):
                prefer = [(dx, 0), (0, dy)]
            else:
                prefer = [(0, dy), (dx, 0)]
            for d in prefer + dirs:
                if d == (0, 0):
                    continue
                nx, ny = cx + d[0], cy + d[1]
                if 0 <= nx < cols and 0 <= ny < rows and (nx, ny) not in avoid:
                    self.target = [float(nx), float(ny)]
                    return

        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cols and 0 <= ny < rows and (nx, ny) not in avoid:
                self.target = [float(nx), float(ny)]
                return

    def update(self, dt, cols, rows, avoid, player_cell=None):
        if self.hit_flash > 0:
            self.hit_flash -= dt
        self.t += dt * 3.0
        kx, ky = self.knock
        if abs(kx) > 0.01 or abs(ky) > 0.01:
            kx -= kx * min(1.0, dt * 7) * 0.75
            ky -= ky * min(1.0, dt * 7) * 0.75
            self.knock = (kx, ky)

        self.prev_cell = list(self.cell)
        self.move_timer += dt
        if self.move_timer >= self.interval:
            self.move_timer = 0.0
            self.prev_cell = list(self.cell)
            if (abs(self.cell[0] - self.target[0]) < 0.01
                    and abs(self.cell[1] - self.target[1]) < 0.01):
                self.pick_target(cols, rows, avoid, player_cell)
            tx, ty = self.target
            self.cell[0] += max(-1, min(1, tx - self.cell[0]))
            self.cell[1] += max(-1, min(1, ty - self.cell[1]))

    def take_damage(self, amount):
        self.hp -= amount
        self.hit_flash = 0.18
        if self.hp <= 0:
            self.alive = False
        return not self.alive

    def knockback(self, from_pos, strength=0.55):
        cx = self.draw_pos[0]
        cy = self.draw_pos[1]
        dx = cx - from_pos[0]
        dy = cy - from_pos[1]
        d = math.hypot(dx, dy) or 1.0
        self.knock = (dx / d * strength, dy / d * strength)

    @property
    def draw_pos(self):
        t = min(1.0, self.move_timer / max(0.01, self.interval))
        cx = (self.prev_cell[0] + (self.cell[0] - self.prev_cell[0]) * t) * S.CELL_SIZE + S.CELL_SIZE / 2
        cy = (self.prev_cell[1] + (self.cell[1] - self.prev_cell[1]) * t) * S.CELL_SIZE + S.CELL_SIZE / 2
        return (cx + self.knock[0], cy + self.knock[1])
