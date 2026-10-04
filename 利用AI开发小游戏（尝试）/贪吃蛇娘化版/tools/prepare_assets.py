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
import shutil
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

# 场景敌人贴图表：(源图相对路径, 产物相对路径, 尺寸上限)。
# 每场景 小怪/精英/Boss 各一张，主题贴合场景；源图放 assets/enemies/src/。
ENEMIES = [
    ("enemies/src/campus_mob.png", "enemies/campus_mob.png", (256, 256)),
    ("enemies/src/campus_elite.png", "enemies/campus_elite.png", (384, 384)),
    ("enemies/src/campus_boss.png", "enemies/campus_boss.png", (512, 512)),
    ("enemies/src/neon_mob.png", "enemies/neon_mob.png", (256, 256)),
    ("enemies/src/neon_elite.png", "enemies/neon_elite.png", (384, 384)),
    ("enemies/src/neon_boss.png", "enemies/neon_boss.png", (512, 512)),
    ("enemies/src/deep_mob.png", "enemies/deep_mob.png", (256, 256)),
    ("enemies/src/deep_elite.png", "enemies/deep_elite.png", (384, 384)),
    ("enemies/src/deep_boss.png", "enemies/deep_boss.png", (512, 512)),
    ("enemies/src/realm_mob.png", "enemies/realm_mob.png", (256, 256)),
    ("enemies/src/realm_elite.png", "enemies/realm_elite.png", (384, 384)),
    ("enemies/src/realm_boss.png", "enemies/realm_boss.png", (512, 512)),
]

# 元素普攻弹丸贴图表：(源图相对路径, 产物相对路径)。
# 源图为纯黑底发光体（ImageGen 生成，放 assets/effects/src/），
# 用「亮度键」把黑底转 alpha（发光体天然 additive，无硬边）。
BULLETS = [
    ("effects/src/bullet_sakura.png", "effects/bullet_sakura.png"),
    ("effects/src/bullet_wind.png", "effects/bullet_wind.png"),
    ("effects/src/bullet_water.png", "effects/bullet_water.png"),
    ("effects/src/bullet_fire.png", "effects/bullet_fire.png"),
    ("effects/src/bullet_star.png", "effects/bullet_star.png"),
    ("effects/src/bullet_moon.png", "effects/bullet_moon.png"),
]

# 角色技能特效贴图表：(源图, 产物, 尺寸, 水印框)。
# 源图为棋盘格伪透明底（灰阶带每张不同），走 strip_checker_tex 纹理去底；
# 产物按技能 id 命名，battle 按「角色技能 id」查表加载，缺图回退程序化特效。
# 水印框比默认大：生图分辨率 1024-1792，右下角灰字占位更宽。
SKILL_FX = [
    ("effects/skills/src/mint_blade.png", "effects/skills/mint_blade.png",
     (640, 360), (400, 100)),
    ("effects/skills/src/mint_dash2.png", "effects/skills/mint_dash2.png",
     (640, 360), (400, 100)),
    ("effects/skills/src/mint_gather.png", "effects/skills/mint_gather.png",
     (512, 512), (300, 90)),
    ("effects/skills/src/mint_detonate.png", "effects/skills/mint_detonate.png",
     (512, 512), (300, 90)),
    ("effects/skills/src/mint_channel.png", "effects/skills/mint_channel.png",
     (512, 512), (300, 90)),
]

# 技能释放姿势立绘表：(源图短键, 角色 id, 技能键数)。
# 源图约定 assets/characters/{短键}_src_{cast|hcast}{键}.png（浅色主体+浅色净底+
# 外圈柔光，与线稿屏障抠图画像一致），产物输出到
# assets/characters/{角色 id}/cast_{键}.png（蛇形态）/ cast_human_{键}.png（人形态）。
# battle 按「技能键 + 当前形态」查表做交叉淡入淡出；没图的角色完全不受影响。
CAST_POSES = [
    ("mint", "lamia_mint", 5),
    # 潮汐「切人五技能」双形态姿势：源图同为浅灰净底（亮度实测 178~234），
    # 与潮汐普攻同画像，用 TIDE_INK（ink_lum=174）避免整片底被当线稿屏障。
    ("tide", "lamia_tide", 5, "TIDE_CAST_INK"),
    # 樱落「种花五技能」双形态姿势：源图为亮浅灰净底（边框亮度实测 176~221、
    # 饱和近 0），与樱落普攻同画像，用 TIDE_INK（ink_lum=174）让整片底可泛洪，
    # 深色描边与粉/白/金主体（sat>26 或被线稿隔断）作屏障保住花瓣高光。
    ("sakura", "sakura", 5, "TIDE_INK"),
    # 绯焰「灼烧引爆五技能」双形态姿势：源图为浅灰白净底（#B8BCC0），
    # 与绯焰普攻同画像，用 TIDE_INK 让整片底可泛洪，深红/橙金火焰主体
    # （sat 高）与深色描边作屏障保住火星高光。
    ("flare", "lamia_flare", 5, "TIDE_INK"),
    # 星璃「连星成轨五技能」双形态姿势：源图为浅灰白净底（边框亮度实测约 188），
    # 与樱落/绯焰同画像，用 TIDE_INK 让整片底可泛洪，深紫描边与紫金星光主体
    # （sat 高）作屏障保住星点/星轨高光。
    ("stella", "lamia_stella", 5, "TIDE_INK"),
]
# 姿势图抠图参数：风环白芯与净底几乎同色，颜色泛洪必败，走线稿屏障；
# 风环/刃扇与本体可能不连通，收尾用 keep_big 保块（只清碎斑不删特效）。
CAST_INK = dict(ink_lum=215, ink_sat=26, seal=2,
                rim_passes=2, rim_lum=228, rim_sat=18, keep_frac=0.002)

# 普攻连击姿势立绘表：(源图短键, 角色 id, 段号元组[, 抠图 ink 覆写])。
# 源图约定 assets/characters/{短键}_src_{atk|hatk}{段}.png，产物输出到
# assets/characters/{角色 id}/atk_{段}.png（蛇形态）/ atk_human_{段}.png（人形态）。
# 只配首尾两段（1 挥爪 / 3 收尾）：第 2 段由 battle 镜像第 1 段得到。
# 没图的角色返回空表，普攻仍走弹丸，零影响。
ATK_POSES = [
    ("mint", "lamia_mint", (1, 3)),
    # 潮汐「凝水潮鞭」：1 挥鞭横扫 / 3 重水砸地（第 2 段由 battle 镜像第 1 段）；
    # 源图为浅灰净底 + 大圈水花特效，与薄荷同画像（线稿屏障 + keep_big 保块）。
    ("tide", "lamia_tide", (1, 3), "TIDE_INK"),
    # 樱落「飞樱散华」：1 指尖送单瓣 / 3 袖出花瓣雨（第 2 段由 battle 镜像第 1 段）；
    # 源图同为浅灰白净底（#B8BCC0，亮度约 188），用 TIDE_INK 避免整片底被当屏障。
    ("sakura", "sakura", (1, 3), "TIDE_INK"),
    # 绯焰「焚烬连珠」远程火弹三段：1 单发大口径燃烬 / 3 齐射爆烬（第 2 段 battle 镜像第 1 段）；
    # 源图为浅灰白净底（#B8BCC0，边角亮度实测约 200），与樱落同画像，用 TIDE_INK
    # 让整片底可泛洪，深红/橙金火焰主体（sat 高）与深色描边作屏障保住火弹高光。
    ("flare", "lamia_flare", (1, 3), "TIDE_INK"),
    # 星璃「星尘连辉」远程星尘弹三段：1 尾尖/食指尖弹出单星 / 3 扇形星散
    # （第 2 段 battle 镜像第 1 段）；源图为浅灰白净底（边框亮度实测约 188，
    # atk3 星散光晕贴边到 218），与樱落/绯焰同画像，用 TIDE_INK 让整片底可泛洪，
    # 深紫描边与紫金星光主体（sat 高）作屏障保住星点高光。
    ("stella", "lamia_stella", (1, 3), "TIDE_INK"),
]
# 潮汐源图净底是偏暗的浅灰（边框亮度实测 178~234，CAST_INK 的 ink_lum=215
# 会把整片底误判成线稿屏障导致泛洪进不去）：ink_lum 压到边框最低亮度以下，
# 底色全部可泛洪；深色描边（lum<174）与彩色主体（sat>26）仍是屏障。
TIDE_INK = dict(CAST_INK, ink_lum=174)
# 潮汐 cast_3 源图是纵向渐变灰底，漩涡围出的整片底用单一 bgm 判不掉，
# 开 grad_hole 走逐行边框均值的渐变孔清理（仅释放姿势，普攻姿势不动）。
TIDE_CAST_INK = dict(TIDE_INK, grad_hole=True)


