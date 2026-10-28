extends Plant000Base
class_name Plant007Chomper

## 咬合时重新查询范围内目标，避免攻击已抬头的僵王。
@onready var detect_component: DetectComponent = $DetectComponent

## ── 换皮：Q 版醉仙客 ────────────────────────────────────────────────────
## 只换形象，状态机（idle / bite / chew / swallow）与逻辑锁（is_chewing）原样沿用，
## 所以这里**不改 .tscn 结构**，散件全部在运行期隐藏，回退只需把 chomper_enable 置 false。
## [br]图鉴详情页走 IsShow 实例化的是本场景，换装挂在 `_ready` 才能一起生效。
@export var chomper_enable: bool = true

## ── 美术资产 ───────────────────────────────────────────────────────────
## 2026-10-26 第三版立绘：用户指定的「侧持青玉葫芦」造型。
## [br]源图为 1024×1536，已做两步处理才进engine：
## [br]1) **头顶补白**：原图内容上边界只离画布 2.9%，直接烘 2 倍图会让头发顶到格子边缘；
## [br]   现在按内容包围盒重排到 947×1706 画布（上下各留 10% 高、左右各 8% 宽）。
## [br]2) **烘成战场 2 倍图**：112 × 2 = 224 高，运行时 art_scale = 0.5，
## [br]   与豆蔻／朝阳童子／镇山老翁同一套做法，不让引擎做小倍率缩小把线稿糊成灰边。
const ART_IDLE := preload("res://assets/image/character/chomper/zuixianke_idle.png")
## **开盖版立绘**：与 ART_IDLE 逐像素相同，只有葫芦口那一小块不同 ——
## [br]塞子被擦掉、换成「玉色口沿 + 深青内腔」的开口。
## [br]为什么必须再出一张：拔盖如果只靠"叠一层塞子飞走"，立绘上原本那个塞子
## [br]会一直待在口上不动（2026-10-26 实测就是这个现象，用户说的"没演出来"）。
## [br]两张图逐像素对齐，切图时只有葫芦口那一小块（x103..116 / y73..97）发生变化，
## [br]看不出拼接。
## [br]⚠️ 2026-10-26 第二轮修正：第一版开口的轴心放在 x≈110.5，而盖着版里塞子的轴心
## [br]是 x≈108.5（实测 y82..88 的柱体中位数）—— 偏右 2px、偏宽 1px，竖着拿的葫芦口
## [br]读起来像「一块横躺的环形亮片」。现在按塞子实际轴心重画：
## [br]· 口沿外半径 4.6、内腔 3.5，边界正好落在塞子原位的左右外沿；
## [br]· 口沿色压到 (176,190,170) —— 原来的 (212,217,199) 太亮，1:1 图鉴里读成白圆环；
## [br]· 内腔 (46,66,58) + 洞底 (26,38,33)，对比度约 145，缩到战场 10px 仍读得出"洞"。
const ART_IDLE_OPEN := preload("res://assets/image/character/chomper/zuixianke_idle_open.png")
## 立绘贴图的像素高度（烘焙后）。
const IDLE_TEX_H := 224.0
## ⚠️ **立绘实体（人物本体）在贴图里的纵向范围**，单位=贴图像素。
## [br]补白之后上下各有约 8% 的透明边，人物实际只占 18..205 这 188 行。
## [br]**缩放必须以这个实体高度为准**，不能拿 IDLE_TEX_H 算 —— 否则人物会小一圈，
## [br]而且因为 Sprite2D 是居中对齐的，多出来的下边距会让脚底离地悬空。
## [br]（2026-10-26 踩过：按画布高算出来实体只有 94，比设计的 112 矮了 16%。）
## [br]2026-10-26 换朝右版贴图（137×224）后按 alpha>8 实测重测：
## [br]bbox = x14..121 / y18..205 → 实体 108×188（此前误记成 16..207 = 192，
## [br]差 4px，会让战场里的人物略偏大 2.3%、脚底下沉 1.2px）。
const IDLE_FIG_TOP := 18.0
const IDLE_FIG_BOTTOM := 205.0
## 实体在贴图里的高度（像素）。
const IDLE_FIG_H := IDLE_FIG_BOTTOM - IDLE_FIG_TOP + 1.0  # = 188
## 战场显示高度，这里的 112 指的是**人物本体**的高度，不含透明留白。
## [br]与原版散件（96.9）比，醉仙客是站姿全身，给 112 让第 7 株看得出更有分量，
## [br]又不会压住后排。图鉴卡／选关缩略图若要用同一视觉量级，按 112 折算即可。
## [br]art_scale = 112 / 188 ≈ 0.596（实体高 188 而非画布 224）。
const CHOMPER_H := 112.0

## 木塞：程序化绘制的独立塞子，**盖着态与拔盖态都由这一层负责**。
## [br]⚠️⚠️ 2026-10-26 第八轮 —— 前七轮的理解已全部作废，留档备查：
## [br]· 前七轮的前提是「立绘本身带着塞子，这层只在拔盖时接管」；
## [br]· 但立绘上那个东西根本不是塞子，是**竖在葫芦口上的一根 7×15 细管**（像葱白/吸管），
## [br]  它自己带一圈 alpha 40~200 的灰白抗锯齿边（x103/x113 两列整条），
## [br]  那圈灰边就是用户连说四轮的"白色方框 / 抠图没干净"；
## [br]· 只要还走"从立绘切一块"的路，无论怎么切都会把这圈灰边带进去。
## [br]现在的分工：
## [br]· 立绘（`zuixianke_idle.png` / `_open.png`）里的颈管/空口**已整根抹成透明**
## [br]  （`_tmp/fix_neck.py`），葫芦在 y77 自然收口；
## [br]· 塞子由这张 56×104 的程序化贴图**独占负责**，盖着时就在葫芦口上，
## [br]  拔盖时从这里飞走，盖盖时飞回来 —— 全程只有它一个"塞子"，
## [br]  不存在"两层叠加 / 交接瞬间跳变 / 切图带边"这三种老问题。
## [br]（原注释留档）木塞：从立绘葫芦口上原位裁下来的独立图层，用于「拔盖」演出。
## [br]· 拔盖时 → 从原位出现，盖住立绘那个塞子，然后带着它一起飞走。
## [br]视觉上就是「葫芦口上的塞子被拔下来了」，飞走后露出的是**已抹净的葫芦口沿**。
## ⚠️⚠️ 2026-10-26 第七轮 —— **彻底不再从立绘里切图，改成一个独立画出来的塞子**。
## [br]前六轮都是「从 idle.png 里抠一块」，用户每一轮反馈的都是同一句话：
## [br]「抠图没抠干净，有白色边框，特别明显」。
## [br]看到 4.5 倍放大图才明白根因：立绘里那根塞子是 **8×15 像素的细玉柱**，
## [br]它和葫芦口沿的高光带在像素上是**连着的**。只要走"切图"这条路，
## [br]就必然带一圈口沿碎片；那片东西是灰度渐变块、没有轮廓，
## [br]贴在草地上就是一块脏补丁 —— 所谓"白边"，本质是"切下来的东西不像塞子"。
## [br]现在这张图是 `_tmp/gen_cap_final.py` **从零画**的：
## [br]圆头 + 收颈 + 鼓肩 + 收底，带左侧暗面、右侧亮面、颈部暗环，
## [br]轮廓完全由代码定义，边缘天然干净（画布最外一圈 alpha 强制 0）。
## [br]贴图 56×104，是立绘那根 8×15 的 7 倍精度，运行时 1:1 显示。
const ART_CAP := preload("res://assets/image/character/chomper/zuixianke_cap_new.png")
## ⚠️ 塞子贴图的**最高原则：整张图上不能有任何"低 alpha + 非黑 RGB"的像素**。
## [br]因为拔盖时它要原地旋转 200°，双线性插值会把边缘像素的 RGB 和相邻像素混色 ——
## [br]alpha=2、(127,127,127) 这种几乎看不见的噪声，转起来会被放大成一道灰白斜边，
## [br]就是用户反复说的"会出现白色边框，特别明显"。
## [br]生成脚本 `_tmp/fix_cap2.py` 做了三件事：alpha<24 清零、边缘 RGB 拉向实心中位色、
## [br]最外一圈强制 alpha=0。以后重切塞子**必须走这个脚本**，不要直接 crop。
## 塞子**中心**在立绘贴图内的坐标（单位=立绘贴图像素）。
## [br]⚠️ 2026-10-26 第七轮 —— 这次是**量出来的，不是猜的**，量法写清楚：
## [br]· 把 `zuixianke_idle_open.png`（开盖图）里那个**墨绿空洞**筛出来
## [br]  （条件：alpha>200 且亮度<80），实测范围 **x99..111 / y74..92 → 13×19**；
## [br]· 把两张图逐像素相减，差值为「塞子 + 口沿」，实测 **x104..112 / y77..93 → 9×17**；
## [br]· 两者中心几乎重合：(105,83) 与 (108,85)。
## [br]塞子要盖住的就是那个洞口，所以取**洞口中心 (105, 83)**。
const CAP_IN_ART := Vector2(105.0, 83.0)
## 塞子贴图的像素尺寸（贴图文件本身，56×104）。
## [br]⚠️ **这是"源图尺寸"，不是"显示尺寸"**。显示尺寸由下面的
## [br]`CAP_SHOW_SIZE` 决定，`_cap_home_scale()` 负责把源图缩到显示尺寸。
## [br]为什么要分开：源图给大（56×104）才有足够精度画圆头和暗面，
## [br]显示尺寸只有 9×17（和葫芦洞口一样大），直接画 9×17 就是一堆方块。
const CAP_TEX_SIZE := Vector2(56.0, 104.0)
## 塞子在立绘贴图坐标系下的**目标显示尺寸**（必须盖住洞口）。
## [br]取自上述实测：洞口 13×19、塞子+口沿 9×17。塞子比洞口略大一点点，
## [br]边缘才能压住口沿、不留缝 —— 取 **12×20**。
const CAP_SHOW_SIZE := Vector2(12.0, 20.0)

## ── 拔盖演出 ────────────────────────────────────────────────────────────
## ⚠️⚠️ 2026-10-27 重做 —— 用户反馈：「出场拔盖子的动作看着很模糊，其实不太能看出来
## [br]是拔盖子的动作，因为我是设计的人才能知道他在干嘛」。
## [br]
## [br]逐项查下来，**四个原因叠在一起**，缺一个都读不出来：
## [br]① **塞子太小**：显示尺寸 12×20 贴图像素 × 0.596 ≈ **7×12 屏幕像素**。
## [br]   这是一个指甲盖大小的方块，60fps 的战斗视距下人眼抓不到它「走了」；
## [br]② **没有预备动作**：旧版第一帧就开始上挺、塞子同时飞。观众的注意力
## [br]   还没落到葫芦口上，事件已经结束了 —— 动画里这叫缺 anticipation，
## [br]   是最典型的「只有作者看得懂」；
## [br]③ **打开之后口部没有变化**：我逐像素比过两张立绘，
## [br]   差异只有 **9 个像素**（x107..111 / y92..93）—— 开盖图上根本看不出「洞」。
## [br]   所以「塞子飞走」没有任何后续视觉支撑，读起来就是「有个小黑点没了」；
## [br]④ **待机呼吸在抢 `_art.position:y`**：旧版上挺只给 9px，而呼吸 tween
## [br]   一直以 ±0.7px 写同一个属性，两条 tween 互相覆盖 —— 实际看到的位移还要打折。
## [br]
## [br]动画语言上的原则：**大姿态传达意图，小细节传达执行**。
## [br]旧版把全部预算压在「塞子」这一个 7px 的小细节上，所以只有设计者知道在干嘛。
## [br]这一版改成三段式（预备 → 发力 → 跟随），并把塞子本身做得能读：
## [br]· 起手先让塞子**隆起放大 1.4 倍并上提** —— 观众先锁定「葫芦口有个东西」；
## [br]· 再把整株**下沉 → 猛地挺起 20px 并后仰** —— 发力的是人，不是那个小方块；
## [br]· 塞子**弹出放大到 1.95 倍**、带 200° 翻滚沿抛物线飞出、身后拖 3 道残影；
## [br]· 口部喷出两团气 —— 这是「容器被打开」能在这个比例下传达的唯一大尺度信号。

## ── 整株三段姿态（游戏内像素 / 度 / 秒）──────────────────────────────────
## 预备：整株往下沉多少、往前压多少度。
## [br]**这一段是本轮新增的核心**。没有预备，观众不知道「接下来要发生什么」；
## [br]有预备，即使后面拍得再快，眼睛也已经先锁定葫芦口了。
const CAP_ANTIC_PX := 5.0
const CAP_ANTIC_LEAN := 2.5
const CAP_ANTIC_TIME := 0.16
## 发力：上挺高度。旧版 9px（≈身高 8%）→ 现在 **20px（≈身高 18%）**。
## [br]20 是上限：再高脚会离格（立绘缩放基准是「内容底边＝脚底」，上挺等于把整个人抬起来），
## [br]超过约 26px 就会看到脚下露缝。
const CAP_LIFT_PX := 20.0
## 上挺同时**后仰** 5°（负 = 逆时针 = 往后）。
## [br]⚠️ 方向别写反：拔盖是「往上、往后拉」，前倾会读成「往下压」——
## [br]正好是盖盖的意思。
const CAP_LIFT_LEAN := -5.0
const CAP_LIFT_TIME := 0.16
## 落回。给 0.24 秒慢慢松下来，比上挺长，读作「用完力了」。
const CAP_SETTLE_TIME := 0.24

