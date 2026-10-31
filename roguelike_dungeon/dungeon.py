"""地宫生成器：随机房间 + L 形走廊连通，产出地图、出生点、怪物和药水坐标。

与迷宫生成器（递归回溯）不同，这里用 Roguelike 经典的「房间-走廊」方案：
先撒互不重叠的房间，再把相邻房间的中心用 L 形走廊打通，
最后用 BFS 验证从出生点能走到所有楼层要素，验证不过就整层重生成。
"""

from random import randrange, sample
from typing import NamedTuple

from settings import MAP_H, MAP_W, TILE_FLOOR, TILE_STAIRS, TILE_WALL


class Room(NamedTuple):
    """一个矩形房间，(x, y) 是左上角，不含右下边界外"""
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def overlaps(self, other: "Room", gap: int = 1) -> bool:
        """两房间之间至少留 gap 格间隔，避免糊成一个大通铺"""
        return not (
            self.x + self.w + gap <= other.x
            or other.x + other.w + gap <= self.x
            or self.y + self.h + gap <= other.y
            or other.y + other.h + gap <= self.y
        )


class Dungeon(NamedTuple):
    map: list[list[int]]                    # map[y][x]，值为 TILE_* 常量
    spawn: tuple[int, int]                  # 玩家出生坐标 (x, y)
    stairs: tuple[int, int]                 # 下行楼梯坐标
    enemy_spawns: list[tuple[int, int]]     # 普通怪物散布坐标（不含出生房间）
    boss_spawn: tuple[int, int] | None      # 守楼梯的精英怪坐标（第 3 层起才有）
    potion_spawns: list[tuple[int, int]]    # 药水散布坐标


def _carve_room(grid: list[list[int]], room: Room) -> None:
    for row in range(room.y, room.y + room.h):
        for col in range(room.x, room.x + room.w):
            grid[row][col] = TILE_FLOOR


def _carve_corridor(grid: list[list[int]], a: tuple[int, int], b: tuple[int, int]) -> None:
    """L 形走廊：先横着走再竖着走（顺序随机，避免所有走廊长得一样）"""
    ax, ay = a
    bx, by = b
    if randrange(2) == 0:
        xs = list(range(ax, bx + (1 if bx >= ax else -1), 1 if bx >= ax else -1))
        for x in xs:
            grid[ay][x] = TILE_FLOOR
        ys = list(range(ay, by + (1 if by >= ay else -1), 1 if by >= ay else -1))
        for y in ys:
            grid[y][bx] = TILE_FLOOR
    else:
        ys = list(range(ay, by + (1 if by >= ay else -1), 1 if by >= ay else -1))
        for y in ys:
            grid[y][ax] = TILE_FLOOR
        xs = list(range(ax, bx + (1 if bx >= ax else -1), 1 if bx >= ax else -1))
        for x in xs:
            grid[by][x] = TILE_FLOOR


def _reachable(grid: list[list[int]], start: tuple[int, int], target: tuple[int, int]) -> bool:
    """BFS 检查两个地板点之间是否连通"""
    from collections import deque

    seen: set[tuple[int, int]] = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        if (x, y) == target:
            return True
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < MAP_W and 0 <= ny < MAP_H \
                    and grid[ny][nx] != TILE_WALL and (nx, ny) not in seen:
                seen.add((nx, ny))
                queue.append((nx, ny))
    return False


def generate(depth: int) -> Dungeon:
    """生成一层地宫。depth 越大房间和怪物越多，精英怪从第 3 层起守在楼梯附近"""
    for _ in range(50):  # 极小概率撒不出连通布局，重试 50 次必成
        rooms = _try_rooms(depth)
        if rooms is None:
            continue
        grid = [[TILE_WALL] * MAP_W for _ in range(MAP_H)]
        for room in rooms:
            _carve_room(grid, room)
        for a, b in zip(rooms, rooms[1:]):
            _carve_corridor(grid, a.center, b.center)

        spawn = rooms[0].center
        stairs = rooms[-1].center
        if not _reachable(grid, spawn, stairs):
            continue

        floor_cells = [
            (x, y)
            for y in range(MAP_H) for x in range(MAP_W)
            if grid[y][x] != TILE_WALL
        ]
        # 怪物点：排除出生房间及其贴墙一圈，避免开局被贴脸
        spawn_room = rooms[0]
        enemy_pool = [
            c for c in floor_cells
            if not (spawn_room.x - 1 <= c[0] <= spawn_room.x + spawn_room.w
                    and spawn_room.y - 1 <= c[1] <= spawn_room.y + spawn_room.h)
        ]
        enemy_count = min(3 + depth, len(enemy_pool))
        # 第 3 层起在楼梯附近放一只精英守卫，逼玩家开局先想怎么过它
        guard_pool = [c for c in enemy_pool if abs(c[0] - stairs[0]) + abs(c[1] - stairs[1]) <= 6]
        if depth >= 3 and guard_pool:
            boss = sample(guard_pool, 1)[0]
            enemies = sample([c for c in enemy_pool if c != boss], enemy_count)
        else:
            boss = None
            enemies = sample(enemy_pool, enemy_count)
        potion_pool = [
            c for c in floor_cells
            if c not in enemies and c != boss and c != spawn and c != stairs
        ]
        potions = sample(potion_pool, min(2 + depth // 2, len(potion_pool)))

        grid[stairs[1]][stairs[0]] = TILE_STAIRS
        return Dungeon(grid, spawn, stairs, enemies, boss, potions)

    raise RuntimeError("地宫生成失败：50 次都没能连通，理论上不该发生")


def _try_rooms(depth: int) -> list[Room] | None:
    """撒 7~10 个互不重叠的房间；第一个是出生安全屋，最后一个是楼梯房，都收窄一点。
    上限卡在 10：40x24 的图再塞就必然摆不下，整层反复重生成"""
    count = min(6 + depth, 10)
    rooms: list[Room] = []
    for i in range(count):
        for _ in range(120):  # 单房间重试 120 次仍放不下，就整批重开
            w = randrange(5, 9) if i not in (0, count - 1) else randrange(5, 7)
            h = randrange(4, 7) if i not in (0, count - 1) else randrange(4, 6)
            x = randrange(1, MAP_W - w - 1)
            y = randrange(1, MAP_H - h - 1)
            room = Room(x, y, w, h)
            if not any(room.overlaps(r) for r in rooms):
                rooms.append(room)
                break
        else:
            return None
    return rooms
