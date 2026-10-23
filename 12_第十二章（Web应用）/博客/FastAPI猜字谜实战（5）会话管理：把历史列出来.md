# FastAPI猜字谜实战（5）会话管理：把历史列出来

> 这是系列的第五篇。前四篇我能开局、能聊天了，但玩过的局散落在 `sessions` 目录里，玩家根本看不见也挑不了。这一篇我补上读取和删除：把历史列出来、把某一局读回来、把不要的删掉。

## 一、只有新建是不够的

RESTful 那套我在第一篇记过：网址找东西、请求方式定动作。新建用了 `POST /api/sessions`，那读取就用 `GET`，删除就用 `DELETE`。

这一篇我要三个接口：给用户看有哪些局的列表接口、点进某一局把内容读回来的详情接口、不要的局删掉的删除接口。至于给局改名那个 `PUT`，我留到最后收官再一起补。

## 二、详情接口：把某一局整个读回来

先做最简单的，根据会话 id 把那局的完整 JSON 读出来。这里用路径参数，把 id 直接写进网址：

```
@app.get("/api/sessions/{session_id}", response_model=ApiResponse, summary="获取指定会话信息", tags=["会话管理"])
def get_session(session_id: str) -> ApiResponse:
    session_file = get_session_file_name(session_id)
    with open(session_file, "r", encoding="utf-8") as f:
        session_data = json.load(f)
    return ApiResponse(code=200, message="获取会话信息成功", data=session_data)
```

`{session_id}` 会被 fastapi 自动接进函数的参数里。我直接复用上一篇那个 `get_session_file_name` 把 id 变成文件路径，读出来整个塞进 `data` 返回。前端拿到这个就能把这局的历史消息全铺出来了。

## 三、删除接口：先确认存在再删

删除看着一行 `os.remove` 就行，但我不敢直接删。万一 id 传错了、文件根本没有，`os.remove` 会抛异常。所以我先判断存在：

```
@app.delete("/api/sessions/{session_id}", response_model=ApiResponse, summary="删除指定会话", tags=["会话管理"])
def delete_session(session_id: str) -> ApiResponse:
    session_file = get_session_file_name(session_id)
    if session_file.exists():
        os.remove(session_file)
    return ApiResponse(code=200, message="删除会话成功", data=None)
```

文件在才删，不在也不报错，照样返回成功。删除这种动作本来也没有数据要回，所以 `data` 我给 `None`。

## 四、列表接口：读目录、排序、返回对象

这个稍微麻烦。历史会话全躺在 `sessions` 目录里，一个 json 文件就是一局。我要做的是把目录里的文件挨个读一遍，提取每局的关键信息，拼成一个列表。

```
@app.get("/api/sessions", response_model=ApiResponse, summary="获取会话列表", tags=["会话管理"])
def get_sessions() -> ApiResponse:
    file_names = os.listdir(SESSIONS_DIR)
    sessions = []
    for name in file_names:
        if not name.endswith(".json"):
            continue
        session_id = os.path.splitext(name)[0]
        display_name = session_id
        messages_count = 0
        with open(SESSIONS_DIR / name, "r", encoding="utf-8") as f:
            data = json.load(f)
        display_name = data.get("name") or session_id
        messages_count = len(data.get("messages", []))
        sessions.append({"id": session_id, "name": display_name, "messages_count": messages_count})

    sessions.sort(key=lambda s: s["id"], reverse=True)
    return ApiResponse(code=200, message="获取会话列表成功", data=sessions)
```

几个我在意的点。一是文件名去掉 `.json` 后缀就是那局的 id，我用 `os.path.splitext` 拆出来。二是名字，我读文件里的 `name` 字段，可新建时 `name` 是空的，所以我用 `data.get("name") or session_id` 兜底：有名字就用名字，是空就退回显示 id。三是每条我都带上 `messages_count`，就是这局说了多少句话，用户在列表一眼能看出哪局玩得多。

最后排序我用 `sort(key=lambda s: s["id"], reverse=True)`。因为 id 本身就是时间戳，按它倒序排，最新的局就自然排到最前面了，我不用另外存时间。

## 五、列表为什么返回对象而不是光一串id

我一开始想省事，列表就返回一堆 id 字符串得了。但马上发现不够用：前端要显示历史，光有 id 它既不知道这局叫什么、也不知道这局有没有内容。

所以我把每一项都做成 `{id, name, messages_count}` 这样一个对象。前端拿到就能直接渲染成一行：名字加条数，再挂上继续和删除的按钮，点继续时用的还是那个 id。数据一次给全，前端就不用为一行历史来回发好几个请求。

## 六、跑通三件套

我在 `/docs` 里连着测了一遍：先新建几局、聊几句，再调列表接口，返回的就是按最新排前的对象数组；拿其中一个 id 调详情，那局的 `messages` 完整回来了；挑一个调删除，再列一次，那条就没了。

到这一步，后端对会话的增、查、删都齐了，就差一个改。下一篇我先不治它，先去解决另一个更烦人的东西：满屏乱飞的 `print` 调试输出。
