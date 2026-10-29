## 卡牌源模板目录；统一按身份值注册，实例创建与静态缩略图复制都经过此入口。
extends Control
class_name AllCardsClass

## 编辑器中的源目录，顺序决定同类卡牌的展示顺序，目录名称不推导内容类别。
@onready var _source_directories: Array[GridContainer] = [
	%PlantCards, %PlantCards2, %ZombieCards, %ZombieCards2, %BossCards,
]
## 已注册源模板；键是类别和角色编号，不是 Resource 的对象身份。
var _templates: Dictionary[Vector2i, Card] = {}
## 按源目录顺序保存的引用，用于分类页和候选卡分页。
var _references: Array[ResourceCardReference] = []

## 横排角色图集的单帧尺寸，与 plant_007_chomper.gd 的 FRAME_W / FRAME_H 保持一致。
## [br]图集只在大嘴花上用，但尺寸放在这里是为了让卡面不依赖角色脚本（卡面加载时机更早）。
const CHOMPER_FRAME_W := 320
const CHOMPER_FRAME_H := 400


## 隐藏运行时目录，并建立唯一模板索引；未配置卡牌保留为空布局节点。
func _ready() -> void:
	hide()
	# 按编辑器中的目录顺序遍历卡牌来源容器。
	for directory: GridContainer in _source_directories:
		# 每个卡牌子节点独立声明身份，不从容器类型推导。
		for child: Node in directory.get_children():
			# 源目录中的实际卡牌；非卡牌布局节点不参与注册。
			var card := child as Card
			if card == null or card.card_reference == null:
				continue
			if not card.card_reference.is_valid() or card.card_reference.is_imitater:
				push_error("AllCards：非法源卡牌引用：%s" % card.get_path())
				continue
			# 基础模板的身份值键，禁止静默覆盖重复注册。
			var key := card.card_reference.get_template_key()
			if _templates.has(key):
				push_error("AllCards：重复卡牌身份：%s" % key)
				continue
			_templates[key] = card
			_references.append(card.card_reference)


## 返回 [param reference] 的源模板；非法或未注册引用返回 null，不回退其他类别。
func get_template(reference: ResourceCardReference) -> Card:
	if reference == null or not reference.is_valid():
		return null
	return _templates.get(reference.get_template_key())


## 创建独立卡牌；[param reference] 描述内容和修饰，[param context] 指定点击用途。
## 返回尚未加入场景树的实例；身份或战斗用途非法时返回 null。
func create_card(reference: ResourceCardReference, context: Card.CardContext = Card.CardContext.Catalog) -> Card:
	# 模板只读，运行时属性与身份引用由新实例独立持有。
	var template := get_template(reference)
	if template == null:
		push_error("AllCards：无法创建未注册卡牌")
		return null
	if (context == Card.CardContext.Battle or context == Card.CardContext.Selection) and not is_battle_card(reference):
		push_error("AllCards：此卡牌不支持选卡或出战用途")
		return null
	# 入树前完成身份与用途设置，让 _ready 使用正确角色参数。
	var card := template.duplicate() as Card
	card.card_reference = reference.copy_reference()
	card.card_context = context
	# 卡槽、选卡、图鉴网格都从这里拿实例，卡面美术统一在这一层替换
	_apply_custom_card_art(card.get_node_or_null("CardBg/CharacterStatic") as Node2D)
	return card


## 返回 [param reference] 的独立静态缩略图；不会实例化出战角色或启动战斗初始化。
func create_static_preview(reference: ResourceCardReference) -> Node2D:
	# 已注册模板持有美术制作完成的静态节点树。
	var template := get_template(reference)
	if template == null:
		push_error("AllCards：无法创建未注册卡牌的缩略图")
		return null
	# 仅复制静态图像容器，保留模板内部的位置和缩放。
	var preview := template.character_static.duplicate() as Node2D
	_apply_custom_card_art(preview)
	if reference.is_imitater:
		preview.material = Card.IMITATER.duplicate()
		# 动画等非图像节点不参与材质继承。
		for child: Node in preview.get_children():
			if child is Node2D:
				GlobalUtils.node_use_parent_material(child as Node2D)
	return preview


## 返回 [param card_type] 的有序引用列表；返回独立引用，调用方不能改写目录身份。
func get_references(card_type: int) -> Array[ResourceCardReference]:
	# 分类页的顺序来自源目录，不保存额外的卡牌位置编号。
	var result: Array[ResourceCardReference] = []
	# 当前基础引用只读使用，分类结果持有独立副本。
	for reference: ResourceCardReference in _references:
		if reference.card_type == card_type:
			result.append(reference.copy_reference())
	return result


