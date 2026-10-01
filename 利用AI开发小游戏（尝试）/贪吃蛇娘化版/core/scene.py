from abc import ABC, abstractmethod
import pygame


class Scene(ABC):
    """所有场景的基类"""

    def __init__(self, game):
        self.game = game
        self.screen = game.render_surface

    @property
    def W(self):
        """当前渲染宽度（像素）"""
        return self.game.window_width

    @property
    def H(self):
        """当前渲染高度（像素）"""
        return self.game.window_height

    @property
    def S(self):
        """缩放因子（1.0 = 1080p 基准）"""
        return self.game.scale

    def s(self, value):
        """将设计尺寸按缩放因子放大（用于字体、按钮、间距等）"""
        return int(value * self.S)

    @abstractmethod
    def enter(self):
        pass

    @abstractmethod
    def exit(self):
        pass

    @abstractmethod
    def handle_events(self, events):
        pass

    @abstractmethod
    def update(self, dt):
        pass

    @abstractmethod
    def draw(self):
        pass