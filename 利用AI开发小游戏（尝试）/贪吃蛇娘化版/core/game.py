# -*- coding: utf-8 -*-
"""
core/game.py —— 游戏主类

负责：
  1. 创建窗口（支持 窗口 / 无边框 / 全屏，可动态切换）
  2. 以窗口原生分辨率渲染（无拉伸，不模糊）
  3. 提供 scale 缩放因子，让所有 UI 元素按比例放大
  4. 主循环与场景切换
"""

import ctypes
import sys

import pygame

import settings
from core.asset_manager import AssetManager
from core.save_manager import SaveManager
from settings import (
    CELL_SIZE_BASE, DESIGN_HEIGHT, DESIGN_WIDTH,
    DISPLAY_MODES, FPS, FULLSCREEN, GAME_TITLE,
    RESOLUTION_OPTIONS, WINDOW_SCALE,
)


class Game:
    """游戏主类：管理窗口、主循环、场景切换"""

    def __init__(self):
        pygame.init()

        # 显示设置：优先读存档
        self.save_manager = SaveManager()
        display = self.save_manager.get("display", {}) or {}
        self.display_mode = display.get("mode", "fullscreen" if FULLSCREEN else "windowed")
        self.display_resolution = tuple(display.get("resolution", [0, 0]))

        self.window_width = DESIGN_WIDTH
        self.window_height = DESIGN_HEIGHT
        self.display = None
        self._apply_display_settings()

        self.clock = pygame.time.Clock()
        self.assets = AssetManager()
        self.running = True
        self.current_scene = None
        self._scenes = {}

    # ==================== 窗口 / 显示设置 ====================
    @property
    def scale(self):
        """缩放因子：窗口宽度 / 设计基准宽度"""
        return self.window_width / DESIGN_WIDTH

    def _apply_display_settings(self):
        """根据 display_mode / display_resolution 创建或重建窗口"""
        info = pygame.display.Info()
        sw, sh = info.current_w, info.current_h

        if self.display_mode == "fullscreen":
            self.window_width, self.window_height = sw, sh
            flags = pygame.FULLSCREEN
        elif self.display_mode == "borderless":
            self.window_width, self.window_height = sw, sh
            flags = pygame.NOFRAME
        else:
            if self.display_resolution != (0, 0):
                tw, th = self.display_resolution
                self.window_width = min(tw, int(sw * 0.95))
                self.window_height = min(th, int(sh * 0.95))
            else:
                max_w = int(sw * WINDOW_SCALE)
                max_h = int(sh * WINDOW_SCALE)
                if max_w / max_h > 16 / 9:
                    self.window_height = max_h
                    self.window_width = int(max_h * 16 / 9)
                else:
                    self.window_width = max_w
                    self.window_height = int(max_w * 9 / 16)
            flags = pygame.RESIZABLE

        self.display = pygame.display.set_mode(
            (self.window_width, self.window_height), flags
        )
        # 渲染表面 = 窗口原生分辨率（1:1 像素映射，零模糊）
        self.render_surface = pygame.Surface((self.window_width, self.window_height))

        # 动态更新 settings 中的渲染分辨率和格子大小
        settings.RENDER_WIDTH = self.window_width
        settings.RENDER_HEIGHT = self.window_height
        settings.CELL_SIZE = int(CELL_SIZE_BASE * self.scale)

        pygame.display.set_caption(GAME_TITLE)
        self._disable_ime()

    def set_display(self, mode=None, resolution=None):
        """切换显示设置（显示设置场景调用），并写入存档"""
        if mode is not None and mode in DISPLAY_MODES:
            self.display_mode = mode
        if resolution is not None:
            self.display_resolution = tuple(resolution)

        self._apply_display_settings()
        self.save_manager.set("display", {
            "mode": self.display_mode,
            "resolution": list(self.display_resolution),
        })
        # 窗口大小变了，需要重新进入当前场景以刷新布局
        if self.current_scene:
            scene_name = None
            for name, cls in self._scenes.items():
                if isinstance(self.current_scene, cls):
                    scene_name = name
                    break
            if scene_name:
                self.change_scene(scene_name)

    def get_available_resolutions(self):
        """返回不超过屏幕尺寸的分辨率选项 [(w, h, 说明), ...]"""
        info = pygame.display.Info()
        sw, sh = info.current_w, info.current_h
        available = [(w, h, label) for w, h, label in RESOLUTION_OPTIONS
                     if w <= sw and h <= sh]
        if not available:
            available.append((sw, sh, "屏幕原生"))
        return available

    def toggle_fullscreen(self):
        """F11 快速全屏 / 窗口切换"""
        if self.display.get_flags() & pygame.FULLSCREEN:
            self.set_display(mode="windowed")
        else:
            self.set_display(mode="fullscreen")

    def _disable_ime(self):
        """禁用输入法，免得打字时弹出候选框挡住游戏"""
        try:
            hwnd = pygame.display.get_wm_info()["window"]
            ctypes.windll.imm32.ImmAssociateContext(hwnd, None)
        except Exception:
            pass

    # ==================== 场景管理 ====================
    def register_scene(self, name, scene_class):
        self._scenes[name] = scene_class

    def change_scene(self, name):
        if self.current_scene:
            self.current_scene.exit()

        scene_class = self._scenes.get(name)
        if scene_class is None:
            print(f"[警告] 场景 '{name}' 未注册！")
            return

        self.current_scene = scene_class(self)
        self.current_scene.enter()

    # ==================== 主循环 ====================
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)          # 卡顿时别让逻辑一次跳太多，避免穿墙

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.type == pygame.VIDEORESIZE and self.display_mode == "windowed":
                    self.window_width = event.w
                    self.window_height = event.h
                    self.render_surface = pygame.Surface((event.w, event.h))
                    settings.RENDER_WIDTH = event.w
                    settings.RENDER_HEIGHT = event.h
                    settings.CELL_SIZE = int(CELL_SIZE_BASE * self.scale)

            if self.current_scene:
                # 渲染表面 = 窗口大小，鼠标坐标无需转换
                self.current_scene.handle_events(events)
                self.current_scene.update(dt)
                self.current_scene.draw()

            # 直接 1:1 blit，无任何缩放 → 零模糊
            self.display.blit(self.render_surface, (0, 0))
            pygame.display.flip()

        self.quit()

    def quit(self):
        self.save_manager.save()
        pygame.quit()
        sys.exit()
