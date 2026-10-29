extends Control
class_name StartMenuRoot

## 冒险模式是否使用原版 50 关选关界面。
## 置 false 即可回到项目原有的 12 关界面，两套场景互相独立，方便随时对比或回退。
const USE_ADVENTURE_50: bool = true

## ── 主菜单闸门（照原版：新存档只有冒险模式能玩）────────────────────────────
## 未解锁的处理分**两种**，别混用：
##
## [br]**一、墓碑（迷你游戏 / 解谜 / 生存）—— 压暗但仍可点。**
## 这几个是主菜单正中的一块块墓碑，未解锁时原版只是颜色暗一点，
## 点它会有人说一句「先打通冒险模式」。**不能挂锁图标** ——
## 一块 80px 的锁盖在墓碑上，墓碑本身（十字、骷髅、南瓜）就全被挡掉了，
## 玩家反而认不出那是什么入口。
##
## [br]**二、图标（图鉴 / 花园 / 商店）—— 未解锁时整块不显示。**
## 原版主菜单下方那几个小图标是「拿到钥匙才长出来」，从来不存在「锁着的图标」这种形态。
## 解锁之后图标直接出现，且出现即可点。
const DIMMED_ENTRIES: Dictionary = {
	"BG_Right/Menu/Button2": AdventureProgress.Feature.MiniGame,
	"BG_Right/Menu/Button3": AdventureProgress.Feature.Puzzle,
	"BG_Right/Menu/Button4": AdventureProgress.Feature.Survival,
}

## 未解锁时整块隐藏、解锁后直接出现的图标入口。
const HIDDEN_ENTRIES: Dictionary = {
	"BG_Right/Item/TextureButton": AdventureProgress.Feature.Garden,
	"BG_Right/Item/TextureButton2": AdventureProgress.Feature.Almanac,
	"BG_Right/Item/TextureButton3": AdventureProgress.Feature.Store,
}

## 压暗后的颜色。0.72 是「一眼看出还没开、但图形还认得出」的程度；
## 再低（0.58 试过）墓碑上的浮雕就糊成一片灰块了。
const DIMMED_MODULATE := Color(0.72, 0.72, 0.74, 1.0)

## 未解锁时点击墓碑给的引导语（用户 2026-10-29 指定的说法）。
const LOCK_GUIDE_TEXT := "通过冒险模式以解锁新的模式"

@onready var dialog: Dialog = $Dialog
@export var bgm:AudioStream
@onready var user: User = $User


# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	$Cloud/AnimationPlayer.play("Idle")
	$BG_Right/Leaf/AnimationPlayer.play("Idle")
	$AnimationPlayer.play("Idle")

	SoundManager.setup_ui_start_menu_sound(self)
	SoundManager.play_bgm(bgm)

	Global.time_scale = 1.0
	Engine.time_scale = Global.time_scale

	## 先把可用植物收窄到冒险进度，再判闸门。
	## [br]⚠️ 必须在这里收一次：植物列表默认是引擎的 49 株全量，只有进过 50 关选关界面
	## 才会被 apply_to_game_state 收窄。玩家开机直接点「图鉴」时没经过选关界面，
	## 不收就会把还没解锁的植物全摆出来（图鉴页就是按 curr_plant 铺的）。
	## [br]开发档（Wow）在这个函数里会走「还原全量」分支，不受影响。
	refresh_unlock_gate()

## 花园需要浇水
var garden_need_water:=true

## 功能未实现
func _unrealized():
	dialog.appear_dialog()


#region 主菜单闸门
## 按**当前存档**重算闸门与卡池。
## [br]⚠️ 切换存档后必须重算：主菜单是同一份场景实例，闸门只在 [method _ready] 里算过一次，
## 换存档后场景既不重建、`_ready` 也不会再跑，界面会保留上一个存档的外观 ——
## 实测就在这儿踩过：新建 test 存档后菜单还是 Wow 的全解锁样子，看起来像「新存档也全开了」。
## [br]调用方见 [method Global.refresh_start_menu_gate]（换存档、给当前存档改名之后）。
func refresh_unlock_gate() -> void:
	AdventurePlantUnlock.apply_to_game_state()
	_apply_unlock_gate()


