# -*- coding: utf-8 -*-
"""
素材整理脚本
把 AI 生成的原始大图，处理成游戏内实际使用的资源：
  1. 自动裁掉纯色/棋盘格底（判断"是不是纯背景色"）
  2. 去掉右下角水印区域
  3. 缩放到目标尺寸
  4. 按规范重命名

只用标准库 + Pillow，可重复执行（幂等）。
"""
import os
import sys
from collections import Counter

from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AST = os.path.join(BASE, "assets")

# 源文件 -> (目标相对路径, 目标尺寸上限, 是否去水印, 是否裁边)
JOBS = [
    # 角色：上半身（不裁边，保留完整构图，只去底）
    ("characters/Anime_game_sprite__upper_body__2026-10-01T08-46-51.png",
     "characters/sakura/head.png", (512, 512), True, False),
    # 角色：尾尖
    ("characters/Anime_game_sprite__the_taperin_2026-10-01T08-49-49.png",
     "characters/sakura/tail_tip.png", (256, 256), True, True),
    # 小怪
    ("characters/Anime_game_sprite__a_small_cut_2026-10-01T08-50-22.png",
     "characters/mob_shadow.png", (192, 192), True, True),
    # 掉落物：经验果
    ("items/Anime_game_item_icon__a_glowin_2026-10-01T08-50-55.png",
     "items/exp_berry.png", (128, 128), True, True),
    # 掉落物：能量结晶
    ("items/Anime_game_item_icon__a_glowin_2026-10-01T08-51-38.png",
     "items/energy_crystal.png", (128, 128), True, True),
    # 场景背景
    ("backgrounds/Anime_background_art__Japanese_2026-10-01T08-50-06.png",
     "backgrounds/campus_garden.png", (1920, 1080), True, False),
]


def strip_checker_bg(im, tol=26, min_frac=0.0005, grow=2):
    """
    去掉 AI 生图常见的「棋盘格伪透明底」。

    难点：棋盘格由深灰/浅灰两种交替的小方块组成，
    不能只按一个背景色去抠，否则会留下另一种灰。

    做法（flood fill + 颜色环绕判定）：
      1. 从四边向内 BFS，只走「接近灰阶且接近背景亮度」的像素
      2. 已连通的区域再往外膨胀 grow 像素，吃掉边缘抗锯齿的灰边
      3. 内部同色小块若也被判为背景，靠连通性自然排除不了，
         所以额外加一步：只保留面积最大的那块前景（清理孤岛）
    """
    from collections import deque

    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    def is_bg(r, g, b):
        # 灰阶判定：三通道接近，且整体是浅灰或深灰
        mx, mn = max(r, g, b), min(r, g, b)
        if mx - mn > tol:
            return False
        lum = (r + g + b) / 3
        return lum >= 150 or lum <= 120

    seen = [[False] * h for _ in range(w)]
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_bg(*px[x, y][:3]) and not seen[x][y]:
                seen[x][y] = True
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg(*px[x, y][:3]) and not seen[x][y]:
                seen[x][y] = True
                q.append((x, y))

    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[nx][ny]:
                if is_bg(*px[nx, ny][:3]):
                    seen[nx][ny] = True
                    q.append((nx, ny))

    # 膨胀，吃掉边缘灰边
    grown = [row[:] for row in seen]
    for _ in range(grow):
        nxt = [row[:] for row in grown]
        for y in range(h):
            for x in range(w):
                if grown[x][y]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and grown[nx][ny]:
                        nxt[x][y] = True
                        break
        grown = nxt

    # 统计剩余前景连通域，只保留最大的一块
    comp = [[0] * h for _ in range(w)]
    best, best_size, cid = 0, 0, 0
    for sy in range(h):
        for sx in range(w):
            if grown[sx][sy] or comp[sx][sy]:
                continue
            cid += 1
            size = 0
            cq = deque([(sx, sy)])
            comp[sx][sy] = cid
            while cq:
                x, y = cq.popleft()
                size += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and not grown[nx][ny] and not comp[nx][ny]:
                        comp[nx][ny] = cid
                        cq.append((nx, ny))
            if size > best_size:
                best_size, best = size, cid

    total = w * h
    for y in range(h):
        for x in range(w):
            if grown[x][y] or comp[x][y] != best:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)

    frac = best_size / total
    if frac < min_frac:
        print(f"   [警告] 前景只占 {frac:.2%}，抠图可能失败")
    return im


