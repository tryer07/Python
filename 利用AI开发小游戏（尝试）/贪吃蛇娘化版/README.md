# 贪吃蛇娘化版 · 项目说明

> 当前状态：**可运行原型（M1 完成）**。核心玩法闭环已跑通，美术已接入。
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
| F11 | 全屏 / 窗口切换 |
| ESC | 返回上层 / 退出 |

---

## 二、已经实现了什么

### 玩法（按你的设定）

- **蛇身固定 10 节，吃东西不再变长**
- 吃经验果 → **升级 → 攻击力提高**（Lv1 攻击 12，每级 +3）
- 吃能量结晶 / 星尘 / 爱心回血
- 撞小怪：双方都掉血，击杀掉星尘
- **难度靠小怪递增**，三条通道同时生效：
  1. 血量变厚（每 30 秒 +22%，最高 6 倍）
  2. 数量变多（刷怪间隔从 3.2 秒压到 0.85 秒，同屏上限 14 只）
  3. 追击欲望变强（开场 10% 概率追你，后期 75%）

### 系统

- **存档**：`saves/save_data.json`，记录星尘、角色、战绩；含旧 ID 自动迁移
- **抽卡**：60 星尘一抽 / 540 十连，R 78% · SR 18% · SSR 4%，10 抽保 SR、60 抽保 SSR，**抽完即时写盘**
- **角色选择**：读 `data/characters.json`，出图后自动多出卡片
- **场景选择**：读 `data/scenes.json`，4 个场景，难度/敌人密度不同
- **显示设置**：窗口 / 无边框 / 全屏，多档分辨率

### 技术

- 渲染与窗口分辨率分离（改 `settings.py` 即可切 4K）
- **蛇身骨骼链渲染** + 旋转预烘焙缓存（避免每帧 `rotate` 拖垮帧率）
- 逻辑固定 tick + 渲染插值（蛇是平滑移动，不跳格）

---

## 三、一局实测数据（自动试玩 4 局）

| 指标 | 结果 |
|---|---|
| 存活时长 | 55 ~ 189 秒（平均 107 秒） |
| 到达等级 | 5 ~ 9 级 |
| 单局得分 | 2700 ~ 8850 |
| 单局星尘 | 6 ~ 18（约 5~10 局能抽一次） |

---

## 四、想改数值改哪里

**全部在 `settings.py`**，不用动逻辑代码：

| 想改什么 | 改哪个 |
|---|---|
| 蛇跑得快慢 | `MOVE_INTERVAL`（越小越快） |
| 蛇身粗细/长度 | `BODY_SCALE_HEAD`、`BODY_SCALE_TAIL`、`SNAKE_LEN` |
| 升级快慢 | `EXP_PER_LEVEL` |
| 攻击力成长 | `ATK_BASE`、`ATK_PER_LEVEL` |
| 小怪强度 | `MOB_HP`、`MOB_TOUCH_DAMAGE`、`MOB_HP_GROWTH` |
| 刷怪节奏 | `MOB_SPAWN_INTERVAL`、`MOB_SPAWN_RAMP`、`MOB_MAX_ALIVE` |
| 各种掉落概率 | `DROP_*` 系列 |
| 切 4K | 把 `RENDER_WIDTH/HEIGHT` 改成 3840/2160 |

抽卡概率改 `data/gacha.json`，场景配置改 `data/scenes.json`，角色表改 `data/characters.json`。

---

## 五、工具脚本（`tools/`）

| 脚本 | 用途 |
|---|---|
| `selfcheck.py` | **改完代码先跑这个**。检查语法、配置引用、素材是否缺失、JSON 是否合法 |
| `playsim.py` | 自动试玩若干局，输出生存时长/等级/得分，用来验证数值平衡 |
| `screenshot.py` | 无头渲染各场景截图到 `tools/_shots/`，不用开窗口就能看画面 |
| `prepare_assets.py` | 素材整理：抠图（含棋盘格底）、去水印、缩放、重命名 |
| `preview_assets.py` | 把处理后的素材拼成一张预览图，检查抠图效果 |

---

## 六、下一步可以做什么

按优先级：

1. **技能系统** —— 现在升级只加攻击力，技能还没做（升级时的钩子 `on_level_up` 已经留好）
2. **多角色** —— 出图 → 放进 `assets/characters/<id>/` → 在 `characters.json` 加一条
3. **多场景贴图** —— 目前只有校园庭院有图，其余 3 个是色块占位
4. **特效与音效** —— 技能特效、BGM、打击音
5. **4K 压测** —— 用 `screenshot.py` 的思路实测 4K 下的帧率

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
│   └── save_manager.py      存档读写 / ID 迁移
├── game_logic/
│   └── entities.py          蛇娘 / 小怪 / 掉落物
├── scenes/
│   ├── main_menu.py         主菜单
│   ├── battle.py            战斗（核心）
│   ├── character_select.py  角色选择
│   ├── scene_select.py      场景选择
│   ├── gacha.py             抽卡
│   └── display_settings.py  显示设置
├── ui/button.py             按钮控件
├── data/
│   ├── characters.json      角色表
│   ├── scenes.json          场景表
│   └── gacha.json           卡池配置
├── assets/
│   ├── characters/          角色立绘 / 蛇身 / 小怪
│   ├── backgrounds/         场景背景
│   └── items/               掉落物图标
├── saves/                   存档
└── tools/                   自检 / 试玩 / 截图 / 素材处理
```
