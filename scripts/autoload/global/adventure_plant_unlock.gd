## 冒险模式（50 关版）的植物解锁进度。
##
## 正式规则照原版：开局只有豌豆射手（P001），**每通一关**按编号顺序解锁下一个。
## 编号 1~48 恰好等于原版解锁顺序，因此不需要额外的映射表。
##
## 另外有一条**仅供跳关测试**的放宽规则（[member debug_unlock_by_highest_level]）：
## 原版按「通关数量」数，跳过 1-1、1-2 直接通 1-3 也只算 1 关，于是「关卡放开了、植物跟不上」，
## 进 1-4 时选卡里没有镇山老翁。打开该开关后改成按「已通最高关卡序号」算 ——
## 线性推进时两种算法完全等价（通 N 关 ⇒ 最高关就是第 N 关），只有跳关 / 漏关时才会多给几株。
## **默认关闭**，由 [ChooseLevelAdventure50] 按它的 `debug_unlock_pages` 决定是否打开，
## 所以把关卡解锁调回逐关推进时，植物也自动回到原版线性规则。
##
## 这里只统计「50 关版冒险模式」的进度，不影响其它模式；
## 进入其它模式时调用 [method restore_full] 把植物列表还原成引擎默认全量。
class_name AdventurePlantUnlock
extends RefCounted

## 50 关版冒险模式的 MainScenes 编号，用于拼存档键。
const ADVENTURE_50_MODE: int = MainSceneRegistry.MainScenes.ChooseLevelAdventure50
## 每页关卡数，必须与 choose_level_50.gd 的 LEVELS_PER_PAGE 保持一致。
const LEVELS_PER_PAGE: int = 10
## 冒险模式最多解锁到 P048（玉米加农炮），之后的编号属于商店/小游戏专用。
const MAX_ADVENTURE_PLANT: int = 48

## 首次调用时记下引擎默认的完整植物列表，用于切换回其它模式时还原。
static var _full_plant_snapshot: Array[CharacterRegistry.PlantType] = []

## 调试开关：true = 按「已通最高关序号」解锁（跳关测试用），false = 按「通关数量」（原版规则）。
## [br]默认 false。只由 [ChooseLevelAdventure50] 在进入选关界面时按 `debug_unlock_pages` 设置，
## 不写进存档、不影响任何存档数据。
static var debug_unlock_by_highest_level: bool = false

## 调试开关：把关卡放开的范围直接当作「已通关的关卡数」参与解锁计算。
## [br]0 = 关闭，完全按上面两条规则算进度。
## [br]它解决的是上面两条规则都覆盖不到的第三种情况：**玩家跳关直达第 N 关，但那一关之前的关卡
## 一关都没打过**。此时「通关数量」是 0、「已通最高关序号」也是 0，而关卡却因为调试开关被放开了，
## 于是关卡进得去、选卡里连豌豆射手之外的植物都看不到。既然关卡是调试放开的，
## 就按放开的范围算进度，两者才对得齐。
## [br]**传入的是「能打到第几关」，不是「已经通到第几关」** —— 玩家把第 N 关打穿了，
## 进度才是 N。所以内部按 N - 1 计，与「通 N 关 ⇒ 解锁第 N + 1 株」的原版规则对齐：
## 放开到 1-8 → 进度 7 → 共 7 株（豆蔻 … 大嘴花），第 8 株双发射手仍然上锁。
## [br]只由 [ChooseLevelAdventure50] 在 `debug_unlock_level > 0` 时设为同样的值，
## 不写进存档；设回 0 即完全回到原版规则。
static var debug_unlock_through_level: int = 0


## 返回冒险模式的存档键，必须与 ChooseLevel 里 set_choose_level 的拼接方式一致。
static func level_save_name(index: int) -> String:
	var page: int = index / LEVELS_PER_PAGE
	var level_id: String = "%04d" % (index + 1)
	return "%d_%d_%s" % [ADVENTURE_50_MODE, page, level_id]


## 统计 50 关版冒险模式已经通关的关卡数量。
## [br]只用于日志与统计，**不参与解锁计算** —— 跳关时它会比最高关序号小，
## 解锁走 [method get_highest_cleared_level_no]。
static func get_cleared_count() -> int:
	var cleared: int = 0
	for index: int in range(AdventureLevelPaths.PATHS.size()):
		var state: Dictionary = Global.global_game_state.curr_all_level_state_data.get(
			level_save_name(index), {}
		)
		if state.get("IsSuccess", false):
			cleared += 1
	return cleared