## 返回 [param reference] 是否为已注册的可出战卡牌；模仿者选择入口只用于辅助选卡。
## 僵王具有普通卡槽出战能力，具体场景的召唤资格由僵尸管理器确认。
func is_battle_card(reference: ResourceCardReference) -> bool:
	if get_template(reference) == null:
		return false
	match reference.card_type:
		ResourceCardReference.CardType.Plant:
			return reference.content_id != CharacterRegistry.PlantType.P999Imitater
		ResourceCardReference.CardType.Zombie:
			return true
		ResourceCardReference.CardType.ZombieBoss:
			return true
	return false


#region 卡面整图替换
## 卡牌模板里的植物是「散件拼装 + Anim_idle / Anim_blink」死摆在场景里的，
## 不会跟随战场上的整图换装。所以复制出实例后，在卡面这一层统一换成同一张烘焙整图，
## 让「卡面 / 图鉴缩略图 / 战场」三处长得完全一样；源模板与战场场景都不受影响。
## [br]键 = 模板里的角色容器节点名（与植物类名一致）。
const CARD_ART: Dictionary = {
	"Plant001PeaShooterSingle": {
		"贴图": "res://assets/image/character/douku/douku_idle_03.png",
		# 与战场保持同一显示高度，卡片本身再统一乘 0.5
		"高度": 76.0,
		# 卡面下移量（卡牌局部坐标，实际显示要乘 0.5）。
		# 散件版原图只有 67 高，豆蔻 76 高，头部会顶到卡面上沿，所以整体压下来一点。
		"下移": 6.0,
	},
	"Plant002SunFlower": {
		"贴图": "res://assets/image/character/sunflower/sunflower_idle_01.png",
		# 战场显示 82（含上下描边留白，实心部分约 76），与豆蔻的视觉高度一致
		"高度": 82.0,
		"下移": 6.0,
	},
	"Plant003CherryBomb": {
		"贴图": "res://assets/image/character/cherry/cherry_idle_01.png",
		# ⚠️ 这里的高度**故意**不跟战场同步（战场已放到 116）。
		# 卡面是 50×70 的固定框（clip_children=2），下方 y≈55 起是费用数字；
		# 实测把高度从 84 提到 116 后，实体上沿会从 y≈6 顶到 y≈-9，两颗头直接被卡框切掉 9px。
		# 84 时实体占 6~45，正好塞满角色区；提到 92 也能塞下，但只多 4px 高度、辨识度没变化。
		# 卡面是「这是谁」的标签，不是尺寸参照 —— 保持和豆蔻(76)/朝阳童子(82)同一视觉量级。
		# 战场变大、图鉴详情页（实例化真实植物）自动跟着变大，这两处才是用户看尺寸的地方。
		# 贴图本身已经换成 215×230，缩到 84 高时比原来的 157×168 更锐利，缩略图顺带变清楚。
		"高度": 84.0,
		"下移": 6.0,
	},
	"Plant005PotatoMine": {
		# 埋锋将军取**蹲伏蓄势**那一档：卡面是「这是谁」的标签，刀在鞘、随时要起身的姿态
		# 最像土豆地雷；准备期的坐地养神只在战场开局那几秒出现，不适合当识别图。
		"贴图": "res://assets/image/character/potato_mine/potato_mine_crouch.png",
		# ⚠️ 裴的高度是本表里**唯一**和战场不一致的一档，原因见下，别照抄 82。
		# 卡面落位（card.tscn + 本函数）的实测公式，单位都是卡面局部：
		#   贴图左上角 y = 30 - 高度 + 下移
		#   实体（深色描边）顶部 = 左上角 + 描边起点/贴图高 * 高度
		# 蹲伏图是 240×240 画布、深色描边占 y9..225（217/240 = 90%），
		# 同一高度下实体比镇山（156/164 = 95%）更矮、但**头顶离画布上沿只有 3.8%**。
		# 结果就是高度给到 82（战场口径）时，贴图整块落在 y -46~36，
		# 发髻整个跑到卡框（y 8~54.5）上方、被 CardBg 的 clip_children 切掉，
		# 卡面只剩胸口以下——这就是「人太上面」的成因，光加下移救不回来：
		# 下移每加 1 只把整块往下挪 1，加 20 脚就到了费字区。
		# 所以改成「按卡框重新定尺」：实体约 56 高，落在 y≈13.1~49.1，
		# 头顶留 5.1、脚底留 5.4，与镇山（头顶被框切、脚底留 15）不是同一构图，
		# 但这是蹲伏姿态唯一能完整入框的放法；图鉴缩略图同参放大 1.6 后同样完整。
		# 战场仍用 82（potato_mine.tscn 自己管），这里只影响卡面与图鉴缩略图。
		"高度": 62.0,
		"下移": 14.5,
	},
	"Plant004WallNut": {		# 镇山老翁三态里取**态1（完好）**：卡面/图鉴缩略图表示「这是什么植物」，
		# 应该是最健康的那一档；破损与濒死只出现在战场挨打之后。
		# 竹杖不单独叠一层：卡面模板同一处只放一张整图，而且 22° 斜背的杖在 41px 的
		# 小卡上只会读成一根杂线，反而糊掉轮廓。战场/图鉴详情页里有杖，那里才看得到。
		"贴图": "res://assets/image/character/wallnut/wallnut_state1.png",
		# 与战场同一显示高度（82），卡片本身再统一乘 0.5；实体占卡面 y≈7~46，与其他三株齐平
		"高度": 82.0,
		"下移": 6.0,
	},
	"Plant007Chomper": {
		# 大嘴花换皮：Q 版醉仙客，侧持青玉酒葫芦。
		# [br]⚠️ **2026-10-26 第二十次换素材：→ zuixianke_idle.png（定稿 v3 侧持）。**
		# 此前用的是 `chomper_idle_01.png`（旧版剑仙，满幅 400 高、实体占 100%），
		# 现在战场已经换成新立绘，卡面必须同步 —— 否则卡上是旧人、场上是新人的两副面孔。
		# [br]新图是 124×224，人物实体只占 y18..205（上下各 7.1% 透明留白，为的是战场头顶不出格）。
		# 所以卡面的「高度」不能照旧值直接搬：同一数值在新图上会缩出**更小的人**。
		"贴图": "res://assets/image/character/chomper/zuixianke_idle.png",
		# 定尺推导（卡面局部坐标，链路：CharacterStatic(24,30) → holder(1,14) scale 0.5 → art）。
		# [br]⚠️ 2026-10-27 校正：下面这段旧推导里的 0.4 和「豆蔻 25.4 / 朝阳 27.5」都不对，
		# 实测 holder 全是 0.5、四株实体分别是 37.6 / 39.0 / 39.0（裴 28.3 是蹲伏特例）。
		# 92 这个值本身没问题（实得 38.6，和其余四株齐平），只是公式写错了倍数，别拿它反推新株。
		# [br]实体落位公式：art_cy = 44 + (下移 - 高度/2) × 0.4；
		# [br]实体 y = art_cy + (18…205 - 112) × (高度/224) × 0.4。
		# 实测各档实得实体高（卡面像素）：
		#   豆蔻 25.4 / 朝阳童子 27.5 / 镇山老翁 27.5
		# 醉仙客若沿用旧值 95 → 实体仅 31.8（比豆蔻高 25%，会读成「比镇山还大一号」）；
		# 取 **92** → 实体 30.8，落在 y 8.1…38.9，
		# 头顶留 8.1（卡框 0~70，上方不会切）、脚底离下方费用数字区留足，
		# 与另外三株「头顶 16~18、脚底 43~44」不是同一构图，但**体量**最接近，
		# 这是带 7% 透明留白的贴图能取到的最近一档。别再往上加。
		"高度": 92.0,
		# 下移：新图透明留白已自带上下气口，比旧图少压
		"下移": 4.0,
	},
	"Plant006SnowPea": {
		# 寒冰射手换皮：Q 版仙侠「雪清仙子」，无球版待机立绘。
		# [br]五张卡的 holder 缩放**都是 0.5**（模板 self scale，不是本表能改的），
		# 真正决定卡面大小的只有「高度」和「贴图里实体占多少」两个变量。
		# [br]贴图是 264×398，人物实体占 y8..390（高 383 = 96.2%），左右已居中
		# （实体中心 x=131，画布中心 132，偏移 1px 可忽略）。
		"贴图": "res://assets/image/character/snow_pea/xueqing_idle.png",
		# 定尺推导（卡面局部坐标，链路：CharacterStatic(24,30) → holder(1,14) scale 0.5 → Body(0,0) → art）：
		# [br]art 中心 y = 44 + (−高度/2 + 下移) × 0.5；
		# [br]画布高 = 高度 × 0.5，实体高 = 画布高 × 383/398。
		# [br]取 79 → 画布 39.5、实体 38.0，落在 y≈7.0…45.0。
		# [br]⚠️ 别照「和别人同一高度值」的直觉填：这张贴图实体占 96.2%（上下各只有 8px 留白），
		# 而醉仙客只占 83.9%、裴无咎 91.2% —— 同一个「高度」在窄画布上缩出来的实体**更小**。
		# 此前按 58 填过一次，实测实体只有 27.9（其余四株是 37.6 / 39.0 / 39.0 / 38.6），
		# 卡面里明显小一号，就是吃了这个亏。
		"高度": 79.0,
		# 下移：贴图上下各只有 8px 透明留白（2%），气口很窄，所以比醉仙客少压
		"下移": 3.5,
	},
	"Plant008PeaShooterDouble": {
		# 阿双换皮：竹青绿衣、竹铳双持的 Q 版少年，待机立绘。
		# [br]口径照豆蔻（P001）——**同一株草坪上并排的两棵，卡面也必须一样高**，
		# 所以匹配的是「实体高」而不是「高度」值本身：
		# [br]豆蔻贴图 125×206、实体占 99.0%（204px，上下各 1px 留白），
		# 高度 76 → 实体 75.26、脚底落在 y=43.63；
		# [br]阿双贴图 133×206、实体占 96.1%（198px，上下各 4px 留白），
		# 同一条实体高反算 → 高度 78.3，下移保持 6.0（脚底同样落在 43.63）。
		# [br]两图实体中心都正好在画布中线（豆蔻 62.5 / 阿双 66.5），横向不用补偏。
		"贴图": "res://assets/image/character/adouble/adouble_idle_03.png",
		"高度": 78.3,
		"下移": 6.0,
	},
}
#endregion


