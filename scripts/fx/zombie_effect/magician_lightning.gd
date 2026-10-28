class_name MagicianLightning
extends Node2D

## 魔术师僵尸的紫电，纯程序化绘制，不依赖贴图；只负责表现，不结算伤害。
## 用法：`setup(杖尖全局坐标, 命中点全局坐标)` 之后 `cast()`，播完自己 queue_free。
##
## 三段式：
##   0.00→0.30  紫电从杖尖「抽」出去，沿途带抖动的锯齿分叉，命中点爆一圈紫光
##   0.30→0.70  保持抖动，亮度衰减
##   0.70→1.00  整条淡出
## 锯齿每 0.045 秒重建一次 —— 不动的话会读成一根静止的紫色棍子。

## 整段演出时长（秒）
@export var duration: float = 0.55
## 白芯色（最内层，最亮）
@export var core_color: Color = Color(0.94, 0.88, 1.0, 1.0)
## 主紫色
@export var bolt_color: Color = Color(0.72, 0.42, 1.0, 1.0)
## 外围光晕紫
@export var glow_color: Color = Color(0.45, 0.18, 0.85, 1.0)
## 折线每段的抖动幅度（像素）
@export var jitter: float = 13.0
## 主电干的分段数
@export var segment_count: int = 14

## 目标点（相对本节点）
var _to: Vector2 = Vector2.ZERO
## 0→1 播放进度
var _progress: float = 0.0
## 抖动重建计时
var _flicker: float = 0.0
## 主电干 + 两条分叉
var _bolts: Array[PackedVector2Array] = []
var _tween: Tween


func _ready() -> void:
	## 画在僵尸前面，否则被立绘压住只剩一点点边
	z_index = 50
	visible = false


## 设置起止点（都用全局坐标）
func setup(from_global: Vector2, to_global: Vector2) -> void:
	global_position = from_global
	_to = to_global - from_global
	_rebuild_bolts()
	queue_redraw()


## 开始播放，播完自动销毁
func cast() -> void:
	visible = true
	_progress = 0.0
	_rebuild_bolts()
	queue_redraw()
	_tween = create_tween()
	_tween.tween_method(_set_progress, 0.0, 1.0, duration)
	_tween.tween_callback(queue_free)


func _set_progress(value: float) -> void:
	_progress = value
	_flicker -= get_process_delta_time()
	if _flicker <= 0.0:
		_flicker = 0.045
		_rebuild_bolts()
	queue_redraw()


## 重建折线：主干一条 + 两条从中段岔出去的分叉，都不超过目标点
func _rebuild_bolts() -> void:
	_bolts.clear()
	if _to.length() < 1.0:
		return
	_bolts.append(_make_bolt(0.0, 1.0, 1.0))
	# 分叉：从主干 0.45 / 0.62 处出发，短一截，抖动更小
	_bolts.append(_make_bolt(0.45, 0.78, 0.55))
	_bolts.append(_make_bolt(0.62, 0.92, 0.45))


## [param t0] 起点在整条上的比例；[param t1] 终点比例；[param amp] 抖动倍率
func _make_bolt(t0: float, t1: float, amp: float) -> PackedVector2Array:
	var dir: Vector2 = _to.normalized()
	var normal: Vector2 = dir.orthogonal()
	var pts := PackedVector2Array()
	var n: int = maxi(3, segment_count)
	for i in n + 1:
		var t: float = lerpf(t0, t1, float(i) / float(n))
		var base: Vector2 = _to * t
		# 两端附近的抖动压小，不然会和杖尖/命中点脱开
		var taper: float = sin(PI * float(i) / float(n))
		var off: float = randf_range(-1.0, 1.0) * jitter * amp * taper
		pts.append(base + normal * off)
	return pts


func _draw() -> void:
	var p: float = _progress
	if p <= 0.0 or p >= 1.0:
		return
	# 抽出长度：前 30% 从杖尖推到命中点
	var grow: float = clampf(p / 0.30, 0.0, 1.0)
	# 亮度：前 10% 拉满，之后按 1.0 → 0 衰减（幂次让尾巴拖得久一点）
	var alpha: float = clampf(p / 0.10, 0.0, 1.0) * pow(1.0 - p, 0.85)
	if alpha <= 0.001:
		return

	# 抽出去的那一截：按 grow 截断折线
	for bolt: PackedVector2Array in _bolts:
		var cut: PackedVector2Array = _clip_by_progress(bolt, grow)
		if cut.size() < 2:
			continue
		# 图层从外到内：光晕 → 主紫 → 白芯
		draw_polyline(cut, _a(glow_color, alpha * 0.30), 16.0, true)
		draw_polyline(cut, _a(bolt_color, alpha * 0.85), 7.0, true)
		draw_polyline(cut, _a(core_color, alpha), 2.6, true)

	# 命中点：紫光爆点 + 一圈外扩环，只在前 55% 存在
	_draw_impact(p, alpha)
	# 杖尖：蓄力余光的残留小光点
	draw_circle(Vector2.ZERO, 7.0 * (1.0 + 0.4 * sin(p * 40.0)), _a(core_color, alpha * 0.55))


func _draw_impact(p: float, alpha: float) -> void:
	var f: float = clampf(p / 0.55, 0.0, 1.0)
	if f >= 1.0:
		return
	var burst: float = pow(1.0 - f, 1.6) * alpha
	draw_circle(_to, lerpf(10.0, 34.0, f), _a(glow_color, burst * 0.55))
	draw_circle(_to, lerpf(5.0, 15.0, f), _a(core_color, burst * 0.85))
	draw_arc(_to, lerpf(14.0, 52.0, f), 0.0, TAU, 28, _a(bolt_color, burst * 0.7), 3.0, true)
	# 四向小电弧
	for i in 4:
		var ang: float = TAU * float(i) / 4.0 + 0.4
		var d: Vector2 = Vector2.from_angle(ang)
		draw_line(_to + d * 8.0, _to + d * lerpf(16.0, 40.0, f), _a(core_color, burst), 2.0, true)


## 按比例截断折线（用于「电从杖尖抽出去」的过程）
func _clip_by_progress(pts: PackedVector2Array, ratio: float) -> PackedVector2Array:
	if ratio >= 1.0:
		return pts
	var out := PackedVector2Array()
	var total: int = pts.size() - 1
	var keep: float = float(total) * ratio
	for i in total + 1:
		if float(i) <= keep:
			out.append(pts[i])
		else:
			var frac: float = keep - float(i - 1)
			if frac > 0.0 and i > 0:
				out.append(pts[i - 1].lerp(pts[i], frac))
			break
	return out


func _a(color: Color, alpha: float) -> Color:
	return Color(color.r, color.g, color.b, clampf(alpha, 0.0, 1.0))
