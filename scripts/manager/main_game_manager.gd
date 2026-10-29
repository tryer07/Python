extends Node2D
class_name MainGameManager

#region 游戏测试
@export_group("测试相关")
## 游戏时测试方便修改阳光数
@export var test_change_sun_value := 9999:
	set(value):
		test_change_sun_value = value
		EventBus.push_event("test_change_sun_value", [value])

## 所有僵尸死亡
@export var test_death_all_zombie:=false:
	set(value):
		print("设置值")
		EventBus.push_event("test_death_all_zombie")

## 游戏速度
## INFO: 游戏速度超过8会代码执行顺序会有问题，可能会导致一些莫名其妙的bug
@export var test_time_scale:=1:
	set(value):
		test_time_scale = value
		Engine.time_scale = test_time_scale

#endregion
#region 游戏管理器
@onready var manager: Node = %Manager
@onready var card_manager: CardManager = %CardManager
@onready var hand_manager: HandManager = %HandManager
@onready var zombie_manager: ZombieManager = %ZombieManager
@onready var game_item_manager: GameItemManager = %GameItemManager
@onready var plant_cell_manager: PlantCellManager = %PlantCellManager
@onready var background_manager: BackgroundManager = %BackgroundManager
@onready var day_suns_manager: DaySunsManagner = %DaySunsManager
@onready var drop_item_manager: DropItemManager = %DropItemManager

#endregion

#region UI元素、相机
@onready var camera_2d: MainGameCamera = %Camera2D
@onready var ui_remind_word: UIRemindWord = %UIRemindWord
@onready var level_info: LevelInfo = $CanvasLayerUI/LevelInfo

#endregion

#region 游戏主元素
@onready var canvas_layer_temp: CanvasLayer = %CanvasLayerTemp
@onready var canvas_layer_ui: CanvasLayer = %CanvasLayerUI

## 阳光收集位置,出战卡槽时更新
var marker_2d_sun_target: Marker2D
@onready var marker_2d_sun_target_default: Marker2D = %Marker2DSunTargetDefault

## 场景内独立物件的挂载节点，包括博士释放的冰火球。
@onready var items: Node2D = %Items

## 将子弹\爆炸\阳光
@onready var bullets: Node2D = %Bullets
@onready var bombs: Node2D = %Bombs
@onready var suns: Node2D = %Suns

@onready var coin_bank_label: CoinBankLabel = %CoinBankLabel
## 卡槽
@onready var card_slot_root: CardSlotRoot = %CardSlotRoot
## 僵尸进家panel
@onready var panel_zombie_go_home: Panel = %PanelZombieGoHome
@onready var marker_2d_zombie_go_home: Marker2D = %Marker2DZombieGoHome

## 全局检测组件,用于检测敌人
##TODO:可能会用于检测敌人离开场景后删除
@onready var detect_component_global: DetectComponent = %DetectComponentGlobal

#endregion

#region 锤子进入节点鼠标显示
## 鼠标是否一致显示,当有锤子时
var is_mouse_visibel_on_hammer:bool = false
@onready var node_mouse_appear_have_hammer:Array[Control] = [
	## 卡槽
	%CardSlotRoot,
	## 菜单
	%MainGameMenuButton, %MainGameMenuOptionDialog, %Dialog
]

#endregion

#region bgm
@export_group("bgm")
## 选卡bgm
var bgm_choose_card: AudioStream = preload("res://assets/audio/BGM/choose_card.mp3")
## 关卡配置的原始战斗音乐，用于常规战斗及解除僵王音乐覆盖。
var bgm_main_game: AudioStream
## 存活僵王入场后覆盖原始战斗音乐的曲目，不改变关卡配置。
var bgm_boss: AudioStream
#endregion


#region 主游戏运行阶段
enum E_MainGameProgress{
	NONE,			## 无
	CHOOSE_CARD,	## 选卡界面
	PREPARE,		## 准备阶段(红字)
	MAIN_GAME,		## 游戏阶段
	GAME_OVER,		## 游戏结束阶段
	RE_CHOOSE_CARD,	## 多轮游戏重新选卡阶段
}

## 重新选卡是否暂停
var is_pause_on_re_choose_card:=false
## 正在保存、等待或重选下一轮时为 true，防止计时器与清场奖杯并发推进轮数。
var _round_transition_pending: bool = false
## 本轮已接受胜利或轮间计时请求；在发送事件或等待前置位，正式开战时重置。
var _round_end_claimed: bool = false
## 本轮实际由额外 Boss 条件结束，用于等待演出和跳过剩余自然波次。
var _round_end_by_boss: bool = false
## 当前关卡流程阶段；更新时同步通知卡槽与角色行为。
var main_game_progress := E_MainGameProgress.NONE:
	set(value):
		main_game_progress = value
		EventBus.push_event("main_game_progress_update", [value])

#endregion

#region 游戏数据
@export_group("地图特殊地形")
## 斜面(屋顶)
@export var main_game_slope:MainGameSlope
## 雪人僵尸逃跑概率(默认不使用该概率,赌狗小游戏使用)
var p_yeti_run :float= -1
#endregion

#region 游戏参数
@export_group("本局游戏参数")
## 正常进入游戏会自动更新对应关卡数据,直接进入该场景会使用该关卡数据,并设置is_test=true
@export var game_para : ResourceLevelData
## 若为true,选卡无冷却
var is_test := false
## 当前轮次
var curr_game_round = 1:
	set(value):
		curr_game_round = value
		level_info.set_round(curr_game_round)

## 初始化时是否存档
var is_save_game_data_on_init:=false

#endregion

#endregion
func _enter_tree() -> void:
	set_game_para()

## 进入树时更新游戏参数，子管理器赋值对应的游戏参数
func set_game_para() -> void:
	Global.main_game = self
	## 先获取当前关卡参数
	if Global.game_para != null:
		game_para = Global.game_para
	else:
		is_test = true
	if game_para == null:
		push_error(
			"主游戏缺少关卡数据 ResourceLevelData：请从选关流程进入，或在编辑器中为该主游戏场景根节点指定「本局游戏参数 / game_para」。"
		)
		queue_free()
		return

func _exit_tree() -> void:
	## 避免切场景后主游戏节点已释放，Global 仍持有野指针
	if Global.main_game == self:
		Global.main_game = null

