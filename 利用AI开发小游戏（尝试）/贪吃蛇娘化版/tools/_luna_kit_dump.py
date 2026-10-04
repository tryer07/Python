# -*- coding: utf-8 -*-
"""一次性：打印月见 kit 现状（跑完即删）。"""
import io
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw = json.load(io.open(os.path.join(BASE, "data", "characters.json"), encoding="utf-8"))
chars = raw.get("characters", raw) if isinstance(raw, dict) else raw
c = [x for x in chars if x.get("id") == "lamia_luna"][0]
print(json.dumps(c, ensure_ascii=False, indent=1))
