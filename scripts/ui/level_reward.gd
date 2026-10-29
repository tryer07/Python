## 通关掉落演出 —— 原版「获得新植物 / 获得新道具」那一屏。
##
## 触发点在 [MainGameManager.win_main_game]：本关**首次**通关、且这一关在
## [AdventureReward] 里有掉落时，先弹这一屏，玩家点「收下」之后才切回选关界面。
## 重复打同一关不再弹（原版也是只发一次）。
##
## 两种形态共用一套版式：
## [br]· [constant AdventureReward.Kind.Plant] → 显示 3 倍大的真实种子卡（向 [AllCards] 要实例，
## 与卡槽/图鉴里是同一份美术）；
## [br]· [constant AdventureReward.Kind.Item] → 显示道具图标（铲子/便签/车钥匙/玉米卷/浇水壶/奖杯）。
##
## 为什么在代码里搭 UI 而不是做一个 .tscn：
## [br]这一屏只有「压暗 + 一句话 + 一张图 + 一个按钮」，节点少、没有动画轨道，
## 用代码搭反而不容易在编辑器里被误改尺寸。
extends CanvasLayer
class_name LevelReward

## 玩家看完（点「收下」）时发一次，调用方据此继续切场景。
signal closed

const PVZ_THEME: Theme = preload("res://data/PVZ_theme.tres")
## 面板尺寸，按 1066x600 的视口居中摆放。
const PANEL_SIZE := Vector2(640.0, 500.0)
## 卡面放大倍数；卡牌原始尺寸是 50x70，放大 3 倍后是 150x210。
const CARD_SCALE := 3.0
const CARD_SIZE := Vector2(50.0, 70.0)
## 道具图标的显示高度。卡面可视高度是实体约 150，道具（80~170px 见方）按等比缩到 ~150 高，
## 两者在面板里视觉量级一致，不会出现「掉道具时突然小一圈」。
const ITEM_ICON_HEIGHT := 150.0
## 简介每行放几个字。17 号宋体下 26 字约 442px，面板内宽 560，留得住边。
const DESCRIPTION_CHARS_PER_LINE := 26
## 植物立绘的可用画框（宽、高），以及它的纵向中心。
## [br]卡面区在面板里占 y≈100..310，立绘画框就对齐在同一块地方，名字与说明的位置不用为它让路。
const FIGURE_BOX := Vector2(360.0, 200.0)
const FIGURE_CENTER_Y := 200.0

## 这一屏要展示的掉落，结构见 [method AdventureReward.get_reward]；空字典表示没东西可演。
var _reward: Dictionary = {}
## 是否画那张**种子卡**。
## [br]第一次发放时画卡（玩家要「拿到手」的那张）；如果卡已经在草坪上被捡起来了
## （[RewardPickup]），这里改成画植物本身的立绘 —— 同一张卡连着看两遍没有意义，
## 换成「卡 + 立绘」才是原版那种「恭喜，这株归你了」的完整信息。
var _with_art: bool = true
## 防止「按钮」等重复触发 closed。
var _is_closing: bool = false


