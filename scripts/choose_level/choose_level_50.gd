extends ChooseLevel
class_name ChooseLevelAdventure50

## 冒险模式 50 关选关界面。
## [br]关卡按钮不再于场景中手工摆放，而是按 [AdventureLevelPaths.PATHS] 的顺序动态生成，
## 每页 [constant LEVELS_PER_PAGE] 关、对应原版的一个大关，共 5 页。
## [br]逐关解锁不在本类重复实现：父类 [method ChooseLevel.update_lock_level] 已按
## [member ChooseLevel.open_level_num] 的剩余名额决定锁定，且已通关的关卡不占名额，
## 这里只要把 50 个按钮按顺序交给父类遍历即可。

## 关卡按钮预制体，直接复用现有按钮，保持外观与其他模式一致
const BUTTON_SCENE: PackedScene = preload("res://scenes/choose_level/choose_level_button.tscn")
## 每页关卡数，与原版「一个大关 10 小关」对齐
const LEVELS_PER_PAGE: int = 10
## 网格列数；2 行 x 5 列刚好容纳 10 关且不超出现有界面宽度
const GRID_COLUMNS: int = 5

## ── 调试：整页解锁（**已停用，保持 0**）────────────────────────────────
## 0 = 关闭，按原版逐关推进；N = 第 1~N 页的关卡全部可点（3 → 开放到 3-10，共 30 关）。
## [br]⚠️ **千万不要再设成 3**：N > 0 时它会把植物解锁切到「按已通最高关序号」，
## 而关卡又放开了 30 关 —— 两下一叠加，卡池会从应有的 7 株涨到 14 株，
## 1-8 的选卡里提前冒出双发射手、小喷菇这些还没到日子的植物。
## 精确到关请用下面的 [member debug_unlock_level]，两者不要同时开。
@export var debug_unlock_pages: int = 0

## ── 调试：精确解锁到第几关 ────────────────────────────────────────────
## 0 = 不启用，回到原版逐关推进；N = 第 1 关到第 N 关可点，第 N+1 关起照旧上锁。
## [br]按 50 关的一维序号计：8 就是 1-8。
## [br]关卡解锁与植物解锁**同时**收口到这一关，避免「关卡进得去、卡池里没有那株」。
## [br]具体做法是把 N 交给 [member AdventurePlantUnlock.debug_unlock_through_level]，
## 让放开的关卡范围直接等同于「已通关的关数」——
## 否则从 1-8 直接跳关、前面 7 关一关没打过时，进度是 0，选卡里连第 2 株都拿不到。
## [br]放开到 8 → 进度按 7 关算 → 卡池正好 7 株，与解锁表逐条对齐：
## 豆蔻 / 朝阳童子 / 并蒂樱童 / 镇山老翁 / 裴无咎 / 寒冰射手 / 醉仙客。
## （原表里 1-4 给的是铲子、1-9 给的是「一大波僵尸」提示，都不是植物，
## 所以「关卡数」与「植物数」不是简单加一，放开到第 8 关时就是 7 株。）
## [br]第 8 株双发射手要等 1-8 打完、进 1-9 才给，不会提前漏出来。
## [br]⚠️ 2026-10-29 归零：跳关调试做完、正式存档要按原版逐关推进，这个开关必须保持 0。
## 要从中间某关开始测，临时改成 8 即可，测完记得改回来。
@export var debug_unlock_level: int = 0

