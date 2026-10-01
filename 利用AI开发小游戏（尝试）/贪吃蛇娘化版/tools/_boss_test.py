# -*- coding: utf-8 -*-
"""临时无头验证：Boss 战系统。跑完即删，不污染用户存档。"""

import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import settings as S  # noqa: E402
from core.game import Game  # noqa: E402
from scenes.battle import BattleScene  # noqa: E402
from game_logic.boss import Boss, Projectile, load_boss_cfg  # noqa: E402

RESULTS = []


def check(name, cond):
    RESULTS.append((name, bool(cond)))
    print(("  PASS  " if cond else "  FAIL  ") + name)


def make_game(scene_id="campus_garden"):
    g = Game()
    g.register_scene("battle", BattleScene)
    g.save_manager.data["selected_scene"] = scene_id
    # 存档写入重定向到临时文件，绝不碰用户真实存档
    g.save_manager.save_path = os.path.join(tempfile.gettempdir(), "_boss_test_save.json")
    g.change_scene("battle")
    return g


def spawn_boss(sc):
    sc.elapsed = 61.0
    sc.update(1 / 60)
    return sc.boss


# ---- A: 时间触发登场 ----
g = make_game("campus_garden")
sc = g.current_scene
b = spawn_boss(sc)
check("A 校园 Boss 按时间阈值登场", b is not None and sc.boss_spawned)
check("A 登场后切 boss BGM 且不崩", sc.boss.name == "樱之守护者")

# ---- B: 4 个 Boss 配置各攻击模式都能跑、产出弹幕/召唤/特效 ----
for sid, need_summon, need_fx in (
    ("campus_garden", False, False),
    ("neon_night", False, False),
    ("deep_sea", False, True),
    ("sakura_realm", True, True),
):
    cfg = load_boss_cfg(sid)
    if not cfg:
        check(f"B {sid} 配置载入", False)
        continue
    bs = Boss(cfg, (20, 6), lambda: S.CELL_SIZE)
    bs.intro = 0
    bs.hp = int(bs.hp_max * 0.15)   # 压到最深阶段，解锁全部攻击
    bullets = summon = fx = 0
    for _ in range(1800):           # 30s
        ev = bs.update(1 / 60, (10, 6),
                       {"cols": S.GRID_COLS, "rows": S.GRID_ROWS, "cell_px": S.CELL_SIZE})
        bullets += len(ev["bullets"])
        summon += ev["summon"]
        fx += len(ev["effects"])
    check(f"B {sid} 产出弹幕", bullets > 0)
    if need_summon:
        check(f"B {sid} 产出召唤", summon > 0)
    if need_fx:
        check(f"B {sid} 产出震击/冲撞特效", fx > 0)

# ---- C: 弹幕命中蛇 → 掉血 ----
sc.snake.invincible = 0.0
hp0 = sc.snake.hp
px, py = sc.snake.draw_pos
sc.projectiles = [Projectile((px, py), (0, 0), S.CELL_SIZE * 0.2, 1, (255, 0, 0))]
sc._handle_projectile_hits()
check("C 弹幕命中蛇掉血", sc.snake.hp == hp0 - 1)
check("C 命中后弹幕被清除", len(sc.projectiles) == 0)

# ---- D: 玩家撞击 Boss → Boss 掉血、玩家不掉血 ----
b = sc.boss
b.charge = None
sc.boss_hit_cd = 0.0
sc.snake.invincible = 0.0
head = sc.snake.cells[0]
b.pos_cells = [float(head[0]), float(head[1])]
php0, bhp0 = sc.snake.hp, b.hp
sc._handle_boss_contact()
check("D 撞击 Boss 掉血", b.hp < bhp0)
check("D 撞击时玩家不掉血", sc.snake.hp == php0)
# 限流：cd 未就绪时不再掉血
bhp1 = b.hp
sc._handle_boss_contact()
check("D BOSS_HIT_CD 限流生效", b.hp == bhp1)

# ---- E: 冲刺撞上玩家 → 玩家掉血 ----
sc.snake.invincible = 0.0
sc.snake.hp = S.HP_MAX
b.charge = {"phase": "dash", "timer": 0.3, "dir": (1, 0)}
php0 = sc.snake.hp
sc._handle_boss_contact()
check("E 冲刺命中玩家掉血", sc.snake.hp < php0)
b.charge = None

# ---- F: 技能（冲锋）打 Boss ----
sc.skills.sync_unlock(10)
sc.skills.dash_charges = 3
b.pos_cells = [sc.snake.grid_pos[0] + 0.5, sc.snake.grid_pos[1]]
bhp0 = b.hp
sc._apply_skill_to_boss(sc.snake.cells[0], set(sc.snake.cells[1:]))
check("F 冲锋技能对 Boss 造成伤害", b.hp < bhp0)

# ---- G: 击败 Boss → 胜利 + 战绩写盘 ----
b.hp = 1
b.alive = True
sc._damage_boss(50)
check("G Boss 血量归零即死", not b.alive)
sc._update_boss(1 / 60)
check("G 击败后 victory + finished", sc.victory and sc.finished)
prog = g.save_manager.data["progress"]
check("G record_victory 写 total_wins", prog.get("total_wins", 0) >= 1)
check("G record_victory 写 bosses_defeated", prog.get("bosses_defeated", {}).get("campus_garden", 0) >= 1)

# ---- H: 无 Boss 配置 → 退回无尽、不崩 ----
g2 = make_game("campus_garden")
sc2 = g2.current_scene
sc2.boss_cfg = None
sc2.elapsed = 200.0
for _ in range(60):
    sc2.update(1 / 60)
check("H 无配置时不登场 Boss 且不崩", sc2.boss is None and not sc2.victory)

# ---- I: 玩家中途死亡仍走 gameover（非胜利）----
g3 = make_game("campus_garden")
sc3 = g3.current_scene
sc3.snake.alive = False
sc3.update(1 / 60)
check("I 玩家死亡走 gameover", sc3.finished and not sc3.victory)

pygame.quit()

print("=" * 52)
ok = sum(1 for _, c in RESULTS if c)
print(f"  通过 {ok} / {len(RESULTS)}")
if ok != len(RESULTS):
    for n, c in RESULTS:
        if not c:
            print("  失败项:", n)
    sys.exit(1)
print("  全部通过")
sys.exit(0)
