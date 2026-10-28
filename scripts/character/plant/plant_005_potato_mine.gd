extends Plant000Base
class_name Plant005PotatoMine

## 裴无咎 · 埋锋将军（土豆地雷）新形象 + 3×3 索敌／爆炸 + 一击斩。
##
## 表演四拍，全部由原有逻辑驱动，不新增状态机：
##   sit    准备期（prepare_time 内）—— 盘膝坐地、闭目养神
##   rise   准备结束（is_prepare_end 置 true）—— 撑地起身，AnimationTree 同时走 PotatoMine_rise
##   crouch 起身完毕（_rise_end 调用）—— 单膝蹲伏、刀在鞘，索敌开启
##   stab   索敌命中 —— 不跃起、不追砍，而是压刀入土；刀锋触地的同一帧结算爆炸，
##          剑气从地面裂口向四周炸开（表现见 plant_005_sword_qi.gd），0.34 秒后消失
##
## 一次性：原来 signal_can_attack 分别直连 bomb_once 与 character_death，
## 两件事落在同一帧、没有插刀的余地。这里改成只连 _on_detect_enemy，
## 由它按「压刀入土 → 爆炸 → 消失」自己排时间轴；bomb_once 内部有 is_bomb 兜底，
## 被啃死走 death_language 也不会重复爆炸。

@onready var detect_component: DetectComponent = $DetectComponent
@onready var bomb_component: BombComponentBase = $BombComponent
@onready var prepare_timer: SpeedTimer = $PrepareTimer

## 准备时间
@export var prepare_time := 10.0

@export_group("动画状态")
@export var is_prepare_end := false

#region 新形象开关与常量
## true  = 用一整张 Q 版少年将军立绘替换原版散件（散件一个都没删，只是被隐藏）
## false = 恢复原版土豆地雷
@export var general_enable: bool = true

const ART_SIT: String = "res://assets/image/character/potato_mine/potato_mine_sit.png"
const ART_CROUCH: String = "res://assets/image/character/potato_mine/potato_mine_crouch.png"
## 出手姿态：双手叠按刀柄、唐刀竖直插进地里
const ART_STAB: String = "res://assets/image/character/potato_mine/potato_mine_stab.png"

## 三张图同出一张 1024 画布，落地线几乎重合（227.1/240），所以整张保留、不各自裁边，
## 姿态之间的相对位置才会天然对齐。
## 显示身高按本工程自建立绘的统一口径「目标高度 ÷ 源图高度」来定（豌豆 103、樱桃 116、坚果 164）。
## 0.70 是在 120 的基础上缩到 70% —— 注意 84 会明显矮于豌豆，介意的只调这一个数。
const ART_TARGET_HEIGHT: float = 84.0
const ART_CANVAS_PX: float = 240.0
## 贴图边长（三张同尺寸）。换贴图尺寸时这里要跟着改，否则脚底会飘
const ART_TEX_PX: float = 240.0
const ART_DISPLAY_SCALE: float = ART_TARGET_HEIGHT / ART_TEX_PX
## 画布里的落地线比例 = 969/1024；换贴图尺寸时这里要跟着改，否则会浮空或陷进草皮
const ART_GROUND_RATIO: float = 0.9463
## 脚底在 Body 局部坐标的落点，由原版 rock1~rock6 的最低点反算：
## BodyCorrect.position.y(-56) + 0.8 × 落地线(78.7) = 6.96。
## ⚠️ 实机若发现整体偏高／偏低，只调这一个数。
const ART_FOOT: Vector2 = Vector2(0.0, 7.0)

## 八卦镜在各姿态立绘上的位置与半径（画布像素）。
## [br]由三张立绘的青色盘面做连通域圆拟合实测（盘心 / 半径）：
## sit (127,136) r14 / crouch (122,132) r15.5 / stab (119,139) r7（被双手压住只剩一角）。
## [br]三张图构图不同，位置必须逐姿态配；跪地时手压在盘上，镜光淡出，
## 否则会在手背上发光 —— 这是上一版「不贴合」的主因。
const MIRROR_BY_POSE: Dictionary = {
	# 姿态：  镜心（画布像素）           半径   是否被手遮挡
	"sit":    {"pos": Vector2(7.0, 16.0),  "radius": 14.0, "occluded": false},
	"crouch": {"pos": Vector2(2.0, 12.0),  "radius": 15.5, "occluded": false},
	"stab":   {"pos": Vector2(-1.0, 19.0), "radius": 13.0, "occluded": true},
}
## 用 preload 拿脚本而不是靠 class_name：避免「解析期类还没注册」的加载顺序问题
const MIRROR_SCRIPT: GDScript = preload("res://scripts/fx/plant_effect/plant_005_bagua_mirror.gd")

