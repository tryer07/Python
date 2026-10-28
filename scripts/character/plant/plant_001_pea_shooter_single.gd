extends Plant000Base
class_name Plant001PeaShooterSingle

## 豆蔻（豌豆射手）新形象开关
## true  = 用一整张 Q 版人形立绘替换原来的 14 个散件
## false = 恢复原版豌豆射手（原散件一个都没删，只是被隐藏）
@export var douku_enable: bool = true

## ── 立绘为什么要「预先烘焙」──────────────────────────────────────────────
## 母版是 165×280，游戏里只显示 45×76，等于运行时把贴图缩到 0.271 倍。
## 而 .import 里 mipmaps/generate=false + 线性过滤，缩小全靠 GPU 双线性取样：
## 线稿被采样成灰糊，待机摇摆和出镖时身体还在转，边缘会一路爬行闪烁。
## 所以改成离线先 Lanczos 缩到「显示尺寸的 2 倍」再锐化，运行时只需 0.5 倍，
## 既保住线稿，也让旋转采样稳定。
##
## 另一处是辨识度：豆蔻是浅豆绿长袍，草坪也是绿，45 像素下轮廓直接糊进背景。
## PVZ 原版植物本身就带深色描边，所以这里补一圈 2 倍空间的深绿描边（显示时约 1 像素），
## 属于「往原版美术语言上靠」，不是额外加装饰。
const DOUKU_ART_PATH: String = "res://assets/image/character/douku/douku_idle_03.png"
## 闭眼帧；文件存在才会启用眨眼，缺图时静默跳过
const DOUKU_BLINK_PATH: String = "res://assets/image/character/douku/douku_blink_03.png"

## ── 尺寸 ────────────────────────────────────────────────────────────────
## 画布显示高度：原 79 → 103（+30.4%），人物本体 76 → 99。
## 贴图是「显示尺寸的 2 倍」烘出来的（125×206），运行时刚好 0.5 倍，线稿不糊。
const DOUKU_HEIGHT: float = 103.0
## 上面那套坐标常量都是按 79 高度量出来的。改高度时不用重算一堆像素，
## 统一乘 _art_k 换算到当前尺寸 —— 见 _apply_douku_art()。
const DOUKU_HEIGHT_REF: float = 79.0
## 2 倍空间里脚底到画布底边的留白，用来把脚底精确对回 y=0
const DOUKU_FOOT_PAD_PX: float = 4.0
## 待机左右摇摆的幅度（度）与单程时长（秒）
const DOUKU_SWAY_DEG: float = 2.2
const DOUKU_SWAY_TIME: float = 1.7
## 呼吸起伏幅度（像素）
const DOUKU_BREATH_PX: float = 0.8

# ══════════════════════════════════════════════════════════════════════════
# 出镖动作
# ──────────────────────────────────────────────────────────────────────────
# 关键约束：豆蔻是一张整图，没有手臂骨骼。第一版想靠「身体前倾 13 度」做出甩的动作，
# 结果整图绕脚底转，头顶（距脚底 65）走了 15 像素、手上（距脚底 37）只走 8 像素，
# 眼睛看到的其实是「整个人往前一探」——和仙人掌吐刺一个观感，方向从一开始就错了。
#
# 现在的分工（一整套：握镖待命 → 翻腕蓄力 → 甩出 → 空手 → 袖口抽下一支）：
#   · 身体只做 9 度的急促前送，单纯当「发力」的暗示，不承担「甩」；
#   · 「甩」全部交给手里那支镖：先翻腕把镖尖压到肩后（-70 → -92 度），
#     再一口气翻到 +14 度甩出去，106 度的翻转才是「腕部发力」的观感；
#   · 甩出的终点按子弹速度算：300 px/s × 0.075 秒 = 22.5 像素，
#     所以从子弹出生点 (20.6,-42.2) 往前 22 像素收尾，镖一淡出子弹就在同一位置接棒。
#     第一版甩到 x=62 才消失、子弹却从 x=20 凭空出现，等于倒跳 40 像素，这条必须对齐；
#   · 下一支镖从「举起来那只手」的宽袖口抽出来，袖口同时闪一下光点做交代。
# ══════════════════════════════════════════════════════════════════════════

## 出镖时身体前送的倾角（度）与横向前顶（像素）
## 刻意压小：大了就变成整身鞠躬，正是「吐刺」感的来源
const DOUKU_THROW_DEG: float = 9.0
const DOUKU_THROW_PUSH: float = 2.8
## 出手前送 / 回弹① / 回弹② / 归位时长（秒）
const DOUKU_THROW_HIT_TIME: float = 0.05
const DOUKU_THROW_BACK_TIME: float = 0.11
const DOUKU_THROW_SETTLE_TIME: float = 0.10
const DOUKU_THROW_RESTORE_TIME: float = 0.14
## 挤压拉伸：甩出去时横向拉长、竖向压扁（脚底不动），回弹时反过来，做出重量感
const DOUKU_THROW_STRETCH: Vector2 = Vector2(1.05, 0.96)
const DOUKU_THROW_RECOIL_SCALE: Vector2 = Vector2(0.98, 1.02)
## 回弹时的反向过冲角度（度）与后坐位移（像素）
const DOUKU_THROW_OVERSHOOT_DEG: float = -2.6
## 第二次过冲：幅度只剩三成，但必须有——少了这一下，回正就变成「被按回去」
const DOUKU_THROW_OVERSHOOT2_DEG: float = 1.2
const DOUKU_THROW_BACK_PUSH: float = -0.55

## 出手前的蓄力：身体往后微坐（反作用力预压），手跟着收到肩后
const DOUKU_WINDUP_DEG: float = -7.5
const DOUKU_WINDUP_PUSH: float = -2.0
const DOUKU_WINDUP_SCALE: Vector2 = Vector2(1.02, 0.98)
## 蓄力时长（秒）。实测「动画开始 → 真正出手」约 0.29~0.43 秒，取 0.18 保证翻腕到位、还能留一点定住的空档
const DOUKU_WINDUP_TIME: float = 0.18

