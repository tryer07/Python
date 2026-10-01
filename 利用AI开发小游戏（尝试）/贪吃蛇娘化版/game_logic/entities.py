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
        self.hp = S.HP_MAX
        self.hp_max = S.HP_MAX
        self.invincible = 0.0
        self.alive = True
        self.on_level_up_cb = None          # 由战斗场景挂上去

        # ---- 闪避状态机 ----
        self.dodge_cd = 0.0                 # 剩余冷却
        self.dodge_t = 0.0                  # 剩余位移时间（>0 表示正在闪避）
        self.dodge_dir = [0.0, 0.0]         # 闪避方向
        self.dodge_from = [0.0, 0.0]        # 闪避起点（做拖影）

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
    def start_dodge(self, direction):
        """开始闪避：direction 为归一化方向。返回是否成功触发。"""
        if self.dodge_cd > 0 or self.dodge_t > 0:
            return False
        dx, dy = direction
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            dx, dy = self.aim_dir
        d = math.hypot(dx, dy) or 1.0
        self.dodge_dir = [dx / d, dy / d]
        self.dodge_t = S.DODGE_TIME
        self.dodge_cd = S.DODGE_CD
        self.dodge_from = list(self.pos)
        self.invincible = max(self.invincible, S.DODGE_IFRAME)
        return True

    def update(self, dt, world_w, world_h, move_dir, speed, dodge_dist=None):
        """
        每帧更新：闪避位移优先，否则按 move_dir 自由移动，最后钳制在世界内。
        move_dir 应为归一化向量；speed 为世界像素/秒。
        """
        if not self.alive:
            return
        if self.invincible > 0:
            self.invincible -= dt
        if self.dodge_cd > 0:
            self.dodge_cd = max(0.0, self.dodge_cd - dt)

        self.move_dir = list(move_dir)

        if self.dodge_t > 0:
            # 闪避：在 DODGE_TIME 内匀速冲过 dodge_dist
            dist = dodge_dist if dodge_dist is not None else S.DODGE_DIST
            step = dist / max(1e-6, S.DODGE_TIME) * dt
            self.pos[0] += self.dodge_dir[0] * step
            self.pos[1] += self.dodge_dir[1] * step
            self.dodge_t = max(0.0, self.dodge_t - dt)
            self.vel = [self.dodge_dir[0] * dist / S.DODGE_TIME,
                        self.dodge_dir[1] * dist / S.DODGE_TIME]
        else:
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
        if self.invincible > 0 or not self.alive:
            return False
        self.hp -= amount
        self.invincible = S.IFRAME_TIME
        if self.hp <= 0:
            self.hp = 0
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
        return S.EXP_PER_LEVEL + (self.level - 1) * 12

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
                 pierce=0):
        self.pos = [float(pos[0]), float(pos[1])]
        self.vel = [float(vel[0]), float(vel[1])]
        self.dmg = dmg
        self.radius = float(radius)
        self.life = S.ATK_BULLET_LIFE if life is None else float(life)
        self.color = color
        self.pierce = pierce          # 还能穿透几只怪（大招用）
        self.alive = True
        self.hit_ids = set()

    def update(self, dt, world_w, world_h):
        self.life -= dt
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

    def __init__(self, pos, hp_mult=1.0, speed=100.0, atk=1, radius=None):
        self.uid = next(_UID_GEN)
        self.pos = [float(pos[0]), float(pos[1])]
        self.vel = [0.0, 0.0]
        self.hp_max = max(1, int(S.MOB_HP * hp_mult))
        self.hp = self.hp_max
        self.alive = True
        self.speed = float(speed)               # 世界像素/秒（battle 按时间注入）
        self.atk = int(atk)                     # 碰触伤害
        self.radius = float(radius if radius is not None else S.MOB_RADIUS)
        self.hit_flash = 0.0
        self.knock = [0.0, 0.0]
        self.t = random.random() * 6.28
        self.jitter = random.uniform(0.85, 1.15)  # 个体速度差，避免整齐划一

    def update(self, dt, player_pos, world_w, world_h, mobs=None):
        if self.hit_flash > 0:
            self.hit_flash -= dt
        self.t += dt * 3.0

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
            sp = self.speed * self.jitter
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

    @property
    def draw_pos(self):
        return (self.pos[0], self.pos[1])
