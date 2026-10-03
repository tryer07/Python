# -*- coding: utf-8 -*-
"""
core/audio_manager.py —— 音频管理器

设计哲学与 AssetManager 一致：「缺素材给占位」。
  - assets/audio/ 下有对应文件（.ogg/.wav/.mp3）就加载真实音频；
  - 没有就用纯 Python 合成一段占位音（复古电子音），无需 numpy、无需联网。
  - 日后把真实音频丢进对应文件名即自动升级，不用改任何代码。

安全降级：mixer 初始化失败（无声卡 / 工具用 dummy 驱动）时，
所有方法都变成 no-op，绝不崩。
"""

import math
import os
import random
import threading
from array import array
from collections import deque

try:
    import numpy as _np
except Exception:  # numpy 缺失时自动回退纯 Python 合成（功能不受影响，只是慢一些）
    _np = None

import pygame

from settings import (
    AUDIO_CHANNELS, AUDIO_DIR, AUDIO_ENABLED, BGM_ENDLESS_POOL, BGM_FADE_MS,
)

SAMPLE_RATE = 44100

# 音符频率表（合成占位音用）
N = {
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61, "G3": 196.00,
    "A3": 220.00, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00,
    "A4": 440.00, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.25, "F5": 698.46, "G5": 783.99,
    "A5": 880.00, "C6": 1046.50,
}

_RNG = random.Random(20261001)   # 固定种子，噪声占位音每次一致


# ============================================================ 合成基础工具
def _tone(freq, dur, wave="sine", vol=0.5, slide_to=None,
          attack=0.008, release=0.06, trem=0.0):
    """生成一段单音（float 采样列表，范围约 [-1, 1]）。

    wave: sine / square / tri / saw；slide_to 非空时频率从 freq 线性滑到 slide_to；
    trem 为颤音深度（0~1）；attack/release 为包络起止时长（秒）。
    """
    n = max(1, int(dur * SAMPLE_RATE))
    a = int(attack * SAMPLE_RATE)
    r = int(release * SAMPLE_RATE)
    if _np is not None:
        # 矢量化路径：与原逐样本实现数学等价（相位累积、滑音、包络、颤音一致），
        # 但快数十倍——这是把合成从 6s+ 降到 ~0.1s、消除进战斗卡顿的关键。
        i = _np.arange(n, dtype=_np.float64)
        if slide_to is None:
            # 用 cumsum 逐样本累加相位，与原纯 Python 的 phase += ... 位级一致
            # （避免方波/三角波在过零点因相位舍入差而翻符号）。
            phase = _np.cumsum(_np.full(n, 2.0 * _np.pi * freq / SAMPLE_RATE))
        else:
            f_inst = freq + (slide_to - freq) * (i / n)
            phase = _np.cumsum(2.0 * _np.pi * f_inst / SAMPLE_RATE)
        s = _np.sin(phase)
        if wave == "square":
            v = _np.where(s >= 0.0, 1.0, -1.0)
        elif wave == "tri":
            v = (2.0 / _np.pi) * _np.arcsin(_np.clip(s, -1.0, 1.0))
        elif wave == "saw":
            v = 2.0 * _np.mod(phase / (2.0 * _np.pi), 1.0) - 1.0
        else:
            v = s
        if trem:
            v = v * (1.0 + trem * _np.sin(2.0 * _np.pi * 6.0 * i / SAMPLE_RATE))
        env = _np.ones(n, dtype=_np.float64)
        if a > 0:
            m = i < a
            env[m] = i[m] / a
        if r > 0:
            m = i > (n - r)
            env[m] = _np.maximum(0.0, (n - i[m]) / max(1, r))
        return (v * vol * env).astype(_np.float32)
    out = [0.0] * n
    phase = 0.0
    for i in range(n):
        p = i / n
        f = freq if slide_to is None else freq + (slide_to - freq) * p
        phase += 2 * math.pi * f / SAMPLE_RATE
        s = math.sin(phase)
        if wave == "square":
            v = 1.0 if s >= 0 else -1.0
        elif wave == "tri":
            v = (2.0 / math.pi) * math.asin(max(-1.0, min(1.0, s)))
        elif wave == "saw":
            v = 2.0 * ((phase / (2 * math.pi)) % 1.0) - 1.0
        else:
            v = s
        if trem:
            v *= (1.0 + trem * math.sin(2 * math.pi * 6.0 * i / SAMPLE_RATE))
        env = 1.0
        if a > 0 and i < a:
            env = i / a
        if r > 0 and i > n - r:
            env = max(0.0, (n - i) / max(1, r))
        out[i] = v * vol * env
    return out


def _noise(dur, vol=0.5, attack=0.002, release=0.05, lp=None):
    """生成一段噪声。lp 非空时做一阶低通（0~1，越小越闷）。"""
    n = max(1, int(dur * SAMPLE_RATE))
    out = [0.0] * n
    a = int(attack * SAMPLE_RATE)
    r = int(release * SAMPLE_RATE)
    last = 0.0
    for i in range(n):
        w = _RNG.uniform(-1.0, 1.0)
        if lp is not None:
            w = last + lp * (w - last)
            last = w
        env = 1.0
        if a > 0 and i < a:
            env = i / a
        if r > 0 and i > n - r:
            env = max(0.0, (n - i) / max(1, r))
        out[i] = w * vol * env
    return out