func _ready() -> void:
	# 参数资源负责校验与初始化；失败时保持 NONE 阶段，不继续选卡或初始化子管理器。
	if not game_para.init_para():
		return
	## 多轮游戏并且有存档
	is_save_game_data_on_init = game_para.game_round != 1 and game_para.save_game_data_main_game != null

	## 订阅总线事件
	event_bus_subscribe()
	## 默认禁用全局敌人检测组件(追踪子弹调用, 放置追踪植物时启用,追踪植物死亡时,检测是否关闭)
	detect_component_global.disable_component(ComponentNormBase.E_IsEnableFactor.Global)
	## 主游戏进程
	main_game_progress = E_MainGameProgress.CHOOSE_CARD
	## 播放选卡bgm
	SoundManager.play_bgm(bgm_choose_card)
	## 连接子节点信号
	signal_connect()
	## 初始化子管理器
	init_manager()
	coin_bank_label.visible = false
	## 初始化游戏背景音乐
	_init_game_BGM()

	## 若有存档
	if is_save_game_data_on_init:
		load_game_main_game()
		# 存档表示上一轮已经结束，选卡阶段直接恢复过渡，不重新判胜。
		_advance_to_next_round()
	else:

		## 如果有戴夫对话
		if game_para.crazy_dave_dialog:
			var crazy_dave:CrazyDave = SceneRegistry.CRAZY_DAVE.instantiate()
			crazy_dave.init_dave(game_para.crazy_dave_dialog)
			canvas_layer_ui.add_child(crazy_dave)
			await crazy_dave.signal_dave_leave_end
			crazy_dave.queue_free()

		## 如果看展示僵尸
		if game_para.look_show_zombie:
			## 创建展示僵尸，等待一秒移动相机
			zombie_manager.create_prepare_show_zombies()
			await get_tree().create_timer(1.0).timeout
			await camera_2d.move_look_zombie()
			## 如果可以选卡
			if game_para.can_choosed_card:
				card_manager.card_slot_appear_choose()
			else:
				await get_tree().create_timer(1.0).timeout
				no_choosed_card_start_game()
		else:
			main_game_start()
	# 录帧自检专用：跳关进战斗时会停在选卡界面等人点「一起摇滚吧」，
	# 命令行带 `autochoose` 就让机器人代点一次（正常游玩不会带这个参数）。
	if "autochoose" in OS.get_cmdline_user_args():
		await get_tree().create_timer(1.2).timeout
		if is_inside_tree() and not is_queued_for_deletion():
			print("调试：自动点掉选卡界面")
			EventBus.emit_signal("card_slot_norm_start_game")

## 主游戏管理器事件总线订阅
func event_bus_subscribe():
	## 手持锤子时，修改鼠标离开ui是否显示鼠标
	EventBus.subscribe("change_is_mouse_visibel_on_hammer", change_is_mouse_visibel_on_hammer)
	## 僵尸进家
	EventBus.subscribe("zombie_go_home", on_zombie_go_home)
	## 创建奖杯
	EventBus.subscribe("create_trophy", create_trophy)
	## 游戏胜利
	EventBus.subscribe("win_main_game", win_main_game)
	## 正常选卡结束后开始游戏
	EventBus.subscribe("card_slot_norm_start_game", choosed_card_start_game)
	## 多轮游戏触发下一轮游戏
	EventBus.subscribe("start_next_round_game", start_next_round_game)
	## 更新阳光收集位置
	EventBus.subscribe("update_marker_2d_sun_target", update_marker_2d_sun_target)


## 更新阳光收集位置
func update_marker_2d_sun_target(new_marker_2d_sun_target:Marker2D):
	marker_2d_sun_target = new_marker_2d_sun_target

#region 游戏关卡初始化
## 初始化管理器
func init_manager():
	card_manager.init_manager()
	plant_cell_manager.init_manager()
	game_item_manager.init_manager()
	hand_manager.init_manager()
	zombie_manager.init_manager()
	background_manager.init_manager()
	drop_item_manager.init_manager()
	day_suns_manager.init_manager()
	print("info:管理器初始化完成")

## 信号连接
func signal_connect():
	zombie_manager.signal_living_bosses_changed.connect(refresh_battle_bgm)
	if game_para.is_hammer:
		for ui_node:Control in node_mouse_appear_have_hammer:
			ui_node.mouse_entered.connect(mouse_appear_have_hammer)
			ui_node.mouse_exited.connect(mouse_disappear_have_hammer)

## 加载关卡原始战斗音乐和僵王音乐，选卡阶段不在此处切换播放。
func _init_game_BGM():
	# 当前关卡配置的战斗音乐资源路径。
	var path_bgm_game: String = ConstLevelData.GameBGMMap[game_para.game_BGM]
	bgm_main_game = load(path_bgm_game) as AudioStream
	# 僵王曲目复用关卡音乐映射，避免另行维护资源路径。
	var path_bgm_boss: String = ConstLevelData.GameBGMMap[ConstLevelData.GameBGM.Boss]
	bgm_boss = load(path_bgm_boss) as AudioStream


## 正式战斗时按存活僵王选择音乐；解除覆盖时从头播放关卡原曲。
## 单轮僵王死亡获胜先进入结算，因此保留僵王音乐，不在结算阶段恢复原曲。
## 相同曲目继续播放，选卡、结算或场景卸载时不覆盖其他界面的音乐。
func refresh_battle_bgm() -> void:
	if not is_inside_tree() or is_queued_for_deletion() \
		or get_tree().current_scene != self or main_game_progress != E_MainGameProgress.MAIN_GAME:
		return
	# 死亡演出中的僵王已不属于存活快照，不必等待动画结束或节点释放。
	var battle_bgm: AudioStream = bgm_main_game if zombie_manager.get_living_bosses().is_empty() else bgm_boss
	SoundManager.play_bgm_if_changed(battle_bgm)


## 不用选择卡片进行的流程
func no_choosed_card_start_game():
	await get_tree().create_timer(2.0).timeout
	## 相机移动回游戏场景
	await camera_2d.move_back_ori()
	main_game_start()
#endregion

#region 多轮游戏下一轮
## 末波计时器请求进入下一轮；末轮不占用结算状态，也不通过计时器创建奖杯。
func start_next_round_game() -> void:
	if curr_game_round == game_para.game_round:
		return
	if not try_claim_round_end():
		return
	_advance_to_next_round()


## 执行已确认的轮间过渡，也供选卡阶段恢复轮末存档；正式开战后解除过渡锁定。
func _advance_to_next_round() -> void:
	## 多轮游戏僵尸管理器计时器触发时，判断是否为最后一轮
	if curr_game_round == game_para.game_round or _round_transition_pending \
		or TreePauseManager.curr_pause_factor.get(TreePauseManager.E_PauseFactor.GameOver, false):
		return
	_round_transition_pending = true
	print("-----------------开始下一轮游戏---------------")
	print("下一轮次：", curr_game_round + 1)
	## 等待3秒后进行下一轮
	await get_tree().create_timer(3).timeout
	# 轮间等待仍允许进房失败；旧协程不能继续推进轮数或重新写入已删除的存档。
	if not is_inside_tree() or is_queued_for_deletion() \
		or TreePauseManager.curr_pause_factor.get(TreePauseManager.E_PauseFactor.GameOver, false):
		return
	# 暂停选卡与清场前保存，将等待期间成功召唤的僵王和血量变化一并纳入快照。
	save_game_main_game()
	## 播放选卡bgm
	if game_para.look_show_zombie:
		## 重新选卡阶段暂停游戏
		start_pause_on_re_choose_card_progress()
		print("----------------播放选卡bgm", bgm_choose_card)
		SoundManager.play_bgm(bgm_choose_card)
	curr_game_round += 1
	main_game_progress = E_MainGameProgress.RE_CHOOSE_CARD
	## 暂停天降阳光
	if game_para.is_day_sun:
		day_suns_manager.pause_day_sun()
	## 更新卡槽数据
	card_manager.start_next_game_card_manager_update()
	## 更新背景,浓雾回退
	background_manager.start_next_game_background_manager_update()
	coin_bank_label.visible = false
	## 更新僵尸管理器
	zombie_manager.start_next_game_zombie_mananger_update(_round_end_by_boss)
	## 更新植物格子数据，（创建罐子） 清除植物数据需要等待两帧
	await plant_cell_manager.start_next_game_plant_cell_manager_update()
	game_item_manager.start_next_game_game_item_manager_update()

	## 如果看展示僵尸
	if game_para.look_show_zombie:
		## 创建展示僵尸，等待一秒移动相机
		zombie_manager.create_prepare_show_zombies()
		await get_tree().create_timer(1.0).timeout
		await camera_2d.move_look_zombie()
		## 如果可以选卡
		if game_para.can_choosed_card:
			card_manager.card_slot_appear_choose()
		else:
			await get_tree().create_timer(1.0).timeout
			no_choosed_card_start_game()
	else:
		main_game_start()


