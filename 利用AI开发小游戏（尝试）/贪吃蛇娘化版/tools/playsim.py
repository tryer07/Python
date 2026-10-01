# -*- coding: utf-8 -*-
"""
tools/playsim.py —— 自动试玩，用来验证平衡

模拟一个「还算聪明」的玩家：
  · 前方是墙就转向
  · 优先去捡最近的掉落物
  · 前方有小怪就尽量绕开

跑完输出一局的统计数据，用来判断难度曲线是否合理，
而不是靠手动试玩拍脑袋。
"""

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import settings as S  # noqa: E402
from core.game import Game  # noqa: E402
from scenes.battle import BattleScene  # noqa: E402


def choose_direction(scene):
    """替玩家做决策"""
    sn = scene.snake
    cx, cy = round(sn.grid_pos[0]), round(sn.grid_pos[1])
    cur = sn.direction

    head_cell = sn.cells[0]
    occupied = set(sn.cells[1:])
    mob_cells = {(round(m.cell[0]), round(m.cell[1])) for m in scene.mobs}

    def cell_ok(d):
        px, py = cx + d[0], cy + d[1]
        if not (0 <= px < S.GRID_COLS and 0 <= py < S.GRID_ROWS):
            return False
        if (px, py) in occupied:
            return False
        return True

    options = [d for d in ((1, 0), (-1, 0), (0, 1), (0, -1))
               if d != (-cur[0], -cur[1]) and cell_ok(d)]
    if not options:
        return cur

    # 目标：最近的掉落物
    target = None
    best = 10 ** 9
    for d in scene.drops:
        dist = abs(d.cell[0] - cx) + abs(d.cell[1] - cy)
        if dist < best:
            best, target = dist, d.cell

    def score(d):
        px, py = cx + d[0], cy + d[1]
        s = 0.0
        # 离墙太近扣分（避免贴墙送血）
        s -= max(0, 2 - min(px, py, S.GRID_COLS - 1 - px, S.GRID_ROWS - 1 - py)) * 6
        # 靠近小怪扣分
        for mx, my in mob_cells:
            if abs(mx - px) + abs(my - py) <= 1:
                s -= 40
        # 靠近目标加分
        if target:
            s -= (abs(target[0] - px) + abs(target[1] - py)) * 3
        # 直行略微优先，走位更自然
        if d == cur:
            s += 2
        return s

    return max(options, key=score)


def run_once(max_seconds=300):
    game = Game()
    game.register_scene("battle", BattleScene)
    game.change_scene("battle")
    scene = game.current_scene

    events = []
    orig = type(scene.snake).take_damage
    hurt = {"wall": 0, "mob": 0, "self": 0}

    dt = 1 / 60
    steps = int(max_seconds / dt)
    decide_every = 3
    for i in range(steps):
        if i % decide_every == 0:
            scene.snake.set_direction(choose_direction(scene))
        hp_before = scene.snake.hp
        scene.update(dt)

        if scene.snake.hp < hp_before:
            # 粗略归因
            head = scene.snake.cells[0]
            if any((round(m.cell[0]), round(m.cell[1])) == head for m in scene.mobs):
                hurt["mob"] += 1
            elif scene.snake.is_self_hit():
                hurt["self"] += 1
            else:
                hurt["wall"] += 1

        if not scene.snake.alive:
            break

    return {
        "time": scene.elapsed,
        "level": scene.snake.level,
        "attack": scene.snake.attack,
        "score": scene.score,
        "stardust": scene.stardust,
        "kills": scene.kills,
        "hp": scene.snake.hp,
        "alive": scene.snake.alive,
        "mobs": len(scene.mobs),
        "spawn": scene._spawn_interval(),
        "hurt": hurt,
    }


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print("=" * 60)
    print(" 自动试玩 · 平衡性检查")
    print("=" * 60)
    rows = []
    for i in range(runs):
        r = run_once()
        rows.append(r)
        print(f"第{i + 1}局  存活 {r['time']:5.1f}s  等级 {r['level']:2d}  "
              f"击杀 {r['kills']:2d}  得分 {r['score']:5d}  星尘 {r['stardust']:2d}  "
              f"结局 {'存活' if r['alive'] else '阵亡'}")

    if rows:
        avg_t = sum(r["time"] for r in rows) / len(rows)
        avg_l = sum(r["level"] for r in rows) / len(rows)
        avg_s = sum(r["score"] for r in rows) / len(rows)
        print("-" * 60)
        print(f"平均存活 {avg_t:.1f}s   平均等级 {avg_l:.1f}   平均得分 {avg_s:.0f}")
        print("\n目标参考：单局 90~240 秒，等级 6~15，得分 1500~8000")
        if avg_t < 40:
            print(">> 偏难：生存时间过短，建议调低 MOB_HP / 放慢刷怪")
        elif avg_t > 280:
            print(">> 偏易：几乎打不死，建议提高 MOB_TOUCH_DAMAGE 或加快刷怪")
        else:
            print(">> 节奏在合理区间")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
