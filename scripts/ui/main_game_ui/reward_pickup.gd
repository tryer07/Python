## 通关掉落物 —— 草坪上那张**可以捡起来的卡**。
##
## 冒险模式打完一关，最后一只僵尸倒下时掉下来的不是通用奖杯，而是这一关解锁的那张东西：
## [br]· [constant AdventureReward.Kind.Plant] → 那张植物的真实种子卡（向 [AllCards] 要实例，
## 和卡槽、图鉴、掉落演出里是同一份美术）；
## [br]· [constant AdventureReward.Kind.Item] → 道具图标（铲子 / 便签 / 车钥匙 / 玉米卷 / 浇水壶 / 奖杯）。
##
## 为什么和 [Trophy] 分成两个类而不是给奖杯加个开关：
## [br]奖杯是「没有掉落可演」时的通用收尾物（重复挑战已通关的关卡、以及其它模式），
## 它只需要一张固定贴图；这里的掉落物要按存档现算美术、要接掉落表，职责完全不同。
## 两者共用的是同一套「抛出 → 点它 → 光芒 → 结算」的手感，那部分靠 [MainGameManager.throw_to] 保持一致。
##
## ⚠️ 点击**不能**直接切场景：要先推 [code]win_main_game[/code] 事件，
## 让主游戏管理器照常写通关记录、再弹出「获得新植物」那一屏（带名字与说明）。
extends Node2D
class_name RewardPickup

#region 外观常量
## 拾取光晕：卡片脚下那圈呼吸的光
const TEX_PICKUP_GLOW: Texture2D = preload("res://assets/image/ui/ui_trophy/AwardPickupGlow.png")
## 点下去之后铺满屏幕的那团白光
const TEX_GLOW: Texture2D = preload("res://assets/image/ui/ui_trophy/AwardGlow.png")
const TEX_RAYS_A: Texture2D = preload("res://assets/image/ui/ui_trophy/AwardRays1.png")
const TEX_RAYS_B: Texture2D = preload("res://assets/image/ui/ui_trophy/AwardRays2.png")
const TEX_RAYS_C: Texture2D = preload("res://assets/image/ui/ui_trophy/AwardRays.png")
const TEX_RAYS_STAR: Texture2D = preload("res://assets/image/ui/ui_trophy/AwardRays_star.png")

## 光芒四张贴图在奖杯场景里的初始角度与统一缩放，这里原样照搬，两张物件的光效才一致
const RAY_LAYOUT: Array[Dictionary] = [
	{"texture": TEX_RAYS_A, "rotation": -4.18879},
	{"texture": TEX_RAYS_B, "rotation": 0.785398},
	{"texture": TEX_RAYS_C, "rotation": 0.0},
	{"texture": TEX_RAYS_STAR, "rotation": 0.0},
]
const RAY_SCALE := 0.265
## 光晕呼吸的幅度
const PICKUP_GLOW_SCALE := Vector2(1.3, 1.3)
const PICKUP_GLOW_PULSE := Vector2(1.9, 1.9)

## 卡面原始尺寸（与卡槽/图鉴一致），草坪上放大到 2.2 倍 ≈ 110x154，够看清是哪一株。
const CARD_SIZE := Vector2(50.0, 70.0)
const CARD_SCALE := 2.2
## 道具图标的显示高度，与掉落演出里的口径一致（各图 80~170px 见方，等比缩）
const ITEM_HEIGHT := 120.0

## 点了之后飞到屏幕中央的时长；光芒在这个时长里铺开
const FLY_TIME := 1.2
const RAY_TIME := 2.0
#endregion

## 这一颗掉的是什么，结构见 [method AdventureReward.get_reward]
var _reward: Dictionary = {}
## 点击判定区；盖在美术上面，尺寸跟着美术走
var _button: Button
var _rays: Node2D
var _glow: Sprite2D
var _pickup_glow: Sprite2D
## 只结算一次，防止连点
var _claimed: bool = false


## 在 [param parent] 下生成一颗掉落物并返回（调用方负责摆位置、抛出）。
## [br][param reward] 为空时返回 null，调用方据此退回通用奖杯。
static func spawn(parent: Node, reward: Dictionary) -> RewardPickup:
	if parent == null or reward.is_empty():
		return null
	var pickup := RewardPickup.new()
	pickup.name = "RewardPickup"
	pickup._reward = reward
	# 和奖杯同一层级：盖在僵尸、植物、小推车上面，不会被草坪挡住
	pickup.z_index = 2000
	pickup.z_as_relative = false
	parent.add_child(pickup)
	return pickup


func _ready() -> void:
	_build_glow()
	_build_rays()
	var art_size: Vector2 = _build_art()
	_build_button(art_size)


#region 搭建
## 脚下那圈呼吸的光，节奏照搬奖杯：1.3 倍 ↔ 1.9 倍，各一秒，无限循环。
func _build_glow() -> void:
	_pickup_glow = Sprite2D.new()
	_pickup_glow.name = "PickUpGlow"
	_pickup_glow.texture = TEX_PICKUP_GLOW
	_pickup_glow.scale = PICKUP_GLOW_SCALE
	add_child(_pickup_glow)

	var pulse := create_tween().set_loops()
	pulse.tween_property(_pickup_glow, "scale", PICKUP_GLOW_PULSE, 1.0) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	pulse.tween_property(_pickup_glow, "scale", PICKUP_GLOW_SCALE, 1.0) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


