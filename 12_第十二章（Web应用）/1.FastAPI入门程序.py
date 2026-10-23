from fastapi import FastAPI
import uvicorn

# 创建 FastAPI 实例
app = FastAPI()


# 定义第一个 API 接口：访问根路径 /
@app.get("/")
def root():
    return {"message": "Hello World"}


# 定义第二个 API 接口：访问路径 /users
@app.get("/users")
def get_users():
    return [
        {"id": 1, "name": "张三"},
        {"id": 2, "name": "李四"},
        {"id": 3, "name": "王五"},
    ]


# 启动 FastAPI 服务
# 注意：本文件名为 1.FastAPI入门程序.py，中间含 “.”，
# 会被 uvicorn / fastapi dev 的命令行方式识别成模块分隔符而报错，
# 因此请务必使用「方式一」：在 PyCharm 中右键本文件 -> Run 直接运行。
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
