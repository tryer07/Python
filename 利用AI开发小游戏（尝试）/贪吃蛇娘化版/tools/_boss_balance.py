# -*- coding: utf-8 -*-
"""临时平衡探针：模拟一个会躲弹幕+撞 Boss 的玩家，测各 Boss 是否可击败且不过易。跑完即删。"""

import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import settings as S  # noqa: E402
from core.game import Game  # noqa: E402
from scenes.battle import BattleScene  # noqa: E402
from game_logic.boss import load_boss_cfg  # noqa: E402


def make_game(scene_id):
    g = Game()
    g.register_scene("battle", BattleScene)
    g.save_manager.data["selected_scene"] = scene_id
    g.save_manager.save_path = os.path.join(tempfile.gettempdir(), "_boss_bal_save.json")
    g.change_scene("battle")
    return g


def fight(scene_id, level=12, max_s=180.0):
    g = make_game(scene_id)
    sc = g.current_scene
    # 直接跳到 Boss 登场，并给玩家一个代表性成长状态
    sc.snake.level = level
    sc.snake.hp = S.HP_MAX
    sc.skills.sync_unlock(level)
    sc.skills.newly_unlocked.clear()
    trig = float((load_boss_cfg(scene_id) or {}).get("trigger", {}).get("value", 60))
    sc.elapsed = trig + 1.0
    spawn_at = sc.elapsed
    sc.update(1 / 60)          # 触发登场
    if sc.boss is None:
        return None

    dt = 1 / 60
    boss_hp0 = sc.boss.hp_max
    hurt = {"bullet": 0, "mob": 0, "boss_body": 0, "wall": 0, "self": 0, "other": 0}
    for _ in range(int(max_s / dt)):
        steer(sc)
        hp_before = sc.snake.hp
        sc.update(dt)
        if sc.snake.hp < hp_before:
            hurt[_attribute(sc)] += 1
        if sc.victory:
            return {"win": True, "t": sc.elapsed - spawn_at, "boss_hp_left": sc.boss.hp,
                    "player_hp": sc.snake.hp, "boss_hp0": boss_hp0, "hurt": hurt}
        if not sc.snake.alive:
            return {"win": False, "t": sc.elapsed - spawn_at,
                    "boss_hp_left": sc.boss.hp, "player_hp": 0, "boss_hp0": boss_hp0,
                    "hurt": hurt}
    return {"win": False, "t": max_s, "boss_hp_left": sc.boss.hp,
            "player_hp": sc.snake.hp, "boss_hp0": boss_hp0, "timeout": True,
            "hurt": hurt}


def _attribute(sc):
    """粗略归因一次掉血。"""
    import math
    sn = sc.snake
    px, py = sn.draw_pos
    head = sn.cells[0]
    if sn.is_self_hit():
        return "self"
    # 弹幕：附近是否有刚命中消失的弹幕（用蛇头周围有无弹幕近似）
    for p in sc.projectiles:
        if math.hypot(p.pos[0] - px, p.pos[1] - py) < sc.CELL * 1.2:
            return "bullet"
    for m in sc.mobs:
        if (round(m.cell[0]), round(m.cell[1])) == head:
            return "mob"
    if sc.boss is not None:
        bx, by = sc.boss.draw_pos
        if math.hypot(px - bx, py - by) < sc.boss.radius_px + sc.CELL:
            return "boss_body"
    # 贴墙（蛇头在边界）
    if head[0] in (0, S.GRID_COLS - 1) or head[1] in (0, S.GRID_ROWS - 1):
        return "wall"
    return "other"


