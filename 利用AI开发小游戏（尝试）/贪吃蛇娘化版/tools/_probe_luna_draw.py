# -*- coding: utf-8 -*-
"""一次性无头探针：验证月见 battle 的 DRAW 路径（playsim 只跑 update 不跑 draw）。

覆盖：
  1. 自然对局循环里每帧 scene.draw()——真实技能释放自然填充
     luna_mark / luna_pull / luna_lock / 月相环 / white_flash，随镜头滚动绘制。
  2. 强制段：手动铺 luna_fields(二段场，自然循环打不出) + 四个月相环 + 白闪，
     逐相位 draw，确保 _draw_luna 的场分支与 _paint_luna_ring 四相位都不崩。
跑完即删。
"""
import os
import shutil
import sys
import tempfile
import traceback

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import core.save_manager as _sm  # noqa: E402
from core.game import Game  # noqa: E402
from scenes.battle import BattleScene  # noqa: E402

FAILS = []
tmp = tempfile.mkdtemp(prefix="sg_lunadraw_")
_sm.SAVES_DIR = tmp

Game._get_desktop_size = lambda self: (2560, 1440)
game = Game()
game.set_display(mode="windowed", resolution=(960, 540))
game.register_scene("battle", BattleScene)
sm = game.save_manager
sm.data["selected_character"] = "lamia_luna"
sm.data["owned_characters"] = ["lamia_luna"]
sm.data["selected_scene"] = "campus_garden"
sm.data["tutorial_done"] = True
game.pending_run = {"mode": "endless", "scene": "campus_garden",
                    "char_id": "lamia_luna"}
game.change_scene("battle")
scene = game.current_scene


class FakeKeys:
    def __init__(self):
        self.pressed = set()

    def __getitem__(self, k):
        return 1 if k in self.pressed else 0


fake = FakeKeys()
real_gp = pygame.key.get_pressed
pygame.key.get_pressed = lambda: fake

phases_seen = set()
saw = {"mark": False, "fields": False, "pull": False, "lock": False,
       "flash": False}
draws = 0
dt = 1 / 60
try:
    for _ in range(int(55 / dt)):
        if scene.card_overlay:
            scene._choose_card(0)
        elif scene.finished or not scene.snake.alive:
            break
        else:
            fake.pressed = set()
            cdr = scene._eff_cdr
            for a in scene.skills.actives:
                sid = a.get("id")
                key = a.get("key", 1)
                if sid and scene.skills.ready(sid, cdr):
                    scene.cast_skill(key)
            scene.update(dt)
        scene.draw()
        draws += 1
        if scene.luna_phase is not None:
            phases_seen.add(scene.luna_phase)
        saw["mark"] |= scene.luna_mark is not None
        saw["fields"] |= len(scene.luna_fields) > 0
        saw["pull"] |= scene.luna_pull is not None
        saw["lock"] |= scene.luna_lock is not None
        saw["flash"] |= scene.white_flash > 0
except Exception:  # noqa: BLE001
    traceback.print_exc()
    FAILS.append("natural sim+draw crashed")
finally:
    pygame.key.get_pressed = real_gp

print(f"NATURAL draws={draws} phases_seen={sorted(phases_seen)} saw={saw}")

# ---- 强制段：fields + 四相位环 + 白闪（自然循环打不出的分支）----
px, py = scene.snake.pos
scene.luna_mark = {"x": px, "y": py, "t": 1.5, "max_t": 2.0,
                   "ev": {}, "fx": "luna_phase_dash"}
scene.luna_fields = [
    {"x": px, "y": py, "r": 100.0, "kind": "speed", "mult": 1.25,
     "t": 2.0, "max_t": 3.0, "fx": "luna_phase_dash", "heal_pct": 0.0},
    {"x": px + 60, "y": py, "r": 100.0, "kind": "heal", "heal_pct": 0.05,
     "mult": 1.0, "t": 2.0, "max_t": 3.0, "fx": "luna_phase_dash"},
]
scene.luna_pull = {"t": 1.0, "max_t": 1.5, "r": 200.0, "strength": 420,
                   "shield_pct": 0.04, "shield_time": 4.0, "pulled": set(),
                   "color": (184, 196, 240), "fx": "luna_pull"}
scene.luna_lock = {"t": 5.0, "max_t": 8.0, "tick": 1.0, "weaken": 3,
                   "ev": {}, "color": (240, 226, 170), "fx": "luna_fullmoon"}
for ph in (0, 1, 2, 3):
    try:
        scene.luna_phase = ph
        scene.white_flash = 0.5
        scene.draw()
        print(f"  forced phase {ph} draw OK")
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        FAILS.append(f"forced phase {ph} draw crashed")

shutil.rmtree(tmp, ignore_errors=True)
pygame.quit()
print("FAILS=", FAILS)
sys.exit(1 if FAILS else 0)
