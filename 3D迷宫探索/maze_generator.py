# 迷宫生成器 —— 纯逻辑，与图形无关，可单独运行测试
# 采用递归回溯算法（Recursive Backtracker），生成"完美迷宫"：任意两点间有且仅有一条路径

import random
from typing import List, Tuple

# 网格单元值：1 = 墙，0 = 通路
WALL = 1
FLOOR = 0


def generate_maze(cols: int, rows: int, seed: int | None = None) -> List[List[int]]:
    """
    生成 cols x rows 的迷宫网格（行列必须为奇数，否则边界会出错）。
    返回二维列表，grid[row][col]，值为 WALL(1) 或 FLOOR(0)。
    """
    if cols % 2 == 0 or rows % 2 == 0:
        raise ValueError("迷宫行列尺寸必须为奇数")

    rng = random.Random(seed)
    # 初始全部填墙
    grid = [[WALL] * cols for _ in range(rows)]

    # 从 (1,1) 出发 carved 通路；每次跨两格，中间那格一并打通
    def carve(cx: int, cy: int) -> None:
        grid[cy][cx] = FLOOR
        directions = [(2, 0), (-2, 0), (0, 2), (0, -2)]
        rng.shuffle(directions)
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if 0 < nx < cols - 1 and 0 < ny < rows - 1 and grid[ny][nx] == WALL:
                grid[cy + dy // 2][cx + dx // 2] = FLOOR
                carve(nx, ny)

    # 用显式栈替代递归，避免大迷宫触发递归深度上限
    stack: List[Tuple[int, int]] = [(1, 1)]
    grid[1][1] = FLOOR
    while stack:
        cx, cy = stack[-1]
        directions = [(2, 0), (-2, 0), (0, 2), (0, -2)]
        rng.shuffle(directions)
        moved = False
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if 0 < nx < cols - 1 and 0 < ny < rows - 1 and grid[ny][nx] == WALL:
                grid[cy + dy // 2][cx + dx // 2] = FLOOR
                grid[ny][nx] = FLOOR
                stack.append((nx, ny))
                moved = True
                break
        if not moved:
            stack.pop()

    return grid


def floor_cells(grid: List[List[int]]) -> List[Tuple[int, int]]:
    """返回所有通路的 (col, row) 坐标"""
    cells: List[Tuple[int, int]] = []
    for r, row in enumerate(grid):
        for c, val in enumerate(row):
            if val == FLOOR:
                cells.append((c, r))
    return cells


def farthest_cell(grid: List[List[int]], start: Tuple[int, int]) -> Tuple[int, int]:
    """
    从 start 出发做广度优先搜索，返回距离最远的通路格子。
    用于把出口放在离出生点最远的角落，保证游戏有足够探索量。
    """
    from collections import deque

    cols, rows = len(grid[0]), len(grid)
    seen = {start}
    queue = deque([(start, 0)])
    best, best_dist = start, 0
    while queue:
        (c, r), dist = queue.popleft()
        if dist > best_dist:
            best, best_dist = (c, r), dist
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if 0 <= nc < cols and 0 <= nr < rows and grid[nr][nc] == FLOOR and (nc, nr) not in seen:
                seen.add((nc, nr))
                queue.append(((nc, nr), dist + 1))
    return best


if __name__ == "__main__":
    # 命令行自测：打印一版小迷宫并检查连通性
    m = generate_maze(15, 15, seed=42)
    for row in m:
        print("".join("██" if v == WALL else "··" for v in row))
    start = (1, 1)
    exit_cell = farthest_cell(m, start)
    print(f"通路格数: {len(floor_cells(m))}, 出生点: {start}, 最远出口: {exit_cell}")