def steer(sc):
    """朝 Boss 走以撞击输出，但优先避开多个提前量预测的弹幕危险格。"""
    sn = sc.snake
    cx, cy = round(sn.grid_pos[0]), round(sn.grid_pos[1])
    cur = sn.direction
    body = set(sn.cells[1:])
    bx, by = sc.boss.pos_cells

    # 预测弹幕在 0.2/0.45/0.7s 后的位置，标记危险格（含半径邻格）
    danger = {}
    cell = sc.CELL
    for p in sc.projectiles:
        for la, w in ((0.2, 3), (0.45, 2), (0.7, 1)):
            gx = int(round((p.pos[0] + p.vel[0] * la) / cell))
            gy = int(round((p.pos[1] + p.vel[1] * la) / cell))
            for ddx in (-1, 0, 1):
                for ddy in (-1, 0, 1):
                    k = (gx + ddx, gy + ddy)
                    danger[k] = max(danger.get(k, 0), w)

    # Boss 即将开火时，其周围（环形弹幕源）视为危险，促使玩家提前撤开
    boss_imminent = getattr(sc.boss, "attack_timer", 9) < 0.55
    if boss_imminent:
        bcx, bcy = int(round(bx)), int(round(by))
        for ddx in range(-3, 4):
            for ddy in range(-3, 4):
                if abs(ddx) + abs(ddy) <= 3:
                    k = (bcx + ddx, bcy + ddy)
                    danger[k] = max(danger.get(k, 0), 2)

    # 预警区（冲撞线 / 震击圈）极度危险，必须走开
    for tg in getattr(sc.boss, "telegraphs", []):
        if tg["type"] == "charge":
            (x0, y0), (x1, y1) = tg["from"], tg["to"]
            for i in range(41):
                gx = int(round((x0 + (x1 - x0) * i / 40) / cell))
                gy = int(round((y0 + (y1 - y0) * i / 40) / cell))
                for ddx in (-1, 0, 1):
                    for ddy in (-1, 0, 1):
                        danger[(gx + ddx, gy + ddy)] = max(danger.get((gx + ddx, gy + ddy), 0), 3)
        elif tg["type"] == "slam":
            sxp, syp = tg["pos"]
            gcx, gcy = int(round(sxp / cell)), int(round(syp / cell))
            R = int(tg["radius_px"] / cell) + 1
            for ddx in range(-R, R + 1):
                for ddy in range(-R, R + 1):
                    if ddx * ddx + ddy * ddy <= R * R:
                        danger[(gcx + ddx, gcy + ddy)] = max(danger.get((gcx + ddx, gcy + ddy), 0), 3)

    # 小怪所在格也危险
    for m in sc.mobs:
        mc = (round(m.cell[0]), round(m.cell[1]))
        danger[mc] = max(danger.get(mc, 0), 2)

    def ok(d):
        px, py = cx + d[0], cy + d[1]
        return (0 <= px < S.GRID_COLS and 0 <= py < S.GRID_ROWS and (px, py) not in body)

    opts = [d for d in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if d != (-cur[0], -cur[1]) and ok(d)]
    if not opts:
        return
    best, bs = cur, -1e9
    for d in opts:
        px, py = cx + d[0], cy + d[1]
        s = 0.0
        s -= (abs(bx - px) + abs(by - py)) * 3      # 靠近 Boss（撞击输出）
        s -= danger.get((px, py), 0) * 60            # 躲弹幕（权重高于追击）
        s -= max(0, 2 - min(px, py, S.GRID_COLS - 1 - px, S.GRID_ROWS - 1 - py)) * 5
        if d == cur:
            s += 2
        if s > bs:
            bs, best = s, d
    sn.set_direction(best)


def main():
    scenes = [("campus_garden", "樱之守护者"), ("neon_night", "霓虹夜主"),
              ("deep_sea", "深海遗主"), ("sakura_realm", "神域主宰")]
    print("=" * 64)
    for sid, name in scenes:
        runs = [fight(sid) for _ in range(4)]
        runs = [r for r in runs if r]
        wins = sum(1 for r in runs if r["win"])
        avg_t = sum(r["t"] for r in runs) / max(1, len(runs))
        avg_left = sum(r["boss_hp_left"] for r in runs) / max(1, len(runs))
        hp0 = runs[0]["boss_hp0"] if runs else 0
        agg = {}
        for r in runs:
            for k, v in r.get("hurt", {}).items():
                agg[k] = agg.get(k, 0) + v
        cause = " ".join(f"{k}{v}" for k, v in sorted(agg.items(), key=lambda kv: -kv[1]) if v)
        print(f"{name:8s}({sid:13s}) 胜 {wins}/{len(runs)}  "
              f"平均耗时 {avg_t:5.1f}s  平均残血 {avg_left:6.0f}/{hp0}  掉血来源[{cause}]")
    pygame.quit()
    print("=" * 64)


if __name__ == "__main__":
    main()
