extends Node2D
## 裴无咎两姿势阴影对比。用完即删。

const MINE := preload("res://scenes/character/plant/plant_005_potato_mine.tscn")

func _ready() -> void:
	var bg := ColorRect.new()
	bg.color = Color(0.376, 0.580, 0.251)
	bg.size = Vector2(900, 460)
	add_child(bg)

	var a := MINE.instantiate() as Plant005PotatoMine
	add_child(a)
	a.position = Vector2(220, 300)
	a._set_pose("sit")

	var b := MINE.instantiate() as Plant005PotatoMine
	add_child(b)
	b.position = Vector2(520, 300)
	b._set_pose("crouch")

	await get_tree().create_timer(0.6).timeout
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("user://shadow_check.png")
	for p: Array in [["sit", a], ["crouch", b]]:
		var sh: Sprite2D = (p[1] as Plant000Base).get_node("Shadow") as Sprite2D
		print("%s shadow scale=%s tex=%s pos=%s" % [
			p[0], str(sh.scale), str(sh.texture.get_size() if sh.texture else Vector2.ZERO), str(sh.position)])
	get_tree().quit()
