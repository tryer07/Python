"""验尸报告：把这局的行动日志喂给 DeepSeek，让它把勇者的死法写成文学。

这是整个项目「程序负责随机和数值，AI 负责叙事」分工的落点：
- 程序把事实记成干巴巴的日志（见 action_log.py），数字绝不交给 AI 编；
- AI 只做一件事：把日志润色成一段吟游诗，要求它不许改数字。

网络失败、没配 API key 都不能影响游戏本身，所以所有异常在这里兜住，
降级成朴素的本地报告——游戏可以没有文学，但不能没有结局。
"""

import os
from pathlib import Path

from action_log import ActionLog

# ---------- 提示词：把 AI 按在「复述者」的位子上 ----------

SYSTEM_PROMPT = """\
你是一名地精酒馆的吟游诗人。听众是一位刚在地牢冒险中死去的勇者的亡魂，
他会给你一份逐条记录本轮冒险的行动日志，你要把他的死因讲成一段酒馆故事。

规则：
1. 只许 1 段，150 字以内，直接开讲，不要标题、不要引号、不要 Markdown。
2. 日志里的数字是铁的事实：回合数、层数、伤害、击杀数，一个都不许改。
3. 你可以虚构氛围、天气、路人反应，但不得虚构日志里没有的关键事件。
4. 语气：三分敬意、七分刻薄，结尾落在他最狼狈的一个细节上。
5. 全程中文，偶尔蹦外语词算你失职。"""

USER_PROMPT_TEMPLATE = """\
战绩：{turns} 个回合，击杀 {kills} 只怪物，挨了 {hits} 次打，喝过 {potions} 瓶药水，
最深摸到地下 {depth} 层，然后就再也没上来。

行动日志（最后 {kept} 条）：
{transcript}

请把这个人的结局讲成一段酒馆故事。"""

REPORT_DIR = Path(__file__).resolve().parent / "autopsy"


def write_report(log: ActionLog) -> tuple[str, bool]:
    """生成验尸报告。返回 (报告正文, 是否 AI 生成)；任何失败都降级为本地报告"""
    stats = log.stats()
    transcript = log.transcript()
    kept = min(ActionLog.TRANSCRIPT_TAIL, len(log.entries))

    ballad = _ask_deepseek(stats, transcript, kept)
    is_ai = ballad is not None
    if ballad is None:
        ballad = _local_report(stats, transcript, kept)

    _save_to_file(stats, transcript, ballad, is_ai)
    return ballad, is_ai


def _ask_deepseek(stats: dict[str, int], transcript: str, kept: int) -> str | None:
    """请求 DeepSeek；没 key / 没装库 / 网络炸了都返回 None 交给本地兜底。
    openai 在函数内延迟导入：没装库的玩家照样能玩，只是报告没有文学润色"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    user_prompt = USER_PROMPT_TEMPLATE.format(
        turns=stats["turns"],
        depth=stats["depth_reached"],
        kills=stats["kills"],
        hits=stats["hits_taken"],
        potions=stats["potions"],
        kept=kept,
        transcript=transcript,
    )
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=1.2,   # 讲故事要发散；再高会蹦外语词（猜字谜项目验证过的边界）
            timeout=30,
        )
        content = completion.choices[0].message.content
        if content is None:
            return None
        return _clean(content)
    except Exception:
        # 这里必须宽兜底：验尸报告是锦上添花，任何异常都不配打断游戏收尾流程
        return None


def _clean(text: str) -> str | None:
    """剥掉 Markdown 残留和多余空行；剩空串就视为失败"""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return None
    text = " ".join(lines)
    for junk in ("**", "##", "`"):
        text = text.replace(junk, "")
    return text.strip() or None


def _local_report(stats: dict[str, int], transcript: str, kept: int) -> str:
    """没有 AI 时的朴素报告：直接把最后几条日志念出来"""
    tail = transcript.splitlines()[-5:]
    return (
        f"他撑了 {stats['turns']} 个回合，杀过 {stats['kills']} 只怪物，"
        f"最深摸到地下 {stats['depth_reached']} 层。最后几笔记录是："
        + "；".join(tail)
        + "。（吟游诗人请假了，这是验尸官自己写的）"
    )


def _save_to_file(stats: dict[str, int], transcript: str, ballad: str, is_ai: bool) -> None:
    """报告连日志一起落盘，留着复盘（也留着做博客素材）"""
    from datetime import datetime

    REPORT_DIR.mkdir(exist_ok=True)
    name = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"autopsy_{name}.txt"
    header = (
        f"验尸报告（{'AI 吟游诗人' if is_ai else '本地验尸官'} 出品）\n"
        f"回合 {stats['turns']} / 最深 B{stats['depth_reached']} / "
        f"击杀 {stats['kills']} / 挨打 {stats['hits_taken']} / 药水 {stats['potions']}\n"
    )
    path.write_text(
        header + "\n【报告正文】\n" + ballad + "\n\n【完整日志】\n" + transcript + "\n",
        encoding="utf-8",
    )
