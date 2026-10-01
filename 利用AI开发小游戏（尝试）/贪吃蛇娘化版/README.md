# 贪吃蛇娘化版 · 项目说明

> 当前状态：**可运行原型（M3 完成）**。核心玩法闭环 + 技能系统 + Boss 战 + 美术 + 音频已就位。
> 目录：`D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版`

---

## 一、怎么跑起来

**在 PyCharm 里**：直接右键 `main.py` → Run。需要装的库只有 `pygame`。

```bash
pip install pygame
```

**命令行**：`python main.py`

操作：

| 按键 | 作用 |
|---|---|
| 方向键 / WASD | 移动 |
| ESC / P | 战斗中暂停 / 继续（暂停菜单可重开、回主菜单、调音量）；其它界面返回上层 |
| ↑ / → | 将“上次鼠标点选的音量”（音乐 or 音效）+10（长按超 1 秒连调；战斗进行中让位给移动） |
| ↓ / ← | 同上，−10 |
| F11 | 全屏 / 窗口切换 |

> **胜负**：每局不再是无尽生存 —— **生存到场景阈值后专属 Boss 登场，击败它即通关结算**（Boss 战中方向键仍只管走位，撞击 Boss / 靠技能输出）。

---

## 二、已经实现了什么

### 玩法（按你的设定）

- **蛇身固定 10 节，吃东西不再变长**
- 吃经验果 → **升级 → 攻击力提高**（Lv1 攻击 12，每级 +3）
- **升级解锁技能**（见下节）
- 吃能量结晶 / 星尘 / 爱心回血
- 撞小怪：双方都掉血，击杀掉星尘
- **难度靠小怪递增 + 一条无条件的时间压力曲线**

### 技能系统（5 个，按等级自动解锁）

设计原则是**不额外加按键** —— 贪吃蛇的核心乐趣就是"只操控方向"，
多一套技能键会毁掉它。所以技能全部是**被动 / 自动触发**：

| 等级 | 技能 | 效果 | 定位 |
|---|---|---|---|
| Lv.2 | 樱花冲锋 | 移动时碾过身旁小怪（3 格充能，2.2 秒回一格） | 主动清场 |
| Lv.4 | 荆棘尾 | 小怪撞上你的尾椎也会受伤（有全局节流） | 被动护身 |
| Lv.6 | 星辉护盾 | 每 22 秒自动获得 1.6 秒无敌 | 救命符 |
| Lv.8 | 蔓生荆棘 | 走过的地面留下伤害荆棘，存在 3.5 秒 | 走位收益 |
| Lv.10 | 樱花风暴 | 每 9 秒在周身 3 格范围造成伤害 | 被围时爆发 |

**解锁等级为什么是 2/4/6/8/10**：初版设的是 3/6/9/12/15，
但实测玩家平均只活到 8~9 级 —— 等于有两个技能永远见不到。
下调后一局（约 100 秒）能完整走完技能树，成长感才成立。

### 难度系统

**四条通道同时生效**：

1. 血量变厚（每 30 秒 +34%，最高 6 倍）
2. 数量变多（刷怪间隔 1.6 秒起，逐步压缩；同屏上限 24 只）
3. 追击欲望变强（开场 10%，上限 90%）
4. **时间压力曲线**（第 90 秒起，每秒加压 0.14，最高 3 倍）

第 4 条是**兜底机制**，也是调平衡时最关键的一条。理由：
前三条都依赖"怪比玩家强"，但技能越强玩家清怪越快，局面反而更安全 ——
实测过 5 局全部 300 秒无伤通关。时间压力是无条件的，
不管你打得多好它都在涨，所以任何打法都无法无限苟。
另外还加了一条**击杀经验衰减**（30 秒后逐步降到 25%），
专门拦住"杀得快 → 升级快 → 更强 → 杀得更快"这个正反馈。

### Boss 战（每场景专属 Boss + 弹幕）

把"无尽生存"升级为"有终点的一局"：**生存到场景阈值 → 专属 Boss 登场 → 击败它即通关结算**。
4 个场景各一个**数据驱动** Boss（配在 `data/bosses.json`），多阶段 + 弹幕：

