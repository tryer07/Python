extends Zombie001Norm
class_name Zombie026Magician

## 魔术师僵尸（Z026）—— 「平图换皮」的模版
##
## ⚠️⚠️ 2026-10-30 第七次返工，先说清楚**为什么不能走原版骨架这条路**（这是用户提的方向，
## 我实机查过之后否掉了，理由记在这儿，免得下次再试一遍）：
##
## 原版僵尸的「换皮」= 每个 reanim 散件换一张图，散件是**沿关节裁开的小块**
## （`Zombie_head.png` 53×48、`Zombie_body.png` 53×63、`Zombie_innerleg_upper.png` …），
## 所以每个 Sprite2D 自己转都不会露底。而魔术师只有**一张平涂立绘**，手臂压在衣服上、
## 腿压在披风下 —— 按关节拆开必然出现「被压住的那部分没人画」的空洞。
## 更要命的是原版骨架的**枢轴位置全是错的**：这工程里 reanim 散件的旋转枢轴 = Sprite2D 的
## 左上角（`centered = false` + `position` 就是枢轴），`Zombie_body` 的枢轴在肩膀、
## `Anim_head1` 的枢轴在头顶左角。**拿这套枢轴去转一张 132px 高的整立绘，
## 头会像挂在钩子上甩，身子会像绕着脖子摆** —— 这就是上一版「走路像纸片」的根因。
##
## 所以现在的结构是：**一块刚体 + 一个自己定的关节**。
##   · 七块部件全部挂在同一根骨头 [`constant PART_BONE`] 上 ⇒ 彼此相对变换恒定，
##     **任何姿势下拼缝都不可能存在**（这是上一版好不容易换来的，不能丢）；
##   · 只有头和帽子再叠一个「绕脖子转」——枢轴用**立绘像素坐标**自己写死
##     （[constant PART_DEFS] 第 6、7 列），跟原版骨架无关；
##   · 走路 = 原版躯干动画（本来就在动）+ 整体上下起伏 / 左右摇 + 点头；
##     啃食 = 一口一下点头。这两件事是这套美术**唯一能安全表达**的动作。
##
## 为什么只有头能动、手臂和腿都坚决不动：
## 平图里手臂下面压着衬衫和外套，手臂只要相对躯干转，就会①带走一块衣服②原位留一道手臂影子。
## 腿同理 —— 前后腿互相遮挡，**被挡住的那条腿在图上根本没有像素**，分开转就是重影 + 空洞。
## 头是唯一「底下压着一块同色同纹理的躯干」的部件，转开的地方露出来的正好是它自己，
## 所以点头零穿帮。
##
## 机制（2026-10-27 按路障僵尸对齐，数值结构不变）：
##   * 本体 [constant MAGICIAN_MAX_HP] = 270，死亡临界值走路障那套（2/3-1、1/3-1）
##   * 魔术帽 = 二类防具 370，总血 640，和路障一枪不差
##   * 每 [member attack_interval] 秒远程打一发，单发 [member attack_damage]
##   * 贴脸照常啃食（沿用 AttackComponentZombieNorm）。**啃食和施法互斥**：
##     咬上去那一刻起，正在进行的施法立刻中断、法杖熄灯、姿态掰回站姿；
##     啃食期间计时器到点也不开新的施法。见 [method _is_bite_busy] / [method _abort_cast]。

#region 立绘常量
## 脚底在贴图像素坐标中的位置（贴图 674×1312，最底部一行已全透明）
const ART_FOOT_PIXEL := Vector2(428.0, 1298.0)
## 贴图里人物的实体像素高度（alpha 包围盒高 1284）
const ART_BODY_PIXEL_H := 1284.0
## 战场立绘高度（按贴图里人物的实体像素高换算，不含透明边）。
## 实测「不透明像素高」：普通僵尸 121、路障僵尸 138。
## 132 比普僵高 9%（看着是个「有点分量的施法者」），又没到路障那头锥形帽的高度。
const ART_TARGET_HEIGHT := 132.0
## 展示态（选卡界面、图鉴详情）的立绘高度，必须和普通僵尸齐平（121）
const ART_SHOW_HEIGHT := 121.0
## 杖尖白球在贴图像素坐标中的位置（左手手杖最前端那颗球，实测圆心 41.5,1097.5）
const ART_WAND_PIXEL := Vector2(41.5, 1097.5)

