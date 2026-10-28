extends BombEffectBase
class_name BombEffectPotatoMine

## 裴无咎出手的爆炸表现：**只有剑气**，不播土豆地雷原来的碎石与压扁贴图。
##
## 为什么要把原有两层停掉：原版激活时会把石屑粒子与 Anim_mashed（压扁的土豆）
## 一起铺出来，0.3 秒内仍读作「土豆地雷炸了」，剑气反而像附加物。
## 这两个节点留在场景里不动（要回退只需删掉下面两行），但不再参与演出。
## 范围/伤害早在 BombComponent 里结算完，这里只碰视觉。

@onready var gpu_particles_2d: GPUParticles2D = $GPUParticles2D
## 原版「压扁土豆」贴图
@onready var anim_mashed: Sprite2D = $Anim_mashed
## 剑气节点；场景里没挂也不会崩，只是少一层表现
@onready var sword_qi: Plant005SwordQi = get_node_or_null("SwordQi") as Plant005SwordQi


func activate_bomb_effect():
	super()
	# 关掉土豆地雷原有的两层表现
	gpu_particles_2d.emitting = false
	gpu_particles_2d.visible = false
	anim_mashed.visible = false

	if sword_qi == null:
		# 没有剑气时才退回原版粒子，免得出事连一个反馈都没有
		gpu_particles_2d.visible = true
		gpu_particles_2d.emitting = true
		await gpu_particles_2d.finished
		queue_free()
		return

	sword_qi.burst()
	# 剑气自己会在 duration 后 queue_free；本节点等演出走完再清
	await get_tree().create_timer(sword_qi.duration + 0.10).timeout
	if is_inside_tree():
		queue_free()