## 图鉴详情页取景：**角色根节点**在 200×200 窗口里的落点。
## [br]为什么不能照抄通用植物的 (100,120)：其它植物是满高度原图，立绘几乎撑满贴图；
## 埋锋将军的 240 贴图缩到 0.35 后**不透明像素只有约 79px 高**（贴图上下各有一圈透明边），
## 人比通用位置矮一大截，直接放 (100,120) 会整块浮在窗口上半部。
## [br]为什么不能拍脑袋往下压：`CharacterBg` 开了 clip_children，越界直接裁掉。
## 实测（拿 texture.get_used_rect() 走完整变换链量出来的）：
##   position.y = 120 → 内容占窗口 y 91.6~170.5（下方空 29.5px，偏上）
##   position.y = 140 → 内容占窗口 y 111.6~190.6（下方空 9.4px）
##   position.y = 150 → 内容占窗口 y 121.6~200.6（**下沿溢出 0.6px，已经切到脚**）
## 所以安全上限就是 140 左右。取 140 让脚底离底边 9px，视觉上「站到画面底、又没被切」。
## ⚠️ 改立绘尺寸或 ART_CANVAS_PX / ART_DISPLAY_SCALE 时必须重算，不能沿用这个数。
const ALMANAC_SHOW_POS: Vector2 = Vector2(100.0, 140.0)

## 脚下阴影：⚠️ 这个属性**不归脚本管**，不要在这里写。
## [br]`Shadow` 的 scale 由 AnimationTree 逐帧驱动，脚本里写多少都会被立刻顶回去：
##   PotatoMine_light（坐姿养神 / 准备期） → 1.40, 1.02
##   PotatoMine_rise                      → 1.40, 1.02 收到 0.90, 0.7639
##   PotatoMine_armed（单膝跪地 / 索敌）  → 0.90, 0.7639
## 原版这两档是 0.90 与 1.51（差 1.68 倍），换成立绘后坐姿红袍盘开约 71px 宽，
## 0.90 那张阴影会被整个压在身下「看不见影子」；跪姿只有约 40px 宽，1.51 那张
## 就左右各露 24px「一大泡」。现在两档都按「脚下留约 6px 软边」重算，
## 坐姿约 83px、跪姿约 53px。改宽度只能去 animation/character/plant/005_potato_mine/ 里改关键帧。

## 待机：坐姿养神要慢而轻，蹲伏蓄势要快而明显
const IDLE_SIT_PERIOD: float = 2.6
const IDLE_SIT_SWAY_DEG: float = 0.5
const IDLE_SIT_BREATH: float = 0.008
const IDLE_CROUCH_PERIOD: float = 1.5
const IDLE_CROUCH_SWAY_DEG: float = 1.0
const IDLE_CROUCH_BREATH: float = 0.014

## 起身：撑地那一下的顿挫
const RISE_POP_TIME: float = 0.22
## 压刀入土：整个人往下一沉 → 刀锋触地 → 剑气炸开 → 停留
const STAB_DRIVE_TIME: float = 0.15
const STAB_DROP_PX: float = 5.0
const STAB_SQUASH: float = 0.97
const STAB_HOLD_TIME: float = 0.34
#endregion

## 立绘与它的两层支点：
## Body → MineIdlePivot（脚底，管微摆与呼吸）→ MineArtPivot（管拔刀前冲）→ 立绘。
## 挂 Body 而不是 BodyCorrect：BodyCorrect 被 AnimationTree 盯着，状态机切状态时会把
## 它的子节点重置成 visible=false，挂进去的立绘会被一起吃掉。
var _art: Sprite2D = null
var _idle_pivot: Node2D = null
var _art_pivot: Node2D = null
## 胸前的八卦镜（程序化，感应场上僵尸）
var _mirror: Node2D = null
## 姿态名 → 贴图；三张同尺寸，换姿态只换 texture，位置缩放都不用重算
var _poses: Dictionary = {}
## 当前该用哪一档姿态。show／garden 初始化不进 ready_norm，默认就是蹲伏
var _pose_name: String = "crouch"
var _idle_tween: Tween = null
## 已经挥刀，防止重复触发
var _is_attacking: bool = false


