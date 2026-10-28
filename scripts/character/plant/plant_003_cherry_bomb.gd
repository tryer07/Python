extends Plant000Base
class_name Plant003CherryBomb

## 樱桃炸弹「符咒双胞胎」：赤童（左，红）执符，青童（右，蓝）念咒。
## 引信分三段：抖符起手 → 念咒渐强 → 符咒烧尽即引爆。
##
## 引信期间刻意停在 AnimationTree 的 Start 状态（不播放任何动画轨道），
## 否则 idle/explode 里的 texture 轨道每帧都会把念咒换上的嘴型顶回第一帧。
## 烧尽时把 is_cast 置 false，状态机自己切到 explode，0.433 秒后由该动画的
## 方法轨道调用 bomb_once 与 character_death 结算，这里不重复触发爆炸。

## ── 并蒂樱童（樱桃炸弹）新形象开关 ──────────────────────────────────────
## true  = 用一整张 Q 版双胞胎立绘替换原版散件（left/right 身体 + 独立眼嘴）
## false = 恢复原版樱桃炸弹（散件一个都没删，只是被隐藏）
## [br]注意：整图立绘没有可分件的嘴，原版「逐帧换 rightmouth1~5」的念咒表演在整图下失效，
## 这里改成「蓄力膨胀 + 抖动 + 烧符染色」三段来演引信。多帧立绘 + 擦除式换帧是下一阶段。
@export var cherry_enable: bool = true

## 立绘母版 905×972，游戏里只显示 116 高，等于运行时缩到 0.13 倍，线稿会被采样糊成灰边。
## 离线先烘到「显示尺寸的 2 倍」（215×230），运行时只缩 0.5 倍 —— 与豆蔻／朝阳童子同一套做法。
## [br]2026-10-25：实心高度从 77.5 提到 108.5（+40%）。原来 155px 的实体是从 902px 母版
## 一次缩到 6.25 分之一的产物，衣服纹样和描边全被双线性采样抹平；这次索性从母版按
## 215px 实体重新烘（只缩 4.2 倍），再在最终尺寸上做一次 USM 锐化 + 局部对比，
## 所以「变大」和「变清楚」是同一件事，不是把旧图拉大。
const CHERRY_ART_PATH: String = "res://assets/image/character/cherry/cherry_idle_01.png"
## 显示高度：贴图 230 高 × 0.504 ≈ 116，其中实心部分 215 × 0.504 ≈ 108.5。
## 参考格子：行距 100 / 列距 80，108.5 仍在单行之内，不会窜到上一行去。
const CHERRY_HEIGHT: float = 116.0
## 2 倍空间下的下沿留白（贴图 230 高、实体底边在 219，剩 11），
## 取值 8 让实体底边落回放大前那个位置（离脚底支点 -1.5px），脚不会离地也不会陷进草皮
const CHERRY_PAD_PX: float = 8.0
## 原版散件在 BodyCorrect 局部坐标里的最低点与水平中心，由 .tscn 里 left3/right3 的
## position+scale 直接算出。新立绘以此为基座，脚底位置和原版完全一致。
const CHERRY_BASE_Y: float = 85.8
const CHERRY_CENTER_X: float = 39.25
## 烧符阶段整株染向的余烬色（不用额外贴图，只改 modulate）
const CHERRY_EMBER: Color = Color(1.0, 0.62, 0.42, 1.0)

## ── 待机动作（与豆蔻、朝阳童子同一套做法）──────────────────────────────
## 支点在脚底，所以摆动与呼吸都是「原地长/晃」，脚不会离地，也不会像浮空那样飘。
## 幅度对齐豆蔻（2.2° / 0.8px）再略收一点：这是一对肩背相抵的人，整体刚体倾斜，
## 角度给到豆蔻同量级就会读成「两个人一起要倒了」。
## [br]立绘从 84 放大到 116 后角度必须按比例收：1.4° 在 108px 实心高度上头顶横移约 2.6px，
## 与放大前（77.5px / 1.8° → 2.4px）几乎一样。角度不改的话，同一句「轻轻晃」
## 会变成「长高了也晃得更凶」，读起来像要倒。
const CHERRY_SWAY_DEG: float = 1.4
const CHERRY_SWAY_TIME: float = 1.7
## 呼吸同理：0.9px 是 77.5px 实心高度的 1.16%，放大后给 1.25px 保持同一相对幅度
const CHERRY_BREATH_PX: float = 1.25
const CHERRY_BREATH_TIME: float = 1.0

