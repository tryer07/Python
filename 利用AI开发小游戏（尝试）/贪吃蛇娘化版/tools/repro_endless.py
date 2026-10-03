# -*- coding: utf-8 -*-
"""
tools/repro_endless.py —— 复现「点无尽闪退」

无头（dummy 驱动）走真实转场链路：
    level_select -> scene_select -> (选每张图) -> battle(endless) 的 enter/update/draw。
playsim 只 update 不 draw、且无尽只测 campus_garden；screenshot 只测 campus/neon。
这里对全部 4 张图都跑 update+draw，任何异常都打完整 traceback。
"""

import os
import sys
import tempfile
import traceback

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import core.save_manager as _sm  # noqa: E402
_sm.SAVES_DIR = tempfile.mkdtemp(prefix="sg_repro_")

from core.game import Game  # noqa: E402
from scenes.main_menu import MainMenuScene  # noqa: E402
from scenes.character_select import CharacterSelectScene  # noqa: E402
from scenes.character_detail import CharacterDetailScene  # noqa: E402
from scenes.scene_select import SceneSelectScene  # noqa: E402
from scenes.level_select import LevelSelectScene  # noqa: E402
from scenes.battle import BattleScene  # noqa: E402
from scenes.gacha import GachaScene  # noqa: E402
from scenes.display_settings import DisplaySettingsScene  # noqa: E402
from scenes.save_manager_scene import SaveManagerScene  # noqa: E402

SCENE_IDS = ["campus_garden", "neon_night", "deep_sea", "sakura_realm"]
CHAR_IDS = ["sakura", "lamia_mint", "lamia_tide", "lamia_flare", "lamia_stella", "lamia_luna"]


def build_game():
    game = Game()
    game.register_scene("main_menu", MainMenuScene)
    game.register_scene("character_select", CharacterSelectScene)
    game.register_scene("character_detail", CharacterDetailScene)
    game.register_scene("scene_select", SceneSelectScene)
    game.register_scene("level_select", LevelSelectScene)
    game.register_scene("battle", BattleScene)
    game.register_scene("gacha", GachaScene)
    game.register_scene("display_settings", DisplaySettingsScene)
    game.register_scene("save_manager", SaveManagerScene)
    game.save_manager.data["tutorial_done"] = True
    return game


def pump(scene, frames=90):
    for _ in range(frames):
        scene.update(1 / 60)
        scene.draw()


def click(game, pos):
    """喂一组真实鼠标事件（移动->按下->松开），并按主循环那样推进一帧。
    完整复现「玩家点击」经 handle_events 触发 change_scene 的链路。"""
    evs = [
        pygame.event.Event(pygame.MOUSEMOTION, {"pos": pos, "rel": (0, 0), "buttons": (0, 0, 0)}),
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
        pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1}),
    ]
    game.current_scene.handle_events(evs)
    game.current_scene.update(1 / 60)
    game.current_scene.draw()


def main():
    failures = 0

    # 1) scene_select 本身能进能画
    game = build_game()
    try:
        game.change_scene("scene_select")
        pump(game.current_scene, 30)
        print("[OK] scene_select enter+draw")
    except Exception:
        failures += 1
        print("[FAIL] scene_select:\n" + traceback.format_exc())

    # 2) level_select 能进能画（无尽按钮所在页）
    try:
        game.change_scene("level_select")
        pump(game.current_scene, 30)
        print("[OK] level_select enter+draw")
    except Exception:
        failures += 1
        print("[FAIL] level_select:\n" + traceback.format_exc())

    # 3) 每张图 × 每个角色：endless battle 的 enter+update+draw
    for sid in SCENE_IDS:
        for cid in CHAR_IDS:
            g = build_game()
            g.save_manager.data["selected_character"] = cid
            g.save_manager.data["selected_scene"] = sid
            g.pending_run = {"mode": "endless", "scene": sid}
            try:
                g.change_scene("battle")
                pump(g.current_scene, 60)
                print(f"[OK] endless battle  scene={sid:14s} char={cid}")
            except Exception:
                failures += 1
                print(f"[FAIL] endless battle scene={sid} char={cid}:\n"
                      + traceback.format_exc())

    # 4) 真实点击链路：level_select 点「无尽模式」-> scene_select 点每张图 -> battle
    for i, sid in enumerate(SCENE_IDS):
        g = build_game()
        g.save_manager.data["selected_character"] = "sakura"
        try:
            g.change_scene("level_select")
            g.current_scene.update(1 / 60)
            g.current_scene.draw()
            # 点「无尽模式」按钮（Button：走 MOUSEBUTTONUP 触发 on_click）
            click(g, g.current_scene.endless_btn.rect.center)
            assert type(g.current_scene).__name__ == "SceneSelectScene", \
                f"点无尽后未进入 scene_select，而是 {type(g.current_scene).__name__}"
            # 点第 i 张场景卡（scene_select：MOUSEBUTTONDOWN 直接开战）
            cards = g.current_scene._cards()
            _, rect, sc = cards[i % len(cards)]
            click(g, rect.center)
            assert type(g.current_scene).__name__ == "BattleScene", \
                f"选图后未进入 battle，而是 {type(g.current_scene).__name__}"
            pump(g.current_scene, 60)
            print(f"[OK] 真实点击链路 -> endless {sc['id']} "
                  f"(mode={g.current_scene.mode}, bg={g.current_scene.scene_bg})")
        except Exception:
            failures += 1
            print(f"[FAIL] 真实点击链路 scene#{i}:\n" + traceback.format_exc())

    pygame.quit()
    print("-" * 60)
    print(f"复现结束：{failures} 处失败" if failures else "复现结束：全部通过，未复现闪退")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
