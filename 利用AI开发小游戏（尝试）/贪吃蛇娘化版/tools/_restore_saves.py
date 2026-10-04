# -*- coding: utf-8 -*-
"""一次性：把 TEMP 备份的存档还原回新构建的 dist\鳞光纪\saves（跑完即删）。"""
import os
import shutil
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dst = os.path.join(BASE, "dist", "鳞光纪", "saves")
src = os.path.join(tempfile.gettempdir(), "sg_lgj_saves_backup")

os.makedirs(dst, exist_ok=True)
n = 0
for root, _dirs, files in os.walk(src):
    for f in files:
        s = os.path.join(root, f)
        rel = os.path.relpath(s, src)
        d = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        n += 1
print("还原存档文件数 =", n)
for root, _d, files in os.walk(dst):
    for f in files:
        print("  ", os.path.relpath(os.path.join(root, f), dst))