#region 关卡缩略图
## 预览框在按钮内的位置与尺寸，照搬原版选关按钮：按钮 104x115，预览框压在圆窗上半部。
## 圆窗贴图（Challenge_Window）中央是透明的，预览框放在它下面就能从窗口里透出来。
const PREVIEW_POS := Vector2(3.0, 2.0)
const PREVIEW_SIZE := Vector2(95.0, 72.0)
## 缩略图里主角脚下留的空隙，别让它贴死在预览框底边
const PREVIEW_BOTTOM_GAP := 6.0
## 豆蔻待机立绘
const DOUKU_TEXTURE: Texture2D = preload("res://assets/image/character/douku/douku_idle_03.png")
## 朝阳童子待机立绘（与游戏内同一张烘焙图，保证封面和实战长得一样）
const SUNFLOWER_TEXTURE: Texture2D = preload("res://assets/image/character/sunflower/sunflower_idle_01.png")
## 并蒂樱童待机立绘（同上，与战场／图鉴共用一张整图）
const CHERRY_TEXTURE: Texture2D = preload("res://assets/image/character/cherry/cherry_idle_01.png")
## 镇山老翁态1立绘（同上；取完好态，破损/濒死只在战场挨打后出现）
const WALLNUT_TEXTURE: Texture2D = preload("res://assets/image/character/wallnut/wallnut_state1.png")
## 埋锋将军蹲伏立绘（与战场／图鉴共用一张整图）
const POTATO_MINE_TEXTURE: Texture2D = preload(
	"res://assets/image/character/potato_mine/potato_mine_crouch.png")
## 醉仙客待机立绘（定稿 v3 侧持青玉葫芦，与战场／图鉴共用一张整图）
const CHOMPER_TEXTURE: Texture2D = preload(
	"res://assets/image/character/chomper/zuixianke_idle.png")
## 雪清仙子待机立绘（寒冰射手换皮，无球版，与战场／卡面／图鉴共用一张整图）
const SNOW_PEA_TEXTURE: Texture2D = preload(
	"res://assets/image/character/snow_pea/xueqing_idle.png")
## 阿双待机立绘（双发射手换皮，竹铳双持，与战场／卡面／图鉴共用一张整图）
const PEA_DOUBLE_TEXTURE: Texture2D = preload(
	"res://assets/image/character/adouble/adouble_idle_03.png")