## ── 塞子：隆起 → 弹出 → 抛物线翻滚 ──────────────────────────────────────
## 预备段塞子先放大并上提，像被两根手指捏住准备拔。
## [br]1.4 倍 ≈ 10×17 屏幕像素 —— 刚好从「背景噪点」跨到「看得出形状」。
const CAP_BULGE_SCALE := 1.40
const CAP_BULGE_LIFT := 3.0
const CAP_BULGE_TIME := 0.16
## 弹射瞬间的放大（"啵"地一下）。
## [br]换算核对一遍，避免又写错量纲：显示尺寸 12×20 贴图像素 × `_art_scale` 0.596
## [br]≈ **7×12 屏幕像素**；放大 1.95 倍 ≈ **14×23 屏幕像素**。
## [br]源图 56×104 对 14px 宽仍有 4 倍精度余量，不会糊。
const CAP_POP_SCALE := 1.95
const CAP_POP_TIME := 0.08
## 飞行轨迹：先向右上抛到顶点，再向右下坠。单位 = 立绘贴图像素。
## [br]（`_cap_clip` 的父节点是 `_art`，所以这里的数值就是贴图像素，不用再乘缩放）
const CAP_ARC_UP := Vector2(14.0, -30.0)
const CAP_ARC_DOWN := Vector2(38.0, -6.0)
const CAP_FLY_UP_TIME := 0.15
const CAP_FLY_DOWN_TIME := 0.19
## 拔开之后塞子停在哪（= 两段之和，贴图像素）≈ 屏幕 (31, -21)。
## [br]盖盖动画就从这里起飞回葫芦口。
## [br]⚠️ 2026-10-26 第六轮留档：曾写到 `(34, -108)`，那会飞到头顶上方 75px 的空中，
## [br]在窗口里根本看不见，玩家只觉得「塞子凭空消失了」。
const CAP_PULL_OFFSET := Vector2(52.0, -36.0)
## 飞行中的翻滚角度（度，正 = 顺时针）。
## [br]⚠️⚠️ 这一条**推翻了 2026-10-26 第四轮的结论**，所以把当时的理由和推翻依据一起留着：
## [br]· 当时写的是「彻底不做旋转」，理由是塞子**从立绘里切出来**，边缘带一圈
## [br]  alpha 40~200 的灰白抗锯齿边，一转就被插值放大成一道白框；
## [br]  并且当时用 `clip_children` 裁剪，转 90° 会把柱子切成两条直线断面。
## [br]· 现在这两个前提**都不成立了**：
## [br]  ① 塞子是程序化生成的独立贴图（`zuixianke_cap_new.png`），
## [br]     实测外圈一整圈 alpha = 0、低 alpha 像素只有 2 个且 RGB 已被拉向实体色
## [br]     (174~202，实体色 208/198/180)，旋转不会冒出任何新颜色；
## [br]  ② 这一层**没有** `clip_children` 了，不存在削形。
## [br]· 而且不转就是读不出来：一个保持竖直的小方块平移，观众只能读到「噪点消失」；
## [br]  翻滚才读得出「一个实体物件被拔下来了」。所以这一版转 200°。
const CAP_SPIN_DEG := 200.0
## 残影：数量 / 间隔（秒）。给「被甩出去」一个速度感，同时把飞行路径描出来。
const CAP_GHOST_COUNT := 3
const CAP_GHOST_STEP := 0.035

## ── 口部喷气：这一版唯一能读出来的「打开」信号 ───────────────────────────
## [br]为什么不靠「把口画空」：实测洞口只有 13×19 贴图像素，缩到战场是
## [br]**7.7×11 屏幕像素**，两张立绘在口部又只差 9 个像素 ——
## [br]在这个比例下，「口变空了」物理上不可能被看出来。
## [br]但「气」可以放大：起始直径 = CHOMPER_H × 0.14 × 2 ≈ 31 贴图像素
## [br]≈ **19 屏幕像素**，扩到 2.1 倍 ≈ **39 屏幕像素**（角色高才 112），
## [br]比塞子大 5 倍 —— 玩家先看到「噗」的一下，才回头注意到塞子已经没了。
## [br]这也符合直觉因果：拔开瓶塞，第一反应就是「有气出来」。
const CAP_PUFF_RADIUS := 0.14
const CAP_PUFF_GROW := 2.1
const CAP_PUFF_RISE := 16.0
const CAP_PUFF_TIME := 0.34
const CAP_PUFF_ALPHA := 0.72

## 盖盖：比拔盖快，符合「随手一按」。
const CAP_PUSH_TIME := 0.26

## ── 开场：上场那一刻先演一次拔盖 ─────────────────────────────────────────
## 用户要求「醉仙客出场应该把酒葫芦的盖子拔下来，然后蓄势待发」。
## [br]所以登场时**先显示盖着的塞子**，再演一次拔盖 —— 玩家才看得到「这个动作发生过」。
## [br]0.35 秒是「种植动画落定」的余量：种下去那一帧角色还在缩放，早于这个时间开演
## [br]会和种植动作叠在一起，反而更看不清。
const CAP_INTRO_DELAY := 0.35

## ── 开封光效：葫芦口"炸开"的一圈淡光 ────────────────────────────────────
## 塞子只有 7 像素宽，光靠它自己动不够 —— 必须在葫芦口给一个**大尺度的信号**，
## 玩家才知道"这株已经准备好可以吸了"。开盖时口沿亮一圈、盖盖时收掉。
## [br]半径按人物高的比例给（112 × 0.34 ≈ 38px），比塞子大 6 倍 ——
## [br]实测 0.16（≈18px）在战斗视距下只影响几十个像素，等于看不见，必须放大。
## [br]⚠️ 0.34 又偏大了：加色混合后整个葫芦上球被打成一片白，口也糊掉了
## [br]（2026-10-26 实机截图确认）。0.22（≈25px）刚好罩住口沿、不糊球体。
const MOUTH_GLOW_RADIUS := 0.22
## 光的颜色：取葫芦玉色的同族亮青，和整体仙侠清雅调一致，不用纯白（太跳）。
const MOUTH_GLOW_COLOR := Color(0.72, 0.96, 0.88, 0.85)
## 呼吸节奏（开盖期间常驻，提示"我在等"）。
## [br]⚠️ 峰值 alpha 不能给到 0.95：加色混合下会把葫芦口吃成纯白，
## [br]开盖和没开盖看起来一样。0.62 是"亮但还看得见那个洞"的上限。
const MOUTH_GLOW_BREATH_TIME := 0.9
const MOUTH_GLOW_ALPHA_MIN := 0.26
const MOUTH_GLOW_ALPHA_MAX := 0.62

## ── 开封环：拔盖/开盖瞬间从葫芦口炸出的一圈亮边 ─────────────────────────
## [br]光晕是"状态"（一直亮着，告诉玩家我在等），环是"事件"（只闪一次，
## [br]告诉玩家盖子刚被打开）。两者缺一：只有状态没有事件，玩家分不清
## [br]"它本来就这样"还是"它刚刚做了个动作"。
const MOUTH_RING_MAX_RADIUS := 0.46   # 0.46 × 112 ≈ 52px，从口沿扩到半个身子
const MOUTH_RING_TIME := 0.42
const MOUTH_RING_ALPHA := 0.9

## ── 图鉴详情页：立绘取景 ────────────────────────────────────────────────
## 图鉴是"静态档案"，只摆一张静物，所以取景要按**档案照**的标准来，而不是战场视距。
## [br]⚠️ 关键前提：`_idle_pivot.position` 原本是 `CHOMPER_FOOT_BODY = (-11.25, 0.9)`，
## [br]它是**战场格子里**的脚底落点。图鉴里角色根节点已经被 `panel_container`
## [br]摆到窗口内的 (100,120)，所以 pivot 的 y 是**相对角色根**的偏移量，
## [br]不是窗口坐标 —— 第一版直接写 196，等于把 196 叠加到 120 上，
## [br]人物整块被推出窗口下沿，只剩头顶露在外面（2026-10-26 实机截图确认）。
## [br]正确做法：只给"往下挪多少"和"放大多少"这两个**相对量**。
## [br]
## [br]实测基线（通用落点、无额外偏移、缩放 1.0）：人物占窗口 y 21~171。
## [br]想要的效果：脚底落到 y≈196、头顶再往上顶一点 → 身高从 150 涨到约 165。
## [br]· 缩放 1.10 → 实体高 112 × 1.10 ≈ 123（这里 112 指的是立绘实体，窗口里是 1:1）
## [br]· 下移量 = 196 − 171 = 25 窗口像素，再减去缩放带来的额外身高 ~15 → 约 10
## [br]最终：`ALMANAC_SHOW_SCALE = 1.10`、`ALMANAC_SHOW_DROP = 10`
## [br]⚠️ 改这两个数之前先记住：`CharacterBg` 的可见区就是 0..200，没有任何缓冲。
const ALMANAC_SHOW_SCALE := 1.10
## 在图鉴里，在角色根节点的基础上把整株往下压多少（像素，窗口坐标）。
## [br]背景：通用落点让脚底停在 y≈171，下面空 29px 显得"挂在画框中间"。
## [br]压 10px 后脚底落在 y≈196 附近，站到画面底、又没被 clip_children 切到。
const ALMANAC_SHOW_DROP := 10.0
## 图鉴里的水平落点（像素，窗口坐标）。
## [br]⚠️ **不能沿用 `CHOMPER_FOOT_BODY.x = -11.25`** —— 那个 x 是「散件包围盒中心」，
## [br]目的是让换装前后在**战场格子**里左右站位不偏；而落地阴影 `Shadow` 是基类场景里的
## [br]固定节点（x=0），图鉴窗口中它正好落在 x=100（画面正中）。
## [br]2026-10-27 实测（把 7 株植物逐株渲进 200×200 窗口、扫 alpha 求实体框）：
## [br]· 豆蔻 103.0 / 朝阳 100.5 / 并蒂 102.0 / 镇山 100.5 / 裴无咎 101.0 / 雪清 99.5
## [br]· **醉仙客 91.5** —— 人比自己的影子左 12px，在详情页里一眼就看得出"没站正"。
## [br]差值 = 11.25 × 1.10(ALMANAC_SHOW_SCALE) ≈ 12.4，与实测完全吻合。
## [br]所以图鉴里把 x 归零：人物中心回到窗口正中，与阴影重合。
## [br]战场仍用 -11.25（那是原版散件的重心），改动只发生在图鉴这一条路径上。
const ALMANAC_SHOW_CENTER_DX := 0.0

## ── 咀嚼晃动 ───────────────────────────────────────────────────────────
## 用户 2026-10-26 定的三段曲线（占 eat_CD = 30 秒）：
## [br]0~5 秒 **剧烈**  → 5~15 秒 **微弱** → 15~30 秒 **基本不动**。
## [br]为什么整株一起晃而不是只晃葫芦：立绘里手是**正面抓着葫芦上球**的
## [br]（四指从左侧包过去、拇指扣右侧），手和葫芦的像素互相交叠，
## [br]单独抠葫芦一定会留下手的轮廓，一动就穿帮。整株一起晃反而更像"被葫芦带着抖"。
const CHEW_FIERCE_END := 5.0
const CHEW_WEAK_END := 15.0
## 各段幅度（度 / 立绘贴图像素）。
const CHEW_FIERCE_DEG := 7.0
const CHEW_FIERCE_PX := 22.0
const CHEW_WEAK_DEG := 2.2
const CHEW_WEAK_PX := 6.0
## 每个来回的时长（秒）。剧烈段快、微弱段慢，静止段不再动。
const CHEW_FIERCE_STEP := 0.26
const CHEW_WEAK_STEP := 0.62

## ── 吞不掉的大家伙：举葫芦连打 ─────────────────────────────────────────
## 用户 2026-10-26 定的口径（覆盖旧版 0.05s × 6 跳）：
## [br]· 巨人僵尸（[Zombie024Gargantuar]）与僵王博士（[ZB000Base]）体积太大，**永远吞不掉**；
## [br]· 改为「拿葫芦对准它」持续攻击，**每 1.5 秒一次、每次 200 伤害**；
## [br]· 这条支路**不触发**开盖 / 盖盖 / 晃动 —— 葫芦一直对着目标，不进「吸收」流程。
const HEAVY_TICK_DAMAGE := 200
const HEAVY_TICK_INTERVAL := 1.5
## 举葫芦的抬升量（立绘贴图像素）。倾角统一交给 [constant ATK_BODY_LEAN] 与
## [constant MOUTH_PRESS_DEG]，这里不再单独给一份，避免两处角度叠成两份前倾。
const HEAVY_AIM_LIFT := 10.0
const HEAVY_AIM_TIME := 0.20

