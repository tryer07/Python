// 云荒录 · 文字冒险RPG 前端逻辑
// 负责：拉取职业、建卡开局、发送行动、渲染剧情、同步状态面板

const API = ""; // 同源，无需写死地址

// ---------- 全局状态 ----------
let sessionId = "";
let selectedClass = "";
let charName = "";

// ---------- DOM 引用 ----------
const $ = (id) => document.getElementById(id);
const createScreen = $("create-screen");
const gameScreen = $("game-screen");
const classList = $("class-list");
const btnStart = $("btn-start");
const storyLog = $("story-log");
const actionInput = $("action-input");
const btnSend = $("btn-send");
const loadingHint = $("loading-hint");

// ---------- 工具：清洗 AI 回复里可能残留的 Markdown 符号 ----------
function cleanMarkdown(text) {
    return text
        .replace(/^#{1,6}\s*/gm, "")   // 去掉行首 # 标题符号
        .replace(/\*\*(.+?)\*\*/g, "$1") // 去掉加粗
        .replace(/\*(.+?)\*/g, "$1")     // 去掉斜体
        .replace(/`/g, "");              // 去掉反引号
}

// ---------- 工具：安全创建气泡节点（用 textContent 防 XSS）----------
function appendBubble(role, text, whoLabel) {
    const bubble = document.createElement("div");
    bubble.className = "bubble " + (role === "user" ? "user" : "gm");
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = whoLabel;
    const body = document.createElement("div");
    body.textContent = text;
    bubble.appendChild(who);
    bubble.appendChild(body);
    storyLog.appendChild(bubble);
    storyLog.scrollTop = storyLog.scrollHeight;
    return bubble;
}

// ---------- 渲染状态面板 ----------
function renderStatus(character) {
    const status = character.status;
    $("char-title").textContent = `${character.name} · ${character.class}`;
    const hpRatio = status.max_hp > 0 ? status.hp / status.max_hp : 0;
    const fill = $("hp-fill");
    fill.style.width = Math.max(0, Math.min(100, hpRatio * 100)) + "%";
    fill.style.background = hpRatio > 0.3 ? "var(--hp-good)" : "var(--hp-bad)";
    $("hp-text").textContent = `${status.hp} / ${status.max_hp}`;
    $("attack-text").textContent = status.attack;
    $("gold-text").textContent = status.gold;

    const list = $("items-list");
    list.innerHTML = "";
    if (status.items.length === 0) {
        const li = document.createElement("li");
        li.textContent = "";
        list.appendChild(li);
    } else {
        status.items.forEach((item) => {
            const li = document.createElement("li");
            li.textContent = item;
            list.appendChild(li);
        });
    }
}

// ---------- 初始化：加载职业列表 ----------
async function loadClasses() {
    try {
        const resp = await fetch(API + "/api/classes", { method: "POST" });
        const result = await resp.json();
        if (result.code !== 200) return;
        classList.innerHTML = "";
        result.data.forEach((cls) => {
            const card = document.createElement("div");
            card.className = "class-card";
            card.dataset.name = cls.name;
            const name = document.createElement("div");
            name.className = "class-name";
            name.textContent = cls.name;
            const desc = document.createElement("div");
            desc.className = "class-desc";
            desc.textContent = cls.desc;
            card.appendChild(name);
            card.appendChild(desc);
            card.addEventListener("click", () => selectClass(cls.name, card));
            classList.appendChild(card);
        });
    } catch (e) {
        $("create-error").textContent = "无法连接服务器，请确认 main.py 已启动";
    }
}

function selectClass(name, card) {
    selectedClass = name;
    document.querySelectorAll(".class-card").forEach((c) => c.classList.remove("selected"));
    card.classList.add("selected");
    checkStartReady();
}

function checkStartReady() {
    charName = $("char-name").value.trim();
    btnStart.disabled = !(charName.length > 0 && selectedClass.length > 0);
}

// ---------- 开局 ----------
async function startGame() {
    btnStart.disabled = true;
    $("create-error").textContent = "";
    btnStart.textContent = "主持人正在推演开场…";
    try {
        const resp = await fetch(API + "/api/game/new", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: charName, character_class: selectedClass }),
        });
        const result = await resp.json();
        if (result.code !== 200) {
            $("create-error").textContent = result.message || "开局失败";
            btnStart.disabled = false;
            btnStart.textContent = "踏入云荒";
            return;
        }
        sessionId = result.data.session_id;
        createScreen.classList.add("hidden");
        gameScreen.classList.remove("hidden");
        storyLog.innerHTML = "";
        renderStatus(result.data.character);
        appendBubble("gm", cleanMarkdown(result.data.story), "主持人");
        actionInput.focus();
    } catch (e) {
        $("create-error").textContent = "请求失败：" + e.message;
        btnStart.disabled = false;
        btnStart.textContent = "踏入云荒";
    } finally {
        loadingHint.classList.add("hidden");
    }
}

// ---------- 发送行动 ----------
async function sendAction() {
    const text = actionInput.value.trim();
    if (!text || !sessionId) return;

    actionInput.value = "";
    btnSend.disabled = true;
    appendBubble("user", text, charName);
    loadingHint.classList.remove("hidden");

    try {
        const resp = await fetch(API + "/api/game/action", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, message: text }),
        });
        const result = await resp.json();
        if (result.code === 200) {
            appendBubble("gm", cleanMarkdown(result.data.story), "主持人");
            renderStatus(result.data.character);
            // 角色阵亡提示（HP 归零）
            if (result.data.character.status.hp <= 0) {
                appendBubble("gm", "你的冒险到此为止。点击左下角「放弃冒险」可重新开局。", "命运");
            }
        } else {
            appendBubble("gm", "（出了点问题：" + result.message + "）", "系统");
        }
    } catch (e) {
        appendBubble("gm", "（与主持人的连接中断了：" + e.message + "）", "系统");
    } finally {
        loadingHint.classList.add("hidden");
        btnSend.disabled = false;
        actionInput.focus();
    }
}

// ---------- 放弃冒险：回到建卡界面 ----------
function quitGame() {
    if (!confirm("确定要放弃当前冒险、回到建卡界面吗？")) return;
    sessionId = "";
    selectedClass = "";
    gameScreen.classList.add("hidden");
    createScreen.classList.remove("hidden");
    document.querySelectorAll(".class-card").forEach((c) => c.classList.remove("selected"));
    $("char-name").value = "";
    btnStart.disabled = true;
    btnStart.textContent = "踏入云荒";
}

// ---------- 事件绑定 ----------
$("char-name").addEventListener("input", checkStartReady);
btnStart.addEventListener("click", startGame);
btnSend.addEventListener("click", sendAction);
$("btn-quit").addEventListener("click", quitGame);
actionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendAction();
    }
});

// ---------- 页面加载即拉取职业 ----------
loadClasses();
