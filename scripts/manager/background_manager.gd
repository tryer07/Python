extends MainGameSubManager
class_name BackgroundManager
## 背景管理器,管理背景和前景

@onready var background: Sprite2D = %Background
@onready var frontground: Node2D = %Frontground

@onready var home: MainGameHome = %Home
## 泳池
var pool:Pool
## 浓雾
var fog:Fog

## 雨
var rain:MainGameRain

## 雾
const FOG = preload("uid://bs55ei6xiuugg")
const RAIN = preload("uid://cv3iw5srgpusv")

#region 草坪铺设
## 荒土底图：还没铺草皮的地面。与 background1.jpg 同尺寸、同视角，可以直接互换。
const BG_FRONT_DIRT: Texture2D = preload("res://assets/image/background/background1unsodded.jpg")
## 单行草皮：原版 sod1row（771×127）的黑底图 + 配套蒙版合成出的带 alpha PNG。
## 上下边缘自带参差的草叶，压在荒土上不会出现生硬的直切口。
const SOD_ROW_TEXTURE: Texture2D = preload("res://assets/image/background/sod_row1.png")
## 三行草皮：原版 sod3row（771×355）与它的蒙版合成出的带 alpha PNG。
## [br][b]为什么必须整块贴、不能逐行复制：[/b]草皮纹理是原版手绘的一整片，
## 把同一行复制三次会让同一丛草叶在纵向上等距重复三遍，而且每一行都自带上下两条参差草叶边，
## 叠起来就是两道假的横向分界线 —— 一眼就能看出是「一行一行铺的」。
## 整块贴则是一片完整的草皮，只有最外面一圈参差边。
const SOD_ROW3_TEXTURE: Texture2D = preload("res://assets/image/background/sod_row3.png")

## 每一行草坪格子的像素跨度（相对背景图左上角，x = 上沿，y = 下沿）。
## 由游戏内植物格子坐标实测换算：96px 一行，行与行之间留 4px 接缝。
const SOD_ROW_SPAN: Array[Vector2i] = [
	Vector2i(82, 178), Vector2i(182, 278), Vector2i(282, 378),
	Vector2i(381, 477), Vector2i(478, 574),
]
## 两块预制草皮的锚点（左上角，背景图坐标系）。
## [br]取法：把草皮块与 background1.jpg（整片铺满的原图）做逐像素对位，
## 求误差最小的偏移 —— 单行块落在 (239,265)（画的正是第 3 行），
## 三行块落在 (235,149)（画的正是第 2~4 行），平均误差都在 7/255 以内。
## [br]换句话说，这两块草皮本来就是从那张整图上裁下来的，位置必须照抄，不能估。
const SOD_ROW_TOPLEFT := Vector2(239.0, 265.0)
const SOD_ROW3_TOPLEFT := Vector2(235.0, 149.0)
## 单行块画的是第几行 —— 其它行号按「行顶差值」平移过去。
const SOD_ROW1_ANCHOR_ROW := 3
## 三行块画的是从第几行开始 —— 只有请求的行号与它对齐时才整块贴。
const SOD_ROW3_ANCHOR_ROW := 2
#endregion


func init_manager() -> void:
	init_background()
	init_frontground()


## 初始化背景
func init_background():
	var curr_bg_texture: Texture2D = ConstLevelData.GameBgTextureMap[game_para.game_BG]
	background.texture = curr_bg_texture
	apply_lawn_sod()
	home.init_home(game_para.game_BG)
	if not game_para.is_zombie_can_home:
		print("僵尸无法进房")
		home.disable_home()
	match game_para.game_BG:
		ConstLevelData.GameBg.Pool, ConstLevelData.GameBg.Fog:
			pool = background.get_node(^"Pool")
			pool.init_pool(game_para)

## 按关卡数据铺草坪。[br]
## [member ResourceLevelData.sod_rows] 为空表示整片草坪已经铺好（默认，直接用原图）；
## 否则把底图换成荒土，只把列出的那几行草皮贴上去，用于还原「草坪逐关铺开」。
func apply_lawn_sod() -> void:
	var sod_rows: Array[int] = game_para.sod_rows
	if sod_rows.is_empty():
		return
	if game_para.game_BG != ConstLevelData.GameBg.FrontDay:
		push_error("草坪未铺满目前只支持白天前院，当前背景为：%s" % game_para.game_BG)
		return

	background.texture = BG_FRONT_DIRT
	# 连续的几行优先用整块草皮。逐行贴只有在「凑不出整块」时才退回去用。
	for rows: Array in _split_sod_runs(sod_rows):
		if rows.size() >= 3 and int(rows[0]) == SOD_ROW3_ANCHOR_ROW:
			_add_sod_strip("SodRow3", SOD_ROW3_TEXTURE, SOD_ROW3_TOPLEFT)
			for i: int in range(3, rows.size()):
				_add_sod_row(int(rows[i]))
		else:
			for row: int in rows:
				_add_sod_row(int(row))


## 把行号切成「连续段」：[2,3,4] → [[2,3,4]]，[1,3,5] → [[1],[3],[5]]。
## 只有连续段才知道能不能整块贴（草皮是按相邻行裁的，跨行拼不了）。
func _split_sod_runs(sod_rows: Array[int]) -> Array[Array]:
	var sorted_rows: Array[int] = sod_rows.duplicate()
	sorted_rows.sort()

	var runs: Array[Array] = []
	var start: int = 0
	for i: int in range(1, sorted_rows.size() + 1):
		# 走到末尾，或者下一行不再是「上一行 + 1」，就把 [start, i) 这段收成一段
		if i == sorted_rows.size() or sorted_rows[i] != sorted_rows[i - 1] + 1:
			var segment: Array[int] = []
			for j: int in range(start, i):
				segment.append(sorted_rows[j])
			runs.append(segment)
			start = i
	return runs


## 贴单行草皮。以「单行块画的那一行」为基准，按行顶差值整体平移。
func _add_sod_row(row: int) -> void:
	if row < 1 or row > SOD_ROW_SPAN.size():
		push_error("草坪行号超出范围：%s（应为 1~%d）" % [row, SOD_ROW_SPAN.size()])
		return
	var anchor_top: int = SOD_ROW_SPAN[SOD_ROW1_ANCHOR_ROW - 1].x
	var dy: float = float(SOD_ROW_SPAN[row - 1].x - anchor_top)
	_add_sod_strip("SodRow%d" % row, SOD_ROW_TEXTURE, SOD_ROW_TOPLEFT + Vector2(0.0, dy))


## 贴一块预制草皮。[param topleft] 是它左上角在背景图坐标系里的位置；
## Sprite2D 默认以中心对齐，换算统一收在这里，调用点只报左上角，避免各算各的算错。
func _add_sod_strip(strip_name: String, texture: Texture2D, topleft: Vector2) -> void:
	var sod := Sprite2D.new()
	sod.name = strip_name
	sod.texture = texture
	sod.position = topleft + Vector2(texture.get_width(), texture.get_height()) * 0.5
	background.add_child(sod)
	# 草皮要压在背景之上、房子和植物之下，所以排到最前面的子节点
	background.move_child(sod, 0)


## 初始化前景
func init_frontground():
	if game_para.is_fog:
		fog = FOG.instantiate()
		frontground.add_child(fog)
	if game_para.is_rain:
		rain = RAIN.instantiate()
		frontground.add_child(rain)

## 展示下一轮僵尸前退雾；直接进入下一轮时保留当前三叶草效果和移动。
func start_next_game_background_manager_update():
	if game_para.look_show_zombie and is_instance_valid(fog):
		fog.fog_outside()
