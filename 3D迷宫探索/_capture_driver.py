# 临时截图驱动器：offscreen 模式真实运行游戏（不弹窗口、不受屏幕其他程序干扰），存 PNG 检查画面
import sys
import time as _wall
from pathlib import Path

from ursina import Ursina, application, invoke, window

PROJECT_ROOT = Path(r'D:\Python\Python项目存放点')
OUT_DIR = PROJECT_ROOT / '截图检查'
OUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(PROJECT_ROOT / '3D迷宫探索'))

import main as game_mod  # noqa: E402  （__main__ 守卫：导入无副作用）


class _FakeMouse:
    """offscreen 下没有真窗口，mouse.locked 会崩；整体替换成无操作假鼠标"""
    velocity = (0.0, 0.0)
    visible = True
    _locked = True

    @property
    def locked(self) -> bool:
        return self._locked

    @locked.setter
    def locked(self, value: bool) -> None:
        self._locked = bool(value)


fake_mouse = _FakeMouse()
import ursina.mouse as _um  # noqa: E402

_um.instance = fake_mouse
game_mod.mouse = fake_mouse

app = Ursina(title='3D 迷宫逃脱', borderless=False, window_type='offscreen')
window.size = (1280, 720)
game = game_mod.MazeGame()
game_mod.game = game


# ursina 只自动派发 __main__（即本驱动）里的 update/input
def update() -> None:
    game.update()


def input(key: str) -> None:  # noqa: A001
    game.input(key)


def grab(name: str) -> None:
    base = application.base
    base.graphicsEngine.renderFrame()   # 确保当前帧已完整渲染
    base.win.screenshot(str(OUT_DIR / name))
    print(f'[{name}] 已截图', flush=True)


def _begin() -> None:
    game._begin()


def _finish() -> None:
    grab('2_游玩界面.png')
    global done
    done = True


done = False
grab('1_开场界面.png')          # 开场面板在 launch 循环跑起来前就已摆好
invoke(_begin, delay=4)
invoke(_finish, delay=8)

_start = _wall.time()
while not done and (_wall.time() - _start) < 60:
    app.step()
