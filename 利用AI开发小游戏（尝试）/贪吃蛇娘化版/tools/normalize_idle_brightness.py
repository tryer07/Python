# -*- coding: utf-8 -*-
"""
tools/normalize_idle_brightness.py —— 常驻立绘亮度对齐工具

问题
----
战斗中角色「常驻(idle)」立绘用的是 full.png / full_human.png，普攻姿势用
atk_*.png、技能姿势用 cast_*.png；释放时 idle 与姿势做交叉淡入淡出。
这两批图来自不同批次的 AI 源图，白平衡/曝光不同 —— 实测 idle 普遍比姿势暗
（绯焰、潮汐最明显，薄荷、樱落轻微），淡入淡出瞬间肤色会「跳亮」，很出戏。

做法
----
以「该角色该形态的姿势集(atk_*+cast_*)不透明像素平均亮度」为目标，对 idle
立绘做 gamma 提亮：out = 255 * (in/255) ** g（g<1 提亮）。gamma 只动 RGB、
不动 alpha，且是曲线而非线性乘 —— 抬中间调、护住高光与暗部，不会像线性亮度
那样把近白像素裁成一片死白，肤色过渡自然。

幂等
----
每轮实测「当前 idle 均亮 vs 姿势均亮」的差，二分求解 g 使二者一致；已对齐时
解得 g≈1 直接跳过。重复运行安全，重跑 prepare_assets 生成新的暗 idle 后再跑
本工具会重新对齐。首次运行把原始 idle 备份到 tools/_brightness_backup/<id>/。

prepare_assets.py 末尾会调用 normalize_all()，故管线重跑后自动保持对齐。
"""
import glob
import os

import numpy as np
from PIL import Image

# 只统计 alpha>=200 的实心像素：抗锯齿半透边混入背景会污染亮度均值
_ALPHA_TH = 200
# gamma 求解区间：<1 提亮、>1 压暗；够覆盖实测最大约 1.4 倍的亮度差
_G_LO, _G_HI = 0.30, 2.50
# 目标与当前差到此程度以内视为已对齐（幂等阈值），|g-1| 小于它就不写盘
_EPS = 0.6


def _opaque_px(path):
    """返回不透明像素的 (N,3) uint8 RGB 数组；无实心像素返回 None。"""
    im = Image.open(path).convert("RGBA")
    arr = np.asarray(im)
    mask = arr[..., 3] >= _ALPHA_TH
    if not mask.any():
        return None
    return arr[..., :3][mask]


def _mean_lum(px):
    """Rec.601 加权亮度均值（0-255）。px 为 (N,3) 数值数组。"""
    lum = (px[:, 0].astype(np.float64) * 299
           + px[:, 1].astype(np.float64) * 587
           + px[:, 2].astype(np.float64) * 114) / 1000.0
    return float(lum.mean())


def _gamma_lut(g):
    """256 项 gamma 查找表（uint8）。"""
    idx = np.arange(256, dtype=np.float64) / 255.0
    out = np.clip(np.round(255.0 * np.power(idx, g)), 0, 255).astype(np.uint8)
    return out


def _solve_gamma(px, target):
    """二分求 gamma，使 px 经 gamma 校正后的平均亮度逼近 target。

    f(g) 关于 g 单调递减（g 越大越暗），故可二分。返回 (g, 校正后均亮)。
    """
    lo, hi = _G_LO, _G_HI
    # 端点夹逼：target 落在可达区间外就取端点（理论上不会发生）
    if _mean_lum(_gamma_lut(hi)[px]) >= target:
        return hi, _mean_lum(_gamma_lut(hi)[px])
    if _mean_lum(_gamma_lut(lo)[px]) <= target:
        return lo, _mean_lum(_gamma_lut(lo)[px])
    for _ in range(48):
        mid = (lo + hi) / 2.0
        m = _mean_lum(_gamma_lut(mid)[px])
        if m > target:
            lo = mid          # 太亮 -> 增大 g 压暗
        else:
            hi = mid          # 太暗 -> 减小 g 提亮
    g = (lo + hi) / 2.0
    return g, _mean_lum(_gamma_lut(g)[px])