## 下轮选卡时暂停游戏
func start_pause_on_re_choose_card_progress():
	is_pause_on_re_choose_card = true
	## 设置相机可以移动
	camera_2d.process_mode = Node.PROCESS_MODE_ALWAYS
	card_slot_root.process_mode = Node.PROCESS_MODE_ALWAYS
	TreePauseManager.start_tree_pause(TreePauseManager.E_PauseFactor.ReChooseCard)

## 下轮选卡结束时取消暂停游戏
func end_pause_on_re_choose_card_progress():
	is_pause_on_re_choose_card = false
	## 设置相机可以移动
	camera_2d.process_mode = Node.PROCESS_MODE_INHERIT
	card_slot_root.process_mode = Node.PROCESS_MODE_INHERIT
	TreePauseManager.end_tree_pause(TreePauseManager.E_PauseFactor.ReChooseCard)

#endregion

## 选择卡片完成
func choosed_card_start_game():
	print("选卡完成")
	## 主游戏进程阶段
	main_game_progress = E_MainGameProgress.PREPARE
	## 隐藏待选卡槽
	await card_manager.card_slot_disappear_choose()
	## 相机移动回游戏场景
	await camera_2d.move_back_ori()
	main_game_start()

## 选卡结束，恢复主游戏；浓雾自行决定继续三叶草等待或正常入场。
func main_game_start():
	if is_pause_on_re_choose_card:
		end_pause_on_re_choose_card_progress()
	print("主游戏开始")
	## 主游戏进程阶段
	main_game_progress = E_MainGameProgress.PREPARE
	if game_para.is_fog:
		background_manager.fog.start_round()

	## 删除展示僵尸
	if game_para.look_show_zombie:
		zombie_manager.delete_prepare_show_zombies()

	## 开始天降阳光
	if game_para.is_day_sun:
		day_suns_manager.start_day_sun()
	print("生成墓碑", game_para.init_tombstone_num)
	## 生成墓碑
	if game_para.init_tombstone_num > 0:
		plant_cell_manager.create_tombstone(game_para.init_tombstone_num)

	## 等待1秒红字出现
	await get_tree().create_timer(1.0).timeout
	await ui_remind_word.ready_set_plant()
	# 先清除上一轮结算记录，再通知战斗阶段，避免同步事件看到旧轮锁定。
	_round_end_claimed = false
	_round_end_by_boss = false
	_round_transition_pending = false
	main_game_progress = E_MainGameProgress.MAIN_GAME
	# 僵王只有在正式战斗阶段才能恢复；先恢复实例与血量，再启用出战卡片。
	zombie_manager.restore_saved_bosses()
	card_manager.card_slot_update_main_game()

	# 本次延迟所属轮次，防止旧轮协程重新播放音乐或启动下一轮刷怪。
	var start_round: int = curr_game_round
	# 红字结束后一秒按当前存活僵王选择音乐，不能覆盖读档或卡牌入场已切换的僵王曲目。
	await get_tree().create_timer(1.0).timeout
	if not is_inside_tree() or is_queued_for_deletion() or get_tree().current_scene != self \
		or main_game_progress != E_MainGameProgress.MAIN_GAME or curr_game_round != start_round:
		return
	refresh_battle_bgm()

	zombie_manager.start_game()
	_debug_auto_plant_from_args()