## ── 吸入演出：把葫芦口压到僵尸身上，而不是把僵尸「拽进瓶子」 ───────────
## ⚠️⚠️ 2026-10-27 —— 上一版（`.bak_20261026`）有一整套「举起葫芦 → 拔塞 → 倾口 → 灌」
## 的动作设计，本轮**全部删除**。原因不是参数没调好，是这条路从结构上就走不通：
## [br]· 它靠「在立绘上叠一层放大 1.5 倍的葫芦，去遮住立绘里本来就画着的那个葫芦」，
## [br]  所以葫芦的位移被锁死在十几像素、倾角锁死在 11° 以内 —— 屏幕上根本读不出「举起」；
## [br]· 更致命的是**葫芦口的位置**：这一版立绘的葫芦口在身体右上方、离僵尸大约 40 屏幕px，
## [br]  而要「吸」，口必须压到僵尸身上，位移需求远超遮盖余量，物理上做不到；
## [br]· 于是实机上看到的就是「葫芦在胸口抖两下，然后僵尸凭空消失」—— 用户说的违和。
## [br]
## [br]这一版换了因果：**不演「僵尸被吸进瓶子」，只演「僵尸被吸进瓶口」**，
## [br]把「进瓶子」这一步交给盖子和摇晃去交代。三件事解决违和：
## [br]1) 葫芦**真的压到僵尸身上**（不再有遮盖约束，因为不再叠道具层）；
## [br]2) 僵尸**在壶口被吞掉的同一帧**沿气管方向缩进壶口 —— 是「缩进去」，不是「凭空消失」；
## [br]3) 壶口前加一圈**向心收缩的气环**，先有「吸力」，再有「消失」，顺序对了才不违和。
## [br]
## [br]葫芦口在图上的倾斜度（度，正 = 顺时针 = 口朝右下 = 朝僵尸）。
## [br]实测：口部上沿 y92..93、左右 x107..111，轴线基本竖直，向右探头约 10°。
const MOUTH_TILT_DEG := 10.0
## 葫芦支点（= 葫芦口）离人物支点的距离（立绘贴图像素）。
## [br]由 CAP_IN_ART（口心 105,83）减去人物实体水平中心算出：
## [br]实体 bbox x14..121 → 中心 67.5，所以口在人物中心右 37.5、上 30.5。
## [br]换算成游戏内像素：37.5 × 0.596 ≈ 22.4、30.5 × 0.596 ≈ 18.2。
const MOUTH_OFFSET_PX := Vector2(37.5, -30.5)

## 葫芦支点最大前伸量（立绘贴图像素）。
## [br]预算：贴图右边界到人物实体右沿只有 (121-105) = 16px，右移 40 已把半只手推出格子，
## [br]靠 `BodyCorrect` 的 `clip_children` 裁掉 —— 只切到手部，头在左上不受影响。
## [br]40 贴图像素 ≈ 24 游戏内像素，正好把壶口从「胸前」送到僵尸下巴附近。
const MOUTH_REACH_PX := 40.0
const MOUTH_DIP_PX := 12.0
## 口朝下压多少度（叠加在 MOUTH_TILT 上，合计约 32°，口正对脚下的僵尸）。
const MOUTH_PRESS_DEG := 22.0
## 整株前倾（度，正 = 顺时针 = 朝僵尸）。
## [br]⚠️ 与上一版差了 11°：那版记的是「负 = 前倾」，实测立绘朝右、僵尸在右，正向才是朝它压。
const ATK_BODY_LEAN := 6.0

## ── 吸入节拍（秒，从咬合关键帧 `_eat_zombie` 起算）──────────────────────
## [br]窗口 = (2.0 − 1.41667) / TimeScale(1.15) ≈ **0.507 秒**，主角（僵尸缩进壶口）
## [br]必须在此之前发生，否则 Bite 会先收尾转 chew，玩家看到的仍是「后消失」。
## [br]· 0.00 ~ 0.20 压壶：壶口从胸前压向僵尸（同时整株前倾），气环从外向口收
## [br]· 0.20       主角：僵尸开始被吸进壶口
## [br]· 0.20 ~ 0.44 继续收：僵尸缩进壶口（0.24 秒，与 SUCTION_TICK_COUNT 同步走完）
## [br]· 0.44 ~ 0.507 壶口已在目标身上，剩下的窗口用来「停住」
const ATK_PRESS_TIME := 0.20
const ATK_SUCK_TIME := 0.24
## 吞不掉的目标（巨人 / 僵王）只需要压到嘴边，不需要缩进去。
const ATK_FORCE_PRESS := 0.34

## 僵尸被吸进壶口的演出参数。
## [br]缩到 0.25 而不是 0：视觉上要「缩进嘴里不见」，而不是「缩成一个点」——
## [br]点是「变小」，缩进容器才是「被吃掉」。剩下那一点由壶口本身和随即盖上的盖子吃掉。
const SUCK_SCALE := 0.25
const SUCK_TIME := 0.24
## 僵尸在吸的过程中往壶口方向的横向收拢（游戏内像素）。
## [br]给僵尸一点「被拽住」的位移，才不像它自己走进去的。只给 6，多了会穿帮。
const SUCK_PULL_PX := 6.0
## 吸进去之后顺手把僵尸的移动与受击全部停掉，防止这一段里它还在往左走。
const SUCK_MOVE_FACTOR := true

## 吸气环（向心收缩的细环）：告诉玩家「有吸力」。
## [br]贴图 `zuixianke_gust.png` 是 64×64 的细环（峰 r=0.70、中心全透明），
## [br]所以直径换算就是「目标直径 / 64」，和光晕同一套口径。
const GUST_START_RADIUS := 0.42   # × CHOMPER_H ≈ 47px
const GUST_END_RADIUS := 0.10     # ≈ 11px，收到壶口上
const GUST_TIME := 0.30
const GUST_PEAK_ALPHA := 0.55
const GUST_COLOR := Color(0.80, 0.94, 1.0, 1.0)

## 咀嚼时整株的挤压幅度（纵向压缩比例）—— 保留原设计，让"还在嚼"多一层体感。
const CHEW_BODY_SQUASH := 0.05

## 脚底在 Body 局部坐标里的位置。
## [br]⚠️ **不是** BodyCorrect 的 position。那 (-33, -79) 只是散件的绘制原点，
## [br]散件自身从原点往下画到 y≈+80，所以内容底边落在 Body 局部的
## [br]BodyCorrect.position.y + 约 79.9 = **0.9**（离线逐件按 position/scale/贴图尺寸算过）。
## [br]若把立绘脚底对齐到 -79，人整体会悬空 80px 站在这一格上方 —— 实测确认过。
## [br]x 取的是散件包围盒水平中心 (-49.8 + 27.3) / 2，让换装前后左右站位也不偏。
const CHOMPER_FOOT_BODY := Vector2(-11.25, 0.9)

## 待机呼吸：绕脚底轻摆 + 上下起伏，和豆蔻的 2.2°／0.8px 同档。
## [br]醉仙客手里拎着葫芦，晃幅再大就会像在晃酒，所以略收。
const IDLE_SWAY_DEG := 1.6
const IDLE_SWAY_TIME := 1.5
const IDLE_BREATH_PX := 0.7
const IDLE_BREATH_TIME := 1.0

var _art: Sprite2D = null
var _idle_pivot: Node2D = null
var _art_scale: float = 1.0
var _art_local_y: float = 0.0

## 塞子（独立图层）。
## [br]结构是**两层**：`_cap_clip`（外层，载体：位置 + 压扁 + 淡出）
## [br]→ `_cap`（内层，纯贴图，不改任何变换）。见 `_build_cap()`。
var _cap: Sprite2D = null
## 塞子的外层容器。⚠️ **不裁剪**，只负责平移 / 横向压扁 / 淡出。
var _cap_clip: Node2D = null
## 塞子当前的 tween（拔/盖），互斥用。
var _cap_tween: Tween = null
## 拔盖 / 盖盖时整株三段姿态的 tween（`_play_uncap_body` / `_play_cap_body`）。
## [br]⚠️ 必须留句柄：它和待机呼吸抢 `_art.position:y`，和解时必须能 kill。
var _body_tween: Tween = null
## 盖子是否处于"已拔开"状态。登场即为 true（用户要求：登场就开盖等僵尸）。
var _cap_opened: bool = false
## 葫芦口"开封"光晕（开盖时常驻呼吸，盖盖时收掉）。
var _mouth_glow: Sprite2D = null
## 光晕的呼吸 tween。
var _mouth_glow_tween: Tween = null
## 拔盖/开盖瞬间的"开封环"（闪一次就消失，是"事件"不是"状态"）。
var _ring_burst: Sprite2D = null

## 咀嚼晃动的 tween（现在动的是 _idle_pivot，整株一起）。
var _chew_shake_tween: Tween = null
## 咀嚼期整株挤压的 tween。
var _chew_body_tween: Tween = null
## 待机轻摆 / 呼吸的两条无限循环 tween。
## [br]⚠️ 必须留句柄：它们和「咀嚼晃动」抢同一个属性（`_idle_pivot.rotation`），
## 谁后写谁生效 —— 详见 [method _set_idle_sway_paused]。
var _idle_sway_tween: Tween = null
var _idle_breath_tween: Tween = null
## 举葫芦连打的循环 tween（巨人/僵王专用）。
var _heavy_tween: Tween = null
## 是否正在对巨人/僵王连打，防止重复开启循环。
var _heavy_attacking: bool = false

## ── 吸入演出 ───────────────────────────────────────────────────────────
## 葫芦支点：挂在 `_art` 下，原点就在**葫芦口**上，所有压壶动作都绕它转。
## [br]挂在 `_art` 下而不是 `_idle_pivot` 下的理由：`_art` 的局部坐标单位
## [br]= 立绘贴图像素（和塞子 `_cap_clip` 完全同一套口径），位置换算不用再乘缩放。
var _mouth: Node2D = null
## 吸气环（细环，向心收缩）。
var _gust: Sprite2D = null
## 咬合演出 tween。
var _atk_tween: Tween = null
## 还没演完的僵尸（吸进去之后要补一次终点，防止体积小到 0 还挂在场景里）。
var _suck_target: Character000Base = null
## 正在被吸的僵尸（防止同一次咬合里重复开演）。
var _sucking: Character000Base = null
## 被吸前的位置。植物中途死亡时要把它放回这里。
var _suck_start_global: Vector2 = Vector2.ZERO

## 咀嚼时间计时器
@onready var chew_timer: SpeedTimer = $ChewTimer
## 啃咬伤害
@export var eat_attack:int = 1800
## 吞咽后的消化秒数。用户 2026-10-26 定为 **30 秒**（原版 40）。
## [br]场景里的 plant_007_chomper.tscn 也已同步改成 30.0；这里留同一默认值兜底。
@export var eat_CD :float = 30

@export_group("动画状态")
## 是否啃咬（保留原状态机用，换皮后不再换帧）
@export var is_bite := false
## 是否咀嚼
@export var is_chewing = false


func ready_norm() -> void:
	super()
	## 基础咀嚼时间不含倍率，进入角色时同步已有速度因素。
	chew_timer.base_wait_time = eat_CD
	owner_update_speed(GlobalUtils.get_dic_product(influence_speed_factors))

func ready_norm_signal_connect():
	super()
	signal_update_speed.connect(owner_update_speed)
	detect_component.signal_can_attack.connect(change_is_attack.bind(true))

## 速度改变保留剩余咀嚼进度，零速由计时器暂停，避免除零。
func owner_update_speed(speed_product:float):
	chew_timer.set_speed_scale(speed_product)

## 改变是否正在攻击,即攻击范围内是否有敌人
func change_is_attack(is_attack:bool):
	if is_attack:
		## 不在咀嚼状态,并且不在啃咬状态
		if not is_chewing and not is_bite:
			is_bite = true

## 换装入口。挂在 `_ready`（而不是 ready_norm）才能覆盖三条初始化路径：
## 战场是 ready_norm、图鉴详情页是 ready_show、禅境花园是 ready_garden。
func _ready() -> void:
	super()
	if not chomper_enable:
		return
	_apply_chomper_art()


## 植物死亡（被啃死 / 被炸 / 被铲）。
## [br]⚠️ 必须在这里收尾「正在吸的那只僵尸」：`_start_suck` 是一个 await 链，
## [br]植物一旦在吸气途中消失，链会在 `is_inside_tree()` 处断掉 ——
## [br]那半截**已经被缩小的僵尸**就永久留在场上（体积 25%、不再移动、也不再被判定）。
## [br]这是本轮新增演出带来的一类新残留，属于必须堵的口子。
func character_death() -> void:
	if is_instance_valid(_suck_target):
		_restore_suck_target(_suck_target)
	_suck_target = null
	_sucking = null
	_pending_target = null
	super()


## 把被吸到一半的僵尸放回去（体积与位置）。
## [br]只还原表现，不改变它的血量 —— 伤害本来就没结算（伤害在吸完才扣）。
func _restore_suck_target(enemy: Character000Base) -> void:
	if not is_instance_valid(enemy) or not is_instance_valid(enemy.body):
		return
	if enemy.is_queued_for_deletion():
		return
	var t: Tween = create_tween()
	t.set_parallel(true)
	t.tween_property(enemy.body, "scale", Vector2.ONE, 0.16)
	t.tween_property(enemy, "global_position", _suck_start_global, 0.16)


