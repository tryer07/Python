extends Node
class_name MainSceneRegistry


## 加载场景
enum MainScenes{
	MainGameFront,
	MainGameBack,
	MainGameRoof,

	StartMenu = 100,
	ChooseLevelAdventure,
	ChooseLevelMiniGame,
	ChooseLevelPuzzle,
	ChooseLevelSurvival,
	ChooseLevelCustom,
	## 原版 50 关冒险模式选关界面。
	## 独立编号是必要的：存档 key 由 game_mode + 页号 + 关卡号组成，
	## 若与 ChooseLevelAdventure 共用 101，两套关卡的前若干关会共享同一份通关记录。
	ChooseLevelAdventure50,

	Garden = 200,
	Almanac,
	Store,

	Null = 999,
}
@export var MainScenesMap = {
	MainScenes.MainGameFront: "res://scenes/main/MainGame01Front.tscn",
	MainScenes.MainGameBack: "res://scenes/main/MainGame02Back.tscn",
	MainScenes.MainGameRoof: "res://scenes/main/MainGame03Roof.tscn",

	MainScenes.StartMenu: "res://scenes/main/01StartMenu.tscn",
	MainScenes.ChooseLevelAdventure: "res://scenes/main/02AdventureChooesLevel.tscn",
	MainScenes.ChooseLevelMiniGame: "res://scenes/main/03MiniGameChooesLevel.tscn",
	MainScenes.ChooseLevelPuzzle: "res://scenes/main/04PuzzleChooesLevel.tscn",
	MainScenes.ChooseLevelSurvival: "res://scenes/main/05SurvivalChooesLevel.tscn",
	MainScenes.ChooseLevelCustom: "res://scenes/main/06CustomChooesLevel.tscn",
	MainScenes.ChooseLevelAdventure50: "res://scenes/main/02AdventureChooesLevel50.tscn",

	MainScenes.Garden: "res://scenes/main/10Garden.tscn",
	MainScenes.Almanac: "res://scenes/main/11Almanac.tscn",
	MainScenes.Store: "res://scenes/main/12Store.tscn",
}

## 场景僵尸的行类型
@export var ZombieRowTypewithMainScenesMap:Dictionary[MainScenes, CharacterRegistry.ZombieRowType] = {
	MainScenes.MainGameFront:CharacterRegistry.ZombieRowType.Land,
	MainScenes.MainGameBack:CharacterRegistry.ZombieRowType.Both,
	MainScenes.MainGameRoof:CharacterRegistry.ZombieRowType.Land,
}