## 临时调试入口：命令行追加 `-- autoplay1 plant` 时自动种一株豆蔻，
## 用于无界面自检攻击动作。追加第 3 个参数 `torch` 会在同排第 5 列补一株火炬树桩，
## 专门验证「飞镖过火炬 → 火焰飞镖」的升级链路。不需要时删掉本函数和上面一行调用即可。
func _debug_auto_plant_from_args() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	print("调试：命令行参数=", args, " 副模式=", Global.autoplay_sub_mode)
	if args.size() < 2:
		return
	# 跳关时副模式被选关脚本搬到了 Global（命令行位置被关卡号占着），
	# 这里优先取它，取到后立刻清空，避免重开一局又误跑一次。
	if Global.autoplay_sub_mode != "":
		var sub: String = Global.autoplay_sub_mode
		var sub_args: PackedStringArray = Global.autoplay_sub_args
		Global.autoplay_sub_mode = ""
		Global.autoplay_sub_args = PackedStringArray()
		await _debug_run_sub_mode(sub, sub_args)
		return
	## 性能压测入口：`-- autoplay1 stress 80` 直接铺 80 只僵尸并每秒打印一次耗时分布
	if args[1] == "stress":
		var count: int = 60
		if args.size() >= 3:
			count = clampi(args[2].to_int(), 1, 300)
		await _debug_run_stress(count)
		return
	## 波次分帧生成验证入口：`-- autoplay1 wavespawn` 直接跑一次大波，打印跨帧数
	if args[1] == "wavespawn":
		await _debug_measure_wave_spawn()
		return
	## 朝阳童子自检入口：`-- autoplay1 sunflower` 直接在第 3 行第 3 列种一株朝阳童子，
	## 用来录帧确认「浮空打坐立绘 + 抬手产阳光」的实际观感。
	## 追加 `slow 0.5` 可放慢时间轴，抬手/落手各占的帧数更多，便于逐帧核对流畅度。
	if args[1] == "sunflower":
		await get_tree().create_timer(0.4).timeout
		if not is_inside_tree() or is_queued_for_deletion():
			return
		plant_cell_manager.all_plant_cells[2][2].create_plant(
			CharacterRegistry.PlantType.P002SunFlower, false, false)
		print("调试：已在第 3 行第 3 列种下朝阳童子")
		if args.size() >= 3 and args[2] == "slow":
			var sun_scale: float = 0.5
			if args.size() >= 4:
				sun_scale = clampf(args[3].to_float(), 0.02, 1.0)
			Engine.time_scale = sun_scale
			print("调试：时间轴已放慢到 %s 倍" % str(sun_scale))
		return
	## 樱桃炸弹自检入口：`-- autoplay1 cherry` 先在右侧放两只僵尸，再种一株樱桃炸弹，
	## 用来确认「引信节奏 / 双胞胎造型 / 爆炸结算」的实际观感。追加 `slow 0.25` 放慢时间轴。
	if args[1] == "cherry":
		await get_tree().create_timer(0.4).timeout
		if not is_inside_tree() or is_queued_for_deletion():
			return
		if args.size() >= 3 and args[2] == "slow":
			var cherry_scale: float = 0.25
			if args.size() >= 4:
				cherry_scale = clampf(args[3].to_float(), 0.02, 1.0)
			Engine.time_scale = cherry_scale
			print("调试：时间轴已放慢到 %s 倍" % str(cherry_scale))
		var cherry_cell: PlantCell = plant_cell_manager.all_plant_cells[2][2]
		for i in 2:
			zombie_manager.create_skill_zombie(
				CharacterRegistry.ZombieType.Z001Norm, 2,
				cherry_cell.global_position.x + 120.0 + i * 70.0)
		cherry_cell.create_plant(CharacterRegistry.PlantType.P003CherryBomb, false, false)
		print("调试：已在第 3 行第 3 列种下樱桃炸弹，右侧两只普通僵尸")
		return
	## 镇山老翁自检入口：`-- autoplay1 wallnut` 在第 3 行第 3 列种一株坚果，
	## 用来确认「整图立绘 + 背后竹杖 + 待机摆动」在**战斗场景**里也成立
	## （图鉴详情页走的是 ready_show，战斗走 ready_norm，是两条不同的初始化路径）。
	## 追加 `stage 2` 可把它直接压到指定形态，检查换图与抽杖在战场上的观感。
	if args[1] == "wallnut":
		await get_tree().create_timer(0.4).timeout
		if not is_inside_tree() or is_queued_for_deletion():
			return
		var nut_cell: PlantCell = plant_cell_manager.all_plant_cells[2][2]
		var nut: Plant000Base = nut_cell.create_plant(
			CharacterRegistry.PlantType.P004WallNut, false, false)
		print("调试：已在第 3 行第 3 列种下镇山老翁 → ", nut != null)
		if nut == null:
			return
		# 立绘/竹杖挂好没有（战斗路径最容易漏的就是这一步）
		var nut_art: Node = nut.find_child("WallnutArt", true, false)
		var nut_staff: Node = nut.find_child("WallnutStaff", true, false)
		print("调试：立绘=", nut_art != null, " 竹杖=", nut_staff != null,
			" 原散件隐藏=", nut.get_node_or_null("Body/BodyCorrect") != null
			and not (nut.get_node("Body/BodyCorrect") as Node2D).visible)
		if args.size() >= 3 and args[2] == "stage":
			var want: int = 2
			if args.size() >= 4:
				want = clampi(args[3].to_int(), 1, 2)
			await get_tree().create_timer(0.6).timeout
			if not is_instance_valid(nut):
				return
			# 阈值沿用场景里的 3666 / 1833：2000 → 态2，800 → 态3
			var hp_arg: int = 2000 if want == 1 else 800
			nut._on_hp_loss(hp_arg, true)
			print("调试：镇山老翁已压到形态 ", nut._stage, "（血量参数 ", hp_arg, "）")
		return
	## 魔术师僵尸自检入口：`-- autoplay1 4 magician` 在第 3 行第 3 列种一株坚果当靶子，
	## 右侧 430 像素放一只魔术师，逐次打印「开始施法 / 掉血 / 恢复行走 / 位置」，
	## 用来核对「每 10 秒一发、单发 500、施法 2 秒停步、打完继续走」这条链路。
	## 追加一个数字可改观察时长，例如 `-- autoplay1 4 magician 35`。
	if args[1] == "magician":
		await _debug_run_magician(args)
		return
	## 醉仙客自检入口：`-- autoplay1 8 chomper` 在第 3 行第 3 列种一株醉仙客，
	## 并在它右边很近的位置放一只普通僵尸，让咬合与酒葫芦演出很快触发。
	## 追加 `slow 0.25` 可放慢时间轴逐帧核对「起手 → 拔塞 → 倾口 → 回位」四段。
	if args[1] == "chomper":
		await get_tree().create_timer(0.4).timeout
		if not is_inside_tree() or is_queued_for_deletion():
			return
		var chomp_cell: PlantCell = plant_cell_manager.all_plant_cells[2][2]
		var chomp: Plant000Base = chomp_cell.create_plant(
			CharacterRegistry.PlantType.P007Chomper, false, false)
		print("调试：已在第 3 行第 3 列种下醉仙客 → ", chomp != null)
		if chomp == null:
			return
		# 道具层挂好没有（葫芦 / 木塞两张贴图，缺一张演出就哑了）
		print("调试：葫芦=", chomp.find_child("PropGourd", true, false) != null,
			" 木塞=", chomp.find_child("PropCap", true, false) != null)
		# 僵尸放近一点（葫芦的攻击范围有限），免得等它慢慢走过来
		var z: Zombie000Base = zombie_manager.create_skill_zombie(
			CharacterRegistry.ZombieType.Z001Norm, 2, chomp_cell.global_position.x + 150.0)
		print("调试：该行右侧生成僵尸 → %s" % str(z != null))
		if args.size() >= 3 and args[2] == "slow":
			var c_scale: float = 0.25
			if args.size() >= 4:
				c_scale = clampf(args[3].to_float(), 0.02, 1.0)
			Engine.time_scale = c_scale
			print("调试：时间轴已放慢到 %s 倍" % str(c_scale))
		return
	if args[1] == "chomp":
		await _debug_run_chomper(args, 1)
		return
	if args[1] != "plant":
		return
	await get_tree().create_timer(0.4).timeout
	if not is_inside_tree() or is_queued_for_deletion():
		return
	var row: Array = plant_cell_manager.all_plant_cells[2]
	var cell: PlantCell = row[2]
	cell.create_plant(CharacterRegistry.PlantType.P001PeaShooterSingle, false, false)
	print("调试：已在第 3 行第 3 列种下豆蔻")
	if args.size() >= 3 and args[2] == "torch":
		plant_cell_manager.all_plant_cells[2][4].create_plant(
			CharacterRegistry.PlantType.P023TorchWood, false, false)
	# 立刻放一只僵尸在它右边，免得等自然出怪
	var zombie: Zombie000Base = zombie_manager.create_skill_zombie(
		CharacterRegistry.ZombieType.Z001Norm, 2, cell.global_position.x + 380.0)
	print("调试：该行右侧生成僵尸 → %s" % str(zombie != null))
	if args.size() >= 3 and args[2] == "slow":
		# 放慢时间轴（只给录帧检查动作用），正常游戏不会走到这里
		# 第 4 个参数可以指定倍率，例如 `-- autoplay1 plant slow 0.1` 看得更细
		var scale: float = 0.25
		if args.size() >= 4:
			scale = clampf(args[3].to_float(), 0.02, 1.0)
		Engine.time_scale = scale
		print("调试：时间轴已放慢到 %s 倍" % str(scale))


