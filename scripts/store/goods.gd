extends Control
class_name Goods
## 商品
@export_group("商品属性")
## 商品价格
@export var price :int = 0
## 是否还有该商品
@export var is_have_goods:bool = true
@onready var is_not_have_goods_label: Label = $VBoxContainer/PanelContainer/IsNotHaveGoodsLabel

## 价格标签
@onready var price_tag_label: Label = $VBoxContainer/PriceTag/Label
@onready var button: Button = $VBoxContainer/PanelContainer/Button

@export_group("解锁条件")
## 购买前置：必须先拿到的**道具**，取 [constant AdventureReward.ITEMS] 的键。
## [br]空串 = 没有前置，一进商店就能买。
## [br]原版紫卡植物要求「4-4 拿到玉米卷之后」才能买，对应这里填 `"taco"`。
## [br]道具的获得与否由通关记录推导（[method AdventureReward.has_item]），不另存状态。
## [br]⚠️ 目前商店里还没有紫卡商品，这个字段暂时没有商品在填；
## 等紫卡上架时把 `"taco"` 填上即可，判定与文案都已就位。
@export var unlock_item_key: String = ""

@export_group("戴夫交流相关")
## 该商品的戴夫对话细节描述
@export var dialog_detail:CrazyDaveDialogDetailResource
var curr_dialog_detail:CrazyDaveDialogDetailResource
var original_dialog_text :String

## 查看商品信号
signal look_goods_signal
## 取消查看商品信号
signal look_end_goods_signal
## 点击当前商品信号
signal signal_pressed_this_goods

func _ready() -> void:
	price_tag_label.text = "$" + GlobalUtils.format_number_with_commas(price)
	is_not_have_goods_label.visible = not is_have_goods
	curr_dialog_detail = dialog_detail.duplicate(true)
	judge_can_get_goods()
	## 连接金币改变信号
	Global.global_game_state.coin_value_changed.connect(func(_new_value: int): judge_can_get_goods())

## 判断是否卖的起,是否有商品,以及前置道具是否到手
func judge_can_get_goods():
	## 先判前置道具：这是最根本的一道门，没拿到之前连「买不起」都不该提
	if not is_unlock_condition_met():
		curr_dialog_detail.text = "**%s**\n%s" % [get_unlock_hint(), dialog_detail.text]
		button.disabled = true
		return
	## 如果当前金币买不起
	if Global.global_game_state.coin_value < price:
		curr_dialog_detail.text = "**你现在还卖不起这个商品**\n" + dialog_detail.text
		button.disabled = true
	else:
		curr_dialog_detail.text = dialog_detail.text
		button.disabled = false

	## 如果没有该商品
	if not is_have_goods:
		button.disabled = true


## 前置道具是否已经到手；[member unlock_item_key] 为空时永远返回 true。
func is_unlock_condition_met() -> bool:
	if unlock_item_key.is_empty():
		return true
	return AdventureReward.has_item(unlock_item_key)


## 前置条件不满足时给玩家看的一句话，例如「先拿到玉米卷才能买」。
func get_unlock_hint() -> String:
	var entry: Dictionary = AdventureReward.ITEMS.get(unlock_item_key, {})
	var item_name: String = String(entry.get("名字", unlock_item_key))
	return "先拿到「%s」才能买" % item_name

## 鼠标进入
func _on_mouse_entered() -> void:
	look_goods_signal.emit(curr_dialog_detail)

## 鼠标移出
func _on_mouse_exited() -> void:
	look_end_goods_signal.emit()

## 点击商品
func _on_button_pressed() -> void:
	## 连接时将自身绑定了
	signal_pressed_this_goods.emit()

## 确认购买该商品
func comfirm_get_this_goods():
	## 按钮已经被禁用，走到这里说明有别的路径绕过了判定，直接拒绝
	if not is_unlock_condition_met():
		print("前置道具未到手，不应该出现该语句，因为按钮已经被禁用")
		return
	if Global.global_game_state.coin_value < price:
		print("买不起，不应该出现该语句，因为按钮已经被禁用")
		return
	else:
		Global.global_game_state.coin_value -= price
		get_one_goods()

## 获得该商品的作用，子类重写
func get_one_goods():
	pass
