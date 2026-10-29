extends Plant000Base
class_name Plant008PeaShooterDouble

## 阿双（双发射手）新形象开关
## true  = 用一整张 Q 版人形立绘替换原来的散件，并接管开火动作
## false = 恢复原版双发射手（原散件一个都没删，只是被隐藏）
@export var adouble_enable: bool = true

# ══════════════════════════════════════════════════════════════════════════
# 为什么这套动作必须「两发分开做」
# ──────────────────────────────────────────────────────────────────────────
# 原版双发射手不是一次打两颗，是**一条动画链打两发**：
#   OneShot 播 PeaShooter_shooting（长 1.5s），方法轨在 t=1.0s 调一次 _shoot_bullet；
#   播完自动切 PeaShooter_shooting_2（长 2.0s），同样在 t=1.0s 再调一次。
#   整条链跑在 TimeScale2=3.0 下面，所以实机大约是：
#       第 1 发 0.28 秒 → 第 2 发 0.69 秒，**两发间隔约 0.42 秒**，周期 1.5 秒。
#
# 阿双是**双持**，不是一株两个喷嚏孔。所以：
#   · 第 1 发由上枪（画面里靠前、靠上那把）开，第 2 发由下枪开；
#   · 每一发都有**自己的枪口爆闪 + 自己的后坐**，谁开火谁动；
#   · 子弹出生点当帧挪到「这一发所在的那把枪的枪口」，
#     否则两颗子弹都从肚子前面同一个点冒出来，火光却在两个高度——一眼就穿帮。
#
# 后坐方向也刻意不同，这是第二个防违和点：
#   上枪在后坐时让身体**往上顶**（枪口高，反作用力把上身抬起来）；
#   下枪在后坐时让身体**往下沉**。
# 两下顿挫方向不一样，眼睛才读得出「是两下」，而不是「一下被按了两遍」。
#
# 关于子弹会不会打不到：子弹碰撞是 Area2D（半径 10 的圆）撞僵尸身上的
# CapsuleShape2D（半径 20、高 100、中心 y=-50，覆盖 y∈[-100,0]）。枪口在
# y≈-63，落在范围内，所以抬高出弹点只改观感、不影响命中。
# ══════════════════════════════════════════════════════════════════════════

## ── 立绘烘焙说明 ────────────────────────────────────────────────────────
## 母版 814×1288，游戏里人物本体只显示 99 高，运行时缩到 0.077 倍，
## 线稿必然糊成一团灰。所以离线先用 Lanczos 缩到「显示尺寸的 2 倍」（本体 198），
## 运行时只需 0.5 倍；另在 2 倍空间补 2px 深绿描边（显示约 1px），
## 阿双是竹青绿衣，草坪也是绿，不描边 45 像素下轮廓会直接糊进背景。
## 这套规范抄自豆蔻（plant_001_pea_shooter_single.gd），两株并排才像同一套美术。
const ADOUBLE_ART_PATH: String = "res://assets/image/character/adouble/adouble_idle_03.png"
## ── 眨眼帧 ──────────────────────────────────────────────────────────────
## 整图立绘没有可单独驱动的眼睛部件，只能再烘一张「闭眼」整图叠上去闪一下。
## 关键：这张图必须和 idle 落在**同一个像素网格**上，否则一眨眼整个人会横移。
## 烘焙脚本 `_bake_adouble_blink.py` 会穷举补透明列的宽度，
## 取「眼睛以外区域与 idle 差异最小」的那一版（实测差异 0，完全重合）。
const ADOUBLE_BLINK_PATH: String = "res://assets/image/character/adouble/adouble_blink_01.png"
## 眨眼间隔随机区间（秒）与闭眼持续时间（秒）
const ADOUBLE_BLINK_GAP_MIN: float = 2.4
const ADOUBLE_BLINK_GAP_MAX: float = 5.6
const ADOUBLE_BLINK_HOLD: float = 0.12

## ── 攻击特效件（全部程序化绘制，风格对齐豆蔻那套）─────────────────────
const ADOUBLE_FX_FLASH: String = "res://assets/image/character/adouble/adouble_muzzle_flash.png"
const ADOUBLE_FX_SMOKE: String = "res://assets/image/character/adouble/adouble_muzzle_smoke.png"
const ADOUBLE_FX_RING: String = "res://assets/image/character/adouble/adouble_shock_ring.png"
const ADOUBLE_FX_SPARK: String = "res://assets/image/character/adouble/adouble_spark.png"
const ADOUBLE_FX_STREAK: String = "res://assets/image/character/adouble/adouble_streak.png"
const ADOUBLE_FX_SHADOW: String = "res://assets/image/character/adouble/adouble_shadow.png"