## 临时性能压测：铺满僵尸后逐帧采样，打印中位帧耗时。
## 只在命令行带 `stress <数量>` 时进入，正常游戏不会走到这里。
##
## 实测结论（2026-10-24，本机 Intel Arc 核显，关垂直同步，取中位帧）：
##   40 只 → 6.5ms(≈153fps)   80 只 → 12.2ms(≈82fps)   160 只 → 28.0ms(≈36fps)
##   基本线性，约 0.15~0.17ms/只，draw calls 也随之线性涨（80 只约 1350）。
##
## 两条已验证/已排除的优化方向：
##   1) 已修：大波僵尸「同一帧实例化」40 只 102ms、80 只 207ms、160 只 358ms（约 2.2ms/只），
##      改成按 3ms/帧预算分帧生成后，最慢单帧降到 5ms，僵尸总数与出场顺序不变。
##      见 zm_zombie_wave_create_manager.gd 的 SPAWN_FRAME_BUDGET_MSEC。
##   2) 已排除：每个僵尸动画 151 条轨道，其中 22% 是恒定值冗余轨道，删掉/禁用后
##      80 只僵尸的帧时间没有可测变化（±10% 噪声内），160 只只有 -12%，
##      说明瓶颈是「每个 AnimationTree 实例的固定开销」，不是轨道数量，别再往这个方向找。
##   注意：僵尸位移是由 Zombie_walk 动画里 `_ground:position` 这条轨道驱动的（传送带做法），
##   所以不能给离屏僵尸关 AnimationTree，否则它就不走了。
## 把自检子模式的分派集中在这里，`_debug_auto_plant_from_args()` 只管解析命令行。
## [br]`sub_arg_offset` 决定 `slow` 之类的修饰词从 args 的第几个位置开始读：
## 直接敲命令时是 `autoplay1 chomper slow`（偏移 2），跳关时是 `autoplay1 8 chomper slow`（偏移 3）。
func _debug_run_sub_mode(sub: String, args: PackedStringArray) -> void:
	var offset: int = 2 if args.size() >= 2 and args[1].is_valid_int() else 1
	if args.size() >= 3 and args[1] == "level":
		offset = 3
	if sub == "chomper" or sub == "chomp":
		await _debug_run_chomper(args, offset)
		return
	if sub == "magician":
		await _debug_run_magician(args)
		return
	# 其余子模式还没迁过来，保持旧路径（命令行里第 1 个就是子模式）
	if sub == "plant":
		Engine.set_meta("debug_plant_sub_args", args)
		return


## 醉仙客自检：种一株 + 近距离放一只僵尸，观察咬合前后的酒葫芦演出。
## 追加 `garg` 会把那只陪练换成巨人僵尸，用来验「吞不掉 → 吸附掉血 200/跳」那条分支。
func _debug_run_chomper(args: PackedStringArray, offset: int) -> void:
	await get_tree().create_timer(0.4).timeout
	if not is_inside_tree() or is_queued_for_deletion():
		return
	var spawn_garg: bool = "garg" in args
	var chomp_cell: PlantCell = plant_cell_manager.all_plant_cells[2][2]
	var chomp: Plant000Base = chomp_cell.create_plant(
		CharacterRegistry.PlantType.P007Chomper, false, false)
	# 对照尺：左邻格种一株豆蔻，录帧时同一画面比大小
	# （醉仙客的战场高度 CHOMPER_H 改过几轮，单看一株判断不了偏大偏小）。
	plant_cell_manager.all_plant_cells[2][1].create_plant(
		CharacterRegistry.PlantType.P001PeaShooterSingle, false, false)
	print("调试：已在第 3 行第 3 列种下醉仙客 → ", chomp != null)
	if chomp == null:
		return
	# 位置/可见性诊断：录帧全是空草坪时，最先要排除的就是「植物种到画面外」或「整株不可见」
	print("调试：醉仙客位置=", chomp.global_position, " 可见=", chomp.visible,
		" 格位=", chomp_cell.global_position)
	print("调试：葫芦=", chomp.find_child("PropGourd", true, false) != null,
		" 木塞=", chomp.find_child("PropCap", true, false) != null)
	var z: Zombie000Base = zombie_manager.create_skill_zombie(
		CharacterRegistry.ZombieType.Z024Gargantuar if spawn_garg \
			else CharacterRegistry.ZombieType.Z001Norm,
		2, chomp_cell.global_position.x + 150.0)
	print("调试：该行右侧生成%s → %s，位置=%s" % ["巨人" if spawn_garg else "僵尸",
		str(z != null), str(z.global_position) if z != null else "null"])
	if spawn_garg and z != null:
		print("调试：巨人血量=", z.hp_component.curr_hp, "/", z.hp_component.max_hp)
	# ⚠️ 不要在这里手改 z.global_position：僵尸位移是 `Zombie_walk` 动画里
	# `_ground:position` 轨道驱动的（传送带做法），直接赋值会在下一帧被动画覆盖，
	# 而且镜头拉回全景时坐标基准不一致，实测会把僵尸甩到画面外。
	# 它自己会走过来，把 quit-after 拉长即可。
	if args.size() > offset and args[offset] == "slow":
		var c_scale: float = 0.25
		if args.size() > offset + 1:
			c_scale = clampf(args[offset + 1].to_float(), 0.02, 1.0)
		Engine.time_scale = c_scale
		print("调试：时间轴已放慢到 %s 倍" % str(c_scale))


