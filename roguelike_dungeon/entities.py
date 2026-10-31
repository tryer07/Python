"""实体：玩家、怪物，以及怪物 AI 用的视线判定。

怪物 AI 刻意做得「傻得可读」：看得见玩家就直冲，看不见就原地晃。
这样玩家的策略（绕柱、卡走廊）才有意思，验尸报告里也才写得出故事。
"""

from collections.abc import Callable
from dataclasses import dataclass
from random import randint, random

from settings import PLAYER_ATK, PLAYER_HP

# 「这一格能不能站」的判定函数（game.py 里由地图+占位提供）
Walkable = Callable[[tuple[int, int]], bool]


@dataclass
class Player:
    x: int
    y: int
    hp: int = PLAYER_HP
    max_hp: int = PLAYER_HP
    atk: int = PLAYER_ATK
    kills: int = 0

    @property
    def pos(self) -> tuple[int, int]:
        return self.x, self.y

    def hurt(self, amount: int) -> None:
        self.hp = max(0, self.hp - amount)

    def heal(self, amount: int) -> int:
        """返回实际回复量（不溢出上限）"""
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    def grow_on_depth(self) -> None:
        """每下一层，玩家也变强一点，否则第 4 层根本打不动"""
        self.max_hp += 4
        self.hp = min(self.max_hp, self.hp + 8)
        self.atk += 1

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class Monster:
    name: str
    x: int
    y: int
    hp: int
    atk: int
    sight: int
    is_boss: bool = False
    xp: int = 1

    @property
    def pos(self) -> tuple[int, int]:
        return self.x, self.y

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def attack_player(self, player: Player) -> int:
        """怪物拍玩家一下，伤害带 ±1 浮动。返回实际伤害（写日志用）"""
        dmg = max(1, self.atk + randint(-1, 1))
        player.hurt(dmg)
        return dmg

    def take_hit(self, player_atk: int) -> int:
        """被玩家撞一下。返回实际伤害"""
        dmg = max(1, player_atk + randint(0, 2))
        self.hp -= dmg
        return dmg

    def choose_step(self, player: Player, walkable: Walkable) -> tuple[int, int] | None:
        """决定本回合移动。返回要去的新格子；相邻且能打到就返回 None（攻击在外部结算）"""
        distance = abs(self.x - player.x) + abs(self.y - player.y)
        if distance == 1:
            return None  # 贴脸了，这回合直接咬，不用挪窝
        if distance <= self.sight and line_of_sight(self.pos, player.pos, walkable):
            return self._chase_step(player, walkable)
        # 看不见玩家：20% 概率随机晃一格，让它永远不可预测
        if random() < 0.2:
            return self._wander_step(walkable)
        return None

    def _chase_step(self, player: Player, walkable: Walkable) -> tuple[int, int] | None:
        """贪心逼近：优先沿距离更大的轴走；被墙挡就试另一轴；两轴都堵就垂直方向滑墙，
        再不行后退一格——绝不让怪物对着墙站桩（第一版就栽在这）"""
        dx = player.x - self.x
        dy = player.y - self.y
        preferred = (
            ((self.x + _sign(dx), self.y), (self.x, self.y + _sign(dy)))
            if abs(dx) >= abs(dy)
            else ((self.x, self.y + _sign(dy)), (self.x + _sign(dx), self.y))
        )
        # 垂直于主方向的两个侧向格：把怪物从凹墙里「滑」出来
        slide = (
            (self.x + _sign(dy), self.y), (self.x - _sign(dy), self.y),
            (self.x, self.y + _sign(dx)), (self.x, self.y - _sign(dx)),
        )
        back = (self.x - _sign(dx), self.y), (self.x, self.y - _sign(dy))
        for cell in (*preferred, *slide, *back):
            if cell != (self.x, self.y) and walkable(cell):
                return cell
        return None

    def _wander_step(self, walkable: Walkable) -> tuple[int, int] | None:
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        start = randint(0, 3)  # 从随机方向起试，避免总往同一边晃
        for i in range(4):
            dx, dy = dirs[(start + i) % 4]
            cell = (self.x + dx, self.y + dy)
            if walkable(cell):
                return cell
        return None


def _sign(n: int) -> int:
    return (n > 0) - (n < 0)


def line_of_sight(a: tuple[int, int], b: tuple[int, int], walkable: Walkable) -> bool:
    """Bresenham 直线：从 a 到 b 逐格采样，中途碰墙就看不见。

    walkable 是「这格能不能站」的判定函数，怪物能穿过去的视野判定
    和它实际能走的格子保持一致，AI 才不会「看见玩家却隔着墙干瞪眼」。
    """
    x0, y0 = a
    x1, y1 = b
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx, sy = _sign(x1 - x0), _sign(y1 - y0)
    err = dx - dy
    while True:
        if (x0, y0) != a and (x0, y0) != b and not walkable((x0, y0)):
            return False
        if x0 == x1 and y0 == y1:
            return True
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