## 四张光芒贴图，默认隐藏；点下去才转起来。角度与缩放照搬奖杯场景。
func _build_rays() -> void:
	_rays = Node2D.new()
	_rays.name = "AllRays"
	_rays.visible = false
	add_child(_rays)
	for layout: Dictionary in RAY_LAYOUT:
		var ray := Sprite2D.new()
		ray.texture = layout["texture"] as Texture2D
		ray.rotation = float(layout["rotation"])
		ray.scale = Vector2(RAY_SCALE, RAY_SCALE)
		_rays.add_child(ray)
	# 和奖杯一样，这团白光藏在最后、默认透明，点下去才淡入
	_glow = Sprite2D.new()
	_glow.name = "Glow"
	_glow.texture = TEX_GLOW
	_glow.scale = Vector2(100.0, 100.0)
	_glow.modulate = Color(1, 1, 1, 0)
	_glow.visible = false
	add_child(_glow)


## 摆出这一颗的美术，返回它占的矩形尺寸（供点击区使用）。
## [br]卡牌用 [Control] 的 pivot + scale 绕中心放大；道具用 [Sprite2D]（默认就在原点居中）。
func _build_art() -> Vector2:
	if _is_plant():
		var card: Card = _make_card()
		if card != null:
			card.name = "Card"
			card.mouse_filter = Control.MOUSE_FILTER_IGNORE
			add_child(card)
			card.pivot_offset = CARD_SIZE * 0.5
			card.position = -CARD_SIZE * 0.5
			card.scale = Vector2(CARD_SCALE, CARD_SCALE)
			return CARD_SIZE * CARD_SCALE
		# 卡面模板缺失：退回名字牌，别让一颗空掉落物摆在那儿
		return _build_fallback_plate()

	var texture: Texture2D = _reward.get("texture") as Texture2D
	if texture == null or texture.get_size().y <= 0.0:
		return _build_fallback_plate()
	var size: Vector2 = texture.get_size()
	var factor: float = ITEM_HEIGHT / size.y
	var icon := Sprite2D.new()
	icon.name = "Icon"
	icon.texture = texture
	icon.scale = Vector2(factor, factor)
	add_child(icon)
	return Vector2(size.x * factor, ITEM_HEIGHT)


## 卡面模板缺失时的兜底：一块面板 + 名字，仍然可以点。
func _build_fallback_plate() -> Vector2:
	var plate := Panel.new()
	plate.name = "FallbackPlate"
	plate.theme_type_variation = &"PanelButtonBG"
	plate.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(plate)
	plate.size = CARD_SIZE * CARD_SCALE
	plate.position = -plate.size * 0.5

	var label := Label.new()
	label.text = String(_reward.get("name", "?"))
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	plate.add_child(label)
	label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return plate.size


## 盖在美术上的透明按钮：形状跟着美术走，鼠标移上去变手型。
func _build_button(art_size: Vector2) -> void:
	_button = Button.new()
	_button.name = "PickupButton"
	_button.flat = true
	_button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	_button.size = art_size
	_button.position = -art_size * 0.5
	add_child(_button)
	_button.pressed.connect(_on_pressed)
	_button.mouse_entered.connect(_on_mouse_entered)


## 按植物编号向 [AllCards] 要一份真实卡牌实例。
func _make_card() -> Card:
	var plant_id: int = int(_reward.get("plant_id", 0))
	if plant_id <= 0:
		return null
	var reference := ResourceCardReference.create(ResourceCardReference.CardType.Plant, plant_id)
	if reference == null:
		return null
	return AllCards.create_card(reference, Card.CardContext.Catalog)
#endregion


#region 点击
## 点掉这颗掉落物：飞向屏幕中央，光芒铺开，再推 win_main_game 让管理器走结算。
## [br]⚠️ 这里**不切场景**：结算、写通关记录、弹「获得新植物」那一屏都由
## [method MainGameManager.win_main_game] 负责，掉落演出与奖杯路径走的是同一条。
func _on_pressed() -> void:
	if _claimed:
		return
	_claimed = true
	_button.disabled = true
	SoundManager.play_other_SFX("winmusic")

	var center: Vector2 = get_viewport().get_visible_rect().size / 2 \
		+ Global.main_game.camera_2d.global_position
	var fly := create_tween()
	fly.tween_property(self, "position", center, FLY_TIME) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	_rays.visible = true
	for ray: Node2D in _rays.get_children():
		var spin := create_tween()
		spin.tween_property(ray, "rotation", ray.rotation + TAU, RAY_TIME * 2.5) \
			.set_trans(Tween.TRANS_LINEAR)
		var bloom := create_tween()
		bloom.tween_property(ray, "scale", Vector2(10, 10), RAY_TIME * 2.5) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

	_glow.visible = true
	var glow_tween := create_tween()
	glow_tween.tween_property(_glow, "modulate:a", 1.0, RAY_TIME)

	await get_tree().create_timer(FLY_TIME + 0.15).timeout
	if is_inside_tree():
		EventBus.push_event("win_main_game")


## 手持锤子时把鼠标显示出来（与奖杯同一处理，避免锤子模式下看不见指针）。
func _on_mouse_entered() -> void:
	if Global.main_game != null and Global.main_game.game_para != null \
			and Global.main_game.game_para.is_hammer:
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
#endregion


func _is_plant() -> bool:
	return int(_reward.get("kind", -1)) == AdventureReward.Kind.Plant
