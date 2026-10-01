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

# 源文件 -> (目标相对路径, 目标尺寸上限, 是否去水印, 是否裁边, 抠图方式)
# 抠图方式: auto=自动判断 / flood=从边缘泛洪(浅色净底+浅色主体, 保住主体内部白色) / flat=纯色全局匹配
JOBS = [
    # 小怪
    ("characters/Anime_game_sprite__a_small_cut_2026-10-01T08-50-22.png",
     "characters/mob_shadow.png", (384, 384), True, True, "auto"),
    # 掉落物：经验果
    ("items/Anime_game_item_icon__a_glowin_2026-10-01T08-50-55.png",
     "items/exp_berry.png", (256, 256), True, True, "auto"),
    # 掉落物：能量结晶
    ("items/Anime_game_item_icon__a_glowin_2026-10-01T08-51-38.png",
     "items/energy_crystal.png", (256, 256), True, True, "auto"),
    # 场景背景
    ("backgrounds/Anime_background_art__Japanese_2026-10-01T08-50-06.png",
     "backgrounds/campus_garden.png", (3840, 2160), True, False, "auto"),
    # 新增关卡背景（AI 生图无水印，wm=False 不做右下角抹除，避免透明角）
    ("backgrounds/neon_night_src.png",
     "backgrounds/neon_night.png", (3840, 2160), False, False, "auto"),
    ("backgrounds/deep_sea_src.png",
     "backgrounds/deep_sea.png", (3840, 2160), False, False, "auto"),
    ("backgrounds/sakura_realm_src.png",
     "backgrounds/sakura_realm.png", (3840, 2160), False, False, "auto"),
]

# 角色三件套表：(源图短键, 角色 id)。
# 源图约定放在 assets/characters/{短键}_src_{upper|scale|tail}.png，
# 产物输出到 assets/characters/{角色 id}/{head|body_seg|tail_tip}.png。
CHARACTERS = [
    ("sakura", "sakura"),
    ("mint", "lamia_mint"),
    ("tide", "lamia_tide"),
    ("flare", "lamia_flare"),
    ("stella", "lamia_stella"),
    ("luna", "lamia_luna"),
]


def strip_checker_bg(im, tol=26, min_frac=0.0005, grow=2, bg_color=None, bg_tol=24):
    """
    去掉 AI 生图常见的「棋盘格伪透明底」。

    难点：棋盘格由深灰/浅灰两种交替的小方块组成，
    不能只按一个背景色去抠，否则会留下另一种灰。

    做法（flood fill + 颜色环绕判定）：
      1. 从四边向内 BFS，只走「接近灰阶且接近背景亮度」的像素
      2. 已连通的区域再往外膨胀 grow 像素，吃掉边缘抗锯齿的灰边
      3. 内部同色小块若也被判为背景，靠连通性自然排除不了，
         所以额外加一步：只保留面积最大的那块前景（清理孤岛）

    bg_color 给定时切换为「紧贴底色」模式：只把与边框底色接近的像素当背景。
    用于角色立绘——否则角色身上的浅色/白色衣物（低饱和）会被灰阶启发式误吃。
    """
    from collections import deque

    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    def is_bg(r, g, b):
        if bg_color is not None:
            return max(abs(r - bg_color[0]), abs(g - bg_color[1]),
                       abs(b - bg_color[2])) <= bg_tol
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


def keep_largest(im, alpha_thresh=8):
    """只保留面积最大的一块前景，清掉孤岛/垫色合并进来的碎片"""
    from collections import deque

    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    comp = [[0] * h for _ in range(w)]
    best, best_size, cid = 0, 0, 0
    for sy in range(h):
        for sx in range(w):
            if px[sx, sy][3] <= alpha_thresh or comp[sx][sy]:
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
                    if 0 <= nx < w and 0 <= ny < h and comp[nx][ny] == 0 \
                            and px[nx, ny][3] > alpha_thresh:
                        comp[nx][ny] = cid
                        cq.append((nx, ny))
            if size > best_size:
                best_size, best = size, cid
    for y in range(h):
        for x in range(w):
            if comp[x][y] != best:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)
    return im


