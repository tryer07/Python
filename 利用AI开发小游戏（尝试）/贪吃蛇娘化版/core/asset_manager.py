import math
import os

import pygame

from settings import ASSETS_DIR, FONT_NAME


class AssetManager:
    """
    统一管理图片、字体等资源的加载与缓存。

    除了普通加载，还负责「旋转预烘焙」：
        pygame.transform.rotate() 每次调用都要重新采样整张图，很慢。
        蛇身每帧要按方向旋转，如果实时旋转，帧率会掉得很难看。
        所以这里把用到的角度先生成好存起来，运行时只查表。
    """

    ROT_STEPS = 48                      # 预烘焙 48 个角度（每 7.5 度一档）

    def __init__(self):
        self._images = {}
        self._fonts = {}
        self._rot_cache = {}
        self._scaled_cache = {}

    # ------------------------------------------------------------ 基础加载
    def get_image(self, relative_path, scale_to=None):
        key = (relative_path, scale_to)
        if key in self._images:
            return self._images[key]

        # 路径为空 / 非字符串 -> 直接给占位图，避免上层还要到处判空
        if not relative_path or not isinstance(relative_path, str):
            image = self._placeholder(scale_to)
            self._images[key] = image
            return image

        full_path = os.path.join(ASSETS_DIR, relative_path.replace("/", os.sep))
        if os.path.exists(full_path):
            try:
                image = pygame.image.load(full_path).convert_alpha()
            except pygame.error as e:
                print(f"[素材读取失败] {relative_path}: {e}")
                image = self._placeholder(scale_to)
        else:
            print(f"[素材缺失] {relative_path} -> 用占位图代替")
            image = self._placeholder(scale_to)

        if scale_to:
            image = pygame.transform.smoothscale(image, scale_to)

        self._images[key] = image
        return image

    @staticmethod
    def _placeholder(size=None):
        """占位图：紫红方块加边框，一眼就能看出是哪张图少了"""
        size = size or (64, 64)
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((190, 70, 140, 200))
        pygame.draw.rect(surf, (255, 255, 255, 220), surf.get_rect(), 3)
        return surf

    # ------------------------------------------------------------ 旋转查表
    def get_rotated(self, relative_path, angle_deg, pivot_center=True):
        """
        取「已经转好角度」的图。angle_deg 会吸附到最接近的预烘焙档位。
        0 度 = 朝右，顺时针为正（符合屏幕坐标习惯）。
        """
        if not relative_path:
            return self.get_image(relative_path)
        step = int(round((angle_deg % 360.0) / (360.0 / self.ROT_STEPS))) % self.ROT_STEPS
        key = (relative_path, step)
        if key in self._rot_cache:
            return self._rot_cache[key]

        base = self.get_image(relative_path)
        real_angle = -step * (360.0 / self.ROT_STEPS)   # pygame 逆时针为正，取负匹配屏幕方向
        surf = pygame.transform.rotozoom(base, real_angle, 1.0)
        self._rot_cache[key] = surf
        return surf

    # ------------------------------------------------------------ 等比缩放
    def get_scaled(self, relative_path, height=None, width=None):
        key = (relative_path, height, width)
        if key in self._scaled_cache:
            return self._scaled_cache[key]

        base = self.get_image(relative_path)
        w, h = base.get_size()
        if height:
            ratio = height / h
        elif width:
            ratio = width / w
        else:
            ratio = 1.0
        # 用 round 而非 int：int(w*(width/w)) 会因浮点误差比 width 小 1，
        # 下游若按 width 去 subsurface 就会越界报 ValueError。
        surf = pygame.transform.smoothscale(
            base, (max(1, round(w * ratio)), max(1, round(h * ratio)))
        )
        self._scaled_cache[key] = surf
        return surf

    # ---------------------------------------------------------------- 字体
    def get_font(self, size, bold=False):
        key = (size, bold)
        if key in self._fonts:
            return self._fonts[key]

        font = pygame.font.SysFont(FONT_NAME, size, bold=bold)
        self._fonts[key] = font
        return font

    # ---------------------------------------------------------------- 清理
    def clear(self):
        self._images.clear()
        self._fonts.clear()
        self._rot_cache.clear()
        self._scaled_cache.clear()


def angle_between(from_pos, to_pos):
    """算两点连线相对「朝右」的角度（度，顺时针为正）"""
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    return math.degrees(math.atan2(-dy, dx))
