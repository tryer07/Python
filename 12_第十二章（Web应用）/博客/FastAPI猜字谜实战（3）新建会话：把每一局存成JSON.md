# FastAPI猜字谜实战（3）新建会话：把每一局存成JSON

> 这是系列的第三篇。骨架搭好了，这一篇我要让后端学会一件事：玩家每开一局猜字谜，都在磁盘上留下一份记录。这就是 RESTful 里 POST 干的新建，也是整个项目存数据的起点。

## 一、先定一个规矩：所有接口都长一个样

在写第一个真正的接口之前，我先给自己立了个规矩：不管哪个接口，返回给前端的结构都统一成三个字段，状态码、提示信息、数据。

```
from pydantic import BaseModel, Field
from typing import Any

class ApiResponse(BaseModel):
    code: int = Field(title="状态码", description="200 表示成功")
    message: str = Field(title="提示信息")
    data: Any = Field(title="返回数据")
```

这么做的好处是，前端只要认这一个格式就行：先看 `code` 是不是 200，是就取 `data`，不是就弹 `message`。后面我写的每个接口都会声明 `response_model=ApiResponse`，等于给自己套了个模子，谁也别跑偏。

## 二、一局猜字谜到底要存什么

我把它叫会话。一局游戏从开出来到结束，无非要记住三样东西：这一局叫什么编号、玩家和 AI 说过哪些话、还有个留给玩家自己起的名字。

```
session_data = {
    "current_session": session_id,
    "name": "",
    "messages": [],
}
```

新建的时候 `name` 我先留空，`messages` 是个空列表，话还没说呢。这个字典存成磁盘上的一个 JSON 文件，一局一个文件，互不干扰。

## 三、给每一局生成一个不会撞车的编号

要一局一个文件，就得有个独一无二的文件名。我一开始直接用时间精确到秒，后来发现个问题：一秒内连点两下新建，两局的时间一模一样，后面那局会把前面那局的文件盖掉。

所以我把编号精确到微秒：

```
from datetime import datetime

def generate_session_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
```

`%f` 是微秒，六位。这样就算同一秒新建好几局，编号也不会重。像 `2026-10-23_15-30-12_482913` 这种，既是文件名，又带着时间顺序，后面列历史的时候我直接按它排倒序就是最新的在最前。

## 四、把新建会话接口写出来

前面三样凑齐，新建接口就顺理成章了。用 `@app.post`，因为我要的是新建：

```
import json
import os

@app.post("/api/sessions", response_model=ApiResponse, summary="新建猜字谜会话", tags=["会话管理"])
def create_session() -> ApiResponse:
    session_id = generate_session_id()
    session_data = {"current_session": session_id, "name": "", "messages": []}

    session_file = SESSIONS_DIR / f"{session_id}.json"
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    return ApiResponse(code=200, message="创建会话成功", data=session_id)
```

我在启动时先确保 `sessions` 目录存在，不存在就 `os.makedirs` 建一个，不然写文件会报错。

`json.dump` 里那两个参数是我特意加的：`ensure_ascii=False` 让中文正常显示、不会变成一堆 `\uXXXX`；`indent=2` 让存下来的 JSON 有缩进，我打开文件能看懂。

## 五、跑一遍，看文件真的落下来了

我在 `/docs` 里点这个新建接口，返回 `code: 200`，`data` 是一串带微秒的编号。然后我去项目目录下的 `sessions` 文件夹一看，多出了一个 `那个编号.json`，打开里面就是我预期的结构，`messages` 是个空列表。

到这一步我确认了：后端真的能把我这一局存到磁盘上了。而且我注意到，新建完只是有了空壳，里面的 `messages` 还是空的，游戏还没有灵魂，AI 还不会说话。

## 六、接下来让 AI 开口

存数据的架子有了，可这一局里该出题、该判对错的那个主持人还没上线。下一篇我就接上大模型 DeepSeek，让这个后端真正能思考，把玩家说的话存进 `messages`、再把 AI 的回复也存回去。