## 铲子图标。**不是**卡片图 Shovel.png 原文件：那张是 80x80 的画布，实体只占 59x63，
## 上下各留 9~11px 透明边，缩略图按画布高度等比缩放会既显小又悬空约 5px。
## Shovel_preview.png 是把实体框裁出来再各留 2px 的预览专用版，落点与立绘对齐。
const SHOVEL_TEXTURE: Texture2D = preload("res://assets/image/ui/ui_card/Shovel_preview.png")
## 缩略图主角：关卡序号（0 起）→ 立绘。
## [br]**口径（用户 2026-10-27 明确）：封面 = 这一关第一次能用的新植物。**
## [br]解锁是「打完第 N 关才发第 N+1 株」，所以植物的登场关永远比解锁它的关**晚一关**：
## [br]· 1-1 豆蔻（初始就有）　· 1-2 朝阳童子（清完 1-1）
## [br]· 1-3 并蒂樱童（清完 1-2）　· 1-4 镇山老翁（清完 1-3）
## [br]· 1-5 铲子（1-4 起关卡带铲子，这一关没有新植物）
## [br]· 1-6 裴无咎　· 1-7 雪清仙子（清完 1-6 才发寒冰射手）
## [br]· 1-8 醉仙客（清完 1-7 才发大嘴花）
## [br]· 1-9 双发射手（清完 1-8 才发）—— **待补，见下面 index 8 的说明**
## [br]⚠️ 别再按「清完第 N 关解锁第 N 株」去推封面，那会把每一关都往前错一位。
## [br]表里没有的关卡暂不给缩略图，等逐关调好了再往这里加。
const PREVIEW_ART: Dictionary = {
	0: DOUKU_TEXTURE,
	1: SUNFLOWER_TEXTURE,
	2: CHERRY_TEXTURE,
	3: WALLNUT_TEXTURE,
	4: SHOVEL_TEXTURE,
	# 1-6：土豆地雷进默认卡池的第一关（1-5 解锁的是铲子，缩略图仍给铲子）
	5: POTATO_MINE_TEXTURE,
	# 1-7：雪清仙子（寒冰射手换皮）进卡池的第一关。
	# [br]⚠️ 2026-10-27 修正：这里原本放的是醉仙客，依据是注释里「通 6 关解锁第 7 株」，
	# 但 [constant AdventurePlantUnlock.UNLOCK_BY_CLEARED_LEVEL] 的实际口径是
	# 「打通第 N 关 → 发第 N 株」：1-6 打完给 P006 寒冰射手，1-7 打完才给 P007 醉仙客。
	# 也就是说 1-7 这一关**根本拿不到醉仙客**，封面放他会读成「这关给剑仙」。
	# 现在按真实解锁表归位：1-7 给雪清仙子，1-8 给醉仙客。
	6: SNOW_PEA_TEXTURE,
	# 1-8：醉仙客（大嘴花换皮）进卡池的第一关。
	7: CHOMPER_TEXTURE,
	# 1-9：阿双（双发射手换皮）进卡池的第一关（清完 1-8 才发）。
	# [br]2026-10-29 补齐：原先这里是空的，注释里记着「做双发射手那一轮记得同时补三处」，
	# 三处（本表、下面的 PREVIEW_ART_HEIGHT、all_cards.gd 的 CARD_ART）此前只补了最后一处。
	8: PEA_DOUBLE_TEXTURE,
}
## 对应的显示高度；三种立绘原始比例不同，高度要分开给，不能共用一个数。
## 朝阳童子是盘腿坐姿，同样高度下视觉上比站姿的豆蔻显小，所以给 52 补回来。
## 并蒂樱童是两人并立、贴图比单人的宽，按战场口径折算成 52，
## 再低就读不出「是两个人」，再高就会顶到预览框上沿（框内可用高度只有 66）——
## 战场已放大到 116，但缩略图**不能**跟着同比放大，52 是预览框的上限。
## 镇山老翁按豆蔻的口径（46 / 战场 76）折算：82 × 0.605 ≈ 50。
## 铲子给 46：裁边后的画布 63x67、实体占 63/67，屏幕上实体约 43x40，
## 底边落在框底上方 7.4（另四株是 6.2~8.5），四株一铲的基线才对得齐。
const PREVIEW_ART_HEIGHT: Dictionary = {
	0: 46.0,
	1: 52.0,
	2: 52.0,
	3: 50.0,
	4: 46.0,
	# 蹲伏比站姿矮：按 82 的战场口径折算，以画布高 82 计实体约 75，与镇山老翁齐平
	5: 50.0,
	# 醉仙客是站姿全身，比豆蔻高一头；框内可用高度 66。
	# [br]⚠️ 2026-10-26 换 v3 侧持立绘：新图 124×224，人物实体只占 y18..205（上下各 7.1% 留白）。
	# 旧值 51 是按**满幅**的旧图定的，直接搬过来实体只有 51 × 188/224 ≈ 42.8，
	# 在和其他株并排的选关封面里会显得突然缩水。反推回同一实体高度：
	#   需要 高度 × 188/224 = 51 → 高度 ≈ 60.8，取 **60**。
	# 60 时贴图整体宽 60 × 124/224 ≈ 33.2（旧图是 51 × 228/400 ≈ 29），
	# 框宽够，葫芦甩在左边也不会顶框；发髻顶到 y≈13、脚底落在框底上方 6。
	7: 60.0,
	# 雪清仙子同样是站姿全身，但贴图是 264×398 的**窄画布**（宽高比 0.66，醉仙客是 0.55），
	# 上下透明留白只有 2%（y8..390 / 398）。要和其他株同一实体高度得按实体算：
	# 实体高 = 高度 × 383/398，取 **52** → 实体 ≈ 50，与镇山老翁(50)/醉仙客(51)齐平。
	# 这是全表最矮的一档不会错：再高到 58，实体 55.8 会明显高出邻框，
	# 而且 52 时整体宽仅 52 × 264/398 ≈ 34.5，飘带不顶框。
	6: 52.0,
	# 阿双（双发射手换皮）：站姿全身，贴图 133×206，实体占 y4..201（96.1%，上下各 4px 留白）。
	# [br]按实体高度齐平算，不用管画布高度：要 实体 ≈ 50 就取 高度 = 50 / 0.961 ≈ 52，
	# 与雪清仙子（52 / 96.2%）落在同一条线上；整体宽 52 × 133/206 ≈ 33.6，竹铳不顶框。
	8: 52.0,
}
## 缩略图底图：借用图鉴里的地面图，按关卡背景挑选
const GROUND_TEXTURES: Dictionary = {
	ConstLevelData.GameBg.FrontDay: preload("res://assets/image/Almanac/Almanac_GroundDay.jpg"),
	ConstLevelData.GameBg.FrontNight: preload("res://assets/image/Almanac/Almanac_GroundNight.jpg"),
	ConstLevelData.GameBg.Pool: preload("res://assets/image/Almanac/Almanac_GroundPool.jpg"),
	ConstLevelData.GameBg.Fog: preload("res://assets/image/Almanac/Almanac_GroundNightPool.jpg"),
	ConstLevelData.GameBg.Roof: preload("res://assets/image/Almanac/Almanac_GroundRoof.jpg"),
	ConstLevelData.GameBg.RoofNight: preload("res://assets/image/Almanac/Almanac_GroundRoof.jpg"),
}
#endregion

