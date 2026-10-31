"""随机地牢 Roguelike：程序负责随机和数值，死亡后 AI 负责把死法写成文学。

像素版渲染的全部思路都在两个地方：
    pixelart.py  字符画 -> 贴图，以及纹理/亮度档的烘焙
    本文件的 Art / 视野计算   把贴图按火把亮度拼成一帧画面

规矩：一格画面 = 一个 TILE(12) 像素 = 一个美术像素，全程不做任何缩放插值；
颜色只从 settings.PALETTE 取；亮度分档在开局一次烘好，主循环只 blit。

操作：方向键 / WASD 移动，走进怪物格子 = 撞它一下造成伤害（Bump 攻击）；
空格原地等一回合；走到楼梯下潜。第 3 层起楼梯有精英守卫。
死亡不再静默弹回菜单，而是把整局的行动日志交给 DeepSeek，
换回一段吟游诗人讲给你听的故事。

架构（对应各模块）：
    dungeon.py    房间-走廊地宫生成（BFS 连通验证）
    entities.py   玩家/怪物数据类 + 贪心 AI + Bresenham 视线
    pixelart.py   像素贴图烘焙（纹理、精灵、压暗分档）
    action_log.py 逐条记录本局事实，界面滚动显示 + 死后喂 AI
    report.py     DeepSeek 验尸报告（本地兜底）
本文件只负责：主循环、回合调度、渲染。所有流程切换走 state 状态机，
不搞递归重启（上一代贪吃蛇踩过 main() 递归吞按键的坑）。
"""

import ctypes
import random
import sys

import pygame

from action_log import ActionLog
from dungeon import Dungeon, generate
from entities import Monster, Player, line_of_sight
from pixelart import (
    SPRITES,
    bake_levels,
    bake_sprite,
    make_deco,
    make_floor,
    make_wall,
)
from report import write_report
from settings import (
    COL_BG,
    COL_FRAME_DARK,
    COL_FRAME_LIGHT,
    COL_HP_EMPTY,
    COL_HP_GOOD,
    COL_HP_LOW,
    COL_LOG_BOLD,
    COL_PANEL,
    COL_TEXT,
    COL_TEXT_DIM,
    FPS,
    GUTTER,
    LIGHT_REMEMBER,
    LIGHT_RINGS,
    MAP_H,
    MAP_W,
    MAX_DEPTH,
    MARGIN,
    PALETTE,
    POTION_HEAL,
    TILE,
    TILE_STAIRS,
    TILE_WALL,
    TORCH_RADIUS,
    TRANSPARENT,
    WIN_H,
    WIN_W,
)

# 每层怪物池：第 1、2 层哥布林，3、4 层兽人，5 层骷髅剑士
MONSTER_POOL = {
    1: ("哥布林", 8, 3, 7),
    2: ("兽人", 14, 4, 6),
    3: ("骷髅剑士", 18, 6, 8),
}
BOSS_HP, BOSS_ATK = 30, 7

STATE_PLAYING = "playing"
STATE_DEAD = "dead"
STATE_WIN = "win"

# 视野里一格只可能是这几档亮度之一（含 1.0 贴脸档与记忆档）
LEVELS: tuple[float, ...] = tuple(
    sorted({f for _, f in LIGHT_RINGS} | {LIGHT_REMEMBER}, reverse=True))
BLACK = (0, 0, 0)                  # 没去过的地方：纯黑，不做混合，保持硬边
SHADOW_TEXT = (6, 5, 10)           # 文字投影，让字从花纹里跳出来
FLOOR_VARIANTS = 8                 # 地板纹理预烘 8 张，铺图时随机挑，避免房间像复制粘贴
WALL_FACES = ("plain", "north", "south", "corner")
DECO_KINDS = ("crack", "bones", "moss")
# 面板右边界与报告正文宽度，从窗口尺寸推出来，不写死数字
PANEL_RIGHT = WIN_W - MARGIN
REPORT_WIDTH = WIN_W - MARGIN * 2 - 120
MONSTER_NAMES = ("哥布林", "兽人", "骷髅剑士", "楼梯守卫")


