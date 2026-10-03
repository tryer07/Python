import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.game import Game
from scenes.main_menu import MainMenuScene
from scenes.character_select import CharacterSelectScene
from scenes.character_detail import CharacterDetailScene
from scenes.scene_select import SceneSelectScene
from scenes.level_select import LevelSelectScene
from scenes.battle import BattleScene
from scenes.gacha import GachaScene
from scenes.display_settings import DisplaySettingsScene
from scenes.control_settings import ControlSettingsScene
from scenes.save_manager_scene import SaveManagerScene


def main():
    # 崩溃兜底：windowed exe 下任何未捕获异常都写 crash.log + 弹窗，绝不静默闪退。
    from core.crash import install_excepthook, report_crash
    install_excepthook()
    try:
        game = Game()

        game.register_scene("main_menu", MainMenuScene)
        game.register_scene("character_select", CharacterSelectScene)
        game.register_scene("character_detail", CharacterDetailScene)
        game.register_scene("scene_select", SceneSelectScene)
        game.register_scene("level_select", LevelSelectScene)
        game.register_scene("battle", BattleScene)
        game.register_scene("gacha", GachaScene)
        game.register_scene("display_settings", DisplaySettingsScene)
        game.register_scene("control_settings", ControlSettingsScene)
        game.register_scene("save_manager", SaveManagerScene)

        game.change_scene("main_menu")
        game.run()
    except SystemExit:
        raise                      # 正常退出（game.quit() 调 sys.exit），不当崩溃
    except BaseException as e:     # 启动/主循环外的任何异常都记一笔
        report_crash(e, context="startup/main")
        sys.exit(1)                # 用 SystemExit 退出，避免再触发 excepthook 重复弹窗


if __name__ == "__main__":
    main()