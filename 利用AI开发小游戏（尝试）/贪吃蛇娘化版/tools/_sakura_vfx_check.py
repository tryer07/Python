# -*- coding: utf-8 -*-
"""核对樱落技能特效：源目录 vs 游戏 assets/effects/skills/，尺寸+透明占比。"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image

SRC = r"D:\AI图片学习包\娘化版人物形象加一些贴图参考\樱落\技能特效"
GAME = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版\assets\effects\skills"

SIDS = ["sakura_dash2", "sakura_detonate", "sakura_gather", "sakura_blade", "sakura_channel"]
SPEC = {  # 验收透明区占比 lamia/human
    "sakura_dash2":   (72.8, 60.4),
    "sakura_detonate":(68.8, 57.8),
    "sakura_gather":  (46.5, 42.3),
    "sakura_blade":   (61.2, 49.3),
    "sakura_channel": (74.0, 68.8),
}

def stat(path):
    if not os.path.isfile(path):
        return None
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    a = im.getchannel("A")
    hist = a.histogram()
    trans = sum(hist[:16])
    return {"dim": (w, h), "trans_pct": round(100.0 * trans / (w * h), 1)}

print("=== 源目录 ===", SRC, "存在=", os.path.isdir(SRC))
if os.path.isdir(SRC):
    for f in sorted(os.listdir(SRC)):
        if not f.lower().endswith(".png"):
            print("  [非图]", f); continue
        print("  ", f, stat(os.path.join(SRC, f)))

print("\n=== 游戏目录 sakura_* ===")
for sid in SIDS:
    for form in ("lamia", "human"):
        name = f"{sid}_{form}.png"
        st = stat(os.path.join(GAME, name))
        spec = SPEC[sid][0 if form == "lamia" else 1]
        if st:
            print(f"  {name}: dim={st['dim']} trans={st['trans_pct']}% (规格{spec}% 差{st['trans_pct']-spec:+.1f})")
        else:
            print(f"  {name}: 缺失")
    print(f"    [base] {sid}.png 存在={os.path.isfile(os.path.join(GAME, sid + '.png'))}")
