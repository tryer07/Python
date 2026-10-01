import os
import json
from settings import SAVES_DIR


class SaveManager:
    """管理游戏存档的读写"""

    DEFAULT_SAVE = {
        "player_name": "玩家",
        "currency": 0,
        "gacha_tickets": 5,
        "owned_characters": ["snake_basic"],
        "selected_character": "snake_basic",
        "selected_scene": "grassland",
        "character_data": {
            "snake_basic": {
                "level": 1,
                "exp": 0,
                "skill_points": 0
            }
        },
        "settings": {
            "bgm_volume": 0.7,
            "sfx_volume": 0.8
        },
        # ===== 战斗战绩 =====
        "progress": {
            "best_score": 0,
            "best_level": 0,
            "total_kills": 0,
            "total_runs": 0,
            "total_stardust": 0,
            "total_wins": 0,
            "bosses_defeated": {}
        }
    }

    def __init__(self):
        os.makedirs(SAVES_DIR, exist_ok=True)
        self.save_path = os.path.join(SAVES_DIR, "save_data.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                merged = json.loads(json.dumps(self.DEFAULT_SAVE))   # 深拷贝
                self._deep_update(merged, saved)
                self._migrate(merged)
                return merged
            except (json.JSONDecodeError, IOError):
                pass
        return json.loads(json.dumps(self.DEFAULT_SAVE))

    # ====== 旧 ID -> 新 ID。改角色/场景命名时在这里加映射，老存档不会失效 ======
    ID_MAP = {
        "snake_basic": "sakura",
        "snake_fire": "sakura",
        "snake_ice": "lamia_tide",
        "snake_thunder": "sakura",
        "grassland": "campus_garden",
        "volcano": "neon_night",
        "ice_field": "deep_sea",
        "thunder_peak": "sakura_realm",
    }

    def _migrate(self, data):
        """把老存档里过期的东西修一修，避免存档一升级就显示不出来"""
        # 角色 ID
        sc = data.get("selected_character")
        if sc in self.ID_MAP:
            data["selected_character"] = self.ID_MAP[sc]
        owned = []
        for c in data.get("owned_characters", []):
            nc = self.ID_MAP.get(c, c)
            if nc not in owned:
                owned.append(nc)
        if "sakura" not in owned:
            owned.insert(0, "sakura")
        data["owned_characters"] = owned

        # 场景 ID
        ss = data.get("selected_scene")
        if ss in self.ID_MAP:
            data["selected_scene"] = self.ID_MAP[ss]

        # 角色数据表也跟一下
        cd = data.get("character_data", {})
        for old, new in self.ID_MAP.items():
            if old in cd and new not in cd:
                cd[new] = cd.pop(old)

    @staticmethod
    def _deep_update(base, incoming):
        """递归合并，这样老存档缺了新字段也不会丢数据"""
        for k, v in incoming.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                SaveManager._deep_update(base[k], v)
            else:
                base[k] = v
        return base

    def save(self):
        with open(self.save_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ======================== 战斗结算接口 ========================
    def add_stardust(self, amount):
        """把一局拿到的星尘存进账号"""
        if amount <= 0:
            return
        self.data["progress"]["total_stardust"] += amount
        self.data["currency"] += amount
        self.save()

    def record_run(self, score, level, kills):
        """记录一局战绩"""
        p = self.data["progress"]
        p["total_runs"] += 1
        p["total_kills"] += kills
        p["best_score"] = max(p["best_score"], score)
        p["best_level"] = max(p["best_level"], level)
        self.save()

    def record_victory(self, scene_id, score, level, kills, time=0):
        """记录一次通关（击败 Boss）。旧存档缺的字段由 _deep_update 自动补齐。"""
        p = self.data["progress"]
        p.setdefault("total_wins", 0)
        p.setdefault("bosses_defeated", {})
        p["total_runs"] += 1
        p["total_wins"] += 1
        p["total_kills"] += kills
        p["best_score"] = max(p["best_score"], score)
        p["best_level"] = max(p["best_level"], level)
        bd = p["bosses_defeated"]
        bd[scene_id] = bd.get(scene_id, 0) + 1
        self.save()

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def reset(self):
        self.data = self.DEFAULT_SAVE.copy()
        self.save()