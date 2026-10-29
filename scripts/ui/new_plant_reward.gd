## 通关掉落植物卡的演出 —— 原版「获得新植物」那一屏。
##
## 触发点在 [MainGameManager.win_main_game]：本关**首次**通关、且这一关在
## [constant AdventurePlantUnlock.UNLOCK_BY_CLEARED_LEVEL] 里有对应的植物时，先弹这一屏，
## 玩家点「收下」之后才切回选关界面。重复打同一关不再弹（原版也是只发一次）。
##
## 为什么在代码里搭 UI 而不是做一个 .tscn：
## [br]这一屏只有「压暗 + 一句话 + 一张卡 + 一个按钮」，节点少、没有动画轨道，
## 用代码搭反而不容易在编辑器里被误改尺寸；卡面本身直接向 [AllCards] 要一份真实卡牌实例，
## 所以「掉落的那张卡」与卡槽里、图鉴里看到的是**同一份美术**，不会出现三副面孔。
extends CanvasLayer
class_name NewPlantReward

## 玩家看完（点「收下」）时发一次，调用方据此继续切场景。
signal closed

const PVZ_THEME: Theme = preload("res://data/PVZ_theme.tres")
## 面板尺寸，按 1066x600 的视口居中摆放。
const PANEL_SIZE := Vector2(640.0, 500.0)
## 卡面放大倍数；卡牌原始尺寸是 50x70，放大 3 倍后是 150x210。
const CARD_SCALE := 3.0
const CARD_SIZE := Vector2(50.0, 70.0)
## 简介每行放几个字。17 号宋体下 26 字约 442px，面板内宽 560，留得住边。
const DESCRIPTION_CHARS_PER_LINE := 26

## 要展示的植物编号。
var _plant_id: int = 0
## 防止「按钮 + 超时」两条路径各触发一次 closed。
var _is_closing: bool = false


## 在 [param host] 下创建并弹出这一屏；返回实例，调用方可连接 [signal closed]。
## [br]挂在 host 而不是当前场景上，是为了不让「切场景」把演出一起清掉。
static func show_for(host: Node, plant_id: int) -> NewPlantReward:
	var layer := NewPlantReward.new()
	layer.name = "NewPlantReward"
	layer._plant_id = plant_id
	# 128 足够压住主游戏的所有 CanvasLayer（暂停菜单、HP 条这些都在 100 以内）
	layer.layer = 128
	host.add_child(layer)
	return layer


func _ready() -> void:
	var root := Control.new()
	root.name = "Root"
	root.theme = PVZ_THEME
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(root)
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	# 压暗层：从透明淡到 0.72，让底下的草坪退成背景
	var scrim := ColorRect.new()
	scrim.name = "Scrim"
	scrim.color = Color(0.0, 0.0, 0.0, 0.0)
	scrim.mouse_filter = Control.MOUSE_FILTER_STOP
	root.add_child(scrim)
	scrim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	var panel := _build_panel(root)
	_build_title(panel)
	var card: Control = _build_card(panel)
	_build_name(panel)
	_build_description(panel)
	_build_confirm(panel)

	# 淡入 + 卡面从「手里甩出来」的那一下
	var tween := create_tween()
	tween.tween_property(scrim, "color:a", 0.72, 0.25)
	if card != null:
		card.modulate.a = 0.0
		card.scale = Vector2(0.55, 0.55)
		tween.parallel().tween_property(card, "modulate:a", 1.0, 0.30)
		tween.parallel().tween_property(card, "scale", Vector2(CARD_SCALE, CARD_SCALE), 0.42) \
			.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


#region UI 搭建
## 居中的弹窗面板，样式沿用游戏里对话框那套 PanelDialogBG。
func _build_panel(root: Control) -> Panel:
	var panel := Panel.new()
	panel.name = "Panel"
	panel.theme_type_variation = &"PanelDialogBG"
	root.add_child(panel)
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.offset_left = -PANEL_SIZE.x * 0.5
	panel.offset_top = -PANEL_SIZE.y * 0.5
	panel.offset_right = PANEL_SIZE.x * 0.5
	panel.offset_bottom = PANEL_SIZE.y * 0.5
	return panel


func _build_title(panel: Panel) -> void:
	var title := _make_label("获得新植物！", 34, Color(1.0, 0.94, 0.62))
	title.name = "Title"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	panel.add_child(title)
	title.position = Vector2(0.0, 26.0)
	title.size = Vector2(PANEL_SIZE.x, 44.0)


## 卡面：直接向 AllCards 要一份真实卡牌实例，保证和卡槽/图鉴里长得一样。
## [br]取不到模板时返回 null，整个演出退化成「只有文字」，不会因为一张图缺失就卡住流程。
func _build_card(panel: Panel) -> Control:
	if _plant_id <= 0:
		return null
	var reference := ResourceCardReference.create(ResourceCardReference.CardType.Plant, _plant_id)
	if reference == null:
		return null
	var card: Card = AllCards.create_card(reference, Card.CardContext.Catalog)
	if card == null:
		push_warning("新植物演出：卡牌模板缺失，改为纯文字展示（植物编号 %d）" % _plant_id)
		return null
	card.name = "RewardCard"
	# 卡面只负责好看，不参与点击
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(card)
	# 围绕中心缩放：pivot 定在卡牌正中，动画才是「从中间弹出来」而不是往右下角长
	card.pivot_offset = CARD_SIZE * 0.5
	card.scale = Vector2(CARD_SCALE, CARD_SCALE)
	card.position = Vector2(
		PANEL_SIZE.x * 0.5 - CARD_SIZE.x * 0.5,
		100.0 + CARD_SIZE.y * 0.5 * (CARD_SCALE - 1.0)
	)
	return card