## 甩完之后的收势已并入 _play_throw_body 的阻尼回弹，这里不再单独留常量

## 手里那支镖：与子弹用同一张图（30×12，镖尖朝右），出手瞬间能和飞行中的镖接上
const DOUKU_DART_PATH: String = "res://assets/image/character/douku/douku_dart.png"
## ── 下面这四个位置都在「79 高度」的参考空间里，实际使用前会乘 _art_k ──────
## 手里待命：镖尖朝上斜握在手心。手的位置由立绘量出：像素 (156,145) → 局部 (19.9,-36.6)
const DOUKU_DART_READY_POS := Vector2(22.0, -38.0)
const DOUKU_DART_READY_DEG: float = -70.0
## 缩放值：飞镖贴图从 30x12 换成 40x14（重绘成锥形刃 + V 尾翼），
## 贴图本身大了 4/3，所以三个 scale 同步乘 0.75，保持手里那支镖的屏幕尺寸不变。
## 待命那支没有再严格等比：0.64 比 0.58 略大一点，让「手里有镖」在 103px 的身高下看得清。
const DOUKU_DART_READY_SCALE := Vector2(0.64, 0.64)
## 翻腕蓄力：镖尖倒向肩后（比待命再多翻 22 度，为甩出去攒行程）
const DOUKU_DART_COCK_POS := Vector2(20.0, -45.0)
const DOUKU_DART_COCK_DEG: float = -92.0
## 袖口：镖藏在「举起来那只手」的宽袖里。量自立绘的袖口内衬：像素 (147,203) → 局部 (17.5,-21.1)
## 有意不用另一边吊着的那只袖子——从那里抽镖要横穿整个胸腹，看起来像一支镖自己飘上来
const DOUKU_DART_SLEEVE_POS := Vector2(17.0, -22.0)
const DOUKU_DART_SLEEVE_DEG: float = 70.0
const DOUKU_DART_SLEEVE_SCALE := Vector2(0.30, 0.30)
## ── 出手终点：这一组【不能】跟着角色尺寸缩放 ────────────────────────────
## 它是由子弹出生点 (20.6,-42.2) 和子弹速度反推出来的：300 px/s × 0.075 秒 = 22.5 像素，
## 所以终点固定在出生点前方 22 像素。子弹出生点挂在场景里那条 marker 链上，
## 不随豆蔻立绘大小变化；这里若跟着放大，镖就会在离手 35 像素的空中消失、
## 子弹却从更靠后的位置凭空出现，反而穿帮。当前镖从手(≈28.6,-49.4)甩到 (43,-41)，
## 行程短一点但交接点严丝合缝。
const DOUKU_DART_RELEASE_POS := Vector2(43.0, -41.0)
const DOUKU_DART_RELEASE_DEG: float = 14.0
const DOUKU_DART_RELEASE_SCALE := Vector2(0.75, 0.75)
## 出手时长 / 出手后隔多久开始抛下一支（秒）
## 抽镖的时长不在这里：[code]DOUKU_TOSS_FLY_TIME[/code] + [code]DOUKU_TOSS_SETTLE_TIME[/code]，
## 因为现在抽镖是三拍的抛接动作，不是一段平移。
const DOUKU_DART_FLY_TIME: float = 0.075
const DOUKU_DART_RELOAD_DELAY: float = 0.13
## 出手弧线：控制点比两端连线再抬高这么多像素，镖才会「挑一下」再飞出去
const DOUKU_DART_ARC_LIFT: float = 4.0
## 刚种下时延后一点再抽镖，别和种下的弹跳动画挤在一起
const DOUKU_DART_FIRST_DRAW_DELAY: float = 0.15

## ── 「手一扬，把袖子里的镖甩出来再抓住」 ────────────────────────────────────
## 原来抽镖只是把镖从袖口「平移」到手上，读起来像贴图被拖动。
## 现在拆成三拍，登场和每次出手后都走这一套：
##   ① 袖口闪一下 + 整个人往上轻轻一弹（镖还没出来，手先动）；
##   ② 镖沿一条向上挑的弧线甩出袖口，自转 220°，同时由小变大、由透明变实；
##   ③ 落进手心时缩一下（BACK 缓动），收在待命姿势。
## 自转 220° 是算出来的不是凑的：袖口里镖是 +70°，待命要 -70°（也就是 +290°），
## 正好差 220°，所以「转一圈落进手里」和最终姿势能严丝合缝，不会莫名扭一下。
const DOUKU_TOSS_FLY_TIME: float = 0.26
const DOUKU_TOSS_SETTLE_TIME: float = 0.09
## 弧线最高点比两端连线再高这么多（79 参考空间，会乘 _art_k）
const DOUKU_TOSS_APEX_LIFT: float = 15.0
## 最高点再往右偏一点：偏直上直下像电梯，偏出去才像「甩」
const DOUKU_TOSS_APEX_SHIFT: float = 2.0
const DOUKU_TOSS_SPIN_DEG: float = 220.0
## 飞行途中比待命略大，落手再缩回去，才有「接住」的错拍感
const DOUKU_TOSS_SCALE_PEAK: float = 0.70
## 上手（整个人往上弹一下）：只动 position:y。
## rotation 和 position:x 归身体发力/蓄力补间管，抢了会抖。
const DOUKU_ARM_LIFT: float = -3.4
const DOUKU_ARM_LIFT_TIME: float = 0.11
const DOUKU_ARM_FALL_TIME: float = 0.17
## ── 出手速度线 ────────────────────────────────────────────────────────────
## 一条锥形速度贴图（头部粗亮、尾部细淡），挂在出手点后方、沿真实飞行角铺开。
## 注意别再沿「蓄力点 → 出手点」去铺：那条线是斜着穿过胸口的，
## 在 30 像素的镖旁边读起来就是一根白杠子，像被人拿板子挡了一下。
const DOUKU_STREAK_PATH: String = "res://assets/image/character/douku/douku_streak.png"
const DOUKU_STREAK_COUNT: int = 2
const DOUKU_STREAK_ALPHA: float = 0.42
const DOUKU_STREAK_HOLD: float = 0.09
## 速度线在画面上的长度（79 参考空间），会再乘 _art_k
const DOUKU_STREAK_SPAN: float = 26.0
## 速度线贴图原始长度（46 像素），用来把 scale_x 换算成「覆盖多少像素」
const DOUKU_STREAK_TEX_LEN: float = 46.0

