# -*- coding: utf-8 -*-
"""一次性探针：验证星璃远程三段普攻（跑完即删）。
起 lamia_stella 无头对局，逐帧统计各段弹丸的 count / pierce / star_trace，
核对设计（段1单发无穿透 / 段2双发 / 段3五连穿透+微星痕），并确认无报错。
"""
import os
import sys
import tempfile
import shutil

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import core.save_manager as _sm  # noqa: E402
from core.game import Game  # noqa: E402
from scenes.battle import BattleScene  # noqa: E402

sys.path.insert(0, os.path.join(BASE, "tools"))
from playsim import FakeKeys, decide_movement, auto_pick_card, cast_ready_skills  # noqa: E402

CHAR = "lamia_stella"


def main():
    tmp = tempfile.mkdtemp(prefix="sg_probe_stella_")
    _sm.SAVES_DIR = tmp
    game = Game()
    game.register_scene("battle", BattleScene)
    smd = game.save_manager.data
    smd["selected_character"] = CHAR
    smd["owned_characters"] = [CHAR]
    smd["selected_scene"] = "campus_garden"
    smd["tutorial_done"] = True
    game.pending_run = {"mode": "endless", "scene": "campus_garden", "char_id": CHAR}
    game.change_scene("battle")
    scene = game.current_scene

    print("char_loaded =", scene.party[0]["char_id"] if scene.party else "?")
    print("ranged_cfg  =", "有" if scene.ranged_cfg else "无（回退单弹）")
    if scene.ranged_cfg:
        cfg = scene.ranged_cfg
        print("  name/range/radius =", cfg["name"], cfg["range"], cfg["bullet_radius"])
        for i, st in enumerate(cfg["stages"], 1):
            print(f"  段{i}: count={int(st['count'])} spread={st['spread_deg']:.0f} "
                  f"mult={st['mult']:.2f} pierce={int(st['pierce'])} "
                  f"hit_trace={st['hit_trace']:.1f} spin={st['spin']:.0f}")

    fake = FakeKeys()
    real = pygame.key.get_pressed
    pygame.key.get_pressed = lambda: fake
    dt = 1 / 60
    seen_stages = {}   # stage -> (count, pierce, star_trace) 首次观测
    starfall_seen = 0
    try:
        for _ in range(int(120 / dt)):
            if scene.card_overlay:
                auto_pick_card(scene)
                continue
            if scene.finished or not scene.snake.alive:
                break
            fake.pressed = decide_movement(scene)
            cast_ready_skills(scene)
            before = len(scene.bullets)
            cb_stage = scene.atk_combo["stage"] if scene.atk_combo else None
            scene.update(dt)
            # 开火帧：本帧新增弹丸归属当前段
            if len(scene.bullets) > before and cb_stage is not None:
                newb = scene.bullets[before:]
                if cb_stage not in seen_stages:
                    b0 = newb[0]
                    seen_stages[cb_stage] = (len(newb), int(b0.pierce), bool(b0.star_trace))
            for e in scene.effects:
                if e.get("type") == "starfall" and abs(e.get("max_life", 0) - 0.8) < 1e-6:
                    starfall_seen += 1
    finally:
        pygame.key.get_pressed = real
        shutil.rmtree(tmp, ignore_errors=True)

    print("观测到的段(发射数/穿透/微星痕) =", dict(sorted(seen_stages.items())))
    print("0.8s 微星痕特效帧计数 =", starfall_seen)
    print("击杀 =", scene.kills, " 存活 =", scene.snake.alive, " 得分 =", scene.score)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