## 脖子枢轴（立绘像素）。取在下巴底下、领结上沿 —— 头转起来下缘一直压在这块上面，
## 而这块底下的躯干是同色同纹理的，所以**头怎么点都不会露洞**。
const JOINT_NECK := Vector2(238.0, 604.0)

## ⚠️ 腿**没有**关节，别再加。2026-10-30 试过、实机出图否掉了：
## 这张图是平涂的，**被前面那条腿挡住的后面那条腿根本不存在像素**。
## 前后腿各切一块矩形，只要两者相对转一点，就会同时出现
## ①两只鞋各转各的（同一只鞋在两张切片里都有，变成重影）
## ②前腿让开的地方是空洞，直接透到草坪。
## 想分开只能重新画腿，代价远大于收益（132px 高的时候腿本来就只露 20 来像素）。
## 所以走路的手感全部交给「原版躯干动画 + 整体起伏 + 点头」这三层，腿跟着整体走。

## 躯干 / 外套 / 披风 / 领结 / 衬衫
const TEX_TORSO: Texture2D = preload("res://assets/image/character/zombie_magician/magician_p_torso.png")
## 画面右侧那条臂（远的，藏在披风前）
const TEX_ARM_FAR: Texture2D = preload("res://assets/image/character/zombie_magician/magician_p_arm_far.png")
## 头（脸、下巴、舌、头发）＋**重画出来的头顶**。
## [br]⚠️ 素材里的「无帽版」其实不是秃头：被帽子压住的那一块是一块颜色和皮肤相同、
## 却没有体积也没有纹理的**帽檐形状平涂**（源头是把帽冠切走了、帽檐留在了身体层上）。
## 帽子一飞走，露出来的就是这块东西 —— 玩家看到的就是「半个头」。
## [br]所以这块贴图不是直接裁的：裁出 (27,140)-(445,642) 之后，把额线（原图 y=312）以上
## 整片抹掉，按额线处的头宽补一颗扁圆的头顶上去（顶点高出额线 112px）。
## 画法照抄这套美术的风格：**平涂 + 硬描边**，颜色逐列取额线下方肤色像素的中位数
## 再横向平滑，所以跟脸没有色阶断层。
const TEX_HEAD: Texture2D = preload("res://assets/image/character/zombie_magician/magician_p_head.png")
## 魔术帽。节点名必须是 MagicianHat —— 场景里的 `sprite_disappear` 按名字引用了它
const TEX_HAT: Texture2D = preload("res://assets/image/character/zombie_magician/magician_p_hat.png")
## 画面左侧那条臂 + 手杖
const TEX_ARM_NEAR: Texture2D = preload("res://assets/image/character/zombie_magician/magician_p_arm_near.png")
## 近腿：蓝裤 + 整只大棕皮鞋（前景）。画在外套后面
const TEX_LEG_NEAR: Texture2D = preload("res://assets/image/character/zombie_magician/magician_p_leg_near.png")
## 远腿：细骨腿 + 蓝破裤脚（鞋被前景挡住）
const TEX_LEG_FAR: Texture2D = preload("res://assets/image/character/zombie_magician/magician_p_leg_far.png")

## 七块部件**统一挂到这一根骨头**上，当刚体。见上面「为什么不能走原版骨架」。
const PART_BONE := "Body/BodyCorrect/Zombie_body"