## 初始化正常出战角色
func ready_norm():
	super()
	## 准备期坐地养神；立绘在 _ready 里才真正建出来，这里只记下要哪一档
	_pose_name = "sit"
	## 土豆雷默认禁用攻击射线检测组件
	detect_component.disable_component(ComponentNormBase.E_IsEnableFactor.Prepare)
	## 默认禁用眨眼组件
	blink_component.disable_component(ComponentNormBase.E_IsEnableFactor.Prepare)

	# 已有速度因素先同步；在零速下种植也能保留完整准备任务。
	update_prepare_speed(GlobalUtils.get_dic_product(influence_speed_factors))
	prepare_timer.start_scaled(prepare_time)

	if is_zombie_mode:
		prepare_timer.stop()
		_on_prepare_timer_timeout()

func ready_norm_signal_connect():
	super()
	## 准备完成后才会检测到敌人；命中后由 _on_detect_enemy 统一排「挥刀→爆炸→消失」
	detect_component.signal_can_attack.connect(_on_detect_enemy)

	## 角色速度改变
	signal_update_speed.connect(update_prepare_speed)

## 亡语：先让镜光退场，再按原逻辑引爆。
## [br]⚠️ 这里刻意不写 super()：父类 Plant000Base.death_language 是空实现，
## 真正在引爆的是 judge_death_bomb，写漏了被啃死就不会炸。
func death_language():
	if is_instance_valid(_mirror):
		_mirror.set_process(false)
		_mirror.queue_free()
		_mirror = null
	bomb_component.judge_death_bomb()

## 土豆类出土动画结束调用
func _rise_end():
	detect_component.enable_component(ComponentNormBase.E_IsEnableFactor.Prepare)
	blink_component.enable_component(ComponentNormBase.E_IsEnableFactor.Prepare)
	bomb_component.is_auto_bomb_in_death = true

## 准备时间结束：置状态位给 AnimationTree（light → rise），同时把立绘换到蹲伏
func _on_prepare_timer_timeout() -> void:
	is_prepare_end = true
	_play_rise()

## 重新设置准备时间
func set_prepare_time(new_prepare_time:float):
	prepare_time = new_prepare_time
	prepare_timer.start_scaled(prepare_time)

## 改变准备倍率时保留进度，不重复缩放剩余时间。
func update_prepare_speed(speed_factor:float):
	prepare_timer.set_speed_scale(speed_factor)


#region 换装
## 换装入口只挂在 `_ready` 上：`character_000_base._ready()` 会按 character_init_type
## 分派 ready_norm／ready_show／ready_garden，在分派之后统一换装，图鉴详情页也不会漏。
func _ready() -> void:
	super()
	if general_enable:
		_apply_general_art()


