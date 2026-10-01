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
from core.audio_manager import AudioManager
from core.save_manager import SaveManager
from settings import (
    CELL_SIZE_BASE, DESIGN_HEIGHT, DESIGN_WIDTH,
    DISPLAY_MODES, FPS, FULLSCREEN, GAME_TITLE,
    RESOLUTION_OPTIONS, VOLUME_HOTKEY_STEP, WINDOW_SCALE,
)


class Game:
    """游戏主类：管理窗口、主循环、场景切换"""

    def __init__(self):
        # 必须在 pygame.init() / set_mode() 之前声明 DPI 感知，
        # 否则在开启了 Windows 显示缩放（125%/150%/200%）的机器上，
        # 全屏会拿到"虚拟分辨率"，被 GPU letterbox 成居中小窗 + 四周黑边。
        self._set_dpi_aware()
        # mixer 必须在 pygame.init() 之前预初始化，锁定采样格式，
        # 后面合成占位音的 Sound(buffer=...) 才能按这个格式对齐（否则声音发尖/报错）。
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass
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
        # 音频管理器：mixer 不可用时内部自动降级为 no-op，不影响启动。
        # 构造时会把自己注册为模块级单例，供 ui/button.py 等无 game 引用处取用。
        try:
            self.audio = AudioManager(self.save_manager)
        except Exception:
            self.audio = AudioManager(None)
        self.running = True
        self.current_scene = None
        self._scenes = {}
        # 音量热键改的是内存值（persist=False），用这个脏标记延迟落盘：
        # 切场景 / 退出 / 取消暂停时一次性写回，避免长按方向键时高频写盘。
        self._audio_dirty = False

    # ==================== 窗口 / 显示设置 ====================
    @property
    def scale(self):
        """缩放因子：窗口宽度 / 设计基准宽度"""
        return self.window_width / DESIGN_WIDTH

    def _apply_display_settings(self):
        """根据 display_mode / display_resolution 创建或重建窗口"""
        # 关键：钳制基准必须用"真实桌面分辨率"，绝不能用 pygame.display.Info().current_w。
        # 窗口模式下 Info().current_w 返回的是当前窗口尺寸而非桌面尺寸，一旦拿它做基准，
        # 每次切分辨率都会在旧窗口上再乘一次系数（min(tw, sw*0.95)），系数反复叠加 → 越选越小。
        sw, sh = self._get_desktop_size()

        if self.display_mode == "fullscreen":
            # 全屏以显示器支持的最大分辨率为基准，才能真正铺满屏幕
            self.window_width, self.window_height = self._get_fullscreen_size()
            flags = pygame.FULLSCREEN
        elif self.display_mode == "borderless":
            # 无边框用桌面尺寸（而非最大模式），否则窗口会超出屏幕
            self.window_width, self.window_height = sw, sh
            flags = pygame.NOFRAME
        else:
            if self.display_resolution != (0, 0):
                tw, th = self.display_resolution
                # 预留标题栏 + 任务栏空间；超出桌面时按宽高比整体缩小（不变形、不叠加）
                avail_w = int(sw * 0.98)
                avail_h = int(sh * 0.92)
                fit = min(1.0, avail_w / tw, avail_h / th)
                self.window_width = max(320, int(tw * fit))
                self.window_height = max(180, int(th * fit))
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
        # 关键：以 SDL 实际创建的显示表面尺寸为准回写。
        # 全屏时请求的分辨率不一定等于驱动真正给出的表面尺寸（DPI 缩放、
        # 非原生模式等），一旦不一致，1:1 blit 就会留出黑边。这里对齐后
        # 渲染表面与显示表面严格等大，铺满整个屏幕。
        self.window_width, self.window_height = self.display.get_size()
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
        """返回全部可选分辨率 [(w, h, 说明), ...]。

        不再按屏幕尺寸过滤：窗口模式下超出屏幕的选择会被 _apply_display_settings
        自动收敛到屏幕的 95%。若在这里过滤，小屏机器会只剩一个选项，
        玩家就无法自由选择窗口大小了。"""
        return list(RESOLUTION_OPTIONS)

    def toggle_fullscreen(self):
        """F11 快速全屏 / 窗口切换"""
        if self.display.get_flags() & pygame.FULLSCREEN:
            self.set_display(mode="windowed")
        else:
            self.set_display(mode="fullscreen")

    def _get_desktop_size(self):
        """返回真实桌面分辨率（不受已创建窗口影响）。

        注意：pygame.display.Info().current_w/h 在窗口模式下会被“当前窗口”污染，
        返回窗口尺寸而非桌面尺寸，用它做钳制基准会导致分辨率越切越小。
        这里优先用 get_desktop_sizes()（始终返回真实桌面），其次退回全屏模式列表最大值。"""
        try:
            sizes = pygame.display.get_desktop_sizes()
            if sizes:
                w, h = sizes[0]
                if int(w) > 0 and int(h) > 0:
                    return int(w), int(h)
        except Exception:
            pass
        try:
            modes = pygame.display.list_modes()
            if isinstance(modes, (list, tuple)) and modes:
                best = max(modes, key=lambda m: int(m[0]) * int(m[1]))
                return int(best[0]), int(best[1])
        except Exception:
            pass
        info = pygame.display.Info()
        return int(info.current_w), int(info.current_h)

    def _get_fullscreen_size(self):
        """检测显示器支持的最大分辨率，作为全屏基准，确保铺满整个屏幕。

        优先用 list_modes() 拿真实支持的全屏模式并取面积最大的一个；
        拿不到（返回 -1 表示任意分辨率 / 空列表 / 异常）时退回桌面分辨率。"""
        try:
            modes = pygame.display.list_modes()
            # list_modes() 可能返回 -1（任意分辨率都支持）或空列表，需先判型
            if isinstance(modes, (list, tuple)) and modes:
                best = max(modes, key=lambda m: int(m[0]) * int(m[1]))
                bw, bh = int(best[0]), int(best[1])
                if bw > 0 and bh > 0:
                    return bw, bh
        except Exception:
            pass
        info = pygame.display.Info()
        return int(info.current_w), int(info.current_h)

    def _set_dpi_aware(self):
        """声明进程 DPI 感知，拿到屏幕真实物理分辨率，避免全屏黑边（仅 Windows）"""
        if sys.platform != "win32":
            return
        try:
            # 优先用 Per-Monitor V2，失败再退回系统级 DPI 感知
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

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
        # 离开当前场景前把热键调过的音量落盘
        self.flush_audio()

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
                elif event.type == pygame.KEYDOWN and self._handle_volume_hotkey(event):
                    pass        # 方向键被音量热键消费（仅在场景不占用方向键时）
                elif event.type == pygame.VIDEORESIZE and self.display_mode == "windowed":
                    # 手动拖拽窗口：同步渲染尺寸，并让当前场景按新缩放重建字体/布局，
                    # 否则拖大拖小后字体和按钮会停留在旧尺寸上不同步。
                    self.window_width = max(1, event.w)
                    self.window_height = max(1, event.h)
                    self.render_surface = pygame.Surface((self.window_width, self.window_height))
                    settings.RENDER_WIDTH = self.window_width
                    settings.RENDER_HEIGHT = self.window_height
                    settings.CELL_SIZE = int(CELL_SIZE_BASE * self.scale)
                    if self.current_scene:
                        self.current_scene.on_resize()

            if self.current_scene:
                # 渲染表面 = 窗口大小，鼠标坐标无需转换
                self.current_scene.handle_events(events)
                self.current_scene.update(dt)
                self.current_scene.draw()

            # 直接 1:1 blit，无任何缩放 → 零模糊
            self.display.blit(self.render_surface, (0, 0))
            pygame.display.flip()

        self.quit()

    # ==================== 音量调试热键 ====================
    def _handle_volume_hotkey(self, event):
        """↑/↓ 调 BGM、←/→ 调 SFX，每按一下 ±VOLUME_HOTKEY_STEP（0~100）。

        仅在「当前场景不占用方向键」时生效（战斗进行中会让路，暂停/菜单才接管）。
        命中时返回 True（事件已消费），否则 False。"""
        if self.current_scene is not None and self.current_scene.wants_movement_keys():
            return False
        step = VOLUME_HOTKEY_STEP / 100.0
        a = self.audio
        if event.key == pygame.K_UP:
            a.set_bgm_volume(a.bgm_volume + step, persist=False)
            self._audio_dirty = True
            return True
        if event.key == pygame.K_DOWN:
            a.set_bgm_volume(a.bgm_volume - step, persist=False)
            self._audio_dirty = True
            return True
        if event.key == pygame.K_RIGHT:
            a.set_sfx_volume(a.sfx_volume + step, persist=False)
            self._audio_dirty = True
            a.play("ui_click")   # 补一声，方便直接听出 SFX 音量大小
            return True
        if event.key == pygame.K_LEFT:
            a.set_sfx_volume(a.sfx_volume - step, persist=False)
            self._audio_dirty = True
            a.play("ui_click")
            return True
        return False

    def flush_audio(self):
        """把热键改过但尚未落盘的音量写回存档（幂等，无脏数据时什么都不做）。"""
        if self._audio_dirty:
            self.audio.save_volumes()
            self._audio_dirty = False

    def quit(self):
        self.flush_audio()
        self.save_manager.save()
        pygame.quit()
        sys.exit()
