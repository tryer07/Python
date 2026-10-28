extends Zombie001Norm
class_name Zombie026Magician

## 魔术师僵尸（Z026）
##
## 立绘只有一张整图，没法像普通僵尸那样改散件，所以换皮是「隐藏 BodyCorrect + 在 Body 下自己挂一套立绘」。
## 「挥动法杖蓄力」用三层叠出来：
##   1. 施法轴 [MagicianPivot] 整体后仰 → 前压（绕脚底转，幅度只有几度，脚不会离地）
##   2. 杖尖光球 [MagicianCharge] 由小到大、符文环越转越快
##   3. 光球撑满的瞬间整条紫电抽出 [MagicianLightning]，光球同时清零 —— 能量「变成」了电
##
## 机制（2026-10-27 按路障僵尸重做，数值结构完全对齐）：
##   * 本体 [constant MAGICIAN_MAX_HP] = 270，和普通僵尸一样；死亡临界值不自己算，
##     走 [HpStageChangeComponent] 的默认档（2/3-1、1/3-1）——**也就是路障僵尸那套**：
##     本体打到 89 点就倒，不是打到 0。别在这里 `set_death_hp(0)`，那会让它比路障硬 181 点。
##   * **魔术帽是二类防具**（[constant MAGICIAN_HAT_HP] = 370），对应路障的一类防具锥形路障：
##     伤害先扣帽子（见 [method HpComponentZombie.Hp_loss] 的匹配顺序），帽子归零才轮到本体。
##     总血量 270+370 = 640，被彻底打死所需的伤害和路障一枪不差。
##   * 帽子走 `body_change_armor2` 的资源驱动（贴图显隐 + 掉落节点），和路障的锥形帽同一条路径，
##     所以小推车碾压时 [`Zombie000Base.be_mowered_run_anim_norm`] 也会顺手把帽子掀飞。
##   * 每 [member attack_interval] 秒远程打一发，单发 [member attack_damage] 点伤害
##   * 一次施法 [member charge_duration] + [member release_duration] = 2 秒，蓄力满才放电，放电期间原地不动
##   * 贴脸时照常啃食（沿用 AttackComponentZombieNorm），啃食期间技能照放，互不干扰
##
## 动作：**整段借原版僵尸的躯干曲线**（见 [constant TORSO_NODE_PATH]），idle / walk / eat
## 自动同相、同幅、同节奏。手调正弦永远追不上它 —— 这是前两版「僵硬」的根因。
##
## 但「借来的幅度」不能 1:1 用：
##   · 站立 / 图鉴展示 → **不转，只平移一丝**。原版待机是头转舌晃的局部运动，
##     整体轮廓几乎不动；整图一转，礼帽和帽檐的水平线就跟着歪，怎么调都「不像」。
##     （用户对图鉴详情页连续反馈三次，最后就是靠这条 0 倾斜解决的，见 [member idle_tilt_scale]。）
##   · 行走 → 倾斜用满，垂直起伏打三折半（没有腿，照搬会变成弹跳），
##     再补一条固定前倾（[member walk_lean_degrees]，是「在走」的静态证据，不是节奏）。
##
## 啃食：整图立绘啃起来本来会「站着不动纯掉血」，所以读动画树里 eat 那条动画的播放头，
## 按 Zombie_eat 的两声 Chomp（[constant EAT_BITE_1] / [constant EAT_BITE_2]）
## 叠一个咬合前冲，和它的节拍严格对齐、且跟着减速一起变慢。
##
## 法杖只在「蓄力」这一段发光：光球的强弱唯一入口是 `_glow_to()`，
## 放电 / 收势 / 死亡一律走 `_glow_off()`，把强度归零、隐藏、并掐掉还在跑的补间。

#region 立绘常量
## 整图立绘（**已经抠掉帽子**的那一层）；透明底，alpha 包围盒 (14,14)-(659,1297)。
## [br]⚠️ 为什么身体和帽子要分两层：帽子是二类防具，被打光必须能单独飞出去。
## 两张贴图是**同一块 674×1312 画布**上抠出来的，所以只要给同一个 position / scale，
## 叠回去和原图逐像素一致（实测差异像素 0），不需要任何对齐微调。
const ART_TEXTURE: Texture2D = preload("res://assets/image/character/zombie_magician/magician_body_nohat.png")
## 帽子层。其余部分全透明，只有帽顶/帽檐/紫色缎带。
const ART_HAT_TEXTURE: Texture2D = preload("res://assets/image/character/zombie_magician/magician_hat.png")
## 脚底在贴图像素坐标中的位置（贴图 674x1312，最底部一行已全透明，脚掌质心 x≈428）
const ART_FOOT_PIXEL := Vector2(428.0, 1298.0)
## 贴图里人物的实体像素高度（包围盒高 1284）
const ART_BODY_PIXEL_H := 1284.0
## 战场立绘高度（按贴图里人物的实体像素高换算，不含透明边）。
## 实测「不透明像素高」：普通僵尸 121、路障僵尸 138。
## 132 比普僵高 9%（看着是个「有点分量的施法者」），又没到路障那头锥形帽的高度。
const ART_TARGET_HEIGHT := 132.0
## 展示态（选卡界面的僵尸展示、图鉴详情）的立绘高度。
## 展示态是几只僵尸并排比对的地方，这里必须和普通僵尸齐平（121），
## 否则又回到「这一只看上去比旁边大一号」的老问题。
const ART_SHOW_HEIGHT := 121.0
## 杖尖白球在贴图像素坐标中的位置（左手手杖最前端那颗球）。
## 实测：白球连通域 x 22..61、y 1078..1117，取圆心 (41.5, 1097.5)。
## [br]⚠️ 早先写的是 (102, 1003) —— 那是手背那边的读数，比球高 94px。
## 换算到战场就是光球浮在杖尖**上方 10 像素**，看着像「杖旁边挂了颗灯」，已按实测改正。
const ART_WAND_PIXEL := Vector2(41.5, 1097.5)
#endregion

