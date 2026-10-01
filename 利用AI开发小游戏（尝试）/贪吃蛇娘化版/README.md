# 贪吃蛇娘化版 · 项目说明

> 当前状态：**可运行原型（自由移动动作版）**。大地图自由移动 + 自动普攻 + 闪避 + 角色专属技能包 + 升级三选一属性卡 + 剧情关卡/无尽双模式 + 精英怪 + Boss 战 + 多存档槽 + 新手指引 + 美术 + 音频已就位。
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
| WASD / 方向键 | 八向自由移动（斜向自动归一化） |
| 鼠标左键 | 闪避：朝当前移动方向（静止时朝鼠标）瞬移一段，带短无敌帧与冷却 |
| 1 | 释放当前角色的**专属主动技能**（有冷却，HUD 显示转圈） |
| ESC / P | 战斗中暂停 / 继续（暂停菜单可重开、回主菜单、调音量）；其它界面返回上层 |
| R | 结算界面重开一局 |
| ↑ / → | 将“上次鼠标点选的音量”（音乐 or 音效）+10（长按超 1 秒连调；战斗进行中让位给移动） |
| ↓ / ← | 同上，−10 |
| F11 | 全屏 / 窗口切换 |

> **胜负**：剧情关**撑满 15 分钟后专属 Boss 登场，击败它即通关并解锁下一关**；无尽模式无 Boss、纯生存刷分；中途血量归零则失败。
> 普攻始终自动开启（向最近的怪发射弹丸），你只管走位、闪避与放技能。

---

## 二、已经实现了什么

### 玩法（大地图俯视角动作生存）

- **世界 = 3×2 屏**，摄像机平滑跟随玩家并钳制在世界内；蛇尾是**纯装饰拖尾**（不碰撞、不会撞死自己）
- **WASD 八向自由移动**；**鼠标左键闪避**（瞬移 + 短无敌帧 + 冷却）
- **自动普攻**始终开启：向最近的怪发射弹丸，攻击频率随等级成长
- 打怪 / 拾取道具获得经验 → **升级弹出三选一强化卡**（技能卡 / 被动数值卡，见下节）
- 道具**品质随时间升档**（经验值放大），进入范围会被**磁吸**过去；道具只给经验，强度成长全靠卡牌
- 小怪**恒定索敌追击**，速度与碰触伤害随时间上升；击杀按概率掉落经验 / 结晶 / 星尘 / 爱心
- **难度 = 怪物递增 + 一条无条件的时间压力曲线**（血量倍率）

### 角色专属技能包（固定，无共通技能）

技能不再靠升级抽卡解锁，而是**每名角色自带一套专属技能包**：
**1 个主动**（绑定 `1` 键，有冷却，独立特效）+ **1 个常驻被动**。
技能 id / 名字 / 颜色 / 特效配在 `data/characters.json` 的 `kit` 字段，数值走 `settings.py`。
升级三选一**只给通用属性卡**（加攻 / 加移速 / 加攻速 / 减冷却 / 加拾取 / 加最大HP并回满），不再有技能卡。

| 角色 | 专属主动（键 1） | 常驻被动 |
|---|---|---|
| 樱落 | 落樱·绯斩：前冲斩 + 短护盾 | 花守：击杀概率回血 |
| 薄荷 | 疾风连闪：多段突进 + 移速爆发 | 御风：常驻移速+、闪避冷却- |
| 潮汐 | 沧澜涌潮：环形水浪减速+击退+伤害 | 寒流：普攻附带减速 |
| 绯焰 | 燎原火鞭：扇形火焰鞭 + 灼烧 DoT | 余烬：攻击附带灼烧 |
| 星璃 | 星陨链：多枚追踪星弹连锁 | 星辉：击杀减主动冷却 |
| 月见 | 月华结界：穿透月光 beam + 护盾 | 静夜：常驻受伤减免 |

减速 / 灼烧等持续状态挂在怪（`Mob`）上结算；主动的瞬发效果由 `SkillEngine.cast()`
返回事件字典、`battle._apply_skill_event()` 落地（各自独立粒子/震屏/连锁线/beam 特效）。

### 关卡模式（剧情序列 + 无尽）

- **剧情模式**：`data/levels.json` 定义 4 关线性序列（对应 4 张场景图），
  第 1→4 关依次解锁。每关 **15 分钟**、**每 3 分钟刷一只精英怪**（体型/血量倍率更高、死亡多掉落），
  撑满时长后**专属 Boss 登场**，击败即通关并解锁下一关。入口：主菜单「开始游戏」→ 关卡选择。
