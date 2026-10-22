# -*- coding: utf-8 -*-
"""场景基类：所有界面（加载页/主菜单/选关）都继承它"""
import pygame


class Scene:
    """单个界面场景。子类按需覆盖各方法。"""

    def __init__(self, game):
        self.game = game  # 持有 Game 实例，便于切换场景

    def on_enter(self):
        """进入场景时调用一次（初始化状态）"""

    def handle_event(self, event: pygame.event.Event):
        """处理输入事件"""

    def update(self, dt: float):
        """每帧逻辑更新，dt 为秒"""

    def draw(self, surface: pygame.Surface):
        """每帧绘制"""

    def on_exit(self):
        """离开场景时调用一次"""
