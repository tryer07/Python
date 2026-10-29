extends Control
class_name ChooseLevel

## 用于生成关卡 ID 的计数
var next_level_number: int = 1

@onready var all_page: Control = $AllPage
@onready var label_page: Label = get_node_or_null("LabelPage")

## 游戏模式,用于管理关卡存档
@export var game_mode:MainSceneRegistry.MainScenes = MainSceneRegistry.MainScenes.Null
## 开放关卡数量，冒险默认为1，其余模式为3，若打开控制台开放所有关卡为-1
var open_level_num:int = -1
## 侧支模式（迷你游戏 / 解谜）的**硬上限**：只开放前 N 关，N 之后的关卡一律上锁。
## [br]0 = 不设上限。它与 [member open_level_num] 的「名额」不是一回事：
## 名额是「打一关放一关」，而原版的迷你游戏/解谜是**固定只开前 3 关**，
## 打穿第 1 关不会把第 4 关放出来，剩下 17 关要等一週目通关才整块放开。
var preview_level_limit:int = 0
var all_pages_array : Array[GridContainer]
@export var curr_page := 0

## 选卡bgm
var bgm_choose_card: AudioStream = preload("res://assets/audio/BGM/choose_card.mp3")

func _ready() -> void:
	## 开发档（Wow / 控制台开了开放所有关卡）不走任何闸门，全部关卡直接可点。
	## 判定统一走 [DevAccess]，避免这里和主菜单、卡池三处各判一套。
	if not DevAccess.is_dev_save():
		## 冒险模式（含 50 关版）**只开放 1-1**，照原版从第一关开始逐关推进：
		## 打过 1-1 才有 1-2，打过 1-2 才有 1-3 …（名额由 update_lock_level 每关消耗一个）。
		## [br]⚠️ 2026-10-29 从 2 改成 1：原先为了让玩家开局就能用到朝阳童子（向日葵）
		## 直接放开了 1-2，那是换皮制作期的方便做法；正式存档要按原版走，所以收回。
		## 朝阳童子改由「打完 1-1 掉卡」获得，见 AdventureProgress / main_game_manager 的通关演出。
		if game_mode == MainSceneRegistry.MainScenes.ChooseLevelAdventure \
				or game_mode == MainSceneRegistry.MainScenes.ChooseLevelAdventure50:
			open_level_num = 1
		## 自定义关卡全开放
		elif game_mode == MainSceneRegistry.MainScenes.ChooseLevelCustom:
			open_level_num = -1
		## 迷你游戏 / 解谜：解锁后**先只开前 3 关**（原版就是这样），
		## 剩下的关卡要等一週目通关（5-10 拿到银向日葵奖杯）才整块放开。
		## [br]⚠️ 这里不能用 open_level_num = 3 凑：名额是「打一关放一关」，
		## 打穿第 1 关就会把第 4 关顶出来，与原版「固定 3 关」不符。
		elif game_mode == MainSceneRegistry.MainScenes.ChooseLevelMiniGame:
			open_level_num = -1
			preview_level_limit = AdventureProgress.get_side_mode_level_limit(
				AdventureProgress.Feature.MiniGame)
		elif game_mode == MainSceneRegistry.MainScenes.ChooseLevelPuzzle:
			open_level_num = -1
			preview_level_limit = AdventureProgress.get_side_mode_level_limit(
				AdventureProgress.Feature.Puzzle)
		## 生存模式：一週目通关才出现，出现即整块开放，没有「先开几关」的说法。
		## [br]⚠️ 仍然要走同一个上限函数：它的返回只会是 -1（未解锁，一关不开）
		## 或 0（已解锁，全开）。不设的话 preview_level_limit 停在 0，
		## 功能没解锁时靠 open_level_num = -1 会**直接全放出来**（实测踩过）。
		elif game_mode == MainSceneRegistry.MainScenes.ChooseLevelSurvival:
			open_level_num = -1
			preview_level_limit = AdventureProgress.get_side_mode_level_limit(
				AdventureProgress.Feature.Survival)
		else:
			open_level_num = 3
	else:
		open_level_num = -1

	# 其它模式保持引擎默认的完整植物列表，避免冒险模式的解锁进度影响小游戏等玩法
	if game_mode != MainSceneRegistry.MainScenes.ChooseLevelAdventure50:
		AdventurePlantUnlock.restore_full()

	for page_i in all_page.get_child_count():
		var page = all_page.get_child(page_i)
		all_pages_array.append(page)
		page.visible = false
		for node in page.get_children():
			## 如果是选关按钮
			if node is ChooseLevelButton:
				var level_id:String = generate_level_id()
				if node.curr_level_data_game_para == null:
					continue
				node.signal_choose_level_button.connect(_on_choose_level_button)
				## 初始化游戏数据的选关数据
				node.curr_level_data_game_para.set_choose_level(game_mode, page_i, level_id)
				var curr_level_state_data:Dictionary = Global.global_game_state.curr_all_level_state_data.get(node.curr_level_data_game_para.save_game_name, {})
				node.update_curr_level_button_state(curr_level_state_data)
				update_lock_level(node, curr_level_state_data)

	print("当前模式关卡数量:", next_level_number - 1)

	_ready_update_page()