## ── 弹药 ────────────────────────────────────────────────────────────────
## 阿双手里是两支竹节短铳，飞出来的还是一颗圆豌豆就不对了。
## 换成竹节弹丸（scenes/bullet/bullet_104_adouble_pellet.tscn）。
## ⚠️ 只改这一株的引用，豌豆系其他植物（单发/寒冰/机枪/三线/裂荚）仍用原豌豆弹。
## 弹丸穿过火炬树桩会升级成 Bullet105AdoublePelletFire（伤害 20 → 40），
## 映射表在 plant_023_torch_wood.gd，别漏。
const ADOUBLE_BULLET_TYPE: BulletRegistry.BulletType = BulletRegistry.BulletType.Bullet104AdoublePellet

## ── 尺寸 ────────────────────────────────────────────────────────────────
## 画布 103 高 / 人物本体 99，和豆蔻完全一致（两人并排一样高）。
## 下面所有像素常量都在「79 高度参考空间」里，使用时统一乘 _art_k。
const ADOUBLE_HEIGHT: float = 103.0
const ADOUBLE_HEIGHT_REF: float = 79.0
## 2 倍空间里脚底到画布底边的留白，用来把脚底精确对回 y=0
const ADOUBLE_FOOT_PAD_PX: float = 4.0
## 待机左右摇摆幅度（度）/ 单程时长（秒）；呼吸起伏（像素）
## 比豆蔻略小：他是端着两把枪的待命姿势，晃太大就像在跳舞
const ADOUBLE_SWAY_DEG: float = 2.0
const ADOUBLE_SWAY_TIME: float = 1.7
const ADOUBLE_BREATH_PX: float = 0.75

## ── 两把枪的枪口锚点 ────────────────────────────────────────────────────
## 从烘焙贴图（133×206，脚底在 (66.5,202)）逐像素反算出来的：
##   上枪口 2 倍像素 (112.07, 81.32) → 相对脚底 (45.57, -120.68) → 显示 (22.79, -60.34)
##   下枪口 2 倍像素 (124.37, 100.54) → 相对脚底 (57.87, -101.46) → 显示 (28.94, -50.73)
## 再除以 _art_k(103/79) 得到下面这两组数。
## 别直接拿原图 814×1288 的像素算 —— 会漏掉画布 4px 留白，
## 算出来偏上约 2 像素，火光就会浮在枪口上方。
const GUN_UP_POS := Vector2(17.48, -46.28)
const GUN_UP_DEG: float = -22.0
const GUN_LOW_POS := Vector2(22.19, -38.91)
const GUN_LOW_DEG: float = -25.0

## ── 抬手预瞄（signal_attack_anim_start，真正出手前约 0.28 秒）──────────
## 枪不像飞镖需要翻腕蓄力，但完全没预备会显得「子弹凭空出现」。
## 只做一个极轻的「压枪」：身体朝枪口方向顶出去一点点，然后定住等开火。
const ADOUBLE_AIM_DEG: float = 0.7
const ADOUBLE_AIM_PUSH: float = 0.5
const ADOUBLE_AIM_TIME: float = 0.14

## ── 后坐（真正出手那一帧）───────────────────────────────────────────────
## 四拍：急促后坐 → 回弹①（反向过冲）→ 回弹②（幅度只剩三成）→ 归位。
## 合计 0.35 秒 < 两发间隔 0.42 秒，所以第二发一定接在第一发收完之后，
## 中间留 0.07 秒的静，节拍是「砰—砰」而不是糊成一下。
const ADOUBLE_RECOIL_HIT_TIME: float = 0.045
const ADOUBLE_RECOIL_BACK_TIME: float = 0.105
const ADOUBLE_RECOIL_SETTLE_TIME: float = 0.085
const ADOUBLE_RECOIL_RESTORE_TIME: float = 0.115