## 部件表：[节点名, 贴图, 像素包围盒左上角, 挂到哪根骨头, z_index, 关节枢轴(像素), 关节名]
## [br]关节名空串 = 刚体，永不单独转动；目前只有 `neck` 一个，见 `_joint_angle()`。
## [br]z_index：腿必须是负的（−2/−3）压在躯干下面 —— 这不只是好看，是腿能动的前提
## （腿块里带着外套像素，只有被外套盖住才不会露出来）。
const PART_DEFS := [
	["MagicianTorso", TEX_TORSO, Vector2(14, 493), PART_BONE, 0, Vector2.ZERO, ""],
	["MagicianArmFar", TEX_ARM_FAR, Vector2(340, 572), PART_BONE, 2, Vector2.ZERO, ""],
	["MagicianHead", TEX_HEAD, Vector2(27, 140), PART_BONE, 10, JOINT_NECK, "neck"],
	["MagicianHat", TEX_HAT, Vector2(21, 14), PART_BONE, 12, JOINT_NECK, "neck"],
	["MagicianArmNear", TEX_ARM_NEAR, Vector2(14, 566), PART_BONE, 20, Vector2.ZERO, ""],
	["MagicianLegNear", TEX_LEG_NEAR, Vector2(180, 1036), PART_BONE, -2, Vector2.ZERO, ""],
	["MagicianLegFar", TEX_LEG_FAR, Vector2(401, 986), PART_BONE, -3, Vector2.ZERO, ""],
]
#endregion

## 本体血量：**和普通僵尸、路障僵尸一模一样**（270）。
const MAGICIAN_MAX_HP := 270
## 魔术帽（二类防具）的耐久。取路障锥形路障的 370，总血量因此也是 640。
const MAGICIAN_HAT_HP := 370

@export_group("远程紫电")
## 两次施法的间隔（秒），从这次开始蓄力算到下次开始蓄力
@export var attack_interval: float = 10.0
## 单次紫电伤害
@export var attack_damage: int = 500
## 索敌最远距离（像素），超出这个距离就不放技能
@export var attack_range: float = 520.0
## 蓄力（挥杖）时长，到点放电
@export var charge_duration: float = 1.0
## 放电后的收势时长；和蓄力加起来就是整段施法 2 秒
@export var release_duration: float = 1.0

@export_group("施法姿态")
## 后仰角度（度），正数=上半身往后仰
@export var windup_degrees: float = 9.0
## 挥出角度（度），负数=往前压
@export var strike_degrees: float = -7.0

@export_group("走路")
## 头随步频点头的幅度（度）。这是「在走」最主要的那点信息
@export var head_bob_degrees: float = 3.2
## 整体上下起伏幅度（Body 空间的像素；战场立绘高 132，2.2 约等于 1.7%）
@export var shuffle_bob: float = 2.2
## 整体左右摇摆幅度（度）
@export var shuffle_rock_degrees: float = 1.4
## 步频（弧度/秒）。8.5 约等于每秒两步
@export var walk_speed: float = 8.5
## 起步/停步时动作量的渐变速度（越大越急）
@export var walk_ramp: float = 9.0

@export_group("啃食")
## 每一口的点头幅度（度）
@export var head_bite_degrees: float = 7.5
## 每一口整个人往前顶的距离（像素）。普僵啃食是「整条上半身往植物上撞」，
## 只点头看着像在打瞌睡，加上这一下才像在咬
@export var eat_thrust: float = 1.8
## 咬合节拍（弧度/秒）。9.0 约等于每秒 1.4 口，跟普通僵尸的啃食频接近
@export var eat_speed: float = 9.0

#region 运行时节点
## 施法姿态轴：**没有子节点**，只用来承载两条补间（绕脚底转，脚不离地）。
## 姿态每帧由 [method _sync_parts] 乘到七块部件上，不靠节点继承 ——
## 部件长在骨头下面，骨头在 BodyCorrect 里，中间塞不进一个"整体轴"。
var _cast_pivot: Node2D
## 杖尖空节点，紫电从这里出发。挂在僵尸根下单独跟随近臂，
## 这样光球不会被骨架那 0.8 / 0.094 两层缩放压扁
var _wand_tip: Node2D
## 杖尖蓄力光球
var _charge: MagicianCharge
## 帽子被打光后用来飞出去的那块（场景里挂好的节点）
var _hat_drop_body: Node2D
## 施法节拍器
var _cast_timer: Timer
## 部件实例：[{name, sprite, bone, bb, joint, pivot, ref_inv}]
var _parts: Array[Dictionary] = []
## 部件按名字索引，[method _part] 用
var _part_index: Dictionary = {}
## 帽子单独留引用（帽子血条空了就藏掉，飞出去的那顶由掉落节点接管）
var _hat: Sprite2D = null
## 身体节点（`Body`），算骨头相对它的变换用
var _body: Node2D = null
#endregion

