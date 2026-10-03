# -*- coding: utf-8 -*-
"""
tools/playsim.py —— 自动试玩，用来验证平衡（自由移动版）

模拟一个「会走位会开盾」的玩家：
  · 朝最近的道具移动去吃经验
  · 附近的怪做斥力避让，太贴脸就左键开护盾承伤
  · 技能一好就放（1-5）
  · 升级弹出的三选一自动挑（直接选第一张通用属性卡）

跑完输出多局统计，用来判断难度曲线是否合理，而不是靠手动试玩拍脑袋。
存档写入被重定向到临时目录，绝不污染 saves/save_data.json。
"""

import math
import os
import shutil
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import settings as S  # noqa: E402
import core.save_manager as _sm  # noqa: E402
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
    """三选一：卡池已只剩通用属性卡，直接选第一张。"""
    if scene.card_overlay:
        scene._choose_card(0)


def cast_ready_skills(scene):
    """多主动：遍历 1-5 键的全部主动，冷却好了就放（模拟连招）。"""
    cdr = scene.stats["cdr"]
    for a in scene.skills.actives:
        sid = a.get("id")
        key = a.get("key", 1)
        if sid and scene.skills.ready(sid, cdr):
            scene.cast_skill(key)


def run_once(mode="endless", level=1, max_seconds=300, char_id="sakura"):
    # 存档隔离：把 SAVES_DIR 指向临时目录，绝不污染真实 saves/
    tmp = tempfile.mkdtemp(prefix="sg_playsim_")
    _sm.SAVES_DIR = tmp
    game = Game()
    game.register_scene("battle", BattleScene)
    game.save_manager.data["selected_character"] = char_id
    game.save_manager.data["selected_scene"] = "campus_garden"
    game.save_manager.data["tutorial_done"] = True   # 试玩不弹新手指引
    if mode == "story":
        game.pending_run = {"mode": "story", "level": level}
    else:
        game.pending_run = {"mode": "endless", "scene": "campus_garden"}
    game.change_scene("battle")
    scene = game.current_scene

    fake = FakeKeys()
    real_get_pressed = pygame.key.get_pressed
    pygame.key.get_pressed = lambda: fake

    dt = 1 / 60
    steps = int(max_seconds / dt)
    shield_cd = 0.0
    hurt_from = 0
    try:
        for i in range(steps):
            if scene.card_overlay:
                auto_pick_card(scene)
                continue
            if scene.finished:
                break

            fake.pressed = decide_movement(scene)

            # 太贴脸且护盾就绪就开盾承伤
            shield_cd -= dt
            if nearest_mob_dist(scene) < 70 * scene.S and scene.snake.shield_cd <= 0 \
                    and shield_cd <= 0:
                scene.try_shield((scene.W // 2, scene.H // 2))
                shield_cd = 0.4

            cast_ready_skills(scene)

            hp_before = scene.snake.hp
            scene.update(dt)
            if scene.snake.hp < hp_before:
                hurt_from += 1
            if not scene.snake.alive:
                break
    finally:
        pygame.key.get_pressed = real_get_pressed
        shutil.rmtree(tmp, ignore_errors=True)

    return {
        "mode": mode,
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
    args = sys.argv[1:]
    runs = int(args[0]) if args else 3
    mode = args[1] if len(args) > 1 else "mixed"
    print("=" * 64)
    print(" 自动试玩 · 平衡性检查（专属技能包 + 剧情/无尽）")
    print("=" * 64)
    rows = []
    chars = ["sakura", "lamia_mint", "lamia_tide", "lamia_flare",
             "lamia_stella", "lamia_luna"]
    for i in range(runs):
        if mode == "mixed":
            m = "story" if i == 0 else "endless"
        else:
            m = mode
        cid = chars[i % len(chars)]
        cap = 960 if m == "story" else 300
        r = run_once(mode=m, level=1, max_seconds=cap, char_id=cid)
        r["char"] = cid
        rows.append(r)
        end = "通关" if r["victory"] else ("存活" if r["alive"] else "阵亡")
        tag = "剧情" if r["mode"] == "story" else "无尽"
        print(f"第{i + 1}局[{tag}·{cid}]  存活 {r['time']:5.1f}s  等级 {r['level']:2d}  "
              f"击杀 {r['kills']:3d}  得分 {r['score']:6d}  "
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
        print(">> 验证目标：剧情/无尽两种模式均无异常报错，能正常推进与结算")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
