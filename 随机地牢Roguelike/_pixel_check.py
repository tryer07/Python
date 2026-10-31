"""临时验证驱动：无头跑通像素版，并实拍几个关键画面。用完即删。"""
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
VENV = os.path.abspath(os.path.join(ROOT, "..", ".venv", "Lib", "site-packages"))
if VENV not in sys.path:
    sys.path.append(VENV)

import pygame  # noqa: E402
import game as game_mod  # noqa: E402
from settings import MAP_H, MAP_W  # noqa: E402

SHOT_DIR = os.path.join(ROOT, "截图检查")
os.makedirs(SHOT_DIR, exist_ok=True)

g = game_mod.Game()


def bfs(start, target, ok):
    seen = {start}
    queue = [start]
    parent = {start: None}
    while queue:
        cur = queue.pop(0)
        if cur == target:
            path = []
            while cur != start:
                path.append(cur)
                cur = parent[cur]
            return path[::-1]
        x, y = cur
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < MAP_W and 0 <= ny < MAP_H and (nx, ny) not in seen and ok((nx, ny)):
                seen.add((nx, ny))
                parent[(nx, ny)] = cur
                queue.append((nx, ny))
    return []


def walk(target):
    depth0 = g.depth
    for _ in range(60):
        path = bfs((g.player.x, g.player.y), target, g._walkable)
        if not path:
            return False
        for cell in path:
            if g.state != game_mod.STATE_PLAYING:
                return False
            g._try_move(cell[0] - g.player.x, cell[1] - g.player.y)
            if (g.player.x, g.player.y) == g.dungeon.stairs:
                return True          # 踩上楼梯会换层，target 立刻变陈旧
        if (g.player.x, g.player.y) == target:
            return True
        if g.depth != depth0:
            return True
    return False


def shoot(name):
    g._render()
    pygame.image.save(g.screen, os.path.join(SHOT_DIR, name))
    print("saved", name)


# 1 开局：火把视野 + 像素贴图
shoot("像素1_开局视野.png")
assert g.lit, "开局视野里一格都没点亮"
assert (g.player.x, g.player.y) in g.lit, "勇者脚下不该是黑的"

# 2 走到楼梯口，路上怪应该进视野
ok = walk(g.dungeon.stairs)
assert ok or (g.player.x, g.player.y) == g.dungeon.stairs, "没能走到楼梯"
print("走到楼梯:", ok, "层:", g.depth, "回合:", g.log.turn)
shoot("像素2_楼梯口遭遇.png")

# 3 一路下到第 3 层（精英守卫出现的那层）
g._new_run()
g.state = game_mod.STATE_PLAYING
guard = 0
while g.depth < 3 and g.state == game_mod.STATE_PLAYING:
    for m in g.monsters:
        if m.alive and abs(m.x - g.player.x) + abs(m.y - g.player.y) == 1:
            g._try_move(m.x - g.player.x, m.y - g.player.y)
    if g.state != game_mod.STATE_PLAYING:
        break
    if not walk(g.dungeon.stairs):
        break
    guard += 1
print("下潜次数:", guard, "当前层:", g.depth, "血量:", g.player.hp,
      "本层怪物:", [(m.name, m.is_boss) for m in g.monsters if m.alive])
shoot("像素3_深层.png")

# 4 把勇者挪到 explored 里离出生点最远的格子：此时旧房间应该以「记忆档」变暗保留
spawn_cell = g.dungeon.spawn
floors = [c for c in g.explored if g.dungeon.map[c[1]][c[0]] != 0]  # 墙能看见但不能站
far = max(floors, key=lambda c: abs(c[0] - spawn_cell[0]) + abs(c[1] - spawn_cell[1]))
g.player.x, g.player.y = far
g._update_view()
shoot("像素4_记忆档.png")
print("点亮格:", len(g.lit), "记忆格:", len(g.remembered),
      "explored:", len(g.explored), "总格:", MAP_W * MAP_H)
assert g.remembered, "走远后应当留下记忆格；一条都没有说明视野记不住地图"

# 5 死亡 + 验尸报告（离线就自然走本地兜底，不浪费网络额度）
g._new_run()
g.state = game_mod.STATE_PLAYING
g.player.hp = 1
g.end_turn()
if g.player.alive:          # 旁边没怪就不掉血，手动补刀保证进 DEAD
    g.player.hp = 0
    g.deaths += 1
    g.state = game_mod.STATE_DEAD
g.report_pending = False
g.report_text, g.report_ai = game_mod.write_report(g.log)
shoot("像素5_验尸报告.png")
print("状态:", g.state, "报告是否 AI:", g.report_ai)

# 6 通关画面
g._new_run()
g.state = game_mod.STATE_PLAYING
g.depth = game_mod.MAX_DEPTH + 1
g.state = game_mod.STATE_WIN
shoot("像素6_通关.png")

# 7 帧时间实测：主循环渲染 200 帧要多久
t0 = time.perf_counter()
for _ in range(200):
    g._render()
cost = (time.perf_counter() - t0) / 200 * 1000
print("平均每帧渲染 %.2f ms" % cost)
print("ALL DONE")