## 装载后的关卡资源，索引与 AdventureLevelPaths.PATHS 一致
var _level_resources: Array[ResourceLevelData] = []

## 页码标签，父类 [method ChooseLevel._update_page] 会把页码写进这里
@onready var page_label: Label = $LabelPage


func _ready() -> void:
	# 两条调试规则互斥，谁开用谁：
	# ① 精确到关（debug_unlock_level）→ 进度按「放开到第 N 关 = 已通 N-1 关」算；
	# ② 整页放开（debug_unlock_pages）→ 进度按「已通最高关序号」算。
	# ⚠️ 千万不能因为 ① 就把 ② 的开关也点亮：那会让存档里的通关记录一起混进来，
	# 卡池从 7 株涨到 14 株，还没到日子的双发射手、小喷菇提前出现在 1-8 的选卡里。
	var by_exact: bool = debug_unlock_level > 0
	var by_pages: bool = not by_exact and debug_unlock_pages > 0
	AdventurePlantUnlock.debug_unlock_by_highest_level = by_pages
	# 精确到关时，放开到第 N 关就等于「前面的 N-1 关都通了」。
	# 跳关直达 1-8、前面一关没打过时，「通关数量」和「已通最高关」都是 0，
	# 不给这条就永远拿不到醉仙客；给到 8 正好等价于「已通 7 关」，卡池 7 株。
	AdventurePlantUnlock.debug_unlock_through_level = debug_unlock_level if by_exact else 0
	# 进入选关前先按通关进度收窄可用植物，选卡界面才会只显示已解锁的植物
	AdventurePlantUnlock.apply_to_game_state()
	_load_all_levels()
	_rebuild_all_pages()
	# 下面的信号连接、存档状态刷新、锁定判定全部交给父类完成
	super()
	_wire_page_buttons()
	_update_page_label()
	_report_after_layout()
	_debug_autoplay_from_args()


