# -*- coding: utf-8 -*-
"""
tools/make_unlock_save.py —— 生成「全解锁」测试存档（自动递增新槽，不覆盖旧槽）

内容验收 / 截图 / 试玩用：
  · 拥有全部角色，强化层数拉满（人形态与专属场景门槛一并解锁）
  · 剧情关卡全部解锁并记为已通关，新手指引完成
  · 星尘 / 抽卡券给到测试额度

用法：python tools/make_unlock_save.py [槽名]
存档写到 saves/slots/slot_N.json（N 取当前未占用的最小编号）。
打包 exe 想读到它：把该文件复制进 dist/鳞光纪/saves/slots/ 即可
（exe 的存档目录是 exe 同级 saves/，见 settings.SAVES_DIR）。
"""

import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from settings import ENHANCE_MAX_LAYER  # noqa: E402


def _load_json(rel):
    with open(os.path.join(BASE, rel.replace("/", os.sep)), "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "全解锁测试"
    chars = _load_json("data/characters.json")
    ids = [c.get("id") for c in chars if c.get("id")]
    levels = _load_json("data/levels.json")
    total = max((lv.get("index", i + 1) for i, lv in enumerate(levels)), default=1)

    slots_dir = os.path.join(BASE, "saves", "slots")
    os.makedirs(slots_dir, exist_ok=True)
    used = set()
    for fn in os.listdir(slots_dir):
        if fn.startswith("slot_") and fn.endswith(".json"):
            num = fn[len("slot_"):-len(".json")]
            if num.isdigit():
                used.add(int(num))
    nid = 1
    while nid in used:
        nid += 1

    data = {
        "slot_name": name,
        "created_at": time.time(),
        "player_name": "测试员",
        "currency": 999999,
        "gacha_tickets": 999,
        "owned_characters": ids,
        "selected_character": "lamia_flare" if "lamia_flare" in ids else ids[0],
        "selected_scene": "campus_garden",
        # 强化满层＝人形态 + 专属场景的门槛一并越过
        "character_data": {
            cid: {"level": 10, "exp": 0, "skill_points": 0,
                  "enhance": ENHANCE_MAX_LAYER}
            for cid in ids
        },
        "story_unlocked": total,
        "story_cleared": list(range(1, total + 1)),
        "tutorial_done": True,
        "progress": {
            "best_score": 0, "best_level": 0, "total_kills": 0,
            "total_runs": 0, "total_stardust": 0, "total_wins": 0,
            "bosses_defeated": {},
        },
    }
    out = os.path.join(slots_dir, f"slot_{nid}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[unlock-save] slot_{nid}：{len(ids)} 角色 / 剧情 {total} 关 / "
          f"强化满层 {ENHANCE_MAX_LAYER}")
    print(f"[unlock-save] -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