## 上枪：枪口高、力臂长 → 后坐更大，身体往上顶
const ADOUBLE_RECOIL_UP_DEG: float = -3.6
const ADOUBLE_RECOIL_UP_PUSH := Vector2(-2.2, -1.0)
const ADOUBLE_RECOIL_UP_SCALE := Vector2(1.035, 0.965)
## 下枪：枪口低、贴近重心 → 后坐小一点，身体往下沉
const ADOUBLE_RECOIL_LOW_DEG: float = -2.4
const ADOUBLE_RECOIL_LOW_PUSH := Vector2(-1.8, 0.7)
const ADOUBLE_RECOIL_LOW_SCALE := Vector2(1.025, 0.975)
## 回弹过冲：幅度约为上一段的 0.27 / 0.42，衰减振荡才像身体自己找平衡
const ADOUBLE_OVERSHOOT_DEG: float = 0.95
const ADOUBLE_OVERSHOOT2_DEG: float = -0.38
const ADOUBLE_OVERSHOOT_BACK_K: float = -0.30
const ADOUBLE_OVERSHOOT2_BACK_K: float = 0.11

## ── 枪口爆闪 ────────────────────────────────────────────────────────────
## 贴图 30×30，运行时 0.34→0.62（约 10→19 像素）。枪管直径在画面上只有 4 像素左右，
## 爆闪做 2~4 倍管径正好，再大就把整把枪吞掉。
const ADOUBLE_FLASH_FROM: float = 0.34
const ADOUBLE_FLASH_TO: float = 0.62
const ADOUBLE_FLASH_TIME: float = 0.085

## ── 冲击环 ──────────────────────────────────────────────────────────────
## 环负责「一下」的爆发感。比爆闪活得久一点、扩得远一点，把枪口那一团撑开。
const ADOUBLE_RING_FROM: float = 0.18
const ADOUBLE_RING_TO: float = 0.92
const ADOUBLE_RING_TIME: float = 0.17
const ADOUBLE_RING_ALPHA: float = 0.85

## ── 枪口烟 ──────────────────────────────────────────────────────────────
## 烟要**慢**：爆闪 0.085 秒就没了，烟拖到 0.34 秒，往枪口前方飘一段，
## 这样两发之间能看出「上一枪的烟还在」，交替感更强。
const ADOUBLE_SMOKE_FROM: float = 0.34
const ADOUBLE_SMOKE_TO: float = 0.66
const ADOUBLE_SMOKE_TIME: float = 0.34
const ADOUBLE_SMOKE_DRIFT := Vector2(7.0, -3.5)
const ADOUBLE_SMOKE_ALPHA: float = 0.55

## ── 枪口火星（爆闪边缘崩出来的点）────────────────────────────────────────
const ADOUBLE_SPARK_FROM: float = 0.30
const ADOUBLE_SPARK_TO: float = 0.62
const ADOUBLE_SPARK_TIME: float = 0.13

## ── 子弹速度线 ──────────────────────────────────────────────────────────
## 铺在枪口到子弹之间，读作「刚从管子口被推出去」。不跟着子弹飞，
## 只在枪口停 0.1 秒就淡掉——跟着飞会变成一条白杠一直拖在屏幕上。
const ADOUBLE_STREAK_SPAN: float = 22.0
const ADOUBLE_STREAK_TEX_LEN: float = 46.0
const ADOUBLE_STREAK_ALPHA: float = 0.5
const ADOUBLE_STREAK_HOLD: float = 0.10

## ── 接地投影 ────────────────────────────────────────────────────────────
## 立绘本身没有影子，站草坪上像贴纸浮着。挂在待机摇摆那层：
## 开火时身体后坐、影子不动，才有踩住地的感觉。
const ADOUBLE_SHADOW_POS := Vector2(1.0, -1.0)

## 调试打印（枪口坐标 / 出手间隔）。定型后保持 false
const ADOUBLE_DEBUG: bool = false

@onready var attack_component: AttackComponentBulletBase = $AttackComponent

## 立绘尺寸换算系数 = 当前高度 / 参考高度
var _art_k: float = 1.0
## 外层：待机摇摆。内层：开火后坐。两层分开，两个旋转才不会互相打断
var _sway_pivot: Node2D = null
var _fire_pivot: Node2D = null
var _art: Sprite2D = null
## 闭眼整图（平时隐藏，眨眼时盖在 idle 上闪一下）
var _blink: Sprite2D = null
var _blink_timer: Timer = null
## 后坐补间 / 预瞄补间
var _recoil_tween: Tween = null
var _aim_tween: Tween = null
## 本周期内已经打了几发（0=还没打）。每次动画开始归零，
## 这样「第 1 发上枪、第 2 发下枪」是**按发数**定的，不靠奇偶漂移
var _shot_in_cycle: int = 0
## 子弹出生点 marker（原场景只有 1 个，两发共用，开火前挪到对应枪口）
var _bullet_marker: Marker2D = null
var _flash: Sprite2D = null
var _smoke: Sprite2D = null
var _ring: Sprite2D = null
var _spark: Sprite2D = null
var _streak: Sprite2D = null
var _flash_tween: Tween = null
var _smoke_tween: Tween = null
var _ring_tween: Tween = null
var _spark_tween: Tween = null
var _streak_tween: Tween = null


