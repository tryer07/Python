# -*- coding: utf-8 -*-
"""
tools/screenshot.py —— 无头截图

不开真实窗口，直接把每个场景渲染到离屏画布并存成 PNG。
这样我在没显示器/不方便弹窗的环境里也能检查画面。

用法：python tools/screenshot.py [场景名 ...]
不带参数就截全部场景。
"""

import os
import shutil
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")     # 无头模式
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

# 存档隔离：把 SAVES_DIR 指向临时目录，截图绝不污染真实 saves/
import core.save_manager as _sm  # noqa: E402
_TMP_SAVES = tempfile.mkdtemp(prefix="sg_shots_")
_sm.SAVES_DIR = _TMP_SAVES

OUT_DIR = os.path.join(BASE, "tools", "_shots")

# (输出名, 注册场景名, 标签)
SCENES = [
    ("battle_story", "battle", "战斗·剧情"),
    ("battle_endless", "battle", "战斗·无尽"),
    ("main_menu", "main_menu", "主菜单"),
    ("level_select", "level_select", "关卡选择"),
    ("save_manager", "save_manager", "存档管理"),
    ("character_select", "character_select", "角色选择"),
    ("character_detail", "character_detail", "角色详情"),
    ("scene_select", "scene_select", "场景选择"),
    ("gacha", "gacha", "抽卡"),
    ("display_settings", "display_settings", "显示设置"),
]

# 战斗截图需要的模式（写入 game.pending_run）
PENDING_RUN = {
    "battle_story": {"mode": "story", "level": 1},
    "battle_endless": {"mode": "endless", "scene": "neon_night"},
}


def main():
    names = sys.argv[1:]
    os.makedirs(OUT_DIR, exist_ok=True)

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
    game.register_scene("main_menu", MainMenuScene)
    game.register_scene("character_select", CharacterSelectScene)
    game.register_scene("character_detail", CharacterDetailScene)
    game.register_scene("scene_select", SceneSelectScene)
    game.register_scene("level_select", LevelSelectScene)
    game.register_scene("battle", BattleScene)
    game.register_scene("gacha", GachaScene)
    game.register_scene("display_settings", DisplaySettingsScene)
    game.register_scene("save_manager", SaveManagerScene)

    targets = [t for t in SCENES if not names or t[0] in names or t[1] in names]

    # 给抽卡一点初始星尘，方便看效果
    game.save_manager.data["currency"] = 1200
    game.save_manager.data.setdefault("owned_characters", [])
    if "sakura" not in game.save_manager.data["owned_characters"]:
        game.save_manager.data["owned_characters"].append("sakura")
    # 多解锁几关，让关卡选择页能展示 可挑战/已通关/锁定 三种状态
    game.save_manager.data["story_unlocked"] = 3
    game.save_manager.data["story_cleared"] = [1]
    # 详情页需要一个待展示角色
    game.pending_char_id = "sakura"

    for out_name, scene_name, label in targets:
        game.pending_run = PENDING_RUN.get(out_name)
        game.change_scene(scene_name)
        scene = game.current_scene
        scene.update(1 / 60)

        # 战斗场景多跑一会儿，让蛇和怪都动起来（剧情局保留新手指引浮层）
        if scene_name == "battle":
            for _ in range(120):
                scene.update(1 / 60)
        # 抽卡场景让它真的抽一次，看结果页
        if scene_name == "gacha":
            scene._pull(10)
            for _ in range(20):
                scene.update(1 / 60)

        scene.draw()
        out = os.path.join(OUT_DIR, f"{out_name}.png")
        pygame.image.save(game.render_surface, out)
        print(f"[截图] {label:10s} -> {out}")

    pygame.quit()
    shutil.rmtree(_TMP_SAVES, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
