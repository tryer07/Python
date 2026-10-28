extends Plant000Base
class_name Plant002SunFlower

## ── 朝阳童子（向日葵）新形象开关 ─────────────────────────────────────────
## true  = 用一整张 Q 版打坐立绘替换原来的 29 个散件（花瓣 + 花盘 + 眨眼帧）
## false = 恢复原版向日葵（原散件一个都没删，只是被隐藏）
@export var sun_enable: bool = true

## 立绘母版 1024×1536，游戏里只显示 56×82，等于运行时缩到 0.05 倍，
## 线稿会被双线性采样糊成灰边。这里改成离线先烘到「显示尺寸的 2 倍」（113×164），
## 运行时只缩 0.5 倍 —— 与豆蔻同一套做法，好处是描边是烘进去的真像素，不随缩放爬动。
##
## 两帧（闭眼打坐 / 睁眼举手）由同一套烘焙脚本产出：画布尺寸、缩放系数、底边锚点
## 三者完全一致，所以运行期两张 Sprite 只要 position 相同就能直接叠在一起，
## 不会出现「换帧时人突然变大变小、脚底往上跳」的现象。
## [br]换帧不是淡化，而是「擦除」：见 SUN_POSE_SHADER。
const SUN_ART_PATH: String = "res://assets/image/character/sunflower/sunflower_idle_01.png"
const SUN_CAST_ART_PATH: String = "res://assets/image/character/sunflower/sunflower_cast_01.png"
## 画布显示高度（含上下描边留白）
const SUN_HEIGHT: float = 82.0
## 2 倍空间里底边到画布下沿的留白，用来把「盘腿底边」精确对回 y=0
const SUN_FOOT_PAD_PX: float = 6.0
## 浮空高度（离地）与上下浮动幅度 / 单程时长
const SUN_HOVER_LIFT: float = 2.0
const SUN_FLOAT_PX: float = 2.6
const SUN_FLOAT_TIME: float = 1.35
## 丹田（双手捧丹处）在局部坐标里的位置，由贴图最亮暖色团块量出。
## 阳光/丹药就从这个点出生，而不是原版花盘那个 (43,27)。
const SUN_DANTIAN: Vector2 = Vector2(-0.5, -28.7)

#region 产阳光动作
## 双手举过头顶时，丹药（阳光）出生的位置。
## [br]由举手帧的贴图像素量出来：两只手的指尖在画布 (56, 8) 附近对到中线，
## 这里就是「掌心之间、头顶以上」那个点，换算到 Body 空间即 (-0.3, -77.0)。
## [br]刻意取在中轴上（x≈0）：植物左右翻转时这个点不会跟着偏，左右朝向都成立。
## [br]注意不要用「AI 原画里那颗丹」的坐标 —— 那颗丹画在右手腕上，偏右偏低了 17px，
## 阳光从那里冒出来会直接糊在脸上。
const SUN_HANDS: Vector2 = Vector2(-0.3, -77.0)

## 换帧擦除用的着色器：一条软边从腰往上扫，扫到哪儿的像素才换成举手帧。
## [br]为什么不用交叉淡化：两帧的差别全在手臂和眼睛，整体淡化会出现「四只手」的重影，
## 越慢越明显，这才是「换帧生硬」的真正来源。擦除式换帧全程只有一帧是实心的。
const SUN_POSE_SHADER: Shader = preload("res://resources/shader/sun_pose_reveal.gdshader")
## 擦除区下沿（UV.y，0 = 头顶）。164px 画布上约 y=123，正好卡在腰腹与盘腿之间：
## 盘腿以下两帧完全一样，不参与擦除就不会跟着闪。
const SUN_POSE_ZONE_BOTTOM: float = 0.75
## 擦除软边宽度（UV 比例）。0.09 × 164 ≈ 15px，比脸窄 ——
## 擦过五官时只会有一两帧半隐，不会出现「两只眼睛叠在一起」的重影。
const SUN_POSE_SOFTNESS: float = 0.09
## 边界扫到「肩线」时对应的 progress。肩在 164px 里的 y≈78 → 118/118 换算得 0.34。
## [br]扫过腰腹（旧手臂让位）和扫过上半身（新手臂长出）必须分成两段不同速度：
## 用同一个速度扫，腰腹清空之后要等很久肩膀才开始出现，中间会有「一段没手」的空档。
const SUN_POSE_SHOULDER_PROGRESS: float = 0.34