def _seq(segments):
    """顺序拼接多段采样。"""
    if _np is not None:
        arrs = [s if isinstance(s, _np.ndarray)
                else _np.asarray(s, dtype=_np.float32) for s in segments]
        if not arrs:
            return _np.zeros(0, dtype=_np.float32)
        return _np.concatenate(arrs).astype(_np.float32)
    out = []
    for s in segments:
        out.extend(s)
    return out


def _mix(tracks):
    """叠加多轨（自动补零到等长）。"""
    if not tracks:
        return _np.zeros(0, dtype=_np.float32) if _np is not None else []
    if _np is not None:
        arrs = [t if isinstance(t, _np.ndarray)
                else _np.asarray(t, dtype=_np.float32) for t in tracks]
        n = max(len(t) for t in arrs)
        out = _np.zeros(n, dtype=_np.float32)
        for t in arrs:
            out[:len(t)] += t
        return out
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    return out


def _pcm_to_stereo_bytes(a):
    """numpy float 采样 -> 16-bit 立体声 interleaved 字节流（矢量化，极快）。"""
    pcm = _np.clip(a, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(_np.int16)
    stereo = _np.empty(pcm.size * 2, dtype=_np.int16)
    stereo[0::2] = pcm
    stereo[1::2] = pcm
    return stereo.tobytes()


def _to_bytes(samples):
    """float 采样列表 -> 16-bit 立体声 interleaved 字节流（匹配 mixer 格式）。"""
    if _np is not None:
        a = samples if isinstance(samples, _np.ndarray) \
            else _np.asarray(samples, dtype=_np.float32)
        return _pcm_to_stereo_bytes(a)
    arr = array("h")
    for s in samples:
        v = int(s * 32767)
        if v > 32767:
            v = 32767
        elif v < -32768:
            v = -32768
        arr.append(v)
        arr.append(v)
    return arr.tobytes()


# ============================================================ 占位音配方
def _recipe(name):
    """按逻辑音效名返回合成采样。未知名字给一个中性提示音。"""
    if name == "ui_click":
        return _tone(1200, 0.04, "square", 0.32, release=0.03)
    if name == "ui_hover":
        return _tone(900, 0.03, "sine", 0.16, release=0.02)
    if name == "ui_back":
        return _tone(500, 0.07, "sine", 0.28, slide_to=320)
    if name == "eat_exp":
        return _tone(660, 0.09, "sine", 0.38, slide_to=990)
    if name == "eat_crystal":
        return _tone(1320, 0.08, "tri", 0.32)
    if name == "eat_stardust":
        return _tone(1560, 0.12, "sine", 0.32, trem=0.3)
    if name == "eat_heart":
        return _tone(880, 0.10, "sine", 0.34, slide_to=1100)
    if name == "level_up":
        return _seq([_tone(N[k], 0.07, "sine", 0.38)
                     for k in ("C5", "E5", "G5", "C6")])
    if name == "skill_unlock":
        arp = _seq([_tone(N[k], 0.07, "sine", 0.34)
                    for k in ("C5", "E5", "G5", "C6")])
        return _mix([arp, _tone(N["C6"] * 2, 0.28, "sine", 0.14)])
    if name == "hurt":
        return _mix([_tone(110, 0.15, "square", 0.36, slide_to=70, release=0.1),
                     _noise(0.15, 0.22, release=0.1)])
    if name == "kill":
        return _mix([_noise(0.12, 0.30, release=0.08),
                     _tone(200, 0.12, "saw", 0.22, slide_to=80)])
    if name == "skill_dash":
        return _mix([_tone(300, 0.15, "saw", 0.22, slide_to=1200),
                     _noise(0.15, 0.14, release=0.1)])
    if name == "skill_spike":
        return _tone(1800, 0.08, "square", 0.24, slide_to=900)
    if name == "skill_shield":
        return _mix([_tone(N["C5"], 0.30, "sine", 0.22),
                     _tone(N["E5"], 0.30, "sine", 0.18),
                     _tone(N["G5"], 0.30, "sine", 0.16)])
    if name == "skill_thorn":
        return _tone(160, 0.07, "square", 0.28, slide_to=90)
    if name == "skill_storm":
        return _mix([_noise(0.40, 0.22, release=0.3),
                     _tone(N["A4"], 0.40, "sine", 0.18, slide_to=N["A5"]),
                     _tone(N["E5"], 0.40, "sine", 0.14)])
    if name == "skill_bloom":
        return _mix([_tone(N["C6"], 0.30, "sine", 0.24, slide_to=N["G5"], trem=0.25),
                     _tone(N["E5"], 0.30, "tri", 0.16),
                     _noise(0.24, 0.10, lp=0.4, release=0.2)])
    # ---------------- 自由移动：普攻 / 闪避 / 选卡 ----------------
    if name == "shoot":
        return _tone(1100, 0.05, "tri", 0.18, slide_to=680, release=0.03)
    if name == "swipe":
        # 近战爪风挥击（薄荷 3 段连击）：短噪声音刷 + 下滑音，与弹丸的"啵"声区分
        return _mix([_noise(0.09, 0.20, lp=0.5, release=0.06),
                     _tone(900, 0.07, "tri", 0.10, slide_to=420)])
    if name == "dodge":
        return _mix([_noise(0.14, 0.16, lp=0.5, release=0.1),
                     _tone(520, 0.12, "sine", 0.16, slide_to=1300)])
    if name == "card_pick":
        return _seq([_tone(N["E5"], 0.06, "sine", 0.30),
                     _tone(N["A5"], 0.10, "sine", 0.28)])
    if name == "gameover":
        return _seq([_tone(N["A4"], 0.18, "sine", 0.34),
                     _tone(N["F4"], 0.18, "sine", 0.34),
                     _tone(N["D4"], 0.18, "sine", 0.34),
                     _tone(N["C4"], 0.35, "sine", 0.34, release=0.2)])
    if name == "gacha_pull":
        return _tone(300, 0.30, "sine", 0.28, slide_to=1200)
    if name == "gacha_error":
        return _seq([_tone(200, 0.09, "square", 0.28),
                     _tone(160, 0.12, "square", 0.28)])
    if name == "gacha_ssr":
        arp = _seq([_tone(N[k], 0.06, "tri", 0.32)
                    for k in ("C5", "E5", "G5", "C6", "E5", "G5", "C6")])
        return _mix([arp, _tone(N["C6"], 0.42, "sine", 0.16)])
    if name == "gacha_sr":
        return _seq([_tone(N[k], 0.08, "tri", 0.30)
                     for k in ("C5", "E5", "G5")])
    if name == "gacha_r":
        return _tone(N["G4"], 0.15, "sine", 0.28)
    # ---------------- Boss 战 ----------------
    if name == "boss_appear":
        return _mix([_tone(70, 0.70, "saw", 0.30, slide_to=180, release=0.4),
                     _noise(0.70, 0.16, lp=0.15, release=0.5)])
    if name == "boss_hit":
        return _tone(420, 0.05, "square", 0.26, slide_to=260, release=0.03)
    if name == "boss_shoot":
        return _tone(1500, 0.05, "square", 0.16, slide_to=900, release=0.03)
    if name == "boss_charge":
        return _mix([_tone(200, 0.35, "saw", 0.26, slide_to=1000, release=0.1),
                     _noise(0.35, 0.12, release=0.2)])
    if name == "boss_slam":
        return _mix([_tone(90, 0.30, "square", 0.34, slide_to=45, release=0.2),
                     _noise(0.30, 0.28, lp=0.25, release=0.2)])
    if name == "boss_defeat":
        return _seq([_tone(N["C5"], 0.12, "saw", 0.30, slide_to=N["C4"]),
                     _tone(N["A4"], 0.12, "saw", 0.28, slide_to=N["A3"]),
                     _tone(N["F4"], 0.16, "saw", 0.26, slide_to=N["F3"]),
                     _mix([_tone(60, 0.55, "square", 0.30, slide_to=35, release=0.4),
                           _noise(0.55, 0.20, lp=0.2, release=0.45)])])
    if name == "victory":
        arp = _seq([_tone(N[k], 0.10, "tri", 0.34)
                    for k in ("C5", "E5", "G5", "C6", "G5", "C6")])
        return _mix([arp, _tone(N["C6"], 0.60, "sine", 0.16, release=0.4)])
    # 未知名字：给个中性提示音，保证「调了就有声」，方便发现漏配
    return _tone(880, 0.06, "sine", 0.28)


# ============================================================ 生成式 BGM
# 不再用 4 秒短循环（听久了单调）。改为「多段落演进的长循环」：
#   · 每首约 16~24 秒，分 4 个段落逐层叠加（pad → +bass/arp → +lead → 全开），
#     听感上渐进推进，循环回到开头也不易察觉接缝；
#   · 场景轮换用「变体」：同一调式家族里移调/换走向/换音色，前后衔接自然；
#   · 纯 Python 逐样本合成较慢，故放到后台线程生成 + 交叉淡入淡出播放（见 AudioManager）。

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "natmin": [0, 2, 3, 5, 7, 8, 10],
    "harmmin": [0, 2, 3, 5, 7, 8, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "pentmaj": [0, 2, 4, 7, 9],
    "pentmin": [0, 3, 5, 7, 10],
}

# 每个主题一份「配器档案」：root=主频、scale=调式、prog=每小节和弦级数、
# beat=每拍秒数、bars=小节数、各层 (波形, 音量)、perc=打击强度、trem=颤音、seed=旋律随机种子。
_BGM_PROFILES = {
    "menu": dict(root=196.0, scale="major", prog=[0, 5, 3, 4], beat=0.52, bars=12,
                 pad=("sine", 0.11), bass=("sine", 0.12), arp=("tri", 0.075),
                 lead=("sine", 0.12), perc=0.0, trem=0.12, seed=1101),
    "battle": dict(root=220.0, scale="natmin", prog=[0, 5, 3, 4], beat=0.34, bars=12,
                   pad=("saw", 0.05), bass=("square", 0.10), arp=("square", 0.075),
                   lead=("saw", 0.09), perc=0.5, trem=0.0, seed=2201),
    "battle_campus_garden": dict(root=261.63, scale="major", prog=[0, 3, 4, 0],
                                 beat=0.36, bars=12, pad=("tri", 0.075),
                                 bass=("sine", 0.11), arp=("sine", 0.085),
                                 lead=("tri", 0.10), perc=0.35, trem=0.06, seed=3101),
    "battle_neon_night": dict(root=220.0, scale="dorian", prog=[0, 3, 4, 6],
                              beat=0.28, bars=14, pad=("saw", 0.05),
                              bass=("square", 0.10), arp=("square", 0.08),
                              lead=("saw", 0.09), perc=0.7, trem=0.0, seed=3201),
    "battle_deep_sea": dict(root=146.83, scale="natmin", prog=[0, 0, 5, 3],
                            beat=0.46, bars=12, pad=("tri", 0.10),
                            bass=("sine", 0.12), arp=("sine", 0.06),
                            lead=("tri", 0.085), perc=0.25, trem=0.18, seed=3301),
    "battle_sakura_realm": dict(root=293.66, scale="pentmaj", prog=[0, 3, 1, 4],
                                beat=0.40, bars=12, pad=("sine", 0.09),
                                bass=("sine", 0.10), arp=("tri", 0.08),
                                lead=("sine", 0.11), perc=0.2, trem=0.28, seed=3401),
    "boss": dict(root=174.61, scale="harmmin", prog=[0, 1, 0, 6], beat=0.24, bars=12,
                 pad=("saw", 0.06), bass=("square", 0.12), arp=("square", 0.09),
                 lead=("saw", 0.10), perc=0.95, trem=0.0, seed=4101),
    "gacha": dict(root=261.63, scale="major", prog=[0, 4, 5, 3], beat=0.40, bars=10,
                  pad=("tri", 0.08), bass=("sine", 0.10), arp=("sine", 0.085),
                  lead=("tri", 0.10), perc=0.2, trem=0.0, seed=5101),
    "gameover": dict(root=174.61, scale="natmin", prog=[0, 5, 3, 0], beat=0.60, bars=8,
                     pad=("sine", 0.11), bass=("sine", 0.10), arp=("tri", 0.05),
                     lead=("sine", 0.10), perc=0.0, trem=0.1, seed=6101),
}

# 无尽模式 15 分钟后的「后期高强度」随机曲库（5 首，互不相同）。
_ENDLESS_PROFILES = [
    dict(root=220.0, scale="natmin", prog=[0, 5, 3, 4], beat=0.30, bars=12,
         pad=("saw", 0.05), bass=("square", 0.11), arp=("square", 0.08),
         lead=("saw", 0.10), perc=0.7, trem=0.0, seed=7001),
    dict(root=196.0, scale="dorian", prog=[0, 3, 4, 6], beat=0.28, bars=14,
         pad=("saw", 0.05), bass=("square", 0.11), arp=("saw", 0.08),
         lead=("square", 0.09), perc=0.8, trem=0.0, seed=7002),
    dict(root=233.08, scale="harmmin", prog=[0, 1, 5, 4], beat=0.26, bars=14,
         pad=("saw", 0.055), bass=("square", 0.12), arp=("square", 0.085),
         lead=("saw", 0.10), perc=0.9, trem=0.0, seed=7003),
    dict(root=174.61, scale="natmin", prog=[0, 6, 5, 4], beat=0.32, bars=12,
         pad=("tri", 0.06), bass=("square", 0.11), arp=("tri", 0.08),
         lead=("saw", 0.095), perc=0.75, trem=0.0, seed=7004),
    dict(root=261.63, scale="pentmin", prog=[0, 3, 4, 0], beat=0.27, bars=14,
         pad=("saw", 0.05), bass=("square", 0.11), arp=("square", 0.09),
         lead=("square", 0.10), perc=0.85, trem=0.0, seed=7005),
]

_LEAD_WAVES = ["sine", "tri", "saw", "square"]


def _deg_hz(root_hz, scale, degree, octave=0):
    """按调式级数取频率。degree 越界自动折八度，负数也安全。"""
    n = len(scale)
    oct_extra = degree // n
    idx = degree % n
    semis = scale[idx] + 12 * (oct_extra + octave)
    return root_hz * (2.0 ** (semis / 12.0))


def _place(buf, seg, start_sec):
    """把一段采样叠加进 float 缓冲区的指定时间位置。"""
    start = int(start_sec * SAMPLE_RATE)
    if start < 0:
        start = 0
    n = len(buf)
    if start >= n:
        return
    if _np is not None:
        s = seg if isinstance(seg, _np.ndarray) \
            else _np.asarray(seg, dtype=_np.float32)
        end = min(n, start + s.size)
        if end > start:
            buf[start:end] += s[:end - start]
        return
    end = start + len(seg)
    if end > n:
        end = n
    for i in range(start, end):
        buf[i] += seg[i - start]


def _f32_to_bytes(buf):
    """float32 缓冲区 -> 16bit 立体声 interleaved 字节流。"""
    if _np is not None:
        a = buf if isinstance(buf, _np.ndarray) \
            else _np.asarray(buf, dtype=_np.float32)
        return _pcm_to_stereo_bytes(a)
    out = array("h")
    ap = out.append
    for s in buf:
        v = int(s * 32767)
        if v > 32767:
            v = 32767
        elif v < -32768:
            v = -32768
        ap(v)
        ap(v)
    return out.tobytes()


def _apply_variant(p, variant):
    """同主题的轮换变体：轻微移调 / 旋转和弦走向 / 换主音色 / 变长度，保持听感连贯。"""
    prog = list(p["prog"])
    if len(prog) > 1:
        rot = variant % len(prog)
        p["prog"] = prog[rot:] + prog[:rot]
    p["beat"] = p["beat"] * (1.0 + 0.05 * ((variant % 3) - 1))
    p["root"] = p["root"] * (2.0 ** (((variant % 3) - 1) * 2 / 12.0))
    lw, lv = p["lead"]
    base_i = _LEAD_WAVES.index(lw) if lw in _LEAD_WAVES else 0
    p["lead"] = (_LEAD_WAVES[(base_i + variant) % len(_LEAD_WAVES)], lv)
    if variant % 2 == 1:
        p["bars"] = p.get("bars", 12) + 2
    p["seed"] = p["seed"] + variant * 7919
    return p


def _bgm_profile(name):
    """逻辑曲名 -> 配器档案。支持 '#N' 变体后缀；endless#N 走后期曲库。"""
    base, _, vsuf = name.partition("#")
    variant = int(vsuf) if vsuf.isdigit() else 0
    if base == "endless":
        return dict(_ENDLESS_PROFILES[variant % len(_ENDLESS_PROFILES)])
    prof = _BGM_PROFILES.get(base)
    if prof is None:
        prof = _BGM_PROFILES["menu"]
    prof = dict(prof)
    if variant:
        prof = _apply_variant(prof, variant)
    return prof


def _generate(p):
    """按配器档案合成一段「多段落演进」的长循环，返回 float32 数组。"""
    scale = SCALES[p["scale"]]
    beat = p["beat"]
    bpb = 4
    bar_dur = beat * bpb
    bars = p["bars"]
    tail = 1.4
    total = int((bars * bar_dur + tail) * SAMPLE_RATE)
    if _np is not None:
        buf = _np.zeros(total, dtype=_np.float32)
    else:
        buf = array("f", [0.0]) * total
    prog = p["prog"]
    root = p["root"]
    rng = random.Random(p["seed"])
    pad_w, pad_v = p["pad"]
    bass_w, bass_v = p["bass"]
    arp_w, arp_v = p["arp"]
    lead_w, lead_v = p["lead"]
    perc_v = p.get("perc", 0.0)
    trem = p.get("trem", 0.0)

    for bar in range(bars):
        t0 = bar * bar_dur
        cd = prog[bar % len(prog)]
        section = (bar * 4) // max(1, bars)      # 0..3：逐段加层，做出渐进感
        tones = [cd, cd + 2, cd + 4]
        # pad：整小节铺和弦（贯穿全曲）
        for k, deg in enumerate(tones):
            f = _deg_hz(root, scale, deg, octave=0 if k == 0 else 1)
            _place(buf, _tone(f, bar_dur * 1.02, pad_w, pad_v * (0.82 + 0.06 * k),
                              attack=bar_dur * 0.35, release=bar_dur * 0.5,
                              trem=trem * 0.5), t0)
        # bass：根音低两个八度，半音符律动
        for b in (0, 2):
            f = _deg_hz(root, scale, cd, octave=-2)
            _place(buf, _tone(f, beat * 2 * 0.92, bass_w, bass_v,
                              attack=0.02, release=beat * 0.5), t0 + b * beat)
        # arp：section>=1 起，8 分音符琶音（后段更密）
        if arp_v > 0 and section >= 1:
            steps = 8 if section >= 2 else 4
            sub = bar_dur / steps
            for i in range(steps):
                deg = tones[i % 3]
                f = _deg_hz(root, scale, deg, octave=1)
                _place(buf, _tone(f, sub * 0.85, arp_w, arp_v, attack=0.006,
                                  release=sub * 0.4, trem=trem), t0 + i * sub)
        # lead：section>=2 起，主旋律（带留白）
        if lead_v > 0 and section >= 2:
            for b in range(4):
                if rng.random() < 0.22:
                    continue
                deg = tones[rng.randint(0, 2)] + rng.choice([0, 0, 2, -1, 4])
                f = _deg_hz(root, scale, deg, octave=2)
                dur = beat * rng.choice([0.5, 0.5, 1.0])
                _place(buf, _tone(f, dur * 0.95, lead_w, lead_v, attack=0.01,
                                  release=dur * 0.5, trem=trem), t0 + b * beat)
        # perc：section>=1 起，底鼓 + 踩镲
        if perc_v > 0 and section >= 1:
            for b in (0, 2):
                _place(buf, _tone(120, 0.13, "sine", 0.5 * perc_v,
                                  slide_to=48, release=0.1), t0 + b * beat)
            for i in range(8):
                _place(buf, _noise(0.028, 0.14 * perc_v, lp=0.35, release=0.02),
                       t0 + i * beat * 0.5)

    # 收尾：回到主和弦的长音，让循环接缝平滑
    cd = prog[0]
    for k, deg in enumerate([cd, cd + 2, cd + 4]):
        f = _deg_hz(root, scale, deg, octave=0 if k == 0 else 1)
        _place(buf, _tone(f, tail * 0.95, pad_w, pad_v * 0.9, attack=0.2,
                          release=tail * 0.6, trem=trem * 0.4), bars * bar_dur)

    # 全局淡入淡出，进一步抹平循环接缝
    fi = int(0.5 * SAMPLE_RATE)
    fo = int(1.2 * SAMPLE_RATE)
    if _np is not None:
        m = min(fi, total)
        if m > 0:
            buf[:m] *= (_np.arange(m, dtype=_np.float32) / _np.float32(fi))
        idx0 = total - fo
        lo_i = max(0, idx0)
        hi_i = min(total, idx0 + fo)
        if hi_i > lo_i:
            j = _np.arange(lo_i - idx0, hi_i - idx0, dtype=_np.float32)
            buf[lo_i:hi_i] *= _np.maximum(
                0.0, (_np.float32(fo) - j) / _np.float32(fo))
        # 峰值归一化到统一响度：防爆音削波 + 不同曲子音量一致，交叉淡化才不生硬。
        peak = float(_np.max(_np.abs(buf))) if total else 0.0
        if peak > 1e-6:
            buf *= _np.float32(0.89 / peak)
        return buf
    for i in range(min(fi, total)):
        buf[i] *= i / fi
    for i in range(fo):
        idx = total - fo + i
        if 0 <= idx < total:
            buf[idx] *= max(0.0, (fo - i) / fo)

    # 峰值归一化到统一响度：既防爆音削波，又让不同曲子音量一致，
    # 交叉淡入淡出时才不会一强一弱、听着突兀（呼应“渐进、不生硬”的要求）。
    hi = max(buf)
    lo = min(buf)
    peak = hi if hi > -lo else -lo
    if peak > 1e-6:
        gain = 0.89 / peak
        for i in range(len(buf)):
            buf[i] *= gain
    return buf


def _bgm_recipe(name):
    """按逻辑曲名返回合成 BGM 的 float32 缓冲区（生成较慢，务必走后台预载）。"""
    return _generate(_bgm_profile(name))


# ============================================================ 空实现（降级用）
class _NullAudio:
    """mixer 不可用 / 单例尚未建立时的替身，所有方法 no-op。"""

    volume_focus = "bgm"   # 与 AudioManager 对齐，热键读取焦点时不报错

    def play(self, *a, **k):
        pass

    def play_bgm(self, *a, **k):
        pass

    def stop_bgm(self, *a, **k):
        pass

    def set_bgm_volume(self, *a, **k):
        pass

    def set_sfx_volume(self, *a, **k):
        pass

    def save_volumes(self, *a, **k):
        pass

    def preload_bgm(self, *a, **k):
        pass

    def preload_bgm_many(self, *a, **k):
        pass

    def update(self, *a, **k):
        pass


_NULL = _NullAudio()
_INSTANCE = None


def get_audio():
    """供 button.py 等无 game 引用的地方延迟取用。永远返回一个可安全调用的对象。"""
    return _INSTANCE if _INSTANCE is not None else _NULL


# ============================================================ 主类
class AudioManager:
    """BGM + SFX 的集中管理：真实文件优先，缺则合成占位；音量写回存档。"""

    BGM_FILES = {
        "menu": "menu", "battle": "battle",
        "gacha": "gacha", "gameover": "gameover", "boss": "boss",
        # 四张地图各自的战斗 BGM。
        # 真实文件位：assets/audio/bgm/battle_<场景id>.ogg（.wav/.mp3 亦可），
        # 放进去即自动替换合成兜底音，不用改代码。
        "battle_campus_garden": "battle_campus_garden",
        "battle_neon_night": "battle_neon_night",
        "battle_deep_sea": "battle_deep_sea",
        "battle_sakura_realm": "battle_sakura_realm",
    }

    # 有独立战斗 BGM 的场景 id（battle 场景按 f"battle_{scene_id}" 取曲）
    SCENE_BGM_IDS = ("campus_garden", "neon_night", "deep_sea", "sakura_realm")

    def __init__(self, save_manager=None):
        global _INSTANCE
        _INSTANCE = self

        self.save_manager = save_manager
        self._sounds = {}          # 逻辑名 -> Sound（SFX）
        self._bgm_sounds = {}      # 逻辑名 -> Sound（合成兜底 BGM，已就绪）
        self._bgm_buffers = {}     # 逻辑名 -> 后台合成好的字节缓冲（待转 Sound）
        self._bgm_queue = deque()  # 后台待合成曲名队列（FIFO，先请求先出）
        self._bgm_queued = set()   # 队列去重集合
        self._bgm_cond = threading.Condition()   # 保护 queue/buffers + 唤醒 worker
        self._bgm_worker = None    # 常驻后台合成线程（惰性启动，Condition 等待不空转）
        self._pending_bgm = None   # (name, fade_ms)：已请求但尚未合成完，就绪即播
        self._last_play = {}       # 逻辑名 -> 上次播放时刻（节流用）
        self._current_bgm = None
        self._bgm_channel = None
        self._bgm_mode = None      # "music" | "sound" | None
        self._enabled = AUDIO_ENABLED

        self._ok = False
        self._refresh_ok()

        st = {}
        if save_manager is not None:
            try:
                st = save_manager.get("settings", {}) or {}
            except Exception:
                st = {}
        self.bgm_volume = self._clamp01(float(st.get("bgm_volume", 0.7)))
        self.sfx_volume = self._clamp01(float(st.get("sfx_volume", 0.8)))
        # 热键调哪个音量由“上次鼠标点选的滑块/音量块”决定："bgm" 或 "sfx"。
        self.volume_focus = "bgm"
        if self._ok:
            try:
                pygame.mixer.music.set_volume(self.bgm_volume)
            except Exception:
                pass

        # 主菜单 BGM 合成较慢，启动即后台预热，进主界面时多半已就绪、可立即淡入。
        self.preload_bgm("menu")

    def _refresh_ok(self):
        """懒判定 mixer 可用性：支持后台线程 mixer.init 晚就绪。

        Game 启动时音频设备在后台线程打开（SDL 开设备偶发卡 ~10s，
        不能拖住出窗口）；这里每次用到音频时看一眼 get_init()，
        就绪即补通道数初始化并翻 True（之后早退，稳态零开销）；
        dummy / 无声卡环境恒 False，全部方法 no-op。
        """
        if self._ok:
            return True
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(AUDIO_CHANNELS)
                self._ok = True
        except Exception:
            pass
        return self._ok

    @staticmethod
    def _clamp01(v):
        return max(0.0, min(1.0, v))

    # ------------------------------------------------------------ SFX
    def play(self, name, volume=1.0, throttle=0.0):
        """播放一个音效。throttle>0 时对同名音效做最小间隔节流（秒）。"""
        if not (self._enabled and self._refresh_ok()):
            return
        if throttle > 0:
            t = pygame.time.get_ticks() / 1000.0
            if t - self._last_play.get(name, -999.0) < throttle:
                return
            self._last_play[name] = t
        snd = self._get_sound(name)
        if snd is None:
            return
        try:
            snd.set_volume(self._clamp01(self.sfx_volume * volume))
            snd.play()
        except Exception:
            pass

    # ------------------------------------------------------------ BGM
    def play_bgm(self, name, fade_ms=BGM_FADE_MS):
        """切换 BGM（交叉淡入淡出，衔接平滑不生硬）。

        幂等：已在放这首、或这首正在后台排队合成，都直接返回，避免场景重进 /
        拖窗口时反复重启。真实音频文件优先走 music 通道；否则用后台合成好的
        Sound，未就绪则登记 pending 并触发预载，待 update() 检测到就绪再无缝淡入。"""
        if not self._enabled:
            return
        if self._current_bgm == name and self._pending_bgm is None:
            return
        if self._pending_bgm is not None and self._pending_bgm[0] == name:
            return
        if not self._refresh_ok():
            # 音频设备还没就绪（后台 init 未完成）：先登记 pending，
            # 就绪后由 update() 无缝淡入开播
            self._pending_bgm = (name, fade_ms)
            self.preload_bgm(name, priority=True)
            return

        base = self.BGM_FILES.get(name) or name.replace("#", "_")
        path = self._find_file("bgm", base)
        if path:
            self._pending_bgm = None
            self._current_bgm = name
            self._crossfade_music(path, fade_ms)
            return

        snd = self._get_bgm_sound(name)
        if snd is not None:
            self._pending_bgm = None
            self._current_bgm = name
            self._crossfade_sound(snd, fade_ms)
        else:
            # 还没合成好：先记下，后台「优先」预载（插到队首，抢在投机预载之前生成），
            # 就绪后由 update() 开播（绝不卡主线程）。当前曲继续放，直到新曲就绪再交叉淡化。
            self._pending_bgm = (name, fade_ms)
            self.preload_bgm(name, priority=True)

    def _crossfade_sound(self, snd, fade_ms):
        """双通道交叉淡入淡出：新曲淡入的同时旧曲淡出，切歌过渡平滑。"""
        try:
            snd.set_volume(self._clamp01(self.bgm_volume))
            old = self._bgm_channel
            new_ch = snd.play(-1, fade_ms=fade_ms)
            if new_ch is None:
                return
            if old is not None and old is not new_ch:
                try:
                    old.fadeout(fade_ms)
                except Exception:
                    try:
                        old.stop()
                    except Exception:
                        pass
            self._bgm_channel = new_ch
            self._bgm_mode = "sound"
        except Exception:
            pass

    def _crossfade_music(self, path, fade_ms):
        """真实音频文件走 music 通道：淡出旧的、加载新曲淡入。"""
        try:
            if self._bgm_mode == "sound" and self._bgm_channel is not None:
                try:
                    self._bgm_channel.fadeout(fade_ms)
                except Exception:
                    pass
                self._bgm_channel = None
            elif self._bgm_mode == "music" and fade_ms > 0:
                try:
                    pygame.mixer.music.fadeout(fade_ms)
                except Exception:
                    pass
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.bgm_volume)
            pygame.mixer.music.play(-1, fade_ms=fade_ms)
            self._bgm_mode = "music"
        except Exception:
            pass

    def preload_bgm(self, name, priority=False):
        """把某首合成 BGM 排进后台生成队列。已就绪 / 有真实文件都跳过。

        priority=True 时插到队首（正在请求播放的曲子抢在投机预载之前生成，
        Boss 登场 / 阵亡结算 / 恢复挂起的 Boss 战等即时切歌才不会有可闻延迟）；
        若它已在队列中，则把它提到队首。"""
        if not self._enabled:
            return
        if name in self._bgm_sounds:
            return
        base = self.BGM_FILES.get(name) or name.replace("#", "_")
        if self._find_file("bgm", base):
            return
        with self._bgm_cond:
            if name in self._bgm_buffers:
                return
            if name in self._bgm_queued:
                if priority:
                    try:
                        self._bgm_queue.remove(name)
                        self._bgm_queue.appendleft(name)
                    except ValueError:
                        pass
                    self._bgm_cond.notify()
                return
            if priority:
                self._bgm_queue.appendleft(name)
            else:
                self._bgm_queue.append(name)
            self._bgm_queued.add(name)
            self._bgm_cond.notify()
        self._ensure_worker()

    def preload_bgm_many(self, names):
        """批量预载（保持传入顺序：先请求的先生成、先能播）。"""
        for n in names:
            self.preload_bgm(n)

    def _ensure_worker(self):
        """惰性拉起常驻后台合成线程（只启一次）。"""
        if self._bgm_worker is not None and self._bgm_worker.is_alive():
            return
        try:
            t = threading.Thread(target=self._bgm_worker_loop, daemon=True)
            self._bgm_worker = t
            t.start()
        except Exception:
            self._bgm_worker = None

    def _bgm_worker_loop(self):
        """后台线程：按 FIFO 逐首合成，成品字节缓冲塞进 _bgm_buffers 供主线程取用。"""
        while True:
            with self._bgm_cond:
                while not self._bgm_queue:
                    self._bgm_cond.wait()
                name = self._bgm_queue.popleft()
                self._bgm_queued.discard(name)
            try:
                data = _f32_to_bytes(_bgm_recipe(name))
            except Exception:
                data = None
            if data is not None:
                with self._bgm_cond:
                    self._bgm_buffers[name] = data

    def update(self, dt=0.0):
        """主循环每帧调用：pending 的 BGM 一旦后台合成完就无缝淡入开播。"""
        if self._pending_bgm is None:
            return
        if not (self._enabled and self._refresh_ok()):
            return
        name, fade_ms = self._pending_bgm
        snd = self._get_bgm_sound(name)
        if snd is None:
            # 真实音频文件的曲子在设备未就绪时也走 pending：就绪后直接 music 通道
            path = self._find_file(
                "bgm", self.BGM_FILES.get(name) or name.replace("#", "_"))
            if not path:
                return
            self._pending_bgm = None
            self._current_bgm = name
            self._crossfade_music(path, fade_ms)
            return
        self._pending_bgm = None
        self._current_bgm = name
        self._crossfade_sound(snd, fade_ms)

    @staticmethod
    def scene_rotation(scene_id):
        """某场景的轮换曲单：同主题 3 个变体，听感连贯又不重复。"""
        return [f"battle_{scene_id}", f"battle_{scene_id}#1", f"battle_{scene_id}#2"]

    @staticmethod
    def endless_pool():
        """无尽模式 15 分钟后的随机曲库（BGM_ENDLESS_POOL 首互不相同的曲子）。"""
        return [f"endless#{i}" for i in range(BGM_ENDLESS_POOL)]

    def stop_bgm(self, fade_ms=BGM_FADE_MS):
        self._current_bgm = None
        self._pending_bgm = None
        if not self._refresh_ok():
            return
        self._stop_internal(fade_ms)

    def _stop_internal(self, fade_ms=0):
        self._pending_bgm = None
        try:
            if self._bgm_mode == "music":
                if fade_ms > 0:
                    pygame.mixer.music.fadeout(fade_ms)
                else:
                    pygame.mixer.music.stop()
            elif self._bgm_channel is not None:
                if fade_ms > 0:
                    self._bgm_channel.fadeout(fade_ms)
                else:
                    self._bgm_channel.stop()
        except Exception:
            pass
        self._bgm_channel = None
        self._bgm_mode = None

    # ------------------------------------------------------------ 音量
    def set_bgm_volume(self, v, persist=True):
        self.bgm_volume = self._clamp01(float(v))
        if self._refresh_ok():
            try:
                pygame.mixer.music.set_volume(self.bgm_volume)
                if self._bgm_mode == "sound" and self._bgm_channel is not None:
                    self._bgm_channel.set_volume(self.bgm_volume)
            except Exception:
                pass
        if persist:
            self._persist()

    def set_sfx_volume(self, v, persist=True):
        self.sfx_volume = self._clamp01(float(v))
        if persist:
            self._persist()

    def save_volumes(self):
        """拖动滑块时先不写盘（避免高频 IO），松手时调这个落盘一次。"""
        self._persist()

    def _persist(self):
        if self.save_manager is None:
            return
        try:
            # 音量是机器级设置，走 set("settings") 路由到 config（跨存档槽共享）
            self.save_manager.set("settings", {
                "bgm_volume": self.bgm_volume,
                "sfx_volume": self.sfx_volume,
            })
        except Exception:
            pass

    # ------------------------------------------------------------ 加载 / 合成
    def _find_file(self, subdir, base):
        d = os.path.join(AUDIO_DIR, subdir)
        for ext in (".ogg", ".wav", ".mp3"):
            p = os.path.join(d, base + ext)
            if os.path.exists(p):
                return p
        return None

    def _get_sound(self, name):
        if name in self._sounds:
            return self._sounds[name]
        snd = None
        path = self._find_file("sfx", name)
        if path:
            try:
                snd = pygame.mixer.Sound(path)
            except Exception:
                snd = None
        if snd is None:
            try:
                snd = pygame.mixer.Sound(buffer=_to_bytes(_recipe(name)))
            except Exception:
                snd = None
        self._sounds[name] = snd
        return snd

    def _get_bgm_sound(self, name):
        """取「已后台合成好」的 BGM Sound；尚未就绪返回 None（绝不在主线程阻塞合成）。

        成品字节缓冲转成 Sound 后即从缓冲字典移除（Sound 自带一份拷贝），省内存。"""
        if name in self._bgm_sounds:
            return self._bgm_sounds[name]
        with self._bgm_cond:
            buf = self._bgm_buffers.pop(name, None)
        if buf is None:
            return None
        try:
            snd = pygame.mixer.Sound(buffer=buf)
        except Exception:
            snd = None
        self._bgm_sounds[name] = snd
        return snd
