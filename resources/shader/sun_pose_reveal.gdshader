shader_type canvas_item;

// 朝阳童子的「抬手 / 落手」换帧擦除。
//
// 两帧立绘下半身完全一样，只有上半身不同（手臂位置、眼睛睁合）。
// 直接交叉淡化会出现「四只手 + 两只眼睛」的重影，读起来就是硬切。
// 这里改成一条软边沿着身体往上扫：扫到哪儿，哪儿的像素才换成新姿势。
// 于是抬手时手臂是从肩膀往指尖方向「长」出来的，落手时从指尖往肩膀收回去，
// 符合肢体伸展 / 收回的前后顺序，不是整块替换。
//
// 擦除方向：UV.y 越小越靠上（0 = 头顶）。
// progress 增大 → 边界上移 → 下半身先换、上半身后换。

// 0 = 完全是旧姿势，1 = 完全是新姿势。由植物脚本的 Tween 驱动。
uniform float progress : hint_range(0.0, 1.0) = 0.0;

// 擦除区下沿（UV.y）。低于这里的两帧像素完全一致（盘腿、袍摆），
// 不参与擦除，免得腿部跟着闪。
uniform float zone_bottom : hint_range(0.0, 1.0) = 0.75;

// 软边宽度（UV 比例）。太窄会出现一条硬切线，太宽又退化成整体淡化 ——
// 0.09 × 164 ≈ 15px，比脸窄，擦过五官时不会出现「两只眼睛叠在一起」。
uniform float softness : hint_range(0.02, 0.5) = 0.09;

// 边界上那一圈暖光。progress 在两端时自动归零，只有扫的过程中才亮，
// 所以收势之后不会在腰上留一条亮线。
uniform float edge_glow : hint_range(0.0, 1.0) = 0.40;

void fragment() {
	vec4 col = texture(TEXTURE, UV);

	// progress=0 → 边界停在擦除区下沿再往下一点（一个像素都不露）；
	// progress=1 → 边界升到画面上沿之上一点（头顶也完全换上）。
	float edge = mix(zone_bottom + softness, -softness, progress);

	// UV.y 在边界以下（更大）= 已经被新姿势覆盖
	float reveal = smoothstep(edge - softness, edge + softness, UV.y);
	// 擦除区以下强制保留旧姿势，腿部永不参与
	reveal *= step(UV.y, zone_bottom);

	// 扫过的暖光带：sin 让它在起手 / 收手两端自然淡出
	float band = (1.0 - smoothstep(0.0, softness * 1.5, abs(UV.y - edge))) * sin(progress * PI);
	col.rgb += vec3(1.0, 0.86, 0.55) * band * edge_glow;

	COLOR = vec4(col.rgb, col.a * reveal);
}
