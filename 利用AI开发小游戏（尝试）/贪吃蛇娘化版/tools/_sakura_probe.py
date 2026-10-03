# -*- coding: utf-8 -*-
"""探针：验证樱落五技能事件构造、CD、数值展示无异常。"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game_logic.skills import SkillEngine

eng = SkillEngine()
eng.load_kit("sakura")
print("role=", eng.role, "element=", eng.element)
print("passive_kind=", eng.passive_kind, "passive_kinds=", eng.passive_kinds)
print("has_mark_passive=", eng.has_mark_passive)
for a in eng.actives:
    sid = a["id"]
    stype = eng._type_of(sid)
    cd0 = eng.cooldown_at(sid, 0, 0.0)
    cdmax = eng.cooldown_at(sid, 5, 0.0)
    ev = eng._build_event(stype, (100, 100), 0)
    print("\n== key%s %s (type=%s) CD lv0=%.2f lv5=%.2f" % (a["key"], sid, stype, cd0, cdmax))
    print("   ev keys:", sorted(ev.keys()))
    print("   stat_lines:", eng.stat_lines(sid, 0))
