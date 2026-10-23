// 汉字弥合前端交互逻辑：负责开新局、发消息给后端、渲染聊天记录
const chatBox = document.getElementById('chat');
const inputEl = document.getElementById('msgInput');
const sendBtn = document.getElementById('sendBtn');
const newGameBtn = document.getElementById('newGameBtn');
const historyBtn = document.getElementById('historyBtn');
const historyPanel = document.getElementById('historyPanel');
const historyList = document.getElementById('historyList');

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

// ---- 历史会话功能 ----

// 从后端拉取会话 id 列表并渲染到面板
async function loadSessionList() {
    historyList.innerHTML = '<li class="history-empty">加载中…</li>';
    try {
        const resp = await fetch('/api/sessions');
        const data = await resp.json();
        if (data.code === 200) {
            renderHistoryList(data.data || []);
        } else {
            historyList.innerHTML = '<li class="history-empty">加载失败：' + data.message + '</li>';
        }
    } catch (e) {
        historyList.innerHTML = '<li class="history-empty">网络错误：' + e + '</li>';
    }
}

// 把会话对象数组渲染成可点击的列表项（每项带“重命名”“删除”按钮）
function renderHistoryList(items) {
    historyList.innerHTML = '';
    if (!items.length) {
        historyList.innerHTML = '<li class="history-empty">还没有历史会话</li>';
        return;
    }
    items.forEach((item) => {
        const li = document.createElement('li');
        li.className = 'history-item';

        const label = document.createElement('span');
        label.className = 'history-id';
        label.textContent = item.name + '（' + item.messages_count + ' 条）';
        label.title = '点击继续这局';
        label.addEventListener('click', () => resumeSession(item.id));

        const actions = document.createElement('span');
        actions.className = 'history-actions';

        const rename = document.createElement('button');
        rename.className = 'history-rename';
        rename.textContent = '重命名';
        rename.addEventListener('click', () => renameSession(item.id, item.name));

        const del = document.createElement('button');
        del.className = 'history-del';
        del.textContent = '删除';
        del.addEventListener('click', () => deleteSession(item.id));

        actions.appendChild(rename);
        actions.appendChild(del);
        li.appendChild(label);
        li.appendChild(actions);
        historyList.appendChild(li);
    });
}

// 载入指定会话的完整历史，渲染成气泡并设为当前会话，以便接着猜
async function resumeSession(id) {
    try {
        const resp = await fetch('/api/sessions/' + encodeURIComponent(id));
        const data = await resp.json();
        if (data.code === 200) {
            sessionId = id;
            chatBox.innerHTML = '';
            const msgs = (data.data && data.data.messages) || [];
            if (msgs.length) {
                msgs.forEach((m) => addBubble(m.role === 'assistant' ? 'ai' : 'me', m.content));
                addBubble('ai', '— 已载入这局历史，继续猜吧！ —');
            } else {
                addBubble('ai', '这局还没有记录，从这里开始猜吧～');
            }
            hideHistory();
            inputEl.focus();
        } else {
            addBubble('ai', '载入失败：' + data.message);
        }
    } catch (e) {
        addBubble('ai', '网络错误：' + e);
    }
}

// 删除指定会话（复用后端 DELETE 接口），删后刷新列表
async function deleteSession(id) {
    try {
        const resp = await fetch('/api/sessions/' + encodeURIComponent(id), { method: 'DELETE' });
        const data = await resp.json();
        if (data.code === 200) {
            if (id === sessionId) sessionId = null; // 删的是当前局，清掉 id 避免误发
            loadSessionList();
        } else {
            addBubble('ai', '删除失败：' + data.message);
        }
    } catch (e) {
        addBubble('ai', '网络错误：' + e);
    }
}

function showHistory() {
    historyPanel.classList.remove('hidden');
    loadSessionList();
}

// 重命名指定会话：弹出输入框取名，调用 PUT 接口后刷新列表
async function renameSession(id, currentName) {
    const input = prompt('给这局起个名字：', currentName === id ? '' : currentName);
    if (input === null) return; // 用户取消
    const newName = input.trim();
    if (!newName) {
        addBubble('ai', '名字不能为空，未做修改。');
        return;
    }
    try {
        const resp = await fetch('/api/sessions/' + encodeURIComponent(id), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName }),
        });
        const data = await resp.json();
        if (data.code === 200) {
            loadSessionList(); // 刷新列表显示新名字
        } else {
            addBubble('ai', '重命名失败：' + data.message);
        }
    } catch (e) {
        addBubble('ai', '网络错误：' + e);
    }
}

function hideHistory() {
    historyPanel.classList.add('hidden');
}

function toggleHistory() {
    if (historyPanel.classList.contains('hidden')) {
        showHistory();
    } else {
        hideHistory();
    }
}

// 事件绑定
sendBtn.addEventListener('click', sendMessage);
inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage();
});
newGameBtn.addEventListener('click', () => { hideHistory(); startNewGame(); });
historyBtn.addEventListener('click', toggleHistory);

// 打开页面：优先继续最近一局（无历史才新开），避免每次刷新都新建空会话
async function initOnLoad() {
    try {
        const resp = await fetch('/api/sessions');
        const data = await resp.json();
        const sessions = (data.code === 200 && data.data) ? data.data : [];
        if (sessions.length) {
            await resumeSession(sessions[0].id); // 列表已按时间倒序，第一项为最近一局
        } else {
            await startNewGame();
        }
    } catch (e) {
        await startNewGame();
    }
}

initOnLoad();
