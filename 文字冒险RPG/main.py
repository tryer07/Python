# 文字冒险RPG —— FastAPI 后端入口
# 运行方式：直接 Run 本文件（main.py），服务启动后浏览器自动弹出游戏页面
# 游玩地址：http://localhost:8001 （无需在 PyCharm 里操作，纯浏览器游玩）

import json
import logging
import os
import re
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field

# ---------- 目录与路径 ----------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SAVES_DIR = BASE_DIR / "saves"
SAVES_DIR.mkdir(exist_ok=True)

# ---------- 日志 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# ---------- DeepSeek 客户端 ----------
client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# ---------- 系统提示词（AI 主持人 GM 的人设与规则）----------
# {character_block} 会在每次调用时替换成当前角色的档案与状态，让 AI 有据可依
SYSTEM_PROMPT_TEMPLATE = """你是一名桌游主持人（GM），负责主持一场文字冒险RPG。玩家通过网页输入行动指令，你负责描写世界、扮演所有NPC、推进剧情、判定战斗结果。

【当前玩家角色】
{character_block}

【主持规则】
1. 世界观：东方奇幻大陆「云荒」，有宗门、妖物、上古遗迹。剧情要连贯，你埋下的伏笔要记得回收。
2. 每次回复先写剧情描写（150~300字），要有画面感，结尾自然地给玩家留下可行动的方向，但不要列选项清单。
3. 战斗不要流水账：玩家攻击时你要判定命中与伤害，并体现在状态数值变化里。难度要公平，玩家乱来你可以让后果很严重。
4. 玩家每次行动后，你必须在回复的最末尾另起一行，用如下格式输出最新状态（这一行会被程序解析，格式绝不能错）：
[状态] HP=数值/上限 攻击=数值 金币=数值 背包=物品1,物品2
   示例：[状态] HP=85/100 攻击=12 金币=30 背包=锈剑,伤药x2
   没有变化也要原样重复当前状态。背包为空时写 背包=无。
5. 除这一行状态标记外，禁止输出任何面向程序的说明文字、Markdown符号（# * -）、以及括号里的旁白。
6. 全程使用简体中文，语气沉浸、有代入感，像一个真正的跑团GM。"""

# ---------- 预设职业 ----------
CHARACTER_CLASSES: dict[str, dict[str, Any]] = {
    "剑客": {"hp": 100, "attack": 14, "gold": 20, "items": ["铁剑"], "desc": "身法凌厉的流浪剑客，攻高血稳，开局一把铁剑。"},
    "术士": {"hp": 70, "attack": 18, "gold": 35, "items": ["桃木符"], "desc": "修习秘术的散修，脆皮但攻击极高，随身携带一道护身符。"},
    "游侠": {"hp": 85, "attack": 12, "gold": 45, "items": ["短弓", "伤药x2"], "desc": "翻山越岭的老猎人，均衡务实，药品和金币比别人都多。"},
}

# 状态标记解析：[状态] HP=85/100 攻击=12 金币=30 背包=锈剑,伤药x2
STATUS_PATTERN = re.compile(
    r"\[状态\]\s*HP=(\d+)/(\d+)\s*攻击=(\d+)\s*金币=(\d+)\s*背包=(.+)"
)

# ---------- 统一响应模型 ----------
class ApiResponse(BaseModel):
    code: int = Field(title="状态码", description="200 表示成功")
    message: str = Field(title="提示信息")
    data: Any = Field(title="返回数据")


# ---------- 请求模型 ----------
class CreateCharacterRequest(BaseModel):
    name: str = Field(title="角色名", description="玩家给角色起的名字")
    character_class: str = Field(title="职业", description="剑客 / 术士 / 游侠")


class ChatRequest(BaseModel):
    session_id: str = Field(title="会话 ID", description="由新建游戏接口返回的 id")
    message: str = Field(title="行动指令", description="玩家本次输入的行动")


# ---------- 会话读写工具 ----------
def get_save_file(session_id: str) -> Path:
    return SAVES_DIR / f"{session_id}.json"


