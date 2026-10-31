"""随机地牢 Roguelike：程序负责随机和数值，死亡后 AI 负责把死法写成文学。

操作：方向键 / WASD 移动，走进怪物格子 = 撞它一下造成伤害（Bump 攻击）；
空格原地等一回合；走到楼梯「>」下潜。第 3 层起楼梯有精英守卫。
死亡不再静默弹回菜单，而是把整局的行动日志交给 DeepSeek，
换回一段吟游诗人讲给你听的故事。

架构（对应各模块）：
    dungeon.py    房间-走廊地宫生成（BFS 连通验证）
    entities.py   玩家/怪物数据类 + 贪心 AI + Bresenham 视线
    action_log.py 逐条记录本局事实，界面滚动显示 + 死后喂 AI
    report.py     DeepSeek 验尸报告（本地兜底）
本文件只负责：主循环、回合调度、渲染。所有流程切换走 state 状态机，
不搞递归重启（上一代贪吃蛇踩过 main() 递归吞按键的坑）。
"""

import ctypes
import sys

import pygame

from action_log import ActionLog
from dungeon import Dungeon, generate
from entities import Monster, Player
from report import write_report
from settings import (
    COL_BG,
    COL_ENEMY,
    COL_ENEMY_BOSS,
    COL_FLOOR,
    COL_FLOOR_LINE,
    COL_HP_GOOD,
    COL_HP_LOW,
    COL_PLAYER,
    COL_POTION,
    COL_STAIRS,
    COL_TEXT,
    COL_TEXT_DIM,
    COL_WALL,
    FPS,
    MAP_H,
    MAP_W,
    MAX_DEPTH,
    MARGIN,
    POTION_HEAL,
    TILE,
    TILE_STAIRS,
    TILE_WALL,
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


def make_monsters(d: Dungeon, depth: int) -> list[Monster]:
    """按层数把生成器给的坐标变成实体。精英固定是「楼梯守卫」"""
    name, hp, atk, sight = MONSTER_POOL[min(depth, 3)]
    ms = [Monster(name, x, y, hp, atk, sight) for x, y in d.enemy_spawns]
    if d.boss_spawn is not None:
        bx, by = d.boss_spawn
        ms.append(Monster("楼梯守卫", bx, by, BOSS_HP, BOSS_ATK, 9, is_boss=True))
    return ms


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("随机地牢 · 验尸报告")
        self._disable_ime()   # 必须在 set_mode 之后：得先有窗口句柄
        self.clock = pygame.time.Clock()
        self.font = self._load_font(18)
        self.big_font = self._load_font(34)
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
        """日志和报告全是中文，必须显式挂中文字体，默认字体会画出一排方框"""
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
        self.log.set_depth(self.depth)
        self.log.add(f"勇者踏进了地下第 {self.depth} 层。")

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

    def end_turn(self) -> None:
        if self.state != STATE_PLAYING:
            return
        self.log.next_turn()
        self._monster_turn()
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
        d = self.dungeon
        for y in range(MAP_H):
            for x in range(MAP_W):
                tile = d.map[y][x]
                if tile == TILE_WALL:
                    continue  # 背景色就是墙色，省一次绘制（楼梯也先铺成地板再画符号）
                px, py = MARGIN + x * TILE, MARGIN + y * TILE
                pygame.draw.rect(self.screen, COL_FLOOR, (px, py, TILE, TILE))
                pygame.draw.line(self.screen, COL_FLOOR_LINE, (px, py), (px + TILE, py))
                pygame.draw.line(self.screen, COL_FLOOR_LINE, (px, py), (px, py + TILE))
        if d.map[d.stairs[1]][d.stairs[0]] == TILE_STAIRS:
            self._glyph(">", COL_STAIRS, *d.stairs)
        for cx, cy in self.potions:
            self._glyph("!", COL_POTION, cx, cy)
        for m in self.monsters:
            if m.alive:
                self._glyph("E", COL_ENEMY_BOSS if m.is_boss else COL_ENEMY, m.x, m.y)
        self._glyph("@", COL_PLAYER, self.player.x, self.player.y)

    def _glyph(self, ch: str, color: tuple[int, int, int], gx: int, gy: int) -> None:
        px, py = MARGIN + gx * TILE, MARGIN + gy * TILE
        surf = self.font.render(ch, True, color)
        rect = surf.get_rect(center=(px + TILE // 2, py + TILE // 2))
        self.screen.blit(surf, rect)

    def _draw_panel(self) -> None:
        left = MARGIN + MAP_W * TILE + 24
        y = MARGIN + 4
        self._text(left, y, "随 机 地 牢", self.big_font, COL_TEXT)
        y += 52
        self._text(left, y, f"地下第 {min(self.depth, MAX_DEPTH)} 层    第 {self.log.turn} 回合", self.font, COL_TEXT)
        y += 30
        self._hp_bar(left, y)
        y += 30
        self._text(left, y, f"攻击 {self.player.atk}   击杀 {self.player.kills}   阵亡 {self.deaths} 次", self.font, COL_TEXT_DIM)
        y += 34
        self._text(left, y, "—— 行动日志 ——", self.font, COL_TEXT_DIM)
        y += 26
        for line in self.log.recent_lines():
            self._text(left, y, line, self.font, COL_TEXT)
            y += 24
        self._text(left, WIN_H - 66, "方向键/WASD 移动·撞怪  空格 等待", self.font, COL_TEXT_DIM)
        self._text(left, WIN_H - 40, "走到 > 下潜，第 3 层起楼梯有守卫", self.font, COL_TEXT_DIM)

    def _hp_bar(self, x: int, y: int) -> None:
        ratio = self.player.hp / self.player.max_hp
        color = COL_HP_GOOD if ratio > 0.35 else COL_HP_LOW
        self._text(x, y, f"生命 {self.player.hp}/{self.player.max_hp}", self.font, color)
        bar_x = x + 150
        pygame.draw.rect(self.screen, COL_WALL, (bar_x, y + 5, 180, 12))
        pygame.draw.rect(self.screen, color, (bar_x, y + 5, int(180 * ratio), 12))

    def _text(self, x: int, y: int, text: str, font: pygame.font.Font, color: tuple[int, int, int]) -> None:
        self.screen.blit(font.render(text, True, color), (x, y))

    def _draw_report_overlay(self, title: str, title_color: tuple[int, int, int]) -> None:
        """死亡/通关浮层：盖住棋盘，只留故事"""
        veil = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        veil.fill((10, 9, 14, 238))
        self.screen.blit(veil, (0, 0))
        left = MARGIN + 120
        y = MARGIN + 40
        self._text(left, y, title, self.big_font, title_color)
        y += 60
        if self.state == STATE_DEAD:
            if self.report_pending:
                self._text(left, y, "吟游诗人正在路上……（正在请求 DeepSeek，约几秒）", self.font, COL_TEXT_DIM)
                return
            who = "吟游诗人（DeepSeek）" if self.report_ai else "本地验尸官（离线兜底）"
            self._text(left, y, f"—— 来自 {who} 的验尸报告 ——", self.font, COL_TEXT_DIM)
            y += 34
            for line in self._wrap(self.report_text, 540):
                self._text(left, y, line, self.font, COL_TEXT)
                y += 28
            self._text(left, y + 30, "日志已存入 autopsy/ 文件夹", self.font, COL_TEXT_DIM)
        else:
            stats = self.log.stats()
            self._text(left, y, f"{stats['turns']} 个回合，地下 {stats['depth_reached']} 层，击杀 {stats['kills']} 只。", self.font, COL_TEXT)
            self._text(left, y + 34, "地宫的出口透进光来。这一次，吟游诗人替你欢呼。", self.font, COL_TEXT)
        self._text(left, WIN_H - 80, "按 R 再来一局    按 Esc 退出", self.font, COL_TEXT)

    def _wrap(self, text: str, max_width: int) -> list[str]:
        """按像素宽度断行（中文没有空格可断，只能逐字量）"""
        lines: list[str] = []
        current = ""
        for ch in text:
            if self.font.size(current + ch)[0] > max_width:
                lines.append(current)
                current = ch
            else:
                current += ch
        if current:
            lines.append(current)
        return lines


if __name__ == "__main__":
    Game().run()
