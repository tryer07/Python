import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.game import Game
from scenes.main_menu import MainMenuScene
from scenes.character_select import CharacterSelectScene
from scenes.scene_select import SceneSelectScene
from scenes.battle import BattleScene
from scenes.gacha import GachaScene
from scenes.display_settings import DisplaySettingsScene


def main():
    game = Game()

    game.register_scene("main_menu", MainMenuScene)
    game.register_scene("character_select", CharacterSelectScene)
    game.register_scene("scene_select", SceneSelectScene)
    game.register_scene("battle", BattleScene)
    game.register_scene("gacha", GachaScene)
    game.register_scene("display_settings", DisplaySettingsScene)

    game.change_scene("main_menu")
    game.run()


if __name__ == "__main__":
    main()