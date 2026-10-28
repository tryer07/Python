# -*- coding: utf-8 -*-
"""
生成原版冒险模式 50 关的关卡配置文件（.tres）。

设计依据：
  - 5 大关 x 10 小关 = 50 关（白天 / 黑夜 / 泳池 / 浓雾 / 屋顶）
  - 每大关第 5 小关固定为小游戏，第 10 小关固定为传送带关
  - 每关通关解锁一个植物（编号 P001~P048 恰好等于原版解锁顺序）
  - 植物/僵尸枚举编号直接沿用项目里的 CharacterRegistry

输出目录：res://resources/level_date_resource/mode_adventure_50/
原始 mode_adventure 目录保持不动，方便随时回退对比。

用法：
    python gen_adventure_levels.py            # 生成全部 50 关
    python gen_adventure_levels.py --check    # 只校验，不写文件
"""

from __future__ import annotations

import argparse
import os
import sys

# ---------------------------------------------------------------- 枚举常量
# 对应 scripts/autoload/global/main_scene_registry.gd -> MainScenes
SCENE_FRONT = 0   # MainGameFront 前院
SCENE_BACK = 1    # MainGameBack  后院（含泳池）
SCENE_ROOF = 2    # MainGameRoof  屋顶

# 对应 scripts/consts/const_level_data.gd -> GameBg
BG_FRONT_DAY = 0
BG_FRONT_NIGHT = 1
BG_POOL = 2
BG_FOG = 3
BG_ROOF = 4
BG_ROOF_NIGHT = 5

# 对应 GameBGM
BGM_FRONT_DAY = 0
BGM_FRONT_NIGHT = 1
BGM_POOL = 2
BGM_FOG = 3
BGM_ROOF = 4
BGM_BOSS = 6

# 对应 E_CardMode
CARD_NORM = 1
CARD_CONVEYOR = 2

# 对应 E_MonsterMode
MONSTER_NULL = 0
MONSTER_NORM = 1

# 对应 CharacterRegistry.ZombieBossType
BOSS_NULL = 0
BOSS_DOCTOR = 1  # ZB001Doctor 僵王博士