## 临时调试入口：命令行追加 `-- autoplay1` 可直接进入第 1 关，用于无界面自检。
## [br]追加 `-- autoplay1 level 12` 可直接进入第 12 关（按 1-1、1-2 … 的顺序数），
## 用于逐关核对铺草坪行数、卡槽与出怪配置。
func _debug_autoplay_from_args() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.is_empty() or args[0] != "autoplay1":
		return
	if _level_resources.is_empty():
		return
	# 关卡序号从 1 开始，和选关界面上的「1-3」一致；越界时夹回合法范围
	var level_no: int = 1
	if args.size() >= 3 and args[1] == "level":
		level_no = clampi(args[2].to_int(), 1, _level_resources.size())
	elif args[1].is_valid_int():
		level_no = clampi(args[1].to_int(), 1, _level_resources.size())
	# 后面紧跟的自检子模式（如 `chomper` / `plant` / `sunflower`）要原样留给
	# main_game_manager 的 `_debug_auto_plant_from_args()`，不能被这里吞掉。
	# 做法：把 `autoplay1 8 chomper` 归一成 `autoplay1 chomper 8` 不现实（用户参数不可写），
	# 所以这里只记录「本关要顺带跑哪个自检」，由一个全局变量转交。
	var sub_mode: String = ""
	if args[1] == "level":
		if args.size() >= 4:
			sub_mode = args[3]
	elif args.size() >= 3:
		sub_mode = args[2]
	if sub_mode != "":
		Global.autoplay_sub_mode = sub_mode
		Global.autoplay_sub_args = args
	var level_index: int = level_no - 1
	var para: ResourceLevelData = _level_resources[level_index]
	para.set_choose_level(game_mode, level_index / LEVELS_PER_PAGE, "%04d" % level_no)
	Global.game_para = para
	# 调试跳关兜底：本关用到的植物必须在可用池里，否则会出现「卡槽有卡、场面种不下去」。
	# 正常游玩由通关进度保证，这里只是把本关真正要发的那几种植物先补进池子。
	var needed_plant_ids: Array[int] = []
	# 预选卡关（1-1~1-3）：卡牌直接从 prechosen_cards 铺开
	for reference: ResourceCardReference in para.prechosen_cards:
		if reference != null and reference.card_type == ResourceCardReference.CardType.Plant:
			needed_plant_ids.append(reference.content_id)
	# 传送带关（1-5 就是 card_mode = 2）：卡牌由 conveyor_weights 按权重随机发出
	for weight: ResourceCardWeight in para.conveyor_weights:
		if weight == null or weight.card_reference == null:
			continue
		if weight.card_reference.card_type == ResourceCardReference.CardType.Plant:
			needed_plant_ids.append(weight.card_reference.content_id)
	AdventurePlantUnlock.apply_to_game_state(needed_plant_ids)
	print("调试：直接进入 %d-%d，save_game_name=%s，草坪行=%s，预选卡=%d，可选卡=%s，初始阳光=%d"
		% [level_index / LEVELS_PER_PAGE + 1, level_index % LEVELS_PER_PAGE + 1,
		para.save_game_name, str(para.sod_rows), para.prechosen_cards.size(),
		str(para.can_choosed_card), para.start_sun])
	# 在 _ready 里立即切换场景会撞上「节点正在增删子节点」，必须延后一帧
	choose_level_start_game.call_deferred(para.game_sences)


## 覆盖父类按「剩余名额递减」的解锁规则，补一条「前 N 页整段可点」。
## [br]父类的 [member ChooseLevel.open_level_num] 只能表达「下一关可以打」这种线性进度：
## 每遇到一个未通关的关卡就消耗一个名额，用完即锁。要一次放开整段，只能在这层改写。
## [br]判断依据是按钮自己的存档键（`106_0_0003` 末四位即 1 起的关卡序号），
## 不依赖遍历顺序，也不消耗父类的名额 —— 所以第 N 页之后的关卡仍然从「下一关」开始算，
## 不会因为整页放开而把后面的进度也一起挤掉。
func update_lock_level(choose_level_button: ChooseLevelButton, curr_level_state_data: Dictionary) -> void:
	# 精确到关优先：只放开到 debug_unlock_level，后面的关卡照旧上锁
	if debug_unlock_level > 0:
		var exact_no: int = _level_no_of(choose_level_button)
		if exact_no > 0 and exact_no <= debug_unlock_level:
			return
		super(choose_level_button, curr_level_state_data)
		return
	if debug_unlock_pages > 0:
		var level_no: int = _level_no_of(choose_level_button)
		if level_no > 0 and level_no <= debug_unlock_pages * LEVELS_PER_PAGE:
			# 落在放开区间内：直接返回，按钮保持默认的可用状态（不加锁、不变灰）
			return
	super(choose_level_button, curr_level_state_data)


