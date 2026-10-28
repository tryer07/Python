extends Plant000Base
class_name Plant006SnowPea

## ============================================================================
## 雪清仙子（寒冰射手同人形象）—— 2026-10-26 第八轮
## [br]做法与 [Plant007Chomper] 完全一致：**不改 .tscn 结构**，
## [br]运行期把原版散件（茎叶 + 头部 + 眼睛 + 嘴 + 冰晶）整体隐藏，
## [br]再挂一张整图立绘。回退只需把 [member snow_pea_enable] 置 false。
## [br]冰球不再画在立绘里 —— 它已经是程序生成的子弹贴图
## [br]（`ice_fire_core.png` / `ice_fire_shell.png`），由攻击组件发射。
## ============================================================================

## 换装总开关。关掉就完全回到原版寒冰射手。
@export var snow_pea_enable: bool = true

## 立绘贴图（2 倍图，264×398，人物实体高 382px）
const ART_IDLE := preload("res://assets/image/character/snow_pea/xueqing_idle.png")

## 贴图尺寸（2 倍图）
const IDLE_TEX_W := 264.0
const IDLE_TEX_H := 398.0
## 人物实体在贴图里的上下边界（2 倍图坐标，alpha>8 量得；左右同样居中，实体中心 x=131 对画布中心 132）
const IDLE_FIG_TOP := 8.0
const IDLE_FIG_BOTTOM := 390.0
const IDLE_FIG_H := IDLE_FIG_BOTTOM - IDLE_FIG_TOP + 1.0   # = 383

## 战场上的人物实体高度（游戏单位）。
## [br]⚠️ 2026-10-27 两轮实测：190 太大 → 缩到 40%（76）又偏小 → **再放大 20% = 91**。
## [br]91 大约与豆蔻（约 86~90）同档，别再往上加。
const SNOW_PEA_H := 91.0

## 脚底支点（相对 BodyCorrect 的本地坐标）。
## [br]⚠️ 2026-10-26 实测校正：一开始误写成 (43, 62)（照着 Stalk_bottom 的 position 猜的），
## [br]结果实机里脚底比格子低了 59px —— 因为 BodyCorrect 自身已有
## [br]`position = (-43, -69)` 的偏移，再加偏移等于双重位移。
## [br]参照醉仙客的 `CHOMPER_FOOT_BODY = (-11.25, 0.9)` 同样是"贴近原点"，
## [br]这里取 (0, 0)：立绘脚底就落在植物节点的原点上，与格子中心对齐。
const SNOW_PEA_FOOT_BODY := Vector2(0.0, 0.0)

## ── 出手动作（冰珠离手）────────────────────────────────────────────────
## 立绘只有一张静态图，原版那套「抬手—发射」动画全在 BodyCorrect 的散件上，
## 换装后散件被隐藏，动作等于没有了。这里用两个补间把它补回来：
## [br]· 支点绕脚底顺时针偏 3.4° —— 整株向前一送（重心压在前脚）；
## [br]· 立绘向右推 3px 并轻微下压 —— 袖口递出去的那一瞬。
## [br]⚠️ 只挂 [signal AttackComponentBulletBase.signal_shoot_bullet]，
## **不挂** signal_attack_anim_start：那一个是「准备开打」，
## 之后如果目标死掉、这一发被取消，植物会卡在蓄力姿态上再也回不来。
## 出手信号一定伴随子弹生成，不会漏触发，也不会落空。
const ATTACK_LUNGE_X := 3.0
const ATTACK_LUNGE_ROT := 0.06      # 弧度，≈3.4°
const ATTACK_OUT_TIME := 0.06
const ATTACK_BACK_TIME := 0.24

## ── 图鉴详情页取景 ──────────────────────────────────────────────────────
## `almanac_character_show_panel.tscn` 里的 `CharacterBg` 是 200×200 且开了
## `clip_children`，越界一律裁掉；通用落点又把植物根节点放在 (100, 120)。
## [br]战场口径 91 时，1:1 摆进去仍比其他株矮一截，所以展示实例单独放大 1.22 倍：
## 91 × 1.22 ≈ 111，与豆蔻（实测 111）同高。
## 脚底落在 y≈125（豆蔻 125 / 朝阳童子 122.5），头顶 y≈14 —— 三株同一构图。
## [br]⚠️ 这个值只跟着 SNOW_PEA_H 走：战场高度一变，这里要按 111 / SNOW_PEA_H 重算。
const ALMANAC_SHOW_SCALE := 1.22
## 脚底在窗口里的目标 y。
## [br]⚠️ 别照「把脚踩到窗口底 196」去填：通用落点 120 就是原版植物的脚底线，
## 豆蔻/朝阳童子都在 122~125。填 196 会让她一个人沉到框底，和同页其他人错位一大截。
const ALMANAC_SHOW_FOOT_Y := 125.0
## 通用落点给植物根节点的位置（见 panel_container.gd 的 _apply_show_layout）。
const ALMANAC_ROOT_Y := 120.0

@onready var attack_component: AttackComponentBulletBase = $AttackComponent

var _art: Sprite2D = null
var _idle_pivot: Node2D = null
var _art_scale: float = 1.0
var _art_local_y: float = 0.0
## 出手补间分位置、角度两条；连发时先 kill 旧的，避免偏移累积
var _attack_tweens: Array[Tween] = []
## 待机浮动的循环补间。图鉴取景要改 `_idle_pivot.position`，
## 而这条补间把基准点写死在创建那一刻（返回 Vector2.ZERO），不先 kill 掉会一直跟取景打架。
var _idle_tween: Tween = null

## 初始化正常出战角色信号连接
func ready_norm_signal_connect():
	super()
	signal_update_speed.connect(attack_component.owner_update_speed)


