import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import FileResponse
import uvicorn

# 以 main.py 自身所在目录为基准定位资源，避免因运行工作目录不同而找不到文件
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SESSIONS_DIR = BASE_DIR / "sessions"

# 创建 sessions 目录：不存在则新建，用于保存每次绘画的会话数据
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

# 创建 FastAPI 实例
app = FastAPI(title="汉字弥合")


# 统一响应模型：所有接口都按 code / message / data 三个字段返回
class ApiResponse(BaseModel):
    code: int
    message: str
    data: Any


# 基于当前时间生成绘画（会话）标识
def generate_session_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


# 访问首页：返回 static/index.html 页面，而不是 JSON
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


# 新建绘画接口：生成会话标识，初始化会话数据并保存到 JSON 文件
@app.post("/api/sessions", response_model=ApiResponse)
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


# 挂载静态资源目录：让 /static 开头的请求自动到 static 目录下查找文件
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# 项目启动入口
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