| 场景 | Boss | 血量 | 特色攻击 |
|---|---|---|---|
| 校园庭院（入门） | 樱之守护者 | 1200 | 环形 + 瞄准 |
| 霓虹夜市（普通） | 霓虹夜主 | 1600 | + 弹墙（留缺口） |
| 深海遗迹（困难） | 深海遗主 | 2000 | + 螺旋 + 震击 |
| 樱花神域（噩梦） | 神域主宰 | 2600 | + 冲撞 + 召唤，阶段最密 |

**伤害模型（关键设计）**：

- 玩家**撞击 Boss 身体 → Boss 掉 `PLAYER_ATK`，玩家不掉血**（受 `BOSS_HIT_CD`≈0.3s 限流，防贴脸秒杀）；冲锋 / 风暴 / 荆棘尾 / 蔓生荆棘也能打 Boss。
- Boss **只通过弹幕 / 蓄力冲撞 / 范围震击 / 召唤的小怪**伤害玩家；冲撞与震击都有**预警**（红线 / 红圈），预警结束才结算伤害。
- 循环 = "躲弹幕 → 找空隙撞 Boss / 靠技能输出"，张力来自弹幕而非接触，符合贪吃蛇的走位内核。
- Boss 血量按比例**分阶段**，越残血攻击越密；登场后普通刷怪放慢（`BOSS_MOB_SPAWN_SCALE`），维持压力但不喧宾夺主。
- Boss 立绘缺失时用**程序化几何绘制**（尖刺冠 + 主体 + 主题色描边 + 眼睛，绝不露品红占位块）；把贴图放进 `assets/characters/boss/<id>.png` 并在 `bosses.json` 填 `sprite` 即自动换成贴图。
- 通关写 `record_victory`：累计 `total_wins` 与 `bosses_defeated[场景]`，额外奖励 `BOSS_REWARD_STARDUST` 星尘。若某场景没配 Boss（或 `BOSS_ENABLED=False`），该局**自动退回纯无尽生存，绝不崩**。

### 系统

- **存档**：`saves/save_data.json`，记录星尘、角色、战绩；含旧 ID 自动迁移
- **抽卡**：60 星尘一抽 / 540 十连，R 78% · SR 18% · SSR 4%，10 抽保 SR、60 抽保 SSR，**抽完即时写盘**
- **角色选择**：读 `data/characters.json`，出图后自动多出卡片
- **场景选择**：读 `data/scenes.json`，4 个场景，难度/敌人密度不同
- **显示设置**：窗口 / 无边框 / 全屏，多档分辨率；含 BGM / 音效音量滑块（拖动即时生效 + 存档）
- **音频**：BGM 按场景切换 + 全套 SFX（吃果/升级/击杀/受伤/技能/抽卡/UI）。
  `assets/audio/` 下有对应文件就用真实音频，没有则用**纯代码合成的占位音**，丢进同名文件即自动升级

### 技术

- 渲染与窗口分辨率分离（改 `settings.py` 即可切 4K）
- **蛇身骨骼链渲染** + 旋转预烘焙缓存（避免每帧 `rotate` 拖垮帧率）
- 逻辑固定 tick + 渲染插值（蛇是平滑移动，不跳格）
- **HUD 全部按缩放自适应**：面板宽度由"最长一行内容有多少像素"反推，
  不是拍脑袋写死；窗口过小还会自动缩小格子保证三段不重叠

---

## 三、一局实测数据（自动试玩 12 局）

| 指标 | 结果 |
|---|---|
| 存活时长 | 最短 81s / 中位 104s / 最长 128s |
| 到达等级 | 平均 11.8 级 |
| 单局击杀 | 平均 74 只 |
| 单局得分 | 平均 22500 |
| **技能覆盖** | **平均 4.8 / 5**（一局能走完技能树） |
| 打不死的局 | 0 / 12 |

击杀来源分布（用于确认没有某个技能一枝独秀）：

