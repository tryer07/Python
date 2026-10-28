extends Plant000Base
class_name Plant004WallNut

## ── 镇山老翁（坚果 P004）新形象 ──────────────────────────────────────────
## true  = 用一整张 Q 版老翁立绘替换原版散件（_ground / Anim_idle / Anim_face / 眨眼图）
## false = 恢复原版坚果（散件一个都没删，只是被隐藏）
##
## 三态：满血＝完整、掉三分之一＝壳裂、再掉＝碎裂过半拄杖。
## 血量阈值沿用场景里 HpStageChangeComponent 的 boundary_value_hp（3666 / 1833 / 0，
## 按 5500 满血的三等分），
## 但那套机制只换 `Anim_face` 的贴图锁定原版散件，整图立绘用不上，
## 所以这里自己听 `signal_hp_loss` 换立绘，原机制保留（回退时仍然有效）。
@export var walnut_enable: bool = true

## ── 立绘 ────────────────────────────────────────────────────────────────
## 母版 1000px 级，离线烘到「游戏内显示尺寸的 2 倍」（130×164，内容高 152），
## 运行时只缩 0.6 倍（见 ART_SCALE）—— 与豆蔻／朝阳童子／并蒂樱童同一套做法，
## 不让引擎做 0.05 倍缩小，否则线稿会被双线性采样糊成灰边。
## [br]0.6 倍下实际是「2 倍母版缩到 1.2 倍内容」——依然在降采样，不会出锯齿糊边。
const ART_S1 := preload("res://assets/image/character/wallnut/wallnut_state1.png")
const ART_S2 := preload("res://assets/image/character/wallnut/wallnut_state2.png")
const ART_S3 := preload("res://assets/image/character/wallnut/wallnut_state3.png")
## 态3 的「无杖版」：只用于抽杖演出的那 0.4 秒 —— 立绘里没有杖，
## 才能让独立竹杖从背后划到身前而不出现两根杖。演完立刻换回 ART_S3。
const ART_S3_HOLD := preload("res://assets/image/character/wallnut/wallnut_state3_hold.png")
## 独立竹杖：198×232，比立绘画布四周各大 34（旋转时杖头要甩出立绘框）。
## 对称留白使「杖贴图中心 == 立绘画布中心」，两者用同一个 position/scale 即自动对齐。
const ART_STAFF := preload("res://assets/image/character/wallnut/wallnut_staff.png")

const ART_H := 164.0
## 立绘贴图四周的单边留白（2 倍空间），运行时用来把实体底边精确对回脚底
const ART_PAD := 6.0

## 运行时缩放。母版按「2 倍」尺寸烘好（130×164，内容高 152），这里缩到 0.6：
## 实体内容高 152×0.6 ≈ **91px**（原 0.5 → 76px，本次放大约 20%）。
## [br]91px 正好与雪清仙子（SNOW_PEA_H = 91）等高，食人花是 112 —— 在工程的尺度语汇里
## 属于「大体格但不越级」，不会盖住上下行。
## [br]缩放基准是「内容底边＝脚底」，所以放大后脚不离格、只往上长。
## 手位、抬杖位、背杖偏移全部由这个数推出来 —— 想再改大小**只动这一个数**。
const ART_SCALE := 0.6

## 脚底在 Body 局部坐标里的位置。
## 由原版 Anim_face 的 position(6.5,4.12)+scale(0.7,0.715)+BodyCorrect(-43,-69) 反算：
## 原版内容底边落在 y=6.6、水平中心 x=-1.5。新立绘的脚底对准同一个点，
## 换装前后站位不会挪。
const FOOT_LOCAL := Vector2(-1.5, 6.6)

## ── 背杖位 ──────────────────────────────────────────────────────────────
## 杖斜背在身后：杖头横把从帽子右肩上方探出、杖身斜向下没入后背。
## 偏移是「画布空间（2 倍）」的像素，运行时乘 art_scale。
## [br]露出剖面（离线逐像素核过，相对 state1 轮廓）：
## 杖头横把 + 上段竿（贴图 v=79..108，占全杖 27%）**整段露在帽子之上**，
## 其余竿身全部藏在身体后面 —— 这正是「斜背在身后」该有的读法。
## 再往下抬只会多露几像素，反而像立了根杆子，所以停在这里。
const STAFF_BACK_ROT := 22.0
const STAFF_BACK_OFF := Vector2(-16.4, -75.3)