## 从存档键取出 1 起的关卡序号；取不到时返回 -1，交给父类按常规规则处理。
## [br]存档键形如 `106_0_0003`（模式_页_三位或四位序号），取末四位即可。
func _level_no_of(choose_level_button: ChooseLevelButton) -> int:
	var para: ResourceLevelData = choose_level_button.curr_level_data_game_para
	if para == null:
		return -1
	var save_name: String = para.save_game_name
	if save_name.length() < 4:
		return -1
	return save_name.substr(save_name.length() - 4).to_int()



## 按路径清单顺序载入全部关卡配置。
## 使用固化路径而非扫描目录，保证导出为 exe 后依然能正确定位资源。
func _load_all_levels() -> void:
	for path: String in AdventureLevelPaths.PATHS:
		# 关卡配置是轻量资源，一次性全部载入不会造成明显内存压力
		var res: ResourceLevelData = ResourceLoader.load(path) as ResourceLevelData
		if res == null:
			push_error("冒险模式关卡加载失败：%s" % path)
			continue
		_level_resources.append(res)


## 清空场景里残留的页面并按每页 10 关重建。
## AllPage 的直接子节点即「一页」，父类依赖这一层级来遍历关卡按钮，不能插入中间容器。
func _rebuild_all_pages() -> void:
	for child: Node in all_page.get_children():
		# 先移出树再释放：queue_free 是延迟的，留在树上会被父类遍历到旧节点
		all_page.remove_child(child)
		child.queue_free()

	# 每页一个网格容器，按关卡数量向上取整
	var total_pages: int = int(ceil(float(_level_resources.size()) / float(LEVELS_PER_PAGE)))
	for page_index: int in total_pages:
		var grid: GridContainer = _create_page_grid(page_index)
		all_page.add_child(grid)

		for slot: int in LEVELS_PER_PAGE:
			var level_index: int = page_index * LEVELS_PER_PAGE + slot
			if level_index >= _level_resources.size():
				break

			var level_button: ChooseLevelButton = BUTTON_SCENE.instantiate() as ChooseLevelButton
			if level_button == null:
				push_error("选关按钮实例化失败")
				continue
			# 必须先赋关卡数据再入树：按钮的 _ready 依赖它判断是否可用
			level_button.curr_level_data_game_para = _level_resources[level_index]
			_set_level_caption(level_button, level_index)
			_add_level_preview(level_button, level_index)
			grid.add_child(level_button)


## 创建一页的网格容器，左右居中、距顶固定。
## [param page_index] 页序号，仅用于节点命名。
func _create_page_grid(page_index: int) -> GridContainer:
	var grid: GridContainer = GridContainer.new()
	grid.name = "Page%d" % page_index
	grid.columns = GRID_COLUMNS
	# 按钮实测 104x115；5 列总宽 = 5 * 104 + 4 * 37 = 668，正好铺满 670 的页面宽度
	grid.add_theme_constant_override("h_separation", 37)
	grid.add_theme_constant_override("v_separation", 20)

	# 水平居中、顶部留出标题空间；offset 相对锚点计算
	grid.anchor_left = 0.5
	grid.anchor_right = 0.5
	grid.offset_left = -335.0
	grid.offset_right = 335.0
	grid.offset_top = 140.0
	grid.offset_bottom = 420.0
	return grid


## 在按钮上显示关卡编号，例如 1-1、3-7。
## [param level_button] 目标按钮；[param level_index] 全局关卡序号（0 起）。
func _set_level_caption(level_button: ChooseLevelButton, level_index: int) -> void:
	var stage: int = level_index / LEVELS_PER_PAGE + 1
	var sub_level: int = level_index % LEVELS_PER_PAGE + 1
	var caption: Label = level_button.get_node_or_null("TextureButton/Label") as Label
	if caption != null:
		caption.text = "%d-%d" % [stage, sub_level]


