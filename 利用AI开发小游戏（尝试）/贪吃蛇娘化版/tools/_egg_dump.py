# -*- coding: utf-8 -*-
"""dump 樱落 characters.json 的 egg_lines（详情页互动台词），供配音对照。"""
import json, io, sys
sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版\data\characters.json"
d = json.load(io.open(P, encoding="utf-8"))
chars = d if isinstance(d, list) else d.get("characters", d)
s = [c for c in chars if isinstance(c, dict) and c.get("id") == "sakura"][0]
eg = s.get("egg_lines") or {}
for region, lines in eg.items():
    print(f"== {region} ({len(lines)} 条) ==")
    for i, l in enumerate(lines):
        print(f"  [{i}] {l}")