## 初始化正常出战角色信号连接
func ready_norm_signal_connect():
	super()
	signal_update_speed.connect(attack_component.owner_update_speed)


func _ready() -> void:
	super()
	if not adouble_enable:
		return
	_apply_adouble_art()
	if attack_component == null:
		return
	# 弹药换成竹节弹丸。只改这一株的引用，其他豌豆系植物不受影响
	attack_component.attack_bullet_type = ADOUBLE_BULLET_TYPE
	if not attack_component.markers_2d_bullet.is_empty():
		_bullet_marker = attack_component.markers_2d_bullet[0]
	# 动画一开始（早于真正出手 约 0.28 秒）：归零发数 + 轻微压枪预瞄
	attack_component.signal_attack_anim_start.connect(_on_attack_anim_start)
	# 真正生成子弹那一帧：挪 marker → 后坐 → 爆闪/环/烟/火星/速度线
	attack_component.signal_shoot_bullet.connect(_on_shoot_bullet)
	# 目标没了要把预瞄姿势收回来，否则会一直歪着
	attack_component.signal_change_is_attack.connect(_on_is_attack_changed)


# ══════════════════════════════════════════════════════════════════════════
# 换装
# ══════════════════════════════════════════════════════════════════════════

## 隐藏散件版身体，换成整图立绘并加轻微待机动作。
## 不改 .tscn 结构，全部运行期完成；回退只需把 adouble_enable 置 false。
func _apply_adouble_art() -> void:
	var body_correct: Node2D = get_node_or_null("Body/BodyCorrect") as Node2D
	if body_correct == null:
		body_correct = find_child("BodyCorrect", true, false) as Node2D
	if body_correct == null:
		push_warning("阿双：找不到 BodyCorrect，跳过换装")
		return

	var tex: Texture2D = load(ADOUBLE_ART_PATH) as Texture2D
	if tex == null:
		push_warning("阿双：贴图没找到或还没被导入 → %s" % ADOUBLE_ART_PATH)
		return

	# 1) 原散件整体隐藏（连同上百条轨道一起藏掉）
	body_correct.visible = false

	_art_k = ADOUBLE_HEIGHT / ADOUBLE_HEIGHT_REF

	var holder: Node2D = body_correct.get_parent()
	var art_scale: float = ADOUBLE_HEIGHT / float(tex.get_height())
	# 画布上下各留了 FOOT_PAD 的描边余量，脚底要减掉这段才正好落回 y=0
	var art_local_y: float = -ADOUBLE_HEIGHT * 0.5 + ADOUBLE_FOOT_PAD_PX * art_scale

	# 2) 两层节点，都以脚底为原点，所以两层旋转都是绕地面转
	_sway_pivot = Node2D.new()
	_sway_pivot.name = "AdoublePivot"
	holder.add_child(_sway_pivot)

	# 反向版（plant_049 双发_反向）的 BodyCorrect 是 scale.x = -1 的镜像。
	# 整图立绘挂在 Body 下、不继承 BodyCorrect 的变换，这里手动补镜像，
	# 否则反向双发（图鉴 Card4）会朝反方向举枪。枪口锚点和特效都挂在这层下面，
	# 镜像后一起翻过去，坐标不用另算。
	if body_correct.scale.x < 0.0:
		_sway_pivot.scale = Vector2(-1.0, 1.0)

	_build_shadow_node(_sway_pivot)

	_fire_pivot = Node2D.new()
	_fire_pivot.name = "AdoubleFire"
	_sway_pivot.add_child(_fire_pivot)

	# 3) 整图。Sprite2D 默认居中，中心上移半个身高，脚底正好落在 y=0
	_art = Sprite2D.new()
	_art.name = "AdoubleIdle"
	_art.texture = tex
	_art.scale = Vector2(art_scale, art_scale)
	_art.position = Vector2(0.0, art_local_y)
	_fire_pivot.add_child(_art)

	_build_blink_node(tex)

	# 4) 待机：左右摇摆 + 呼吸起伏
	var sway: Tween = create_tween().set_loops()
	sway.tween_property(_sway_pivot, "rotation", deg_to_rad(ADOUBLE_SWAY_DEG), ADOUBLE_SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	sway.tween_property(_sway_pivot, "rotation", deg_to_rad(-ADOUBLE_SWAY_DEG), ADOUBLE_SWAY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	var breath: Tween = create_tween().set_loops()
	breath.tween_property(_art, "position:y", art_local_y - ADOUBLE_BREATH_PX, 0.9) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	breath.tween_property(_art, "position:y", art_local_y, 0.9) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	# 5) 特效层（都挂在开火节点下，跟着后坐一起动）
	_build_fx_nodes()


## 闭眼整图。挂在 _art 底下当子节点：
## 这样它自动继承立绘的缩放、位置、呼吸起伏、后坐、摇摆，
## 眨眼那一帧绝不会因为父节点正在位移而错开。
func _build_blink_node(idle_tex: Texture2D) -> void:
	if _art == null:
		return
	if not ResourceLoader.exists(ADOUBLE_BLINK_PATH):
		push_warning("阿双：眨眼贴图不存在 → %s" % ADOUBLE_BLINK_PATH)
		return
	var tex: Texture2D = load(ADOUBLE_BLINK_PATH) as Texture2D
	if tex == null:
		return
	# 尺寸对不上就别叠，宁可没有眨眼也不要错位
	if tex.get_size() != idle_tex.get_size():
		push_warning("阿双：眨眼贴图尺寸 %s 与立绘 %s 不一致，跳过眨眼"
			% [str(tex.get_size()), str(idle_tex.get_size())])
		return
	_blink = Sprite2D.new()
	_blink.name = "AdoubleBlink"
	_blink.texture = tex
	_blink.position = Vector2.ZERO
	_blink.scale = Vector2.ONE
	_blink.z_index = 1
	_blink.visible = false
	_art.add_child(_blink)
	_start_blink_loop()


## 随机间隔眨眼。间隔和闭眼时长都是小数值，别每帧算
func _start_blink_loop() -> void:
	if _blink == null:
		return
	_blink_timer = Timer.new()
	_blink_timer.name = "AdoubleBlinkTimer"
	_blink_timer.one_shot = true
	_blink_timer.wait_time = randf_range(ADOUBLE_BLINK_GAP_MIN, ADOUBLE_BLINK_GAP_MAX)
	add_child(_blink_timer)
	_blink_timer.timeout.connect(_on_blink_timeout)
	_blink_timer.start()


func _on_blink_timeout() -> void:
	if not is_instance_valid(_blink):
		return
	_blink.visible = true
	await get_tree().create_timer(ADOUBLE_BLINK_HOLD).timeout
	# 等这 0.12 秒里可能已经被打死、被铲掉，先判活再复原
	if not is_instance_valid(_blink):
		return
	_blink.visible = false
	if is_instance_valid(_blink_timer):
		_blink_timer.wait_time = randf_range(ADOUBLE_BLINK_GAP_MIN, ADOUBLE_BLINK_GAP_MAX)
		_blink_timer.start()


## 特效件全部挂到开火节点下。缺图就静默跳过，不影响主体
func _build_fx_nodes() -> void:
	if _fire_pivot == null:
		return
	_flash = _make_fx_sprite("AdoubleMuzzleFlash", ADOUBLE_FX_FLASH, 9)
	_ring = _make_fx_sprite("AdoubleShockRing", ADOUBLE_FX_RING, 8)
	_smoke = _make_fx_sprite("AdoubleMuzzleSmoke", ADOUBLE_FX_SMOKE, 7)
	_spark = _make_fx_sprite("AdoubleMuzzleSpark", ADOUBLE_FX_SPARK, 10)
	_streak = _make_fx_sprite("AdoubleStreak", ADOUBLE_FX_STREAK, 6)


func _make_fx_sprite(node_name: String, path: String, z: int) -> Sprite2D:
	if not ResourceLoader.exists(path):
		push_warning("阿双：特效贴图不存在 → %s" % path)
		return null
	var tex: Texture2D = load(path) as Texture2D
	if tex == null:
		push_warning("阿双：特效贴图加载失败（可能还没导入）→ %s" % path)
		return null
	var sp := Sprite2D.new()
	sp.name = node_name
	sp.texture = tex
	sp.visible = false
	sp.z_index = z
	_fire_pivot.add_child(sp)
	return sp


## 脚下的软投影。缺图就整段跳过
func _build_shadow_node(parent: Node2D) -> void:
	if not ResourceLoader.exists(ADOUBLE_FX_SHADOW):
		return
	var tex: Texture2D = load(ADOUBLE_FX_SHADOW) as Texture2D
	if tex == null:
		return
	var sp := Sprite2D.new()
	sp.name = "AdoubleShadow"
	sp.texture = tex
	sp.position = _art_pos(ADOUBLE_SHADOW_POS)
	## 影子跟着人物一起放大，否则 99px 高的角色会踩在一小片影子上
	sp.scale = Vector2(_art_k, _art_k)
	sp.z_index = -1
	parent.add_child(sp)


# ══════════════════════════════════════════════════════════════════════════
# 开火链路
# ══════════════════════════════════════════════════════════════════════════

## 动画开始：归零发数 + 轻微压枪预瞄。
## 归零放这里而不是靠抬头枪偶数轮换，是为了「跳过一发」时配对不会错位。
func _on_attack_anim_start() -> void:
	_shot_in_cycle = 0
	if _fire_pivot == null:
		return
	# 上一轮的后坐若还没收完，先掐掉，否则两段补间同时写 rotation 会抖
	_kill_recoil()
	_kill_aim()
	_aim_tween = create_tween()
	_aim_tween.tween_property(_fire_pivot, "rotation", deg_to_rad(ADOUBLE_AIM_DEG), ADOUBLE_AIM_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_aim_tween.parallel().tween_property(_fire_pivot, "position:x", ADOUBLE_AIM_PUSH * _art_k, ADOUBLE_AIM_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_aim_tween.parallel().tween_property(_fire_pivot, "position:y", 0.0, ADOUBLE_AIM_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)


## 真正生成子弹那一帧。
## 注意执行顺序：这个回调是在 AttackComponent._shoot_bullet() 里
## signal_shoot_bullet.emit() 期间跑的，而**读 marker 位置在 emit 之后**，
## 所以这里挪 marker 当帧就生效，子弹一定从这一发的那把枪口出来。
func _on_shoot_bullet() -> void:
	var use_upper: bool = (_shot_in_cycle % 2) == 0
	_shot_in_cycle += 1

	var muzzle: Vector2 = GUN_UP_POS if use_upper else GUN_LOW_POS
	var gun_deg: float = GUN_UP_DEG if use_upper else GUN_LOW_DEG

	_move_bullet_marker(muzzle)
	if _fire_pivot == null:
		return
	_kill_recoil()
	_kill_aim()
	_play_recoil(use_upper)
	_play_muzzle_fx(muzzle, gun_deg)
	if ADOUBLE_DEBUG:
		print("阿双第 %d 发：%s枪口 local=%s world=%s" % [
			_shot_in_cycle, "上" if use_upper else "下",
			str(_art_pos(muzzle)), str(_fire_pivot.to_global(_art_pos(muzzle)))])


## 把子弹出生点挪到当前枪口。
## 原场景里只有一个 Marker2DBullet，两发共用它；不挪的话两颗子弹会从
## 肚子前面同一个点冒出来，而火光却亮在两个不同高度——最典型的违和。
func _move_bullet_marker(muzzle: Vector2) -> void:
	if not is_instance_valid(_bullet_marker):
		return
	var pivot: Node2D = _fire_pivot if _fire_pivot != null else self
	_bullet_marker.global_position = pivot.to_global(_art_pos(muzzle))


## 身体后坐：急促往后 → 衰减振荡回正。
## 方向和幅度按「谁开的火」分开，这是两发能被读成「两下」的关键。
func _play_recoil(use_upper: bool) -> void:
	if _fire_pivot == null:
		return
	var deg: float = ADOUBLE_RECOIL_UP_DEG if use_upper else ADOUBLE_RECOIL_LOW_DEG
	var push: Vector2 = (ADOUBLE_RECOIL_UP_PUSH if use_upper else ADOUBLE_RECOIL_LOW_PUSH) * _art_k
	var squash: Vector2 = ADOUBLE_RECOIL_UP_SCALE if use_upper else ADOUBLE_RECOIL_LOW_SCALE

	_recoil_tween = create_tween()
	# 1) 后坐：CUBIC 缓出（前段极快），像被反作用力顶了一下
	_recoil_tween.tween_property(_fire_pivot, "rotation", deg_to_rad(deg), ADOUBLE_RECOIL_HIT_TIME) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_recoil_tween.parallel().tween_property(_fire_pivot, "position", push, ADOUBLE_RECOIL_HIT_TIME) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_recoil_tween.parallel().tween_property(_fire_pivot, "scale", squash, ADOUBLE_RECOIL_HIT_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	# 2) 回弹①：反向过冲，竖着拉一下，做出重量
	_recoil_tween.tween_property(_fire_pivot, "rotation", deg_to_rad(ADOUBLE_OVERSHOOT_DEG), ADOUBLE_RECOIL_BACK_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_recoil_tween.parallel().tween_property(_fire_pivot, "position", push * ADOUBLE_OVERSHOOT_BACK_K, ADOUBLE_RECOIL_BACK_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_recoil_tween.parallel().tween_property(_fire_pivot, "scale", Vector2(0.992, 1.008), ADOUBLE_RECOIL_BACK_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	# 3) 回弹②：再反向一次，幅度只剩三成，同时把挤压拉伸还原
	_recoil_tween.tween_property(_fire_pivot, "rotation", deg_to_rad(ADOUBLE_OVERSHOOT2_DEG), ADOUBLE_RECOIL_SETTLE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_recoil_tween.parallel().tween_property(_fire_pivot, "position", push * ADOUBLE_OVERSHOOT2_BACK_K, ADOUBLE_RECOIL_SETTLE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_recoil_tween.parallel().tween_property(_fire_pivot, "scale", Vector2.ONE, ADOUBLE_RECOIL_SETTLE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	# 4) 归位：余震收到 0
	_recoil_tween.tween_property(_fire_pivot, "rotation", 0.0, ADOUBLE_RECOIL_RESTORE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_recoil_tween.parallel().tween_property(_fire_pivot, "position", Vector2.ZERO, ADOUBLE_RECOIL_RESTORE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)


## 枪口上的五件套。全部以枪口为锚点、按枪管角度摆，所以换枪口常量时整套自动跟
func _play_muzzle_fx(muzzle: Vector2, gun_deg: float) -> void:
	var at: Vector2 = _art_pos(muzzle)
	_play_flash(at, gun_deg)
	_play_ring(at, gun_deg)
	_play_smoke(at, gun_deg)
	_play_spark(at)
	_play_streak(at, gun_deg)


func _play_flash(at: Vector2, gun_deg: float) -> void:
	if not is_instance_valid(_flash):
		return
	if _flash_tween != null and _flash_tween.is_valid():
		_flash_tween.kill()
	_flash.visible = true
	_flash.position = at
	_flash.rotation = deg_to_rad(gun_deg)
	_flash.scale = Vector2(ADOUBLE_FLASH_FROM, ADOUBLE_FLASH_FROM)
	_flash.modulate.a = 1.0
	_flash_tween = create_tween()
	## 起手就是最亮，然后撑开、淡掉
	_flash_tween.tween_property(_flash, "modulate:a", 0.0, ADOUBLE_FLASH_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	## 沿枪管方向再拉长一点，火光才有「喷」出去的方向
	_flash_tween.parallel().tween_property(_flash, "scale",
		Vector2(ADOUBLE_FLASH_TO * 1.18, ADOUBLE_FLASH_TO * 0.92), ADOUBLE_FLASH_TIME) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_flash_tween.tween_callback(_flash.hide)


func _play_ring(at: Vector2, gun_deg: float) -> void:
	if not is_instance_valid(_ring):
		return
	if _ring_tween != null and _ring_tween.is_valid():
		_ring_tween.kill()
	_ring.visible = true
	_ring.position = at
	_ring.rotation = deg_to_rad(gun_deg)
	_ring.scale = Vector2(ADOUBLE_RING_FROM, ADOUBLE_RING_FROM)
	_ring.modulate.a = ADOUBLE_RING_ALPHA
	_ring_tween = create_tween()
	_ring_tween.tween_property(_ring, "modulate:a", 0.0, ADOUBLE_RING_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_ring_tween.parallel().tween_property(_ring, "scale", Vector2(ADOUBLE_RING_TO, ADOUBLE_RING_TO), ADOUBLE_RING_TIME) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_ring_tween.tween_callback(_ring.hide)


func _play_smoke(at: Vector2, gun_deg: float) -> void:
	if not is_instance_valid(_smoke):
		return
	if _smoke_tween != null and _smoke_tween.is_valid():
		_smoke_tween.kill()
	_smoke.visible = true
	_smoke.position = at
	_smoke.rotation = deg_to_rad(gun_deg)
	_smoke.scale = Vector2(ADOUBLE_SMOKE_FROM, ADOUBLE_SMOKE_FROM)
	_smoke.modulate.a = ADOUBLE_SMOKE_ALPHA
	_smoke_tween = create_tween()
	_smoke_tween.tween_property(_smoke, "position", at + _art_pos(ADOUBLE_SMOKE_DRIFT), ADOUBLE_SMOKE_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_smoke_tween.parallel().tween_property(_smoke, "scale", Vector2(ADOUBLE_SMOKE_TO, ADOUBLE_SMOKE_TO), ADOUBLE_SMOKE_TIME) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_smoke_tween.parallel().tween_property(_smoke, "modulate:a", 0.0, ADOUBLE_SMOKE_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	_smoke_tween.tween_callback(_smoke.hide)


func _play_spark(at: Vector2) -> void:
	if not is_instance_valid(_spark):
		return
	if _spark_tween != null and _spark_tween.is_valid():
		_spark_tween.kill()
	_spark.visible = true
	_spark.position = at
	_spark.rotation = 0.0
	_spark.scale = Vector2(ADOUBLE_SPARK_FROM, ADOUBLE_SPARK_FROM)
	_spark.modulate.a = 0.9
	_spark_tween = create_tween()
	_spark_tween.tween_property(_spark, "modulate:a", 0.0, ADOUBLE_SPARK_TIME) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_spark_tween.parallel().tween_property(_spark, "scale", Vector2(ADOUBLE_SPARK_TO, ADOUBLE_SPARK_TO), ADOUBLE_SPARK_TIME) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_spark_tween.parallel().tween_property(_spark, "rotation", deg_to_rad(42.0), ADOUBLE_SPARK_TIME)
	_spark_tween.tween_callback(_spark.hide)


## 速度线：沿真实枪管角度铺在枪口前方，头朝枪口方向
func _play_streak(at: Vector2, gun_deg: float) -> void:
	if not is_instance_valid(_streak):
		return
	if _streak_tween != null and _streak_tween.is_valid():
		_streak_tween.kill()
	var dir: Vector2 = Vector2.RIGHT.rotated(deg_to_rad(gun_deg))
	var span: float = ADOUBLE_STREAK_SPAN * _art_k
	if span < 0.01:
		return
	var base_sx: float = span / ADOUBLE_STREAK_TEX_LEN
	_streak.visible = true
	## 贴图头在 +x，所以整段往前推一半，才从枪口起铺、不压进枪管里
	_streak.position = at + dir * (span * 0.5 + 1.0)
	_streak.rotation = dir.angle()
	_streak.scale = Vector2(base_sx, 1.0)
	_streak.modulate.a = ADOUBLE_STREAK_ALPHA
	_streak_tween = create_tween()
	_streak_tween.tween_property(_streak, "modulate:a", 0.0, ADOUBLE_STREAK_HOLD) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_streak_tween.parallel().tween_property(_streak, "scale:x", base_sx * 1.45, ADOUBLE_STREAK_HOLD) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_streak_tween.tween_callback(_streak.hide)


## 能不能攻击变了：目标没了要把预瞄姿势收回来
func _on_is_attack_changed(value: bool) -> void:
	if value or _fire_pivot == null:
		return
	if _recoil_tween != null and _recoil_tween.is_running():
		return
	_kill_aim()
	_aim_tween = create_tween()
	_aim_tween.tween_property(_fire_pivot, "rotation", 0.0, 0.18) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_aim_tween.parallel().tween_property(_fire_pivot, "position", Vector2.ZERO, 0.18) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_aim_tween.parallel().tween_property(_fire_pivot, "scale", Vector2.ONE, 0.18) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)


# ══════════════════════════════════════════════════════════════════════════
# 小工具
# ══════════════════════════════════════════════════════════════════════════

## 把「79 高度参考空间」里的坐标换算到当前立绘尺寸
func _art_pos(v: Vector2) -> Vector2:
	return v * _art_k


func _kill_recoil() -> void:
	if _recoil_tween != null and _recoil_tween.is_valid():
		_recoil_tween.kill()
	_recoil_tween = null


func _kill_aim() -> void:
	if _aim_tween != null and _aim_tween.is_valid():
		_aim_tween.kill()
	_aim_tween = null
