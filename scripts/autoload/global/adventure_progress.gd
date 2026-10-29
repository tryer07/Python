## 冒险模式的**功能**解锁进度：图鉴 / 商店 / 迷你游戏 / 解谜模式 / 生存模式 / 禅境花园。
##
## 原版规则（植物大战僵尸 Wiki「冒险模式」一页，一週目）：
## [br]· 每个大关的第 4 关后给一件**道具**，道具才是开功能的钥匙：
## [br]　1-4 铲子 → 2-4 图鉴 → 3-4 疯狂戴夫的车钥匙（商店）→ 4-4 玉米卷 → 5-4 浇水壶（禅境花园）
## [br]· 3-2 打穿 → 迷你游戏开放（先只开前三关）
## [br]· 4-6 打穿 → 解谜模式开放（先只开前三关）
## [br]· 5-10 打穿（银向日葵奖杯）→ 生存模式 + 迷你游戏/解谜的剩余关卡全部开放
##
## 所以新存档进游戏时主菜单上**只有冒险模式能点**，图鉴、商店、花园、迷你游戏、解谜、生存
## 六个入口全是锁着的，靠一关一关打上去才亮 —— 这正是用户 2026-10-29 要的原版流程。
##
## 判定所用的「进度」直接取 [method AdventurePlantUnlock.get_progress_count]，
## **不再自己数一遍通关记录** —— 关卡解锁、植物解锁、功能解锁三处必须是同一个数，
## 否则会出现「关卡进去了、卡池有植物、但主菜单还锁着」这种对不上的状态。
##
## 自定义关卡（[MainSceneRegistry.MainScenes.ChooseLevelCustom]）原版没有，
## 是本改版的调试/自制入口，**不受这里的闸门控制，始终可点**。
class_name AdventureProgress
extends RefCounted

## 受冒险进度控制的功能。编号顺序无意义，只用于字典键。
enum Feature {
	MiniGame, ## 迷你游戏（原版 3-2 打穿后开放）
	Puzzle,   ## 解谜模式（原版 4-6）
	Survival, ## 生存模式（原版 5-10，即打穿一週目）
	Garden,   ## 禅境花园（原版 5-4 拿到浇水壶）
	Almanac,  ## 图鉴（原版 2-4）
	Store,    ## 疯狂戴夫的商店（原版 3-4 拿到车钥匙）
}

## ── 功能解锁表（**唯一的权威口径**，改解锁节点只动这张表）──────────────────
## 键 = 功能，值 = 「已经打穿多少关」才能用。
## [br]数值由「大关-小关」换算成 1 起的关卡序号，口径与 [AdventurePlantUnlock] 完全一致：
## [br]2-4 = 第 14 关、3-2 = 22、3-4 = 24、4-6 = 36、5-4 = 44、5-10 = 50。
## [br]⚠️ 别按「第几大关」直接填 2 / 3 / 4 / 5 —— 那是大关号，不是关卡数。
const UNLOCK_BY_CLEARED_LEVEL: Dictionary = {
	Feature.Almanac: 14,   # 2-4 打完 → 图鉴
	Feature.MiniGame: 22,  # 3-2 打完 → 迷你游戏（先开前三关）
	Feature.Store: 24,     # 3-4 打完 → 车钥匙 → 商店
	Feature.Puzzle: 36,    # 4-6 打完 → 解谜模式
	Feature.Garden: 44,    # 5-4 打完 → 浇水壶 → 禅境花园
	Feature.Survival: 50,  # 5-10 打完 → 生存模式
}

## 主菜单上显示的名字，用于锁定提示文案与日志。
const FEATURE_LABELS: Dictionary = {
	Feature.Almanac: "图鉴",
	Feature.MiniGame: "迷你游戏",
	Feature.Store: "商店",
	Feature.Puzzle: "解谜模式",
	Feature.Garden: "禅境花园",
	Feature.Survival: "生存模式",
}