## 在 [param host] 下创建并弹出这一屏；返回实例，调用方可连接 [signal closed]。
## [br]挂在 host 而不是当前场景上，是为了不让「切场景」把演出一起清掉。
## [br][param with_art] 为 false 时省掉中间那张大图（各段文字整体上移，面板不留空洞）。
static func show_for(host: Node, reward: Dictionary, with_art: bool = true) -> LevelReward:
	if reward.is_empty():
		return null
	var layer := LevelReward.new()
	layer.name = "LevelReward"
	layer._reward = reward
	layer._with_art = with_art
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
	var art: Control = _build_art(panel)
	_build_name(panel)
	_build_description(panel)
	_build_confirm(panel)

	# 淡入 + 掉落物从「手里甩出来」的那一下
	# [br]⚠️ 缩放的**终点**不是统一的：卡面要停在 3 倍，立绘与道具停在 1 倍
	# （它们的 rect / 缩放已经算好了）。把卡面也设成 1 倍会瞬间缩成一张 50x70 的小纸片。
	var target_scale: Vector2 = Vector2(CARD_SCALE, CARD_SCALE) if _is_card() else Vector2.ONE
	var tween := create_tween()
	tween.tween_property(scrim, "color:a", 0.72, 0.25)
	if art != null:
		art.modulate.a = 0.0
		art.scale = target_scale * 0.55
		tween.parallel().tween_property(art, "modulate:a", 1.0, 0.30)
		tween.parallel().tween_property(art, "scale", target_scale, 0.42) \
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
	var title := _make_label("获得新植物！" if _is_plant() else "获得新道具！",
		34, Color(1.0, 0.94, 0.62))
	title.name = "Title"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	panel.add_child(title)
	title.position = Vector2(0.0, 26.0)
	title.size = Vector2(PANEL_SIZE.x, 44.0)


## 决定这一屏中间画什么：
## [br]· 第一次发放（[member _with_art]）→ 那张可收藏的种子卡；
## [br]· 卡已经在草坪上被捡过 → 改画**植物本身**（静态预览立绘），不再重复同一张卡；
## [br]· 道具 → 一律画图标（道具没有第二套美术）。
func _build_art(panel: Panel) -> Control:
	if not _is_plant():
		return _build_item_icon(panel)
	if _with_art:
		return _build_card(panel)
	return _build_plant_figure(panel)


## 植物立绘：向 [AllCards] 要一份静态预览（图鉴头像用的同一份美术），
## 量出它的实际像素范围后等比装进 [constant FIGURE_BOX]，水平垂直都居中。
## [br]为什么先量再缩：各株的模板尺寸差得很远（豆蔻 37x41、玉米加农炮 69x73），
## 按固定倍数放大就会有的顶到标题、有的缩成一小团。
func _build_plant_figure(panel: Panel) -> Control:
	var reference := _plant_reference()
	if reference == null:
		return null
	var figure: Node2D = AllCards.create_static_preview(reference)
	if figure == null:
		push_warning("掉落演出：植物静态预览缺失（植物编号 %d）" % _plant_id())
		return null

	var holder := Control.new()
	holder.name = "RewardFigure"
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.size = FIGURE_BOX
	holder.position = Vector2((PANEL_SIZE.x - FIGURE_BOX.x) * 0.5, FIGURE_CENTER_Y - FIGURE_BOX.y * 0.5)
	# 绕盒心缩放，弹出动画才从中间长出来
	holder.pivot_offset = FIGURE_BOX * 0.5
	panel.add_child(holder)
	holder.add_child(figure)

	var bounds: Rect2 = _art_bounds(figure, holder)
	if bounds.size.x <= 0.0 or bounds.size.y <= 0.0:
		push_warning("掉落演出：植物立绘量不出尺寸（植物编号 %d）" % _plant_id())
		holder.queue_free()
		return null

	# 立绘是卡面模板里那块 CharacterStatic 的复制品，自带 position/scale 与一堆子 Sprite2D。
	# [br]bounds 是在面框（holder）空间量到的、**已经含 figure 原有缩放**的外框，
	# 所以倍数 k 直接乘到原 scale 上；包围盒中心相对立绘原点的偏移也同步乘 k，
	# 视觉中心才会正好落在画框正中（否则会把模板原有的 (24,30) 之类偏移一起放大，立绘歪到一边）。
	var offset: Vector2 = bounds.get_center() - figure.position
	var k: float = minf(FIGURE_BOX.x / bounds.size.x, FIGURE_BOX.y / bounds.size.y)
	figure.scale = figure.scale * k
	figure.position = FIGURE_BOX * 0.5 - offset * k
	return holder


