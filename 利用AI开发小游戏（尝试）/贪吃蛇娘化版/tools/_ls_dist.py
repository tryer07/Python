# -*- coding: utf-8 -*-
import os, sys, time
sys.stdout.reconfigure(encoding="utf-8")
GAME = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版"

def mt(p):
    return time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(p)))

exe = os.path.join(GAME, "dist", "鳞光纪", "鳞光纪.exe")
print("exe            ", mt(exe))
print("--- 本轮改动的源码/素材 ---")
for rel in ["scenes/battle.py", "game_logic/skills.py", "data/characters.json",
            "tools/prepare_assets.py",
            "assets/characters/sakura/cast_1.png",
            "assets/characters/sakura/cast_human_5.png",
            "assets/effects/skills/sakura_dash2_lamia.png"]:
    p = os.path.join(GAME, rel.replace("/", os.sep))
    print(f"{rel:48s} {mt(p) if os.path.exists(p) else '缺'}")
# dist 内打包进去的素材副本时间（onedir 的 _internal/assets）
ia = os.path.join(GAME, "dist", "鳞光纪", "_internal", "assets", "characters", "sakura")
print("--- dist 内 sakura 素材副本 ---")
if os.path.isdir(ia):
    for f in ("cast_1.png", "full.png"):
        p = os.path.join(ia, f)
        print(f"  {f:16s} {mt(p) if os.path.exists(p) else '缺'}")
else:
    print("  (dist/_internal/assets/characters/sakura 不存在)")
