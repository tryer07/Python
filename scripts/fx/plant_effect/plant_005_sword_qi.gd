class_name Plant005SwordQi
extends Node2D

## 裴无咎（埋锋将军）的出手表现，分前后两段：
##   前段 p 0→0.24  刀锋入土 —— 一道自上而下收尖的光轨 + 触地点炸开的地面裂口
##   后段 p 0.16→1  剑气炸开 —— 爆闪 + 冲击环 + 八道外飞弧刃
## 纯程序化绘制，不依赖任何贴图；只负责表现，不结算伤害。
## 圆形绘制在 _ready 里压成 240×300 的椭圆比例，正好铺满 3×3 判定框。

## 剑气最远半径（像素），配合节点缩放即 3×3 的 240×300
@export var reach: float = 145.0
## 弧刃数量
@export_range(1, 16) var blade_count: int = 8
## 单道弧刃的半张角（度）。
## 8 道时上限 22.5°，取 20° —— 间隙仍有 2.5°，但比 18° 明显更「满」
@export_range(5.0, 40.0) var blade_half_angle_deg: float = 20.0
## 弧刃最厚处（像素）。上一版 18 在 0.35 显示缩放下只剩 6px，太细读不出刀气
@export var blade_thickness: float = 30.0
## 整段演出时长（秒）：入土 + 剑气
@export var duration: float = 0.55
## 刃口亮色
@export var core_color: Color = Color(1.0, 1.0, 1.0, 1.0)
## 外围青光
@export var glow_color: Color = Color(0.34, 0.78, 0.92, 1.0)

## 刀尖位置 = 立绘里唐刀插进地面的那一点（相对判定框中心，未经 scale 的局部坐标）。
## 由 potato_mine_stab.png 实测反算：烘焙画布刀尖 (129.4, 226.6)／地面线 227.1，
## 即比中线右 9.4px、比地面高 0.5px；×0.5 显示缩放 → 右 4.7、高 0.25；
## 再叠加压刀下沉 5px（世界 y = 7 - 0.25 + 5 = 11.75），最后除回节点 x 缩放 0.83。
const STAB_TIP: Vector2 = Vector2(5.7, 61.8)

## 0→1 的播放进度
var _progress: float = 0.0
## 起旋角，每次爆炸随机一点，连爆不会完全一样
var _spin: float = 0.0
var _tween: Tween


func _ready() -> void:
	# 把圆压成 240 宽 × 290 高的椭圆，贴合 3×3 判定框
	scale = Vector2(0.83, 1.0)
	# ⚠️ 上一版这里是 z_index = -2（压到立绘后面），本意是让十字光不糊脸，
	# 但代价是**八道弧刃也一起被角色挡住了** —— 立绘缩到 84 高之后占的画面很小，
	# 刃被压在身后只剩轮廓外一圈细边，实际读作「几乎看不见的淡光」。
	# 现在改成画在立绘前面（z_index = 3），用「刃从盘心外飞」的构图避免糊脸：
	# 弧刃起跳半径已拉到 reach*0.30 之外，中间那块正好空出来给角色。
	z_index = 3
	visible = false


## 释放一次剑气；重复调用会从头重播。
func burst() -> void:
	if _tween != null and _tween.is_valid():
		_tween.kill()
	visible = true
	_progress = 0.0
	_spin = deg_to_rad(randf_range(-10.0, 10.0))
	queue_redraw()
	_tween = create_tween()
	_tween.tween_method(_set_progress, 0.0, 1.0, duration) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_tween.tween_callback(queue_free)


func _set_progress(value: float) -> void:
	_progress = value
	queue_redraw()


func _draw() -> void:
	if _progress <= 0.0 or _progress >= 1.0:
		return
	var p: float = _progress
	# 刀已经在立绘里插进地面了，这里从「刀尖触地的裂口」直接起
	_draw_ground_crack(p)
	# 剑气整体错后半拍，让地裂先被看见
	var q: float = clampf((p - 0.05) / 0.95, 0.0, 1.0)
	if q <= 0.0:
		return
	# 顺序即图层：爆闪在最底，环在中，刃在最上
	_draw_flash(q)
	_draw_ring(q)
	_draw_blades(q)


