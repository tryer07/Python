# -*- coding: utf-8 -*-
"""离屏渲染三个场景并截图，用于快速自检（不弹窗）
运行: python tools/screenshot.py
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402
from pvz import settings  # noqa: E402
from pvz.core.game import Game  # noqa: E402
from pvz.scenes.loading_scene import LoadingScene  # noqa: E402
from pvz.scenes.main_menu_scene import MainMenuScene  # noqa: E402
from pvz.scenes.level_select_scene import LevelSelectScene  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")


def shoot(game, scene, name, frames=30, hover_pos=None):
    game.scene = scene
    scene.on_enter()
    if hover_pos:  # 模拟鼠标悬停，检查按钮高亮
        ev = pygame.event.Event(pygame.MOUSEMOTION, {"pos": hover_pos, "rel": (0, 0), "buttons": (0, 0, 0)})
        scene.handle_event(ev)
    for _ in range(frames):
        scene.update(1 / 60)
        scene.draw(game.screen)
    path = os.path.join(OUT_DIR, name)
    pygame.image.save(game.screen, path)
    print("saved:", path)
    scene.on_exit()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    game = Game()
    shoot(game, LoadingScene(game), "01_loading.png", frames=90)
    # 加载页跑到 100% 后应能自动切主菜单（直接截主菜单即可）
    shoot(game, MainMenuScene(game), "02_main_menu.png", hover_pos=(settings.SCREEN_W // 2 - 230, settings.SCREEN_H - 95))
    shoot(game, LevelSelectScene(game), "03_level_select.png")

    # 验证加载页自动切换逻辑
    loading = LoadingScene(game)
    game.scene = loading
    loading.on_enter()
    for _ in range(int((LoadingScene.DURATION + 0.6) * 60)):
        loading.update(1 / 60)
        if not isinstance(game.scene, LoadingScene):
            break
        loading.draw(game.screen)
    assert isinstance(game.scene, MainMenuScene), "加载页未能自动切换到主菜单！"
    print("场景自动切换 OK: Loading -> MainMenu")
    pygame.quit()


if __name__ == "__main__":
    main()