## 一个节点树里所有 Sprite2D 在 [param relative_to] 空间下的并集矩形。
## [br][param relative_to] 用 [CanvasItem] 而不是 [Node2D]：立绘的容器是个 [Control]。
func _art_bounds(root: Node2D, relative_to: CanvasItem) -> Rect2:
	var out := Rect2()
	var first := true
	var to_relative: Transform2D = relative_to.get_global_transform().affine_inverse()
	var pending: Array[Node] = [root]
	while not pending.is_empty():
		var node: Node = pending.pop_back()
		for child: Node in node.get_children():
			pending.append(child)
		var sprite := node as Sprite2D
		# 隐藏件不参与测量：植物模板里常有一两个备用的隐藏贴图，位置往往远在一边，
		# 算进去会把包围盒撑大，结果立绘缩成一小团。
		if sprite == null or sprite.texture == null or not sprite.visible or sprite.modulate.a <= 0.0:
			continue
		var tex_size: Vector2 = sprite.texture.get_size()
		var local := Rect2(-tex_size * 0.5 + sprite.offset, tex_size)
		var xf: Transform2D = to_relative * sprite.get_global_transform()
		var rect: Rect2 = xf * local
		out = rect if first else out.merge(rect)
		first = false
	return out


## 卡面：直接向 AllCards 要一份真实卡牌实例，保证和卡槽/图鉴里长得一样。
## [br]取不到模板时返回 null，整个演出退化成「只有文字」，不会因为一张图缺失就卡住流程。
## [br]注意这里的 scale 最终是 [constant CARD_SCALE]（卡面本身要放大 3 倍才够看）。
func _build_card(panel: Panel) -> Control:
	var reference := _plant_reference()
	if reference == null:
		return null
	var card: Card = AllCards.create_card(reference, Card.CardContext.Catalog)
	if card == null:
		push_warning("掉落演出：卡牌模板缺失，改为纯文字展示（植物编号 %d）" % _plant_id())
		return null
	card.name = "RewardCard"
	# 卡面只负责好看，不参与点击
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(card)
	# 围绕中心缩放：pivot 定在卡牌正中，动画才是「从中间弹出来」而不是往右下角长
	# [br]位置只跟 pivot 有关，与 scale 无关 —— 视觉中心固定落在面板 (320, 205)。
	card.pivot_offset = CARD_SIZE * 0.5
	card.position = Vector2(
		PANEL_SIZE.x * 0.5 - CARD_SIZE.x * 0.5,
		205.0 - CARD_SIZE.y * 0.5
	)
	return card


## 道具图标：等比缩到 [constant ITEM_ICON_HEIGHT] 高、水平居中，垂直中心与卡面同一行（y=205）。
## [br]缩放不靠 Control.scale，而是直接按贴图宽高比算 rect —— 道具图尺寸各不相同
## （便签 78x52、奖杯 166x136），用 scale 会让动画起点不一致。
func _build_item_icon(panel: Panel) -> Control:
	var texture: Texture2D = _reward.get("texture") as Texture2D
	if texture == null:
		return null
	var texture_size: Vector2 = texture.get_size()
	if texture_size.y <= 0.0:
		return null
	var icon_width: float = ITEM_ICON_HEIGHT * texture_size.x / texture_size.y
	var holder := Control.new()
	holder.name = "RewardItem"
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(holder)
	# 起点定在图标正中，动画才围绕中心放大
	holder.pivot_offset = Vector2(icon_width, ITEM_ICON_HEIGHT) * 0.5
	holder.size = Vector2(icon_width, ITEM_ICON_HEIGHT)
	holder.position = Vector2(PANEL_SIZE.x * 0.5 - icon_width * 0.5, 205.0 - ITEM_ICON_HEIGHT * 0.5)

	var icon := TextureRect.new()
	icon.name = "Icon"
	icon.texture = texture
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_SCALE
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(icon)
	icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return holder


func _build_name(panel: Panel) -> void:
	var display_name := _display_name()
	if display_name.is_empty():
		return
	var label := _make_label(display_name, 26, Color(1.0, 1.0, 1.0))
	label.name = "RewardName"
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	panel.add_child(label)
	label.position = Vector2(0.0, 322.0)
	label.size = Vector2(PANEL_SIZE.x, 36.0)


