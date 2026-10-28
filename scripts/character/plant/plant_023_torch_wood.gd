extends Plant000Base
class_name Plant023TorchWood

## 当前升级的子弹
var curr_bullet_up :Array[Bullet000Base] = []
## 子弹根节点
var bullets:Node2D

## 子弹升级数据
const bullet_upgrade_data = {
	BulletRegistry.BulletType.Bullet001Pea: BulletRegistry.BulletType.Bullet006PeaFire,
	## ⚠️ 2026-10-26 第八轮：原来这里写的是 Bullet001Pea（普通豌豆）——
	## 雪清仙子的冰球过火会**掉级成既无冰也无火的普通豌豆**，这就是
	## "寒冰射手过火炬树桩变成原来的豌豆"的真正原因，跟贴图无关。
	## 现按用户指定改为「冰火球」：伤害翻倍 + 保留减速。
	BulletRegistry.BulletType.Bullet002PeaSnow: BulletRegistry.BulletType.Bullet103IceFire,
	## 豆蔻的飞镖穿过火炬树桩后淬火，变成火焰飞镖（伤害翻倍）
	BulletRegistry.BulletType.Bullet101Dart: BulletRegistry.BulletType.Bullet102DartFire,
}

func ready_norm() -> void:
	super()
	var main_game:MainGameManager = get_tree().current_scene
	bullets = main_game.bullets

## 子弹进入升级区域
func _on_area_2d_up_bullet_area_entered(area: Area2D) -> void:
	var bullet:Bullet000Base = area.owner
	if bullet.is_can_up and bullet.bullet_type in bullet_upgrade_data.keys():
		_up_bullet(bullet)

## 子弹离开当前区域
func _on_area_2d_up_bullet_area_exited(area: Area2D) -> void:
	var bullet:Bullet000Base = area.owner
	if bullet in curr_bullet_up:
		curr_bullet_up.erase(bullet)

## 升级子弹
func _up_bullet(curr_bullet:Bullet000Base):
	if curr_bullet not in curr_bullet_up:
		var new_bullet_up_scenes = Global.bullet_registry.get_bullet_scenes(bullet_upgrade_data[curr_bullet.bullet_type])
		var bullet_up :Bullet000Base = new_bullet_up_scenes.instantiate()
		bullet_up.init_bullet(curr_bullet.get_bullet_paras())
		curr_bullet_up.append(bullet_up)
		bullets.call_deferred("add_child", bullet_up)
		curr_bullet.queue_free()
