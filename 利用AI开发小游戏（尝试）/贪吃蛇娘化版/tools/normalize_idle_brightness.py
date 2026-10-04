# -*- coding: utf-8 -*-
"""
tools/normalize_idle_brightness.py —— 常驻立绘肤色/观感对齐工具（人工分级版）

问题
----
战斗中「常驻(idle)」立绘(full.png / full_human.png) 与普攻(atk_*)/技能(cast_*)
姿势立绘交叉淡入淡出。两批 AI 源图观感不一致：idle 偏灰白、低对比、发暗，
姿势图对比足、中高饱和、更亮（潮汐最明显）。自动全局统计匹配（gamma / Reinhard /
S-L）反复失败，因为差异在局部对比与饱和风格，不是单一全局量。

做法（只调色差：对比 + 饱和 + 亮度，色相不动）
----------------------------------------------
对每张 idle 从「原始备份」确定性施加三级分级，再写回 live：
  1. 对比：rgb = MID + (rgb - MID) * contrast      （MID=128，拉开明暗层次）
  2. 饱和：rgb = L + (rgb - L) * sat                （L=Rec.601 亮度，绕亮度轴加饱和）
  3. 亮度：rgb *= value                             （整体明暗，默认自动对齐姿势身体亮度）
clamp 到 [0,255]，alpha 不动。
GRADE 表按 (角色, 形态) 给 (sat, contrast)；value 缺省自动 = 姿势身体亮度/idle 身体亮度。
表里没有的角色/形态走 sat=1, contrast=1, value 自动（即仅亮度对齐）。

确定性/幂等
-----------
永远从 tools/_brightness_backup/<id>/ 的原始图读取再分级写回 live，故重复运行结果
一致（幂等）；重跑 prepare_assets 生成新暗图后，本工具仍从备份分级，保持一致。
首次运行若备份不存在，则把当前 live 存为备份。
prepare_assets.py 末尾调用 normalize_all()，管线重跑后自动保持对齐。
"""
import glob
import os

import numpy as np
from PIL import Image

_ALPHA_TH = 200
# 身体区域：不透明 + 亮度中段调，排除近白特效/纯黑，用于自动亮度对齐
_BODY_LUM_LO, _BODY_LUM_HI = 60.0, 235.0
_MID = 128.0

# 人工分级表：(角色, 形态) -> (sat, contrast)。value 省略=自动对齐姿势亮度。
# 目检标定：idle 偏灰白低对比，需加饱和+加对比；亮度交给自动对齐。
GRADE = {
    ("lamia_tide", "lamia"): (1.30, 1.16),
    ("lamia_tide", "human"): (1.15, 1.12),
    ("lamia_flare", "lamia"): (1.12, 1.10),
    ("lamia_flare", "human"): (1.10, 1.08),
    ("lamia_mint", "lamia"): (1.12, 1.08),
    ("lamia_mint", "human"): (1.10, 1.08),
    ("sakura", "lamia"): (1.10, 1.06),
    ("sakura", "human"): (1.10, 1.06),
}


def _load_rgba(path):
    return np.asarray(Image.open(path).convert("RGBA"))


def _body_lum(arr):
    """身体中段调像素的平均亮度；不足返回 None。"""
    rgb = arr[..., :3].astype(np.float64)
    al = arr[..., 3]
    lum = (rgb[..., 0] * 299 + rgb[..., 1] * 587 + rgb[..., 2] * 114) / 1000.0
    mask = (al >= _ALPHA_TH) & (lum >= _BODY_LUM_LO) & (lum <= _BODY_LUM_HI)
    if mask.sum() < 64:
        return None
    return float(lum[mask].mean())


def _pose_body_lum(cdir, form):
    pats = ("atk_[0-9].png", "cast_[0-9].png") if form == "lamia" \
        else ("atk_human_*.png", "cast_human_*.png")
    vals = []
    for p in pats:
        for f in sorted(glob.glob(os.path.join(cdir, p))):
            l = _body_lum(_load_rgba(f))
            if l is not None:
                vals.append(l)
    return float(np.mean(vals)) if vals else None


def _grade(rgb, sat, contrast, value):
    """对比 -> 饱和 -> 亮度，返回 uint8 (...,3)。色相不动。"""
    rgb = _MID + (rgb - _MID) * contrast
    lum = (rgb[..., 0] * 299 + rgb[..., 1] * 587 + rgb[..., 2] * 114) / 1000.0
    rgb = lum[..., None] + (rgb - lum[..., None]) * sat
    rgb = rgb * value
    return np.clip(np.round(rgb), 0, 255).astype(np.uint8)


def _backup_path(cdir, name):
    cid = os.path.basename(cdir)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_brightness_backup", cid, name)


def _ensure_backup(cdir, name):
    dst = _backup_path(cdir, name)
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        Image.open(os.path.join(cdir, name)).save(dst, "PNG", optimize=True)
    return dst


def normalize_char(cdir):
    cid = os.path.basename(cdir)
    report = []
    for form, idle in (("lamia", "full.png"), ("human", "full_human.png")):
        live = os.path.join(cdir, idle)
        if not os.path.exists(live):
            continue
        src = _ensure_backup(cdir, idle)      # 永远从原始图分级
        sat, contrast = GRADE.get((cid, form), (1.0, 1.0))
        arr = _load_rgba(src)
        l_i = _body_lum(arr)
        l_p = _pose_body_lum(cdir, form)
        if l_p is None or l_i is None:
            continue                           # 无姿势图（luna/stella）：跳过
        value = l_p / l_i if l_i > 1e-6 else 1.0
        value = min(2.0, max(0.5, value))
        rgb = _grade(arr[..., :3].astype(np.float64), sat, contrast, value)
        out = arr.copy()
        out[..., :3] = rgb
        Image.fromarray(out, "RGBA").save(live, "PNG", optimize=True)
        report.append(f"  {cid:14s} {form:5s} sat={sat:.2f} contrast={contrast:.2f} "
                      f"value={value:.3f} (idleL={l_i:.0f}->poseL={l_p:.0f})")
    return report


def normalize_all(chars_dir):
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
    print("[肤色对齐] 常驻立绘 -> 姿势观感（对比+饱和+亮度，色相不动）")
    for r in normalize_all(cdir):
        print(r)
    print("[完成]")
