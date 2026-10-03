# -*- coding: utf-8 -*-
import io, sys
sys.stdout.reconfigure(encoding="utf-8")
p = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版\data\characters.json"
lines = io.open(p, encoding="utf-8").read().splitlines()
start = None
for i, l in enumerate(lines):
    if '"sakura"' in l:
        start = i
    if start is not None and i >= start and i <= start + 130:
        print(i + 1, l)
    if start is not None and i > start + 130:
        break
