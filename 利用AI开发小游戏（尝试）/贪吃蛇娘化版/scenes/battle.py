# -*- coding: utf-8 -*-
"""
scenes/battle.py —— 战斗场景（大地图自由移动动作生存）

一局的完整过程：
    WASD 自由移动 → 自动普攻索敌 → 左键护盾 → 1-5 主动技能 → 捡道具升级选卡
    → 小怪越来越多越来越硬 → 生存到阈值触发 Boss → 击败结算 / 阵亡结算

坐标系（重要）：
    · 世界尺寸 = WORLD_SCREENS_X * 窗口宽 × WORLD_SCREENS_Y * 窗口高（世界像素）
    · 所有实体 pos 都是世界像素；绘制时用 wx()/wy() 减去摄像机 self.cam
    · 标注 (设计像素) 的常量按 self.S 缩放成当前分辨率的真实像素
    · Boss 复用 boss.py：pos_cells 用「世界格」（世界像素 / CELL），
      ctx 传 world_cols / world_rows / CELL，Boss 弹幕天然运作在世界坐标
"""

import json
import math
import os
import random
import time

import pygame

import settings as S
from core.audio_manager import AudioManager
from core.scene import Scene
from game_logic.entities import Drop, EliteMob, Mob, PlayerBullet, SnakeGirl
from game_logic.boss import Boss, Projectile, boss_trigger_met, load_boss_cfg
from game_logic.skills import SkillEngine, skill_info
from core.controls import describe_shield, describe_key
from ui.button import Button
from ui.keybind_panel import KeybindPanel
from settings import (
    COLOR_ACCENT, COLOR_ACCENT_DARK, COLOR_BG, COLOR_BG_LIGHT, COLOR_DANGER,
    COLOR_EXP, COLOR_GOLD, COLOR_GOOD, COLOR_HP, COLOR_TEXT, COLOR_TEXT_DIM,
    FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_SUBTITLE, FONT_SIZE_TITLE,
)

# 数字键 1-6 -> 技能键位
_NUM_KEYS = {
    pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3,
    pygame.K_4: 4, pygame.K_5: 5, pygame.K_6: 6,
}

# 元素 -> 弹丸贴图文件名（普攻/技能飞行物按元素 blit 缓存贴图）
_EL_BULLET = {
    "樱": "sakura", "风": "wind", "水": "water",
    "火": "fire", "星": "star", "月": "moon",
}

# 元素 -> 远程普攻的弹丸光晕/枪口/火星拖尾主色。远程三段普攻原为樱落专用、
# 主色硬编码成樱粉；绯焰(火)接入后按活跃元素取色，缺省回退樱粉——只有樱落
# 配 ranged 时行为完全不变，火/水等各自拿到对味的主色（火=橙红，同其技能配色）。
_EL_RANGED_COLOR = {
    "樱": (255, 190, 215), "火": (255, 140, 80), "水": (120, 200, 255),
    "风": (150, 240, 190), "星": (190, 150, 255), "月": (200, 210, 255),
}

# 旋转贴图查表档数：连续自旋（阵风/风实体/弹丸/技能贴图）每帧角度都在变，
# 若每帧 pygame.transform.rotate/rotozoom 会整张图重采样，是技能掉帧主因。
# 把角度吸附到这么多档位（每 7.5°一档，与 AssetManager.ROT_STEPS 一致），
# 只在首次遇到某档时转一次并缓存，之后查表 blit，肉眼无差别。
_ROT_STEPS = 48
# rotozoom 缩放查表档数：缩放吸附到 1/这么多档，配合角度档共同限缓存条目数。
_RZ_SCALE_STEPS = 16

# 技能释放动作：释放成功后把 idle 立绘交叉淡入淡出成对应技能键的姿势立绘。
# 姿势立绘在 enter/切人/resize 时预缩放缓存（_prewarm_cast_poses），
# 运行时只查表 + blit，不产生任何每帧重采样。
CAST_POSE_DUR = 0.62      # 姿势总时长（秒）
CAST_POSE_IN = 0.10       # 淡入段
CAST_POSE_OUT = 0.18      # 淡出段
CAST_POSE_H_MULT = 1.15   # 姿势立绘高 / idle 立绘高
ATK_POSE_IN = 0.06        # 普攻姿势淡入段（秒）：跟爪风节拍的快淡入
ATK_POSE_OUT = 0.12       # 普攻姿势淡出段（秒）：收尾后摇内收完（姿势含风环等特效，
                          # 放大一点人物本体才与 idle 同尺度，衔接不跳变）
_SHAKE_PX_DIV = 14.0      # 规格书「震屏像素」→ shake 值换算：draw 端位移 = shake × s(14)


def _seg_dist(px, py, x1, y1, x2, y2):
    """点 (px,py) 到线段 (x1,y1)-(x2,y2) 的最短距离。冲锋路径伤害用。"""
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 <= 1e-6:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / L2
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (x1 + dx * t), py - (y1 + dy * t))


class BattleScene(Scene):
    """战斗场景（自由移动版）"""

    # ================================================================ 生命周期
    def enter(self):
        self.assets = self.game.assets
        self.keybind_panel = KeybindPanel(self.game)   # 暂停菜单内改键浮层复用
        self._setup_view()
        susp = getattr(self.game, "pending_suspend", None)
        run = getattr(self.game, "pending_run", None)
        if susp and isinstance(run, dict) and susp.get("party"):
            # v2 快照带编队：让 reset 先按快照的编队人数建基础局
            run["party"] = [m.get("char_id") for m in susp["party"]
                            if isinstance(m, dict) and m.get("char_id")]
        self.reset()
        # 「暂时离开」留下的挂起进度：reset 建好基础局后整体覆盖还原
        if susp:
            self.game.pending_suspend = None
            try:
                self._apply_suspend(susp)
            except Exception:
                self.reset()      # 快照损坏就开新局，绝不崩

    def on_resize(self):
        """拖拽改变窗口大小：重算字体/世界尺寸/摄像机，绝不重置战斗进度"""
        self._bg_surf = None          # 背景缓存失效（世界尺寸变了）
        self._setup_view()
        self._clamp_cam()
        self._prewarm_cast_poses()    # 缩放变了，姿势缓存重建（加载期一次性开销）
        self._prewarm_atk_poses()

    def _setup_view(self):
        """按当前窗口尺寸/缩放重算字体、世界几何与暂停按钮布局"""
        # 绘制缓存：小装饰面/字体渲染/全屏画布都随缩放变化，resize 后整体失效
        self._surf_cache = {}
        self._text_cache = {}      # 静态文字面 / 折行结果 / 悬停介绍面板
        self._otxt_cache = {}      # 飘字描边面（单独一份，见 _outlined_text）
        self._ov_surf = None
        self.f_tiny = self.assets.get_font(self.s(FONT_SIZE_SMALL - 2))
        self.f_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))
        self.f_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.f_sub = self.assets.get_font(self.s(FONT_SIZE_SUBTITLE))
        self.f_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)

        # ---- 世界几何：一律现取 S.XXX，避免导入快照幽灵 bug ----
        self.CELL = S.CELL_SIZE
        self.world_w = max(self.W, S.WORLD_SCREENS_X * self.W)
        self.world_h = max(self.H, S.WORLD_SCREENS_Y * self.H)
        self.world_cols = self.world_w / max(1, self.CELL)
        self.world_rows = self.world_h / max(1, self.CELL)

        # ---- 暂停菜单按钮（居中竖排）----
        bw, bh = self.s(300), self.s(58)
        bx = self.W // 2 - bw // 2
        by = self.H // 2 - self.s(96)
        gap = bh + self.s(14)
        self.resume_btn = Button("继续  (ESC)", bx, by, bw, bh,
                                 font_size=self.s(FONT_SIZE_BODY),
                                 on_click=self._toggle_pause)
        self.restart_btn = Button("重开本局", bx, by + gap, bw, bh,
                                  font_size=self.s(FONT_SIZE_BODY),
                                  on_click=self.reset)
        self.rebind_btn = Button("按键设置", bx, by + gap * 2, bw, bh,
                                 font_size=self.s(FONT_SIZE_BODY),
                                 on_click=self._open_rebind)
        self.quit_btn = Button("返回主菜单", bx, by + gap * 3, bw, bh,
                               font_size=self.s(FONT_SIZE_BODY),
                               on_click=self._ask_quit_menu)

        # ---- 「返回主菜单」二次确认浮层的按钮（告知进度已保存）----
        qw, qh = self.s(240), self.s(56)
        qgap = self.s(24)
        qy = self.H // 2 + self.s(60)
        self.quit_yes_btn = Button("保存并返回", self.W // 2 - qw - qgap // 2, qy,
                                   qw, qh, font_size=self.s(FONT_SIZE_SMALL),
                                   on_click=self._confirm_quit_menu)
        self.quit_no_btn = Button("取消", self.W // 2 + qgap // 2, qy,
                                  qw, qh, font_size=self.s(FONT_SIZE_SMALL),
                                  on_click=self._cancel_quit_menu)

        # ---- 暂停内「按键设置」浮层的按钮 ----
        self.keybind_panel_w = min(self.s(660), int(self.W * 0.86))
        self.keybind_panel_x = self.W // 2 - self.keybind_panel_w // 2
        self.keybind_panel_y = self.H // 2 - self.s(250)
        kbtn_y = self.keybind_panel_y + self.keybind_panel.height(self.s) + self.s(10)
        self.rebind_restore_btn = Button(
            "恢复默认按键", self.W // 2 - self.s(320), kbtn_y,
            self.s(290), self.s(52), font_size=self.s(FONT_SIZE_SMALL),
            on_click=self._rebind_restore)
        self.rebind_back_btn = Button(
            "返回 (ESC)", self.W // 2 + self.s(30), kbtn_y,
            self.s(290), self.s(52), font_size=self.s(FONT_SIZE_SMALL),
            on_click=self._close_rebind)

    def exit(self):
        self.game.input_capture = False

    def wants_movement_keys(self):
        """只有「进行中」才占用方向键（移动）；暂停 / 结算 / 选卡时让给音量热键。"""
        return not self.paused and not self.finished and not self.card_overlay

    # ================================================================ 重置
    def reset(self):
        run = getattr(self.game, "pending_run", None) or {}
        # 恢复挂起局时编队由快照指定（run["party"] / run["char_id"]），新局才用出战编队
        party_ids = self._resolve_party(run)
        char_id = party_ids[0]

        # ---- 本局模式：剧情 / 无尽，由关卡选择场景写入 game.pending_run ----
        self.mode = run.get("mode", "endless")
        self.level_cfg = None
        self.level_index = 0
        if self.mode == "story":
            self.level_index = int(run.get("level", 1))
            self.level_cfg = self._load_level(self.level_index)
            if self.level_cfg:
                self.scene_id = self.level_cfg.get("scene", "campus_garden")
                self.level_index = int(self.level_cfg.get("index", self.level_index))
            else:
                self.scene_id = self.game.save_manager.get(
                    "selected_scene", "campus_garden")
        else:
            self.scene_id = run.get("scene") or self.game.save_manager.get(
                "selected_scene", "campus_garden")
        self.snake_name, self.snake_rarity = self._char_label(char_id)
        # 场景难度/敌人贴图与全身立绘的默认值（_load_skin 会按场景/角色覆写）
        self.char_full = ""
        self.scene_density = S.SCENE_DENSITY_DEFAULT
        self.scene_hp_growth = S.SCENE_HP_GROWTH_DEFAULT
        self.scene_mob_sprite = ""
        self.scene_elite_sprite = ""
        self.ward_t = 0.0                  # 月元素自身减伤剩余秒
        self._load_skin(char_id, self.scene_id)

        # ---- 战斗 BGM 在 reset() 末尾统一由 _setup_bgm() 接管（需要 elapsed 已初始化）----

        # ---- 出战编队：1-2 名蛇娘，玩家只操作「活跃成员」，其余在场外待命 ----
        self.party = [self._make_member(cid, i) for i, cid in enumerate(party_ids)]
        self.active_idx = 0
        self.switch_cd = 0.0
        # 开局一次性提示：双人局教「切人」，人形态已解锁的再教「V 切形态」
        self.switch_hint_t = 6.0 if (len(self.party) > 1 or any(
            self._form_available(m) for m in self.party)) else 0.0
        # 近战数据驱动规格 / 顿帧计时：必须在 _activate 之前初始化——
        # _activate 会按活跃成员把 melee_cfg 指向其规格块，之后不能再被覆盖。
        self.melee_cfg = None
        self.ranged_cfg = None
        self.ranged_engaged = False
        self.hitstop_t = 0.0
        # 星璃·连星成轨场景级持久态：须在首次 _activate 之前存在
        # （_activate 会按出战被动计算 stella_mark_supply）。
        # 星位/星轨/引力井/星座窗口同潮汐水域不随切人消失，随各自计时自然到期。
        self.stella_nodes = []           # 星位：[{"x","y","t","max_t","ph"}]
        self.stella_links = []           # 星轨：[{"a","b","t","max_t","tick","dmg","const"}]
        self.stella_wells = []           # 引力井：[{"x","y","r","t","max_t","strength","stun","hit","fx"}]
        self.stella_const_t = 0.0        # 星图共鸣余韵：新落星位自动连线窗口剩余秒
        self.stella_mark_supply = False  # 「星之标记」供料模式（满层落星位不自爆）
        self._activate(0, teleport=False)

        self.skill_toast = []
        self._cards_cache = None
        # 职业系数（_activate 按活跃成员 role 覆写）
        self.role = "hybrid"
        self.role_armor = 0.0
        self.role_skilldmg = 1.0
        # dash2 二段位移的待引爆元素实体 / channel 吟唱读条（均为场景级瞬态）
        self.dash2 = None
        self.channel = None
        self.cast_pose = None          # 技能释放动作（见 _start_cast_pose）
        self.atk_combo = None          # 近战爪风连击（见 _auto_attack_melee）
        self.gusts = []          # 旋风引：飞行中的阵风实体（风系聚怪）
        # 樱落·种花闭环持续态：花圃区域 / 花期增益 / 花护层 / 催放延迟二次跳
        self.sakura_beds = []
        self.sakura_kaki_t = 0.0
        self.sakura_guard = 0
        self.sakura_delay = []
        # 绯焰·灼烧引爆闭环持续态：燃径火径区域 / 引信烙印 / 缭焰火环
        # （余烬层挂在 Mob/Boss 实体上；火径同潮汐水域不随切人消失）
        self.flare_trails = []
        self.flare_fuses = []
        self.flare_ring_t = 0.0
        self.flare_ring_amp = 0.0
        self.fx_sprites = []     # 一次性技能贴图特效（引爆/爆发等，缺图自动回退程序化 VFX）
        # 鼓舞(rally)增益：key5 技能释放后短时提升攻击/攻速，挂在场景上
        self.rally_t = 0.0
        self.rally_atk = 1.0
        self.rally_atkspd = 1.0
        self.rally_armor = 0.0           # 鼓舞满级：增益期内额外减伤（0=无）
        self.rally_color = (255, 200, 220)   # 鼓舞增益期间脚下光环的配色
        self.regen_acc = 0.0             # 生命再生卡的小数累加
        self._ls_acc = 0.0               # 吸血回血的飘字节流累加
        # ---- 潮汐·切人联动场景级持久态（_activate 切人不清，随各自计时自然到期）----
        self.zones = []                  # 涌潮水域：[{"x","y","r","t","max_t","enemy_slow"}]
        self.contract = None             # 潮汐契约：{"t","dmg","cd","inner_cd"}
        self.domain = None               # 潮汐领域：{"t","wet","slow"}
        self.handoff_holder = None       # 潮汐交接盾的持有成员（切走时转移给登场者）
        self.handoff_transfer = S.TIDE_HANDOFF_TRANSFER  # 交接盾转移比例（满级 0.75）
        self.landing_t = 0.0             # 踏浪登场增益剩余秒（移速+减伤）

        # ---- 实体容器 ----
        self.drops = []
        self.mobs = []
        self.bullets = []          # 玩家普攻 / 专属主动弹
        self.projectiles = []      # Boss 弹幕
        self.particles = []
        self.floaters = []
        self.effects = []          # 技能特效（环 / 光束 / 扇形 / 拖影）

        # ---- 计时 / 计分 ----
        self.elapsed = 0.0
        self.score = 0
        self.stardust = 0
        self.kills = 0
        self.mob_spawn_timer = 1.4
        self.item_spawn_timer = S.ITEM_SPAWN_INTERVAL
        self.shake = 0.0
        self.flash = 0.0
        self.finished = False
        self.paused = False
        self.rebind_open = False     # 暂停菜单里的「按键设置」浮层是否展开
        self.quit_confirm = False    # 暂停菜单里「返回主菜单」二次确认是否展开
        self.victory = False

        # ---- 升级选卡：card_queue 记录「还要为哪位成员选一张」----
        self.card_queue = []
        self.card_overlay = None
        self.card_rects = []

        # ---- Boss 战状态 ----
        # 剧情模式：撑满 story_duration 触发 Boss；无尽模式：无 Boss 纯生存。
        self.story_duration = float(S.STORY_DURATION)
        self.elite_interval = float(S.ELITE_INTERVAL)
        if self.level_cfg:
            self.story_duration = float(self.level_cfg.get("duration", S.STORY_DURATION))
            self.elite_interval = float(
                self.level_cfg.get("elite_interval", S.ELITE_INTERVAL))
        if self.mode == "story":
            self.boss_cfg = load_boss_cfg(self.scene_id)
            if self.boss_cfg:
                self.boss_cfg = dict(self.boss_cfg)
                self.boss_cfg["trigger"] = {"mode": "time",
                                            "value": self.story_duration}
        else:
            self.boss_cfg = None
        self.boss = None
        self.boss_spawned = False
        self.boss_hit_cd = 0.0
        self.boss_banner = 0.0
        # ---- 剧情节奏计时 ----
        self.elite_timer = self.elite_interval
        self.elites_spawned = 0

        # ---- 新手指引：当前槽未看过时，开局按序播放定时浮层 ----
        self.tutorial_hints = list(getattr(S, "TUTORIAL_HINTS", []))
        self.tutorial_index = 0
        self.tutorial_timer = 0.0
        try:
            done = bool(self.game.save_manager.get("tutorial_done", False))
        except Exception:
            done = True
        self.tutorial_active = (not done) and bool(self.tutorial_hints)

        # ---- 摄像机 ----
        self.cam = [self.snake.pos[0] - self.W / 2, self.snake.pos[1] - self.H / 2]
        self._clamp_cam()
        self._bg_surf = None

        # 开局先撒一批道具，免得前期空手
        for _ in range(6):
            self._spawn_item(near_player=False)

        # ---- 战斗 BGM：场景轮换 + 无尽后期随机曲库，后台预载 + 交叉淡入淡出 ----
        self._setup_bgm()

    # ================================================================ BGM 轮换调度
    def _setup_bgm(self):
        """按当前模式/场景准备轮换曲单，后台预载，并按已存活时长选当前曲。"""
        audio = self.game.audio
        if self.scene_id in AudioManager.SCENE_BGM_IDS:
            self._bgm_rot = AudioManager.scene_rotation(self.scene_id)
        else:
            self._bgm_rot = ["battle"]
        self._bgm_late_pool = AudioManager.endless_pool()
        self._bgm_index = 0
        self._bgm_late = False
        self._bgm_last = None
        # 后台预载轮换曲（无尽额外预载后期曲库）+ Boss/结算曲，切歌时已就绪不卡顿。
        # 队列 FIFO：轮换曲在前（开局马上要用），Boss/结算在后（数分钟后才触发）。
        names = list(self._bgm_rot)
        if self.mode == "endless":
            names += self._bgm_late_pool
        names += ["boss", "gameover"]
        audio.preload_bgm_many(names)
        self._play_initial_bgm()

    def _play_initial_bgm(self):
        """按已存活时长选开局该放哪首，并把切歌倒计时对齐到下一个 3 分钟边界。"""
        audio = self.game.audio
        interval = S.BGM_SWITCH_INTERVAL
        if self.mode == "endless" and self.elapsed >= S.BGM_ENDLESS_LATE_START:
            self._bgm_late = True
            name = random.choice(self._bgm_late_pool)
        else:
            self._bgm_late = False
            self._bgm_index = int(self.elapsed // interval) % len(self._bgm_rot)
            name = self._bgm_rot[self._bgm_index]
        self._bgm_last = name
        self._bgm_timer = interval - (self.elapsed % interval)
        if self._bgm_timer <= 0:
            self._bgm_timer = interval
        audio.play_bgm(name, fade_ms=S.BGM_FADE_MS)

    def _advance_bgm(self):
        """切下一首：剧情/无尽前期按场景轮换，无尽 15 分钟后从曲库随机挑。"""
        audio = self.game.audio
        if self.mode == "endless":
            if not self._bgm_late and self.elapsed >= S.BGM_ENDLESS_LATE_START:
                self._bgm_late = True
            if self._bgm_late:
                pool = [n for n in self._bgm_late_pool if n != self._bgm_last]
                name = random.choice(pool or self._bgm_late_pool)
                self._bgm_last = name
                audio.play_bgm(name, fade_ms=S.BGM_SWITCH_MS)
                return
        self._bgm_index = (self._bgm_index + 1) % len(self._bgm_rot)
        name = self._bgm_rot[self._bgm_index]
        self._bgm_last = name
        audio.play_bgm(name, fade_ms=S.BGM_SWITCH_MS)

    def _update_bgm(self, dt):
        """每帧推进切歌倒计时（Boss 登场/结算时不抢，交给 boss/gameover BGM）。"""
        if self.boss is not None or self.finished:
            return
        self._bgm_timer -= dt
        if self._bgm_timer <= 0:
            self._bgm_timer += S.BGM_SWITCH_INTERVAL
            self._advance_bgm()

    # ================================================================ 外观 / 配置
    def _char_label(self, char_id):
        try:
            path = os.path.join(S.DATA_DIR, "characters.json")
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            items = raw.get("characters", raw) if isinstance(raw, dict) else raw
            for c in items:
                if c.get("id") == char_id:
                    name = c.get("name", char_id)
                    rarity = c.get("rarity", "")
                    return name, f"{name} · {rarity}" if rarity else name
        except (IOError, json.JSONDecodeError, AttributeError, TypeError):
            pass
        return char_id, char_id

    def _load_level(self, index):
        """按关卡序号读 data/levels.json 配置，取不到返回 None。"""
        try:
            path = os.path.join(S.DATA_DIR, "levels.json")
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            items = raw.get("levels", raw) if isinstance(raw, dict) else raw
            for lv in items:
                if isinstance(lv, dict) and int(lv.get("index", -1)) == int(index):
                    return lv
        except (IOError, json.JSONDecodeError, AttributeError, TypeError, ValueError):
            pass
        return None

    def _load_skin(self, char_id, scene_id):
        """读当前活跃成员的外观与场景背景（成员皮肤由 _member_skin 统一取）。"""
        default_bg = "backgrounds/campus_garden.png"

        char = self._find_in_json("characters.json", "characters", char_id)
        rarity = char.get("rarity", "")
        if rarity:
            self.snake_rarity = f"{self.snake_name} · {rarity}"
        skin = self._member_skin(char_id)
        self.char_head = skin["head"]
        self.char_body = skin["body"]
        self.char_tail = skin["tail"]
        self.char_human = skin["human"]
        self.char_full = skin["full"]

        scene = self._find_in_json("scenes.json", "scenes", scene_id)
        self.scene_bg = scene.get("bg") or default_bg
        # 场景渐进难度：后解锁的场景刷怪更密、怪血成长更快（读 scenes.json）
        try:
            self.scene_density = float(scene.get("enemy_density",
                                                 S.SCENE_DENSITY_DEFAULT))
            self.scene_hp_growth = float(scene.get("hp_growth",
                                                   S.SCENE_HP_GROWTH_DEFAULT))
        except (TypeError, ValueError):
            self.scene_density = S.SCENE_DENSITY_DEFAULT
            self.scene_hp_growth = S.SCENE_HP_GROWTH_DEFAULT
        self.scene_mob_sprite = scene.get("mob_sprite") or ""
        self.scene_elite_sprite = scene.get("elite_sprite") or ""

    @staticmethod
    def _cast_pose_paths(char):
        """技能释放姿势立绘路径（形态 -> {技能键: 相对路径}），缺图不进表。

        约定：assets/characters/{角色 id}/cast_{键}.png（蛇形态）与
        cast_human_{键}.png（人形态），键 = 主动技能 key(1-5)。
        只有薄荷配了全套；其它角色返回空表，绘制路径零开销零影响。
        """
        cid = char.get("id") or ""
        out = {"lamia": {}, "human": {}}
        if not cid:
            return out
        for k in range(1, 6):
            for form, name in (("lamia", f"cast_{k}.png"),
                               ("human", f"cast_human_{k}.png")):
                rel = f"characters/{cid}/{name}"
                if os.path.exists(os.path.join(S.ASSETS_DIR,
                                               rel.replace("/", os.sep))):
                    out[form][k] = rel
        return out

    @staticmethod
    def _atk_pose_paths(char):
        """普攻连击姿势立绘路径（形态 -> {连击段: 相对路径}），缺图不进表。

        约定：assets/characters/{角色 id}/atk_{1,3}.png（蛇形态）与
        atk_human_{1,3}.png（人形态）；第 2 段由绘制端镜像第 1 段得到。
        只有薄荷配了图；其它角色返回空表，普攻照旧走弹丸、零影响。
        """
        cid = char.get("id") or ""
        out = {"lamia": {}, "human": {}}
        if not cid:
            return out
        for k in (1, 3):
            for form, name in (("lamia", f"atk_{k}.png"),
                               ("human", f"atk_human_{k}.png")):
                rel = f"characters/{cid}/{name}"
                if os.path.exists(os.path.join(S.ASSETS_DIR,
                                               rel.replace("/", os.sep))):
                    out[form][k] = rel
        return out

    def _member_skin(self, char_id):
        """某角色的全部立绘资源路径（蛇形态三件 + 人形态全身 + 释放姿势）。"""
        char = self._find_in_json("characters.json", "characters", char_id)
        return {
            "head": char.get("head") or "characters/sakura/head.png",
            "body": char.get("body_seg") or "characters/sakura/body_seg.png",
            "tail": char.get("tail_tip") or "characters/sakura/tail_tip.png",
            "human": char.get("full_human") or "",
            "full": char.get("full") or "",
            "cast": self._cast_pose_paths(char),
            "atk": self._atk_pose_paths(char),
            "melee": char.get("melee") or None,
            "ranged": char.get("ranged") or None,
        }

    # ================================================================ 出战编队
    def _resolve_party(self, run):
        """本局出战编队（1-2 人）：run["party"] → run["char_id"] → 存档编队。"""
        sm = self.game.save_manager
        owned = sm.get("owned_characters", []) or []
        ids = run.get("party")
        if not ids and run.get("char_id"):
            ids = [run["char_id"]]
        if not ids:
            try:
                ids = sm.get_deploy_party()
            except Exception:
                ids = None
        if not ids:
            ids = [sm.get("selected_character", "sakura")]
        out = []
        for cid in ids:
            if not isinstance(cid, str) or cid in out:
                continue
            if owned and cid not in owned:
                continue
            out.append(cid)
        return out[:S.PARTY_MAX] or ["sakura"]

    @staticmethod
    def _base_card_stats():
        """局内属性副本的初始值（升级选卡直接改这份，再乘强化养成乘区）。"""
        return {"atk": 1.0, "speed": 1.0, "atkspd": 1.0,
                "cdr": 0.0, "pickup": 1.0,
                "exp": 1.0, "armor": 0.0,
                "regen": 0.0, "skilldmg": 1.0, "range": 1.0,
                "lifesteal": 0.0, "shield": 0.0}

    def _make_member(self, char_id, index):
        """构造一名出战成员：本体 + 技能包 + 强化乘区 + 皮肤 + 局内属性副本。"""
        name, rarity = self._char_label(char_id)
        snake = SnakeGirl(char_id, start_pos=(self.world_w / 2, self.world_h / 2))
        snake.radius = self.s(S.PLAYER_RADIUS)
        snake.seg_len = self.s(S.BODY_SEG_LEN)
        snake._init_path()
        snake.facing_update()
        snake.on_level_up_cb = self._on_level_up
        skills = SkillEngine()
        skills.load_kit(char_id)
        # 职业血量系数：坦克血厚、法师血薄（乘在 HP_MAX 上，再进强化/选卡乘区）
        role = getattr(skills, "role", "hybrid") or "hybrid"
        snake.hp_max = max(1, int(round(S.HP_MAX * S.ROLE_HP_MULT.get(role, 1.0))))
        # 强化养成乘区：按该角色强化层数叠加（无氪金、玩久可满的公平养成）
        layer = self.game.save_manager.get_enhance(char_id)
        enh = {
            "atk": 1.0 + layer * S.ENHANCE_ATK_PER_LAYER,
            "speed": 1.0 + layer * S.ENHANCE_SPEED_PER_LAYER,
            "atkspd": 1.0 + layer * S.ENHANCE_ATKSPD_PER_LAYER,
            "pickup": 1.0 + layer * S.ENHANCE_PICKUP_PER_LAYER,
            "cdr": layer * S.ENHANCE_CDR_PER_LAYER,
            "hp": 1.0 + layer * S.ENHANCE_HP_PER_LAYER,
        }
        m = {
            "char_id": char_id, "index": index,
            "name": name, "rarity": rarity,
            "form": self.game.save_manager.get_form_pref(char_id),
            "snake": snake, "skills": skills, "skill_lv": skills.levels,
            "passive_kind": skills.passive_kind, "role": role,
            "card_stats": self._base_card_stats(),
            "enh": enh, "skin": self._member_skin(char_id),
            "hp_base": int(snake.hp_max),   # 未经强化/选卡加成的原始上限
            "hp_bonus": 0,                  # 生命卡累计加成
        }
        self._rebuild_member_hp(m)
        snake.hp = float(snake.hp_max)
        return m

    @staticmethod
    def _rebuild_member_hp(m):
        """成员生命上限 = 原始上限 × 强化乘区 + 生命卡加成。"""
        base = int(round(m["hp_base"] * m["enh"]["hp"]))
        m["snake"].hp_max = max(1, base + int(m["hp_bonus"]))

    def _rebuild_stats(self):
        """活跃成员最终属性 = 局内卡牌属性 × 自身强化乘区（+ 御风被动）。"""
        m = self.party[self.active_idx]
        c, e = m["card_stats"], m["enh"]
        self.stats = {
            "atk": c["atk"] * e["atk"],
            "speed": c["speed"] * e["speed"],
            "atkspd": c["atkspd"] * e["atkspd"],
            "cdr": min(0.75, c["cdr"] + e["cdr"]),
            "pickup": c["pickup"] * e["pickup"],
            "exp": c["exp"], "armor": c["armor"],
            "regen": c["regen"], "skilldmg": c["skilldmg"],
            "range": c["range"], "lifesteal": c["lifesteal"],
            "shield": c.get("shield", 0.0),
        }
        # 常驻被动落地：御风(移速+) 直接进 stats，其余在对应结算处按 passive_kind 生效
        if m["passive_kind"] == "speed":
            self.stats["speed"] *= S.PASSIVE_GALE_SPEED

    def _activate(self, idx, teleport=True):
        """把活跃视图指向 idx 号成员（本体/技能/属性/皮肤/名字全部重指向）。"""
        prev = self.party[self.active_idx] if self.party else None
        self.active_idx = max(0, min(int(idx), len(self.party) - 1))
        m = self.party[self.active_idx]
        if teleport and prev is not None and prev is not m:
            # 待命者顶替上场：站到前任的位置、继承朝向，尾迹重新铺开
            sn, pn = m["snake"], prev["snake"]
            sn.pos = list(pn.pos)
            sn.aim_dir = list(pn.aim_dir)
            sn.move_dir = list(pn.move_dir)
            sn.atk_timer = min(sn.atk_timer, 0.1)
            sn._init_path()
        sn = m["snake"]
        sn.facing_update()
        self.snake = sn
        self.skills = m["skills"]
        self.skill_lv = m["skill_lv"]   # 局内技能强化等级（与引擎共享同一字典）
        self.passive_kind = m["passive_kind"]
        # 切换成员：清掉上一位遗留的二段位移实体、吟唱读条与阵风，重取职业系数
        self.dash2 = None
        self.channel = None
        self.gusts = []
        # 樱落·种花闭环持续态随切人清零（花圃/花期/花护/催放延迟跳不跨成员继承）
        self.sakura_beds = []
        self.sakura_kaki_t = 0.0
        self.sakura_guard = 0
        self.sakura_delay = []
        # 绯焰·缭焰火环/引信烙印随切人清零（燃径火径同水域，留在场上烧完）
        self.flare_fuses = []
        self.flare_ring_t = 0.0
        self.flare_ring_amp = 0.0
        # 星璃·连星成轨：地面态不随切人清理（同 flare_trails/zones），
        # 只重算「星之标记」供料模式（印记满层落星位而非自爆）
        self.stella_mark_supply = any(
            p.get("id") == "p_stella_mark"
            for p in getattr(self.skills, "passives", []))
        self.fx_sprites = []
        self.role = m.get("role", "hybrid")
        self.role_armor = S.ROLE_ARMOR.get(self.role, 0.0)
        self.role_skilldmg = S.ROLE_SKILLDMG_MULT.get(self.role, 1.0)
        self.snake_name = m["name"]
        self.snake_rarity = m["rarity"]
        skin = m["skin"]
        self.char_head = skin["head"]
        self.char_body = skin["body"]
        self.char_tail = skin["tail"]
        self.char_human = skin["human"]
        self.char_full = skin["full"]
        self.char_cast_poses = skin["cast"]
        self.cast_pose = None          # 切人即断掉上一位的释放动作
        self._prewarm_cast_poses()
        self.char_atk_poses = skin["atk"]
        # 数据驱动远程三段（樱落「飞樱散华」）：配了 ranged 块走远程连段路径
        self.ranged_cfg = self._norm_ranged_cfg(skin.get("ranged"))
        self.ranged_engaged = False    # 远程追击迟滞：进 range 开火后才咬住目标
        # 配了普攻姿势立绘且无远程规格 = 近战爪风连击；都没配的角色走弹丸普攻
        self.melee_atk = (self.ranged_cfg is None) and bool(
            self.char_atk_poses["lamia"] or self.char_atk_poses["human"])
        # 数据驱动近战规格（潮汐「凝水潮鞭」）：没配 melee 块的角色走薄荷 legacy 常量
        self.melee_cfg = self._norm_melee_cfg(skin.get("melee"))
        self.hitstop_t = 0.0
        self.atk_combo = None          # 切人即断掉上一位的连击
        self._prewarm_atk_poses()
        # 近战斩击贴图（可选）：effects/melee/<prefix>_atk_{human,lamia}.png，
        # 缺图回退矢量掌风（其他角色零影响）
        prefix = m.get("char_id", "").replace("lamia_", "")
        self._melee_fx_rel = {}
        for fm, tag in (("human", "_atk_human.png"), ("lamia", "_atk_lamia.png")):
            rel = f"effects/melee/{prefix}{tag}"
            if os.path.exists(os.path.join(S.ASSETS_DIR, rel.replace("/", os.sep))):
                self._melee_fx_rel[fm] = rel
        self._prewarm_melee_fx()
        self._rebuild_stats()

    # ------------------------------------------------------------ 切换出战
    def _switch_target(self, direction):
        """按方向取模循环找下一位能上场的成员下标（2 号往后滑回 1 号），没有返回 None。"""
        n = len(self.party)
        if n < 2:
            return None
        for step in range(1, n):
            idx = (self.active_idx + int(direction) * step) % n
            if self.party[idx]["snake"].alive:
                return idx
        return None

    def _switch_to(self, idx, cd=0.0, iframe=0.0, text=""):
        """实际切人：重指向视图 + 切换 CD + 新活跃者无敌帧 + 飘字反馈。"""
        prev = self.party[self.active_idx] if self.party else None
        self._activate(idx)
        self.switch_cd = max(0.0, cd)
        sn = self.snake
        # 潮汐·潮汐交接：切走者若持交接盾，把剩余盾量按 transfer 比例转移给登场者
        if prev is not None and prev is self.handoff_holder:
            self._transfer_handoff_shield(prev, self.party[self.active_idx])
        # 潮汐·踏浪登场：登场者落在水域上（且编队带该被动）则给短时移速+减伤
        self.landing_t = 0.0
        if (self.zones and self._pos_in_zone(sn.pos[0], sn.pos[1])
                and self._party_has_passive("p_wave_landing")):
            self.landing_t = S.PASSIVE_WAVE_LANDING_TIME
            self._float("踏浪登场!", sn.pos[0], sn.pos[1] - self.s(92),
                        (160, 215, 255), 26)
        if iframe > 0:
            sn.invincible = max(sn.invincible, iframe)
        sn.hurt_t = 0.0
        self.game.audio.play("ui_click", throttle=0.05)
        if text:
            self._float(text, sn.pos[0], sn.pos[1] - self.s(70), COLOR_GOLD, 32)
        self._burst(sn.pos[0], sn.pos[1], (255, 226, 140), 22)
        self.shake = max(self.shake, 0.18)

    def _try_switch(self, direction=1):
        """Q 键 / 滞轮切换出战：需编队≥2、非结算/暂停/选卡、CD 转好且目标存活。"""
        if len(self.party) < 2:
            return False
        if self.finished or self.paused or self.card_overlay:
            return False
        if self.switch_cd > 0:
            return False
        idx = self._switch_target(direction)
        if idx is None:
            return False
        self._switch_to(idx, cd=S.SWITCH_CD, iframe=S.SWITCH_IFRAME,
                        text=f"{self.party[idx]['name']} 登场！")
        return True

    def _auto_switch(self):
        """场上角色阵亡：无视 CD 让存活待命者接管；无人可接返回 False。"""
        if len(self.party) < 2:
            return False
        idx = self._switch_target(1)
        if idx is None:
            return False
        self._switch_to(idx, cd=0.0, iframe=S.SWITCH_IFRAME,
                        text=f"{self.party[idx]['name']} 接管战场！")
        return True

    def _standby_regen(self, dt):
        """待命成员缓慢回血（自身 regen × STANDBY_REGEN_MULT），不飘字不被索敌。"""
        for i, m in enumerate(self.party):
            if i == self.active_idx:
                continue
            sn = m["snake"]
            regen = m["card_stats"].get("regen", 0.0) * S.STANDBY_REGEN_MULT
            if regen > 0 and sn.alive and sn.hp < sn.hp_max:
                sn.hp = min(float(sn.hp_max), sn.hp + regen * dt)

    @staticmethod
    def _find_in_json(filename, wrap_key, want_id):
        try:
            path = os.path.join(S.DATA_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            items = raw.get(wrap_key, raw) if isinstance(raw, dict) else raw
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict) and it.get("id") == want_id:
                        return it
        except (IOError, json.JSONDecodeError, AttributeError, TypeError):
            pass
        return {}

    def _card_pool(self):
        """读 data/cards.json 卡池（缓存）。"""
        if self._cards_cache is None:
            self._cards_cache = []
            try:
                path = os.path.join(S.DATA_DIR, "cards.json")
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                items = raw.get("cards", raw) if isinstance(raw, dict) else raw
                for c in items:
                    if isinstance(c, dict) and c.get("id"):
                        self._cards_cache.append(c)
            except (IOError, json.JSONDecodeError, AttributeError, TypeError):
                self._cards_cache = []
        return self._cards_cache

    # ================================================================ 派生属性
    @property
    def player_speed(self):
        # 薄荷「疾风连闪」主动释放后的短时移速爆发
        burst = S.GALE_SPEED_MULT if self.skills.gale_active else 1.0
        mult = burst
        # 潮汐·涌潮水域：己方站在其中移速 +20%
        if self._active_in_zone():
            mult *= (1.0 + S.TIDE_ZONE_ALLY_SPEED)
        # 潮汐·踏浪登场：在水域上切人后短时移速 +20%
        if getattr(self, "landing_t", 0.0) > 0:
            mult *= (1.0 + S.PASSIVE_WAVE_LANDING_SPEED)
        return S.PLAYER_SPEED * self.S * self.stats["speed"] * mult

    @property
    def player_damage(self):
        rally = self.rally_atk if self.rally_t > 0 else 1.0
        return max(1, int(round(self.snake.attack * self.stats["atk"] * rally)))

    @property
    def atk_interval(self):
        base = S.ATK_INTERVAL_BASE - (self.snake.level - 1) * S.ATK_INTERVAL_PER_LEVEL
        base = max(S.ATK_INTERVAL_MIN, base)
        rally = self.rally_atkspd if self.rally_t > 0 else 1.0
        return base / max(0.2, self.stats["atkspd"] * rally)

    @property
    def magnet_radius(self):
        return S.ITEM_MAGNET_RADIUS * self.S * self.stats["pickup"]

    @property
    def pickup_radius(self):
        return S.ITEM_PICKUP_RADIUS * self.S

    # ---- 世界 <-> 屏幕 ----
    def wx(self, x, sx=0.0):
        return x - self.cam[0] + sx

    def wy(self, y, sy=0.0):
        return y - self.cam[1] + sy

    def _clamp_cam(self):
        self.cam[0] = min(max(self.cam[0], 0.0), max(0.0, self.world_w - self.W))
        self.cam[1] = min(max(self.cam[1], 0.0), max(0.0, self.world_h - self.H))

    # ================================================================ 难度曲线
    def _time_pressure(self):
        if self.elapsed <= S.TIME_PRESSURE_START:
            return 1.0
        t = (self.elapsed - S.TIME_PRESSURE_START) * S.TIME_PRESSURE_RAMP
        return min(S.TIME_PRESSURE_MAX, 1.0 + t)

    def _mob_speed(self):
        base = S.MOB_SPEED_BASE * self.S
        mult = min(S.MOB_SPEED_MAX_MULT, 1.0 + S.MOB_SPEED_GROWTH * (self.elapsed / 30.0))
        tp = self._time_pressure()
        return base * mult * (1.0 + (tp - 1) * 0.25)

    def _mob_atk(self):
        base = S.MOB_TOUCH_DAMAGE + (self.elapsed / 60.0) * S.MOB_ATK_GROWTH
        return max(1, int(round(base * self.scene_density)))

    def _mob_hp_mult(self):
        tp = self._time_pressure()
        return min(S.MOB_HP_MAX_MULT, 1.0 + self.scene_hp_growth * (self.elapsed / 30.0)) * tp

    def _spawn_interval(self):
        v = S.MOB_SPAWN_INTERVAL - S.MOB_SPAWN_RAMP * (self.elapsed / 10.0)
        v /= self._time_pressure() ** 0.6
        v /= max(0.5, self.scene_density)
        return max(S.MOB_SPAWN_MIN * 0.6, v)

    def _item_tier(self):
        return max(1, min(S.ITEM_TIER_MAX, 1 + int(self.elapsed / S.ITEM_TIER_TIME)))

    # ================================================================ 生成
    def _offscreen_pos(self):
        """在当前摄像机视野外一圈取一个刷怪点（保证不在玩家眼前凭空出现）。"""
        m = S.MOB_SPAWN_OFFSCREEN_MARGIN * self.S
        left, top = self.cam[0] - m, self.cam[1] - m
        right, bottom = self.cam[0] + self.W + m, self.cam[1] + self.H + m
        side = random.randint(0, 3)
        if side == 0:
            x, y = left, random.uniform(top, bottom)
        elif side == 1:
            x, y = right, random.uniform(top, bottom)
        elif side == 2:
            x, y = random.uniform(left, right), top
        else:
            x, y = random.uniform(left, right), bottom
        x = min(max(x, 0.0), self.world_w)
        y = min(max(y, 0.0), self.world_h)
        return (x, y)

    def _spawn_mob(self):
        pos = self._offscreen_pos()
        self.mobs.append(Mob(
            pos,
            hp_mult=self._mob_hp_mult(),
            speed=self._mob_speed(),
            atk=self._mob_atk(),
            radius=self.s(S.MOB_RADIUS),
            sprite=self.scene_mob_sprite,
        ))

    def _spawn_elite(self):
        """刷一只精英怪，登场带警示环与震屏。"""
        self.elites_spawned += 1
        pos = self._offscreen_pos()
        dens = self.scene_density
        e = EliteMob(
            pos,
            hp_mult=self._mob_hp_mult() * dens,
            speed=self._mob_speed(),
            atk=max(1, int(round(S.ELITE_ATK * dens))),
            radius=self.s(S.MOB_RADIUS),
            name=f"精英 · 第{self.elites_spawned}波",
            sprite=self.scene_elite_sprite,
        )
        self.mobs.append(e)
        self._fx_ring(pos[0], pos[1], self.s(150), (255, 90, 120), life=0.6)
        self.shake = max(self.shake, 0.45)
        self.game.audio.play("boss_appear", throttle=0.1)
        self._float("精英怪出现!", self.snake.pos[0],
                    self.snake.pos[1] - self.s(90), (255, 90, 120), 34)

    def _roll_kind(self):
        r = random.random()
        if r < S.DROP_EXP:
            return "exp"
        if r < S.DROP_EXP + S.DROP_CRYSTAL:
            return "crystal"
        if r < S.DROP_EXP + S.DROP_CRYSTAL + S.DROP_STARDUST:
            return "stardust"
        return "heart"

    def _spawn_item(self, near_player=True):
        if len(self.drops) >= S.ITEM_MAX_ON_MAP:
            return
        if near_player:
            px, py = self.snake.pos
            span = math.hypot(self.W, self.H)
            dist = random.uniform(0.5, 1.4) * span
            ang = random.random() * math.tau
            x = min(max(px + math.cos(ang) * dist, 40), self.world_w - 40)
            y = min(max(py + math.sin(ang) * dist, 40), self.world_h - 40)
        else:
            x = random.uniform(40, self.world_w - 40)
            y = random.uniform(40, self.world_h - 40)
        self.drops.append(Drop(self._roll_kind(), (x, y), tier=self._item_tier()))

    def _drop_from_mob(self, m):
        self.drops.append(Drop(self._roll_kind(), (m.pos[0], m.pos[1]),
                               tier=self._item_tier()))

    # ================================================================ 主更新
    def update(self, dt):
        # 改键浮层开着时挂起输入捕获，让全局音量热键让路（暂停中 update 会早退，
        # 故放在最前面）。paused/rebind_open 变化后下一帧生效，足够。
        self.game.input_capture = bool(self.rebind_open and self.paused)
        if self.finished or self.paused or self.card_overlay:
            return
        # 卡顿尖峰钳制 dt：避免一帧跨度过大导致穿模/数值爆炸，手感更稳
        dt = min(dt, S.DT_MAX)
        # 顿帧（hitstop）：重击命中瞬间冻结全世界逻辑，渲染照常 → 打击感
        if self.hitstop_t > 0:
            self.hitstop_t = max(0.0, self.hitstop_t - dt)
            dt = 0.0

        self.elapsed += dt
        self._update_bgm(dt)
        self.switch_cd = max(0.0, self.switch_cd - dt)
        if self.cast_pose is not None:
            cp = self.cast_pose
            if cp.get("hold") and self.channel is not None:
                # 吟唱技能：姿势停在包络保持段，读条结束才释放淡出
                cp["t"] = min(cp["t"] + dt, CAST_POSE_DUR - CAST_POSE_OUT)
            else:
                cp["t"] += dt
                if cp["t"] >= CAST_POSE_DUR:
                    self.cast_pose = None
        if self.switch_hint_t > 0:
            self.switch_hint_t = max(0.0, self.switch_hint_t - dt)

        self._update_player(dt)
        self.snake.update_path(dt)
        self.snake.facing_update()
        # 技能冷却：待命成员也照走，切上来就能接招
        for m in self.party:
            m["skills"].update(dt)
        if self.rally_t > 0:
            self.rally_t = max(0.0, self.rally_t - dt)
        if self.ward_t > 0:
            self.ward_t = max(0.0, self.ward_t - dt)
        self._update_dash2(dt)
        self._update_channel(dt)
        self._update_gusts(dt)
        self._update_sakura(dt)
        self._update_flare(dt)
        self._update_stella(dt)
        self._update_fx_sprites(dt)
        self._update_tide_fields(dt)
        # 生命再生：血条制下直接把 regen*dt 累加进 hp（浮点），整数变化时飘字
        regen = self.stats.get("regen", 0.0)
        if regen > 0 and self.snake.alive and self.snake.hp < self.snake.hp_max:
            before = int(self.snake.hp)
            self.snake.hp = min(float(self.snake.hp_max),
                                self.snake.hp + regen * dt)
            gained = int(self.snake.hp) - before
            if gained > 0:
                self._float(f"+{gained}", self.snake.pos[0],
                            self.snake.pos[1] - self.s(34), COLOR_HP, 20)
        self._standby_regen(dt)

        self._auto_attack(dt)
        self._update_bullets(dt)
        self._update_mobs(dt)
        self._update_items(dt)
        self._update_mob_status(dt)
        self._handle_mob_contact()
        self._update_boss(dt)

        self.shake = max(0.0, self.shake - dt * 3.2)
        self.flash = max(0.0, self.flash - dt * 2.4)

        self.particles = list(self._tick_particles(dt))
        if len(self.particles) > S.PARTICLE_MAX:
            self.particles = self.particles[-S.PARTICLE_MAX:]
        self.floaters = list(self._tick_floaters(dt))
        for e in self.effects:
            e["life"] -= dt
            if e["type"] == "leaf":
                # 碎叶：沿挥向飘出 + 风压下坠 + 自旋，全在这里结算
                e["x"] += e["vx"] * dt
                e["y"] += e["vy"] * dt
                e["vy"] += self.s(260) * dt
                e["vx"] *= 1.0 - min(1.0, dt * 1.6)
                e["ang"] += e["spin"] * dt
        self.effects = [e for e in self.effects if e["life"] > 0]
        for t in self.skill_toast:
            t["life"] -= dt
        self.skill_toast = [t for t in self.skill_toast if t["life"] > 0]

        self._update_cam(dt)
        self._update_tutorial(dt)

        # 升级选卡：攒着的卡在这里弹出（双人局每级按 1→2 号位各选一张）
        if self.card_queue and self.card_overlay is None:
            self._open_card_overlay()

        if not self.snake.alive and not self._auto_switch():
            self.finished = True
            self._finish_tutorial()
            self.game.audio.play("gameover")
            self.game.audio.play_bgm("gameover")
            self._clear_suspend()
            self.game.save_manager.add_stardust(self.stardust)
            self.game.save_manager.record_run(self.score, self.snake.level, self.kills)

    # ------------------------------------------------------------ 玩家
    def _update_player(self, dt):
        keys = pygame.key.get_pressed()
        dx = (1 if keys[pygame.K_d] else 0) + (1 if keys[pygame.K_RIGHT] else 0) \
            - (1 if keys[pygame.K_a] else 0) - (1 if keys[pygame.K_LEFT] else 0)
        dy = (1 if keys[pygame.K_s] else 0) + (1 if keys[pygame.K_DOWN] else 0) \
            - (1 if keys[pygame.K_w] else 0) - (1 if keys[pygame.K_UP] else 0)
        move = [float(dx), float(dy)]
        self.snake.update(dt, self.world_w, self.world_h, move,
                          self.player_speed)
        # 静止时朝向最近的敌人，立绘/普攻方向更自然
        if dx == 0 and dy == 0:
            tgt = self._nearest_target()
            if tgt is not None:
                _kind, obj = tgt
                tx, ty = obj.pos[0], obj.pos[1]
                ax, ay = tx - self.snake.pos[0], ty - self.snake.pos[1]
                d = math.hypot(ax, ay) or 1.0
                self.snake.aim_dir = [ax / d, ay / d]

    def _nearest_target(self, max_range=None):
        px, py = self.snake.pos
        best = None
        bd = float("inf")
        for m in self.mobs:
            if not m.alive:
                continue
            d = math.hypot(m.pos[0] - px, m.pos[1] - py)
            if d < bd:
                bd = d
                best = ("mob", m)
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            d = math.hypot(bx - px, by - py)
            if d < bd:
                bd = d
                best = ("boss", self.boss)
        if best is None:
            return None
        if max_range is not None and bd > max_range:
            return None
        return best

    def try_shield(self, mouse_pos=None):
        """左键护盾：冷却就绪时给自己套一层吸收池 + 时限护盾（取代旧闪避）。"""
        sn = self.snake
        if sn.shield_cd > 0 or not sn.alive:
            return
        mult = 1.0 + min(S.SHIELD_STAT_CAP, self.stats.get("shield", 0.0))
        sn.grant_shield(S.SHIELD_TIME * mult, S.SHIELD_POOL * mult)
        sn.shield_cd = S.SHIELD_CD
        self.game.audio.play("skill_shield", throttle=0.05)
        self._burst(sn.pos[0], sn.pos[1], (160, 210, 255), 14)
        self._fx_ring(sn.pos[0], sn.pos[1], self.s(70), (180, 220, 255), life=0.4)

    # ------------------------------------------------------------ 自动普攻
    def _auto_attack(self, dt):
        # 吟唱读条未结束不插普攻（吟唱姿势也全程保持，见 _start_cast_pose 的 hold）
        if self.channel is not None:
            return
        if self.melee_atk:
            self._auto_attack_melee(dt)
            return
        if self.ranged_cfg is not None:
            self._auto_attack_ranged(dt)
            return
        self.snake.atk_timer -= dt
        if self.snake.atk_timer > 0:
            return
        tgt = self._nearest_target(max_range=S.ATK_RANGE * self.S
                                   * self.stats.get("range", 1.0))
        if tgt is None:
            self.snake.atk_timer = 0.06
            return
        self.snake.atk_timer = self.atk_interval
        _kind, obj = tgt
        tx, ty = obj.pos[0], obj.pos[1]
        px, py = self.snake.pos
        dx, dy = tx - px, ty - py
        d = math.hypot(dx, dy) or 1.0
        spd = S.ATK_BULLET_SPEED * self.S
        self.bullets.append(PlayerBullet(
            (px, py), (dx / d * spd, dy / d * spd), self.player_damage,
            self.s(S.ATK_BULLET_RADIUS), element=self._active_element()))
        self.game.audio.play("shoot", throttle=0.05)

    def _auto_attack_melee(self, dt):
        """近战爪风连击（薄荷）：3 段循环 + 收尾后摇，贴身站桩不位移。

        节拍走 S.MELEE_COMBO_LOOP：1/2/3 段依次命中、第 3 段强化收尾；
        循环结束进后摇段（复用 atk_interval，等级成长与攻速卡都压缩它）；
        任意技能可强取消后摇（见 _cancel_atk_recover）。
        """
        if self.melee_cfg is not None:
            self._auto_attack_melee_cfg(dt)
            return
        cb = self.atk_combo
        if cb is not None and cb["recover"] > 0:
            cb["recover"] -= dt
            if cb["recover"] <= 0:
                self.atk_combo = None
                self.snake.atk_timer = 0.0
            return
        if cb is not None:
            cb["t"] += dt
            step = S.MELEE_COMBO_LOOP / 3.0
            want = min(3, int(cb["t"] / step) + 1)
            while cb["stage"] < want:
                cb["stage"] += 1
                self._melee_swing(cb["stage"])
            if cb["t"] >= S.MELEE_COMBO_LOOP:
                cb["recover"] = cb["recover_max"] = self.atk_interval
            return
        self.snake.atk_timer -= dt
        if self.snake.atk_timer > 0:
            return
        rng = S.MELEE_COMBO_RANGE * self.S * self.stats.get("range", 1.0)
        if self._nearest_target(max_range=rng) is None:
            self.snake.atk_timer = 0.06
            return
        self.atk_combo = {"t": 0.0, "stage": 1, "recover": 0.0, "recover_max": 0.0}
        self._melee_swing(1)

    def _melee_swing(self, stage):
        """连击单段结算：锁最近目标伤害 + 命中被动；收尾段加倍率与小击退。

        没锁到目标也挥空（只出掌风/碎叶表现），循环节奏不断。
        """
        px, py = self.snake.pos
        rng = S.MELEE_COMBO_RANGE * self.S * self.stats.get("range", 1.0)
        tgt = self._nearest_target(max_range=rng)
        if tgt is not None:
            _kind, obj = tgt
            ang = math.atan2(obj.pos[1] - py, obj.pos[0] - px)
        else:
            ang = math.atan2(self.snake.aim_dir[1], self.snake.aim_dir[0])
        self._fx_slash(px, py, ang, stage)
        self._fx_leaves(px, py, ang, 2 if stage < 3 else 3)
        self.game.audio.play("swipe", throttle=0.04)
        if tgt is None:
            return
        dmg = max(1, int(round(self.player_damage * S.MELEE_COMBO_HIT_MULT)))
        if stage == 3:
            dmg = max(1, int(round(dmg * S.MELEE_COMBO_FINISHER_MULT)))
        kind, obj = tgt
        if kind == "mob":
            m = obj
            self._hurt_mob(m, dmg, m.pos[0], m.pos[1],
                           color=(150, 240, 190), spark=6)
            self._apply_onhit_passive(m)
            if stage == 3 and m.alive:
                m.knockback(self.snake.pos, S.MELEE_COMBO_FINISHER_KNOCK)
        else:
            self._damage_boss(dmg, color=(150, 240, 190))

    # ------------------------------------------------------------ 数据驱动近战（潮汐）
    @staticmethod
    def _norm_melee_cfg(raw):
        """规整 characters.json 的 melee 规格块：缺项补默认，非法返回 None。

        没配 melee 块的角色（如薄荷）返回 None → 走上面的 legacy 常量路径，零影响。
        """
        if not isinstance(raw, dict):
            return None
        cfg = dict(raw)
        defaults = {
            "range": 160.0, "arc_deg": 120.0, "finisher_radius": 100.0,
            "exit_range": 200.0,
            "windup": 0.16, "hit_window": 0.14, "recover": 0.30,
            "recover_min": 0.15, "idle_return": 0.15,
            "hit_mult": 0.75, "finisher_mult": 1.6, "finisher_knock": 320.0,
            "hitstop": 0.12, "shake_px": 2.0, "shake_px_finisher": 4.5,
            "shield_pct": 0.01, "shield_cap": 0.10, "shield_time": 4.0,
        }
        for k, v in defaults.items():
            try:
                cfg[k] = float(cfg.get(k, v))
            except (TypeError, ValueError):
                cfg[k] = v
        return cfg

    def _melee_recover_secs(self, cfg):
        """收势段实际时长：攻速加成只压收势（recover），最低压到 recover_min。"""
        ratio = min(1.0, self.atk_interval / S.ATK_INTERVAL_BASE)
        return max(cfg["recover_min"], cfg["recover"] * ratio)

    def _auto_attack_melee_cfg(self, dt):
        """数据驱动三段连击（潮汐「凝水潮鞭」）：起手→命中→收势→回 idle。

        · 命中帧在起手结束后准时结算（扇形/环形见 _melee_swing_cfg）；
        · 攻速只压收势段；第 3 段附加顿帧 + 强震屏；
        · 追击迟滞：进 range 开打、退 exit_range 才脱战，防边界抖动；
        · 任意技能可强取消收势（见 _cancel_atk_recover）。
        """
        cfg = self.melee_cfg
        rmult = self.stats.get("range", 1.0)
        cb = self.atk_combo
        if cb is not None:
            # 迟滞退出：连击中目标全部退出 exit_range 才收招，避免边界反复起收
            if self._nearest_target(max_range=cfg["exit_range"] * self.S * rmult) is None:
                self.atk_combo = None
                self.snake.atk_timer = 0.05
                return
            cb["t"] += dt
            hit_at = cfg["windup"]
            if not cb["hit_done"] and cb["t"] >= hit_at:
                cb["hit_done"] = True
                self._melee_swing_cfg(cb["stage"])
            total = (cfg["windup"] + cfg["hit_window"]
                     + cb["recover_max"] + cfg["idle_return"])
            if cb["t"] >= total:
                cb["stage"] = cb["stage"] % 3 + 1
                cb["t"] = 0.0
                cb["hit_done"] = False
                cb["recover_max"] = self._melee_recover_secs(cfg)
            return
        self.snake.atk_timer -= dt
        if self.snake.atk_timer > 0:
            return
        rng = cfg["range"] * self.S * rmult
        if self._nearest_target(max_range=rng) is None:
            self.snake.atk_timer = 0.06
            return
        self.atk_combo = {"t": 0.0, "stage": 1, "hit_done": False,
                         "recover": 0.0,
                         "recover_max": self._melee_recover_secs(cfg)}

    def _melee_swing_cfg(self, stage):
        """单段结算：1/2 段扇形横扫（120°/4 身位），3 段 360° 环形砸地带击退。

        命中为自身叠 1% 最大生命护盾（上限 10%）；3 段附加顿帧 + 强震屏。
        """
        cfg = self.melee_cfg
        sn = self.snake
        px, py = sn.pos
        rmult = self.stats.get("range", 1.0)
        # 挥向：锁最近目标，没有就朝当前面向（空挥也出特效，节拍不断）
        tgt = self._nearest_target(max_range=cfg["exit_range"] * self.S * rmult)
        if tgt is not None:
            _kind, obj = tgt
            ang = math.atan2(obj.pos[1] - py, obj.pos[0] - px)
        else:
            ang = math.atan2(sn.aim_dir[1], sn.aim_dir[0])
        if stage == 3:
            radius = cfg["finisher_radius"] * self.S * rmult
            half = None                       # 360° 环形
        else:
            radius = cfg["range"] * self.S * rmult
            half = math.radians(cfg["arc_deg"]) / 2.0
        hits = []
        for m in self.mobs:
            if not m.alive:
                continue
            dx, dy = m.pos[0] - px, m.pos[1] - py
            d = math.hypot(dx, dy)
            if d > radius + m.radius:
                continue
            # 贴身的目标不看角度（都糊在脸上了还挑扇形方位太苛刻）
            if half is not None and d > m.radius + self.s(12):
                da = abs((math.atan2(dy, dx) - ang + math.pi) % math.tau - math.pi)
                if da > half:
                    continue
            hits.append(("mob", m))
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - px, by - py) <= radius + self.boss.radius_px:
                hits.append(("boss", self.boss))
        self._fx_melee_swing(px, py, ang, stage)
        self.game.audio.play("swipe", throttle=0.04)
        shake_px = cfg["shake_px_finisher"] if stage == 3 else cfg["shake_px"]
        self.shake = max(self.shake, shake_px / _SHAKE_PX_DIV)
        if stage == 3 and cfg["hitstop"] > 0:
            self.hitstop_t = max(self.hitstop_t, cfg["hitstop"])
        if not hits:
            return
        dmg = self.player_damage * cfg["hit_mult"]
        if stage == 3:
            dmg *= cfg["finisher_mult"]
        dmg = max(1, int(round(dmg)))
        for kind, obj in hits:
            if kind == "mob":
                m = obj
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1],
                               color=(120, 200, 255), spark=6)
                self._apply_onhit_passive(m)
                if stage == 3 and m.alive:
                    m.knockback(sn.pos, cfg["finisher_knock"])
            else:
                self._damage_boss(dmg, color=(120, 200, 255))
        # 潮汐契约：普攻命中触发水柱追击（内置 CD 限流，见 _try_contract_proc）
        if self.contract is not None:
            _k, _o = hits[0]
            self._try_contract_proc(_o.pos[0], _o.pos[1])
        # 命中叠盾：每次命中 +1% 最大生命吸收池，封顶 10%（时限滚动刷新）
        if cfg["shield_pct"] > 0 and sn.alive:
            cap = sn.hp_max * cfg["shield_cap"]
            sn.shield_pool = min(cap, sn.shield_pool + sn.hp_max * cfg["shield_pct"])
            sn.shield_t = max(sn.shield_t, cfg["shield_time"])

    def _fx_melee_swing(self, x, y, ang, stage):
        """潮汐普攻特效：只用 tide_atk_{lamia,human} 两贴图及镜像/缩放变体。

        1/2 段=弧痕扫掠（第 2 段水平镜像 → 反向回扫）；3 段=踏地涌浪环扩散；
        双缺图回退矢量掌风（同薄荷），绝不拿技能级特效充数。
        """
        cfg = self.melee_cfg
        am = self.party[self.active_idx]
        form = "human" if (self.char_human and am["form"] == "human") else "lamia"
        rels = getattr(self, "_melee_fx_rel", {})
        if stage == 3:
            rel = rels.get(form) or rels.get("lamia") or rels.get("human")
            if rel is None:
                r = self.s(cfg["finisher_radius"])
                life = 0.30
                self.effects.append({"type": "slash", "x": x, "y": y, "r": r,
                                     "ang": ang, "half": math.pi,
                                     "color": (120, 200, 255),
                                     "life": life, "max_life": life})
                return
            size = self.s(cfg["finisher_radius"]) * 2.6
            life = 0.42
            self.effects.append({
                "type": "melee_tex", "kind": "ring", "rel": rel, "form": form,
                "ang": ang, "x": x, "y": y, "size": size,
                "color": (120, 200, 255), "life": life, "max_life": life})
            return
        rel = rels.get("lamia") or rels.get("human")
        if rel is None:
            r = self.s(cfg["range"] * 0.62)
            life = 0.20
            self.effects.append({"type": "slash", "x": x, "y": y, "r": r,
                                 "ang": ang, "half": math.radians(cfg["arc_deg"]) / 2,
                                 "color": (120, 200, 255),
                                 "life": life, "max_life": life})
            return
        dist = self.s(cfg["range"]) * 0.45
        size = self.s(cfg["range"]) * 1.8
        life = 0.34
        self.effects.append({
            "type": "melee_tex", "kind": "arc", "rel": rel, "form": form,
            "flip": stage == 2, "ang": ang,
            "x": x + math.cos(ang) * dist, "y": y + math.sin(ang) * dist,
            "size": size, "color": (120, 200, 255),
            "life": life, "max_life": life})

    # ------------------------------------------------------------ 数据驱动远程（樱落）
    @staticmethod
    def _norm_ranged_cfg(raw):
        """规整 characters.json 的 ranged 规格块：缺项补默认，非法返回 None。

        stages 必须恰为三段（飞樱散华 1/2/3），任一段缺失即整体非法，
        回退通用单弹丸普攻路径，零影响。
        """
        if not isinstance(raw, dict):
            return None
        cfg = dict(raw)
        defaults = {
            "range": 460.0, "exit_range": 520.0, "bullet_radius": 8.0,
            "hitstop": 0.08, "shake_px": 2.0, "shake_px_finisher": 3.0,
        }
        for k, v in defaults.items():
            try:
                cfg[k] = float(cfg.get(k, v))
            except (TypeError, ValueError):
                cfg[k] = v
        stages = []
        for st in (raw.get("stages") or []):
            if not isinstance(st, dict):
                return None
            d = {"count": 1.0, "spread_deg": 0.0, "speed": 820.0, "mult": 1.0,
                 "life": 1.1, "curve": 0.0, "spin": 0.0, "trail": 0.0, "mark": 0.0,
                 "pierce": 0.0, "hit_trace": 0.0}
            for k in d:
                try:
                    d[k] = float(st.get(k, d[k]))
                except (TypeError, ValueError):
                    pass
            stages.append(d)
        if len(stages) != 3:
            return None
        cfg["stages"] = stages
        return cfg

    def _auto_attack_ranged(self, dt):
        """樱落「飞樱散华」三段循环：每 atk_interval 发一段，1→2→3 循环。

        · 追击迟滞：进 range 开火、退 exit_range 才脱战，防边界抖动；
        · 攻速只压 atk_interval（段间隔），不减每段花瓣枚数；
        · 段3 附加顿帧 + 强震屏（前两段只轻震屏）。
        """
        cfg = self.ranged_cfg
        rmult = self.stats.get("range", 1.0)
        cb = self.atk_combo
        if cb is not None:
            cb["t"] += dt
            # 迟滞退出：目标全部退出 exit_range 才收花瓣，避免边界反复起收
            if self._nearest_target(max_range=cfg["exit_range"] * self.S * rmult) is None:
                self.atk_combo = None
                self.ranged_engaged = False
                self.snake.atk_timer = 0.05
                return
        self.snake.atk_timer -= dt
        if self.snake.atk_timer > 0:
            return
        rng = (cfg["exit_range"] if self.ranged_engaged else cfg["range"]) \
            * self.S * rmult
        tgt = self._nearest_target(max_range=rng)
        if tgt is None:
            self.ranged_engaged = False
            self.snake.atk_timer = 0.06
            return
        self.ranged_engaged = True
        self.snake.atk_timer = self.atk_interval
        stage = 1 if cb is None else cb["stage"] % 3 + 1
        self.atk_combo = {"t": 0.0, "stage": stage,
                          "recover": 0.0, "recover_max": 0.0}
        self._ranged_volley(stage, tgt)

    def _ranged_volley(self, stage, tgt):
        """单段结算：按该段枚数/Spread 角/弹速/倍率撒花瓣，没锁到目标也空挥。

        段2 两枚左右对称弧旋；段3 旋转拖尾 + 命中必叠花瓣标记；
        震屏/顿帧在开火帧结算（与近战收尾段同一节拍点）。
        """
        cfg = self.ranged_cfg
        st = cfg["stages"][stage - 1]
        sn = self.snake
        px, py = sn.pos
        if tgt is not None:
            _kind, obj = tgt
            ang = math.atan2(obj.pos[1] - py, obj.pos[0] - px)
        else:
            ang = math.atan2(sn.aim_dir[1], sn.aim_dir[0])
        rels = getattr(self, "_melee_fx_rel", {})
        if stage == 3:
            tex = rels.get("human") or rels.get("lamia")
            tex_mult = 6.0
        else:
            tex = rels.get("lamia") or rels.get("human")
            tex_mult = 4.0
        n = max(1, int(st["count"]))
        spread = math.radians(st["spread_deg"])
        dmg = max(1, int(round(self.player_damage * st["mult"])))
        spd = st["speed"] * self.S
        radius = self.s(cfg["bullet_radius"])
        for i in range(n):
            off = 0.0 if n < 2 else -spread / 2.0 + spread * i / (n - 1)
            a = ang + off
            # 弧旋左右对称：偶数枚偏左、奇数枚偏右，段2 两瓣各画一道外弧
            curve = st["curve"] * (-1.0 if i % 2 == 0 else 1.0) if st["curve"] else 0.0
            b = PlayerBullet(
                (px, py), (math.cos(a) * spd, math.sin(a) * spd), dmg, radius,
                life=st["life"], color=self._ranged_color(),
                element=self._active_element(), curve=curve, spin=st["spin"],
                pierce=int(st["pierce"]))
            b.rot = math.degrees(a)
            b.trail = st["trail"] > 0
            b.mark = st["mark"] > 0
            b.star_trace = st["hit_trace"] > 0   # 星璃段3：命中留微星痕（纯视觉）
            b.tex_rel = tex
            b.tex_mult = tex_mult
            self.bullets.append(b)
        self._fx_ranged_muzzle(px, py, ang, stage)
        self.game.audio.play("shoot", throttle=0.05)
        shake_px = cfg["shake_px_finisher"] if stage == 3 else cfg["shake_px"]
        self.shake = max(self.shake, shake_px / _SHAKE_PX_DIV)
        if stage == 3 and cfg["hitstop"] > 0:
            self.hitstop_t = max(self.hitstop_t, cfg["hitstop"])

    def _fx_ranged_muzzle(self, x, y, ang, stage):
        """樱落普攻枪口特效：只用 sakura_atk_{lamia,human} 两贴图及镜像/缩放变体。

        1/2 段=扇形花瓣弧（第 2 段水平镜像反向回扫）；3 段=环形花瓣爆发扩散；
        双缺图回退矢量花瓣风，绝不拿技能级特效充数。
        """
        color = self._ranged_color()
        rels = getattr(self, "_melee_fx_rel", {})
        am = self.party[self.active_idx]
        form = "human" if (self.char_human and am["form"] == "human") else "lamia"
        if stage == 3:
            rel = rels.get("human") or rels.get("lamia")
            if rel is None:
                self._fx_petals(x, y, self.s(120), color)
                return
            life = 0.42
            self.effects.append({
                "type": "melee_tex", "kind": "ring", "rel": rel, "form": form,
                "ang": ang, "x": x, "y": y, "size": self.s(260),
                "color": color, "life": life, "max_life": life})
            return
        rel = rels.get("lamia") or rels.get("human")
        if rel is None:
            life = 0.20
            self.effects.append({"type": "slash", "x": x, "y": y,
                                 "r": self.s(120), "ang": ang,
                                 "half": math.radians(28),
                                 "color": color, "life": life, "max_life": life})
            return
        dist = self.s(56)
        life = 0.30
        self.effects.append({
            "type": "melee_tex", "kind": "arc", "rel": rel, "form": form,
            "flip": stage == 2, "ang": ang,
            "x": x + math.cos(ang) * dist, "y": y + math.sin(ang) * dist,
            "size": self.s(200), "color": color, "life": life, "max_life": life})

    def _melee_fx_surf_flip(self, rel, size):
        """近战贴图的水平镜像缓存（第 2 段反向回扫用，翻一次常驻查表）。"""
        base = self._melee_fx_surf(rel, size)
        if base is None:
            return None
        size = max(16, int(size))
        key = ("meleefxflip", rel, size)
        if key in self._surf_cache:
            return self._surf_cache[key]
        img = pygame.transform.flip(base, True, False)
        self._surf_cache[key] = img
        return img

    def _cancel_atk_recover(self):
        """取消规则：任意技能可强取消近战连击的收尾后摇，取消后普攻立即续接。"""
        cb = self.atk_combo
        if cb is None:
            return
        if self.melee_cfg is not None:
            # cfg 驱动：命中已结算后，技能把收势段直接清零（回 idle 段仍播完，
            # 姿势无缝落回起始帧，不会闪跳）
            cfg = self.melee_cfg
            if cb.get("hit_done") or cb["t"] >= cfg["windup"] + cfg["hit_window"]:
                cb["recover_max"] = 0.0
            return
        if cb["recover"] > 0:
            self.atk_combo = None
            self.snake.atk_timer = 0.0

    def _fx_slash(self, x, y, ang, stage):
        """命中表现：双形态近战斩击贴图（人形态=X 形斩 / 蛇形态=旋风环），
        缩放弹跳 + 旋转 + 淡出，收尾段圈更大更久；缺贴图回退矢量掌风。"""
        am = self.party[self.active_idx]
        form = "human" if (self.char_human and am["form"] == "human") else "lamia"
        rel = getattr(self, "_melee_fx_rel", {}).get(form)
        if rel is None:
            r = self.s(S.MELEE_COMBO_RANGE * (0.62 if stage < 3 else 0.80))
            life = 0.16 if stage < 3 else 0.22
            self.effects.append({"type": "slash", "x": x, "y": y, "r": r,
                                 "ang": ang, "half": 0.85 if stage < 3 else 1.15,
                                 "color": (150, 240, 190),
                                 "life": life, "max_life": life})
            return
        # 斩击中心放在挥向前一步，寿命内再沿挥向漂一点，方向感更自然
        dist = self.s(S.MELEE_COMBO_RANGE) * 0.42
        size = self.s(S.MELEE_COMBO_RANGE) * (1.5 if stage < 3 else 1.9)
        life = 0.30 if stage < 3 else 0.40
        self.effects.append({
            "type": "melee_tex", "rel": rel, "form": form, "ang": ang,
            "x": x + math.cos(ang) * dist, "y": y + math.sin(ang) * dist,
            "size": size, "color": (150, 240, 190),
            "life": life, "max_life": life})

    def _melee_fx_surf(self, rel, size):
        """近战斩击贴图按高度缩放缓存（键结构与 _skill_fx_surf 同款）。"""
        size = max(16, int(size))
        key = ("meleefx", rel, size)
        if key in self._surf_cache:
            return self._surf_cache[key]
        img = None
        try:
            img = self.assets.get_scaled(rel, height=size)
        except Exception:
            img = None
        self._surf_cache[key] = img
        return img

    def _prewarm_melee_fx(self):
        """开局把斩击贴图两段尺寸 + 动画全程的旋转/缩放档位预烘焙，
        首段命中帧不产生读盘/smoothscale/rotate 重采样（同姿势预热策略）。"""
        rcfg = getattr(self, "ranged_cfg", None)
        if rcfg is not None:
            # 樱落：枪口弧痕（16 旋转档，含段2 镜像底图）+ 环形爆发（缩放档）
            # + 弹丸两尺寸档全角度旋转档（弧旋/自旋方向逐帧变）
            arc_rel = (self._melee_fx_rel.get("lamia")
                       or self._melee_fx_rel.get("human"))
            if arc_rel:
                mz = self.s(200)
                for base in (self._melee_fx_surf(arc_rel, mz),
                             self._melee_fx_surf_flip(arc_rel, mz)):
                    if base is None:
                        continue
                    for step in range(16):
                        self._rot_surf(base, step * 22.5)
                bb = self._melee_fx_surf(arc_rel,
                                         self.s(rcfg["bullet_radius"]) * 4)
                if bb is not None:
                    for step in range(_ROT_STEPS):
                        self._rot_surf(bb, step * (360.0 / _ROT_STEPS))
            ring_rel = (self._melee_fx_rel.get("human")
                        or self._melee_fx_rel.get("lamia"))
            if ring_rel:
                base = self._melee_fx_surf(ring_rel, self.s(260))
                if base is not None:
                    for zs in range(8, 19):
                        self._rotozoom_surf(base, 0.0, zs / float(_RZ_SCALE_STEPS))
                bb = self._melee_fx_surf(ring_rel,
                                         self.s(rcfg["bullet_radius"]) * 6)
                if bb is not None:
                    for step in range(_ROT_STEPS):
                        self._rot_surf(bb, step * (360.0 / _ROT_STEPS))
            return
        cfg = getattr(self, "melee_cfg", None)
        if cfg is not None:
            # 潮汐：arc=横扫弧痕（旋转 16 档，含第 2 段镜像底图），ring=涌浪环（缩放档）
            rmult = 1.0
            arc_rel = (self._melee_fx_rel.get("lamia")
                       or self._melee_fx_rel.get("human"))
            if arc_rel:
                base = self._melee_fx_surf(arc_rel, self.s(cfg["range"]) * 1.8 * rmult)
                flip = self._melee_fx_surf_flip(arc_rel,
                                                self.s(cfg["range"]) * 1.8 * rmult)
                for b in (base, flip):
                    if b is None:
                        continue
                    for step in range(16):
                        self._rot_surf(b, step * 22.5)
            ring_rel = (self._melee_fx_rel.get("human")
                        or self._melee_fx_rel.get("lamia"))
            if ring_rel:
                base = self._melee_fx_surf(ring_rel,
                                           self.s(cfg["finisher_radius"]) * 2.6)
                if base is not None:
                    for zs in range(8, 19):
                        self._rotozoom_surf(base, 0.0, zs / float(_RZ_SCALE_STEPS))
            return
        for fm, rel in getattr(self, "_melee_fx_rel", {}).items():
            for mult in (1.5, 1.9):
                base = self._melee_fx_surf(rel, self.s(S.MELEE_COMBO_RANGE) * mult)
                if base is None:
                    continue
                if fm == "lamia":
                    # 旋风环扫过 0~110°，共 16 个角度档
                    for step in range(16):
                        self._rot_surf(base, step * (360.0 / _ROT_STEPS))
                else:
                    # X 形斩：3 个角度档 × 缩放 0.75→1.0 共 5 档
                    for rot in (36.0, 45.0, 54.0):
                        for zs in range(12, 17):
                            self._rotozoom_surf(base, rot, zs / 16.0)

    def _fx_leaves(self, x, y, ang, n):
        """命中表现：2-3 片碎叶沿挥向飘散（多边形直绘，不转贴图、零重采样）。"""
        for _ in range(n):
            a = ang + random.uniform(-0.9, 0.9)
            spd = self.s(random.uniform(120, 220))
            life = random.uniform(0.4, 0.6)
            self.effects.append({
                "type": "leaf",
                "x": x + math.cos(a) * self.s(40),
                "y": y + math.sin(a) * self.s(40) - self.s(30),
                "vx": math.cos(a) * spd,
                "vy": math.sin(a) * spd - self.s(60),
                "ang": random.uniform(0.0, math.tau),
                "spin": random.uniform(-6.0, 6.0),
                "size": self.s(random.uniform(7, 11)),
                "color": (110, 190, 120),
                "life": life, "max_life": life})

    def _update_bullets(self, dt):
        for b in self.bullets:
            b.update(dt, self.world_w, self.world_h)
            if b.trail and b.alive:
                # 段3 旋转拖尾：每 0.03s 撒一片花瓣粒子（粉色缓落）
                b.trail_acc += dt
                if b.trail_acc >= 0.03:
                    b.trail_acc = 0.0
                    self.particles.append({
                        "x": b.pos[0], "y": b.pos[1],
                        "vx": random.uniform(-30, 30) * self.S,
                        "vy": random.uniform(-10, 50) * self.S,
                        "life": random.uniform(0.25, 0.45), "max_life": 0.45,
                        "color": b.color,
                        "r": random.randint(self.s(2), self.s(4)),
                    })
        self._bullet_vs_mobs()
        self._bullet_vs_boss()
        self.bullets = [b for b in self.bullets if b.alive]

    def _bullet_vs_mobs(self):
        for b in self.bullets:
            if not b.alive:
                continue
            for m in self.mobs:
                if not m.alive or m.uid in b.hit_ids:
                    continue
                if math.hypot(b.pos[0] - m.pos[0], b.pos[1] - m.pos[1]) <= b.radius + m.radius:
                    b.hit_ids.add(m.uid)
                    self._hurt_mob(m, b.dmg, m.pos[0], m.pos[1], color=b.color, spark=6)
                    self._apply_onhit_passive(m)
                    if getattr(b, "star_node", False):
                        # 星璃·流星雨：每枚命中在敌人脚下落 1 颗星位
                        self._stella_add_node(m.pos[0], m.pos[1])
                    if b.star_trace:
                        self._fx_starfall(m.pos[0], m.pos[1], self.s(46), life=0.8)
                    if not b.from_skill:
                        self._try_contract_proc(m.pos[0], m.pos[1])
                        # 樱落·花期：期间普攻每段必叠 SAKURA_CHANNEL_STACK 层（不只段3）
                        if m.alive and self.sakura_kaki_t > 0:
                            for _ in range(S.SAKURA_CHANNEL_STACK):
                                self._sakura_mark_stack(m)
                        # 樱落段3 散华：命中必叠花瓣标记（种花主手段），叠满绽放
                        elif b.mark and m.alive:
                            self._sakura_mark_stack(m)
                    if b.from_skill and m.alive:
                        # 技能飞行物（blade）：命中施加元素副效果 + 叠标记被动
                        if b.onhit:
                            self._apply_combo_secondary(m, b.onhit,
                                                        m.pos[0], m.pos[1],
                                                        use_knock=False)
                        self._apply_mark_stack(m)
                    if b.pierce <= 0:
                        b.alive = False
                        break
                    b.pierce -= 1
        self.mobs = [m for m in self.mobs if m.alive]

    def _bullet_vs_boss(self):
        if self.boss is None or not self.boss.alive:
            return
        bx, by = self.boss.pos
        r = self.boss.radius_px
        for b in self.bullets:
            if not b.alive:
                continue
            if math.hypot(b.pos[0] - bx, b.pos[1] - by) <= b.radius + r:
                b.alive = False
                self._damage_boss(b.dmg, color=b.color)
                if getattr(b, "star_node", False):
                    self._stella_add_node(bx, by)
                if b.star_trace:
                    self._fx_starfall(bx, by, self.s(46), life=0.8)
                if not b.from_skill:
                    self._try_contract_proc(bx, by)
                    if self.boss.alive and self.sakura_kaki_t > 0:
                        for _ in range(S.SAKURA_CHANNEL_STACK):
                            self._sakura_mark_stack(self.boss)
                    elif b.mark and self.boss.alive:
                        self._sakura_mark_stack(self.boss)

    # ------------------------------------------------------------ 小怪
    def _update_mobs(self, dt):
        self.mob_spawn_timer -= dt
        if self.mob_spawn_timer <= 0:
            interval = self._spawn_interval()
            if self.boss is not None:
                interval *= S.BOSS_MOB_SPAWN_SCALE
            self.mob_spawn_timer = interval
            self._spawn_mob()

        # 剧情模式：每 elite_interval 秒刷一只精英怪，直到 Boss 登场
        if (self.mode == "story" and self.boss is None and not self.boss_spawned
                and self.elapsed < self.story_duration):
            self.elite_timer -= dt
            if self.elite_timer <= 0:
                self.elite_timer += self.elite_interval
                self._spawn_elite()

        for m in self.mobs:
            m.update(dt, self.snake.pos, self.world_w, self.world_h, mobs=self.mobs)

        cap = S.MOB_MAX_ALIVE
        overflow = len(self.mobs) - cap
        if overflow > 0:
            px, py = self.snake.pos
            self.mobs.sort(key=lambda m: -math.hypot(m.pos[0] - px, m.pos[1] - py))
            self.mobs = self.mobs[overflow:]

    def _handle_mob_contact(self):
        px, py = self.snake.pos
        pr = self.snake.radius
        for m in self.mobs:
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - px, m.pos[1] - py) <= pr + m.radius:
                m.knockback(self.snake.pos, 180.0)
                dmg = self._snake_hurt(m.eff_atk())
                if dmg:
                    self._on_hurt(dmg)

    # ------------------------------------------------------------ 道具
    def _update_items(self, dt):
        self.item_spawn_timer -= dt
        if self.item_spawn_timer <= 0:
            self.item_spawn_timer = S.ITEM_SPAWN_INTERVAL
            self._spawn_item(near_player=True)
        mr, pr = self.magnet_radius, self.pickup_radius
        px, py = self.snake.pos
        for d in self.drops:
            if d.update(dt, self.snake.pos, mr, pr):
                d.alive = False
                self._apply_drop(d, px, py)
        self.drops = [d for d in self.drops if d.alive]

    def _apply_drop(self, d, hx, hy):
        self.game.audio.play(f"eat_{d.kind}")
        if d.kind == "exp":
            val = max(1, int(round(d.exp_value() * self.stats.get("exp", 1.0))))
            gained = self.snake.gain_exp(val)
            self.score += val * 2
            self._float(f"+{val} EXP", hx, hy, COLOR_EXP)
            if gained:
                self._burst(hx, hy, (255, 226, 140), 24)
                self._float(f"LEVEL {self.snake.level}", hx, hy - self.s(46),
                            COLOR_GOLD, 34)
        elif d.kind == "crystal":
            self.score += 45 * d.tier
            self._float("+能量", hx, hy, (140, 224, 214))
            self._burst(hx, hy, (140, 224, 214), 12)
        elif d.kind == "stardust":
            self.stardust += d.tier
            self.score += 120
            self._float(f"+{d.tier} 星尘", hx, hy, (206, 168, 255))
            self._burst(hx, hy, (206, 168, 255), 16)
        elif d.kind == "heart":
            if self.snake.hp < self.snake.hp_max:
                healed = min(S.HEART_HEAL, self.snake.hp_max - self.snake.hp)
                self.snake.hp += healed
                self._float(f"+{int(round(healed))} HP", hx, hy, COLOR_HP)
            else:
                self.score += 80
                self._float("+80", hx, hy, COLOR_GOLD)
            self._burst(hx, hy, (255, 130, 160), 14)

    # ------------------------------------------------------------ 技能释放
    def cast_skill(self, key):
        """按 key(1-5) 释放对应主动：1=专属大招，2-5=连招组件。"""
        # dash2 二段：一段释放后技能即进冷却，再按同键会被冷却门控拦下；
        # 这里识别「实体仍挂起 + 按键正是 dash2」直接触发瞬移引爆（绕过冷却）。
        if self.dash2 is not None:
            a = self.skills._active_by_key(key)
            if a is not None:
                sid = a.get("id")
                stype = a.get("type") or sid
                if stype == "dash2":
                    ev = self.dash2["ev"]
                    sd = self.stats.get("skilldmg", 1.0) * self.role_skilldmg
                    dmg = int(round(ev.get("dmg", S.DASH2_DMG) * sd))
                    px, py = self.snake.pos
                    self._skill_dash2(ev, px, py, *self.snake.aim_dir, dmg=dmg)
                    self._start_cast_pose(key)
                    self._cancel_atk_recover()
                    return
                if stype == "stella_place":
                    # 星璃·落星二段：引爆落点处星轨（伤害吃技能伤卡/职业系数）
                    ev = self.dash2["ev"]
                    sd = self.stats.get("skilldmg", 1.0) * self.role_skilldmg
                    dmg = int(round(ev.get("det_dmg", S.STELLA_PLACE_DET_DMG) * sd))
                    self._skill_stella_place_det(ev, dmg)
                    self._start_cast_pose(key)
                    self._cancel_atk_recover()
                    return
        ev = self.skills.cast(self.snake.pos, key, self.stats["cdr"])
        if ev:
            # 法师「消耗多」：伤害型技能自伤一小截血（起手就扣，
            # dash2 再按引爆走上面的分支，不会重复计费）
            self._pay_skill_cost(ev.get("hp_cost", 0.0))
            # 技能伤害卡：统一放大大招与连招组件的基础伤害
            sd = self.stats.get("skilldmg", 1.0) * self.role_skilldmg
            if sd != 1.0 and "dmg" in ev:
                ev["dmg"] = int(round(ev["dmg"] * sd))
            self._apply_skill_event(ev)
            self._start_cast_pose(key)
            self._cancel_atk_recover()

    def _start_cast_pose(self, key):
        """记一次释放动作：_draw_snake 按当前形态交叉淡入该技能键的姿势立绘。

        角色没配对应姿势立绘时皮肤表里就是空字典，这里静默跳过。
        """
        am = self.party[self.active_idx]
        form = "human" if (self.char_human and am["form"] == "human") else "lamia"
        if self.char_cast_poses.get(form, {}).get(int(key)):
            a = self.skills._active_by_key(int(key))
            self.cast_pose = {"key": int(key), "t": 0.0,
                              # 吟唱/漩涡引导：姿势保持到读条结束（见 update 里的 hold 分支）
                              "hold": bool(a) and a.get("type") in (
                                  "channel", "tide_vortex", "stella_constellation")}

    def _cast_pose_alpha(self):
        """姿势透明度包络：快淡入 → 保持 → 淡出，smoothstep 让交叉更顺。"""
        cp = self.cast_pose
        if cp is None:
            return 0.0
        k = min(1.0, cp["t"] / CAST_POSE_IN,
                (CAST_POSE_DUR - cp["t"]) / CAST_POSE_OUT)
        if k <= 0.0:
            return 0.0
        return k * k * (3.0 - 2.0 * k)

    def _prewarm_cast_poses(self):
        """enter/切人/resize 时把活跃成员姿势立绘预缩放并缓存两个翻转方向。

        姿势源图约千像素高，若等首次释放那帧才 smoothscale 会掉 1-2 帧——
        正是动作系统不该有的卡顿；缩放成本整体挪到加载期一次付清。
        """
        poses = getattr(self, "char_cast_poses", None)
        if not poses or not getattr(self, "party", None):
            return
        am = self.party[self.active_idx]
        human = bool(self.char_human) and am["form"] == "human"
        fig_h = int(self.CELL * (4.0 if human else 3.5))
        pose_h = int(fig_h * CAST_POSE_H_MULT)
        for rel in poses.get("human" if human else "lamia", {}).values():
            for flip in (False, True):
                self._fig_surf(rel, pose_h, flip)

    def _atk_pose_alpha(self):
        """普攻姿势透明度包络：循环起手快淡入、后摇段淡出；释放姿势优先。"""
        cb = self.atk_combo
        if cb is None or self.cast_pose is not None:
            return 0.0
        if self.ranged_cfg is not None:
            # 远程三段：段开火后快淡入，保持约 7 成段间隔，下一段前淡出
            hold = max(0.12, self.atk_interval * 0.72)
            t = cb["t"]
            if t < hold:
                k = min(1.0, t / ATK_POSE_IN)
            else:
                k = 1.0 - min(1.0, (t - hold) / ATK_POSE_OUT)
            if k <= 0.0:
                return 0.0
            return k * k * (3.0 - 2.0 * k)
        if self.melee_cfg is not None:
            # cfg 驱动：起手快淡入，保持到收势结束，回 idle 段内淡出（无缝循环）
            cfg = self.melee_cfg
            hold_end = cfg["windup"] + cfg["hit_window"] + cb["recover_max"]
            t = cb["t"]
            if t < hold_end:
                k = min(1.0, t / ATK_POSE_IN)
            else:
                k = 1.0 - min(1.0, (t - hold_end) / max(1e-4, cfg["idle_return"]))
        elif cb["recover"] > 0:
            spent = cb["recover_max"] - cb["recover"]
            k = 1.0 - min(1.0, spent / ATK_POSE_OUT)
        else:
            k = min(1.0, cb["t"] / ATK_POSE_IN)
        if k <= 0.0:
            return 0.0
        return k * k * (3.0 - 2.0 * k)

    def _atk_pose_surf(self, human, flip):
        """当前连击段的普攻姿势立绘：1/3 段查表，2 段镜像 1 段（左右爪交替）。"""
        cb = self.atk_combo
        if cb is None:
            return None, flip
        poses = self.char_atk_poses.get("human" if human else "lamia", {})
        stage = cb["stage"]
        if stage == 2:
            return poses.get(1), not flip
        return poses.get(stage), flip

    def _prewarm_atk_poses(self):
        """普攻姿势立绘预缩放缓存（2 段 × 2 翻转），命中帧不产生 smoothscale。"""
        poses = getattr(self, "char_atk_poses", None)
        if not poses or not getattr(self, "party", None):
            return
        am = self.party[self.active_idx]
        human = bool(self.char_human) and am["form"] == "human"
        fig_h = int(self.CELL * (4.0 if human else 3.5))
        pose_h = int(fig_h * CAST_POSE_H_MULT)
        for rel in poses.get("human" if human else "lamia", {}).values():
            for flip in (False, True):
                self._fig_surf(rel, pose_h, flip)

    # ------------------------------------------------------------ 形态自由切换
    def _form_available(self, m):
        """该成员能否切人形态：配了人形态立绘 + 强化层数达到解锁门槛。"""
        if not m["skin"].get("human"):
            return False
        return self.game.save_manager.human_form_unlocked(m["char_id"])

    def _prewarm_figure(self, m):
        """把该成员当前形态的全身立绘预缩放缓存（两个翻转方向）。"""
        skin = m["skin"]
        human = bool(skin.get("human")) and m["form"] == "human"
        img = skin["human"] if human else (skin["full"] or skin["head"])
        fig_h = int(self.CELL * (4.0 if human else 3.5))
        for flip in (False, True):
            self._fig_surf(img, fig_h, flip)

    def _toggle_form(self):
        """V 键在蛇形态 / 人形态之间切换（纯外观，无数值差异）。

        偏好写回存档，与角色详情页的「形态」按钮同源：局内切一次，往后每局沿用。
        未解锁（强化未达标）时只飘字提示当前层数，不改任何状态。
        """
        if self.finished or self.paused or self.card_overlay:
            return False
        am = self.party[self.active_idx]
        sn = am["snake"]
        if not self._form_available(am):
            layer = self.game.save_manager.get_enhance(am["char_id"])
            self._float(f"人形态 · 强化 {S.HUMAN_FORM_ENHANCE_REQ} 层解锁"
                        f"（当前 {layer}）",
                        sn.pos[0], sn.pos[1] - self.s(70), COLOR_TEXT_DIM, 26)
            self.game.audio.play("ui_click", throttle=0.05)
            return False
        nxt = "lamia" if am["form"] == "human" else "human"
        am["form"] = self.game.save_manager.set_form_pref(am["char_id"], nxt)
        # 形态换了：断掉上一形态的姿势动作，并按新形态预热立绘缓存，避免切换那帧掉帧
        self.cast_pose = None
        self.atk_combo = None
        self._prewarm_cast_poses()
        self._prewarm_atk_poses()
        self._prewarm_figure(am)
        self._float("人形态" if am["form"] == "human" else "蛇形态",
                    sn.pos[0], sn.pos[1] - self.s(70), COLOR_GOLD, 30)
        self._burst(sn.pos[0], sn.pos[1], (255, 226, 140), 26)
        self.game.audio.play("eat_heart")
        self.shake = max(self.shake, 0.14)
        return True

    def _apply_skill_event(self, ev):
        t = ev["type"]
        px, py = self.snake.pos
        dx, dy = self.snake.aim_dir
        base_ang = math.atan2(dy, dx)
        if t == "petal_slash":
            # 樱落：前冲斩 + 短护盾（护盾走 shield_t，画泡泡不闪烁）
            dist = ev["dist"] * self.S
            x2 = min(max(px + dx * dist, self.snake.radius), self.world_w - self.snake.radius)
            y2 = min(max(py + dy * dist, self.snake.radius), self.world_h - self.snake.radius)
            self.game.audio.play("skill_dash")
            self._damage_segment(px, py, x2, y2, ev["dmg"], (255, 150, 190))
            if ev.get("double"):
                # 满级：紧接着补一段 50% 伤害的斩击（同一冲刺路径）
                self._damage_segment(px, py, x2, y2, max(1, ev["dmg"] // 2),
                                     (255, 190, 215))
            self.snake.pos[0], self.snake.pos[1] = x2, y2
            self.snake.shield_t = max(self.snake.shield_t, ev["shield"])
            self._burst(x2, y2, (255, 150, 190), 32)
            self._fx_trail(px, py, x2, y2, (255, 150, 190))
            self._fx_trail(px, py, x2, y2, (255, 200, 225), life=0.42)
            self.shake = max(self.shake, 0.36)
            self._fx_ultimate(x2, y2, (255, 150, 190))
            self._float(ev.get("name", "落樱·绯斩"), px, py - self.s(54), (255, 150, 190), 30)
        elif t == "gale_dash":
            # 薄荷：多段突进 + 移速爆发
            self.game.audio.play("skill_dash")
            cx, cy = px, py
            n = max(1, ev["count"])
            for i in range(n):
                ang = base_ang + (i - (n - 1) / 2.0) * 0.4
                step = ev["dist"] * self.S
                nx = min(max(cx + math.cos(ang) * step, self.snake.radius),
                         self.world_w - self.snake.radius)
                ny = min(max(cy + math.sin(ang) * step, self.snake.radius),
                         self.world_h - self.snake.radius)
                self._damage_segment(cx, cy, nx, ny, ev["dmg"], (150, 240, 190))
                self._fx_trail(cx, cy, nx, ny, (150, 240, 190), life=0.26)
                self._burst(nx, ny, (150, 240, 190), 12)
                cx, cy = nx, ny
            self.snake.pos[0], self.snake.pos[1] = cx, cy
            self._fx_ultimate(cx, cy, (150, 240, 190))
            self._float("疾风连闪", px, py - self.s(54), (150, 240, 190), 30)
            self.shake = max(self.shake, 0.25)
        elif t == "tide_surge":
            # 潮汐：环形水浪 击退+减速+伤害
            r = ev["radius"] * self.S
            self.game.audio.play("skill_storm")
            self._fx_ring(px, py, r, (120, 200, 255), life=0.5)
            for m in list(self.mobs):
                if not m.alive:
                    continue
                if math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                    m.apply_slow(ev["slow_mult"], ev["slow_time"])
                    m.knockback((px, py), ev["knock"])
                    self._hurt_mob(m, ev["dmg"], m.pos[0], m.pos[1],
                                   color=(120, 200, 255), spark=8)
            self.mobs = [m for m in self.mobs if m.alive]
            if self.boss is not None and self.boss.alive:
                bx, by = self.boss.pos
                if math.hypot(bx - px, by - py) <= r + self.boss.radius_px:
                    self._damage_boss(ev["dmg"], color=(120, 200, 255))
            self._fx_ultimate(px, py, (120, 200, 255))
            self._float("沧澜涌潮", px, py - self.s(58), (120, 200, 255), 32)
            self.shake = max(self.shake, 0.35)
        elif t == "ember_lash":
            # 绯焰：扇形火焰鞭 + 灼烧
            self.game.audio.play("skill_storm")
            rng = ev["range"] * self.S
            half = ev["angle"]
            self._fx_fan(px, py, rng, base_ang, half, (255, 140, 80), life=0.4)
            for m in list(self.mobs):
                if not m.alive:
                    continue
                vx, vy = m.pos[0] - px, m.pos[1] - py
                d0 = math.hypot(vx, vy)
                if d0 <= rng + m.radius:
                    da = abs((math.atan2(vy, vx) - base_ang + math.pi) % math.tau - math.pi)
                    if d0 <= m.radius + self.s(12) or da <= half:
                        m.apply_burn(ev["burn_dps"], ev["burn_time"])
                        self._hurt_mob(m, ev["dmg"], m.pos[0], m.pos[1],
                                       color=(255, 140, 80), spark=8)
            self.mobs = [m for m in self.mobs if m.alive]
            if self.boss is not None and self.boss.alive:
                bx, by = self.boss.pos
                if math.hypot(bx - px, by - py) <= rng + self.boss.radius_px:
                    self._damage_boss(ev["dmg"], color=(255, 140, 80))
            self._fx_ultimate(px, py, (255, 140, 80))
            self._float("燎原火鞭", px, py - self.s(58), (255, 140, 80), 32)
            self.shake = max(self.shake, 0.32)
        elif t == "star_chain":
            # 星璃：多枚追踪星弹，锁定不同敌人
            spd = ev["speed"] * self.S
            targets = self._nearest_mobs(ev["count"])
            for i in range(ev["count"]):
                if i < len(targets):
                    m = targets[i]
                    ax, ay = m.pos[0] - px, m.pos[1] - py
                else:
                    ang = base_ang + (i - (ev["count"] - 1) / 2.0) * 0.5
                    ax, ay = math.cos(ang), math.sin(ang)
                d0 = math.hypot(ax, ay) or 1.0
                self.bullets.append(PlayerBullet(
                    (px, py), (ax / d0 * spd, ay / d0 * spd), ev["dmg"],
                    self.s(10), life=ev["life"], color=(190, 150, 255),
                    pierce=ev.get("pierce", 1)))
            self.game.audio.play("skill_bloom")
            self._burst(px, py, (190, 150, 255), 20)
            self._fx_starfall(px, py, self.s(130))
            self._fx_ultimate(px, py, (190, 150, 255))
            self._float("星陨链", px, py - self.s(58), (190, 150, 255), 32)
        elif t == "moon_ward":
            # 月见：穿透月光束 + 护盾
            length = ev["length"] * self.S
            halfw = ev["width"] * self.S * 0.5
            x2, y2 = px + dx * length, py + dy * length
            self.game.audio.play("skill_shield")
            self._fx_beam(px, py, x2, y2, halfw * 2, (200, 210, 255), life=0.35)
            for m in list(self.mobs):
                if not m.alive:
                    continue
                if _seg_dist(m.pos[0], m.pos[1], px, py, x2, y2) <= halfw + m.radius:
                    self._hurt_mob(m, ev["dmg"], m.pos[0], m.pos[1],
                                   color=(200, 210, 255), spark=8)
            self.mobs = [m for m in self.mobs if m.alive]
            if self.boss is not None and self.boss.alive:
                bx, by = self.boss.pos
                if _seg_dist(bx, by, px, py, x2, y2) <= halfw + self.boss.radius_px:
                    self._damage_boss(ev["dmg"], color=(200, 210, 255))
            self.snake.shield_t = max(self.snake.shield_t, ev["shield"])
            self._fx_ultimate(px, py, (200, 210, 255))
            self._float("月华结界", px, py - self.s(58), (200, 210, 255), 32)
            self.shake = max(self.shake, 0.3)
        elif t == "mark":
            # 花印/标记：范围内敌人易伤 + 少量即时伤害
            r = ev["radius"] * self.S
            color = ev.get("color", (255, 180, 210))
            self.game.audio.play("skill_bloom")
            self._fx_rune(px, py, r, color, life=0.5)   # 标记=旋转魔法阵
            for m in list(self.mobs):
                if not m.alive:
                    continue
                if math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                    m.apply_mark(ev["amp"], ev["time"], ev.get("max_stacks", 1))
                    self._apply_combo_secondary(m, ev, px, py, use_knock=False)
                    self._hurt_mob(m, ev["dmg"], m.pos[0], m.pos[1], color=color, spark=6)
            self.mobs = [m for m in self.mobs if m.alive]
            if self.boss is not None and self.boss.alive:
                bx, by = self.boss.pos
                if math.hypot(bx - px, by - py) <= r + self.boss.radius_px:
                    self.boss.apply_mark(ev["amp"], ev["time"], ev.get("max_stacks", 1))
                    self._damage_boss(ev["dmg"], color=color)
            self._fx_element(ev.get("element", ""), px, py, r)
            self._float(ev.get("name", "标记"), px, py - self.s(58), color, 30)
        elif t == "pull":
            # 引/聚怪：把范围内敌人拉向自己并减速
            r = ev["radius"] * self.S
            color = ev.get("color", (255, 160, 200))
            root_mult = ev.get("root_mult")          # 满级：附带短时定身
            root_time = ev.get("root_time", 0.0)
            self.game.audio.play("skill_storm")
            self._fx_vortex(px, py, r, color, life=0.55)  # 聚怪=内卷漩涡
            for m in list(self.mobs):
                if not m.alive:
                    continue
                if math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                    m.apply_slow(ev["slow_mult"], ev["slow_time"])
                    if root_mult is not None:
                        m.apply_slow(root_mult, root_time)
                    m.knockback((px, py), -ev["strength"])   # 负强度=拉向玩家
                    self._apply_combo_secondary(m, ev, px, py, use_knock=False)
                    self._hurt_mob(m, ev["dmg"], m.pos[0], m.pos[1], color=color, spark=6)
            self.mobs = [m for m in self.mobs if m.alive]
            self._fx_element(ev.get("element", ""), px, py, r)
            self._float(ev.get("name", "聚怪"), px, py - self.s(58), color, 30)
            self.shake = max(self.shake, 0.22)
        elif t == "burst":
            # 引爆：消费敌人身上的状态，按状态数量追加伤害
            r = ev["radius"] * self.S
            color = ev.get("color", (255, 120, 170))
            self.game.audio.play("skill_storm")
            self._fx_nova(px, py, r, color, life=0.6)   # 引爆=放射冲击波
            tfull = ev.get("mark_time_full", 0.0) or 1.0
            per_stack = ev.get("per_stack", 0.0)
            time_bonus = ev.get("time_bonus", 0.0)
            for m in list(self.mobs):
                if not m.alive:
                    continue
                if math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                    # 先统计状态数与标记层数/剩余时间，再清状态，最后结算伤害（避免与标记易伤双算）
                    status = ((1 if m.mark_t > 0 else 0) + (1 if m.slow_t > 0 else 0)
                              + (1 if m.burn_t > 0 else 0))
                    stacks = getattr(m, "mark_stacks", 0)
                    tratio = min(1.0, m.mark_t / tfull) if m.mark_t > 0 else 0.0
                    bonus = (ev["status_bonus"] * status
                             + per_stack * stacks + time_bonus * tratio)
                    dmg = ev["dmg"] * (1.0 + bonus)
                    m.mark_t = 0.0
                    m.mark_amp = 0.0
                    m.mark_stacks = 0
                    m.slow_t = 0.0
                    m.slow_mult = 1.0
                    m.burn_t = 0.0
                    m.burn_dps = 0.0
                    m.burn_acc = 0.0
                    self._hurt_mob(m, int(round(dmg)), m.pos[0], m.pos[1],
                                   color=color, spark=12)
                    if m.alive:
                        self._apply_combo_secondary(m, ev, px, py, use_knock=True)
            self.mobs = [m for m in self.mobs if m.alive]
            if self.boss is not None and self.boss.alive:
                bx, by = self.boss.pos
                if math.hypot(bx - px, by - py) <= r + self.boss.radius_px:
                    stacks = getattr(self.boss, "mark_stacks", 0)
                    tratio = (min(1.0, self.boss.mark_t / tfull)
                              if self.boss.mark_t > 0 else 0.0)
                    bdmg = ev["dmg"] * (1.0 + per_stack * stacks + time_bonus * tratio)
                    self.boss.clear_mark()
                    self._damage_boss(int(round(bdmg)), color=color)
            self._fx_element(ev.get("element", ""), px, py, r)
            if ev.get("starfall"):
                for o in self._nearest_mobs(3):
                    self._fx_starfall(o.pos[0], o.pos[1], self.s(60))
                    self._hurt_mob(o, max(1, int(ev["dmg"] * 0.5)),
                                   o.pos[0], o.pos[1], color=(190, 150, 255), spark=8)
                self.mobs = [x for x in self.mobs if x.alive]
            if ev.get("bloom"):
                self._fx_petals(px, py, r, (255, 150, 190))
            self._float(ev.get("name", "引爆"), px, py - self.s(58), color, 32)
            self.shake = max(self.shake, 0.38)
        elif t == "rally":
            # 鼓舞：短时提升自身攻击与攻速（增益挂在场景上）
            color = ev.get("color", (255, 200, 220))
            self.game.audio.play("skill_shield")
            self.rally_t = ev["time"]
            self.rally_atk = ev["atk"]
            self.rally_atkspd = ev["atkspd"]
            self.rally_armor = ev.get("armor_bonus", 0.0)  # 满级：增益期额外减伤
            # 元素副效果：风=额外攻速 / 水·月=护盾 / 火=灼烧光环 / 星=减CD / 月=回血
            if ev.get("speed_bonus"):
                self.rally_atkspd += ev["speed_bonus"]
            if ev.get("shield"):
                self.snake.shield_t = max(self.snake.shield_t, ev["shield"])
            if ev.get("heal"):
                healed = min(max(0.0, self.snake.hp_max - self.snake.hp),
                             self.snake.hp_max * float(ev["heal"]))
                if healed > 0:
                    self.snake.hp += healed
                    self._float(f"+{int(round(healed))} HP", px, py - self.s(40),
                                COLOR_HP, 24)
            if ev.get("cdr_bonus"):
                self.skills.reduce_cd_frac(ev["cdr_bonus"])
            if ev.get("burn_aura"):
                aura_r = self.s(190)
                for m in list(self.mobs):
                    if (m.alive and math.hypot(m.pos[0] - px, m.pos[1] - py)
                            <= aura_r + m.radius):
                        m.apply_burn(S.EMBER_BURN_DPS, 3.0)
            self.rally_color = color
            self._fx_aura(px, py, self.s(120), color, life=0.7)  # 鼓舞=上升光柱
            self._fx_element(ev.get("element", ""), px, py, self.s(130))
            self._burst(px, py, color, 20)
            self._float(ev.get("name", "鼓舞"), px, py - self.s(58), color, 30)
        elif t == "dash2":
            self._skill_dash2(ev, px, py, dx, dy)
        elif t == "detonate":
            self._skill_detonate(ev, px, py)
        elif t == "gather":
            self._skill_gather(ev, px, py, dx, dy)
        elif t == "blade":
            self._skill_blade(ev, px, py, base_ang)
        elif t == "channel":
            self._skill_channel(ev, px, py)
        elif t == "tide_handoff":
            self._skill_handoff(ev, px, py)
        elif t == "tide_zone":
            self._skill_zone(ev, px, py)
        elif t == "tide_vortex":
            self._skill_vortex(ev, px, py)
        elif t == "tide_contract":
            self._skill_contract(ev, px, py)
        elif t == "tide_domain":
            self._skill_domain(ev, px, py)
        elif t == "sakura_dash2":
            self._skill_sakura_dash2(ev, px, py, dx, dy)
        elif t == "sakura_detonate":
            self._skill_sakura_detonate(ev, px, py)
        elif t == "sakura_gather":
            self._skill_sakura_gather(ev, px, py, dx, dy)
        elif t == "sakura_blade":
            self._skill_sakura_blade(ev, px, py, base_ang)
        elif t == "sakura_channel":
            self._skill_sakura_channel(ev, px, py)
        elif t == "flare_scatter":
            self._skill_flare_scatter(ev, px, py, base_ang)
        elif t == "flare_trail":
            self._skill_flare_trail(ev, px, py, dx, dy)
        elif t == "flare_fuse":
            self._skill_flare_fuse(ev, px, py)
        elif t == "flare_ring":
            self._skill_flare_ring(ev, px, py)
        elif t == "flare_burst":
            self._skill_flare_burst(ev, px, py)
        elif t == "stella_place":
            self._skill_stella_place(ev, px, py, dx, dy)
        elif t == "stella_link":
            self._skill_stella_link(ev, px, py)
        elif t == "stella_well":
            self._skill_stella_well(ev, px, py, dx, dy)
        elif t == "stella_shower":
            self._skill_stella_shower(ev, px, py, base_ang)
        elif t == "stella_constellation":
            self._skill_stella_constellation(ev, px, py)

    def _damage_segment(self, x1, y1, x2, y2, dmg, color, mark=False):
        reach = self.s(18)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if _seg_dist(m.pos[0], m.pos[1], x1, y1, x2, y2) <= m.radius + reach:
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=8)
                self._apply_onhit_passive(m)
                if mark and m.alive:
                    self._apply_mark_stack(m)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if _seg_dist(bx, by, x1, y1, x2, y2) <= self.boss.radius_px + reach:
                self._damage_boss(dmg, color=color)

    # -------------------------------------------------- 通用骨架技能（新）
    def _skill_dash2(self, ev, px, py, dx, dy, dmg=None):
        """二段位移：一段前冲并留下元素实体；再按瞬移引爆，到期自爆小伤害。
        风系特化：一段不前冲，而是刮出一阵有实体的风向前飞；再按瞬移到风所在
        位置 AoE，不按则风飞到尽头四散 AoE。
        dmg：再按引爆的伤害（cast_skill 已算好技能伤加成），缺省取 ev 原值。"""
        color = ev.get("color", (255, 255, 255))
        if dmg is None:
            dmg = ev.get("dmg", S.DASH2_DMG)
        if self.dash2 is None:
            dist = ev.get("dist", S.DASH2_DIST) * self.S
            if ev.get("element", "") == "风":
                spd = ev.get("fly_speed", S.DASH2_WIND_SPEED) * self.S
                life = ev.get("mark_t", S.DASH2_MARK_T)
                self.game.audio.play("skill_dash")
                self._burst(px, py, color, 12)
                self.dash2 = {
                    "x": px + dx * self.s(24), "y": py + dy * self.s(24),
                    "vx": dx * spd, "vy": dy * spd,
                    "t": life, "total": life,
                    "element": "风", "color": color, "ev": ev,
                    "radius": ev.get("radius", S.DASH2_RADIUS) * self.S,
                    "fly": True, "traveled": 0.0, "max_travel": dist,
                    "fx": ev.get("sid"),
                    "hit": set(),
                }
                self._float(ev.get("name", "位移"), px, py - self.s(54), color, 28)
                return
            x2 = min(max(px + dx * dist, self.snake.radius),
                     self.world_w - self.snake.radius)
            y2 = min(max(py + dy * dist, self.snake.radius),
                     self.world_h - self.snake.radius)
            self.game.audio.play("skill_dash")
            self._damage_segment(px, py, x2, y2, ev.get("dmg", 0), color, mark=True)
            self.snake.pos[0], self.snake.pos[1] = x2, y2
            self._fx_trail(px, py, x2, y2, color)
            self._burst(x2, y2, color, 18)
            life = ev.get("mark_t", S.DASH2_MARK_T)
            self.dash2 = {
                "x": x2, "y": y2, "t": life, "total": life,
                "element": ev.get("element", ""), "color": color, "ev": ev,
                "radius": ev.get("radius", S.DASH2_RADIUS) * self.S,
            }
            self._float(ev.get("name", "位移"), px, py - self.s(54), color, 28)
        else:
            d = self.dash2
            self.dash2 = None
            self.game.audio.play("skill_dash")
            self._fx_trail(px, py, d["x"], d["y"], color)
            self.snake.pos[0], self.snake.pos[1] = d["x"], d["y"]
            self._dash2_explode(d, dmg)
            self.shake = max(self.shake, 0.3)

    def _dash2_explode(self, d, dmg):
        """二段位移落点的范围元素伤害（再按引爆 / 到期自爆共用）。"""
        x, y = d["x"], d["y"]
        r = d["radius"]
        color = d["color"]
        ev = d["ev"]
        self._fx_nova(x, y, r, color, life=0.5)
        self._fx_element(d.get("element", ""), x, y, r)
        self._spawn_fx_sprite(d.get("fx"), x, y, max(self.s(70), r * 1.4),
                              life=0.45, expand=1.7, spin=3.0)
        self._burst(x, y, color, 20)
        self.game.audio.play("skill_storm", throttle=0.05)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - x, m.pos[1] - y) <= r + m.radius:
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=8)
                if m.alive:
                    self._apply_combo_secondary(m, ev, x, y, use_knock=True)
                    self._apply_mark_stack(m)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - x, by - y) <= r + self.boss.radius_px:
                self._damage_boss(dmg, color=color)

    def _update_dash2(self, dt):
        d = self.dash2
        if d is None:
            return
        d["t"] -= dt
        if d.get("fly"):
            # 实体风向前飞：移动 + 沿途刮伤；撞世界边界或飞满距离即视为到尽头
            step = math.hypot(d["vx"], d["vy"]) * dt
            nx = d["x"] + d["vx"] * dt
            ny = d["y"] + d["vy"] * dt
            r = self.snake.radius
            hit_wall = not (r < nx < self.world_w - r and r < ny < self.world_h - r)
            d["x"] = min(max(nx, r), self.world_w - r)
            d["y"] = min(max(ny, r), self.world_h - r)
            d["traveled"] += step
            self._wind_scrape(d)
            if hit_wall or d["traveled"] >= d["max_travel"]:
                d["t"] = min(d["t"], 0.0)
        if d["t"] <= 0:
            self.dash2 = None
            if d.get("stella"):
                # 星璃·落星二段窗口超时：星轨余晖散掉，不爆炸（落点星位仍在）
                self._fx_ring(d["x"], d["y"], self.s(46), (190, 150, 255), life=0.3)
                return
            d["radius"] = d["radius"] * 0.75      # 未按再按：实体四散，小范围伤害
            self._dash2_explode(d, d["ev"].get("expire_dmg", S.DASH2_EXPIRE_DMG))

    def _wind_scrape(self, d):
        """实体风飞行途中刮到敌人：小额伤害 + 叠标记（同一怪只刮一次）。"""
        x, y = d["x"], d["y"]
        r = d["radius"] * 0.6
        color = d["color"]
        dmg = max(1, int(round(d["ev"].get("dmg", S.DASH2_DMG) * S.DASH2_WIND_SCRAPE)))
        for m in list(self.mobs):
            if not m.alive or m in d["hit"]:
                continue
            if math.hypot(m.pos[0] - x, m.pos[1] - y) <= r + m.radius:
                d["hit"].add(m)
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=4)
                if m.alive:
                    self._apply_mark_stack(m)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive and self.boss not in d["hit"]:
            bx, by = self.boss.pos
            if math.hypot(bx - x, by - y) <= r + self.boss.radius_px:
                d["hit"].add(self.boss)
                self._damage_boss(dmg, color=color)

    def _skill_detonate(self, ev, px, py):
        """引爆：范围内有标记者按层数追加伤害并清标记；无标记者叠一层。"""
        r = ev.get("radius", S.DETONATE_RADIUS) * self.S
        color = ev.get("color", (255, 120, 170))
        per_stack = ev.get("per_stack", S.DETONATE_PER_STACK)
        max_stacks = ev.get("max_stacks", S.MARKPASSIVE_STACKS)
        self.game.audio.play("skill_storm")
        self._fx_nova(px, py, r, color, life=0.6)
        self._spawn_fx_sprite(ev.get("sid"), px, py, max(self.s(80), r * 1.5),
                              life=0.55, expand=1.5, spin=2.0)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                stacks = getattr(m, "mark_stacks", 0)
                if stacks > 0 and m.mark_t > 0:
                    dmg = ev["dmg"] * (1.0 + per_stack * stacks)
                    m.clear_mark()
                    self._hurt_mob(m, int(round(dmg)), m.pos[0], m.pos[1],
                                   color=color, spark=12)
                    if m.alive:
                        self._apply_combo_secondary(m, ev, px, py, use_knock=True)
                else:
                    self._hurt_mob(m, ev["dmg"], m.pos[0], m.pos[1],
                                   color=color, spark=6)
                    if m.alive:
                        self._apply_combo_secondary(m, ev, px, py, use_knock=False)
                        self._apply_mark_stack(m, max_stacks=max_stacks)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - px, by - py) <= r + self.boss.radius_px:
                stacks = getattr(self.boss, "mark_stacks", 0)
                bdmg = (ev["dmg"] * (1.0 + per_stack * stacks)
                        if stacks > 0 and self.boss.mark_t > 0 else ev["dmg"])
                self.boss.clear_mark()
                self._damage_boss(int(round(bdmg)), color=color)
        self._fx_element(ev.get("element", ""), px, py, r)
        self._float(ev.get("name", "引爆"), px, py - self.s(58), color, 30)
        self.shake = max(self.shake, 0.34)

    def _skill_gather(self, ev, px, py, dx=0.0, dy=0.0):
        """聚怪：把范围内敌人拉向自己 + 减速 + 叠一层标记。风系改为向前阵风。"""
        r = ev.get("radius", S.GATHER_RADIUS) * self.S
        color = ev.get("color", (255, 160, 200))
        max_stacks = ev.get("max_stacks", S.MARKPASSIVE_STACKS)
        root_mult = ev.get("root_mult")
        root_time = ev.get("root_time", 0.0)
        if ev.get("element", "") == "风":
            self._spawn_gust(ev, px, py, dx, dy, r, color)
            return
        self.game.audio.play("skill_storm")
        self._fx_vortex(px, py, r, color, life=0.55)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                m.apply_slow(ev["slow_mult"], ev["slow_time"])
                if root_mult is not None:
                    m.apply_slow(root_mult, root_time)
                m.knockback((px, py), -ev["strength"])
                self._apply_combo_secondary(m, ev, px, py, use_knock=False)
                self._hurt_mob(m, ev["dmg"], m.pos[0], m.pos[1], color=color, spark=6)
                if m.alive:
                    self._apply_mark_stack(m, max_stacks=max_stacks)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - px, by - py) <= r + self.boss.radius_px:
                self._damage_boss(ev["dmg"], color=color)
        self._fx_element(ev.get("element", ""), px, py, r)
        self._float(ev.get("name", "聚怪"), px, py - self.s(58), color, 30)
        self.shake = max(self.shake, 0.22)

    def _spawn_gust(self, ev, px, py, dx, dy, r, color):
        """风系聚怪：刮出一道可见的阵风实体向前飞（取代旧瞬发走廊）。
        飞行途中刮伤路径上的敌人，飞到尽头/撞墙后化作漩涡把周围敌人
        聚到风消失处 + 减速 + 叠标记。贴图程序化生成，各场景背景通用。"""
        spd = S.GATHER_WIND_SPEED * self.S
        self.gusts.append({
            "x": px + dx * self.s(26), "y": py + dy * self.s(26),
            "vx": dx * spd, "vy": dy * spd,
            "traveled": 0.0, "max_travel": max(self.s(120), r),
            "half": r * 0.5, "color": color, "ev": ev,
            "hit": set(), "spin": random.uniform(0.0, math.tau),
            "fx": ev.get("sid"),
        })
        self.game.audio.play("skill_storm")
        self._burst(px, py, color, 10)
        self._float(ev.get("name", "聚怪"), px, py - self.s(58), color, 30)

    def _update_gusts(self, dt):
        """阵风每帧：前飞 + 沿途刮伤 + 拖尾风屑；飞满距离或撞墙即到期聚怪。"""
        if not self.gusts:
            return
        rr = self.snake.radius
        for g in self.gusts:
            step = math.hypot(g["vx"], g["vy"]) * dt
            nx = g["x"] + g["vx"] * dt
            ny = g["y"] + g["vy"] * dt
            g["spin"] += dt * 9.0
            hit_wall = not (rr < nx < self.world_w - rr
                            and rr < ny < self.world_h - rr)
            g["x"] = min(max(nx, rr), self.world_w - rr)
            g["y"] = min(max(ny, rr), self.world_h - rr)
            g["traveled"] += step
            self._gust_scrape(g)
            # 拖尾风屑：少量粒子让飞行轨迹更可读
            if random.random() < 0.6:
                self.particles.append({
                    "x": g["x"] + random.uniform(-g["half"], g["half"]) * 0.6,
                    "y": g["y"] + random.uniform(-g["half"], g["half"]) * 0.6,
                    "vx": -g["vx"] * 0.12, "vy": -g["vy"] * 0.12,
                    "life": 0.3, "max_life": 0.3,
                    "r": max(1, self.s(3)), "color": g["color"]})
            if hit_wall or g["traveled"] >= g["max_travel"]:
                g["done"] = True
        live = []
        for g in self.gusts:
            if g.get("done"):
                self._gust_arrive(g)
            else:
                live.append(g)
        self.gusts = live

    def _gust_scrape(self, g):
        """阵风飞行途中刮到敌人：小额伤害（同一怪只刮一次）。"""
        x, y = g["x"], g["y"]
        r = g["half"]
        color = g["color"]
        dmg = max(1, int(round(g["ev"].get("dmg", S.GATHER_DMG)
                               * S.GATHER_WIND_SCRAPE)))
        for m in list(self.mobs):
            if not m.alive or m in g["hit"]:
                continue
            if math.hypot(m.pos[0] - x, m.pos[1] - y) <= r + m.radius:
                g["hit"].add(m)
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=4)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive and self.boss not in g["hit"]:
            bx, by = self.boss.pos
            if math.hypot(bx - x, by - y) <= r + self.boss.radius_px:
                g["hit"].add(self.boss)
                self._damage_boss(dmg, color=color)

    def _gust_arrive(self, g):
        """阵风飞到尽头：化作漩涡把周围敌人聚到风消失处 + 减速 + 叠标记。"""
        ev = g["ev"]
        x, y = g["x"], g["y"]
        r = g["half"] * 1.4
        color = g["color"]
        max_stacks = ev.get("max_stacks", S.MARKPASSIVE_STACKS)
        root_mult = ev.get("root_mult")
        root_time = ev.get("root_time", 0.0)
        self.game.audio.play("skill_storm", throttle=0.05)
        self._fx_vortex(x, y, r, color, life=0.55)
        self._spawn_fx_sprite(ev.get("sid"), x, y, max(self.s(80), r * 1.5),
                              life=0.5, expand=1.6, spin=2.5)
        self._burst(x, y, color, 16)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - x, m.pos[1] - y) <= r + m.radius:
                m.apply_slow(ev["slow_mult"], ev["slow_time"])
                if root_mult is not None:
                    m.apply_slow(root_mult, root_time)
                m.knockback((x, y), -ev["strength"])   # 负强度=拉向风尽头
                self._apply_combo_secondary(m, ev, x, y, use_knock=False)
                self._hurt_mob(m, ev["dmg"], m.pos[0], m.pos[1],
                               color=color, spark=6)
                if m.alive:
                    self._apply_mark_stack(m, max_stacks=max_stacks)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - x, by - y) <= r + self.boss.radius_px:
                self._damage_boss(ev["dmg"], color=color)
        self._fx_element(ev.get("element", ""), x, y, r)
        self.shake = max(self.shake, 0.22)

    def _skill_blade(self, ev, px, py, base_ang):
        """飞行物：甩出 N 枚元素刃，命中叠标记 + 伤害（元素副效果随弹携带）。"""
        color = ev.get("color", (255, 255, 255))
        el = ev.get("element", "")
        spd = ev.get("speed", S.BLADE_SPEED) * self.S
        n = max(1, ev.get("count", S.BLADE_COUNT))
        life = ev.get("life", S.BLADE_LIFE)
        pierce = ev.get("pierce", 0)
        onhit = {k: ev[k] for k in ("slow_mult", "slow_time", "freeze_time",
                                    "burn_dps", "burn_time", "stun_time",
                                    "weaken_mult", "weaken_time")
                 if k in ev}
        self.game.audio.play("skill_bloom")
        for i in range(n):
            ang = base_ang + (i - (n - 1) / 2.0) * 0.42
            self.bullets.append(PlayerBullet(
                (px, py), (math.cos(ang) * spd, math.sin(ang) * spd), ev["dmg"],
                self.s(9), life=life, color=color, pierce=pierce,
                element=el, from_skill=True, onhit=onhit, fx=ev.get("sid")))
        self._burst(px, py, color, 16)
        self._float(ev.get("name", "飞行物"), px, py - self.s(54), color, 28)

    def _skill_channel(self, ev, px, py):
        """吟唱：开始读条（可移动、不被打断），读满后施加增益。"""
        color = ev.get("color", (255, 200, 220))
        self.game.audio.play("skill_shield")
        self.channel = {"t": 0.0, "total": max(0.05, ev.get("time", S.CHANNEL_TIME)),
                        "ev": ev, "color": color, "fx": ev.get("sid")}
        self.atk_combo = None   # 吟唱接管动作：清掉进行中的近战连击，避免姿势/节拍打架
        self._fx_aura(px, py, self.s(110), color, life=0.5)
        self._float(ev.get("name", "吟唱") + " 吟唱中…", px, py - self.s(58), color, 26)

    def _update_channel(self, dt):
        ch = self.channel
        if ch is None:
            return
        ch["t"] += dt
        if ch.get("vortex"):
            self._vortex_tick(ch, dt)
        if ch["t"] >= ch["total"]:
            self.channel = None
            if ch.get("vortex"):
                self._finish_vortex(ch["ev"], ch["color"])
            elif ch.get("stella_const"):
                self._finish_constellation(ch["ev"], ch["color"])
            else:
                self._finish_channel(ch["ev"], ch["color"])

    def _finish_channel(self, ev, color):
        """读条结束：施加增益（复用 rally_* 驱动攻击/攻速），并落元素副效果。"""
        px, py = self.snake.pos
        self.rally_t = ev.get("buff_time", S.CHANNEL_BUFF_TIME)
        self.rally_atk = ev.get("atk", S.CHANNEL_ATK)
        self.rally_atkspd = ev.get("atkspd", S.CHANNEL_ATKSPD)
        self.rally_armor = ev.get("armor_bonus", 0.0)
        if ev.get("atk_bonus"):
            self.rally_atk += ev["atk_bonus"]
        if ev.get("speed_bonus"):
            self.rally_atkspd += ev["speed_bonus"]
        if ev.get("shield"):
            self.snake.grant_shield(ev["shield"], S.SHIELD_POOL)
        if ev.get("heal"):
            healed = min(max(0.0, self.snake.hp_max - self.snake.hp),
                         self.snake.hp_max * float(ev["heal"]))
            if healed > 0:
                self.snake.hp += healed
                self._float(f"+{int(round(healed))} HP", px, py - self.s(40),
                            COLOR_HP, 24)
        if ev.get("cdr_bonus"):
            self.skills.reduce_cd_frac(ev["cdr_bonus"])
        if ev.get("burn_aura"):
            aura_r = self.s(190)
            for m in list(self.mobs):
                if (m.alive and math.hypot(m.pos[0] - px, m.pos[1] - py)
                        <= aura_r + m.radius):
                    m.apply_burn(S.EMBER_BURN_DPS, 3.0)
        self.rally_color = color
        self._fx_aura(px, py, self.s(120), color, life=0.7)
        self._fx_element(ev.get("element", ""), px, py, self.s(130))
        self._spawn_fx_sprite(ev.get("sid"), px, py, self.s(170),
                              life=0.6, expand=1.8, spin=2.0)
        self._burst(px, py, color, 20)
        self.game.audio.play("skill_shield")
        self._float(ev.get("name", "鼓舞") + " 增益!", px, py - self.s(58), color, 30)

    # -------------------------------------------------- 潮汐·切人五技能
    # 水属性坦克：场上同时只有一名角色，技能全部围绕「切人」联动。
    # 循环：铺水域(②)→上盾(①)→切走(盾转移)→队友站水域输出+普攻触发契约(④)
    #      →切回引爆水域(③)→大招刷新水域+湿身(⑤)→重开。
    def _skill_handoff(self, ev, px, py):
        """① 潮汐交接：给自己套水幕护盾（吸收量=潮汐最大生命×shield_pct），
        记录盾源与转移比例；切走时由 _switch_to 把剩余盾量转移给登场者。"""
        color = ev.get("color", (150, 215, 255))
        mult = 1.0 + min(S.SHIELD_STAT_CAP, self.stats.get("shield", 0.0))
        pool = self.snake.hp_max * ev["shield_pct"] * mult
        self.snake.grant_shield(ev["time"] * mult, pool)
        self.handoff_holder = self.party[self.active_idx]
        self.handoff_transfer = ev.get("transfer", S.TIDE_HANDOFF_TRANSFER)
        self.game.audio.play("skill_shield")
        self._fx_ring(px, py, self.s(96), color, life=0.5)
        self._burst(px, py, color, 18)
        self._float(ev.get("name", "潮汐交接"), px, py - self.s(58), color, 30)

    def _skill_zone(self, ev, px, py):
        """② 涌潮：在脚下铺开一片水域（全链地基，不随切人消失）。
        域内敌人持续减速，己方享移速/减伤（见 player_speed 与 _snake_hurt）。"""
        r = ev["radius"] * self.S
        self.zones.append({"x": px, "y": py, "r": r,
                           "t": ev["time"], "max_t": ev["time"],
                           "enemy_slow": ev["enemy_slow"]})
        color = ev.get("color", (120, 200, 255))
        self.game.audio.play("skill_storm")
        self._fx_ring(px, py, r, color, life=0.6)
        self._burst(px, py, color, 16)
        self._float(ev.get("name", "涌潮"), px, py - self.s(58), color, 30)

    def _skill_vortex(self, ev, px, py):
        """③ 漩涡：引导 time 秒持续把周围敌人卷向自身（复用 channel 读条）；
        引导中切走即中断（_activate 清 channel）；结束时若身处水域之上则引爆全场水域。"""
        color = ev.get("color", (110, 190, 250))
        self.game.audio.play("skill_storm")
        self.channel = {"t": 0.0, "total": max(0.05, ev.get("time", S.TIDE_VORTEX_TIME)),
                        "ev": ev, "color": color, "fx": ev.get("sid"),
                        "vortex": True, "tick": 0.0}
        self.atk_combo = None
        self._fx_vortex(px, py, ev.get("radius", S.TIDE_VORTEX_RADIUS) * self.S,
                        color, life=0.6)
        self._float(ev.get("name", "漩涡") + " 引导中…", px, py - self.s(58), color, 26)

    def _skill_contract(self, ev, px, py):
        """④ 潮汐契约：立下 time 秒水之契约，期间出战角色普攻命中召来水柱追击
        （伤害=施放时潮汐攻击力×atk_ratio 的快照）；切到后台也持续生效。"""
        color = ev.get("color", (130, 205, 255))
        dmg = max(1, int(round(self.player_damage * ev["atk_ratio"])))
        self.contract = {"t": ev["time"], "dmg": dmg,
                         "cd": 0.0, "inner_cd": ev["inner_cd"]}
        self.game.audio.play("skill_shield")
        self._fx_rune(px, py, self.s(130), color, life=0.6)
        self._burst(px, py, color, 18)
        self._float(ev.get("name", "潮汐契约"), px, py - self.s(58), color, 30)

    def _skill_domain(self, ev, px, py):
        """⑤ 潮汐领域（大招）：展开 time 秒领域，全场敌人湿身（受伤+）并减速，
        刷新所有水域；契约剩余时长转化为全队护盾。释放须在场，之后可切走收割。"""
        color = ev.get("color", (180, 225, 255))
        dom_time = ev["time"]
        self.domain = {"t": dom_time, "wet": ev["wet_amp"], "slow": ev["slow_mult"]}
        # 刷新所有水域：把每片水域的剩余时间顶满（大招后水域链重新续上）
        for z in self.zones:
            z["t"] = max(z["t"], S.TIDE_ZONE_TIME)
            z["max_t"] = S.TIDE_ZONE_TIME
        # 契约剩余时长转全队护盾：每剩 1s 转 shield_per_sec 点吸收量
        if self.contract and self.contract["t"] > 0:
            shield = self.contract["t"] * ev.get("shield_per_sec",
                                                 S.TIDE_DOMAIN_SHIELD_PER_SEC)
            for mbr in self.party:
                if mbr["snake"].alive:
                    mbr["snake"].grant_shield(dom_time, shield)
            self.contract = None
            self._float("契约转化为护盾!", px, py - self.s(96), color, 26)
        self.game.audio.play("skill_storm")
        self._fx_ultimate(px, py, color)
        self._fx_ring(px, py, self.s(440), color, life=0.85)
        self._burst(px, py, color, 40)
        self.shake = max(self.shake, 0.5)
        self.flash = max(self.flash, 0.4)
        self._float(ev.get("name", "潮汐领域"), px, py - self.s(58), color, 34)

    def _vortex_tick(self, ch, dt):
        """漩涡引导期：每帧把范围内敌人持续卷向自身，并按 0.25s 间隔结算小额伤害。"""
        ev = ch["ev"]
        px, py = self.snake.pos
        r = ev.get("radius", S.TIDE_VORTEX_RADIUS) * self.S
        strength = ev.get("strength", S.TIDE_VORTEX_STRENGTH) * self.S
        for m in self.mobs:
            if not m.alive:
                continue
            dx, dy = px - m.pos[0], py - m.pos[1]
            d = math.hypot(dx, dy)
            if d <= r + m.radius and d > 1.0:
                m.pos[0] += dx / d * strength * dt
                m.pos[1] += dy / d * strength * dt
        ch["tick"] = ch.get("tick", 0.0) + dt
        if ch["tick"] < 0.25:
            return
        ch["tick"] = 0.0
        tick_dmg = max(1, int(ev.get("tick_dmg", S.TIDE_VORTEX_TICK_DMG)))
        self._fx_vortex(px, py, r, ch["color"], life=0.26)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                self._hurt_mob(m, tick_dmg, m.pos[0], m.pos[1],
                               color=ch["color"], spark=3)
        self.mobs = [m for m in self.mobs if m.alive]

    def _finish_vortex(self, ev, color):
        """漩涡引导结束：身处水域之上则引爆全场水域（主要输出），否则只是收势。"""
        px, py = self.snake.pos
        self._fx_vortex(px, py, ev.get("radius", S.TIDE_VORTEX_RADIUS) * self.S,
                        color, life=0.5)
        if self.zones and self._pos_in_zone(px, py):
            self._detonate_zones(ev, color)
            self._float(ev.get("name", "漩涡") + " 引爆水域!", px, py - self.s(58),
                        color, 32)
        else:
            self._float(ev.get("name", "漩涡"), px, py - self.s(58), color, 28)

    def _detonate_zones(self, ev, color):
        """引爆全场所有水域：每片对域内敌人造成 detonate 伤害，随后清空水域。"""
        dmg = max(1, int(ev.get("dmg", S.TIDE_VORTEX_DETONATE_DMG)))
        self.game.audio.play("skill_storm")
        for z in self.zones:
            zx, zy, zr = z["x"], z["y"], z["r"]
            self._fx_nova(zx, zy, zr, color, life=0.55)
            self._burst(zx, zy, color, 22)
            for m in list(self.mobs):
                if not m.alive:
                    continue
                if math.hypot(m.pos[0] - zx, m.pos[1] - zy) <= zr + m.radius:
                    self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=10)
            if self.boss is not None and self.boss.alive:
                bx, by = self.boss.pos
                if math.hypot(bx - zx, by - zy) <= zr + self.boss.radius_px:
                    self._damage_boss(dmg, color=color)
        self.mobs = [m for m in self.mobs if m.alive]
        self.zones = []
        self.shake = max(self.shake, 0.45)

    def _try_contract_proc(self, mx, my):
        """潮汐契约：出战角色普攻命中时在命中点召来水柱追击（内置 CD 限流）。
        伤害为施放契约时快照的潮汐攻击力×比例，切到后台也照常触发。"""
        c = self.contract
        if c is None or c["t"] <= 0 or c["cd"] > 0:
            return
        c["cd"] = c["inner_cd"]
        dmg = c["dmg"]
        color = (130, 205, 255)
        self._fx_geyser(mx, my, color)
        self.game.audio.play("skill_storm", throttle=0.08)
        r = self.s(72)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - mx, m.pos[1] - my) <= r + m.radius:
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=6)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - mx, by - my) <= r + self.boss.radius_px:
                self._damage_boss(dmg, color=color)

    def _fx_geyser(self, x, y, color):
        """水柱追击特效：地面水环 + 上冲粒子簇（复用既有 VFX，不新增绘制类型）。"""
        self._fx_ring(x, y, self.s(58), color, life=0.32)
        self._burst(x, y - self.s(24), color, 12)

    def _update_tide_fields(self, dt):
        """潮汐切人体系的场景级持续效果：水域计时+域内敌人减速、契约计时+内置CD、
        领域计时+全场湿身/减速（覆盖期间新刷的怪）、踏浪登场增益计时。"""
        if self.landing_t > 0:
            self.landing_t = max(0.0, self.landing_t - dt)
        # 涌潮水域：计时到期移除；域内敌人持续减速（短刷新，离开即恢复）
        if self.zones:
            for z in self.zones:
                z["t"] -= dt
            self.zones = [z for z in self.zones if z["t"] > 0]
            for z in self.zones:
                slow = z.get("enemy_slow", S.TIDE_ZONE_ENEMY_SLOW)
                for m in self.mobs:
                    if not m.alive:
                        continue
                    if (math.hypot(m.pos[0] - z["x"], m.pos[1] - z["y"])
                            <= z["r"] + m.radius):
                        m.apply_slow(slow, 0.25)
        # 潮汐契约：计时 + 内置 CD
        if self.contract is not None:
            c = self.contract
            c["t"] -= dt
            if c["cd"] > 0:
                c["cd"] = max(0.0, c["cd"] - dt)
            if c["t"] <= 0:
                self.contract = None
        # 潮汐领域：全场湿身（受水伤+）+ 减速，覆盖期间新刷的怪
        if self.domain is not None:
            d = self.domain
            d["t"] -= dt
            if d["t"] <= 0:
                self.domain = None
            else:
                for m in self.mobs:
                    if m.alive:
                        m.apply_wet(d["wet"], 0.3)
                        m.apply_slow(d["slow"], 0.3)
                if self.boss is not None and self.boss.alive:
                    self.boss.apply_wet(d["wet"], 0.3)

    # ---- 潮汐·切人联动辅助（被动判定 / 水域几何 / 盾转移）----
    def _member_has_passive(self, m, pid):
        """该成员技能包是否含指定 id 的被动。"""
        try:
            for p in m["skills"].passives:
                if p.get("id") == pid:
                    return True
        except (AttributeError, TypeError, KeyError):
            pass
        return False

    def _party_has_passive(self, pid):
        """编队中是否有任意成员带指定被动。"""
        return any(self._member_has_passive(m, pid) for m in self.party)

    def _backwave_reduce(self):
        """潮汐·后浪：潮汐在后台（非活跃）且存活时，出战角色的免伤比例。
        潮汐强化层数达标升到 20%，否则 15%；潮汐不在后台/阵亡则 0。"""
        for i, m in enumerate(self.party):
            if i == self.active_idx:
                continue
            if m["snake"].alive and self._member_has_passive(m, "p_backwave"):
                layer = self.game.save_manager.get_enhance(m["char_id"])
                if layer >= S.PASSIVE_BACKWAVE_UP_LAYER:
                    return S.PASSIVE_BACKWAVE_REDUCE_UP
                return S.PASSIVE_BACKWAVE_REDUCE
        return 0.0

    def _pos_in_zone(self, x, y):
        """世界坐标 (x,y) 是否落在任意存活水域内。"""
        for z in getattr(self, "zones", []):
            if math.hypot(x - z["x"], y - z["y"]) <= z["r"]:
                return True
        return False

    def _active_in_zone(self):
        """当前活跃角色是否站在水域上（供移速/减伤/漩涡引爆判定复用）。"""
        px, py = self.snake.pos
        return self._pos_in_zone(px, py)

    def _transfer_handoff_shield(self, src, dst):
        """潮汐交接：把切走者剩余护盾吸收量按 transfer 比例转移给登场者。"""
        self.handoff_holder = None
        src_sn, dst_sn = src["snake"], dst["snake"]
        if src_sn is dst_sn or not dst_sn.alive:
            return
        if src_sn.shield_t > 0 and src_sn.shield_pool > 0:
            transfer = src_sn.shield_pool * self.handoff_transfer
            dst_sn.grant_shield(src_sn.shield_t, transfer)
            src_sn.shield_pool = max(0.0, src_sn.shield_pool - transfer)
            if src_sn.shield_pool <= 0:
                src_sn.shield_t = 0.0
            self._float(f"盾转移 {int(round(transfer))}", dst_sn.pos[0],
                        dst_sn.pos[1] - self.s(72), (150, 215, 255), 24)

    # -------------------------------------------------- 标记被动（叠层自爆）
    def _apply_mark_stack(self, m, amp=None, time=None, max_stacks=None):
        """标记被动：技能命中给怪叠一层印记，叠满触发自爆（仅带被动时生效）。"""
        if not getattr(self.skills, "has_mark_passive", False):
            return
        if not getattr(m, "alive", False):
            return
        amp = S.MARKPASSIVE_AMP if amp is None else amp
        time = S.MARKPASSIVE_TIME if time is None else time
        max_stacks = S.MARKPASSIVE_STACKS if max_stacks is None else max_stacks
        full = m.apply_mark(amp, time, max_stacks)
        self._fx_rune(m.pos[0], m.pos[1], m.radius * 2.4, (255, 220, 150), life=0.28)
        if full:
            if self.stella_mark_supply:
                # 星璃「星之标记」供料：叠满 3 层不再自爆，改在敌人脚下落 1 颗星位
                m.clear_mark()
                self._stella_add_node(m.pos[0], m.pos[1])
                self._fx_starfall(m.pos[0], m.pos[1], self.s(64), life=0.5)
            else:
                self._mark_explode(m)

    def _mark_explode(self, m):
        """标记叠满自爆：范围伤害 + 清标记 + 华丽 VFX（对精英/Boss 同样生效）。"""
        mx, my = m.pos[0], m.pos[1]
        r = S.MARKPASSIVE_EXPLODE_RADIUS * self.S
        color = (255, 200, 120)
        dmg = S.MARKPASSIVE_EXPLODE_DMG
        self._fx_nova(mx, my, r, color, life=0.5)
        self._burst(mx, my, color, 24)
        self.game.audio.play("skill_storm", throttle=0.06)
        self.shake = max(self.shake, 0.22)
        m.clear_mark()
        self._hurt_mob(m, dmg, mx, my, color=color, spark=10)
        for o in list(self.mobs):
            if not o.alive or o is m:
                continue
            if math.hypot(o.pos[0] - mx, o.pos[1] - my) <= r + o.radius:
                o.clear_mark()
                self._hurt_mob(o, dmg, o.pos[0], o.pos[1], color=color, spark=8)
        self.mobs = [x for x in self.mobs if x.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - mx, by - my) <= r + self.boss.radius_px:
                self.boss.clear_mark()
                self._damage_boss(dmg, color=color)

    def _nearest_mobs(self, count):
        px, py = self.snake.pos
        pool = [m for m in self.mobs if m.alive]
        pool.sort(key=lambda m: math.hypot(m.pos[0] - px, m.pos[1] - py))
        return pool[:max(0, int(count))]

    def _apply_onhit_passive(self, m):
        """普攻/技能命中时按被动附加减速(寒流)或灼烧(余烬)，并触发元素 proc。"""
        if not getattr(m, "alive", False):
            return
        if self.passive_kind == "slow":
            m.apply_slow(S.PASSIVE_COLD_SLOW, S.PASSIVE_COLD_TIME)
        elif self.passive_kind == "burn":
            m.apply_burn(S.PASSIVE_EMBER_BURN_DPS, S.PASSIVE_EMBER_BURN_TIME)
        self._apply_element_proc(m)

    # ------------------------------------------------------------ 元素对怪效果
    def _active_element(self):
        """当前活跃成员的元素（来自技能引擎 load_kit）。"""
        return getattr(self.skills, "element", "") or ""

    def _ranged_color(self):
        """远程普攻弹丸光晕/枪口/火星拖尾的主色：按活跃元素取色（樱=粉、火=橙红…），
        缺省回退樱落粉，保证只有樱落配 ranged 时表现完全不变。"""
        return _EL_RANGED_COLOR.get(self._active_element(), (255, 190, 215))

    def _apply_element_proc(self, m):
        """命中时按活跃成员元素概率触发对怪效果，让属性有实际意义。
        樱=叠花瓣标记满层绽放 / 风=击退+减速 / 水=减速+概率冻结 /
        火=灼烧+概率爆燃 / 星=贯穿次近目标 / 月=削弱该怪+自身短时减伤。"""
        if not getattr(m, "alive", False):
            return
        el = self._active_element()
        if not el or random.random() >= S.ELEMENT_PROC_CHANCE:
            return
        mx, my = m.pos[0], m.pos[1]
        if el == "樱":
            m.apply_mark(S.ELEMENT_SAKURA_AMP, S.ELEMENT_SAKURA_TIME,
                         S.ELEMENT_SAKURA_STACKS)
            self._fx_petals(mx, my, self.s(48), (255, 170, 200))
            if getattr(m, "mark_stacks", 0) >= S.ELEMENT_SAKURA_STACKS:
                self._sakura_bloom(m)
        elif el == "风":
            m.knockback(self.snake.pos, S.ELEMENT_WIND_KNOCK)
            m.apply_slow(S.ELEMENT_WIND_SLOW, S.ELEMENT_WIND_TIME)
            self._fx_ring(mx, my, self.s(56), (150, 240, 190), life=0.32)
        elif el == "水":
            m.apply_slow(0.6, 1.2)
            if random.random() < S.ELEMENT_WATER_FREEZE_CHANCE:
                m.apply_slow(S.ELEMENT_FREEZE_MULT, S.ELEMENT_FREEZE_TIME)
                self._fx_freeze(mx, my, m.radius)
            else:
                self._fx_ring(mx, my, self.s(48), (120, 200, 255), life=0.3)
        elif el == "火":
            m.apply_burn(S.PASSIVE_EMBER_BURN_DPS * 2, 2.5)
            self._burst(mx, my, (255, 140, 80), 8)
            if random.random() < S.ELEMENT_FIRE_BLAST_CHANCE:
                self._fire_blast(mx, my)
        elif el == "星":
            self._star_pierce(m)
        elif el == "月":
            m.apply_weaken(S.ELEMENT_MOON_WEAKEN, S.ELEMENT_MOON_TIME)
            self.ward_t = max(self.ward_t, S.ELEMENT_MOON_WARD)
            self._fx_ring(mx, my, self.s(50), (200, 210, 255), life=0.34)

    def _sakura_bloom(self, m):
        """樱花瓣标记叠满绽放：以目标为中心范围伤害并清标记。

        结算顺序（见 _sakura_mark_stack 调用点）：叠层→判满 3 层→绽放清层。
        伤害 = ELEMENT_SAKURA_BLOOM ×(1 + BLOOM_PER_STACK×层数)，目标站在花圃内
        再 ×BED_MULT；花期(kaki)期间绽放半径 ×CHANNEL_BLOOM_MULT。同一目标
        BLOOM_CD 秒内不重复绽放（含被溅射者），避免同帧连锁炸屏。
        绽放命中即触发花守被动（回血 + 叠花护减伤层）。
        """
        if not getattr(m, "alive", False):
            return
        # 同目标绽放节流：BLOOM_CD 秒内已绽放过就跳过
        if self.elapsed - getattr(m, "sakura_bloom_at", -999.0) < S.SAKURA_BLOOM_CD:
            return
        m.sakura_bloom_at = self.elapsed
        mx, my = m.pos[0], m.pos[1]
        stacks = max(1, getattr(m, "mark_stacks", 0))
        mult = 1.0 + S.SAKURA_BLOOM_PER_STACK * stacks
        if self._sakura_in_bed(mx, my):
            mult *= S.SAKURA_BLOOM_BED_MULT
        dmg = max(1, int(round(S.ELEMENT_SAKURA_BLOOM * mult)))
        r = S.ELEMENT_SAKURA_RADIUS * self.S
        if self.sakura_kaki_t > 0:
            r *= S.SAKURA_CHANNEL_BLOOM_MULT
        self._fx_petals(mx, my, r, (255, 150, 190))
        self._fx_nova(mx, my, r, (255, 170, 200), life=0.4)
        self.game.audio.play("skill_bloom", throttle=0.08)
        for o in list(self.mobs):
            if not o.alive:
                continue
            if math.hypot(o.pos[0] - mx, o.pos[1] - my) <= r + o.radius:
                o.clear_mark()
                o.sakura_bloom_at = self.elapsed
                self._hurt_mob(o, dmg, o.pos[0], o.pos[1],
                               color=(255, 150, 190), spark=8)
        self.mobs = [x for x in self.mobs if x.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - mx, by - my) <= r + self.boss.radius_px:
                self.boss.clear_mark()
                self.boss.sakura_bloom_at = self.elapsed
                self._damage_boss(dmg, color=(255, 150, 190))
        # 花守被动：每次绽放回固定血 + 叠 1 层花护减伤
        if self.passive_kind == "bloomguard":
            self._sakura_bloomguard(mx, my)

    def _sakura_bloomguard(self, mx, my):
        """花守被动落地：绽放即回复 SAKURA_BLOOM_HEAL 生命并叠 1 层花护（有上限）。"""
        sn = self.snake
        if sn.alive and sn.hp < sn.hp_max:
            healed = min(S.SAKURA_BLOOM_HEAL, sn.hp_max - sn.hp)
            if healed > 0:
                sn.hp += healed
                self._float(f"+{int(round(healed))} HP", mx, my - self.s(20), COLOR_HP)
        if self.sakura_guard < S.SAKURA_GUARD_MAX:
            self.sakura_guard += 1

    def _sakura_in_bed(self, x, y):
        """坐标是否落在任意活跃花圃内（绽放 ×BED_MULT 判据）。"""
        for b in self.sakura_beds:
            if math.hypot(x - b["x"], y - b["y"]) <= b["r"]:
                return True
        return False

    def _sakura_skill_dmg(self, ev=None, mult=1.0):
        """樱落技能伤害基数：随等级(attack)/技能伤卡/职业系数/局内强化成长。

        mult 为各技能自己的倍率（花刃每段、催放每层等）。事件里没有 dmg 字段，
        伤害全部在此按当前面板计算，让 atk/技能伤卡与强化等级照常生效。"""
        lv = (ev or {}).get("lv", 0)
        sd = self.stats.get("skilldmg", 1.0) * self.role_skilldmg
        enh = 1.0 + S.SKILL_ENH_DMG_PER_LV * lv
        return max(1, int(round(self.snake.attack * sd * enh * mult)))

    def _sakura_mark_stack(self, m):
        """樱落普攻段3：确定性叠花瓣标记（种花主手段），叠满即绽放。

        与元素 proc 的概率叠层不同，散华命中必叠一层；标记参数与技能
        同源 ELEMENT_SAKURA_*，满层绽放复用 _sakura_bloom（小怪/Boss 通吃）。
        """
        if not getattr(m, "alive", False):
            return
        m.apply_mark(S.ELEMENT_SAKURA_AMP, S.ELEMENT_SAKURA_TIME,
                     S.ELEMENT_SAKURA_STACKS)
        self._fx_petals(m.pos[0], m.pos[1], self.s(48), (255, 170, 200))
        if getattr(m, "mark_stacks", 0) >= S.ELEMENT_SAKURA_STACKS:
            self._sakura_bloom(m)

    # -------------------------------------------------- 樱落·种花闭环五技能
    # 樱属性刺客：延时爆发（种花→催放→绽放）。花瓣标记叠满 3 层立即绽放；
    # 五个技能各自围绕「叠层 / 引爆 / 铺花圃 / 往返叠层 / 花期增益」，数值固定
    # 不吃职业系数（见 skills.cooldown_at 豁免），伤害由 _sakura_skill_dmg 按面板算。
    def _skill_sakura_dash2(self, ev, px, py, dx, dy):
        """① 花信：朝瞄准方向突进 dist，沿途每 plant_step 为敌人种 1 层花瓣标记
        （单怪上限 plant_cap），中途留樱分身爆散，落地获 shield_time 护盾（吸收
        shield_pct 最大生命）+ 起手 iframe 无敌帧。"""
        color = ev.get("color", (255, 150, 190))
        dist = ev.get("dist", S.SAKURA_DASH2_DIST) * self.S
        step = max(1.0, ev.get("plant_step", S.SAKURA_DASH2_PLANT_STEP) * self.S)
        cap = max(1, int(ev.get("plant_cap", S.SAKURA_DASH2_PLANT_CAP)))
        x2 = min(max(px + dx * dist, self.snake.radius), self.world_w - self.snake.radius)
        y2 = min(max(py + dy * dist, self.snake.radius), self.world_h - self.snake.radius)
        self.game.audio.play("skill_dash")
        iframe = ev.get("iframe", S.SAKURA_DASH2_IFRAME)
        if iframe > 0:
            self.snake.invincible = max(self.snake.invincible, iframe)
        # 沿途种花：按 plant_step 取样路径点，对附近敌人叠标记（单怪限 cap 次）
        planted = {}
        reach = self.s(70)
        d = math.hypot(x2 - px, y2 - py) or 1.0
        n = max(1, int(d // step))
        for i in range(1, n + 1):
            wx = px + (x2 - px) * i / n
            wy = py + (y2 - py) * i / n
            self._fx_petals(wx, wy, self.s(40), (255, 190, 215))
            for m in list(self.mobs):
                if not m.alive:
                    continue
                if math.hypot(m.pos[0] - wx, m.pos[1] - wy) <= reach + m.radius:
                    if planted.get(id(m), 0) < cap:
                        planted[id(m)] = planted.get(id(m), 0) + 1
                        self._sakura_mark_stack(m)
            if self.boss is not None and self.boss.alive:
                bx, by = self.boss.pos
                if (math.hypot(bx - wx, by - wy) <= reach + self.boss.radius_px
                        and planted.get("boss", 0) < cap):
                    planted["boss"] = planted.get("boss", 0) + 1
                    self._sakura_mark_stack(self.boss)
        self.mobs = [m for m in self.mobs if m.alive]
        # 突进本体伤害（路径上的敌人吃一次斩冲）+ 位移到落点
        self._damage_segment(px, py, x2, y2, self._sakura_skill_dmg(ev, 0.5), color)
        self.snake.pos[0], self.snake.pos[1] = x2, y2
        self._fx_trail(px, py, x2, y2, color)
        # 樱分身：中点爆散
        midx, midy = (px + x2) / 2, (py + y2) / 2
        self._spawn_fx_sprite(ev.get("sid"), midx, midy, self.s(150),
                              life=0.4, expand=1.7, spin=2.5)
        self._burst(midx, midy, (255, 190, 215), 18)
        # 落地护盾（护盾卡加成同潮汐交接）
        shield_pct = ev.get("shield_pct", S.SAKURA_DASH2_SHIELD_PCT)
        shield_time = ev.get("shield_time", S.SAKURA_DASH2_SHIELD_TIME)
        smult = 1.0 + min(S.SHIELD_STAT_CAP, self.stats.get("shield", 0.0))
        self.snake.grant_shield(shield_time * smult,
                                self.snake.hp_max * shield_pct * smult)
        self._burst(x2, y2, color, 20)
        self._fx_ring(x2, y2, self.s(80), (255, 200, 225), life=0.4)
        self._float(ev.get("name", "花信"), px, py - self.s(54), color, 30)
        self.shake = max(self.shake, 0.28)

    def _skill_sakura_detonate(self, ev, px, py):
        """② 催放：立即引爆半径内所有花瓣标记（不等满层），每层 ×per_stack 追加伤害；
        引爆后 delay 秒对同一批目标再补一跳 delay_pct 的余震。"""
        r = ev.get("radius", S.SAKURA_DETONATE_RADIUS) * self.S
        per_stack = ev.get("per_stack", S.SAKURA_DETONATE_PER_STACK)
        delay = ev.get("delay", S.SAKURA_DETONATE_DELAY)
        delay_pct = ev.get("delay_pct", S.SAKURA_DETONATE_DELAY_PCT)
        color = ev.get("color", (255, 180, 210))
        base = self._sakura_skill_dmg(ev, 1.0)
        self.game.audio.play("skill_storm")
        self._fx_nova(px, py, r, color, life=0.6)
        self._spawn_fx_sprite(ev.get("sid"), px, py, max(self.s(90), r * 1.5),
                              life=0.55, expand=1.6, spin=2.0)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                stacks = getattr(m, "mark_stacks", 0)
                if stacks > 0:
                    dmg = int(round(base * (1.0 + per_stack * stacks)))
                    m.clear_mark()
                    self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=12)
                    if m.alive and delay > 0:
                        self.sakura_delay.append(
                            {"t": delay, "mob": m, "boss": False,
                             "dmg": max(1, int(round(dmg * delay_pct))),
                             "color": color})
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - px, by - py) <= r + self.boss.radius_px:
                stacks = getattr(self.boss, "mark_stacks", 0)
                if stacks > 0:
                    bdmg = int(round(base * (1.0 + per_stack * stacks)))
                    self.boss.clear_mark()
                    self._damage_boss(bdmg, color=color)
                    if self.boss.alive and delay > 0:
                        self.sakura_delay.append(
                            {"t": delay, "mob": self.boss, "boss": True,
                             "dmg": max(1, int(round(bdmg * delay_pct))),
                             "color": color})
        self._float(ev.get("name", "催放"), px, py - self.s(58), color, 30)
        self.shake = max(self.shake, 0.34)

    def _skill_sakura_gather(self, ev, px, py, dx, dy):
        """③ 落樱引：在指定点铺一片持续 time 秒的圆形花圃，圃内敌人每 tick 叠 1 层
        花瓣标记，叠满 3 层立即绽放（绽放结算见 _update_sakura / _sakura_bloom）。
        指定点优先取最近敌人脚下，否则沿瞄准方向抛出。"""
        r = ev.get("radius", S.SAKURA_GATHER_RADIUS) * self.S
        gt = ev.get("time", S.SAKURA_GATHER_TIME)
        tick = ev.get("tick", S.SAKURA_GATHER_TICK)
        color = ev.get("color", (255, 160, 200))
        tgt = self._nearest_target(max_range=r * 3.0)
        if tgt is not None:
            _kind, obj = tgt
            cx, cy = obj.pos[0], obj.pos[1]
        else:
            cx, cy = px + dx * r, py + dy * r
        cx = min(max(cx, r), max(r, self.world_w - r))
        cy = min(max(cy, r), max(r, self.world_h - r))
        self.sakura_beds.append({"x": cx, "y": cy, "r": r, "t": gt, "max_t": gt,
                                 "tick": max(0.05, tick), "acc": 0.0,
                                 "color": color, "sid": ev.get("sid")})
        self.game.audio.play("skill_storm")
        self._fx_rune(cx, cy, r, color, life=0.6)
        self._fx_petals(cx, cy, r, (255, 190, 215))
        self._spawn_fx_sprite(ev.get("sid"), cx, cy, max(self.s(120), r * 1.6),
                              life=0.7, expand=1.3, spin=1.2)
        self._float(ev.get("name", "落樱引"), px, py - self.s(58), color, 30)

    def _sakura_bed_tick(self, bed):
        """花圃每 tick：对圃内敌人叠 1 层花瓣标记（满层由 _sakura_mark_stack 触发绽放），
        并补一圈法阵让花圃在存续期内持续可见。"""
        x, y, r = bed["x"], bed["y"], bed["r"]
        color = bed["color"]
        self._fx_rune(x, y, r, color, life=0.85)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - x, m.pos[1] - y) <= r + m.radius:
                self._sakura_mark_stack(m)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - x, by - y) <= r + self.boss.radius_px:
                self._sakura_mark_stack(self.boss)

    def _skill_sakura_blade(self, ev, px, py, base_ang):
        """④ 回旋花刃：沿瞄准方向甩出花刃轮往返 trips 趟，每趟对射线走廊内敌人
        造成 mult 倍伤害并叠 1 层花瓣标记；命中已带标记者额外 +marked_bonus。"""
        rng = ev.get("range", S.SAKURA_BLADE_RANGE) * self.S
        halfw = ev.get("width", S.SAKURA_BLADE_WIDTH) * self.S * 0.5
        mult = ev.get("mult", S.SAKURA_BLADE_MULT)
        trips = max(1, int(ev.get("trips", S.SAKURA_BLADE_TRIPS)))
        bonus = ev.get("marked_bonus", S.SAKURA_BLADE_MARKED_BONUS)
        color = ev.get("color", (255, 170, 200))
        x2 = px + math.cos(base_ang) * rng
        y2 = py + math.sin(base_ang) * rng
        self.game.audio.play("skill_bloom")
        base = self._sakura_skill_dmg(ev, mult)
        for trip in range(trips):
            self._fx_beam(px, py, x2, y2, halfw * 2, color, life=0.3)
            self._spawn_fx_sprite(ev.get("sid"), (px + x2) / 2, (py + y2) / 2,
                                  self.s(150), life=0.35, expand=1.4,
                                  spin=(4.0 if trip % 2 == 0 else -4.0))
            for m in list(self.mobs):
                if not m.alive:
                    continue
                if _seg_dist(m.pos[0], m.pos[1], px, py, x2, y2) <= halfw + m.radius:
                    had = getattr(m, "mark_stacks", 0) > 0
                    dmg = int(round(base * (1.0 + bonus))) if had else base
                    self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=6)
                    if m.alive:
                        self._sakura_mark_stack(m)
            self.mobs = [m for m in self.mobs if m.alive]
            if self.boss is not None and self.boss.alive:
                bx, by = self.boss.pos
                if _seg_dist(bx, by, px, py, x2, y2) <= halfw + self.boss.radius_px:
                    had = getattr(self.boss, "mark_stacks", 0) > 0
                    bdmg = int(round(base * (1.0 + bonus))) if had else base
                    self._damage_boss(bdmg, color=color)
                    self._sakura_mark_stack(self.boss)
        self._float(ev.get("name", "回旋花刃"), px, py - self.s(58), color, 30)
        self.shake = max(self.shake, 0.26)

    def _skill_sakura_channel(self, ev, px, py):
        """⑤ 花期：进入 time 秒的花期状态——期间普攻每段必叠 stack 层花瓣标记
        （见弹丸钩子），且绽放半径 ×bloom_mult（见 _sakura_bloom）。"""
        gt = ev.get("time", S.SAKURA_CHANNEL_TIME)
        color = ev.get("color", (255, 200, 220))
        self.sakura_kaki_t = max(self.sakura_kaki_t, gt)
        self.game.audio.play("skill_shield")
        self._fx_aura(px, py, self.s(120), color, life=0.7)
        self._spawn_fx_sprite(ev.get("sid"), px, py, self.s(170),
                              life=0.7, expand=1.6, spin=1.5)
        self._burst(px, py, color, 20)
        self._float(ev.get("name", "花期") + " 绽放增益!", px, py - self.s(58), color, 30)

    def _update_sakura(self, dt):
        """樱落持续态每帧推进：花期倒计时 / 催放延迟二次跳 / 花圃区域叠层绽放。"""
        if self.sakura_kaki_t > 0:
            self.sakura_kaki_t = max(0.0, self.sakura_kaki_t - dt)
        # 催放延迟二次跳：到期对仍存活的目标补一跳余震
        if self.sakura_delay:
            for d in self.sakura_delay:
                d["t"] -= dt
            due = [d for d in self.sakura_delay if d["t"] <= 0]
            self.sakura_delay = [d for d in self.sakura_delay if d["t"] > 0]
            for d in due:
                m = d["mob"]
                if not getattr(m, "alive", False):
                    continue
                if d["boss"]:
                    self._damage_boss(d["dmg"], color=d["color"])
                else:
                    self._hurt_mob(m, d["dmg"], m.pos[0], m.pos[1],
                                   color=d["color"], spark=6)
                    self._fx_petals(m.pos[0], m.pos[1], self.s(40), d["color"])
            self.mobs = [m for m in self.mobs if m.alive]
        # 花圃区域：每 tick 叠层，存续时间到即消散
        if self.sakura_beds:
            for bed in self.sakura_beds:
                bed["t"] -= dt
                bed["acc"] += dt
                if bed["acc"] >= bed["tick"]:
                    bed["acc"] -= bed["tick"]
                    self._sakura_bed_tick(bed)
            self.sakura_beds = [b for b in self.sakura_beds if b["t"] > 0]

    # -------------------------------------------------- 绯焰·灼烧引爆闭环五技能
    # 火属性法师：余烬叠层（DOT，随时间自耗一层）→ 引爆类技能按剩余层数一次性
    # 结算爆发伤害。全队只有绯焰能叠层与引爆；数值固定不吃职业系数
    # （见 skills.cooldown_at 豁免），伤害由 _flare_skill_dmg 按面板算。
    def _flare_skill_dmg(self, ev, mult):
        """绯焰技能伤害基数：同樱落，事件里没有 dmg，按当前面板 × 倍率计算。"""
        lv = (ev or {}).get("lv", 0)
        sd = self.stats.get("skilldmg", 1.0) * self.role_skilldmg
        enh = 1.0 + S.SKILL_ENH_DMG_PER_LV * lv
        return max(1, int(round(self.snake.attack * sd * enh * mult)))

    def _ember_stack(self, obj, stacks=1):
        """给目标叠余烬层（小怪/Boss 通吃），叠满封顶时冒个火圈提示。"""
        full = obj.add_ember(stacks)
        self._burst(obj.pos[0], obj.pos[1], (255, 217, 138), 3)
        if full:
            self._fx_ring(obj.pos[0], obj.pos[1],
                          max(self.s(30), obj.radius * 1.6), (255, 201, 60), life=0.3)

    def _ember_detonate(self, obj, base, is_boss, sid=None):
        """引爆单个目标的余烬：伤害 = base ×(1+每层加成×层数)，缭焰期间再增伤。
        返回被引爆的层数（0 = 目标身上没有余烬）。"""
        stacks = obj.consume_ember()
        if stacks <= 0:
            return 0
        amp = 1.0 + (self.flare_ring_amp if self.flare_ring_t > 0 else 0.0)
        dmg = max(1, int(round(base * (1.0 + S.FLARE_EMBER_BURST_MULT * stacks) * amp)))
        color = (255, 122, 46)
        x, y = obj.pos[0], obj.pos[1]
        if is_boss:
            self._damage_boss(dmg, color=color)
        else:
            self._hurt_mob(obj, dmg, x, y, color=color, spark=14)
        self._fx_nova(x, y, max(self.s(60), getattr(obj, "radius", self.s(20)) * 2.6),
                      color, life=0.45)
        self._spawn_fx_sprite(sid, x, y, max(self.s(110), self.s(40) * stacks),
                              life=0.5, expand=1.8, spin=2.0)
        self._float(f"引爆×{stacks}", x, y - self.s(46), (255, 201, 60), 26)
        return stacks

    def _skill_flare_scatter(self, ev, px, py, base_ang):
        """① 撒烬：朝矄准方向扇形撒出火星雨，命中敌人造成小伤害并叠 1 层余烬。"""
        rng = ev.get("range", S.FLARE_SCATTER_RANGE) * self.S
        half = ev.get("angle", S.FLARE_SCATTER_ANGLE)
        count = max(1, int(ev.get("count", S.FLARE_SCATTER_COUNT)))
        mult = ev.get("mult", S.FLARE_SCATTER_MULT)
        color = ev.get("color", (255, 140, 80))
        self.game.audio.play("skill_storm")
        self._fx_fan(px, py, rng, base_ang, half, color, life=0.4)
        # 火星雨：扇形内随机撒 count 颗火星粒子（纯视觉）
        for i in range(count):
            a = base_ang + random.uniform(-half, half)
            d = rng * random.uniform(0.45, 1.0)
            self._burst(px + math.cos(a) * d, py + math.sin(a) * d, (255, 217, 138), 3)
        self._spawn_fx_sprite(ev.get("sid"), px + math.cos(base_ang) * rng * 0.5,
                              py + math.sin(base_ang) * rng * 0.5, self.s(170),
                              life=0.45, expand=1.5, spin=1.5)
        dmg = self._flare_skill_dmg(ev, mult)
        for m in list(self.mobs):
            if not m.alive:
                continue
            vx, vy = m.pos[0] - px, m.pos[1] - py
            d0 = math.hypot(vx, vy)
            if d0 <= rng + m.radius:
                da = abs((math.atan2(vy, vx) - base_ang + math.pi) % math.tau - math.pi)
                if d0 <= m.radius + self.s(12) or da <= half:
                    self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=6)
                    if m.alive:
                        self._ember_stack(m)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - px, by - py) <= rng + self.boss.radius_px:
                self._damage_boss(dmg, color=color)
                self._ember_stack(self.boss)
        self._float(ev.get("name", "撒烬"), px, py - self.s(58), color, 30)
        self.shake = max(self.shake, 0.2)

    def _skill_flare_trail(self, ev, px, py, dx, dy):
        """② 燃径：沿矄准方向烙一条直线火径 time 秒，踩踏敌人每 tick 叠 1 层余烬
        并吃一跳小伤害。火径留在场上烧完（同潮汐水域，不随切人消失）；
        视觉＝每次 tick 补一道贴地火线（life > tick，存续期内不断线）。"""
        length = ev.get("length", S.FLARE_TRAIL_LEN) * self.S
        width = ev.get("width", S.FLARE_TRAIL_WIDTH) * self.S
        tt = ev.get("time", S.FLARE_TRAIL_TIME)
        tick = max(0.05, ev.get("tick", S.FLARE_TRAIL_TICK))
        tick_mult = ev.get("tick_mult", S.FLARE_TRAIL_TICK_MULT)
        color = ev.get("color", (255, 122, 46))
        x2 = min(max(px + dx * length, 0.0), self.world_w)
        y2 = min(max(py + dy * length, 0.0), self.world_h)
        self.game.audio.play("skill_storm")
        self.flare_trails.append({
            "x1": px, "y1": py, "x2": x2, "y2": y2, "half": width * 0.5,
            "t": tt, "tick": tick, "acc": 0.0, "mult": tick_mult,
            "color": color, "sid": ev.get("sid"), "lv": ev.get("lv", 0)})
        # 视觉＝一道细火线：beam 辉光按 w*6 扩张，传判定区宽会糊成实心色块，
        # 判定宽度只留在 zone 字典里供踩踏检测用
        self._fx_beam(px, py, x2, y2, self.s(6), color, life=tick + 0.15)
        self._spawn_fx_sprite(ev.get("sid"), (px + x2) / 2, (py + y2) / 2,
                              max(self.s(140), length * 0.5), life=0.5,
                              expand=1.2, spin=0.0)
        self._float(ev.get("name", "燃径"), px, py - self.s(58), color, 30)

    def _flare_trail_tick(self, tr):
        """火径每 tick：对踩踏敌人叠 1 层余烬 + 一跳小伤害，并补一段火线维持视觉。"""
        x1, y1, x2, y2 = tr["x1"], tr["y1"], tr["x2"], tr["y2"]
        half, color = tr["half"], tr["color"]
        self._fx_beam(x1, y1, x2, y2, self.s(6), color, life=tr["tick"] + 0.15)
        dmg = self._flare_skill_dmg(tr, tr["mult"])
        for m in list(self.mobs):
            if not m.alive:
                continue
            if _seg_dist(m.pos[0], m.pos[1], x1, y1, x2, y2) <= half + m.radius:
                self._ember_stack(m)
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=4)
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if _seg_dist(bx, by, x1, y1, x2, y2) <= half + self.boss.radius_px:
                self._ember_stack(self.boss)
                self._damage_boss(dmg, color=color)

    def _skill_flare_fuse(self, ev, px, py):
        """③ 引信：点刺射程内最近的单体烙印——即时小伤害，冻结其现有余烬层数
        （delay 秒内不自然衰减），delay 秒后自动引爆（伤害按引爆时的剩余层数结算，
        期间新叠的层也一并吃进；base 在施放时快照，切人后照常爆）。"""
        rng = ev.get("range", S.FLARE_FUSE_RANGE) * self.S
        mult = ev.get("mult", S.FLARE_FUSE_MULT)
        delay = ev.get("delay", S.FLARE_FUSE_DELAY)
        det_mult = ev.get("det_mult", S.FLARE_FUSE_DET_MULT)
        color = ev.get("color", (255, 201, 60))
        tgt = self._nearest_target(max_range=rng)
        self.game.audio.play("skill_bloom")
        if tgt is None:
            # 空放：只在身前点一簇火星（CD 照走，鼓励对着目标放）
            self._burst(px, py, (255, 217, 138), 10)
            self._float("无目标…", px, py - self.s(54), color, 24)
            return
        kind, obj = tgt
        tx, ty = obj.pos[0], obj.pos[1]
        self._fx_beam(px, py, tx, ty, self.s(10), color, life=0.25)
        dmg = self._flare_skill_dmg(ev, mult)
        if kind == "boss":
            self._damage_boss(dmg, color=color)
        else:
            self._hurt_mob(obj, dmg, tx, ty, color=color, spark=8)
        if not getattr(obj, "alive", False):
            return
        # 烙印：锁定现有层数（冻结衰减），delay 秒后自动引爆
        obj.freeze_ember(delay + 0.15)
        locked = getattr(obj, "ember_stacks", 0)
        base = max(1, int(round(self._flare_skill_dmg(ev, det_mult))))
        self.flare_fuses.append({"t": delay, "obj": obj, "boss": kind == "boss",
                                 "base": base, "sid": ev.get("sid"),
                                 "color": color})
        # 烙印火纹：环形法阵 + 贴图特效
        rr = max(self.s(36), getattr(obj, "radius", self.s(16)) * 2.0)
        self._fx_rune(tx, ty, rr, color, life=0.6)
        self._spawn_fx_sprite(ev.get("sid"), tx, ty, rr * 2.4, life=0.6,
                              expand=1.3, spin=1.8)
        self._float(f"{ev.get('name', '引信')} 锁定×{locked}", px, py - self.s(58),
                    color, 28)

    def _skill_flare_ring(self, ev, px, py):
        """④ 缭焰：自身环绕火环 time 秒——环内敌人每 tick 叠 1 层余烬并减速，
        期间绯焰的引爆伤害提升 amp（缭焰增伤对引信/焚天都生效）。"""
        r = ev.get("radius", S.FLARE_RING_RADIUS) * self.S
        tt = ev.get("time", S.FLARE_RING_TIME)
        tick = max(0.05, ev.get("tick", S.FLARE_RING_TICK))
        slow = ev.get("slow", S.FLARE_RING_SLOW)
        amp = ev.get("amp", S.FLARE_RING_AMP)
        color = ev.get("color", (255, 160, 90))
        self.flare_ring_t = max(self.flare_ring_t, tt)
        self.flare_ring_amp = max(self.flare_ring_amp, amp)
        self.flare_ring = {"r": r, "tick": tick, "acc": 0.0, "slow": slow,
                           "color": color, "sid": ev.get("sid")}
        self.game.audio.play("skill_shield")
        self._fx_ring(px, py, r, color, life=tick + 0.2)
        self._fx_aura(px, py, self.s(120), color, life=0.7)
        self._spawn_fx_sprite(ev.get("sid"), px, py, r * 1.6, life=0.6,
                              expand=1.2, spin=2.2)
        self._float(ev.get("name", "缭焰") + f" 引爆+{int(round(amp * 100))}%!",
                    px, py - self.s(58), color, 30)

    def _flare_ring_tick(self):
        """火环每 tick：环内敌人叠 1 层余烬 + 减速，并补一圈火环维持视觉。"""
        ring = getattr(self, "flare_ring", None)
        if ring is None:
            return
        r, color = ring["r"], ring["color"]
        px, py = self.snake.pos
        self._fx_ring(px, py, r, color, life=ring["tick"] + 0.2)
        for m in list(self.mobs):
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - px, m.pos[1] - py) <= r + m.radius:
                m.apply_slow(ring["slow"], ring["tick"] * 2.0)
                self._ember_stack(m)
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - px, by - py) <= r + self.boss.radius_px:
                self._ember_stack(self.boss)

    def _skill_flare_burst(self, ev, px, py):
        """⑤ 焚天（大招）：全场引爆所有目标的余烬层，每引爆一个目标返还自身
        refund 秒冷却；无余烬目标不吃伤害。"""
        mult = ev.get("mult", S.FLARE_BURST_MULT)
        refund = ev.get("refund", S.FLARE_BURST_REFUND)
        color = ev.get("color", (255, 122, 46))
        sid = ev.get("sid")
        base = self._flare_skill_dmg(ev, mult)
        self.game.audio.play("skill_storm")
        self._fx_ultimate(px, py, color)
        self._spawn_fx_sprite(sid, px, py, self.s(260), life=0.8, expand=2.0, spin=1.0)
        hit = 0
        for m in list(self.mobs):
            if m.alive and getattr(m, "ember_stacks", 0) > 0:
                if self._ember_detonate(m, base, False, sid):
                    hit += 1
        self.mobs = [m for m in self.mobs if m.alive]
        if (self.boss is not None and self.boss.alive
                and getattr(self.boss, "ember_stacks", 0) > 0):
            if self._ember_detonate(self.boss, base, True, sid):
                hit += 1
        # 逐人返还自身冷却（当前出战成员的技能引擎）
        if hit > 0 and refund > 0 and sid:
            cds = getattr(self.skills, "cds", None)
            if isinstance(cds, dict) and sid in cds:
                cds[sid] = max(0.0, cds[sid] - refund * hit)
        self._float(ev.get("name", "焚天") + (f" 引爆×{hit}!" if hit else ""),
                    px, py - self.s(64), (255, 201, 60), 34)
        self.shake = max(self.shake, 0.5)

    def _update_flare(self, dt):
        """绯焰持续态每帧推进：余烬 DOT / 燃径火径 tick / 缭焰火环 / 引信自动引爆。
        余烬挂在实体上，DOT 与火径不随切人停摆（全队只有绯焰能叠层，无需判活跃）。"""
        # 余烬 DOT：每层每秒 FLARE_EMBER_DPS，仿灼烧用小数累加、整数掉血
        for m in list(self.mobs):
            if not m.alive or m.ember_stacks <= 0:
                continue
            m.ember_acc += S.FLARE_EMBER_DPS * m.ember_stacks * dt
            whole = int(m.ember_acc)
            if whole > 0:
                m.ember_acc -= whole
                self._burst(m.pos[0], m.pos[1], (255, 160, 90), 2)
                if m.take_damage(whole):
                    self._on_mob_killed(m, m.pos[0], m.pos[1])
        self.mobs = [m for m in self.mobs if m.alive]
        if self.boss is not None and self.boss.alive and self.boss.ember_stacks > 0:
            b = self.boss
            b.ember_acc += S.FLARE_EMBER_DPS * b.ember_stacks * dt
            whole = int(b.ember_acc)
            if whole > 0:
                b.ember_acc -= whole
                self._burst(b.pos[0], b.pos[1], (255, 160, 90), 2)
                if b.take_damage(whole) and b.alive is False:
                    self._on_boss_defeated()
        # 燃径火径：每 tick 叠层+小伤，烧完即散
        if self.flare_trails:
            for tr in self.flare_trails:
                tr["t"] -= dt
                tr["acc"] += dt
                if tr["acc"] >= tr["tick"]:
                    tr["acc"] -= tr["tick"]
                    self._flare_trail_tick(tr)
            self.flare_trails = [t for t in self.flare_trails if t["t"] > 0]
        # 缭焰火环：跟随自身，每 tick 叠层+减速
        if self.flare_ring_t > 0:
            self.flare_ring_t = max(0.0, self.flare_ring_t - dt)
            if self.flare_ring_t <= 0:
                self.flare_ring_amp = 0.0
                self.flare_ring = None
            elif getattr(self, "flare_ring", None) is not None:
                ring = self.flare_ring
                ring["acc"] += dt
                if ring["acc"] >= ring["tick"]:
                    ring["acc"] -= ring["tick"]
                    self._flare_ring_tick()
        # 引信烙印：到期自动引爆（base 施放时已快照）
        if self.flare_fuses:
            for f in self.flare_fuses:
                f["t"] -= dt
            due = [f for f in self.flare_fuses if f["t"] <= 0]
            self.flare_fuses = [f for f in self.flare_fuses if f["t"] > 0]
            for f in due:
                obj = f["obj"]
                if not getattr(obj, "alive", False):
                    continue
                self._ember_detonate(obj, f["base"], f["boss"], f.get("sid"))
            self.mobs = [m for m in self.mobs if m.alive]

    def _fire_blast(self, mx, my):
        """火元素爆燃：小范围灼烧 + 即时伤害。"""
        r = S.ELEMENT_FIRE_BLAST_RADIUS * self.S
        dmg = max(1, int(S.EMBER_BURN_DPS * 1.5))
        self._fx_ring(mx, my, r, (255, 140, 80), life=0.36)
        self._burst(mx, my, (255, 180, 90), 14)
        self.shake = max(self.shake, 0.14)
        for o in list(self.mobs):
            if not o.alive:
                continue
            if math.hypot(o.pos[0] - mx, o.pos[1] - my) <= r + o.radius:
                o.apply_burn(S.PASSIVE_EMBER_BURN_DPS * 2, 2.0)
                self._hurt_mob(o, dmg, o.pos[0], o.pos[1],
                               color=(255, 140, 80), spark=6)
        self.mobs = [x for x in self.mobs if x.alive]

    # -------------------------------------------------- 星璃·连星成轨五技能
    # 星属性游侠：星位供料 → 连星成轨。地面落发光星点（上限 STELLA_NODE_MAX、
    # 持续 STELLA_NODE_LIFE 秒），两两间距 ≤STELLA_LINK_DIST 自动连成星轨，
    # 星轨每 STELLA_LINK_TICK 秒跳动一次伤害并沿线触发星之贯穿。
    # 数值固定不吃职业系数（见 skills.cooldown_at 与 _apply_role 的 stella_ 豁免），
    # 事件带 dmg 绝对值，经 cast_skill 技能伤卡与 _scale_event 局内强化缩放。
    _STELLA_COL = (190, 150, 255)      # 星轨/星位主色（同 _EL_RANGED_COLOR["星"]）
    _STELLA_COL2 = (255, 214, 140)     # 星芯暖金点缀

    def _stella_link_dmg(self):
        """星轨单跳伤害：设计基数 × 当前技能伤卡/职业系数快照（建轨时定格）。"""
        sd = self.stats.get("skilldmg", 1.0) * self.role_skilldmg
        return max(1, int(round(S.STELLA_LINK_DMG * sd)))

    def _stella_add_node(self, x, y):
        """在地面落一颗星位：超上限删最旧；与近旁星位自动连成星轨
        （间距 ≤STELLA_LINK_DIST；星图共鸣窗口内不限间距）。返回新星位。"""
        x = min(max(float(x), self.s(20)), self.world_w - self.s(20))
        y = min(max(float(y), self.s(20)), self.world_h - self.s(20))
        node = {"x": x, "y": y, "t": S.STELLA_NODE_LIFE,
                "max_t": S.STELLA_NODE_LIFE, "ph": random.uniform(0.0, math.tau)}
        self.stella_nodes.append(node)
        while len(self.stella_nodes) > S.STELLA_NODE_MAX:
            self.stella_nodes.pop(0)          # 溢出删最旧（其星轨随端点失效自清）
        thresh = S.STELLA_LINK_DIST * self.S
        for other in self.stella_nodes[:-1]:
            if self.stella_const_t > 0 or \
                    math.hypot(other["x"] - x, other["y"] - y) <= thresh:
                self._stella_try_link(other, node)
        self._fx_starfall(x, y, self.s(56), life=0.45)
        self._burst(x, y, self._STELLA_COL2, 6)
        return node

    def _stella_try_link(self, a, b):
        """尝试把两颗星位连成星轨（去重：同对星位只连一条）。"""
        for lk in self.stella_links:
            if ((lk["a"] is a and lk["b"] is b)
                    or (lk["a"] is b and lk["b"] is a)):
                return None
        lk = {"a": a, "b": b, "t": S.STELLA_NODE_LIFE, "max_t": S.STELLA_NODE_LIFE,
              "tick": S.STELLA_LINK_TICK, "dmg": self._stella_link_dmg(),
              "const": self.stella_const_t > 0}
        self.stella_links.append(lk)
        self._fx_beam(a["x"], a["y"], b["x"], b["y"], self.s(8),
                      self._STELLA_COL, life=0.3)
        return lk

    def _stella_link_tick(self, lk):
        """星轨一跳：沿线走廊伤害 + 从线上目标向后方延长线触发星之贯穿。"""
        a, b = lk["a"], lk["b"]
        x1, y1, x2, y2 = a["x"], a["y"], b["x"], b["y"]
        half = S.STELLA_LINK_WIDTH * self.S * 0.5
        dmg = lk["dmg"]
        touched = []
        for m in list(self.mobs):
            if not m.alive:
                continue
            if _seg_dist(m.pos[0], m.pos[1], x1, y1, x2, y2) <= half + m.radius:
                touched.append(m)
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1],
                               color=self._STELLA_COL, spark=4)
        self.mobs = [m for m in self.mobs if m.alive]
        boss_hit = False
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if _seg_dist(bx, by, x1, y1, x2, y2) <= half + self.boss.radius_px:
                boss_hit = True
                self._damage_boss(dmg, color=self._STELLA_COL)
        src = touched[0] if touched else None
        if src is None and boss_hit and self.boss is not None:
            src = self.boss
        if src is not None:
            self._stella_pierce(x1, y1, x2, y2, src)
        self._fx_beam(x1, y1, x2, y2, self.s(10), self._STELLA_COL, life=0.18)

    def _stella_pierce(self, x1, y1, x2, y2, src):
        """星之贯穿：沿星轨延长线在 src 后方找最近敌人，追加贯穿伤害 + 光束。"""
        lx, ly = x2 - x1, y2 - y1
        ln = math.hypot(lx, ly)
        if ln < 1e-6:
            return
        ux, uy = lx / ln, ly / ln
        sx, sy = src.pos[0], src.pos[1]
        best = None
        bd = float("inf")
        for o in self.mobs:
            if not o.alive or o is src:
                continue
            t = (o.pos[0] - sx) * ux + (o.pos[1] - sy) * uy
            if t <= o.radius:
                continue                       # 只认线后方（延长线方向）的目标
            d = abs((o.pos[0] - sx) * uy - (o.pos[1] - sy) * ux)
            if d <= S.STELLA_LINK_WIDTH * self.S and t < bd:
                bd, best = t, o
        if best is None:
            return
        self._fx_beam(sx, sy, best.pos[0], best.pos[1], self.s(6),
                      self._STELLA_COL, life=0.22)
        self._hurt_mob(best, S.ELEMENT_STAR_PIERCE, best.pos[0], best.pos[1],
                       color=self._STELLA_COL, spark=6)

    def _stella_burst_line(self, a, b, dmg, color):
        """立即沿线贯穿爆发（连星②/星图共鸣⑤共用）：走廊伤害 + 星之贯穿。"""
        x1, y1, x2, y2 = a["x"], a["y"], b["x"], b["y"]
        half = S.STELLA_LINK_WIDTH * self.S * 0.5 + self.s(10)
        self._fx_beam(x1, y1, x2, y2, self.s(16), color, life=0.34)
        self._spawn_fx_sprite("stella_link", (x1 + x2) / 2, (y1 + y2) / 2,
                              self.s(110), life=0.35, expand=1.5, spin=1.5)
        touched = []
        for m in list(self.mobs):
            if not m.alive:
                continue
            if _seg_dist(m.pos[0], m.pos[1], x1, y1, x2, y2) <= half + m.radius:
                touched.append(m)
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=10)
        self.mobs = [m for m in self.mobs if m.alive]
        src = touched[0] if touched else None
        if src is None and self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if _seg_dist(bx, by, x1, y1, x2, y2) <= half + self.boss.radius_px:
                self._damage_boss(dmg, color=color)
                src = self.boss
        elif src is not None and self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if _seg_dist(bx, by, x1, y1, x2, y2) <= half + self.boss.radius_px:
                self._damage_boss(dmg, color=color)
        if src is not None:
            self._stella_pierce(x1, y1, x2, y2, src)

    def _skill_stella_place(self, ev, px, py, dx, dy):
        """① 落星：向朝向闪现 dist，起点与落点各落 1 颗星位；
        window 秒内再按同键引爆落点处星轨（小范围贯穿，见 _skill_stella_place_det），
        超时失效不爆（见 _update_dash2 的 stella 分支）。"""
        color = ev.get("color", self._STELLA_COL)
        dist = ev.get("dist", S.STELLA_PLACE_DIST) * self.S
        window = ev.get("window", S.STELLA_PLACE_WINDOW)
        x2 = min(max(px + dx * dist, self.snake.radius), self.world_w - self.snake.radius)
        y2 = min(max(py + dy * dist, self.snake.radius), self.world_h - self.snake.radius)
        self.game.audio.play("skill_dash")
        self._stella_add_node(px, py)
        self.snake.pos[0], self.snake.pos[1] = x2, y2
        self._stella_add_node(x2, y2)
        self._fx_trail(px, py, x2, y2, color)
        self._fx_trail(px, py, x2, y2, self._STELLA_COL2, life=0.42)
        self._spawn_fx_sprite(ev.get("sid"), x2, y2, self.s(130),
                              life=0.4, expand=1.6, spin=2.0)
        self._burst(x2, y2, color, 18)
        # 二段挂起：复用 dash2 容器（stella 标记使到期不爆、不画待爆光球）
        self.dash2 = {"x": x2, "y": y2, "t": window, "total": window,
                      "element": "星", "color": color, "ev": ev,
                      "radius": ev.get("det_radius", S.STELLA_PLACE_DET_RADIUS) * self.S,
                      "stella": True}
        self._float(ev.get("name", "落星"), px, py - self.s(54), color, 30)
        self.shake = max(self.shake, 0.24)

    def _skill_stella_place_det(self, ev, dmg):
        """① 落星二段：引爆落点处星轨——小范围伤害 + 星之贯穿（由 cast_skill 再按触发）。"""
        d = self.dash2
        self.dash2 = None
        if d is None:
            return
        x, y = d["x"], d["y"]
        r = d["radius"]
        color = d["color"]
        self.game.audio.play("skill_storm")
        self._fx_nova(x, y, r, color, life=0.5)
        self._fx_starfall(x, y, r, life=0.5)
        self._burst(x, y, self._STELLA_COL2, 18)
        src = None
        for m in list(self.mobs):
            if not m.alive:
                continue
            if math.hypot(m.pos[0] - x, m.pos[1] - y) <= r + m.radius:
                if src is None:
                    src = m
                self._hurt_mob(m, dmg, m.pos[0], m.pos[1], color=color, spark=10)
        self.mobs = [m for m in self.mobs if m.alive]
        if src is not None and src.alive:
            self._stella_pierce(x - r, y, x + r, y, src)   # 横向贯穿后方敌人
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            if math.hypot(bx - x, by - y) <= r + self.boss.radius_px:
                self._damage_boss(dmg, color=color)
        self.shake = max(self.shake, 0.3)

    def _skill_stella_link(self, ev, px, py):
        """② 连星：把最近的星位两两连成星轨并立即沿线贯穿爆发（单条 ev[dmg]＋贯穿）；
        场上不足两颗时先在自身周围补落 2 颗。"""
        color = ev.get("color", self._STELLA_COL)
        nodes = list(self.stella_nodes)
        if len(nodes) < 2:
            for k in range(2):
                ang = k * math.pi + 0.6
                nodes.append(self._stella_add_node(
                    px + math.cos(ang) * S.STELLA_LINK_DIST * self.S * 0.55,
                    py + math.sin(ang) * S.STELLA_LINK_DIST * self.S * 0.55))
        nodes.sort(key=lambda n: math.hypot(n["x"] - px, n["y"] - py))
        sel = nodes[:4]                       # 取最近 4 颗两两相连（最多 6 条，防满屏光束）
        dmg = max(1, int(ev.get("dmg", S.STELLA_LINK_BURST_DMG)))
        self.game.audio.play("skill_storm")
        for i in range(len(sel)):
            for j in range(i + 1, len(sel)):
                lk = self._stella_try_link(sel[i], sel[j])
                if lk is not None:
                    lk["const"] = True        # 立即爆发过的轨转常驻，继续周期跳动
                self._stella_burst_line(sel[i], sel[j], dmg, color)
        self._burst(px, py, color, 16)
        self._float(ev.get("name", "连星"), px, py - self.s(58), color, 30)
        self.shake = max(self.shake, 0.3)

    def _skill_stella_well(self, ev, px, py, dx, dy):
        """③ 星引：在前方指定点开引力井（优先最近敌人脚下），拉扯敌人并入井眩晕，
        井心落 1 颗星位（拉扯/眩晕结算见 _update_stella）。"""
        color = ev.get("color", self._STELLA_COL)
        r = ev.get("radius", S.STELLA_WELL_RADIUS) * self.S
        tgt = self._nearest_target(max_range=r * 3.0)
        if tgt is not None:
            _kind, obj = tgt
            cx, cy = obj.pos[0], obj.pos[1]
        else:
            cx, cy = px + dx * r * 1.2, py + dy * r * 1.2
        cx = min(max(cx, r), max(r, self.world_w - r))
        cy = min(max(cy, r), max(r, self.world_h - r))
        self.stella_wells.append({
            "x": cx, "y": cy, "r": r, "t": ev.get("time", S.STELLA_WELL_TIME),
            "max_t": ev.get("time", S.STELLA_WELL_TIME),
            "strength": ev.get("strength", S.STELLA_WELL_STRENGTH) * self.S,
            "stun": ev.get("stun", S.STELLA_WELL_STUN), "hit": set(),
            "fx": ev.get("sid")})
        self._stella_add_node(cx, cy)
        self.game.audio.play("skill_storm")
        self._fx_vortex(cx, cy, r, color, life=0.55)
        self._float(ev.get("name", "星引"), px, py - self.s(58), color, 30)

    def _skill_stella_shower(self, ev, px, py, base_ang):
        """④ 流星雨：count 枚追踪流星弹（homing 转向见 PlayerBullet.update，
        目标死亡由 _update_stella 重定向），每枚命中在敌人脚下落 1 颗星位。"""
        color = ev.get("color", self._STELLA_COL)
        n = max(1, int(ev.get("count", S.STELLA_SHOWER_COUNT)))
        spd = ev.get("speed", S.STELLA_SHOWER_SPEED) * self.S
        life = ev.get("life", S.STELLA_SHOWER_LIFE)
        dmg = max(1, int(ev.get("dmg", S.STELLA_SHOWER_DMG)))
        targets = self._nearest_mobs(n)
        for i in range(n):
            if i < len(targets):
                tgt = targets[i]
                ax, ay = tgt.pos[0] - px, tgt.pos[1] - py
            else:
                tgt = None
                ang = base_ang + (i - (n - 1) / 2.0) * 0.5
                ax, ay = math.cos(ang), math.sin(ang)
            d0 = math.hypot(ax, ay) or 1.0
            b = PlayerBullet((px, py), (ax / d0 * spd, ay / d0 * spd), dmg,
                             self.s(10), life=life, color=color,
                             pierce=0, element="星", from_skill=True,
                             fx=ev.get("sid"))
            b.homing = tgt
            b.star_node = True
            b.star_trace = True
            self.bullets.append(b)
        self.game.audio.play("skill_bloom")
        self._burst(px, py, color, 18)
        self._fx_starfall(px, py, self.s(120))
        self._float(ev.get("name", "流星雨"), px, py - self.s(58), color, 30)

    def _skill_stella_constellation(self, ev, px, py):
        """⑤ 星图共鸣（大招）：吟唱 time 秒（可移动，复用 channel 读条），
        读满全场星位两两连成星座（见 _finish_constellation）。"""
        color = ev.get("color", self._STELLA_COL)
        self.game.audio.play("skill_shield")
        self.channel = {"t": 0.0,
                        "total": max(0.05, ev.get("time", S.STELLA_CONST_TIME)),
                        "ev": ev, "color": color, "fx": ev.get("sid"),
                        "stella_const": True}
        self.atk_combo = None   # 吟唱接管动作（同 _skill_channel）
        self._fx_aura(px, py, self.s(110), color, life=0.5)
        self._float(ev.get("name", "星图共鸣") + " 吟唱中…", px, py - self.s(58),
                    color, 26)

    def _finish_constellation(self, ev, color):
        """星图共鸣读满：全场星位两两连成星座（取最近 pair，上限 max_lines 条），
        每条星轨 ev[dmg] 伤害＋贯穿；随后 window 秒内新落星位自动连线（不限间距），
        既有星位续满寿命。"""
        px, py = self.snake.pos
        nodes = list(self.stella_nodes)
        pairs = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                d = math.hypot(nodes[i]["x"] - nodes[j]["x"],
                               nodes[i]["y"] - nodes[j]["y"])
                pairs.append((d, nodes[i], nodes[j]))
        pairs.sort(key=lambda p: p[0])
        max_lines = max(1, int(ev.get("max_lines", S.STELLA_CONST_MAX_LINES)))
        dmg = max(1, int(ev.get("dmg", S.STELLA_CONST_DMG)))
        made = 0
        for _d, a, b in pairs:
            if made >= max_lines:
                break
            lk = self._stella_try_link(a, b)
            if lk is None:
                continue                      # 已有星轨：不重复建，但仍沿线爆发
            lk["const"] = True
            made += 1
            self._stella_burst_line(a, b, dmg, color)
        for n in nodes:
            n["t"] = n["max_t"]               # 共鸣把既有星位续满
        self.stella_const_t = ev.get("window", S.STELLA_CONST_WINDOW)
        self._fx_ultimate(px, py, color)
        self._spawn_fx_sprite(ev.get("sid"), px, py, self.s(220),
                              life=0.6, expand=1.8, spin=2.0)
        self.game.audio.play("skill_storm")
        self.shake = max(self.shake, 0.45)
        self.flash = max(self.flash, 0.3)
        self._float(ev.get("name", "星图共鸣"), px, py - self.s(58), color, 34)

    def _update_stella(self, dt):
        """星璃持续态每帧推进：星位到期 / 星轨跳动 / 引力井拉扯 / 星座窗口倒计时。
        地面态不随切人停摆（同潮汐水域/绯焰燃径）。"""
        if self.stella_const_t > 0:
            self.stella_const_t = max(0.0, self.stella_const_t - dt)
        # 星位到期：连带清掉挂在它上的星轨
        if self.stella_nodes:
            for n in self.stella_nodes:
                n["t"] -= dt
            alive = [n for n in self.stella_nodes if n["t"] > 0]
            if len(alive) != len(self.stella_nodes):
                self.stella_nodes = alive
                aset = set(map(id, alive))
                self.stella_links = [lk for lk in self.stella_links
                                     if id(lk["a"]) in aset and id(lk["b"]) in aset]
        # 星轨跳动：每 STELLA_LINK_TICK 秒沿线走廊伤害＋贯穿
        for lk in self.stella_links:
            lk["t"] = min(lk["t"], lk["a"]["t"], lk["b"]["t"])   # 随端点星位到期
            lk["tick"] -= dt
            if lk["tick"] <= 0:
                lk["tick"] += S.STELLA_LINK_TICK
                self._stella_link_tick(lk)
        self.stella_links = [lk for lk in self.stella_links if lk["t"] > 0]
        # 引力井：持续拉扯入井敌人，首次入井眩晕一次
        if self.stella_wells:
            for w in self.stella_wells:
                w["t"] -= dt
                for m in self.mobs:
                    if not m.alive:
                        continue
                    dx, dy = w["x"] - m.pos[0], w["y"] - m.pos[1]
                    d = math.hypot(dx, dy)
                    if d <= w["r"] + m.radius and d > 1.0:
                        m.pos[0] += dx / d * w["strength"] * dt
                        m.pos[1] += dy / d * w["strength"] * dt
                        if m.uid not in w["hit"]:
                            w["hit"].add(m.uid)
                            m.apply_slow(0.05, w["stun"])   # 眩晕＝极限减速（同星元素 proc）
                            self._fx_freeze(m.pos[0], m.pos[1], m.radius)
                self._fx_vortex(w["x"], w["y"], w["r"], self._STELLA_COL, life=0.24)
            self.stella_wells = [w for w in self.stella_wells if w["t"] > 0]
        # 流星雨追踪目标死亡：重定向最近敌人（没有就直飞到底）
        for b in self.bullets:
            if getattr(b, "star_node", False) and b.alive:
                tgt = b.homing
                if tgt is None or not getattr(tgt, "alive", False):
                    pool = self._nearest_mobs(1)
                    b.homing = pool[0] if pool else None

    def _draw_stella_fields(self, screen, sx, sy):
        """星璃·连星成轨地面层：星位/星轨/引力井/星座窗口（画在怪与角色之前，
        直接用 RGBA 在不透明 screen 上混合，同 _draw_zones）。"""
        # 星轨：连线 + 沿线流动星光（跳动临近时更亮，给玩家节奏提示）
        for lk in self.stella_links:
            a, b = lk["a"], lk["b"]
            x1, y1 = int(self.wx(a["x"], sx)), int(self.wy(a["y"], sy))
            x2, y2 = int(self.wx(b["x"], sx)), int(self.wy(b["y"], sy))
            fade = max(0.0, min(1.0, lk["t"] / max(1e-4, lk["max_t"])))
            base_a = int(120 * min(1.0, fade * 4.0))
            glow_a = base_a + int(70 * (1.0 - min(1.0, lk["tick"] / S.STELLA_LINK_TICK)))
            pygame.draw.line(screen, (*self._STELLA_COL, base_a), (x1, y1), (x2, y2),
                             max(2, self.s(5)))
            pygame.draw.line(screen, (*self._STELLA_COL2, min(230, glow_a)),
                             (x1, y1), (x2, y2), max(1, self.s(2)))
            t = (self.elapsed * 1.6 + lk["tick"]) % 1.0
            mx = int(x1 + (x2 - x1) * t)
            my = int(y1 + (y2 - y1) * t)
            spark = self._glow_surf(self.s(9), self._STELLA_COL2, min(220, glow_a + 40))
            screen.blit(spark, spark.get_rect(center=(mx, my)))
        # 星位：柔光 + 脉动四芒星 + 剩余寿命细环
        for n in self.stella_nodes:
            x = int(self.wx(n["x"], sx))
            y = int(self.wy(n["y"], sy))
            fade = max(0.0, min(1.0, n["t"] / max(1e-4, n["max_t"])))
            pulse = 0.75 + 0.25 * math.sin(self.elapsed * 4.0 + n["ph"])
            r = int(self.s(22) * pulse)
            glow = self._glow_surf(r * 2, self._STELLA_COL,
                                   int(90 * min(1.0, fade * 4.0)))
            screen.blit(glow, glow.get_rect(center=(x, y)))
            k = r * 0.9
            pts = [(x, y - k), (x + k * 0.34, y - k * 0.34), (x + k, y),
                   (x + k * 0.34, y + k * 0.34), (x, y + k),
                   (x - k * 0.34, y + k * 0.34), (x - k, y),
                   (x - k * 0.34, y - k * 0.34)]
            pygame.draw.polygon(screen, (*self._STELLA_COL2,
                                         int(225 * min(1.0, fade * 4.0))), pts)
            ring_r = int(self.s(16))
            pygame.draw.arc(screen, (*self._STELLA_COL, 150),
                            pygame.Rect(x - ring_r, y - ring_r,
                                        ring_r * 2, ring_r * 2),
                            math.pi / 2, math.pi / 2 + math.tau * fade,
                            max(1, self.s(2)))
        # 引力井：内卷漩涡 + 井口细环
        for w in self.stella_wells:
            x = int(self.wx(w["x"], sx))
            y = int(self.wy(w["y"], sy))
            r = int(w["r"])
            fade = max(0.0, min(1.0, w["t"] / max(1e-4, w["max_t"])))
            a = int(90 * min(1.0, fade * 3.0))
            pygame.draw.circle(screen, (*self._STELLA_COL, a), (x, y), r)
            pygame.draw.circle(screen, (*self._STELLA_COL2, min(215, a + 90)),
                               (x, y), r, max(2, self.s(3)))
            phase = (self.elapsed * 0.8) % 1.0
            rr = int(r * (1.0 - phase))
            if rr > 2:
                pygame.draw.circle(screen, (225, 210, 255, 60), (x, y), rr,
                                   max(1, self.s(2)))
        # 星图共鸣余韵：全屏星位自动连线窗口，场上星位亮度提升提示
        if self.stella_const_t > 0 and self.stella_nodes:
            ratio = min(1.0, self.stella_const_t / S.STELLA_CONST_WINDOW)
            for i in range(len(self.stella_nodes)):
                for j in range(i + 1, len(self.stella_nodes)):
                    a, b = self.stella_nodes[i], self.stella_nodes[j]
                    x1 = int(self.wx(a["x"], sx))
                    y1 = int(self.wy(a["y"], sy))
                    x2 = int(self.wx(b["x"], sx))
                    y2 = int(self.wy(b["y"], sy))
                    pygame.draw.line(screen, (*self._STELLA_COL, int(46 * ratio)),
                                     (x1, y1), (x2, y2), max(1, self.s(2)))

    def _star_pierce(self, m):
        """星元素贯穿：对最近另一个敌人追加一道星弹伤害。"""
        pool = [o for o in self.mobs if o.alive and o is not m]
        if not pool:
            return
        pool.sort(key=lambda o: math.hypot(o.pos[0] - m.pos[0], o.pos[1] - m.pos[1]))
        tgt = pool[0]
        self._fx_beam(m.pos[0], m.pos[1], tgt.pos[0], tgt.pos[1],
                      self.s(6), (190, 150, 255), life=0.24)
        self._hurt_mob(tgt, S.ELEMENT_STAR_PIERCE, tgt.pos[0], tgt.pos[1],
                       color=(190, 150, 255), spark=6)

    def _apply_combo_secondary(self, m, ev, px, py, use_knock=True):
        """连招组件的元素副效果落地：风击退/水冻结/火灼烧/星眩晕/月削弱。"""
        if ev.get("slow_mult") is not None and ev.get("slow_time"):
            m.apply_slow(ev["slow_mult"], ev["slow_time"])
        if use_knock and ev.get("knock"):
            m.knockback((px, py), ev["knock"])
        fz = ev.get("freeze_time")
        if fz:
            m.apply_slow(S.ELEMENT_FREEZE_MULT, fz)
            self._fx_freeze(m.pos[0], m.pos[1], m.radius)
        if ev.get("burn_dps"):
            m.apply_burn(ev["burn_dps"], ev.get("burn_time", 2.0))
        st = ev.get("stun_time")
        if st:
            m.apply_slow(0.05, st)
            self._fx_freeze(m.pos[0], m.pos[1], m.radius)
        if ev.get("weaken_mult"):
            m.apply_weaken(ev["weaken_mult"], ev.get("weaken_time", 2.0))

    def _update_mob_status(self, dt):
        """灼烧 DoT 结算（减速在 Mob.update 内自结算）。"""
        for m in list(self.mobs):
            if not m.alive or m.burn_t <= 0:
                continue
            m.burn_t = max(0.0, m.burn_t - dt)
            m.burn_acc += m.burn_dps * dt
            whole = int(m.burn_acc)
            if whole > 0:
                m.burn_acc -= whole
                self._burst(m.pos[0], m.pos[1], (255, 140, 80), 2)
                if m.take_damage(whole):
                    self._on_mob_killed(m, m.pos[0], m.pos[1])
            if m.burn_t <= 0:
                m.burn_dps = 0.0
                m.burn_acc = 0.0
        self.mobs = [m for m in self.mobs if m.alive]

    # ------------------------------------------------------------ 特效辅助
    def _fx_ring(self, x, y, r, color, life=0.45):
        self.effects.append({"type": "ring", "x": x, "y": y, "r": r,
                             "color": color, "life": life, "max_life": life})

    def _fx_beam(self, x1, y1, x2, y2, width, color, life=0.35):
        self.effects.append({"type": "beam", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                             "width": width, "color": color, "life": life,
                             "max_life": life})

    def _fx_trail(self, x1, y1, x2, y2, color, life=0.3):
        self.effects.append({"type": "trail", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                             "width": self.s(16), "color": color, "life": life,
                             "max_life": life})

    def _fx_fan(self, x, y, rng, ang, half, color, life=0.4):
        self.effects.append({"type": "fan", "x": x, "y": y, "range": rng, "ang": ang,
                             "half": half, "color": color, "life": life,
                             "max_life": life})

    def _fx_rune(self, x, y, r, color, life=0.5):
        """标记法阵：主环 + 旋转星芒 + 反向内三角（与聚怪/引爆明显区分）。"""
        self.effects.append({"type": "rune", "x": x, "y": y, "r": r,
                             "color": color, "life": life, "max_life": life})

    def _fx_vortex(self, x, y, r, color, life=0.55):
        """聚怪漩涡：三条向内收缩的螺旋臂，直观表达“把怪吸过来”。"""
        self.effects.append({"type": "vortex", "x": x, "y": y, "r": r,
                             "color": color, "life": life, "max_life": life})

    def _fx_nova(self, x, y, r, color, life=0.6):
        """引爆冲击：核心白闪 + 双层震波 + 放射尖刺，最“炸”的一个。"""
        self.effects.append({"type": "nova", "x": x, "y": y, "r": r,
                             "color": color, "life": life, "max_life": life})

    def _fx_aura(self, x, y, r, color, life=0.7):
        """鼓舞上升光柱：脚下一圈向上飘的光柱，表达“增益上身”。"""
        self.effects.append({"type": "aura", "x": x, "y": y, "r": r,
                             "color": color, "life": life, "max_life": life})

    def _fx_freeze(self, x, y, r):
        """冰冻结晶：水/星元素的定身瞬间。"""
        self.effects.append({"type": "freeze", "x": x, "y": y,
                             "r": max(self.s(22), r * 2.4),
                             "color": (150, 220, 255), "life": 0.5, "max_life": 0.5})

    def _fx_petals(self, x, y, r, color):
        """樱花瓣旋涡：绽放/标记时的飞散花瓣。"""
        self.effects.append({"type": "petals", "x": x, "y": y, "r": r,
                             "color": color, "life": 0.6, "max_life": 0.6})

    def _fx_starfall(self, x, y, r, life=0.6):
        """星陨拖尾：星元素的坠落星辉（星璃段3 命中留 0.8s 微星痕亦复用此）。"""
        self.effects.append({"type": "starfall", "x": x, "y": y, "r": r,
                             "color": (190, 150, 255), "life": life, "max_life": life})

    def _fx_element(self, el, x, y, r):
        """按元素追加一层专属特效，让同框架连招不同元素视觉各异。"""
        if el == "樱":
            self._fx_petals(x, y, r, (255, 170, 200))
        elif el == "风":
            self._fx_ring(x, y, r, (150, 240, 190), life=0.4)
            self._fx_ring(x, y, r * 0.6, (210, 255, 225), life=0.3)
        elif el == "水":
            self._fx_ring(x, y, r, (120, 200, 255), life=0.45)
        elif el == "火":
            self._fx_nova(x, y, r * 0.8, (255, 140, 80), life=0.4)
        elif el == "星":
            self._fx_starfall(x, y, r)
        elif el == "月":
            self._fx_ring(x, y, r, (200, 210, 255), life=0.5)

    def _fx_ultimate(self, x, y, color):
        """大招华丽层：大范围光环 + 冲击新星 + 多层粒子 + 震屏。"""
        self._fx_ring(x, y, self.s(210), color, life=0.6)
        self._fx_nova(x, y, self.s(150), color, life=0.55)
        self._burst(x, y, color, 34)
        self._burst(x, y, (255, 255, 255), 18)
        self.shake = max(self.shake, 0.5)

    # ------------------------------------------------------------ 伤害结算
    def _lifesteal_heal(self, dmg):
        """吸血：概率触发。每次造成伤害有 LIFESTEAL_PROC_CHANCE 概率吸血，
        触发时按 stats['lifesteal'] × LIFESTEAL_PROC_BONUS 把伤害转化为生命
        （浮点、封顶 hp_max）。回血用绿色飘字，按整数节流避免刷屏。"""
        rate = self.stats.get("lifesteal", 0.0)
        if rate <= 0 or dmg <= 0 or not self.snake.alive:
            return
        if self.snake.hp >= self.snake.hp_max:
            return
        if random.random() >= S.LIFESTEAL_PROC_CHANCE:
            return                                  # 未触发：本次不吸血
        before = self.snake.hp
        self.snake.hp = min(float(self.snake.hp_max),
                            self.snake.hp + float(dmg) * rate * S.LIFESTEAL_PROC_BONUS)
        gained = self.snake.hp - before
        if gained <= 0:
            return
        self._ls_acc += gained
        if self._ls_acc >= 1.0:
            shown = int(self._ls_acc)
            self._ls_acc -= shown
            self._float(f"+{shown}", self.snake.pos[0],
                        self.snake.pos[1] - self.s(44), COLOR_GOOD, 20)

    def _hurt_mob(self, m, dmg, mx, my, color=COLOR_GOLD, spark=0):
        killed = m.take_damage(dmg)
        m.knockback(self.snake.pos, 120.0)
        self._float(f"-{dmg}", mx, my, color, 22)
        if spark:
            self._burst(mx, my, color, spark)
        self._lifesteal_heal(dmg)
        if killed:
            self._on_mob_killed(m, mx, my)

    def _on_mob_killed(self, m, mx, my):
        self.kills += 1
        self.game.audio.play("kill", throttle=0.04)
        self.score += 60
        self._burst(mx, my, (200, 130, 255), 20)
        # 掉落：精英必掉多份（drop_count），普通怪先过 DROP_CHANCE 概率门
        if getattr(m, "is_elite", False):
            n_drop = max(1, int(getattr(m, "drop_count", S.ELITE_DROPS)))
        else:
            n_drop = 1 if random.random() < S.DROP_CHANCE else 0
        for _ in range(n_drop):
            jx = m.pos[0] + random.uniform(-self.s(30), self.s(30))
            jy = m.pos[1] + random.uniform(-self.s(30), self.s(30))
            self.drops.append(Drop(self._roll_kind(), (jx, jy),
                                   tier=self._item_tier()))
        if getattr(m, "is_elite", False):
            self.score += 400
            self._burst(mx, my, (255, 90, 120), 40)
            self.shake = max(self.shake, 0.4)
        # 被动：花守(击杀概率回血) / 星辉(击杀减主动 CD)
        if self.passive_kind == "heal":
            if (self.snake.hp < self.snake.hp_max
                    and random.random() < S.PASSIVE_BLOOM_HEAL_CHANCE):
                healed = min(S.PASSIVE_BLOOM_HEAL, self.snake.hp_max - self.snake.hp)
                self.snake.hp += healed
                self._float(f"+{int(round(healed))} HP", mx, my - self.s(20), COLOR_HP)
        elif self.passive_kind == "cdr":
            self.skills.reduce_cd(S.PASSIVE_STARLIGHT_CDR)

    def _pay_skill_cost(self, frac):
        """技能自身代价（法师「消耗多」）：按最大生命比例自伤。

        不走护甲/护盾减免，也不触发受击表现（不是被打，是自己烧的），
        最低留 1 点血——代价永远不能把自己烧死。"""
        try:
            frac = float(frac)
        except (TypeError, ValueError):
            return
        if frac <= 0.0 or not self.snake.alive:
            return
        amt = self.snake.hp_max * frac
        if amt <= 0.0:
            return
        self.snake.hp = max(1.0, self.snake.hp - amt)
        px, py = self.snake.pos
        self._float(f"-{int(round(amt))} 代价", px, py - self.s(46),
                    (255, 150, 120), 24)

    def _snake_hurt(self, amount):
        """玩家承伤入口：血条制下直接扣浮点血。静夜被动 / 护甲卡 / 职业免伤 / 鼓舞满级按倍率减免。
        受击无敌帧(invincible)期间免疫；护盾由 take_damage 内部优先扣吸收池。返回本次实际扣除的血量（0=未命中）。"""
        if self.snake.invincible > 0 or not self.snake.alive:
            return 0.0
        mult = 1.0
        if self.passive_kind == "guard":
            mult *= S.PASSIVE_NIGHT_REDUCE
        # 樱落·花守：花护层数减伤（每层 SAKURA_GUARD_REDUCE，绽放叠层，上限 GUARD_MAX）
        if self.passive_kind == "bloomguard" and self.sakura_guard > 0:
            mult *= (1.0 - S.SAKURA_GUARD_REDUCE * self.sakura_guard)
        # 潮汐·后浪：潮汐在后台且存活时，出战角色免伤（强化达标 20%，否则 15%）
        bw = self._backwave_reduce()
        if bw > 0:
            mult *= (1.0 - bw)
        # 潮汐·涌潮水域：己方站在其中减伤 15%
        if self._active_in_zone():
            mult *= (1.0 - S.TIDE_ZONE_ALLY_REDUCE)
        # 潮汐·踏浪登场：在水域上切人后短时减伤 10%
        if getattr(self, "landing_t", 0.0) > 0:
            mult *= (1.0 - S.PASSIVE_WAVE_LANDING_REDUCE)
        armor = min(S.ARMOR_CAP, self.stats.get("armor", 0.0) + self.role_armor)
        if self.rally_t > 0 and self.rally_armor > 0:
            armor = min(S.ARMOR_CAP, armor + self.rally_armor)
        mult *= (1.0 - armor)
        if self.ward_t > 0:
            mult *= S.ELEMENT_MOON_WARD_MULT
        amt = max(0.0, float(amount) * mult)
        if amt <= 0:
            return 0.0
        before = self.snake.hp
        if self.snake.take_damage(amt):
            return before - self.snake.hp
        return 0.0

    def _on_hurt(self, amount=0):
        self.game.audio.play("hurt")
        self.shake = 0.6
        self.flash = 0.5
        self.snake.hurt_t = 0.35              # 触发受击动画（红 tint + 后座）
        px, py = self.snake.pos
        shown = int(round(amount)) if amount else 0
        self._float(f"-{shown}" if shown > 0 else "-HP",
                    px, py - self.s(30), COLOR_DANGER, 32)
        self._burst(px, py, (255, 90, 110), 20)

    def _on_level_up(self, level, gained):
        # 经验共享：升级后把进度镜像给其余成员，并按 1→2 号位排队各选一张卡
        self._mirror_progress()
        for _ in range(max(0, int(gained))):
            self.card_queue.extend(range(len(self.party)))
        self.game.audio.play("level_up")
        self.flash = max(self.flash, 0.3)

    def _mirror_progress(self):
        """编队共享等级/经验：把活跃成员的进度写回其余成员（不触发升级回调）。"""
        sn = self.snake
        for m in self.party:
            other = m["snake"]
            if other is sn:
                continue
            other.level = sn.level
            other.exp = sn.exp

    # ================================================================ Boss 战
    def _update_boss(self, dt):
        if self.boss_hit_cd > 0:
            self.boss_hit_cd -= dt
        if self.boss_banner > 0:
            self.boss_banner -= dt

        if (self.boss is None and not self.boss_spawned and self.boss_cfg
                and boss_trigger_met(self.boss_cfg, self.elapsed,
                                     self.snake.level, self.kills)):
            self._spawn_boss()

        if self.boss is None:
            return
        if not self.boss.alive:
            self._on_boss_defeated()
            return

        snake_cell = (self.snake.pos[0] / self.CELL, self.snake.pos[1] / self.CELL)
        ctx = {"cols": self.world_cols, "rows": self.world_rows, "cell_px": self.CELL}
        events = self.boss.update(dt, snake_cell, ctx)

        for name in events.get("sfx", []):
            self.game.audio.play(name, throttle=0.05)
        self.projectiles.extend(events.get("bullets", []))
        for _ in range(events.get("summon", 0)):
            self._spawn_mob()
        for eff in events.get("effects", []):
            if eff.get("type") == "slam_burst":
                self._resolve_slam(eff)

        for p in self.projectiles:
            p.update(dt, self.world_cols, self.world_rows, self.CELL)
        self.projectiles = [p for p in self.projectiles if p.alive]

        self._handle_projectile_hits()
        self._handle_boss_contact()

        if not self.boss.alive:
            self._on_boss_defeated()

    def _spawn_boss(self):
        px = self.snake.pos[0]
        cx = self.world_cols - 4 if px < self.world_w / 2 else 3
        cy = self.world_rows / 2
        cfg = dict(self.boss_cfg or {})
        try:
            cfg["hp"] = max(1, int(round(float(cfg.get("hp", 1200)) * self.scene_density)))
        except (TypeError, ValueError):
            pass
        self.boss = Boss(cfg, (cx, cy), lambda: self.CELL)
        self.boss_spawned = True
        self.projectiles = []
        self.boss_banner = 2.6
        self.shake = max(self.shake, 0.6)
        self.flash = max(self.flash, 0.5)
        self.game.audio.play_bgm("boss")
        self.game.audio.play("boss_appear")

    def _resolve_slam(self, eff):
        ex, ey = eff["pos"]
        r = eff["radius_px"]
        self._burst(ex, ey, (255, 200, 120), 30)
        self.shake = max(self.shake, 0.5)
        px, py = self.snake.pos
        if math.hypot(px - ex, py - ey) <= r + self.snake.radius:
            dmg = self._snake_hurt(S.BOSS_SLAM_DAMAGE)
            if dmg:
                self._on_hurt(dmg)

    def _handle_projectile_hits(self):
        if not self.projectiles:
            return
        px, py = self.snake.pos
        pr = self.snake.radius
        for p in self.projectiles:
            if not p.alive:
                continue
            if math.hypot(p.pos[0] - px, p.pos[1] - py) <= p.radius + pr:
                p.alive = False
                self._burst(p.pos[0], p.pos[1], (255, 120, 150), 8)
                dmg = self._snake_hurt(p.damage)
                if dmg:
                    self._on_hurt(dmg)
        self.projectiles = [p for p in self.projectiles if p.alive]

    def _handle_boss_contact(self):
        if self.boss is None or not self.boss.alive:
            return
        px, py = self.snake.pos
        bx, by = self.boss.draw_pos
        if math.hypot(px - bx, py - by) > self.boss.radius_px + self.snake.radius:
            return
        if self.boss.charge_active:
            dmg = self._snake_hurt(S.BOSS_CHARGE_DAMAGE)
            if dmg:
                self._on_hurt(dmg)
                self.shake = max(self.shake, 0.5)
            return
        if self.boss_hit_cd > 0:
            return
        self.boss_hit_cd = S.BOSS_HIT_CD
        self._damage_boss(S.PLAYER_ATK, color=COLOR_GOLD)

    def _damage_boss(self, amount, color=COLOR_GOLD):
        if self.boss is None or not self.boss.alive:
            return
        bx, by = self.boss.draw_pos
        self.boss.take_damage(amount)
        self.game.audio.play("boss_hit", throttle=0.04)
        self._float(f"-{amount}", bx, by - self.boss.radius_px * 0.6, color, 26)
        self._burst(bx, by, color, 10)
        self._lifesteal_heal(amount)

    def _on_boss_defeated(self):
        if self.victory:
            return
        self.victory = True
        self.finished = True
        self._finish_tutorial()
        self._clear_suspend()
        self.projectiles = []
        bx, by = self.boss.draw_pos
        self._burst(bx, by, (255, 220, 140), 60)
        self.shake = max(self.shake, 0.8)
        self.flash = max(self.flash, 0.6)
        self.score += 1000
        self.game.audio.play("boss_defeat")
        self.game.audio.play("victory")
        self.game.save_manager.add_stardust(self.stardust + S.BOSS_REWARD_STARDUST)
        self.game.save_manager.record_victory(
            self.scene_id, self.score, self.snake.level,
            self.kills, int(self.elapsed))
        # 剧情模式：击败 Boss 通关，解锁下一关
        if self.mode == "story" and self.level_index > 0:
            rec = getattr(self.game.save_manager, "record_level_clear", None)
            if rec:
                rec(self.level_index)

    # ================================================================ 摄像机
    def _update_cam(self, dt):
        tx = self.snake.pos[0] - self.W / 2
        ty = self.snake.pos[1] - self.H / 2
        k = 1.0 - math.exp(-S.CAM_LERP * dt)
        self.cam[0] += (tx - self.cam[0]) * k
        self.cam[1] += (ty - self.cam[1]) * k
        self._clamp_cam()

    # ================================================================ 特效
    def _burst(self, x, y, color, n):
        for _ in range(n):
            a = random.random() * 6.283
            sp = random.uniform(70, 330) * self.S
            self.particles.append({
                "x": x, "y": y,
                "vx": math.cos(a) * sp, "vy": math.sin(a) * sp - 60 * self.S,
                "life": random.uniform(0.28, 0.7), "max_life": 0.7,
                "color": color, "r": random.randint(self.s(2), self.s(5)),
            })

    def _float(self, text, x, y, color, size=26):
        self.floaters.append({"text": text, "x": x, "y": y,
                              "color": color, "life": 0.9, "size": self.s(size)})

    def _tick_particles(self, dt):
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 280 * dt * self.S
                yield p

    def _tick_floaters(self, dt):
        for f in self.floaters:
            f["life"] -= dt
            f["y"] -= 48 * dt * self.S
            if f["life"] > 0:
                yield f

    # ================================================================ 新手指引
    def _update_tutorial(self, dt):
        """按 TUTORIAL_HINT_DURATION 逐条推进提示；走完则标记完成。"""
        if not self.tutorial_active:
            return
        self.tutorial_timer += dt
        if self.tutorial_timer >= S.TUTORIAL_HINT_DURATION:
            self.tutorial_timer = 0.0
            self.tutorial_index += 1
            if self.tutorial_index >= len(self.tutorial_hints):
                self.tutorial_active = False
                self._finish_tutorial()

    def _finish_tutorial(self):
        """首局结束或提示走完：把当前槽标记为已看过指引并存盘（幂等）。"""
        self.tutorial_active = False
        try:
            if not self.game.save_manager.get("tutorial_done", False):
                self.game.save_manager.set("tutorial_done", True)
        except Exception:
            pass

    def _draw_tutorial(self):
        if not self.tutorial_active:
            return
        if self.tutorial_index >= len(self.tutorial_hints):
            return
        text = self.tutorial_hints[self.tutorial_index]
        screen = self.screen
        dur = S.TUTORIAL_HINT_DURATION
        t = self.tutorial_timer
        if t < 0.4:
            fade = t / 0.4
        elif t > dur - 0.6:
            fade = max(0.0, (dur - t) / 0.6)
        else:
            fade = 1.0
        label = f"新手指引  {self.tutorial_index + 1}/{len(self.tutorial_hints)}"
        tsurf = self.f_body.render(text, True, (255, 255, 255))
        lsurf = self.f_small.render(label, True, COLOR_GOLD)
        pad = self.s(20)
        w = max(tsurf.get_width(), lsurf.get_width()) + pad * 2
        h = lsurf.get_height() + tsurf.get_height() + pad * 2 + self.s(6)
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((20, 18, 32, 225))
        pygame.draw.rect(panel, (*COLOR_ACCENT, 255), panel.get_rect(),
                         self.s(2), border_radius=self.s(10))
        panel.blit(lsurf, (pad, pad))
        panel.blit(tsurf, (pad, pad + lsurf.get_height() + self.s(6)))
        panel.set_alpha(int(255 * fade))
        x = (self.W - w) // 2
        # 上移到技能槽名字标签之上，避免浮层压住底部技能栏文字
        y = self.H - self.s(216)
        screen.blit(panel, (x, y))

    # ================================================================ 升级选卡
    def _card_target(self):
        """当前浮层要为哪位成员选卡：card_queue 首位；队空时回退活跃成员。"""
        if self.card_queue:
            idx = int(self.card_queue[0])
            if 0 <= idx < len(self.party):
                return self.party[idx]
        return self.party[self.active_idx]

    def _is_active(self, m):
        return m is self.party[self.active_idx]

    def _enhanceable_sids(self, member=None):
        """目标成员里还能强化的主动 sid（局内等级 < SKILL_ENH_MAX）。"""
        m = member or self.party[self.active_idx]
        return [sid for sid in m["skills"].active_sids
                if m["skill_lv"].get(sid, 0) < S.SKILL_ENH_MAX]

    def _make_enh_card(self, sid, member=None):
        """为某主动动态生成一张「强化·<技能名>」卡（type=skill_enh，展示信息取自技能）。"""
        m = member or self.party[self.active_idx]
        info = skill_info(sid)
        lv = m["skill_lv"].get(sid, 0)
        name = info.get("name", sid)
        tail = ("满级：解锁专属强化机制" if lv + 1 >= S.SKILL_ENH_MAX
                else "伤害/范围提升，冷却缩短")
        return {
            "id": f"enh_{sid}", "type": "skill_enh", "sid": sid, "lv": lv,
            "name": f"强化·{name}", "icon": info.get("vfx", ""),
            "color": list(info.get("color", (255, 255, 255))),
            "desc": f"{name} 强化至 Lv.{lv + 1}/{S.SKILL_ENH_MAX}：{tail}",
        }

    def _stat_preview(self, stat, m):
        """属性卡的成长预览：返回 (当前值, 选中后值) 两个展示字符串。
        乘区型属性（基准 1.0）展示为「加成百分比」，递减/叠加型按各自口径。"""
        c = m["card_stats"]

        def pc(x):
            return f"{round(x * 100)}%"

        mult_steps = {
            "atk": S.CARD_ATK_STEP, "speed": S.CARD_SPEED_STEP,
            "atkspd": S.CARD_ATKSPD_STEP, "pickup": S.CARD_PICKUP_STEP,
            "exp": S.CARD_EXP_STEP, "skilldmg": S.CARD_SKILLDMG_STEP,
            "range": S.CARD_RANGE_STEP,
        }
        if stat in mult_steps:
            cur = c.get(stat, 1.0) - 1.0
            return f"+{round(cur * 100)}%", f"+{round((cur + mult_steps[stat]) * 100)}%"
        if stat == "cdr":
            cur = c["cdr"]
            return pc(cur), pc(min(0.75, cur + S.CARD_CDR_STEP))
        if stat == "armor":
            cur = c["armor"]
            return pc(cur), pc(min(S.ARMOR_CAP, cur + S.CARD_ARMOR_STEP))
        if stat == "lifesteal":
            cur = c["lifesteal"]
            return pc(cur), pc(min(S.LIFESTEAL_CAP, cur + S.CARD_LIFESTEAL_STEP))
        if stat == "shield":
            cur = c.get("shield", 0.0)
            return pc(cur), pc(min(S.SHIELD_STAT_CAP, cur + S.CARD_SHIELD_STEP))
        if stat == "regen":
            cur = c["regen"]
            return f"{cur:.1f}/秒", f"{cur + S.CARD_REGEN_STEP:.1f}/秒"
        if stat == "hp":
            cur = int(m["snake"].hp_max)
            return f"{cur}", f"{cur + S.CARD_HP_STEP}"
        return "", ""

    def _with_preview(self, card, m):
        """给属性卡附加一行「当前 → 选中后」预览（不改缓存里的原卡）。"""
        stat = card.get("stat")
        if not stat:
            return card
        cur, nxt = self._stat_preview(stat, m)
        if not cur and not nxt:
            return card
        c = dict(card)
        c["preview"] = f"{cur}  →  {nxt}"
        return c

    def _roll_cards(self, member=None):
        # 属性卡（去掉旧 skill 类型）+ 为目标成员未满级主动动态生成的「强化卡」一起抽
        m = member or self.party[self.active_idx]
        candidates = [(self._with_preview(c, m), 2) for c in self._card_pool()
                      if c.get("type") != "skill"]
        candidates += [(self._make_enh_card(sid, m), 2)
                       for sid in self._enhanceable_sids(m)]
        result = []
        while len(result) < S.CARD_CHOICES and candidates:
            total = sum(w for _c, w in candidates)
            r = random.random() * total
            acc = 0.0
            for i, (c, w) in enumerate(candidates):
                acc += w
                if r <= acc:
                    result.append(c)
                    candidates.pop(i)
                    break
            else:
                break
        return result

    def _layout_card_rects(self):
        n = len(self.card_overlay)
        cw, ch = self.s(220), self.s(300)
        gap = self.s(28)
        total = cw * n + gap * (n - 1)
        x0 = self.W // 2 - total // 2
        y0 = self.H // 2 - ch // 2
        self.card_rects = [pygame.Rect(x0 + i * (cw + gap), y0, cw, ch)
                           for i in range(n)]

    def _open_card_overlay(self):
        while True:
            m = self._card_target()
            cards = self._roll_cards(m)
            if cards:
                self.card_overlay = cards
                self._layout_card_rects()
                return
            if not self.card_queue:
                self.card_overlay = None
                self.card_rects = []
                return
            self.card_queue.pop(0)      # 该成员已无卡可选，跳给下一位

    def _choose_card(self, index):
        if self.card_overlay is None:
            return
        if index < 0 or index >= len(self.card_overlay):
            return
        card = self.card_overlay[index]
        m = self._card_target()
        if card.get("type") == "skill_enh":
            self._apply_skill_enhance(card.get("sid"), m)
        else:
            self._apply_passive(card.get("stat"), m)
        self.game.audio.play("card_pick")
        if self.card_queue:
            self.card_queue.pop(0)
        self.card_overlay = None
        self.card_rects = []

    def _apply_skill_enhance(self, sid, member=None):
        """强化卡：目标成员的对应主动局内等级 +1（封顶 SKILL_ENH_MAX）。"""
        m = member or self.party[self.active_idx]
        lv_dict = m["skill_lv"]      # 即 m["skills"].levels（同一字典）
        if not sid or sid not in lv_dict:
            return
        if lv_dict[sid] >= S.SKILL_ENH_MAX:
            return
        lv_dict[sid] += 1
        lv = lv_dict[sid]
        info = skill_info(sid)
        color = tuple(info.get("color", (255, 226, 140)))
        px, py = self.snake.pos      # 飘字一律给场上角色，待命者位置不在镜头内
        if self._is_active(m):
            self.skill_toast.append({"sid": sid, "life": 3.0})
        tag = "满级!" if lv >= S.SKILL_ENH_MAX else f"Lv.{lv}"
        who = "" if self._is_active(m) else f"{m['name']} "
        self._float(f"{who}{info.get('name', sid)} {tag}", px, py - self.s(56), color, 30)
        self._burst(px, py, color, 26)

    def _apply_passive(self, stat, member=None):
        """属性卡：写进目标成员的局内属性副本，再重算活跃成员最终属性。"""
        m = member or self.party[self.active_idx]
        c = m["card_stats"]
        px, py = self.snake.pos
        who = "" if self._is_active(m) else f"{m['name']} "
        if stat == "atk":
            c["atk"] += S.CARD_ATK_STEP
            self._float(who + "攻击强化", px, py - self.s(50), (255, 120, 120), 28)
        elif stat == "speed":
            c["speed"] += S.CARD_SPEED_STEP
            self._float(who + "移速强化", px, py - self.s(50), (140, 220, 255), 28)
        elif stat == "atkspd":
            c["atkspd"] += S.CARD_ATKSPD_STEP
            self._float(who + "攻速强化", px, py - self.s(50), (255, 200, 120), 28)
        elif stat == "cdr":
            c["cdr"] = min(0.75, c["cdr"] + S.CARD_CDR_STEP)
            self._float(who + "冷却缩减", px, py - self.s(50), (180, 160, 255), 28)
        elif stat == "pickup":
            c["pickup"] += S.CARD_PICKUP_STEP
            self._float(who + "拾取强化", px, py - self.s(50), (200, 160, 255), 28)
        elif stat == "hp":
            m["hp_bonus"] += S.CARD_HP_STEP
            self._rebuild_member_hp(m)
            m["snake"].hp = float(m["snake"].hp_max)
            self._float(who + f"生命上限 +{S.CARD_HP_STEP}", px, py - self.s(50),
                        COLOR_HP, 28)
        elif stat == "exp":
            c["exp"] += S.CARD_EXP_STEP
            self._float(who + "经验获取提升", px, py - self.s(50), COLOR_EXP, 28)
        elif stat == "armor":
            c["armor"] = min(S.ARMOR_CAP, c["armor"] + S.CARD_ARMOR_STEP)
            self._float(who + "伤害减免", px, py - self.s(50), (180, 200, 230), 28)
        elif stat == "regen":
            c["regen"] += S.CARD_REGEN_STEP
            self._float(who + "生命再生", px, py - self.s(50), COLOR_GOOD, 28)
        elif stat == "skilldmg":
            c["skilldmg"] += S.CARD_SKILLDMG_STEP
            self._float(who + "技能伤害提升", px, py - self.s(50), (255, 160, 120), 28)
        elif stat == "range":
            c["range"] += S.CARD_RANGE_STEP
            self._float(who + "索敌范围提升", px, py - self.s(50), (200, 220, 140), 28)
        elif stat == "lifesteal":
            c["lifesteal"] = min(S.LIFESTEAL_CAP,
                                 c["lifesteal"] + S.CARD_LIFESTEAL_STEP)
            self._float(who + "嗜血之牙", px, py - self.s(50), (255, 90, 120), 28)
        elif stat == "shield":
            c["shield"] = min(S.SHIELD_STAT_CAP, c["shield"] + S.CARD_SHIELD_STEP)
            self._float(who + "护盾强化", px, py - self.s(50), (140, 220, 255), 28)
        self._rebuild_stats()
        self._burst(px, py, (255, 226, 140), 20)

    # ================================================================ 渲染
    def draw(self):
        screen = self.screen
        sx = sy = 0.0
        if self.shake > 0:
            sx = random.uniform(-1, 1) * self.shake * self.s(14)
            sy = random.uniform(-1, 1) * self.shake * self.s(14)

        self._draw_background(screen, sx, sy)
        self._draw_world_border(screen, sx, sy)
        self._draw_zones(screen, sx, sy)
        self._draw_stella_fields(screen, sx, sy)
        self._draw_effects(screen, sx, sy)
        self._draw_boss_telegraph(screen, sx, sy)
        self._draw_drops(screen, sx, sy)
        self._draw_mobs(screen, sx, sy)
        self._draw_boss(screen, sx, sy)
        self._draw_bullets(screen, sx, sy)
        self._draw_dash2_pending(screen, sx, sy)
        self._draw_gusts(screen, sx, sy)
        self._draw_fx_sprites(screen, sx, sy)
        self._draw_snake(screen, sx, sy)
        self._draw_channel_bar(screen, sx, sy)
        self._draw_projectiles(screen, sx, sy)
        self._draw_particles(screen, sx, sy)
        self._draw_floaters(screen, sx, sy)

        if self.flash > 0:
            veil = self._overlay()
            veil.fill((255, 70, 100, int(70 * self.flash)))
            screen.blit(veil, (0, 0))

        self._draw_hud()
        self._draw_boss_banner()
        self._draw_skill_toast()
        self._draw_tutorial()
        self._draw_switch_hint(screen)

        if self.card_overlay:
            self._draw_card_overlay()
        elif self.finished:
            self._draw_gameover()
        elif self.paused:
            if self.rebind_open:
                self._draw_rebind()
            else:
                self._draw_pause()

    def _draw_background(self, screen, sx, sy):
        screen.fill(COLOR_BG)
        if (self._bg_surf is None
                or self._bg_surf.get_size() != (self.world_w, self.world_h)):
            base = self.assets.get_image(self.scene_bg)
            surf = pygame.transform.smoothscale(
                base, (max(1, self.world_w), max(1, self.world_h)))
            # 暗纱直接烘进背景图（一次性），省掉每帧一次全屏半透明 blit；
            # 烘完 convert() 转不透明面，后续每帧是不带 alpha 的快速 blit。
            veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            veil.fill((14, 12, 22, 70))
            surf.blit(veil, (0, 0))
            self._bg_surf = surf.convert()
        screen.blit(self._bg_surf, (int(self.wx(0, sx)), int(self.wy(0, sy))))

    def _draw_world_border(self, screen, sx, sy):
        rect = pygame.Rect(int(self.wx(0, sx)), int(self.wy(0, sy)),
                           self.world_w, self.world_h)
        pygame.draw.rect(screen, COLOR_ACCENT_DARK, rect, max(2, self.s(3)))

    def _draw_zones(self, screen, sx, sy):
        """潮汐·涌潮水域：地面半透明水洼（世界坐标），随剩余时间淡出、边缘泛波纹。
        画在怪/角色之前当作地面贴花；直接用 RGBA 在不透明 screen 上混合（同 _draw_effects）。"""
        if not getattr(self, "zones", None):
            return
        for z in self.zones:
            x = int(self.wx(z["x"], sx))
            y = int(self.wy(z["y"], sy))
            r = int(z["r"])
            if r <= 0:
                continue
            fade = max(0.0, min(1.0, z["t"] / max(1e-4, z["max_t"])))
            base_a = int(78 * min(1.0, fade * 4.0))   # 到期前快速收敛，不硬切
            pygame.draw.circle(screen, (60, 140, 210, base_a), (x, y), r)
            pygame.draw.circle(screen, (150, 215, 255, min(215, base_a + 95)),
                               (x, y), r, max(2, self.s(3)))
            phase = (self.elapsed * 0.5) % 1.0
            for k in (0.0, 0.5):
                rr = int(r * ((phase + k) % 1.0))
                if rr > 2:
                    pygame.draw.circle(screen, (205, 238, 255, 44), (x, y), rr,
                                       max(1, self.s(2)))

    # ================================================================ 绘制缓存
    def _cached_surf(self, key, size, draw_fn):
        """按 key 缓存「画一次反复用」的小装饰面（阴影/光环/泡泡）。

        怪潮时每怪每帧新建 Surface+draw 是掉帧主因之一；装饰面尺寸只随
        缩放/体型变化，画一次进缓存，之后每帧只 blit。_setup_view 清缓存。
        """
        surf = self._surf_cache.get(key)
        if surf is None:
            surf = pygame.Surface(size, pygame.SRCALPHA)
            draw_fn(surf)
            self._surf_cache[key] = surf
        return surf

    def _cached_text(self, font, text, color):
        """缓存字体渲染结果（SDL_ttf render 很慢，精英名每帧 render 会拖帧）。"""
        key = (id(font), text, color)
        surf = self._text_cache.get(key)
        if surf is None:
            surf = font.render(text, True, color)
            self._text_cache[key] = surf
        return surf

    # ---- 旋转 / 缩放 / 柔光 查表缓存（技能 VFX 掉帧优化的核心）----
    # 说明：base 均来自 _skill_fx_surf/_bullet_sprite/_gust_sprite，已存进
    # _surf_cache 常驻不释放，故 id(base) 在本场景生命周期内稳定可作键；
    # resize 时 _setup_view 整体清空 _surf_cache，base 与派生副本一起失效，无脏键。
    def _rot_surf(self, base, angle_deg):
        """按角度查表缓存「旋转后的 base」，代替每帧 pygame.transform.rotate 重采样。
        angle_deg 顺时针为正（与旧代码 rotate(base, -ang) 的方向约定一致）。"""
        if base is None:
            return None
        step = int(round((angle_deg % 360.0) / (360.0 / _ROT_STEPS))) % _ROT_STEPS
        key = ("rot", id(base), step)
        surf = self._surf_cache.get(key)
        if surf is None:
            surf = pygame.transform.rotate(base, -step * (360.0 / _ROT_STEPS))
            self._surf_cache[key] = surf
        return surf

    def _rotozoom_surf(self, base, angle_deg, scale):
        """按 (角度档, 缩放档) 查表缓存 rotozoom，代替每帧重采样。
        用于一次性技能贴图特效(fx_sprites)与吟唱光环这类既转又缩放的绘制。"""
        if base is None:
            return None
        step = int(round((angle_deg % 360.0) / (360.0 / _ROT_STEPS))) % _ROT_STEPS
        zs = max(1, int(round(scale * _RZ_SCALE_STEPS)))
        key = ("rz", id(base), step, zs)
        surf = self._surf_cache.get(key)
        if surf is None:
            surf = pygame.transform.rotozoom(
                base, -step * (360.0 / _ROT_STEPS), zs / _RZ_SCALE_STEPS)
            self._surf_cache[key] = surf
        return surf

    def _glow_surf(self, radius, color, alpha):
        """缓存柔光圆（radial glow）：按 (半径,色,透明度) 画一次反复 blit，
        代替弹丸/阵风/道具/弹幕每帧新建 Surface+draw.circle 的高频分配。"""
        radius = max(1, int(radius))
        color = tuple(color)
        alpha = int(alpha)
        return self._cached_surf(
            ("glow", radius, color, alpha), (radius * 2, radius * 2),
            lambda s: pygame.draw.circle(s, (*color, alpha), (radius, radius), radius))

    def _overlay(self):
        """复用的全屏半透明画布（特效/粒子/受击幕），每帧清空，避免反复分配 W*H。"""
        ov = self._ov_surf
        if ov is None or ov.get_size() != (self.W, self.H):
            ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            self._ov_surf = ov
        else:
            ov.fill((0, 0, 0, 0))
        return ov

    def _fig_surf(self, body_img, fig_h, flip):
        """全身立绘按 (图, 高, 是否翻转) 缓存，避免每帧 smoothscale/flip 大图。"""
        key = ("fig", body_img, fig_h, flip)
        surf = self._surf_cache.get(key)
        if surf is None:
            base = self.assets.get_scaled(body_img, height=fig_h)
            surf = pygame.transform.flip(base, True, False) if flip else base
            self._surf_cache[key] = surf
        return surf

    def _draw_effects(self, screen, sx, sy):
        """技能特效：每种技能都有独特的形状/运动签名，并用多层发光做华丽。
        ring=涌潮水环 / beam=月光束 / trail=突进斩拖影 / fan=火焰扇 /
        rune=标记法阵(旋转星芒) / vortex=聚怪漩涡(内卷螺旋) /
        nova=引爆冲击(震波+放射尖刺+核心闪光) / aura=鼓舞上升光柱。"""
        if not self.effects:
            return
        # 直接画到 screen：省掉全屏半透明画布的每帧 clear + 全屏 blit。
        # pygame.draw / blit 的 RGBA 颜色在不透明面上同样按 alpha 混合，观感不变。
        ov = screen
        for e in self.effects:
            ratio = max(0.0, min(1.0, e["life"] / e["max_life"]))
            prog = 1.0 - ratio                     # 0→1 播放进度
            a = int(248 * ratio)
            if a <= 0:
                continue
            col = e["color"]
            et = e["type"]
            if et in ("ring", "rune", "vortex", "nova", "aura",
                      "freeze", "petals", "starfall"):
                x, y = int(self.wx(e["x"], sx)), int(self.wy(e["y"], sy))
                if et == "ring":
                    self._ef_ring(ov, x, y, e["r"], col, a, prog)
                elif et == "rune":
                    self._ef_rune(ov, x, y, e["r"], col, a, prog)
                elif et == "vortex":
                    self._ef_vortex(ov, x, y, e["r"], col, a, prog)
                elif et == "nova":
                    self._ef_nova(ov, x, y, e["r"], col, a, prog)
                elif et == "freeze":
                    self._ef_freeze(ov, x, y, e["r"], col, a, prog)
                elif et == "petals":
                    self._ef_petals(ov, x, y, e["r"], col, a, prog)
                elif et == "starfall":
                    self._ef_starfall(ov, x, y, e["r"], col, a, prog)
                else:
                    self._ef_aura(ov, x, y, e["r"], col, a, prog)
            elif et in ("beam", "trail"):
                self._ef_beam_trail(ov, e, sx, sy, col, a, ratio)
            elif et == "fan":
                self._ef_fan(ov, e, sx, sy, col, a, prog)
            elif et == "slash":
                self._ef_slash(ov, e, sx, sy, col, a, prog)
            elif et == "melee_tex":
                self._ef_melee_tex(ov, e, sx, sy)
            elif et == "leaf":
                self._ef_leaf(ov, e, sx, sy, col, a)

    def _ef_slash(self, ov, e, sx, sy, col, a, prog):
        """新月掌风：沿挥向的双层弧线 + 白热内缘，随进度外扩再收。"""
        x, y = int(self.wx(e["x"], sx)), int(self.wy(e["y"], sy))
        r = max(4, int(e["r"] * (0.82 + 0.30 * prog)))
        half = e["half"]
        a0, a1 = e["ang"] - half, e["ang"] + half
        lw = max(2, self.s(9))
        rect = pygame.Rect(x - r, y - r, r * 2, r * 2)
        pygame.draw.arc(ov, (*col, int(a * 0.30)),
                        rect.inflate(lw * 3, lw * 3), a0, a1, lw * 3)
        pygame.draw.arc(ov, (*col, a), rect, a0, a1, lw)
        r2 = max(3, int(r * 0.86))
        rect2 = pygame.Rect(x - r2, y - r2, r2 * 2, r2 * 2)
        pygame.draw.arc(ov, (255, 255, 255, int(a * 0.55)), rect2,
                        a0 + half * 0.25, a1 - half * 0.25, max(1, lw // 2))

    def _ef_melee_tex(self, ov, e, sx, sy):
        """近战斩击贴图：kind=arc 弧痕扫掠（潮汐 1/2 段，第 2 段镜像反扫）；
        kind=ring 涌浪环扩散（潮汐 3 段）；无 kind 走薄荷旧路径（蛇=旋风环旋转、
        人=X 形斩小角度修正 + 缩放弹跳）。统一 10% 快淡入 / 尾段 45% 淡出。"""
        ratio = max(0.0, min(1.0, e["life"] / e["max_life"]))
        prog = 1.0 - ratio
        kind = e.get("kind", "")
        if kind == "arc":
            if e.get("flip"):
                base = self._melee_fx_surf_flip(e["rel"], e["size"])
            else:
                base = self._melee_fx_surf(e["rel"], e["size"])
            if base is None:
                return
            # 弧痕绕自身扫过 ±55°（镜像段反向），并沿挥向漂一点增强甩动感
            sweep = -55.0 + 110.0 * prog
            rot = math.degrees(e["ang"]) + (-sweep if e.get("flip") else sweep)
            img = self._rot_surf(base, rot)
            if img is None:
                return
            env = min(1.0, prog / 0.10, ratio / 0.45)
            img.set_alpha(int(235 * max(0.0, min(1.0, env))))
            drift = e["size"] * 0.10 * prog
            x = int(self.wx(e["x"] + math.cos(e["ang"]) * drift, sx))
            y = int(self.wy(e["y"] + math.sin(e["ang"]) * drift, sy))
            ov.blit(img, img.get_rect(center=(x, y)))
            return
        if kind == "ring":
            base = self._melee_fx_surf(e["rel"], e["size"])
            if base is None:
                return
            # 涌浪环：ease-out 快速铺开再放缓，中心不漂移（踏地即以自身为圆心）
            scale = 0.55 + 0.60 * (1.0 - (1.0 - prog) ** 2)
            img = self._rotozoom_surf(base, 0.0, scale)
            if img is None:
                return
            env = min(1.0, prog / 0.10, ratio / 0.45)
            img.set_alpha(int(235 * max(0.0, min(1.0, env))))
            x = int(self.wx(e["x"], sx))
            y = int(self.wy(e["y"], sy))
            ov.blit(img, img.get_rect(center=(x, y)))
            return
        base = self._melee_fx_surf(e["rel"], e["size"])
        if base is None:
            return
        if e["form"] == "lamia":
            img = self._rot_surf(base, prog * 110.0)
        else:
            rot = 45.0 + (prog - 0.5) * 18.0
            scale = 0.72 + 0.28 * (1.0 - (1.0 - prog) ** 3)
            img = self._rotozoom_surf(base, rot, scale)
        if img is None:
            return
        env = min(1.0, prog / 0.10, ratio / 0.45)
        img.set_alpha(int(235 * max(0.0, min(1.0, env))))
        drift = self.s(S.MELEE_COMBO_RANGE) * 0.18 * prog
        x = int(self.wx(e["x"] + math.cos(e["ang"]) * drift, sx))
        y = int(self.wy(e["y"] + math.sin(e["ang"]) * drift, sy))
        ov.blit(img, img.get_rect(center=(x, y)))

    def _ef_leaf(self, ov, e, sx, sy, col, a):
        """碎叶：四点多边形模拟风中转动的叶片 + 一道白热叶脉。"""
        x = self.wx(e["x"], sx)
        y = self.wy(e["y"], sy)
        L = e["size"]
        wd = L * 0.42
        ca, sa = math.cos(e["ang"]), math.sin(e["ang"])
        pts = [(int(x + ca * L), int(y + sa * L)),
               (int(x - sa * wd), int(y + ca * wd)),
               (int(x - ca * L), int(y - sa * L)),
               (int(x + sa * wd), int(y - ca * wd))]
        pygame.draw.polygon(ov, (*col, a), pts)
        pygame.draw.line(ov, (255, 255, 255, int(a * 0.4)),
                         (int(x - ca * L * 0.8), int(y - sa * L * 0.8)),
                         (int(x + ca * L * 0.8), int(y + sa * L * 0.8)), 1)

    # ---- 发光基础件 -------------------------------------------------
    def _ef_radial(self, ov, x, y, r, col, alpha):
        """由外向内的径向柔光（同心圆近似渐变），做“光晕底”。"""
        r = int(r)
        if r <= 1 or alpha <= 0:
            return
        steps = 9
        for i in range(steps, 0, -1):
            rr = max(1, int(r * i / steps))
            aa = int(alpha * (steps - i + 1) / steps * 0.46)
            if aa > 0:
                pygame.draw.circle(ov, (*col, aa), (x, y), rr)

    def _ef_glow_ring(self, ov, x, y, r, col, alpha, width):
        """带外发光的圆环：最外柔光晕 + 外柔光 + 中环 + 主环 + 白热内芯。"""
        r = int(r)
        if r < 1 or alpha <= 0:
            return
        width = max(2, int(width))
        pygame.draw.circle(ov, (*col, int(alpha * 0.06)), (x, y), r + width * 3, width * 3)
        pygame.draw.circle(ov, (*col, int(alpha * 0.14)), (x, y), r, width * 4)
        pygame.draw.circle(ov, (*col, int(alpha * 0.30)), (x, y), r, width * 2)
        pygame.draw.circle(ov, (*col, alpha), (x, y), r, width)
        if r - width > 1:
            pygame.draw.circle(ov, (255, 255, 255, int(alpha * 0.5)),
                               (x, y), r - width, max(1, width // 2))

    def _ef_sparkle(self, ov, x, y, r, col, alpha):
        """四角星芒闪光：竖横两道 + 对角两道 + 白热中心，点缀华丽感。"""
        r = max(2, int(r))
        if alpha <= 0:
            return
        lw = max(1, r // 3)
        pygame.draw.line(ov, (*col, alpha), (x - r, y), (x + r, y), lw)
        pygame.draw.line(ov, (*col, alpha), (x, y - r), (x, y + r), lw)
        d = int(r * 0.6)
        pygame.draw.line(ov, (*col, int(alpha * 0.55)), (x - d, y - d), (x + d, y + d), 1)
        pygame.draw.line(ov, (*col, int(alpha * 0.55)), (x - d, y + d), (x + d, y - d), 1)
        pygame.draw.circle(ov, (255, 255, 255, alpha), (x, y), max(1, r // 3))

    # ---- 各技能专属形状 ---------------------------------------------
    def _ef_ring(self, ov, x, y, r, col, a, prog):
        """涌潮：扩散水环 + 中心柔光 + 内圈白涟漪 + 外圈二次波 + 水珠星芒。"""
        rr = max(2, int(r * (0.35 + 0.65 * prog)))
        self._ef_radial(ov, x, y, rr, col, int(a * 0.55))
        rr2 = max(2, int(r * (0.15 + 0.95 * prog)))
        self._ef_glow_ring(ov, x, y, rr2, col, int(a * 0.35), self.s(2))
        self._ef_glow_ring(ov, x, y, rr, col, a, self.s(6))
        self._ef_glow_ring(ov, x, y, int(rr * 0.62), (255, 255, 255),
                           int(a * 0.45), self.s(2))
        for k in range(8):
            ang = k * math.tau / 8 + prog * 1.5
            ex = int(x + math.cos(ang) * rr)
            ey = int(y + math.sin(ang) * rr)
            self._ef_sparkle(ov, ex, ey, self.s(7), (255, 255, 255), int(a * 0.5))

    def _ef_rune(self, ov, x, y, r, col, a, prog):
        """标记：旋转魔法阵——外刻度环 + 主环 + 六道星芒 + 反向六芒星。"""
        rr = max(6, int(r * (0.55 + 0.45 * prog)))
        self._ef_radial(ov, x, y, rr, col, int(a * 0.45))
        spin = prog * math.pi * 1.6
        # 外圈反向旋转刻度环
        outer = int(rr * 1.22)
        self._ef_glow_ring(ov, x, y, outer, col, int(a * 0.4), self.s(2))
        for k in range(16):
            ang = -spin * 0.8 + k * math.tau / 16
            ix = int(x + math.cos(ang) * outer * 0.9)
            iy = int(y + math.sin(ang) * outer * 0.9)
            ox = int(x + math.cos(ang) * outer)
            oy = int(y + math.sin(ang) * outer)
            pygame.draw.line(ov, (*col, int(a * 0.55)), (ix, iy), (ox, oy),
                             max(1, self.s(2)))
        self._ef_glow_ring(ov, x, y, rr, col, a, self.s(4))
        # 六道旋转星芒（顶点白热亮点 + 星芒闪光）
        for k in range(6):
            ang = spin + k * math.tau / 6
            ex = int(x + math.cos(ang) * rr)
            ey = int(y + math.sin(ang) * rr)
            pygame.draw.line(ov, (*col, int(a * 0.65)), (x, y), (ex, ey),
                             max(1, self.s(2)))
            pygame.draw.circle(ov, (255, 255, 255, int(a * 0.9)),
                               (ex, ey), max(2, self.s(4)))
            self._ef_sparkle(ov, ex, ey, self.s(9), col, int(a * 0.6))
        # 反向六芒星（两个交错三角）
        inner = max(4, int(rr * 0.62))
        for off in (0.0, math.pi / 3):
            pts = [(int(x + math.cos(-spin * 1.3 + off + k * math.tau / 3) * inner),
                    int(y + math.sin(-spin * 1.3 + off + k * math.tau / 3) * inner))
                   for k in range(3)]
            pygame.draw.polygon(ov, (*col, int(a * 0.5)), pts, max(2, self.s(2)))

    def _ef_vortex(self, ov, x, y, r, col, a, prog):
        """聚怪：三层内卷螺旋臂 + 收拢环 + 向心光屑 + 明亮塌缩核心。"""
        rr = max(6, int(r * (1.0 - 0.55 * prog)))
        self._ef_radial(ov, x, y, int(r * 0.6), col, int(a * 0.45))
        spin = prog * math.pi * 3.0
        for arm in range(3):
            base = spin + arm * math.tau / 3
            pts = []
            for i in range(22):
                tt = i / 21.0
                ang = base + tt * math.pi * 1.9
                rad = rr * (1.0 - tt * 0.85)
                pts.append((int(x + math.cos(ang) * rad),
                            int(y + math.sin(ang) * rad)))
            pygame.draw.lines(ov, (*col, int(a * 0.3)), False, pts, max(4, self.s(7)))
            pygame.draw.lines(ov, (*col, int(a * 0.9)), False, pts, max(2, self.s(3)))
            pygame.draw.lines(ov, (255, 255, 255, int(a * 0.5)), False, pts,
                              max(1, self.s(1)))
        # 向心飞散的光屑：从外缘沿半径往里冲
        for k in range(10):
            ang = -spin * 1.4 + k * math.tau / 10
            rad = rr * (1.15 - 0.9 * prog)
            px = int(x + math.cos(ang) * rad)
            py = int(y + math.sin(ang) * rad)
            self._ef_sparkle(ov, px, py, self.s(6), col, int(a * 0.55))
        self._ef_glow_ring(ov, x, y, rr, col, int(a * 0.6), self.s(3))
        # 塌缩核心（越到后期越亮越小）
        core = max(2, int(r * 0.22 * (1.0 - prog * 0.6)))
        self._ef_radial(ov, x, y, core * 2, (255, 255, 255), int(a * 0.5))
        pygame.draw.circle(ov, (255, 255, 255, int(a * 0.85)), (x, y), core)

    def _ef_nova(self, ov, x, y, r, col, a, prog):
        """引爆：核心白闪 + 三层震波 + 十六道放射尖刺 + 外飞余烬。"""
        fr = max(2, int(r * 0.5 * (1.0 - prog)))
        self._ef_radial(ov, x, y, fr, (255, 255, 255), int(a * 0.85))
        self._ef_radial(ov, x, y, fr * 2, col, int(a * 0.5))
        rr = max(2, int(r * (0.25 + 0.75 * prog)))
        self._ef_glow_ring(ov, x, y, rr, col, a, self.s(7))
        self._ef_glow_ring(ov, x, y, int(rr * 0.7), (255, 255, 255),
                           int(a * 0.55), self.s(2))
        rr2 = max(2, int(r * (0.1 + 1.05 * prog)))
        self._ef_glow_ring(ov, x, y, rr2, col, int(a * 0.3), self.s(2))
        # 十六道放射尖刺（长短交替，末端亮点点缀）
        for k in range(16):
            ang = k * math.tau / 16 + prog * 0.7
            long = rr * (1.25 if k % 2 == 0 else 0.85)
            ex = int(x + math.cos(ang) * long)
            ey = int(y + math.sin(ang) * long)
            pygame.draw.line(ov, (*col, int(a * 0.75)), (x, y), (ex, ey),
                             max(1, self.s(3)))
            if k % 2 == 0:
                self._ef_sparkle(ov, ex, ey, self.s(8), (255, 255, 255),
                                 int(a * 0.5))
        # 外飞余烬：随进度向外扩散的火屑
        for k in range(12):
            ang = k * math.tau / 12 + 0.3
            rad = r * (0.4 + 0.9 * prog)
            px = int(x + math.cos(ang) * rad)
            py = int(y + math.sin(ang) * rad)
            pygame.draw.circle(ov, (*col, int(a * 0.6)), (px, py),
                               max(1, self.s(3)))

    def _ef_aura(self, ov, x, y, r, col, a, prog):
        """鼓舞：地面脉动光环 + 一圈向上飘的光柱 + 升腾的星屑光点。"""
        self._ef_radial(ov, x, y, int(r * 0.9), col, int(a * 0.35))
        self._ef_glow_ring(ov, x, y, int(r * 0.72), col, int(a * 0.75), self.s(4))
        self._ef_glow_ring(ov, x, y, int(r * 0.72 * (0.6 + 0.4 * prog)),
                           (255, 255, 255), int(a * 0.35), self.s(2))
        rise = prog * self.s(150)
        for k in range(12):
            ang = k * math.tau / 12 + prog * 1.2
            bx = int(x + math.cos(ang) * r * 0.72)
            by = int(y + math.sin(ang) * r * 0.36)
            hgt = self.s(84) * (0.65 + 0.35 * abs(math.sin(k * 1.7)))
            base = (bx, int(by - rise))
            top = (bx, int(by - rise - hgt))
            pygame.draw.line(ov, (*col, int(a * 0.26)), base, top, max(4, self.s(9)))
            pygame.draw.line(ov, (*col, int(a * 0.85)), base, top, max(2, self.s(4)))
            pygame.draw.line(ov, (255, 255, 255, int(a * 0.55)), base, top,
                             max(1, self.s(2)))
            self._ef_sparkle(ov, top[0], top[1], self.s(7), col, int(a * 0.5))
        # 升腾光点
        for k in range(8):
            ang = k * math.tau / 8 + prog * 2.0
            rad = r * 0.5
            px = int(x + math.cos(ang) * rad)
            py = int(y + math.sin(ang) * rad * 0.5 - rise * 1.2 - k * self.s(6))
            pygame.draw.circle(ov, (255, 255, 255, int(a * 0.5)), (px, py),
                               max(1, self.s(2)))

    def _ef_freeze(self, ov, x, y, r, col, a, prog):
        """冻结：冰晶六芒 + 霜环 + 中心白闪，表达定身瞬间。"""
        rr = max(4, int(r * (0.72 + 0.28 * (1.0 - prog))))
        self._ef_radial(ov, x, y, rr, col, int(a * 0.4))
        self._ef_glow_ring(ov, x, y, rr, col, int(a * 0.8), self.s(3))
        for k in range(6):
            ang = k * math.tau / 6 + prog * 0.4
            ex = int(x + math.cos(ang) * rr)
            ey = int(y + math.sin(ang) * rr)
            pygame.draw.line(ov, (255, 255, 255, int(a * 0.85)), (x, y), (ex, ey),
                             max(1, self.s(2)))
            self._ef_sparkle(ov, ex, ey, self.s(6), col, int(a * 0.6))
        pygame.draw.circle(ov, (255, 255, 255, int(a * 0.6)), (x, y),
                           max(2, int(rr * 0.28)))

    def _ef_petals(self, ov, x, y, r, col, a, prog):
        """樱绽：旋转飞散的花瓣（椭圆）+ 粉色柔光。"""
        self._ef_radial(ov, x, y, int(r * 0.85), col, int(a * 0.4))
        spin = prog * math.pi * 2.0
        for k in range(10):
            ang = spin + k * math.tau / 10
            rad = r * (0.3 + 0.85 * prog)
            px = int(x + math.cos(ang) * rad)
            py = int(y + math.sin(ang) * rad * 0.7)
            pr = max(2, int(self.s(7) * (1.0 - prog * 0.4)))
            pygame.draw.ellipse(ov, (*col, int(a * 0.85)),
                                (px - pr, py - pr // 2, pr * 2, max(1, pr)))
            pygame.draw.ellipse(ov, (255, 255, 255, int(a * 0.4)),
                                (px - pr // 2, py - max(1, pr // 4), pr, max(1, pr // 2)))
        self._ef_glow_ring(ov, x, y, int(r * (0.4 + 0.6 * prog)), col,
                           int(a * 0.35), self.s(2))

    def _ef_starfall(self, ov, x, y, r, col, a, prog):
        """星陨：数道自上方坠落的星辉拖尾 + 落点光环。"""
        for k in range(6):
            off = (k - 2.5) * r * 0.42
            t = min(1.0, prog * 1.4 + k * 0.08)
            sx0 = int(x + off)
            sy0 = int(y - r * 1.7 + t * r * 1.7)
            tx = int(x + off * 0.35)
            ty = int(y)
            pygame.draw.line(ov, (*col, int(a * 0.22)), (sx0, sy0), (tx, ty),
                             max(3, self.s(6)))
            pygame.draw.line(ov, (255, 255, 255, int(a * 0.7)), (sx0, sy0), (tx, ty),
                             max(1, self.s(2)))
            self._ef_sparkle(ov, sx0, sy0, self.s(7), col, int(a * 0.6))
        self._ef_glow_ring(ov, x, y, int(r * (0.3 + 0.7 * prog)), col,
                           int(a * 0.5), self.s(3))

    def _ef_beam_trail(self, ov, e, sx, sy, col, a, ratio):
        """月光束 / 突进斩拖影：多层描边 + 白热芯 + 流动能量脉冲 + 端点星芒。"""
        x1, y1 = int(self.wx(e["x1"], sx)), int(self.wy(e["y1"], sy))
        x2, y2 = int(self.wx(e["x2"], sx)), int(self.wy(e["y2"], sy))
        taper = 1.0 if e["type"] == "beam" else ratio
        w = max(2, int(e.get("width", self.s(10)) * taper))
        pygame.draw.line(ov, (*col, int(a * 0.10)), (x1, y1), (x2, y2), w * 6)
        pygame.draw.line(ov, (*col, int(a * 0.18)), (x1, y1), (x2, y2), w * 4)
        pygame.draw.line(ov, (*col, int(a * 0.34)), (x1, y1), (x2, y2), w * 2)
        pygame.draw.line(ov, (*col, a), (x1, y1), (x2, y2), w)
        pygame.draw.line(ov, (255, 255, 255, int(a * 0.9)), (x1, y1), (x2, y2),
                         max(1, w // 3))
        # 沿线流动的能量脉冲（两道亮点来回跑）
        for ph in (0.0, 0.5):
            t = (1.0 - ratio + ph) % 1.0
            px = int(x1 + (x2 - x1) * t)
            py = int(y1 + (y2 - y1) * t)
            self._ef_sparkle(ov, px, py, w + self.s(6), (255, 255, 255),
                             int(a * 0.6))
        for ex, ey in ((x1, y1), (x2, y2)):
            pygame.draw.circle(ov, (*col, int(a * 0.4)), (ex, ey), max(3, w))
            pygame.draw.circle(ov, (255, 255, 255, int(a * 0.5)), (ex, ey),
                               max(1, w // 2))

    def _ef_fan(self, ov, e, sx, sy, col, a, prog):
        """火焰扇：外焰柔光 + 主体扇形 + 内层白热 + 火舌尖 + 飞散火星。"""
        x, y = int(self.wx(e["x"], sx)), int(self.wy(e["y"], sy))
        rng = e["range"] * (0.55 + 0.45 * prog)
        a0, a1 = e["ang"] - e["half"], e["ang"] + e["half"]
        steps = 24

        def arc(scale):
            pts = [(x, y)]
            for k in range(steps + 1):
                aa = a0 + (a1 - a0) * k / steps
                pts.append((int(x + math.cos(aa) * rng * scale),
                            int(y + math.sin(aa) * rng * scale)))
            return pts

        self._ef_radial(ov, x, y, int(rng * 0.5), col, int(a * 0.3))
        pygame.draw.polygon(ov, (*col, int(a * 0.14)), arc(1.22))
        pygame.draw.polygon(ov, (*col, int(a * 0.20)), arc(1.1))
        pygame.draw.polygon(ov, (*col, int(a * 0.45)), arc(1.0))
        pygame.draw.polygon(ov, (*col, a), arc(1.0), max(2, self.s(3)))
        pygame.draw.polygon(ov, (255, 224, 170, int(a * 0.4)), arc(0.62))
        pygame.draw.polygon(ov, (255, 255, 255, int(a * 0.3)), arc(0.34))
        # 火舌：沿外缘起伏的尖刺
        for k in range(steps + 1):
            aa = a0 + (a1 - a0) * k / steps
            flick = 1.06 + 0.1 * math.sin(k * 2.3 + prog * 12.0)
            ex = int(x + math.cos(aa) * rng * flick)
            ey = int(y + math.sin(aa) * rng * flick)
            ix = int(x + math.cos(aa) * rng * 0.96)
            iy = int(y + math.sin(aa) * rng * 0.96)
            pygame.draw.line(ov, (*col, int(a * 0.6)), (ix, iy), (ex, ey),
                             max(1, self.s(3)))
        # 飞散火星
        for k in range(9):
            aa = a0 + (a1 - a0) * (k + 0.5) / 9
            rad = rng * (0.5 + 0.6 * prog)
            px = int(x + math.cos(aa) * rad)
            py = int(y + math.sin(aa) * rad)
            self._ef_sparkle(ov, px, py, self.s(6), (255, 200, 120), int(a * 0.5))

    def _draw_drops(self, screen, sx, sy):
        for d in self.drops:
            size = max(8, self.s(d.size))
            img = self.assets.get_scaled(d.asset, height=size)
            x = self.wx(d.draw_pos[0], sx)
            y = self.wy(d.draw_pos[1], sy)
            gr = size // 2 + self.s(10)
            glow = self._glow_surf(gr, d.color, 62)
            screen.blit(glow, glow.get_rect(center=(int(x), int(y))))
            screen.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))
            # 品质档标记：高档道具下方点几颗小星
            if d.tier > 1:
                for i in range(d.tier - 1):
                    px = x - (d.tier - 2) * self.s(5) + i * self.s(10)
                    pygame.draw.circle(screen, COLOR_GOLD,
                                       (int(px), int(y + size / 2 + self.s(6))),
                                       max(1, self.s(2)))

    def _mark_petal_surf(self, h):
        """单片花瓣指示底图：粉色花瓣（椭圆）+ 白芯高光，按高度档缓存。"""
        h = max(6, int(h))
        key = ("markpetal", h)
        if key in self._surf_cache:
            return self._surf_cache[key]
        w = max(4, int(h * 0.72))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (255, 170, 200, 235), s.get_rect())
        pygame.draw.ellipse(s, (255, 235, 245, 200),
                            pygame.Rect(w // 4, h // 4, w // 2, h // 2))
        self._surf_cache[key] = s
        return s

    def _draw_mark_petals(self, screen, x, y, size, stacks):
        """花瓣标记层数指示：每层一片花瓣贴在目标身周，随时间轻摆。

        叠几层贴几片＝层数可视化；旋转角度量化查表，不逐帧重采样。
        """
        base = self._mark_petal_surf(self.s(14))
        rr = size * 0.44
        for k in range(min(stacks, 6)):
            a = -math.pi / 2 + (k - (stacks - 1) / 2.0) * 0.85 \
                + 0.10 * math.sin(self.elapsed * 2.6 + k * 1.7)
            px = x + math.cos(a) * rr
            py = y + math.sin(a) * rr * 0.85
            img = self._rot_surf(base, math.degrees(a) + 90.0)
            screen.blit(img, img.get_rect(center=(int(px), int(py))))

    def _ember_pip_surf(self, h):
        """单颗余烬火星指示底图：金芯橙焰小火苗，按高度档缓存。"""
        h = max(6, int(h))
        key = ("emberpip", h)
        if key in self._surf_cache:
            return self._surf_cache[key]
        w = max(4, int(h * 0.7))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (255, 122, 46, 235), s.get_rect())
        pygame.draw.ellipse(s, (255, 201, 60, 220),
                            pygame.Rect(w // 5, h // 5, w - w * 2 // 5, h // 2))
        pygame.draw.ellipse(s, (255, 217, 138, 200),
                            pygame.Rect(w // 3, h // 3, w // 3, h // 3))
        self._surf_cache[key] = s
        return s

    def _draw_ember_pips(self, screen, x, y, size, stacks):
        """余烬层数指示：每层一颗火星横排贴在目标下方，随时间轻闪
        （花瓣标记在上方、余烬在下方，两套叠层指示互不打架）。"""
        pip = self._ember_pip_surf(self.s(10))
        n = max(1, min(int(stacks), S.FLARE_EMBER_MAX))
        gap = self.s(9)
        y0 = y + size * 0.52
        for k in range(n):
            px = x + (k - (n - 1) / 2.0) * gap
            flick = 0.75 + 0.25 * math.sin(self.elapsed * 7.0 + k * 1.9)
            p = pip.copy()
            p.set_alpha(int(255 * flick))
            screen.blit(p, p.get_rect(center=(int(px), int(y0))))

    def _draw_mobs(self, screen, sx, sy):
        for m in self.mobs:
            size = max(12, int(m.radius * 2.2))
            sprite = getattr(m, "sprite", "") or "characters/mob_shadow.png"
            img = self.assets.get_scaled(sprite, height=size)
            x = self.wx(m.pos[0], sx)
            y = self.wy(m.pos[1], sy)
            bob = math.sin(m.t) * self.s(3)
            rect = img.get_rect(center=(int(x), int(y + bob)))
            sh_h = max(3, size // 3)
            sh = self._cached_surf(("msh", size, sh_h), (size, sh_h),
                                   lambda s: pygame.draw.ellipse(
                                       s, (0, 0, 0, 95), s.get_rect()))
            screen.blit(sh, sh.get_rect(center=(rect.centerx, rect.bottom - self.s(4))))
            if getattr(m, "is_elite", False):
                gd = size + self.s(24)
                gr = size // 2 + self.s(6)
                glow = self._cached_surf(
                    ("eglow", size), (gd, gd),
                    lambda s: pygame.draw.circle(s, (255, 90, 120, 70),
                                                 (gd // 2, gd // 2), gr))
                screen.blit(glow, glow.get_rect(center=rect.center))
            screen.blit(img, rect)
            # 花瓣标记指示：每层贴一片花瓣（贴身上方，随时间轻摆）
            if m.mark_t > 0 and m.mark_stacks > 0:
                self._draw_mark_petals(screen, x, y + bob, size, m.mark_stacks)
            # 余烬层指示：每层一颗火星横排贴在下方（绯焰灼烧引爆闭环）
            if m.ember_stacks > 0:
                self._draw_ember_pips(screen, x, y + bob, size, m.ember_stacks)
            if m.hit_flash > 0:
                # 白闪=整体调透明度：缓存副本只 set_alpha，不每帧 copy+fill
                fk = ("mflash", sprite, size)
                fl = self._surf_cache.get(fk)
                if fl is None:
                    fl = img.copy()
                    self._surf_cache[fk] = fl
                fl.set_alpha(int(190 * (m.hit_flash / 0.18)))
                screen.blit(fl, rect)
            if getattr(m, "is_elite", False):
                # 精英：常驻名字 + 加宽血条
                bw, bh = max(40, int(size * 1.1)), self.s(7)
                bx = rect.centerx - bw / 2
                by = rect.top - self.s(16)
                pygame.draw.rect(screen, (30, 20, 40), (bx, by, bw, bh), border_radius=2)
                pygame.draw.rect(screen, (255, 90, 120),
                                 (bx, by, bw * max(0.0, m.hp / m.hp_max), bh),
                                 border_radius=2)
                pygame.draw.rect(screen, (255, 200, 210), (bx, by, bw, bh), 1,
                                 border_radius=2)
                nm = self._cached_text(self.f_tiny, m.elite_name or "精英",
                                       (255, 150, 170))
                screen.blit(nm, nm.get_rect(midbottom=(rect.centerx, by - self.s(1))))
            elif m.hp < m.hp_max:
                bw, bh = max(16, int(size * 0.9)), self.s(5)
                bx = rect.centerx - bw / 2
                by = rect.top - self.s(10)
                pygame.draw.rect(screen, (30, 20, 40), (bx, by, bw, bh), border_radius=2)
                pygame.draw.rect(screen, COLOR_DANGER,
                                 (bx, by, bw * m.hp / m.hp_max, bh), border_radius=2)

    def _draw_bullets(self, screen, sx, sy):
        for b in self.bullets:
            x = self.wx(b.pos[0], sx)
            y = self.wy(b.pos[1], sy)
            r = max(2, int(b.radius))
            glow = self._glow_surf(r * 2, b.color, 70)
            screen.blit(glow, glow.get_rect(center=(int(x), int(y))))
            img = self._skill_fx_surf(getattr(b, "fx", None), r * 4)
            if img is None and getattr(b, "tex_rel", None):
                # 普攻贴图（樱落花瓣）：缩放变体，尺寸档由段别 tex_mult 决定
                img = self._melee_fx_surf(b.tex_rel, r * getattr(b, "tex_mult", 4.0))
            if img is None:
                img = self._bullet_sprite(b.element, r)
            if img is not None:
                # 技能/元素弹丸贴图：朝速度方向旋转（贴图缺失时回退纯色圆点）
                # 弧旋/自旋弹方向逐帧变，用弹体累计的 rot；旋转结果查表缓存
                ang = b.rot if getattr(b, "rot", None) is not None \
                    else math.degrees(math.atan2(b.vel[1], b.vel[0]))
                rot = self._rot_surf(img, ang)
                screen.blit(rot, rot.get_rect(center=(int(x), int(y))))
            else:
                pygame.draw.circle(screen, b.color, (int(x), int(y)), r)
                pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), max(1, r // 2))

    def _bullet_sprite(self, element, r):
        """按元素取缓存的弹丸贴图（缩放到 ~4r 高）；无元素/贴图缺失返回 None。"""
        name = _EL_BULLET.get(element or "")
        if not name:
            return None
        size = max(8, int(r * 4))
        key = ("bullet", name, size)
        if key in self._surf_cache:
            return self._surf_cache[key]
        rel = f"effects/bullet_{name}.png"
        full = os.path.join(S.ASSETS_DIR, rel.replace("/", os.sep))
        img = None
        if os.path.exists(full):
            try:
                img = self.assets.get_scaled(rel, height=size)
            except Exception:
                img = None
        self._surf_cache[key] = img
        return img

    def _skill_fx_surf(self, sid, height, form=None):
        """按技能 id 取缓存的专属贴图（缩放到 height 高）。

        给了 form 就优先取形态专属图 effects/skills/<sid>_<form>.png，
        缺图自动回退通用的 <sid>.png；不带 form 即旧行为（HUD 图标走这条）。
        无 sid / 贴图缺失返回 None，调用方据此回退到程序化 VFX（其他角色零影响）。
        """
        if not sid:
            return None
        size = max(16, int(height))
        key = ("skillfx", sid, size, form)
        if key in self._surf_cache:
            return self._surf_cache[key]
        rels = [f"effects/skills/{sid}_{form}.png"] if form else []
        rels.append(f"effects/skills/{sid}.png")
        img = None
        for rel in rels:
            full = os.path.join(S.ASSETS_DIR, rel.replace("/", os.sep))
            if not os.path.exists(full):
                continue
            try:
                img = self.assets.get_scaled(rel, height=size)
            except Exception:
                img = None
            if img is not None:
                break
        self._surf_cache[key] = img
        return img

    def _active_form(self):
        """当前出战成员的形态标记 'human' / 'lamia'（与近战贴图分支同一判据）。"""
        try:
            am = self.party[self.active_idx]
        except Exception:
            return "lamia"
        return "human" if (self.char_human and am.get("form") == "human") else "lamia"

    def _skill_icon_surf(self, sid, box):
        """把技能专属贴图（effects/skills/<sid>.png）等比缩进 box 见方作为图标；
        缺图返回 None，调用方回退程序化图标（其他角色零影响）。"""
        if not sid:
            return None
        box = max(8, int(box))
        key = ("skillicon", sid, box)
        if key in self._surf_cache:
            return self._surf_cache[key]
        base = self._skill_fx_surf(sid, self.s(256))
        if base is None:
            # 绯焰等双形态角色只有 <sid>_lamia/_human 成品图：HUD 图标回退蛇形态版
            base = self._skill_fx_surf(sid, self.s(256), "lamia")
        img = None
        if base is not None:
            w, h = base.get_size()
            k = min(box / w, box / h)
            img = pygame.transform.smoothscale(
                base, (max(1, int(w * k)), max(1, int(h * k))))
        self._surf_cache[key] = img
        return img

    def _spawn_fx_sprite(self, sid, x, y, size, life=0.5, spin=0.0, expand=1.6):
        """一次性技能贴图特效：从 size 扩张到 size*expand 并淡出（缺图则不生成）。

        出场瞬间锁定当前形态的贴图：人形态优先 <sid>_human.png、蛇形态 <sid>_lamia.png，
        缺图回退通用 <sid>.png——没配双形态特效的角色（薄荷等）行为完全不变。
        """
        form = self._active_form()
        if self._skill_fx_surf(sid, max(16, int(size)), form) is None:
            return
        self.fx_sprites.append({
            "sid": sid, "x": x, "y": y, "size": float(size),
            "life": life, "max_life": max(1e-6, life),
            "spin": spin, "expand": expand, "ang": 0.0,
            "form": form,
        })

    def _update_fx_sprites(self, dt):
        if not self.fx_sprites:
            return
        for f in self.fx_sprites:
            f["life"] -= dt
            f["ang"] += f["spin"] * dt
        self.fx_sprites = [f for f in self.fx_sprites if f["life"] > 0]

    def _draw_fx_sprites(self, screen, sx, sy):
        for f in self.fx_sprites:
            base = self._skill_fx_surf(f["sid"], f["size"], f.get("form"))
            if base is None:
                continue
            ratio = max(0.0, min(1.0, f["life"] / f["max_life"]))
            scale = 1.0 + (f["expand"] - 1.0) * (1.0 - ratio)
            img = self._rotozoom_surf(base, math.degrees(f["ang"]), scale)
            img.set_alpha(int(255 * ratio))
            x = int(self.wx(f["x"], sx))
            y = int(self.wy(f["y"], sy))
            screen.blit(img, img.get_rect(center=(x, y)))

    def _draw_snake(self, screen, sx, sy):
        sn = self.snake
        # 人形态彩蛋：全身站立像代替「上半身 + 蛇尾拖尾」，纯外观无数值差异
        am = self.party[self.active_idx]
        human = bool(self.char_human) and am["form"] == "human"
        # 鼓舞增益：脚下持续光环（在角色下方，随增益存在而脉动）
        if self.rally_t > 0:
            cx = int(self.wx(sn.pos[0], sx))
            cy = int(self.wy(sn.pos[1], sy)) + self.s(20)
            pulse = 0.78 + 0.22 * math.sin(self.elapsed * 8.0)
            rr = int(self.s(74) * pulse)
            gc = rr * 3 // 2
            col = self.rally_color
            lw1, lw2 = max(2, self.s(3)), max(1, self.s(2))
            glow = self._cached_surf(
                ("rglow", rr, col, lw1, lw2), (rr * 3, rr * 3),
                lambda s: (pygame.draw.circle(s, (*col, 34), (gc, gc), rr),
                           pygame.draw.circle(s, (*col, 95), (gc, gc), rr, lw1),
                           pygame.draw.circle(s, (255, 255, 255, 70), (gc, gc),
                                              int(rr * 0.58), lw2)))
            screen.blit(glow, (cx - gc, cy - gc))

        base_x = self.wx(sn.pos[0], sx)
        base_y = self.wy(sn.pos[1], sy)

        # 影子
        sh_w, sh_h = self.s(72), self.s(22)
        sh = self._cached_surf(("ssh", sh_w, sh_h), (sh_w, sh_h),
                               lambda s: pygame.draw.ellipse(
                                   s, (0, 0, 0, 115), s.get_rect()))
        screen.blit(sh, sh.get_rect(center=(int(base_x), int(base_y + self.s(24)))))

        # 全身立绘：蛇形态用盘尾立绘、人形态用站立像，脚底/盘尾锚定到 base_y
        sn.bob_t += 0.045
        bob = math.sin(sn.bob_t) * self.s(3)
        alpha = 255
        if sn.invincible > 0 and int(sn.invincible * 14) % 2 == 0:
            alpha = 105
        # 受击动画：沿反方向小幅后座 + 立绘红 tint
        recoil_x = recoil_y = 0.0
        hurt = sn.hurt_t > 0
        if hurt:
            k = sn.hurt_t / 0.35
            recoil_x = -sn.aim_dir[0] * self.s(10) * k
            recoil_y = -sn.aim_dir[1] * self.s(10) * k
        body_img = self.char_human if human else (self.char_full or self.char_head)
        fig_h = int(self.CELL * (4.0 if human else 3.5))
        flip = sn.aim_dir[0] < 0
        base = self._fig_surf(body_img, fig_h, flip)
        if hurt:
            # 受击红 tint：缓存已染红副本，只按帧调透明度，不每帧 copy+fill
            tk = ("figtint", body_img, fig_h, flip)
            fig = self._surf_cache.get(tk)
            if fig is None:
                fig = base.copy()
                fig.fill((255, 90, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
                self._surf_cache[tk] = fig
            fig.set_alpha(alpha)
        elif alpha < 255:
            # 无敌闪烁：缓存副本调透明度，避免污染共享的 base
            ak = ("figalpha", body_img, fig_h, flip)
            fig = self._surf_cache.get(ak)
            if fig is None:
                fig = base.copy()
                self._surf_cache[ak] = fig
            fig.set_alpha(alpha)
        else:
            fig = base
        fx = base_x - fig.get_width() / 2 + recoil_x
        fy = base_y + self.s(24) - fig.get_height() + bob + recoil_y
        # 技能护盾泡泡（shield_t>0，半透明环，不闪烁；与受击无敌帧区分）
        if sn.shield_t > 0:
            pulse = 0.85 + 0.15 * math.sin(self.elapsed * 9.0)
            rr = int(self.s(66) * pulse)
            lw = max(2, self.s(3))
            bub = self._cached_surf(
                ("bub", rr, lw), (rr * 2, rr * 2),
                lambda s: (pygame.draw.circle(s, (160, 210, 255, 38), (rr, rr), rr),
                           pygame.draw.circle(s, (200, 230, 255, 150), (rr, rr), rr, lw)))
            bcx = int(base_x + recoil_x)
            bcy = int(fy + fig.get_height() * 0.55 + bob)
            screen.blit(bub, (bcx - rr, bcy - rr))
        # 释放动作：idle 立绘与姿势立绘交叉淡入淡出（包络见 _cast_pose_alpha）。
        # 两张都锚定脚底同一点，淡入淡出用 smoothstep，衔接无跳变。
        pa = self._cast_pose_alpha()
        pose_rel = (self.char_cast_poses.get("human" if human else "lamia", {})
                    .get(self.cast_pose["key"]) if pa > 0.0 else None)
        if pose_rel:
            if fig is base:
                # idle 立绘交叉期要逐帧调透明度，用缓存副本，不污染共享 base
                fig = self._surf_cache.setdefault(
                    ("figfade", body_img, fig_h, flip), base.copy())
            fig.set_alpha(max(0, int(alpha * (1.0 - pa))))
            screen.blit(fig, (fx, fy))
            pfig = self._fig_surf(pose_rel, int(fig_h * CAST_POSE_H_MULT), flip)
            pfig.set_alpha(int(255 * pa))   # 该缓存面只在此消费，逐帧直设安全
            screen.blit(pfig, (base_x - pfig.get_width() / 2 + recoil_x,
                               base_y + self.s(24) - pfig.get_height() + bob))
        else:
            aa = self._atk_pose_alpha()
            arel, aflip = self._atk_pose_surf(human, flip) if aa > 0.0 \
                else (None, flip)
            if arel:
                if fig is base:
                    fig = self._surf_cache.setdefault(
                        ("figfade", body_img, fig_h, flip), base.copy())
                fig.set_alpha(max(0, int(alpha * (1.0 - aa))))
                screen.blit(fig, (fx, fy))
                pfig = self._fig_surf(arel, int(fig_h * CAST_POSE_H_MULT), aflip)
                pfig.set_alpha(int(255 * aa))
                screen.blit(pfig, (base_x - pfig.get_width() / 2 + recoil_x,
                                   base_y + self.s(24) - pfig.get_height() + bob))
            else:
                screen.blit(fig, (fx, fy))
        # 受击火花：立绘四周几道放射短线（纯绘制，不产生粒子）
        if hurt:
            k = sn.hurt_t / 0.35
            sr = int(self.s(50))
            cx = int(base_x + recoil_x)
            cy = int(fy + fig.get_height() * 0.36 + bob)
            spark = pygame.Surface((sr * 2, sr * 2), pygame.SRCALPHA)
            a = int(210 * k)
            for i in range(6):
                ang = i * math.tau / 6 + self.elapsed * 2.0
                x0 = sr + math.cos(ang) * sr * 0.48
                y0 = sr + math.sin(ang) * sr * 0.48
                x1 = sr + math.cos(ang) * sr * 0.95
                y1 = sr + math.sin(ang) * sr * 0.95
                pygame.draw.line(spark, (255, 140, 160, a), (x0, y0), (x1, y1),
                                 max(2, self.s(3)))
            screen.blit(spark, (cx - sr, cy - sr))

    def _draw_projectiles(self, screen, sx, sy):
        for p in self.projectiles:
            x = self.wx(p.pos[0], sx)
            y = self.wy(p.pos[1], sy)
            r = max(2, int(p.radius))
            glow = self._glow_surf(r * 2, p.color, 70)
            screen.blit(glow, glow.get_rect(center=(int(x), int(y))))
            pygame.draw.circle(screen, p.color, (int(x), int(y)), r)
            pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), max(1, r // 2))

    def _draw_particles(self, screen, sx, sy):
        # 直接画到 screen：粒子自带 alpha，pygame.draw.circle 在不透明面上即按
        # alpha 混合；省掉复用画布的每帧全屏 clear + 全屏 blit（怪潮时掉帧主因）。
        if not self.particles:
            return
        for p in self.particles:
            a = max(0, int(255 * (p["life"] / p["max_life"])))
            r = p["r"]
            pygame.draw.circle(screen, (*p["color"], a),
                               (int(self.wx(p["x"], sx)), int(self.wy(p["y"], sy))), r)

    def _outlined_text(self, text, font, color, outline=(14, 12, 20)):
        """带深色描边的文字 Surface（结果缓存进 _text_cache）。

        场上飘字（升级 / 拾取 / 选完卡后的「攻击强化」这类效果说明）用的都是
        高亮色，直接画在樱花校园、霓虹夜这种明亮背景上会亮到糊成一片。
        统一垫一圈深色描边后，任何背景、任何文字颜色都能保持可读。
        描边要渲染 9 次，所以必须缓存——飘字同屏可能十几条，逐帧重画会掉帧。
        用独立的 _otxt_cache：「+123 EXP」这类带数字的飘字会不断产生新 key，
        混在 _text_cache 里会把悬停介绍面板挤出去，造成面板反复重建反而卡。
        """
        key = ("otxt", text, font.get_height(), tuple(color))
        hit = self._otxt_cache.get(key)
        if hit is not None:
            return hit
        if len(self._otxt_cache) > 300:
            self._otxt_cache.clear()
        o = max(1, int(self.s(2)))
        base = font.render(text, True, color)
        dark = font.render(text, True, outline)
        cv = pygame.Surface((base.get_width() + o * 2, base.get_height() + o * 2),
                            pygame.SRCALPHA)
        for dx in (-o, 0, o):
            for dy in (-o, 0, o):
                if dx or dy:
                    cv.blit(dark, (o + dx, o + dy))
        cv.blit(base, (o, o))
        self._otxt_cache[key] = cv
        return cv

    def _draw_floaters(self, screen, sx, sy):
        for f in self.floaters:
            a = max(0, min(255, int(255 * (f["life"] / 0.9))))
            font = self.assets.get_font(f["size"], bold=True)
            t = self._outlined_text(f["text"], font, f["color"])
            t.set_alpha(a)          # 缓存面共享，blit 前按本条飘字的寿命重设淡出
            screen.blit(t, t.get_rect(center=(int(self.wx(f["x"], sx)),
                                              int(self.wy(f["y"], sy)))))

    def _draw_boss_telegraph(self, screen, sx, sy):
        if self.boss is None:
            return
        for tg in self.boss.telegraphs:
            prog = max(0.0, min(1.0, tg.get("progress", 0.0)))
            a = int(70 + 150 * prog)
            if tg["type"] == "charge":
                x0 = self.wx(tg["from"][0], sx)
                y0 = self.wy(tg["from"][1], sy)
                x1 = self.wx(tg["to"][0], sx)
                y1 = self.wy(tg["to"][1], sy)
                w = max(2, int(tg["width_px"]))
                pygame.draw.line(screen, (255, 90, 90, 255), (x0, y0), (x1, y1), w)
                pygame.draw.line(screen, (255, 220, 120, a), (x0, y0), (x1, y1),
                                 max(1, w // 3))
            elif tg["type"] == "slam":
                cx = self.wx(tg["pos"][0], sx)
                cy = self.wy(tg["pos"][1], sy)
                r = max(2, int(tg["radius_px"] * (0.5 + 0.5 * prog)))
                ring = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(ring, (255, 120, 80, a), (r + 2, r + 2), r, 3)
                pygame.draw.circle(ring, (255, 200, 120, int(a * 0.25)), (r + 2, r + 2), r)
                screen.blit(ring, ring.get_rect(center=(int(cx), int(cy))))

    def _draw_boss(self, screen, sx, sy):
        b = self.boss
        if b is None:
            return
        bx = self.wx(b.draw_pos[0], sx)
        by = self.wy(b.draw_pos[1], sy)
        r = max(6, int(b.radius_px))
        sh = pygame.Surface((r * 2, max(4, int(r / 1.6)) + 2), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 100), sh.get_rect())
        screen.blit(sh, sh.get_rect(center=(int(bx), int(by + r * 0.85))))

        if b.sprite:
            img = self.assets.get_scaled(b.sprite, height=r * 2)
            rect = img.get_rect(center=(int(bx), int(by)))
            screen.blit(img, rect)
            if b.hit_flash > 0:
                fl = img.copy()
                fl.fill((255, 255, 255, int(190 * (b.hit_flash / 0.16))),
                        special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(fl, rect)
            if b.mark_t > 0 and b.mark_stacks > 0:
                self._draw_mark_petals(screen, bx, by, r * 2, b.mark_stacks)
            if b.ember_stacks > 0:
                self._draw_ember_pips(screen, bx, by, r * 2, b.ember_stacks)
            return

        tint = b.tint
        dark = tuple(max(0, int(c * 0.55)) for c in tint)
        light = tuple(min(255, int(c + 60)) for c in tint)
        spike = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        sc = r + 4
        n_sp = 10
        for k in range(n_sp):
            ang = k * math.tau / n_sp + b.t * 0.15
            tip = (sc + math.cos(ang) * (r + 4), sc + math.sin(ang) * (r + 4))
            b1 = (sc + math.cos(ang + 0.28) * r * 0.85,
                  sc + math.sin(ang + 0.28) * r * 0.85)
            b2 = (sc + math.cos(ang - 0.28) * r * 0.85,
                  sc + math.sin(ang - 0.28) * r * 0.85)
            pygame.draw.polygon(spike, (*dark, 255), (tip, b1, b2))
        screen.blit(spike, spike.get_rect(center=(int(bx), int(by))))
        pygame.draw.circle(screen, tint, (int(bx), int(by)), r)
        pygame.draw.circle(screen, light, (int(bx), int(by)), r, max(2, r // 8))
        pygame.draw.circle(screen, (*light, 120),
                           (int(bx - r * 0.25), int(by - r * 0.3)), max(2, int(r * 0.3)))
        ex = math.cos(b.t * 0.5) * r * 0.2
        ey = math.sin(b.t * 0.5) * r * 0.2
        for sgn in (-1, 1):
            cx = int(bx + ex + sgn * r * 0.32)
            cy = int(by + ey - r * 0.1)
            pygame.draw.circle(screen, (255, 255, 255), (cx, cy), max(2, int(r * 0.18)))
            pygame.draw.circle(screen, (30, 10, 20), (cx, cy), max(1, int(r * 0.09)))
        if b.hit_flash > 0:
            fl = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            aa = int(200 * (b.hit_flash / 0.16))
            pygame.draw.circle(fl, (255, 255, 255, aa), (r + 2, r + 2), r)
            screen.blit(fl, fl.get_rect(center=(int(bx), int(by))))
        if b.mark_t > 0 and b.mark_stacks > 0:
            self._draw_mark_petals(screen, bx, by, r * 2, b.mark_stacks)
        if b.ember_stacks > 0:
            self._draw_ember_pips(screen, bx, by, r * 2, b.ember_stacks)

    # ================================================================ HUD
    def _draw_hud(self):
        screen = self.screen
        self._draw_topleft_status(screen)
        self._draw_topcenter_info(screen)
        self._draw_minimap(screen)
        self._draw_skill_bar(screen)
        self._draw_shield_indicator(screen)
        self._draw_boss_bar()

    def _draw_topleft_status(self, screen):
        pad = self.s(12)
        x, y = pad, pad
        panel_w = self.s(280)
        sn = self.snake
        multi = len(self.party) > 1
        # 编队每位一行：活跃行金边全亮，待命行 60% 透明
        for i, m in enumerate(self.party):
            y = self._draw_member_row(screen, m, i == self.active_idx,
                                      x, y, panel_w, multi)
        # 切换指示（双人局）
        if multi:
            if self.switch_cd > 0:
                txt, col = f"切换冷却 {self.switch_cd:.1f}s", COLOR_TEXT_DIM
            else:
                txt, col = "Q / 滚轮 切换就绪", COLOR_GOOD
            w = self.f_tiny.render(txt, True, col)
            screen.blit(w, (x, y))
            y += w.get_height() + self.s(6)
        else:
            y += self.s(4)

        # 经验条（编队共享一条）
        bw = panel_w
        bh = self.s(12)
        pygame.draw.rect(screen, (24, 20, 34), (x, y, bw, bh), border_radius=bh // 2)
        need = sn.exp_needed()
        ratio = min(1.0, sn.exp / need) if need else 1.0
        if ratio > 0:
            pygame.draw.rect(screen, COLOR_EXP, (x, y, int(bw * ratio), bh),
                             border_radius=bh // 2)
        pygame.draw.rect(screen, (90, 80, 110), (x, y, bw, bh), 1, border_radius=bh // 2)
        y += bh + self.s(2)
        t = self.f_tiny.render(f"EXP {sn.exp} / {need}   攻击 {self.player_damage}",
                               True, COLOR_TEXT_DIM)
        screen.blit(t, (x, y))

    def _draw_member_row(self, screen, m, active, x, y, panel_w, multi):
        """画一名编队成员的 HUD 行（槽位号 + 名字 + Lv + 血条），返回下一行 y。"""
        msn = m["snake"]
        dim = 255 if active else 150
        label = (f"{'①' if m['index'] == 0 else '②'} {m['name']}" if multi
                 else m["name"])
        if not msn.alive:
            label += "（阵亡）"
        t = self.f_sub.render(label, True,
                              COLOR_ACCENT if active else COLOR_TEXT_DIM)
        t.set_alpha(dim)
        screen.blit(t, (x, y))
        lv = self.f_sub.render(f"Lv.{msn.level}", True, COLOR_GOLD)
        lv.set_alpha(dim)
        screen.blit(lv, (x + panel_w - lv.get_width(), y))
        y += t.get_height() + self.s(4)

        # 生命条（血条制：红底 + 深色空槽 + 白描边 + 数值）
        hp_w = panel_w
        hp_h = self.s(18)
        ratio = (msn.hp / msn.hp_max) if msn.hp_max > 0 else 0.0
        ratio = max(0.0, min(1.0, ratio))
        bar = pygame.Surface((hp_w, hp_h), pygame.SRCALPHA)
        pygame.draw.rect(bar, (40, 30, 40, dim), bar.get_rect(),
                         border_radius=hp_h // 2)
        fill_w = int(hp_w * ratio)
        if fill_w > 0:
            if not msn.alive:
                bar_col = (130, 120, 130)
            else:
                bar_col = COLOR_HP if ratio > 0.3 else (255, 60, 70)
            pygame.draw.rect(bar, (*bar_col, dim), (0, 0, fill_w, hp_h),
                             border_radius=hp_h // 2)
        outline = (255, 255, 255, dim) if active else (255, 255, 255, dim // 2)
        pygame.draw.rect(bar, outline, bar.get_rect(), 1, border_radius=hp_h // 2)
        screen.blit(bar, (x, y))
        hp_txt = self.f_tiny.render(f"{int(round(msn.hp))} / {msn.hp_max}", True,
                                    COLOR_TEXT)
        hp_txt.set_alpha(dim)
        screen.blit(hp_txt, hp_txt.get_rect(center=(x + hp_w // 2,
                                                    int(y + hp_h // 2))))
        return y + hp_h + self.s(6)

    def _draw_switch_hint(self, screen):
        """开局一次性提示：Q / 滚轮 切出战蛇娘；V 切形态（人形态解锁后）。"""
        if self.switch_hint_t <= 0:
            return
        if self.card_overlay:
            return    # 选卡浮层打开时让位，避免压在「选择强化」标题下
        lines = []
        if len(self.party) >= 2:
            lines.append("Q / 鼠标滚轮 切换出战蛇娘（下滑下一位 · 上滑上一位）")
        if any(self._form_available(m) for m in self.party):
            lines.append("V 切换形态（蛇形态 / 人形态 · 纯外观无数值差异）")
        if not lines:
            return
        fade = min(1.0, self.switch_hint_t / 0.8)
        surfs = [self.f_body.render(t, True, COLOR_GOLD) for t in lines]
        line_h = max(s.get_height() for s in surfs) + self.s(6)
        bw = max(s.get_width() for s in surfs) + self.s(32)
        bh = line_h * len(surfs) + self.s(14)
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg.fill((16, 14, 26, int(185 * fade)))
        bx = self.W // 2 - bw // 2
        by = self.H // 2 - self.s(200)
        screen.blit(bg, (bx, by))
        pygame.draw.rect(screen, (*COLOR_ACCENT, int(255 * fade)),
                         bg.get_rect(topleft=(bx, by)), self.s(2),
                         border_radius=self.s(10))
        for i, sf in enumerate(surfs):
            sf.set_alpha(int(255 * fade))
            screen.blit(sf, (bx + (bw - sf.get_width()) // 2,
                             by + self.s(7) + i * line_h))

    def _draw_topcenter_info(self, screen):
        if self.mode == "story":
            name = self.level_cfg.get("name", "剧情关") if self.level_cfg else "剧情关"
            if self.boss is not None or self.boss_spawned:
                head = f"{name}    Boss 战!"
            else:
                remain = max(0, int(self.story_duration - self.elapsed))
                mm, ss = divmod(remain, 60)
                head = f"{name}    距 Boss {mm:02d}:{ss:02d}"
            txt = f"{head}    击杀 {self.kills}    得分 {self.score}"
        else:
            txt = f"无尽 {int(self.elapsed)}s    击杀 {self.kills}    得分 {self.score}"
        t = self.f_body.render(txt, True, COLOR_TEXT)
        x = self.W // 2 - t.get_width() // 2
        bg = pygame.Surface((t.get_width() + self.s(24), t.get_height() + self.s(8)),
                             pygame.SRCALPHA)
        bg.fill((*COLOR_BG_LIGHT, 150))
        screen.blit(bg, (x - self.s(12), self.s(8)))
        screen.blit(t, (x, self.s(12)))
        sub_y = self.s(12) + t.get_height() + self.s(4)
        # 剧情模式：未出 Boss 时显示下一精英倒计时
        if (self.mode == "story" and self.boss is None and not self.boss_spawned
                and self.elapsed < self.story_duration):
            ne = max(0, int(self.elite_timer))
            w = self.f_tiny.render(
                f"下一精英 {ne}s   已讨伐精英 {self.elites_spawned}", True, COLOR_DANGER)
            screen.blit(w, (self.W // 2 - w.get_width() // 2, sub_y))
            sub_y += w.get_height() + self.s(2)
        tp = self._time_pressure()
        if tp > 1.05:
            w = self.f_tiny.render(f"压力 x{tp:.1f}", True, COLOR_DANGER)
            screen.blit(w, (self.W // 2 - w.get_width() // 2, sub_y))

    def _draw_minimap(self, screen):
        pad = self.s(12)
        mw = self.s(180)
        mh = max(1, int(mw * self.world_h / max(1, self.world_w)))
        mx = self.W - mw - pad
        my = pad + self.s(46)
        bg = pygame.Surface((mw, mh), pygame.SRCALPHA)
        bg.fill((16, 14, 26, 170))
        screen.blit(bg, (mx, my))
        pygame.draw.rect(screen, COLOR_ACCENT_DARK, (mx, my, mw, mh), 2)
        kx = mw / max(1, self.world_w)
        ky = mh / max(1, self.world_h)
        # 摄像机可视区
        view = pygame.Rect(mx + self.cam[0] * kx, my + self.cam[1] * ky,
                           self.W * kx, self.H * ky)
        pygame.draw.rect(screen, (255, 255, 255, 90), view, 1)
        # 道具
        for d in self.drops:
            pygame.draw.circle(screen, d.color,
                               (int(mx + d.pos[0] * kx), int(my + d.pos[1] * ky)),
                               max(1, self.s(2)))
        # 小怪
        for m in self.mobs:
            pygame.draw.circle(screen, COLOR_DANGER,
                               (int(mx + m.pos[0] * kx), int(my + m.pos[1] * ky)),
                               max(1, self.s(2)))
        # Boss
        if self.boss is not None and self.boss.alive:
            bx, by = self.boss.pos
            pygame.draw.circle(screen, COLOR_GOLD,
                               (int(mx + bx * kx), int(my + by * ky)), max(2, self.s(4)))
        # 玩家
        pygame.draw.circle(screen, (120, 255, 160),
                           (int(mx + self.snake.pos[0] * kx),
                            int(my + self.snake.pos[1] * ky)), max(2, self.s(3)))
        fps = self.game.clock.get_fps()
        color = COLOR_GOOD if fps > 55 else (COLOR_GOLD if fps > 40 else COLOR_DANGER)
        t = self.f_tiny.render(f"{fps:.0f} FPS", True, color)
        screen.blit(t, (mx + mw - t.get_width(), my + mh + self.s(2)))

    def _draw_skill_bar(self, screen):
        actives = self.skills.actives
        n_act = len(actives)
        slot = self.s(54)
        gap = self.s(9)
        cdr = self.stats["cdr"]
        n_total = n_act + 1                       # 主动 + 被动
        total = slot * n_total + gap * (n_total - 1)
        x0 = self.W // 2 - total // 2
        y0 = self.H - slot - self.s(16)
        slots = []
        # --- 主动槽（1..n）：名字统一放槽上方（见 _draw_skill_slot），不再只给首个大招 ---
        for i, a in enumerate(actives):
            rect = pygame.Rect(x0 + i * (slot + gap), y0, slot, slot)
            sid = a.get("id")
            # 键位标签跟随玩家自定义绑定（默认 1-6，改键后显示新键）
            kidx = int(a.get("key", i + 1)) - 1
            sk = self.game.controls.skill_keys
            key_label = (describe_key(sk[kidx]) if 0 <= kidx < len(sk)
                         else str(i + 1))
            self._draw_skill_slot(screen, rect, sid, key_label, cdr,
                                  active=True, show_name=True)
            slots.append((rect, sid, True, key_label))
        # --- 被动槽（常驻）---
        rect2 = pygame.Rect(x0 + n_act * (slot + gap), y0, slot, slot)
        self._draw_skill_slot(screen, rect2, self.skills.passive_id, "被动", cdr,
                              active=False, show_name=True)
        slots.append((rect2, self.skills.passive_id, False, "被动"))
        # --- 鼠标悬停在技能槽上时，浮出该技能的介绍 ---
        self._draw_skill_tooltip(screen, slots, cdr)

    def _draw_skill_tooltip(self, screen, slots, cdr):
        """鼠标悬停某个技能槽时，在其上方浮出介绍（名字/键位/冷却/说明/当前等级数值）。
        整块内容已预渲染缓存，悬停期间每帧只算位置 + blit 一次。"""
        mx, my = pygame.mouse.get_pos()
        hit = None
        for rect, sid, active, key_label in slots:
            if sid and rect.collidepoint(mx, my):
                hit = (rect, sid, active, key_label)
                break
        if hit is None:
            return
        rect, sid, active, key_label = hit
        panel, w, h = self._tooltip_panel(sid, active, key_label, cdr)
        x = max(self.s(8), min(rect.centerx - w // 2, self.W - w - self.s(8)))
        y = rect.top - h - self.s(10)
        screen.blit(panel, (x, y))

    def _tooltip_panel(self, sid, active, key_label, cdr):
        """把整块悬停介绍渲染成一张面并缓存，返回 (面板, 宽, 高)。

        技能文案现在是「详细机制说明」级别，悬停时逐帧折行 + 渲染十几行
        + 重跑数值管线，在战斗里会直接吃掉帧预算。key 里带了等级与冷却文本，
        吃到强化卡 / 冷却缩减变化时会自动重建，数值不会陷在旧缓存里。
        """
        info = skill_info(sid)
        color = tuple(info["color"])
        desc = info.get("desc", "") or "（暂无说明）"
        pad = self.s(16)
        max_w = self.s(360)
        inner_w = max_w - pad * 2
        cd_txt = (f"冷却 {self.skills.cooldown_max(sid, cdr):.1f}s" if active
                  else "常驻被动 · 无需释放")
        lv = self.skills.levels.get(sid, 0) if active else -1
        ckey = ("tip", sid, bool(active), key_label, cd_txt, lv)
        hit = self._text_cache.get(ckey)
        if hit is not None:
            return hit

        head = self._text_surf(f"[{key_label}]  {info['name']}", self.f_body, color)
        cdline = self._text_surf(cd_txt, self.f_tiny, COLOR_TEXT_DIM)
        desc_surfs = [self._text_surf(ln, self.f_small, COLOR_TEXT)
                      for ln in self._wrap_text(desc, self.f_small, inner_w)]
        line_h = self.f_small.get_height() + self.s(4)
        # 当前强化等级下的实时数值（与局内生效值同源），主动技才显示
        stat_surfs = []
        stat_h = self.f_tiny.get_height() + self.s(3)
        if active:
            parts = [f"{lab} {val}" for lab, val in self.skills.stat_lines(sid)]
            if parts:
                stat_txt = "　".join(parts)
                stat_surfs = [self._text_surf(ln, self.f_tiny, COLOR_GOLD)
                              for ln in self._wrap_text(stat_txt, self.f_tiny,
                                                        inner_w)]
        w = max(max_w, head.get_width() + pad * 2)
        h = (pad * 2 + head.get_height() + self.s(6) + cdline.get_height()
             + self.s(8) + line_h * max(1, len(desc_surfs))
             + (self.s(8) + stat_h * len(stat_surfs) if stat_surfs else 0))
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((18, 16, 30, 238))
        pygame.draw.rect(panel, color, panel.get_rect(), 2,
                         border_radius=self.s(10))
        cx, cy = pad, pad
        panel.blit(head, (cx, cy))
        cy += head.get_height() + self.s(6)
        panel.blit(cdline, (cx, cy))
        cy += cdline.get_height() + self.s(8)
        for s in desc_surfs:
            panel.blit(s, (cx, cy))
            cy += line_h
        if stat_surfs:
            cy += self.s(4)
            for s in stat_surfs:
                panel.blit(s, (cx, cy))
                cy += stat_h
        if len(self._text_cache) > 420:
            self._text_cache.clear()
        res = (panel, w, h)
        self._text_cache[ckey] = res
        return res

    def _text_surf(self, text, font, color):
        """渲染并缓存一行文字（同文本+同字号+同颜色只渲染一次）。
        返回的是共享面，调用方不要对它 set_alpha。"""
        key = ("txt", text, font.get_height(), tuple(color))
        hit = self._text_cache.get(key)
        if hit is not None:
            return hit
        if len(self._text_cache) > 420:
            self._text_cache.clear()
        surf = font.render(text, True, color)
        self._text_cache[key] = surf
        return surf

    def _draw_skill_slot(self, screen, rect, sid, key_label, cdr, active, show_name):
        """画一个技能槽：底板 + 图标 + 冷却遮罩 + 角标 + 槽上方名字。

        角标位置按主动/被动区分：主动键帽单字放左上，被动「被动」两字放左下——
        被动图标居中偏上，左上角标会正好压在图标脸上。名字统一放槽上方
        （主动被动同一标准），技能名最长 5 字、槽间距 63 设计像素，不会相邻重叠。"""
        slot = rect.width
        pygame.draw.rect(screen, (26, 22, 38, 210), rect, border_radius=self.s(8))
        if not sid:
            return
        info = skill_info(sid)
        color = info["color"]
        pygame.draw.rect(screen, color, rect, 2, border_radius=self.s(8))
        icon = self._skill_icon_surf(sid, slot * 0.80) if active else None
        if icon is not None:
            screen.blit(icon, icon.get_rect(
                center=(rect.centerx, rect.centery - self.s(2))))
        else:
            self._draw_skill_icon(screen, info.get("vfx", ""), rect.centerx,
                                  rect.centery - self.s(4), color,
                                  slot * (0.62 if active else 0.56))
        if active:
            ratio = self.skills.cd_ratio(sid, cdr)
            if ratio < 1.0:
                cover = pygame.Surface((slot, int(slot * (1.0 - ratio))), pygame.SRCALPHA)
                cover.fill((10, 8, 16, 165))
                screen.blit(cover, (rect.x, rect.y))
                left = self.skills.cooldown_left(sid)
                if left > 0.05:
                    cd = self.f_tiny.render(f"{left:.0f}", True, COLOR_TEXT)
                    screen.blit(cd, cd.get_rect(center=rect.center))
        tag = self._text_surf(key_label, self.f_tiny, COLOR_TEXT_DIM)
        if active:
            screen.blit(tag, (rect.x + self.s(4), rect.y + self.s(2)))
        else:
            # 被动：左下角标，避开居中的图标
            screen.blit(tag, (rect.x + self.s(4),
                              rect.bottom - tag.get_height() - self.s(2)))
        if show_name:
            nm = self._text_surf(info["name"], self.f_tiny, color)
            screen.blit(nm, nm.get_rect(
                midtop=(rect.centerx, rect.y - nm.get_height() - self.s(2))))

    def _draw_shield_indicator(self, screen):
        sn = self.snake
        pad = self.s(16)
        x = pad
        y = self.H - self.s(52)
        w, h = self.s(120), self.s(12)
        active = sn.shield_t > 0
        ready = sn.shield_cd <= 0
        ratio = 1.0 if ready else max(0.0, 1.0 - sn.shield_cd / max(1e-6, S.SHIELD_CD))
        shield_name = describe_shield(self.game.controls.shield)
        if active:
            txt, col = f"护盾 {int(round(sn.shield_pool))}", (160, 210, 255)
        else:
            txt = f"护盾 ({shield_name})"
            col = COLOR_GOOD if ready else COLOR_TEXT_DIM
        label = self.f_tiny.render(txt, True, col)
        screen.blit(label, (x, y - label.get_height() - self.s(2)))
        pygame.draw.rect(screen, (24, 20, 34), (x, y, w, h), border_radius=h // 2)
        bar_col = (160, 210, 255) if active else (COLOR_GOOD if ready else (120, 180, 220))
        if ratio > 0:
            pygame.draw.rect(screen, bar_col, (x, y, int(w * ratio), h), border_radius=h // 2)
        pygame.draw.rect(screen, (90, 80, 110), (x, y, w, h), 1, border_radius=h // 2)

    def _draw_dash2_pending(self, screen, sx, sy):
        """画出 dash2 一段留下的待引爆元素实体（脉动光环 + 剩余时限细环）。"""
        d = self.dash2
        if d is None:
            return
        if d.get("stella"):
            # 星璃·落星：落点已有星位地面视觉，二段窗口内不再画待爆光球
            return
        x = int(self.wx(d["x"], sx))
        y = int(self.wy(d["y"], sy))
        color = d["color"]
        ratio = max(0.0, min(1.0, d["t"] / max(1e-6, d["total"])))
        fx = self._skill_fx_surf(d.get("fx"), self.s(72)) if d.get("fly") else None
        if fx is not None:
            # 风系飞行实体：专属旋转贴图朝飞行方向自旋（叠外柔光）
            ang = math.degrees(math.atan2(d.get("vy", 0.0), d.get("vx", 1.0))) \
                + self.elapsed * 480.0
            gr = self.s(48)
            glow = self._glow_surf(gr, color, 46)
            screen.blit(glow, glow.get_rect(center=(x, y)))
            rot = self._rot_surf(fx, ang)
            screen.blit(rot, rot.get_rect(center=(x, y)))
        else:
            pulse = 0.7 + 0.3 * math.sin(self.elapsed * 10.0)
            rr = int(self.s(30) * pulse)
            orb = self._cached_surf(
                ("orb", rr, tuple(color)), (rr * 2, rr * 2),
                lambda s: (pygame.draw.circle(s, (*color, 70), (rr, rr), rr),
                           pygame.draw.circle(s, (*color, 200), (rr, rr),
                                              max(2, rr // 2)),
                           pygame.draw.circle(s, (255, 255, 255, 220), (rr, rr),
                                              max(1, rr // 4))))
            screen.blit(orb, orb.get_rect(center=(x, y)))
        ring_r = int(self.s(34))
        pygame.draw.arc(screen, color,
                        pygame.Rect(x - ring_r, y - ring_r, ring_r * 2, ring_r * 2),
                        math.pi / 2, math.pi / 2 + math.tau * ratio, max(2, self.s(3)))

    def _gust_sprite(self, size, color):
        """程序化旋涡风贴图（白底，绘制时按元素色 tint），按 (尺寸,色) 缓存。
        不依赖外部素材，各场景背景下都清晰可读。"""
        key = ("gust", int(size), tuple(color))
        surf = self._surf_cache.get(key)
        if surf is not None:
            return surf
        size = max(16, int(size))
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        r = c - max(2, size // 16)
        # 外圈柔光 + 主环
        pygame.draw.circle(surf, (*color, 40), (c, c), r)
        pygame.draw.circle(surf, (*color, 110), (c, c), r,
                           max(2, size // 22))
        # 三条内卷螺旋臂：半径逐圈收窄、相位各差 120°，旋转后像风在打转
        lw = max(2, size // 26)
        for k in range(3):
            pts = []
            ph = k * math.tau / 3
            for i in range(26):
                t = i / 25.0
                a = ph + t * math.tau * 1.6
                rr = r * (0.92 - 0.66 * t)
                pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
            pygame.draw.lines(surf, (*color, 200), False, pts, lw)
        # 白热风眼
        pygame.draw.circle(surf, (255, 255, 255, 225), (c, c),
                           max(2, size // 10))
        self._surf_cache[key] = surf
        return surf

    def _draw_gusts(self, screen, sx, sy):
        """飞行中的阵风：旋涡贴图按速度方向 + spin 自旋，外叠柔光。"""
        for g in self.gusts:
            x = int(self.wx(g["x"], sx))
            y = int(self.wy(g["y"], sy))
            size = int(max(self.s(44), g["half"] * 1.7))
            img = self._skill_fx_surf(g.get("fx"), size)
            if img is None:
                img = self._gust_sprite(size, g["color"])
            ang = math.degrees(math.atan2(g["vy"], g["vx"])) \
                + math.degrees(g["spin"])
            rot = self._rot_surf(img, ang)
            glow = self._glow_surf(size, g["color"], 46)
            screen.blit(glow, glow.get_rect(center=(x, y)))
            screen.blit(rot, rot.get_rect(center=(x, y)))

    def _draw_channel_bar(self, screen, sx, sy):
        """吟唱读条：角色头顶一条进度条（读满施加增益）。"""
        ch = self.channel
        if ch is None:
            return
        sn = self.snake
        cx = int(self.wx(sn.pos[0], sx))
        cy = int(self.wy(sn.pos[1], sy)) - self.s(96)
        fx = self._skill_fx_surf(ch.get("fx"), self.s(150))
        if fx is not None:
            # 读条期：角色身上环绕脉动旋转的技能光环贴图
            pulse = 0.82 + 0.18 * math.sin(self.elapsed * 6.0)
            halo = self._rotozoom_surf(fx, self.elapsed * 55.0, pulse)
            halo.set_alpha(150)
            screen.blit(halo, halo.get_rect(center=(cx, cy + self.s(96))))
        w, h = self.s(90), self.s(9)
        ratio = max(0.0, min(1.0, ch["t"] / max(1e-6, ch["total"])))
        color = ch["color"]
        x = cx - w // 2
        pygame.draw.rect(screen, (20, 16, 30), (x - 2, cy - 2, w + 4, h + 4),
                         border_radius=h // 2)
        if ratio > 0:
            pygame.draw.rect(screen, color, (x, cy, int(w * ratio), h),
                             border_radius=h // 2)
        pygame.draw.rect(screen, (255, 255, 255), (x, cy, w, h), 1, border_radius=h // 2)
        lab = self.f_tiny.render("吟唱中…", True, color)
        screen.blit(lab, lab.get_rect(midbottom=(cx, cy - self.s(3))))

    def _draw_skill_icon(self, screen, key, cx, cy, color, size=None):
        """按 vfx / 卡片 icon 标识绘制图标（主动/被动/属性卡共用）。"""
        r = (size or self.s(44)) * 0.5
        cx, cy = int(cx), int(cy)
        if key in ("slash", "atk"):
            # 斩击 / 攻击：斜刃
            pygame.draw.line(screen, color, (cx - r * 0.7, cy + r * 0.7),
                             (cx + r * 0.7, cy - r * 0.7), max(2, int(r * 0.22)))
            pygame.draw.line(screen, color, (cx - r * 0.15, cy + r * 0.8),
                             (cx + r * 0.8, cy - r * 0.15), max(1, int(r * 0.12)))
        elif key in ("wind", "speed", "atkspd"):
            # 风 / 移速 / 攻速：三道流线
            for k in range(3):
                yy = cy - r * 0.5 + k * r * 0.5
                pygame.draw.line(screen, color, (cx - r * 0.8, yy),
                                 (cx + r * (0.8 - k * 0.18), yy), max(2, int(r * 0.16)))
        elif key in ("wave", "slow", "pickup"):
            # 水浪 / 减速 / 拾取：同心弧
            for rr in (r * 0.85, r * 0.55, r * 0.28):
                rect = pygame.Rect(int(cx - rr), int(cy - rr), int(rr * 2), int(rr * 2))
                pygame.draw.arc(screen, color, rect, math.pi * 0.15, math.pi * 0.95,
                                max(2, int(r * 0.14)))
        elif key in ("flame", "burn"):
            # 火 / 灼烧：火苗
            pygame.draw.polygon(screen, color, [
                (cx, cy - r * 0.85), (cx + r * 0.55, cy + r * 0.1),
                (cx + r * 0.22, cy + r * 0.05), (cx + r * 0.35, cy + r * 0.78),
                (cx - r * 0.35, cy + r * 0.78), (cx - r * 0.28, cy + r * 0.02),
                (cx - r * 0.55, cy + r * 0.15)])
        elif key in ("star", "cdr"):
            # 星 / 冷却：五角星
            pts = []
            for k in range(10):
                a = -math.pi / 2 + k * math.pi / 5
                rr = r * (0.88 if k % 2 == 0 else 0.4)
                pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
            pygame.draw.polygon(screen, color, pts)
        elif key in ("moon", "guard"):
            # 月 / 守护：盾形
            k = r * 0.85
            pts = [(cx, cy - k), (cx + k * 0.78, cy - k * 0.4),
                   (cx + k * 0.78, cy + k * 0.2), (cx, cy + k),
                   (cx - k * 0.78, cy + k * 0.2), (cx - k * 0.78, cy - k * 0.4)]
            pygame.draw.polygon(screen, color, pts)
            pygame.draw.polygon(screen, (255, 255, 255), pts, 1)
        elif key == "heal":
            # 治疗：十字
            w = max(2, int(r * 0.32))
            pygame.draw.rect(screen, color, (cx - w // 2, int(cy - r * 0.72), w,
                                             int(r * 1.44)))
            pygame.draw.rect(screen, color, (int(cx - r * 0.72), cy - w // 2,
                                             int(r * 1.44), w))
        elif key == "hp":
            # 生命：心形（近似）
            pygame.draw.circle(screen, color, (int(cx - r * 0.3), int(cy - r * 0.22)),
                               max(2, int(r * 0.4)))
            pygame.draw.circle(screen, color, (int(cx + r * 0.3), int(cy - r * 0.22)),
                               max(2, int(r * 0.4)))
            pygame.draw.polygon(screen, color, [
                (cx - r * 0.66, cy - r * 0.05), (cx + r * 0.66, cy - r * 0.05),
                (cx, cy + r * 0.78)])
        else:
            # 未知图标：菱形宝石
            k = r * 0.75
            pygame.draw.polygon(screen, color, [(cx, cy - k), (cx + k, cy),
                                                (cx, cy + k), (cx - k, cy)])

    def _draw_skill_toast(self):
        if not self.skill_toast:
            return
        screen = self.screen
        for i, item in enumerate(self.skill_toast[:3]):
            info = skill_info(item["sid"])
            life = item["life"]
            if life > 2.75:
                a = (3.0 - life) / 0.25
            elif life < 0.5:
                a = life / 0.5
            else:
                a = 1.0
            a = max(0.0, min(1.0, a)) * 255
            w, h = self.s(430), self.s(70)
            x = self.W // 2 - w // 2
            y = self.s(70) + i * (h + self.s(10))
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            panel.fill((*COLOR_BG_LIGHT, int(220 * a / 255)))
            pygame.draw.rect(panel, (*info["color"], int(a)), panel.get_rect(),
                             self.s(3), border_radius=self.s(12))
            screen.blit(panel, (x, y))
            pad = self.s(14)
            t1 = self.f_tiny.render("获得/强化技能", True, COLOR_TEXT_DIM)
            t1.set_alpha(int(a))
            screen.blit(t1, (x + pad, y + pad))
            self._draw_skill_icon(screen, item["sid"], x + pad + self.s(10),
                                  y + h - self.s(24), info["color"], self.s(40))
            t2 = self.f_body.render(info["name"], True, info["color"])
            t2.set_alpha(int(a))
            screen.blit(t2, (x + pad + self.s(36),
                             y + h - self.s(24) - t2.get_height() / 2))

    def _draw_boss_bar(self):
        b = self.boss
        if b is None:
            return
        screen = self.screen
        w = int(self.W * 0.6)
        h = self.s(18)
        x = self.W // 2 - w // 2
        y = self.s(52)
        bar = pygame.Surface((w, h), pygame.SRCALPHA)
        bar.fill((20, 14, 26, 210))
        screen.blit(bar, (x, y))
        ratio = b.hp_ratio()
        fill_w = int(w * ratio)
        if fill_w > 0:
            grad = pygame.Surface((fill_w, h), pygame.SRCALPHA)
            grad.fill((*b.tint, 235))
            screen.blit(grad, (x, y))
        pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(x, y, w, h), 2,
                         border_radius=self.s(4))
        for ph in b.phases:
            below = float(ph.get("below", 1.0))
            if 0.0 < below < 1.0:
                mx = x + int(w * below)
                pygame.draw.line(screen, (255, 255, 255), (mx, y), (mx, y + h), 1)
        name = self.f_small.render(b.name, True, COLOR_TEXT)
        screen.blit(name, (x, y - name.get_height() - self.s(2)))
        hp_txt = self.f_tiny.render(f"{int(b.hp)} / {b.hp_max}", True, COLOR_TEXT_DIM)
        screen.blit(hp_txt, (x + w - hp_txt.get_width(),
                             y - hp_txt.get_height() - self.s(2)))

    def _draw_boss_banner(self):
        if self.boss_banner <= 0 or self.boss is None:
            return
        screen = self.screen
        total = 2.6
        life = self.boss_banner
        if life > total - 0.4:
            a = (total - life) / 0.4
        elif life < 0.6:
            a = life / 0.6
        else:
            a = 1.0
        a = max(0.0, min(1.0, a))
        cx = self.W // 2
        cy = int(self.H * 0.32)
        tint = self.boss.tint
        band = pygame.Surface((int(self.W * 0.6), self.s(64)), pygame.SRCALPHA)
        band.fill((10, 8, 16, int(190 * a)))
        pygame.draw.rect(band, (*tint, int(230 * a)), band.get_rect(), self.s(3),
                         border_radius=self.s(8))
        screen.blit(band, band.get_rect(center=(cx, cy)))
        warn = self.f_tiny.render("强敌登场", True, (*tint,))
        warn.set_alpha(int(255 * a))
        screen.blit(warn, warn.get_rect(center=(cx, cy - self.s(16))))
        nm = self.f_sub.render(self.boss.name, True, COLOR_TEXT)
        nm.set_alpha(int(255 * a))
        screen.blit(nm, nm.get_rect(center=(cx, cy + self.s(12))))

    # ================================================================ 选卡界面
    def _draw_card_overlay(self):
        screen = self.screen
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((8, 6, 14, 200))
        screen.blit(veil, (0, 0))
        m = self._card_target()
        if len(self.party) > 1:
            slot = "①" if m["index"] == 0 else "②"
            head_txt = f"选择强化 · 为 {slot} {m['name']}"
        else:
            head_txt = "选择强化"
        title = self.f_title.render(head_txt, True, COLOR_GOLD)
        screen.blit(title, title.get_rect(center=(self.W // 2,
                                                  self.card_rects[0].top - self.s(60))))
        hint_txt = "鼠标点击 或 按 1 / 2 / 3 选择"
        if len(self.card_queue) > 1:
            hint_txt += f"（还需为下一位选 {len(self.card_queue) - 1} 张）"
        hint = self.f_small.render(hint_txt, True, COLOR_TEXT_DIM)
        screen.blit(hint, hint.get_rect(center=(self.W // 2,
                                                self.card_rects[0].bottom + self.s(40))))
        for i, card in enumerate(self.card_overlay):
            rect = self.card_rects[i]
            color = tuple(card.get("color", [255, 255, 255])[:3])
            panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            panel.fill((*COLOR_BG_LIGHT, 235))
            screen.blit(panel, rect.topleft)
            pygame.draw.rect(screen, color, rect, self.s(3), border_radius=self.s(14))
            # 图标
            self._draw_skill_icon(screen, card.get("icon", ""), rect.centerx,
                                  rect.top + self.s(84), color, self.s(90))
            # 类型标签 + 强化卡等级角标
            is_enh = card.get("type") == "skill_enh"
            tt = self.f_tiny.render("技能强化" if is_enh else "强化", True, color)
            screen.blit(tt, tt.get_rect(center=(rect.centerx, rect.top + self.s(24))))
            if is_enh:
                lv = card.get("lv", 0)
                badge = self.f_tiny.render(f"Lv.{lv}/{S.SKILL_ENH_MAX}", True, COLOR_GOLD)
                screen.blit(badge, badge.get_rect(
                    topright=(rect.right - self.s(12), rect.top + self.s(10))))
            # 名称
            nm = self.f_body.render(card.get("name", ""), True, COLOR_TEXT)
            screen.blit(nm, nm.get_rect(center=(rect.centerx, rect.top + self.s(156))))
            # 描述（自动换行）
            self._draw_wrapped(screen, card.get("desc", ""), self.f_small,
                               COLOR_TEXT_DIM, rect.centerx, rect.top + self.s(196),
                               rect.width - self.s(32))
            # 成长预览：当前值 → 选中后值（属性卡专属，让玩家看清叠加后的结果）
            prev = card.get("preview")
            if prev:
                strip = pygame.Rect(rect.x + self.s(14), rect.bottom - self.s(56),
                                    rect.width - self.s(28), self.s(34))
                # 原先只铺一层 alpha=46 的卡片色，亮色卡（金/白）底下金字对比不足，
                # 选完卡根本看不清涨了多少。改成深色实底 + 卡片色描边，字改浅金。
                pad = pygame.Surface((strip.width, strip.height), pygame.SRCALPHA)
                pad.fill((14, 12, 22, 208))
                screen.blit(pad, strip.topleft)
                pygame.draw.rect(screen, (*color, 200), strip, max(1, self.s(2)),
                                 border_radius=self.s(9))
                pt = self.f_small.render(prev, True, (255, 226, 150))
                screen.blit(pt, pt.get_rect(center=strip.center))
            # 序号
            idx = self.f_small.render(str(i + 1), True, COLOR_TEXT_DIM)
            screen.blit(idx, (rect.x + self.s(12), rect.y + self.s(10)))

    def _draw_wrapped(self, screen, text, font, color, cx, top_y, max_w):
        lines = self._wrap_text(text, font, max_w)
        y = top_y
        for ln in lines[:4]:
            t = font.render(ln, True, color)
            screen.blit(t, t.get_rect(midtop=(cx, y)))
            y += t.get_height() + self.s(2)

    def _wrap_text(self, text, font, max_w):
        """中文按字折行（结果缓存 + 二分找断点），返回行列表。

        font.size() 单次要 ~0.17ms，旧的逐字折行在技能文案加长后
        每次悬停/选卡都要上千次测量，是战斗 UI 掉帧的大头：
          · 二分找断点：每行只要 log2(字数) 次测量（~7 次）；
          · 结果按 (文本, 字号, 宽) 缓存：同一张卡/同一个技能只折一次。
        """
        text = text or ""
        key = ("wrap", text, font.get_height(), max_w)
        hit = self._text_cache.get(key)
        if hit is not None:
            return hit
        lines = []
        rest = text
        while rest:
            if font.size(rest)[0] <= max_w:
                lines.append(rest)
                rest = ""
                break
            lo, hi, cut = 1, len(rest) - 1, 1
            while lo <= hi:
                mid = (lo + hi) // 2
                if font.size(rest[:mid])[0] <= max_w:
                    cut = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            lines.append(rest[:cut])
            rest = rest[cut:]
        if len(self._text_cache) > 420:
            self._text_cache.clear()
        self._text_cache[key] = lines or [""]
        return lines or [""]

    # ================================================================ 结算
    def _draw_gameover(self):
        screen = self.screen
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((10, 8, 16, 195))
        screen.blit(veil, (0, 0))
        cx, cy = self.W // 2, self.H // 2
        title = "胜利!" if self.victory else "战斗结束"
        title_color = COLOR_GOLD if self.victory else COLOR_ACCENT
        t = self.f_title.render(title, True, title_color)
        screen.blit(t, t.get_rect(center=(cx, cy - self.s(250))))
        rows = [
            ("最终得分", f"{self.score}", COLOR_TEXT),
            ("抵达等级", f"Lv.{self.snake.level}", COLOR_GOLD),
            ("击杀小怪", f"{self.kills}", COLOR_DANGER),
            ("存活时间", f"{int(self.elapsed)} 秒", (120, 210, 200)),
            ("获得星尘", f"{self.stardust}", (206, 168, 255)),
        ]
        if self.mode == "story" and self.elites_spawned > 0:
            rows.insert(3, ("讨伐精英", f"{self.elites_spawned}", (255, 90, 120)))
        if self.victory:
            boss_name = self.boss.name if self.boss else "Boss"
            rows.insert(0, ("击败 Boss", boss_name, title_color))
            rows.append(("通关奖励", f"+{S.BOSS_REWARD_STARDUST} 星尘", (206, 168, 255)))
        y = cy - self.s(180 if self.victory else 140)
        for label, value, color in rows:
            lt = self.f_body.render(label, True, COLOR_TEXT_DIM)
            vt = self.f_body.render(value, True, color)
            screen.blit(lt, lt.get_rect(midright=(cx - self.s(24), int(y))))
            screen.blit(vt, vt.get_rect(midleft=(cx + self.s(24), int(y))))
            y += self.s(50)
        t = self.f_small.render("按 R 再来一局    ·    按 ESC 返回主菜单", True, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(cx, cy + self.s(220))))

    # ================================================================ 暂停
    def _toggle_pause(self):
        self.paused = not self.paused
        if not self.paused:
            # 取消暂停：顺手关掉改键浮层并释放输入捕获
            self.rebind_open = False
            self.keybind_panel.listening = None
            self.game.input_capture = False
            self.game.flush_audio()

    def _open_rebind(self):
        """暂停菜单里展开「按键设置」浮层（不切场景，保留本局进度）。"""
        self.rebind_open = True
        self.keybind_panel.listening = None
        self.keybind_panel.message = ""
        self.game.input_capture = True

    def _close_rebind(self):
        self.rebind_open = False
        self.keybind_panel.listening = None
        self.game.input_capture = False

    def _rebind_restore(self):
        """一键恢复初始按键设置。"""
        self.game.controls.reset()
        self.keybind_panel.listening = None
        self.keybind_panel.message = "已恢复默认按键"

    # ================================================================ 返回主菜单（保存进度）
    def _ask_quit_menu(self):
        """暂停菜单点「返回主菜单」：弹二次确认（告知进度会保存）。"""
        self.quit_confirm = True

    def _cancel_quit_menu(self):
        self.quit_confirm = False

    def _confirm_quit_menu(self):
        """确认返回：把整局进度按 (模式,场景) 存盘后回主菜单，下次可继续。"""
        self.quit_confirm = False
        if not self.finished:
            self.game.save_manager.save_suspend(self._build_suspend())
        self.paused = False
        self.rebind_open = False
        self.game.input_capture = False
        self.game.change_scene("main_menu")

    def _clear_suspend(self):
        """本局结束（阵亡/通关）：清掉该 (模式,场景) 的挂起进度。"""
        try:
            self.game.save_manager.clear_suspend(self.mode, self.scene_id)
        except Exception:
            pass

    def _build_suspend(self):
        """把整局战斗状态序列化成可落盘的 dict。

        分辨率无关约定：位置存「世界比例」(0..1)，S 缩放的像素值存「设计值」
        (除以 self.S)，恢复时再乘回当前 S / 世界尺寸，换窗口大小也不错位。
        """
        ww, wh = max(1.0, self.world_w), max(1.0, self.world_h)
        sc = max(1e-6, self.S)

        def np_(p):
            return [float(p[0]) / ww, float(p[1]) / wh]

        sn = self.snake

        def snake_snap(s):
            return {
                "pos": np_(s.pos), "aim": list(s.aim_dir),
                "level": s.level, "exp": s.exp,
                "hp": s.hp, "hp_max": s.hp_max,
                "invincible": max(0.0, s.invincible),
                "shield_t": max(0.0, s.shield_t),
                "shield_pool": max(0.0, s.shield_pool),
                "shield_cd": max(0.0, s.shield_cd), "alive": s.alive,
                "atk_timer": s.atk_timer, "facing_angle": s.facing_angle,
                "path": [np_(p) for p in s.path],
            }

        def member_snap(mb):
            return {
                "char_id": mb["char_id"], "form": mb["form"],
                "snake": snake_snap(mb["snake"]),
                "card_stats": {k: float(v) for k, v in mb["card_stats"].items()},
                "hp_bonus": int(mb["hp_bonus"]),
                "skill_cds": {k: max(0.0, v) for k, v in mb["skills"].cds.items()},
                "skill_lv": {k: int(v) for k, v in mb["skill_lv"].items()},
                "gale_left": max(0.0, mb["skills"].gale_left),
            }

        return {
            "version": 2,
            "saved_at": time.time(),
            "mode": self.mode,
            "level_index": self.level_index,
            "scene_id": self.scene_id,
            "char_id": sn.char_id,
            "party": [member_snap(mb) for mb in self.party],
            "active_index": int(self.active_idx),
            "switch_cd": max(0.0, self.switch_cd),
            "card_queue": [int(i) for i in self.card_queue],
            # 以下单成员字段 = 活跃成员快照，保留给只读单角色的旧逻辑
            "snake": snake_snap(sn),
            "stats": {k: float(v) for k, v in self.stats.items()},
            "skill_cds": {k: max(0.0, v) for k, v in self.skills.cds.items()},
            "skill_lv": {k: int(v) for k, v in self.skill_lv.items()},
            "gale_left": max(0.0, self.skills.gale_left),
            "rally": [max(0.0, self.rally_t), self.rally_atk, self.rally_atkspd,
                      self.rally_armor],
            "regen_acc": self.regen_acc,
            "drops": [{"kind": d.kind, "pos": np_(d.pos), "tier": d.tier,
                       "magnet": bool(d.magnet)} for d in self.drops if d.alive],
            "mobs": [{
                "elite": bool(m.is_elite), "name": m.elite_name,
                "pos": np_(m.pos), "hp": m.hp, "hp_max": m.hp_max,
                "speed": m.speed / sc, "atk": m.atk, "radius": m.radius / sc,
                "jitter": m.jitter, "drop_count": m.drop_count,
                "slow_mult": m.slow_mult, "slow_t": max(0.0, m.slow_t),
                "burn_dps": m.burn_dps, "burn_t": max(0.0, m.burn_t),
                "burn_acc": m.burn_acc,
                "mark_t": max(0.0, m.mark_t), "mark_amp": m.mark_amp,
                "mark_stacks": m.mark_stacks,
            } for m in self.mobs if m.alive],
            "bullets": [{"pos": np_(b.pos),
                         "vel": [b.vel[0] / sc, b.vel[1] / sc],
                         "dmg": b.dmg, "radius": b.radius / sc, "life": b.life,
                         "color": list(b.color), "pierce": b.pierce}
                        for b in self.bullets if b.alive],
            "projectiles": [{"pos": np_(p.pos),
                             "vel": [p.vel[0] / sc, p.vel[1] / sc],
                             "radius": p.radius / sc, "damage": p.damage,
                             "color": list(p.color), "kind": p.kind, "life": p.life}
                            for p in self.projectiles if p.alive],
            "boss": self._boss_snapshot(np_) if self.boss else None,
            "boss_spawned": bool(self.boss_spawned),
            "boss_hit_cd": max(0.0, self.boss_hit_cd),
            "elapsed": self.elapsed, "score": self.score,
            "stardust": self.stardust, "kills": self.kills,
            "mob_spawn_timer": self.mob_spawn_timer,
            "item_spawn_timer": self.item_spawn_timer,
            "elite_timer": self.elite_timer,
            "elites_spawned": self.elites_spawned,
            "pending_cards": len(self.card_queue),
            "tutorial": [bool(self.tutorial_active), self.tutorial_index,
                         self.tutorial_timer],
        }

    def _boss_snapshot(self, np_):
        b = self.boss
        charge = None
        if b.charge:
            charge = {"phase": b.charge.get("phase", "telegraph"),
                      "timer": float(b.charge.get("timer", 0.0)),
                      "dir": list(b.charge.get("dir", (1.0, 0.0)))}
        slam = None
        if b.slam:
            slam = {"phase": b.slam.get("phase", "telegraph"),
                    "timer": float(b.slam.get("timer", 0.0)),
                    "pos": np_(b.slam.get("pos", b.pos))}
        return {"hp": b.hp, "hp_max": b.hp_max, "pos_cells": list(b.pos_cells),
                "intro": max(0.0, b.intro), "attack_timer": b.attack_timer,
                "spiral_angle": b.spiral_angle, "charge": charge, "slam": slam,
                "mark_t": max(0.0, b.mark_t), "mark_amp": b.mark_amp,
                "mark_stacks": b.mark_stacks}

    def _spawn_boss_silent(self):
        """恢复挂起局时重建 Boss：不播登场演出/音效/清弹幕。"""
        px = self.snake.pos[0]
        cx = self.world_cols - 4 if px < self.world_w / 2 else 3
        cy = self.world_rows / 2
        self.boss = Boss(self.boss_cfg, (cx, cy), lambda: self.CELL)
        self.boss_spawned = True

    def _restore_snake(self, sn, sd, dp):
        """把一份本体快照回填到 SnakeGirl 上（位置是世界比例）。"""
        if sd.get("pos"):
            sn.pos = dp(sd["pos"])
        if sd.get("aim"):
            sn.aim_dir = [float(v) for v in sd["aim"]]
        sn.level = int(sd.get("level", sn.level))
        sn.exp = int(sd.get("exp", sn.exp))
        sn.hp_max = max(1, int(sd.get("hp_max", sn.hp_max)))
        sn.hp = max(0.0, min(float(sn.hp_max), float(sd.get("hp", sn.hp))))
        sn.invincible = float(sd.get("invincible", 0.0))
        sn.shield_t = float(sd.get("shield_t", 0.0))
        sn.shield_pool = float(sd.get("shield_pool", 0.0))
        sn.shield_cd = float(sd.get("shield_cd", 0.0))
        sn.alive = bool(sd.get("alive", True))
        sn.atk_timer = float(sd.get("atk_timer", 0.0))
        sn.facing_angle = float(sd.get("facing_angle", 0.0))
        if sd.get("path"):
            sn.path = [tuple(dp(p)) for p in sd["path"]]
        sn.facing_update()

    def _restore_member(self, m, p, dp):
        """回填一名成员：形态 / 本体 / 局内属性副本 / 技能冷却与强化等级。"""
        m["form"] = p.get("form", m["form"])
        self._restore_snake(m["snake"], p.get("snake") or {}, dp)
        cs = p.get("card_stats") or {}
        for k in m["card_stats"]:
            if k in cs:
                m["card_stats"][k] = float(cs[k])
        m["hp_bonus"] = max(0, int(p.get("hp_bonus", 0)))
        self._rebuild_member_hp(m)
        m["snake"].hp = max(0.0, min(float(m["snake"].hp_max),
                                     float(m["snake"].hp)))
        cds = p.get("skill_cds") or {}
        for sid in list(m["skills"].cds):
            m["skills"].cds[sid] = float(cds.get(sid, 0.0))
        m["skills"].gale_left = float(p.get("gale_left", 0.0))
        slv = p.get("skill_lv") or {}
        for sid in list(m["skill_lv"]):
            m["skill_lv"][sid] = max(0, min(S.SKILL_ENH_MAX, int(slv.get(sid, 0))))

    def _restore_party(self, parts, dp):
        """按 v2 快照重建整支编队（人数/角色可能与 reset 建的不同）。"""
        ids = [p.get("char_id") for p in parts if isinstance(p, dict)
               and p.get("char_id")]
        if ids and ids != [m["char_id"] for m in self.party]:
            self.party = [self._make_member(cid, i) for i, cid in enumerate(ids)]
        for i, m in enumerate(self.party):
            if i < len(parts):
                self._restore_member(m, parts[i] or {}, dp)

    def _restore_card_stats_v1(self, m, st):
        """v1 快照存的是「最终属性」：反推回局内卡牌副本（除掉强化/被动乘区）。"""
        e = m["enh"]
        gale = S.PASSIVE_GALE_SPEED if m["passive_kind"] == "speed" else 1.0
        for k in m["card_stats"]:
            if k not in st:
                continue
            v = float(st[k])
            if k == "atk":
                v /= max(1e-6, e["atk"])
            elif k == "speed":
                v /= max(1e-6, e["speed"] * gale)
            elif k == "atkspd":
                v /= max(1e-6, e["atkspd"])
            elif k == "pickup":
                v /= max(1e-6, e["pickup"])
            elif k == "cdr":
                v = max(0.0, v - e["cdr"])
            m["card_stats"][k] = v
        # 生命卡加成：由快照 hp_max 减去强化后的原始上限反推
        base_hp = int(round(m["hp_base"] * e["hp"]))
        m["hp_bonus"] = max(0, int(m["snake"].hp_max) - base_hp)
        self._rebuild_member_hp(m)
        m["snake"].hp = max(0.0, min(float(m["snake"].hp_max),
                                     float(m["snake"].hp)))

    def _apply_suspend(self, data):
        """把 _build_suspend 的快照覆盖回当前战斗（reset 已建好同模式基础局）。"""
        ww, wh = self.world_w, self.world_h
        sc = self.S

        def dp(p):
            return [float(p[0]) * ww, float(p[1]) * wh]

        parts = data.get("party") or []
        if int(data.get("version", 1)) >= 2 and parts:
            # v2：整支编队逐个还原，再把活跃视图指回快照里的那一位
            self._restore_party(parts, dp)
            self.active_idx = 0
            ai = max(0, min(int(data.get("active_index", 0)), len(self.party) - 1))
            self._activate(ai, teleport=False)
            self.switch_cd = max(0.0, float(data.get("switch_cd", 0.0)))
            self.card_queue = [int(i) for i in (data.get("card_queue") or [])
                               if 0 <= int(i) < len(self.party)]
        else:
            # v1 老快照：单成员局，编队收缩到快照里的那个角色再回填
            cid = data.get("char_id") or self.party[self.active_idx]["char_id"]
            if [mb["char_id"] for mb in self.party] != [cid]:
                self.party = [self._make_member(cid, 0)]
            self.active_idx = 0
            self._activate(0, teleport=False)
            m = self.party[0]
            self._restore_snake(m["snake"], data.get("snake", {}) or {}, dp)
            self._restore_card_stats_v1(m, data.get("stats") or {})
            cds = data.get("skill_cds") or {}
            for sid in list(m["skills"].cds):
                m["skills"].cds[sid] = float(cds.get(sid, 0.0))
            m["skills"].gale_left = float(data.get("gale_left", 0.0))
            slv = data.get("skill_lv") or {}
            for sid in list(m["skill_lv"]):
                m["skill_lv"][sid] = max(0, min(S.SKILL_ENH_MAX,
                                                int(slv.get(sid, 0))))
            self._activate(self.active_idx, teleport=False)
            self.switch_cd = 0.0
            self.card_queue = [0] * int(data.get("pending_cards", 0))
        sn = self.snake

        rally = data.get("rally") or [0.0, 1.0, 1.0, 0.0]
        self.rally_t = float(rally[0])
        self.rally_atk = float(rally[1])
        self.rally_atkspd = float(rally[2])
        self.rally_armor = float(rally[3]) if len(rally) > 3 else 0.0
        self.regen_acc = float(data.get("regen_acc", 0.0))

        self.drops = []
        for d in data.get("drops", []) or []:
            drop = Drop(d.get("kind", "exp"), dp(d.get("pos", [0.5, 0.5])),
                        tier=d.get("tier", 1))
            drop.magnet = bool(d.get("magnet", False))
            self.drops.append(drop)

        self.mobs = []
        for m in data.get("mobs", []) or []:
            mob = Mob(dp(m.get("pos", [0.5, 0.5])), hp_mult=1.0,
                      speed=float(m.get("speed", 100.0)) * sc,
                      atk=int(m.get("atk", 1)),
                      radius=float(m.get("radius", S.MOB_RADIUS)) * sc)
            mob.hp_max = max(1, int(m.get("hp_max", mob.hp_max)))
            mob.hp = max(1, min(mob.hp_max, int(m.get("hp", mob.hp_max))))
            mob.jitter = float(m.get("jitter", mob.jitter))
            mob.drop_count = int(m.get("drop_count", 1))
            mob.slow_mult = float(m.get("slow_mult", 1.0))
            mob.slow_t = float(m.get("slow_t", 0.0))
            mob.burn_dps = float(m.get("burn_dps", 0.0))
            mob.burn_t = float(m.get("burn_t", 0.0))
            mob.burn_acc = float(m.get("burn_acc", 0.0))
            mob.mark_t = float(m.get("mark_t", 0.0))
            mob.mark_amp = float(m.get("mark_amp", 0.0))
            mob.mark_stacks = int(m.get("mark_stacks", 0))
            if m.get("elite"):
                mob.is_elite = True
                mob.elite_name = m.get("name", "精英")
            self.mobs.append(mob)

        self.bullets = []
        for b in data.get("bullets", []) or []:
            self.bullets.append(PlayerBullet(
                dp(b.get("pos", [0.5, 0.5])),
                [float(v) * sc for v in b.get("vel", [0.0, 0.0])],
                b.get("dmg", 1), float(b.get("radius", 6)) * sc,
                life=float(b.get("life", S.ATK_BULLET_LIFE)),
                color=tuple(b.get("color", (255, 210, 230))),
                pierce=int(b.get("pierce", 0))))

        self.projectiles = []
        for p in data.get("projectiles", []) or []:
            self.projectiles.append(Projectile(
                dp(p.get("pos", [0.5, 0.5])),
                [float(v) * sc for v in p.get("vel", [0.0, 0.0])],
                float(p.get("radius", 6)) * sc, p.get("damage", 1),
                tuple(p.get("color", (255, 120, 150))),
                kind=p.get("kind", "bullet"),
                life=float(p.get("life", S.BOSS_BULLET_LIFE))))

        bs = data.get("boss")
        if bs and self.boss_cfg:
            if self.boss is None:
                self._spawn_boss_silent()
            b = self.boss
            b.hp_max = max(1, int(bs.get("hp_max", b.hp_max)))
            b.hp = max(0, min(b.hp_max, int(bs.get("hp", b.hp_max))))
            if bs.get("pos_cells"):
                b.pos_cells = [float(v) for v in bs["pos_cells"]]
            b.intro = float(bs.get("intro", 0.0))
            b.attack_timer = float(bs.get("attack_timer", 1.4))
            b.spiral_angle = float(bs.get("spiral_angle", 0.0))
            b.mark_t = float(bs.get("mark_t", 0.0))
            b.mark_amp = float(bs.get("mark_amp", 0.0))
            b.mark_stacks = int(bs.get("mark_stacks", 0))
            ch = bs.get("charge")
            b.charge = ({"phase": ch.get("phase", "telegraph"),
                         "timer": float(ch.get("timer", 0.0)),
                         "dir": tuple(ch.get("dir", (1.0, 0.0)))} if ch else None)
            sl = bs.get("slam")
            b.slam = ({"phase": sl.get("phase", "telegraph"),
                       "timer": float(sl.get("timer", 0.0)),
                       "pos": tuple(dp(sl.get("pos", [0.5, 0.5])))} if sl else None)
            self.boss_spawned = bool(data.get("boss_spawned", True))
            if b.alive:
                self.game.audio.play_bgm("boss")
        else:
            self.boss = None
            self.boss_spawned = bool(data.get("boss_spawned", False))
        self.boss_hit_cd = float(data.get("boss_hit_cd", 0.0))

        self.elapsed = float(data.get("elapsed", 0.0))
        self.score = int(data.get("score", 0))
        self.stardust = int(data.get("stardust", 0))
        self.kills = int(data.get("kills", 0))
        self.mob_spawn_timer = float(data.get("mob_spawn_timer", 1.4))
        self.item_spawn_timer = float(
            data.get("item_spawn_timer", S.ITEM_SPAWN_INTERVAL))
        self.elite_timer = float(data.get("elite_timer", self.elite_interval))
        self.elites_spawned = int(data.get("elites_spawned", 0))
        tut = data.get("tutorial")
        if tut:
            self.tutorial_active = bool(tut[0])
            self.tutorial_index = int(tut[1])
            self.tutorial_timer = float(tut[2])

        # 摄像机跟随 + 收尾状态
        self.cam = [sn.pos[0] - self.W / 2, sn.pos[1] - self.H / 2]
        self._clamp_cam()
        self.paused = False
        self.finished = False
        self.victory = False
        self.card_overlay = None
        # BGM 同步到恢复后的时长；Boss 仍存活则继续放 Boss 战音乐
        self._setup_bgm()
        if self.boss is not None and self.boss.alive:
            self.game.audio.play_bgm("boss")
        if self.card_queue:
            self._open_card_overlay()

    def _pause_vol_layout(self):
        cx = self.W // 2
        cy = self.H // 2 - self.s(160)
        w, h = self.s(240), self.s(50)
        bgm_rect = pygame.Rect(0, 0, w, h)
        bgm_rect.center = (cx - self.s(150), cy)
        sfx_rect = pygame.Rect(0, 0, w, h)
        sfx_rect.center = (cx + self.s(150), cy)
        return bgm_rect, sfx_rect

    def _draw_pause(self):
        screen = self.screen
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((10, 8, 16, 190))
        screen.blit(veil, (0, 0))
        cx, cy = self.W // 2, self.H // 2
        t = self.f_title.render("已暂停", True, COLOR_ACCENT)
        screen.blit(t, t.get_rect(center=(cx, cy - self.s(230))))
        a = self.game.audio
        bgm = int(round(a.bgm_volume * 100))
        sfx = int(round(a.sfx_volume * 100))
        bgm_rect, sfx_rect = self._pause_vol_layout()
        for rect, label, val, key in (
            (bgm_rect, "音乐", bgm, "bgm"),
            (sfx_rect, "音效", sfx, "sfx"),
        ):
            focused = (a.volume_focus == key)
            color = COLOR_ACCENT if focused else COLOR_TEXT
            txt = self.f_body.render(f"{label} {val}", True, color)
            screen.blit(txt, txt.get_rect(center=rect.center))
            if focused:
                ul = pygame.Rect(0, 0, rect.width - self.s(70), 2)
                ul.center = (rect.centerx, rect.bottom - self.s(8))
                pygame.draw.rect(screen, COLOR_ACCENT, ul)
        hint = self.f_small.render(
            "鼠标点选 音乐/音效 后：↑/→ 增大  ↓/← 减小（±10，长按连调）", True,
            COLOR_TEXT_DIM)
        screen.blit(hint, hint.get_rect(center=(cx, cy - self.s(118))))
        self.resume_btn.draw(screen)
        self.restart_btn.draw(screen)
        self.rebind_btn.draw(screen)
        self.quit_btn.draw(screen)
        if self.quit_confirm:
            self._draw_quit_confirm(screen)

    def _draw_quit_confirm(self, screen):
        """「返回主菜单」二次确认：告知进度已保存，下次可继续。"""
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((8, 6, 14, 214))
        screen.blit(veil, (0, 0))
        cx = self.W // 2
        cy = self.H // 2
        w, h = self.s(640), self.s(320)
        panel = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(screen, COLOR_BG_LIGHT, panel, border_radius=self.s(14))
        pygame.draw.rect(screen, COLOR_ACCENT, panel, width=self.s(3),
                         border_radius=self.s(14))
        t = self.f_title.render("返回主菜单？", True, COLOR_ACCENT)
        screen.blit(t, t.get_rect(center=(cx, panel.top + self.s(66))))
        if self.finished:
            self.quit_yes_btn.text = "返回主菜单"
            l1 = self.f_body.render("本局已结束，直接返回主菜单。", True, COLOR_TEXT)
        else:
            self.quit_yes_btn.text = "保存并返回"
            l1 = self.f_body.render("当前进度会自动保存，下次选同一模式+场景可继续。",
                                    True, COLOR_TEXT)
        screen.blit(l1, l1.get_rect(center=(cx, panel.top + self.s(150))))
        self.quit_yes_btn.draw(screen)
        self.quit_no_btn.draw(screen)

    def _draw_rebind(self):
        """暂停内的改键浮层：标题 + 改键面板 + 恢复/返回按钮。"""
        screen = self.screen
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((8, 6, 14, 214))
        screen.blit(veil, (0, 0))
        cx = self.W // 2
        t = self.f_title.render("按键设置", True, COLOR_ACCENT)
        screen.blit(t, t.get_rect(center=(cx, self.keybind_panel_y - self.s(56))))
        sub = self.f_small.render(
            "点击某一行后按下新按键即可改键（护盾也可绑鼠标键）· 即时生效并保存",
            True, COLOR_TEXT_DIM)
        screen.blit(sub, sub.get_rect(
            center=(cx, self.keybind_panel_y - self.s(20))))
        self.keybind_panel.draw(screen, self.keybind_panel_x, self.keybind_panel_y,
                                self.keybind_panel_w, self.s,
                                self.f_body, self.f_small)
        self.rebind_restore_btn.draw(screen)
        self.rebind_back_btn.draw(screen)

    # ================================================================ 输入
    def handle_events(self, events):
        # ---- 选卡态：鼠标点击 / 数字键选卡 ----
        if self.card_overlay:
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, r in enumerate(self.card_rects):
                        if r.collidepoint(event.pos):
                            self._choose_card(i)
                            return
                elif event.type == pygame.KEYDOWN and event.key in _NUM_KEYS:
                    idx = _NUM_KEYS[event.key] - 1
                    if idx < len(self.card_overlay):
                        self._choose_card(idx)
                        return
            return

        # ---- 结算态：R 重开 / ESC 回主菜单 ----
        if self.finished:
            for event in events:
                if event.type != pygame.KEYDOWN:
                    continue
                if event.key == pygame.K_ESCAPE:
                    self.game.change_scene("main_menu")
                    return
                if event.key == pygame.K_r:
                    self.reset()
            return

        # ---- 暂停态 ----
        if self.paused:
            # 「返回主菜单」二次确认展开：只响应确认/取消，ESC 取消
            if self.quit_confirm:
                for event in events:
                    if (event.type == pygame.KEYDOWN
                            and event.key == pygame.K_ESCAPE):
                        self._cancel_quit_menu()
                        return
                    self.quit_yes_btn.handle_event(event)
                    self.quit_no_btn.handle_event(event)
                return
            # 改键浮层展开：优先把事件交给面板，其次浮层按钮，ESC 关闭浮层
            if self.rebind_open:
                for event in events:
                    if self.keybind_panel.handle_event(event):
                        continue
                    if (event.type == pygame.KEYDOWN
                            and event.key == pygame.K_ESCAPE):
                        self._close_rebind()
                        return
                    self.rebind_restore_btn.handle_event(event)
                    self.rebind_back_btn.handle_event(event)
                return
            # 普通暂停：鼠标点按钮/音量块 + ESC/P 继续
            bgm_rect, sfx_rect = self._pause_vol_layout()
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                    self._toggle_pause()
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if bgm_rect.collidepoint(event.pos):
                        self.game.audio.volume_focus = "bgm"
                    elif sfx_rect.collidepoint(event.pos):
                        self.game.audio.volume_focus = "sfx"
                self.resume_btn.handle_event(event)
                self.restart_btn.handle_event(event)
                self.rebind_btn.handle_event(event)
                self.quit_btn.handle_event(event)
            return

        # ---- 进行中：自定义护盾键 / 自定义技能键 / ESC-P 暂停（移动靠轮询）----
        ctrl = self.game.controls
        skill_map = ctrl.skill_map()
        shield = ctrl.shield
        shield_mouse = (shield.get("type") == "mouse")
        shield_btn = int(shield.get("button", 1))
        shield_key = int(shield.get("key", 0))
        # Q 为固定切换键：被玩家绑成技能键/护盾键时让位（技能优先）
        q_free = (pygame.K_q not in skill_map
                  and (shield_mouse or shield_key != pygame.K_q))
        # V 为形态切换键：同样在被占用时让位
        v_free = (pygame.K_v not in skill_map
                  and (shield_mouse or shield_key != pygame.K_v))
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if shield_mouse and event.button == shield_btn:
                    self.try_shield(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                # 滚轮切换出战：下滑(y<0)=下一号，上滑(y>0)=上一号，取模循环
                if getattr(event, "y", 0):
                    self._try_switch(1 if event.y < 0 else -1)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_p):
                    self._toggle_pause()
                    return
                if not shield_mouse and event.key == shield_key:
                    self.try_shield(pygame.mouse.get_pos())
                    continue
                if q_free and event.key == pygame.K_q:
                    self._try_switch(1)
                    continue
                if v_free and event.key == pygame.K_v:
                    self._toggle_form()
                    continue
                slot = skill_map.get(event.key)
                if slot is not None:
                    self.cast_skill(slot)