## 地面裂口：刀尖处炸开的三圈扁平冲击波 + 一记贴地闪光。
## 用压扁的椭圆而不是圆 —— 这是俯视透视下的地面，圆环会被读成球。
func _draw_ground_crack(p: float) -> void:
	var fl: float = clampf(p / 0.14, 0.0, 1.0)
	if fl < 1.0:
		draw_colored_polygon(
			_ellipse_points(STAB_TIP, lerpf(30.0, 96.0, fl), lerpf(9.0, 26.0, fl), 24),
			_with_alpha(core_color, (1.0 - fl) * 0.75))
	for i in 3:
		var rp: float = clampf((p - 0.04 * float(i)) / 0.58, 0.0, 1.0)
		if rp <= 0.0 or rp >= 1.0:
			continue
		# 138 是能塞进 3×3 的上限：138×0.83 + 刀尖偏移 4.7 ≈ 119.2，刚好压在半宽 120 以内
		var rx: float = lerpf(18.0, 138.0, rp)
		var a: float = (1.0 - rp) * 0.7
		var w: float = lerpf(6.0, 1.0, rp)
		var pts: PackedVector2Array = _ellipse_points(STAB_TIP, rx, rx * 0.26, 36)
		draw_polyline(pts, _with_alpha(glow_color, a * 0.8), w, true)
		draw_polyline(pts, _with_alpha(core_color, a), maxf(w * 0.4, 0.8), true)


## 刀尖处的一记「星芒」——热斑 + 两道交叉光，只在前 1/4 段时间可见。
## 现在整层画在立绘前面，所以十字不再靠「被身体挡住」来收边，
## 而是直接把长度压短（reach*0.26），让它停在角色躯干范围内不乱窜。
func _draw_flash(p: float) -> void:
	var fp: float = clampf(p / 0.24, 0.0, 1.0)
	if fp >= 1.0:
		return
	var a: float = (1.0 - fp) * 0.95
	draw_circle(
		STAB_TIP,
		reach * 0.18 * (1.0 + fp * 1.2),
		_with_alpha(core_color, a * 0.55))
	for i in 2:
		# 十字故意转 45°：正十字会和判定框的边平行，读成「记号」；斜十字才读成爆点
		var ang: float = _spin + PI * 0.25 + float(i) * PI * 0.5 + fp * 0.45
		var dir: Vector2 = Vector2.from_angle(ang)
		var half_len: float = reach * 0.26 * (1.0 + fp * 0.5)
		var half_w: float = (lerpf(11.0, 2.0, fp)) * 0.5
		var normal: Vector2 = dir.orthogonal() * half_w
		var quad := PackedVector2Array([
			STAB_TIP - dir * half_len + normal,
			STAB_TIP + dir * half_len + normal,
			STAB_TIP + dir * half_len - normal,
			STAB_TIP - dir * half_len - normal,
		])
		draw_colored_polygon(quad, _with_alpha(core_color, a))


## 冲击环：前 60% 时间走完半径，剩下只做淡出，读起来才像冲击波。
## 线宽和亮度都压在弧刃之下 —— 否则它会抢成主角，整招读成防御罩。
func _draw_ring(p: float) -> void:
	var rp: float = clampf(p / 0.78, 0.0, 1.0)
	if rp >= 1.0:
		return
	var radius: float = lerpf(reach * 0.14, reach, minf(rp / 0.60, 1.0))
	var a: float = pow(1.0 - rp, 1.35) * 0.72
	var width: float = lerpf(9.0, 1.6, rp)
	draw_arc(Vector2.ZERO, radius, 0.0, TAU, 72, _with_alpha(glow_color, a * 0.8), width, true)
	draw_arc(Vector2.ZERO, radius, 0.0, TAU, 72, _with_alpha(core_color, a), maxf(width * 0.45, 1.0), true)