def make_monsters(d: Dungeon, depth: int) -> list[Monster]:
    """按层数把生成器给的坐标变成实体。精英固定是「楼梯守卫」"""
    name, hp, atk, sight = MONSTER_POOL[min(depth, 3)]
    ms = [Monster(name, x, y, hp, atk, sight) for x, y in d.enemy_spawns]
    if d.boss_spawn is not None:
        bx, by = d.boss_spawn
        ms.append(Monster("楼梯守卫", bx, by, BOSS_HP, BOSS_ATK, 9, is_boss=True))
    return ms


class Art:
    """开局一次性把所有贴图（含各亮度档）烘好，之后主循环只查表和 blit"""

    def __init__(self) -> None:
        # 墙：四种贴边 × 五个亮度档
        self.wall: dict[str, dict[float, pygame.Surface]] = {}
        for face in WALL_FACES:
            base = make_wall(face)
            self.wall[face] = bake_levels(base, LEVELS)
        # 地板：预烘 8 张纹理，每张再压各档亮度
        rng = random.Random(20261031)
        self.floor: list[dict[float, pygame.Surface]] = [
            bake_levels(make_floor(rng), LEVELS) for _ in range(FLOOR_VARIANTS)
        ]
        self.deco: dict[str, dict[float, pygame.Surface]] = {
            kind: bake_levels(make_deco(kind), LEVELS) for kind in DECO_KINDS
        }
        # 静态物件与角色
        self.stairs = bake_levels(bake_sprite(SPRITES["stairs"]), LEVELS)
        self.potion = bake_levels(bake_sprite(SPRITES["potion"]), LEVELS)
        self.surds = bake_levels(bake_sprite(SPRITES["player"]), LEVELS)
        self.monster: dict[str, dict[float, pygame.Surface]] = {
            name: bake_levels(bake_sprite(grid), LEVELS)
            for name, grid in SPRITES.items()
            if name in {*MONSTER_POOL.values().__iter__().__class__ and (), }
        }
        # 上面那行是占位，真正的怪物表在下面按名字烘
        self.monster = {
            name: bake_levels(bake_sprite(SPRITES[name]), LEVELS)
            for name in ("哥布林", "兽人", "骷髅剑士", "楼梯守卫")
        }
