# -*- coding: utf-8 -*-
"""临时：以 1920x1080 渲染指定场景，便于目检文字遮挡。用完即删。"""
import os
import shutil
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import core.save_manager as _sm  # noqa: E402

_TMP = tempfile.mkdtemp(prefix="sg_hi_")
_sm.SAVES_DIR = _TMP

OUT = os.path.join(BASE, "tools", "_shots", "_hi")


def main():
    names = sys.argv[1:] or ["main_menu"]
    os.makedirs(OUT, exist_ok=True)
    from core.game import Game
    from scenes.main_menu import MainMenuScene
    from scenes.character_select import CharacterSelectScene
    from scenes.character_detail import CharacterDetailScene
    from scenes.scene_select import SceneSelectScene
    from scenes.level_select import LevelSelectScene
    from scenes.battle import BattleScene
    from scenes.gacha import GachaScene
    from scenes.display_settings import DisplaySettingsScene
    from scenes.save_manager_scene import SaveManagerScene

    game = Game()
    for n, c in [("main_menu", MainMenuScene), ("character_select", CharacterSelectScene),
                 ("character_detail", CharacterDetailScene), ("scene_select", SceneSelectScene),
                 ("level_select", LevelSelectScene), ("battle", BattleScene),
                 ("gacha", GachaScene), ("display_settings", DisplaySettingsScene),
                 ("save_manager", SaveManagerScene)]:
        game.register_scene(n, c)

    import settings as _st
    game.window_width, game.window_height = 1920, 1080
    game.render_surface = pygame.Surface((1920, 1080))
    _st.RENDER_WIDTH, _st.RENDER_HEIGHT = 1920, 1080
    _st.CELL_SIZE = int(_st.CELL_SIZE_BASE * game.scale)
    print("window:", game.window_width, game.window_height, "scale:", game.scale)

    game.save_manager.data["currency"] = 1200
    game.save_manager.data.setdefault("owned_characters", [])
    if "sakura" not in game.save_manager.data["owned_characters"]:
        game.save_manager.data["owned_characters"].append("sakura")
    game.save_manager.data["story_unlocked"] = 3
    game.save_manager.data["story_cleared"] = [1]
    game.pending_char_id = "sakura"
    # 多造几个存档槽，看列表挤压
    game.save_manager.create_slot("樱花之旅", activate=False)
    game.save_manager.create_slot("霓虹夜行", activate=False)

    runs = {
        "battle": {"mode": "story", "level": 1},
    }
    for name in names:
        game.pending_run = runs.get(name)
        game.change_scene(name)
        sc = game.current_scene
        sc.update(1 / 60)
        if name == "battle":
            for _ in range(120):
                sc.update(1 / 60)
        if name == "gacha":
            sc._pull(10)
            for _ in range(20):
                sc.update(1 / 60)
        sc.draw()
        out = os.path.join(OUT, f"{name}.png")
        pygame.image.save(game.render_surface, out)
        print("[hi]", name, "->", out)
    pygame.quit()
    shutil.rmtree(_TMP, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
