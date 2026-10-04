# -*- coding: utf-8 -*-
"""一次性：月见五技能VFX落位 assets/effects/skills(+_raw) + 暗底对照表（跑完即删）。"""
import os
import shutil
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = r"D:\AI图片学习包\娘化版人物形象加一些贴图参考\月见\技能特效"
DST = os.path.join(BASE, "assets", "effects", "skills")
RAW = os.path.join(DST, "_raw")
os.makedirs(RAW, exist_ok=True)

SIDS = ["luna_phase_dash", "luna_arc", "luna_pull", "luna_crescent", "luna_fullmoon"]
n = 0
for sid in SIDS:
    for form in ("lamia", "human"):
        s = os.path.join(SRC, f"{sid}_{form}.png")
        d = os.path.join(DST, f"{sid}_{form}.png")
        shutil.copyfile(s, d)
        n += 1
        sr = os.path.join(SRC, "_raw", f"{sid}_{form}_raw.png")
        if os.path.exists(sr):
            shutil.copyfile(sr, os.path.join(RAW, f"{sid}_{form}_raw.png"))
        else:
            print("缺 raw:", sr)
print("落位", n, "张 →", DST)

# 暗底对照表（10 张 2 列）
CELL = 260
cols, rows = 2, 5
sheet = Image.new("RGBA", (cols * CELL, rows * (CELL + 22)), (20, 22, 36, 255))
from PIL import ImageDraw
dr = ImageDraw.Draw(sheet)
i = 0
for sid in SIDS:
    for form in ("lamia", "human"):
        p = os.path.join(DST, f"{sid}_{form}.png")
        im = Image.open(p).convert("RGBA")
        im.thumbnail((CELL - 10, CELL - 10), Image.LANCZOS)
        cx, cy = (i % cols) * CELL, (i // cols) * (CELL + 22)
        sheet.alpha_composite(im, (cx + 5, cy + 5))
        dr.text((cx + 6, cy + CELL + 3), f"{sid}_{form}", fill=(235, 230, 255, 255))
        i += 1
out = os.path.join(BASE, "tools", "_shots", "_luna_vfx_dark.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
sheet.convert("RGB").save(out)
print("[对照表]", out, sheet.size)