def strip_with_pad(im, pad=8, detect_tol=25, key=(255, 0, 255)):
    """
    适合「浅色净底 + 主体含白色且可能贴着图像边缘」的图（如白裙立绘、鳞片条带）。

    直接泛洪的问题：主体贴边时，贴边的白色会和外部背景连通，
    泛洪从边界灌进主体内部把白裙/鳞片高光吃掉。

    做法：
      1. 检测哪些边被主体碰到（该边存在明显非底色的像素）
      2. 只在碰到的边外垫一圈饱和 key 色（泛洪不认它，起到封口作用）
      3. 泛洪去底（主体内部白色因被封口而保留）
      4. 裁掉垫的边，恢复原构图
    """
    from collections import Counter as _Counter

    im = im.convert("RGBA")
    w, h = im.size
    border = []
    for x in range(0, w, 2):
        border.append(im.getpixel((x, 0))[:3])
        border.append(im.getpixel((x, h - 1))[:3])
    for y in range(0, h, 2):
        border.append(im.getpixel((0, y))[:3])
        border.append(im.getpixel((w - 1, y))[:3])
    bg = _Counter(border).most_common(1)[0][0]

    def nonbg(p):
        return max(abs(p[i] - bg[i]) for i in range(3)) > detect_tol

    touch_top = any(nonbg(im.getpixel((x, 0))[:3]) for x in range(w))
    touch_bot = any(nonbg(im.getpixel((x, h - 1))[:3]) for x in range(w))
    touch_l = any(nonbg(im.getpixel((0, y))[:3]) for y in range(h))
    touch_r = any(nonbg(im.getpixel((w - 1, y))[:3]) for y in range(h))
    pl = pad if touch_l else 0
    pt = pad if touch_top else 0
    pr = pad if touch_r else 0
    pb = pad if touch_bot else 0
    if pl or pt or pr or pb:
        canvas = Image.new("RGBA", (w + pl + pr, h + pt + pb), key + (255,))
        canvas.alpha_composite(im, (pl, pt))
        im = canvas
    stripped = strip_checker_bg(im, bg_color=bg, bg_tol=24)
    if pl or pt or pr or pb:
        W, H = stripped.size
        stripped = stripped.crop((pl, pt, W - pr, H - pb))
        # 垫色会把同一条边上多个碎片连成一块，裁掉垫色后再取最大连通域清碎片
        stripped = keep_largest(stripped)
    return stripped


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


def auto_strip(im, name="", prefer="auto"):
    """自动判断是棋盘格底还是纯色底；prefer 可强制 flood(泛洪)/flat(纯色)"""
    im = im.convert("RGBA")
    if prefer == "flood":
        print("   [泛洪去底] 贴边垫色封口 + 泛洪，保住主体内部浅色")
        return strip_with_pad(im)
    if prefer == "flat":
        print("   [纯色去底] 全局匹配")
        return strip_flat_bg(im)
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


def patch_watermark(im, wm_w=300, wm_h=90):
    """用「水印区域正上方同尺寸的一块」盖掉右下角的 AI 水印文字。

    与 kill_watermark(置透明) 不同，这里不产生透明角，适合整幅背景图：
    背景右下角通常是地面/街景，从上方复制一块能自然延续纹理。
    """
    im = im.convert("RGBA")
    w, h = im.size
    wm_w = min(wm_w, w)
    wm_h = min(wm_h, h // 2)
    src_box = (w - wm_w, h - wm_h * 2, w, h - wm_h)   # 水印正上方一块
    dst_box = (w - wm_w, h - wm_h)                    # 水印所在角
    patch = im.crop(src_box)
    im.paste(patch, dst_box)
    return im


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
    """等比缩放到 max_size；允许 LANCZOS 放大，避免浪费高分辨率源图"""
    im = im.convert("RGBA")
    w, h = im.size
    mw, mh = max_size
    ratio = min(mw / w, mh / h)
    if ratio != 1:
        im = im.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)
    return im


def soften_alpha(im, radius=4):
    """对 alpha 通道做一次模糊，消除抠图留下的锯齿（要放在缩放之后）"""
    from PIL import ImageFilter
    im = im.convert("RGBA")
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    im.putalpha(a)
    return im


