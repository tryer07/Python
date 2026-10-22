# -*- coding: utf-8 -*-
"""植物大战僵尸·改版 —— 启动入口
运行: python main.py
"""
from pvz.core.game import Game
from pvz.scenes.loading_scene import LoadingScene


def main():
    game = Game()
    game.change_scene(LoadingScene(game))
    game.run()


if __name__ == "__main__":
    main()