def _apply_gamma(path, g):
    """对整张图 RGB 施加 gamma（alpha 原样保留），原地覆盖保存。"""
    im = Image.open(path).convert("RGBA")
    lut = [int(v) for v in _gamma_lut(g)]
    r, gg, b, a = im.split()
    r = r.point(lut)
    gg = gg.point(lut)
    b = b.point(lut)
    Image.merge("RGBA", (r, gg, b, a)).save(path, "PNG", optimize=True)


def _backup_once(cdir, name):
    """首次运行把原始 idle 备份到 tools/_brightness_backup/<id>/，供回滚。

    刻意放在 assets 之外：既不会被 PyInstaller 打进包，也不会被任何资源扫描
    误收；已存在则不覆盖（永远留住最初的原始暗图）。
    """
    cid = os.path.basename(cdir)
    bdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_brightness_backup", cid)
    os.makedirs(bdir, exist_ok=True)
    dst = os.path.join(bdir, name)
    if not os.path.exists(dst):
        Image.open(os.path.join(cdir, name)).save(dst, "PNG", optimize=True)


def _pose_target(cdir, form):
    """该形态姿势集(atk+cast)的平均亮度（各图等权）；无姿势图返回 None。"""
    if form == "lamia":
        pats = ("atk_[0-9].png", "cast_[0-9].png")
    else:
        pats = ("atk_human_*.png", "cast_human_*.png")
    files = []
    for p in pats:
        files.extend(sorted(glob.glob(os.path.join(cdir, p))))
    means = []
    for f in files:
        px = _opaque_px(f)
        if px is not None:
            means.append(_mean_lum(px))
    if not means:
        return None
    return float(np.mean(means))


def normalize_char(cdir):
    """对齐一个角色目录下 full.png / full_human.png 到各自姿势集亮度。

    返回可读的报告行列表（空列表 = 该角色无姿势图，无需处理）。
    """
    cid = os.path.basename(cdir)
    report = []
    for form, idle in (("lamia", "full.png"), ("human", "full_human.png")):
        idle_path = os.path.join(cdir, idle)
        if not os.path.exists(idle_path):
            continue
        target = _pose_target(cdir, form)
        if target is None:
            continue                       # luna/stella 等无姿势图的角色：跳过
        px = _opaque_px(idle_path)
        if px is None:
            continue
        cur = _mean_lum(px)
        if abs(cur - target) <= _EPS:
            report.append(f"  {cid:14s} {form:5s} idle={cur:6.1f} "
                          f"pose={target:6.1f}  已对齐，跳过")
            continue
        g, after = _solve_gamma(px, target)
        if abs(g - 1.0) < 0.004:
            report.append(f"  {cid:14s} {form:5s} idle={cur:6.1f} "
                          f"pose={target:6.1f}  g≈1，跳过")
            continue
        _backup_once(cdir, idle)
        _apply_gamma(idle_path, g)
        report.append(f"  {cid:14s} {form:5s} idle={cur:6.1f} -> "
                      f"pose={target:6.1f}  (gamma={g:.3f}, 实测→{after:6.1f})")
    return report


def normalize_all(chars_dir):
    """遍历 characters/ 下所有角色目录做亮度对齐，返回全部报告行。"""
    lines = []
    if not os.path.isdir(chars_dir):
        return lines
    for cid in sorted(os.listdir(chars_dir)):
        cdir = os.path.join(chars_dir, cid)
        if os.path.isdir(cdir):
            lines.extend(normalize_char(cdir))
    return lines


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    cdir = os.path.join(root, "assets", "characters")
    print("[亮度对齐] 常驻立绘 -> 姿势集均亮（gamma 提亮，护高光/暗部）")
    rows = normalize_all(cdir)
    if not rows:
        print("  （无可处理的角色：均未配姿势立绘）")
    for r in rows:
        print(r)
    print("[完成]")
