# -*- coding: utf-8 -*-
"""用 edge-tts 把樱落详情页互动台词渲染成日语配音（作者期合成，运行时离线）。

产物落 assets/audio/sfx/voice_sakura_<region>_<i>.mp3，与 characters.json 的
egg_lines[region][i] 按下标一一对应；AudioManager.play("voice_sakura_<region>_<i>")
走现有 sfx 文件探测直接播放，无需改播放逻辑。
声线 ja-JP-NanamiNeural（自然女声，真人感）；语速稍缓贴合樱落温柔人设。
"""
import os, sys, asyncio
sys.stdout.reconfigure(encoding="utf-8")
import edge_tts

SFX = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版\assets\audio\sfx"
VOICE = "ja-JP-NanamiNeural"
RATE = "-6%"      # 稍缓，温柔感
PITCH = "+2Hz"    # 微抬，少女感但不失真

# 与 characters.json sakura.egg_lines 下标严格对齐的日语台词
LINES = {
    "head": [
        "あっ…頭、触られちゃった。花びら、乱れちゃうじゃない。",
        "頭は…あなただけにしか許さないんだから。",
    ],
    "body": [
        "腰のあたりは…鱗が始まるところなの。くすぐったい…",
        "も、もう…勝手に触らないで。恥ずかしいんだから。",
    ],
    "tail": [
        "尻尾は私の誇りなの。優しくしてね。",
        "尾の先が撫でたところから、新しい芽が顔を出すの。",
    ],
}


async def gen(region, i, text):
    name = f"voice_sakura_{region}_{i}"
    out = os.path.join(SFX, name + ".mp3")
    os.makedirs(SFX, exist_ok=True)
    com = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await com.save(out)
    print(f"[ok] {name}.mp3  {os.path.getsize(out)//1024}KB  {text}")


async def main():
    for region, lines in LINES.items():
        for i, text in enumerate(lines):
            await gen(region, i, text)


asyncio.run(main())
print("配音生成完成")
