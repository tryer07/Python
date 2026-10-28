extends BulletLinear000Base
class_name Bullet102DartFire

## 豆蔻的火焰飞镖。
## 飞镖穿过火炬树桩后由 [Plant023TorchWood] 升级成此子弹：[br]
## - 外形换成淬火后的火镖（[code]douku_dart_fire.png[/code]）+ 多股火舌拖焰；[br]
## - 伤害翻倍（20 -> 40），与火焰豌豆的火弹倍率一致；[br]
## - 命中先解除目标的冰冻，再结算伤害（火属性统一行为）。

## 拖焰贴图节点。放在 Body 下、z_index = -1，保证压在本体后面。
@onready var trail: Sprite2D = $Body/FireTrail

## 拖焰在场景里配置的基准缩放，闪烁时以它为基准做相对变化。
var _trail_base_scale: Vector2 = Vector2.ONE
## 闪烁相位，避免同屏多枚火镖同步呼吸。
var _flicker_phase: float = 0.0

func _ready() -> void:
	super()
	_flicker_phase = randf() * TAU
	if trail != null:
		_trail_base_scale = trail.scale
	else:
		push_warning("Bullet102DartFire: 缺少 Body/FireTrail，火镖将没有拖焰表现。")

## 拖焰做轻微呼吸，避免看起来像一张静态贴纸。
func _process(delta: float) -> void:
	if trail == null:
		return
	_flicker_phase += delta
	var t: float = _flicker_phase
	trail.scale = Vector2(
		_trail_base_scale.x * (1.0 + sin(t * 24.0) * 0.09),
		_trail_base_scale.y * (1.0 + sin(t * 17.0 + 1.3) * 0.12)
	)
	trail.modulate.a = 0.80 + sin(t * 29.0) * 0.20

## 火属性：先解冻再结算双倍伤害。参数为空表示撞地或落空。
func _attack_enemy(enemy: Character000Base) -> void:
	if is_instance_valid(enemy) and _can_attack_character(enemy):
		enemy.cancel_ice()
	super(enemy)