## 把 [param static_root] 里登记过的散件版角色换成整图；没登记的卡牌原样返回。
func _apply_custom_card_art(static_root: Node2D) -> void:
	if not is_instance_valid(static_root):
		return
	for role_name: String in CARD_ART:
		# 卡面容器按角色名登记，只有对应那张卡会有这个节点
		var holder: Node2D = static_root.find_child(role_name, true, false) as Node2D
		if holder == null:
			continue
		var body_correct: Node2D = holder.find_child("BodyCorrect", true, false) as Node2D
		if body_correct == null:
			continue
		# 已经换过就不再重复叠加；每个角色用自己的节点名，模仿卡也不会互相覆盖
		var art_name: String = "CardArt_" + role_name
		if body_correct.get_parent().find_child(art_name, false, false) != null:
			continue
		var entry: Dictionary = CARD_ART[role_name]
		var art_path: String = entry["贴图"]
		var tex: Texture2D = _card_art_texture(art_path, int(entry.get("贴图帧", -1)))
		if tex == null:
			push_warning("卡面：贴图没找到或还没导入 → %s" % art_path)
			continue
		var height: float = entry["高度"]
		# 散件整体隐藏，只留整图
		body_correct.visible = false
		var art := Sprite2D.new()
		art.name = art_name
		art.texture = tex
		var s: float = height / float(tex.get_height())
		art.scale = Vector2(s, s)
		# 脚底对齐到 y=0，与散件版的基准线一致；再整体下移一点，让大头不顶卡面上沿
		art.position = Vector2(0.0, -height * 0.5 + float(entry["下移"]))
		body_correct.get_parent().add_child(art)


## 取卡面用的贴图。[param frame] 为负时整张直用；否则把它当横排图集，切出第 [param frame] 帧。
## [br]图集每帧 320×400、等宽排布、脚底已对齐 —— 与战场那张完全同一份素材，
## 切出来的单帧高度仍是 400，所以「高度」口径不受影响。
func _card_art_texture(art_path: String, frame: int) -> Texture2D:
	var src: Texture2D = load(art_path) as Texture2D
	if src == null or frame < 0:
		return src
	var atlas := AtlasTexture.new()
	atlas.atlas = src
	atlas.region = Rect2(frame * CHOMPER_FRAME_W, 0, CHOMPER_FRAME_W, CHOMPER_FRAME_H)
	atlas.filter_clip = true
	return atlas