# ---------------------------------------------------------------- 关卡数据
# 每关字段说明：
#   stage     大关号 1~5
#   index     小关号 1~10
#   scene     主游戏场景
#   bg        背景
#   bgm       背景音乐
#   waves     出怪波数
#   zombies   该关可刷新的僵尸类型编号列表
#   card      0=自选(用植物解锁天然限制) 2=传送带
#   sun       开局阳光
#   slots     最大卡槽数
#   tomb      墓碑数量（0 表示无墓碑）
#   fog       是否有雾
#   day       是否白天
#   unlock    通关解锁内容（植物编号或文字说明）
LEVELS = [
    # ---------------- 第一大关：前院 白天 ----------------
    # 1-1 照原版教学关：不选卡（卡槽里只有一张不可取消的豌豆射手）、只有中间一条草坪铺了草皮、
    # 僵尸也只走这一条道，通关解锁向日葵
    dict(stage=1, index=1,  scene=SCENE_FRONT, bg=BG_FRONT_DAY, bgm=BGM_FRONT_DAY,
         waves=10, zombies=[1], card=CARD_NORM, sun=50, slots=1, tomb=0, fog=False, day=True,
         no_choose=True, pre=[1], sod=[3], unlock="P002 向日葵"),
    # 1-2 原版就在这一关给到第二株植物（向日葵），草坪也只铺中间三行（2/3/4）。
    # 卡牌不依赖「通关数解锁」，直接固定两张：豌豆射手 + 向日葵。原因有两个：
    #   1) 选关界面把 1-2 一起放开了，玩家可能没打 1-1 就直接进 1-2；
    #      而植物解锁是按通关数算的（1 + 通关数），没通关就只剩豌豆射手一张，
    #      甚至因为没选卡而空手上场 —— 直接不可通关。
    #   2) 原版 1-2 的选卡池本来也只有这两张，固定下来观感和原版一致，还省一次点击。
    # 草坪沿用 1-1 → 1-2 → 1-3 逐关铺开的节奏：1-1 单行(3)、1-2 三行(2/3/4)、1-3 起五行全铺。
    dict(stage=1, index=2,  scene=SCENE_FRONT, bg=BG_FRONT_DAY, bgm=BGM_FRONT_DAY,
         waves=10, zombies=[1], card=CARD_NORM, sun=50, slots=2, tomb=0, fog=False, day=True,
         no_choose=True, pre=[1, 2], sod=[2, 3, 4], unlock="P003 樱桃炸弹"),
    dict(stage=1, index=3,  scene=SCENE_FRONT, bg=BG_FRONT_DAY, bgm=BGM_FRONT_DAY,
         waves=10, zombies=[1, 2, 3], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P004 坚果墙"),
    dict(stage=1, index=4,  scene=SCENE_FRONT, bg=BG_FRONT_DAY, bgm=BGM_FRONT_DAY,
         waves=10, zombies=[1, 2, 3], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="铲子"),
    dict(stage=1, index=5,  scene=SCENE_FRONT, bg=BG_FRONT_DAY, bgm=BGM_FRONT_DAY,
         waves=10, zombies=[1, 3], card=CARD_CONVEYOR, sun=0, slots=10, tomb=0, fog=False, day=True,
         conveyor=[1, 2, 3, 4], unlock="P005 土豆地雷"),
    dict(stage=1, index=6,  scene=SCENE_FRONT, bg=BG_FRONT_DAY, bgm=BGM_FRONT_DAY,
         waves=10, zombies=[1, 2, 3, 4], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P006 寒冰射手"),
    dict(stage=1, index=7,  scene=SCENE_FRONT, bg=BG_FRONT_DAY, bgm=BGM_FRONT_DAY,
         waves=20, zombies=[1, 2, 3, 4], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P007 大嘴花"),
    dict(stage=1, index=8,  scene=SCENE_FRONT, bg=BG_FRONT_DAY, bgm=BGM_FRONT_DAY,
         waves=10, zombies=[1, 2, 3, 4, 5], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P008 双发射手"),
    dict(stage=1, index=9,  scene=SCENE_FRONT, bg=BG_FRONT_DAY, bgm=BGM_FRONT_DAY,
         waves=20, zombies=[1, 2, 3, 4, 5], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="僵尸便条"),
    dict(stage=1, index=10, scene=SCENE_FRONT, bg=BG_FRONT_DAY, bgm=BGM_FRONT_DAY,
         waves=20, zombies=[1, 2, 3, 4, 5], card=CARD_CONVEYOR, sun=0, slots=10, tomb=0, fog=False, day=True,
         conveyor=[1, 2, 3, 4, 6, 8], unlock="P009 小喷菇"),

    # ---------------- 第二大关：前院 黑夜 ----------------
    dict(stage=2, index=1,  scene=SCENE_FRONT, bg=BG_FRONT_NIGHT, bgm=BGM_FRONT_NIGHT,
         waves=10, zombies=[1, 3, 6], card=CARD_NORM, sun=50, slots=10, tomb=4, fog=False, day=False, unlock="P010 阳光菇"),
    dict(stage=2, index=2,  scene=SCENE_FRONT, bg=BG_FRONT_NIGHT, bgm=BGM_FRONT_NIGHT,
         waves=20, zombies=[1, 3, 6], card=CARD_NORM, sun=50, slots=10, tomb=4, fog=False, day=False, unlock="P011 大喷菇"),
    dict(stage=2, index=3,  scene=SCENE_FRONT, bg=BG_FRONT_NIGHT, bgm=BGM_FRONT_NIGHT,
         waves=10, zombies=[1, 3, 6, 7], card=CARD_NORM, sun=50, slots=10, tomb=4, fog=False, day=False, unlock="P012 墓碑吞噬者"),
    dict(stage=2, index=4,  scene=SCENE_FRONT, bg=BG_FRONT_NIGHT, bgm=BGM_FRONT_NIGHT,
         waves=20, zombies=[1, 3, 6, 7], card=CARD_NORM, sun=50, slots=10, tomb=7, fog=False, day=False, unlock="图鉴"),
    dict(stage=2, index=5,  scene=SCENE_FRONT, bg=BG_FRONT_NIGHT, bgm=BGM_FRONT_NIGHT,
         waves=10, zombies=[1, 3], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=False, unlock="P013 魅惑菇"),
    dict(stage=2, index=6,  scene=SCENE_FRONT, bg=BG_FRONT_NIGHT, bgm=BGM_FRONT_NIGHT,
         waves=10, zombies=[1, 3, 6, 7, 8], card=CARD_NORM, sun=50, slots=10, tomb=7, fog=False, day=False, unlock="P014 胆小菇"),
    dict(stage=2, index=7,  scene=SCENE_FRONT, bg=BG_FRONT_NIGHT, bgm=BGM_FRONT_NIGHT,
         waves=20, zombies=[1, 3, 6, 7, 8], card=CARD_NORM, sun=50, slots=10, tomb=11, fog=False, day=False, unlock="P015 寒冰菇"),
    dict(stage=2, index=8,  scene=SCENE_FRONT, bg=BG_FRONT_NIGHT, bgm=BGM_FRONT_NIGHT,
         waves=10, zombies=[1, 3, 6, 7, 8], card=CARD_NORM, sun=50, slots=10, tomb=11, fog=False, day=False, unlock="P016 毁灭菇"),
    dict(stage=2, index=9,  scene=SCENE_FRONT, bg=BG_FRONT_NIGHT, bgm=BGM_FRONT_NIGHT,
         waves=20, zombies=[1, 2, 3, 6, 7, 8], card=CARD_NORM, sun=50, slots=10, tomb=11, fog=False, day=False, unlock="僵尸便条"),
    dict(stage=2, index=10, scene=SCENE_FRONT, bg=BG_FRONT_NIGHT, bgm=BGM_FRONT_NIGHT,
         waves=20, zombies=[1, 2, 3, 6, 7, 8], card=CARD_CONVEYOR, sun=0, slots=10, tomb=11, fog=False, day=False,
         conveyor=[1, 2, 3, 4, 6, 8, 9, 10, 11, 13], unlock="P017 睡莲"),

    # ---------------- 第三大关：后院 泳池 ----------------
    dict(stage=3, index=1,  scene=SCENE_BACK, bg=BG_POOL, bgm=BGM_POOL,
         waves=10, zombies=[1, 3, 5, 9, 11], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P018 窝瓜"),
    dict(stage=3, index=2,  scene=SCENE_BACK, bg=BG_POOL, bgm=BGM_POOL,
         waves=20, zombies=[1, 3, 5, 9, 11], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P019 三线射手 + 解锁迷你游戏"),
    dict(stage=3, index=3,  scene=SCENE_BACK, bg=BG_POOL, bgm=BGM_POOL,
         waves=20, zombies=[1, 3, 5, 9, 10, 12], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P020 缠绕水草"),
    dict(stage=3, index=4,  scene=SCENE_BACK, bg=BG_POOL, bgm=BGM_POOL,
         waves=30, zombies=[1, 3, 5, 9, 10, 12], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="商店 + 洒水壶"),
    dict(stage=3, index=5,  scene=SCENE_BACK, bg=BG_POOL, bgm=BGM_POOL,
         waves=20, zombies=[1, 3, 5, 12], card=CARD_CONVEYOR, sun=0, slots=10, tomb=0, fog=False, day=True,
         conveyor=[1, 2, 17, 18, 19], unlock="P021 火爆辣椒"),
    dict(stage=3, index=6,  scene=SCENE_BACK, bg=BG_POOL, bgm=BGM_POOL,
         waves=20, zombies=[1, 3, 5, 9, 12, 13], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P022 地刺"),
    dict(stage=3, index=7,  scene=SCENE_BACK, bg=BG_POOL, bgm=BGM_POOL,
         waves=30, zombies=[1, 3, 5, 9, 10, 13, 14], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P023 火炬树桩"),
    dict(stage=3, index=8,  scene=SCENE_BACK, bg=BG_POOL, bgm=BGM_POOL,
         waves=20, zombies=[1, 3, 5, 9, 12, 13, 14, 15], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P024 高坚果"),
    dict(stage=3, index=9,  scene=SCENE_BACK, bg=BG_POOL, bgm=BGM_POOL,
         waves=30, zombies=[1, 2, 3, 5, 9, 13, 14, 15], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="僵尸便条"),
    dict(stage=3, index=10, scene=SCENE_BACK, bg=BG_POOL, bgm=BGM_POOL,
         waves=30, zombies=[1, 2, 3, 5, 9, 11, 13, 14, 15], card=CARD_CONVEYOR, sun=0, slots=10, tomb=0, fog=False, day=True,
         conveyor=[1, 2, 17, 18, 19, 21, 22], unlock="P025 水兵菇"),

    # ---------------- 第四大关：后院 浓雾 ----------------
    dict(stage=4, index=1,  scene=SCENE_BACK, bg=BG_FOG, bgm=BGM_FOG,
         waves=10, zombies=[1, 3, 5, 9, 12], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=True, day=True, unlock="P026 路灯花"),
    dict(stage=4, index=2,  scene=SCENE_BACK, bg=BG_FOG, bgm=BGM_FOG,
         waves=20, zombies=[1, 3, 5, 9, 12, 17], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=True, day=True, unlock="P027 仙人掌"),
    dict(stage=4, index=3,  scene=SCENE_BACK, bg=BG_FOG, bgm=BGM_FOG,
         waves=10, zombies=[1, 3, 5, 9, 12, 17], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=True, day=True, unlock="P028 三叶草"),
    dict(stage=4, index=4,  scene=SCENE_BACK, bg=BG_FOG, bgm=BGM_FOG,
         waves=20, zombies=[1, 3, 5, 9, 12, 16, 17], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=True, day=True, unlock="咖啡豆/洒水壶"),
    # 4-5 原版是砸罐子小游戏；罐子场景需单独接入，第一版先按普通关配置，保证可通关不会卡住
    dict(stage=4, index=5,  scene=SCENE_BACK, bg=BG_FOG, bgm=BGM_FOG,
         waves=10, zombies=[1, 3, 5, 9, 12], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=True, day=True, unlock="P029 裂荚射手（砸罐子小游戏）"),
    dict(stage=4, index=6,  scene=SCENE_BACK, bg=BG_FOG, bgm=BGM_FOG,
         waves=10, zombies=[1, 3, 5, 9, 12, 16, 17, 18], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=True, day=True, unlock="P030 杨桃 + 解锁解谜模式"),
    dict(stage=4, index=7,  scene=SCENE_BACK, bg=BG_FOG, bgm=BGM_FOG,
         waves=20, zombies=[1, 3, 5, 9, 12, 16, 17, 18, 19], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=True, day=True, unlock="P031 南瓜头"),
    dict(stage=4, index=8,  scene=SCENE_BACK, bg=BG_FOG, bgm=BGM_FOG,
         waves=10, zombies=[1, 3, 5, 9, 12, 16, 17, 18, 19], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=True, day=True, unlock="P032 磁力菇"),
    dict(stage=4, index=9,  scene=SCENE_BACK, bg=BG_FOG, bgm=BGM_FOG,
         waves=20, zombies=[1, 2, 3, 5, 9, 12, 17, 18, 19], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=True, day=True, unlock="僵尸便条"),
    dict(stage=4, index=10, scene=SCENE_BACK, bg=BG_FOG, bgm=BGM_FOG,
         waves=20, zombies=[1, 2, 3, 5, 9, 12, 16, 17, 18, 19], card=CARD_CONVEYOR, sun=0, slots=10, tomb=0, fog=True, day=True,
         conveyor=[1, 2, 17, 21, 22, 26, 27, 28], unlock="P033 卷心菜投手"),

    # ---------------- 第五大关：屋顶 ----------------
    dict(stage=5, index=1,  scene=SCENE_ROOF, bg=BG_ROOF, bgm=BGM_ROOF,
         waves=10, zombies=[1, 3, 5, 9, 16, 18], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P034 花盆"),
    dict(stage=5, index=2,  scene=SCENE_ROOF, bg=BG_ROOF, bgm=BGM_ROOF,
         waves=20, zombies=[1, 3, 5, 9, 16, 18, 22], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P035 玉米投手"),
    dict(stage=5, index=3,  scene=SCENE_ROOF, bg=BG_ROOF, bgm=BGM_ROOF,
         waves=20, zombies=[1, 3, 5, 9, 16, 18, 22], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P036 咖啡豆"),
    dict(stage=5, index=4,  scene=SCENE_ROOF, bg=BG_ROOF, bgm=BGM_ROOF,
         waves=30, zombies=[1, 3, 5, 9, 16, 18, 22, 24], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="洒水壶"),
    dict(stage=5, index=5,  scene=SCENE_ROOF, bg=BG_ROOF, bgm=BGM_ROOF,
         waves=20, zombies=[1, 3, 5, 9, 18, 22], card=CARD_CONVEYOR, sun=0, slots=10, tomb=0, fog=False, day=True,
         # 屋顶必须能拿到花盆(34)，否则整关无法种植
         conveyor=[34, 1, 2, 23, 24, 33, 35], unlock="P037 大蒜"),
    dict(stage=5, index=6,  scene=SCENE_ROOF, bg=BG_ROOF, bgm=BGM_ROOF,
         waves=20, zombies=[1, 3, 5, 9, 16, 18, 22, 23], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P038 叶子保护伞"),
    dict(stage=5, index=7,  scene=SCENE_ROOF, bg=BG_ROOF, bgm=BGM_ROOF,
         waves=30, zombies=[1, 3, 5, 9, 16, 18, 22, 23, 24], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P039 金盏花"),
    dict(stage=5, index=8,  scene=SCENE_ROOF, bg=BG_ROOF, bgm=BGM_ROOF,
         waves=20, zombies=[1, 3, 5, 9, 16, 18, 22, 23, 24], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="P040 西瓜投手"),
    dict(stage=5, index=9,  scene=SCENE_ROOF, bg=BG_ROOF, bgm=BGM_ROOF,
         waves=30, zombies=[1, 2, 3, 5, 9, 16, 18, 22, 23, 24], card=CARD_NORM, sun=50, slots=10, tomb=0, fog=False, day=True, unlock="僵尸便条"),
    # 最终关：僵王博士，开战即生成（boss_spawn_wave = 0），打死僵王直接判胜。
    # 原版 5-10 是「传送带 + 无阳光」的 boss 战：植物全靠传送带送，天降阳光也关闭。
    # 卡池权重按用途配：花盆最频繁（屋顶每个格子都要垫），投手是主力输出，
    # 樱桃/窝瓜/辣椒/寒冰菇用于拆僵王的冰球和火球。
    dict(stage=5, index=10, scene=SCENE_ROOF, bg=BG_ROOF_NIGHT, bgm=BGM_BOSS,
         waves=20, zombies=[1, 3, 5, 9, 16, 18, 22, 23, 24], card=CARD_CONVEYOR, sun=0,
         slots=10, tomb=0, fog=False, day=True, day_sun=False, boss=True,
         conveyor=[(34, 6), (33, 4), (35, 4), (40, 3), (3, 2), (18, 2), (21, 2), (15, 2)],
         unlock="通关：银向日葵奖杯"),
]

# 项目里两个脚本资源的固定 uid（从现有 .tres 复制，不能手写新的）
SCRIPT_PRE_PLANT_UID = "uid://bke3sg5otco7s"
SCRIPT_LEVEL_DATA_UID = "uid://bjt3l56exxmdw"
SCRIPT_PRE_PLANT_PATH = "res://scripts/resources/level/pre_plant_in_level.gd"
SCRIPT_LEVEL_DATA_PATH = "res://scripts/resources/level/level_data.gd"

# 传送带卡池所需的两个资源脚本。只写 path 不写 uid：这两个脚本本身
# 由 Godot 生成 uid，手写反而容易冲突。
SCRIPT_CARD_REFERENCE = "res://scripts/resources/card/card_reference.gd"
SCRIPT_CARD_WEIGHT = "res://scripts/resources/card/card_weight.gd"

# 对应 ResourceCardReference.CardType
CARD_TYPE_PLANT = 1

OUT_DIR = "resources/level_date_resource/mode_adventure_50"
# 清单输出到项目根，UTF-8 BOM + CRLF，Windows 记事本可直接打开
LIST_OUT_NAME = "冒险模式50关清单.txt"
# 供 GDScript 读取的关卡路径清单。导出为 exe 后 DirAccess 扫描 res:// 不可靠，
# 因此把路径固化成常量数组，运行时按顺序加载。
PATHS_OUT = "scripts/choose_level/adventure_level_paths.gd"


def level_name(lv: dict) -> str:
    """返回关卡显示名，例如 1-3。"""
    return f"{lv['stage']}-{lv['index']}"


def file_name(lv: dict) -> str:
    """返回输出文件名，例如 adventure_1_03_front_day.tres。"""
    scene_tag = {SCENE_FRONT: "front", SCENE_BACK: "back", SCENE_ROOF: "roof"}[lv["scene"]]
    bg_tag = {
        BG_FRONT_DAY: "day", BG_FRONT_NIGHT: "night", BG_POOL: "pool",
        BG_FOG: "fog", BG_ROOF: "roof", BG_ROOF_NIGHT: "roofboss",
    }[lv["bg"]]
    return f"adv_{lv['stage']}_{lv['index']:02d}_{scene_tag}_{bg_tag}.tres"


def normalize_pool(pool: list) -> list[tuple[int, int]]:
    """把卡池条目统一成 (植物编号, 权重) 列表。

    允许两种写法：
        1, 2, 3           -> 等概率
        (34, 6), (33, 4)  -> 指定权重，用于让花盆这类基建卡更频繁
    """
    result: list[tuple[int, int]] = []
    for item in pool:
        if isinstance(item, (list, tuple)):
            result.append((int(item[0]), int(item[1])))
        else:
            result.append((int(item), 1))
    return result


def build_tres(lv: dict) -> str:
    """把一关的数据渲染成 .tres 文本。

    注意：不写顶层 uid，交给 Godot 导入时自动生成，避免手写 uid 冲突。
    传送带关必须带卡池，否则卡槽无从抽卡会直接死局，因此会额外生成
    card_reference / card_weight 子资源。
    """
    # 只有传送带关且确实配了卡池，才引入权重脚本与权重子资源
    conveyor_pool = normalize_pool(lv.get("conveyor") or [])
    use_conveyor_pool = lv["card"] == CARD_CONVEYOR and bool(conveyor_pool)
    # 系统预选卡：不选卡的教学关用它把固定卡塞进卡槽
    prechosen = [int(plant_id) for plant_id in (lv.get("pre") or [])]

    ext_lines = [
        f'[ext_resource type="Script" uid="{SCRIPT_PRE_PLANT_UID}" '
        f'path="{SCRIPT_PRE_PLANT_PATH}" id="1_pre"]',
        f'[ext_resource type="Script" uid="{SCRIPT_LEVEL_DATA_UID}" '
        f'path="{SCRIPT_LEVEL_DATA_PATH}" id="2_ld"]',
    ]
    if use_conveyor_pool or prechosen:
        ext_lines.append(f'[ext_resource type="Script" path="{SCRIPT_CARD_REFERENCE}" id="3_cardref"]')
    if use_conveyor_pool:
        ext_lines.append(f'[ext_resource type="Script" path="{SCRIPT_CARD_WEIGHT}" id="4_cardweight"]')

    # 预选卡引用 + 传送带「引用+权重」
    sub_blocks: list[str] = []
    for i, plant_id in enumerate(prechosen):
        sub_blocks.append(
            f'[sub_resource type="Resource" id="PreCardRef_{i}"]\n'
            f'script = ExtResource("3_cardref")\n'
            f'card_type = {CARD_TYPE_PLANT}\n'
            f'content_id = {plant_id}'
        )
    if use_conveyor_pool:
        for i, (plant_id, _weight) in enumerate(conveyor_pool):
            sub_blocks.append(
                f'[sub_resource type="Resource" id="CardRef_{i}"]\n'
                f'script = ExtResource("3_cardref")\n'
                f'card_type = {CARD_TYPE_PLANT}\n'
                f'content_id = {plant_id}'
            )
        for i, (_plant_id, weight) in enumerate(conveyor_pool):
            sub_blocks.append(
                f'[sub_resource type="Resource" id="CardWeight_{i}"]\n'
                f'script = ExtResource("4_cardweight")\n'
                f'card_reference = SubResource("CardRef_{i}")\n'
                f'weight = {weight}'
            )

    load_steps = 1 + len(ext_lines) + len(sub_blocks)

    lines = [
        f'[gd_resource type="Resource" script_class="ResourceLevelData" '
        f'load_steps={load_steps} format=3]',
        "",
    ]
    lines.extend(ext_lines)
    lines.append("")
    for block in sub_blocks:
        lines.append(block)
        lines.append("")
    lines.extend([
        "[resource]",
        'script = ExtResource("2_ld")',
        # 主游戏场景
        f"game_sences = {lv['scene']}",
        f"game_BG = {lv['bg']}",
        f"game_BGM = {lv['bgm']}",
        # 场地属性
        f"is_fog = {str(lv['fog']).lower()}",
        f"is_day = {str(lv['day']).lower()}",
        f"is_day_sun = {str(lv.get('day_sun', lv['day'])).lower()}",
        "is_lawn_mover = true",
        "is_zombie_can_home = true",
    ])

    # 草坪铺设：只有写了 sod 的关卡才输出，其余保持「整片草坪已铺好」
    sod_rows = lv.get("sod") or []
    if sod_rows:
        ids = ", ".join(str(r) for r in sod_rows)
        lines.append(f"sod_rows = Array[int]([{ids}])")

    # 起点展示僵尸：原版教学关不需要展示
    show_zombie = not (lv["stage"] == 1 and lv["index"] <= 3)
    lines.append(f"look_show_zombie = {str(show_zombie).lower()}")

    # 出怪配置
    if lv["waves"] > 0:
        lines.append(f"monster_mode = {MONSTER_NORM}")
        lines.append(f"max_wave = {lv['waves']}")
        zs = ", ".join(str(z) for z in lv["zombies"])
        lines.append(f"zombie_refresh_types = Array[int]([{zs}])")
    else:
        lines.append(f"monster_mode = {MONSTER_NULL}")

    # 墓碑
    lines.append(f"is_have_tombston = {str(lv['tomb'] > 0).lower()}")
    lines.append(f"init_tombstone_num = {lv['tomb']}")

    # 僵王配置：仅最终关，开战即生成（0 表示正式开战生成），击杀僵王即判胜
    if lv.get("boss"):
        lines.append("win_on_boss_death = true")
        lines.append(f"boss_type = {BOSS_DOCTOR}")
        lines.append("boss_spawn_wave = 0")

    # 卡槽
    can_choose = lv["card"] == CARD_NORM and not lv.get("no_choose", False)
    lines.append(f"can_choosed_card = {str(can_choose).lower()}")
    lines.append(f"card_mode = {lv['card']}")
    # 预选卡：教学关不选卡，卡槽里直接放固定卡
    if prechosen:
        refs = ", ".join(f'SubResource("PreCardRef_{i}")' for i in range(len(prechosen)))
        lines.append(f"prechosen_cards = Array[ResourceCardReference]([{refs}])")
    # 传送带卡池：顺序与子资源一致，权重均为 1
    if use_conveyor_pool:
        refs = ", ".join(
            f'SubResource("CardWeight_{i}")' for i in range(len(conveyor_pool))
        )
        lines.append(f"conveyor_weights = Array[ResourceCardWeight]([{refs}])")
    lines.append(f"max_choosed_card_num = {lv['slots']}")
    lines.append(f"start_sun = {lv['sun']}")
    # 铲子：原版前 3 关还没有铲子，1-4 通关才拿到
    has_shovel = not (lv["stage"] == 1 and lv["index"] <= 3)
    lines.append(f"is_shovel = {str(has_shovel).lower()}")

    # 类型标记，保持与 Godot 导出一致
    lines.append(f'metadata/_custom_type_script = "{SCRIPT_LEVEL_DATA_UID}"')
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成原版冒险模式 50 关配置")
    parser.add_argument("--check", action="store_true", help="只校验不写文件")
    parser.add_argument("--root", default=None, help="Godot 项目根目录")
    args = parser.parse_args()

    # 定位项目根（脚本位于 <root>/tools/）
    root = args.root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, *OUT_DIR.split("/"))

    print("=" * 56)
    print("原版冒险模式 50 关生成器")
    print(f"项目根：{root}")
    print(f"输出到：{out_dir}")
    print("=" * 56)

    # ---- 校验数据完整性 ----
    errors = []
    if len(LEVELS) != 50:
        errors.append(f"关卡总数应为 50，实际 {len(LEVELS)}")

    seen = set()
    for lv in LEVELS:
        key = (lv["stage"], lv["index"])
        if key in seen:
            errors.append(f"关卡重复：{key}")
        seen.add(key)
        if not 1 <= lv["index"] <= 10:
            errors.append(f"{level_name(lv)} 小关号越界")
        for z in lv["zombies"]:
            if not 1 <= z <= 25:
                errors.append(f"{level_name(lv)} 僵尸编号 {z} 不在 1~25 范围")
        if lv["waves"] > 0 and not lv["zombies"]:
            errors.append(f"{level_name(lv)} 有波次但没有僵尸")
        # 旗帜进度条断言波数必须是 10 的倍数（每 10 波一面旗），否则进关即报错
        if lv["waves"] > 0 and lv["waves"] % 10 != 0:
            errors.append(f"{level_name(lv)} 波数 {lv['waves']} 不是 10 的倍数，旗帜进度条会断言失败")

        # 不选卡的关卡必须预置卡，否则卡槽空着无法种植
        pre_list = [int(p) for p in (lv.get("pre") or [])]
        if lv.get("no_choose", False) and not pre_list:
            errors.append(f"{level_name(lv)} 设为不选卡但没有预置植物，会无法种植")
        if pre_list and lv["card"] != CARD_NORM:
            errors.append(f"{level_name(lv)} 预置卡只能用于自选卡模式")
        for pid in pre_list:
            if not 1 <= pid <= 48:
                errors.append(f"{level_name(lv)} 预置植物编号 {pid} 不在 1~48 范围")

        # 传送带关必须有卡池，否则卡槽抽不到任何卡，开局直接死局
        pool = normalize_pool(lv.get("conveyor") or [])
        pool_ids = [pid for pid, _w in pool]
        if lv["card"] == CARD_CONVEYOR and not pool:
            errors.append(f"{level_name(lv)} 是传送带关但没配 conveyor 卡池")
        for pid in pool_ids:
            if not 1 <= pid <= 48:
                errors.append(f"{level_name(lv)} 卡池植物编号 {pid} 不在 1~48 范围")
        for _pid, weight in pool:
            if weight <= 0:
                errors.append(f"{level_name(lv)} 卡池植物 {_pid} 权重必须大于 0")
        # 屋顶关卡不放花盆就无处种植，必然卡死
        if lv["scene"] == SCENE_ROOF and pool and 34 not in pool_ids:
            errors.append(f"{level_name(lv)} 屋顶传送带卡池缺少花盆(P034)")

        # 草坪铺设：行号从 1 开始，只能在白天前院使用，且不能一行都不铺（否则无处种植）
        sod_rows = lv.get("sod") or []
        for r in sod_rows:
            if not 1 <= r <= 5:
                errors.append(f"{level_name(lv)} 草坪行号 {r} 不在 1~5 范围")
        if sod_rows and lv["bg"] != BG_FRONT_DAY:
            errors.append(f"{level_name(lv)} 草坪未铺满只支持白天前院")
        if sod_rows and len(sod_rows) >= 5:
            errors.append(f"{level_name(lv)} 五条草坪都铺了，直接留空即可")

    if errors:
        print("\n❌ 数据校验未通过：")
        for e in errors:
            print("   -", e)
        return 1
    print("\n✅ 数据校验通过：50 关，编号与僵尸引用均有效")

    if args.check:
        print("（--check 模式，未写入文件）")
        return 0

    # ---- 写文件 ----
    os.makedirs(out_dir, exist_ok=True)
    written = 0
    for lv in LEVELS:
        path = os.path.join(out_dir, file_name(lv))
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(build_tres(lv))
        written += 1

    print(f"✅ 已生成 {written} 个关卡配置文件")

    # ---- 生成 GDScript 路径清单（供选关界面按顺序加载）----
    paths_file = os.path.join(root, *PATHS_OUT.split("/"))
    os.makedirs(os.path.dirname(paths_file), exist_ok=True)
    glines = [
        'extends RefCounted',
        'class_name AdventureLevelPaths',
        '',
        '## 冒险模式 50 关配置文件的路径清单，由 tools/gen_adventure_levels.py 自动生成。',
        '## 请勿手工修改本文件；调整关卡请改生成器的 LEVELS 数据表后重跑。',
        '## 顺序即关卡顺序（1-1 到 5-10），选关界面按此顺序铺开并计算解锁进度。',
        'const PATHS: Array[String] = [',
    ]
    for lv in LEVELS:
        rel = OUT_DIR + "/" + file_name(lv)
        glines.append(f'\t"res://{rel}",  # {level_name(lv)}')
    glines.append("]")
    glines.append("")
    with open(paths_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(glines))
    print(f"✅ 已生成路径清单：{paths_file}")

    # ---- 输出清单（控制台 + 记事本可读的 txt）----
    stage_titles = {
        1: "第一大关  前院 · 白天",
        2: "第二大关  前院 · 黑夜",
        3: "第三大关  后院 · 泳池",
        4: "第四大关  后院 · 浓雾",
        5: "第五大关  屋顶",
    }
    report: list[str] = []
    report.append("植物大战僵尸  冒险模式 50 关清单")
    report.append("=" * 60)
    report.append("说明：以下配置已生成到")
    report.append("      resources/level_date_resource/mode_adventure_50/")
    report.append("      修改本清单对应的数据后重跑生成器即可整体更新。")
    report.append("")
    report.append(f"{'关卡':<6}{'卡牌':<8}{'波次':<8}{'僵尸数':<8}通关解锁")
    report.append("-" * 60)

    last_stage = 0
    for lv in LEVELS:
        if lv["stage"] != last_stage:
            last_stage = lv["stage"]
            report.append("")
            report.append(stage_titles[lv["stage"]])
            report.append("-" * 60)

        if lv["card"] == CARD_CONVEYOR:
            mode = "传送带"
        elif lv.get("no_choose", False):
            mode = "固定卡"
        else:
            mode = "自选"
        # 波次列：僵王关单独标注，无波次关标为小游戏
        if lv.get("boss"):
            waves = "僵王战"
        elif lv["waves"]:
            waves = f"{lv['waves']} 波"
        else:
            waves = "小游戏"
        znum = f"{len(lv['zombies'])} 种" if lv["zombies"] else "-"
        report.append(f"{level_name(lv):<6}{mode:<8}{waves:<8}{znum:<8}{lv['unlock']}")

    report.append("")
    report.append("=" * 60)
    report.append("备注")
    report.append("  1-1 照原版教学关：只有中间一条草坪铺了草皮（其余是荒土，不能种植也不能出僵尸），")
    report.append("  不选卡（卡槽只有一张不可取消的豌豆射手），没有铲子，只有普通僵尸，通关解锁向日葵。")
    report.append("  1-2~1-3 同样没有铲子。")
    report.append("  1-5 / 2-5 / 3-5 / 5-5 目前按普通关配置，4-5 也未接入砸罐子，")
    report.append("  先保证可以正常通关，后续单独接入小游戏场景。")

    # 控制台输出
    print()
    for line in report:
        print(line)

    # txt 输出（UTF-8 BOM + CRLF，记事本友好）
    # 同时写两份：项目根一份便于随代码走；向上 3 层一份便于直接找到
    # （本项目目录有三层同名嵌套，外层是用户常用的工作目录）
    text = "\n".join(report)
    list_paths = [os.path.join(root, LIST_OUT_NAME)]
    upper = os.path.normpath(os.path.join(root, "..", "..", ".."))
    if os.path.isdir(upper) and os.path.normpath(upper) != os.path.normpath(root):
        list_paths.append(os.path.join(upper, LIST_OUT_NAME))

    for list_path in list_paths:
        try:
            with open(list_path, "w", encoding="utf-8-sig", newline="\r\n") as f:
                f.write(text)
            print(f"\n✅ 清单已写出：{list_path}")
        except OSError as exc:
            # 外层目录不可写时不影响生成，只提示
            print(f"\n⚠️ 清单写出失败（不影响关卡文件）：{list_path} -> {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