def strip_checker_bg(im, tol=26, min_frac=0.0005, grow=2, bg_color=None, bg_tol=24,
                     bg_set=None):
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
    bg_set 给定时切换为「渐变底」模式：背景是渐变色时单一参考色盖不住全范围，
    改用边框采样色的量化集合（含邻格扩张）判定，连通性仍负责保护主体内部。
    """
    from collections import deque

    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    def is_bg(r, g, b):
        if bg_set is not None:
            return (r // 6, g // 6, b // 6) in bg_set
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

    # 封闭背景孔洞：发丝/肢体围出来的背景小岛不与边界连通，泛洪够不到。
    # 颜色落在背景色带内且面积很小（<2%）的一律当背景清掉；
    # 主体内部的大块浅色（白鳞/白裙）面积超标，自然保留。
    # 仅在显式底色模式（bg_color/bg_set）下启用，棋盘格启发式模式不动。
    if bg_color is not None or bg_set is not None:
        hole_max = int(w * h * 0.02)
        # 每行背景估计色：左右边框均值；边框被主体碰到的行不可靠，置 None
        row_bg = []
        for y in range(h):
            lc, rc = px[0, y][:3], px[w - 1, y][:3]
            if is_bg(*lc) and is_bg(*rc):
                row_bg.append(((lc[0] + rc[0]) / 2, (lc[1] + rc[1]) / 2,
                               (lc[2] + rc[2]) / 2))
            else:
                row_bg.append(None)
        scanned = [[False] * h for _ in range(w)]
        for sy in range(h):
            for sx in range(w):
                if seen[sx][sy] or scanned[sx][sy] \
                        or not is_bg(*px[sx, sy][:3]):
                    continue
                blob = [(sx, sy)]
                scanned[sx][sy] = True
                sr = sg = sb = 0.0
                ssat = 0.0
                sy_sum = 0.0
                cr, cg, cb = px[sx, sy][:3]
                sr, sg, sb = sr + cr, sg + cg, sb + cb
                ssat += float(max(cr, cg, cb) - min(cr, cg, cb))
                sy_sum = float(sy)
                hq = deque([(sx, sy)])
                while hq:
                    x, y = hq.popleft()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if not (0 <= nx < w and 0 <= ny < h) \
                                or seen[nx][ny] or scanned[nx][ny]:
                            continue
                        nr, ng, nb = px[nx, ny][:3]
                        if is_bg(nr, ng, nb):
                            scanned[nx][ny] = True
                            blob.append((nx, ny))
                            hq.append((nx, ny))
                            sr, sg, sb = sr + nr, sg + ng, sb + nb
                            ssat += float(max(nr, ng, nb) - min(nr, ng, nb))
                            sy_sum += ny
                n = len(blob)
                if n:
                    # 背景孔洞 = 灰底被彩色发丝/肢体围住，块均色与环均色反差大；
                    # 主体内部浅色块（白鳞/白纱）与周围主体颜色连续，反差小→保留
                    mr, mg, mb = sr / n, sg / n, sb / n
                    # 环带：blob 外扩 6px 内的主体像素——孔洞边缘贴着抗锯齿
                    # 灰边和宽阴影渐变带，只摸 4 邻永远取不到真发丝色
                    blobset = set(blob)
                    zone = set(blobset)
                    front = blobset
                    for _ in range(6):
                        nxt = set()
                        for x, y in front:
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                                p = (x + dx, y + dy)
                                if 0 <= p[0] < w and 0 <= p[1] < h \
                                        and p not in zone:
                                    zone.add(p)
                                    nxt.add(p)
                        front = nxt
                    rr = rg = rb = rn = 0.0
                    for x, y in zone:
                        if (x, y) in blobset:
                            continue
                        nr, ng, nb = px[x, y][:3]
                        # 环带只认与块均色反差>20 的像素：孔洞边缘的抗锯齿
                        # 灰边跟块色接近，混进来会把反差稀释掉；白发/鳞缝
                        # 靠亮度反差入环，彩发靠色相反差入环
                        if max(abs(nr - mr), abs(ng - mg), abs(nb - mb)) > 20:
                            rr, rg, rb, rn = rr + nr, rg + ng, rb + nb, rn + 1
                    if rn > 0:
                        d = max(abs(mr - rr / rn), abs(mg - rg / rn),
                                abs(mb - rb / rn))
                        clear = n <= hole_max and d > 45
                        if not clear and d > 25:
                            # 大块背景（发后/袖间整片灰底+软投影）：均色贴近
                            # 该行背景色且整体低饱和（灰）才清；主体白块比行
                            # 背景亮得多、或带粉/青色调（饱和超标），双重幸免
                            if ssat / n <= 8:
                                est = row_bg[int(sy_sum / n)]
                                if est is not None:
                                    clear = max(abs(mr - est[0]),
                                                abs(mg - est[1]),
                                                abs(mb - est[2])) <= 12
                        if clear:
                            for x, y in blob:
                                seen[x][y] = True

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


def keep_big(im, min_frac=0.002, alpha_thresh=8):
    """保留所有大于阈值的前景块（keep_largest 只留一块的版本会误删特效）。

    技能释放姿势图里风环/刃扇/漩涡与人物本体可能不连通成一块，
    keep_largest 会把整团技能特效当孤岛删掉；这里只清微小碎斑
    （水印渣/噪点），特效块与本体都保留。
    """
    from collections import deque

    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    comp = [[0] * h for _ in range(w)]
    sizes = [0]
    cid = 0
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
            sizes.append(size)
    keep_min = max(64, int(w * h * min_frac))
    for y in range(h):
        for x in range(w):
            c = comp[x][y]
            if c == 0 or sizes[c] < keep_min:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)
    return im


def fill_pinholes(im, max_area_frac=0.0006, alpha_thresh=8):
    """回填被不透明像素完全包围的微小透明针孔。

    抠图的封闭孔洞清理偶尔会在浅色主体（白发/白鳞）内部误清出几个像素
    的小洞，深色 UI 一垫就变成"黑点"。这里把不接触边框、面积很小的透明
    连通块用环带均色填回不透明；大的真透空（发丝间/盘尾圈）面积超标不动。
    """
    from collections import deque

    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    max_area = max(4, int(w * h * max_area_frac))
    seen = [[False] * h for _ in range(w)]
    for sy in range(h):
        for sx in range(w):
            if seen[sx][sy] or px[sx, sy][3] > alpha_thresh:
                continue
            blob = [(sx, sy)]
            seen[sx][sy] = True
            touch = sx in (0, w - 1) or sy in (0, h - 1)
            dq = deque([(sx, sy)])
            while dq:
                x, y = dq.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and not seen[nx][ny] \
                            and px[nx, ny][3] <= alpha_thresh:
                        seen[nx][ny] = True
                        if nx in (0, w - 1) or ny in (0, h - 1):
                            touch = True
                        blob.append((nx, ny))
                        dq.append((nx, ny))
            if touch or len(blob) > max_area:
                continue
            blobset = set(blob)
            rr = gg = bb = rn = 0
            for x, y in blobset:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h \
                                and (nx, ny) not in blobset \
                                and px[nx, ny][3] > alpha_thresh:
                            cr, cg, cb, _ = px[nx, ny]
                            rr += cr
                            gg += cg
                            bb += cb
                            rn += 1
            if rn == 0:
                continue
            fill = (rr // rn, gg // rn, bb // rn, 255)
            for x, y in blob:
                px[x, y] = fill
    return im


GRAD_TOL = 70     # 渐变带相对主底色的最大偏移；超过则视为贴边主体异色


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
    # 边框量化色种类：均匀底只有 1~几种，渐变底会铺满一条色带。
    # 但若主体贴边（近黑服装/纯白高光碰到边框），其异色会混进采样，
    # 泛洪会从贴边主体灌进内部掏洞。故只保留与主底色接近（渐变带内）
    # 的边框像素构建色带：渐变相对主底色偏移有限（<=GRAD_TOL），
    # 而贴边主体（近黑 ~150 / 纯白 ~90）偏移更大被剔除。
    bgband = [p for p in border
              if max(abs(p[i] - bg[i]) for i in range(3)) <= GRAD_TOL]
    quals = {(p[0] // 6, p[1] // 6, p[2] // 6) for p in bgband}
    bg_set = None
    if len(quals) > 4:
        bg_set = set(quals)
        print(f"   [渐变底] 边框采到 {len(quals)} 种量化色，改用色带集合判背景")

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
    stripped = strip_checker_bg(im, bg_color=bg, bg_tol=24, bg_set=bg_set)
    if pl or pt or pr or pb:
        W, H = stripped.size
        stripped = stripped.crop((pl, pt, W - pr, H - pb))
        # 垫色会把同一条边上多个碎片连成一块，裁掉垫色后再取最大连通域清碎片
        stripped = keep_largest(stripped)
    return stripped


def strip_glow_halo(im, smooth_step=10, min_lum=170, max_depth=0, seed_sat=40,
                    use_mask=False):
    """
    去掉主体外圈「柔光晕」残留（flood 抠不掉的亮色渐变雾）。

    生图常在主体外围画一圈比背景更亮的柔光（月见的月光晕、绯焰的火焰光雾），
    它比背景亮、又比主体暗，单一底色容差盖不住，flood 后会留下一圈灰白雾块。

    做法（边缘感知的平滑泛洪）：只从「与图像边界连通的外背景」出发，沿
    「颜色平滑过渡 + 低饱和」的亮像素向内吃（光晕是低饱和渐变，步长小）；
    碰到描边/高饱和主体（颜色突变 > smooth_step 或饱和超标）就停。
    不从发丝/肢体间的内部透明缝出发，避免咬到缝边的亮色皮肤/衣物。
    max_depth>0 时限制向内吃的层数：用于主体本身也含大片亮白（月见白尾/白裙）
    的图，只削掉贴背景的那圈薄光晕，不深入主体内部。
    use_mask=True 时改用「低饱和+高亮」蒙版贯穿光晕全厚（不看平滑步长）：
    适合光晕本身近中性、而主体轮廓带彩色描边（饱和突变）的图（月见）。
    """
    from collections import deque
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    def lum_of(c):
        return (c[0] + c[1] + c[2]) / 3.0

    def sat_of(c):
        return max(c) - min(c)

    # 外背景：与边界连通的透明区域（内部发丝缝不算）
    outer = [[False] * h for _ in range(w)]
    oq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if px[x, y][3] <= 8 and not outer[x][y]:
                outer[x][y] = True
                oq.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if px[x, y][3] <= 8 and not outer[x][y]:
                outer[x][y] = True
                oq.append((x, y))
    while oq:
        x, y = oq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not outer[nx][ny] \
                    and px[nx, ny][3] <= 8:
                outer[nx][ny] = True
                oq.append((nx, ny))

    halo = [[False] * h for _ in range(w)]
    depth = [[0] * h for _ in range(w)]
    q = deque()
    # 种子：外背景邻接的「亮 + 低饱和」像素即光晕外缘
    for y in range(h):
        for x in range(w):
            if px[x, y][3] > 8 or not outer[x][y]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3] > 8 \
                        and not halo[nx][ny]:
                    c = px[nx, ny][:3]
                    if lum_of(c) >= min_lum and sat_of(c) <= seed_sat:
                        halo[nx][ny] = True
                        depth[nx][ny] = 1
                        q.append((nx, ny))
    # 沿平滑渐变向内扩张
    while q:
        x, y = q.popleft()
        if max_depth and depth[x][y] >= max_depth:
            continue
        pc = px[x, y][:3]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < w and 0 <= ny < h) or halo[nx][ny]:
                continue
            if px[nx, ny][3] <= 8:
                continue
            c = px[nx, ny][:3]
            if lum_of(c) < min_lum or sat_of(c) > seed_sat + 8:
                continue
            if use_mask:
                ok = sat_of(c) <= seed_sat
            else:
                ok = max(abs(c[i] - pc[i]) for i in range(3)) <= smooth_step
            if ok:
                halo[nx][ny] = True
                depth[nx][ny] = depth[x][y] + 1
                q.append((nx, ny))
    n = 0
    for y in range(h):
        for x in range(w):
            if halo[x][y]:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)
                n += 1
    if n:
        print(f"   [光晕清理] 吃掉外圈柔光 {n} px")
    return im


def strip_by_outline(im, ink_lum=215, ink_sat=26, seal=2, rim_passes=2,
                     rim_lum=228, rim_sat=18, hole_tol=4, hole_std=2.0,
                     min_hole_frac=0.0011, min_frac=0.02, keep_frac=0.0,
                     grad_hole=False):
    """
    「线稿屏障」抠图：适合浅色主体 + 浅色净底 + 外圈柔光晕（月见）。

    颜色泛洪在此类图上必败：白裙/白尾与底色几乎同色（容差内），会从描边
    薄弱处漏进主体掏洞；而外圈光晕又比底亮、盖不住留下碎边。唯一可靠的
    分离线是线稿描边。

    做法：
      1. 屏障 = 偏暗(lum<ink_lum) 或 带饱和(sat>ink_sat) 的线稿/彩色区，
         再膨胀 seal 圈封住描边抗锯齿细缝；
      2. 从边框泛洪「非屏障」像素（底色 + 光晕都亮且低饱和），遇屏障停，
         得到外背景；主体白裙/白尾在描边内侧不被触及；
      3. 清封闭真透空孔：与边框底色同色、被主体围住的不透明块（盘尾圈/
         发丝缝露出的底）。主体白裙/白尾的最亮高光与底色几乎同色，故另加
         双守卫：块面积≥min_hole_frac 且亮度平坦(std≤hole_std)——真孔是
         大片纯平底色，主体高光是带渐变/纹理的小岛；清完再向外扩 2 圈
         吃掉孔缘的淡紫阴影环；
      4. 削掉贴屏障残留的亮低饱和光晕 rim（只削与透明区相邻的边缘像素）；
      5. 取最大连通域清孤岛（水印/杂点），前景过少则回退原图。
         keep_frac>0 时改保留所有大于该占比的块（姿势图的风环/刃扇与本体
         可能不连通，只留最大块会删掉技能特效）。
    """
    from collections import deque
    im = im.convert("RGBA")
    out = im.copy()
    w, h = out.size
    px = out.load()

    def lum_of(c):
        return (c[0] + c[1] + c[2]) / 3.0

    def sat_of(c):
        return max(c) - min(c)

    ink = [[False] * h for _ in range(w)]
    for y in range(h):
        for x in range(w):
            c = px[x, y][:3]
            if lum_of(c) < ink_lum or sat_of(c) > ink_sat:
                ink[x][y] = True
    # 膨胀封住描边抗锯齿细缝（否则泛洪从 1px 弱缝漏进白裙）
    bar = [row[:] for row in ink]
    for _ in range(seal):
        nxt = [row[:] for row in bar]
        for y in range(h):
            for x in range(w):
                if bar[x][y]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and bar[nx][ny]:
                        nxt[x][y] = True
                        break
        bar = nxt
    # 从边框泛洪外背景（含光晕），遇屏障停
    outside = [[False] * h for _ in range(w)]
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not bar[x][y] and not outside[x][y]:
                outside[x][y] = True
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not bar[x][y] and not outside[x][y]:
                outside[x][y] = True
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not outside[nx][ny] \
                    and not bar[nx][ny]:
                outside[nx][ny] = True
                q.append((nx, ny))
    for y in range(h):
        for x in range(w):
            if outside[x][y]:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)
    # 清封闭真透空孔：与边框底色同色、被主体围住的不透明块
    br = bg_g = bb = bn = 0
    for x in range(w):
        for y in (0, h - 1):
            c = px[x, y][:3]
            br += c[0]
            bg_g += c[1]
            bb += c[2]
            bn += 1
    for y in range(h):
        for x in (0, w - 1):
            c = px[x, y][:3]
            br += c[0]
            bg_g += c[1]
            bb += c[2]
            bn += 1
    bgm = (br // bn, bg_g // bn, bb // bn)

    def bglike(x, y):
        if px[x, y][3] <= 8:
            return False
        c = px[x, y][:3]
        return (abs(c[0] - bgm[0]) <= hole_tol and abs(c[1] - bgm[1]) <= hole_tol
                and abs(c[2] - bgm[2]) <= hole_tol)

    def rimlike(x, y):
        # 孔缘的淡紫阴影环：比底色略暗但仍亮且低饱和；深色描边/彩色主体不达标
        if px[x, y][3] <= 8:
            return False
        c = px[x, y][:3]
        if max(c) - min(c) > 22:
            return False
        if (c[0] + c[1] + c[2]) / 3.0 < 200:
            return False
        return max(abs(c[i] - bgm[i]) for i in range(3)) <= 18

    seen = [[False] * h for _ in range(w)]
    holes = 0
    for sy in range(h):
        for sx in range(w):
            if seen[sx][sy] or not bglike(sx, sy):
                continue
            blob = [(sx, sy)]
            seen[sx][sy] = True
            dq = deque([(sx, sy)])
            while dq:
                x, y = dq.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and not seen[nx][ny] \
                            and bglike(nx, ny):
                        seen[nx][ny] = True
                        blob.append((nx, ny))
                        dq.append((nx, ny))
            if len(blob) > w * h * 0.25 or len(blob) < w * h * min_hole_frac:
                continue
            lums = [(px[x, y][0] + px[x, y][1] + px[x, y][2]) / 3.0 for x, y in blob]
            m = sum(lums) / len(lums)
            std = (sum((v - m) ** 2 for v in lums) / len(lums)) ** 0.5
            if std > hole_std:
                continue
            # 孔缘扩张：吃掉孔边一圈淡紫阴影环（深色描边/彩色主体不达标会停）
            blobset = set(blob)
            frontier = blob
            for _ in range(2):
                nxt = []
                for x, y in frontier:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h \
                                and (nx, ny) not in blobset and rimlike(nx, ny):
                            blobset.add((nx, ny))
                            nxt.append((nx, ny))
                if not nxt:
                    break
                frontier = nxt
            for x, y in blobset:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)
            holes += len(blobset)
    if holes:
        print(f"   [透空孔] 清掉封闭底色块 {holes} px")
    # 渐变底封闭大孔：单一 bgm 盖不住纵向渐变（潮汐 cast_3 漩涡围出的整片
    # 灰底），改用「blob 覆盖行的边框均值」逐行估计背景。面积/平坦/行匹配
    # 三重守卫：只吃 4%~30% 的中性灰平坦大块，主体彩发/白沫/鳞尾不达标幸免。
    if grad_hole:
        row_bg = []
        for y in range(h):
            lc, rc = px[0, y][:3], px[w - 1, y][:3]
            row_bg.append(((lc[0] + rc[0]) / 2.0, (lc[1] + rc[1]) / 2.0,
                           (lc[2] + rc[2]) / 2.0))

        def grayish(x, y):
            if px[x, y][3] <= 8:
                return False
            c = px[x, y][:3]
            if max(c) - min(c) > 16:
                return False
            return 130 <= (c[0] + c[1] + c[2]) / 3.0 <= 215

        seen2 = [[False] * h for _ in range(w)]
        cleared = 0
        for sy in range(h):
            for sx in range(w):
                if seen2[sx][sy] or not grayish(sx, sy):
                    continue
                blob = [(sx, sy)]
                seen2[sx][sy] = True
                sr = sg = sb = 0.0
                slum = []
                dq = deque([(sx, sy)])
                while dq:
                    x, y = dq.popleft()
                    c = px[x, y][:3]
                    sr += c[0]
                    sg += c[1]
                    sb += c[2]
                    slum.append((c[0] + c[1] + c[2]) / 3.0)
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and not seen2[nx][ny] \
                                and grayish(nx, ny):
                            seen2[nx][ny] = True
                            blob.append((nx, ny))
                            dq.append((nx, ny))
                n = len(blob)
                # 大块=漩涡围出的整片底；小块=发丝/水臂夹出的底口袋。
                # 小块用更紧的行匹配容差，防误吃主体上的中性阴影像素。
                if not (w * h * 0.001 <= n <= w * h * 0.30):
                    continue
                m = sum(slum) / n
                std = (sum((v - m) ** 2 for v in slum) / n) ** 0.5
                # 渐变底本身带纵向亮度坡度，平坦度只作宽松上限（挡纹理主体），
                # 真正区分灰底/主体靠下面的「行背景均值匹配」。
                if std > 40:
                    continue
                ys = [yy for _xx, yy in blob]
                y0, y1 = min(ys), max(ys)
                er = eg = eb = 0.0
                for y in range(y0, y1 + 1):
                    er += row_bg[y][0]
                    eg += row_bg[y][1]
                    eb += row_bg[y][2]
                cnt = y1 - y0 + 1
                est = (er / cnt, eg / cnt, eb / cnt)
                tol = 18 if n >= w * h * 0.04 else 10
                if max(abs(sr / n - est[0]), abs(sg / n - est[1]),
                       abs(sb / n - est[2])) <= tol:
                    for x, y in blob:
                        r, g, b, _ = px[x, y]
                        px[x, y] = (r, g, b, 0)
                    cleared += n
        if cleared:
            print(f"   [渐变孔] 清掉封闭灰底 {cleared} px")
    # 削掉贴屏障残留的亮低饱和光晕 rim（仅与透明区相邻的边缘像素）
    for _ in range(rim_passes):
        rim = []
        for y in range(h):
            for x in range(w):
                if px[x, y][3] <= 8:
                    continue
                c = px[x, y][:3]
                if lum_of(c) < rim_lum or sat_of(c) > rim_sat:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3] <= 8:
                        rim.append((x, y))
                        break
        if not rim:
            break
        for x, y in rim:
            r, g, b, _ = px[x, y]
            px[x, y] = (r, g, b, 0)
    out = keep_big(out, keep_frac) if keep_frac > 0 else keep_largest(out)
    hist = out.getchannel("A").histogram()
    frac = sum(hist[9:]) / max(1, sum(hist))
    if frac < min_frac:
        print(f"   [警告] 描边抠图前景只占 {frac:.2%}，回退原图")
        return im
    print(f"   [描边抠图] 前景 {frac:.1%}（线稿屏障+光晕rim清理）")
    return out


def strip_dark_bg(im, lum=100, grow=2, min_frac=0.0005):
    """
    深色底（夜空/暗底）抠图：亮度低于阈值的视为背景，从边缘泛洪。

    用于「浅色主体 + 深色底」的立绘（如月见重生成版）：主体全亮、
    背景全暗，用亮度判背景比用单一底色更稳，能连暗色光晕一起吃掉；
    主体内部的深色描边因不与边界连通而被最大连通域保留。
    """
    from collections import deque
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    def is_bg(r, g, b):
        # 深色且偏蓝（夜空/冷光晕）才算背景；主体内部的暗部阴影多为
        # 中性黑（r≈g≈b），不算背景，避免把脖子/下颌阴影抠成洞
        return (r + g + b) / 3.0 < lum and (b - r) > 10

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
    # 膨胀吃掉边缘暗边
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
    # 只清掉微小孤岛（夜空星点），保留所有较大的前景块：
    # 立绘内部暗部阴影可能把主体切成多块（头/躯干），不能只留最大块
    comp = [[0] * h for _ in range(w)]
    sizes = [0]
    cid = 0
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
            sizes.append(size)
    keep_min = max(64, int(w * h * 0.002))
    kept = 0
    for cidx in range(1, cid + 1):
        if sizes[cidx] >= keep_min:
            kept += sizes[cidx]
    for y in range(h):
        for x in range(w):
            c = comp[x][y]
            if grown[x][y] or c == 0 or sizes[c] < keep_min:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)
    if kept / (w * h) < min_frac:
        print(f"   [警告] 深色底抠图前景只占 {kept / (w * h):.2%}")
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


def auto_strip(im, name="", prefer="auto"):
    """自动判断是棋盘格底还是纯色底；prefer 可强制 flood(泛洪)/flat(纯色)"""
    im = im.convert("RGBA")
    if prefer == "none":
        return im
    if prefer == "flood":
        print("   [泛洪去底] 贴边垫色封口 + 泛洪，保住主体内部浅色")
        return strip_with_pad(im)
    if prefer == "lum":
        print("   [亮度去底] 深色底泛洪，连暗色光晕一起吃掉")
        return strip_dark_bg(im)
    if prefer == "flat":
        print("   [纯色去底] 全局匹配")
        return strip_flat_bg(im)
    if prefer == "checkerfx":
        return strip_checker_tex(im)
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


def strip_checker_tex(im, sat_max=14, win_sat_max=34, grow=3):
    """
    棋盘格底「特效贴图」去底：靠棋盘格的「振荡性」分离，而不是靠颜色。

    AI 生图的棋盘格底灰阶带每张都不一样（亮带 211-253 / 中带 145-174 /
    暗带 116-150），亮带甚至与风体白色几乎同色；而且方块边长漂移、
    边缘模糊（软棋盘），固定位移的相位门也靠不住。白芯的赛璐璐云染
    色阶差又与棋盘格两色调差同量级——颜色/极差/相位启发式都会误切。
    棋盘格独有的特征是「双相振荡」：像素亮度对局部均值(25窗)的偏差
    dev ≈ ±半振幅，且 ±16px 内必存在反相（dev 异号同量级）邻居；
    色阶边缘单调（dev 只一侧超标）、白芯平滑（dev 不超标）、薄风丝
    内 dev 超标但邻域只有同相/弱反相邻居——全部自然幸免。再叠低饱和
    + 窗口饱和上限 + 底色亮度带三道门，逐像素判定、不依赖连通性——
    风隙间被围住的棋盘格孔洞一并清掉；也不取最大连通域，孤立飞叶保留。

    残留抗锯齿灰边靠 grow 外扩吃掉（只扩进低饱和且亮度在底色带内的像素）。
    """
    from PIL import ImageFilter

    import numpy as np
    im = im.convert("RGBA")
    rgb = np.array(im.convert("RGB")).astype(int)
    sat = (rgb.max(axis=2) - rgb.min(axis=2)).astype(np.uint8)
    lum = np.array(im.convert("L")).astype(int)

    # 边框环：估周期 s 与底色亮度带
    ring = np.concatenate([
        lum[:4, :].ravel(), lum[-4:, :].ravel(),
        lum[:, :4].ravel(), lum[:, -4:].ravel()])
    ring_sat = np.concatenate([
        sat[:4, :].ravel(), sat[-4:, :].ravel(),
        sat[:, :4].ravel(), sat[:, -4:].ravel()])
    ring = ring[ring_sat <= sat_max]
    # 棋盘两色调 = 边框亮度直方图最高的两个峰（风体白尖碰边框也只占一个峰）
    hist, _ = np.histogram(ring, bins=32, range=(0, 256))
    order = np.argsort(hist)[::-1]
    p1 = int(order[0]) * 8 + 4
    p2 = -1
    for o in order[1:]:
        c = int(o) * 8 + 4
        if abs(c - p1) >= 10:
            p2 = c
            break
    if p2 < 0 or hist[order[1]] < max(4, hist[order[0]] // 20):
        p2 = int(np.percentile(ring, 10))
        p1 = int(np.percentile(ring, 90))
    lo_tone, hi_tone = min(p1, p2), max(p1, p2)
    amp = hi_tone - lo_tone
    band_lo, band_hi = lo_tone - 22, hi_tone + 22
    thr = max(6, int(amp * 0.28))

    # 双相振荡门：dev 超标 且 ±16 内有反相同量级邻居（行、列各一）
    mean = np.array(im.convert("L").filter(ImageFilter.BoxBlur(12))).astype(int)
    dev = lum - mean
    # 行/列方向分别取反相邻居（用 1D 滚动窗避免对角混入）
    opp_row_lo = np.full_like(dev, 128)
    opp_row_hi = np.full_like(dev, -128)
    opp_col_lo = np.full_like(dev, 128)
    opp_col_hi = np.full_like(dev, -128)
    for d in range(8, 17):
        opp_row_lo = np.minimum(opp_row_lo, np.roll(dev, d, axis=1))
        opp_row_lo = np.minimum(opp_row_lo, np.roll(dev, -d, axis=1))
        opp_row_hi = np.maximum(opp_row_hi, np.roll(dev, d, axis=1))
        opp_row_hi = np.maximum(opp_row_hi, np.roll(dev, -d, axis=1))
        opp_col_lo = np.minimum(opp_col_lo, np.roll(dev, d, axis=0))
        opp_col_lo = np.minimum(opp_col_lo, np.roll(dev, -d, axis=0))
        opp_col_hi = np.maximum(opp_col_hi, np.roll(dev, d, axis=0))
        opp_col_hi = np.maximum(opp_col_hi, np.roll(dev, -d, axis=0))
    pos = dev >= thr          # 亮相像素：需要反相暗邻居
    neg = dev <= -thr         # 暗相像素：需要反相亮邻居
    opp_pos = (opp_row_lo <= -thr) & (opp_col_lo <= -thr)
    opp_neg = (opp_row_hi >= thr) & (opp_col_hi >= thr)
    osc = (pos & opp_pos) | (neg & opp_neg)

    # 阻尼棋盘门：光晕罩在棋盘格上会把振幅压到主门阈值以下、亮度抬到
    # 亮色调之上。特征：低饱和 + 局部极差中等 + ±16 内零交叉 ≥2 次
    # （色阶边缘只交叉 1 次、白芯平滑 0 次，自然幸免）。
    lrng = np.array(im.convert("L").filter(ImageFilter.MaxFilter(33))).astype(int) \
        - np.array(im.convert("L").filter(ImageFilter.MinFilter(33))).astype(int)
    sg = np.where(dev > 2, 1, np.where(dev < -2, -1, 0)).astype(np.int8)

    def win_count(ch, half=16):
        # 积分图求 ±half 窗口内符号零交叉次数
        p = np.pad(ch.astype(np.int32), half + 1, mode="constant")
        ii = np.cumsum(np.cumsum(p, axis=0), axis=1)
        h, w = ch.shape
        return (ii[2 * half + 1:2 * half + 1 + h, 2 * half + 1:2 * half + 1 + w]
                - ii[0:h, 2 * half + 1:2 * half + 1 + w]
                - ii[2 * half + 1:2 * half + 1 + h, 0:w]
                + ii[0:h, 0:w])

    cr = win_count((sg * np.roll(sg, 1, axis=1)) < 0)
    cc = win_count((sg * np.roll(sg, 1, axis=0)) < 0)
    # 只对暗/中带棋盘启用：亮带图的光晕罩棋很弱，主门已够；
    # 且白芯(250)远高于 hi_tone+46，上限门把色阶误切挡在外面。
    damped = (hi_tone < 220) & (sat <= sat_max) \
        & (lrng >= 7) & (lrng <= 45) \
        & (lum >= hi_tone - 6) & (lum <= hi_tone + 46) \
        & ((cr >= 2) | (cc >= 2))
    wsat = np.array(Image.fromarray(sat).filter(
        ImageFilter.MaxFilter(25))).astype(int)
    bg = (osc | damped) & (sat <= sat_max) & (wsat <= win_sat_max) \
        & (lum >= band_lo) & (lum <= band_hi + 70)
    # 外扩：吃棋盘格与主体交界的抗锯齿灰边（低饱和、亮度在底色带内）
    for _ in range(grow):
        nb = bg.copy()
        for ax, sh in ((0, 1), (0, -1), (1, 1), (1, -1)):
            nb |= np.roll(bg, sh, axis=ax)
        edge = nb & ~bg & (sat <= win_sat_max + 8) \
            & (lum >= band_lo) & (lum <= band_hi)
        bg |= edge
    a = np.array(im.getchannel("A"))
    a[bg] = 0
    # 孤岛碎斑清理：不透明且 5x5 内不透明邻居极少的像素（残留棋盘点）；
    # 飞叶/风丝是实块或连续线，邻居计数高，不受影响。两遍吃掉小簇。
    def _speck_mask(alpha):
        op = alpha > 0
        p = np.pad(op.astype(np.int32), 2, mode="constant")
        ii = np.zeros((op.shape[0] + 5, op.shape[1] + 5), dtype=np.int64)
        ii[1:, 1:] = np.cumsum(np.cumsum(p, axis=0), axis=1)
        h, w = op.shape
        cnt = ii[5:5 + h, 5:5 + w] - ii[0:h, 5:5 + w] \
            - ii[5:5 + h, 0:w] + ii[0:h, 0:w]
        return op & (cnt <= 10)
    for _ in range(2):
        sp = _speck_mask(a)
        if not sp.any():
            break
        a[sp] = 0
    im.putalpha(Image.fromarray(a))
    n = int((a == 0).sum())
    print(f"   [棋盘格纹理去底] 亮度带[{band_lo},{band_hi}] 振幅{amp} 阈{thr} "
          f"清掉 {n} px ({n / (im.width * im.height):.1%})")
    return im


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
    # 全幅纹理（无净底）会被泛洪/亮度键吃空：前景过少时回退用原图
    hist = im.getchannel("A").histogram()
    opaque = sum(hist[9:]) / max(1, sum(hist))
    if opaque < 0.05:
        print("   [回退] 去底后前景过少（全幅纹理），改用原图")
        im = Image.open(src_path).convert("RGBA")
    im = fill_pinholes(im)
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


def make_bullet(src_path, dst_path, size=(160, 160), wm_box=(340, 120)):
    """
    把纯黑底发光弹丸源图转成透明 PNG。

    发光体在纯黑底上，用「亮度键」最干净：alpha = max(r,g,b)，
    黑底自然变全透明、光晕按亮度渐变，不会留下抠图硬边/灰雾。
    先抹掉右下角水印灰字（否则 keying 后会残留半透明文字）。
    """
    if not os.path.exists(src_path):
        print("[跳过] 源文件不存在:", src_path)
        return False
    im = Image.open(src_path).convert("RGBA")
    w, h = im.size
    px = im.load()
    # 抹水印：右下角一块置黑
    for y in range(max(0, h - wm_box[1]), h):
        for x in range(max(0, w - wm_box[0]), w):
            px[x, y] = (0, 0, 0, 255)
    # 亮度键：黑 -> 透明，光晕按亮度渐变
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            a = max(r, g, b)
            px[x, y] = (r, g, b, a)
    im = autocrop(im, pad=4, alpha_thresh=6)
    im = fit(im, size)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    im.save(dst_path, "PNG", optimize=True)
    print(f"[完成] bullet {os.path.relpath(dst_path, AST)}  "
          f"{im.size[0]}x{im.size[1]}  {os.path.getsize(dst_path)//1024}KB")
    return True


def _keep_largest_blob(im, thresh=8):
    """只保留 alpha 最大连通域。

    rembg 偶尔把背景道具（星璃场景里的望远镜）或零星碎斑也判成前景，
    这些块与人物主体不连通；按连通域面积取最大者即可干净剔除，
    主体（含与发丝/飘带相连的月环等）始终是一整块不受影响。
    """
    import numpy as np
    from scipy import ndimage
    a = np.asarray(im.getchannel("A"))
    mask = a > thresh
    lab, n = ndimage.label(mask)
    if n <= 1:
        return im
    sizes = ndimage.sum(mask, lab, index=np.arange(1, n + 1))
    keep = int(np.argmax(sizes)) + 1
    drop = (lab != keep) & mask
    if not drop.any():
        return im
    px = np.array(im)  # np.array 默认拷贝，可写；asarray 会是只读视图
    px[drop, 3] = 0
    print(f"   [连通域] 剔除 {n - 1} 块游离前景 共 {int(drop.sum())} px")
    return Image.fromarray(px, "RGBA")


def _clean_matte(im):
    """rembg 蒙版残留清理：把三类「不该有」的半透层置全透。

    ① 地面阴影/亮灰边：低饱和+偏亮+alpha<252（源图垫底阴影、被误判成
       前景的亮灰背景块，alpha 常到 240 左右，垫深色场景就是白边）；
    ② 暗烟雾：低饱和+偏暗+alpha<200（绯焰源图右侧的灰烟）；
    ③ 保留高饱和彩色光雾（火焰须/花瓣）与不透明主体（alpha>=252），
       主体抗锯齿内圈不受影响，只削最外一圈混底色的边。
    """
    import numpy as np
    px = np.array(im)  # 拷贝可写
    rgb = px[..., :3].astype(np.int32)
    a = px[..., 3].astype(np.int32)
    lum = rgb.sum(axis=2) // 3
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    drop = (a > 8) & (a < 252) & (sat < 45) & (lum > 140)
    drop |= (a > 8) & (a < 200) & (sat < 70) & (lum <= 140)
    # ③ 中性灰半透（盘圈透空孔里的垫影薄膜、残余灰边）：饱和度极低
    #    的半透像素只可能是混了灰底/阴影的边缘，彩色光雾不会这么灰
    drop |= (a > 8) & (a < 252) & (sat < 30)
    if drop.any():
        px[drop, 3] = 0
    print(f"   [matte清理] 置透半透残留 {int(drop.sum())} px")
    im = Image.fromarray(px, "RGBA")
    return _drop_hole_films(im)


def _drop_hole_films(im, min_area=200):
    """清盘圈透空孔里的不透明阴影残膜。

    盘尾围出的透空孔里，rembg 常把源图垫影判成不透明前景（alpha=255
    的灰白薄片），半透规则切不到。判定：低饱和高亮的不透明连通块，
    若它邻接的全透区域都是「不碰边框的封闭孔」，即孔中残膜，置透；
    主体白纱/白鳞虽同色，但邻接外背景（碰边框的全透巨块），不误伤。
    """
    import numpy as np
    from scipy import ndimage
    px = np.array(im)
    rgb = px[..., :3].astype(np.int32)
    a = px[..., 3].astype(np.int32)
    lum = rgb.sum(axis=2) // 3
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    zero = a <= 8
    gray = (a > 8) & (sat < 35) & (lum > 150)
    lab_z, nz = ndimage.label(zero)
    if nz == 0:
        return im
    touch = np.zeros(nz + 1, dtype=bool)
    for edge in (lab_z[0, :], lab_z[-1, :], lab_z[:, 0], lab_z[:, -1]):
        touch[np.unique(edge)] = True
    lab_g, ng = ndimage.label(gray)
    if ng == 0:
        return im
    # 每个灰亮块邻接哪些全透连通域
    ring = ndimage.grey_dilation(lab_g, size=(3, 3))
    killed = 0
    for i in range(1, ng + 1):
        comp = lab_g == i
        if comp.sum() < min_area:
            continue
        nbr = np.unique(ring[comp & zero])
        nbr = nbr[nbr > 0]
        if len(nbr) == 0 or touch[nbr].any():
            continue    # 邻接外背景 = 主体白纱/白鳞，保留
        killed += int(comp.sum())
        px[comp, 3] = 0
    if killed:
        print(f"   [孔内残膜] 置透 {killed} px")
    return Image.fromarray(px, "RGBA")


def _erase_polys(im, polys):
    """按归一化多边形把 alpha 置 0：擦掉源图自带的「出画尾桩/卷尾」。

    生图常把尾尖画出画布外（直切一刀的鳞条桩、右侧卷尾），抠图会原样
    保留，垫场景背景就像多出一条小尾巴。坐标为「首次 fit 后画布」的
    宽高比例（目检合成图直接量），擦完再 autocrop+fit 重新居中，
    尾桩占的死边不会把主体挤偏。
    """
    from PIL import ImageDraw
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    for poly in polys:
        d.polygon([(fx * w, fy * h) for fx, fy in poly], fill=255)
    import numpy as np
    px = np.array(im)
    erase = np.asarray(mask) > 0
    px[erase, 3] = 0
    print(f"   [擦尾桩] 置透 {int(erase.sum())} px / {len(polys)} 块多边形")
    return Image.fromarray(px, "RGBA")


def _process_rembg(src, dst, size, keep_blob=True, clean=False, polys=None,
                   polys_post=None, final_blob=False):
    """rembg 动漫抠图通用入口 -> 裁边缩放存盘。

    isnet-anime 对动漫人物的蒙版干净，连半透明飘带/火焰光雾的半透边
    都能保住，比颜色泛洪更适合这两类源图：人形态是全彩专属场景插画
    （泛洪/线稿无从下手）；蛇形态灰底立绘泛洪会留灰边、吃掉光雾。
    RGB 取源图、alpha 取 rembg：rembg 会把背景 RGB 清零，直接拿它的
    RGBA 会让透边在半透处混进黑色（缩放/回填后成黑缝黑边）。
    clean=True 时清理阴影/灰边/烟雾半透残留；polys 擦源图自带尾桩。
    keep_blob=True 时只留最大连通域（人形态需剔除背景道具如望远镜）；
    蛇形态灰底无杂物、且火焰/月环等特效可能与主体不连通，传 False 保留。
    polys_post 在最终 fit 之后（不再裁边）按成品坐标补擦贴边残桩；
    final_blob 在成品末尾再保留一次最大连通域，清掉被 polys 切断后
    悬空的孤立残块（火须/碎屑），不伤与主体相连的线圈。
    抠图只发生在工具期，游戏运行不依赖 rembg。
    """
    if not os.path.exists(src):
        print("[跳过] 源文件不存在:", src)
        return False
    im = Image.open(src).convert("RGBA")
    cut = strip_anime(im)
    im.putalpha(cut.getchannel("A"))
    if clean:
        im = _clean_matte(im)
    if keep_blob:
        im = _keep_largest_blob(im)
    hist = im.getchannel("A").histogram()
    frac = sum(hist[9:]) / max(1, sum(hist))
    if frac < 0.02:
        print(f"   [警告] 抠图前景只占 {frac:.2%}，保留旧版不覆盖")
        return False
    im = autocrop(im)
    im = fit(im, size)
    if polys:
        # 尾桩多边形在首次 fit 画布坐标上擦（目检直接量），擦完重新裁边居中
        im = _erase_polys(im, polys)
        im = autocrop(im)
        im = fit(im, size)
    im = fill_pinholes(im)
    if polys_post:
        # 成品坐标补擦贴边残桩（不再裁边，坐标与目检成品图 1:1）
        im = _erase_polys(im, polys_post)
    if final_blob:
        im = _keep_largest_blob(im)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, "PNG", optimize=True)
    print(f"[完成] {os.path.relpath(dst, AST)}  {im.size[0]}x{im.size[1]}  "
          f"{os.path.getsize(dst)//1024}KB")
    return True


_REMBG_SESSION = None


def strip_anime(im):
    """rembg isnet-anime 抠图；会话级缓存模型，六张图只加载一次。"""
    global _REMBG_SESSION
    from rembg import new_session, remove
    if _REMBG_SESSION is None:
        print("   [rembg] 加载 isnet-anime 模型…")
        _REMBG_SESSION = new_session("isnet-anime")
    return remove(im, session=_REMBG_SESSION)


def _process(src, dst, size, wm, crop, strip, halo=False, ink=None):
    """通用单图处理：去底 -> (光晕清理) -> 去水印 -> (裁边) -> 缩放 -> 存盘"""
    if not os.path.exists(src):
        print("[跳过] 源文件不存在:", src)
        return False
    im = Image.open(src)
    if ink:
        im = strip_by_outline(im, **ink)
    else:
        im = auto_strip(im, src, prefer=strip)
        if halo:
            im = strip_glow_halo(im, max_depth=halo[0], seed_sat=halo[1],
                                 min_lum=halo[2], use_mask=halo[3])
    if wm:
        im = kill_watermark(im, *(wm if isinstance(wm, tuple) else ()))
    if crop:
        im = autocrop(im)
    im = fit(im, size)
    # 针孔回填放在缩放之后：LANCZOS 缩放会在封闭缝隙里重新振铃出微小低 alpha 点，
    # 若先填后缩，存盘图仍会残留黑点。
    im = fill_pinholes(im)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, "PNG", optimize=True)
    print(f"[完成] {os.path.relpath(dst, AST)}  {im.size[0]}x{im.size[1]}  "
          f"{os.path.getsize(dst)//1024}KB")
    return True


def main():
    # 可选命令行参数：只跑某一节（jobs/chars/enemies/bullets/fx/poses），
    # 调参迭代时避免整表重跑（线稿屏障抠图是纯 Python BFS，全表很慢）。
    only = sys.argv[1] if len(sys.argv) > 1 else None

    def want(tag):
        return only is None or only == tag

    ok, fail = 0, 0
    for src_rel, dst_rel, size, wm, crop, strip in (JOBS if want("jobs") else []):
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
    # 绯焰源图带外圈火焰光雾，flood 抠不净，需额外光晕清理；
    # 值=(max_depth, seed_sat, min_lum, use_mask)：火雾暖色、主体高饱和 → 平滑步长泛洪不限深
    HALO_KEYS = {"flare": (0, 40, 170, False)}
    # 月见是「白主体+浅薰衣草净底+外圈月光晕」：白裙/白尾与底色几乎同色，
    # 颜色泛洪会从描边薄弱处漏进白裙掏洞、又盖不住外圈光晕碎边，
    # 改用线稿屏障抠图（只作用于立绘 full/head，鳞条/尾尖仍走泛洪）
    INK_KEYS = {"luna": dict(ink_lum=215, ink_sat=26, seal=2,
                             rim_passes=2, rim_lum=228, rim_sat=18)}
    # 蛇形态灰底立绘改走 rembg 的角色：泛洪在这些图上留灰边/吃光雾
    # （薄荷飘带、绯焰火雾、潮汐贴边尾盘、月见月环、樱落发丝/花瓣、
    # 星璃垫底阴影泛洪吃不净），六角色统一 rembg + matte 清理
    SNAKE_REMBG_KEYS = {"mint", "tide", "flare", "luna", "sakura", "stella"}
    # matte 残留清理开关：仅源图带垫底阴影/灰烟的角色需要；
    # 薄荷/潮汐/月见的半透飘带月环已验收，不动避免回归
    MATTE_CLEAN_KEYS = {"sakura", "stella", "flare"}
    # 成品末尾再保留最大连通域：清掉被 ERASE_POLYS 切断后悬空的孤立残块
    # （绯焰右侧火须/碎屑、星璃悬浮碎膜）。仅用于确认无合法悬浮部件的角色。
    FINAL_BLOB_KEYS = {"flare", "stella"}
    # 成品空间（最终 fit 后、不再裁边）补擦贴边残桩：坐标按目检成品图实测。
    # 绯焰右下角直切尾桩残楔（贴线圈右下外缘）。
    ERASE_POLYS_POST = {
        "flare": [
            [(0.880, 0.938), (1.0, 0.938), (1.0, 1.0), (0.880, 1.0)],
        ],
        "stella": [
            [(0.882, 0.958), (0.952, 0.958), (0.952, 1.0), (0.882, 1.0)],
        ],
    }
    # 源图自带「出画尾桩/卷尾」的角色：归一化多边形擦除
    # （坐标 = 首次 fit 画布比例，按目检合成图实测标定）。
    # 绯焰=右侧卷尾+右下直切尾桩；星璃=右下直切尾桩；樱落=右下尾条残片
    ERASE_POLYS = {
        "flare": [
            [(0.765, 0.630), (0.970, 0.630), (0.970, 0.815), (0.920, 0.800),
             (0.880, 0.760), (0.845, 0.720), (0.800, 0.705), (0.765, 0.680)],
            [(0.940, 0.940), (1.0, 0.940), (1.0, 1.0), (0.860, 1.0),
             (0.900, 0.975), (0.930, 0.955)],
        ],
        "stella": [
            [(0.930, 0.895), (1.0, 0.895), (1.0, 1.0), (0.850, 1.0),
             (0.900, 0.960), (0.925, 0.925)],
        ],
        "sakura": [
            [(0.930, 0.945), (1.0, 0.945), (1.0, 1.0), (0.840, 1.0),
             (0.890, 0.970)],
        ],
    }
    for key, cid in (CHARACTERS if want("chars") else []):
        cdir = os.path.join(AST, "characters", cid)
        up = os.path.join(AST, f"characters/{key}_src_upper.png")
        sc = os.path.join(AST, f"characters/{key}_src_scale.png")
        tl = os.path.join(AST, f"characters/{key}_src_tail.png")
        fl = os.path.join(AST, f"characters/{key}_src_full.png")
        halo = HALO_KEYS.get(key, 0)
        ink = INK_KEYS.get(key)
        # 立绘源图为「浅色主体+浅色净底」，统一用泛洪（贴边垫色封口）保住主体白色
        pf = "flood"
        if os.path.exists(fl):
            # 新立绘源图无 AI 水印：wm=False，避免误抹右下角盘尾的透明角。
            if key in SNAKE_REMBG_KEYS:
                # 灰底立绘泛洪留灰边/吃光雾，改走 rembg；缺 rembg 或失败回退泛洪
                try:
                    done = _process_rembg(fl, os.path.join(cdir, "full.png"),
                                          (1024, 1536), keep_blob=False,
                                          clean=key in MATTE_CLEAN_KEYS,
                                          polys=ERASE_POLYS.get(key),
                                          polys_post=ERASE_POLYS_POST.get(key),
                                          final_blob=key in FINAL_BLOB_KEYS)
                except ImportError:
                    done = False
                if not done:
                    done = _process(fl, os.path.join(cdir, "full.png"),
                                    (1024, 1536), False, True, pf, halo, None)
            else:
                # 兜底：不在 SNAKE_REMBG_KEYS 的角色仍走泛洪原路径
                done = _process(fl, os.path.join(cdir, "full.png"),
                                (1024, 1536), False, True, pf, halo, None)
            if done:
                ok += 1
            else:
                fail += 1
        else:
            print("[跳过] 源文件不存在:", f"{key}_src_full.png")
        # 人形态全身立绘（彩蛋形态：选角/详情展示 + 战斗内全身精灵）。
        # 新人形态源图是全彩专属场景带背景原图，泛洪/线稿都无从下手，
        # 改走 rembg 动漫抠图；同一张源图另原样拷贝为专属场景 human_scene.png。
        hm = os.path.join(AST, f"characters/{key}_src_human_scene.png")
        if os.path.exists(hm):
            try:
                done = _process_rembg(hm, os.path.join(cdir, "full_human.png"),
                                      (1024, 1536))
            except ImportError:
                done = False
                print("[警告] 缺 rembg，跳过人形态抠图（保留现有 full_human.png）")
            if done:
                ok += 1
            else:
                fail += 1
            # 专属场景：带背景原图原样欣赏（不抠图不缩放，零画质损失）
            dst_hs = os.path.join(cdir, "human_scene.png")
            shutil.copyfile(hm, dst_hs)
            print(f"[完成] {os.path.relpath(dst_hs, AST)} 原图拷贝  "
                  f"{os.path.getsize(dst_hs)//1024}KB")
        else:
            print("[跳过] 源文件不存在:", f"{key}_src_human_scene.png")
        if _process(up, os.path.join(cdir, "head.png"), (1024, 1024), True, False, pf,
                    0 if ink else halo, ink):
            ok += 1
        else:
            fail += 1
        if _process(tl, os.path.join(cdir, "tail_tip.png"), (512, 512), True, True, "flood"):
            ok += 1
        else:
            fail += 1
        if os.path.exists(sc):
            make_body_seg(sc, os.path.join(cdir, "body_seg.png"),
                          prefer="flood")
            ok += 1
        else:
            print("[跳过] 源文件不存在:", sc)
            fail += 1

    # 场景敌人贴图：小怪/精英/Boss 每场景各一张（去底+填针孔+裁边+缩放）
    for src_rel, dst_rel, size in (ENEMIES if want("enemies") else []):
        src = os.path.join(AST, src_rel.replace("/", os.sep))
        dst = os.path.join(AST, dst_rel.replace("/", os.sep))
        if _process(src, dst, size, False, True, "auto"):
            ok += 1
        else:
            fail += 1

    # 元素普攻弹丸贴图：纯黑底发光体 -> 亮度键转透明
    for src_rel, dst_rel in (BULLETS if want("bullets") else []):
        src = os.path.join(AST, src_rel.replace("/", os.sep))
        dst = os.path.join(AST, dst_rel.replace("/", os.sep))
        if make_bullet(src, dst):
            ok += 1
        else:
            fail += 1

    # 角色技能特效贴图：棋盘格伪透明底 -> 纹理去底 + 去水印 + 裁边 + 缩放
    for src_rel, dst_rel, size, wm_box in (SKILL_FX if want("fx") else []):
        src = os.path.join(AST, src_rel.replace("/", os.sep))
        dst = os.path.join(AST, dst_rel.replace("/", os.sep))
        if _process(src, dst, size, wm_box, True, "checkerfx"):
            ok += 1
        else:
            fail += 1

    # 技能释放姿势立绘：线稿屏障抠图 + 保块 + 填针孔 + 裁边 + 缩放
    for entry in (CAST_POSES if want("poses") else []):
        key, cid, n = entry[0], entry[1], entry[2]
        ink = globals().get(entry[3], CAST_INK) if len(entry) > 3 else CAST_INK
        cdir = os.path.join(AST, "characters", cid)
        for k in range(1, n + 1):
            for tag, name in (("cast", f"cast_{k}.png"),
                              ("hcast", f"cast_human_{k}.png")):
                src = os.path.join(AST, f"characters/{key}_src_{tag}{k}.png")
                if _process(src, os.path.join(cdir, name), (768, 960),
                            False, True, "none", ink=ink):
                    ok += 1
                else:
                    fail += 1

    # 普攻连击姿势立绘：与释放姿势同画像（浅色主体+掌风/风环特效），复用同一套参数
    for entry in (ATK_POSES if want("poses") else []):
        key, cid, stages = entry[0], entry[1], entry[2]
        ink = globals().get(entry[3], CAST_INK) if len(entry) > 3 else CAST_INK
        cdir = os.path.join(AST, "characters", cid)
        for k in stages:
            for tag, name in (("atk", f"atk_{k}.png"),
                              ("hatk", f"atk_human_{k}.png")):
                src = os.path.join(AST, f"characters/{key}_src_{tag}{k}.png")
                if _process(src, os.path.join(cdir, name), (768, 960),
                            False, True, "none", ink=ink):
                    ok += 1
                else:
                    fail += 1

    # 常驻立绘亮度对齐：idle(full/full_human) 与姿势集(atk/cast)来自不同批次
    # 源图、白平衡不同，战斗交叉淡入淡出时会露出肤色跳变（idle 偏暗）。以姿势集
    # 均亮度为目标对 idle 做 gamma 提亮，使二者一致（幂等，详见该模块 docstring）。
    # 只在重生成立绘/姿势时跑：单独调背景等无关节不必付这份开销。
    if only is None or only in ("chars", "poses"):
        try:
            import normalize_idle_brightness as _nib
            print("\n[亮度对齐] 常驻立绘 -> 姿势集均亮")
            for _r in _nib.normalize_all(os.path.join(AST, "characters")):
                print(_r)
        except Exception as _e:
            print("[警告] 亮度对齐跳过:", _e)

    print(f"\n成功 {ok} 个，失败 {fail} 个")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
