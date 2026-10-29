## 「当前存档是否享受全权限」的唯一判定。
##
## 用户 2026-10-29 明确：**Wow 那个存档是开发档，一切放开；新建的存档才走原版解锁流程。**
## 所以闸门不能只看「关卡通关数」，必须先问一句「这个存档要不要闸门」。
##
## 判定条件有两条，命中任意一条即全权限：
## [br]1. 控制台的「开放所有关卡」（[member ConfigService.open_all_level]）—— 临时调试用；
## [br]2. 存档名在 [constant DEV_USER_NAMES] 里 —— 开发档。
##
## 为什么存档名要写死在代码里，而不是只靠 config 里的开关：
## 配置文件是会丢的（换机、重装、删 user 目录），丢了之后开发档会突然被闸门锁住，
## 而「这个存档是开发档」这件事不该跟着配置文件一起丢。
##
## 单独成一个类而不是塞进 [AdventureProgress]，是为了打破循环依赖：
## [AdventurePlantUnlock] 也要问这个问题（它决定卡池要不要收窄），
## 而 [AdventureProgress] 反过来又依赖 [AdventurePlantUnlock]。
class_name DevAccess
extends RefCounted

## 开发档的用户名。**不区分大小写**，避免手输存档名时的大小写差异。
const DEV_USER_NAMES: PackedStringArray = ["Wow"]


## 当前存档是否享受全权限（不设关卡锁、不收窄卡池、主菜单全亮）。
static func is_dev_save() -> bool:
	if Global.config_service != null and Global.config_service.open_all_level:
		return true
	return is_dev_user_name(_current_user_name())


## 指定用户名是否属于开发档。
static func is_dev_user_name(user_name: String) -> bool:
	if user_name.is_empty():
		return false
	for dev_name: String in DEV_USER_NAMES:
		if dev_name.to_lower() == user_name.to_lower():
			return true
	return false


## 当前登录的用户名；未选用户时返回空串。
static func _current_user_name() -> String:
	if Global.user_manager == null:
		return ""
	return String(Global.user_manager.curr_user_name)