- **无尽模式**：独立入口（关卡选择页「无尽模式」→ 选图），无 Boss、无胜利条件，纯生存随时间加压刷分。
- 关卡进度（已解锁/已通关）记在存档槽里（`story_unlocked` / `story_cleared`）。

### 难度系统

**多条通道同时生效**：

1. 怪物提速（`MOB_SPEED_BASE` 起，随时间按 `MOB_SPEED_GROWTH` 增长，有上限倍率）
2. 怪物碰触伤害增长（`MOB_ATK_GROWTH`，随时间从 1 往上加）
3. 数量变多（刷怪间隔逐步压缩；同屏上限 `MOB_MAX_ALIVE`）
4. 怪物血量倍率随时间上升
5. **时间压力曲线**（无条件加压的血量倍率，兜底防无限苟）

道具**品质随时间升档**（`ITEM_TIER_TIME`），越往后拾取 / 掉落给的经验越多，
保证升级节奏不掉队；强度成长则完全交给卡牌，
避免"杀得快 → 升级快 → 更强 → 杀得更快"这个正反馈失控。

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

- **普攻弹丸 / 技能 / 撞击 Boss 身体 → Boss 掉血**（撞击受 `BOSS_HIT_CD`≈0.3s 限流，防贴脸秒杀）；Boss 蓄力冲撞期间贴脸则玩家掉血。
- Boss **只通过弹幕 / 蓄力冲撞 / 范围震击 / 召唤的小怪**伤害玩家；冲撞与震击都有**预警**（红线 / 红圈），预警结束才结算伤害。
- 循环 = "躲弹幕 → 找空隙撞 Boss / 靠技能输出"，张力来自弹幕而非接触，符合贪吃蛇的走位内核。
- Boss 血量按比例**分阶段**，越残血攻击越密；登场后普通刷怪放慢（`BOSS_MOB_SPAWN_SCALE`），维持压力但不喧宾夺主。
- Boss 立绘缺失时用**程序化几何绘制**（尖刺冠 + 主体 + 主题色描边 + 眼睛，绝不露品红占位块）；把贴图放进 `assets/characters/boss/<id>.png` 并在 `bosses.json` 填 `sprite` 即自动换成贴图。
- 通关写 `record_victory`：累计 `total_wins` 与 `bosses_defeated[场景]`，额外奖励 `BOSS_REWARD_STARDUST` 星尘。若某场景没配 Boss（或 `BOSS_ENABLED=False`），该局**自动退回纯无尽生存，绝不崩**。

### 系统

- **多存档槽**：`saves/config.json`（机器级：显示/音量/当前槽）+ `saves/slots/<id>.json`（每槽游戏进度）。
  主菜单「存档管理」可**命名新建 / 切换 / 重命名 / 删除**存档槽；旧版单文件 `save_data.json`
  首次启动自动迁移为槽 1「测试存档」。每槽独立记录星尘、角色、战绩、剧情进度、新手指引状态。
- **新手指引**：新存档首局按 `settings.TUTORIAL_HINTS` 顺序播放定时浮层
  （移动/闪避/放技能/选卡/剧情目标），走完或首局结束即标记 `tutorial_done` 不再打扰。
- **角色收集 + 强化养成（无氪金 · 全 SSR · 可追平）**：本作**没有氪金系统**，所有角色**同为 SSR**。
  抽卡 = 等概率纯收集（60 星尘一抽 / 540 十连，无概率差、无保底）：
  抽到未拥有角色即入库（记 0 层）；抽到**已拥有**角色 = 该角色**强化 +1 层**（上限 15），
  强化**同时加外观与战斗数值**；满 15 层后再抽返还星尘（`data/gacha.json` 的 `overflow_refund`），**抽完即时写盘**。
  因为无氪金、玩久人人可满，这是**公平养成**而非付费碾压。当前共 **6 名角色**：樱落 / 薄荷 / 潮汐 / 绯焰 / 星璃 / 月见。
- **角色选择**：读 `data/characters.json`，3×2 卡片网格；左上 SSR 角标、右上强化层数角标，
  底部独立状态条（不再遮挡名字/称号/属性）；**点击已拥有角色进入详情页**。
- **角色详情页**：切换 4 个场景背景看角色的**全身立绘**（蛇尾与身体一体、无拼接缝）；点击**头/身/尾**三段触发彩蛋台词；
  展示背景故事 / 技能 / 强化层数进度；可“设为出战”。