## 隐藏散件版身体，换成整图立绘；不改 .tscn 结构，回退只需把 general_enable 置 false。
func _apply_general_art() -> void:
	# 幂等：初始化路径已收口到 _ready，换装仍可能被外部重入
	if is_instance_valid(_art):
		return
	var body_node: Node2D = get_node_or_null("Body") as Node2D
	var body_correct: Node2D = get_node_or_null("Body/BodyCorrect") as Node2D
	if body_node == null or body_correct == null:
		push_warning("埋锋将军：找不到 Body / BodyCorrect，跳过换装")
		return

	for key: String in ["sit", "crouch", "stab"]:
		var path: String = {"sit": ART_SIT, "crouch": ART_CROUCH, "stab": ART_STAB}[key]
		var tex: Texture2D = load(path) as Texture2D
		if tex == null:
			push_warning("埋锋将军：贴图没找到或还没被导入 → %s" % path)
			return
		_poses[key] = tex

	# 1) 原散件整体隐藏（rock1~rock6 + stem + blink + 眼嘴）
	body_correct.visible = false

	# 2) 两层支点都落在脚底：呼吸／摆动都是绕脚底变形，
	#    支点在头顶会变成「往地里沉 + 被吊着晃」
	_idle_pivot = Node2D.new()
	_idle_pivot.name = "MineIdlePivot"
	_idle_pivot.position = ART_FOOT
	body_node.add_child(_idle_pivot)

	_art_pivot = Node2D.new()
	_art_pivot.name = "MineArtPivot"
	_idle_pivot.add_child(_art_pivot)

	# 3) 立绘：居中贴图，按落地线比例上移，让画布落地线正好落在支点上
	var tex_main: Texture2D = _poses[_pose_name]
	var px_h: float = float(tex_main.get_height())
	var art_scale: float = ART_CANVAS_PX * ART_DISPLAY_SCALE / px_h
	var display_h: float = px_h * art_scale
	_art = Sprite2D.new()
	_art.name = "MineArt"
	_art.texture = tex_main
	_art.scale = Vector2(art_scale, art_scale)
	_art.position = Vector2(0.0, -(ART_GROUND_RATIO - 0.5) * display_h)
	_art_pivot.add_child(_art)

	_attach_bagua_mirror()

	_play_idle_for(_pose_name)


## 八卦镜：贴图做不到「越近闪得越快」，只能挂一个程序化节点在镜面位置上。
## [br]挂在立绘本体（不是 pivot）下，换姿态时位置跟着同一张画布走。
## [br]父节点（立绘 Sprite2D）的 scale 就是 art_scale，所以这里写的是**画布像素**。
func _attach_bagua_mirror() -> void:
	if not is_instance_valid(_art) or is_instance_valid(_mirror):
		return
	var mirror: Node2D = MIRROR_SCRIPT.new() as Node2D
	if mirror == null:
		push_warning("埋锋将军：八卦镜脚本加载失败，跳过镜光")
		return
	mirror.name = "BaguaMirror"
	# 节点放在立绘原点，偏移交给 mirror_pos —— 只让一处写 position
	mirror.position = Vector2.ZERO
	_art.add_child(mirror)
	_mirror = mirror
	_sync_mirror_to_pose(_pose_name)


## 按姿态把镜心、半径、遮挡状态同步到镜光节点上。
## [br]三张立绘构图不同，镜盘位置不一样，必须逐姿态配；
## 跪地时双手压在镜面上，镜光淡出，否则会在手背上发光。
func _sync_mirror_to_pose(pose: String) -> void:
	if not is_instance_valid(_mirror):
		return
	var cfg: Dictionary = MIRROR_BY_POSE.get(pose, MIRROR_BY_POSE["crouch"])
	_mirror.mirror_pos = cfg["pos"]
	_mirror.mirror_radius = cfg["radius"]
	_mirror.set_occluded(cfg["occluded"])


## 换姿态。三张图同画布同尺寸，只换 texture；镜光位置跟着姿态重配。
## [br]⚠️ 阴影不在这里改：`Shadow:scale` 由 AnimationTree 按状态驱动，见 SHADOW 说明。
func _set_pose(pose: String) -> void:
	_pose_name = pose
	if not is_instance_valid(_art) or not _poses.has(pose):
		return
	_art.texture = _poses[pose]
	_sync_mirror_to_pose(pose)


## 按姿态起对应的待机呼吸
func _play_idle_for(pose: String) -> void:
	if pose == "sit":
		_play_idle(IDLE_SIT_PERIOD, IDLE_SIT_SWAY_DEG, IDLE_SIT_BREATH)
	else:
		_play_idle(IDLE_CROUCH_PERIOD, IDLE_CROUCH_SWAY_DEG, IDLE_CROUCH_BREATH)


## 待机：绕脚底左右轻摆 + 呼吸起伏，用单一相位 v∈[0,1] 同时驱动两个属性。
## [br]为什么不用两条 Tween 分别写 rotation / scale：出手的 _set_stab_drive 也要写 scale，
## 两条 Tween 抢同一个属性会互相顶；收成一条相位 Tween 后，出手前 kill 一次就干净了。
## sin(2πv) 与 cos 在 v=0 和 v=1 处的值和导数都相同，循环接缝看不出来。
func _play_idle(period: float, sway_deg: float, breath: float) -> void:
	if not is_instance_valid(_idle_pivot) or not is_instance_valid(_art_pivot):
		return
	if is_instance_valid(_idle_tween):
		_idle_tween.kill()
	_set_idle_phase(0.0, sway_deg, breath)
	_idle_tween = create_tween().set_loops()
	_idle_tween.tween_method(_set_idle_phase.bind(sway_deg, breath), 0.0, 1.0, period)


