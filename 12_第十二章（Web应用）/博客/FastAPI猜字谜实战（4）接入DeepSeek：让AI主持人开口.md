# FastAPI猜字谜实战（4）接入DeepSeek：让AI主持人开口

> 这是系列的第四篇。上一篇我把每局游戏的空壳存下来了，但里面 `messages` 是空的，AI 还不会说话。这一篇我接上大模型 DeepSeek，让主持人柯灵真正出题、判题，还能记住我们聊到哪了。

## 一、先想清楚：大模型到底吃什么

我一开始以为调大模型就是把用户那句话发过去就行，后来发现不是。大模型是无状态的，它不记得上一句，每次都得你把该知道的背景全塞给它。

所以调用它时我发的是一个列表，叫 `messages`，里面每条都是一个带 `role` 和 `content` 的字典。`role` 有三种：`system` 是我给它的总设定，`user` 是玩家说的话，`assistant` 是 AI 之前回过的话。它靠把历史全带上，才制造出一种它在记住的错觉。

## 二、给AI立人设：SYSTEM_PROMPT

柯灵该是什么脾气、该怎么出题判题，我写在一段系统提示词里，做成一个全局变量：

```
SYSTEM_PROMPT = """你是一位汉字猜字谜游戏的主持人，名叫柯灵。
- 每次给一个字谜，难度先询问用户，不重复出题。
- 你必须牢牢记住当前这道题的谜底，用户猜错就判错，绝不因为用户说得自信就改口。
- 用户猜错时先给一点提示，不要直接公布谜底。
- 语气亲切活泼，回复尽量简短。"""
```

这段我放在函数外面，因为每次调用都要用它，且它是恒定不变的人设。判题那条是我特意强调的，不然 AI 特别容易被玩家忽悠着承认错误答案。

## 三、装openai库、配密钥

DeepSeek 兼容 openai 的调用格式，所以我直接 `pip install openai`，然后建一个客户端：

```
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)
```

这个 `api_key` 我死活没写死在代码里，而是从环境变量读。因为密钥一旦硬编码，我传代码或者截图时就泄露了。我把密钥配在系统环境变量 `DEEPSEEK_API_KEY` 里，代码只负责去取。`base_url` 告诉它请求发到 DeepSeek 的服务器，而不是 openai 官方。

## 四、组装messages：背景+历史+这一次

到了对话接口里，我最核心的动作就是把三样东西按顺序拼成 `messages`：

```
@app.post("/api/chat", response_model=ApiResponse, summary="与AI柯灵猜字谜", tags=["AI 对话"])
def chat(request: ChatRequest) -> ApiResponse:
    session_file = get_session_file_name(request.session_id)
    with open(session_file, "r", encoding="utf-8") as f:
        session_data = json.load(f)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(session_data["messages"])
    messages.append({"role": "user", "content": request.message})
```

第一步先根据会话 id 把那局的历史 JSON 读出来。然后我拼消息：第一条永远是系统人设，中间把历史消息 `extend` 进来，最后把玩家这一次说的话作为 `user` 加上。顺序不能乱，人设必须在最前面压着。

那个 `get_session_file_name` 是个小工具，把会话 id 变成 `sessions/那个id.json` 的路径，好几个接口都要用，我就抽出来单独写。

## 五、调用并解析回复

拼好消息就发给大模型：

```
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=False,
    )
    ai_reply = response.choices[0].message.content
```

`stream=False` 是我先不做打字机效果，一次性把整段回复拿回来。拿到之后，真正的答案文字藏在 `response.choices[0].message.content` 里，我把这段取出来就是柯灵这轮的回复。

## 六、让它记住进度：一存一删是关键

光回一句不够，得让这轮的问答也存进历史，下轮才接得上。这里有个我琢磨了才懂的细节：

```
    messages.append({"role": "assistant", "content": ai_reply})
    messages.pop(0)
    session_data["messages"] = messages
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    return ApiResponse(code=200, message="请求成功", data=ai_reply)
```

我先把 AI 这句回复以 `assistant` 角色追加进 `messages`，这样历史就完整了。但紧接着我 `pop(0)` 把第一条系统提示词删掉，再写回文件。

为什么要删？因为系统人设是我每次调用时现加的，根本不需要存进文件。要是把它也存下来，文件会越来越臃肿，而且下轮我又加一遍，就重复了。所以落盘的历史里只有 user 和 assistant 交替，干净又能续得上。

我实测连猜了两轮，JSON 里确实累积了四条消息、且没有 system 那条，进度也接得上。到这一步游戏有灵魂了。不过我发现还有个毛病：AI 回复偶尔夹带 Markdown 符号，页面看着脏兮兮的，这个留到最后收官那篇再治。而眼下更该补的，是历史会话的增删改查，下一篇就来做。
