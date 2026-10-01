# -*- coding: utf-8 -*-
"""
tools/screenshot.py —— 无头截图

不开真实窗口，直接把每个场景渲染到离屏画布并存成 PNG。
这样我在没显示器/不方便弹窗的环境里也能检查画面。

用法：python tools/screenshot.py [场景名 ...]
不带参数就截全部场景。
"""

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")     # 无头模式
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

OUT_DIR = os.path.join(BASE, "tools", "_shots")

SCENES = [
    ("battle", "战斗"),
    ("main_menu", "主菜单"),
    ("character_select", "角色选择"),
    ("character_detail", "角色详情"),
    ("scene_select", "场景选择"),
    ("gacha", "抽卡"),
    ("display_settings", "显示设置"),
]


def main():
    names = sys.argv[1:]
    os.makedirs(OUT_DIR, exist_ok=True)

    from core.game import Game
    from scenes.main_menu import MainMenuScene
    from scenes.character_select import CharacterSelectScene
    from scenes.character_detail import CharacterDetailScene
    from scenes.scene_select import SceneSelectScene
    from scenes.battle import BattleScene
    from scenes.gacha import GachaScene
    from scenes.display_settings import DisplaySettingsScene

    game = Game()
    game.register_scene("main_menu", MainMenuScene)
    game.register_scene("character_select", CharacterSelectScene)
    game.register_scene("character_detail", CharacterDetailScene)
    game.register_scene("scene_select", SceneSelectScene)
    game.register_scene("battle", BattleScene)
    game.register_scene("gacha", GachaScene)
    game.register_scene("display_settings", DisplaySettingsScene)

    targets = [(n, t) for n, t in SCENES if not names or n in names]

    # 给抽卡一点初始星尘，方便看效果
    game.save_manager.data["currency"] = 1200
    game.save_manager.data.setdefault("owned_characters", [])
    if "sakura" not in game.save_manager.data["owned_characters"]:
        game.save_manager.data["owned_characters"].append("sakura")
    # 详情页需要一个待展示角色
    game.pending_char_id = "sakura"

    for name, label in targets:
        game.change_scene(name)
        scene = game.current_scene
        scene.update(1 / 60)

        # 战斗场景多跑一会儿，让蛇和怪都动起来
        if name == "battle":
            for _ in range(180):
                scene.update(1 / 60)
        # 抽卡场景让它真的抽一次，看结果页
        if name == "gacha":
            scene._pull(10)
            for _ in range(20):
                scene.update(1 / 60)

        scene.draw()
        out = os.path.join(OUT_DIR, f"{name}.png")
        pygame.image.save(game.render_surface, out)
        print(f"[截图] {label:6s} -> {out}")

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