## ── 待机动作 ────────────────────────────────────────────────────────────
## 支点在脚底，所以摆动与呼吸都是「原地长／晃」，脚不离地。
## 幅度对齐豆蔻（2.2°/0.8px）略收：这位是拄拐的老人家，晃太活泛会显得腿脚利索。
const SWAY_DEG := 2.0
const SWAY_TIME := 1.6
const BREATH_PX := 0.7
const BREATH_TIME := 1.0

## ── 态3 喘息循环 ────────────────────────────────────────────────────────
## 快吸 → 短停 → 缓呼 → 长歇。速率不对称才有「喘」的味儿：
## 匀速正弦只会读成「呼吸平稳」，而拄着拐还在喘的人是一口气吸进去、
## 撑不住地慢慢塌下来、然后歇一会儿再吸。
const GASP_IN := 0.55
const GASP_HOLD := 0.20
const GASP_OUT := 0.78
const GASP_RISE_BACK := 0.32
const GASP_REST := 1.15
const GASP_LIFT := 1.0
const GASP_SINK := 1.5
## 态3 的摆动幅度收到很小：整张图一起晃，幅度大了会像要把拐杖晃倒
const GASP_SWAY_DEG := 0.7
const GASP_SWAY_TIME := 1.9

## 抽杖演出：抽出（杖在立绘后）→ 换层 → 落下（杖在立绘前）→ 切图
const PULL_LIFT_TIME := 0.16
const PULL_DROP_TIME := 0.20
## 抬起位：竹杖在这里与「无杖立绘」**零重叠**（离线逐像素核过，100.00% 可见）。
## 所以「在这一帧把杖从立绘后面换到前面」肉眼绝对看不出 —— 换层的跳变被
## 零遮挡这个条件完全消掉了。少了这一步，杖整根都会钻进身体里消失，
## 玩家会以为它凭空蒸发了，这正是「拐杖出现得太突兀」的来源。
## [br]与 HAND_CANVAS 同属画布空间（原点＝画布中心），运行时经 `_canvas_to_local()` 换算。
const PULL_LIFT_ROT := 8.0
const PULL_LIFT_CANVAS := Vector2(32.0, -72.0)
## 拐杖落地那一下的整体下沉量（屏幕像素）
const LAND_DIP := 1.6

## ── 亡语：临终一杖 ──────────────────────────────────────────────────────
## 血量归零时不立刻消失，而是把杖拽到手里向前横扫，结算完伤害才倒下消散。
## 时间轴（秒）：拽杖 0.14 → 后仰蓄力 0.12 → 挥下 0.11 → 定格 0.09 → 前扑淡出 0.26。
## 总长约 0.72 秒：再长会挡住玩家补种，再短读不出「挥」这个动作。
const DEATH_DRAW_TIME := 0.14
const DEATH_WINDUP_TIME := 0.12
const DEATH_SWING_TIME := 0.11
const DEATH_HOLD_TIME := 0.09
const DEATH_FADE_TIME := 0.26

## 一杖的伤害，同行身前的每个目标各吃一次
const DEATH_RATTLE_DAMAGE := 500
## 「身前」的容差：僵尸贴上来啃时脚点会略在植物中心左边，留 40px 才不会漏掉它
const DEATH_REACH_BACK := 40.0

## 挥杖支点＝手的位置。手位由态3 立绘里那根画上去的竹杖反推：
## 杖身纵贯 x≈17..30、y≈-56..-1，握在杖身约 65% 处 → 0.5 倍下读作支点系 (24, -22)。
## [br]⚠️ 但 (24,-22) 是**带缩放的读数**，直接写死会让「立绘放大后手位跟不上」——
## 杖会从肚子旁边扫出去。所以这里存**画布空间**（贴图原始像素、原点＝画布中心）
## (48, 32)，运行时经 `_canvas_to_local()` 换算：立绘多大，手就在多大。
const HAND_CANVAS := Vector2(48.0, 32.0)
## 挥杖角度：先向身后抬起，再一路压到身前。
## 正角度＝顺时针＝杖头往右（屏幕前方），所以蓄力是负、挥下是正。
const STAFF_WINDUP_DEG := -58.0
const STAFF_SWING_DEG := 86.0
## 身体配合：后仰蓄力 → 前倾发力 → 前扑倒地。
## 摆动共用脚底支点，所以这三个角度都是「原地压」而不是平移。
const BODY_WINDUP_DEG := -4.0
const BODY_SWING_DEG := 9.0
const BODY_COLLAPSE_DEG := 17.0