def load_session(session_id: str) -> dict[str, Any]:
    with open(get_save_file(session_id), "r", encoding="utf-8") as f:
        return json.load(f)


def save_session(session_data: dict[str, Any]) -> None:
    session_file = get_save_file(session_data["current_session"])
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)


def generate_session_id() -> str:
    # 精确到微秒，防止同一秒内新建两局时 id 碰撞互相覆盖
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")


def build_character_block(session_data: dict[str, Any]) -> str:
    """把角色档案拼成文本，塞进系统提示词，让 AI 知道玩家当前状态"""
    character = session_data["character"]
    status = character["status"]
    items_text = ",".join(status["items"]) if status["items"] else "无"
    return (
        f"姓名：{character['name']}（职业：{character['class']}）\n"
        f"当前状态：HP={status['hp']}/{status['max_hp']} 攻击={status['attack']} "
        f"金币={status['gold']} 背包={items_text}"
    )


def call_gm(messages: list[Any]) -> str:
    """请求 DeepSeek 主持游戏，返回 GM 的完整回复文本"""
    logging.info("[GM] 正在请求 DeepSeek 推演剧情...")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=False,
        temperature=1.2,
    )
    ai_reply: str = response.choices[0].message.content or ""
    return ai_reply


def apply_status_to_session(session_data: dict[str, Any], reply_text: str) -> str:
    """
    从 AI 回复中解析 [状态] 标记行并同步进会话数据。
    返回剔除状态行之后的纯净文本（用于展示给玩家）。
    解析失败则不改数值、原文返回，保证游戏不中断。
    """
    match = STATUS_PATTERN.search(reply_text)
    if not match:
        return reply_text

    hp, max_hp, attack, gold, items_text = match.groups()
    status = session_data["character"]["status"]
    status["hp"] = int(hp)
    status["max_hp"] = int(max_hp)
    status["attack"] = int(attack)
    status["gold"] = int(gold)
    items = [item.strip() for item in items_text.split(",")]
    status["items"] = [] if items == ["无"] else items

    clean_text = reply_text[: match.start()].rstrip()
    return clean_text


# ---------- FastAPI 实例 ----------
tags_metadata = [
    {"name": "游戏流程", "description": "建卡、开局、行动推演"},
    {"name": "存档", "description": "游戏进度的读取与查询"},
]

app = FastAPI(
    title="文字冒险RPG",
    description="云荒大陆 —— AI 主持人（GM）实时生成剧情的文字冒险游戏",
    openapi_tags=tags_metadata,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------- 全局异常处理 ----------
@app.exception_handler(Exception)
async def handle_exception(request: Request, exc: Exception) -> JSONResponse:
    logging.error(f"[异常] 请求 {request.url.path} 失败: {exc}")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误，请稍后重试", "data": None},
    )


# ---------- 页面 ----------
@app.get("/", include_in_schema=False)
def read_index() -> Any:
    return FileResponse(STATIC_DIR / "index.html")



# ---------- 游戏接口 ----------
@app.post("/api/classes", response_model=ApiResponse, summary="获取可选职业列表", tags=["游戏流程"])
def list_classes() -> ApiResponse:
    data = [{"name": name, "desc": info["desc"]} for name, info in CHARACTER_CLASSES.items()]
    return ApiResponse(code=200, message="ok", data=data)