## 返回「冒险模式当前的有效通关进度」，即已经打穿了多少关。
## [br]**这是全项目所有解锁判定的唯一进度口径**：植物解锁（[method get_unlocked_plant_ids]）
## 和功能解锁（[AdventureProgress]）都走这里，两边不会算出不同的数。
## [br]正常线性推进时它就等于 [method get_cleared_count]；两个调试开关打开时按各自的放宽规则算。
static func get_progress_count() -> int:
	var cleared: int = get_highest_cleared_level_no() if debug_unlock_by_highest_level else get_cleared_count()
	return maxi(cleared, maxi(debug_unlock_through_level - 1, 0))


## 从存档键取出「1 起」的关卡序号，用于反查这一关打完发什么。
## [br]存档键形如 `106_0_0003`（模式_页_四位序号），取末四位即可；
## [br]键格式不对（长度不足）时返回 0，调用方按「不是冒险关卡」处理。
static func level_no_from_save_name(save_name: String) -> int:
	if save_name.length() < 4:
		return 0
	return save_name.substr(save_name.length() - 4).to_int()


## 打通第 [param level_no] 关会发哪一株植物；这一关不发植物时返回 0。
## [br]返回 0 的三种情况：1-4（发铲子）、1-9（发「一大波僵尸」便签）、
## 以及解锁表只写到 1-10、往后的关卡还没登记。掉落演出靠它判断「要不要弹卡」。
static func get_plant_unlocked_by_cleared_level(level_no: int) -> int:
	return int(UNLOCK_BY_CLEARED_LEVEL.get(level_no, 0))


## 返回已通关关卡里最大的「1 起关卡序号」；一关都没通关时返回 0。
## [br]例：只通了 1-3（哪怕 1-1、1-2 没记录）→ 返回 3。
static func get_highest_cleared_level_no() -> int:
	var highest: int = 0
	for index: int in range(AdventureLevelPaths.PATHS.size()):
		var state: Dictionary = Global.global_game_state.curr_all_level_state_data.get(
			level_save_name(index), {}
		)
		if state.get("IsSuccess", false):
			highest = maxi(highest, index + 1)
	return highest


## ── 冒险模式的解锁表（**唯一的权威口径**，改解锁顺序只动这张表）────────────
## [br]键是「已经打穿的关卡数」，值是那一关打完解锁的东西的植物编号。
## [br]植物编号本身就是解锁顺序号，所以这张表等价于「1~N 顺序解锁」，
## 之所以还要写出来，是因为中间有两关给的根本不是植物：
## [br]· 1-4 打完给**铲子**（`is_shovel`），不占植物位；
## [br]· 1-9 打完给**「一大波僵尸即将来袭」便签**，也不占植物位。
## [br]于是「关卡数」与「植物数」不是 N + 1 的关系 —— 打到 1-8 时卡池上限是
## 豆蔻 / 朝阳童子 / 并蒂樱童 / 镇山老翁 / 裴无咎 / 寒冰射手 / 醉仙客，共 7 株；
## 第 8 株双发射手要等 1-8 打完、进 1-9 才给。
## [br]对照表（用户 2026-10-25 亲自确认）：
## [br]1-1 默认豆蔻      → 打完解锁 朝阳童子
## [br]1-2 打完          → 并蒂樱童
## [br]1-3 打完          → 镇山老翁（坚果）
## [br]1-4 打完          → 铲子（非植物）
## [br]1-5 打完          → 裴无咎（土豆地雷）
## [br]1-6 打完          → 寒冰射手
## [br]1-7 打完          → 醉仙客（大嘴花）
## [br]1-8 打完          → 双发射手
## [br]1-9 打完          → 便签「一大波僵尸即将来袭」（非植物）
const UNLOCK_BY_CLEARED_LEVEL: Dictionary = {
	1: 2,   # 1-1 → 朝阳童子
	2: 3,   # 1-2 → 并蒂樱童
	3: 4,   # 1-3 → 镇山老翁
	# 4 是铲子，跳过
	5: 5,   # 1-5 → 裴无咎
	6: 6,   # 1-6 → 寒冰射手
	7: 7,   # 1-7 → 醉仙客
	8: 8,   # 1-8 → 双发射手
	# 9 是「一大波僵尸即将来袭」便签，跳过
	10: 9,  # 1-10 → 小喷菇
}