- **场景选择**：读 `data/scenes.json`，4 个场景，难度/敌人密度不同
- **显示设置**：窗口 / 无边框 / 全屏，多档分辨率；含 BGM / 音效音量滑块（拖动即时生效 + 存档）
- **音频**：BGM 按场景切换 + 全套 SFX（吃果/升级/击杀/受伤/技能/抽卡/UI）。
  `assets/audio/` 下有对应文件就用真实音频，没有则用**纯代码合成的占位音**，丢进同名文件即自动升级

### 技术

- 渲染与窗口分辨率分离（改 `settings.py` 即可切 4K）
- **蛇身骨骼链渲染** + 旋转预烘焙缓存（避免每帧 `rotate` 拖垮帧率）；上半身立绘与尾根之间插入一段**腰→尾衔接过渡段**，让立绘自然“长出”蛇尾而非硬接
- 逻辑固定 tick + 渲染插值（蛇是平滑移动，不跳格）
- **HUD 全部按缩放自适应**：面板宽度由"最长一行内容有多少像素"反推，
  不是拍脑袋写死；窗口过小还会自动缩小格子保证三段不重叠

---

## 三、一局实测数据（自动试玩 · 自由移动版）

用 `tools/playsim.py` 模拟"会走位会闪避"的玩家跑多局
（朝道具走 + 躲怪 + 贴脸左键闪避 + 专属技能全放 + 自动选卡），覆盖剧情与无尽两种模式：

| 指标 | 结果 |
|---|---|
| 剧情局 | 撑满 15 分钟击败 Boss 通关 |
| 无尽局 | 存活至上限计时，正常结算 |
| 受伤 | 0 点（探针为完美风筝 AI） |

> 探针是"完美风筝"的超级 AI，0 伤不代表真人难度 ——
> 真人只有 3 点血、还要躲弹幕与怪群，压力明显更大。
> 调平衡的教训：**改数值不如改机制**；自由移动版把强度成长从"击杀经验"
> 移到"升级三选一卡牌"，让操作（走位 / 闪避）与构筑（选卡）共同决定难度。

---

## 四、想改数值改哪里

**全部在 `settings.py`**，不用动逻辑代码：

| 想改什么 | 改哪个 |
|---|---|
| 世界大小（几屏） | `WORLD_SCREENS_X` / `WORLD_SCREENS_Y` |
| 玩家跑得快慢 | `PLAYER_SPEED` |
| 闪避距离 / 冷却 / 无敌帧 | `DODGE_DIST` / `DODGE_CD` / `DODGE_IFRAME` |
| 普攻频率 / 射程 / 弹速 | `ATK_INTERVAL_BASE` / `ATK_INTERVAL_PER_LEVEL` / `ATK_INTERVAL_MIN` / `ATK_RANGE` / `ATK_BULLET_SPEED` |
| 升级快慢 | `EXP_PER_LEVEL` |
| 攻击力成长 | `ATK_BASE`、`ATK_PER_LEVEL` |
| 蛇身粗细 / 拖尾 / 体型 | `BODY_SCALE_HEAD`、`BODY_SCALE_TAIL`、`BODY_SEG_LEN`、`PLAYER_RADIUS` |
| 选卡张数 | `CARD_CHOICES` |
| 被动卡步长 | `CARD_ATK_STEP`、`CARD_SPEED_STEP`、`CARD_ATKSPD_STEP`、`CARD_CDR_STEP`、`CARD_PICKUP_STEP`、`CARD_HP_STEP` |
| 角色强化每层加成 / 上限 | `ENHANCE_MAX_LAYER`、`ENHANCE_ATK_PER_LAYER`、`ENHANCE_SPEED_PER_LAYER`、`ENHANCE_ATKSPD_PER_LAYER`、`ENHANCE_CDR_PER_LAYER`、`ENHANCE_PICKUP_PER_LAYER`、`ENHANCE_HP_PER_LAYER` |
| 专属技能数值 / 冷却 | `PETAL_SLASH_*`、`GALE_*`、`TIDE_*`、`EMBER_*`、`STAR_CHAIN_*`、`MOON_WARD_*` |
| 剧情时长 / 精英间隔 / 精英强度 | `STORY_DURATION`、`ELITE_INTERVAL`、`ELITE_*` |
| 新手指引文案 / 单条时长 | `TUTORIAL_HINTS`、`TUTORIAL_HINT_DURATION` |
| 怪物速度 / 伤害成长 | `MOB_SPEED_BASE`、`MOB_SPEED_GROWTH`、`MOB_SPEED_MAX_MULT`、`MOB_ATK_GROWTH` |
| 刷怪节奏 | `MOB_SPAWN_INTERVAL`、`MOB_MAX_ALIVE` |
| 道具刷新 / 品质升档 / 磁吸 | `ITEM_SPAWN_INTERVAL`、`ITEM_MAX_ON_MAP`、`ITEM_TIER_TIME`、`ITEM_MAGNET_RADIUS` |
| **时间压力** | `TIME_PRESSURE_START`、`TIME_PRESSURE_RAMP` |
| **Boss 弹幕 / 技能** | `BOSS_*`、`RADIAL_COUNT`、`AIMED_*`、`SPIRAL_*`、`WALL_*`（全局参数） |
| **Boss 血量 / 阶段 / 登场阈值** | `data/bosses.json`（按场景配，数据驱动） |
| 各种掉落概率 | `DROP_*` 系列 |
| 切 4K | 把 `RENDER_WIDTH/HEIGHT` 改成 3840/2160 |

