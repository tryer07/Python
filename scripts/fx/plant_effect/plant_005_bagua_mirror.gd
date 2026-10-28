extends Node2D
class_name Plant005BaguaMirror

## 裴无咎胸前的八卦镜 —— 感应预警。
##
## 规则：
##   1. 场上没有僵尸 → 只留一丝冷光，几乎看不出在亮
##   2. 有僵尸 → 开始预警，**最近的僵尸越近，预警越急、越亮**
##   3. 坐姿（准备期）同样预警，不区分姿态
##   4. 跪地（stab）姿态把手压在镜面上 → 镜光淡出，否则会在手背上发光
##
## 画法要点（上一版读作「贴了个发光糖纸」的原因）：
##   - 旧版是整个盘面铺一块纯色半透明圆 + 一道正弦圆环，没有结构
##   - 现在拆成：盘底补光 → 盘沿高光环（贴着金属边）→ 盘中卦纹扫光 → 镜心
##   - 关键：光只落在**盘面内侧**（<= 0.92r），盘沿用描边对齐金属边，
##     这样光看起来是「从盘里透出来」，而不是「在胸前糊了一团」

## 镜心（立绘 Sprite 局部像素坐标）
@export var mirror_pos: Vector2 = Vector2(6.0, 13.0)
## 镜盘半径（立绘局部像素）。父节点按姿态传入
@export var mirror_radius: float = 16.0
## 场上完全没有僵尸时的静止亮度
@export var idle_alpha: float = 0.10
## 僵尸贴到 0 距离时的预警周期（秒）
@export var fast_period: float = 0.26
## 最近僵尸距离达到 near_range 时的预警周期（秒）
@export var slow_period: float = 1.40
## 感应半径：最近僵尸超过这个距离就熄灭
@export var near_range: float = 330.0
## 镜盘底色（青玉）
@export var glow_color: Color = Color(0.40, 0.88, 0.94, 1.0)
## 镜心与卦纹亮色
@export var core_color: Color = Color(0.85, 1.0, 1.0, 1.0)
## 每帧重新扫僵尸的间隔（秒）
@export var scan_interval: float = 0.1

## 场上最近僵尸距离；-1 = 没有
var _nearest_dist: float = -1.0
## 预警相位 0→1
var _phase: float = 0.0
## 当前亮度
var _level: float = 0.0
var _scan_accum: float = 0.0
var _zombie_manager: Node = null
## 姿态遮挡系数：跪地时双手压镜，降到 0 让镜光退场
var _occlude: float = 1.0


func _ready() -> void:
	# 画在立绘之上（立绘 z=0）
	z_index = 2
	set_process(true)


## 切换姿态时由植物脚本调用。
## [param occluded] true = 镜面被手压住，应淡出
func set_occluded(occluded: bool) -> void:
	_occlude = 0.0 if occluded else 1.0


func _process(delta: float) -> void:
	_scan_accum += delta
	if _scan_accum >= scan_interval:
		_scan_accum = 0.0
		_refresh_nearest()

	# 亮度：有僵尸拉满，无僵尸回到 idle_alpha，再乘遮挡系数
	var base: float = idle_alpha if _nearest_dist < 0.0 else 1.0
	var target: float = base * _occlude
	# 点亮快、熄灭慢，读作「察觉 → 长亮」
	var ease_speed: float = 2.6 if target > _level else 3.4
	_level = move_toward(_level, target, ease_speed * delta)

	# 预警频率：距离越近周期越短（k² 让近身段变化更剧烈）
	if _nearest_dist >= 0.0:
		var k: float = clampf(1.0 - _nearest_dist / near_range, 0.0, 1.0)
		var period: float = lerpf(slow_period, fast_period, k * k)
		_phase = fmod(_phase + delta / maxf(period, 0.04), 1.0)
	else:
		_phase = fmod(_phase + delta / slow_period, 1.0)

	queue_redraw()


func _refresh_nearest() -> void:
	if not is_instance_valid(_zombie_manager):
		_zombie_manager = _find_zombie_manager()
	var best: float = -1.0
	if is_instance_valid(_zombie_manager):
		var list: Array = _zombie_manager.get("all_zombies_1d")
		for z: Variant in list:
			if not is_instance_valid(z) or z.get("is_death"):
				continue
			var d: float = global_position.distance_to((z as Node2D).global_position)
			if best < 0.0 or d < best:
				best = d
	_nearest_dist = best if best >= 0.0 and best <= near_range else -1.0


func _find_zombie_manager() -> Node:
	var global_node: Node = get_node_or_null("/root/Global")
	if global_node == null:
		return null
	var main_game: Node = global_node.get("main_game")
	if not is_instance_valid(main_game):
		return null
	return main_game.get("zombie_manager")


## 画镜光。所有半径以 mirror_radius 为单位，光全部收在 0.92r 以内。
func _draw() -> void:
	if _level <= 0.002:
		return
	var beat: float = 0.5 - 0.5 * cos(TAU * _phase)
	var lit: float = _level
	var r: float = mirror_radius
	var o: Vector2 = mirror_pos

	# ── 1 盘底补光：只覆盖盘面内侧，让镜盘整体「亮起来」，不越到甲片
	draw_circle(o, r * 0.86, _c(glow_color, (0.10 + 0.26 * beat) * lit))

	# ── 2 盘沿光环：贴着金属边的一圈，是「镜在发光」最核心的读法
	#     半径 0.90r、宽度按 r 走，缩到 0.35 倍后仍有 1px 以上
	draw_arc(o, r * 0.90, 0.0, TAU, 44,
		_c(glow_color, (0.55 + 0.40 * beat) * lit), maxf(1.0, r * 0.11), true)
	# 内白芯压在光环内侧，让边缘读作「有厚度的高光」而不是一条细线
	draw_arc(o, r * 0.84, 0.0, TAU, 44,
		_c(core_color, (0.30 + 0.25 * beat) * lit), maxf(0.8, r * 0.05), true)

	# ── 3 卦纹扫光：从盘心向外推的一道环，半径随相位走 —— 频率的直观载体
	#     起点在盘心外侧，终点压在盘沿之前，读作「从镜里荡出来」
	var wave: float = 0.18 + 0.66 * beat
	draw_arc(o, r * wave, 0.0, TAU, 40,
		_c(core_color, (0.80 - 0.50 * beat) * lit), maxf(0.8, r * 0.07), true)

	# ── 4 镜心：阴阳鱼那一点，峰值最亮但很小，不糊满盘面
	draw_circle(o, r * (0.16 + 0.07 * beat * lit), _c(core_color, (0.55 + 0.35 * beat) * lit))


func _c(c: Color, a: float) -> Color:
	return Color(c.r, c.g, c.b, clampf(a, 0.0, 1.0))
