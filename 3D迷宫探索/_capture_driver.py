# 临时截图驱动器：真实启动游戏（不改任何游戏代码），在开场指南/游玩中各截一张窗口图
import ctypes
import sys
import ctypes.wintypes
import time as _wall
from pathlib import Path

from ursina import application, invoke

PROJECT_ROOT = Path(r'D:\Python\Python项目存放点')
OUT_DIR = PROJECT_ROOT / '截图检查'
OUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(PROJECT_ROOT / '3D迷宫探索'))

import main as game_mod  # noqa: E402  （__main__ 守卫：导入无副作用）

from ursina import Ursina, window  # noqa: E402

app = Ursina(title='3D 迷宫逃脱', borderless=False, fullscreen=False)
window.size = (1280, 720)
game = game_mod.MazeGame()
game_mod.game = game


# ursina 只自动派发 __main__（即本驱动）里的 update/input
def update() -> None:
    game.update()


def input(key: str) -> None:  # noqa: A001
    game.input(key)


class _FakeMouse:
    """游玩状态下冒充已锁定的鼠标：驱动里无法真锁，绕过暂停分支"""
    locked = True
    velocity = (0.0, 0.0)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', ctypes.c_uint32), ('biWidth', ctypes.c_int32),
        ('biHeight', ctypes.c_int32), ('biPlanes', ctypes.c_uint16),
        ('biBitCount', ctypes.c_uint16), ('biCompression', ctypes.c_uint32),
        ('biSizeImage', ctypes.c_uint32), ('biXPelsPerMeter', ctypes.c_int32),
        ('biYPelsPerMeter', ctypes.c_int32), ('biClrUsed', ctypes.c_uint32),
        ('biClrImportant', ctypes.c_uint32)]


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


def grab(name: str) -> None:
    """PrintWindow 直接抽游戏窗口像素存 BMP：不受遮挡影响，失败则退回屏幕区域拷贝"""
    hwnd = ctypes.c_void_p(int(application.base.win.getWindowHandle().getIntHandle()))
    rect = ctypes.wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        print(f'[{name}] 拿不到窗口矩形', flush=True)
        return
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w < 200 or h < 200:
        print(f'[{name}] 窗口尺寸异常 {w}x{h}', flush=True)
        return

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [('bmiHeader', BITMAPINFOHEADER),
                    ('bmiColors', ctypes.c_uint32 * 3)]

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h          # 顶向下的行序
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)

    hdc_win = user32.GetDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hdc_win)
    bmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
    gdi32.SelectObject(mem_dc, bmp)
    got = user32.PrintWindow(hwnd, mem_dc, 2)   # PW_RENDERFULLCONTENT
    if got:
        got = gdi32.GetDIBits(mem_dc, bmp, 0, h, buf, ctypes.byref(bmi), 0) == h
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hdc_win)
    if not got:
        print(f'[{name}] 提像素失败 w={w} h={h}', flush=True)
        return

    out = str(OUT_DIR / name)
    import struct
    with open(out, 'wb') as f:
        f.write(b'BM')
        f.write(struct.pack('<IHHI', 54 + len(buf.raw), 0, 0, 54))
        f.write(ctypes.string_at(ctypes.addressof(bmi.bmiHeader),
                                 ctypes.sizeof(BITMAPINFOHEADER)))
        f.write(buf.raw)
    print(f'[{name}] 已存 {out} {w}x{h}', flush=True)


def launch() -> None:
    invoke(grab, '1_开场界面.bmp', delay=6)
    # 模拟玩家点了“开始”按钮之后的状态（绕过鼠标未锁的暂停分支）
    def _begin() -> None:
        game.mouse = _FakeMouse()
        game._begin()
    invoke(_begin, delay=9)
    invoke(_finish, delay=12)


def _finish() -> None:
    grab('2_游玩界面.bmp')
    global done
    done = True
    application.quit()


done = False
_start = _wall.time()
launch()
while not done and (_wall.time() - _start) < 40:
    app.step()
