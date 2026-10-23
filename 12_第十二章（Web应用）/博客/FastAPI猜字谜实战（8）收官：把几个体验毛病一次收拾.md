# FastAPI猜字谜实战（8）收官：把几个体验毛病一次收拾

> 这是系列的最后一篇。功能都齐了，页面也能玩了，但攒了几个硌应的小毛病没治：每次得手动开浏览器、AI 回复带乱码符号、一进页面就顶掉我上局的进度、历史全是时间戳分不清。这一篇挨个收拾，项目就算落地了。

## 一、不想每次手动敲地址，让它自己弹出来

最烦的是每次玩都得先跑 `main.py`、再切到浏览器输 `localhost:8000`。能不能一启动就自动把页面打开？

能。Python 自带 `webbrowser`，我配合定时器延后一下就成：

```
import threading
import webbrowser

if __name__ == "__main__":
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8000/")).start()
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)
```

关键是那个延迟。服务是 `uvicorn.run` 才起来的，我要是紧接着就 `webbrowser.open`，浏览器抢在服务监听之前打开，会显示连不上。所以我用 `threading.Timer` 把开浏览器这件事推后 1.5 秒，等后厨把门支起来了再叫客人。这样我直接 Run `main.py`，终端服务和浏览器页面一起就位。

## 二、AI回复带一堆井号星号，看着太脏

大模型爱用 Markdown 排版，动不动给我冒出 `# 标题`、`**加粗**` 这些符号，可我的气泡是纯文本，这些符号就原样杵在那，脏兮兮。

我上了两道防线。第一道从源头治，在系统提示词里明令禁止：

```
- 只用纯文本回复，绝对不要使用任何 Markdown 标记（如 # 井号标题、* 星号加粗、反引号、- 列表符号等）。
```

但 prompt 不是百分百听话，偶尔还是漏。所以第二道在前端兜底，渲染 AI 回复前先用正则把这些符号洗掉：

```
function cleanMarkdown(text) {
    if (!text) return text;
    return text
        .replace(/```[\s\S]*?```/g, '')
        .replace(/`([^`]*)`/g, '$1')
        .replace(/\*\*([^*]*)\*\*/g, '$1')
        .replace(/(^|\n)[ \t]*#{1,6}[ \t]*/g, '$1')
        .replace(/(^|\n)[ \t]*[*-][ \t]+/g, '$1')
        .trim();
}
```

我在 `addBubble` 里，凡是 AI 的消息就先过一遍 `cleanMarkdown` 再显示，我的消息不用洗。源头约束加末端兜底，双保险，页面就干净了。

## 三、一进页面就顶掉上局进度，改成接着玩

第七篇我写的是页面一加载就 `startNewGame` 新开一局。可我想续玩上一局时，一刷新全没了，特别气人。

我改了加载逻辑：进来先问后端要历史列表，有历史就自动载入最近那一局，实在没有才新开。

```
async function initOnLoad() {
    const resp = await fetch('/api/sessions');
    const data = await resp.json();
    const sessions = (data.code === 200 && data.data) ? data.data : [];
    if (sessions.length) {
        await resumeSession(sessions[0].id);
    } else {
        await startNewGame();
    }
}
```

这里能直接拿 `sessions[0]` 当最近一局，靠的是第五篇列表接口已经按时间倒序排好了，头一个就是最新。`resumeSession` 会请求那局的详情、把历史消息一条条铺成气泡，我接着往下猜就行。想开新局我留了新游戏按钮，主动点它才是新开。

## 四、历史全是时间戳分不清，给它加个名字

历史一多全是 `2026-10-23_15-30-12` 这种，根本记不住哪个是哪局。第三篇我存了个空 `name` 字段，就是留着这时候用的。

后端我补了个 `PUT` 接口专门改名。改名前我先判断这局在不在，不在就返回 404 提示，而不是抛异常：

```
@app.put("/api/sessions/{session_id}", response_model=ApiResponse, summary="重命名会话", tags=["会话管理"])
def rename_session(session_id: str, request: RenameRequest) -> ApiResponse:
    session_file = get_session_file_name(session_id)
    if not session_file.exists():
        return ApiResponse(code=404, message="会话不存在，无法重命名", data=None)

    with open(session_file, "r", encoding="utf-8") as f:
        session_data = json.load(f)
    session_data["name"] = request.name
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)
    return ApiResponse(code=200, message="重命名成功", data=None)
```

我只改 `name` 这一个字段，读出来改完再原样写回，`messages` 一点不动。前端历史列表每项挂个重命名按钮，弹个框让玩家输新名字，POST 上去成功后刷新列表就显示新名了。这一来 RESTful 那四个动作 GET 查、POST 增、PUT 改、DELETE 删，我总算在这项目里凑齐了。

## 五、AI偶尔蹦几个外语乱码词，调下温度

有个小毛病我注意了一阵：AI 偶尔会莫名其妙蹦出 first、obg 这种外语碎词，很出戏。这是模型采样太跳脱导致的，跟提示词关系不大。

我调了调用大模型时的 `temperature`，从偏高的 1.5 降到 1.2：

```
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    stream=False,
    temperature=1.2,
)
```

这个值管的是回复的随机程度，越高越放飞、越低越稳。猜字谜这种要它老老实实出题判题的活，我不需要它太有创意，降一点之后中文输出明显稳了，乱码词基本不蹦了。

## 六、折腾完回头看这八篇

从第一篇那六行 Hello World，到这最后一篇的这些细碎打磨，一个能在浏览器里点着玩的 AI 猜字谜应用，就这么一步步立起来了。

我最大的体会是，这活真不是我想象中的高深。前后端怎么分工、数据怎么存成 JSON、大模型怎么接、页面怎么点着玩，拆开看每一步都挺朴素，就是一个接一个地把痛点填上。我这一路的顺序也一直没乱：先把后端接口写出来、拿 `/docs` 点通，再去做前端把接口接上玩，最后回头收拾那些体验毛病。要是反过来先搭花架子，我多半早就绕晕在前后端那条线里了。