def make_body_seg(src_path, dst_path, size=(512, 512), taper=0.62, aspect=0.34, prefer="auto"):
    """
    把矩形蛇身纹理裁成「左粗右细」的梯形条带。
    游戏内按骨骼方向旋转拼接，就用这一张。
      aspect: 条带高度 / 图片宽度 —— 决定蛇的粗细（相对一格的大小）
      taper : 右端高度 / 左端高度  —— 0.62 表示向右收细到 62%
    """
    im = Image.open(src_path).convert("RGBA")
    im = auto_strip(im, prefer=prefer)
    im = autocrop(im)
    # 生图常把鳞片条带画成「3D 缎带」：正面是鳞片、下缘带一条低饱和灰白背面。
    # 背面与主体连通、泛洪吃不掉，会混进中心条带。这里按行统计饱和度/亮度，
    # 只保留真正有鳞片内容的行区间（饱和度高 或 偏暗），裁掉灰白背面。
    w, h = im.size
    px = im.load()
    step = max(1, w // 64)
    rows = []
    for y in range(h):
        sat = lum = n = 0
        for x in range(0, w, step):
            r, g, b, a = px[x, y]
            if a <= 8:
                continue
            sat += max(r, g, b) - min(r, g, b)
            lum += (r + g + b) // 3
            n += 1
        if n == 0:
            rows.append(False)
            continue
        rows.append(sat / n > 15 or lum / n < 180)
    best_s = best_e = -1
    s = -1
    for y in range(h + 1):
        ok = y < h and rows[y]
        if ok and s < 0:
            s = y
        elif not ok and s >= 0:
            if y - s > best_e - best_s:
                best_s, best_e = s, y
            s = -1
    if best_s >= 0 and best_e - best_s >= max(16, h // 8):
        im = im.crop((0, best_s, w, best_e))
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


def _process(src, dst, size, wm, crop, strip):
    """通用单图处理：去底 -> 去水印 -> (裁边) -> 缩放 -> 存盘"""
    if not os.path.exists(src):
        print("[跳过] 源文件不存在:", src)
        return False
    im = Image.open(src)
    im = auto_strip(im, src, prefer=strip)
    if wm:
        im = kill_watermark(im)
    if crop:
        im = autocrop(im)
    im = fit(im, size)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, "PNG", optimize=True)
    print(f"[完成] {os.path.relpath(dst, AST)}  {im.size[0]}x{im.size[1]}  "
          f"{os.path.getsize(dst)//1024}KB")
    return True


def main():
    ok, fail = 0, 0
    for src_rel, dst_rel, size, wm, crop, strip in JOBS:
        src = os.path.join(AST, src_rel.replace("/", os.sep))
        dst = os.path.join(AST, dst_rel.replace("/", os.sep))
        if "backgrounds" in src_rel:
            # 背景是整幅插画，不去底，仅去水印 + 缩放
            if not os.path.exists(src):
                print("[跳过] 源文件不存在:", src_rel)
                fail += 1
                continue
            im = Image.open(src)
            if wm:
                im = kill_watermark(im)
            else:
                im = patch_watermark(im)
            im = fit(im, size)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            im.save(dst, "PNG", optimize=True)
            print(f"[完成] {dst_rel}  {im.size[0]}x{im.size[1]}")
            ok += 1
        else:
            if _process(src, dst, size, wm, crop, strip):
                ok += 1
            else:
                fail += 1

    # 角色三件套：head(不裁边保构图) / tail_tip(裁边) / body_seg(梯形条带)
    # 另：full(全身立绘，供角色选择/详情/抽卡展示，裁边)
    for key, cid in CHARACTERS:
        cdir = os.path.join(AST, "characters", cid)
        up = os.path.join(AST, f"characters/{key}_src_upper.png")
        sc = os.path.join(AST, f"characters/{key}_src_scale.png")
        tl = os.path.join(AST, f"characters/{key}_src_tail.png")
        fl = os.path.join(AST, f"characters/{key}_src_full.png")
        if os.path.exists(fl):
            if _process(fl, os.path.join(cdir, "full.png"), (1024, 1536), True, True, "flood"):
                ok += 1
            else:
                fail += 1
        else:
            print("[跳过] 源文件不存在:", f"{key}_src_full.png")
        if _process(up, os.path.join(cdir, "head.png"), (1024, 1024), True, False, "flood"):
            ok += 1
        else:
            fail += 1
        if _process(tl, os.path.join(cdir, "tail_tip.png"), (512, 512), True, True, "flood"):
            ok += 1
        else:
            fail += 1
        if os.path.exists(sc):
            make_body_seg(sc, os.path.join(cdir, "body_seg.png"), prefer="flood")
            ok += 1
        else:
            print("[跳过] 源文件不存在:", sc)
            fail += 1

    print(f"\n成功 {ok} 个，失败 {fail} 个")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