@onready var hp_stage_change_component: HpStageChangeComponent = $HpStageChangeComponent

## 立绘与竹杖。两层支点是最小必要：
## Body → WallnutIdlePivot（只做 rotation 摆动 + 落地顿挫）→ WallnutArtPivot（只做呼吸）
## 呼吸写 ArtPivot.position.y、摆动写 IdlePivot.rotation，两者不抢同一个属性，
## 叠起来才是「一边晃一边喘」。
var _art: Sprite2D = null
var _staff: Sprite2D = null
var _idle_pivot: Node2D = null
var _art_pivot: Node2D = null
var _art_scale: float = ART_SCALE
var _art_local_y: float = 0.0
## 当前形态：0=完整、1=破损、2=濒死
var _stage: int = 0
## 待机/喘息用到的 Tween，换形态时统一收掉，免得两套动作叠着跑
var _motion: Array[Tween] = []
## 抽杖演出用的 Tween。它不在 `_motion` 里（那是循环动作），单独记一份，
## 免得血量刚好在抽杖那 0.36 秒里归零时，它还在往 `_staff` 的 position/rotation 上写字。
var _pull_tween: Tween = null
## 亡语的挥杖支点，运行时挂在 `_art_pivot` 下；没死亡时为 null
var _swing_pivot: Node2D = null


## 换装入口只挂在 `_ready` 上，与豆蔻／朝阳童子／并蒂樱童一致。
## [br]`character_000_base._ready()` 按 `character_init_type` 分派
## ready_norm / ready_show / ready_garden，在分派之后统一换装，
## 任何初始化类型都不会漏（图鉴详情页就是 IsShow 那条路）。
func _ready() -> void:
	super()
	if not walnut_enable:
		return
	_apply_walnut_art()
	hp_component.signal_hp_loss.connect(_on_hp_loss)


func ready_norm_signal_connect():
	super()
	## 连接信号
	hp_component.signal_hp_loss.connect(hp_stage_change_component.judge_body_change)


## 隐藏散件版身体，换成整图立绘 + 独立竹杖。
## 不改 .tscn 结构，全部在运行期完成，回退只需把 walnut_enable 置 false。
## [br]挂到 Body（BodyCorrect 的父节点）而不是 BodyCorrect 下：状态机停在 Start 时
## 会把 BodyCorrect 的子精灵重置成 visible=false / scale≈0，挂进去的立绘会被一起吃掉。
func _apply_walnut_art() -> void:
	# 幂等：三条初始化路径已收口到 _ready，但换装可能被外部重入
	if is_instance_valid(_art):
		return
	var body_correct: Node2D = get_node_or_null("Body/BodyCorrect") as Node2D
	if body_correct == null:
		body_correct = find_child("BodyCorrect", true, false) as Node2D
	if body_correct == null:
		push_warning("镇山老翁：找不到 BodyCorrect，跳过换装")
		return

	# 1) 原散件整体隐藏（土块 + 身体 + 脸 + 两种眨眼）
	body_correct.visible = false

	# 2) 两层支点都落在「脚底」：绕支点旋转才是「原地晃」，
	#    支点若在贴图中心，摆动会带着脚一起左右平移，像在台阶上滑。
	_idle_pivot = Node2D.new()
	_idle_pivot.name = "WallnutIdlePivot"
	_idle_pivot.position = FOOT_LOCAL
	body_correct.get_parent().add_child(_idle_pivot)

	_art_pivot = Node2D.new()
	_art_pivot.name = "WallnutArtPivot"
	_idle_pivot.add_child(_art_pivot)

	# 3) 立绘几何：居中贴图，中心上移半个身高，实体底边正好落在支点上
	#    ⚠️ 这一段是「全部尺寸的唯一来源」：脚底对位、手位、抬杖位都从 _art_scale
	#    与 _art_local_y 推出来，所以改 ART_SCALE 不需要再手改任何偏移量。
	_art_scale = ART_SCALE
	_art_local_y = -ART_H * 0.5 * _art_scale + ART_PAD * _art_scale

	# 4) 竹杖先入树。同一 z 序下「先加先画」= 杖被立绘压住，这一个层级同时解决两件事：
	#    背在身后时中段被身体盖住（只露杖头），撑地时杖身被手心盖住（读成握住）。
	# [br]这里**绝不能**用 z_index = -1：z_index 是沿父链累加的，-1 会把这根杖
	# 一路压到图鉴面板背景之后，整根被背景板吃掉（实测「藏杖」与「显示杖」两张
	# 同帧截图差异为 0 像素，而把它提到 z=2 差异立刻变成 379 像素）。
	# 同级绘制顺序只影响「立绘 vs 竹杖」的先后，不会脱离父节点落到背景后面。
	_staff = Sprite2D.new()
	_staff.name = "WallnutStaff"
	_staff.texture = ART_STAFF
	_staff.scale = Vector2(_art_scale, _art_scale)
	_staff.position = _staff_back_pos()
	_staff.rotation = deg_to_rad(STAFF_BACK_ROT)
	_art_pivot.add_child(_staff)

	# 5) 立绘后入树 → 画在竹杖之上
	_art = Sprite2D.new()
	_art.name = "WallnutArt"
	_art.texture = ART_S1
	_art.scale = Vector2(_art_scale, _art_scale)
	_art.position = Vector2(0.0, _art_local_y)
	_art_pivot.add_child(_art)

	_play_idle_motion()