## 隐藏散件版大嘴花，换成整图立绘；不改 .tscn 结构，回退只需把 chomper_enable 置 false。
## [br]挂到 Body（BodyCorrect 的父节点）而不是 BodyCorrect 下：状态机把 BodyCorrect
## [br]里每个子精灵的 visible / scale 都写了轨道，立绘挂进去会被 idle 的 Start 帧一起改掉。
func _apply_chomper_art() -> void:
	if is_instance_valid(_art):
		return
	var body_correct: Node2D = get_node_or_null("Body/BodyCorrect") as Node2D
	if body_correct == null:
		body_correct = find_child("BodyCorrect", true, false) as Node2D
	if body_correct == null:
		push_warning("醉仙客：找不到 BodyCorrect，跳过换装")
		return

	# 1) 原散件整体隐藏（茎叶 + 上下颚 + 舌头 + 被吞僵尸的手臂，共 26 个 Sprite2D）
	body_correct.visible = false

	# 2) 支点落在脚底：绕脚底旋转才是原地晃，支点若在贴图中心脚会左右滑。
	var foot: Vector2 = CHOMPER_FOOT_BODY
	_idle_pivot = Node2D.new()
	_idle_pivot.name = "ZuixiankeIdlePivot"
	_idle_pivot.position = foot
	body_correct.get_parent().add_child(_idle_pivot)

	# 3) 几何：Sprite2D 默认居中。缩放按**人物实体高度**算，再把中心上移到
	#    「实体底边正好落在支点」的位置 —— 上下各 7.1% 的透明边一起参与换算。
	_art_scale = CHOMPER_H / IDLE_FIG_H
	# 实体中心在贴图里的 y（相对画布中心为正向下）
	var fig_center_in_tex: float = (IDLE_FIG_TOP + IDLE_FIG_BOTTOM) * 0.5 - IDLE_TEX_H * 0.5
	# 想让实体底边落在 pivot 原点：中心须上移 fig_center_in_tex * scale + CHOMPER_H/2
	_art_local_y = -(CHOMPER_H * 0.5 + fig_center_in_tex * _art_scale)

	_art = Sprite2D.new()
	_art.name = "ZuixiankeArt"
	_art.texture = ART_IDLE
	_art.scale = Vector2(_art_scale, _art_scale)
	_art.position = Vector2(0.0, _art_local_y)
	_idle_pivot.add_child(_art)

	# ⚠️ 立绘的贴图中心在人物实体水平中心右 19px（实体 bbox x14..121，中心 67.5，
	# [br]而画布宽 137）。所以 Sprite2D 一旦改变位置，人物会整体左移。
	# [br]吸入演出不能挪立绘本身（那会连脚一起滑出格子），只能挪 `_art` 的**父级**
	# [br]（`_idle_pivot`，它绕脚底转）和下面这个葫芦支点。
	_build_mouth()
	_build_cap()
	_build_mouth_glow()
	_build_ring_burst()
	_build_gust()
	_play_idle_motion()
	# ── 图鉴详情页：不做拔盖演出 ──
	# 图鉴窗口只有 200×200、立绘被放大到接近 1:1，拔盖那一串动作在那里
	# 全是大特写：塞子飞出去时能清楚看到它的切边、开封环糊在葫芦口上、
	# 光晕把上球打成一片白。用户 2026-10-26 反馈"点开看的时候贴图太明显"就是这个。
	# 图鉴是"静态档案"，不是"演示动画"，所以直接给**盖着**的状态：
	# 立绘自己带着塞子，不建叠加层、不开光晕，一张图就是一个完整的静物。
	if is_show:
		_apply_almanac_framing()
		_set_cap_state(true, true)
		return
	# 战场：用户要求**登场就把盖子拔开**。注意这里不是"直接置为开盖状态"——
	# 那样玩家永远看不到"拔"这个动作。先维持盖着（视觉上和立绘一致），
	# 过 CAP_INTRO_DELAY 再演一次真正的拔盖 → 蓄势待发。
	_set_cap_state(true, true)
	_play_intro_uncap()


## 建立葫芦支点。
## [br]⚠️⚠️ 2026-10-27 —— 这是本轮重做的关键节点，**为什么不再叠一层道具葫芦**：
## [br]旧方案（`.bak_20261026`）把葫芦从立绘里抠出来单独叠一层，靠「放大」把它盖住原位那个。
## [br]一旦放大成了播放动作的前提，位移就只能有十几像素、倾角只能有 11°，
## [br]因为再大就露出底下那个不动的葫芦。结果就是「葫芦在胸口抖两下」——
## [br]用户说的「把僵尸吸进酒葫芦的动作实在违和」。
## [br]
## [br]现在的做法：不叠任何贴图，只立一个**空支点**，原点就放在葫芦口上（CAP_IN_ART）。
## [br]葫芦在立绘里跟着它一起转 —— 是「连人带葫芦一起往前探」，
## [br]而不是「葫芦脱离人物单独飞」。所以位移可以给到 [constant MOUTH_REACH_PX]，
## [br]把壶口真的压到僵尸身上。这样因果关系才对：**壶口到了，僵尸才被吸进去**。
## [br]
## [br]坐标口径：挂 `_art` 下 → 单位是立绘贴图像素（与 `_cap_clip` 一致），
## [br]`_art` 自己负责乘 `_art_scale`，这里**不要**再乘一次。
func _build_mouth() -> void:
	if not is_instance_valid(_art):
		return
	_mouth = Node2D.new()
	_mouth.name = "ZuixiankeMouth"
	_mouth.position = _mouth_home()
	# 默认 z_index = 0：和立绘同层、但在立绘之后绘制，所以吸气环盖在人物上是可见的。
	_art.add_child(_mouth)


## 葫芦口的归位坐标（`_art` 局部，立绘贴图像素）。
func _mouth_home() -> Vector2:
	return CAP_IN_ART - ART_IDLE.get_size() * 0.5


## 壶口当前的世界坐标。吸僵尸时要拿它当终点，所以单独拎出来。
func _mouth_global() -> Vector2:
	if is_instance_valid(_mouth):
		return _mouth.global_position
	if is_instance_valid(_art):
		return _art.to_global(_mouth_home())
	return global_position



## [br]为什么放在这里而不是 `panel_container._apply_show_layout()`：
## [br]那边是按 `CharacterRegistry.PlantType` 逐个特判的公共布局代码，改它等于给
## [br]每一株新建植物都欠一笔债；换装参数本来就在本脚本里，取景也该一起住在这一边。
## [br]实现上只动 `_idle_pivot`（角色根的子节点）的 scale / position：
## [br]· 缩放作用在 pivot 上，`_art_scale` 保持原值 → 塞子、光晕、环全部跟着一起放大，
## [br]  不会出现"人放大了但塞子还是小号"的错位；
## [br]· `_ready()` 里已把 pivot 挂在 body_correct 的父节点，body 本身没动，
## [br]  所以战场 / 花园的站位一点不受影响。
func _apply_almanac_framing() -> void:
	if not is_instance_valid(_idle_pivot):
		return
	_idle_pivot.scale = Vector2(ALMANAC_SHOW_SCALE, ALMANAC_SHOW_SCALE)
	# ⚠️ 只叠加"往下压多少"，**不要**覆写成窗口绝对坐标 —— 见 ALMANAC_SHOW_DROP 的注释。
	# x 用 ALMANAC_SHOW_CENTER_DX 而不是 CHOMPER_FOOT_BODY.x：图鉴里要跟阴影对齐居中。
	_idle_pivot.position = Vector2(
		ALMANAC_SHOW_CENTER_DX, CHOMPER_FOOT_BODY.y + ALMANAC_SHOW_DROP)


## 登场演出：等一小会儿（让种植动画落定），再把手抬起来拔盖。
func _play_intro_uncap() -> void:
	await get_tree().create_timer(CAP_INTRO_DELAY).timeout
	if not is_inside_tree() or is_queued_for_deletion():
		return
	# 已经因为别的原因进过吸收流程，就别再演开场的拔盖了
	if _cap_opened:
		return
	_set_cap_state(false)


## 建立塞子图层。
## [br]⚠️⚠️ 2026-10-26 第八轮 —— **约定反过来了：盖着的时候这层也要显示**。
## [br]前七轮的前提是「立绘自己带着一根塞子，这层只是拔盖时接管一下」。
## [br]但用户连续四轮反馈"白色方框/抠图没干净"，逐像素查下来根因就在这个前提：
## [br]立绘里那根"塞子"其实是竖在葫芦口上的一根 7×15 细管（像葱白/吸管），
## [br]它自己带一圈 alpha 40~200 的灰白抗锯齿边（x103/x113 两列整条），
## [br]那圈灰边就是用户看到的"白边"。只要还从立绘切图，怎么切都会把它带进去。
## [br]所以现在改成：
## [br]· **立绘的那根颈管已被整根抹成透明**（`_tmp/fix_neck.py`，葫芦口自然收口）；
## [br]· **塞子由程序化的 `zuixianke_cap_new.png` 独占负责**，盖着/拔开都在这一层上画；
## [br]· 立绘只剩「盖着版 / 开盖版」两张的区别 —— 唇部开合与嘴内阴影，不再管塞子。
## [br]位置必须和葫芦口中心对齐（CAP_IN_ART / CAP_SHOW_SIZE）。
## [br]坐标换算：立绘 Sprite2D 以自身中心为原点、缩放 _art_scale；
## [br]塞子在立绘贴图内的相对位置是 CAP_IN_ART，先转成"相对立绘中心"再乘缩放。
## [br]⚠️ **这一层绝对不能加 `clip_children`**。2026-10-26 试过竖框和方框两次：
## [br]竖框在转 90° 时会把塞子两端切成两条直线断面，方框会把圆头削平变成一块砖。
## [br]只有两条路能同时满足「能翻滚」和「不变形」——就是**不裁剪**。
## [br]（塞子贴图外圈一整圈 alpha = 0，不裁剪也不会露出任何边框，见
## [br][constant CAP_SPIN_DEG] 的注释里那份实测数据。）
## [br]保留 `_cap_clip` 这层空 Node2D 是为了给 tween 一个统一的「位置 + 缩放 + 旋转」载体。
func _build_cap() -> void:
	if not is_instance_valid(_art):
		return
	_cap = Sprite2D.new()
	_cap.name = "ZuixiankeCap"
	_cap.texture = ART_CAP
	_cap.scale = Vector2.ONE
	_cap.position = Vector2.ZERO
	_cap.z_index = 2
	var clip: Node2D = Node2D.new()
	clip.name = "ZuixiankeCapClip"
	clip.position = _cap_home()
	clip.scale = _cap_home_scale()
	clip.z_index = 2
	clip.add_child(_cap)
	# ⚠️⚠️ 2026-10-26 第六轮 —— **这里原来是 `_cap.visible = false`，是个致命 bug**。
	# [br]本意是"盖着的时候这层不显示"，但那是 `_cap_clip` 该管的事（见下面那行）。
	# [br]把**内层贴图**也关掉，就再也没有任何地方把它打开过 ——
	# [br]`_set_cap_state()` 只改 `_cap_clip.visible`，内层永远是 false，
	# [br]于是拔盖动画照常播、位置照常动，**但屏幕上什么都没有**。
	# [br]用户反复说"拔盖子的动作贴图太明显"，有一部分原因就在这：
	# [br]动画层没画出来，玩家看到的只是立绘上那个从没被拔走的塞子。
	# [br]分工要记牢：`_cap_clip.visible` = 这一整套动效是否存在；
	# [br]`_cap` 永远 visible，它只负责"画贴图"。
	_cap.visible = true
	_art.add_child(clip)
	_cap_clip = clip
	# ⚠️ 2026-10-26 第八轮：**盖着态 = 可见**（前七轮这里是 false）。
	# [br]理由见 `_build_cap()` 顶部注释：立绘那根颈管已被抹掉，
	# [br]葫芦口现在是空的，必须由这一层常驻盖住，否则图鉴里会看到"没有塞子的葫芦"。
	_cap_clip.visible = true


