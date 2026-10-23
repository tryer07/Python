// 汉字弥合前端交互逻辑：负责开新局、发消息给后端、渲染聊天记录
const chatBox = document.getElementById('chat');
const inputEl = document.getElementById('msgInput');
const sendBtn = document.getElementById('sendBtn');
const newGameBtn = document.getElementById('newGameBtn');

let sessionId = null; // 当前会话 id，由后端“新建会话”接口返回

// 清除 AI 回复中的 Markdown 标记符号（#、*、反引号、加粗等），让纯文本气泡更干净
function cleanMarkdown(text) {
    if (!text) return text;
    return text
        .replace(/```[\s\S]*?```/g, '')            // 多行代码块
        .replace(/`([^`]*)`/g, '$1')              // 行内代码 `x`
        .replace(/\*\*([^*]*)\*\*/g, '$1')        // 加粗 **x**
        .replace(/(^|\n)[ \t]*#{1,6}[ \t]*/g, '$1') // 行首 # 标题
        .replace(/(^|\n)[ \t]*[*-][ \t]+/g, '$1')  // 行首 * 或 - 列表符
        .replace(/[ \t]+\n/g, '\n')
        .trim();
}

// 追加一条聊天气泡；role 为 'ai' 或 'me'
function addBubble(role, text) {
    const row = document.createElement('div');
    row.className = 'row ' + role;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    // AI 回复先洗一遍 Markdown 符号；textContent 仍防 XSS 并保留换行
    bubble.textContent = role === 'ai' ? cleanMarkdown(text) : text;

    row.appendChild(bubble);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight; // 自动滚到底部
}

// 请求后端新建会话，成功后重置界面
async function startNewGame() {
    try {
        const resp = await fetch('/api/sessions', { method: 'POST' });
        const data = await resp.json();
        if (data.code === 200) {
            sessionId = data.data;
            chatBox.innerHTML = ''; // 清空旧记录
            addBubble('ai', '欢迎来到汉字弥合！我是主持人柯灵～ 想玩什么难度？简单、中等还是地狱？');
            inputEl.focus();
        } else {
            addBubble('ai', '新建会话失败：' + data.message);
        }
    } catch (e) {
        addBubble('ai', '网络错误，请确认后端服务已启动：' + e);
    }
}

// 发送用户消息给后端 AI 对话接口
async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text || !sessionId) {
        if (!sessionId) {
            addBubble('ai', '还没有会话，请先点“新游戏”。');
        }
        return;
    }

    addBubble('me', text);
    inputEl.value = '';
    sendBtn.disabled = true;
    inputEl.disabled = true;

    // 显示“正在思考”占位气泡
    const loading = document.createElement('div');
    loading.className = 'row ai';
    loading.innerHTML = '<div class="bubble thinking">柯灵正在思考…</div>';
    chatBox.appendChild(loading);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, message: text }),
        });
        const data = await resp.json();
        chatBox.removeChild(loading); // 移除“正在思考”

        if (data.code === 200) {
            addBubble('ai', data.data);
        } else {
            addBubble('ai', '出错了：' + data.message);
        }
    } catch (e) {
        chatBox.removeChild(loading);
        addBubble('ai', '请求失败：' + e);
    } finally {
        sendBtn.disabled = false;
        inputEl.disabled = false;
        inputEl.focus();
    }
}

// 事件绑定
sendBtn.addEventListener('click', sendMessage);
inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage();
});
newGameBtn.addEventListener('click', startNewGame);

// 打开页面即自动开一局
startNewGame();
