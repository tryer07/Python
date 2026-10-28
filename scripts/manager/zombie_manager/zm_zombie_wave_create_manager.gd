extends Node
## 僵尸波次生成管理器
class_name ZombieWaveCreateManager

#region 波次生成僵尸管理器参数
## 出怪倍率
var zombie_multy := 1
## 蹦极僵尸数量范围
var range_num_bungi:Vector2i = Vector2i(3,5)
#endregion
@onready var zombie_manager: ZombieManager = %ZombieManager

## 僵尸选行系统
@onready var zombie_choose_row_system: ZombieChooseRowSystem = %ZombieChooseRowSystem

## 本管理器独立维护的运行时权重，实例创建时复制注册表基础数据，后续按自然波次调整。[br]
## 键和值均为整数值类型，普通复制即可隔离修改，无需深度复制。
var zombie_weights: Dictionary[CharacterRegistry.ZombieType, int] = CharacterRegistry.ZombieSpawnWeights.duplicate()

## 僵尸随机选择池
var zombie_choose_random_pool:RandomPicker

## 关卡允许出怪的行权重，下标即行号。空数组表示所有行都可以出怪（默认）。[br]
## 草坪只铺了一部分时，没草皮的行同样不能出僵尸，否则僵尸会走在荒土上白吃一条车道。
var lane_weights: Array[float] = []

## 每波最大僵尸数量
@export var max_zombies_per_wave = 50

## 单帧生成预算（毫秒）。一个僵尸从实例化到入树约 2ms，
## 大波一次铺 40~50 只放在同一帧会冻结 100~200ms（实测 80 只 207ms）。
## 超过预算就让出一帧再继续，场上僵尸总数和出场顺序完全不变，只是把开销摊到几十帧里。
const SPAWN_FRAME_BUDGET_MSEC := 3
## 刷新类型最小战力
var min_power:=100
## 当前波次生成的僵尸
var wave_all_zombies:Array[Zombie000Base]

## 上一次波次生成里「单帧花在实例化上的最长时间（毫秒）」，用于验证分帧预算是否生效。[br]
## 分帧前大波一次性生成 80 只约 207ms，分帧后应稳定在 3~6ms。
var spawn_max_frame_msec: int = 0

## 使用 [param game_para] 初始化波次生成配置、选行系统和随机池，保留本实例已有的运行时权重。
func init_zombie_wave_create_manager(game_para:ResourceLevelData):
	zombie_multy = game_para.zombie_multy
	range_num_bungi = game_para.range_num_bungi
	zombie_choose_row_system.init_zombie_choose_row_system(zombie_manager.all_zombie_rows)
	update_lane_weights(game_para.sod_rows)
	update_zombie_refresh_types()


## 按已铺草皮的行生成出怪行权重；[param sod_rows] 为空时保持「所有行都可以出怪」。
func update_lane_weights(sod_rows: Array[int]) -> void:
	lane_weights.clear()
	if sod_rows.is_empty():
		return
	# 与 all_zombie_rows 等长，行号从 0 开始，sod_rows 用的是从 1 开始的行号
	for i: int in zombie_manager.all_zombie_rows.size():
		lane_weights.append(1.0 if sod_rows.has(i + 1) else 0.0)
	print("出怪行权重：", lane_weights, "（空表示所有行都出怪）")


## 更新可以刷新的僵尸列表
func update_zombie_refresh_types():
	## 初始化僵尸生成随机池数据
	var zombie_choose_random_pool_data:Array[Array] = []
	min_power = 100
	for zombie_type in zombie_manager.zombie_refresh_types:
		if min_power > CharacterRegistry.ZombieSpawnPower[zombie_type]:
			min_power = CharacterRegistry.ZombieSpawnPower[zombie_type]
		zombie_choose_random_pool_data.append([zombie_type, zombie_weights[zombie_type]])
	print("更新僵尸随机选择池")
	zombie_choose_random_pool = RandomPicker.new(zombie_choose_random_pool_data)