## 返回该功能要求的「已通关卡数」；0 表示无条件开放。
static func get_required_cleared_level(feature: Feature) -> int:
	return int(UNLOCK_BY_CLEARED_LEVEL.get(feature, 0))


## 返回该功能在主菜单上显示的名字。
static func get_feature_label(feature: Feature) -> String:
	return String(FEATURE_LABELS.get(feature, "该功能"))


## 该功能当前是否已开放。
## [br]开发档（见 [DevAccess]）与「开放所有关卡」开关打开时全部放开 ——
## 这是用户 2026-10-29 明确的口径：**Wow 存档不设闸门，新建存档才走原版流程**。
static func is_unlocked(feature: Feature) -> bool:
	if DevAccess.is_dev_save():
		return true
	var need: int = get_required_cleared_level(feature)
	if need <= 0:
		return true
	return AdventurePlantUnlock.get_progress_count() >= need


## 把「已通关卡数」换成人看的「大关-小关」。
## [br]例：14 → "2-4"，22 → "3-2"；传 0 表示一关都还没通。
static func level_text_of_cleared_level(level_no: int) -> String:
	if level_no <= 0:
		return "冒险模式开局"
	var per_page: int = AdventurePlantUnlock.LEVELS_PER_PAGE
	var stage: int = (level_no - 1) / per_page + 1
	var sub_level: int = (level_no - 1) % per_page + 1
	return "%d-%d" % [stage, sub_level]


## 锁定状态下给玩家看的提示，例如「通关 2-4 后解锁」。
static func get_lock_hint(feature: Feature) -> String:
	return "通关 %s 后解锁" % level_text_of_cleared_level(get_required_cleared_level(feature))


## 一行概况，供选关界面与主菜单在日志里核对闸门是否按预期生效。
static func describe() -> String:
	var progress: int = AdventurePlantUnlock.get_progress_count()
	var parts: PackedStringArray = []
	for feature: Feature in UNLOCK_BY_CLEARED_LEVEL:
		var mark: String = "√" if is_unlocked(feature) else "×"
		parts.append("%s%s(需%s)" % [mark, get_feature_label(feature),
			level_text_of_cleared_level(get_required_cleared_level(feature))])
	return "冒险进度 %d 关｜%s" % [progress, " ".join(parts)]


#region 二级锁：解锁后先只开前几关
## 迷你游戏 / 解谜模式**刚解锁时**开放的前 N 关（原版两个模式都是先开 3 关）。
const SIDE_MODE_PREVIEW_LEVELS: int = 3

## 一週目总关卡数（5-10 的序号），与大关-小关换算同源。
const MAX_ADVENTURE_LEVEL: int = 50

## 一週目是否已经打穿（5-10）。
## [br]只按通关记录算，不看调试开关 —— 需要「已经全开」请用
## [method is_side_mode_fully_unlocked]。
static func is_week_cleared() -> bool:
	return AdventurePlantUnlock.get_progress_count() >= MAX_ADVENTURE_LEVEL

## 迷你游戏 / 解谜是否已经整块开放（不再受「先开 3 关」限制）。
## [br]原版是打完一週目（拿到银向日葵奖杯）才把剩下的关卡全放出来；
## 开发档视作已通关。
static func is_side_mode_fully_unlocked() -> bool:
	if DevAccess.is_dev_save():
		return true
	return is_week_cleared()


## 该侧支模式当前最多开放到第几关（1 起）。
## [br]返回 **0** = 不设上限、整块开放；返回 **-1** = 一关都不开（功能还没解锁）；
## [br]其余正数 = 只开前 N 关。调用方（[ChooseLevel]）拿它去锁「第 N+1 关及之后」的按钮。
static func get_side_mode_level_limit(feature: Feature) -> int:
	if not is_unlocked(feature):
		return -1
	if is_side_mode_fully_unlocked():
		return 0
	return SIDE_MODE_PREVIEW_LEVELS
#endregion

