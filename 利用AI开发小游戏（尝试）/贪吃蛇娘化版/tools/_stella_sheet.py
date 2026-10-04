# -*- coding: utf-8 -*-
"""一次性：把星璃普攻姿势图(4)+特效贴图(2)拼成对照表，目检抠图与配色（跑完即删）。"""
import os

from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = os.path.join(BASE, "assets", "characters", "lamia_stella")
FX = os.path.join(BASE, "assets", "effects", "melee")

tiles = [
    ("atk_1", os.path.join(CH, "atk_1.png")),
    ("atk_3", os.path.join(CH, "atk_3.png")),
    ("atk_human_1", os.path.join(CH, "atk_human_1.png")),
    ("atk_human_3", os.path.join(CH, "atk_human_3.png")),
    ("fx_lamia", os.path.join(FX, "stella_atk_lamia.png")),
    ("fx_human", os.path.join(FX, "stella_atk_human.png")),
]

CELL = 360
cols, rows = 3, 2
sheet = Image.new("RGBA", (cols * CELL, rows * (CELL + 24)), (24, 20, 34, 255))
from PIL import ImageDraw
dr = ImageDraw.Draw(sheet)
for i, (label, path) in enumerate(tiles):
    if not os.path.exists(path):
        print("缺文件:", path)
        continue
    im = Image.open(path).convert("RGBA")
    im.thumbnail((CELL - 12, CELL - 12), Image.LANCZOS)
    cx, cy = (i % cols) * CELL, (i // cols) * (CELL + 24)
    sheet.alpha_composite(im, (cx + 6, cy + 6))
    dr.text((cx + 8, cy + CELL + 4), label, fill=(240, 230, 255, 255))

out = os.path.join(BASE, "tools", "_shots", "_stella_pose_sheet.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
sheet.convert("RGB").save(out)
print("[对照表]", out, sheet.size)