## 返回「已打通 [param cleared] 关」时应当可用的植物编号。
## [br]从豆蔻（P001）起算，每打通一关按 [constant UNLOCK_BY_CLEARED_LEVEL] 加一株；
## 表里没有的关卡（铲子关、便签关）不产植物，卡池原地不动。
## [br]表走完之后维持最后一株，不越界。
## [br]例：放开到 1-8 且此前一关未通 → 进度 8 - 1 = 7 → 卡池上限 7，
## 正好是豆蔻 / 朝阳童子 / 并蒂樱童 / 镇山老翁 / 裴无咎 / 寒冰射手 / 醉仙客；
## 第 8 株双发射手要等 1-8 打完（进度 8）才给。
static func get_unlocked_plant_ids() -> Array[int]:
	## 先把进度换算成「已打通的关卡数」：
	## [br]· 调试放开到第 N 关（[member debug_unlock_through_level]）：玩家此刻站在第 N 关，
	##   能打通的只有它前面那 N - 1 关 —— 所以进度是 N - 1，不是 N；
	## [br]· 整页放开 / 正式模式：分别按「已通最高关序号」与「已通关数量」。
	## [br]两者取大，避免存档里的通关记录被调试开关「撤销」掉。
	var cleared: int = get_progress_count()

	# 卡池上限：豆蔻 + 已通关卡里发过的植物数
	var top: int = 1
	for level_no: int in UNLOCK_BY_CLEARED_LEVEL:
		if level_no <= cleared:
			top = maxi(top, int(UNLOCK_BY_CLEARED_LEVEL[level_no]))
	top = clampi(top, 1, MAX_ADVENTURE_PLANT)

	var result: Array[int] = []
	for plant_id: int in range(1, top + 1):
		result.append(plant_id)
	return result


## 按冒险进度收窄 [member Global.global_game_state.curr_plant]。
## 开发档（见 [DevAccess]，「开放所有关卡」也走这条）不收窄，直接还原全量 ——
## 用户 2026-10-29 明确：Wow 存档全权限，只有新建存档才需要按进度给卡。
## [param extra_plant_ids] 额外强制保留的植物编号，用于「本关预选卡里出现的植物」这类硬需求 ——
## 预选关（1-1~1-3、1-5）不走选卡界面，卡槽里的植物一旦不在可用池里就种不下去。
static func apply_to_game_state(extra_plant_ids: Array[int] = []) -> void:
	if DevAccess.is_dev_save():
		restore_full()
		return
	_capture_full_snapshot()
	# 冒险植物之外的专用内容（模仿者、小游戏专用植物）始终保留，避免其它玩法被误伤
	var allowed: Array[CharacterRegistry.PlantType] = []
	for plant_id: int in get_unlocked_plant_ids():
		# 植物枚举底层就是 int，直接追加即可写入强类型数组
		allowed.append(plant_id)
	# 本关预选卡需要的植物必须带上，否则跳关时卡槽有卡、场面种不下去
	for extra_id: int in extra_plant_ids:
		if not allowed.has(extra_id):
			allowed.append(extra_id)
	for preserved: CharacterRegistry.PlantType in _extra_plants():
		if not allowed.has(preserved):
			allowed.append(preserved)
	Global.global_game_state.curr_plant = allowed


## 还原成引擎默认的完整植物列表，供非冒险模式使用。
static func restore_full() -> void:
	_capture_full_snapshot()
	if _full_plant_snapshot.is_empty():
		return
	Global.global_game_state.curr_plant = _full_plant_snapshot.duplicate()


## 冒险植物列表之外仍需保留的编号：模仿者与小游戏专用植物。
static func _extra_plants() -> Array[CharacterRegistry.PlantType]:
	return [
		CharacterRegistry.PlantType.P049PeaShooterDoubleReverse,
		CharacterRegistry.PlantType.P999Imitater,
		CharacterRegistry.PlantType.P1000Sprout,
		CharacterRegistry.PlantType.P1001WallNutBowling,
		CharacterRegistry.PlantType.P1002WallNutBowlingBomb,
		CharacterRegistry.PlantType.P1003WallNutBowlingBig,
	]


## 第一次调用时把当前植物列表存成快照；必须在任何收窄之前调用。
static func _capture_full_snapshot() -> void:
	if not _full_plant_snapshot.is_empty():
		return
	if Global.global_game_state == null:
		return
	_full_plant_snapshot = Global.global_game_state.curr_plant.duplicate()