#region 创建当前波次僵尸
## 创建当前波僵尸。[br]
## 返回前会把整波僵尸都生成好；若单帧预算用尽会 [code]await[/code] 让出一帧，
## 因此调用方要写成 [code]await create_curr_wave_all_zombies(...)[/code]。
func create_curr_wave_all_zombies(wave:int, is_big_wave:bool):
	## 获取当前波僵尸生成列表
	var wave_spawn :Array[CharacterRegistry.ZombieType] = create_curr_wave_zombie_list(wave, is_big_wave)
	## 特殊基础权重,若有雪橇车僵尸,更新该权重
	var special_base_weight:Array[float] = []
	wave_all_zombies.clear()
	spawn_max_frame_msec = 0
	## 当前波次僵尸数据
	var curr_wave_zombie_date:Array[Dictionary]
	## 本帧开始生成的时间戳，用于分帧预算
	var frame_spawn_start: int = Time.get_ticks_msec()

	for i in range(wave_spawn.size()):
		var zombie_type : CharacterRegistry.ZombieType = wave_spawn[i]
		var lane :int = -1
		## 雪橇车僵尸
		if zombie_type == CharacterRegistry.ZombieType.Z014Bobsled:
			## 计算冰道权重
			if special_base_weight.is_empty():
				for row_ice_road:Array[IceRoad] in zombie_manager.all_ice_roads:
					if row_ice_road.is_empty():
						special_base_weight.append(0)
					else:
						special_base_weight.append(1)
				print(special_base_weight)
			## 如果没有冰道
			if GlobalUtils.sum_arr(special_base_weight) == 0:
				zombie_type = CharacterRegistry.ZombieType.Z013Zamboni
				lane = zombie_choose_row_system.select_spawn_row(Global.character_registry.ZombieInfo[zombie_type][CharacterRegistry.ZombieInfoAttribute.ZombieRowType], lane_weights)
			else:
				lane = zombie_choose_row_system.select_spawn_row(Global.character_registry.ZombieInfo[zombie_type][CharacterRegistry.ZombieInfoAttribute.ZombieRowType], special_base_weight)
		else:
			lane = zombie_choose_row_system.select_spawn_row(Global.character_registry.ZombieInfo[zombie_type][CharacterRegistry.ZombieInfoAttribute.ZombieRowType], lane_weights)
		# 选行失败时跳过该项，不能把 -1 作为最后一行索引使用。
		if lane < 0:
			continue
		curr_wave_zombie_date.append(
			{
				"zombie_type":zombie_type,
				"lane":lane,
			}
		)
	for curr_wave_one_zombie_date in curr_wave_zombie_date:
		var zombie = wave_create_zombie(
			curr_wave_one_zombie_date["zombie_type"],
			curr_wave_one_zombie_date["lane"],
			wave
		)
		if is_instance_valid(zombie):
			wave_all_zombies.append(zombie)
		# 单帧预算用尽：让出一帧再继续，避免大波同一帧实例化造成掉帧卡顿。
		var frame_spend: int = Time.get_ticks_msec() - frame_spawn_start
		if frame_spend >= SPAWN_FRAME_BUDGET_MSEC:
			spawn_max_frame_msec = maxi(spawn_max_frame_msec, frame_spend)
			await get_tree().process_frame
			# 等待期间可能已经切关或结束战斗，先退出，由调用方按刷新版本决定是否继续。
			if not is_inside_tree():
				return wave_all_zombies
			frame_spawn_start = Time.get_ticks_msec()
	spawn_max_frame_msec = maxi(spawn_max_frame_msec, Time.get_ticks_msec() - frame_spawn_start)

	return wave_all_zombies


## 生成波次僵尸
func wave_create_zombie(
	zombie_type:CharacterRegistry.ZombieType,
	lane:int, 	## 僵尸行
	curr_wave:int,		## 僵尸波次
	init_zombie_special:Callable = Callable()		## 初始化僵尸特殊属性
):
	# 直接调用者也必须使用真实存在的行，防止错误下标进入通用创建入口。
	if lane < 0 or lane >= zombie_manager.all_zombie_rows.size():
		return null
	var zombie_init_para:Dictionary = {
		Zombie000Base.E_ZInitAttr.CharacterInitType:Character000Base.E_CharacterInitType.IsNorm,
		Zombie000Base.E_ZInitAttr.Lane:lane,
		Zombie000Base.E_ZInitAttr.CurrWave:curr_wave,
	}
	var zombie_parent = zombie_manager.all_zombie_rows[lane]
	var zombie_glo_pos = zombie_manager.all_zombie_rows[lane].zombie_create_position.global_position + Vector2(randf_range(-10, 10), 0)

	var zombie = zombie_manager.create_norm_zombie(zombie_type,zombie_parent,zombie_init_para, zombie_glo_pos, init_zombie_special)

	return zombie

