shader_type canvas_item;
render_mode blend_add;

// 符咒自下而上烧尽（叠加发光版）。
// 和 talisman_burn.gdshader 的区别：
// 1) 这里是 blend_add —— 整图立绘里赤童手上本来就画着符，再盖一张实心符就成了两张符，
//    叠加发光才是「同一张符在烧」。
// 2) 烧线带两层噪声抖动 + 一道白热芯 + 火苗跳动。
//    老版本是一条笔直的 `1.0 - burn` 切一刀，在十几像素的符上根本读不出「在烧」，
//    看起来只像有人从下面把纸抽走了。
uniform float burn : hint_range(0.0, 1.0) = 0.0;
// 火线厚度（UV）。符贴图只有 14×32，0.42 就等于符纸全长的 41%——
// 纸烧掉一半后剩下的部分会整块落进火线带，糊成一个纯白方块，
// 反而看不出「火在往上走」。0.18 ≈ 6px，火舌另外用 plume 铺开。
uniform float edge_width : hint_range(0.02, 0.8) = 0.18;
uniform vec4 ember_color : source_color = vec4(1.0, 0.58, 0.24, 1.0);
uniform vec4 core_color : source_color = vec4(1.0, 0.97, 0.86, 1.0);
uniform float ember_strength : hint_range(0.0, 1.0) = 0.0;
// 烧线锯齿的频率：值越大锯齿越碎，符纸窄，7 左右正好出 2~3 个起伏
uniform float noise_scale : hint_range(1.0, 40.0) = 7.0;
uniform float flicker : hint_range(0.0, 1.0) = 0.45;

float hash21(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash21(i);
	float b = hash21(i + vec2(1.0, 0.0));
	float c = hash21(i + vec2(0.0, 1.0));
	float d = hash21(i + vec2(1.0, 1.0));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void fragment() {
	vec4 tex = texture(TEXTURE, UV);
	float alpha = tex.a * COLOR.a;
	if (alpha < 0.01) {
		discard;
	}

	// 烧线：基础位置随 burn 自下而上推（UV.y 向下为正），再叠两层噪声把边缘啃成锯齿。
	// 抖动幅度乘 burn 渐入，否则刚点亮时烧线还没到，符脚就先缺一块。
	float wobble = (vnoise(vec2(UV.x * noise_scale, 1.7)) - 0.5) * 0.22
			+ (vnoise(vec2(UV.x * noise_scale * 2.7 + 11.3, 5.1)) - 0.5) * 0.10;
	wobble *= clamp(burn * 3.0, 0.0, 1.0);
	float line = 1.0 - burn + wobble;

	// 已烧尽的部分直接抠掉，露出立绘上原来那张符
	float dist = line - UV.y;
	if (dist <= 0.0) {
		discard;
	}

	// 火线分两层：贴线 35% 的宽度是满强度白热芯，再往外一圈半强度余烬。
	// 只用一层 smoothstep 的时候，真正「热」的只剩 1~2 个屏幕像素，
	// 缩进 GIF 等于没有，中段看起来像火已经灭了。
	float core = 1.0 - smoothstep(0.0, edge_width * 0.35, dist);
	float halo = 1.0 - smoothstep(edge_width * 0.35, edge_width, dist);
	float ember = core + halo * 0.55;

	// 火苗跳动：相位按 UV 拉开，读起来是火在舔纸，而不是整条线一起呼吸
	float t = TIME * 11.0;
	float flick = 0.72 + 0.28 * sin(t + UV.y * 34.0 + UV.x * 19.0)
			+ 0.08 * sin(t * 2.3 + UV.x * 7.0);
	ember *= mix(1.0, clamp(flick, 0.0, 1.6), flicker);

	// 底层是「被点亮的符纸」，火线处推向橙红→白热
	vec3 base = tex.rgb * ember_color.rgb;
	vec3 hot = mix(ember_color.rgb * 2.4, core_color.rgb * 3.2, ember);
	vec3 rgb = mix(base, hot, clamp(ember * ember_strength * 1.7, 0.0, 1.0));
	// 火线附近再补一点溢出光，让火苗「冒」出符纸轮廓
	rgb += core_color.rgb * ember * ember_strength * 0.35;

	// 火舌：烧线上方一小段随噪声闪烁的橙光，像火苗顺着符纸往上舔。
	// 没有这一层时，纸一烧掉就是「变暗 + 一条细线」，读不出火，
	// 只像有人把纸从下往上抽走了。
	if (ember_strength > 0.001) {
		float plume = 1.0 - smoothstep(0.0, edge_width * 2.6, dist);
		float n = vnoise(vec2(UV.x * 13.0, UV.y * 9.0 - TIME * 5.5));
		float tongue = smoothstep(0.38, 0.92, plume * (0.5 + 0.95 * n));
		rgb += ember_color.rgb * 2.0 * tongue * ember_strength;
	}

	COLOR = vec4(rgb, alpha);
}
