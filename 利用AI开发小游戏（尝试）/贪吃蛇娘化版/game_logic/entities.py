# -*- coding: utf-8 -*-
"""
game_logic/entities.py —— 游戏里的所有实体（自由移动版）

坐标系：所有实体的 pos 都是「世界像素」（原点 = 世界左上角）。
绘制时由 battle 减去摄像机偏移 cam，得到屏幕坐标。
标注 (设计像素) 的尺寸常量在 battle 里按 self.S 缩放后传入。

设计要点：
  · 玩家用 WASD 八向自由移动，蛇尾变成纯装饰拖尾（不再碰撞）
  · 小怪始终索敌跟随玩家，速度 / 攻击力随时间上升
  · 道具只给经验，进入磁吸半径会飞向玩家
"""

import itertools
import math
import random

import settings as S
from core.asset_manager import angle_between

# 小怪唯一 id 生成器（荆棘/技能计冷却时要按"这只怪"来记）
_UID_GEN = itertools.count(1)


# ======================================================================
#  娘化角色蛇（自由移动玩家）
# ======================================================================
class SnakeGirl:
    """
    蛇娘本体（自由移动）。

    身体分成两部分画：
      · 上半身 = 一张人物立绘，贴在玩家位置
      · 下半身 = 一串「尾椎」贴图，沿玩家走过的路径反向排布（纯装饰）
    """

    def __init__(self, char_id="sakura", start_pos=(0.0, 0.0)):
        self.char_id = char_id
        self.pos = [float(start_pos[0]), float(start_pos[1])]   # 世界像素
        self.vel = [0.0, 0.0]                                    # 当前速度（世界像素/秒）
        self.move_dir = [0.0, 0.0]                               # 归一化输入方向
        self.aim_dir = [1.0, 0.0]                                # 朝向（普攻/立绘翻转用）
        self.radius = S.PLAYER_RADIUS                            # 碰撞半径（世界像素，battle 会覆写）

        # ---- 成长属性 ----
        self.level = 1
        self.exp = 0
        self.hp = float(S.HP_MAX)
        self.hp_max = S.HP_MAX
        self.invincible = 0.0             # 受击无敌帧（渲染时闪烁）
        self.shield_t = 0.0               # 护盾剩余时限（>0 时优先用吸收池承伤）
        self.shield_pool = 0.0            # 护盾剩余可吸收伤害量
        self.shield_cd = 0.0              # 左键护盾冷却
        self.hurt_t = 0.0                 # 受击动画计时（>0 时立绘红 tint + 后座）
        self.alive = True
        self.on_level_up_cb = None          # 由战斗场景挂上去

        # ---- 攻击节奏 ----
        self.atk_timer = 0.0

        # ---- 装饰尾迹 ----
        self.path = []                      # [(x, y), ...] 世界像素
        self.body_length = S.SNAKE_LEN
        self.seg_len = S.BODY_SEG_LEN       # 世界像素（battle 会按 scale 覆写）

        # ---- 视觉 ----
        self.facing_angle = 0.0
        self.bob_t = random.random() * 6.28

        self._init_path()

    # ------------------------------------------------------------ 初始化
    def _init_path(self):
        """初始路径：沿身后铺一条直线，免得开局尾椎全挤在身上"""
        hx, hy = self.pos
        total = int(self.seg_len * (self.body_length + 2))
        self.path = []
        for i in range(total, -1, -1):
            self.path.append((hx - self.aim_dir[0] * i, hy - self.aim_dir[1] * i))

    # ---------------------------------------------------------------- 移动
    def grant_shield(self, seconds, pool):
        """施加护盾：时限 + 吸收池，取更强者叠加。"""
        self.shield_t = max(self.shield_t, float(seconds))
        self.shield_pool = max(self.shield_pool, float(pool))

    def update(self, dt, world_w, world_h, move_dir, speed):
        """
        每帧更新：闪避位移优先，否则按 move_dir 自由移动，最后钳制在世界内。
        move_dir 应为归一化向量；speed 为世界像素/秒。
        """
        if not self.alive:
            return
        if self.invincible > 0:
            self.invincible -= dt
        if self.shield_t > 0:
            self.shield_t = max(0.0, self.shield_t - dt)
            if self.shield_t <= 0:
                self.shield_pool = 0.0
        if self.shield_cd > 0:
            self.shield_cd = max(0.0, self.shield_cd - dt)
        if self.hurt_t > 0:
            self.hurt_t = max(0.0, self.hurt_t - dt)

        self.move_dir = list(move_dir)
        mx, my = self.move_dir
        if abs(mx) > 1e-6 or abs(my) > 1e-6:
            d = math.hypot(mx, my) or 1.0
            mx, my = mx / d, my / d
            self.aim_dir = [mx, my]
        self.pos[0] += mx * speed * dt
        self.pos[1] += my * speed * dt
        self.vel = [mx * speed, my * speed]

        # 钳制在世界内（留一点边距，别让立绘卡出界）
        m = self.radius
        self.pos[0] = min(max(self.pos[0], m), max(m, world_w - m))
        self.pos[1] = min(max(self.pos[1], m), max(m, world_h - m))

    @property
    def draw_pos(self):
        """渲染位置 = 世界像素（battle 再减 cam）"""
        return (self.pos[0], self.pos[1])

    def update_path(self, dt):
        """把当前位置追加进路径，并裁掉过长的部分（装饰尾迹用）"""
        px, py = self.pos
        if not self.path or math.hypot(px - self.path[-1][0], py - self.path[-1][1]) > 1.5:
            self.path.append((px, py))
        max_pts = int(self.seg_len * (self.body_length + 3))
        if len(self.path) > max_pts:
            self.path = self.path[-max_pts:]

    def sample_tail_points(self):
        """
        沿路径反向均匀采样，得到每节尾椎的位置。
        返回 [(x, y, angle, scale), ...]，从靠近头到靠近尾。
        """
        if len(self.path) < 2:
            return []
        pts = []
        seg_len = self.seg_len
        n = self.body_length
        for i in range(1, n + 1):
            dist = seg_len * i
            p = self._point_at_distance_from_head(dist)
            if p is None:
                break
            nx, ny = self._point_at_distance_from_head(dist + 6) or p
            ang = angle_between((nx, ny), p)
            t = (i - 1) / max(1, n - 1)
            scale = S.BODY_SCALE_HEAD + (S.BODY_SCALE_TAIL - S.BODY_SCALE_HEAD) * t
            pts.append((p[0], p[1], ang, scale))
        return pts

    def _point_at_distance_from_head(self, dist):
        """从蛇头沿路径往回数 dist 像素，返回那个点"""
        if not self.path:
            return None
        acc = 0.0
        cur = self.path[-1]
        for i in range(len(self.path) - 2, -1, -1):
            prev = self.path[i]
            d = math.hypot(cur[0] - prev[0], cur[1] - prev[1])
            if acc + d >= dist:
                ratio = (dist - acc) / d if d > 1e-6 else 0.0
                return (cur[0] + (prev[0] - cur[0]) * ratio,
                        cur[1] + (prev[1] - cur[1]) * ratio)
            acc += d
            cur = prev
        return None

    def facing_update(self):
        self.facing_angle = angle_between((0, 0), (self.aim_dir[0], self.aim_dir[1]))

    # ---------------------------------------------------------------- 承伤
    def take_damage(self, amount):
        """承伤：护盾时限内优先扣吸收池，池空/到期才扣血。返回是否真的扣了血。"""
        if self.invincible > 0 or not self.alive:
            return False
        amount = float(amount)
        if self.shield_t > 0 and self.shield_pool > 0:
            absorb = min(amount, self.shield_pool)
            self.shield_pool -= absorb
            amount -= absorb
            if self.shield_pool <= 0:
                self.shield_t = 0.0
            if amount <= 0:
                return False          # 被护盾完全吸收
        self.hp -= amount
        self.invincible = S.IFRAME_TIME
        if self.hp <= 0:
            self.hp = 0.0
            self.alive = False
        return True

    # ---------------------------------------------------------------- 成长
    def gain_exp(self, amount):
        """加经验，可能连升多级。返回升了几级。"""
        if self.level >= S.LEVEL_MAX:
            return 0
        self.exp += amount
        gained = 0
        while self.exp >= self.exp_needed() and self.level < S.LEVEL_MAX:
            self.exp -= self.exp_needed()
            self.level += 1
            gained += 1
        if gained:
            self.on_level_up(gained)
        return gained

    def exp_needed(self):
        return S.EXP_PER_LEVEL + (self.level - 1) * S.EXP_GROWTH_PER_LEVEL

    def on_level_up(self, gained):
        if self.on_level_up_cb:
            self.on_level_up_cb(self.level, gained)

    @property
    def attack(self):
        return S.ATK_BASE + (self.level - 1) * S.ATK_PER_LEVEL


