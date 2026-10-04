# -*- coding: utf-8 -*-
"""一次性：列月见技能特效源图 + 检查透明度/尺寸（跑完即删）。"""
import os
from PIL import Image

D = r"D:\AI图片学习包\娘化版人物形象加一些贴图参考\月见"
for root, _, files in os.walk(D):
    rel = os.path.relpath(root, D)
    if "特效" not in rel and rel != ".":
        continue
    for f in sorted(files):
        p = os.path.join(root, f)
        info = ""
        if f.lower().endswith(".png"):
            try:
                im = Image.open(p)
                has_alpha = im.mode in ("RGBA", "LA")
                corner = None
                if has_alpha:
                    a = im.convert("RGBA").getchannel("A")
                    w, h = a.size
                    corner = [a.getpixel(xy) for xy in
                              ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
                info = f" mode={im.mode} size={im.size} alpha={has_alpha} corners={corner}"
            except Exception as e:
                info = f" ERR={e}"
        print(os.path.join(rel, f), os.path.getsize(p), info)