## ── 引爆表演（整图立绘模式）────────────────────────────────────────────
## 立绘是一整张「两人并肩」的图，两人之间没有留白，按列切会把衣服撕开，
## 所以不做「谁单独动」的骨骼拆解，改成在各自身上叠局部特效：
## 赤童（左）手里本来就画着一张符 → 在符的位置叠一层叠加发光的符，随燃烧自下而上烧尽；
## 青童（右）念咒 → 他头顶浮出「急急如律令」五个朱砂红字，一字一字显形。
## 两处特效在画面上左右分开，一眼就能读成「一边念、一边引」。
##
## 五个字是按「一个嘴型一步」显形的：CHANT_MOUTH 正好 5 档，0.85 秒念完，
## 每一步吐出下一个字。所以字不是随机冒，而是被嘴型逐字「说」出来的。
const CHERRY_CHANT_CHARS: Array[Texture2D] = [
	preload("res://assets/image/character/cherry/cherry_chant_char_1.png"),
	preload("res://assets/image/character/cherry/cherry_chant_char_2.png"),
	preload("res://assets/image/character/cherry/cherry_chant_char_3.png"),
	preload("res://assets/image/character/cherry/cherry_chant_char_4.png"),
	preload("res://assets/image/character/cherry/cherry_chant_char_5.png"),
]
const CHERRY_TALISMAN_TEX := preload("res://assets/image/character/cherry/cherry_talisman.png")
## 立绘贴图尺寸与中心点，用来把「贴图像素坐标」换算成 Sprite2D 的子节点坐标
## [br]⚠️ 换贴图尺寸时这三个特效锚点必须一起改，否则咒字会飘到脸上、发光符会烧到袖子：
## 旧图 157×168 的实心框是 (19,4)-(153,159)，新图 215×230 是 (25,4)-(211,219)，
## 换算关系 new = old × 1.387 − 1.4（横向）/ − 1.55（纵向）。下面四个常量都是这么推出来的。
const CHERRY_ART_W: float = 215.0
const CHERRY_ART_H: float = 230.0
## 「急急如律令」整条的横向排布（贴图像素）：五字等距横排、浮在两人头顶上方。
## 立绘 215×230，头顶在 y=4，整条压到 y=-21 的空白里（离头顶 25 贴图像素，与放大前同比例），不遮脸。
## 单字贴图 64px，屏幕上 64 × 0.694 × 0.504 ≈ 22.4px；横向步距 41.6 贴图像素 ≈ 20.9px，
## 字与字仍重叠 1.5px —— 这条必须「连起来读成一句话」，留缝就散了。
const CHERRY_CHAR_Y: float = -21.0
const CHERRY_CHAR_STEP: float = 41.6
const CHERRY_CHAR_SCALE: float = 0.694
## 单字显形时的「弹一下」：从 1.45 倍收到 1 倍
const CHERRY_CHAR_POP: float = 1.45
const CHERRY_CHAR_POP_TIME: float = 0.11
## 赤童手里那张符的中点与倾角（贴图像素），叠加的发光符要盖在它上面。
## 数值是拿立绘放大到 12 倍、打网格量出来的：符从 (16,63) 斜到 (37,86)。
## [br]换 215×230 的贴图后按 new = old × 1.387 − 1.4 换算，中点落在 (35.4, 101.8)；
## 倾角是角度量，不跟着缩放走，-0.74 原样保留。
const CHERRY_TALISMAN_PX := Vector2(35.4, 101.8)
const CHERRY_TALISMAN_ROT: float = -0.74
## 发光符放大到 2.5 倍：原尺寸（14×32）只堪堪盖住纸上那张符，屏幕上不过 7×16px，
## 火线在这个尺寸下永远是「一个像素的亮」，怎么调 shader 都读不出来。
## 立绘放大 1.4 倍后，纸上那张符也跟着变大了，覆盖层必须同比放大：
## 1.8 × 1.387 ≈ 2.5，屏幕上约 17.6×40.3px，火舌才有地方铺开。
const CHERRY_TALISMAN_SCALE: float = 2.5
## 引爆瞬间白闪的残影时长
const CHERRY_FLASH_TIME: float = 0.12

const TALISMAN_BURN_SHADER := preload("res://resources/shader/talisman_burn.gdshader")
## 叠加发光版：整图立绘里赤童手上已经画着一张符，只能用「加光」去点亮它，
## 用实心符纸盖上去会变成两张符。
const TALISMAN_BURN_ADD_SHADER := preload("res://resources/shader/talisman_burn_add.gdshader")

## 念咒时青童的嘴型，由小到大：最后一帧是张大嘴
const CHANT_MOUTH: Array[Texture2D] = [
	preload("res://assets/reanim/CherryBomb_rightmouth1.png"),
	preload("res://assets/reanim/CherryBomb_rightmouth2.png"),
	preload("res://assets/reanim/CherryBomb_rightmouth3.png"),
	preload("res://assets/reanim/CherryBomb_rightmouth4.png"),
	preload("res://assets/reanim/CherryBomb_rightmouth5.png"),
]
## 念咒时青童的两只眼睛，同样由小到大
const CHANT_EYE_LEFT: Array[Texture2D] = [
	preload("res://assets/reanim/CherryBomb_righteye11.png"),
	preload("res://assets/reanim/CherryBomb_righteye12.png"),
	preload("res://assets/reanim/CherryBomb_righteye13.png"),
	preload("res://assets/reanim/CherryBomb_righteye14.png"),
	preload("res://assets/reanim/CherryBomb_righteye15.png"),
]
const CHANT_EYE_RIGHT: Array[Texture2D] = [
	preload("res://assets/reanim/CherryBomb_righteye21.png"),
	preload("res://assets/reanim/CherryBomb_righteye22.png"),
	preload("res://assets/reanim/CherryBomb_righteye23.png"),
	preload("res://assets/reanim/CherryBomb_righteye24.png"),
	preload("res://assets/reanim/CherryBomb_righteye25.png"),
]

