# -*- coding: utf-8 -*-
"""重打 onedir 包前后保护玩家存档：backup 把 dist\鳞光纪\saves 拷到
dist\_saves_backup；restore 拷回并删除备份。用法: python _saves_guard.py backup|restore"""
import os, sys, shutil
sys.stdout.reconfigure(encoding="utf-8")
GAME = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版"
SAVES = os.path.join(GAME, "dist", "鳞光纪", "saves")
BAK = os.path.join(GAME, "dist", "_saves_backup")

mode = sys.argv[1] if len(sys.argv) > 1 else "backup"
if mode == "backup":
    if os.path.isdir(SAVES):
        if os.path.isdir(BAK):
            shutil.rmtree(BAK)
        shutil.copytree(SAVES, BAK)
        n = sum(len(f) for _, _, f in os.walk(BAK))
        print(f"[backup] 已备份 {n} 个存档文件 -> dist\\_saves_backup")
    else:
        print("[backup] 无 saves 目录，跳过")
elif mode == "restore":
    if os.path.isdir(BAK):
        os.makedirs(SAVES, exist_ok=True)
        for root, _, files in os.walk(BAK):
            for f in files:
                sp = os.path.join(root, f)
                dp = os.path.join(SAVES, os.path.relpath(sp, BAK))
                os.makedirs(os.path.dirname(dp), exist_ok=True)
                shutil.copyfile(sp, dp)
        shutil.rmtree(BAK)
        n = sum(len(f) for _, _, f in os.walk(SAVES))
        print(f"[restore] 已恢复 {n} 个存档文件到 dist\\鳞光纪\\saves，备份已删")
    else:
        print("[restore] 无备份，跳过")
