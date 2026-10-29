extends Control
class_name StartMenuRoot

## 冒险模式是否使用原版 50 关选关界面。
## 置 false 即可回到项目原有的 12 关界面，两套场景互相独立，方便随时对比或回退。
const USE_ADVENTURE_50: bool = true

## 锁图标：与选关界面的关卡锁是同一张图，主菜单上盖在锁住的入口中间。
const LOCK_TEXTURE: Texture2D = preload("res://assets/image/main_game_item/lock.png")

## ── 主菜单闸门（照原版：新存档只有冒险模式能点）──────────────────────────
## 键 = 按钮节点路径，值 = 它对应的功能。
## [br]⚠️ **不在这里的东西一律无条件可点**：冒险模式（[constant USE_ADVENTURE_50] 决定进哪套选关）、
## 自定义关卡（原版没有，本改版的自制/调试入口）、以及选项区的三个按钮。
## [br]顺序与原版主菜单一致：上面四个模式，下面一排花园/图鉴/商店。
const GATED_ENTRIES: Dictionary = {
	"BG_Right/Menu/Button2": AdventureProgress.Feature.MiniGame,
	"BG_Right/Menu/Button3": AdventureProgress.Feature.Puzzle,
	"BG_Right/Menu/Button4": AdventureProgress.Feature.Survival,
	"BG_Right/Item/TextureButton": AdventureProgress.Feature.Garden,
	"BG_Right/Item/TextureButton2": AdventureProgress.Feature.Almanac,
	"BG_Right/Item/TextureButton3": AdventureProgress.Feature.Store,
}

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
	AdventurePlantUnlock.apply_to_game_state()
	_apply_unlock_gate()

## 花园需要浇水
var garden_need_water:=true

## 功能未实现
func _unrealized():
	dialog.appear_dialog()


#region 主菜单闸门
## 按冒险进度决定六个入口是亮着还是锁着。
## [br]锁住时**不禁用按钮**：禁用后点了毫无反应，玩家只会以为坏了；
## 压暗 + 盖锁 + 点击弹「通关 X-X 后解锁」才是能自解释的做法（原版其实是不显示图标，
## 但改版里图标位是场景写死的，藏掉会留一块空洞）。
func _apply_unlock_gate() -> void:
	for node_path: String in GATED_ENTRIES:
		var button: BaseButton = get_node_or_null(node_path) as BaseButton
		if button == null:
			push_warning("主菜单闸门：找不到入口 %s" % node_path)
			continue
		var feature: AdventureProgress.Feature = GATED_ENTRIES[node_path]
		_set_entry_locked(button, not AdventureProgress.is_unlocked(feature), feature)
	print("主菜单闸门：", AdventureProgress.describe())


## 把一个入口设成锁定态或正常态。
## [param button] 目标按钮；[param locked] true = 压暗并盖锁；[param feature] 它对应的功能。
func _set_entry_locked(button: BaseButton, locked: bool, feature: AdventureProgress.Feature) -> void:
	# 锁定态记在按钮自己身上，点击回调里靠它判断要不要弹提示
	button.set_meta("locked_feature", feature if locked else null)
	# 压暗到 0.58：低到一眼看出不可用，又还认得出是哪张图标
	button.modulate = Color(0.58, 0.58, 0.60, 1.0) if locked else Color.WHITE

	var lock_icon: TextureRect = button.get_node_or_null("LockIcon") as TextureRect
	if lock_icon == null and locked:
		lock_icon = TextureRect.new()
		lock_icon.name = "LockIcon"
		lock_icon.texture = LOCK_TEXTURE
		lock_icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		lock_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		lock_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		button.add_child(lock_icon)
		# 铺满按钮、等比居中：锁图本身带透明留白，缩到按钮高度就自然落在正中
		lock_icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	if lock_icon != null:
		lock_icon.visible = locked


## 入口点击前的闸门判定；锁定则弹提示并返回 false。
## [param node_path] 必须与 [constant GATED_ENTRIES] 的键一致。
func _pass_gate(node_path: String) -> bool:
	var feature: Variant = GATED_ENTRIES.get(node_path)
	if feature == null:
		return true
	if AdventureProgress.is_unlocked(feature):
		return true
	_show_lock_hint(feature)
	return false


## 复用场景里那个「功能未实现」的对话框，把文案换成解锁条件。
## [br]Label 原尺寸只有 40x23（写的是「没做」两个字），这里临时撑到面板宽度并开自动换行，
## 提示句放得下；面板与按钮的位置不动，外观还是原版那套。
func _show_lock_hint(feature: AdventureProgress.Feature) -> void:
	if dialog == null:
		return
	var label: Label = dialog.get_node_or_null("Label") as Label
	if label != null:
		label.text = "%s还没解锁\n%s" % [
			AdventureProgress.get_feature_label(feature), AdventureProgress.get_lock_hint(feature)]
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
func _on_item_button_1_pressed() -> void:
	if not _pass_gate("BG_Right/Item/TextureButton"):
		return
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.Garden])

## 图鉴
func _on_item_button_2_pressed() -> void:
	if not _pass_gate("BG_Right/Item/TextureButton2"):
		return
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.Almanac])

## 商店
func _on_item_button_3_pressed() -> void:
	if not _pass_gate("BG_Right/Item/TextureButton3"):
		return
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.Store])

## 点击用户更新时
func _on_button_update_user_pressed() -> void:
	user.visible = true