## 落地后到起手的停顿
const FUSE_DELAY := 0.10
## 念咒渐强用时
const CHANT_TIME := 0.85
## 符咒从符脚烧到符头用时，烧尽即引爆。
## 0.26 → 0.40：0.26 秒只有 6 帧（24fps 的 GIF 里 3 帧），火线刚看清就没了，
## 而「烧」恰恰是这套表演里最需要被读到的一段，宁可让引信整体慢半拍。
const BURN_TIME := 0.40
## 蓄力末段身体最多胀大多少
const SWELL_MAX := 0.10
## 口边符文的生成间隔与飘升高度
const GLYPH_INTERVAL := 0.24
const GLYPH_RISE := 20.0
const GLYPH_LIFE := 0.55

@onready var bomb_component: BombComponentBase = %BombComponent
@onready var _body_correct: Node2D = $Body/BodyCorrect
@onready var _mouth: Sprite2D = $Body/BodyCorrect/CherryBomb_rightmouth1
@onready var _eye_left: Sprite2D = $Body/BodyCorrect/CherryBomb_righteye11
@onready var _eye_right: Sprite2D = $Body/BodyCorrect/CherryBomb_righteye21
@onready var _talisman: Sprite2D = $Body/BodyCorrect/Talisman
@onready var _glyphs: Array[Sprite2D] = [
	$Body/BodyCorrect/ChantGlyph1,
	$Body/BodyCorrect/ChantGlyph2,
	$Body/BodyCorrect/ChantGlyph3,
]

## 引信是否还在跑；为 false 时状态机才会切到 explode
@export var is_cast := false

## 符咒材质与起手时的初始位姿
var _talisman_material: ShaderMaterial
var _talisman_rest := Vector2.ZERO
var _fuse_tween: Tween
var _glyph_tween: Tween
var _glyph_cursor := 0

## 整图立绘与它的支点。支点单独一层，是为了让蓄力膨胀/抖动只作用于立绘，
## 不去改 BodyCorrect —— 那个节点被 AnimationTree 盯着，改它会被状态机顶回去。
## [br]节点层次：Body → CherryIdlePivot（待机摆动）→ CherryArtPivot（引信膨胀/抖动）→ 立绘。
## 两层分开是必须的：引信期间 `_set_swell` 每帧写 ArtPivot 的 scale/position，
## 待机呼吸写的是立绘自己的 position.y，两者不抢同一个属性，叠在一起才有「一边喘一边胀」。
var _art: Sprite2D = null
var _idle_pivot: Node2D = null
var _art_pivot: Node2D = null
var _art_scale: float = 0.5
var _art_local_y: float = 0.0
var _art_pivot_base: Vector2 = Vector2.ZERO

## 立绘原始贴图，白闪残影要复用同一张剪影
var _art_tex: Texture2D = null
## 引爆瞬间盖在立绘上的白色叠加剪影
var _flash: Sprite2D = null
## 盖在赤童手里那张符上的叠加发光符；随燃烧自下而上烧空
var _talisman_glow: Sprite2D = null
## 青童口边的三个「咒」字，轮转发出去（游标沿用上面的 _glyph_cursor）
var _glyph_fx: Array[Sprite2D] = []
var _glyph_loop: Tween = null
var _talisman_tween: Tween = null

## 亡语
func death_language():
	print("[樱桃] 死亡 %d" % Time.get_ticks_msec())
	bomb_component.judge_death_bomb()


## 换装入口只挂在 `_ready` 上，与豆蔻／朝阳童子一致。
## [br]为什么不再分 `ready_norm` / `ready_show` / `ready_garden` 三处去调：
## `character_000_base._ready()` 按 `character_init_type` 分派这三条路径，
## 之前只挂了 ready_norm，结果图鉴详情页（IsShow）里一直是原版散件。
## 在分派之后统一换装，任何初始化类型都不会漏。
func _ready() -> void:
	super()
	if cherry_enable:
		_apply_cherry_art()
		# 爆炸结算（bomb_once）那一刻把立绘换成一道白光：伤害结算与火海生成都在同一帧，
		# 所以闪白挂在 bomb_once 的信号上，而不是跟随爆炸动画的时间轴。
		bomb_component.signal_bomb_once.connect(_on_bomb_once)


func ready_norm() -> void:
	super()
	is_cast = true
	_setup_talisman()
	## 等这一帧的节点初始化走完再挂引信，避免在 _ready 里直接改子节点
	_start_fuse.call_deferred()


