extends Panel
class_name PanleRenameUser

@onready var user: User = $".."

@onready var line_edit: LineEdit = $Panel/LineEdit

@onready var button_ok: PVZButtonBase = $HBoxContainer/ButtonOK
@onready var button_cancel: PVZButtonBase = $HBoxContainer/ButtonCancel

@onready var dialog_error: DialogError = $DialogError

func _ready() -> void:
	button_ok.pressed.connect(_on_button_ok_pressed)
	button_cancel.pressed.connect(_on_button_cancel_pressed)

## 当按下ok按钮时
func _on_button_ok_pressed():
	var new_user_name = line_edit.text
	var old_user_name: String = user.curr_user_button.user_name_on_curr_button
	var add_user_res = Global.user_manager.rename_user(old_user_name, new_user_name)
	if add_user_res.is_empty():
		# 改的是当前存档的名字 → 它可能刚变成 / 刚不再是开发档（Wow），闸门必须重算
		if old_user_name == Global.user_manager.curr_user_name or new_user_name == Global.user_manager.curr_user_name:
			Global.refresh_start_menu_gate()
		_disappear_create_new_user_panel()
	else:
		dialog_error.update_text(add_user_res)
		dialog_error.visible = true

## 当按下取消按钮时
func _on_button_cancel_pressed():
	_disappear_create_new_user_panel()

func _disappear_create_new_user_panel():
	line_edit.text = ""
	visible = false
