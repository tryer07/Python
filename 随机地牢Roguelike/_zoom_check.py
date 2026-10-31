"""临时：把 12x12 精灵放大到 96x96 单独实拍，检查像素画在放大镜下是否成形。用完即删。"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
VENV = os.path.abspath(os.path.join(ROOT, "..", ".venv", "Lib", "site-packages"))
if VENV not in sys.path:
    sys.path.append(VENV)

import pygame  # noqa: E402
import game as game_mod  # noqa: E402
from pixelart import SPRITES, bake_sprite, make_floor, make_wall  # noqa: E402
from settings import PALETTE, TILE  # noqa: E402

pygame.init()
Z = 8
names = ["player", "哥布林", "兽人", "骷髅剑士", "楼梯守卫", "potion", "stairs"]
cols = len(names)
sheet = pygame.Surface((cols * TILE * Z + (cols + 1) * 8, TILE * Z + 44))
sheet.fill((30, 28, 40))
font = pygame.font.Font(r"C:\Windows\Fonts\msyh.ttc", 14)
for i, name in enumerate(names):
    surf = bake_sprite(SPRITES[name])
    x = 8 + i * (TILE * Z + 8)
    pygame.draw.rect(sheet, PALETTE["b"], (x, 8, TILE * Z, TILE * Z))
    sheet.blit(pygame.transform.scale(surf, (TILE * Z, TILE * Z)), (x, 8))
    sheet.blit(font.render(name, True, PALETTE["k"]), (x, 8 + TILE * Z + 4))
pygame.image.save(sheet, os.path.join(ROOT, "截图检查", "像素0_精灵放大.png"))

# 纹理放大：三种墙 + 两块地板
tex = pygame.Surface((5 * TILE * Z + 6 * 8, TILE * Z + 8 * 2))
tex.fill((30, 28, 40))
kinds = [make_wall("plain"), make_wall("north"), make_wall("south"),
         make_wall("corner"), make_floor()]
for i, t in enumerate(kinds):
    x = 8 + i * (TILE * Z + 8)
    tex.blit(pygame.transform.scale(t, (TILE * Z, TILE * Z)), (x, 8))
pygame.image.save(tex, os.path.join(ROOT, "截图检查", "像素0_纹理放大.png"))
print("saved 两张放大图")

# 强制下潜到第 3 层：直接置 depth 重生层，直到出现 boss（不靠随机寻路）
g = game_mod.Game()
g._new_run()
g.state = game_mod.STATE_PLAYING
g.player.max_hp = 999
g.player.hp = 999
for _ in range(60):
    g.depth = 3
    g._enter_floor()
    if any(m.is_boss for m in g.monsters):
        break
print("层:", g.depth, "怪物:", [(m.name, m.is_boss) for m in g.monsters if m.alive])
# 把勇者直接放到守卫旁边的可走格（靠寻路接近会被游荡的怪堵住），保证 boss 入镜
boss = next((m for m in g.monsters if m.is_boss), None)
if boss is not None:
    for cell in ((boss.x + 1, boss.y), (boss.x - 1, boss.y),
                 (boss.x, boss.y + 1), (boss.x, boss.y - 1)):
        if g._is_floor_cell(cell):
            g.player.x, g.player.y = cell
            break
    g._update_view()
    print("守卫进入视野:", (boss.x, boss.y) in g.lit, "距离:",
          abs(boss.x - g.player.x) + abs(boss.y - g.player.y))
g._render()
pygame.image.save(g.screen, os.path.join(ROOT, "截图检查", "像素3_精英守卫.png"))
print("saved 像素3_精英守卫.png  回合", g.log.turn)

# 极端血量：分格装不下时要退成整条，不能溢出面板
g.player.max_hp, g.player.hp = 100, 62
g._render()
pygame.image.save(g.screen, os.path.join(ROOT, "截图检查", "像素7_高血量面板.png"))
print("saved 像素7_高血量面板.png")
