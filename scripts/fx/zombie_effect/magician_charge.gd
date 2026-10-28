class_name MagicianCharge
extends Node2D

## 魔术师僵尸杖尖的蓄力光球（纯程序化，不依赖贴图）。
##
## 立绘是一张整图，法杖没法真的抬起来，所以「挥动法杖蓄力」这一段靠三样东西撑起来：
##   1. 立绘整体后仰→前压（由僵尸脚本补间 pivot 完成）
##   2. 杖尖这颗光球由小到大、越转越快（就是本节点）
##   3. 光球撑满时整条紫电抽出（见 MagicianLightning）
##
## 用法：挂到杖尖节点下，`level` 0→1 补间即可；释放后补间回 0 再隐藏。

## 光球最大半径（像素）
@export var max_radius: float = 15.0
## 白芯色
@export var core_color: Color = Color(0.97, 0.92, 1.0, 1.0)
## 主紫色
@export var bolt_color: Color = Color(0.74, 0.45, 1.0, 1.0)
## 外围光晕紫
@export var glow_color: Color = Color(0.42, 0.16, 0.82, 1.0)

## 蓄力强度 0→1，由外部补间驱动
var level: float = 0.0:
	set(value):
		level = clampf(value, 0.0, 1.0)
		queue_redraw()

## 符文环旋转角度
var _spin: float = 0.0
## 每帧重掷的电弧偏移，让光球一直在「噼啪」
var _arc_offsets: Array[float] = []
## 电弧重掷计时
var _flicker: float = 0.0


func _ready() -> void:
	## 画在立绘之上（立绘是本节点的兄弟，靠后的排在后面）
	z_index = 5
	for i in 8:
		_arc_offsets.append(randf_range(-1.0, 1.0))
	queue_redraw()


func _process(delta: float) -> void:
	if level <= 0.001:
		return
	_spin += delta * lerpf(2.4, 7.0, level)
	_flicker -= delta
	if _flicker <= 0.0:
		_flicker = 0.05
		for i in _arc_offsets.size():
			_arc_offsets[i] = randf_range(-1.0, 1.0)
	queue_redraw()


func _draw() -> void:
	if level <= 0.001:
		return
	var r: float = 2.0 + max_radius * level
	# 三层光晕，从外到内逐渐收敛，读起来才像「能量在聚集」而不是一个圆点
	draw_circle(Vector2.ZERO, r * 2.30, _a(glow_color, 0.10 * level))
	draw_circle(Vector2.ZERO, r * 1.55, _a(glow_color, 0.22 * level))
	draw_circle(Vector2.ZERO, r * 1.10, _a(bolt_color, 0.55 * level))
	draw_circle(Vector2.ZERO, r * 0.55, _a(core_color, 0.95 * level))

	# 符文环：两段圆弧，随强度加速旋转
	var ring_r: float = r * 1.85
	var ring_alpha: float = 0.55 * level
	for i in 2:
		var start: float = _spin + PI * float(i)
		draw_arc(Vector2.ZERO, ring_r, start, start + PI * 0.62, 18,
			_a(bolt_color, ring_alpha), 1.8, true)

	# 八条放射电弧，长度随抖动变化
	for i in _arc_offsets.size():
		var ang: float = TAU * float(i) / 8.0 + _spin * 0.35
		var dir: Vector2 = Vector2.from_angle(ang)
		var len_a: float = r * (1.15 + 0.45 * absf(_arc_offsets[i]))
		draw_line(dir * r * 0.9, dir * len_a, _a(core_color, 0.65 * level), 1.6, true)


func _a(color: Color, alpha: float) -> Color:
	return Color(color.r, color.g, color.b, clampf(alpha, 0.0, 1.0))
