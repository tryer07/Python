"""行动日志：把这一局发生的事逐条记下来。

这份日志有两个用途，所以每条都同时带「回合数、层数、事件」三个要素：
1. 游戏界面右下角滚动显示（只留最近几条）；
2. 玩家死亡后整份喂给 DeepSeek，让它把日志写成吟游诗（验尸报告）。

记录的原则：只写事实，不写形容词。「哥布林 打了 勇者 3 点」这种句子，
AI 才有的可发挥；程序自己把戏加足，AI 就只能照抄了。
"""

from dataclasses import dataclass


@dataclass
class LogEntry:
    turn: int
    depth: int
    text: str

    def format_line(self) -> str:
        return f"[第{self.turn}回合·B{self.depth}] {self.text}"


class ActionLog:
    MAX_KEEP = 400          # 单局日志硬上限，防止无限膨胀（真活到 400 回合算你厉害）
    SHOW_RECENT = 7         # 界面里滚动显示最近几条
    TRANSCRIPT_TAIL = 120   # 喂给 AI 时保留的最后条数（太头部的流水账没价值）

    def __init__(self) -> None:
        self.entries: list[LogEntry] = []
        self.turn = 0
        self.depth = 1

    # ---------- 记录 ----------

    def next_turn(self) -> None:
        """每执行一个玩家动作算一回合（原地等待也是一回合）"""
        self.turn += 1

    def set_depth(self, depth: int) -> None:
        self.depth = depth

    def add(self, text: str) -> None:
        if len(self.entries) >= self.MAX_KEEP:
            return
        self.entries.append(LogEntry(self.turn, self.depth, text))

    # ---------- 界面显示 ----------

    def recent_lines(self) -> list[str]:
        return [e.format_line() for e in self.entries[-self.SHOW_RECENT:]]

    # ---------- 喂 AI / 存档用 ----------

    def stats(self) -> dict[str, int]:
        """从日志文本里统计这局的战绩，作为报告的数字骨架。
        口径与 add() 的措辞约定绑定：击杀一律写「击杀」、
        怪物打玩家一律写「打了」、拾取药水一律写「喝下」"""
        kills = hits_taken = potions = 0
        for e in self.entries:
            if "击杀" in e.text:
                kills += 1
            if "打了" in e.text:
                hits_taken += 1
            if "喝下" in e.text:
                potions += 1
        return {
            "turns": self.turn,
            "depth_reached": max(e.depth for e in self.entries) if self.entries else 1,
            "kills": kills,
            "hits_taken": hits_taken,
            "potions": potions,
        }

    def transcript(self) -> str:
        """压缩成纯文本日志，给 AI 读。丢掉头部流水账，保留中后段"""
        tail = self.entries[-self.TRANSCRIPT_TAIL:]
        return "\n".join(e.format_line() for e in tail)