## 本体血量：**和普通僵尸、路障僵尸一模一样**（270）。
## [br]⚠️ 别在这里加总血。以前写的是 640「等于路障名义总血」，结果没有护甲结构、
## 又把死亡线拉到 0，实际比路障耐打得多。现在 640 由 270 本体 + 370 魔术帽凑出来，
## 和路障的 270 + 370 锥形路障是同一个配方（见 [constant MAGICIAN_HAT_HP]）。
const MAGICIAN_MAX_HP := 270
## 魔术帽（二类防具）的耐久。取路障锥形路障的 370，总血量因此也是 640。
const MAGICIAN_HAT_HP := 370
## ── 动作驱动：直接借用原版僵尸的躯干曲线 ────────────────────────────────
## ⚠️⚠️ 2026-10-27 第三次返工 —— 整段重写的核心，先读这里再看代码。
##
## 前两版都是「手调幅度」：算一条正弦 + 几个常量，指望调出「像普通僵尸」的量。
## 两版都被否掉（「摇摆幅度和其它僵尸完全不一样」「还是非常僵硬」），
## 根因是**手调的正弦不可能和原版动画同相、同幅、同节奏**：
## 原版僵尸的动作是 151 条轨道一起算出来的，躯干那条本身就不是正弦。
##
## 现在改成「照抄」：
##   · 原版僵尸的整图由 AnimationTree 驱动，`Body/BodyCorrect/Zombie_body`（躯干）
##     和 `Zombie_neck`（颈）每帧都被写入真实位移；
##   · 换皮只把 `BodyCorrect` 整棵隐藏，**动画照常在对它写值**；
##   · 所以每帧读 `Zombie_body.position` 的偏移量，就是「这一刻普通僵尸的躯干在哪」。
##
## idle / walk / eat / 死亡全自动同步，寒冰减速、时间尺度、状态切换一律不用自己管 ——
## 因为用的就是同一份数据。
## 实测原版躯干位移范围（贴图像素，rig 与屏幕 1:1）：
##   Zombie_idle  x 27.0~39.9  y 29.9~37.0   →  12.9 × 7.1
##   Zombie_walk  x 19.0~34.0  y 27.0~35.8   →  15.0 × 8.8
##   Zombie_eat   x 27.2~30.3  y 31.7~35.5   →   3.1 × 3.8
## 对比魔术师旧版手调待机 0.7px / 0.56° —— **差 18 倍**，这就是「雕像感」的来源。
const TORSO_NODE_PATH := "Zombie_body"
## 躯干位移轨道的路径（相对僵尸根节点），用来从动画资源里读出「正中姿势」
const TORSO_TRACK_PATH := "Body/BodyCorrect/Zombie_body:position"
## 垂直分量只借一部分：躯干平移 1:1 搬到整图上**脚会跟着离地**，
## 原版是腿在下面撑着，我们没有腿，所以垂直只借一半左右，走路时再打三折（见 `_process`）。
@export_range(0.0, 1.5, 0.05) var torso_bob_gain: float = 0.55
## 躯干水平位移 → 绕脚底旋转的放大系数。**1.0 = 头顶横移量和原版躯干完全一致**，
## 也就是「整株的倾斜量」正好等于原版躯干身体的倾斜量，走路时对得最准。
## [br]⚠️ 这个值不要往「对齐头」的方向加。原版躯干的横移只是它身体在动，
## 头比它多摆的那部分来自颈和头的**局部**旋转；整图立绘没有局部，一加就是整块倾斜，
## 帽子、肩膀、斗篷的水平线一起歪 —— 眼睛对这种整体倾斜极度敏感，
## 两三度就能看出「和旁边那只不是一个物种」。实测加到头摆幅（1.9 倍）会歪到 12°，已经像喝醉。
@export_range(0.0, 3.0, 0.05) var torso_sway_gain: float = 1.0
## 待机时倾斜的折减系数。**默认 0，也就是站着时一点都不转**。
## [br]原版僵尸的待机是「局部在动」：头转、舌头晃、手摆，而**整个轮廓几乎不动**
## （头世界横移 4.8px，脚只有 1.5px）。整图立绘做不出局部，只能整块转 ——
## 一转头顶礼帽和帽檐的水平线就跟着歪，哪怕只有 0.6°，眼睛立刻读成「整块纸片在晃」，
## 和旁边安静的僵尸完全不是一个物种。**图鉴详情页把这个毛病放到最大**：
## 旁边几只几乎静止，这只在慢慢摇，用户三次反馈「还是没改过来」就是它。
## [br]所以站立状态一律不转，只留极小的平移（见 [member idle_shift_gain]）。
@export_range(0.0, 1.0, 0.05) var idle_tilt_scale: float = 0.0
## 待机时改用「整株小幅平移」的力度。平移不改变轮廓形状，不会读成「歪」，
## 但脚会跟着滑 —— 展示态僵尸本来就不走路，两像素以内看不出来，这是划算的交换。
## [br]0.22 ≈ 原位横移量的 22%，待机实测约 ±1.4px（原版头是 ±2.4px）。再大就开始像「飘」。
@export_range(0.0, 2.0, 0.05) var idle_shift_gain: float = 0.22
## 待机时垂直方向的折减。原版躯干待机上下 7.1px，那是双腿在下面伸屈撑出来的；
## 整图立绘没有腿，照搬就是整个人在浮。0.30 之后约 ±0.6px，只是「还有呼吸」。
@export_range(0.0, 1.0, 0.05) var idle_bob_scale: float = 0.30
## 啃食时把借来的躯干动作放大。原版 eat 曲线本身很小（3.1px），
## 因为它靠下巴和手臂在演，整图立绘没有这两样，不放大读不出「在咬」。
@export_range(1.0, 4.0, 0.1) var eat_motion_gain: float = 2.2