## ── 出手闪光 ──────────────────────────────────────────────────────────────
## 甩出去的那一帧在手腕位置炸一下小白光。没有它，镖是「突然从手里消失再出现在前方」；
## 有了它，那一下就是「甩」的落点。
const DOUKU_FLASH_PATH: String = "res://assets/image/character/douku/douku_flash.png"
const DOUKU_FLASH_POS := Vector2(38.0, -39.0)
## 贴图是 20×20，所以显示尺寸 = 20 × scale。原来 0.9→1.2 再乘 1.3 的 _art_k
## 会涨到 31 px，正好糊在脸上；现在收到 0.62→0.92（约 16→24 px）
const DOUKU_FLASH_FROM: float = 0.62
const DOUKU_FLASH_TO: float = 0.92
const DOUKU_FLASH_TIME: float = 0.09
## ── 接地投影 ──────────────────────────────────────────────────────────────
## 立绘本身没有影子，站在草坪上像贴纸浮着。补一片软椭圆压在脚下，
## 而且挂在「待机摇摆」那层（不是发力那层），出镖时身体前送、影子不动，才有踩住地的感觉。
const DOUKU_SHADOW_PATH: String = "res://assets/image/character/douku/douku_shadow.png"
const DOUKU_SHADOW_POS := Vector2(1.0, -1.0)

## 抽镖时袖口闪一下光点：不加这个，「从袖子里拿」只是一支镖自己滑上来
const DOUKU_SPARK_PATH: String = "res://assets/image/character/douku/douku_spark.png"

## 调试打印（出手间隔 / 子弹出生点）。定型后改成 false 即可静音
const DOUKU_DEBUG: bool = false

@onready var attack_component: AttackComponentBulletBase = $AttackComponent

## 立绘尺寸换算系数 = 当前高度 / 参考高度。所有按 79 高度量出来的像素坐标都乘它。
var _art_k: float = 1.0

## 闭眼帧精灵，供眨眼协程切换显隐
var douku_blink_sprite: Sprite2D = null
## 出镖动作节点：与待机摇摆分离，两个旋转才不会互相打断
var douku_throw_pivot: Node2D = null
## 整个身体的发力动作（前送 / 回弹 / 收势），一段补间走完
var douku_body_tween: Tween = null
## 手里的飞镖（待命 / 蓄力 / 出手 / 抽镖都动它）
var douku_dart_sprite: Sprite2D = null
## 出手速度线（锥形贴图，按实际飞行角铺在扫过的路径上）
var douku_streaks: Array[Sprite2D] = []
var douku_streak_tweens: Array[Tween] = []
## 脚下接地投影
var douku_shadow_sprite: Sprite2D = null
## 出手瞬间的手腕闪光
var douku_flash_sprite: Sprite2D = null
var douku_flash_tween: Tween = null
## 袖口闪光的精灵
var douku_spark_sprite: Sprite2D = null
var douku_spark_tween: Tween = null
## 飞镖当前这一段动作；重开时整段杀掉，避免两支镖的动作叠在一起
var douku_dart_tween: Tween = null
## 蓄力动作
var douku_windup_tween: Tween = null
## 抽镖时「手一扬」的动作
var douku_arm_tween: Tween = null
## 手里现在有没有镖（正在从袖子里抽的时候是 false）
var douku_dart_in_hand: bool = false
## 调试用：上一次攻击动画开始的时间点，用来量「请求 → 真正出手」的间隔
var _attack_anim_start_msec: int = 0


## 初始化正常出战角色信号连接
func ready_norm_signal_connect():
	super()
	signal_update_speed.connect(attack_component.owner_update_speed)


func _ready() -> void:
	super()
	if douku_enable:
		_apply_douku_art()
		# 弹药换成飞镖。只改这一株的引用，豌豆系其他植物仍用原豌豆弹
		attack_component.attack_bullet_type = BulletRegistry.BulletType.Bullet101Dart
		# 动画里调用 _shoot_bullet 的同一帧抛出，用来同步甩镖动作
		attack_component.signal_shoot_bullet.connect(_on_douku_shoot_bullet)
		# 攻击动画一开始先蓄力（反向压 + 翻腕），出手那一帧才是「甩」而不是「吐」
		attack_component.signal_attack_anim_start.connect(_on_douku_attack_anim_start)
		# 目标没了要收势，否则会定在蓄力姿势上
		attack_component.signal_change_is_attack.connect(_on_douku_is_attack_changed)


