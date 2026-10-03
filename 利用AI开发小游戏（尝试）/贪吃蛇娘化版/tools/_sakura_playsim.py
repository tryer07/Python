# -*- coding: utf-8 -*-
"""聚焦樱落：剧情(打 Boss)+无尽各跑一局，验证五技能 handler 运行时不崩。"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import playsim

for mode, cap in (("story", 960), ("endless", 300), ("endless", 300)):
    r = playsim.run_once(mode=mode, level=1, max_seconds=cap, char_id="sakura")
    end = "通关" if r["victory"] else ("存活" if r["alive"] else "阵亡")
    print(f"[{mode}] 存活{r['time']:.1f}s 等级{r['level']} 击杀{r['kills']} "
          f"得分{r['score']} 受伤{r['hurt']} 技能数{r['skills']} 结局{end}")
print("OK: 樱落实战模拟无异常")
