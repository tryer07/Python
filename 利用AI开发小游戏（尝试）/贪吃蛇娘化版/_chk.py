# -*- coding: utf-8 -*-
"""临时检查脚本：查看贴图模式/尺寸/透明像素分布（用完即删）。"""
from PIL import Image

paths = [
    r"assets/effects/melee/stella_atk_lamia.png",
    r"assets/effects/melee/stella_atk_human.png",
    r"assets/effects/melee/sakura_atk_lamia.png",
    r"assets/effects/melee/src/stella_atk_lamia.png",
    r"assets/characters/lamia_flare/atk_1.png",
]
for p in paths:
    im = Image.open(p)
    info = [p, im.mode, im.size]
    if im.mode == "RGBA":
        h = im.getchannel("A").histogram()
        info.append(("transparent_px", h[0], "opaque_px", h[255]))
    print(info)