| 来源 | 占比 |
|---|---|
| 樱花冲锋 | 54% |
| 蔓生荆棘 | 19% |
| 荆棘尾 | 17% |
| 主动撞击（核心操作） | 10% |

> 调平衡踩过的坑都写在 `settings.py` 的 `[平衡记录]` 注释里了。
> 最核心的教训：**改数值不如改机制**。冲锋初版是"无冷却永续 AOE"，
> 独占 68% 击杀、把核心操作挤成 0%；后来靠"充能制 + 全局节流"
> 这类机制改动才真正解决，光调伤害数字只会来回震荡。

---

## 四、想改数值改哪里

**全部在 `settings.py`**，不用动逻辑代码：

| 想改什么 | 改哪个 |
|---|---|
| 蛇跑得快慢 | `MOVE_INTERVAL`（越小越快） |
| 蛇身粗细/长度 | `BODY_SCALE_HEAD`、`BODY_SCALE_TAIL`、`SNAKE_LEN` |
| 升级快慢 | `EXP_PER_LEVEL` |
| 攻击力成长 | `ATK_BASE`、`ATK_PER_LEVEL` |
| **技能解锁等级** | `SKILL_UNLOCK` |
| **冲锋强度** | `DASH_DMG`、`DASH_CHARGES`、`DASH_RECHARGE` |
| **荆棘尾强度** | `SPIKE_DMG`、`SPIKE_TICK`、`SPIKE_GLOBAL_CD` |
| **护盾频率** | `SHIELD_INTERVAL`、`SHIELD_TIME` |
| **荆棘地形** | `THORN_LIFE`、`THORN_SPACING`、`THORN_DMG` |
| **风暴强度** | `STORM_INTERVAL`、`STORM_RADIUS`、`STORM_DMG` |
| **时间压力** | `TIME_PRESSURE_START`、`TIME_PRESSURE_RAMP` |
| 击杀经验衰减 | `KILL_EXP_BASE`、`KILL_EXP_DECAY_RATE` |
| 小怪强度 | `MOB_HP`、`MOB_TOUCH_DAMAGE`、`MOB_HP_GROWTH` |
| 刷怪节奏 | `MOB_SPAWN_INTERVAL`、`MOB_SPAWN_RAMP`、`MOB_MAX_ALIVE` |
| **Boss 弹幕 / 技能** | `BOSS_*`、`RADIAL_COUNT`、`AIMED_*`、`SPIRAL_*`、`WALL_*`（全局参数） |
| **Boss 血量 / 阶段 / 登场阈值** | `data/bosses.json`（按场景配，数据驱动） |
| 各种掉落概率 | `DROP_*` 系列 |
| 切 4K | 把 `RENDER_WIDTH/HEIGHT` 改成 3840/2160 |

抽卡概率改 `data/gacha.json`，场景配置改 `data/scenes.json`，
角色表改 `data/characters.json`，技能文案改 `data/skills.json`，Boss 配置改 `data/bosses.json`。

### 音频文件清单

所有音频**都可缺省**——缺哪个就用合成占位音顶上，游戏照常跑。
想要真实音频，把文件按下表名字放进 `assets/audio/`（每个名字按 `.ogg`→`.wav`→`.mp3` 顺序探测）：

```
assets/audio/bgm/  menu  battle  boss  gacha  gameover
assets/audio/sfx/  ui_click  ui_hover  ui_back
                   eat_exp  eat_crystal  eat_stardust  eat_heart
                   level_up  skill_unlock  hurt  kill  gameover
                   skill_dash  skill_spike  skill_shield  skill_thorn  skill_storm
                   gacha_pull  gacha_error  gacha_ssr  gacha_sr  gacha_r
                   boss_appear  boss_hit  boss_shoot  boss_charge  boss_slam
                   boss_defeat  victory
```

