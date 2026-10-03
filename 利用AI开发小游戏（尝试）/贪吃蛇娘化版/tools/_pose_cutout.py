# -*- coding: utf-8 -*-
"""把樱落 10 张释放姿势源图（浅灰不透明底）抠成透明底，裁切后写入
assets/characters/sakura/cast_{1-5}.png（半人半蛇）与 cast_human_{1-5}.png（人化）。

去底策略：只清除「与画面边界连通的近背景色区域」（border-connected flood fill），
角色内部的白色/浅色（花瓣、高光）因被轮廓隔断而保留，避免误伤。
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from PIL import Image

SRC = r"D:\AI图片学习包\娘化版人物形象加一些贴图参考\樱落"
DST = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版\assets\characters\sakura"

MAP = {  # 目标文件名 -> 源文件名
    "cast_1.png": "樱落_技能1_花信.png",
    "cast_2.png": "樱落_技能2_催放.png",
    "cast_3.png": "樱落_技能3_花圃.png",
    "cast_4.png": "樱落_技能4_回旋花刃.png",
    "cast_5.png": "樱落_技能5_花期.png",
    "cast_human_1.png": "樱落人化_技能1_花信.png",
    "cast_human_2.png": "樱落人化_技能2_催放.png",
    "cast_human_3.png": "樱落人化_技能3_花圃.png",
    "cast_human_4.png": "樱落人化_技能4_回旋花刃.png",
    "cast_human_5.png": "樱落人化_技能5_花期.png",
}

SAT_TOL = 34       # 背景近中性灰：max-min 通道差上限
DIST_TOL = 46      # 与参考背景色的欧氏距离上限


def bg_ref(rgb):
    """取四角 24×24 补丁的中位色作为背景参考色。"""
    h, w, _ = rgb.shape
    p = []
    for ys, xs in ((0, 0), (0, w - 24), (h - 24, 0), (h - 24, w - 24)):
        p.append(rgb[ys:ys + 24, xs:xs + 24].reshape(-1, 3))
    return np.median(np.concatenate(p, 0), axis=0)


def flood_from_border(mask):
    """返回 mask 中「与边界连通」的像素布尔图（4 邻域迭代膨胀至不动点）。"""
    reach = np.zeros_like(mask)
    reach[0, :] = mask[0, :]
    reach[-1, :] = mask[-1, :]
    reach[:, 0] = mask[:, 0]
    reach[:, -1] = mask[:, -1]
    while True:
        new = reach.copy()
        new[1:, :] |= reach[:-1, :]
        new[:-1, :] |= reach[1:, :]
        new[:, 1:] |= reach[:, :-1]
        new[:, :-1] |= reach[:, 1:]
        new &= mask
        if np.array_equal(new, reach):
            return reach
        reach = new


def cutout(src_path, dst_path):
    im = Image.open(src_path).convert("RGBA")
    arr = np.array(im).astype(np.int16)
    rgb = arr[:, :, :3]
    a = arr[:, :, 3]
    ref = bg_ref(rgb.astype(np.float32))
    sat = rgb.max(2) - rgb.min(2)
    dist = np.sqrt(((rgb.astype(np.float32) - ref) ** 2).sum(2))
    near_bg = (sat < SAT_TOL) & (dist < DIST_TOL) & (a > 0)
    bg = flood_from_border(near_bg)
    out = np.array(im)
    out[:, :, 3] = np.where(bg, 0, out[:, :, 3])
    # 裁切到内容包围盒 + 8px 边距
    alpha = out[:, :, 3]
    ys, xs = np.where(alpha > 0)
    if len(ys):
        y0, y1 = max(0, ys.min() - 8), min(out.shape[0], ys.max() + 9)
        x0, x1 = max(0, xs.min() - 8), min(out.shape[1], xs.max() + 9)
        out = out[y0:y1, x0:x1]
    Image.fromarray(out, "RGBA").save(dst_path)
    h, w = out.shape[:2]
    trans = round(100.0 * float((out[:, :, 3] == 0).sum()) / (w * h), 1)
    return (w, h), trans


os.makedirs(DST, exist_ok=True)
for dst_name, src_name in MAP.items():
    sp = os.path.join(SRC, src_name)
    dp = os.path.join(DST, dst_name)
    if not os.path.isfile(sp):
        print("缺源图:", src_name); continue
    dim, trans = cutout(sp, dp)
    print(f"{dst_name:20s} <- {src_name}  尺寸{dim}  透明占比{trans}%")
print("完成")
