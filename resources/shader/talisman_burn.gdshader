shader_type canvas_item;

// 符咒自下而上烧尽：burn 0 为完整，1 为烧空。
// 燃烧线附近叠一层橙红余烬，ember_strength 用来做「蓄力越来越亮」。
uniform float burn : hint_range(0.0, 1.0) = 0.0;
uniform float edge_width : hint_range(0.01, 0.4) = 0.12;
uniform vec4 ember_color : source_color = vec4(1.0, 0.60, 0.16, 1.0);
uniform float ember_strength : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	vec4 tex = texture(TEXTURE, UV);
	// UV.y 向下为正：燃烧线以上的部分保留，以下的部分烧掉
	float line = 1.0 - burn;
	if (UV.y > line) {
		discard;
	}
	float dist = line - UV.y;
	float ember = 1.0 - smoothstep(0.0, edge_width, dist);
	vec3 hot = ember_color.rgb * (1.0 + ember * ember_strength * 1.8);
	tex.rgb = mix(tex.rgb, hot, ember * ember_strength);
	COLOR = tex * COLOR;
}
