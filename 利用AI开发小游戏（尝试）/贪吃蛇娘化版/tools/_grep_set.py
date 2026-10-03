# -*- coding: utf-8 -*-
import io, sys
sys.stdout.reconfigure(encoding="utf-8")
p = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版\settings.py"
keys = ("SAKURA", "MARKPASSIVE", "DASH2_", "DETONATE_", "GATHER_", "BLADE_", "CHANNEL_")
for i, l in enumerate(io.open(p, encoding="utf-8")):
    if any(k in l for k in keys):
        print(i + 1, l.rstrip())