## 更新关卡是否锁住 无尽模式默认开放，不占用开放名额
func update_lock_level(choose_level_button:ChooseLevelButton, curr_level_state_data:Dictionary):
	## ⚠️ 侧支模式的「固定前 N 关」必须先判，而且要排在 open_level_num == -1 的直通之前：
	## 迷你游戏/解谜的 open_level_num 本来就是 -1（不按名额算），
	## 若先判 -1 直接 return，preview_level_limit 就永远不会生效。
	## [br]preview_level_limit：0 = 不限制；-1 = 一关都不开；N > 0 = 只开前 N 关。
	if preview_level_limit != 0:
		var side_level_no: int = _level_no_of_choose_level(choose_level_button)
		if side_level_no > preview_level_limit:
			choose_level_button.lock_choose_level_button()
			return
	## 如果开放名额为-1，即所有关卡都开发
	if open_level_num == -1:
		return
	## 无尽模式
	if choose_level_button.curr_level_data_game_para.game_round == -1:
		return
	## 如果当前关卡通关
	if curr_level_state_data.get("IsSuccess", false):
		return
	## 还有开发关卡名额
	if open_level_num > 0:
		open_level_num -= 1
		return
	else:
		choose_level_button.lock_choose_level_button()


## 从存档键取出 1 起的关卡序号；取不到时返回 -1。
## [br]存档键形如 `102_0_0003`（模式_页_四位序号），取末四位即可 ——
## 这几个模式的关卡 id 都由 [method generate_level_id] 从 0001 起递增，
## 所以末四位就是按钮在该模式里的第几关。
func _level_no_of_choose_level(choose_level_button: ChooseLevelButton) -> int:
	if choose_level_button == null or choose_level_button.curr_level_data_game_para == null:
		return -1
	var save_name: String = choose_level_button.curr_level_data_game_para.save_game_name
	if save_name.length() < 4:
		return -1
	return save_name.substr(save_name.length() - 4).to_int()

func _ready_update_page():
	## 如果从游戏中退出
	if Global.game_para != null and Global.game_para.game_mode == game_mode:
		curr_page = Global.game_para.level_page

	if curr_page > all_pages_array.size():
		curr_page = 0
	if not all_pages_array.is_empty():
		all_pages_array[curr_page].visible = true
		if is_instance_valid(label_page):
			_update_page(curr_page)

	SoundManager.play_bgm(bgm_choose_card)

## 获取关卡id
func generate_level_id() -> String:
	# 用格式化字符串，让数字变成 4 位，前面补 0
	# GDScript 支持类似 C 风格字符串格式化
	var id_str = "%04d" % next_level_number  # 例如 0 -> "0000", 12 -> "0012"
	next_level_number += 1
	return id_str

func _on_choose_level_button(choose_level_button:ChooseLevelButton):
	Global.game_para = choose_level_button.curr_level_data_game_para
	choose_level_start_game(choose_level_button.curr_level_data_game_para.game_sences)

## 进入游戏关卡
func choose_level_start_game(game_scense:MainSceneRegistry.MainScenes):
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[game_scense])

## 返回开始菜单
func back_start_menu():
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.StartMenu])


func _on_last_pressed() -> void:
	_update_page(curr_page - 1)

func _on_next_pressed() -> void:
	_update_page(curr_page + 1)


func _update_page(new_page:int):
	new_page = posmod(new_page, all_pages_array.size())
	all_pages_array[curr_page].visible = false
	curr_page = new_page
	all_pages_array[curr_page].visible = true
	label_page.text = "当前页数:" + str(curr_page + 1) + "/" + str(all_pages_array.size())