#region 创建当前波僵尸生成列表
## 根据零起始波次 [param wave] 和大波标记 [param is_big_wave] 返回本波僵尸类型列表。[br]
## 每次生成前同步权重与随机池，确保直接载入后期波次也使用对应的衰减权重。
func create_curr_wave_zombie_list(wave:int, is_big_wave:bool):
	# 本波可分配给僵尸的战力总额。
	var curr_wave_power_limit = calculate_wave_power_limit(wave, is_big_wave)
	# 按当前波次直接计算，不能依赖先前波次曾经更新过权重。
	_update_weights(wave)
	# 按本波权重和战力预算抽取的僵尸类型列表。
	var wave_spawn :Array[CharacterRegistry.ZombieType] = get_curr_wave_zombie_list(wave, is_big_wave, curr_wave_power_limit)

	return wave_spawn

## 计算每波的战力上限
func calculate_wave_power_limit(wave:int, is_big_wave: bool) -> int:
	## x从0开始
	## 计算战力上限 = y=int(x/3)+1
	@warning_ignore("integer_division")
	var base_power_limit:int = wave / 3 + 1
	## 如果是大波，战力上限是原战力上限的2.5倍
	if is_big_wave:
		return int(base_power_limit * 2.5) * zombie_multy

	return base_power_limit * zombie_multy

## 按零起始自然波次 [param wave] 更新权重及随机池；本函数独立维护自然出怪的成长规则。[br]
## 每次从注册表基础值计算，重复调用不会累加衰减，超过索引 25 后保持末档权重。
func _update_weights(wave: int) -> void:
	zombie_weights = CharacterRegistry.ZombieSpawnWeights.duplicate()
	# 前六波保持基础权重，之后最多衰减二十档，保留原自然出怪公式。
	var decay_steps: int = clampi(wave - 5, 0, 20)
	zombie_weights[CharacterRegistry.ZombieType.Z001Norm] -= decay_steps * 180
	zombie_weights[CharacterRegistry.ZombieType.Z003Cone] -= decay_steps * 150
	## 魔术师按「权重与路障一致」配平，所以跟着路障同步衰减，否则后期它会比路障更常出现。
	zombie_weights[CharacterRegistry.ZombieType.Z026Magician] -= decay_steps * 150
	# 只让这几类随进度衰减，其余随机池条目保持基础权重。
	for zombie_type: CharacterRegistry.ZombieType in [
		CharacterRegistry.ZombieType.Z001Norm,
		CharacterRegistry.ZombieType.Z003Cone,
		CharacterRegistry.ZombieType.Z026Magician,
	]:
		if zombie_type in zombie_manager.zombie_refresh_types:
			zombie_choose_random_pool.update_item_weight(zombie_type, zombie_weights[zombie_type], false)
	zombie_choose_random_pool.rebuild_alias_table()

## 获取当前波僵尸列表
func get_curr_wave_zombie_list(wave:int, is_big_wave: bool, curr_wave_power_limit:int) ->Array[CharacterRegistry.ZombieType]:
	## 当前波的僵尸列表
	var wave_spawn :Array[CharacterRegistry.ZombieType]= []
	## 目前总战力
	var total_power = 0
	## 当前空隙位置
	var curr_spare_slot = max_zombies_per_wave

	## 如果是大波，先刷新特殊僵尸
	if is_big_wave:
		## 第一个旗帜僵尸
		wave_spawn.append(CharacterRegistry.ZombieType.Z002Flag)
		total_power += CharacterRegistry.ZombieSpawnPower[CharacterRegistry.ZombieType.Z002Flag]
		curr_spare_slot -= 1

		# 第一次大波（第10波），刷新4个普通僵尸
		if wave == 9:
			for i in range(4):
				wave_spawn.append(CharacterRegistry.ZombieType.Z001Norm)
				total_power += CharacterRegistry.ZombieSpawnPower[CharacterRegistry.ZombieType.Z001Norm]
				curr_spare_slot -= 1
		# 之后的大波（第20波、30波...），刷新8个普通僵尸
		else:
			for i in range(8):
				wave_spawn.append(CharacterRegistry.ZombieType.Z001Norm)
				total_power += CharacterRegistry.ZombieSpawnPower[CharacterRegistry.ZombieType.Z001Norm]
				curr_spare_slot -= 1

	# 生成剩余僵尸，直到总战力符合当前战力上限
	while curr_spare_slot > 0 and total_power < curr_wave_power_limit:

		var selected_zombie:CharacterRegistry.ZombieType = zombie_choose_random_pool.get_random_item()
		# 本次抽中类型消耗的战力，统一读取角色注册表。
		var zombie_power_value: int = CharacterRegistry.ZombieSpawnPower[selected_zombie]

		#prints("当前剩余僵尸", curr_spare_slot, "当前战力:", total_power, "当前所选僵尸:", selected_zombie, "当前所选僵尸战力:", zombie_power_value)

		# 检查如果加上该僵尸的战力后超过当前波的战力上限，重新选择
		if total_power + zombie_power_value <= curr_wave_power_limit:
			wave_spawn.append(selected_zombie)
			total_power += zombie_power_value
			curr_spare_slot -= 1
		elif curr_wave_power_limit - total_power < min_power:
			for i in range(curr_wave_power_limit - total_power):
				wave_spawn.append(CharacterRegistry.ZombieType.Z001Norm)
				total_power += CharacterRegistry.ZombieSpawnPower[CharacterRegistry.ZombieType.Z001Norm]
				curr_spare_slot -= 1
			continue
		else:
			continue

	return wave_spawn