## 竹杖换到立绘**前面**（抽杖落定那半段用）。
## [br]用同级顺序而不是 z_index：`move_to_front()` 只动兄弟排序，
## 不会被父链累加成负 z 而掉到背景后面。
func _staff_to_front() -> void:
	if is_instance_valid(_staff):
		_staff.move_to_front()


## 竹杖换回立绘**后面**（背杖状态）。
func _staff_to_back() -> void:
	if is_instance_valid(_art):
		_art.move_to_front()


## 背杖位：杖 Sprite 与立绘共用 position，再叠一个画布空间偏移
func _staff_back_pos() -> Vector2:
	return Vector2(0.0, _art_local_y) + STAFF_BACK_OFF * _art_scale


## 画布空间 → 立绘支点坐标系（游戏内像素）。
## [br]立绘以「内容底边＝脚底」为基准缩放：内容里的点离脚底多远，就按 _art_scale 等比长。
## 所以画布上的读数只要乘一次 _art_scale、再把「画布中心相对脚底」的 _art_local_y 加回去。
## [br]⚠️ 不要反过来把游戏内像素写死进常量 —— 那样一改 ART_SCALE，手位和杖位就会和身体脱节。
func _canvas_to_local(p: Vector2) -> Vector2:
	return Vector2(p.x * _art_scale, _art_local_y + p.y * _art_scale)


## 手位（亡语挥杖的支点）
func _hand_local() -> Vector2:
	return _canvas_to_local(HAND_CANVAS)


## 抽杖时的抬杖位
func _pull_lift_pos() -> Vector2:
	return _canvas_to_local(PULL_LIFT_CANVAS)