## 给关卡按钮补一张缩略图：关卡背景对应的地面图打底，本关主角站在上面。
## [br]主角按 [constant PREVIEW_ART] 里登记的关卡查，没登记的关卡直接跳过（只有按钮，没有缩略图）。
## [br]预览框的 z_index 保持默认 0，正好压在圆窗贴图（z_index 1）下面，从窗口的透明区域透出来；
## 锁定图标（z_index 10）和关卡编号（在 TextureButton 内）仍然盖在缩略图之上。
func _add_level_preview(level_button: ChooseLevelButton, level_index: int) -> void:
	var art_texture: Texture2D = PREVIEW_ART.get(level_index) as Texture2D
	if art_texture == null:
		return
	var game_bg: ConstLevelData.GameBg = _level_resources[level_index].game_BG

	# 预览框：用 Panel 承载，clip_children 只负责把子节点裁进这个小窗口，本身不画任何东西
	var frame := Panel.new()
	frame.name = "Preview"
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.add_theme_stylebox_override("panel", StyleBoxEmpty.new())
	level_button.add_child(frame)
	# 尺寸必须入树之后再设，否则会在进入场景树时被锚点重算覆盖
	frame.position = PREVIEW_POS
	frame.size = PREVIEW_SIZE
	frame.clip_children = CanvasItem.CLIP_CHILDREN_ONLY

	# 地面图铺满预览框；直接拉伸到窗口大小，不做等比溢出，避免压到按钮外面
	var ground := TextureRect.new()
	ground.name = "Ground"
	ground.texture = GROUND_TEXTURES.get(game_bg, GROUND_TEXTURES[ConstLevelData.GameBg.FrontDay])
	ground.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ground.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	ground.stretch_mode = TextureRect.STRETCH_SCALE
	frame.add_child(ground)
	ground.position = Vector2.ZERO
	ground.size = PREVIEW_SIZE

	# 主角站在地面上，脚底留一点空隙，别贴死在边框上
	var actor := TextureRect.new()
	actor.name = "Actor"
	actor.texture = art_texture
	actor.mouse_filter = Control.MOUSE_FILTER_IGNORE
	actor.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	actor.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	var actor_height: float = float(PREVIEW_ART_HEIGHT.get(level_index, 46.0))
	var texture_size: Vector2 = art_texture.get_size()
	var actor_width: float = actor_height * texture_size.x / maxf(texture_size.y, 1.0)
	frame.add_child(actor)
	actor.size = Vector2(actor_width, actor_height)
	actor.position = Vector2(
		(PREVIEW_SIZE.x - actor_width) * 0.5,
		PREVIEW_SIZE.y - actor_height - PREVIEW_BOTTOM_GAP
	)


## 连接上一页 / 下一页 / 返回按钮。
func _wire_page_buttons() -> void:
	var prev_button: Button = get_node_or_null("PrevButton") as Button
	var next_button: Button = get_node_or_null("NextButton") as Button
	var back_button: Button = get_node_or_null("BackButton") as Button

	if prev_button != null:
		prev_button.pressed.connect(func() -> void: _update_page(curr_page - 1))
	if next_button != null:
		next_button.pressed.connect(func() -> void: _update_page(curr_page + 1))
	if back_button != null:
		back_button.pressed.connect(back_start_menu)