# ======================================================================
#  玩家普攻弹丸
# ======================================================================
class PlayerBullet:
    """自动普攻发射的弹丸。命中最近的怪即消失。pos/vel 世界像素。"""

    def __init__(self, pos, vel, dmg, radius, life=None, color=(255, 210, 230),
                 pierce=0, element="", from_skill=False, onhit=None, fx=None,
                 curve=0.0, spin=0.0):
        self.pos = [float(pos[0]), float(pos[1])]
        self.vel = [float(vel[0]), float(vel[1])]
        self.dmg = dmg
        self.radius = float(radius)
        self.life = S.ATK_BULLET_LIFE if life is None else float(life)
        self.color = color
        self.pierce = pierce          # 还能穿透几只怪（大招用）
        self.element = element        # 元素（普攻/风刃贴图与命中叠标记用）
        self.from_skill = from_skill  # 是否为技能飞行物（命中叠标记被动）
        self.onhit = onhit or None    # 命中时施加的元素副效果字段（供 _apply_combo_secondary）
        self.fx = fx or None          # 技能贴图 id（如 mint_blade）：绘制时优先用专属贴图
        # 樱落「飞樱散华」：curve=弹道角速度（rad/s，正负=弧旋方向），
        # spin=贴图自旋（度/秒）；rot 为当前贴图角度（度），None=朝速度方向。
        self.curve = float(curve)
        self.spin = float(spin)
        self.rot = None
        self.trail = False            # 旋转拖尾：飞行中撒花瓣粒子（battle 端结算）
        self.mark = False             # 命中必叠花瓣标记（段3 种花主手段）
        self.tex_rel = None           # 普攻贴图相对路径（effects/melee/…，缩放变体）
        self.trail_acc = 0.0
        self.alive = True
        self.hit_ids = set()

    def update(self, dt, world_w, world_h):
        self.life -= dt
        if self.curve:
            # 弧旋弹道：速度向量绕自身旋转，花瓣走弧线而非直线
            ca = self.curve * dt
            cv, sv = math.cos(ca), math.sin(ca)
            vx, vy = self.vel
            self.vel = [vx * cv - vy * sv, vx * sv + vy * cv]
        if self.spin:
            base = math.degrees(math.atan2(self.vel[1], self.vel[0])) \
                if self.rot is None else self.rot
            self.rot = base + self.spin * dt
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        if self.life <= 0:
            self.alive = False
            return
        if (self.pos[0] < -40 or self.pos[0] > world_w + 40
                or self.pos[1] < -40 or self.pos[1] > world_h + 40):
            self.alive = False


