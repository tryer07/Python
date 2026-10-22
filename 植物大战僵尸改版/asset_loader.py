# -*- coding: utf-8 -*-
"""素材索引器：按文件名（不含扩展名、忽略大小写）查找贴图与音效。

设计要点（对应工程约定第 1 条）：
  - 启动时先 build_image_index() 建立文件索引，preload() 一次性加载并
    convert_alpha() 预转换，游戏循环内只查缓存、禁止 load/scale。
  - 找不到的素材返回洋红色占位图并记入缺失清单，绝不抛异常中断。
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import pygame

import constants

# ---------- 内部缓存与索引 ----------
_image_index: Dict[str, str] = {}          # 归一化名字 -> 贴图文件完整路径
_sound_index: Dict[str, str] = {}          # 归一化名字 -> 音效文件完整路径
_surface_cache: Dict[str, pygame.Surface] = {}   # 原名 -> 原始尺寸 Surface
_scaled_cache: Dict[str, pygame.Surface] = {}    # 原名 -> 放大后 Surface
_sound_cache: Dict[str, Optional[pygame.mixer.Sound]] = {}
_missing_assets: List[str] = []            # 缺失素材清单（保序去重）

# 占位图颜色（洋红）与尺寸
_PLACEHOLDER_COLOR = (255, 0, 255)
_PLACEHOLDER_SIZE = (128, 128)


def _norm_key(filename: str) -> str:
    """把文件名归一化为查找键：去掉扩展名、转小写。"""
    stem = os.path.splitext(filename)[0]
    return stem.lower()


def build_image_index() -> None:
    """扫描贴图目录，建立 名字->路径 索引；同名不同扩展时优先 PNG。"""
    global _image_index
    _image_index = {}
    if not os.path.isdir(constants.ASSETS_DIR):
        print(f"[asset_loader] 贴图目录不存在: {constants.ASSETS_DIR}")
        return
    for name in os.listdir(constants.ASSETS_DIR):
        if not name.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        key = _norm_key(name)
        # PNG 透明图优先于 JPG 背景图
        if key in _image_index and not _index_entry_is_png(key):
            if not name.lower().endswith(".png"):
                continue
        _image_index[key] = os.path.join(constants.ASSETS_DIR, name)


def _index_entry_is_png(key: str) -> bool:
    """判断当前索引里该键存的是否已是 PNG 文件。"""
    return _image_index.get(key, "").lower().endswith(".png")


def build_sound_index() -> None:
    """扫描音效目录，建立 名字->路径 索引（.ogg）。"""
    global _sound_index
    _sound_index = {}
    if not os.path.isdir(constants.SOUNDS_DIR):
        print(f"[asset_loader] 音效目录不存在: {constants.SOUNDS_DIR}")
        return
    for name in os.listdir(constants.SOUNDS_DIR):
        if not name.lower().endswith(".ogg"):
            continue
        _sound_index[_norm_key(name)] = os.path.join(constants.SOUNDS_DIR, name)


def _record_missing(name: str) -> None:
    """把缺失素材记入清单并打印一次警告。"""
    if name not in _missing_assets:
        _missing_assets.append(name)
        print(f"[asset_loader] 素材缺失（已用洋红占位图）: {name}")


def _make_placeholder() -> pygame.Surface:
    """生成洋红色占位图，保证缺素材时流程不中断。"""
    surf = pygame.Surface(_PLACEHOLDER_SIZE, pygame.SRCALPHA)
    surf.fill(_PLACEHOLDER_COLOR)
    return surf


def _load_surface(name: str) -> pygame.Surface:
    """按名字加载单张贴图并 convert_alpha() 预转换。"""
    path = _image_index.get(name.lower())
    if path is None:
        _record_missing(name)
        return _make_placeholder()
    try:
        surf = pygame.image.load(path)
        # convert_alpha() 需要显示窗口已创建；未创建时保留原始 Surface
        if pygame.display.get_surface() is not None:
            surf = surf.convert_alpha()
    except pygame.error as exc:
        _record_missing(name)
        print(f"[asset_loader] 贴图加载失败: {path} ({exc})")
        return _make_placeholder()
    return surf


def get(name: str) -> pygame.Surface:
    """取得原始尺寸的贴图 Surface（带缓存，缓存键不区分大小写）。"""
    key = name.lower()
    if key not in _surface_cache:
        _surface_cache[key] = _load_surface(name)
    return _surface_cache[key]


def get_scaled(name: str) -> pygame.Surface:
    """取得按 ASSET_SCALE 放大后的贴图 Surface（预转缓存，循环内直接 blit）。"""
    key = name.lower()
    if key not in _scaled_cache:
        base = get(name)
        if constants.ASSET_SCALE == 1.0:
            _scaled_cache[key] = base
        else:
            size = (int(round(base.get_width() * constants.ASSET_SCALE)),
                    int(round(base.get_height() * constants.ASSET_SCALE)))
            _scaled_cache[key] = pygame.transform.smoothscale(base, size)
    return _scaled_cache[key]


def load_sound(name: str) -> Optional[pygame.mixer.Sound]:
    """取得音效 Sound；找不到或音频设备不可用时返回 None，不抛异常。"""
    key = name.lower()
    if key in _sound_cache:
        return _sound_cache[key]
    path = _sound_index.get(key)
    if path is None:
        _record_missing(name)
        _sound_cache[key] = None
        return None
    try:
        sound = pygame.mixer.Sound(path)
    except pygame.error as exc:
        print(f"[asset_loader] 音效加载失败: {path} ({exc})")
        sound = None
    _sound_cache[key] = sound
    return sound


def preload(names: List[str]) -> None:
    """启动时一次性预加载贴图清单（放大版一并预生成）。"""
    for name in names:
        get(name)
        get_scaled(name)


def report_missing() -> None:
    """打印缺失素材清单（验收/排错用）。"""
    if _missing_assets:
        print(f"[asset_loader] 共缺失 {len(_missing_assets)} 个素材: "
              f"{_missing_assets}")
    else:
        print("[asset_loader] 无缺失素材")
