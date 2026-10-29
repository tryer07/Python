# 临时截图驱动器：真实窗口模式运行游戏，每帧把窗口刷到最顶层，从屏幕拷贝窗口区域
import ctypes
import ctypes.wintypes
import shutil
import struct
import sys
import time as _wall
from pathlib import Path

# 必须在导入任何 GUI 模块前提前声明 DPI 感知，坐标才与物理像素一致
ctypes.windll.shcore.SetProcessDpiAwareness(2)

from ursina import Ursina, application, invoke, window

PROJECT_ROOT = Path(r'D:\Python\Python项目存放点')
OUT_DIR = PROJECT_ROOT / '截图检查'
OUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(PROJECT_ROOT / '3D迷宫探索'))

import main as game_mod  # noqa: E402  （__main__ 守卫：导入无副作用）


class _FakeMouse:
    """驱动里无法真锁鼠标：locked 恒 True 绕过暂停分支，velocity 恒 0 不转视角"""
    locked = True
    velocity = (0.0, 0.0)

app = Ursina(title='3D 迷宫逃脱', borderless=False, fullscreen=False,
             size=(1280, 720), position=(60, 60))
game = game_mod.MazeGame()
game_mod.game = game

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
hwnd_holder: dict = {}


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', ctypes.c_uint32), ('biWidth', ctypes.c_int32),
        ('biHeight', ctypes.c_int32), ('biPlanes', ctypes.c_uint16),
        ('biBitCount', ctypes.c_uint16), ('biCompression', ctypes.c_uint32),
        ('biSizeImage', ctypes.c_uint32), ('biXPelsPerMeter', ctypes.c_int32),
        ('biYPelsPerMeter', ctypes.c_int32), ('biClrUsed', ctypes.c_uint32),
        ('biClrImportant', ctypes.c_uint32)]


# ursina 只自动派发 __main__（即本驱动）里的 update/input
def update() -> None:
    game.update()


def input(key: str) -> None:  # noqa: A001
    game.input(key)


def ascii_path(p: Path) -> str:
    """中文目录转 NTFS 8.3 短路径，给 Panda 写文件用"""
    user32.GetShortPathNameW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
    buf = ctypes.create_unicode_buffer(512)
    user32.GetShortPathNameW(str(p), buf, 512)
    return buf.value or str(p)


def grab(name: str, tries: int = 3) -> None:
    """直接从 OpenGL 后缓冲取像素（getScreenshot），不受屏幕上其他窗口遮挡影响"""
    base = application.base
    for _ in range(tries):
        base.graphicsEngine.renderFrame()
        pm = base.win.getScreenshot()
        if pm.getXSize() > 10:
            tmp = ascii_path(PROJECT_ROOT / '_shot_tmp.png')
            if pm.write(tmp):
                shutil.move(tmp, str(OUT_DIR / name))
                print(f'[{name}] 已截图 {pm.getXSize()}x{pm.getYSize()}', flush=True)
                return
        _wall.sleep(0.3)
    print(f'[{name}] 后缓冲取像素失败', flush=True)


def _begin() -> None:
    game.mouse = _FakeMouse()   # 绕过未锁鼠标的暂停分支
    game._begin()


def _finish() -> None:
    grab('2_游玩界面.png')
    global done
    done = True


done = False
invoke(_begin, delay=4)
invoke(_finish, delay=8)

hwnd_holder['h'] = ctypes.c_void_p(
    int(window.pipe.win32_buffered_window_handle)
    if hasattr(window, 'pipe')
    else int(app.win.getWindowHandle().getIntHandle()))

_start = _wall.time()
_frames = 0
while not done and (_wall.time() - _start) < 60:
    app.step()
    _frames += 1
    if _frames % 5 == 0:   # 持续置顶，防止被用户屏幕上的其他窗口盖住
        user32.SetWindowPos(hwnd_holder['h'], -1, 60, 60, 0, 0,
                            0x0001 | 0x0040 | 0x0001)
    if _frames == 120:
        grab('1_开场界面.png')      # 跑约 120 帧后截开场
