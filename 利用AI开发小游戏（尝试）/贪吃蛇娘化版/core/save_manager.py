import os
import json
import time
from settings import SAVES_DIR, ENHANCE_MAX_LAYER, PARTY_MAX, HUMAN_FORM_ENHANCE_REQ


class SaveManager:
    """管理游戏存档的读写（多存档槽）。

    目录结构：
      saves/config.json        —— 机器级配置：display + settings(音量) + controls(按键绑定) + active_slot
      saves/slots/<id>.json    —— 每个存档槽的游戏进度（角色/星尘/战绩/剧情解锁…）
      saves/suspend/<key>.json —— 战斗「返回主菜单」的挂起进度，按 (模式,场景) 各自独立一份
                                  key = <mode>__<scene_id>，例：endless__neon_night、story__campus_garden
      saves/save_data.json     —— 旧版单存档；首次运行且无槽时自动导入为 slot_1

    路由约定：
      get/set("settings" | "display" | "controls")  -> config（跨槽共享）
      其余 key                          -> 当前激活槽的 self.data
    """

    DEFAULT_SAVE = {
        "slot_name": "存档",
        "created_at": 0,
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
        # ===== 剧情关卡进度 =====
        "story_unlocked": 1,      # 已解锁到第几关（1 起）
        "story_cleared": [],      # 已通关的关卡 index 列表
        "tutorial_done": False,   # 新手指引是否已看过
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

    DEFAULT_CONFIG = {
        "active_slot": None,
        "settings": {"bgm_volume": 0.7, "sfx_volume": 0.8},
        "display": {},
        "controls": {},
    }

    # 这些 key 存在机器级 config，不随存档槽切换
    # controls=按键绑定（技能/闪避热键），也做成跨槽共享的机器级偏好
    CONFIG_KEYS = ("settings", "display", "controls")

    def __init__(self):
        os.makedirs(SAVES_DIR, exist_ok=True)
        self.slots_dir = os.path.join(SAVES_DIR, "slots")
        os.makedirs(self.slots_dir, exist_ok=True)
        self.config_path = os.path.join(SAVES_DIR, "config.json")
        self.legacy_path = os.path.join(SAVES_DIR, "save_data.json")
        # 挂起进度改为「按 (模式,场景) 各存一份」，放在 saves/suspend/ 目录下。
        self.suspend_dir = os.path.join(SAVES_DIR, "suspend")
        os.makedirs(self.suspend_dir, exist_ok=True)
        # 兼容旧版：全局单份 saves/suspend.json 迁移进新目录后删除。
        self._legacy_suspend_path = os.path.join(SAVES_DIR, "suspend.json")

        self.config = self._load_config()
        self._migrate_legacy()
        self._migrate_legacy_suspend()

        # 选定激活槽：config 记录的 -> 已存在的第一个 -> 新建一个
        self.active_slot = self.config.get("active_slot")
        if not self.active_slot or not self._slot_exists(self.active_slot):
            slots = self.list_slots()
            if slots:
                self.active_slot = slots[0]["id"]
            else:
                self.active_slot = self.create_slot("存档 1", activate=False)
            self.config["active_slot"] = self.active_slot
            self._save_config()

        self.save_path = self._slot_path(self.active_slot)
        self.data = self._load_slot(self.active_slot)

    # ======================== 路径 / 基础 IO ========================
    def _slot_path(self, slot_id):
        return os.path.join(self.slots_dir, f"{slot_id}.json")

    def _slot_exists(self, slot_id):
        return bool(slot_id) and os.path.exists(self._slot_path(slot_id))

    def _load_config(self):
        cfg = json.loads(json.dumps(self.DEFAULT_CONFIG))   # 深拷贝
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._deep_update(cfg, saved)
            except (json.JSONDecodeError, IOError):
                pass
        return cfg

    def _save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def _load_slot(self, slot_id):
        path = self._slot_path(slot_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                merged = json.loads(json.dumps(self.DEFAULT_SAVE))   # 深拷贝
                self._deep_update(merged, saved)
                self._migrate(merged)
                return merged
            except (json.JSONDecodeError, IOError):
                pass
        fresh = json.loads(json.dumps(self.DEFAULT_SAVE))
        self._migrate(fresh)
        return fresh

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

        # 强化层数：老存档没有 enhance 字段，补 0；并夹到合法区间
        for cid in data.get("owned_characters", []):
            entry = cd.setdefault(cid, {"level": 1, "exp": 0, "skill_points": 0})
            if not isinstance(entry, dict):
                entry = {"level": 1, "exp": 0, "skill_points": 0}
                cd[cid] = entry
            entry["enhance"] = max(0, min(ENHANCE_MAX_LAYER, int(entry.get("enhance", 0) or 0)))

        # 剧情 / 新手指引字段：老存档没有则补默认
        data.setdefault("story_unlocked", 1)
        if not isinstance(data.get("story_cleared"), list):
            data["story_cleared"] = []
        data.setdefault("tutorial_done", False)

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
        """写回当前激活槽。"""
        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    # ======================== 战斗挂起（返回主菜单保存进度）========================
    # 不同模式 + 不同场景各自独立一份：无尽退到无尽、剧情退到剧情，
    # 同一模式下樱庭/霓虹等场景也分开存。key = <mode>__<scene_id>。
    @staticmethod
    def _suspend_key(mode, scene_id):
        """(mode, scene_id) -> 安全文件名词干。只保留字母数字下划线连字符。"""
        raw = f"{mode or 'endless'}__{scene_id or 'unknown'}"
        return "".join(c if (c.isalnum() or c in "_-") else "_" for c in raw)

    def _suspend_path(self, mode, scene_id):
        return os.path.join(self.suspend_dir, self._suspend_key(mode, scene_id) + ".json")

    def save_suspend(self, data):
        """写入战斗挂起快照（按 data 里的 mode/scene_id 定位到对应文件）。返回是否成功。"""
        if not isinstance(data, dict):
            return False
        mode = data.get("mode", "endless")
        scene_id = data.get("scene_id", "unknown")
        try:
            with open(self._suspend_path(mode, scene_id), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            return True
        except IOError:
            return False

    def load_suspend(self, mode, scene_id):
        """读指定 (模式,场景) 的挂起快照；不存在/损坏返回 None。"""
        path = self._suspend_path(mode, scene_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else None
        except (json.JSONDecodeError, IOError):
            return None

    def has_suspend(self, mode, scene_id):
        return os.path.exists(self._suspend_path(mode, scene_id))

    def clear_suspend(self, mode, scene_id):
        """丢弃指定 (模式,场景) 的挂起进度（继续开局/阵亡/通关后调用）。"""
        try:
            path = self._suspend_path(mode, scene_id)
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    def list_suspends(self):
        """返回所有挂起快照摘要 [{mode, scene_id, char_id, elapsed, level, score}, ...]。"""
        out = []
        try:
            files = os.listdir(self.suspend_dir)
        except OSError:
            files = []
        for fn in files:
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.suspend_dir, fn), "r", encoding="utf-8") as f:
                    d = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue
            if not isinstance(d, dict):
                continue
            snake = d.get("snake", {}) or {}
            out.append({
                "mode": d.get("mode", "endless"),
                "scene_id": d.get("scene_id", "unknown"),
                "char_id": d.get("char_id", "sakura"),
                "elapsed": int(d.get("elapsed", 0)),
                "level": int(snake.get("level", 1)),
                "score": int(d.get("score", 0)),
            })
        return out

    def _migrate_legacy_suspend(self):
        """把旧版全局单份 saves/suspend.json 搬进新的 saves/suspend/<key>.json，然后删除旧文件。"""
        if not os.path.exists(self._legacy_suspend_path):
            return
        try:
            with open(self._legacy_suspend_path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (json.JSONDecodeError, IOError):
            d = None
        if isinstance(d, dict):
            self.save_suspend(d)
        try:
            os.remove(self._legacy_suspend_path)
        except OSError:
            pass

    # ======================== 旧单存档迁移 ========================
    def _migrate_legacy(self):
        """若存在旧 saves/save_data.json 且尚无任何槽，导入为 slot_1「测试存档」。

        同时把旧存档里的 display / settings 提升到机器级 config。
        迁移完成后把旧文件改名为 .imported，保证只导入一次。"""
        if not os.path.exists(self.legacy_path):
            return
        if self.list_slots():
            return
        try:
            with open(self.legacy_path, "r", encoding="utf-8") as f:
                legacy = json.load(f)
        except (json.JSONDecodeError, IOError):
            return
        if not isinstance(legacy, dict):
            return

        # display / settings 提升到 config（仅当 config 里还是空默认时）
        if legacy.get("display") and not self.config.get("display"):
            self.config["display"] = legacy["display"]
        if legacy.get("settings"):
            self.config["settings"] = legacy["settings"]

        slot_data = json.loads(json.dumps(self.DEFAULT_SAVE))
        # 剔除已提升到 config 的机器级字段，其余并入槽数据
        for k, v in legacy.items():
            if k in self.CONFIG_KEYS:
                continue
            slot_data[k] = v
        slot_data["slot_name"] = legacy.get("slot_name") or "测试存档"
        slot_data.setdefault("created_at", time.time())

        slot_id = "slot_1"
        self._migrate(slot_data)
        try:
            with open(self._slot_path(slot_id), "w", encoding="utf-8") as f:
                json.dump(slot_data, f, ensure_ascii=False, indent=2)
        except IOError:
            return

        self.config["active_slot"] = slot_id
        self._save_config()
        # 旧文件改名，避免重复导入
        try:
            os.replace(self.legacy_path, self.legacy_path + ".imported")
        except OSError:
            pass

    # ======================== 多存档槽管理 ========================
    def _next_slot_id(self):
        """扫描 slots 目录，返回下一个可用的 slot_N。"""
        max_n = 0
        try:
            for fn in os.listdir(self.slots_dir):
                if fn.startswith("slot_") and fn.endswith(".json"):
                    try:
                        max_n = max(max_n, int(fn[len("slot_"):-len(".json")]))
                    except ValueError:
                        pass
        except OSError:
            pass
        return f"slot_{max_n + 1}"

    def list_slots(self):
        """返回所有存档槽摘要（按创建时间升序）。

        每项：{id, name, selected_character, story_unlocked, story_cleared,
              currency, best_score, total_runs, created_at}
        """
        out = []
        try:
            files = os.listdir(self.slots_dir)
        except OSError:
            files = []
        for fn in files:
            if not (fn.startswith("slot_") and fn.endswith(".json")):
                continue
            slot_id = fn[:-len(".json")]
            try:
                with open(os.path.join(self.slots_dir, fn), "r", encoding="utf-8") as f:
                    d = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue
            if not isinstance(d, dict):
                continue
            prog = d.get("progress", {}) or {}
            out.append({
                "id": slot_id,
                "name": d.get("slot_name", slot_id),
                "selected_character": d.get("selected_character", "sakura"),
                "story_unlocked": d.get("story_unlocked", 1),
                "story_cleared": d.get("story_cleared", []),
                "currency": d.get("currency", 0),
                "best_score": prog.get("best_score", 0),
                "total_runs": prog.get("total_runs", 0),
                "created_at": d.get("created_at", 0),
            })
        out.sort(key=lambda s: (s.get("created_at", 0), s["id"]))
        return out

    def create_slot(self, name="新存档", activate=True):
        """以 DEFAULT_SAVE 起一个新槽，标记 tutorial_done=False、story_unlocked=1。

        返回新槽 id。activate=True 时立即切换到该槽。"""
        slot_id = self._next_slot_id()
        data = json.loads(json.dumps(self.DEFAULT_SAVE))
        data["slot_name"] = name or "新存档"
        data["created_at"] = time.time()
        data["story_unlocked"] = 1
        data["story_cleared"] = []
        data["tutorial_done"] = False
        self._migrate(data)
        try:
            with open(self._slot_path(slot_id), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError:
            return None
        if activate:
            self.switch_slot(slot_id)
        return slot_id

    def delete_slot(self, slot_id):
        """删除指定槽。若删的是激活槽，则手动切到剩余的第一个
        （都没有就新建）。切走时绝不能 save() 回写已删的槽。"""
        if not self._slot_exists(slot_id):
            return False
        was_active = (self.active_slot == slot_id)
        try:
            os.remove(self._slot_path(slot_id))
        except OSError:
            return False
        if was_active:
            remaining = self.list_slots()          # 已不含被删槽
            if remaining:
                target = remaining[0]["id"]
            else:
                target = self.create_slot("存档 1", activate=False)
            # 手动切换，不走 switch_slot（避免它 self.save() 重建被删文件）
            self.active_slot = target
            self.save_path = self._slot_path(target)
            self.data = self._load_slot(target)
            self.config["active_slot"] = target
            self._save_config()
        return True

    def switch_slot(self, slot_id):
        """保存当前槽 -> 切换到目标槽 -> 重载数据 -> 回写 config.active_slot。"""
        if not self._slot_exists(slot_id):
            return False
        self.save()                       # 落盘当前槽
        self.active_slot = slot_id
        self.save_path = self._slot_path(slot_id)
        self.data = self._load_slot(slot_id)
        self.config["active_slot"] = slot_id
        self._save_config()
        return True

    @property
    def active_slot_name(self):
        return self.data.get("slot_name", self.active_slot)

    def rename_slot(self, slot_id, name):
        """重命名指定槽（激活槽直接改内存并落盘；非激活槽读写其文件）。"""
        if slot_id == self.active_slot:
            self.data["slot_name"] = name
            self.save()
            return True
        path = self._slot_path(slot_id)
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            d["slot_name"] = name
            with open(path, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, IOError):
            return False
        return True

    # ======================== 剧情进度接口 ========================
    def record_level_clear(self, level_index):
        """通关第 level_index 关：记入 story_cleared 并解锁下一关。"""
        if level_index <= 0:
            return
        cleared = self.data.setdefault("story_cleared", [])
        if level_index not in cleared:
            cleared.append(level_index)
        self.data["story_unlocked"] = max(int(self.data.get("story_unlocked", 1)),
                                          level_index + 1)
        self.save()

    def get_story_progress(self):
        return {
            "unlocked": int(self.data.get("story_unlocked", 1)),
            "cleared": list(self.data.get("story_cleared", [])),
        }

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
        if key in self.CONFIG_KEYS:
            return self.config.get(key, default)
        return self.data.get(key, default)

    def set(self, key, value):
        if key in self.CONFIG_KEYS:
            self.config[key] = value
            self._save_config()
        else:
            self.data[key] = value
            self.save()

    # ======================== 强化养成接口 ========================
    def get_enhance(self, char_id):
        """读取某角色的强化层数（缺省 0）"""
        cd = self.data.get("character_data", {})
        entry = cd.get(char_id)
        if not isinstance(entry, dict):
            return 0
        return max(0, min(ENHANCE_MAX_LAYER, int(entry.get("enhance", 0) or 0)))

    def add_enhance(self, char_id):
        """重复抽到同一角色：强化 +1 层。

        返回 (new_layer, was_maxed)：new_layer 为加层后的层数；
        was_maxed 为 True 表示加之前已满层（本次不加，调用方应返还星尘）。
        """
        cd = self.data.setdefault("character_data", {})
        entry = cd.setdefault(char_id, {"level": 1, "exp": 0, "skill_points": 0})
        cur = max(0, min(ENHANCE_MAX_LAYER, int(entry.get("enhance", 0) or 0)))
        if cur >= ENHANCE_MAX_LAYER:
            return cur, True
        entry["enhance"] = cur + 1
        return cur + 1, False

    # ======================== 出战编队 / 形态偏好接口 ========================
    def get_deploy_party(self):
        """读出战编队（owned 过滤 + 去重 + 截 PARTY_MAX）。

        老存档没有 deploy_party 键时，回退 legacy 的 selected_character 单人编队。
        """
        owned = self.data.get("owned_characters", []) or []
        party = []
        raw = self.data.get("deploy_party")
        if isinstance(raw, list):
            for cid in raw:
                if isinstance(cid, str) and cid in owned and cid not in party:
                    party.append(cid)
        if not party:
            sel = self.data.get("selected_character", "sakura")
            if sel in owned:
                party.append(sel)
        return party[:PARTY_MAX]

    def set_deploy_slot(self, slot, char_id):
        """把角色设入 1/2 号出战槽（同一角色只会留在一个槽里）。

        返回写入后的编队列表；角色未拥有时拒绝写入。
        """
        owned = self.data.get("owned_characters", []) or []
        if char_id not in owned:
            return self.get_deploy_party()
        party = [c for c in (self.data.get("deploy_party") or [])
                 if isinstance(c, str) and c in owned and c != char_id]
        if int(slot) == 1:
            party = [char_id] + party[:PARTY_MAX - 1]
        else:
            party = ([party[0]] if party else []) + [char_id]
        party = party[:PARTY_MAX]
        self.set("deploy_party", party)
        if party:
            # 兼容 legacy 单角色键：1 号位即默认出战角色
            self.set("selected_character", party[0])
        return party

    def human_form_unlocked(self, char_id):
        """人形态彩蛋是否已解锁（强化层数达标）"""
        return self.get_enhance(char_id) >= HUMAN_FORM_ENHANCE_REQ

    def get_form_pref(self, char_id):
        """读出战形态偏好：human 仅在解锁后生效，其余情况一律回退 lamia。"""
        prefs = self.data.get("form_prefs")
        pref = prefs.get(char_id, "lamia") if isinstance(prefs, dict) else "lamia"
        if pref == "human" and self.human_form_unlocked(char_id):
            return "human"
        return "lamia"

    def set_form_pref(self, char_id, form):
        """写形态偏好；未解锁时写 human 无效。返回写入后的生效值。"""
        form = form if form in ("lamia", "human") else "lamia"
        if form == "human" and not self.human_form_unlocked(char_id):
            return self.get_form_pref(char_id)
        prefs = dict(self.data.get("form_prefs") or {})
        prefs[char_id] = form
        self.set("form_prefs", prefs)
        return self.get_form_pref(char_id)

    def reset(self):
        self.data = json.loads(json.dumps(self.DEFAULT_SAVE))
        self._migrate(self.data)
        self.save()