func _build_name(panel: Panel) -> void:
	var plant_name := _plant_display_name()
	if plant_name.is_empty():
		return
	var label := _make_label(plant_name, 26, Color(1.0, 1.0, 1.0))
	label.name = "PlantName"
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	panel.add_child(label)
	label.position = Vector2(0.0, 322.0)
	label.size = Vector2(PANEL_SIZE.x, 36.0)


func _build_description(panel: Panel) -> void:
	var description := _plant_description()
	if description.is_empty():
		return
	var label := _make_label(_wrap_text(description, DESCRIPTION_CHARS_PER_LINE, 3), 17,
		Color(0.92, 0.96, 0.86))
	label.name = "PlantDescription"
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	panel.add_child(label)
	label.position = Vector2(40.0, 364.0)
	label.size = Vector2(PANEL_SIZE.x - 80.0, 68.0)


## 按字数硬折行，不用 Label 自带的 autowrap。
## [br]⚠️ 这里**必须**手动折：autowrap 的 Label 在「父节点不是容器」时会被最小尺寸钳住 ——
## 实测把 autowrap 打开后 Height 从 68 被撑到 564（一行一个字竖着排），直接压出面板。
## 中文是等宽方块字，按字数折行视觉上完全够用；超出行数时末行补省略号。
func _wrap_text(text: String, per_line: int, max_lines: int) -> String:
	if per_line <= 0:
		return text
	var lines: Array[String] = []
	var rest := text
	while not rest.is_empty() and lines.size() < max_lines:
		if rest.length() <= per_line:
			lines.append(rest)
			rest = ""
			break
		lines.append(rest.substr(0, per_line))
		rest = rest.substr(per_line)
	if not rest.is_empty():
		var last: String = lines[lines.size() - 1]
		lines[lines.size() - 1] = last.substr(0, per_line - 1) + "…"
	return "\n".join(lines)


## 收下按钮：底层 Panel 出 PVZ 的按钮底纹，上面盖一个 flat Button 吃点击。
func _build_confirm(panel: Panel) -> void:
	var button_panel := Panel.new()
	button_panel.name = "ConfirmPanel"
	button_panel.theme_type_variation = &"PanelButtonBG"
	panel.add_child(button_panel)
	button_panel.size = Vector2(170.0, 46.0)
	button_panel.position = Vector2((PANEL_SIZE.x - 170.0) * 0.5, 440.0)

	var label := _make_label("收下", 22, Color(0.16, 0.20, 0.10))
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	button_panel.add_child(label)
	label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	var button := Button.new()
	button.name = "ConfirmButton"
	button.flat = true
	button_panel.add_child(button)
	button.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	button.pressed.connect(_on_confirm_pressed)
	button.grab_focus()


## 统一走一遍 Label 主题覆盖：主题里的 Label 默认是绿色描边字，
## 在深色压暗层上读不出来，这里逐项改成描黑边的浅色字。
func _make_label(text: String, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_outline_color", Color(0.06, 0.05, 0.03, 1.0))
	label.add_theme_constant_override("outline_size", 4)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label
#endregion


#region 文案
## 植物的显示名（豆蔻、朝阳童子…）；图鉴里没有条目时退回注册表里的键名。
func _plant_display_name() -> String:
	if _plant_id <= 0:
		return ""
	var key: String = _plant_key()
	var entry := _almanac_entry()
	return String(entry.get("名字", key))


## 植物的一句简介（图鉴里的「描述」字段），没有条目时返回空串。
func _plant_description() -> String:
	var entry := _almanac_entry()
	return String(entry.get("描述", ""))


## 注册表里该植物在图鉴 JSON 中的键，例如 P002 对应 "SunFlower" 一类。
func _plant_key() -> String:
	if Global.character_registry == null:
		return ""
	var raw: Variant = Global.character_registry.get_plant_info(
		_plant_id, CharacterRegistry.PlantInfoAttribute.PlantName)
	return String(raw) if raw != null else ""


## 图鉴里这条植物的完整条目；未加载或没写条目时返回空字典。
func _almanac_entry() -> Dictionary:
	var key := _plant_key()
	if key.is_empty():
		return {}
	Global.global_read_data.ensure_almanac_loaded()
	var plant_section: Dictionary = Global.global_read_data.data_almanac.get("Plant", {})
	return plant_section.get(key, {})
#endregion


## 点「收下」：只放行一次，随后发 [signal closed] 并清掉自己。
func _on_confirm_pressed() -> void:
	if _is_closing:
		return
	_is_closing = true
	closed.emit()
	queue_free()