## 普通僵尸的啃食循环，从动画资源里读出来的实测值（不是估的）：
## `Zombie_eat.tres` 时长 3.25 秒、循环播放；`attack_once`（那声 Chomp、也是真正
## 结算「咬一口」的那一刻）的时间轨落在 0.75 与 2.41667 秒。
## 咬合前冲对齐这两个点，才谈得上「和普通僵尸一样」。
const EAT_LOOP := 3.25
## 一口的两个时间点（秒），从 `Zombie_eat.tres` 的方法轨读出来的
const EAT_BITE_1 := 0.75
const EAT_BITE_2 := 2.41667
## 咬合脉冲的上升/回落时长（秒）。咬下去是快动作、松口是慢的，所以上升短回落长
const EAT_PULSE_RISE := 0.30
const EAT_PULSE_FALL := 0.42
## 状态机里「啃食」这个状态的名字（顶层 `AnimationNodeStateMachine` 的一个 state）
const EAT_STATE_NAME := &"eat"
## 顶层状态 → 它底下可能播的那几条动画。
## [br]Idle 和 Walk 内部各自套了一层小状态机，会在两条动画之间轮换
## （Zombie_idle ↔ Zombie_idle2、Zombie_walk ↔ Zombie_walk2），这里把两条都列上，
## 取它们中点的平均作为这个状态的「正中姿势」。
## [br]⚠️ 不要按「当前正在播哪一条」去换中心值 —— 小状态机切换时中心会跟着跳，
## 整株就被「追着抹平」，实测摆幅被削掉两成多（像被谁按住了一样）。
const STATE_ANIM_GROUPS := {
	&"Idle": [&"Zombie_idle", &"Zombie_idle2"],
	&"Walk": [&"Zombie_walk", &"Zombie_walk2"],
	&"eat": [&"Zombie_eat"],
}
## 啃食那条动画在动画树里的播放头路径。eat 状态内部是 BlendTree：
## `Animation → TimeScale → output`，所以真正在被播放的那条动画叫 `Animation`。
## [br]有了它就能直接问「这一口咬到第几秒了」，不必猜播放速度。
const EAT_POS_PATH := "parameters/StateMachine/eat/Animation/current_position"
## 动画树里两处时间缩放的路径。啃食那条动画在里面是 2.0 倍速，外面整棵树还有一层
## `TimeScale/scale = 1.2`，两层相乘才是真实的播放速度 —— 读播放头失败时用它兜底计时。
const ANIM_TOP_SCALE_PATH := "parameters/TimeScale/scale"
const ANIM_EAT_SCALE_PATH := "parameters/StateMachine/eat/TimeScale/scale"
## 行走时垂直只借三成半。`Zombie_walk` 的躯干上下有 8.8px，那是腿在下面伸缩撑出来的，
## 整图立绘没有腿，照搬就是「原地弹跳」。
const WALK_BOB_SCALE := 0.35

@export_group("远程紫电")
## 两次施法的间隔（秒），从这次开始蓄力算到下次开始蓄力
@export var attack_interval: float = 10.0
## 单次紫电伤害
@export var attack_damage: int = 500
## 索敌最远距离（像素），超出这个距离就不放技能，免得在屏幕外隔空打植物
@export var attack_range: float = 520.0
## 蓄力（挥杖）时长，到点放电
@export var charge_duration: float = 1.0
## 放电后的收势时长；和蓄力加起来就是整段施法 2 秒
@export var release_duration: float = 1.0

@export_group("施法姿态")
## 后仰角度（度），正数=上半身往右倒，也就是往后仰
@export var windup_degrees: float = 9.0
## 挥出角度（度），负数=往前压
@export var strike_degrees: float = -7.0

@export_group("行走表现")
## 行走时的固定前倾（度，负数=往屏幕前方压）。
## 没有腿的情况下，身体稍微「探出去」是「在走」这件事最省力的证据。
## ⚠️ 行走的起伏与侧倾不再由这里给 —— 全部来自原版 `Zombie_walk` 的躯干曲线。
## 这里只剩这一条「姿态」参数：它是常量偏移，不是节奏。
@export var walk_lean_degrees: float = -1.6

@export_group("啃食表现")
## 一口咬下去的前冲距离（像素，往前=负 x）。
## [br]2026-10-27 第三次调：原版 eat 的躯干只动 3.1px（它靠下巴和手臂演），
## 整图立绘必须把「咬」画大才看得见。11px ≈ 身高 8%，配 8° 前压才读得出「扑上去咬」。
@export var eat_lunge_px: float = 11.0
## 咬合时的前倾角度（度，负数=往前压）
@export var eat_lean_degrees: float = -8.0
## 咬合时身体下沉（像素），表现「咬住往下拽」
@export var eat_dip_px: float = 4.0
## 咬到底时整株纵向压扁的比例。咬合是「上下合拢」，3.5% 的压缩刚好读出这一下，
## 再多就会变成橡皮球。
@export var eat_squash: float = 0.035

#region 运行时节点
## 施法姿态轴，绕脚底旋转
var _cast_pivot: Node2D
## 行走起伏节点，和施法轴分开，补间不会互相打架
var _bob_node: Node2D
## 整图立绘
var _art: Sprite2D
## 帽子层（二类防具的表现）。和 [member _art] 同 position / scale，叠在上面
var _hat: Sprite2D
## 帽子被打光后用来飞出去的那块。场景里挂好的 `Body/NodeDrop/Node2D_HatDrop/Hat_Drop`；
## 掉落瞬间把 [member _hat] 的全局变换抄过来，帽子就从头上原位置脱手，不会「闪现一下再掉」
var _hat_drop_body: Node2D
## 杖尖空节点，紫电从这里出发
var _wand_tip: Node2D
## 杖尖蓄力光球
var _charge: MagicianCharge
## 施法节拍器
var _cast_timer: Timer
#endregion

## 是否正在施法（施法期间不再接新的施法）
var _is_casting := false
## 行走状态的平滑权重（1=在走）。只用来过渡那条固定前倾，节奏不靠它
var _bob_weight := 0.0
## 当前立绘高度，切换展示/战场时平滑过渡
var _art_height := ART_TARGET_HEIGHT
## 可攻击的植物状态位，从检测组件读，读不到就用默认的「正常+低矮」
var _attackable_plant_status: int = 9
## 是否正在啃食。**每帧从攻击组件轮询**，不依赖信号 —— 理由见 `_process`
var _eat_active := false
## 上一帧是否在啃食，用来抓「刚咬上去」的那一帧
var _was_eating := false
## 啃食自计时。只在读不到动画播放头时当退路用，正常情况下以动画时间为准
var _eat_clock := 0.0
## 啃食段动画的实际播放速度倍率（两层 TimeScale 相乘）。兜底计时用它换算成动画时间
var _eat_speed := 1.0
## 普通僵尸的 AnimationTree（路径固定是根下的 "AnimationTree"）。
## [br]⚠️ 不要改用 `AnimationPlayer.current_animation` 判状态 —— 实测它始终是空串
## （动画走的是 AnimationTree 的状态机，不回填这个字段），照那个写会永远走进兜底分支。
var _anim_tree: AnimationTree = null
## 顶层状态机的播放控制器，用来问「现在是不是在 eat」以及咬到第几秒
var _eat_playback: AnimationNodeStateMachinePlayback = null
## 蓄力光球的补间。单独记一份，放电/中断时要能立刻掐掉，
## 否则它继续往 1.0 走，杖尖就会「莫名其妙一直亮着」
var _glow_tween: Tween = null