#花名占位class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("随机地牢 · 像素版 · 验尸报告")
        self._disable_ime()   # 必须在 set_mode 之后：得先有窗口句柄
        self.clock = pygame.time.Clock()
        self.font = self._load_font(15)
        self.mid_font = self._load_font(16)
        self.big_font = self._load_font(24)
        self.art = Art()
        self.log = ActionLog()
        self.state = STATE_PLAYING
        self.deaths = 0
        self.report_text = ""
        self.report_ai = False
        self.report_pending = False
        self._new_run()

    @staticmethod
    def _disable_ime() -> None:
        """搜狗/QQ 输入法中文模式会吞掉方向键（贪吃蛇项目踩过的坑），
        把窗口和 IME 解除关联；非 Windows / 拿不到句柄（如无头驱动）就静默跳过"""
        if sys.platform != "win32":
            return
        info = pygame.display.get_wm_info()
        hwnd = info.get("window", 0) if info else 0
        if hwnd:
            ctypes.windll.imm32.ImmAssociateContext(int(hwnd), 0)

    @staticmethod
    def _load_font(size: int) -> pygame.font.Font:
        """日志和报告全是中文，必须显式挂中文字体，默认字体会画出一排方框。
        像素风里中文没法用 12x12 点阵画，只能继续用 TrueType + 一层投影"""
        for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
            try:
                return pygame.font.Font(path, size)
            except (FileNotFoundError, OSError):
                continue
        return pygame.font.SysFont("microsoftyahei,simhei", size)

    # ------------------------------------------------------------------
    # 局与层的推进
    # ------------------------------------------------------------------

    def _new_run(self) -> None:
        self.log = ActionLog()
        self.player = Player(0, 0)
        self.depth = 1
        self._enter_floor()
        self.log.add("勇者举着火把走进了地宫。")

    def _enter_floor(self) -> None:
        self.dungeon: Dungeon = generate(self.depth)
        self.player.x, self.player.y = self.dungeon.spawn
        self.monsters = make_monsters(self.dungeon, self.depth)
        self.potions: set[tuple[int, int]] = set(self.dungeon.potion_spawns)
        self._build_floor_art()
        self.explored: set[tuple[int, int]] = set()
        self.lit: dict[tuple[int, int], float] = {}
        self.remembered: set[tuple[int, int]] = set()
        self.log.set_depth(self.depth)
        self.log.add(f"勇者踏进了地下第 {self.depth} 层。")
        self._update_view()

    def _build_floor_art(self) -> None:
        """本层的地板纹理号与墙贴边类型固定下来，之后每帧都画成同一个样子，
        否则每帧随机会让地面像抖动"""
        rng = random.Random(hash(self.dungeon.spawn) ^ (self.depth * 7919))
        self.floor_variant = [
            [rng.randrange(FLOOR_VARIANTS) for _ in range(MAP_W)] for _ in range(MAP_H)
        ]
        self.deco_cell = [
            [rng.choice(self.art.deco) if rng.random() < 0.09 else None
             for _ in range(MAP_W)] for _ in range(MAP_H)
        ]
        d = self.dungeon
        self.wall_face: list[list[str]] = []
        for y in range(MAP_H):
            row: list[str] = []
            for x in range(MAP_W):
                if d.map[y][x] != TILE_WALL:
                    row.append("plain")
                    continue
                open_up = y > 0 and d.map[y - 1][x] != TILE_WALL
                open_down = y + 1 < MAP_H and d.map[y + 1][x] != TILE_WALL
                open_right = x + 1 < MAP_W and d.map[y][x + 1] != TILE_WALL
                if open_down and open_up:
                    row.append("plain")
                elif open_down and open_right:
                    row.append("corner")
                elif open_down:
                    row.append("south")
                elif open_up:
                    row.append("north")
                else:
                    row.append("plain")
            self.wall_face.append(row)

    def _descend(self) -> None:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            self.state = STATE_WIN
            self.log.add("勇者带着满身的伤走到了地宫尽头。")
            return
        self.player.grow_on_depth()
        self._enter_floor()

    # ------------------------------------------------------------------
    # 回合调度：玩家一个动作，全体怪物一个动作，算一圈
    # ------------------------------------------------------------------

    def _try_move(self, dx: int, dy: int) -> None:
        tx, ty = self.player.x + dx, self.player.y + dy
        hit = next((m for m in self.monsters if m.alive and (m.x, m.y) == (tx, ty)), None)
        if hit is not None:
            dmg = hit.take_hit(self.player.atk)
            if hit.alive:
                self.log.add(f"勇者 撞击 {hit.name} 造成 {dmg} 点")
            else:
                self.player.kills += 1
                self.log.add(f"勇者 击杀 了 {hit.name}")
            self.end_turn()
            return
        if not self._walkable((tx, ty)):
            return  # 撞墙不消耗回合，手感优先
        self.player.x, self.player.y = tx, ty
        if (tx, ty) in self.potions:
            self.potions.discard((tx, ty))
            healed = self.player.heal(POTION_HEAL)
            self.log.add(f"勇者 喝下 药水，回复 {healed} 点")
        if self.dungeon.map[ty][tx] == TILE_STAIRS:
            self.log.add("勇者沿着楼梯向下走去。")
            self._descend()
            if self.state == STATE_PLAYING:
                self.end_turn()
            return
        self.end_turn()

    def _walkable(self, cell: tuple[int, int]) -> bool:
        """能站的格子：在图内、不是墙、没有活怪占着。楼梯和药水都能踩着过"""
        x, y = cell
        if not (0 <= x < MAP_W and 0 <= y < MAP_H):
            return False
        if self.dungeon.map[y][x] == TILE_WALL:
            return False
        return not any(m.alive and (m.x, m.y) == cell for m in self.monsters)

    def _is_floor_cell(self, cell: tuple[int, int]) -> bool:
        """视线判定用：墙挡眼，别的都不挡"""
        x, y = cell
        return (0 <= x < MAP_W and 0 <= y < MAP_H
                and self.dungeon.map[y][x] != TILE_WALL)

    def _update_view(self) -> None:
        """火把视野：半径内、且不穿墙的格子才点亮；点亮过的永久记入 explored"""
        self.lit, self.remembered = {}, set()
        px, py = self.player.x, self.player.y
        for (dx, dy), factor in LIGHT_TABLE.items():
            cell = (px + dx, py + dy)
            if not (0 <= cell[0] < MAP_W and 0 <= cell[1] < MAP_H):
                continue
            if not line_of_sight((px, py), cell, self._is_floor_cell):
                continue
            self.lit[cell] = factor
            self.explored.add(cell)
        for cell in self.explored:
            if cell not in self.lit:
                self.remembered.add(cell)

    def end_turn(self) -> None:
        if self.state != STATE_PLAYING:
            return
        self.log.next_turn()
        self._monster_turn()
        self._update_view()
        if not self.player.alive:
            self.deaths += 1
            self.state = STATE_DEAD
            self.report_pending = True  # 报告延迟到下一帧生成，先让「阵亡」画面见屏

    def _generate_report(self) -> None:
        """本局唯一一次网络请求。窗口会停几秒等诗人，写完立即浮层见屏"""
        self.report_text, self.report_ai = write_report(self.log)
        self.report_pending = False

    def _monster_turn(self) -> None:
        for m in self.monsters:
            if not m.alive:
                continue
            if abs(m.x - self.player.x) + abs(m.y - self.player.y) == 1:
                dmg = m.attack_player(self.player)
                self.log.add(f"{m.name} 打了 勇者 {dmg} 点")
                if not self.player.alive:
                    self.log.add("勇者倒下了。")
                    return
                continue
            step = m.choose_step(self.player, self._walkable)
            if step is not None and self._walkable(step):
                m.x, m.y = step

    # ------------------------------------------------------------------
    # 主循环与渲染
    # ------------------------------------------------------------------

    def run(self) -> None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if self.state == STATE_PLAYING:
                        self._handle_key(event.key)
                    elif event.key == pygame.K_r:
                        self._new_run()
                        self.state = STATE_PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
            self._render()
            pygame.display.flip()          # 先把当前帧推上屏
            if self.report_pending:
                # 网络阻塞前已经翻过一屏，玩家至少看得到「诗人正在路上」；
                # 报告写完后下一轮循环再画浮层
                self._generate_report()
            self.clock.tick(FPS)

    def _handle_key(self, key: int) -> None:
        moves = {
            pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
            pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
            pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
            pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
        }
        if key in moves:
            dx, dy = moves[key]
            self._try_move(dx, dy)
        elif key in (pygame.K_SPACE, pygame.K_PERIOD):
            self.log.add("勇者 原地屏息等待。")
            self.end_turn()
        elif key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

    def _render(self) -> None:
        self.screen.fill(COL_BG)
        self._draw_map()
        self._draw_panel()
        if self.state == STATE_DEAD:
            self._draw_report_overlay("勇者命丧地宫", COL_HP_LOW)
        elif self.state == STATE_WIN:
            self._draw_report_overlay("勇者走到了尽头", COL_HP_GOOD)

    def _draw_map(self) -> None:
        """一格一格拼：先定亮度档，再贴地板/墙，最后盖装饰与角色"""
        d = self.dungeon
        frame = (MARGIN - 3, MARGIN - 3, MAP_W * TILE + 6, MAP_H * TILE + 6)
        pygame.draw.rect(self.screen, COL_FRAME_DARK, frame, 3)
        for gy in range(MAP_H):
            for gx in range(MAP_W):
                cx, cy = MARGIN + gx * TILE, MARGIN + gy * TILE
                if (gx, gy) in self.lit:
                    factor = self.lit[(gx, gy)]
                elif (gx, gy) in self.remembered:
                    factor = LIGHT_REMEMBER
                else:
                    self.screen.blit(self.art.black, (cx, cy))
                    continue
                if d.map[gy][gx] == TILE_WALL:
                    face = self.wall_face[gy][gx]
                    self.screen.blit(self.art.wall[face][factor], (cx, cy))
                    continue
                self.screen.blit(self.art.floor[self.floor_variant[gy][gx]][factor],
                                 (cx, cy))
                deco = self.deco_cell[gy][gx]
                if deco is not None:
                    self.screen.blit(self.art.deco[deco][factor], (cx, cy))
                self._draw_cell_items(gx, gy, cx, cy, factor)

    def _draw_cell_items(self, gx: int, gy: int, cx: int, cy: int,
                         factor: float) -> None:
        """楼梯、药水、怪物、勇者：同一档亮度查同一张预烘贴图，绝不现压暗"""
        if (gx, gy) == self.dungeon.stairs:
            self.screen.blit(self.art.stairs[factor], (cx, cy))
        if (gx, gy) in self.potions:
            self.screen.blit(self.art.potion[factor], (cx, cy))
        mob = next((m for m in self.monsters if m.alive and (m.x, m.y) == (gx, gy)),
                   None)
        if mob is not None:
            self.screen.blit(self.art.sprite_for(mob)[factor], (cx, cy))
        elif (gx, gy) == (self.player.x, self.player.y):
            self.screen.blit(self.art.surds[factor], (cx, cy))

    # ---------- 面板 ----------

    def _draw_panel(self) -> None:
        left = MARGIN + MAP_W * TILE + GUTTER
        top = MARGIN
        box = (left - 6, top, PANEL_X_END - left, WIN_H - top * 2)
        pygame.draw.rect(self.screen, COL_PANEL, box)
        pygame.draw.rect(self.screen, COL_FRAME_LIGHT, box, 1)
        x = left + 10
        y = top + 8
        self._text(x, y, "随机地牢", self.big_font, COL_LOG_BOLD)
        y += 34
        self._divider(x, y)
        y += 12
        self._text(x, y, f"地下第 {min(self.depth, MAX_DEPTH)} 层 · "
                         f"第 {self.log.turn} 回合", self.mid_font, COL_TEXT)
        y += 26
        self._hp_blocks(x, y)
        y += 22
        self._text(x, y, f"攻击 {self.player.atk}  击杀 {self.player.kills}"
                         f"  阵亡 {self.deaths} 次", self.font, COL_TEXT_DIM)
        y += 26
        self._divider(x, y)
        y += 10
        for line in self.log.recent_lines():
            self._text(x, y, line, self.font, COL_TEXT)
            y += 21
        self._text(x, WIN_H - 60, "方向键/WASD 移动·撞怪", self.font, COL_TEXT_DIM)
        self._text(x, WIN_H - 42, "空格 等待  踩上台阶下潜", self.font, COL_TEXT_DIM)
        self._text(x, WIN_H - 24, "火把照不到的只是没看见，不是没有", self.font,
                   PALETTE["t"])

    def _hp_blocks(self, x: int, y: int) -> None:
        """生命用一格的方块表示，2 点血一块——像素风里不该出现光滑进度条"""
        ratio = self.player.hp / self.player.max_hp
        color = COL_HP_GOOD if ratio > 0.35 else COL_HP_LOW
        self._text(x, y, f"生命 {self.player.hp}/{self.player.max_hp}",
                   self.font, color)
        blocks = (self.player.max_hp + 1) // 2
        bx = x + 118
        for i in range(blocks):
            full = self.player.hp >= (i + 1) * 2
            half = not full and self.player.hp == i * 2 + 1
            pygame.draw.rect(self.screen, COL_HP_EMPTY,
                             (bx + i * 9, y + 1, 8, 8))
            if full:
                pygame.draw.rect(self.screen, color, (bx + i * 9, y + 1, 8, 8))
            elif half:
                pygame.draw.rect(self.screen, color, (bx + i * 9, y + 1, 4, 8))

    def _divider(self, x: int, y: int) -> None:
        """方块拼的分隔线，代替一根细线"""
        for i in range(0, PANEL_X_END - x - 20, 6):
            pygame.draw.rect(self.screen, COL_FRAME_LIGHT, (x + i, y, 4, 2))

    def _text(self, x: int, y: int, text: str, font: pygame.font.Font,
              color: tuple[int, int, int]) -> None:
        """先画一层 1 像素投影再画正文：花砖地上中文才不至于糊成一团"""
        shadow = font.render(text, True, SHADOW_TEXT)
        self.screen.blit(shadow, (x + 1, y + 1))
        self.screen.blit(font.render(text, True, color), (x, y))

    # ---------- 结算浮层 ----------

    def _draw_report_overlay(self, title: str, title_color: tuple[int, int, int]) -> None:
        """死亡/通关浮层：盖住棋盘，只留故事"""
        veil = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        veil.fill((8, 7, 12, 240))
        self.screen.blit(veil, (0, 0))
        left = MARGIN + 60
        y = MARGIN + 26
        self._text(left, y, title, self.big_font, title_color)
        y += 40
        if self.state == STATE_DEAD:
            if self.report_pending:
                self._text(left, y, "吟游诗人正在路上……（正在请求 DeepSeek，约几秒）",
                           self.mid_font, COL_TEXT_DIM)
                self._draw_hints(left)
                return
            who = "吟游诗人（DeepSeek）" if self.report_ai else "本地验尸官（离线兜底）"
            self._text(left, y, f"—— 来自 {who} 的验尸报告 ——", self.mid_font,
                       PALETTE["t"])
            y += 30
            for line in self._wrap(self.report_text, REPORT_WIDTH):
                self._text(left, y, line, self.mid_font, COL_TEXT)
                y += 25
            self._text(left, y + 14, "日志已存入 autopsy/ 文件夹", self.font,
                       COL_TEXT_DIM)
        else:
            stats = self.log.stats()
            self._text(left, y, f"{stats['turns']} 个回合，地下 {stats['depth_reached']} "
                                f"层，击杀 {stats['kills']} 只。", self.mid_font, COL_TEXT)
            self._text(left, y + 30, "地宫的出口透进光来。这一次，吟游诗人替你欢呼。",
                       self.mid_font, COL_TEXT)
        self._draw_hints(left)

    def _draw_hints(self, left: int) -> None:
        self._text(left, WIN_H - 40, "按 R 再来一局    按 Esc 退出", self.mid_font,
                   COL_LOG_BOLD)

    def _wrap(self, text: str, max_width: int) -> list[str]:
        """按像素宽度断行（中文没有空格可断，只能逐字量）"""
        lines: list[str] = []
        current = ""
        for ch in text:
            if self.mid_font.size(current + ch)[0] > max_width:
                lines.append(current)
                current = ch
            else:
                current += ch
        if current:
            lines.append(current)
        return lines


# 面板右边界与报告正文宽度，从窗口尺寸推出来，不写死数字
PANEL_X_END = WIN_W - MARGIN
REPORT_WIDTH = WIN_W - MARGIN * 2 - 120


if __name__ == "__main__":
    Game().run()
