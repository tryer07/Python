import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field
from starlette.responses import FileResponse
import uvicorn

# 配置日志：级别 INFO，格式包含时间、级别、文件名、行号、日志内容
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)

# 以 main.py 自身所在目录为基准定位资源，避免因运行工作目录不同而找不到文件
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SESSIONS_DIR = BASE_DIR / "sessions"

# 创建 sessions 目录：不存在则新建，用于保存每次绘画的会话数据
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

# 系统提示词：定义 AI 的人设（猜字谜游戏主持人「柯灵」），作为全局变量供每次调用使用
SYSTEM_PROMPT = """你是一位汉字猜字谜游戏的主持人，名叫「柯灵」。

【出题】
- 每次给一个字谜（谜面 + "打一字"），难度先询问用户想玩什么难度，不要重复出过的题。

【判题——最重要】
- 你必须牢牢记住当前这道题的标准谜底，并在心里锁定它。
- 用户猜时，你只拿用户答案和这个锁定的谜底比对：一致就判对，不一致就判错。
- 绝不因为用户说得自信就改口承认错误答案。

【提示】
- 用户猜错时，先给一点点提示，不要直接公布谜底；猜错 3 次后可适当放宽。

【语气与格式】
- 语气亲切、温柔、体贴、活泼，每次回复尽量简短，适合游戏节奏。"""

# 创建 DeepSeek 大模型客户端（api_key 从环境变量读取，避免写死泄露）
client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# 接口分组说明（中文）
tags_metadata = [
    {"name": "页面", "description": "返回猜字谜游戏的前端页面"},
    {"name": "会话管理", "description": "创建并管理一局猜字谜会话"},
    {"name": "AI 对话", "description": "与猜字谜主持人「柯灵」对话"},
]

# 创建 FastAPI 实例
app = FastAPI(
    title="汉字弥合",
    description="汉字猜字谜游戏 —— AI 主持人「柯灵」会出题、判题并记住你们的进度",
    openapi_tags=tags_metadata,
)


# 统一响应模型：所有接口都按 code / message / data 三个字段返回
class ApiResponse(BaseModel):
    code: int = Field(title="状态码", description="200 表示成功")
    message: str = Field(title="提示信息")
    data: Any = Field(title="返回数据")


# 聊天请求模型：接收前端 POST 请求体中的 JSON 参数
class ChatRequest(BaseModel):
    session_id: str = Field(title="会话 ID", description="由“新建会话”接口返回的 id")
    message: str = Field(title="消息内容", description="本次发给 AI 的话")


# 基于当前时间生成绘画（会话）标识
def generate_session_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


