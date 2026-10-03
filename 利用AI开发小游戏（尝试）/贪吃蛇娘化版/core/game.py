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
import threading

import pygame

import settings
from core.asset_manager import AssetManager
from core.audio_manager import AudioManager
from core.controls import Controls
from core.save_manager import SaveManager
from settings import (
    CELL_SIZE_BASE, DESIGN_HEIGHT, DESIGN_WIDTH,
    DISPLAY_MODES, FPS, FULLSCREEN, GAME_TITLE,
    RESOLUTION_OPTIONS, VOLUME_HOTKEY_STEP, VOLUME_REPEAT_DELAY_MS,
    VOLUME_REPEAT_INTERVAL_MS, WINDOW_SCALE,
)


class Game:
    """游戏主类：管理窗口、主循环、场景切换"""

    def __init__(self):
        # 必须在创建显示 / set_mode() 之前声明 DPI 感知，
        # 否则在开启了 Windows 显示缩放（125%/150%/200%）的机器上，
        # 全屏会拿到"虚拟分辨率"，被 GPU letterbox 成居中小窗 + 四周黑边。
        self._set_dpi_aware()
        # mixer 必须在 mixer.init() 之前预初始化，锁定采样格式，
        # 后面合成占位音的 Sound(buffer=...) 才能按这个格式对齐（否则声音发尖/报错）。
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass
        # 只初始化真正用到的子系统，不走 pygame.init()。
        # pygame.init() 会顺手初始化 joystick，而 Windows 枚举手柄设备在本机
        # 实测要卡 10 秒（启动慢的真凶，exe 与源码运行同病）。本作纯键鼠操作，
        # 跳过 joystick 后启动从 ~10s 降到 ~0.3s。
        pygame.display.init()
        pygame.font.init()
        # 音频设备后台线程打开：SDL 开设备偶发慢（设备被占 / 上一个进程
        # 强杀未释放时实测卡 ~10s），同步调会拖住出窗口或首帧。后台开 +
        # AudioManager 懒判定（_refresh_ok）：就绪自动接上，未就绪/无声卡
        # 降级静音，启动观感与音频互不拖累。
        self._mixer_thread = threading.Thread(
            target=self._bg_mixer_init, daemon=True)
        self._mixer_thread.start()

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
        # 音频管理器：mixer 尚未就绪/不可用时内部自动降级为 no-op，
        # 后台线程 init 完成后由 _refresh_ok 懒接上，不影响启动。
        # 构造时会把自己注册为模块级单例，供 ui/button.py 等无 game 引用处取用。
        try:
            self.audio = AudioManager(self.save_manager)
        except Exception:
            self.audio = AudioManager(None)
        self.running = True
        self.current_scene = None
        self._scenes = {}
        # 按键绑定（技能/闪避热键）：机器级配置，玩家可在游戏内改键。
        self.controls = Controls(self.save_manager)
        # 输入捕获标志：改键面板等待新按键时置 True，
        # 此时全局音量热键（方向键）主动让路，避免改键时误调音量。
        self.input_capture = False
        # 音量热键改的是内存值（persist=False），用这个脏标记延迟落盘：
        # 切场景 / 退出 / 取消暂停时一次性写回，避免长按方向键时高频写盘。
        self._audio_dirty = False
        # 长按连发状态：方向键 -> “下次可连发的时刻”（pygame.time ticks 毫秒）。
        # 按一下先走一格并记下 now+延迟；主循环轮询到点就持续连调。
        self._vol_hold = {}

    # ==================== 窗口 / 显示设置 ====================
    @staticmethod
    def _bg_mixer_init():
        """后台线程体：开音频设备，失败静默（AudioManager 自动 no-op）。"""
        try:
            pygame.mixer.init()
        except Exception:
            pass

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
        """禁用输入法，免得打字时弹出候选框挡住游戏。

        首次调用时把系统原本的输入法上下文句柄存下来，
        供 set_text_input(True) 临时恢复（存档命名等自由输入场景）。"""
        try:
            hwnd = pygame.display.get_wm_info()["window"]
            if not hasattr(self, "_ime_himc"):
                self._ime_himc = ctypes.windll.imm32.ImmAssociateContext(hwnd, None)
            else:
                ctypes.windll.imm32.ImmAssociateContext(hwnd, None)
        except Exception:
            pass

    def set_text_input(self, enabled):
        """开启/关闭自由文本输入（仅 Windows 有意义）。

        开启：恢复输入法关联 + start_text_input，场景才能收到
        pygame.TEXTINPUT（含中文 IME 提交）；
        关闭：stop_text_input + 重新禁用输入法，回到纯游戏按键状态。"""
        if enabled:
            try:
                hwnd = pygame.display.get_wm_info()["window"]
                ctypes.windll.imm32.ImmAssociateContext(
                    hwnd, getattr(self, "_ime_himc", None))
            except Exception:
                pass
            try:
                pygame.key.start_text_input()
            except Exception:
                pass
        else:
            try:
                pygame.key.stop_text_input()
            except Exception:
                pass
            self._disable_ime()

    # ==================== 场景管理 ====================
    def register_scene(self, name, scene_class):
        self._scenes[name] = scene_class

    def change_scene(self, name):
        if self.current_scene:
            self.current_scene.exit()
        # 离开当前场景前把热键调过的音量落盘，并清掉长按连发状态
        self.flush_audio()
        self._vol_hold.clear()

        scene_class = self._scenes.get(name)
        if scene_class is None:
            print(f"[警告] 场景 '{name}' 未注册！")
            return

        # 离开旧场景：清掉可能残留的输入捕获状态（改键浮层开着时切场景）
        self.input_capture = False
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

            # 长按方向键时持续连调音量（仅在场景不占用方向键时生效）
            self._update_volume_repeat()

            # 驱动后台 BGM：预载好的曲子一旦就绪就无缝淡入开播（交叉淡入淡出）
            self.audio.update(dt)

            if self.current_scene:
                # 渲染表面 = 窗口大小，鼠标坐标无需转换
                try:
                    self.current_scene.handle_events(events)
                    self.current_scene.update(dt)
                    self.current_scene.draw()
                except Exception as e:  # 兜底：绝不让 windowed exe 静默闪退
                    from core.crash import report_crash
                    name = type(self.current_scene).__name__ if self.current_scene else "?"
                    report_crash(e, context=f"scene={name}")
                    self.running = False
                    break

            # 直接 1:1 blit，无任何缩放 → 零模糊
            self.display.blit(self.render_surface, (0, 0))
            pygame.display.flip()

        self.quit()

    # ==================== 音量调试热键 ====================
    # 方向键 -> 增减方向。↑/→ 增大、↓/← 减小，作用于“上次鼠标点选”的音量目标。
    _VOL_KEY_DIR = {
        pygame.K_UP: 1, pygame.K_RIGHT: 1,
        pygame.K_DOWN: -1, pygame.K_LEFT: -1,
    }

    def _handle_volume_hotkey(self, event):
        """方向键调节音量：作用于玩家上次用鼠标点选的目标（音乐 or 音效）。

        仅在「当前场景不占用方向键」时生效（战斗进行中会让路，暂停/菜单才接管）。
        按一下走一格；按住超过 VOLUME_REPEAT_DELAY_MS 后由 _update_volume_repeat 连发。
        命中时返回 True（事件已消费），否则 False。"""
        if getattr(self, "input_capture", False):
            return False        # 改键面板正在捕获按键，方向键让给它
        if self.current_scene is not None and self.current_scene.wants_movement_keys():
            return False
        direction = self._VOL_KEY_DIR.get(event.key)
        if direction is None:
            return False
        self._apply_volume_step(direction)
        # 记下“连发启动时刻”：长按超过延迟后主循环才开始连调
        self._vol_hold[event.key] = pygame.time.get_ticks() + VOLUME_REPEAT_DELAY_MS
        return True

    def _apply_volume_step(self, direction):
        """对当前焦点音量（audio.volume_focus）增减一格 ±VOLUME_HOTKEY_STEP/100。"""
        a = self.audio
        step = VOLUME_HOTKEY_STEP / 100.0
        if getattr(a, "volume_focus", "bgm") == "sfx":
            a.set_sfx_volume(a.sfx_volume + direction * step, persist=False)
            a.play("ui_click", throttle=0.05)   # 补一声，直接听出 SFX 音量大小
        else:
            a.set_bgm_volume(a.bgm_volume + direction * step, persist=False)
        self._audio_dirty = True

    def _update_volume_repeat(self):
        """长按方向键连发：按住超过延迟后，每 VOLUME_REPEAT_INTERVAL_MS 调一格。

        pygame 默认不自动重复 KEYDOWN，所以这里靠轮询按键状态自己做连发。"""
        if not self._vol_hold:
            return
        # 场景开始占用方向键（如取消暂停回到战斗）时，立刻停止连发
        if self.current_scene is not None and self.current_scene.wants_movement_keys():
            self._vol_hold.clear()
            return
        pressed = pygame.key.get_pressed()
        now = pygame.time.get_ticks()
        for key, next_at in list(self._vol_hold.items()):
            if not pressed[key]:
                del self._vol_hold[key]       # 已松开，清理
                continue
            if now >= next_at:
                direction = self._VOL_KEY_DIR.get(key)
                if direction is not None:
                    self._apply_volume_step(direction)
                self._vol_hold[key] = now + VOLUME_REPEAT_INTERVAL_MS

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
