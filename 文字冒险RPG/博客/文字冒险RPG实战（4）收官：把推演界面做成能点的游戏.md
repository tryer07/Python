# 文字冒险RPG实战（4）收官：把推演界面做成能点的游戏

> 这是系列的最后一篇。前三篇都在讲后端，这一篇把浏览器这边补上：建卡、聊天式的剧情流、状态面板、死亡处理，最后收官聊聊这个项目比猜字谜那次多学会了什么。

## 一、一个页面装两个界面

我没有做多页面，`index.html` 里就是两个大的 div，建卡界面和游戏界面，靠一个 `hidden` 样式类互相切换：

```
<div id="create-screen" class="screen">
    角色名输入框 + 职业卡容器 + 踏入废土按钮 + 读取存档按钮
</div>
<div id="game-screen" class="screen hidden">
    左侧状态面板 + 右侧剧情气泡区 + 底部行动输入条
</div>
```

开局成功就调 `enterGame`，把建卡层藏起来、游戏层露出来：

```
function enterGame(character) {
    createScreen.classList.add("hidden");
    gameScreen.classList.remove("hidden");
    storyLog.innerHTML = "";
    renderStatus(character);
    setDead(false);
}
```

这个思路其实是从猜字谜那边学来的，单页加显隐，省掉了页面跳转和一堆状态传参，小游戏完全够用。

## 二、职业卡片不写死在 HTML 里

建卡页面上的三张职业卡，HTML 里只有一个空容器，内容是我请求 `/api/classes` 之后用脚本捏出来的。

这里我一开始想偷懒：职业就仨，直接写死在 HTML 里呗。后来改掉了，因为职业名、描述、数值的源头在后端那个 `CHARACTER_CLASSES` 字典里。写死在 HTML 就等于同一份信息抄两处，我改天数值的平衡时肯定忘改前端。让接口吐卡片数据，HTML 只留壳，以后加第四个职业只需要往字典里添一条，前端一个字不用动。

```
result.data.forEach((cls) => {
    const card = document.createElement("div");
    card.className = "class-card";
    name.textContent = cls.name;
    desc.textContent = cls.desc;
    card.addEventListener("click", () => selectClass(cls.name, card));
    classList.appendChild(card);
});
```

顺手加了个小体验：名字和职业都选定之前，开始按钮一直是 `disabled`。省得有人空着名字点踏入废土，然后对着一句报错发懵。

## 三、状态面板只信后端回传的数据

左侧面板显示 HP 条、攻击、物资、背包。每回合行动接口返回里都捎着最新的 `character` 对象，面板每次整体重刷：

```
const hpRatio = status.max_hp > 0 ? status.hp / status.max_hp : 0;
fill.style.width = Math.max(0, Math.min(100, hpRatio * 100)) + "%";
fill.style.background = hpRatio > 0.3 ? "var(--hp-good)" : "var(--hp-bad)";
```

两个小心思。血量条宽度钳在 0 到 100 之间，AI 万一吐个负数或超上限的数，界面也不会扭曲；血量比例低于三成时条子从绿色换成红色，玩家扫一眼就知道自己快不行了，这个比数字直观。

背包列表每次 `innerHTML = ""` 重建，空背包渲染一个空项占住版式，面板不至于跳来跳去。

## 四、一次行动的完整往返

前端发行动的主流程，我把节奏感当重点做了：

```
appendBubble("user", text, charName);
loadingHint.classList.remove("hidden");
btnSend.disabled = true;
try {
    const resp = await fetch(API + "/api/game/action", { method: "POST", ... });
    const result = await resp.json();
    if (result.code === 200) {
        appendBubble("gm", cleanMarkdown(result.data.story), "主持人");
        renderStatus(result.data.character);
    }
} finally {
    loadingHint.classList.add("hidden");
    btnSend.disabled = false;
}
```

顺序是有讲究的：先把玩家那句话上屏，再转"主持人正在推演剧情"的等待提示。DeepSeek 一回合要几秒钟，不挂这个提示，玩家会以为自己网卡了、再点一次，那就真重复发行动了。所以发送期间按钮禁用，`finally` 里无论成败都恢复。

错误处理我全兜住了：网络断了进 `catch`，后端返回非 200 走 `else`，两种都在剧情流里冒一个"系统"气泡说人话，比如"与主持人的连接中断了"，而不是甩用户一个控制台报错。

## 五、死亡在前后端各锁一道门

上一篇讲了后端拿 409 拒掉死人的行动请求，这边讲前端怎么配合。

正常推演的返回里带一个 `dead` 布尔，HP 归零的那回合，先补一句命运旁白再锁界面：

```
if (result.data.dead) {
    appendBubble("gm", "你倒下了，视野渐渐暗下去……这一局到此为止。", "命运");
    setDead(true);
}

function setDead(dead) {
    deathPanel.classList.toggle("hidden", !dead);
    actionInput.disabled = dead;
    btnSend.disabled = dead;
}
```

遮罩上只留两个出口：重新开始、读取其他存档。输入框直接禁用，玩家没法再对一个死人下指令。而如果玩家开着两个标签页，从另一个页面把这一局玩死了，这边页面发行动收到的是 409，前端接住这个码同样调 `setDead(true)`，界面前后就是自洽的。

读存档列表还有个防止误删的小细节，存档条目整条可点、进这局游戏，行尾又嵌着一个删除按钮。点删除如果不处理冒泡，会连带触发整条的点击，删完存档顺手把这局又打开了。我加了 `e.stopPropagation()` 隔开两个行为，再补一个 `confirm` 确认框，删当前正在玩的档还会主动把玩家退回建卡页。

## 六、收官：和猜字谜那次比，我多学会了什么

八篇猜字谜教会我 FastAPI 的接口怎么摆、前后端怎么分。这个 RPG 项目建立在那套地基上，但多出来的几个教训是这次才有的。

第一，AI 应用的核心工程问题不是调用，是围绕调用的约束。整个后端真正调大模型的代码就十几行，剩下全是在给它立规矩：单行状态协议、数值锚点、前情摘要、失败兜底。模型负责创造，程序负责事实，这条分界线画得越清楚，应用越稳。

第二，输出协议宁土勿巧。JSON 优雅，但一行定长标记对模型更友好、被截断损失更小、正则十行搞定。以后再做结构化输出，我大概率还选这种丑但结实的路子。

第三，容错要按"玩家不能卡住"来设计。状态行缺了就当没掉血，摘要炸了就退回截断，网络断了就冒个气泡说明。每个降级路径的终点都是游戏还能继续。

毛病也还剩着：存档是明文 JSON 且没有任何登录校验，本地玩具没问题，想上线得先加个用户体系；偶尔 AI 判定的数值还是会偷偷偏保守，得回去再拧紧提示词。这些等我解决了，也许会有别的系列再聊。

四篇写完了，欢迎评论区指正。
