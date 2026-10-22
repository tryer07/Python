# -*- coding: utf-8 -*-
"""PVZ 同人重制版 · STEP 1 入口。

目标（按提示词）：1600x900 窗口，主循环，左上角实时 FPS，ESC 退出，
屏幕中央显示按 ASSET_SCALE 放大后的豌豆射手脑袋。

架构要点（工程约定第 1/3 条）：
  - 逻辑用固定时间步（60Hz accumulator），渲染每帧一次，两者分离。
  - 素材启动时一次性预加载，循环内只 blit 缓存。
  - 内部始终渲染到 1600x900 画布，再缩放到自适应大小的窗口。
"""

from __future__ import annotations

import ctypes
import sys

import pygame

import asset_loader
import constants

# ---------- 固定时间步 ----------
FIXED_DT = 1.0 / constants.FPS   # 逻辑步长（秒）


def _set_dpi_aware() -> None:
    """声明 DPI 感知，避免 Windows 显示缩放导致窗口模糊/黑边。"""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except OSError:
            pass  # 环境不支持时忽略，不影响启动


def init_pygame() -> tuple[pygame.Surface, pygame.font.Font]:
    """初始化 pygame，创建窗口与字体，返回 (窗口 Surface, FPS 字体)。"""
    _set_dpi_aware()
    pygame.init()
    try:
        pygame.mixer.init()          # 音频设备不可用时不影响主流程
    except pygame.error as exc:
        print(f"[main] 音频初始化失败（无声运行）: {exc}")
    screen = pygame.display.set_mode((constants.SCREEN_W, constants.SCREEN_H),
                                     pygame.RESIZABLE)
    pygame.display.set_caption("PVZ 同人重制版 · STEP 1 骨架")
    font = pygame.font.SysFont("microsoftyahei,segoeui", 24)
    return screen, font


def load_step1_assets() -> None:
    """建立素材索引并一次性预加载本步用到的贴图。"""
    asset_loader.build_image_index()
    asset_loader.build_sound_index()
    asset_loader.preload(["PeaShooter_Head"])
    asset_loader.report_missing()


class Game:
    """STEP 1 骨架演示：中央展示豌豆射手脑袋 + 左上角 FPS。"""

    def __init__(self, screen: pygame.Surface,
                 font: pygame.font.Font) -> None:
        self.screen = screen
        self.font = font
        # 画布固定 1600x900，与窗口实际大小解耦（窗口自适应缩放）
        self.canvas = pygame.Surface((constants.SCREEN_W, constants.SCREEN_H))
        self.head = asset_loader.get_scaled("PeaShooter_Head")
        # 预计算贴图居中位置（循环内不做任何加载/缩放）
        self.head_rect = self.head.get_rect(
            center=(constants.SCREEN_W // 2, constants.SCREEN_H // 2))
        self.running = True

    def handle_events(self) -> None:
        """事件处理：ESC 退出、窗口尺寸变化时重建缩放目标。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
            elif event.type == pygame.VIDEORESIZE:
                # RESIZABLE 模式下窗口大小变化，只需更新 screen 尺寸
                self.screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE)

    def update(self, dt: float) -> None:
        """固定步长逻辑更新。STEP 1 无玩法逻辑，仅占位。"""
        _ = dt  # 本步暂无逻辑，保持签名与后续步骤一致

    def render(self, fps: float) -> None:
        """渲染一帧：先画到 1600x900 画布，再缩放到窗口。"""
        self.canvas.fill((0, 0, 0))
        self.canvas.blit(self.head, self.head_rect)
        # 左上角实时 FPS（由主循环传入 clock 实测值）
        fps_text = self.font.render(f"FPS: {fps:.0f}", False, (0, 255, 0))
        self.canvas.blit(fps_text, (8, 8))
        # 窗口自适应缩放：尺寸一致时 1:1 直贴，避免多余缩放开销
        win_size = self.screen.get_size()
        if win_size == self.canvas.get_size():
            self.screen.blit(self.canvas, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(self.canvas, win_size)
            self.screen.blit(scaled, (0, 0))
        pygame.display.flip()


def main() -> None:
    """入口：初始化 -> 固定时间步主循环 -> 退出清理。"""
    screen, font = init_pygame()
    load_step1_assets()
    game = Game(screen, font)

    clock = pygame.time.Clock()
    accumulator = 0.0
    while game.running:
        # 帧间隔计入累加器，按固定步长驱动逻辑（60Hz）
        frame_ms = clock.tick(constants.FPS)
        game.handle_events()          # 事件每帧处理一次，保证响应不延迟
        accumulator += frame_ms / 1000.0
        accumulator = min(accumulator, 0.25)   # 防卡顿后逻辑追帧雪崩
        while accumulator >= FIXED_DT:
            game.update(FIXED_DT)
            accumulator -= FIXED_DT
        # 渲染每帧一次，FPS 直接取 clock 实测值
        game.render(clock.get_fps())
    pygame.quit()


if __name__ == "__main__":
    main()