## 魔术师僵尸自检：种一株坚果当靶子，右侧放一只魔术师，按时间轴打印施法/掉血/位移。
## 不带慢放：10 秒的间隔必须按真实时间看，放慢会把「每 10 秒一发」的量测搅乱。
func _debug_run_magician(args: PackedStringArray) -> void:
	## 观察时长默认 23 秒，正好覆盖两次施法（第 10 秒、第 20 秒）
	var observe_time: float = 23.0
	var mode_index: int = args.find("magician")
	if mode_index >= 0 and args.size() > mode_index + 1 and args[mode_index + 1].is_valid_int():
		observe_time = clampi(args[mode_index + 1].to_int(), 5, 90)

	await get_tree().create_timer(0.4).timeout
	if not is_inside_tree() or is_queued_for_deletion():
		return
	var cell: PlantCell = plant_cell_manager.all_plant_cells[2][2]
	var nut: Plant000Base = cell.create_plant(
		CharacterRegistry.PlantType.P004WallNut, false, false)
	if nut == null:
		print("调试：魔术师自检失败，靶子坚果没种下去（格子被占？）")
		return
	var spawn_x: float = cell.global_position.x + 430.0
	var mag: Zombie026Magician = zombie_manager.create_skill_zombie(
		CharacterRegistry.ZombieType.Z026Magician, 2, spawn_x) as Zombie026Magician
	if mag == null:
		print("调试：魔术师自检失败，僵尸没生成出来")
		return
	print("调试：魔术师自检开始 → 僵尸hp=%d/%d 出生x=%.0f 靶子hp=%d 观察%.0f秒"
		% [mag.hp_component.curr_hp, mag.hp_component.max_hp, spawn_x,
		nut.hp_component.curr_hp, observe_time])

	var begin_ms: int = Time.get_ticks_msec()
	var last_casting: bool = false
	var last_target_hp: int = nut.hp_component.curr_hp
	var last_sample_time: float = 0.0
	while true:
		await get_tree().create_timer(0.2).timeout
		var t: float = (Time.get_ticks_msec() - begin_ms) / 1000.0
		if not is_instance_valid(mag):
			print("调试：[%.2f] 魔术师已被释放" % t)
			break
		if mag._is_casting != last_casting:
			last_casting = mag._is_casting
			print("调试：[%.2f] %s  x=%.0f 靶子hp=%d" % [
				t, "开始施法（停步）" if last_casting else "施法结束（恢复行走）",
				mag.global_position.x,
				nut.hp_component.curr_hp if is_instance_valid(nut) else -1])
		if is_instance_valid(nut):
			var hp_now: int = nut.hp_component.curr_hp
			if hp_now != last_target_hp:
				print("调试：[%.2f] 靶子掉血 %d → %d（本次 %d）"
					% [t, last_target_hp, hp_now, last_target_hp - hp_now])
				last_target_hp = hp_now
		elif last_target_hp >= 0:
			print("调试：[%.2f] 靶子已被打掉" % t)
			last_target_hp = -1
		if t - last_sample_time >= 4.0:
			last_sample_time = t
			print("调试：[%.2f] 位置 x=%.0f 存活=%s"
				% [t, mag.global_position.x, str(not mag.is_death)])
		if t >= observe_time or mag.is_death:
			break
	print("调试：魔术师自检结束（观察 %.0f 秒）" % observe_time)
	get_tree().quit()


func _debug_run_stress(count: int) -> void:
	## 压测时必须关垂直同步，否则帧率被锁在显示器刷新率上，量不出真实开销
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	await get_tree().create_timer(0.6).timeout
	if not is_inside_tree() or is_queued_for_deletion():
		return
	var rows: int = plant_cell_manager.all_plant_cells.size()
	var per_row: int = maxi(1, count / maxi(1, rows))
	for lane in rows:
		for i in per_row:
			zombie_manager.create_skill_zombie(
				CharacterRegistry.ZombieType.Z001Norm, lane, 620.0 + i * 34.0)
	print("性能压测：请求 %d 只，实际铺 %d 只" % [count, per_row * rows])

	await _debug_sample_perf("A 正常", 160)


## 直接跑一次大波，打印「僵尸数 / 跨了几帧 / 总耗时」，用来确认分帧生成生效。
## 只在命令行带 `wavespawn` 时进入，正常游戏不会走到这里。
func _debug_measure_wave_spawn() -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	await get_tree().create_timer(0.6).timeout
	if not is_inside_tree() or is_queued_for_deletion():
		return
	var m: ZombieWaveCreateManager = find_child("ZombieWaveCreateManager", true, false) as ZombieWaveCreateManager
	if m == null:
		print("[波次生成] 找不到 ZombieWaveCreateManager")
		return
	var frame_begin: int = Engine.get_process_frames()
	var time_begin: int = Time.get_ticks_msec()
	var list: Array[Zombie000Base] = await m.create_curr_wave_all_zombies(40, true)
	var span_frames: int = Engine.get_process_frames() - frame_begin
	var span_msec: int = Time.get_ticks_msec() - time_begin
	print("[波次生成] 大波僵尸 %d 只，跨 %d 帧，总耗时 %d ms，最慢单帧实例化 %d ms（分帧前约 207ms/80只）"
		% [list.size(), span_frames, span_msec, m.spawn_max_frame_msec])
	await _debug_sample_perf("B 分帧生成后", 160)


## 逐帧采样取中位数，避免单帧尖峰（出怪那一帧）污染平均值。
## [param frames] 为采样帧数，前 20 帧作为预热丢弃。
func _debug_sample_perf(tag: String, frames: int) -> void:
	for i in 20:
		await get_tree().process_frame
	var deltas: Array[float] = []
	var tick_prev: int = Time.get_ticks_usec()
	for i in frames:
		await get_tree().process_frame
		var tick_now: int = Time.get_ticks_usec()
		deltas.append(float(tick_now - tick_prev) / 1000000.0)
		tick_prev = tick_now
	deltas.sort()
	var n: int = deltas.size()
	if n == 0:
		return
	var med: float = deltas[n / 2]
	print("[%s] 中位帧=%.2fms (≈%.1ffps)  p90=%.2fms  最慢=%.2fms  nodes=%d draws=%d"
		% [tag, med * 1000.0, 1.0 / maxf(med, 0.00001),
			deltas[mini(n - 1, int(n * 0.9))] * 1000.0, deltas[n - 1] * 1000.0,
			int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)),
			int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))])


#region 游戏结束
## 修改僵尸位置
func change_zombie_position(zombie:Zombie000Base):
	## 要删除碰撞器，不然会闪退(这里好像是因为暂停的时候会重复循环执行一些代码，不清楚为什么)
	zombie.hurt_box_component.free()
	zombie.get_parent().remove_child(zombie)
	panel_zombie_go_home.add_child(zombie)
	zombie.position = marker_2d_zombie_go_home.position
	if game_para.game_BG == ConstLevelData.GameBg.Roof:
		roof_zombie_go_home(zombie)


func roof_zombie_go_home(zombie:Zombie000Base):
	print("禁用僵尸移动组件")
	zombie.move_component.disable_component(ComponentNormBase.E_IsEnableFactor.GameMode)
	await get_tree().create_timer(3).timeout
	var tween = zombie.create_tween()
	tween.tween_property(zombie, "position:y", 300, 10.0).as_relative()



## 僵尸进房
func on_zombie_go_home(zombie:Zombie000Base):
	re_main_game()

	main_game_progress = E_MainGameProgress.GAME_OVER
	card_slot_root.visible = false

	## 设置相机可以移动
	camera_2d.process_mode = Node.PROCESS_MODE_ALWAYS
	## 游戏暂停
	TreePauseManager.start_tree_pause(TreePauseManager.E_PauseFactor.GameOver)
	call_deferred("change_zombie_position", zombie)
	## 如果有锤子
	if game_para.is_hammer:
		game_item_manager.gim_other.hammer.set_is_used(false)
	await get_tree().create_timer(1).timeout

	camera_2d.move_to(Vector2(-200, 0), 2)
	SoundManager.play_other_SFX("losemusic")
	await get_tree().create_timer(3).timeout
	SoundManager.play_other_SFX("scream")
	ui_remind_word.zombie_won_word_appear()


