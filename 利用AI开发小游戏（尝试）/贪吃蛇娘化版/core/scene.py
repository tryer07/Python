from abc import ABC, abstractmethod
import pygame


class Scene(ABC):
    """所有场景的基类"""

    def __init__(self, game):
        self.game = game
        self.screen = game.render_surface

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