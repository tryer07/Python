extends BombEffectBase
class_name BombEffectCherryBomb

## 火海持续时长：伤害早在 bomb_once 里一次性结算完了，这里只是让余烬烧满一秒。
const FIRE_SEA_TIME: float = 1.0
## 火海覆盖的行列数（自身所在格 ± 1）
const FIRE_SEA_ROWS: int = 3
const FIRE_SEA_COLS: int = 3

@onready var gpu_particles_2d: GPUParticles2D = $GPUParticles2D
@onready var gpu_particles_2d_2: GPUParticles2D = $GPUParticles2D2
@onready var explosive_font: Sprite2D = $ExplosiveFont


## 樱桃炸弹爆炸特效
func activate_bomb_effect():
	# 火海要按草坪格子铺，必须在 super() 把本节点搬去 bombs 之前先拿到植物与它的格子。
	var plant: Plant000Base = _get_owner_plant()
	super()
	gpu_particles_2d.emitting = true
	gpu_particles_2d_2.emitting = true
	_spawn_fire_sea(plant)

	await get_tree().create_timer(gpu_particles_2d.lifetime/2).timeout
	explosive_font.queue_free()
	await gpu_particles_2d.finished
	queue_free()


## 取爆炸组件所属的植物。节点层次固定是 植物 → BombComponent → BombEffect。
func _get_owner_plant() -> Plant000Base:
	var component: Node = get_parent()
	if component == null:
		return null
	var owner_plant: Node = component.get_parent()
	return owner_plant as Plant000Base


## 铺三行三列火海。火海挂在格子上而不是植物上，植物被销毁后余烬仍会烧完。
func _spawn_fire_sea(plant: Plant000Base) -> void:
	if plant == null or plant.plant_cell == null:
		return
	if Global.main_game == null:
		return
	Global.main_game.plant_cell_manager.cherry_fire_sea(
		plant.row_col, FIRE_SEA_ROWS, FIRE_SEA_COLS, FIRE_SEA_TIME)