@app.post("/api/game/new", response_model=ApiResponse, summary="创建角色并开局", tags=["游戏流程"])
def new_game(request: CreateCharacterRequest) -> ApiResponse:
    # 1. 校验职业
    if request.character_class not in CHARACTER_CLASSES:
        return ApiResponse(code=400, message="没有这个职业，请重新选择", data=None)

    class_info = CHARACTER_CLASSES[request.character_class]

    # 2. 组装会话数据
    session_id = generate_session_id()
    session_data: dict[str, Any] = {
        "current_session": session_id,
        "name": f"{request.name}的冒险",
        "character": {
            "name": request.name,
            "class": request.character_class,
            "status": {
                "hp": class_info["hp"],
                "max_hp": class_info["hp"],
                "attack": class_info["attack"],
                "gold": class_info["gold"],
                "items": list(class_info["items"]),
            },
        },
        "messages": [],
    }

    # 3. 让 GM 生成开场剧情（不带历史，只给人设和角色卡）
    opening_prompt = (
        f"玩家「{request.name}（{request.character_class}）」刚进入云荒大陆，"
        f"请为这局冒险写一段开场：交代他此刻身处何地和眼下的困境，并自然邀请他迈出第一步。"
    )
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        character_block=build_character_block(session_data)
    )
    messages: list[Any] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": opening_prompt},
    ]
    opening_text = apply_status_to_session(session_data, call_gm(messages))

    # 4. 开场白写入历史并落盘
    session_data["messages"].append({"role": "assistant", "content": opening_text})
    save_session(session_data)
    logging.info(f"[新开局] 会话 {session_id} 创建成功，角色：{request.name}（{request.character_class}）")

    return ApiResponse(
        code=200,
        message="开局成功",
        data={
            "session_id": session_id,
            "character": session_data["character"],
            "story": opening_text,
        },
    )


@app.post("/api/game/action", response_model=ApiResponse, summary="玩家输入行动，GM推演结果", tags=["游戏流程"])
def game_action(request: ChatRequest) -> ApiResponse:
    # 1. 读取会话
    session_file = get_save_file(request.session_id)
    if not session_file.exists():
        return ApiResponse(code=404, message="存档不存在，请重新开局", data=None)
    session_data = load_session(request.session_id)

    # 2. 组装 messages：系统人设(含最新状态) + 历史 + 本次行动
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        character_block=build_character_block(session_data)
    )
    messages: list[Any] = [{"role": "system", "content": system_prompt}]
    messages.extend(session_data["messages"])
    messages.append({"role": "user", "content": request.message})

    # 3. 请求 GM
    reply_text = call_gm(messages)

    # 4. 解析状态标记 → 同步数值，并得到供玩家看的纯剧情
    clean_story = apply_status_to_session(session_data, reply_text)

    # 5. 历史只存干净剧情（状态行每次由系统提示词现给，不必落盘）
    session_data["messages"].append({"role": "user", "content": request.message})
    session_data["messages"].append({"role": "assistant", "content": clean_story})
    # 控制存档体积：过长时丢弃最早的消息，保留最近 40 条
    if len(session_data["messages"]) > 40:
        session_data["messages"] = session_data["messages"][-40:]
    save_session(session_data)

    return ApiResponse(
        code=200,
        message="ok",
        data={"story": clean_story, "character": session_data["character"]},
    )


@app.get("/api/game/{session_id}", response_model=ApiResponse, summary="查询存档与角色状态", tags=["存档"])
def get_game(session_id: str) -> ApiResponse:
    session_file = get_save_file(session_id)
    if not session_file.exists():
        return ApiResponse(code=404, message="存档不存在", data=None)
    session_data = load_session(session_id)
    return ApiResponse(
        code=200,
        message="ok",
        data={
            "session_id": session_id,
            "character": session_data["character"],
            "messages": session_data["messages"],
        },
    )


@app.get("/api/saves", response_model=ApiResponse, summary="列出全部存档", tags=["存档"])
def list_saves() -> ApiResponse:
    saves: list[dict[str, Any]] = []
    for save_file in sorted(SAVES_DIR.glob("*.json"), reverse=True):
        with open(save_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        character = data["character"]
        status = character["status"]
        saves.append(
            {
                "session_id": save_file.stem,
                "name": character["name"],
                "class": character["class"],
                "hp": f"{status['hp']}/{status['max_hp']}",
                "turns": len(data["messages"]) // 2,
            }
        )
    return ApiResponse(code=200, message="ok", data=saves)


if __name__ == "__main__":
    import uvicorn

    # 延迟 1.5 秒自动弹出浏览器，确保服务先起来
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8001")).start()
    uvicorn.run(app, host="0.0.0.0", port=8001, access_log=False)