## 是否正在施法（施法期间不再接新的施法）
var _is_casting := false
## 施法代号。每开一次施法 +1，`_cast_at` 里每一段 `await` 回来都要先核对它。
## [br]啃食打断施法时靠它让旧的那一段立刻失效 —— 否则松口之后它会接着往下跑，
## 把紫电补放出去，表现就是「明明在咬，头顶突然劈一道电」。
var _cast_token := 0
## 当前施法姿态补间。中断时必须掐掉，不然它还会把 pivot 转到前压位
var _cast_tween: Tween = null
## 当前立绘高度，切换展示/战场时平滑过渡
var _art_height := ART_TARGET_HEIGHT
## 可攻击的植物状态位，从检测组件读，读不到就用默认的「正常+低矮」
var _attackable_plant_status: int = 9
## 是否正在啃食。**每帧从攻击组件轮询**，不依赖信号（理由见 `_process`）
var _eat_active := false
## 蓄力光球的补间。放电/中断时要能立刻掐掉，否则它继续往 1.0 走，杖尖就一直亮着
var _glow_tween: Tween = null
## 走路相位（弧度）
var _walk_phase := 0.0
## 走路动作量 0..1（起步/停步渐变，硬切会「啪」地弹一下）
var _walk_amount := 0.0
## 啃食相位（弧度）
var _eat_phase := 0.0
## 啃食动作量 0..1
var _eat_amount := 0.0
## 当前这一帧的起伏量：竖直位移（Body 空间像素）与整体摇摆角（度）
var _shuffle_y := 0.0
var _shuffle_rock := 0.0
## 当前这一帧啃食往前顶的位移（Body 空间像素，负值=朝植物那边）
var _eat_forward := 0.0
## 上一帧的世界坐标 x，用来判断「这一帧到底有没有在走」
var _last_global_x := 0.0


func _ready() -> void:
	super()
	_apply_magician_art()
	## 帽子归零那一帧先把掉落节点对到头上（这条信号早于 body_change_armor2 的隐藏/激活）
	var hp_zombie := hp_component as HpComponentZombie
	if hp_zombie != null:
		hp_zombie.signal_armor2_death.connect(_sync_hat_drop)
	_apply_magician_stats()
	## 出生那一帧的世界坐标，不然第一帧会被算成「走了 300 像素」，动作突然蹦一下
	_last_global_x = global_position.x
	## 展示/花园状态不放技能，只有正常出战才开节拍器
	if character_init_type == E_CharacterInitType.IsNorm:
		_setup_cast_timer()


#region 换皮：把立绘切成散件挂到骨头上
## 原版散件只清 alpha，**不能设 visible**：Godot 的 visible 会连子节点一起藏，
## 而我们的部件正好长在这些骨头下面。
## [br]用 `self_modulate`（只影响自己）而不是 `modulate`（会连子节点一起乘）。
func _fade_norm_sprites(node: Node) -> void:
	if node is Sprite2D or node is AnimatedSprite2D:
		(node as CanvasItem).self_modulate = Color(1.0, 1.0, 1.0, 0.0)
	for child: Node in node.get_children():
		_fade_norm_sprites(child)