## 八道外飞弧刃：外缘亮、两端收尖，用来读成「剑气」而不是「爆炸」。
## 三道一组错开半径（lane），否则八道刃永远同半径同速度，会读成一条旋转的链子。
func _draw_blades(p: float) -> void:
	# 比冲击环晚半拍起跳：先炸开，再飞刃
	var bp: float = clampf((p - 0.04) / 0.88, 0.0, 1.0)
	if bp <= 0.0:
		return
	# 前 55% 就把半径推到框边，之后停在边上淡出 —— 否则刃还没到位就看不见了
	# 0.90 是因为刃口还有 12% 外凸，这样八道刃刚好顶到 3×3 边界而不越出
	# ⚠️ 起跳半径从 0.30 收到 0.16：立绘只有 84 高、角色占画面很小，
	# 从 0.30 起跳会让刃整圈飘在角色外面，读作「身边有一圈特效」而不是「从身上炸出来」
	var fly: float = minf(bp / 0.55, 1.0)
	var lead: float = lerpf(reach * 0.16, reach * 0.90, fly)
	# 起手 10% 内把透明度拉满，避免弧刃凭空弹出
	var a: float = clampf(bp / 0.10, 0.0, 1.0) * (1.0 - pow(bp, 2.4))
	var thickness: float = blade_thickness * lerpf(1.0, 0.50, fly)
	var step: float = TAU / float(blade_count)
	for i in blade_count:
		# 相邻刃的起旋角只差一点点、半径错开一点 —— 读作一层层推出去，而不是同步旋转
		var center: float = _spin + step * float(i) + bp * 0.22
		var lane: float = 1.0 - 0.07 * float(i % 3)
		_draw_blade(center, lead * lane, thickness * lane, a)
	# 起手那一下的「一整圈」青光：八道刃单看有间隙，加这一圈把「炸开」的势能补上，
	# 只在前 30% 存在，亮度迅速衰减，不会读成防御罩
	var halo: float = clampf(1.0 - bp / 0.30, 0.0, 1.0)
	if halo > 0.0:
		draw_arc(Vector2.ZERO, reach * 0.72, 0.0, TAU, 64,
			_with_alpha(glow_color, 0.42 * halo * halo), 12.0, true)


## 单道弧刃：沿弧线铺点，外缘半径略凸，厚度向两端收敛成尖。
## 三层叠加 —— 外层青光铺底、中层亮青勾锋、内层白芯提亮。
## 上一版只有两层且外缘白线只有 2.4px（缩到 0.35 倍后不足 1px），读作「淡」。
func _draw_blade(center_angle: float, lead: float, thickness: float, a: float) -> void:
	const SEGMENTS: int = 12
	var half: float = deg_to_rad(blade_half_angle_deg)
	var outer := PackedVector2Array()
	var inner := PackedVector2Array()
	outer.resize(SEGMENTS + 1)
	inner.resize(SEGMENTS + 1)
	for s in SEGMENTS + 1:
		var t: float = float(s) / float(SEGMENTS)
		var ang: float = center_angle + (t - 0.5) * 2.0 * half
		var taper: float = pow(sin(PI * t), 0.55)
		var r_out: float = lead * (1.0 + 0.12 * taper)
		var r_in: float = r_out - maxf(thickness * taper, 0.8)
		var dir: Vector2 = Vector2.from_angle(ang)
		outer[s] = dir * r_out
		inner[s] = dir * r_in
	# 外缘过去、内缘回来，闭合成一条月牙带
	var poly := PackedVector2Array()
	poly.append_array(outer)
	for s in range(SEGMENTS, -1, -1):
		poly.append(inner[s])
	# 刃身：把原来 0.68 提到 0.92，缩到 0.35 倍后仍是一块明确的青蓝刀气
	draw_colored_polygon(poly, _with_alpha(glow_color, a * 0.92))
	# 刃口：青色描边＋白芯双层，白芯线宽 3.6（显示后约 1.3px）
	draw_polyline(outer, _with_alpha(glow_color, a), 6.4, true)
	draw_polyline(outer, _with_alpha(core_color, a), 3.6, true)


## 椭圆上的闭合点串，用来画贴地的扁平冲击波。
func _ellipse_points(center: Vector2, rx: float, ry: float, segments: int) -> PackedVector2Array:
	var pts := PackedVector2Array()
	pts.resize(segments + 1)
	for i in segments + 1:
		var ang: float = TAU * float(i) / float(segments)
		pts[i] = center + Vector2(cos(ang) * rx, sin(ang) * ry)
	return pts


func _with_alpha(color: Color, alpha: float) -> Color:
	return Color(color.r, color.g, color.b, clampf(alpha, 0.0, 1.0))
