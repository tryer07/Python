# -*- coding: utf-8 -*-
"""检查樱落释放姿势源图 vs 薄荷既有 cast 图：尺寸/模式/四角透明度。"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image

SRC = r"D:\AI图片学习包\娘化版人物形象加一些贴图参考\樱落"
MINT = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版\assets\characters\lamia_mint"

def corners(path):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()
    cs = [px[0, 0], px[w-1, 0], px[0, h-1], px[w-1, h-1]]
    # 统计完全透明像素占比
    a = im.getchannel("A")
    hist = a.histogram()
    trans = sum(hist[:8])
    return im.size, im.mode, cs, round(100.0*trans/(w*h), 1)

print("=== 薄荷既有 cast 参考 ===")
for n in ("cast_1.png", "cast_human_1.png"):
    p = os.path.join(MINT, n)
    if os.path.isfile(p):
        print(n, corners(p))

print("\n=== 樱落源姿势图 ===")
for f in sorted(os.listdir(SRC)):
    if "技能" in f and f.endswith(".png"):
        print(f, corners(os.path.join(SRC, f)))