func _apply_magician_art() -> void:
	_body = get_node_or_null("Body") as Node2D
	if _body == null:
		return
	var body_correct := _body.get_node_or_null("BodyCorrect")
	if body_correct != null:
		_fade_norm_sprites(body_correct)

	## 施法姿态轴：只承载补间，没有任何子节点
	_cast_pivot = Node2D.new()
	_cast_pivot.name = "MagicianCastPivot"
	_body.add_child(_cast_pivot)

	_parts.clear()
	_part_index.clear()
	for def: Array in PART_DEFS:
		var part_name: String = def[0]
		var tex: Texture2D = def[1]
		var bb: Vector2 = def[2]
		var bone_path: String = def[3]
		var z: int = def[4]
		var pivot: Vector2 = def[5]
		var joint: String = def[6]
		var bone := get_node_or_null(bone_path) as Node2D
		if bone == null:
			push_warning("魔术师换皮：找不到骨头 %s（%s 这块拼不上）" % [bone_path, part_name])
			continue
		var sprite := Sprite2D.new()
		sprite.name = part_name
		sprite.texture = tex
		sprite.centered = false
		sprite.z_index = z
		bone.add_child(sprite)
		## 骨头相对 Body 的变换在**这一刻**取一次当基准。
		## 取当下而不是「静止姿势」是故意的：七块都是在同一帧取的，所以它们彼此之间
		## 一定拼得严丝合缝；之后各自跟着骨头动，动量的起点就是这张原画。
		var bone_xf: Transform2D = _body.global_transform.affine_inverse() * bone.global_transform
		var rec := {
			"name": part_name,
			"sprite": sprite,
			"bone": bone,
			"bb": bb,
			"joint": joint,
			"pivot": pivot,
			"ref_inv": bone_xf.affine_inverse(),
		}
		_parts.append(rec)
		_part_index[part_name] = rec
		if part_name == "MagicianHat":
			_hat = sprite

	_hat_drop_body = get_node_or_null("Body/NodeDrop/Node2D_HatDrop/Hat_Drop") as Node2D
	## 掉出去的帽子必须压在七块部件上面（部件 z 最高到 20）
	if is_instance_valid(_hat_drop_body):
		_hat_drop_body.z_index = 40

	_wand_tip = Node2D.new()
	_wand_tip.name = "MagicianWandTip"
	_wand_tip.z_index = 30
	add_child(_wand_tip)

	_charge = MagicianCharge.new()
	_charge.name = "MagicianCharge"
	_charge.max_radius = 10.0
	_charge.level = 0.0
	_charge.visible = false
	_wand_tip.add_child(_charge)

	## 展示态入树前 is_show 就已经是 true，所以出生时直接按对应高度定尺
	_art_height = ART_SHOW_HEIGHT if is_show else ART_TARGET_HEIGHT
	_sync_parts()
	_update_hat_layers()

	var detect_component := attack_component.detect_component
	if detect_component != null:
		_attackable_plant_status = detect_component.can_attack_plant_status


## 取一块部件的记录，没有就返回空字典
func _part(part_name: String) -> Dictionary:
	if _part_index.has(part_name):
		return _part_index[part_name] as Dictionary
	return {}


## 帽子血条空了就把头上那顶藏掉（飞出去的那顶由掉落节点自己落）。
## [br]头顶不用另外补：颅顶已经画在头部件里，帽子只是「压在它上面的一层」，
## 所以掉帽只是这一层没了 —— 这也是后面所有「防具掉落」僵尸的统一做法。
func _update_hat_layers() -> void:
	var hp_zombie := hp_component as HpComponentZombie
	var hat_gone: bool = hp_zombie != null and hp_zombie.curr_hp_armor2 <= 0
	if is_instance_valid(_hat):
		_hat.visible = not hat_gone
#endregion


#region 部件摆放（每帧）
## 关节角（弧度）。**这是整套动作唯一的口径**：目前只有脖子一个关节。
## 头以外一律为 0（刚体，不可能撕裂）。
func _joint_angle(joint: String) -> float:
	match joint:
		"neck":
			## 走路小幅点头 + 啃食一口一下往下砸；两件事可以同时发生
			return deg_to_rad(
				sin(_walk_phase * 2.0) * head_bob_degrees * _walk_amount
				- absf(sin(_eat_phase)) * head_bite_degrees * _eat_amount
			)
	return 0.0


## 一块部件「贴图像素 → Body 空间」的变换。
## [br]推导：部件自己的局部像素 `q` 在整立绘里是 `q + off`（off = 包围盒左上 − 脚底），
## 要它绕立绘里的枢轴 `p` 转 `a`，等价于 `p + R(a)·(q + off − p)`；
## 最后整体乘立绘缩放 `s`。Godot 的 `Transform2D(rot, scale, skew, pos)` 正好是
## 「先缩放后旋转」，所以只需把旋转量同时写进 rot 和「已经转过的原点」两处。
func _art_xf(off: Vector2, pivot: Vector2, angle: float, s: float) -> Transform2D:
	if is_zero_approx(angle):
		return Transform2D(0.0, Vector2(s, s), 0.0, off * s)
	var spin := Transform2D(angle, Vector2.ONE, 0.0, Vector2.ZERO)
	return Transform2D(angle, Vector2(s, s), 0.0, (pivot + spin * (off - pivot)) * s)