## 隐藏散件版身体，换成整图立绘并加轻微待机动作
## 说明：不改 .tscn 结构，全部在运行期完成，回退只需把 douku_enable 置 false
func _apply_douku_art() -> void:
	var body_correct: Node2D = get_node_or_null("Body/BodyCorrect") as Node2D
	if body_correct == null:
		# 兜底：不同场景层级下按名字找，避免路径写死
		body_correct = find_child("BodyCorrect", true, false) as Node2D
	if body_correct == null:
		push_warning("豆蔻：找不到 BodyCorrect，跳过换装")
		return

	var tex: Texture2D = load(DOUKU_ART_PATH) as Texture2D
	if tex == null:
		push_warning("豆蔻：贴图没找到或还没被导入 → %s" % DOUKU_ART_PATH)
		return

	# 1) 原散件整体隐藏（含眨眼、摆头等动画，一起藏掉）
	body_correct.visible = false

	# 参考空间(高 79) → 当前尺寸的换算系数。改 DOUKU_HEIGHT 时这里自动跟着变，
	# 不必再手算镖/袖口/闪光的一堆像素坐标。
	_art_k = DOUKU_HEIGHT / DOUKU_HEIGHT_REF

	var holder: Node2D = body_correct.get_parent()
	var art_scale: float = DOUKU_HEIGHT / float(tex.get_height())
	# 画布上下各留了 DOUKU_FOOT_PAD_PX 的描边余量，脚底要减掉这段才正好落回 y=0
	var art_local_y: float = -DOUKU_HEIGHT * 0.5 + DOUKU_FOOT_PAD_PX * art_scale

	# 2) 两层节点：外层管待机摇摆，内层管出镖动作
	#    挂在同一个父节点下、都以脚底为原点，所以两层旋转都是绕地面转
	var sway_pivot := Node2D.new()
	sway_pivot.name = "DookuPivot"
	holder.add_child(sway_pivot)

	# 2.5) 接地投影挂在外层：出镖时身体前送，影子不跟着动，才像踩在地上
	_build_shadow_node(sway_pivot)

	douku_throw_pivot = Node2D.new()
	douku_throw_pivot.name = "DookuThrow"
	sway_pivot.add_child(douku_throw_pivot)

	# 3) 整图。Sprite2D 默认居中，中心上移半个身高，脚底正好落在 y=0
	var art := Sprite2D.new()
	art.name = "DookuIdle"
	art.texture = tex
	art.scale = Vector2(art_scale, art_scale)
	art.position = Vector2(0.0, art_local_y)
	douku_throw_pivot.add_child(art)

	# 4) 待机：左右摇摆 + 呼吸起伏
	var sway: Tween = create_tween().set_loops()
	sway.tween_property(sway_pivot, "rotation", deg_to_rad(DOUKU_SWAY_DEG), DOUKU_SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	sway.tween_property(sway_pivot, "rotation", deg_to_rad(-DOUKU_SWAY_DEG), DOUKU_SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	var breath: Tween = create_tween().set_loops()
	breath.tween_property(art, "position:y", art_local_y - DOUKU_BREATH_PX, 0.9) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	breath.tween_property(art, "position:y", art_local_y, 0.9) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	# 5) 手里的飞镖。挂在出镖节点下，身体发力时镖跟着一起动；
	#    待命时露在袖口，出手时甩出去，出手后再从下摆袖口抽下一支。
	_build_dart_nodes()

	# 6) 新种下的豆蔻：先从袖子里抽一支出来待命
	if is_instance_valid(douku_dart_sprite):
		_play_first_draw()

	# 7) 眨眼：有闭眼帧才启用，缺图时这一步整体跳过
	_build_blink_node(tex, art_scale, art_local_y)


## 建飞镖本体 + 拖影 + 袖口光点（都挂在出镖节点下）
func _build_dart_nodes() -> void:
	if douku_throw_pivot == null:
		return
	var dart_tex: Texture2D = load(DOUKU_DART_PATH) as Texture2D
	if dart_tex == null:
		push_warning("豆蔻：飞镖贴图没找到 → %s" % DOUKU_DART_PATH)
		return

	douku_dart_sprite = Sprite2D.new()
	douku_dart_sprite.name = "DookuDart"
	douku_dart_sprite.texture = dart_tex
	## 压在立绘之上
	douku_dart_sprite.z_index = 3
	douku_dart_sprite.visible = false
	douku_throw_pivot.add_child(douku_dart_sprite)

	## 速度线：锥形贴图，压在镖下面一层；缺图就整段跳过
	if ResourceLoader.exists(DOUKU_STREAK_PATH):
		var streak_tex: Texture2D = load(DOUKU_STREAK_PATH) as Texture2D
		if streak_tex != null:
			for i: int in DOUKU_STREAK_COUNT:
				var streak := Sprite2D.new()
				streak.name = "DookuStreak%d" % i
				streak.texture = streak_tex
				streak.z_index = 2
				streak.visible = false
				douku_throw_pivot.add_child(streak)
				douku_streaks.append(streak)
		else:
			push_warning("豆蔻：速度线贴图加载失败（可能还没被导入）→ %s" % DOUKU_STREAK_PATH)
	else:
		push_warning("豆蔻：速度线贴图不存在 → %s" % DOUKU_STREAK_PATH)

	## 出手闪光：只在甩出去那一帧出现，压在镖之上
	if ResourceLoader.exists(DOUKU_FLASH_PATH):
		var flash_tex: Texture2D = load(DOUKU_FLASH_PATH) as Texture2D
		if flash_tex != null:
			douku_flash_sprite = Sprite2D.new()
			douku_flash_sprite.name = "DookuReleaseFlash"
			douku_flash_sprite.texture = flash_tex
			douku_flash_sprite.z_index = 5
			douku_flash_sprite.visible = false
			douku_throw_pivot.add_child(douku_flash_sprite)
		else:
			push_warning("豆蔻：闪光贴图加载失败（可能还没被导入）→ %s" % DOUKU_FLASH_PATH)
	else:
		push_warning("豆蔻：闪光贴图不存在 → %s" % DOUKU_FLASH_PATH)

	## 袖口光点：缺图就不建，后续调用会自动跳过
	if ResourceLoader.exists(DOUKU_SPARK_PATH):
		var spark_tex: Texture2D = load(DOUKU_SPARK_PATH) as Texture2D
		if spark_tex != null:
			douku_spark_sprite = Sprite2D.new()
			douku_spark_sprite.name = "DookuSleeveSpark"
			douku_spark_sprite.texture = spark_tex
			douku_spark_sprite.z_index = 4
			douku_spark_sprite.visible = false
			douku_throw_pivot.add_child(douku_spark_sprite)


## 脚下的软投影。缺图就跳过（不建节点，后面也不会有人引用它）
func _build_shadow_node(parent: Node2D) -> void:
	if not ResourceLoader.exists(DOUKU_SHADOW_PATH):
		return
	var shadow_tex: Texture2D = load(DOUKU_SHADOW_PATH) as Texture2D
	if shadow_tex == null:
		return
	douku_shadow_sprite = Sprite2D.new()
	douku_shadow_sprite.name = "DookuShadow"
	douku_shadow_sprite.texture = shadow_tex
	douku_shadow_sprite.position = _art_pos(DOUKU_SHADOW_POS)
	## 影子跟着人物一起放大，否则 99px 高的角色会踩在一小片 42px 的影子上
	douku_shadow_sprite.scale = Vector2(_art_k, _art_k)
	## 压到立绘下面
	douku_shadow_sprite.z_index = -1
	parent.add_child(douku_shadow_sprite)


## 建闭眼帧。没有闭眼图就整段跳过
func _build_blink_node(tex: Texture2D, art_scale: float, art_local_y: float) -> void:
	if not ResourceLoader.exists(DOUKU_BLINK_PATH):
		return
	var blink_tex: Texture2D = load(DOUKU_BLINK_PATH) as Texture2D
	if blink_tex == null:
		return
	douku_blink_sprite = Sprite2D.new()
	douku_blink_sprite.name = "DookuBlink"
	douku_blink_sprite.texture = blink_tex
	douku_blink_sprite.scale = Vector2(art_scale, art_scale)
	douku_blink_sprite.position = Vector2(0.0, art_local_y)
	douku_blink_sprite.visible = false
	douku_blink_sprite.z_index = 1
	douku_throw_pivot.add_child(douku_blink_sprite)
	_start_blink_loop()


# ══════════════════════════════════════════════════════════════════════════
# 出手链路：蓄力（动画开始） → 甩镖（子弹生成那一帧） → 抽下一支
# ══════════════════════════════════════════════════════════════════════════

## 攻击动画开始：身体往后微坐蓄力，同时翻腕把镖压到肩后
func _on_douku_attack_anim_start() -> void:
	_attack_anim_start_msec = Time.get_ticks_msec()
	if douku_throw_pivot == null:
		return
	# 上一发如果还在归位，先掐掉，否则两段补间同时写 rotation 会抖
	if douku_body_tween != null and douku_body_tween.is_valid():
		douku_body_tween.kill()
	douku_body_tween = null
	_kill_windup_tween()
	# 抽镖时的「手上扬」写的是 position:y，这里必须先归零并掐掉，
	# 否则那一发会带着几像素的抬升去发力，看着像整个人悬着
	if douku_arm_tween != null and douku_arm_tween.is_valid():
		douku_arm_tween.kill()
	douku_arm_tween = null
	douku_throw_pivot.position.y = 0.0
	douku_windup_tween = create_tween()
	douku_windup_tween.tween_property(douku_throw_pivot, "rotation", deg_to_rad(DOUKU_WINDUP_DEG), DOUKU_WINDUP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	douku_windup_tween.parallel().tween_property(douku_throw_pivot, "position:x", DOUKU_WINDUP_PUSH, DOUKU_WINDUP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	douku_windup_tween.parallel().tween_property(douku_throw_pivot, "scale", DOUKU_WINDUP_SCALE, DOUKU_WINDUP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_cock_dart()


## 翻腕：镖尖从「朝上」倒向「肩后」，这一段才是甩出去的势能
## 只在手里确实有镖的时候做；还在袖子里抽的话不能打断抽取动画
func _cock_dart() -> void:
	if not douku_dart_in_hand or not is_instance_valid(douku_dart_sprite):
		return
	_kill_dart_tween()
	douku_dart_tween = create_tween()
	douku_dart_tween.tween_property(douku_dart_sprite, "position", _art_pos(DOUKU_DART_COCK_POS), DOUKU_WINDUP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	douku_dart_tween.parallel().tween_property(douku_dart_sprite, "rotation", deg_to_rad(DOUKU_DART_COCK_DEG), DOUKU_WINDUP_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)


## 动画里真正生成子弹的那一帧：镖甩出去 + 身体急促前送
func _on_douku_shoot_bullet() -> void:
	if douku_throw_pivot == null:
		return
	if DOUKU_DEBUG:
		_print_shoot_debug()
	# 蓄力到此为止，接下来交给甩镖，从当前姿势起算所以更「弹」
	_kill_windup_tween()
	_play_throw_body()
	_play_dart_release()


## 身体发力：急促前送 → 阻尼回弹（两次递减的过冲） → 归位
##
## 上一版是「前送 → 一次反向过冲 → 直接线性回正 → 一段 0→0 的空补间」。
## 0→0 那段什么也不做，只是把补间拖长；而回正是线性贴到 0 的，
## 看着像被人按回原位。现在把收势做成一条【衰减振荡】：
##   +9° → -2.6° → +1.2° → 0°，每段幅度约为上一段的 0.28 / 0.46，
## 这才是被手甩出去之后、身体自己找平衡的样子。
func _play_throw_body() -> void:
	if douku_body_tween != null and douku_body_tween.is_valid():
		douku_body_tween.kill()
	douku_body_tween = create_tween()
	# 1) 前送：CUBIC 缓出（前段极快），像被手带出去的那一下
	douku_body_tween.tween_property(douku_throw_pivot, "rotation", deg_to_rad(DOUKU_THROW_DEG), DOUKU_THROW_HIT_TIME) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	douku_body_tween.parallel().tween_property(douku_throw_pivot, "position:x", DOUKU_THROW_PUSH, DOUKU_THROW_HIT_TIME) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	douku_body_tween.parallel().tween_property(douku_throw_pivot, "scale", DOUKU_THROW_STRETCH, DOUKU_THROW_HIT_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	# 2) 回弹①：反向过冲 + 竖着拉一下，做出惯性和重量
	douku_body_tween.tween_property(douku_throw_pivot, "rotation", deg_to_rad(DOUKU_THROW_OVERSHOOT_DEG), DOUKU_THROW_BACK_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	douku_body_tween.parallel().tween_property(douku_throw_pivot, "position:x", DOUKU_THROW_BACK_PUSH, DOUKU_THROW_BACK_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	douku_body_tween.parallel().tween_property(douku_throw_pivot, "scale", DOUKU_THROW_RECOIL_SCALE, DOUKU_THROW_BACK_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	# 3) 回弹②：再反向一次，幅度只剩三成，同时把挤压拉伸还原
	douku_body_tween.tween_property(douku_throw_pivot, "rotation", deg_to_rad(DOUKU_THROW_OVERSHOOT2_DEG), DOUKU_THROW_SETTLE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	douku_body_tween.parallel().tween_property(douku_throw_pivot, "position:x", DOUKU_THROW_BACK_PUSH * -0.28, DOUKU_THROW_SETTLE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	douku_body_tween.parallel().tween_property(douku_throw_pivot, "scale", Vector2.ONE, DOUKU_THROW_SETTLE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	# 4) 归位：最后一点点余震收到 0，正好盖住「从袖子里抽下一支」那段时间
	douku_body_tween.tween_property(douku_throw_pivot, "rotation", 0.0, DOUKU_THROW_RESTORE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	douku_body_tween.parallel().tween_property(douku_throw_pivot, "position:x", 0.0, DOUKU_THROW_RESTORE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)


## 镖的那一段：甩出去 → 空手 → 袖口一闪 → 抽出下一支
func _play_dart_release() -> void:
	if not is_instance_valid(douku_dart_sprite):
		return
	var dart: Sprite2D = douku_dart_sprite
	_kill_dart_tween()
	_hide_streaks()
	# 攻击间隔被压到极短、镖还在袖子里没抽完就要出手：直接摆到手里，
	# 否则镖会从肚子上方一路飞出去，看着像凭空冒出来的
	if not douku_dart_in_hand:
		_snap_dart_to_hand()
	douku_dart_in_hand = false

	douku_dart_tween = create_tween()
	# 1) 甩出去：走一条小弧线（不是直线平移）+ 翻腕砸到 +14 度，同时压平、缩小、淡出
	#    直线平移读起来像「贴图被拖动」；手腕翻出去的轨迹是个向下压的弧，所以位置用二次贝塞尔补
	var p0: Vector2 = dart.position
	var p2: Vector2 = DOUKU_DART_RELEASE_POS
	var p1: Vector2 = (p0 + p2) * 0.5 + Vector2(0.0, -DOUKU_DART_ARC_LIFT)
	douku_dart_tween.tween_method(
		func(t: float) -> void: dart.position = _quad_bezier(p0, p1, p2, t),
		0.0, 1.0, DOUKU_DART_FLY_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	douku_dart_tween.parallel().tween_property(dart, "rotation", deg_to_rad(DOUKU_DART_RELEASE_DEG), DOUKU_DART_FLY_TIME) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	douku_dart_tween.parallel().tween_property(dart, "scale", DOUKU_DART_RELEASE_SCALE, DOUKU_DART_FLY_TIME)
	douku_dart_tween.parallel().tween_property(dart, "modulate:a", 0.0, DOUKU_DART_FLY_TIME * 0.8)
	douku_dart_tween.tween_callback(_hide_dart)
	# 2) 空手缓一下 → 袖口闪光 → 抽出下一支
	_append_draw(douku_dart_tween, DOUKU_DART_RELOAD_DELAY)
	# 3) 手腕闪一下 + 沿真实飞行角铺一道锥形速度线
	_play_release_flash()
	_play_dart_streak()


## 刚种下：直接从袖子里抽一支出来待命
func _play_first_draw() -> void:
	_kill_dart_tween()
	douku_dart_in_hand = false
	douku_dart_tween = create_tween()
	_append_draw(douku_dart_tween, DOUKU_DART_FIRST_DRAW_DELAY)


## 把「袖口闪光 → 手一扬 → 抛袖出镖 → 接住待命」接到某段补间的末尾
##
## 登场（刚种下）和每次出手之后走的都是这一套，所以「豆蔻登场」和
## 「甩完再掏一支」在画面上是同一种动作，看几轮就能读出她的节奏。
func _append_draw(tw: Tween, lead_delay: float) -> void:
	if tw == null:
		return
	if lead_delay > 0.0:
		tw.tween_interval(lead_delay)
	# ① 袖口先闪，同时整个人往上弹一下 —— 手先动，镖后出
	tw.tween_callback(_flash_sleeve)
	tw.tween_callback(_play_arm_lift)
	tw.tween_callback(_place_dart_in_sleeve)
	# ② 甩出来：弧线 + 自转 + 由小变大由透明变实
	tw.tween_method(_apply_dart_toss, 0.0, 1.0, DOUKU_TOSS_FLY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(douku_dart_sprite, "scale",
		Vector2(DOUKU_TOSS_SCALE_PEAK, DOUKU_TOSS_SCALE_PEAK), DOUKU_TOSS_FLY_TIME)
	tw.parallel().tween_property(douku_dart_sprite, "modulate:a", 1.0, DOUKU_TOSS_FLY_TIME * 0.45)
	# ③ 接住：缩回待命尺寸，BACK 缓动让「抓住」那一下有个回弹
	tw.tween_property(douku_dart_sprite, "scale", DOUKU_DART_READY_SCALE, DOUKU_TOSS_SETTLE_TIME) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_callback(_catch_dart)


## 抛袖动作的每一帧：二次贝塞尔弧线 + 线性自转
## 起点终点都取自己人身上的锚点，所以改 DOUKU_DART_*_POS 时弧线会自己跟着走
func _apply_dart_toss(t: float) -> void:
	if not is_instance_valid(douku_dart_sprite):
		return
	var p0: Vector2 = _art_pos(DOUKU_DART_SLEEVE_POS)
	var p2: Vector2 = _art_pos(DOUKU_DART_READY_POS)
	var apex: Vector2 = (p0 + p2) * 0.5 + Vector2(
		DOUKU_TOSS_APEX_SHIFT * _art_k, -DOUKU_TOSS_APEX_LIFT * _art_k)
	douku_dart_sprite.position = _quad_bezier(p0, apex, p2, t)
	douku_dart_sprite.rotation = deg_to_rad(
		lerpf(DOUKU_DART_SLEEVE_DEG, DOUKU_DART_SLEEVE_DEG + DOUKU_TOSS_SPIN_DEG, t))


## 手一扬：整个人往上弹一下再接住。只写 position:y，不碰另外两个属性
func _play_arm_lift() -> void:
	if douku_throw_pivot == null:
		return
	if douku_arm_tween != null and douku_arm_tween.is_valid():
		douku_arm_tween.kill()
	douku_arm_tween = create_tween()
	douku_arm_tween.tween_property(douku_throw_pivot, "position:y",
		DOUKU_ARM_LIFT * _art_k, DOUKU_ARM_LIFT_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	douku_arm_tween.tween_property(douku_throw_pivot, "position:y", 0.0, DOUKU_ARM_FALL_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


## 接住：标记「手里有镖」+ 手心点一颗小火星，给这一拍一个落点
func _catch_dart() -> void:
	_mark_dart_in_hand()
	_flash_catch()


## 落手火星：比袖口那颗更小更短，只负责把「抓住了」点出来
func _flash_catch() -> void:
	if not is_instance_valid(douku_spark_sprite):
		return
	var sp: Sprite2D = douku_spark_sprite
	sp.position = _art_pos(DOUKU_DART_READY_POS)
	sp.rotation = 0.0
	sp.scale = Vector2(0.26, 0.26)
	sp.modulate.a = 0.0
	sp.visible = true
	if douku_spark_tween != null and douku_spark_tween.is_valid():
		douku_spark_tween.kill()
	douku_spark_tween = create_tween()
	douku_spark_tween.tween_property(sp, "modulate:a", 0.72, 0.04)
	douku_spark_tween.parallel().tween_property(sp, "scale", Vector2(0.60, 0.60), 0.13) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	douku_spark_tween.tween_property(sp, "modulate:a", 0.0, 0.11)
	douku_spark_tween.tween_callback(sp.hide)


## 出手速度线：方向与长度都按镖的真实行程算，铺满它扫过的那一段
## 不写死角度：以后改 DOUKU_DART_*_POS，速度线会自己跟着对齐
func _play_dart_streak() -> void:
	if douku_streaks.is_empty():
		return
	_kill_streak_tweens()
	## 方向取真实出手角，位置贴在出手点后方：速度线要读成「镖刚扫过这里」，
	## 而不是一条横在角色胸前、和镖无关的白杠。
	var dir_vec: Vector2 = Vector2.RIGHT.rotated(deg_to_rad(DOUKU_DART_RELEASE_DEG))
	var span: float = DOUKU_STREAK_SPAN * _art_k
	if span < 0.01:
		return
	var tail_mid: Vector2 = DOUKU_DART_RELEASE_POS - dir_vec * (span * 0.5 + 2.0)
	## 锥形贴图头朝 +x，要正好覆盖 span 像素：scale_x = span / 贴图长度
	var base_sx: float = span / DOUKU_STREAK_TEX_LEN
	for i: int in douku_streaks.size():
		var streak: Sprite2D = douku_streaks[i]
		var k: float = float(i)          # 0 = 主道；1 = 外圈更淡更长
		streak.position = tail_mid
		streak.rotation = dir_vec.angle()
		streak.scale = Vector2(base_sx * (1.0 + 0.35 * k), 1.0 + 0.4 * k)
		streak.modulate.a = DOUKU_STREAK_ALPHA * (1.0 - 0.55 * k)
		streak.visible = true
		var t: Tween = create_tween()
		## 立刻开始拉长并淡出：读作一道掠过去的风，而不是一支透明的镖
		t.tween_property(streak, "modulate:a", 0.0, DOUKU_STREAK_HOLD) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		t.parallel().tween_property(streak, "scale:x", base_sx * (1.5 + 0.4 * k), DOUKU_STREAK_HOLD) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		t.tween_callback(streak.hide)
		douku_streak_tweens.append(t)


## 甩出去那一帧：手腕位置炸一小团白光，把「甩」的落点点出来
func _play_release_flash() -> void:
	if not is_instance_valid(douku_flash_sprite):
		return
	var fl: Sprite2D = douku_flash_sprite
	if douku_flash_tween != null and douku_flash_tween.is_valid():
		douku_flash_tween.kill()
	fl.position = _art_pos(DOUKU_FLASH_POS)
	fl.rotation = 0.0
	fl.scale = Vector2(DOUKU_FLASH_FROM, DOUKU_FLASH_FROM) * _art_k
	fl.modulate = Color(1.0, 1.0, 1.0, 1.0)
	fl.visible = true
	douku_flash_tween = create_tween()
	## 起手就是最亮，然后撑开、淡掉
	douku_flash_tween.tween_property(fl, "modulate:a", 0.0, DOUKU_FLASH_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	douku_flash_tween.parallel().tween_property(fl, "scale", Vector2(DOUKU_FLASH_TO, DOUKU_FLASH_TO) * _art_k, DOUKU_FLASH_TIME) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	douku_flash_tween.parallel().tween_property(fl, "rotation", deg_to_rad(28.0), DOUKU_FLASH_TIME)
	douku_flash_tween.tween_callback(fl.hide)


## 袖口闪一下：菱形光点弹一下再消失，"从袖子里掏出来"才有交代
func _flash_sleeve() -> void:
	if not is_instance_valid(douku_spark_sprite):
		return
	var sp: Sprite2D = douku_spark_sprite
	sp.position = _art_pos(DOUKU_DART_SLEEVE_POS)
	sp.rotation = 0.0
	sp.scale = Vector2(0.35, 0.35)
	sp.modulate.a = 0.0
	sp.visible = true
	if douku_spark_tween != null and douku_spark_tween.is_valid():
		douku_spark_tween.kill()
	douku_spark_tween = create_tween()
	douku_spark_tween.tween_property(sp, "modulate:a", 0.8, 0.06)
	douku_spark_tween.parallel().tween_property(sp, "scale", Vector2(0.85, 0.85), 0.16) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	douku_spark_tween.parallel().tween_property(sp, "rotation", deg_to_rad(35.0), 0.26)
	douku_spark_tween.tween_property(sp, "modulate:a", 0.0, 0.16)
	douku_spark_tween.tween_callback(sp.hide)


## 能不能攻击变了：目标没了要把蓄力姿势收回来，否则会一直歪着
func _on_douku_is_attack_changed(value: bool) -> void:
	if value or douku_throw_pivot == null:
		return
	# 正在发力就让它走完，别中途抢姿势
	if douku_body_tween != null and douku_body_tween.is_running():
		return
	_kill_windup_tween()
	_uncock_dart()
	douku_windup_tween = create_tween()
	douku_windup_tween.tween_property(douku_throw_pivot, "rotation", 0.0, 0.18) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	douku_windup_tween.parallel().tween_property(douku_throw_pivot, "position:x", 0.0, 0.18) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	douku_windup_tween.parallel().tween_property(douku_throw_pivot, "scale", Vector2.ONE, 0.18) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)


## 收势时把翻到肩后的镖放回待命角度
func _uncock_dart() -> void:
	if not douku_dart_in_hand or not is_instance_valid(douku_dart_sprite):
		return
	_kill_dart_tween()
	douku_dart_tween = create_tween()
	douku_dart_tween.tween_property(douku_dart_sprite, "position", _art_pos(DOUKU_DART_READY_POS), 0.16) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	douku_dart_tween.parallel().tween_property(douku_dart_sprite, "rotation", deg_to_rad(DOUKU_DART_READY_DEG), 0.16) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)


# ══════════════════════════════════════════════════════════════════════════
# 小工具
# ══════════════════════════════════════════════════════════════════════════

## 把「79 高度参考空间」里的坐标换算到当前立绘尺寸
func _art_pos(v: Vector2) -> Vector2:
	return v * _art_k


## 把「79 高度参考空间」里的缩放换算到当前立绘尺寸；手里的镖要跟人一起变大，
## 否则人拉高了 30% 而镖没变，画面上会变成「大个子捏着一根牙签」
func _art_scale(v: Vector2) -> Vector2:
	return v * _art_k


## 二次贝塞尔：t=0 在 p0，t=1 在 p2，p1 是控制点
func _quad_bezier(p0: Vector2, p1: Vector2, p2: Vector2, t: float) -> Vector2:
	var u: float = 1.0 - t
	return u * u * p0 + 2.0 * u * t * p1 + t * t * p2

## 把镖直接摆到待命位（含之前被隐藏 / 抽到一半的情况）
func _snap_dart_to_hand() -> void:
	var dart: Sprite2D = douku_dart_sprite
	dart.visible = true
	dart.position = _art_pos(DOUKU_DART_READY_POS)
	dart.rotation = deg_to_rad(DOUKU_DART_READY_DEG)
	dart.scale = DOUKU_DART_READY_SCALE
	dart.modulate.a = 1.0


func _hide_dart() -> void:
	if is_instance_valid(douku_dart_sprite):
		douku_dart_sprite.visible = false


## 镖出现在下摆袖口（缩小、横斜、透明），下一步由补间把它抽到手上
func _place_dart_in_sleeve() -> void:
	if not is_instance_valid(douku_dart_sprite):
		return
	var dart: Sprite2D = douku_dart_sprite
	dart.visible = true
	dart.position = _art_pos(DOUKU_DART_SLEEVE_POS)
	dart.rotation = deg_to_rad(DOUKU_DART_SLEEVE_DEG)
	dart.scale = _art_scale(DOUKU_DART_SLEEVE_SCALE)
	dart.modulate.a = 0.0


func _mark_dart_in_hand() -> void:
	douku_dart_in_hand = true


func _hide_streaks() -> void:
	_kill_streak_tweens()
	for streak: Sprite2D in douku_streaks:
		if is_instance_valid(streak):
			streak.visible = false


func _kill_streak_tweens() -> void:
	for t: Tween in douku_streak_tweens:
		if t != null and t.is_valid():
			t.kill()
	douku_streak_tweens.clear()


func _kill_dart_tween() -> void:
	if douku_dart_tween != null and douku_dart_tween.is_valid():
		douku_dart_tween.kill()
	douku_dart_tween = null


func _kill_windup_tween() -> void:
	if douku_windup_tween != null and douku_windup_tween.is_valid():
		douku_windup_tween.kill()
	douku_windup_tween = null


## 调试：出手间隔 + 子弹真实出生点（用来核对镖的甩出终点对不对得上）
func _print_shoot_debug() -> void:
	print("豆蔻实际出手间隔：%.3f 秒" % ((Time.get_ticks_msec() - _attack_anim_start_msec) / 1000.0))
	if attack_component.markers_2d_bullet.size() == 0:
		return
	var marker: Marker2D = attack_component.markers_2d_bullet[0]
	if marker == null:
		return
	var offset: Vector2 = marker.global_position - global_position
	print("豆蔻子弹出生点(植物局部)：%s  ← 飞镖甩出终点应与它对齐" % str(offset))


## 随机间隔眨眼，间隔与眨眼时长都写死成小数值，避免每帧计算
func _start_blink_loop() -> void:
	var timer := Timer.new()
	timer.name = "DookuBlinkTimer"
	timer.one_shot = true
	timer.wait_time = randf_range(2.5, 5.5)
	add_child(timer)
	timer.timeout.connect(_on_douku_blink_timeout)
	timer.start()


func _on_douku_blink_timeout() -> void:
	if is_instance_valid(douku_blink_sprite):
		douku_blink_sprite.visible = true
		await get_tree().create_timer(0.12).timeout
		if is_instance_valid(douku_blink_sprite):
			douku_blink_sprite.visible = false
	var timer: Timer = get_node_or_null("DookuBlinkTimer") as Timer
	if timer != null:
		timer.wait_time = randf_range(2.5, 5.5)
		timer.start()