## 等布局稳定后输出关卡、解锁与尺寸概况，便于在日志里确认进度与排版是否正确。
## 布局尺寸要等一帧才计算完成，因此这里延迟两帧再统计。
func _report_after_layout() -> void:
	# 先抓住 SceneTree 引用：切场景后本节点会离开树，再调用 get_tree() 会拿到 null
	var tree: SceneTree = get_tree()
	if tree == null:
		return
	await tree.process_frame
	await tree.process_frame
	# 等待期间可能已经切场景（调试入口会立刻进关），此时节点已离开树，直接放弃统计
	if not is_inside_tree():
		return

	var total: int = 0
	var locked: int = 0
	for page_node: Node in all_pages_array:
		for node: Node in page_node.get_children():
			if node is ChooseLevelButton:
				total += 1
				var lock_icon: CanvasItem = node.get_node_or_null("Lock") as CanvasItem
				if lock_icon != null and lock_icon.visible:
					locked += 1
	print("冒险模式50关：共 %d 关，%d 页，已解锁 %d 关，锁定 %d 关"
		% [total, all_pages_array.size(), total - locked, locked])

	# 打印当前可用的植物数量，用于确认解锁进度是否生效（第 1 关时只有豌豆射手）
	var unlocked_ids: Array[int] = AdventurePlantUnlock.get_unlocked_plant_ids()
	print("冒险模式50关：已通关 %d 关（最高通到第 %d 关，调试放开到第 %d 关），可用植物 %d 种，编号 %s"
		% [AdventurePlantUnlock.get_cleared_count(),
		AdventurePlantUnlock.get_highest_cleared_level_no(),
		AdventurePlantUnlock.debug_unlock_through_level,
		unlocked_ids.size(), str(unlocked_ids)])
	# 功能闸门（图鉴/商店/迷你游戏/解谜/生存/花园）是否按进度亮起，主菜单上看到的就是这一行
	print("主菜单闸门：", AdventureProgress.describe())
	# 首关存档键，用于核对解锁进度统计与引擎实际写入的键是否一致
	for page_node: Node in all_pages_array:
		for node: Node in page_node.get_children():
			if node is ChooseLevelButton:
				print("冒险模式50关：首关存档键 %s（统计用键 %s）"
					% [node.curr_level_data_game_para.save_game_name,
					AdventurePlantUnlock.level_save_name(0)])
				break
		break

	# 打印首个按钮与页容器的实际尺寸，用于校准网格间距
	if all_pages_array.is_empty():
		return
	var first_page: Control = all_pages_array[0] as Control
	if first_page == null:
		return
	for node: Node in first_page.get_children():
		var button_rect: Control = node as Control
		if button_rect != null:
			print("冒险模式50关：按钮 %s px，页容器 %s px"
				% [button_rect.size, first_page.size])
			# 缩略图矩形，确认预览框确实被收在按钮范围内
			var preview: Control = button_rect.get_node_or_null("Preview") as Control
			if preview != null:
				var ground: Control = preview.get_node_or_null("Ground") as Control
				print("冒险模式50关：缩略图 %s px，地面 %s px"
					% [preview.get_rect(), ground.get_rect() if ground != null else Rect2()])
			break


## 刷新页码文字。父类的 _update_page 已写页码，这里补充初始状态。
func _update_page_label() -> void:
	if page_label == null:
		return
	page_label.text = "第 %d / %d 关" % [curr_page + 1, maxi(1, all_pages_array.size())]


## 覆盖父类翻页实现，额外刷新页码文字与分页按钮可用状态。
## [param new_page] 目标页序号，越界时循环。
func _update_page(new_page: int) -> void:
	super(new_page)
	if page_label != null:
		page_label.text = "第 %d / %d 关" % [curr_page + 1, maxi(1, all_pages_array.size())]
	_refresh_page_buttons()


## 首页时禁用「上一页」、末页时禁用「下一页」，避免循环翻页造成困惑。
func _refresh_page_buttons() -> void:
	var prev_button: Button = get_node_or_null("PrevButton") as Button
	var next_button: Button = get_node_or_null("NextButton") as Button
	var last_index: int = maxi(0, all_pages_array.size() - 1)
	if prev_button != null:
		prev_button.disabled = curr_page <= 0
	if next_button != null:
		next_button.disabled = curr_page >= last_index
