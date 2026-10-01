# -*- coding: utf-8 -*-
"""把处理后的素材拼成一张预览图（放在棋盘底上，方便看透明区和水印）"""
import os
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AST = os.path.join(BASE, "assets")
OUT = os.path.join(BASE, "tools", "_preview.png")

FILES = [
    "characters/sakura/head.png",
    "characters/sakura/body_seg.png",
    "characters/sakura/tail_tip.png",
    "characters/mob_shadow.png",
    "items/exp_berry.png",
    "items/energy_crystal.png",
]

CELL = 300
COLS = 3
ROWS = 2
W, H = CELL * COLS, CELL * ROWS

canvas = Image.new("RGBA", (W, H), (40, 40, 42, 255))
# 棋盘底
for y in range(0, H, 20):
    for x in range(0, W, 20):
        if (x // 20 + y // 20) % 2 == 0:
            for yy in range(y, min(y + 20, H)):
                for xx in range(x, min(x + 20, W)):
                    canvas.putpixel((xx, yy), (58, 58, 60, 255))

for i, rel in enumerate(FILES):
    p = os.path.join(AST, rel.replace("/", os.sep))
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGBA")
    im.thumbnail((CELL - 30, CELL - 30), Image.LANCZOS)
    cx = (i % COLS) * CELL + CELL // 2
    cy = (i // COLS) * CELL + CELL // 2
    canvas.alpha_composite(im, (cx - im.width // 2, cy - im.height // 2))

canvas.convert("RGB").save(OUT, "PNG")
print(OUT)