## 把「关节角 + 整体姿态」写到七块部件上。
## [br]整体姿态 = 施法补间（[_cast_pivot]）＋ 走路起伏（[_shuffle_y] / [_shuffle_rock]）。
## [br]为什么要手动乘：部件长在骨头下面、骨头在 BodyCorrect 里，
## 中间插不进一个「整体轴」节点（插了会打断动画的 NodePath 轨道）。
## 所以姿态只能这么合成：`部件局部 = 骨头变换⁻¹ × 姿态 × 骨头变换 × 静止值`，
## 等价于「先按骨头摆好，再整体绕脚底转一下」。
## [br]七块挂在同一根骨头上（见 [constant PART_DEFS]），所以这一步对七块是同一个变换，
## **整体怎么晃都不可能撕裂拼缝**。
func _sync_parts() -> void:
	if _parts.is_empty() or not is_instance_valid(_body):
		return
	var s: float = _art_height / ART_BODY_PIXEL_H
	var pose := Transform2D.IDENTITY
	if is_instance_valid(_cast_pivot):
		pose = Transform2D(
			_cast_pivot.rotation + deg_to_rad(_shuffle_rock),
			_cast_pivot.position + Vector2(_eat_forward, _shuffle_y)
		)
	var has_pose: bool = not pose.is_equal_approx(Transform2D.IDENTITY)
	var body_inv: Transform2D = _body.global_transform.affine_inverse()
	for rec: Dictionary in _parts:
		var off: Vector2 = (rec["bb"] as Vector2) - ART_FOOT_PIXEL
		var xf: Transform2D = _art_xf(
			off, rec["pivot"] as Vector2, _joint_angle(rec["joint"] as String), s
		)
		var local: Transform2D = (rec["ref_inv"] as Transform2D) * xf
		if has_pose:
			var bone: Node2D = rec["bone"]
			var bx: Transform2D = body_inv * bone.global_transform
			local = bx.affine_inverse() * pose * bx * local
		(rec["sprite"] as Sprite2D).transform = local


## 动作量的推进：走路 / 啃食各一条相位，都用「目标值 + 渐变」推，
## 所以起步、停步、开口、闭口都不会「啪」地跳。
## [br]「有没有在走」靠**世界坐标这一帧变了没有**判断：移动组件没有现成的布尔量，
## 而位移是最不容易和别的状态打架的信号（被冻住/被挡住时自然为 0）。
func _update_articulation(delta: float) -> void:
	var dx: float = global_position.x - _last_global_x
	_last_global_x = global_position.x
	var walking: bool = absf(dx) > 0.02 and not is_death and not is_show and is_inside_tree()

	_walk_amount = lerpf(_walk_amount, 1.0 if walking else 0.0, minf(1.0, delta * walk_ramp))
	if walking:
		_walk_phase = wrapf(_walk_phase + delta * walk_speed, 0.0, TAU)

	var eating: bool = _eat_active and not is_death
	_eat_amount = lerpf(_eat_amount, 1.0 if eating else 0.0, minf(1.0, delta * 12.0))
	if _eat_amount > 0.01:
		_eat_phase = wrapf(_eat_phase + delta * eat_speed, 0.0, TAU)
	else:
		_eat_phase = 0.0
	## 僵尸朝左，所以往前顶是 −x。和点头同相：先撞上去再收回来
	_eat_forward = -absf(sin(_eat_phase)) * eat_thrust * _eat_amount

	if walking:
		# 一步一个峰：-|sin| 让身体在两次落脚之间往下沉，比 ±sin 更像走路
		_shuffle_y = -absf(sin(_walk_phase)) * shuffle_bob
		# 摇摆是起伏的两倍频（左右各一次 = 一个完整步幅）
		_shuffle_rock = sin(_walk_phase * 2.0) * shuffle_rock_degrees
		return
	# 停下来的时候两个量一起衰减回 0，不能硬切
	var k: float = minf(1.0, delta * 9.0)
	_shuffle_y = lerpf(_shuffle_y, 0.0, k)
	_shuffle_rock = lerpf(_shuffle_rock, 0.0, k)