## [param v] 相位 0→1；[param sway_deg] 左右摆角；[param breath] 纵向呼吸比例
func _set_idle_phase(v: float, sway_deg: float, breath: float) -> void:
	if not is_instance_valid(_idle_pivot) or not is_instance_valid(_art_pivot):
		return
	_idle_pivot.rotation = deg_to_rad(sway_deg * sin(TAU * v))
	var b: float = 0.5 - 0.5 * cos(TAU * v)
	_art_pivot.scale = Vector2(1.0, 1.0 + breath * b)


## 起身：坐 → 蹲，压扁一下再弹起来，读作「撑地起身」
func _play_rise() -> void:
	_set_pose("crouch")
	if not is_instance_valid(_art_pivot):
		return
	if is_instance_valid(_idle_tween):
		_idle_tween.kill()
	_idle_pivot.rotation = 0.0
	_art_pivot.scale = Vector2(1.06, 0.92)
	_art_pivot.position = Vector2(0.0, 4.0)
	var pop: Tween = create_tween().set_parallel(true)
	pop.tween_property(_art_pivot, ^"scale", Vector2.ONE, RISE_POP_TIME) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	pop.tween_property(_art_pivot, ^"position", Vector2.ZERO, RISE_POP_TIME) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	## 弹完再起待机，否则待机的 scale 会被这一记回弹顶回去
	pop.chain().tween_callback(func() -> void: _play_idle_for("crouch"))
#endregion


#region 压刀入土
## 索敌命中：压刀入土 → 触地结算 → 剑气炸开 → 消失，全程只走一次
func _on_detect_enemy() -> void:
	if _is_attacking or is_death:
		return
	_is_attacking = true
	## 关掉索敌，避免出手期间又报一次
	detect_component.disable_component(ComponentNormBase.E_IsEnableFactor.Character)
	_set_pose("stab")
	if is_instance_valid(_idle_tween):
		_idle_tween.kill()
	if is_instance_valid(_idle_pivot):
		_idle_pivot.rotation = 0.0

	var timeline: Tween = create_tween()
	timeline.tween_method(_set_stab_drive, 0.0, 1.0, STAB_DRIVE_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	timeline.tween_callback(_bomb_now)
	timeline.tween_interval(STAB_HOLD_TIME)
	timeline.tween_callback(_finish_attack)


## 入土行程：整个人往下一沉 + 纵向压扁，读作「把刀按进土里」。
## 不做旋转与位移 —— 立绘里的刀是竖直插地的，一转就歪了。
func _set_stab_drive(value: float) -> void:
	if not is_instance_valid(_art_pivot):
		return
	_art_pivot.position.y = STAB_DROP_PX * value
	_art_pivot.scale = Vector2(
		1.0 + 0.02 * value,
		1.0 - (1.0 - STAB_SQUASH) * value)


## 触地：结算 3×3 爆炸（伤害与剑气同一帧起），立绘再压住 0.1 秒才淡出。
## 为什么不当场淡出：刀插在土里、剑气正从刀尖炸开，这 0.1 秒才是整招最好看的一帧，
## 立绘先没掉就只剩一团光，看不出「是这一刀劈出来的」。
func _bomb_now() -> void:
	if is_death:
		return
	bomb_component.bomb_once()
	# 镜光也要跟着一起退场，否则立绘淡没了、胸口还飘着一个亮点
	if is_instance_valid(_mirror):
		_mirror.set_process(false)
		_mirror.queue_free()
		_mirror = null
	if is_instance_valid(_art):
		var fade: Tween = create_tween()
		fade.tween_interval(STAB_HOLD_TIME * 0.30)
		fade.tween_property(_art, ^"modulate:a", 0.0, STAB_HOLD_TIME * 0.70)


## 收尾：土豆地雷一次性，爆炸后本体消失
func _finish_attack() -> void:
	if is_death or not is_inside_tree():
		return
	character_death()
#endregion
