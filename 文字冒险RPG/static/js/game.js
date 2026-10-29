// 废土余生 · 末世文字冒险RPG 前端逻辑
// 负责：拉取职业、建卡开局、发送行动、渲染剧情、同步状态、死亡拦截、读取存档续玩

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
const btnLoad = $("btn-load");
const saveList = $("save-list");
const storyLog = $("story-log");
const actionInput = $("action-input");
const btnSend = $("btn-send");
const loadingHint = $("loading-hint");
const deathPanel = $("death-panel");

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

// ---------- 死亡态 UI：显示死亡面板并锁住输入 ----------
function setDead(dead) {
    deathPanel.classList.toggle("hidden", !dead);
    actionInput.disabled = dead;
    btnSend.disabled = dead;
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

// ---------- 进入对局界面并复位状态 ----------
function enterGame(character) {
    createScreen.classList.add("hidden");
    gameScreen.classList.remove("hidden");
    storyLog.innerHTML = "";
    charName = character.name;
    renderStatus(character);
    setDead(false);
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
            btnStart.textContent = "踏入废土";
            return;
        }
        sessionId = result.data.session_id;
        enterGame(result.data.character);
        appendBubble("gm", cleanMarkdown(result.data.story), "主持人");
        actionInput.focus();
    } catch (e) {
        $("create-error").textContent = "请求失败：" + e.message;
        btnStart.disabled = false;
        btnStart.textContent = "踏入废土";
    }
    btnStart.disabled = false;
    btnStart.textContent = "踏入废土";
}

// ---------- 发送行动 ----------
async function sendAction() {
    const text = actionInput.value.trim();
    if (!text || !sessionId || actionInput.disabled) return;

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
            if (result.data.dead) {
                appendBubble("gm", "你倒下了，视野渐渐暗下去……这一局到此为止。", "命运");
                setDead(true);
            }
        } else if (result.code === 409) {
            // 后端死亡拦截：本存档角色已阵亡
            setDead(true);
        } else {
            appendBubble("gm", "（出了点问题：" + result.message + "）", "系统");
        }
    } catch (e) {
        appendBubble("gm", "（与主持人的连接中断了：" + e.message + "）", "系统");
    } finally {
        loadingHint.classList.add("hidden");
        if (!actionInput.disabled) {
            btnSend.disabled = false;
            actionInput.focus();
        }
    }
}

// ---------- 读取存档列表（在建卡界面展开/收起）----------
async function toggleSaveList() {
    if (!saveList.classList.contains("hidden")) {
        saveList.classList.add("hidden");
        return;
    }
    saveList.classList.remove("hidden");
    saveList.textContent = "加载存档中…";
    try {
        const resp = await fetch(API + "/api/saves");
        const result = await resp.json();
        saveList.innerHTML = "";
        if (result.code !== 200 || !result.data.length) {
            const empty = document.createElement("div");
            empty.className = "save-empty";
            empty.textContent = "暂无存档";
            saveList.appendChild(empty);
            return;
        }
        result.data.forEach((s) => {
            const item = document.createElement("div");
            item.className = "save-item";
            const dead = Number(String(s.hp).split("/")[0]) <= 0;
            const info = document.createElement("div");
            info.className = "save-info";
            const nameEl = document.createElement("span");
            nameEl.className = "save-name";
            nameEl.textContent = `${s.name} · ${s.class}${dead ? " ☠" : ""}`;
            const metaEl = document.createElement("span");
            metaEl.className = "save-meta";
            metaEl.textContent = `HP ${s.hp} · ${s.turns} 回合`;
            info.appendChild(nameEl);
            info.appendChild(metaEl);
            item.appendChild(info);

            const delBtn = document.createElement("button");
            delBtn.className = "save-del";
            delBtn.type = "button";
            delBtn.title = "删除这份存档";
            delBtn.textContent = "删除";
            // 阻止冒泡，否则点删除会顺带进入这局游戏
            delBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                deleteSave(s.session_id, s.name, item);
            });
            item.appendChild(delBtn);

            item.addEventListener("click", () => resumeSave(s.session_id));
            saveList.appendChild(item);
        });
    } catch (e) {
        saveList.textContent = "读取失败：" + e.message;
    }
}