## 起手前的下压：像蹲一下再起身，给「发力」一个来处，也让后面的抬手不显得突然。
const SUN_ANTICIPATE_TIME: float = 0.12
## 抹掉腰腹旧手臂（progress 0 → 肩线）的时长。
const SUN_SWEEP_BELLY_TIME: float = 0.11
## 上半身擦除（progress 肩线 → 1）的时长，也就是手臂从肩膀长到指尖的时间。
const SUN_SWEEP_ARM_TIME: float = 0.27
## 抬手全程 = 下压 + 两段擦除，必须恰好等于 CreateSunComponent 里「身体点亮」的半程 0.5s：
## 这样双手到顶的瞬间正好是阳光出生的瞬间，光最亮、手最高、丹刚出现，三个点重合。
const SUN_RAISE_TIME: float = SUN_ANTICIPATE_TIME + SUN_SWEEP_BELLY_TIME + SUN_SWEEP_ARM_TIME

## 举顶停留：让「阳光从手里出来」这一下被看见，别一闪而过。
## [br]0.5s 不是随手定的：阳光出生后会先向上抛再往下落，整个下落路径正好从立绘正面
## 压过去，约 0.55s 后才让开。停留短于这个时间，玩家看到的就是「丹一出来就把人糊住了」，
## 「放下双手」这一半动作等于白做。留够时间，读取顺序才是「抬手 → 出丹 → 放手」。
const SUN_HOLD_TIME: float = 0.5
## 落手时长，明显长于抬手 —— 「慢慢放下」比「一举而起」慢，收势才显得稳。
const SUN_LOWER_TIME: float = 0.72
## 抬手过程中整个人向上提一点，落手回位
const SUN_RAISE_LIFT: float = 2.0
## 起手下压时的缩放：纵向压扁、横向撑开（体积守恒），读起来是「蓄力」
const SUN_ANTICIPATE_SCALE := Vector2(1.03, 0.965)
## 举到顶时的缩放：纵向拉长、横向收一点，读起来是「向上够」，
## 也顺手把视觉重心引到头顶，擦除边界往上扫时眼睛会跟着走
const SUN_REACH_SCALE := Vector2(0.985, 1.035)
## 阳光出生的那一瞬整体「顶一下」，给一点弹性反馈
const SUN_POP_SCALE: float = 1.06
const SUN_POP_UP_TIME: float = 0.07
const SUN_POP_DOWN_TIME: float = 0.11
## 发光峰值。朝阳童子的袍子本来就是浅黄，用组件默认的 2 倍会被冲成一张白纸，
## 发光期间眼睛、发丝全糊掉 —— 恰好把「睁眼」这个最关键的表演盖住了。
## 1.5 倍：袍子依然亮到发白（发光感保留），但深色细节还能读出来。
const SUN_FLASH_PEAK: float = 1.5
#endregion

@onready var create_sun_component: CreateSunComponent = $CreateSunComponent

## 闭眼打坐帧 / 睁眼举手帧，生命周期与植物一致
var _art_idle: Sprite2D = null
var _art_cast: Sprite2D = null
## 举手帧的擦除材质（progress 由 Tween 驱动）
var _pose_material: ShaderMaterial = null
## 动作支点：只承载「抬手/落手」的位移与弹性缩放，与浮空支点互不干扰
var _pose_pivot: Node2D = null
var _pose_tween: Tween = null
## 阳光出生点，以及它在「丹田 / 手上」两个位置相对 BodyCorrect 的局部坐标
var _marker: Marker2D = null
var _marker_dantian: Vector2 = Vector2.ZERO
var _marker_hands: Vector2 = Vector2.ZERO