## 杖尖跟着近臂走。直接读那块部件的画布变换 ——
## 它已经包含了骨头动画、施法姿态、缩放，取一个点就是杖尖的世界坐标。
func _update_wand_tip() -> void:
	if not is_instance_valid(_wand_tip):
		return
	var rec := _part("MagicianArmNear")
	if rec.is_empty():
		return
	var sprite: Sprite2D = rec["sprite"]
	if not is_instance_valid(sprite):
		return
	_wand_tip.global_position = sprite.to_global(ART_WAND_PIXEL - (rec["bb"] as Vector2))
#endregion


#region 血量 / 防具
## 血量落地。**数值的唯一来源是场景文件**，这里只兜底 + 清掉整图立绘用不上的散件阶段。
## [br]⚠️ 三条不能碰的东西（都是上一版的病根）：
##   · 不要 `boundary_value_hp.assign([0])`：那是「打到 0 才死」。留空让它按 max_hp 自动填
##     2/3-1、1/3-1，才是路障僵尸的临界值（本体 270 → 打到 89 就倒）。
##   · 不要 `hp_component.set_death_hp(0)`：默认已经按 boundary_value_hp[-1] 设好了。
##   · 不要把本体血量写成 640：总血 640 由「本体 270 + 帽子 370」凑。
func _apply_magician_stats() -> void:
	if hp_component.max_hp != MAGICIAN_MAX_HP:
		hp_component.max_hp = MAGICIAN_MAX_HP
		hp_component.curr_hp = MAGICIAN_MAX_HP
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
		## 普僵那套「掉手 → 掉头」对这套散件没意义，两个阶段都留空。
		## [br]数组长度必须和 boundary_value_hp 对齐（自动填的是 2 档），
		## 少给一个会在 `judge_body_change` 里索引越界。
		hp_stage_change_component.body_change.assign([null, null])


## 帽子被彻底打掉之前的最后一次对表：
## 把「帽子此刻在屏幕上的变换」抄给掉落节点，帽子就从头上原地脱手飞出去。
## [br]时机：`signal_armor2_death` 是在 `curr_hp_armor2` 的 setter 里发的，
## 早于 `body_change_armor2` 的隐藏/激活，所以这里抄完它才真正飞。
func _sync_hat_drop() -> void:
	if not is_instance_valid(_hat_drop_body) or not is_instance_valid(_hat):
		return
	_hat_drop_body.z_index = 40
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
	## ⚠️ 嘴里正在咬就不施法。这是「啃食期间不挥杖」的第一道闸门，
	## 第二道在 `_process`（咬上去的中途打断已经开始的施法）。
	if _is_bite_busy():
		return
	if _find_target() == null:
		return
	_cast_at()


## 现在是不是在啃食。**两条来源都要看**：
##   · `_eat_active` 是 `_process` 每帧轮询出来的结果（最可靠）；
##   · `attack_component.is_attack_res` 是同一份判定的原始出处，
##     这里再兜一道，免得「刚咬上去、`_process` 还没跑到」的那一帧漏过去。
func _is_bite_busy() -> bool:
	if _eat_active:
		return true
	if is_instance_valid(attack_component):
		return attack_component.is_attack_res
	return false


## 整段施法：停下 → 挥杖蓄力 → 放电 → 收势 → 继续走
func _cast_at() -> void:
	_is_casting = true
	_cast_token += 1
	var token: int = _cast_token
	move_component.update_move_factor(true, MoveComponent.E_MoveFactor.IsAnimGap)
	_play_windup()

	await _await_seconds(charge_duration)
	if token != _cast_token or not _can_continue_cast():
		return

	_fire()
	_play_strike()

	await _await_seconds(release_duration)
	if token != _cast_token or not _can_continue_cast():
		return
	_end_cast()


