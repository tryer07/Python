# -*- coding: utf-8 -*-
"""校验樱落日语配音 mp3 是否齐备（6 条，与 egg_lines 下标对齐）。"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
SFX = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版\assets\audio\sfx"
ok = 0
for region in ("head", "body", "tail"):
    for i in (0, 1):
        name = f"voice_sakura_{region}_{i}.mp3"
        p = os.path.join(SFX, name)
        if os.path.exists(p):
            print(f"[ok] {name}  {os.path.getsize(p)//1024}KB")
            ok += 1
        else:
            print(f"[MISSING] {name}")
print(f"合计 {ok}/6")