## ── 借用原版躯干动作 ────────────────────────────────────────────────────
## 原版僵尸被 AnimationTree 驱动的那块躯干（`Body/BodyCorrect/Zombie_body`）。
## 换皮只隐藏了 BodyCorrect，**动画仍然每帧在写它的 position**，读出来就是现成的动作。
var _torso: Node2D = null
## 各条动画里「躯干的正中姿势」= 该条轨道所有关键帧的最小/最大值的**中点**。
## 键是动画名（Zombie_idle / Zombie_walk / Zombie_eat …），在 `_ready` 里一次算好。
## [br]为什么不用场景里的静止坐标：实测它是 (38.14, 31.07)，而 idle 的摆动区间是
## 27.0~39.9 —— 静止值贴着最大值，拿它当零点会让整株永久歪 5°。
## [br]为什么不用「运行中观察到的包络」：包络跨越状态会取并集，切换后中心是旧状态和新状态
## 的中点，实测把摆幅削掉 25%，而且会持续几秒慢慢回正 —— 肉眼就是「越走越回去」。
## 剪辑里的中点是个定值，摆幅一点不损失。
var _state_center: Dictionary = {}
## 当前正在追踪的那个「正中姿势」
var _torso_center := Vector2.ZERO
## 目标正中姿势（切状态时换它，`_torso_center` 平滑追过去，避免「啪」地正回来）
var _torso_center_target := Vector2.ZERO
## 当前躯干相对正中姿势的偏移（rig 贴图像素，y 正 = 向下）
var _torso_delta := Vector2.ZERO
## 固定不动的偏差（直流分量），由慢速滑动平均估出来再减掉，见 `_sync_torso_motion`
var _torso_dc := Vector2.ZERO


func _ready() -> void:
	super()
	_apply_magician_art()
	## 帽子归零的那一帧先把掉落节点对到头上（这条信号早于 body_change_armor2 的隐藏/激活）
	var hp_zombie := hp_component as HpComponentZombie
	if hp_zombie != null:
		hp_zombie.signal_armor2_death.connect(_sync_hat_drop)
	_apply_magician_stats()
	## 展示/花园状态不放技能，只有正常出战才开节拍器
	if character_init_type == E_CharacterInitType.IsNorm:
		_setup_cast_timer()
	## 啃食状态每帧轮询攻击组件的判定结果，不再连信号（理由见 `_process`）
	_anim_tree = get_node_or_null("AnimationTree") as AnimationTree
	if _anim_tree != null:
		_eat_playback = _anim_tree.get("parameters/StateMachine/playback") \
			as AnimationNodeStateMachinePlayback
		_refresh_eat_speed()
	_build_state_centers()


#region 换皮
## 隐藏普僵散件，在 Body 下挂一套整图立绘 + 杖尖
func _apply_magician_art() -> void:
	## 散件全部收起来。注意不能直接删/停动画：移动组件靠 BodyCorrect/_ground 的位移在跑
	var body_correct := body.get_node_or_null("BodyCorrect")
	if body_correct != null:
		body_correct.visible = false
		## 顺手抓住被 AnimationTree 驱动的躯干节点 —— 整套动作的数据源（见 TORSO_NODE_PATH）。
		var torso_node := body_correct.get_node_or_null(TORSO_NODE_PATH) as Node2D
		if torso_node != null:
			_torso = torso_node
			_torso_center = torso_node.position

	_cast_pivot = Node2D.new()
	_cast_pivot.name = "MagicianCastPivot"
	body.add_child(_cast_pivot)

	_bob_node = Node2D.new()
	_bob_node.name = "MagicianBob"
	_cast_pivot.add_child(_bob_node)

	_art = Sprite2D.new()
	_art.name = "MagicianArt"
	_art.texture = ART_TEXTURE
	_art.centered = false
	_bob_node.add_child(_art)

	## 帽子单独一层，叠在身体上面（同一块画布的同一套坐标，直接同 position / scale 就严丝合缝）。
	## 它是二类防具的表现层：被打光的瞬间会由 `body_change_armor2` 里的 `sprite_disappear` 隐藏，
	## 所以节点名 `MagicianHat` 是**被场景文件里的 NodePath 引用的**，别随手改。
	_hat = Sprite2D.new()
	_hat.name = "MagicianHat"
	_hat.texture = ART_HAT_TEXTURE
	_hat.centered = false
	_bob_node.add_child(_hat)

	_hat_drop_body = get_node_or_null("Body/NodeDrop/Node2D_HatDrop/Hat_Drop") as Node2D

	_wand_tip = Node2D.new()
	_wand_tip.name = "WandTip"
	## 立绘带缩放，杖尖要挂在立绘外面单独换算，否则光球会被缩放压小
	_bob_node.add_child(_wand_tip)

	## 展示态入树前 is_show 就已经是 true，所以出生时直接按对应高度定尺
	_art_height = ART_SHOW_HEIGHT if is_show else ART_TARGET_HEIGHT
	_set_art_height(_art_height)

	_charge = MagicianCharge.new()
	_charge.name = "MagicianCharge"
	_charge.max_radius = 10.0
	## 出生就是「不发光」：法杖只在蓄力那 1 秒亮。
	## 除了 level=0（自身也不画），这里再叠一道 visible，双保险防止有补间漏写
	_charge.level = 0.0
	_charge.visible = false
	_wand_tip.add_child(_charge)

	var detect_component := attack_component.detect_component
	if detect_component != null:
		_attackable_plant_status = detect_component.can_attack_plant_status