def strip_flat_bg(im, tol=18):
    """纯色背景抠图（用于白底/纯色底的图）"""
    im = im.convert("RGBA")
    w, h = im.size
    pts = []
    for x in range(0, w, max(1, w // 40)):
        for y in range(0, 3 * max(1, h // 40)):
            pts.append(im.getpixel((x, y))[:3])
    bg = Counter(pts).most_common(1)[0][0]
    px = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            if abs(r - bg[0]) <= tol and abs(g - bg[1]) <= tol and abs(b - bg[2]) <= tol:
                px[x, y] = (r, g, b, 0)
    return im


def auto_strip(im, name=""):
    """自动判断是棋盘格底还是纯色底"""
    im = im.convert("RGBA")
    w, h = im.size
    # 采四角 5x5 区域，看颜色种类
    samples = set()
    for ox, oy in ((0, 0), (w - 5, 0), (0, h - 5), (w - 5, h - 5)):
        for x in range(ox, ox + 5):
            for y in range(oy, oy + 5):
                samples.add(im.getpixel((x, y))[:3])
    if len(samples) > 1:
        print(f"   [棋盘格底] 检测到 {len(samples)} 种底色")
        return strip_checker_bg(im)
    print("   [纯色底] 检测到单一底色")
    return strip_flat_bg(im)


def kill_watermark(im, wm_w=230, wm_h=70):
    """抹掉右下角水印"""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(max(0, h - wm_h), h):
        for x in range(max(0, w - wm_w), w):
            r, g, b, a = px[x, y]
            px[x, y] = (r, g, b, 0)
    return im


def autocrop(im, pad=6, alpha_thresh=8):
    """按 alpha 裁掉四周空白"""
    im = im.convert("RGBA")
    bbox = im.getchannel("A").point(lambda v: 255 if v > alpha_thresh else 0).getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    l = max(0, l - pad); t = max(0, t - pad)
    r = min(im.width, r + pad); b = min(im.height, b + pad)
    return im.crop((l, t, r, b))


def fit(im, max_size):
    """等比缩放到不超过 max_size"""
    im = im.convert("RGBA")
    w, h = im.size
    mw, mh = max_size
    ratio = min(mw / w, mh / h)
    if ratio < 1:
        im = im.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)
    return im


def soften_alpha(im, radius=4):
    """对 alpha 通道做一次模糊，消除抠图留下的锯齿（要放在缩放之后）"""
    from PIL import ImageFilter
    im = im.convert("RGBA")
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    im.putalpha(a)
    return im


def make_body_seg(src_path, dst_path, size=(384, 384), taper=0.62, aspect=0.34):
    """
    把矩形蛇身纹理裁成「左粗右细」的梯形条带。
    游戏内按骨骼方向旋转拼接，就用这一张。
      aspect: 条带高度 / 图片宽度 —— 决定蛇的粗细（相对一格的大小）
      taper : 右端高度 / 左端高度  —— 0.62 表示向右收细到 62%
    """
    im = Image.open(src_path).convert("RGBA")
    im = auto_strip(im)
    im = autocrop(im)
    w, h = im.size
    band_h = max(24, int(w * aspect))
    top = (h - band_h) // 2
    band = im.crop((0, top, w, top + band_h))

    out_w, out_h = size
    canvas = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    left_h = int(out_h * 0.92)
    right_h = max(8, int(left_h * taper))
    for x in range(out_w):
        t = x / max(1, out_w - 1)
        seg_h = int(left_h + (right_h - left_h) * t)
        src_x = int(t * (band.width - 1))
        col = band.crop((src_x, 0, src_x + 1, band.height))
        col = col.resize((1, seg_h), Image.LANCZOS)
        canvas.alpha_composite(col, (x, (out_h - seg_h) // 2))
    canvas = soften_alpha(canvas, 1.2)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    canvas.save(dst_path, "PNG", optimize=True)
    print(f"[完成] body_seg 梯形 {canvas.size[0]}x{canvas.size[1]}  "
          f"{os.path.getsize(dst_path)//1024}KB  (taper={taper})")
    return canvas


def main():
    ok, fail = 0, 0
    for src_rel, dst_rel, size, wm, crop in JOBS:
        src = os.path.join(AST, src_rel.replace("/", os.sep))
        dst = os.path.join(AST, dst_rel.replace("/", os.sep))
        if not os.path.exists(src):
            print("[跳过] 源文件不存在:", src_rel)
            fail += 1
            continue
        im = Image.open(src)
        is_photo = "backgrounds" in src_rel
        if not is_photo:
            im = auto_strip(im, src_rel)
        if wm:
            im = kill_watermark(im)
        if crop and not is_photo:
            im = autocrop(im)
        im = fit(im, size)
        if "_soft" in dst_rel:
            im = soften_alpha(im)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im.save(dst, "PNG", optimize=True)
        print(f"[完成] {dst_rel}  {im.size[0]}x{im.size[1]}  {os.path.getsize(dst)//1024}KB")
        ok += 1

    # 单独处理：蛇身段做成梯形条带（不走通用流程）
    seg_src = os.path.join(AST, "characters/Anime_game_sprite_texture__a_h_2026-10-01T08-47-35.png"
                                .replace("/", os.sep))
    seg_dst = os.path.join(AST, "characters", "sakura", "body_seg.png")
    if os.path.exists(seg_src):
        make_body_seg(seg_src, seg_dst)
        ok += 1

    print(f"\n成功 {ok} 个，失败 {fail} 个")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
