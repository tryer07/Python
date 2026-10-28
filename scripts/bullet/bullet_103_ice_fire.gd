extends BulletLinear000Base
class_name Bullet103IceFire

## 雪清仙子的「冰火球」——冰球穿过火炬树桩后由 [Plant023TorchWood] 升级成此子弹。
## [br]设计口径（用户 2026-10-26 明确指定，不要改）：
## [br]· **伤害翻倍**：场景里 attack_value = 40（普通冰豆 20）；
## [br]· **保留减速**：命中后仍调用 [method Character000Base.be_ice_decelerate]；
## [br]· **火属性附带解冻**：与火豌豆一致，命中时先 [method Character000Base.cancel_ice]。
## [br]⚠️ 顺序不可颠倒：`cancel_ice()` 会停掉减速计时器并恢复原速，
## [br]所以必须**先解冻再挂减速**；反过来火焰会把自己刚加的减速立刻取消。
## [br]净效果：解除硬冰冻控制（冰壳特效消失），但保留 50% 减速 —— 这正是
## [br]"冰火球"该有的手感，也符合用户"仍有减速效果"的要求。
## [br]参数传递：升级时走 [method Bullet000NormBase.init_bullet]，只继承
## [br]行号/位置/方向/可攻击状态；伤害、速度、减速时长全部由本子弹场景自身决定。

## 命中后减速持续的秒数，与 [Bullet002PeaSnow] 保持一致。
@export var time_be_decelerated: float = 3.0

## 火壳闪烁相位，让每颗球的火苗节奏错开，避免一排齐闪。
var _fire_phase: float = 0.0
## 火壳贴图，用于做呼吸式缩放
var _fire_shell: Sprite2D
## 火壳在场景里定好的基准缩放（0.6），呼吸时在此基础上乘系数
var _fire_shell_base_scale: Vector2 = Vector2.ONE

func _ready() -> void:
	super()
	_fire_phase = randf() * TAU
	_fire_shell = get_node_or_null(^"Body/FireShell") as Sprite2D
	## ⚠️ 必须记住场景里画好的基准缩放：下面 `_process` 每帧写的是**绝对值**，
	## 直接写 Vector2(k,k) 会把 tscn 里的 0.6 覆盖成 1.0，火环瞬间涨回 66px。
	if _fire_shell != null:
		_fire_shell_base_scale = _fire_shell.scale

## 火壳呼吸：只缩放外圈，冰核保持稳定，强调"外火内冰"的结构差。
func _process(delta: float) -> void:
	if _fire_shell == null:
		return
	_fire_phase += delta * 7.0
	var k: float = 1.0 + sin(_fire_phase) * 0.06
	_fire_shell.scale = _fire_shell_base_scale * k

func _attack_enemy(enemy: Character000Base) -> void:
	var can_hit: bool = is_instance_valid(enemy) and _can_attack_character(enemy)
	if can_hit:
		## 火属性统一行为：命中先解冻（否则残留的冰冻状态和火属性观感冲突）
		enemy.cancel_ice()
	super(enemy)
	if not can_hit:
		return
	## 目标可能在本体伤害里被击杀并释放，挂减速前必须重新校验
	if not is_instance_valid(enemy) or not _can_attack_character(enemy):
		return
	## 冰属性保留：二类防具还在的僵尸不吃冰冻减速，与原版寒冰豌豆规则一致
	if enemy is ZB000Base:
		enemy.be_ice_decelerate(time_be_decelerated)
	elif enemy is Zombie000Base and enemy.hp_component.curr_hp_armor2 <= 0:
		enemy.be_ice_decelerate(time_be_decelerated)