## 按冒险进度决定哪些入口能玩、哪些压暗、哪些还不该出现。
## [br]开发档（Wow）走 [DevAccess] 的短路，这里全部按「已解锁」处理。
func _apply_unlock_gate() -> void:
	# 一、墓碑：压暗但仍可点
	for node_path: String in DIMMED_ENTRIES:
		var button: BaseButton = get_node_or_null(node_path) as BaseButton
		if button == null:
			push_warning("主菜单闸门：找不到入口 %s" % node_path)
			continue
		var feature: AdventureProgress.Feature = DIMMED_ENTRIES[node_path]
		_set_entry_dimmed(button, not AdventureProgress.is_unlocked(feature))
	# 二、图标：未解锁整块不显示
	for node_path: String in HIDDEN_ENTRIES:
		var entry: CanvasItem = get_node_or_null(node_path) as CanvasItem
		if entry == null:
			push_warning("主菜单闸门：找不到入口 %s" % node_path)
			continue
		var feature: AdventureProgress.Feature = HIDDEN_ENTRIES[node_path]
		entry.visible = AdventureProgress.is_unlocked(feature)
	print("主菜单闸门：当前存档 %s（%s）｜%s" % [
		DevAccess.current_user_name(),
		"全权限" if DevAccess.is_dev_save() else "逐关解锁",
		AdventureProgress.describe(),
	])


## 把墓碑设成「未解锁」外观：只压暗，不加任何覆盖物。
func _set_entry_dimmed(button: BaseButton, dimmed: bool) -> void:
	button.modulate = DIMMED_MODULATE if dimmed else Color.WHITE


## 入口点击前的闸门判定；未解锁则弹引导语并返回 false。
## [param node_path] 必须是 [constant DIMMED_ENTRIES] 的键（隐藏的那三个压根点不到）。
func _pass_gate(node_path: String) -> bool:
	var feature: Variant = DIMMED_ENTRIES.get(node_path)
	if feature == null:
		return true
	if AdventureProgress.is_unlocked(feature):
		return true
	_show_lock_hint(feature)
	return false


## 复用场景里那个「功能未实现」的对话框，把文案换成解锁引导。
## [br]Label 原尺寸只有 40x23（写的是「没做」两个字），这里临时撑到面板宽度并开自动换行，
## 两句提示放得下；面板与按钮的位置不动，外观还是原版那套。
func _show_lock_hint(feature: AdventureProgress.Feature) -> void:
	if dialog == null:
		return
	var label: Label = dialog.get_node_or_null("Label") as Label
	if label != null:
		label.text = "%s\n（%s）" % [LOCK_GUIDE_TEXT, AdventureProgress.get_lock_hint(feature)]
		label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		label.offset_left = 24.0
		label.offset_top = 96.0
		label.offset_right = 297.0
		label.offset_bottom = 216.0
	dialog.appear_dialog()
#endregion


## 开始游戏（冒险模式）
func _on_button_1_pressed() -> void:
	Global.game_para = null
	# 由 USE_ADVENTURE_50 决定进入 50 关界面还是原有的 12 关界面
	var target: MainSceneRegistry.MainScenes = MainSceneRegistry.MainScenes.ChooseLevelAdventure
	if USE_ADVENTURE_50:
		target = MainSceneRegistry.MainScenes.ChooseLevelAdventure50
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[target])


## 迷你游戏
func _on_button_2_pressed() -> void:
	if not _pass_gate("BG_Right/Menu/Button2"):
		return
	Global.game_para = null
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.ChooseLevelMiniGame])

## 解密模式
func _on_button_3_pressed() -> void:
	if not _pass_gate("BG_Right/Menu/Button3"):
		return
	Global.game_para = null
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.ChooseLevelPuzzle])

## 生存模式
func _on_button_4_pressed() -> void:
	if not _pass_gate("BG_Right/Menu/Button4"):
		return
	Global.game_para = null
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.ChooseLevelSurvival])

## 自定义关卡
func _on_custom_button_pressed() -> void:
	Global.game_para = null
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.ChooseLevelCustom])

#region 选项
func _on_option_button_1_pressed() -> void:
	$StartMenuOptionDialog.appear_menu()


func _on_option_button_2_pressed() -> void:
	$Dialog_Help.appear_dialog()

## 退出游戏
func _on_option_button_3_pressed() -> void:
	get_tree().quit()


func _on_full_screen_button_toggled(toggled_on: bool) -> void:
	if toggled_on:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
#endregion


## 花园
## [br]这三个图标未解锁时是**整块不显示**（见 [constant HIDDEN_ENTRIES]），
## 玩家根本点不到，所以这里不需要再做一次运行时判定。
func _on_item_button_1_pressed() -> void:
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.Garden])

## 图鉴
func _on_item_button_2_pressed() -> void:
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.Almanac])

## 商店
func _on_item_button_3_pressed() -> void:
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.Store])

## 点击用户更新时
func _on_button_update_user_pressed() -> void:
	user.visible = true