## 切换盖子状态。
## [param closed] true=盖上，false=拔开。
## [param instant] true=不做动画直接到位（初始化 / 重置用）。
func _set_cap_state(closed: bool, instant: bool = false) -> void:
	if not is_instance_valid(_cap) or not is_instance_valid(_cap_clip):
		return
	_cap_opened = not closed
	if is_instance_valid(_cap_tween):
		_cap_tween.kill()
		_cap_tween = null
	var home: Vector2 = _cap_home()
	# 拔开的落点。
	# ⚠️ `CAP_PULL_OFFSET` 是**贴图像素**单位，和 `_cap_home()` 同一套坐标系，
	# [br]所以这里**不要再乘 `_art_scale`** —— 父节点 `_art` 会统一缩。
	# [br]（第六轮之前这里乘了，而 `_cap_home()` 也乘了，两处叠起来才出现缩放越大越偏。）
	var opened_pos: Vector2 = home + CAP_PULL_OFFSET

	if instant:
		# 盖着 = 这一层就画在葫芦口上（立绘那根颈管已抹掉，不会再出现两层塞子）
		_cap_clip.position = home
		_cap_clip.scale = _cap_home_scale()
		# 拔盖会把 rotation 转到 200°，instant 分支必须一起归零，
		# [br]否则图鉴/重生这类「直接到位」的路径会继承上一次的翻滚角，塞子是歪的。
		_cap_clip.rotation = 0.0
		_cap_clip.modulate.a = 1.0
		_cap_clip.visible = true
		_apply_open_texture(not closed)
		_set_mouth_glow(not closed)
		return

	_set_mouth_glow(not closed)

	if closed:
		# ── 盖盖：塞子从拔开的落点飞回葫芦口 ──
		# ⚠️ 2026-10-26 第八轮：塞子**回来之后不再隐藏**，它就是盖着态的画面本体。
		# [br]立绘切回"盖着版"只影响唇部与嘴内阴影，塞子完全由这一层负责。
		_cap_clip.visible = true
		# ⚠️ 起点不能写死 `opened_pos`：拔盖动画有 0.58 秒，如果这期间咬合进来
		# [br]（`_on_sucked` 会立刻盖盖），上一段 tween 已被上面 kill 掉，塞子停在半空。
		# [br]写死起点会让它先瞬移回终点再飞回来 —— 肉眼看到的就是「跳了一下」。
		# [br]所以：仍在画面里（a > 0.01）就从当前位置起飞，否则才用拔开落点。
		var from_pos: Vector2 = _cap_clip.position
		if _cap_clip.modulate.a <= 0.01:
			from_pos = opened_pos
		_cap_clip.position = from_pos
		_cap_clip.scale = _cap_home_scale()
		_cap_clip.rotation = 0.0
		_cap_clip.modulate.a = 1.0
		# 盖盖也带一点整株动作，像"抬手往下一按"
		_play_cap_body()
		_cap_tween = create_tween()
		# 立绘先切回盖着版，塞子同时飞回来 —— 落定时两者已经吻合
		_apply_open_texture(false)
		# 回来时顺带把飞出去时的翻滚转回来（200° → 0°），落定才是正的
		_cap_tween.tween_property(_cap_clip, "position", home, CAP_PUSH_TIME) \
			.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		_cap_tween.parallel().tween_property(_cap_clip, "rotation", 0.0, CAP_PUSH_TIME) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		# 落定后只把透明度兜底归 1，**不隐藏**
		_cap_tween.tween_callback(func() -> void:
			_cap_clip.position = home
			_cap_clip.scale = _cap_home_scale()
			_cap_clip.rotation = 0.0
			_cap_clip.modulate.a = 1.0
			_cap_clip.visible = true)
		return

	# ── 拔盖：起手 → 弹射 → 抛物线翻滚 ─────────────────────────────────────
	# ⚠️⚠️ 时间轴写清楚，改参数前先读一遍（每一段都和 `_play_uncap_body` 对齐）：
	# [br]  0.00 ~ 0.16  ① 起手：整株下沉（预备）+ 塞子隆起放大到 1.4 并上提 3px
	# [br]  0.16          ② 弹射帧：切开盖图 + 开封环 + 口部喷气 + 拔塞音 + 撒 3 道残影
	# [br]  0.16 ~ 0.24  ③ 塞子弹出放大到 1.95（"啵"地一下）
	# [br]  0.16 ~ 0.32  ④ 整株猛地挺起 20px + 后仰 5°   ← 主信号
	# [br]  0.24 ~ 0.39  ⑤ 塞子向右上抛到顶点
	# [br]  0.32 ~ 0.56  ⑥ 整株落回
	# [br]  0.39 ~ 0.58  ⑦ 塞子向右下坠落并淡出
	# [br]合计 0.58 秒。比旧版 0.45 长，但这只在上场和消化完后播，不占战斗节奏。
	var base: Vector2 = _cap_home_scale()
	_cap_clip.visible = true
	_cap_clip.position = home
	_cap_clip.scale = base
	_cap_clip.rotation = 0.0
	_cap_clip.modulate.a = 1.0
	# 整株三段姿态必须**从这一帧就开始**，它的 0~0.16 是预备段，
	# 正好和塞子的隆起同步 —— 观众的注意力在「人沉下去」时被带到葫芦口上。
	_play_uncap_body()
	_cap_tween = create_tween()
	# ① 起手：塞子隆起 + 上提。这一步是让观众先「看见葫芦口有个东西」，
	# [br]没有它，后面的飞走只是「一块噪点消失了」。
	_cap_tween.tween_property(_cap_clip, "scale", base * CAP_BULGE_SCALE, CAP_BULGE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_cap_tween.parallel().tween_property(_cap_clip, "position",
		home + Vector2(0.0, -CAP_BULGE_LIFT), CAP_BULGE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	# ② 弹射帧：所有「同一瞬间发生」的事情都塞进这一个 callback，
	# [br]保证切图 / 环 / 气 / 音 / 残影严格同帧 —— 差一帧就会被读成两件事。
	_cap_tween.tween_callback(func() -> void:
		_apply_open_texture(true)
		_play_cap_puff()
		SoundManager.play_character_SFX(&"ZuixiankeUncork")
		_spawn_cap_ghosts(home, base))
	# ③ 弹出放大：TRANS_BACK 会先冲过 1.95 再回落，读作「被手指弹出来」
	_cap_tween.tween_property(_cap_clip, "scale", base * CAP_POP_SCALE, CAP_POP_TIME) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	# ⑤ 上抛：到顶点时翻滚到 90°，同时收回到正常大小
	_cap_tween.tween_property(_cap_clip, "position", home + CAP_ARC_UP, CAP_FLY_UP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_cap_tween.parallel().tween_property(_cap_clip, "rotation",
		deg_to_rad(CAP_SPIN_DEG * 0.45), CAP_FLY_UP_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_cap_tween.parallel().tween_property(_cap_clip, "scale", base, CAP_FLY_UP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	# ⑦ 坠落：EASE_IN（越落越快），翻滚走完剩下的 110°
	_cap_tween.tween_property(_cap_clip, "position",
		home + CAP_ARC_UP + CAP_ARC_DOWN, CAP_FLY_DOWN_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	_cap_tween.parallel().tween_property(_cap_clip, "rotation",
		deg_to_rad(CAP_SPIN_DEG), CAP_FLY_DOWN_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	# 淡出只在下落的后 3/4 发生（delay 1/4 + 时长 3/4，加起来正好等于本段时长 ——
	# [br]⚠️ 两者之和不等于本段时长的话，整组会被拉长或截断，第六轮踩过这个坑）
	_cap_tween.parallel().tween_property(_cap_clip, "modulate:a", 0.0,
		CAP_FLY_DOWN_TIME * 0.75).set_delay(CAP_FLY_DOWN_TIME * 0.25)
	_cap_tween.tween_callback(func() -> void:
		# 复位成「拔开但不可见」：盖盖动画从 opened_pos 起步，只需把 a 拉回 1
		_cap_clip.position = opened_pos
		_cap_clip.scale = base
		_cap_clip.rotation = 0.0
		_cap_clip.modulate.a = 0.0
		_cap_clip.visible = true)


## 塞子层的基准缩放：把 56×104 的源图缩到 12×20 的显示尺寸。
## [br]⚠️⚠️ 2026-10-26 第七轮 —— 这一版终于把"缩放"这件事理清了，记在这里：
## [br]· `_cap_clip` 的父节点是 `_art`，`_art.scale ≈ 0.5957`（= 112/188），
## [br]  所以 `clip.position` 和 `clip.scale` 都会被乘一遍 `_art_scale`；
## [br]· 我们想要的最终效果是：塞子在屏幕上 = `CAP_SHOW_SIZE` × 立绘当前缩放
## [br]  （图鉴放大 1.1 倍它也跟着大，战场缩小它也一起缩）；
## [br]· 设 clip.scale = k，则屏幕尺寸 = 56 × _art_scale × k（再乘 pivot 缩放），
## [br]  要它等于 `CAP_SHOW_SIZE.x × _art_scale`（跟着立绘走），
## [br]  → **k = CAP_SHOW_SIZE.x / 56**，`_art_scale` 自动约掉。
## [br]所以这里只做"源图 → 显示尺寸"的归一，**不要再乘 `_art_scale`**。
## [br]（前几轮在这里乘 `_art_scale`，又用 8×15 的图，等于把塞子画成了 4.8×9，
## [br]  又小又糊 —— 那才是"贴图太明显/像块补丁"的物理原因。）
func _cap_home_scale() -> Vector2:
	var src: Vector2 = ART_CAP.get_size()
	return Vector2(CAP_SHOW_SIZE.x / src.x, CAP_SHOW_SIZE.y / src.y)


## 切换立绘的「盖着 / 开盖」两张图。
## [param open] true=用开盖版（葫芦口是空的），false=用盖着版。
func _apply_open_texture(open: bool) -> void:
	if not is_instance_valid(_art):
		return
	_art.texture = ART_IDLE_OPEN if open else ART_IDLE
	# 切到开盖版的同时炸一圈开封环 —— "洞出现了"和"光炸开了"必须同帧发生，
	# 否则两个信号会被读成两件事（先亮一下，然后洞莫名其妙地出现）。
	if open:
		_play_ring_burst()


## 拔盖的整株三段姿态：**预备 → 发力 → 跟随**。
## [br]⚠️ 这是本轮「让动作明显」的**第一主信号**，比塞子重要得多。
## [br]理由：塞子只有 7×12 屏幕像素，它在动与否，玩家余光根本抓不到；
## [br]但一个 112px 高的角色**先沉下去、再猛地挺起 20px 并后仰**，隔着半个屏幕都看得见。
## [br]观众先看到「人动了」，再顺着视线找到葫芦口 —— 顺序必须是这个，反过来不成立。
## [br]
## [br]⚠️ 三个必须遵守的实现约束：
## [br]① **必须挂起待机呼吸**。`_idle_breath_tween` 一直在写 `_art.position:y`（±0.7px、周期 1s），
## [br]   两条 tween 抢同一属性会互相覆盖 —— 旧版 9px 的上挺有一部分就是这么被吃掉的。
## [br]② **不能写到脚底去**。立绘的缩放基准是「内容底边＝脚底」，`_art.position:y` 往上抬
## [br]   等于把整个人抬离地面，超过约 26px 脚下会露缝。所以 20px 是上限。
## [br]③ **后仰用负角度**。醉仙客立绘朝右，`rotation` 正值是前倾（朝僵尸压）；
## [br]   拔盖是往上往后拉，写成正值会读成「往下压」—— 那是盖盖的意思。
func _play_uncap_body() -> void:
	if not is_instance_valid(_art):
		return
	if is_instance_valid(_body_tween):
		_body_tween.kill()
		_body_tween = null
	_set_idle_breath_paused(true)
	var y0: float = _art_local_y
	_body_tween = create_tween()
	# ① 预备：沉下去、往前压一点。观众在这一段里把眼睛挪到葫芦口上。
	_body_tween.tween_property(_art, "position:y", y0 + CAP_ANTIC_PX, CAP_ANTIC_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_body_tween.parallel().tween_property(_art, "rotation", deg_to_rad(CAP_ANTIC_LEAN), CAP_ANTIC_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	# ② 发力：猛地挺起 + 后仰。TRANS_BACK 会冲过一点再回落，正是「使劲」的读感；
	#    用 SINE 会变成匀速平移，像被人搬起来而不是自己挺起来的。
	_body_tween.tween_property(_art, "position:y", y0 - CAP_LIFT_PX, CAP_LIFT_TIME) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_body_tween.parallel().tween_property(_art, "rotation", deg_to_rad(CAP_LIFT_LEAN), CAP_LIFT_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	# ③ 跟随：落回原位。这一段给得比发力长（0.24 vs 0.16），读作「力用完了」。
	_body_tween.tween_property(_art, "position:y", y0, CAP_SETTLE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_body_tween.parallel().tween_property(_art, "rotation", 0.0, CAP_SETTLE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_body_tween.tween_callback(func() -> void: _set_idle_breath_paused(false))


## 盖盖的整株姿态：抬手一点，再往下一按。
## [br]方向和老版相反的一处：旧版是「往上一挺」，那读起来和拔盖一模一样 ——
## [br]盖盖应该是**压下去**，所以这里改成「先抬 2px 再落回 y0」，落点比起点更低是错的，
## [br]因为立绘脚底不能离开格子，所以用「抬一下再回来」表达按下，靠光晕收掉和塞子飞回来传达。
func _play_cap_body() -> void:
	if not is_instance_valid(_art):
		return
	if is_instance_valid(_body_tween):
		_body_tween.kill()
		_body_tween = null
	_set_idle_breath_paused(true)
	var y0: float = _art_local_y
	_body_tween = create_tween()
	_body_tween.tween_property(_art, "position:y", y0 - CAP_ANTIC_PX * 0.4, CAP_PUSH_TIME * 0.35) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_body_tween.tween_property(_art, "position:y", y0, CAP_PUSH_TIME * 0.65) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_body_tween.tween_callback(func() -> void: _set_idle_breath_paused(false))


## 塞子飞行的残影：沿同一方向滞后几帧，把「被甩出去」的速度描出来。
## [br]⚠️ 残影**不做抛物线**，只做一条直线 + 翻滚 + 淡出：
## [br]它是余晖，轨迹精度无所谓；而如果给残影也排两段不同时长的并行动画，
## [br]Godot 的 Tween 会把并行组按「组内最长者」对齐，轨迹会断成两截（这个坑在
## [br]2026-10-26 第六轮的拔盖 tween 上已经踩过一次）。全部同长最稳。
func _spawn_cap_ghosts(home: Vector2, base_scale: Vector2) -> void:
	if not is_instance_valid(_art):
		return
	var total: float = CAP_FLY_UP_TIME + CAP_FLY_DOWN_TIME
	var end_pos: Vector2 = home + CAP_PULL_OFFSET
	for i in CAP_GHOST_COUNT:
		var g: Sprite2D = Sprite2D.new()
		g.name = "ZuixiankeCapGhost%d" % i
		g.texture = ART_CAP
		g.position = home
		g.scale = base_scale
		# 在塞子（z=2）之下，这样拖尾不会盖住本体
		g.z_index = 1
		# 加色混合：残影是「运动的余晖」，叠加而不是遮挡，草地上也不会出现一块实色补丁
		var mat: CanvasItemMaterial = CanvasItemMaterial.new()
		mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		g.material = mat
		g.modulate = Color(1, 1, 1, 0.42 - 0.11 * i)
		_art.add_child(g)
		var delay: float = CAP_GHOST_STEP * (i + 1)
		var t: Tween = create_tween()
		t.tween_interval(delay)
		t.tween_property(g, "position", end_pos, total) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		t.parallel().tween_property(g, "rotation", deg_to_rad(CAP_SPIN_DEG), total) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		t.parallel().tween_property(g, "modulate:a", 0.0, total) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		t.tween_callback(g.queue_free)


## 拔盖瞬间口部喷出的两团气。
## [br]⚠️ 这是本版用来替代「把口画空」的信号，理由见 [constant CAP_PUFF_RADIUS] 的注释：
## [br]洞口在战场只有 7.7×11 屏幕像素，两张立绘又只差 9 个像素，
## [br]「口变空了」在这个比例下不可能被读出来。而气可以做到 38px。
## [br]两团左右分开一点、向上飘、边飘边扩散，0.34 秒淡掉 —— 短促，不拖泥带水。
func _play_cap_puff() -> void:
	if not is_instance_valid(_mouth):
		return
	var r0: float = CHOMPER_H * CAP_PUFF_RADIUS * 2.0
	for i in 2:
		var p: Sprite2D = Sprite2D.new()
		p.name = "ZuixiankeCapPuff%d" % i
		p.texture = ART_GLOW
		var mat: CanvasItemMaterial = CanvasItemMaterial.new()
		mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		p.material = mat
		# 画在所有光效之上：气应该在葫芦口外面，不能被口沿挡住
		p.z_index = 6
		var side: float = -1.0 if i == 0 else 1.0
		var start: Vector2 = Vector2(side * 2.0, -2.0)
		p.position = start
		p.scale = Vector2(r0 / 64.0, r0 / 64.0)
		p.modulate = Color(1, 1, 1, 0.0)
		_mouth.add_child(p)
		var t: Tween = create_tween()
		# 0.06 秒蹿出来：气压释放是「噗」的一下，慢吞吞亮起来就不像气了
		t.tween_property(p, "modulate:a", CAP_PUFF_ALPHA, 0.06) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		t.tween_property(p, "modulate:a", 0.0, CAP_PUFF_TIME) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		t.parallel().tween_property(p, "position",
			start + Vector2(side * 6.0, -CAP_PUFF_RISE), CAP_PUFF_TIME) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		t.parallel().tween_property(p, "scale",
			Vector2.ONE * (r0 * CAP_PUFF_GROW / 64.0), CAP_PUFF_TIME) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		t.tween_callback(p.queue_free)


## 塞子「盖上」时的**父节点（`_art`）局部坐标**。
## [br]⚠️⚠️ 2026-10-26 第六轮 —— 这个函数被改了三遍，最终结论写在这里。
## [br]出错链条：
## [br]· 旧版返回 `(cap_center - art_center) * _art_scale`，**乘了 `_art_scale`**；
## [br]· 但 `_cap_clip` 的父节点就是 `_art`，`_art` 自己已经带 `_art_scale`，
## [br]  所以这份偏移被缩放了**两次**（0.596² ≈ 0.355）；
## [br]· 更麻烦的是 `_art` 的**父级** `_idle_pivot` —— 图鉴里是 1.10、
## [br]  验证场景里我放大到了 4.5，pivot 的缩放会**原样**作用到 clip 的 position 上。
## [br]实测：`cap_clip.position = (39.5, -34)` 时，`cap.global` 算出 (658, 93)，
## [br]而葫芦口实际在 (590, 235) —— 差了 80 多像素，看起来就是"塞子画到头发上"。
## [br]正解：**clip 要的是 `_art` 的局部坐标**，而 `_art` 的局部坐标 = 贴图像素差；
## [br]因为 `_art` 自己会乘 `_art_scale`，pivot 会再乘 pivot.scale，
## [br]所以这里只要给**纯贴图像素差**，两层缩放都会自动生效，位置一定对。
## [br]⚠️ 2026-10-26 第七轮 —— 现在非常简单，因为坐标系统一了：
## [br]`_cap` 是 `Sprite2D`（默认 `centered=true`），所以 `_cap_clip.position`
## [br]就是**塞子中心**在 `_art` 局部坐标里的位置；而 `_art` 的局部坐标单位
## [br]= 立绘贴图像素（`_art` 自己负责乘 `_art_scale`）。
## [br]所以只要把「洞口中心」翻译成「相对立绘中心」：
## [br]  `CAP_IN_ART - ART_IDLE.get_size() / 2`
## [br]前几轮这里加过 `CAP_TEX_SIZE * 0.5`，那是因为当时 `CAP_IN_ART` 记的是
## [br]**左上角**；现在 `CAP_IN_ART` 直接就是**中心**，再多加半个尺寸就偏右下半个塞子。
func _cap_home() -> Vector2:
	var tex_size: Vector2 = ART_IDLE.get_size()
	return CAP_IN_ART - tex_size * 0.5


## 开封环 / 口部光晕的贴图：**预生成的 PNG**，不再用 GradientTexture2D。
## [br]⚠️⚠️ 2026-10-26 第八轮 —— 这是"白色方框"的最终解法，过程全部留在这里。
## [br]原来两张光效都是 `GradientTexture2D + FILL_RADIAL` 运行时生成的方形贴图。
## [br]方形画布里画圆，**四个角天然在圆外**，而圆外像素的 alpha 取自渐变末端色标 ——
## [br]只要末端不是严格 0，加色混合（BLEND_MODE_ADD）一开，那四个角就是一块亮方块。
## [br]实测（一次性诊断脚本逐像素读出的真值，96×96）：
## [br]· 原参数 `fill_to = (1.0, 0.5)` → **四角 a = 255，纯白**，这就是用户看到的白方框；
## [br]· `fill_to = (1.4142, 0.5)` → 角 a = 217，仍然明显；
## [br]· `fill_to = (2.0, 0.5)` → 角 a = 0，但渐变半径翻倍会把整块实心亮斑压缩进贴图 1/4 区域，
## [br]  实机抓图是**整屏过曝**，比原问题更糟。
## [br]结论：在方形画布上用径向渐变做圆形光，这件事没有好解。所以直接画进像素：
## [br]  `_tmp/gen_glow_ring.py` 在 float 缓冲里按圆心距逐像素算 alpha，
## [br]  圆半径 = 半宽 × 0.96，四角距圆心 1.414 × 半宽 > 半径 → **必为 0**，
## [br]  外沿再硬归零 + 最外 1 圈清零，任何缩放插值都不会冒边。
## [br]换成 PNG 后，scale 换算也回到最朴素的「目标直径 / 贴图尺寸」，不再有任何魔法系数。
const ART_RING := preload("res://assets/image/character/chomper/zuixianke_ring.png")
const ART_GLOW := preload("res://assets/image/character/chomper/zuixianke_glow.png")
## 吸气环：64×64 细环（峰在 r=0.70、中心及外圈全透明）。
## [br]由 `zuixianke_glow.png` 改 alpha 曲线生成，不是新素材 —— 颜色与光晕同族，
## [br]技能打在草地上时不会出现一个「外来色」的光圈。
const ART_GUST := preload("res://assets/image/character/chomper/zuixianke_gust.png")
## [br]为什么需要它：塞子在战场上只有 7.6 屏幕像素宽，物理上不可能当主信号用。
## [br]光晕在**葫芦口中心**（塞子底部）画一个径向渐变圆，半径约 18 屏幕像素，
## [br]开盖时淡入并常驻呼吸 —— 玩家隔着半个屏幕也能看到"这株在等人来"。
func _build_mouth_glow() -> void:
	if not is_instance_valid(_art):
		return
	_mouth_glow = Sprite2D.new()
	_mouth_glow.name = "ZuixiankeMouthGlow"
	_mouth_glow.texture = ART_GLOW
	# 光晕中心对准葫芦口沿（= 塞子底端），而不是塞子中心
	var tex_size: Vector2 = ART_IDLE.get_size()
	var art_center: Vector2 = tex_size * 0.5
	# ⚠️ 2026-10-26 第七轮：用 `CAP_SHOW_SIZE`（显示尺寸）而不是 `CAP_TEX_SIZE`（源图 56×104），
	# [br]否则光晕会被顶到洞口下方 40 多像素的地方。
	var mouth_in_tex: Vector2 = Vector2(
		CAP_IN_ART.x,
		CAP_IN_ART.y + CAP_SHOW_SIZE.y * 0.5)
	# ⚠️ position 用**贴图像素**（不乘 `_art_scale`，父节点会统一缩）；
	# [br]scale 也给 1.0：贴图像素 = 立绘像素，和塞子同一套口径。
	# [br]第六轮之前两处都乘了 `_art_scale`，光晕位置会随缩放放大偏移 —— 和塞子同一个 bug。
	_mouth_glow.position = mouth_in_tex - art_center
	_mouth_glow.scale = Vector2.ONE
	_mouth_glow.modulate = Color(1, 1, 1, 0)
	# ⚠️ z_index 必须为正：光晕是 _art 的子节点，负值会被立绘盖住（2026-10-26 实测 -1 完全不可见）
	# 加色混合，让光"发亮"而不是糊一层灰
	_mouth_glow.z_index = 3
	var add_mat: CanvasItemMaterial = CanvasItemMaterial.new()
	add_mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_mouth_glow.material = add_mat
	_mouth_glow.visible = false
	_art.add_child(_mouth_glow)


## 拔盖瞬间的"开封环"：一圈亮边从葫芦口炸开、扩大、淡出。
## [br]为什么光晕不够、还要这一圈：光晕是**静态的加色亮斑**，拔盖那一刻
## [br]它只是从 0 淡到 0.62，观众读到的是"这里变亮了"，读不到"有什么被打开了"。
## [br]（2026-10-26 实测：单靠光晕，04_opened 与 01_closed 只差 96 点亮度，
## [br]几乎看不出开没开。）一环从中心扩出去，才是"开封"这个词的动作感。
## [br]环心是透明的（见 `zuixianke_ring.png` 的生成脚本），所以不会把葫芦口的洞盖住。
func _build_ring_burst() -> void:
	if not is_instance_valid(_art):
		return
	_ring_burst = Sprite2D.new()
	_ring_burst.name = "ZuixiankeRingBurst"
	_ring_burst.texture = ART_RING
	_ring_burst.position = _mouth_glow.position
	# ⚠️ 2026-10-26 第七轮：**不要乘 `_art_scale`**。`_art` 父节点已经缩过一遍，
	# [br]这里再乘就等于 0.596² ≈ 0.355，环缩成一个小点，实机几乎看不见。
	# [br]本项目统一口径：**子在 `_art` 下的所有 position / scale 都用「立绘贴图像素」**，
	# [br]缩放由 `_art.scale` 一次性负责。塞子、光晕、环三者全部遵守这条。
	_ring_burst.scale = Vector2.ONE
	_ring_burst.modulate = MOUTH_GLOW_COLOR
	_ring_burst.modulate.a = 0.0
	# 在光晕之上（光晕 3），这样环不会被自己那团光吃进去
	_ring_burst.z_index = 4
	var add_mat: CanvasItemMaterial = CanvasItemMaterial.new()
	add_mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_ring_burst.material = add_mat
	_ring_burst.visible = false
	_art.add_child(_ring_burst)


## 播一次开封环。
func _play_ring_burst() -> void:
	if not is_instance_valid(_ring_burst):
		return
	_ring_burst.visible = true
	_ring_burst.scale = Vector2.ONE
	_ring_burst.modulate = MOUTH_GLOW_COLOR
	_ring_burst.modulate.a = MOUTH_RING_ALPHA
	# 贴图 96×96，圆的直径 = 96 × 0.96 = 92.16px，占满后就是 92 贴图像素。
	# [br]用 `CHOMPER_H * MOUTH_RING_MAX_RADIUS` 作为**目标半径**，
	# [br]换成贴图像素直径再除以贴图边长，就是最朴素的换算 —— 没有任何魔法系数。
	var target_d: float = CHOMPER_H * MOUTH_RING_MAX_RADIUS * 2.0
	var k: float = target_d / 96.0
	var t: Tween = create_tween()
	t.set_parallel(true)
	t.tween_property(_ring_burst, "scale",
		Vector2(k, k), MOUTH_RING_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t.tween_property(_ring_burst, "modulate:a", 0.0, MOUTH_RING_TIME) \
		.set_delay(MOUTH_RING_TIME * 0.35)
	t.chain().tween_callback(func() -> void: _ring_burst.visible = false)


## 开 / 关葫芦口光晕。
## [param on] true=开盖状态（亮起并呼吸），false=盖着（收掉）。
func _set_mouth_glow(on: bool) -> void:
	if not is_instance_valid(_mouth_glow):
		return
	if is_instance_valid(_mouth_glow_tween):
		_mouth_glow_tween.kill()
		_mouth_glow_tween = null
	var r: float = CHOMPER_H * MOUTH_GLOW_RADIUS * 2.0  # 直径（立绘贴图像素）
	# 贴图 64×64，光斑直径目标 = r（立绘贴图像素），换算是 `r / 64`。
	# [br]**不乘 `_art_scale`**（父节点 `_art` 统一缩）。
	var k: float = r / 64.0
	_mouth_glow.scale = Vector2(k, k)
	if not on:
		_mouth_glow.visible = false
		_mouth_glow.modulate.a = 0.0
		return

	_mouth_glow.visible = true
	_mouth_glow.modulate = MOUTH_GLOW_COLOR
	_mouth_glow.modulate.a = 0.0
	# 亮起来 → 常驻呼吸
	_mouth_glow_tween = create_tween()
	_mouth_glow_tween.tween_property(_mouth_glow, "modulate:a",
		MOUTH_GLOW_ALPHA_MAX, 0.25).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_mouth_glow_tween.tween_property(_mouth_glow, "modulate:a",
		MOUTH_GLOW_ALPHA_MIN, MOUTH_GLOW_BREATH_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_mouth_glow_tween.tween_property(_mouth_glow, "modulate:a",
		MOUTH_GLOW_ALPHA_MAX, MOUTH_GLOW_BREATH_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_mouth_glow_tween.set_loops()


## 吸气环：一圈细环从外面**收**进壶口。
## [br]为什么必须有它：僵尸缩进壶口这件事只有 0.24 秒，而且发生在壶口那个
## [br]约 10px 的小范围内 —— 没有「吸力」的先兆，玩家只会看到「僵尸莫名其妙不见了」。
## [br]环从 47px 收到 11px 并淡出，等于替观众把视线从僵尸一路引到壶口：
## [br]先看到「有东西在吸」，再看到「僵尸进去了」，两件事被读成一个动作。
## [br]⚠️ 这和「开封环」正好相反：那个是**从中心往外炸**（盖子打开 = 往外），
## [br]这个是从外往中心收（吸气 = 往里）。方向反了，含义就全反了。
func _build_gust() -> void:
	if not is_instance_valid(_mouth):
		return
	_gust = Sprite2D.new()
	_gust.name = "ZuixiankeGust"
	_gust.texture = ART_GUST
	_gust.position = Vector2.ZERO
	_gust.scale = Vector2.ONE
	_gust.modulate = GUST_COLOR
	_gust.modulate.a = 0.0
	# 画在壶口之上（注意：环的父节点是 `_mouth`，本地坐标原点就是壶口）
	_gust.z_index = 5
	var add_mat: CanvasItemMaterial = CanvasItemMaterial.new()
	add_mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_gust.material = add_mat
	_gust.visible = false
	_mouth.add_child(_gust)


## 播一次向心收缩的吸气环。
func _play_gust() -> void:
	if not is_instance_valid(_gust):
		return
	_gust.visible = true
	# 贴图 64×64、环的外沿直径 = 64 × 0.98 ≈ 63px，
	# [br]所以「目标直径 / 63」就是最朴素的换算 —— 和光晕、开封环同一套口径，没有魔法系数。
	var r0: float = CHOMPER_H * GUST_START_RADIUS * 2.0
	var r1: float = CHOMPER_H * GUST_END_RADIUS * 2.0
	_gust.scale = Vector2(r0 / 63.0, r0 / 63.0)
	_gust.modulate = GUST_COLOR
	_gust.modulate.a = 0.0
	var t: Tween = create_tween()
	t.set_parallel(true)
	# 淡入只要 0.08：吸力是「突然起来」的，慢吞吞地亮起来就不像吸力了
	t.tween_property(_gust, "modulate:a", GUST_PEAK_ALPHA, 0.08) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	t.tween_property(_gust, "scale", Vector2(r1 / 63.0, r1 / 63.0), GUST_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	t.chain().tween_property(_gust, "modulate:a", 0.0, GUST_TIME * 0.45) \
		.set_trans(Tween.TRANS_SINE)
	t.chain().tween_callback(func() -> void: _gust.visible = false)


## 待机：左右轻摆 + 呼吸起伏。全部 SINE + EASE_IN_OUT，两端速度为 0，循环接缝看不出来。
func _play_idle_motion() -> void:
	if not is_instance_valid(_idle_pivot) or not is_instance_valid(_art):
		return
	var sway: Tween = create_tween().set_loops()
	sway.tween_property(_idle_pivot, "rotation", deg_to_rad(IDLE_SWAY_DEG), IDLE_SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	sway.tween_property(_idle_pivot, "rotation", deg_to_rad(-IDLE_SWAY_DEG), IDLE_SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_idle_sway_tween = sway

	var breath: Tween = create_tween().set_loops()
	breath.tween_property(_art, "position:y", _art_local_y - IDLE_BREATH_PX, IDLE_BREATH_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	breath.tween_property(_art, "position:y", _art_local_y, IDLE_BREATH_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_idle_breath_tween = breath


## 挂起 / 恢复待机轻摆。
## [br]⚠️ 2026-10-27 实测发现的问题：`_play_chew_shake` 和待机摆动**都在写
## `_idle_pivot.rotation`**，两条 tween 同时跑，谁后写谁生效。第二、三段
## （微弱 2.2° / 静止）被待机的 1.6° 顶掉，15 秒之后实测还有 1.6° 在晃 ——
## 和第二阶段几乎分不出来，"三段"读起来只有两段。
## [br]所以咀嚼期间把待机摆动挂起，第三段才是真的静止；30 秒消化完再放开。
func _set_idle_sway_paused(paused: bool) -> void:
	if not is_instance_valid(_idle_sway_tween) or not _idle_sway_tween.is_valid():
		return
	if paused:
		_idle_sway_tween.pause()
	else:
		_idle_sway_tween.play()


## 挂起 / 恢复待机呼吸（上下 ±0.7px）。
## [br]同理：举葫芦那一下要把立绘抬起 10px，而呼吸循环一直在写 `_art.position:y`，
## 抬起 0.2 秒结束后会被呼吸立刻拽回原位 —— 连打期间姿态立不住。
func _set_idle_breath_paused(paused: bool) -> void:
	if not is_instance_valid(_idle_breath_tween) or not _idle_breath_tween.is_valid():
		return
	if paused:
		_idle_breath_tween.pause()
	else:
		_idle_breath_tween.play()


## 咀嚼完成 —— 消化 30 秒走完，重新拔开盖子等下一只。
func _on_chew_timer_timeout() -> void:
	is_chewing = false
	_stop_chew_shake()
	_stop_heavy_attack()
	# 用户要求：消化完全后**再打开盖子**，等待新僵尸
	_set_cap_state(false)


## 停掉咀嚼晃动并复位。
func _stop_chew_shake() -> void:
	if is_instance_valid(_chew_shake_tween):
		_chew_shake_tween.kill()
		_chew_shake_tween = null
	if is_instance_valid(_chew_body_tween):
		_chew_body_tween.kill()
		_chew_body_tween = null
	if is_instance_valid(_idle_pivot):
		_idle_pivot.rotation = 0.0
		_idle_pivot.scale = Vector2.ONE
	if is_instance_valid(_art):
		_art.rotation = 0.0
		_art.position.y = _art_local_y
	# 壶口也要一起回位：咀嚼三段都只动 pivot 和 art，壶口本身不参与，
	# [br]但 `_play_press` 留下的压壶角度如果不在这里收掉，一次被铲打断就会永久歪着。
	if is_instance_valid(_mouth):
		_mouth.position = _mouth_home()
		_mouth.rotation = deg_to_rad(MOUTH_TILT_DEG)
	# 晃动结束，把待机摆动还回去
	_set_idle_sway_paused(false)


#region 咀嚼晃动（三段：剧烈 → 微弱 → 静止）
## 葫芦里的僵尸在挣扎：0~5 秒剧烈、5~15 秒微弱、15~30 秒基本不动。
## [br]**整株一起晃**（动 _idle_pivot），不是只晃葫芦 —— 理由见 CHEW_FIERCE_END 的注释：
## [br]立绘里手是抓着葫芦上球的，单独抠葫芦会把手留下，一动就穿帮。
## [br]晃动的同时带一点整株挤压（chew_body），读出"人被葫芦拽着抖"的体感。
func _play_chew_shake() -> void:
	if not is_instance_valid(_idle_pivot) or not is_instance_valid(_art):
		return
	_stop_chew_shake()
	# 待机摆动会让第三段「静止」名不副实，咀嚼期间先挂起
	_set_idle_sway_paused(true)

	# 剧烈段：幅度大、节奏快，来回摆
	var fierce_loops: int = int(CHEW_FIERCE_END / CHEW_FIERCE_STEP)
	# 微弱段：幅度小、节奏慢
	var weak_loops: int = int((CHEW_WEAK_END - CHEW_FIERCE_END) / CHEW_WEAK_STEP)

	_chew_shake_tween = create_tween()
	_chew_shake_tween.set_parallel(false)

	# ── 第一段：0~5 秒 剧烈 ──
	for i in fierce_loops:
		var sgn: float = 1.0 if (i % 2 == 0) else -1.0
		_chew_shake_tween.tween_property(_idle_pivot, "rotation",
			deg_to_rad(CHEW_FIERCE_DEG * sgn), CHEW_FIERCE_STEP) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		_chew_shake_tween.parallel().tween_property(_art, "position:x",
			CHEW_FIERCE_PX * 0.5 * sgn * _art_scale, CHEW_FIERCE_STEP) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	# ── 第二段：5~15 秒 微弱 ──
	for i in weak_loops:
		var sgn2: float = 1.0 if (i % 2 == 0) else -1.0
		_chew_shake_tween.tween_property(_idle_pivot, "rotation",
			deg_to_rad(CHEW_WEAK_DEG * sgn2), CHEW_WEAK_STEP) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		_chew_shake_tween.parallel().tween_property(_art, "position:x",
			CHEW_WEAK_PX * 0.4 * sgn2 * _art_scale, CHEW_WEAK_STEP) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	# ── 第三段：15~30 秒 基本不动（缓缓回正后停住） ──
	_chew_shake_tween.tween_property(_idle_pivot, "rotation", 0.0, 0.5) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_chew_shake_tween.parallel().tween_property(_art, "position:x", 0.0, 0.5) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)

	# 挤压：只在前 5 秒跟着剧烈段走，后面身体静下来
	_chew_body_tween = create_tween()
	for i in fierce_loops:
		_chew_body_tween.tween_property(_idle_pivot, "scale",
			Vector2(1.0 + CHEW_BODY_SQUASH * 0.6, 1.0 - CHEW_BODY_SQUASH), CHEW_FIERCE_STEP * 0.5) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		_chew_body_tween.tween_property(_idle_pivot, "scale", Vector2.ONE, CHEW_FIERCE_STEP * 0.5) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
#endregion


#region 巨人 / 僵王：举葫芦连打
## 对着吞不掉的大家伙持续攻击：**每 1.5 秒一次、每次 200**，直到目标死亡或被铲。
## [br]这条支路**不触发**开盖/盖盖 —— 葫芦一直对着目标，不进"吸收"流程（用户口径）。
func _start_heavy_attack(enemy: Character000Base) -> void:
	if not is_instance_valid(enemy):
		return
	# 已经在连打同一只就不重开（避免每次咬合都叠一条循环）
	if _heavy_attacking:
		return
	_heavy_attacking = true
	_stop_chew_shake()
	# 葫芦对准目标：整株前倾 + 微微抬起（不拔盖）
	_play_aim_motion()
	_heavy_loop(enemy)


## 连打循环。用 await 计时而不是 Tween：只关心时间点，不需要插值；
## [br]每一拍之前都重新确认「植物还在、目标还在」，中途被铲掉/目标死亡就自然收尾。
func _heavy_loop(enemy: Character000Base) -> void:
	# 首发放在这里（不等 1.5 秒），咬到就立刻吃一发
	while true:
		if not is_inside_tree() or is_queued_for_deletion():
			_heavy_attacking = false
			return
		if not is_instance_valid(enemy):
			break
		enemy.be_attacked_bullet(HEAVY_TICK_DAMAGE,
			BulletRegistry.AttackMode.Penetration, false, false)
		SoundManager.play_character_SFX(&"ZuixiankeGulp")
		await get_tree().create_timer(HEAVY_TICK_INTERVAL).timeout
	# 目标死了 / 走掉了：收尾，把 is_bite 放开让植物回到待机
	_stop_heavy_attack()
	is_bite = false
	# 如果范围内还有新的大家伙，立刻接着打
	if is_instance_valid(detect_component.update_first_enemy()):
		is_bite = true


## 举葫芦对准目标的一次性姿态（整株前倾 + 壶口压出去）。
## [br]⚠️ 2026-10-27 修正了两处：原来动的是 `_art`（立绘本身），而 `_play_press` 动的是
## [br]`_idle_pivot` —— 两条 tween 抢不同的节点，收尾时会把姿态叠成两份。
## [br]现在统一由 `_play_press(true)` 负责前倾与壶口前伸（它在 `_eat_zombie` 里已经先调过），
## [br]这里只补「抬起来一点」这个连打专属的体感。
func _play_aim_motion() -> void:
	if not is_instance_valid(_art) or not is_instance_valid(_mouth):
		return
	if is_instance_valid(_heavy_tween):
		_heavy_tween.kill()
		_heavy_tween = null
	# 呼吸会一直写 `_art.position:y`，连打期间先挂起，否则抬起会被它拽回去
	_set_idle_breath_paused(true)
	var t: Tween = create_tween()
	t.set_parallel(true)
	t.tween_property(_mouth, "position:y",
		_mouth_home().y + MOUTH_DIP_PX - HEAVY_AIM_LIFT, HEAVY_AIM_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_heavy_tween = t


## 收尾：姿态回正。
## [br]注意这里**只**负责呼吸与 `_art.position` 的收口；前倾角与壶口位置
## [br]交给 `_release_press()`，两处各管各的，不会互相覆盖。
func _stop_heavy_attack() -> void:
	_heavy_attacking = false
	if is_instance_valid(_heavy_tween):
		_heavy_tween.kill()
		_heavy_tween = null
	_release_press()
	if is_instance_valid(_art):
		var t: Tween = create_tween()
		t.set_parallel(true)
		t.tween_property(_art, "position:y", _art_local_y, 0.18).set_trans(Tween.TRANS_SINE)
		# 回正走完再把呼吸放开，否则呼吸会在回正途中抢先写 y、把人拽下去
		t.finished.connect(_set_idle_breath_paused.bind(false), CONNECT_ONE_SHOT)
	else:
		_set_idle_breath_paused(false)
#endregion


#region 动画轨道调用
## 吞咽动画结束
func swallow_end():
	if is_instance_valid(detect_component.update_first_enemy()):
		is_bite = true

## 咬合动画结束
func bite_end():
	is_bite = false
	## 换皮后：这一帧之前 `_on_sucked` 已经把目标吞掉并置了 is_chewing，
	## 所以正常情况下走不到下面的分支。留一条兜底 —— 万一吞噬被跳过
	## （目标在演出途中消失），不能让植物卡在「张着嘴咬不到」的状态里。
	## [br]⚠️ 对巨人/僵王：连打期间必须**保持 is_bite = true**，否则
	## [br]change_is_attack 每帧都会把它重新置 true → 反复重播举葫芦姿态，画面抖动。
	if _heavy_attacking:
		is_bite = true
		return
	# 「还在吞噬前摇里」：僵尸已经锁定、还没吸完 → 不回待机，等 `_on_sucked` 把 is_chewing 立起来
	if _pending_target != null or _sucking != null:
		return
	# 吸完之后万一 `_on_sucked` 被打断（植物被铲），不能永远卡在 is_bite
	if not is_chewing:
		if is_instance_valid(detect_component.update_first_enemy()):
			is_bite = true
#endregion

## 咬合关键帧（`Bite` 轨道 1.41667 秒那一帧，TimeScale 1.15 → 墙钟约 1.232 秒）。
## [br]⚠️ 阈值必须落在窗口内：`Bite` 在 2.0/1.15 = 1.739 秒（墙钟）收尾转 `Chomper_chew`。
## [br]窗口 0.507 秒，主角（僵尸缩进壶口）在 0.20~0.44 秒之间完成，留 0.07 秒余量。
## [br]2026-10-27 起 `ATK_EAT_DELAY` 与 `_eat_timer` 已删除：吞噬改由 `_start_suck` 的
## [br]await 链驱动，必须和「壶口压到位」同帧发生，不能再挂一个独立定时器。
const ATK_BITE_DELAY := 0.10

## 咬合时锁定的目标。`bite_end` 靠它判断「还在前摇里」。
var _pending_target: Character000Base = null


func _eat_zombie():
	# 咬合关键帧：先认目标，再开演
	var enemy: Character000Base = detect_component.update_first_enemy()
	if enemy == null or not (enemy is ZB000Base or enemy is Zombie000Base):
		# 没咬到东西：空放一下「压壶」，让动作有个交代，但不吸气、不留尾巴
		_play_press(false)
		return
	# 巨人 / 僵王：吞不下去，壶口只压到它们身上，不吸进去
	# ⚠️ 这条分支**不能**设 `_pending_target`：`bite_end` 用它的非空来判断
	# 「还在吞噬前摇里」，留着会把这株植物永久卡在张嘴状态。
	if _is_unswallowable(enemy):
		_play_press(true)
		_start_heavy_attack(enemy)
		return
	_pending_target = enemy
	# ── 因果顺序（这是本轮重做的核心）────────────────────────────────
	# 从这一帧起，壶口先往僵尸身上压（ATK_PRESS_TIME），压到的**同一刻**僵尸才开始被吸。
	# 吞噬本身由 `_start_suck` 触发，不再挂独立定时器 ——
	# 因为它必须和「壶口到位」严丝合缝地同帧发生，差一帧就会被读成两件事。
	_play_press(true)
	_start_suck(enemy)


## 这一只吞得下去吗？巨人僵尸与僵王博士都吞不下 —— 只打、不吞。
func _is_unswallowable(enemy: Character000Base) -> bool:
	return enemy is Zombie024Gargantuar or enemy is ZB000Base


## 压壶：壶口从胸前压向目标方向（整株前倾配合）。
## [br][param suck] true = 这一下后面要接吸入，壶口压得深、朝向压得更低；
## [br]false = 空放，只压到一半就回来，不给玩家「它好像吸到了什么」的错觉。
## [br]⚠️ 动的是 `_mouth`（绕壶口转）和 `_idle_pivot`（绕脚底转），**不动 `_art` 的位置** ——
## [br]`_art` 一挪整株会连脚一起滑出格子（它的贴图中心比人物实体中心偏右 19px）。
func _play_press(suck: bool) -> void:
	if not is_instance_valid(_mouth) or not is_instance_valid(_idle_pivot):
		return
	if is_instance_valid(_atk_tween):
		_atk_tween.kill()
		_atk_tween = null
	_mouth.position = _mouth_home()
	_mouth.rotation = deg_to_rad(MOUTH_TILT_DEG)
	_idle_pivot.rotation = 0.0
	# 吸气环只有「收」这一个方向。空放（suck=false）不播环：
	# [br]没有吸力这件事，玩家才相信「什么都没吸到」。
	if suck:
		_play_gust()

	var reach: float = MOUTH_REACH_PX if suck else MOUTH_REACH_PX * 0.5
	var dip: float = MOUTH_DIP_PX if suck else MOUTH_DIP_PX * 0.4
	var press: float = MOUTH_PRESS_DEG if suck else MOUTH_PRESS_DEG * 0.4
	var lean: float = ATK_BODY_LEAN if suck else ATK_BODY_LEAN * 0.5
	var dur: float = ATK_PRESS_TIME if suck else ATK_FORCE_PRESS

	_atk_tween = create_tween()
	_atk_tween.set_parallel(true)
	# 壶口前伸 + 下压：TRANS_BACK 的 EASE_OUT 会给一个轻微的「冲过头再回一点」，
	# [br]这正是「把瓶子怼出去」的加速度读感；单纯 SINE 看起来像匀速平移，没有发力感。
	_atk_tween.tween_property(_mouth, "position",
		_mouth_home() + Vector2(reach, dip), dur) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_atk_tween.tween_property(_mouth, "rotation",
		deg_to_rad(MOUTH_TILT_DEG + press), dur) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_atk_tween.tween_property(_idle_pivot, "rotation",
		deg_to_rad(lean), dur) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)


## 收壶：压完之后回到胸前。
## [br]用 TRANS_SINE 的 EASE_IN_OUT 慢慢回，因为这一刻僵尸已经没了，
## [br]画面该「松下来」—— 回得急会像甩了一下空瓶子。
func _release_press() -> void:
	if is_instance_valid(_atk_tween):
		_atk_tween.kill()
		_atk_tween = null
	if not is_instance_valid(_mouth) or not is_instance_valid(_idle_pivot):
		return
	_atk_tween = create_tween()
	_atk_tween.set_parallel(true)
	_atk_tween.tween_property(_mouth, "position", _mouth_home(), 0.18) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_atk_tween.tween_property(_mouth, "rotation", deg_to_rad(MOUTH_TILT_DEG), 0.18) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_atk_tween.tween_property(_idle_pivot, "rotation", 0.0, 0.18) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


## 吸：壶口压到位（ATK_PRESS_TIME）之后，僵尸就**缩进壶口**，而不是凭空消失。
## [br]⚠️⚠️ 这是修掉「违和」的那一步，说清楚为什么必须这么做：
## [br]原来的 `be_chomper_eat()` 是 `queue_free()` —— 僵尸在那一帧**整个从场景里没了**。
## [br]前摇再好看，观众看到的是「葫芦抖了两下 → 僵尸瞬间蒸发了」，
## [br]中间缺了「进去」这一段，所以怎么调参数都觉得怪。
## [br]现在补上这一段：把僵尸搬到壶口前，同时缩到 [constant SUCK_SCALE]，
## [br]0.24 秒里把「体积」和「存在」一起收掉 —— 玩家读到的才是「被吸进去了」。
## [br]
## ⚠️ 为什么缩的是 `body.scale` 而不是僵尸根节点的 scale：
## [br]① 根节点的 `scale.x` 被朝向逻辑（`update_direction_x_root`）占着，改它下一帧就被覆盖，
## [br]   而且朝右的僵尸缩起来会直接镜像；
## [br]② `Character000Base` 上**没有** `size` 这个属性（我按这个写过一版，是错的）。
## [br]`body`（`BodyCharacter`）是纯表现节点，scale 只被压扁类状态用过，收起来是干净的。
func _start_suck(enemy: Character000Base) -> void:
	if not is_instance_valid(enemy) or _sucking == enemy:
		return
	_sucking = enemy
	# 压壶要压缩完才轮到「吸」，否则两件事同时发生，又变成「莫名其妙」
	await get_tree().create_timer(ATK_PRESS_TIME).timeout
	if not is_inside_tree() or is_queued_for_deletion():
		_release_press()
		return
	if not is_instance_valid(enemy) or not is_instance_valid(enemy.body):
		_sucking = null
		_release_press()
		return

	# 从这一刻起这只僵尸不再走路、不再出手。只停它自己，不碰别的角色。
	if SUCK_MOVE_FACTOR and enemy is Zombie000Base:
		var z: Zombie000Base = enemy as Zombie000Base
		if is_instance_valid(z.move_component):
			z.move_component.update_move_factor(true, MoveComponent.E_MoveFactor.IsDisable)

	var start_global: Vector2 = enemy.global_position
	var start_body_scale: Vector2 = enemy.body.scale
	_suck_target = enemy
	_suck_start_global = start_global
	# 终点用壶口的**实时**世界坐标（不是开演时缓存的），因为整株在前倾、壶口在动。
	# [br]再往下拉一点：僵尸的 origin 在脚底，要让「身体」进到壶口里，
	# [br]终点得落在它身体的中段高度（约 120px 高的 35%），否则是拿脚去够壶口。
	var mouth: Vector2 = _mouth_global()
	var end_global: Vector2 = mouth + Vector2(-SUCK_PULL_PX, -42.0)
	var end_scale: Vector2 = start_body_scale * SUCK_SCALE

	var t: Tween = create_tween()
	t.set_parallel(true)
	# 位移用 TRANS_QUAD / EASE_IN：起步慢、越近越快 —— 这是「被吸力拽过去」的标准曲线。
	# [br]反过来（EASE_OUT，先快后慢）读起来像僵尸自己扑过去的，正好是反意。
	t.tween_property(enemy, "global_position", end_global, SUCK_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	t.tween_property(enemy.body, "scale", end_scale, SUCK_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	await t.finished

	_sucking = null
	_suck_target = null
	# 真正的伤害与「吞掉」仍然走原生的 `be_chomper_eat` ——
	# 这样掉落、音效、咀嚼计时、连杀判定全都和原版大嘴花完全一致，不留分叉。
	if is_instance_valid(enemy):
		enemy.be_chomper_eat(eat_attack)
		# 兜底：万一这一下没把它打死（残血扛住了），体积已经缩掉了，得放回去。
		if is_instance_valid(enemy) and not enemy.is_queued_for_deletion() \
				and is_instance_valid(enemy.body):
			var back: Tween = create_tween()
			back.set_parallel(true)
			back.tween_property(enemy.body, "scale", start_body_scale, 0.16)
			back.tween_property(enemy, "global_position", start_global, 0.16)
	_on_sucked()


## 吸完成之后：盖盖（宣告「满了」）+ 起嚼 + 收壶。
func _on_sucked() -> void:
	_pending_target = null
	SoundManager.play_character_SFX(&"ZuixiankeGulp")
	# 用户要求：僵尸被吸进葫芦后**立即盖上盖子**，表明已经不能再吸。
	# [br]这里就是「僵尸进到瓶子里面」的那一下 —— 之前缺的正是它，所以观众看到的是消失。
	# [br]⚠️ 顺序必须是「先起嚼、再盖盖」：
	# [br]`_play_chew_shake()` 开头会调 `_stop_chew_shake()`，那里把 `_art.position.y`
	# [br]**直接赋值**回 `_art_local_y`。而盖盖的整株动作（`_play_cap_body`）也在 tween
	# [br]`_art.position:y` —— 先盖盖再起嚼的话，那 0.09 秒的「抬手」会被这一句抹掉，
	# [br]盖盖看起来就是硬切。这两条写的是同一个属性，顺序不能反。
	chew_timer.start_scaled()
	is_chewing = true
	_play_chew_shake()
	_set_cap_state(true)
	_release_press()