## 按目标高度重设立绘缩放，并让脚底始终落在僵尸原点（地面）
## [param target_height] 立绘里人物的实体像素高对应的显示高度
func _set_art_height(target_height: float) -> void:
	var art_scale: float = target_height / ART_BODY_PIXEL_H
	_art.scale = Vector2(art_scale, art_scale)
	## 让贴图的脚底正好落在僵尸原点（地面）
	_art.position = -ART_FOOT_PIXEL * art_scale
	## 帽子必须是身体的**同一个变换**：同画布挖出来的两层，复制过去就天然对齐
	if _hat != null:
		_hat.scale = _art.scale
		_hat.position = _art.position
	## 杖尖跟着立绘一起缩，否则光球会在换尺寸后错位
	if _wand_tip != null:
		_wand_tip.position = _art.position + ART_WAND_PIXEL * art_scale


#region 血量 / 防具
## 血量落地。**数值的唯一来源是场景文件**，这里只兜底 + 清掉整图立绘用不上的散件阶段。
## [br]⚠️ 三条不能碰的东西（都是上一版的病根）：
##   · 不要 `boundary_value_hp.assign([0])`：那是「打到 0 才死」。留空让它按 max_hp 自动填
##     2/3-1、1/3-1，才是路障僵尸的临界值（本体 270 → 打到 89 就倒）。
##   · 不要 `hp_component.set_death_hp(0)`：默认已经按 boundary_value_hp[-1] 设好了。
##   · 不要把本体血量写成 640：总血 640 由「本体 270 + 帽子 370」凑，硬塞给本体就变成没护甲还加倍。
func _apply_magician_stats() -> void:
	## 兜底校验：万一继承的场景被改成别的数，临界值会按错的 max_hp 算，这里纠回来
	if hp_component.max_hp != MAGICIAN_MAX_HP:
		hp_component.max_hp = MAGICIAN_MAX_HP
		hp_component.curr_hp = MAGICIAN_MAX_HP
		## 临界值是组件在 `_ready` 里按当时的 max_hp 现算的，改完必须同步重算，
		## 否则会留着一份按旧 max_hp 算出来的档位（那才是「临界值不对」的来源）
		if hp_stage_change_component != null:
			var boundary_2: int = floori(MAGICIAN_MAX_HP * 2.0 / 3.0) - 1
			var boundary_1: int = floori(MAGICIAN_MAX_HP / 3.0) - 1
			hp_stage_change_component.boundary_value_hp.assign([boundary_2, boundary_1])
			hp_component.set_death_hp(boundary_1)
	var hp_zombie := hp_component as HpComponentZombie
	if hp_zombie != null and hp_zombie.max_hp_armor2 != MAGICIAN_HAT_HP:
		hp_zombie.max_hp_armor2 = MAGICIAN_HAT_HP
		hp_zombie.curr_hp_armor2 = MAGICIAN_HAT_HP
	if hp_stage_change_component != null:
		## 普僵那套「掉手 → 掉头」对整图立绘没意义，两个阶段都留空。
		## [br]数组长度必须和 boundary_value_hp 对齐（自动填的是 2 档），
		## 少给一个会在 `judge_body_change` 里索引越界。
		hp_stage_change_component.body_change.assign([null, null])


## 帽子被彻底打掉（二类防具归零）之前的最后一次对表：
## 把「帽子此刻在屏幕上的变换」抄给掉落节点，帽子就从头上原地脱手飞出去。
## [br]为什么能这么抄：`ZombieDropBase.acitvate_it()` 用的是 `reparent()`，
## 默认保留全局变换，所以这块东西不会在脱手那一帧跳一下。
## [br]时机：`signal_armor2_death` 是在 `curr_hp_armor2` 的 setter 里发的，
## 早于 `body_change_armor2` 的隐藏/激活，所以这里抄完它才真正飞。
func _sync_hat_drop() -> void:
	if not is_instance_valid(_hat_drop_body) or not is_instance_valid(_hat):
		return
	_hat_drop_body.global_transform = _hat.global_transform
#endregion


#region 施法节拍
func _setup_cast_timer() -> void:
	_cast_timer = Timer.new()
	_cast_timer.name = "MagicianCastTimer"
	_cast_timer.wait_time = maxf(attack_interval, 0.5)
	_cast_timer.one_shot = false
	_cast_timer.timeout.connect(_on_cast_timer_timeout)
	add_child(_cast_timer)
	_cast_timer.start(_cast_timer.wait_time)


func _on_cast_timer_timeout() -> void:
	if is_death or is_hypno or _is_casting:
		return
	## 这里只判断「有没有可打的东西」，不锁定具体是哪一株 ——
	## 真正打谁在 [method _fire] 结算那一刻才决定，理由见那里的注释
	if _find_target() == null:
		return
	_cast_at()


## 整段施法：停下 → 挥杖蓄力 → 放电 → 收势 → 继续走
func _cast_at() -> void:
	_is_casting = true
	## IsAnimGap 是「动画间隙暂停」，和啃食用的 IsAttack 分开，啃食时不会被这一条覆盖掉
	move_component.update_move_factor(true, MoveComponent.E_MoveFactor.IsAnimGap)
	_play_windup()

	await _await_seconds(charge_duration)
	if not _can_continue_cast():
		return

	_fire()
	_play_strike()

	await _await_seconds(release_duration)
	_end_cast()


func _can_continue_cast() -> bool:
	return not is_death and is_inside_tree()


func _end_cast() -> void:
	_is_casting = false
	## 收势结束一定要熄灯：不管前面有没有走到 `_fire`，这里都兜住
	_glow_off()
	if is_death:
		return
	move_component.update_move_factor(false, MoveComponent.E_MoveFactor.IsAnimGap)


## 计时器换一种写法，让它跟着游戏暂停一起停；process_always=false
func _await_seconds(seconds: float) -> void:
	await get_tree().create_timer(maxf(seconds, 0.01), false).timeout
#endregion