## 态1／态2 的待机：绕脚底左右轻摆 + 呼吸起伏。
## [br]用 SINE + EASE_IN_OUT：两个端点速度都是 0，循环接缝处看不出来。
func _play_idle_motion() -> void:
	_kill_motion()
	var sway: Tween = create_tween().set_loops()
	sway.tween_property(_idle_pivot, ^"rotation", deg_to_rad(SWAY_DEG), SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	sway.tween_property(_idle_pivot, ^"rotation", deg_to_rad(-SWAY_DEG), SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	var breath: Tween = create_tween().set_loops()
	breath.tween_property(_art_pivot, ^"position:y", -BREATH_PX, BREATH_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	breath.tween_property(_art_pivot, ^"position:y", 0.0, BREATH_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	_motion = [sway, breath]


## 态3 的喘息：快吸 → 短停 → 缓呼 → 长歇。
## [br]和待机的匀速呼吸是两套东西，所以这里必须先把待机 Tween 收掉。
func _play_gasp_motion() -> void:
	_kill_motion()
	_idle_pivot.rotation = 0.0
	_art_pivot.position = Vector2.ZERO

	var gasp: Tween = create_tween().set_loops()
	# 吸气：胸腔提起来，速度略快、末段减速（吸到顶会顿一下）
	gasp.tween_property(_art_pivot, ^"position:y", -GASP_LIFT, GASP_IN) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	gasp.tween_interval(GASP_HOLD)
	# 呼气：塌下去，而且沉到比静止还低 —— 这是「撑不住」的关键
	gasp.tween_property(_art_pivot, ^"position:y", GASP_SINK, GASP_OUT) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	# 缓慢回位，再歇一口气
	gasp.tween_property(_art_pivot, ^"position:y", 0.0, GASP_RISE_BACK) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	gasp.tween_interval(GASP_REST)

	var sway: Tween = create_tween().set_loops()
	sway.tween_property(_idle_pivot, ^"rotation", deg_to_rad(GASP_SWAY_DEG), GASP_SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	sway.tween_property(_idle_pivot, ^"rotation", deg_to_rad(-GASP_SWAY_DEG), GASP_SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	_motion = [gasp, sway]


func _kill_motion() -> void:
	for t: Tween in _motion:
		if is_instance_valid(t):
			t.kill()
	_motion.clear()
	_idle_pivot.rotation = 0.0
	_art_pivot.position = Vector2.ZERO


## 血量变化 → 换算成形态。阈值沿用场景里配的 boundary_value_hp，不另抄一份。
## [br]注意不能「命中第一个边界就 break」：boundary 是递减的（2666 / 1333 / 0），
## 1000 血同时满足 <=2666 与 <=1333，要取更靠后的那个才是「濒死」。
## 所以这里一路往下比，最后落到的那个 i 才是当前形态。
func _on_hp_loss(curr_hp: int, is_drop: bool) -> void:
	if not is_drop or not is_instance_valid(_art):
		return
	var boundaries: Array[int] = hp_stage_change_component.boundary_value_hp
	var stage: int = 0
	for i: int in boundaries.size():
		# 最后一个是死亡线，不参与形态划分
		if i >= 2:
			break
		if curr_hp <= boundaries[i]:
			stage = i + 1
	_set_stage(stage)


func _set_stage(stage: int) -> void:
	if stage == _stage:
		return
	_stage = stage
	if stage >= 2:
		_pull_out_staff()
		return
	_art.texture = ART_S1 if stage == 0 else ART_S2
	_staff.visible = true
	_staff.rotation = deg_to_rad(STAFF_BACK_ROT)
	_staff.position = _staff_back_pos()
	_staff_to_back()
	_play_idle_motion()


## 抽杖：血量跌进濒死档的那一下。
## [br]流程刻意是「先换无杖立绘、杖再从背后划出来、最后才换回带杖立绘」：
## 立绘里那根杖是画的，若不先拿掉，抽杖途中会同时出现两根。
## 无杖版只在 PULL_LIFT_TIME + PULL_DROP_TIME（0.36 秒）里露面，
## 这点时间不足以让玩家看出独立杖比画里的杖细一圈。
## [br]三段式：抽出（杖在立绘后，只露杖头 → 越转越露）→ 换层 → 落下（杖在立绘前）。
func _pull_out_staff() -> void:
	_kill_motion()
	_art.texture = ART_S3_HOLD
	_staff.visible = true
	_staff.rotation = deg_to_rad(STAFF_BACK_ROT)
	_staff.position = _staff_back_pos()
	_staff_to_back()

	var pull: Tween = create_tween()
	_pull_tween = pull
	# 1) 抽出：从背带里抬起、转正、顺势滑到身体右侧之外。
	#    这一段杖还在立绘后面，可见度从 36% 一路单调爬到 100%，
	#    读起来就是「从背后抽出来」而不是「凭空出现」。
	pull.tween_property(_staff, ^"rotation", deg_to_rad(PULL_LIFT_ROT), PULL_LIFT_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	pull.parallel().tween_property(_staff, ^"position", _pull_lift_pos(), PULL_LIFT_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	# 2) 换层：此刻杖与立绘零重叠，换到前景看不出来
	pull.tween_callback(_staff_to_front)
	# 3) 落下：竖直落到脚边撑地
	pull.tween_property(_staff, ^"rotation", 0.0, PULL_DROP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	pull.parallel().tween_property(_staff, ^"position",
		Vector2(0.0, _art_local_y), PULL_DROP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	pull.tween_callback(_on_staff_landed)


## 杖落地那一瞬：换回带杖立绘、收起独立杖，再让整株「一顿」。
## [br]这一顿是必须的 —— 换图的硬切和被拐杖拽了一下的震动同时发生，
## 视线在震，跳变就看不见了。
func _on_staff_landed() -> void:
	_art.texture = ART_S3
	_staff.visible = false

	var dip: Tween = create_tween()
	dip.tween_property(_idle_pivot, ^"position:y", FOOT_LOCAL.y + LAND_DIP, 0.07) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	dip.tween_property(_idle_pivot, ^"position:y", FOOT_LOCAL.y, 0.18) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_play_gasp_motion()


#region 亡语：临终一杖
## 亡语入口，由 `Character000Base.character_death()` 在 `is_can_death_language` 为真时调用。
## [br]⚠️ 时序是关键：父类 `Plant000Base.character_death()` 先 `super()`（亡语就在里面跑），
## 之后才判断 `is_death_free` 并 `queue_free()`。所以在这里把 `is_death_free` 压成 false，
## 父类那一步就不会执行，挥杖才演得出来 —— 收尾由 `_death_rattle_collapse()` 自己补。
## [br]铲除、坑洞清场均会把 `is_can_death_language` 置 false，这一杖不会误触。
func death_language() -> void:
	# 图鉴/花园里的镇山老翁不该挥杖（那里也没有僵尸管理器）
	if not walnut_enable or character_init_type != E_CharacterInitType.IsNorm:
		return
	# 换装没成功（立绘或竹杖缺失）就退回原版行为：直接消失
	if not is_instance_valid(_art) or not is_instance_valid(_staff):
		return
	# 幂等：`character_death()` 正常只会被血量信号触发一次，但子类里有人直接调用它，
	# 真被叫第二次时不能再抽一根杖出来
	if is_instance_valid(_swing_pivot):
		return
	is_death_free = false
	_death_rattle_start()


## 挥杖支点在支点坐标系里的「握把」位置：竹杖中心对齐立绘中心，再减掉手位。
func _staff_grip_pos() -> Vector2:
	return Vector2(0.0, _art_local_y) - _hand_local()


## 把挥杖支点排到立绘之后（即画在立绘上面）。
## [br]用同级顺序而不是 z_index：z_index 会沿父链累加，负值会把整根杖压到背景板后面。
func _swing_pivot_to_front() -> void:
	if is_instance_valid(_swing_pivot) and is_instance_valid(_art_pivot):
		_art_pivot.move_child(_swing_pivot, _art_pivot.get_child_count() - 1)


func _death_rattle_start() -> void:
	# 待机/喘息/抽杖三套动作全收掉，否则会有别的 Tween 抢同一个属性
	_kill_motion()
	if is_instance_valid(_pull_tween):
		_pull_tween.kill()
		_pull_tween = null

	# 态3 立绘里画着一根竹杖，挥杖前先换「无杖版」，不然会同时出现两根
	if _stage >= 2:
		_art.texture = ART_S3_HOLD

	# 支点落在手上：绕手转才是挥杖，绕贴图中心转会变成风车
	_swing_pivot = Node2D.new()
	_swing_pivot.name = "WallnutSwingPivot"
	_swing_pivot.position = _hand_local()
	_art_pivot.add_child(_swing_pivot)
	# 先排在立绘后面：态0/1 的杖本来就斜背在身后，抽杖途中不该突然穿到身前
	_art_pivot.move_child(_swing_pivot, 0)

	# 接管独立竹杖。reparent 第二参数为 false 时保留的是「局部变换的数值」，
	# 而父节点原点换了，所以要把手位从 position 里减回去，画面才不会跳一下。
	var from_pos: Vector2 = _staff.position - _hand_local()
	var from_rot: float = _staff.rotation
	_staff.reparent(_swing_pivot, false)
	_staff.position = from_pos
	_staff.rotation = from_rot
	_staff.visible = true

	# ── 竹杖时间轴：拽到手里 → 换层 → 后仰 → 挥下 → 定格 → 倒下
	var staff_tween: Tween = create_tween()
	staff_tween.tween_property(_staff, ^"position", _staff_grip_pos(), DEATH_DRAW_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	staff_tween.parallel().tween_property(_staff, ^"rotation", 0.0, DEATH_DRAW_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	# 杖抽出来了才换到身前，挥击才不会从身体里穿过去
	staff_tween.tween_callback(_swing_pivot_to_front)
	staff_tween.tween_callback(func(): SoundManager.play_other_SFX(&"swing"))
	# 蓄力：杖头抬到身后上方，末段减速（抬到顶会顿一下）
	staff_tween.tween_property(_swing_pivot, ^"rotation", deg_to_rad(STAFF_WINDUP_DEG), DEATH_WINDUP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	# 挥下：EASE_IN + QUAD 才有「越挥越快、砸到最前才停」的加速感
	staff_tween.tween_property(_swing_pivot, ^"rotation", deg_to_rad(STAFF_SWING_DEG), DEATH_SWING_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	staff_tween.tween_callback(_death_rattle_strike)
	staff_tween.tween_interval(DEATH_HOLD_TIME)
	staff_tween.tween_callback(_death_rattle_collapse)

	# ── 身体配合：后仰 → 前倾。单独一条 Tween，起手等拽杖演完再动
	var body_tween: Tween = create_tween()
	body_tween.tween_interval(DEATH_DRAW_TIME)
	body_tween.tween_property(_idle_pivot, ^"rotation", deg_to_rad(BODY_WINDUP_DEG), DEATH_WINDUP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	body_tween.tween_property(_idle_pivot, ^"rotation", deg_to_rad(BODY_SWING_DEG), DEATH_SWING_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)


## 挥到最前的那一帧：音效、杖头闪光、结算伤害。三者同帧，打击感才对得上。
func _death_rattle_strike() -> void:
	SoundManager.play_other_SFX(&"bonk")
	if is_instance_valid(_staff):
		# 没有拖尾特效，用一下高亮补掉「挥到头」的那一瞬
		_staff.modulate = Color(2.0, 1.9, 1.6)
		var flash: Tween = create_tween()
		flash.tween_property(_staff, ^"modulate", Color.WHITE, 0.16)
	_death_rattle_damage()


## 同行、身前的所有目标各吃 500 真实伤害。
## [br]走 `be_attacked_bullet(..., Real, ...)`：与地刺同一套结算，僵尸会正常白闪、
## 正常掉血，而不是像爆炸那样直接变成灰。
func _death_rattle_damage() -> void:
	var game: MainGameManager = Global.main_game
	# 图鉴/花园没有主游戏管理器
	if not is_instance_valid(game):
		return
	var manager: ZombieManager = game.zombie_manager
	if not is_instance_valid(manager):
		return

	var front_x: float = global_position.x - DEATH_REACH_BACK

	# 普通僵尸：倒序遍历，被这一杖打死的会立刻从行列表里移除
	if lane >= 0 and lane < manager.all_zombies_2d.size():
		var row: Array = manager.all_zombies_2d[lane]
		for i: int in range(row.size() - 1, -1, -1):
			var zombie := row[i] as Zombie000Base
			if not is_instance_valid(zombie) or zombie.is_death or zombie.is_queued_for_deletion():
				continue
			# 只打正常状态的：地下的、跳在半空的、水下的都不该被一杖扫到
			if (zombie.curr_be_attack_status & Zombie000Base.E_BeAttackStatusZombie.IsNorm) == 0:
				continue
			if zombie.global_position.x < front_x:
				continue
			zombie.be_attacked_bullet(DEATH_RATTLE_DAMAGE, BulletRegistry.AttackMode.Real, true, true)

	# 僵王：同样只看行号与身前，受击窗口由它自己的入口判定
	for boss: ZB000Base in manager.get_living_bosses():
		if not is_instance_valid(boss) or boss.is_death or boss.is_queued_for_deletion():
			continue
		if boss.lane != lane or boss.global_position.x < front_x:
			continue
		boss.be_attacked_bullet(DEATH_RATTLE_DAMAGE, BulletRegistry.AttackMode.Real, false, false)


## 收杖倒下：前扑 + 整体淡出，最后才真正删除节点。
## [br]淡出写在 `self.modulate` 上，影子、立绘、竹杖、血条一起收，
## 不会出现「身体没了影子还杵在地上」。
func _death_rattle_collapse() -> void:
	var fall: Tween = create_tween()
	fall.tween_property(_idle_pivot, ^"rotation", deg_to_rad(BODY_COLLAPSE_DEG), DEATH_FADE_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	fall.parallel().tween_property(self, ^"modulate:a", 0.0, DEATH_FADE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	fall.tween_callback(queue_free)
#endregion