# ======================================================================
#  掉落物 / 地图道具
# ======================================================================
class Drop:
    """
    地上可以捡的东西：经验果 / 能量结晶 / 星尘 / 爱心。
    tier = 品质档（1..ITEM_TIER_MAX），越高经验越多、体积越大、颜色越亮。
    """

    KINDS = {
        "exp":      {"asset": "items/exp_berry.png",      "size": 44, "color": (240, 186, 96)},
        "crystal":  {"asset": "items/energy_crystal.png", "size": 44, "color": (120, 210, 200)},
        "stardust": {"asset": "items/energy_crystal.png", "size": 36, "color": (200, 160, 255)},
        "heart":    {"asset": "items/exp_berry.png",      "size": 40, "color": (226, 84, 110)},
    }

    def __init__(self, kind, pos, tier=1):
        self.kind = kind
        self.pos = [float(pos[0]), float(pos[1])]
        self.tier = max(1, min(S.ITEM_TIER_MAX, int(tier)))
        self.alive = True
        cfg = self.KINDS.get(kind, self.KINDS["exp"])
        self.asset = cfg["asset"]
        self.base_size = cfg["size"]
        self.color = cfg["color"]
        self.t = random.random() * 6.28
        self.magnet = False

    @property
    def size(self):
        """品质越高越大（+12% / 档）"""
        return int(self.base_size * (1.0 + 0.12 * (self.tier - 1)))

    def exp_value(self):
        """经验果随品质档放大经验值"""
        if self.kind != "exp":
            return 0
        return int(S.ITEM_EXP_BASE * (S.ITEM_TIER_EXP_MULT ** (self.tier - 1)))

    def update(self, dt, player_pos, magnet_radius, pickup_radius):
        """浮动动画 + 磁吸：进入磁吸半径就飞向玩家，够近则标记可拾取。"""
        self.t += dt * 2.6
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist <= magnet_radius:
            self.magnet = True
        if self.magnet and dist > 1.0:
            # 越近吸得越快
            pull = 620.0 + (magnet_radius - min(dist, magnet_radius)) * 3.0
            self.pos[0] += dx / dist * pull * dt
            self.pos[1] += dy / dist * pull * dt
            dist = math.hypot(player_pos[0] - self.pos[0],
                              player_pos[1] - self.pos[1])
        return dist <= pickup_radius       # 返回是否已可拾取

    @property
    def draw_pos(self):
        return (self.pos[0], self.pos[1] + math.sin(self.t) * 4)