收集卡池 / 强化上限 / 满层返还改 `data/gacha.json`，场景配置改 `data/scenes.json`，
角色表（含专属技能包 `kit`）改 `data/characters.json`，**剧情关卡改 `data/levels.json`**，
**升级属性卡池改 `data/cards.json`**，Boss 配置改 `data/bosses.json`。

### 音频文件清单

所有音频**都可缺省**——缺哪个就用合成占位音顶上，游戏照常跑。
想要真实音频，把文件按下表名字放进 `assets/audio/`（每个名字按 `.ogg`→`.wav`→`.mp3` 顺序探测）：

```
assets/audio/bgm/  menu  battle  boss  gacha  gameover
assets/audio/sfx/  ui_click  ui_hover  ui_back
                   eat_exp  eat_crystal  eat_stardust  eat_heart
                   level_up  skill_unlock  hurt  kill  gameover
                   shoot  dodge  card_pick
                   skill_dash  skill_spike  skill_shield  skill_thorn  skill_storm  skill_bloom
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
| `prepare_assets.py` | 素材整理：抠图（棋盘格底 / 纯色底 / 贴边垫色泛洪）、去水印、高清化缩放、重命名 |
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
3. **多角色** —— 已完成 6 名（全 SSR · 强度一致）；再加角色：出图 → 放进 `assets/characters/<id>/` → 在 `characters.json` 加一条（含 `kit`）→ `gacha.json` 的 `pool` 补上 id
4. **更多剧情关** —— 目前 4 关（4 张场景图已齐）；加关只需在 `levels.json` 追加 + 出新场景图
5. **存档命名输入法** —— 现为预设名 + 逐字符选择（规避中文 IME）；如需完整键盘中文命名可后续接入

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
│   └── save_manager.py      多存档槽读写（config + slots）/ 旧档迁移
├── game_logic/
│   ├── entities.py          自由移动玩家 / 世界怪 / 磁吸掉落物 / 普攻弹丸
│   ├── boss.py              Boss / 弹幕（多阶段 + 环形/瞄准/螺旋/弹墙/冲撞/震击/召唤，世界坐标）
│   └── skills.py            角色专属技能包引擎（kit 装载、冷却、释放事件）
├── scenes/
│   ├── main_menu.py         主菜单
│   ├── battle.py            战斗（核心：世界/摄像机/刷怪/道具/选卡/HUD）
│   ├── character_select.py  角色选择
│   ├── character_detail.py  角色详情（场景预览/部位彩蛋/背景故事/强化展示）
│   ├── scene_select.py      场景选择（无尽模式选图）
│   ├── level_select.py      关卡选择（剧情序列 + 无尽入口）
│   ├── save_manager_scene.py 存档管理（多槽新建/切换/重命名/删除）
│   ├── gacha.py             抽卡
│   └── display_settings.py  显示设置
├── ui/
│   ├── button.py            按钮控件（含点击 / 悬停音效）
│   └── slider.py            音量滑块控件
├── data/
│   ├── characters.json      角色表（含专属技能包 kit）
│   ├── scenes.json          场景表
│   ├── levels.json          剧情关卡序列（时长/精英间隔/Boss/解锁）
│   ├── bosses.json          Boss 表（每场景专属 Boss，多阶段 + 弹幕）
│   ├── gacha.json           抽卡卡池配置
│   ├── cards.json           升级三选一属性卡池（仅通用属性）
│   └── skills.json          专属技能展示表（HUD/详情页读取）
├── assets/
│   ├── characters/          角色立绘 / 蛇身 / 小怪
│   ├── backgrounds/         场景背景
│   └── items/               掉落物图标
├── saves/                   存档（config.json + slots/<id>.json）
└── tools/                   自检 / 试玩 / 截图 / 素材处理
```