## 中断施法（啃食抢占）。四件事缺一不可：
##   ① 作废旧协程 ② 熄灭法杖 ③ 掐掉姿态补间并把姿态掰回站姿 ④ 放开移动锁
func _abort_cast() -> void:
	_cast_token += 1
	_is_casting = false
	_glow_off()
	if is_instance_valid(_cast_tween):
		_cast_tween.kill()
		_cast_tween = null
	if is_instance_valid(_cast_pivot):
		_cast_pivot.rotation = 0.0
		_cast_pivot.position = Vector2.ZERO
	if is_death:
		return
	move_component.update_move_factor(false, MoveComponent.E_MoveFactor.IsAnimGap)


func _can_continue_cast() -> bool:
	return not is_death and is_inside_tree()


func _end_cast() -> void:
	_is_casting = false
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
	if is_instance_valid(_cast_tween):
		_cast_tween.kill()
	_cast_tween = wind

	_glow_to(1.0, charge_duration)


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
	if is_instance_valid(_cast_tween):
		_cast_tween.kill()
	_cast_tween = strike


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


## 放电 + 结算伤害。
## [br]⚠️ **目标在结算这一刻才确定**，不在蓄力开始时锁定。
## 从开始蓄力到伤害真正落地有 [member charge_duration] 秒（默认 1 秒），这期间玩家完全
## 可能在最前面补种一株 —— 规则既然是「打最前面的那一株」，那就该打在那株新的身上。
## [br]结算时找不到目标就只放电、不结算伤害（视觉上是一道打空的电）。
func _fire() -> void:
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


## 紫电命中点：植物原点在脚下，往上抬一点打到身上
func _plant_hit_global(plant: Plant000Base) -> Vector2:
	return plant.global_position + Vector2(0.0, -40.0)
#endregion


#region 索敌
## 找同一行里、在自己前面、射程内、位置最靠右（离自己最近）的植物
func _find_target() -> Plant000Base:
	if lane < 0:
		return null
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
		if distance_x <= 0.0 or distance_x > attack_range:
			continue
		return plant
	return null
#endregion


#region 每帧
## 动作全部交给 [_update_articulation] + [_sync_parts]，这里只管：
##   ① 轮询「有没有在啃」并给施法让路  ② 帽子显隐  ③ 杖尖跟随  ④ 立绘高度过渡
func _process(delta: float) -> void:
	if _parts.is_empty():
		return

	## 啃食状态**每帧轮询**攻击组件的判定结果，不连信号。
	## [br]⚠️ 旧版连的是 `signal_change_is_attack`，但那条信号只在「能否攻击」发生**翻转**时发一次；
	## 僵尸要是出生就贴着植物、或者信号在 `_ready` 之前就已经发过，连接完成后就再也收不到 ——
	## 表现就是「明明在啃，咬合动作一次都不出现」。轮询 `is_attack_res` 没有这个时序问题。
	var eat_now: bool = not is_show and not is_death
	if eat_now and is_instance_valid(attack_component):
		eat_now = attack_component.is_attack_res
	_eat_active = eat_now

	## 啃食优先，施法让路：一旦咬上去就中断正在进行的施法。
	## [br]⚠️ 只中断、不接管 —— 松口之后也不会自动接着放，下一发重新走计时器。
	if _eat_active and _is_casting:
		_abort_cast()

	_update_hat_layers()

	## 展示态和战场的立绘高度不一样，切换时（选卡 → 上场）平滑过渡，不要「啪」地跳一下
	var target_height: float = ART_SHOW_HEIGHT if is_show else ART_TARGET_HEIGHT
	if not is_equal_approx(_art_height, target_height):
		_art_height = lerpf(_art_height, target_height, minf(1.0, delta * 8.0))
		if absf(_art_height - target_height) < 0.05:
			_art_height = target_height

	_update_articulation(delta)
	_sync_parts()
	_update_wand_tip()
#endregion


func character_death() -> void:
	super()
	if is_instance_valid(_cast_timer):
		_cast_timer.stop()
	_is_casting = false
	_eat_active = false
	_glow_off()