#region 施法表现
## 后仰蓄力：前 72% 缓慢后仰，最后 28% 绷住再抖一点
func _play_windup() -> void:
	if _cast_pivot == null:
		return
	var windup_time: float = charge_duration * 0.72
	var tense_time: float = charge_duration - windup_time

	var wind := create_tween()
	wind.set_trans(Tween.TRANS_SINE)
	wind.tween_property(_cast_pivot, "rotation", deg_to_rad(windup_degrees), windup_time).set_ease(Tween.EASE_OUT)
	wind.parallel().tween_property(_cast_pivot, "position:x", 4.0, windup_time).set_ease(Tween.EASE_OUT)
	wind.tween_property(_cast_pivot, "rotation", deg_to_rad(windup_degrees + 2.0), tense_time)

	if _charge != null:
		_glow_to(1.0, charge_duration)


#region 法杖发光：只有蓄力才亮
## 把光球推到目标强度。**这是唯一允许让法杖发光的入口**，别处一律走 `_glow_off()`。
func _glow_to(target: float, time: float) -> void:
	if not is_instance_valid(_charge):
		return
	if is_instance_valid(_glow_tween):
		_glow_tween.kill()
	_charge.visible = true
	_glow_tween = create_tween()
	_glow_tween.tween_property(_charge, "level", target, maxf(time, 0.01)) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)


## 立刻熄灭：强度归零 + 隐藏 + 掐掉还在跑的补间。
## [br]三件事缺一不可 —— 只把 `level` 置 0 的话，那条补间还在往 1.0 爬，
## 下一帧光球又自己亮回来，表现就是「没在施法、法杖却一直亮着」。
func _glow_off() -> void:
	if is_instance_valid(_glow_tween):
		_glow_tween.kill()
		_glow_tween = null
	if not is_instance_valid(_charge):
		return
	_charge.level = 0.0
	_charge.visible = false
#endregion


## 挥出：快速前压，然后慢慢收回站姿
func _play_strike() -> void:
	if _cast_pivot == null:
		return
	var snap_time: float = 0.14
	var recover_time: float = maxf(release_duration - snap_time, 0.05)

	var strike := create_tween()
	strike.set_trans(Tween.TRANS_SINE)
	strike.tween_property(_cast_pivot, "rotation", deg_to_rad(strike_degrees), snap_time).set_ease(Tween.EASE_OUT)
	strike.parallel().tween_property(_cast_pivot, "position:x", -6.0, snap_time).set_ease(Tween.EASE_OUT)
	strike.tween_property(_cast_pivot, "rotation", 0.0, recover_time).set_ease(Tween.EASE_IN_OUT)
	strike.parallel().tween_property(_cast_pivot, "position:x", 0.0, recover_time).set_ease(Tween.EASE_IN_OUT)


## 放电 + 结算伤害。
## [br]⚠️ **目标在结算这一刻才确定**，不在蓄力开始时锁定。
## 从开始蓄力到伤害真正落地有 [member charge_duration] 秒（默认 1 秒），这期间玩家完全
## 可能在最前面补种一株 —— 规则既然是「打最前面的那一株」，那就该打在那株新的身上。
## 锁定旧目标的写法会让紫电穿过刚种下的坚果去打后排，看着像穿模。
## [br]结算时找不到目标就只放电、不结算伤害（视觉上是一道打空的电）。
func _fire() -> void:
	## 光球一次性清零，读起来就是「能量变成了这道电」
	_glow_off()

	var from_global: Vector2 = global_position + Vector2(-30.0, -30.0)
	if is_instance_valid(_wand_tip):
		from_global = _wand_tip.global_position

	var target: Plant000Base = _find_target()
	var is_target_alive: bool = target != null
	var to_global: Vector2 = from_global + Vector2(-attack_range * 0.35, 0.0)
	if is_target_alive:
		to_global = _plant_hit_global(target)

	var bolt := MagicianLightning.new()
	add_child(bolt)
	bolt.setup(from_global, to_global)
	bolt.cast()

	if is_target_alive:
		target.be_zombie_eat(attack_damage, self)
		target.body.body_light()
#endregion


#region 索敌
## 找同一行里、在自己前面、射程内、位置最靠右（离自己最近）的植物
func _find_target() -> Plant000Base:
	if lane < 0:
		return null
	## Global.main_game 是运行时注入的，静态类型推不出来，这里显式标注
	var plant_cell_manager: PlantCellManager = Global.main_game.plant_cell_manager
	if plant_cell_manager == null or lane >= plant_cell_manager.all_plant_cells.size():
		return null

	var cells: Array = plant_cell_manager.all_plant_cells[lane]
	## 格子数组是从左到右排的，僵尸从右边来，所以倒着找第一个就是最近的
	for i: int in range(cells.size() - 1, -1, -1):
		var plant_cell := cells[i] as PlantCell
		if plant_cell == null:
			continue
		var plant := plant_cell.get_bungi_target()
		if plant == null or plant.is_death:
			continue
		## 状态不允许被攻击的（比如在地下的地刺）不打
		if (plant.curr_be_attack_status & _attackable_plant_status) == 0:
			continue
		var distance_x: float = global_position.x - plant.global_position.x
		## 已经在身后了，或者还太远
		if distance_x <= 0.0 or distance_x > attack_range:
			continue
		return plant
	return null


## 紫电命中点：植物原点在脚下，往上抬一点打到身上
func _plant_hit_global(plant: Plant000Base) -> Vector2:
	return plant.global_position + Vector2(0.0, -40.0)
#endregion


