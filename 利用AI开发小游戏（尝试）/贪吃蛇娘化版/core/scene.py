from abc import ABC, abstractmethod
import pygame


class Scene(ABC):
    """所有场景的基类"""

    def __init__(self, game):
        self.game = game

    @property
    def screen(self):
        """当前渲染表面。动态跟随 game.render_surface，
        避免全屏 / 缩放 / 手动改变窗口大小后，场景仍画在旧表面上导致黑屏黑边。"""
        return self.game.render_surface

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

    def wants_movement_keys(self):
        """当前场景是否正在占用方向键（如战斗进行中的蛇移动）。

        返回 True 时，全局音量热键（↑/↓/←/→）会主动让路，不拦截方向键；
        默认 False，即菜单/设置/战斗暂停等场景都可随时用方向键调音量。"""
        return False

    def on_resize(self):
        """窗口尺寸变化时的默认处理：重新进入场景，按新缩放重建字体与按钮布局。
        菜单类场景无状态，直接重建即可；战斗等有进度的场景应重写此方法，
        只重算布局而不重置状态。"""
        self.enter()

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