# 根据 session id 返回 sessions 目录下对应的会话 JSON 文件路径
def get_session_file_name(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


# 访问首页：返回 static/index.html 页面，而不是 JSON
@app.get("/", summary="打开首页", tags=["页面"])
def index():
    return FileResponse(STATIC_DIR / "index.html")


# 新建绘画接口：生成会话标识，初始化会话数据并保存到 JSON 文件
@app.post("/api/sessions", response_model=ApiResponse, summary="新建猜字谜会话", tags=["会话管理"])
def create_session() -> ApiResponse:
    # 生成当前绘画的 id
    session_id = generate_session_id()

    # 组装绘画数据：新建时 messages 为空列表
    session_data = {
        "current_session": session_id,
        "messages": [],
    }

    # 保存到 sessions/{session_id}.json，ensure_ascii=False 保证中文正常，indent=2 提供缩进
    session_file = SESSIONS_DIR / f"{session_id}.json"
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    # 返回统一格式数据
    return ApiResponse(code=200, message="创建会话成功", data=session_id)


# 获取会话列表接口：读取 sessions 目录下所有会话 id，按时间倒序返回
@app.get("/api/sessions", response_model=ApiResponse, summary="获取会话列表", tags=["会话管理"])
def get_sessions() -> ApiResponse:
    logging.info("[sessions] 正在读取会话列表...")

    # 读取 sessions 目录下的所有文件名
    file_names = os.listdir(SESSIONS_DIR)

    # 遍历文件名，用 split('.') 去掉 .json 后缀，封装成 session_ids 列表
    session_ids = [name.split(".")[0] for name in file_names]

    # 按时间倒序排序（最新创建的会话排在最前）
    session_ids.sort(reverse=True)

    logging.info(f"[sessions] 共找到 {len(session_ids)} 个会话")
    return ApiResponse(code=200, message="获取会话列表成功", data=session_ids)


# 获取指定会话信息接口：根据路径参数 session_id 读取对应会话 JSON 的完整数据
@app.get("/api/sessions/{session_id}", response_model=ApiResponse, summary="获取指定会话信息", tags=["会话管理"])
def get_session(session_id: str) -> ApiResponse:
    logging.info(f"[session] 正在读取会话 {session_id} 的信息...")

    # 根据 session_id 定位对应会话文件并读取数据
    session_file = get_session_file_name(session_id)
    with open(session_file, "r", encoding="utf-8") as f:
        session_data = json.load(f)

    # 封装并返回会话数据
    return ApiResponse(code=200, message="获取会话信息成功", data=session_data)


# 删除指定绘画接口：根据 session_id 删除对应的会话 JSON 文件
@app.delete("/api/sessions/{session_id}", response_model=ApiResponse, summary="删除指定会话", tags=["会话管理"])
def delete_session(session_id: str) -> ApiResponse:
    logging.info(f"[session] 正在删除会话 {session_id} ...")

    # 根据 session_id 获取对应绘画文件名
    session_file = get_session_file_name(session_id)

    # 删除前先判断文件是否存在，存在才删（避免不存在时报错）
    if session_file.exists():
        os.remove(session_file)
        logging.info(f"[session] 已删除文件 {session_file.name}")
    else:
        logging.info("[session] 文件不存在，无需删除")

    # 返回删除结果
    return ApiResponse(code=200, message="删除会话成功", data=None)


# 与 AI 交互接口：读取会话历史，调用 DeepSeek 大模型，保存并返回回复
@app.post("/api/chat", response_model=ApiResponse, summary="与 AI「柯灵」猜字谜", tags=["AI 对话"])
def chat(request: ChatRequest) -> ApiResponse:
    # 日志：收到请求
    logging.info(f"[chat] 收到请求 session_id={request.session_id}, message={request.message}")

    # 1. 定位本次会话的 JSON 文件并读取历史会话数据
    session_file = get_session_file_name(request.session_id)
    with open(session_file, "r", encoding="utf-8") as f:
        session_data = json.load(f)

    # 2. 构建发给大模型的 messages：系统提示词 + 历史消息 + 本次用户消息
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(session_data["messages"])
    messages.append({"role": "user", "content": request.message})

    # 日志：请求大模型前
    logging.info("[chat] 正在请求 DeepSeek 大模型...")

    # 3. 调用 DeepSeek 大模型
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=False,
        temperature=1.5,
    )

    # 4. 解析大模型返回内容
    ai_reply = response.choices[0].message.content
    logging.info(f"[chat] 大模型返回: {ai_reply}")

    # 5. 将本次 AI 回复以 assistant 角色追加到消息列表
    messages.append({"role": "assistant", "content": ai_reply})

    # 6. 删除第一条系统提示词，避免写入 JSON 文件
    messages.pop(0)

    # 7. 更新会话数据并写回 JSON 文件
    session_data["messages"] = messages
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)
    logging.info("[chat] 会话数据已保存回 JSON 文件")

    # 8. 返回 AI 回复给前端
    return ApiResponse(code=200, message="请求成功", data=ai_reply)


# 全局异常处理器：统一捕获所有未处理异常，记录错误日志并返回统一 JSON 错误格式
@app.exception_handler(Exception)
def handler_exception(request: Request, exception: Exception) -> JSONResponse:
    logging.error(f"处理异常：请求路径 {request.url}，错误信息：{exception}")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误请联系管理员", "data": None},
    )


# 挂载静态资源目录：让 /static 开头的请求自动到 static 目录下查找文件
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# 项目启动入口
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)