#region 行走 / 啃食 / 待机
## 整图立绘的位移完全由原版动画驱动，见文件顶部 [constant TORSO_NODE_PATH] 那一大段。
## 这里只负责把这个「躯干偏移」翻译成立绘能做的动作，外加两条手写的补充：
##
##   · 水平偏移 → 绕脚底旋转（θ = dx / 立绘高度 × [member torso_sway_gain]）：
##     头顶横移量和原版躯干同量级，脚底不动、不滑步
##   · 垂直偏移 → 打折平移（[member torso_bob_gain]，走路再打三折）：整图平移会让脚离地
##   · 固定前倾 −1.6°：只在走路时给，是「在走」的静态证据
##   · 啃食咬合脉冲：对齐 `Zombie_eat` 里那两声 Chomp，原版那条躯干曲线太小，必须自己画
##
## ⚠️ 只动 [MagicianBob]、不动 [MagicianCastPivot]：后者被施法补间占着，两边一起写会互相盖掉。
func _process(delta: float) -> void:
	if _bob_node == null:
		return
	var is_moving: bool = move_component.is_move and not is_death and not is_show
	_bob_weight = lerpf(_bob_weight, 1.0 if is_moving else 0.0, minf(1.0, delta * 6.0))

	## 啃食状态**每帧轮询**攻击组件的判定结果，不连信号。
	## [br]⚠️ 旧版连的是 `signal_change_is_attack`，但那条信号只在「能否攻击」发生**翻转**时发一次；
	## 僵尸要是出生就贴着植物、或者信号在 `_ready` 之前就已经发过，连接完成后就再也收不到 ——
	## 表现就是「明明在啃，咬合动作一次都不出现」。轮询 `is_attack_res` 没有这个时序问题。
	var eat_now: bool = not is_show and not is_death
	if eat_now and is_instance_valid(attack_component):
		eat_now = attack_component.is_attack_res
	if eat_now and not _was_eating:
		## 刚咬上去：自计时清零，第一口才踩在动画 0.75 秒那一拍上
		_eat_clock = 0.0
	_was_eating = eat_now
	_eat_active = eat_now

	_sync_torso_motion(delta)

	## ── 把「原版躯干的位移」翻译成立绘做得到的两个动作 ────────────────────
	## 水平：整图没有腿，平移等于连脚一起滑（读作溜冰）。改成**绕脚底旋转**：
	##   转 θ 弧度时头顶（高 H）横移 H·sinθ，令 θ = dx / H，头顶横移量就**正好等于**
	##   原版躯干的横移量 —— 幅度一致，脚底不动。
	## 垂直：直接平移，但打折（见 torso_bob_gain）。原版躯干下沉时腿会跟着屈，脚并不动；
	##   整图跟着 1:1 下沉会陷进地里。
	##   走路时再打三折：`Zombie_walk` 的躯干上下有 8.8px，那是腿在下面伸缩撑出来的，
	##   整图立绘没有腿，照搬就是「原地弹跳」—— 这是上一版被吐槽过的老毛病。
	var art_h: float = maxf(_art_height, 1.0)
	var motion_gain: float = eat_motion_gain if _eat_active else 1.0
	## 走路的摇摆比待机大得多（实测头 26.7px vs 4.8px），所以两条腿分别给：
	## 站立时倾斜归零（[member idle_tilt_scale]），只留一丝平移；走路才用满倾斜。
	var tilt_scale: float = lerpf(idle_tilt_scale, 1.0, _bob_weight)
	var sway_gain_now: float = torso_sway_gain * tilt_scale
	var rot_drive: float = _torso_delta.x / art_h * sway_gain_now * motion_gain
	## 待机的水平位移走平移（轮廓不变形），走路归零 —— 走路时平移就是滑步
	var x_drive: float = _torso_delta.x * idle_shift_gain * (1.0 - _bob_weight) * motion_gain
	var bob_gain_now: float = torso_bob_gain * lerpf(idle_bob_scale, WALK_BOB_SCALE, _bob_weight)
	var y_drive: float = _torso_delta.y * bob_gain_now * motion_gain

	## 固定前倾：只在走路时给，是「在走」的静态证据（不是节奏）
	var rot_lean: float = deg_to_rad(walk_lean_degrees) * _bob_weight

	## 啃食：按 `Zombie_eat` 的时间轴叠一个咬合脉冲。
	## 原版躯干在 eat 里只动 3px，靠下巴和手臂演；整图立绘没有这两样，
	## 必须自己把「扑上去咬」画出来，否则就是站着不动纯掉血。
	var bite: float = _eat_amount(delta)
	var x_eat: float = -bite * eat_lunge_px
	var y_eat: float = bite * eat_dip_px
	var rot_eat: float = deg_to_rad(eat_lean_degrees) * bite
	var eat_squash_now: float = bite * eat_squash

	_bob_node.position = Vector2(x_drive + x_eat, y_drive + y_eat)
	_bob_node.rotation = rot_drive + rot_lean + rot_eat
	_bob_node.scale = Vector2(1.0 + eat_squash_now * 0.6, 1.0 - eat_squash_now)

	## 展示态和战场的立绘高度不一样，切换时（选卡 → 上场）平滑过渡，不要「啪」地跳一下
	var target_height: float = ART_SHOW_HEIGHT if is_show else ART_TARGET_HEIGHT
	if not is_equal_approx(_art_height, target_height):
		_art_height = lerpf(_art_height, target_height, minf(1.0, delta * 8.0))
		if absf(_art_height - target_height) < 0.05:
			_art_height = target_height
		_set_art_height(_art_height)


## 从原版僵尸的躯干节点上取「这一刻的位移偏移」。
## [br]这是整套动作的数据源：动画在写、我们只读，所以节奏天然和普通僵尸一致 ——
## 不需要自己算相位。
## [br]参数 [param delta] 只用于中心值平滑的速度，与动作节奏无关。
func _sync_torso_motion(delta: float) -> void:
	if not is_instance_valid(_torso):
		_torso_delta = Vector2.ZERO
		return
	var state_name: StringName = _current_state_group()
	if state_name != &"" and _state_center.has(state_name):
		_torso_center_target = _state_center[state_name]
	## 中心值平滑跟过去（约 0.1 秒）。不直接赋值是因为状态切换那一帧中心会跳 2~7px，
	## 整株会「啪」地正一下；平滑一下就读成自然的姿态过渡。
	_torso_center = _torso_center.lerp(_torso_center_target, minf(1.0, delta * 12.0))
	var raw: Vector2 = _torso.position - _torso_center
	## 直流微调：`_torso_center` 是「这一组动画的中点的平均」，而实际可能只播组里的一条，
	## 两条的中点不一样时整株会固定歪两三度。这里用一条很慢的滑动平均把这个固定偏差吃掉。
	## [br]慢到什么程度：周期 1.5 秒的摆动在这个时间常数下只会漏进去不到一成，
	## 所以摆幅基本不损；但「一直歪着」这种直流偏差会在三四秒内被抹平。
	_torso_dc = _torso_dc.lerp(raw, minf(1.0, delta * 0.35))
	_torso_delta = raw - _torso_dc


