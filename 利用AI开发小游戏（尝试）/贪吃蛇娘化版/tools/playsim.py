# -*- coding: utf-8 -*-
"""
tools/playsim.py —— 自动试玩，用来验证平衡（自由移动版）

模拟一个「会走位会闪避」的玩家：
  · 朝最近的道具移动去吃经验
  · 附近的怪做斥力避让，太贴脸就左键闪避拉开
  · 技能一好就放（1-6）
  · 升级弹出的三选一自动挑（优先补满 6 个技能，再叠被动）

跑完输出多局统计，用来判断难度曲线是否合理，而不是靠手动试玩拍脑袋。
存档写入被重定向到临时目录，绝不污染 saves/save_data.json。
"""

import math
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


class FakeKeys:
    """顶替 pygame.key.get_pressed()，让 battle 的 WASD 轮询读到 AI 的意图。"""

    def __init__(self):
        self.pressed = set()

    def __getitem__(self, k):
        return 1 if k in self.pressed else 0


def decide_movement(scene):
    """返回一个按键集合（模拟 WASD），朝道具走 + 躲怪 + 靠边回中。"""
    sn = scene.snake
    px, py = sn.pos
    vx, vy = 0.0, 0.0

    # 目标：最近的道具
    best, target = 1e18, None
    for d in scene.drops:
        dist = math.hypot(d.pos[0] - px, d.pos[1] - py)
        if dist < best:
            best, target = dist, d
    if target is not None:
        dx, dy = target.pos[0] - px, target.pos[1] - py
        d = math.hypot(dx, dy) or 1.0
        vx += dx / d
        vy += dy / d

    # 斥力：附近的怪
    for m in scene.mobs:
        dx, dy = px - m.pos[0], py - m.pos[1]
        d = math.hypot(dx, dy)
        flee = 180.0 * scene.S
        if 0 < d < flee:
            w = (flee - d) / flee * 2.4
            vx += dx / d * w
            vy += dy / d * w

    # Boss 也躲（弹幕另说，至少别贴脸）
    if scene.boss is not None and scene.boss.alive:
        bx, by = scene.boss.pos
        dx, dy = px - bx, py - by
        d = math.hypot(dx, dy)
        keep = scene.boss.radius_px + 160 * scene.S
        if 0 < d < keep:
            vx += dx / d * 1.5
            vy += dy / d * 1.5

    # 靠世界边缘就往中心拉
    margin = 120 * scene.S
    if px < margin:
        vx += 1
    if px > scene.world_w - margin:
        vx -= 1
    if py < margin:
        vy += 1
    if py > scene.world_h - margin:
        vy -= 1

    keys = set()
    if vx > 0.25:
        keys.add(pygame.K_d)
    elif vx < -0.25:
        keys.add(pygame.K_a)
    if vy > 0.25:
        keys.add(pygame.K_s)
    elif vy < -0.25:
        keys.add(pygame.K_w)
    return keys


def nearest_mob_dist(scene):
    px, py = scene.snake.pos
    best = 1e18
    for m in scene.mobs:
        best = min(best, math.hypot(m.pos[0] - px, m.pos[1] - py))
    return best


def auto_pick_card(scene):
    """三选一：优先补满 6 个技能，技能齐了再叠被动。"""
    overlay = scene.card_overlay
    if not overlay:
        return
    skill_idx = next((i for i, c in enumerate(overlay)
                      if c.get("type") == "skill"
                      and not scene.skills.has(c.get("ref"))), None)
    if skill_idx is None and scene.skills.count >= 6:
        skill_idx = next((i for i, c in enumerate(overlay)
                          if c.get("type") == "skill"), None)
    idx = skill_idx if skill_idx is not None else 0
    scene._choose_card(idx)


def cast_ready_skills(scene):
    cdr = scene.stats["cdr"]
    for key in range(1, 7):
        sid = scene.skills.sid_at_key(key)
        if sid and scene.skills.ready(sid, cdr):
            scene.cast_skill(key)


def run_once(max_seconds=300):
    game = Game()
    game.register_scene("battle", BattleScene)
    tmp = tempfile.mkdtemp(prefix="sg_playsim_")
    game.save_manager.save_path = os.path.join(tmp, "save_data.json")
    game.save_manager.data["selected_character"] = "sakura"
    game.save_manager.data["selected_scene"] = "campus_garden"
    game.change_scene("battle")
    scene = game.current_scene

    fake = FakeKeys()
    real_get_pressed = pygame.key.get_pressed
    pygame.key.get_pressed = lambda: fake

    dt = 1 / 60
    steps = int(max_seconds / dt)
    dodge_cd = 0.0
    hurt_from = 0
    try:
        for i in range(steps):
            if scene.card_overlay:
                auto_pick_card(scene)
                continue
            if scene.finished:
                break

            fake.pressed = decide_movement(scene)

            # 太贴脸且有闪避就拉开
            dodge_cd -= dt
            if nearest_mob_dist(scene) < 70 * scene.S and scene.snake.dodge_cd <= 0 \
                    and dodge_cd <= 0:
                scene.try_dodge((scene.W // 2, scene.H // 2))
                dodge_cd = 0.4

            cast_ready_skills(scene)

            hp_before = scene.snake.hp
            scene.update(dt)
            if scene.snake.hp < hp_before:
                hurt_from += 1
            if not scene.snake.alive:
                break
    finally:
        pygame.key.get_pressed = real_get_pressed

    return {
        "time": scene.elapsed,
        "level": scene.snake.level,
        "attack": scene.player_damage,
        "score": scene.score,
        "stardust": scene.stardust,
        "kills": scene.kills,
        "hp": scene.snake.hp,
        "alive": scene.snake.alive,
        "victory": scene.victory,
        "skills": scene.skills.count,
        "mobs": len(scene.mobs),
        "hurt": hurt_from,
    }


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print("=" * 64)
    print(" 自动试玩 · 平衡性检查（自由移动版）")
    print("=" * 64)
    rows = []
    for i in range(runs):
        r = run_once()
        rows.append(r)
        end = "通关" if r["victory"] else ("存活" if r["alive"] else "阵亡")
        print(f"第{i + 1}局  存活 {r['time']:5.1f}s  等级 {r['level']:2d}  "
              f"技能 {r['skills']}/6  击杀 {r['kills']:3d}  得分 {r['score']:6d}  "
              f"受伤 {r['hurt']:2d}  结局 {end}")

    if rows:
        n = len(rows)
        avg_t = sum(r["time"] for r in rows) / n
        avg_l = sum(r["level"] for r in rows) / n
        avg_k = sum(r["kills"] for r in rows) / n
        wins = sum(1 for r in rows if r["victory"])
        print("-" * 64)
        print(f"平均存活 {avg_t:.1f}s   平均等级 {avg_l:.1f}   "
              f"平均击杀 {avg_k:.0f}   通关 {wins}/{n}")
        print("\n目标参考：能活到 Boss 触发（~60s）并有输赢悬念；"
              "会走位的玩家通关率不宜 0% 也不宜 100%")
        if avg_t < 40:
            print(">> 偏难：生存时间过短，建议调低 MOB_HP_GROWTH / 放慢刷怪 / 加闪避")
        elif wins == n and avg_t > 200:
            print(">> 偏易：稳定通关且耗时很长，建议上调怪物成长或 Boss 血量")
        else:
            print(">> 节奏在合理区间")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