## 隐藏散件版身体，换成整图立绘。
## 不改 .tscn 结构，全部在运行期完成，回退只需把 cherry_enable 置 false。
## [br]挂到 Body（BodyCorrect 的父节点）而不是 BodyCorrect 下：状态机停在 Start 时
## 会把 BodyCorrect 的子精灵重置成 visible=false / scale≈0，挂进去的立绘会被一起吃掉。
func _apply_cherry_art() -> void:
	# 幂等：三条初始化路径已经收口到 _ready，但换装可能被外部重入，第二次直接跳过
	if is_instance_valid(_art):
		return
	var body_correct: Node2D = get_node_or_null("Body/BodyCorrect") as Node2D
	if body_correct == null:
		body_correct = find_child("BodyCorrect", true, false) as Node2D
	if body_correct == null:
		push_warning("并蒂樱童：找不到 BodyCorrect，跳过换装")
		return

	var tex: Texture2D = load(CHERRY_ART_PATH) as Texture2D
	if tex == null:
		push_warning("并蒂樱童：贴图没找到或还没被导入 → %s" % CHERRY_ART_PATH)
		return

	# 1) 原散件整体隐藏（两棵树身 + 全部眼睛嘴巴 + 叶子）
	body_correct.visible = false

	# 2) 两层支点都落在「脚底」而不是 BodyCorrect 的原点上：
	#    蓄力膨胀与待机摆动都是绕支点变形/旋转的，支点在脚底才是「从地里往上长 + 原地晃」，
	#    支点在头顶就会往地里沉、像被吊着晃。
	#    - CherryIdlePivot：只负责待机摆动（rotation），引信全程都在跑
	#    - CherryArtPivot ：只负责引信膨胀/抖动，由 `_set_swell` 每帧写
	var foot: Vector2 = body_correct.position + Vector2(CHERRY_CENTER_X, CHERRY_BASE_Y)
	_idle_pivot = Node2D.new()
	_idle_pivot.name = "CherryIdlePivot"
	_idle_pivot.position = foot
	body_correct.get_parent().add_child(_idle_pivot)

	_art_pivot = Node2D.new()
	_art_pivot.name = "CherryArtPivot"
	_art_pivot_base = Vector2.ZERO
	_idle_pivot.add_child(_art_pivot)

	# 3) 立绘：居中贴图，中心上移半个身高，实体底边正好落在支点上
	_art_tex = tex
	_art_scale = CHERRY_HEIGHT / float(tex.get_height())
	_art_local_y = -CHERRY_HEIGHT * 0.5 + CHERRY_PAD_PX * _art_scale
	_art = Sprite2D.new()
	_art.name = "CherryArt"
	_art.texture = tex
	_art.scale = Vector2(_art_scale, _art_scale)
	_art.position = Vector2(0.0, _art_local_y)
	_art_pivot.add_child(_art)

	# 4) 引信/引爆的局部特效（咒字、发光符、白闪），全部挂在立绘上跟着身体一起缩放
	_build_detonate_fx()

	_play_idle_motion()