## 现在顶层状态机停在哪个状态（Idle / Walk / eat …）。
## 只认有中位姿态可查的那几个，死亡之类返回空串 —— 中心值保持不动，不会乱跳。
func _current_state_group() -> StringName:
	if not is_instance_valid(_eat_playback):
		return &""
	return _eat_playback.get_current_node()


## 把 AnimationPlayer 里每一条动画的「躯干正中姿势」算出来，再按状态归组取平均备用。
## 中点 = 该轨道全部关键帧的 min/max 的中点。用中点而不是平均值，是为了让摆幅左右对称 ——
## 关键帧在时间上并不均匀，平均值会被密集的那一段拽偏。
func _build_state_centers() -> void:
	var player := get_node_or_null("AnimationPlayer") as AnimationPlayer
	if player == null:
		return
	var anim_center: Dictionary = {}
	for lib_name: StringName in player.get_animation_library_list():
		var lib: AnimationLibrary = player.get_animation_library(lib_name)
		if lib == null:
			continue
		for anim_name: StringName in lib.get_animation_list():
			var anim: Animation = lib.get_animation(anim_name)
			if anim == null:
				continue
			var center: Vector2 = _torso_track_center(anim)
			if center.x > -1e8:
				anim_center[anim_name] = center
	for state: StringName in STATE_ANIM_GROUPS:
		var sum := Vector2.ZERO
		var n := 0
		for anim_name: StringName in STATE_ANIM_GROUPS[state]:
			if anim_center.has(anim_name):
				sum += anim_center[anim_name] as Vector2
				n += 1
		if n > 0:
			_state_center[state] = sum / float(n)


## 读一条动画里躯干位移轨道的中点。没有这条轨道就返回一个哨兵值（x 极小）。
func _torso_track_center(anim: Animation) -> Vector2:
	var track: int = anim.find_track(NodePath(TORSO_TRACK_PATH), Animation.TYPE_VALUE)
	if track < 0:
		return Vector2(-1e9, -1e9)
	var count: int = anim.track_get_key_count(track)
	if count <= 0:
		return Vector2(-1e9, -1e9)
	var lo := Vector2(1e9, 1e9)
	var hi := Vector2(-1e9, -1e9)
	for i: int in range(count):
		var v: Variant = anim.track_get_key_value(track, i)
		if v is Vector2:
			var p: Vector2 = v
			lo = Vector2(minf(lo.x, p.x), minf(lo.y, p.y))
			hi = Vector2(maxf(hi.x, p.x), maxf(hi.y, p.y))
	if lo.x > 1e8:
		return Vector2(-1e9, -1e9)
	return (lo + hi) * 0.5



## 当前这一帧的咬合强度（0=松口，1=咬到底）。
## [br]相位优先问动画树：「eat 状态里那条动画现在播到第几秒」。
## 这样连动画速度倍率（eat 内部 2 倍速、寒冰减速、时间尺度）都自动同步，不需要自己算。
## 问不到才退回自计时，自计时也按同一套速度倍率推进，不会和动画走散。
func _eat_amount(delta: float) -> float:
	if not _eat_active or is_death or is_show:
		return 0.0
	var t: float = _eat_clip_time()
	if t < 0.0:
		_eat_clock = fposmod(_eat_clock + delta * _eat_speed, EAT_LOOP)
		t = _eat_clock
	var amount: float = maxf(_bite_pulse(t, EAT_BITE_1), _bite_pulse(t, EAT_BITE_2))
	return amount


## 读啃食那条动画的播放头（单位是动画自己的时间轴，0~[constant EAT_LOOP]）。
## 读不到返回 -1，交给自计时兜底。
func _eat_clip_time() -> float:
	if not is_instance_valid(_eat_playback) or not is_instance_valid(_anim_tree):
		return -1.0
	if _eat_playback.get_current_node() != EAT_STATE_NAME:
		return -1.0
	_refresh_eat_speed()
	var raw: Variant = _anim_tree.get(EAT_POS_PATH)
	if raw is float:
		var t: float = fposmod(raw as float, EAT_LOOP)
		## 顺手把自计时对齐到播放头：万一下一帧读不到了，兜底也是从同一相位接着走，
		## 不会突然跳回上一次的旧值
		_eat_clock = t
		return t
	return -1.0


## 刷新啃食段动画的实际速度倍率。两层 TimeScale 相乘：
## 外层整棵树一层（默认 1.2），eat 状态内部再一层（默认 2.0）。
## [br]少了这一层换算，自计时就会比动画慢一倍半，咬合会掉在两次 Chomp 之间。
func _refresh_eat_speed() -> void:
	if not is_instance_valid(_anim_tree):
		return
	var top: Variant = _anim_tree.get(ANIM_TOP_SCALE_PATH)
	var inner: Variant = _anim_tree.get(ANIM_EAT_SCALE_PATH)
	var speed := 1.0
	if top is float:
		speed *= top as float
	if inner is float and (inner as float) > 0.01:
		speed *= inner as float
	_eat_speed = maxf(speed, 0.05)


## 单口咬合的脉冲：提前 [constant EAT_PULSE_RISE] 抬头前冲，到点咬合，
## 之后用 [constant EAT_PULSE_FALL] 松口退回。快咬慢松才像在嚼。
func _bite_pulse(t: float, bite_time: float) -> float:
	if t < bite_time - EAT_PULSE_RISE or t > bite_time + EAT_PULSE_FALL:
		return 0.0
	if t <= bite_time:
		return smoothstep(0.0, 1.0, (t - (bite_time - EAT_PULSE_RISE)) / EAT_PULSE_RISE)
	return 1.0 - smoothstep(0.0, 1.0, (t - bite_time) / EAT_PULSE_FALL)
#endregion


func character_death() -> void:
	super()
	if is_instance_valid(_cast_timer):
		_cast_timer.stop()
	_is_casting = false
	_eat_active = false
	_glow_off()


## 退出时松掉对动画树的引用。
## [br]`_eat_playback` 是 AnimationTree 内部的对象，脚本持有引用会让它在树拆除后
## 还多活一份，退出时报 "ObjectDB instances were leaked"。这里主动放手。
func _exit_tree() -> void:
	_eat_playback = null
	_anim_tree = null