func _ready() -> void:
	super()
	if sun_enable:
		_apply_sun_art()
		_connect_sun_pose()


## 隐藏散件版身体，换成整图立绘并加「浮空打坐」的待机动作。
## 说明：不改 .tscn 结构，全部在运行期完成，回退只需把 sun_enable 置 false。
func _apply_sun_art() -> void:
	var body_correct: Node2D = get_node_or_null("Body/BodyCorrect") as Node2D
	if body_correct == null:
		# 兜底：不同场景层级下按名字找，避免路径写死
		body_correct = find_child("BodyCorrect", true, false) as Node2D
	if body_correct == null:
		push_warning("朝阳童子：找不到 BodyCorrect，跳过换装")
		return

	var tex_idle: Texture2D = load(SUN_ART_PATH) as Texture2D
	var tex_cast: Texture2D = load(SUN_CAST_ART_PATH) as Texture2D
	if tex_idle == null or tex_cast == null:
		push_warning("朝阳童子：贴图没找到或还没被导入 → %s / %s" % [SUN_ART_PATH, SUN_CAST_ART_PATH])
		return
	if tex_idle.get_size() != tex_cast.get_size():
		# 两帧尺寸不一致就没法靠 position 对齐做交叉淡化，宁可报错也别让玩家看到跳帧
		push_error("朝阳童子：两帧立绘尺寸不一致 %s ≠ %s，请重跑烘焙脚本"
			% [tex_idle.get_size(), tex_cast.get_size()])
		return

	# 1) 原散件整体隐藏（花瓣、花盘、眨眼帧一起藏掉）
	body_correct.visible = false

	var holder: Node2D = body_correct.get_parent()
	var art_scale: float = SUN_HEIGHT / float(tex_idle.get_height())
	# 画布上下各留了 SUN_FOOT_PAD_PX 的描边余量，底边要减掉这段才正好落回 y=0
	var art_local_y: float = -SUN_HEIGHT * 0.5 + SUN_FOOT_PAD_PX * art_scale

	# 2) 浮空支点：先把整体抬起 SUN_HOVER_LIFT，再在这个支点上做上下浮动。
	#    拆成两层是为了两个量互不干扰 —— 以后调浮空高度不会牵动呼吸幅度，反之亦然。
	var float_pivot := Node2D.new()
	float_pivot.name = "SunFloatPivot"
	float_pivot.position = Vector2(0.0, -SUN_HOVER_LIFT)
	holder.add_child(float_pivot)

	# 3) 动作支点：抬手的位移与弹性缩放挂这里，刻意与浮空支点分开，
	#    否则两条 Tween 抢同一个 position:y 会互相打断。
	_pose_pivot = Node2D.new()
	_pose_pivot.name = "SunPosePivot"
	float_pivot.add_child(_pose_pivot)

	# 4) 两帧：位置、缩放完全一致，只有「举手帧露多少」不同 —— 举手帧盖在打坐帧上面，
	#    靠擦除材质控制它露出的比例，所以任何时候画面上只有一帧是实心的，不会出现重影。
	_art_idle = _make_art(tex_idle, art_scale, art_local_y, "SunIdle")
	_art_cast = _make_art(tex_cast, art_scale, art_local_y, "SunCast")
	_setup_pose_material(_art_cast)

	# 5) 浮空：上下慢飘。用 SINE 往返，两个端点速度都为 0，循环接缝看不出来
	var flt: Tween = create_tween().set_loops()
	flt.tween_property(float_pivot, "position:y", -SUN_HOVER_LIFT - SUN_FLOAT_PX, SUN_FLOAT_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	flt.tween_property(float_pivot, "position:y", -SUN_HOVER_LIFT + SUN_FLOAT_PX, SUN_FLOAT_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	# 6) 丹药出生点：算出「丹田」和「手上」两个位置。
	#    原坐标 (43,27) 是给花盘量出来的，这里用 BodyCorrect 的位移反算回 Body 空间，不写死像素。
	_marker = get_node_or_null("Body/BodyCorrect/Marker2DCreateSun") as Marker2D
	if _marker != null:
		_marker_dantian = SUN_DANTIAN - body_correct.position
		_marker_hands = SUN_HANDS - body_correct.position
		_marker.position = _marker_dantian
	else:
		push_warning("朝阳童子：找不到 Marker2DCreateSun，丹药仍从花盘位置出生")


## 生成一张整图立绘 Sprite，位置/缩放/父节点统一在这里定，保证两帧对齐。
func _make_art(tex: Texture2D, art_scale: float, local_y: float, node_name: String) -> Sprite2D:
	var art := Sprite2D.new()
	art.name = node_name
	art.texture = tex
	art.scale = Vector2(art_scale, art_scale)
	art.position = Vector2(0.0, local_y)
	# 默认居中：中心上移半个身高，盘腿底边正好落在 y=0
	_pose_pivot.add_child(art)
	return art


## 给举手帧挂擦除材质。progress=0 时这一层完全不可见，等于只有打坐帧。
func _setup_pose_material(art: Sprite2D) -> void:
	_pose_material = ShaderMaterial.new()
	_pose_material.shader = SUN_POSE_SHADER
	_pose_material.set_shader_parameter("progress", 0.0)
	_pose_material.set_shader_parameter("zone_bottom", SUN_POSE_ZONE_BOTTOM)
	_pose_material.set_shader_parameter("softness", SUN_POSE_SOFTNESS)
	art.material = _pose_material


## 擦除进度由 Tween 写进来（0 = 打坐帧，1 = 举手帧）。
func _set_pose_progress(value: float) -> void:
	if _pose_material != null:
		_pose_material.set_shader_parameter("progress", value)


## 接上产阳光组件的两个信号：开始蓄力 → 抬手，阳光出生 → 落手。
## 组件那边只发信号、不知道有立绘这回事，外观全部由植物自己管。
func _connect_sun_pose() -> void:
	if create_sun_component == null:
		push_warning("朝阳童子：找不到 CreateSunComponent，抬手动作不会播放")
		return
	create_sun_component.create_sun_started.connect(_on_create_sun_started)
	create_sun_component.create_sun_spawned.connect(_on_create_sun_spawned)
	# 只改发光强度，不动发光时长：节奏还是组件那套 0.5s 亮 / 0.5s 暗，
	# 抬手正好卡在「最亮」上，改峰值不会破坏这个对位。
	create_sun_component.create_sun_flash_peak = SUN_FLASH_PEAK


## 开始产阳光：下压蓄力 → 手臂从肩膀长上头顶，一气呵成。
## [br]整条动作是四拍，不是一次淡入：
## [br]1. 下压（0.12s）：身体微微一沉、横里撑开一点，给「发力」一个来处；
## [br]2. 抹腰腹（0.11s）：擦除边界快速扫过腰腹，捧丹的双手先让位；
## [br]3. 长手臂（0.27s）：边界从肩线扫到指尖，举手帧的手臂沿着肩膀→指尖的方向长出来。
## [br]1+2+3 正好 0.50s，等于组件发光的半程 —— 双手到顶时刚好阳光出生。
func _on_create_sun_started() -> void:
	if _art_cast == null or _pose_material == null:
		return
	# 出生点必须在阳光真正生成之前就位，而 marker 不参与绘制，提前挪看不出破绽
	if _marker != null:
		_marker.position = _marker_hands

	_kill_pose_tween()
	# 上一轮如果停在半途（极少数：打光被打断），先把姿势与缩放摆正再起手
	_pose_pivot.scale = Vector2.ONE
	_pose_pivot.position.y = 0.0
	_set_pose_progress(0.0)

	_pose_tween = create_tween()

	# 1) 下压蓄力。EASE_OUT：一上来就沉，后半程几乎不动，接得住下一拍
	_pose_tween.set_parallel(true)
	_pose_tween.tween_property(_pose_pivot, "scale", SUN_ANTICIPATE_SCALE, SUN_ANTICIPATE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_pose_tween.tween_property(_pose_pivot, "position:y", 0.8, SUN_ANTICIPATE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)

	# 2) 抹掉腰腹：这一段只是让旧手臂退场，不需要看得清，给得短
	_pose_tween.set_parallel(false)
	_pose_tween.tween_method(_set_pose_progress, 0.0, SUN_POSE_SHOULDER_PROGRESS, SUN_SWEEP_BELLY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)

	# 3) 长手臂 + 整个人向上提、纵向拉长。EASE_OUT 收得慢一点，
	#    让最后指尖到位那一下有余韵，不会「啪」地停住
	_pose_tween.set_parallel(true)
	_pose_tween.tween_method(_set_pose_progress,
		SUN_POSE_SHOULDER_PROGRESS, 1.0, SUN_SWEEP_ARM_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_pose_tween.tween_property(_pose_pivot, "position:y", -SUN_RAISE_LIFT, SUN_SWEEP_ARM_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_pose_tween.tween_property(_pose_pivot, "scale", SUN_REACH_SCALE, SUN_SWEEP_ARM_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)


## 阳光出生：手上「顶一下」→ 举顶停留 → 慢慢放下双手回丹田。
## [br]落手是抬手的严格逆序（指尖→肩膀→腰腹），而且更慢，所以「收」比「发」稳。
func _on_create_sun_spawned() -> void:
	if _art_cast == null:
		return

	_kill_pose_tween()
	_pose_tween = create_tween()

	# 1) 弹出的那一瞬整体顶一下：支点在脚底，所以是「向上长」而不是原地膨胀
	_pose_tween.tween_property(_pose_pivot, "scale", Vector2.ONE * SUN_POP_SCALE, SUN_POP_UP_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_pose_tween.tween_property(_pose_pivot, "scale", SUN_REACH_SCALE, SUN_POP_DOWN_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	# 2) 举顶停留，让「阳光从手里出来」这一下被看见
	_pose_tween.tween_interval(SUN_HOLD_TIME)
	# 3) 慢慢放下：擦除边界从头顶退回腰腹，手掌先收、脸后合眼、最后腰腹回到捧丹的手。
	#    三条同步，任何一条都不该抢跑
	_pose_tween.set_parallel(true)
	_pose_tween.tween_method(_set_pose_progress, 1.0, 0.0, SUN_LOWER_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_pose_tween.tween_property(_pose_pivot, "position:y", 0.0, SUN_LOWER_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_pose_tween.tween_property(_pose_pivot, "scale", Vector2.ONE, SUN_LOWER_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	# 4) 双手落回丹田之后，出生点才跟着回丹田。
	#    放在最后而不是立刻还原，是为了让「落在丹田的那一帧」和「之后的正常产阳光」
	#    在同一个位置上，不会出现下一颗阳光从胸口凭空冒出来。
	_pose_tween.set_parallel(false)
	_pose_tween.tween_callback(_reset_marker_to_dantian)


## 出生点收回丹田（落手动作完全结束后调用）。
func _reset_marker_to_dantian() -> void:
	if _marker != null:
		_marker.position = _marker_dantian


## 打断上一段动作。Tween 绑在植物节点上，节点释放时会自动清理，
## 这里只需处理「新动作覆盖旧动作」的情况。
func _kill_pose_tween() -> void:
	if _pose_tween != null and _pose_tween.is_valid():
		_pose_tween.kill()
	_pose_tween = null


func ready_norm() -> void:
	super()
	if is_zombie_mode:
		create_sun_component.disable_component(ComponentNormBase.E_IsEnableFactor.GameMode)

## 初始化正常出战角色信号连接
func ready_norm_signal_connect():
	super()
	signal_update_speed.connect(create_sun_component.owner_update_speed)


## 被僵尸啃食一次特殊效果,魅惑\大蒜\我是僵尸生产阳光
func _be_zombie_eat_once_special(_attack_zombie:Zombie000Base):
	if is_zombie_mode:
		create_sun_component._on_be_eat_once()

## 植物死亡
func character_death():
	if is_zombie_mode:
		create_sun_component._on_character_death()
	super()
