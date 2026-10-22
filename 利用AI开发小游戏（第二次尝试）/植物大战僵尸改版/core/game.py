# -*- coding: utf-8 -*-
"""Game 主控制器：单一主循环 + 场景切换（状态机模式，禁止递归开新循环）"""
import pygame

import settings
from core.scene import Scene


class Game:
    def __init__(self):
        pygame.init()
        # 强制英文输入法环境下的事件正常派发（对鼠标为主的本项目影响小，留作保险）
        self.screen = pygame.display.set_mode((settings.SCREEN_W, settings.SCREEN_H))
        pygame.display.set_caption(settings.GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.scene: Scene | None = None

    def change_scene(self, scene: Scene):
        """切换场景：先通知旧场景退出，再进入新场景"""
        if self.scene is not None:
            self.scene.on_exit()
        self.scene = scene
        scene.on_enter()

    def run(self):
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif self.scene is not None:
                    self.scene.handle_event(event)
            if self.scene is not None:
                self.scene.update(dt)
                self.scene.draw(self.screen)
            pygame.display.flip()
        pygame.quit()