# ======================================================================
#  小怪（自动索敌）
# ======================================================================
class Mob:
    """
    小怪。始终朝玩家直线追击，带轻微个体速度差与分离力防重叠。
    碰到玩家扣血，被弹丸/技能命中掉血。
    """

    def __init__(self, pos, hp_mult=1.0, speed=100.0, atk=1, radius=None,
                 sprite=""):
        self.uid = next(_UID_GEN)
        self.pos = [float(pos[0]), float(pos[1])]
        self.vel = [0.0, 0.0]
        self.hp_max = max(1, int(S.MOB_HP * hp_mult))
        self.hp = self.hp_max
        self.alive = True
        self.speed = float(speed)               # 世界像素/秒（battle 按时间注入）
        self.atk = int(atk)                     # 碰触伤害
        self.radius = float(radius if radius is not None else S.MOB_RADIUS)
        self.sprite = sprite or ""              # 场景主题贴图（空则回退通用影子图）
        self.hit_flash = 0.0
        self.knock = [0.0, 0.0]
        self.t = random.random() * 6.28
        self.jitter = random.uniform(0.85, 1.15)  # 个体速度差，避免整齐划一

        # ---- 持续状态（减速 / 灼烧 / 标记）：由 battle 施加，减速在 update 内自结算 ----
        self.slow_mult = 1.0
        self.slow_t = 0.0
        self.burn_dps = 0.0
        self.burn_t = 0.0
        self.burn_acc = 0.0
        # 标记（花印）：被标记者受到的伤害放大 mark_amp，到期自动清除
        self.mark_t = 0.0
        self.mark_amp = 0.0
        self.mark_stacks = 0            # 标记层数（重复标记叠加，越高越易伤）
        self.mark_exploded = False      # 满层自爆是否已触发（防重复爆）
        # 削弱（月属性 proc）：期间碰触伤害乘 weaken_mult
        self.weaken_t = 0.0
        self.weaken_mult = 1.0
        # 湿身（潮汐领域）：期间受到的伤害放大 wet_amp（水域体系视作水伤）
        self.wet_t = 0.0
        self.wet_amp = 0.0
        # 余烬（绯焰灼烧引爆闭环）：叠层 DOT，每 ember_decay 秒自耗 1 层；
        # 引信烙印期间（ember_frozen>0）冻结衰减，DOT 由 battle._update_flare 结算
        self.ember_stacks = 0
        self.ember_decay = S.FLARE_EMBER_DECAY
        self.ember_decay_t = 0.0
        self.ember_acc = 0.0
        self.ember_frozen = 0.0
        # ---- 精英标记（普通小怪为 False）----
        self.is_elite = False
        self.elite_name = ""
        self.drop_count = 1

    def update(self, dt, player_pos, world_w, world_h, mobs=None):
        if self.hit_flash > 0:
            self.hit_flash -= dt
        self.t += dt * 3.0

        # 减速状态到期自动恢复
        if self.slow_t > 0:
            self.slow_t = max(0.0, self.slow_t - dt)
            if self.slow_t <= 0:
                self.slow_mult = 1.0

        # 标记（易伤）状态到期自动清除
        if self.mark_t > 0:
            self.mark_t = max(0.0, self.mark_t - dt)
            if self.mark_t <= 0:
                self.mark_amp = 0.0
                self.mark_stacks = 0
                self.mark_exploded = False

        # 削弱状态到期自动恢复
        if self.weaken_t > 0:
            self.weaken_t = max(0.0, self.weaken_t - dt)
            if self.weaken_t <= 0:
                self.weaken_mult = 1.0

        # 湿身（易伤）状态到期自动清除
        if self.wet_t > 0:
            self.wet_t = max(0.0, self.wet_t - dt)
            if self.wet_t <= 0:
                self.wet_amp = 0.0

        # 余烬：非冻结期间按周期自耗一层，层数归零后清空
        if self.ember_frozen > 0:
            self.ember_frozen = max(0.0, self.ember_frozen - dt)
        elif self.ember_stacks > 0:
            self.ember_decay_t += dt
            while self.ember_decay_t >= self.ember_decay and self.ember_stacks > 0:
                self.ember_decay_t -= self.ember_decay
                self.ember_stacks -= 1
            if self.ember_stacks <= 0:
                self.ember_decay_t = 0.0
                self.ember_acc = 0.0

        # 击退衰减
        kx, ky = self.knock
        if abs(kx) > 0.5 or abs(ky) > 0.5:
            fade = min(1.0, dt * 8)
            kx -= kx * fade
            ky -= ky * fade
            self.knock = [kx, ky]
            self.pos[0] += kx * dt * 6
            self.pos[1] += ky * dt * 6

        # 追击玩家
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        d = math.hypot(dx, dy)
        if d > 1.0:
            sp = self.speed * self.jitter * self.slow_mult
            self.pos[0] += dx / d * sp * dt
            self.pos[1] += dy / d * sp * dt

        # 分离力：和同伴太近就互相推开，避免叠成一个点
        if mobs:
            sx = sy = 0.0
            for o in mobs:
                if o is self or not o.alive:
                    continue
                ox = self.pos[0] - o.pos[0]
                oy = self.pos[1] - o.pos[1]
                od = math.hypot(ox, oy)
                mind = self.radius + o.radius
                if 0 < od < mind:
                    f = (mind - od) / mind
                    sx += ox / od * f
                    sy += oy / od * f
            self.pos[0] += sx * 60 * dt
            self.pos[1] += sy * 60 * dt

        # 钳制在世界内
        m = self.radius
        self.pos[0] = min(max(self.pos[0], -m), world_w + m)
        self.pos[1] = min(max(self.pos[1], -m), world_h + m)

    def take_damage(self, amount):
        # 被标记（花印）时受到的伤害放大，连招核心
        if self.mark_t > 0:
            amount = amount * (1.0 + self.mark_amp)
        # 湿身（潮汐领域）时受到的伤害再放大
        if self.wet_t > 0:
            amount = amount * (1.0 + self.wet_amp)
        self.hp -= amount
        self.hit_flash = 0.18
        if self.hp <= 0:
            self.alive = False
        return not self.alive

    def knockback(self, from_pos, strength=140.0):
        dx = self.pos[0] - from_pos[0]
        dy = self.pos[1] - from_pos[1]
        d = math.hypot(dx, dy) or 1.0
        self.knock = [dx / d * strength, dy / d * strength]

    def apply_slow(self, mult, time):
        """被减速：保留更强的倍率与更长的剩余时间。"""
        mult = max(0.1, min(1.0, mult))
        if self.slow_t <= 0 or mult < self.slow_mult:
            self.slow_mult = mult
        self.slow_t = max(self.slow_t, time)

    def apply_burn(self, dps, time):
        """被灼烧：保留更高 DoT 与更长剩余时间。"""
        self.burn_dps = max(self.burn_dps, dps)
        self.burn_t = max(self.burn_t, time)

    def apply_mark(self, amp, time, max_stacks=1):
        """被标记：叠加层数（每层提升易伤 amp），刷新持续时间。
        amp 为「每层」易伤加成，总易伤 = amp × 当前层数，最多 max_stacks 层。
        返回 True 表示本次刚好叠满 max_stacks（触发满层自爆，仅一次）。"""
        max_stacks = max(1, int(max_stacks))
        self.mark_stacks = min(max_stacks, self.mark_stacks + 1)
        self.mark_amp = amp * self.mark_stacks
        self.mark_t = max(self.mark_t, time)
        if self.mark_stacks >= max_stacks and not self.mark_exploded:
            self.mark_exploded = True
            return True
        return False

    def clear_mark(self):
        """清空标记状态（引爆/自爆后调用）。"""
        self.mark_t = 0.0
        self.mark_amp = 0.0
        self.mark_stacks = 0
        self.mark_exploded = False

    def apply_weaken(self, mult, time):
        """被削弱（月属性）：期间碰触伤害乘 mult，保留更强倍率与更长剩余时间。"""
        mult = max(0.1, min(1.0, mult))
        if self.weaken_t <= 0 or mult < self.weaken_mult:
            self.weaken_mult = mult
        self.weaken_t = max(self.weaken_t, time)

    def apply_wet(self, amp, time):
        """被湿身（潮汐领域）：期间受到的伤害放大 amp，保留更强倍率与更长剩余时间。"""
        if self.wet_t <= 0 or amp > self.wet_amp:
            self.wet_amp = amp
        self.wet_t = max(self.wet_t, time)

    def add_ember(self, stacks=1):
        """叠余烬层（绯焰专属）：封顶 FLARE_EMBER_MAX，新叠层重置衰减计时，
        让刚撒上的火星烧得更久。返回 True 表示本次叠到了封顶。"""
        self.ember_stacks = min(S.FLARE_EMBER_MAX, self.ember_stacks + stacks)
        self.ember_decay_t = 0.0
        return self.ember_stacks >= S.FLARE_EMBER_MAX

    def freeze_ember(self, time):
        """引信烙印：冻结余烬自然衰减 time 秒（等自动引爆）。"""
        self.ember_frozen = max(self.ember_frozen, time)

    def consume_ember(self):
        """引爆结算：取走当前层数并清空余烬状态，返回被引爆的层数。"""
        n = self.ember_stacks
        self.ember_stacks = 0
        self.ember_decay_t = 0.0
        self.ember_acc = 0.0
        self.ember_frozen = 0.0
        return n

    def eff_atk(self):
        """实际碰触伤害：被削弱时打折。"""
        if self.weaken_t > 0:
            return max(1, int(round(self.atk * self.weaken_mult)))
        return self.atk

    @property
    def draw_pos(self):
        return (self.pos[0], self.pos[1])


# ======================================================================
#  精英怪（剧情模式定时登场）
# ======================================================================
class EliteMob(Mob):
    """精英怪：体型更大、血量更厚、碰触更痛，死亡多掉落，头顶常驻名字与血条。"""

    def __init__(self, pos, hp_mult=1.0, speed=100.0, atk=None, radius=None,
                 name="精英", sprite=""):
        base_radius = radius if radius is not None else S.MOB_RADIUS
        super().__init__(
            pos,
            hp_mult=hp_mult * S.ELITE_HP_MULT,
            speed=speed * S.ELITE_SPEED_MULT,
            atk=atk if atk is not None else S.ELITE_ATK,
            radius=base_radius * S.ELITE_SIZE_MULT,
            sprite=sprite,
        )
        self.is_elite = True
        self.elite_name = name
        self.drop_count = S.ELITE_DROPS