## 换装入口。必须挂 `_ready` 而不是 ready_norm：
## 战场走 ready_norm、图鉴详情页走 ready_show、禅境花园走 ready_garden，
## 挂在 _ready 才能一次覆盖三条路径。
func _ready() -> void:
	super()
	if not snow_pea_enable:
		return
	_apply_snow_pea_art()


## 隐藏原版散件、换整图立绘。
## [br]挂到 Body 下（BodyCorrect 的父节点）而不是 BodyCorrect 里：
## [br]动画状态机会对 BodyCorrect 里每个子精灵写 visible / scale 轨道，
## [br]立绘挂进去会被 idle 的 Start 帧覆盖掉（醉仙客那轮踩过）。
func _apply_snow_pea_art() -> void:
	if is_instance_valid(_art):
		return
	var body_correct: Node2D = get_node_or_null("Body/BodyCorrect") as Node2D
	if body_correct == null:
		body_correct = find_child("BodyCorrect", true, false) as Node2D
	if body_correct == null:
		push_warning("雪清仙子：找不到 BodyCorrect，跳过换装")
		return

	# 1) 原版散件整体隐藏
	body_correct.visible = false

	# 2) 脚底支点：绕脚底旋转才是原地晃，支点在贴图中心脚会左右滑
	_idle_pivot = Node2D.new()
	_idle_pivot.name = "XueqingIdlePivot"
	_idle_pivot.position = SNOW_PEA_FOOT_BODY
	body_correct.get_parent().add_child(_idle_pivot)

	# 3) 几何：Sprite2D 默认以贴图中心为原点。
	#    先按"人物实体高度"算缩放，再把中心上移，使实体底边正好落在支点原点。
	_art_scale = SNOW_PEA_H / IDLE_FIG_H
	var fig_center_in_tex: float = (IDLE_FIG_TOP + IDLE_FIG_BOTTOM) * 0.5 - IDLE_TEX_H * 0.5
	_art_local_y = -(SNOW_PEA_H * 0.5 + fig_center_in_tex * _art_scale)

	_art = Sprite2D.new()
	_art.name = "XueqingArt"
	_art.texture = ART_IDLE
	_art.scale = Vector2(_art_scale, _art_scale)
	_art.position = Vector2(0.0, _art_local_y)
	_idle_pivot.add_child(_art)

	_play_idle_motion()
	_connect_attack_motion()
	# ⚠️ 必须放在换装**之后**判断：`is_show` 是 ready_show() 里置的，
	# 而 ready_show 在本方法的 super() 里就已经跑过了，此时立绘还不存在。
	if is_show:
		_apply_almanac_framing()


## 图鉴详情页取景：缩一档 + 把脚底压到窗口底部，让 190 高的立绘整个人进框。
## [br]只动 pivot（缩放 + 位移），`_art` 的本地坐标不变，战场 / 卡面都不受影响。
func _apply_almanac_framing() -> void:
	if not is_instance_valid(_idle_pivot):
		return
	_idle_pivot.scale = Vector2(ALMANAC_SHOW_SCALE, ALMANAC_SHOW_SCALE)
	_idle_pivot.position = SNOW_PEA_FOOT_BODY + Vector2(
		0.0, ALMANAC_SHOW_FOOT_Y - ALMANAC_ROOT_Y)
	# 待机浮动会以新落点为基准重新起一条，老的必须先停掉
	_play_idle_motion()


## 接出手信号。换装关掉时整段跳过，原版散件动画照旧。
func _connect_attack_motion() -> void:
	if attack_component == null:
		return
	if not attack_component.signal_shoot_bullet.is_connected(_on_shoot_bullet):
		attack_component.signal_shoot_bullet.connect(_on_shoot_bullet)


## 冰珠离手：向前一送再缓缓落回。
## [br]两条补间分开建（位置 / 角度），因为同一个 Tween 里连写两个属性会变成**先后**执行，
## 而不是同时 —— 那样会先推出去、推完才开始转头，读起来是两拍。
func _on_shoot_bullet() -> void:
	if not is_instance_valid(_idle_pivot) or not is_instance_valid(_art):
		return
	for t: Tween in _attack_tweens:
		if is_instance_valid(t) and t.is_valid():
			t.kill()
	_attack_tweens.clear()
	# 连发时可能上一次还没落回，先归零再起新的一拍，避免越推越远
	_idle_pivot.rotation = 0.0
	_art.position = Vector2(0.0, _art_local_y)

	var t_pos := create_tween()
	t_pos.tween_property(_art, "position:x", ATTACK_LUNGE_X, ATTACK_OUT_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t_pos.tween_property(_art, "position:x", 0.0, ATTACK_BACK_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	var t_rot := create_tween()
	t_rot.tween_property(_idle_pivot, "rotation", ATTACK_LUNGE_ROT, ATTACK_OUT_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t_rot.tween_property(_idle_pivot, "rotation", 0.0, ATTACK_BACK_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	_attack_tweens.append(t_pos)
	_attack_tweens.append(t_rot)


## 待机微呼吸：整株上下轻浮动 + 极缓左右摆。
## [br]幅度刻意压得很小 —— 白衣长裙大幅晃动会显得飘，仙子要"稳"。
func _play_idle_motion() -> void:
	if not is_instance_valid(_idle_pivot):
		return
	if is_instance_valid(_idle_tween) and _idle_tween.is_valid():
		_idle_tween.kill()
	var base_pos: Vector2 = _idle_pivot.position
	var t := create_tween()
	t.set_loops()
	t.tween_property(_idle_pivot, "position", base_pos + Vector2(0.0, -1.6), 1.5) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	t.tween_property(_idle_pivot, "position", base_pos + Vector2(0.0, 0.4), 1.5) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_idle_tween = t
