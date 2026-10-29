## 通关掉落表：打通某一关时**掉什么东西**。
##
## 原版一週目的掉落分三种，全部按「大关-小关」固定发放，与打得好不好无关：
## [br]· 第 1~3 关、第 5~8 关 → 一株植物（表在 [constant AdventurePlantUnlock.UNLOCK_BY_CLEARED_LEVEL]）
## [br]· 第 4 关 → 一件**道具**（铲子 / 图鉴 / 车钥匙 / 玉米卷 / 浇水壶）
## [br]· 第 9 关 → 一张**便签**「一大波僵尸即将来袭」
## [br]· 第 10 关 → 下一大关的关键植物（1-10 是小喷菇，属植物表）
##
## 本类只管**道具**这一支；植物那一支留在 [AdventurePlantUnlock] 里不动 ——
## 那张表同时是「卡池上限」的权威口径，挪出来会让两处判定分叉。
## [method get_reward] 是给演出用的合并入口，调用方不用自己分辨是哪一支。
##
## ⚠️ 道具**不进存档**。它们的效果全都能从通关记录推导：
## 铲子是关卡的 is_shovel 配置、图鉴/商店/花园是主菜单闸门（[AdventureProgress]）、
## 玉米卷是商店紫卡的前置。多存一份「已获得道具」只会和通关记录打架。
class_name AdventureReward
extends RefCounted

## 掉落物的种类。
enum Kind {
	Plant, ## 一株植物，演出时显示种子卡。
	Item,  ## 一件道具，演出时显示图标。
}

## ── 道具图标（全部 80~170px 见方的透明图，演出里等比放大到 150 高）──────
const TEX_SHOVEL: Texture2D = preload("res://assets/image/ui/ui_card/Shovel_hi_res.png")
const TEX_NOTE: Texture2D = preload("res://assets/image/zombie_note/ZombieNoteSmall.png")
const TEX_ALMANAC: Texture2D = preload("res://assets/image/ui/ui_start_menu/SelectorScreen_Almanac.png")
const TEX_CAR_KEYS: Texture2D = preload("res://assets/image/main_game_item/CarKeys.png")
const TEX_TACO: Texture2D = preload("res://assets/image/main_game_item/Taco.png")
const TEX_WATERING_CAN: Texture2D = preload("res://assets/image/garden/WateringCan.png")
const TEX_TROPHY: Texture2D = preload("res://assets/image/ui/ui_trophy/trophy_hi_res.png")

## ── 道具表：键 → 名字、说明、图标 ───────────────────────────────────────
## 说明文字口径：说清「这东西让你能干什么」，不写「恭喜获得」这类废话。
const ITEMS: Dictionary = {
	"shovel": {
		"名字": "铲子",
		"说明": "种错了位置就把它挖回来，一铲子下去不伤根系。",
		"贴图": TEX_SHOVEL,
	},
	"note": {
		"名字": "一张纸条",
		"说明": "「一大波僵尸即将来袭。」字迹潦草，只剩纸角那点笑意。",
		"贴图": TEX_NOTE,
	},
	"almanac": {
		"名字": "图鉴",
		"说明": "戴夫塞给你的小册子，翻开能查每株植物和每种僵尸的底细。",
		"贴图": TEX_ALMANAC,
	},
	"carkeys": {
		"名字": "车钥匙",
		"说明": "疯狂戴夫的车钥匙。他说从这一刻起，后车厢随你翻。",
		"贴图": TEX_CAR_KEYS,
	},
	"taco": {
		"名字": "玉米卷",
		"说明": "戴夫念叨了一整晚的玉米卷。卖掉能换一颗钻石，也是他给你开后门的凭证。",
		"贴图": TEX_TACO,
	},
	"wateringcan": {
		"名字": "浇水壶",
		"说明": "浇花用。禅境花园从这一刻起归你打理。",
		"贴图": TEX_WATERING_CAN,
	},
	"trophy": {
		"名字": "银向日葵奖杯",
		"说明": "一週目通关。家庭草坪保住了 —— 迷你游戏、解谜与生存模式全部开放。",
		"贴图": TEX_TROPHY,
	},
}

## ── 道具掉落表（**唯一的权威口径**，改掉落节点只动这张表）─────────────────
## 键 = 「1 起」的关卡序号（与大关-小关的换算是 (大关-1)*10 + 小关），值 = [constant ITEMS] 的键。
## [br]对照：1-4 → 4、1-9 → 9、2-4 → 14、2-9 → 19、3-4 → 24、3-9 → 29、
## [br]4-4 → 34、4-9 → 39、5-4 → 44、5-9 → 49、5-10 → 50。
## [br]表里没有的关卡不掉道具（那些关掉的是植物，走 AdventurePlantUnlock）。
const ITEM_BY_CLEARED_LEVEL: Dictionary = {
	4: "shovel",        # 1-4
	9: "note",          # 1-9
	14: "almanac",      # 2-4  → 图鉴
	19: "note",         # 2-9
	24: "carkeys",      # 3-4  → 开商店
	29: "note",         # 3-9
	34: "taco",         # 4-4  → 商店紫卡的前置
	39: "note",         # 4-9
	44: "wateringcan",  # 5-4  → 开禅境花园
	49: "note",         # 5-9
	50: "trophy",       # 5-10 → 一週目通关
}


## 合并入口：打通第 [param level_no] 关掉什么。
## [br]返回 `{}` 表示这一关不掉东西。否则返回以下两种之一：
## [br]· `{"kind": Kind.Plant, "plant_id": int}`
## [br]· `{"kind": Kind.Item, "key": String, "name": String, "desc": String, "texture": Texture2D}`
## [br]植物优先：植物表与道具表在数值上不重叠（第 4、9、10 关之外才有植物），
## 万一以后改表改重合了，也以「掉植物」为准，不会两边都弹一次。
static func get_reward(level_no: int) -> Dictionary:
	var plant_id: int = AdventurePlantUnlock.get_plant_unlocked_by_cleared_level(level_no)
	if plant_id > 0:
		return {"kind": Kind.Plant, "plant_id": plant_id}
	var key: String = String(ITEM_BY_CLEARED_LEVEL.get(level_no, ""))
	if key.is_empty():
		return {}
	var entry: Dictionary = ITEMS.get(key, {})
	if entry.is_empty():
		push_warning("通关掉落：道具表里没有 %s" % key)
		return {}
	return {
		"kind": Kind.Item,
		"key": key,
		"name": String(entry.get("名字", key)),
		"desc": String(entry.get("说明", "")),
		"texture": entry.get("贴图") as Texture2D,
	}


## 该道具是否已经在进度里发过了（用于「商店紫卡要不要玉米卷」这类前置判定）。
## [br]口径仍然是通关记录，不另存状态：通关数够了就等于拿到了。
static func has_item(key: String) -> bool:
	var progress: int = AdventurePlantUnlock.get_progress_count()
	for level_no: int in ITEM_BY_CLEARED_LEVEL:
		if String(ITEM_BY_CLEARED_LEVEL[level_no]) == key and level_no <= progress:
			return true
	return false
