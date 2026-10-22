# -*- coding: utf-8 -*-
"""资源加载：图片带缓存，缺失时返回 None 由场景自行回退绘制"""
import os
import pygame

from ..settings import BG_DIR, UI_DIR

_cache: dict[str, pygame.Surface] = {}


def load_image(name: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
    """按名称从 backgrounds / ui 目录加载图片，size 可缩放"""
    if name in _cache:
        img = _cache[name]
    else:
        img = None
        for folder in (BG_DIR, UI_DIR):
            path = os.path.join(folder, name)
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                break
        if img is not None:
            _cache[name] = img
    if img is not None and size is not None and img.get_size() != size:
        img = pygame.transform.smoothscale(img, size)
    return img


_font_cache: dict[tuple[str, int], pygame.font.Font] = {}


def get_font(path: str, size: int) -> pygame.font.Font:
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.Font(path, size)
    return _font_cache[key]