// ---------- 删除某份存档 ----------
async function deleteSave(sid, name, itemEl) {
    if (!confirm(`确定删除「${name}」这份存档吗？删了就找不回来了。`)) return;
    try {
        const resp = await fetch(API + "/api/game/" + encodeURIComponent(sid), { method: "DELETE" });
        const result = await resp.json();
        if (result.code !== 200) {
            alert(result.message || "删除失败");
            return;
        }
        if (itemEl) itemEl.remove();
        // 如果删的是当前正在玩的这局，直接退回建卡界面
        if (sessionId === sid) {
            appendBubble("gm", "这份存档被删掉了，这一局到此结束。", "系统");
            quitToCreate(false);
        }
        if (!saveList.querySelector(".save-item")) {
            saveList.innerHTML = "";
            const empty = document.createElement("div");
            empty.className = "save-empty";
            empty.textContent = "暂无存档";
            saveList.appendChild(empty);
        }
    } catch (e) {
        alert("删除失败：" + e.message);
    }
}

// ---------- 续玩某个存档 ----------
async function resumeSave(sid) {
    try {
        const resp = await fetch(API + "/api/game/" + sid);
        const result = await resp.json();
        if (result.code !== 200) {
            $("create-error").textContent = result.message || "存档读取失败";
            return;
        }
        sessionId = sid;
        selectedClass = "";
        saveList.classList.add("hidden");
        enterGame(result.data.character);
        result.data.messages.forEach((m) => {
            appendBubble(
                m.role === "user" ? "user" : "gm",
                cleanMarkdown(m.content),
                m.role === "user" ? charName : "主持人"
            );
        });
        if (result.data.dead) {
            appendBubble("gm", "这段记录里，你已经死去了。要重新开始，或换一份存档。", "命运");
            setDead(true);
        } else {
            actionInput.focus();
        }
    } catch (e) {
        $("create-error").textContent = "读取存档失败：" + e.message;
    }
}

// ---------- 回到建卡界面 ----------
function quitToCreate(openSaves) {
    sessionId = "";
    selectedClass = "";
    gameScreen.classList.add("hidden");
    createScreen.classList.remove("hidden");
    setDead(false);
    document.querySelectorAll(".class-card").forEach((c) => c.classList.remove("selected"));
    $("char-name").value = "";
    btnStart.disabled = true;
    btnStart.textContent = "踏入废土";
    saveList.classList.add("hidden");
    if (openSaves) toggleSaveList();
}

// ---------- 放弃冒险：确认后回到建卡界面 ----------
function quitGame() {
    if (!confirm("确定要放弃当前冒险、回到建卡界面吗？")) return;
    quitToCreate(false);
}

// ---------- 删除当前这一局的存档 ----------
async function deleteCurrentSave() {
    if (!sessionId) return;
    if (!confirm("确定删除当前这一局的存档吗？删了就找不回来了。")) return;
    await deleteSave(sessionId, charName || "当前存档", null);
}

// ---------- 事件绑定 ----------
$("char-name").addEventListener("input", checkStartReady);
btnStart.addEventListener("click", startGame);
btnSend.addEventListener("click", sendAction);
btnLoad.addEventListener("click", toggleSaveList);
$("btn-quit").addEventListener("click", quitGame);
$("btn-delete-save").addEventListener("click", deleteCurrentSave);
$("btn-death-new").addEventListener("click", () => quitToCreate(false));
$("btn-death-load").addEventListener("click", () => quitToCreate(true));
actionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendAction();
    }
});

// ---------- 页面加载即拉取职业 ----------
loadClasses();
