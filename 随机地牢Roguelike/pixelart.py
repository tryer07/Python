"""像素美术层：把「字符画网格」烘成贴图，并提供 1 像素=一个画面像素的纹理生成。

设计原则（和 NES/SNES 地牢游戏同一套规矩）：
1. **全程序生成，零外部素材**——所有图案就是下面的字符画，改一个字符就换一个像素；
2. **限色调色板**——所有贴图只从 PALETTE 取色，颜色一少，画面自然就有「卡带味」；
3. **纹理 12x12 / 图案 12x12**——正好等于 settings.TILE，所以全程没有缩放、没有插值，
   一个画面像素就是一个美术像素，绝不会出现半灰半糊的脏边。

对外提供的东西：
    bake_sprite(grid)          字符画 -> 12x12 贴图（透明底）
    make_wall/make_floor(...)  程序生成的砖墙、石板地（可做明暗档、随机噪点）
    make_deco(kind)            地面小装饰（裂缝 / 碎骨 / 苔斑）
    shade(surface, k)          把贴图整体压暗到 k 倍，用于火光衰减与「记忆中的暗」
"""

import random

import pygame

from settings import PALETTE, SIZE, TILE, TRANSPARENT


def bake_sprite(grid: list[str]) -> pygame.Surface:
    """字符画 -> TILE x TILE 贴图（尺寸正好等于一格，所以全程不缩放）。
    没画的像素保持 Surface 初始的纯黑，下面 set_colorkey 把它抠掉；
    调色板里最暗的颜色也不是纯黑，所以两者不会混。"""
    if len(grid) != SIZE or any(len(row) != SIZE for row in grid):
        raise ValueError(f"精灵网格必须是 {SIZE}x{SIZE}，当前 {len(grid)} 行")
    surf = pygame.Surface((TILE, TILE))
    for y, row in enumerate(grid):
        for x, key in enumerate(row):
            color = PALETTE.get(key)
            if color is None:
                raise KeyError(f"调色板里没有字符 {key!r}")
            if color == TRANSPARENT:
                continue
            pygame.draw.rect(surf, color, (x, y, 1, 1))
    surf.set_colorkey(TRANSPARENT)
    return surf


def _tile_surface() -> pygame.Surface:
    surf = pygame.Surface((TILE, TILE))
    surf.fill(PALETTE["."])
    return surf


def make_wall(face: str = "plain", rng: random.Random | None = None) -> pygame.Surface:
    """砖墙：三皮砖、两道路缝，上下两皮错半砖。
    铺满整格不留白，否则墙在地板上会像悬浮的色块。
    face: plain / north（上边缘高光）/ south（下边缘阴影）/ corner"""
    rng = rng or random.Random(7)
    surf = _tile_surface()
    surf.fill(PALETTE["."])                        # 先打砖缝底色
    for course, (y0, y1) in enumerate(((1, 4), (5, 8), (9, 12))):
        offset = 0 if course % 2 == 0 else 3       # 上下两皮错半砖
        for x in range(offset - 6, TILE, 6):
            left = max(x, 0)
            right = min(x + 5, TILE)               # 砖之间留 1 列当竖缝
            if right <= left:
                continue
            brick = PALETTE["W"] if rng.random() < 0.5 else PALETTE["w"]
            pygame.draw.rect(surf, brick, (left, y0, right - left, y1 - y0))
            for _ in range(rng.randrange(1, 4)):   # 砖面麻点
                pygame.draw.rect(
                    surf, PALETTE["w"],
                    (rng.randrange(left, right), rng.randrange(y0, y1), 1, 1))
    if face == "north":
        pygame.draw.line(surf, PALETTE["E"], (0, 0), (TILE - 1, 0))
    elif face == "south":
        pygame.draw.line(surf, PALETTE["b"], (0, TILE - 1), (TILE - 1, TILE - 1))
    elif face == "corner":
        pygame.draw.line(surf, PALETTE["b"], (0, TILE - 1), (TILE - 1, TILE - 1))
        pygame.draw.rect(surf, PALETTE["b"], (TILE - 1, 0, 1, TILE))
    return surf


def make_floor(rng: random.Random | None = None) -> pygame.Surface:
    """石板地：底色 + 一道接缝 + 若干暗斑与高光，让地面不像一张纸"""
    rng = rng or random.Random(11)
    surf = _tile_surface()
    surf.fill(PALETTE["F"])
    seam_x = rng.randrange(3, TILE - 3)
    seam_y = rng.randrange(3, TILE - 3)
    pygame.draw.line(surf, PALETTE["f"], (seam_x, 0), (seam_x, TILE - 1))
    pygame.draw.line(surf, PALETTE["f"], (0, seam_y), (TILE - 1, seam_y))
    for _ in range(rng.randrange(8, 16)):
        shade = PALETTE["f"] if rng.random() < 0.6 else PALETTE["E"]
        pygame.draw.rect(
            surf, shade, (rng.randrange(TILE), rng.randrange(TILE),
                          rng.choice((1, 1, 2)), 1))
    return surf