#region 奖杯
## 接受本轮第一次结束请求，成功返回 true；只在正式战斗且未失败、未过渡时接受。
## [param is_boss_win] 表示实际由额外 Boss 条件结束，不表示关卡是否启用了该选项。
func try_claim_round_end(is_boss_win: bool = false) -> bool:
	if not is_inside_tree() or is_queued_for_deletion() \
		or main_game_progress != E_MainGameProgress.MAIN_GAME \
		or _round_end_claimed or _round_transition_pending \
		or TreePauseManager.curr_pause_factor.get(TreePauseManager.E_PauseFactor.GameOver, false):
		return false
	_round_end_claimed = true
	_round_end_by_boss = is_boss_win
	return true


## 普通胜利请求共用一次性结算入口；[param glo_pos] 为奖杯生成的世界坐标。
## 清场、罐子和脑子条件始终有效，与额外 Boss 胜利选项独立。
func create_trophy(glo_pos: Vector2) -> void:
	if not try_claim_round_end():
		return
	_finish_round_victory(glo_pos)


## [param glo_pos] 为最后一只 Boss 请求的奖杯世界坐标；完成已接受的 Boss 胜利。
## 动画和直接消失由僵王管理器保证只请求一次，此处不重新接受胜利条件。
func complete_boss_victory(glo_pos: Vector2) -> void:
	if not is_inside_tree() or is_queued_for_deletion() \
		or not _round_end_claimed or not _round_end_by_boss or _round_transition_pending \
		or main_game_progress != E_MainGameProgress.GAME_OVER \
		or TreePauseManager.curr_pause_factor.get(TreePauseManager.E_PauseFactor.GameOver, false):
		return
	_finish_round_victory(glo_pos)


## 完成已接受的胜利，非末轮直接过渡，末轮生成奖杯或直接结算掉落；[param glo_pos] 为世界坐标。
func _finish_round_victory(glo_pos: Vector2) -> void:
	print("胜利条件达成，结算通关")
	## 如果不是最后一轮游戏，触发下一轮
	if curr_game_round != game_para.game_round:
		_advance_to_next_round()
		return


	print("=======================游戏结束，您获胜了=======================")
	## 草坪上掉的是什么，分两种情况：
	## [br]1. 冒险 50 关**首次通关** → 掉这一关解锁的那张东西（植物卡 / 铲子 / 纸条 / 奖杯），
	## 原版掉的就是解锁物本身，不该先给一个通用奖杯让人捡；
	## [br]2. 没有掉落可演（重复挑战已通关的关卡、其它模式没有掉落表）→ 通用奖杯。
	## 两者的抛出、捡起、光芒、结算手感完全共用，差别只在生成的物件。
	var pickup: RewardPickup = RewardPickup.spawn(canvas_layer_temp, _take_level_reward())
	# 记一笔「这一关的卡是玩家在草坪上捡到的」：后面那屏就不必再把同一张卡画一遍
	_reward_via_pickup = pickup != null
	var drop: Node2D = pickup
	if drop == null:
		drop = SceneRegistry.TROPHY.instantiate()
		canvas_layer_temp.add_child(drop)
	drop.global_position = glo_pos
	if drop.global_position.x >= 750:
		# 右侧掉落物向场内抛出的水平偏移。
		var x_diff = drop.global_position.x - 700
		throw_to(drop, drop.position - Vector2(x_diff + randf_range(-50,50), 0))
	elif drop.global_position.x <= 50:
		# 左侧掉落物向场内抛出的水平偏移。
		var x_diff = drop.global_position.x - 100
		throw_to(drop, drop.position - Vector2(x_diff + randf_range(-50,50), 0))

	else:
		throw_to(drop, drop.position - Vector2(randf_range(-50,50), 0))

## 掉落物抛出
func throw_to(node:Node2D, target_pos: Vector2, duration: float = 1.0):
	main_game_progress = E_MainGameProgress.GAME_OVER
	var start_pos = node.position
	var peak_pos = start_pos.lerp(target_pos, 0.5)
	peak_pos.y -= 50  # 向上抛

	var tween = create_tween()
	tween.tween_property(node, "position:x", target_pos.x, duration).set_trans(Tween.TRANS_LINEAR)

	tween.parallel().tween_property(node, "position:y", peak_pos.y, duration / 2).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	tween.parallel().tween_property(node, "position:y", target_pos.y, duration / 2).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN).set_delay(duration / 2)

#endregion


## 当前关卡完成；奖杯点击的延迟回调在失败后到达时不能再登记通关。
func win_main_game():
	# 奖杯按钮等待期间仍可能进房失败，必须在清除暂停因素前拒绝晚到回调。
	if TreePauseManager.curr_pause_factor.get(TreePauseManager.E_PauseFactor.GameOver, false):
		return

	## 游戏暂停因素、游戏速度
	TreePauseManager.end_tree_pause_clear_all_pause_factors()
	Global.time_scale = 1.0
	Engine.time_scale = Global.time_scale

	## ⚠️ 掉落判定必须在写通关记录**之前**做：记录写下去之后这一关就永远是「已通关」，
	## 判断不出「是不是首次通关」，重复打同一关会每次都掉一张卡。
	var reward: Dictionary = _take_level_reward()
	update_level_state_data_success()
	## 多轮游戏，重置主游戏数据
	if game_para.game_round != 1:
		re_main_game()
	## 有掉落就先演「获得新植物 / 获得新道具」，玩家点收下之后再退回选关界面
	if not reward.is_empty():
		_show_level_reward(reward)
		return
	back_to_mode_scene()


## 退回本关所属模式的场景（冒险 → 选关，其它 → 对应入口）。
func back_to_mode_scene() -> void:
	get_tree().change_scene_to_file(Global.main_scene_registry.MainScenesMap.get(game_para.game_mode, Global.main_scene_registry.MainScenesMap[MainSceneRegistry.MainScenes.StartMenu]))


## 本关首次通关时应当掉落的东西；不该掉落时返回空字典。
## [br]结构见 [method AdventureReward.get_reward]，调用方不用分辨是植物还是道具。
## [br]返回空字典的三种情况：不是 50 关版冒险模式、这一关已经通关过（重复挑战）、
## 存档键取不出关卡序号。
func _take_level_reward() -> Dictionary:
	if game_para == null or game_para.game_mode != MainSceneRegistry.MainScenes.ChooseLevelAdventure50:
		return {}
	var save_name: String = game_para.save_game_name
	var state: Dictionary = Global.global_game_state.curr_all_level_state_data.get(save_name, {})
	if state.get("IsSuccess", false):
		return {}
	return AdventureReward.get_reward(AdventurePlantUnlock.level_no_from_save_name(save_name))


## 本关的掉落是不是已经被玩家在草坪上捡到了（见 [RewardPickup]）。
## [br]是的话，后面那屏只补名字与说明，不再画一遍同一张卡。
var _reward_via_pickup: bool = false


