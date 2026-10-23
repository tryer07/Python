# FastAPI猜字谜实战（7）前端页面：让它像游戏一样点着玩

> 这是系列的第七篇。后端到上一篇已经能开局、能聊天了，可我只能对着 `/docs` 手动填参数、看 JSON，一点玩的感觉都没有。这一篇我用 HTML、CSS、JS 给这个项目做张脸，让玩家在浏览器里像聊天一样把游戏玩了。

## 一、前端就仨文件，各管一块

我在 `static` 目录下放了三个文件。`index.html` 管结构，就是页面上有哪些东西；`css/style.css` 管长相，颜色圆角那些；`js/game.js` 管行为，点了按钮干啥。这三个通过上一篇挂载好的 `/static` 路径被后端端出来，浏览器就能加载它们。

## 二、index.html：一个聊天的壳子

页面我照着聊天软件的样子搭。顶上放标题和一个新游戏按钮，中间一大块用来显示消息，底下放输入框和发送按钮：

```
<div class="app">
    <header class="topbar">
        <h1>汉字弥合 · 猜字谜</h1>
        <button id="newGameBtn" class="new-btn">新游戏</button>
    </header>
    <main id="chat" class="chat"></main>
    <footer class="inputbar">
        <input id="msgInput" type="text" placeholder="输入你的答案，回车发送">
        <button id="sendBtn" class="send-btn">发送</button>
    </footer>
</div>
<script src="/static/js/game.js"></script>
```

中间那个 `chat` 区我一开始是空的，消息都靠 JS 往里塞。我给每个要操作的元素都留了 `id`，比如 `msgInput`、`sendBtn`，JS 就靠这些 id 找到它们。

## 三、style.css：让它别太素

我不懂设计，就套了个深色聊天风。整个背景一层深紫渐变，中间框成一块手机屏大小的区域。聊天区我给成可滚动的纵向弹性布局：

```
.chat {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.bubble {
    max-width: 75%;
    padding: 10px 14px;
    border-radius: 14px;
    white-space: pre-wrap;
}

.row.me .bubble { background: #6c5ce7; }
.row.ai .bubble { background: #362a4d; }
```

关键是每条消息我包一层 `row`，我发的 `.row.me` 靠右、紫色气泡，AI 的 `.row.ai` 靠左、暗紫气泡。那个 `white-space: pre-wrap` 是我特意加的，为的是 AI 回复里的换行能正常显示，不然全挤成一行。

## 四、game.js：进来先开一局

交互全在 JS 里。页面一打开我就自动请求后端新建一局，把返回的会话 id 存起来，后面发消息都带上它：

```
let sessionId = null;

async function startNewGame() {
    const resp = await fetch('/api/sessions', { method: 'POST' });
    const data = await resp.json();
    if (data.code === 200) {
        sessionId = data.data;
        chatBox.innerHTML = '';
        addBubble('ai', '欢迎来到汉字弥合！想玩什么难度？');
    }
}
```

我为什么老盯着 `data.code === 200`？因为第三篇定的那个三件套统一格式在这用上了：前端只要认这一个判断，成功取 `data`、失败弹 `message`，所有接口都一个套路。

## 五、发消息：用fetch把话递给后端

玩家在输入框打字、点发送，我就把这句话连同会话 id POST 给聊天接口：

```
async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text || !sessionId) return;

    addBubble('me', text);
    inputEl.value = '';

    const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    const data = await resp.json();
    if (data.code === 200) {
        addBubble('ai', data.data);
    }
}
```

我先把玩家这句渲染成一个靠右的气泡、清空输入框，再发请求。POST 带 JSON 有固定三步：`method` 写 POST，`headers` 声明我发的是 JSON，`body` 用 `JSON.stringify` 把对象转成字符串。后端第四篇那个接口读的就是这俩字段。等它回来，我把 AI 的回复渲染成靠左气泡。

大模型响应有快有慢，中间那段空窗期我在发送时先插一个柯灵正在思考的占位气泡，回复到了再把它删掉，不然玩家会以为页面卡死了。发送按钮和输入框这段时间我也临时禁用，防止连点发重。

## 六、渲染气泡时我踩过的一个安全点

我往气泡里写字，用的是 `bubble.textContent = text`，不是 `innerHTML`。

这一开始是我图省事，后来才明白这差别很关键。`innerHTML` 会把字符串当 HTML 解析，万一 AI 回复或者玩家输入里带了 `<script>` 之类，就真被当代码执行了，这是 XSS。`textContent` 只当纯文本处理，再把换行交给 CSS 的 `pre-wrap` 去显示。我又不是要给消息排版富文本，没必要冒这个险。

到这儿，页面能玩了：一进来自动开局，打字发送，AI 回话，气泡左右分开。可还有几个体验毛病没治：AI 回复带乱码符号、每次刷新都新开一局把我之前的进度顶掉、也找不到历史局。这些我攒到收官那篇一起收拾。