音量有两种调法：「显示设置」页拖动滑块，或用**方向键热键**。热键调的是音乐还是音效，
**由你上次鼠标点选的那个音量决定**（点音乐滑块/暂停面板的“音乐”就调音乐，点“音效”就调音效，选中项会高亮）；
选定后 **↑/→ 增大、↓/← 减小，每次 ±10，按住超过 1 秒会快速连调**
（战斗进行中方向键要留给移动，需先按 ESC/P 开暂停菜单再调），两者都会自动写进存档。合成占位音的配方都在
`core/audio_manager.py` 的 `_recipe()` / `_bgm_recipe()` 里，想调音色改那里。

---

## 五、工具脚本（`tools/`）

| 脚本 | 用途 |
|---|---|
| `selfcheck.py` | **改完代码先跑这个**。查语法、配置引用、素材缺失、JSON 合法性，以及**用了没导入的名字** |
| `playsim.py` | 自动试玩若干局，输出生存时长/等级/得分，用来验证数值平衡 |
| `screenshot.py` | 无头渲染各场景截图到 `tools/_shots/`，不用开窗口就能看画面 |
| `prepare_assets.py` | 素材整理：抠图（含棋盘格底）、去水印、缩放、重命名 |
| `preview_assets.py` | 把处理后的素材拼成一张预览图，检查抠图效果 |

> `selfcheck.py` 里的"未定义名字检查"是踩坑后才加的：
> 项目里 settings 的常量有两种访问方式（`from settings import X` 和 `S.X`），
> 混用时会出现"某个分支用了裸名字但顶部没导入"。
> 这种错**编译期查不出来**，只有那行代码真的执行到才崩 ——
> 而且往往是玩到解锁某个技能时才崩，本地测不出来。

---

## 六、下一步可以做什么

按优先级：

1. **Boss 立绘** —— 目前 4 个 Boss 是程序化几何绘制；出图后放进 `assets/characters/boss/<id>.png` 并在 `bosses.json` 填 `sprite` 即升级
2. **场景卡片显示 Boss 战绩** —— `scene_select.py` 读 `bosses_defeated`，在卡片上显示该场景 Boss 名与是否已击败
3. **多角色** —— 出图 → 放进 `assets/characters/<id>/` → 在 `characters.json` 加一条
4. **多场景贴图** —— 目前只有校园庭院有图，其余 3 个是色块占位
5. **技能 / Boss 特效** —— 音频已完成；视觉仍为几何图形与飘字，可加更华丽的特效
6. **技能分支** —— 现在技能是固定解锁；可改成"升级时二选一"，增加构筑深度

---

## 七、目录结构

```
贪吃蛇娘化版/
├── main.py                  入口
├── settings.py              所有数值配置（改这里就够了）
├── core/
│   ├── game.py              主循环、窗口、场景切换
│   ├── scene.py             场景基类
│   ├── asset_manager.py     素材加载 / 旋转预烘焙
│   ├── audio_manager.py     BGM / SFX 加载 + 合成占位 + 音量
│   └── save_manager.py      存档读写 / ID 迁移
├── game_logic/
│   ├── entities.py          蛇娘 / 小怪 / 掉落物
│   ├── boss.py              Boss / 弹幕（多阶段 + 环形/瞄准/螺旋/弹墙/冲撞/震击/召唤）
│   └── skills.py            技能引擎（解锁、充能、荆棘地形）
├── scenes/
│   ├── main_menu.py         主菜单
│   ├── battle.py            战斗（核心）
│   ├── character_select.py  角色选择
│   ├── scene_select.py      场景选择
│   ├── gacha.py             抽卡
│   └── display_settings.py  显示设置
├── ui/
│   ├── button.py            按钮控件（含点击 / 悬停音效）
│   └── slider.py            音量滑块控件
├── data/
│   ├── characters.json      角色表
│   ├── scenes.json          场景表
│   ├── bosses.json          Boss 表（每场景专属 Boss，多阶段 + 弹幕）
│   ├── gacha.json           卡池配置
│   └── skills.json          技能文案
├── assets/
│   ├── characters/          角色立绘 / 蛇身 / 小怪
│   ├── backgrounds/         场景背景
│   └── items/               掉落物图标
├── saves/                   存档
└── tools/                   自检 / 试玩 / 截图 / 素材处理
```