## 弹出掉落演出，收下后才切回选关界面。
## [br]宿主挂 [code]get_tree().root[/code] 而不是主游戏场景：切场景会把当前场景整棵释放，
## 挂在场景上的演出会跟着一起没；root 只有 current_scene 会被替换，挂在 root 上的层能活到玩家点完。
func _show_level_reward(reward: Dictionary) -> void:
	var host: Node = get_tree().root
	if host == null:
		back_to_mode_scene()
		return
	# 掉什么打进日志：这一屏是纯手搭 UI，出问题时除了日志没有别的痕迹可查
	print("掉落演出：%s%s" % [_reward_text(reward), "（已在草坪上捡到，不再画图）" if _reward_via_pickup else ""])
	# 取完就清：这面旗只服务「捡到卡之后的这一屏」
	var with_art: bool = not _reward_via_pickup
	_reward_via_pickup = false
	var layer := LevelReward.show_for(host, reward, with_art)
	if layer == null:
		back_to_mode_scene()
		return
	layer.closed.connect(back_to_mode_scene)


## 掉落物的一行文字，只用于日志（植物写编号 + 图鉴名，道具写名字）。
func _reward_text(reward: Dictionary) -> String:
	if int(reward.get("kind", -1)) == AdventureReward.Kind.Plant:
		var plant_id: int = int(reward.get("plant_id", 0))
		var raw: Variant = Global.character_registry.get_plant_info(
			plant_id, CharacterRegistry.PlantInfoAttribute.PlantName)
		return "植物 P%03d %s" % [plant_id, String(raw) if raw != null else "?"]
	return "道具 %s（%s）" % [String(reward.get("name", "")), String(reward.get("key", ""))]

#endregion


#region 锤子鼠标交互
## 锤子鼠标进入后，显示鼠标
func mouse_appear_have_hammer():
	if main_game_progress == E_MainGameProgress.MAIN_GAME:
		## 如果有锤子
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

## 有锤子时连接该信号
func mouse_disappear_have_hammer():
	## 如果有锤子不显示鼠标（非重新开始、离开游戏）
	if not is_mouse_visibel_on_hammer and main_game_progress == E_MainGameProgress.MAIN_GAME:
		## 如果有锤子
		Input.set_mouse_mode(Input.MOUSE_MODE_HIDDEN)

## 点击重新开始或主菜单时，修改值，可以一直显示鼠标
func change_is_mouse_visibel_on_hammer(value:bool):
	if game_para.is_hammer:
		is_mouse_visibel_on_hammer = value

#endregion

#region 存档
## 读档系统只能从空白场景读档

## 保存轮末快照；实际由 Boss 提前结束的自然波次按已完成本轮保存，续关不补旧波。
func save_game_main_game():
	# 本轮结束后的快照，加载时直接进入下一轮。
	var save_game_data_main_game:ResourceSaveGameMainGame = ResourceSaveGameMainGame.new()
	save_game_data_main_game.curr_game_round = curr_game_round
	## 植物数据
	save_game_data_main_game.plant_cell_manager_data = plant_cell_manager.get_save_game_data_plant_cell_manager()
	## 僵尸, gema_para 自动更新该值
	save_game_data_main_game.curr_max_wave = zombie_manager.zombie_wave_manager.max_wave
	save_game_data_main_game.curr_wave = zombie_manager.zombie_wave_manager.curr_wave
	if _round_end_by_boss and game_para.monster_mode == ConstLevelData.E_MonsterMode.Norm:
		# 只标准化实际 Boss 胜利的快照，不依据配置或死亡统计推断结束原因。
		save_game_data_main_game.curr_wave = save_game_data_main_game.curr_max_wave - 1
	## 天降阳光
	save_game_data_main_game.day_sun_curr_sun_sum_value = day_suns_manager.curr_sun_sum_value
	## 植物卡槽数据
	save_game_data_main_game.card_manager_data = card_manager.get_save_game_data_card_manager()
	## 小推车数据
	save_game_data_main_game.lawn_mover_manager_data = game_item_manager.gim_lawn_mover.get_save_game_data_lawn_mover_manager()
	# 僵王管理器保留存活实例与整局统计；读档后的待恢复数据也由其统一保存。
	save_game_data_main_game.boss_manager_data = zombie_manager.get_save_game_data_bosses()

	# 当前关卡轮间快照的保存路径。
	var path = game_para.get_save_game_path()
	# 资源保存结果，失败时保留错误码供诊断。
	var err = ResourceSaver.save(save_game_data_main_game, path)
	if err != OK:
		push_error("关卡数据存档失败:%s, 错误代码 %d" % [path, err])
	else:
		print("关卡数据存档成功：", path)
		update_level_state_data_multi_round_data(true)


## 重置当前主游戏 多轮关卡存档,多轮关卡数据
func re_main_game():
	## 删除存档(若有存档会删除,没有就跳过)
	game_para.delete_game_data()
	## 更新当前关卡数据
	update_level_state_data_multi_round_data(false)


## 读档
func load_game_main_game():
	if game_para.save_game_data_main_game != null:
		curr_game_round = game_para.save_game_data_main_game.curr_game_round
		var save_game_data_main_game:ResourceSaveGameMainGame = game_para.save_game_data_main_game
		## 罐子模式
		if game_para.is_pot_mode:
			if game_para.is_save_plant_on_pot_mode:
				plant_cell_manager.load_game_data_plant_cell_manager(save_game_data_main_game.plant_cell_manager_data)
		else:
			plant_cell_manager.load_game_data_plant_cell_manager(save_game_data_main_game.plant_cell_manager_data)
		## 天降阳光
		day_suns_manager.curr_sun_sum_value = save_game_data_main_game.day_sun_curr_sun_sum_value
		## 植物卡槽数据
		card_manager.load_game_data_card_manager(save_game_data_main_game.card_manager_data)
		# 选卡和准备阶段只缓存僵王数据，正式进入 MAIN_GAME 后再恢复角色实例。
		zombie_manager.load_game_data_bosses(save_game_data_main_game.boss_manager_data)

#endregion
#region 更新全局关卡数据
## 更新当前关卡数据 (完成)
func update_level_state_data_success():
	## 更新全局关卡数据
	var curr_level_state_data:Dictionary = Global.global_game_state.curr_all_level_state_data.get(game_para.save_game_name, {})
	curr_level_state_data["IsSuccess"] = true
	Global.global_game_state.curr_all_level_state_data[game_para.save_game_name] = curr_level_state_data
	Global.save_service.save_now()
	# 冒险模式（50 关版）通关后立即刷新可用植物，下一关选卡就能看到刚解锁的植物
	if game_para.game_mode == MainSceneRegistry.MainScenes.ChooseLevelAdventure50:
		AdventurePlantUnlock.apply_to_game_state()

## 更新当前关卡数据 (多轮游戏)
func update_level_state_data_multi_round_data(is_have_multi_round_data:=true):
	## 更新全局关卡数据
	var curr_level_state_data:Dictionary = Global.global_game_state.curr_all_level_state_data.get(game_para.save_game_name, {})
	curr_level_state_data["IsHaveMultiRoundSaveGameData"] = is_have_multi_round_data
	curr_level_state_data["CurrGameRound"] = curr_game_round
	Global.global_game_state.curr_all_level_state_data[game_para.save_game_name] = curr_level_state_data
	Global.save_service.save_now()
#endregion