def make_deco(kind: str) -> pygame.Surface:
    """地面小装饰。画在地板之上，纯点缀，不带任何玩法含义"""
    surf = pygame.Surface((TILE, TILE))
    surf.fill(TRANSPARENT)
    if kind == "crack":
        for x, y in ((3, 4), (4, 5), (5, 6), (6, 5), (7, 4), (8, 5), (5, 7), (5, 8)):
            pygame.draw.rect(surf, PALETTE["b"], (x, y, 1, 1))
    elif kind == "bones":
        for x, y in ((3, 7), (4, 7), (5, 7), (7, 6), (8, 6), (4, 4), (5, 3), (8, 8)):
            pygame.draw.rect(surf, PALETTE["s"], (x, y, 1, 1))
    elif kind == "moss":
        for x, y in ((2, 9), (3, 9), (4, 10), (6, 9), (7, 10), (3, 8), (8, 9)):
            pygame.draw.rect(surf, PALETTE["l"], (x, y, 1, 1))
    else:
        raise ValueError(f"不认识的地面装饰：{kind}")
    surf.set_colorkey(TRANSPARENT)
    return surf


_factor_cache: dict[tuple[tuple[int, int, int], float], tuple[int, int, int]] = {}


def _shade_color(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """把一个颜色按 factor 压暗。限色调色板一共才二十几种颜色，
    所以用一个表记下来，同一颜色同亮度只算一次"""
    key = (color, factor)
    cached = _factor_cache.get(key)
    if cached is None:
        cached = (round(color[0] * factor), round(color[1] * factor),
                  round(color[2] * factor))
        _factor_cache[key] = cached
    return cached


def shade(src: pygame.Surface, factor: float) -> pygame.Surface:
    """整张贴图按 factor 压暗（1.0 就是原图）。colorkey 会跟着 copy 保留。

    不用 PixelArray：本版本 pygame 的 pixelarray.pyi 里根本没有 __setitem__ 签名，
    写进去必被类型检查报 Unsupported target；而贴图最多数百像素，
    get_at/set_at 加颜色缓存反而更好读、开销也可忽略（只在开局烘一次）"""
    factor = max(0.0, min(1.0, factor))
    out = src.copy()
    if factor == 1.0:
        return out
    width, height = out.get_size()
    for y in range(height):
        for x in range(width):
            rgb = out.get_at((x, y))
            out.set_at((x, y), _shade_color((rgb.r, rgb.g, rgb.b), factor))
    return out


def bake_levels(src: pygame.Surface, factors: tuple[float, ...]) -> dict[float, pygame.Surface]:
    """把一张贴图预先烘好几个亮度档，用的时候直接 blit，绝不每帧重算"""
    return {f: shade(src, f) for f in factors}


# ---------- 精灵图案 ----------
SPRITES: dict[str, list[str]] = {
    # 勇者：带羽饰的头盔、面罩里两只眼、右侧一把竖剑
    "player": [
        "    rr      ",
        "   rRRr     ",
        "  aAAAAAa   ",
        "  aAAeAAa   ",
        "  aCCCCCA A ",
        "  CCCCCCaA  ",
        "  CCCCCCa   ",
        "   CCC C    ",
        "   C C C    ",
        "  kk  kk    ",
        "  bb  bb    ",
        "            ",
    ],
    # 哥布林：大耳朵 + 尖牙，绿皮红眼
    "哥布林": [
        "            ",
        " g      g   ",
        " gg    gg   ",
        "  GGGGGG    ",
        "  GereerG   ",
        "  GGGGGG    ",
        "  GkeekkG   ",
        "   GGGG     ",
        "  GGGGGG    ",
        "  G GG G    ",
        "  g g g     ",
        "            ",
    ],
    # 兽人：宽肩、獠牙、腰带上小腹
    "兽人": [
        "            ",
        "  GGGGGG    ",
        " GReeeerG   ",
        " GGGGGGGG   ",
        " GkGGGGkG   ",
        "  GGGGGG    ",
        " mmmmmmmm   ",
        "mmmdddmmm   ",
        " mmmmmmmm   ",
        "  G    G    ",
        "  g    g    ",
        "            ",
    ],
    # 骷髅剑士：头骨 + 肋条 + 一把剑
    "骷髅剑士": [
        "      A     ",
        "  kkkkkk A  ",
        "  kekk ekA  ",
        "  kkkkkkk   ",
        "  kbkbkbk   ",
        "   kkkk     ",
        "  kkkkkk    ",
        "  k kkk k   ",
        "  kkkkkk    ",
        "   k  k     ",
        "  kk  kk    ",
        "            ",
    ],
    # 楼梯守卫：黄铜盔、双肩甲，比小怪大一圈的存在感
    "楼梯守卫": [
        "  t      t  ",
        "  tt    tt  ",
        "   TTTT     ",
        "  TTeeTT    ",
        "  TTTTTT    ",
        " oo oo oo   ",
        "ooooooooooo ",
        "ooORRRROooo ",
        " oo oo oo   ",
        "  o o o     ",
        "  O   O     ",
        "            ",
    ],
    # 药水：木塞 + 细颈 + 鼓肚
    "potion": [
        "            ",
        "            ",
        "     nn     ",
        "     vv     ",
        "    vuuuv   ",
        "   vu  uv   ",
        "  vu    uv  ",
        "  vuuuuuuv  ",
        "  vuuuuuuv  ",
        "   vvvvvv   ",
        "            ",
        "            ",
    ],
    # 下行楼梯：一圈圈往下的台阶
    "stairs": [
        "            ",
        "  TTTTTTTT  ",
        "  TttttttT  ",
        "  TttttttT  ",
        "   TTTTTT   ",
        "   TttttT   ",
        "   TttttT   ",
        "    TTTT    ",
        "    TttT    ",
        "    TttT    ",
        "     TT     ",
        "            ",
    ],
}


def bake_all_sprites() -> dict[str, pygame.Surface]:
    """把上面所有字符画烘成贴图，键名与 entities 用的怪物名对应"""
    return {name: bake_sprite(grid) for name, grid in SPRITES.items()}