#endregion

#endregion

#region 大波僵尸时生成特殊僵尸
## 大波僵尸时创建特殊僵尸
## [is_final:bool] 是否为最后一波
func spawn_special_zombie_in_big_wave(is_final:=false):
	## 珊瑚僵尸,若有水路自动创建,没有则不创建
	if is_final:
		if not zombie_manager.is_ice:
			print("生成珊瑚僵尸")
			spawn_sea_weed_zombies()
		else:
			print("被冰冻无法生成珊瑚僵尸")
	## 如果有蹦极僵尸
	if zombie_manager.is_bungi:
		spawn_bungi_zombies()

#region 珊瑚僵尸
## 最后一大波珊瑚僵尸
func spawn_sea_weed_zombies():
	var zombie_row_pool_i :Array[int]
	for i in range(zombie_manager.all_zombie_rows.size()):
		if zombie_manager.all_zombie_rows[i].zombie_row_type == CharacterRegistry.ZombieRowType.Pool:
			zombie_row_pool_i.append(i)
	if zombie_row_pool_i.is_empty():
		print("无水路,无法生成珊瑚僵尸")
		return

	var zombie_type_sea_weed_list :Array= [CharacterRegistry.ZombieType.Z001Norm, CharacterRegistry.ZombieType.Z003Cone, CharacterRegistry.ZombieType.Z005Bucket]

	for i in range(3):
		var zombie_type:CharacterRegistry.ZombieType = zombie_type_sea_weed_list.pick_random()
		var lane:int= zombie_row_pool_i.pick_random()
		var zombie_sea_weed:Zombie000Base = wave_create_zombie(zombie_type, lane, -1, _zombie_seaweed)

		if is_instance_valid(zombie_sea_weed):
			zombie_sea_weed.global_position.x = randf_range(500, 750)

## 珊瑚僵尸
func _zombie_seaweed(z:Zombie001Norm):
	z.is_seaweed = true
#endregion

#region 蹦极僵尸
func spawn_bungi_zombies():
	## 选择plant_cell
	var num_bungi_rand:int = randi_range(range_num_bungi.x, range_num_bungi.y)
	var all_cell_have_plant:Array[PlantCell] = zombie_manager.main_game.plant_cell_manager.get_cell_have_plant()
	var num_bungi_res:int = min(num_bungi_rand, all_cell_have_plant.size())
	## 打乱顺序
	all_cell_have_plant.shuffle()
	## 蹦极僵尸选中的plant_cell
	var all_cell_be_bungi = all_cell_have_plant.slice(0, num_bungi_res)
	## 生成蹦极僵尸
	for plant_cell:PlantCell in all_cell_be_bungi:
		var zombie_init_para:Dictionary = {
			Zombie000Base.E_ZInitAttr.CharacterInitType:Character000Base.E_CharacterInitType.IsNorm,
			Zombie000Base.E_ZInitAttr.Lane:plant_cell.row_col.x
		}

		zombie_manager.create_norm_zombie(
			CharacterRegistry.ZombieType.Z021Bungi,
			zombie_manager.all_zombie_rows[plant_cell.row_col.x],
			zombie_init_para,
			Vector2(plant_cell.global_position.x + plant_cell.size.x/2,
				zombie_manager.all_zombie_rows[plant_cell.row_col.x].zombie_create_position.global_position.y
			),
			GlobalUtils.create_bungi.bind(plant_cell)
		)

#endregion

#endregion
