from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
import uvicorn

# 以 main.py 自身所在目录为基准定位 static，避免因运行工作目录不同而找不到文件
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# 创建 FastAPI 实例
app = FastAPI(title="汉字弥合")


# 访问首页：返回 static/index.html 页面，而不是 JSON
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


# 挂载静态资源目录：让 /static 开头的请求自动到 static 目录下查找文件
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# 项目启动入口
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