## 待机动作：绕脚底左右轻摆 + 呼吸起伏。
## [br]与豆蔻同一套：摆动放在支点的 rotation 上，呼吸改立绘自己的 position.y。
## 这两个属性引信都不碰（引信写的是 ArtPivot 的 scale/position），所以引信期间
## 「一边喘一边胀」不会互相打断，也不需要专门去 kill 待机 Tween。
## [br]用 SINE + EASE_IN_OUT：两个端点速度都是 0，循环接缝处看不出来。
func _play_idle_motion() -> void:
	var sway: Tween = create_tween().set_loops()
	sway.tween_property(_idle_pivot, ^"rotation", deg_to_rad(CHERRY_SWAY_DEG), CHERRY_SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	sway.tween_property(_idle_pivot, ^"rotation", deg_to_rad(-CHERRY_SWAY_DEG), CHERRY_SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	var breath: Tween = create_tween().set_loops()
	breath.tween_property(_art, ^"position:y", _art_local_y - CHERRY_BREATH_PX, CHERRY_BREATH_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	breath.tween_property(_art, ^"position:y", _art_local_y, CHERRY_BREATH_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


## 符咒：材质换成燃烧着色器，初始收起
## [br]整图立绘里赤童手上已经画着那张符了，再叠一张独立符就是「两张符」，
## 所以换装后这个节点全程保持隐藏，只保留原版散件的走法。
func _setup_talisman() -> void:
	_talisman.visible = false
	for glyph in _glyphs:
		glyph.visible = false
	if cherry_enable:
		return
	_talisman_rest = _talisman.position
	_talisman_material = ShaderMaterial.new()
	_talisman_material.shader = TALISMAN_BURN_SHADER
	_talisman.material = _talisman_material
	_talisman.scale = Vector2(0.2, 0.2)

## 引信时间轴：停顿 → 起手 → 念咒渐强 → 烧符 → 交棒给爆炸动画
func _start_fuse() -> void:
	if not is_inside_tree() or is_death or is_queued_for_deletion():
		return
	_fuse_tween = create_tween()
	_fuse_tween.tween_interval(FUSE_DELAY)
	_fuse_tween.tween_callback(_on_cast_begin)
	_fuse_tween.tween_method(_set_chant_step, 0.0, float(CHANT_MOUTH.size() - 1), CHANT_TIME)
	_fuse_tween.tween_callback(_on_burn_begin)
	_fuse_tween.tween_method(_set_burn, 0.0, 1.0, BURN_TIME)
	_fuse_tween.tween_callback(_detonate)
	## 蓄力抖动与膨胀贯穿整段引信，越到后面越明显
	var swell := create_tween()
	swell.tween_method(_set_swell, 0.0, 1.0, FUSE_DELAY + CHANT_TIME + BURN_TIME)

## 起手：符咒自袖中弹出、悬空自转，青童开始念咒
## [br]整图立绘下这一整套「独立符 + 口边符文」都不再需要 —— 符已经画在赤童手里，
## 表演交给 _set_swell 的膨胀抖动和 _set_burn 的染色。
func _on_cast_begin() -> void:
	print("[樱桃] 起手 %d" % Time.get_ticks_msec())
	if cherry_enable:
		## 整图：青童吐咒字、赤童手里的符开始发亮，身体交给 _set_swell 慢慢鼓起来
		_begin_chant_fx()
		return
	_talisman.visible = true
	_talisman.scale = Vector2(0.2, 0.2)
	_talisman.rotation = -0.5
	var pop := create_tween().set_parallel(true)
	pop.tween_property(_talisman, ^"scale", Vector2.ONE, 0.22) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	pop.tween_property(_talisman, ^"rotation", 0.0, 0.22).set_ease(Tween.EASE_OUT)
	## 悬空自转：左右小幅摇摆，像被气机托着
	var sway := create_tween().set_loops()
	sway.tween_property(_talisman, ^"rotation", 0.20, 0.42).set_trans(Tween.TRANS_SINE)
	sway.tween_property(_talisman, ^"rotation", -0.20, 0.42).set_trans(Tween.TRANS_SINE)
	var bob := create_tween().set_loops()
	bob.tween_property(_talisman, ^"position:y", _talisman_rest.y - 2.0, 0.5).set_trans(Tween.TRANS_SINE)
	bob.tween_property(_talisman, ^"position:y", _talisman_rest.y, 0.5).set_trans(Tween.TRANS_SINE)
	_start_chant_glyphs()

## 口边符文：轮转发出一枚「咒」，边升边淡出
func _start_chant_glyphs() -> void:
	_glyph_tween = create_tween().set_loops()
	_glyph_tween.tween_callback(_emit_glyph)
	_glyph_tween.tween_interval(GLYPH_INTERVAL)

func _emit_glyph() -> void:
	if _glyphs.is_empty():
		return
	var glyph := _glyphs[_glyph_cursor % _glyphs.size()]
	_glyph_cursor += 1
	glyph.visible = true
	glyph.position = _mouth.position + Vector2(randf_range(-2.0, 4.0), 2.0)
	glyph.modulate = Color(1.0, 0.85, 0.6, 0.0)
	glyph.scale = Vector2(0.7, 0.7)
	var rise := create_tween().set_parallel(true)
	rise.tween_property(glyph, ^"position:y", glyph.position.y - GLYPH_RISE, GLYPH_LIFE) \
		.set_ease(Tween.EASE_OUT)
	rise.tween_property(glyph, ^"scale", Vector2(1.15, 1.15), GLYPH_LIFE).set_ease(Tween.EASE_OUT)
	rise.tween_property(glyph, ^"modulate:a", 0.0, GLYPH_LIFE).set_ease(Tween.EASE_IN)
	rise.chain().tween_callback(func() -> void: glyph.visible = false)

## 念咒渐强：按进度换嘴型与眼型，最后一档是张大嘴
func _set_chant_step(value: float) -> void:
	var idx := clampi(roundi(value), 0, CHANT_MOUTH.size() - 1)
	_mouth.texture = CHANT_MOUTH[idx]
	_eye_left.texture = CHANT_EYE_LEFT[idx]
	_eye_right.texture = CHANT_EYE_RIGHT[idx]

## 蓄力：身体轻微膨胀 + 越来越快的抖动
## [br]换整图后作用于立绘支点（支点在脚底），而不是 BodyCorrect ——
## BodyCorrect 的属性被 AnimationTree 的 Start 状态盯着，改完下一帧就被顶回去。
func _set_swell(value: float) -> void:
	var amp := value * value * 1.6
	if cherry_enable:
		if not is_instance_valid(_art_pivot):
			return
		_art_pivot.scale = Vector2.ONE * (1.0 + SWELL_MAX * value)
		_art_pivot.position = _art_pivot_base + Vector2(sin(value * 61.0) * amp, cos(value * 49.0) * amp)
		return
	if not is_instance_valid(_body_correct):
		return
	_body_correct.scale = Vector2.ONE * (1.0 + SWELL_MAX * value)
	_body_correct.position = Vector2(sin(value * 61.0) * amp, cos(value * 49.0) * amp)

## 咒成符燃：符纸被点着的一下顿挫，让「烧」有起点
func _on_burn_begin() -> void:
	print("[樱桃] 烧符 %d" % Time.get_ticks_msec())
	if cherry_enable:
		## 咒念完了：五个字凑齐后整条一起淡掉，再去点符 ——
		## 顺序反了会变成「一边烧符一边还在念」，看起来像两件事各说各的。
		_fade_chant_chars(0.14)
		_ignite_talisman_fx()
		## 整图下没有独立符纸可顿挫，整株再「顶一下」，读起来仍是「火起手」
		if not is_instance_valid(_art_pivot):
			return
		var kick := create_tween()
		kick.tween_property(_art_pivot, ^"scale", Vector2.ONE * 1.06, 0.05)
		kick.tween_property(_art_pivot, ^"scale", Vector2.ONE, 0.12)
		return
	if not is_instance_valid(_talisman):
		return
	var lit := create_tween()
	lit.tween_property(_talisman, ^"scale", Vector2(1.12, 1.12), 0.05)
	lit.tween_property(_talisman, ^"scale", Vector2.ONE, 0.12)

## 烧符：符脚往上烧，同时余烬越来越亮
## [br]整图把「符纸烧尽」折算成整株染色：从本色推到余烬色，越接近引爆越亮。
func _set_burn(value: float) -> void:
	if cherry_enable:
		_burn_talisman_fx(value)
		if is_instance_valid(_art):
			_art.self_modulate = Color(1.0, 1.0, 1.0, 1.0).lerp(CHERRY_EMBER, value * value)
		return
	if not is_instance_valid(_talisman_material):
		return
	_talisman_material.set_shader_parameter(&"burn", value)
	_talisman_material.set_shader_parameter(&"ember_strength", value * value)

## 烧尽：撤掉蓄力形变，把控制权交给 explode 动画
func _detonate() -> void:
	print("[樱桃] 引爆 %d" % Time.get_ticks_msec())
	is_cast = false
	_talisman.visible = false
	if is_instance_valid(_glyph_tween):
		_glyph_tween.kill()
	for glyph in _glyphs:
		glyph.visible = false
	if is_instance_valid(_art_pivot):
		_art_pivot.scale = Vector2.ONE
		_art_pivot.position = _art_pivot_base
	if is_instance_valid(_body_correct):
		_body_correct.scale = Vector2.ONE
		_body_correct.position = Vector2.ZERO
	if not cherry_enable:
		return
	## 整图：符已烧尽，人还在。爆炸动画（0.433 秒）播完才真正结算，
	## 这段空档用「全身越来越白」填住，否则会看到 Twins 站着不动硬等 0.4 秒。
	if is_instance_valid(_glyph_loop):
		_glyph_loop.kill()
	for glyph: Sprite2D in _glyph_fx:
		glyph.visible = false
	if is_instance_valid(_talisman_glow):
		_talisman_glow.visible = false
	if is_instance_valid(_art):
		_art.self_modulate = Color(1.0, 1.0, 1.0, 1.0)
	if not is_instance_valid(_flash):
		return
	_flash.visible = true
	_flash.modulate = Color(1.0, 0.96, 0.86, 0.0)
	var heat: Tween = create_tween()
	heat.tween_property(_flash, ^"modulate:a", 0.18, 0.10)
	heat.tween_property(_flash, ^"modulate:a", 0.5, 0.30)


#region 整图立绘：念咒 / 引符 / 引爆的局部特效
## 把「贴图像素坐标」换成挂在立绘下面的子节点坐标。
## [br]立绘 Sprite2D 默认居中，所以子节点的原点就是贴图中心。
func _art_px(pixel: Vector2) -> Vector2:
	return pixel - Vector2(CHERRY_ART_W * 0.5, CHERRY_ART_H * 0.5)


## 叠加发光用的材质。ADD 混合让特效只「加亮」不改底色，不会把立绘盖成一块色斑。
func _make_add_material() -> CanvasItemMaterial:
	var material := CanvasItemMaterial.new()
	material.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	return material


## 建三组特效：
## 1) 白闪剪影挂在立绘支点上（不挂在立绘下面，免得跟着余烬染色一起变暗）
## 2) 发光符与咒字挂在立绘下面，跟着身体膨胀/抖动一起动
func _build_detonate_fx() -> void:
	if not is_instance_valid(_art) or _art_tex == null:
		return

	# 白闪：和立绘同尺寸同位置的白色剪影，平时 alpha 为 0
	_flash = Sprite2D.new()
	_flash.name = "CherryFlash"
	_flash.texture = _art_tex
	_flash.material = _make_add_material()
	_flash.position = Vector2(0.0, _art_local_y)
	_flash.scale = Vector2(_art_scale, _art_scale)
	_flash.modulate = Color(1.0, 0.96, 0.86, 0.0)
	_flash.visible = false
	_art_pivot.add_child(_flash)

	# 发光符：盖在赤童手里那张符上，随 burn 自下而上烧空
	_talisman_glow = Sprite2D.new()
	_talisman_glow.name = "CherryTalismanGlow"
	_talisman_glow.texture = CHERRY_TALISMAN_TEX
	_talisman_glow.material = _make_add_material()
	_talisman_glow.position = _art_px(CHERRY_TALISMAN_PX)
	_talisman_glow.rotation = CHERRY_TALISMAN_ROT
	_talisman_glow.scale = Vector2(CHERRY_TALISMAN_SCALE, CHERRY_TALISMAN_SCALE)
	_talisman_glow.modulate = Color(1.0, 0.72, 0.34, 0.0)
	_talisman_glow.visible = false
	_art.add_child(_talisman_glow)

	# 「急急如律令」五个字：位置固定、横排在头顶，靠 opacity 逐字显形。
	# 不做「升空飘散」——五个字要能连起来读成一句话，一飘就散了。
	# [br]这里**不能**像符纸辉光那样用 ADD：叠加混色下「红 + 绿草皮」= 黄，
	# 朱砂红会被底下草坪加成土黄，用户要的红就没了。正片叠底才能留住红。
	for i: int in CHERRY_CHANT_CHARS.size():
		var glyph := Sprite2D.new()
		glyph.name = "CherryChantChar%d" % (i + 1)
		glyph.texture = CHERRY_CHANT_CHARS[i]
		# 字色已经烘在贴图里（朱砂红），这里只控制透明度，别再乘一次色
		glyph.modulate = Color(1.0, 1.0, 1.0, 0.0)
		glyph.position = _art_px(Vector2(
			CHERRY_ART_W * 0.5 + (float(i) - 2.0) * CHERRY_CHAR_STEP, CHERRY_CHAR_Y))
		glyph.scale = Vector2(CHERRY_CHAR_SCALE, CHERRY_CHAR_SCALE)
		glyph.visible = false
		_art.add_child(glyph)
		_glyph_fx.append(glyph)


## 起手：青童开始吐咒字，赤童手里的符开始发亮
func _begin_chant_fx() -> void:
	if _glyph_fx.is_empty():
		return
	if is_instance_valid(_glyph_loop):
		_glyph_loop.kill()
	# 念多久就吐几个字：CHANT_MOUTH 是 5 档嘴型，五个字正好一步一个字，
	# 念完「令」的下一拍就去点符 —— 所以这里不用循环，数满就停。
	_glyph_loop = create_tween()
	var step: float = CHANT_TIME / float(_glyph_fx.size())
	_glyph_cursor = 0
	for i: int in _glyph_fx.size():
		_glyph_loop.tween_callback(_emit_chant_glyph)
		_glyph_loop.tween_interval(step)

	if not is_instance_valid(_talisman_glow):
		return
	_talisman_glow.visible = true
	if is_instance_valid(_talisman_tween):
		_talisman_tween.kill()
	# 念咒这一段：符从暗到亮，亮度跟着符咒一起「蓄」
	_talisman_tween = create_tween()
	_talisman_tween.tween_property(
		_talisman_glow, ^"modulate:a", 0.62, CHANT_TIME * 0.85
	).set_ease(Tween.EASE_IN)


## 显形第 N 个朱砂字：一记「弹一下」的缩放 + 淡入，然后一直留着，
## 五个字凑齐就是完整的「急急如律令」，等点火时整条一起撤掉。
func _emit_chant_glyph() -> void:
	if _glyph_fx.is_empty():
		return
	var glyph: Sprite2D = _glyph_fx[_glyph_cursor % _glyph_fx.size()]
	_glyph_cursor += 1
	glyph.visible = true
	glyph.scale = Vector2(CHERRY_CHAR_SCALE, CHERRY_CHAR_SCALE) * CHERRY_CHAR_POP
	glyph.modulate = Color(1.0, 1.0, 1.0, 0.0)
	var pop: Tween = create_tween().set_parallel(true)
	pop.tween_property(glyph, ^"modulate:a", 1.0, CHERRY_CHAR_POP_TIME).set_ease(Tween.EASE_OUT)
	pop.tween_property(
		glyph, ^"scale", Vector2(CHERRY_CHAR_SCALE, CHERRY_CHAR_SCALE), CHERRY_CHAR_POP_TIME
	).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


## 整条咒语一起淡掉（点火 / 引爆那一下用）
func _fade_chant_chars(duration: float) -> void:
	if is_instance_valid(_glyph_loop):
		_glyph_loop.kill()
	for glyph: Sprite2D in _glyph_fx:
		if not glyph.visible:
			continue
		var out: Tween = create_tween()
		out.tween_property(glyph, ^"modulate:a", 0.0, duration)
		out.tween_callback(func() -> void: glyph.visible = false)


## 点火：符纸整体「爆亮」一下（白闪）→ 回落成余烬暖色 → 烧到符头再成炽白。
## [br]以前只有 0.05 秒的透明度爬升 + 1.5 倍缩放，颜色一直停在暖黄，
## 点着和没点着在画面上几乎没有区别，这次把亮度做成「先冲顶、再回落」的顿挫。
func _ignite_talisman_fx() -> void:
	if not is_instance_valid(_talisman_glow):
		return
	if is_instance_valid(_talisman_tween):
		_talisman_tween.kill()
	var base := Vector2(CHERRY_TALISMAN_SCALE, CHERRY_TALISMAN_SCALE)
	_talisman_glow.visible = true
	_talisman_glow.scale = base
	_talisman_glow.modulate = Color(1.0, 0.86, 0.52, 0.62)
	_talisman_tween = create_tween()
	# 第一下：白闪冲顶，同时整张符「涨」出去一截，读作「点着了」。
	# 0.07s 而不是 0.05s：24fps 的 GIF 里 0.05 秒还不到两帧，一闪就没了
	_talisman_tween.tween_property(
		_talisman_glow, ^"modulate", Color(1.0, 1.0, 1.0, 1.0), 0.07
	).set_ease(Tween.EASE_OUT)
	_talisman_tween.parallel().tween_property(
		_talisman_glow, ^"scale", base * 1.4, 0.07
	).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	# 第二下：亮度落回暖橙（火苗本色），符纸稍微收一点，火才开始往上爬。
	# 别落太暗 —— 落成 0.74 时中段整片比点火前还暗，看起来像火灭了
	_talisman_tween.tween_property(
		_talisman_glow, ^"modulate", Color(1.0, 0.86, 0.55, 1.0), 0.11
	)
	_talisman_tween.parallel().tween_property(_talisman_glow, ^"scale", base * 1.12, 0.14)
	# 第三下：烧到符头时整张符成一道炽白，接上引爆。
	# 三段加起来必须正好等于 BURN_TIME —— 原来最后一段拖到 0.31 秒才转白，
	# 那时符纸早被 shader 烧没了，白得再亮也没纸可亮，等于白烧一场。
	_talisman_tween.tween_property(
		_talisman_glow, ^"modulate", Color(1.0, 0.98, 0.9, 1.0), BURN_TIME - 0.18
	)


## 符纸自下而上烧空：复用散件那套 burning shader，只换参数
## [br]ember_strength 提前拉满（value × 2.2）：烧线只有 0.26 秒就推进完，
## 若跟着 value 线性爬，最亮的一刻永远落在符已经烧没之后，白烧了一场。
func _burn_talisman_fx(value: float) -> void:
	if not is_instance_valid(_talisman_glow):
		return
	if _talisman_material == null:
		_talisman_material = ShaderMaterial.new()
		_talisman_material.shader = TALISMAN_BURN_ADD_SHADER
		# 叠加混合下 shader 输出的是发光量：余烬压成偏橙的红，
		# 火芯给到近白，两者插值后火线才有一圈真正「热」的白边。
		_talisman_material.set_shader_parameter(&"ember_color", Color(1.0, 0.58, 0.24, 1.0))
		_talisman_material.set_shader_parameter(&"core_color", Color(1.0, 0.97, 0.86, 1.0))
		# 火线厚度：贴图只有 14×32，0.18 UV ≈ 6px。
		# 给到 0.42 时整张纸的 41% 都算「火线」，中段会糊成一块纯白，看不出在推进
		_talisman_material.set_shader_parameter(&"edge_width", 0.18)
		_talisman_material.set_shader_parameter(&"flicker", 0.5)
		_talisman_glow.material = _talisman_material
	_talisman_material.set_shader_parameter(&"burn", value)
	_talisman_material.set_shader_parameter(&"ember_strength", minf(1.0, value * 2.2))


## bomb_once 那一帧：立绘换成一道白光，交给三行三列火海
func _on_bomb_once() -> void:
	if not cherry_enable:
		return
	if is_instance_valid(_glyph_loop):
		_glyph_loop.kill()
	for glyph: Sprite2D in _glyph_fx:
		glyph.visible = false
	if is_instance_valid(_talisman_glow):
		_talisman_glow.visible = false
	if is_instance_valid(_art):
		_art.visible = false
	if not is_instance_valid(_flash):
		return
	_flash.visible = true
	_flash.modulate = Color(1.0, 0.96, 0.86, 1.0)
	# 植物本身会在这一帧之后被销毁，Tween 可能跑不完；
	# 跑不完也无所谓，火海已经接管画面，闪白跟着节点一起消失即可。
	var fade: Tween = create_tween()
	fade.tween_property(_flash, ^"modulate:a", 0.0, CHERRY_FLASH_TIME)
	fade.tween_callback(func() -> void: _flash.visible = false)
#endregion