func _build_description(panel: Panel) -> void:
	var description := _description()
	if description.is_empty():
		return
	var label := _make_label(_wrap_text(description, DESCRIPTION_CHARS_PER_LINE, 3), 17,
		Color(0.92, 0.96, 0.86))
	label.name = "RewardDescription"
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	panel.add_child(label)
	label.position = Vector2(40.0, 364.0)
	label.size = Vector2(PANEL_SIZE.x - 80.0, 68.0)


## 按字数硬折行，不用 Label 自带的 autowrap。
## [br]⚠️ 这里**必须**手动折：autowrap 的 Label 在「父节点不是容器」时会被最小尺寸钳住 ——
## 实测把 autowrap 打开后 Height 从 68 被撑到 564（一行一个字竖着排），直接压出面板。
## [br]折行时**优先在中文标点处断开**：纯按字数切会把「生存模式」切成「生 / 存模式」，
## 读起来是断的。做法是往后多看几个字，取窗口里最后一个标点当断点；
## 找不到标点才退回按字数硬切。超出行数时末行补省略号。
func _wrap_text(text: String, per_line: int, max_lines: int) -> String:
	if per_line <= 0:
		return text
	var break_chars := "，。、；：！？」"
	var lines: Array[String] = []
	var rest := text
	while not rest.is_empty() and lines.size() < max_lines:
		if rest.length() <= per_line:
			lines.append(rest)
			rest = ""
			break
		# 往 per_line 之后多看 6 个字找标点；最少也要切到六成长度，避免第一行太短
		var window_end: int = mini(rest.length(), per_line + 6)
		var floor_len: int = int(maxi(1, int(per_line * 0.6)))
		var cut: int = per_line
		for i: int in range(window_end - 1, floor_len - 1, -1):
			if break_chars.contains(rest[i]):
				cut = i + 1
				break
		lines.append(rest.substr(0, cut))
		rest = rest.substr(cut)
	if not rest.is_empty():
		var last: String = lines[lines.size() - 1]
		lines[lines.size() - 1] = last.substr(0, maxi(1, last.length() - 1)) + "…"
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
func _is_plant() -> bool:
	return int(_reward.get("kind", -1)) == AdventureReward.Kind.Plant


## 这一屏画的是不是那张种子卡（只有植物 + 第一次发放才是）。
## [br]卡面要放大 3 倍，立绘/道具则是已经算好的 1 倍 —— 弹出动画的缩放终点靠这个区分。
func _is_card() -> bool:
	return _is_plant() and _with_art


## 掉落物的显示名：植物走图鉴里的「名字」，道具走 [constant AdventureReward.ITEMS]。
func _display_name() -> String:
	if _is_plant():
		var key: String = _plant_key()
		return String(_almanac_entry().get("名字", key))
	return String(_reward.get("name", ""))


## 掉落物的一句说明。植物取图鉴的「描述」字段，道具取表里的「说明」。
func _description() -> String:
	if _is_plant():
		return String(_almanac_entry().get("描述", ""))
	return String(_reward.get("desc", ""))


## 注册表里该植物在图鉴 JSON 中的键，例如 P002 对应 "SunFlower" 一类。
func _plant_key() -> String:
	if _plant_id() <= 0 or Global.character_registry == null:
		return ""
	var raw: Variant = Global.character_registry.get_plant_info(
		_plant_id(), CharacterRegistry.PlantInfoAttribute.PlantName)
	return String(raw) if raw != null else ""


func _plant_id() -> int:
	return int(_reward.get("plant_id", 0))


## 这株植物的卡牌引用；编号非法时返回 null。
func _plant_reference() -> ResourceCardReference:
	var plant_id: int = _plant_id()
	if plant_id <= 0:
		return null
	return ResourceCardReference.create(ResourceCardReference.CardType.Plant, plant_id)


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
