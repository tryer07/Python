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
    透明像素统一涂成 TRANSPARENT 再用 colorkey 抠掉，
    这样烘进不透明底图时是「盖上去」而不是「糊一层」"""
    if len(grid) != SIZE or any(len(row) != SIZE for row in grid):
        raise ValueError(f"精灵网格必须是 {SIZE}x{SIZE}，当前 {len(grid)} 行")
    surf = pygame.Surface((TILE, TILE))
    surf.fill(TRANSPARENT)
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
    """砖墙。face: plain / north / south / corner
    north = 上边缘压一道高光、south = 下边缘压一道暗缝，
    让「墙脚下是地板」的那一圈自己长出立体感"""
    rng = rng or random.Random(7)
    surf = _tile_surface()
    surf.fill(PALETTE["."])                       # 砖缝打底
    for course, (y0, y1) in enumerate(((1, 4), (6, 9))):
        offset = 0 if course == 0 else 3          # 上下两层砖错缝
        for x in range(offset, SIZE, 6):          # 每块砖宽 6
            brick = PALETTE["W"] if rng.random() < 0.5 else PALETTE["w"]
            pygame.draw.rect(surf, brick, (x, y0, 6, y1 - y0))
            for _ in range(rng.randrange(0, 3)):  # 砖面麻点
                pygame.draw.rect(
                    surf, PALETTE["w"],
                    (rng.randrange(x, x + 6), rng.randrange(y0, y1), 1, 1))
    if face == "north":
        pygame.draw.line(surf, PALETTE["E"], (0, 0), (SIZE - 1, 0))
    elif face == "south":
        pygame.draw.line(surf, PALETTE["b"], (0, SIZE - 1), (SIZE - 1, SIZE - 1))
    elif face == "corner":
        pygame.draw.line(surf, PALETTE["b"], (0, SIZE - 1), (SIZE - 1, SIZE - 1))
        pygame.draw.rect(surf, PALETTE["b"], (SIZE - 1, 0, 1, SIZE))
    return surf


def make_floor(rng: random.Random | None = None) -> pygame.Surface:
    """石板地：底色 + 随机暗斑 + 一道浅色接缝"""
    rng = rng or random.Random(11)
    surf = _tile_surface()
    surf.fill(PALETTE["F"])
    for _ in range(rng.randrange(5, 12)):
        shade = PALETTE["f"] if rng.random() < 0.7 else PALETTE["E"]
        pygame.draw.rect(
            surf, shade, (rng.randrange(SIZE), rng.randrange(SIZE),
                          rng.choice((1, 1, 2)), 1))
    if rng.random() < 0.35:
        x = rng.randrange(2, SIZE - 2)
        pygame.draw.line(surf, PALETTE["E"], (x, 1), (x, SIZE - 2))
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


def shade(src: pygame.Surface, factor: float) -> pygame.Surface:
    """整张贴图按 factor 压暗（1.0 就是原图）。colorkey 会跟着 copy 保留，
    因为透明像素本来就是 TRANSPARENT 那块颜色，压暗后仍是它。

    用逐列 PixelArray 赋值：实测本版本 PixelArray 只吃「每列一个 int 列表」，
    不接 numpy 数组；贴图只有 12x12，所以这点开销可以忽略，
    而且只在开局烘一次，不进主循环"""
    factor = max(0.0, min(1.0, factor))
    out = src.copy()
    if factor == 1.0:
        return out
    scale = round(factor * 255)
    pa = pygame.PixelArray(src)
    opa = pygame.PixelArray(out)
    for x in range(src.get_width()):
        opa[x] = [
            (((c >> 16 & 0xFF) * scale) >> 8 << 16)
            | (((c >> 8 & 0xFF) * scale) >> 8 << 8)
            | ((c & 0xFF) * scale) >> 8
            for c in pa[x]
        ]
    pa.close()
    opa.close()
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
