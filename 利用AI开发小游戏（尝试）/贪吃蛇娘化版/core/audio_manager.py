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
from array import array

import pygame

from settings import (
    AUDIO_CHANNELS, AUDIO_DIR, AUDIO_ENABLED, BGM_FADE_MS,
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
    out = [0.0] * n
    a = int(attack * SAMPLE_RATE)
    r = int(release * SAMPLE_RATE)
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
    out = []
    for s in segments:
        out.extend(s)
    return out


def _mix(tracks):
    """叠加多轨（自动补零到等长）。"""
    if not tracks:
        return []
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    return out


def _to_bytes(samples):
    """float 采样列表 -> 16-bit 立体声 interleaved 字节流（匹配 mixer 格式）。"""
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


def _bgm_recipe(name):
    """兜底 BGM：约 4 秒柔和琶音循环（真实文件存在时不会用到）。
    不同场景用略微不同的和弦走向，做一点区分。"""
    if name == "battle":
        chords = [("A3", "C4", "E4"), ("A3", "C4", "E4"),
                  ("F3", "A3", "C4"), ("G3", "B3", "D4")]
        note_dur = 0.16
    elif name == "boss":
        # 更急促、更紧张的循环：小调走向 + 短音，营造 Boss 战压迫感
        chords = [("A3", "C4", "E4"), ("G3", "B3", "D4"),
                  ("F3", "A3", "C4"), ("E3", "G3", "B3")]
        note_dur = 0.11
    elif name == "gacha":
        chords = [("C4", "E4", "G4"), ("A3", "C4", "E4"),
                  ("F3", "A3", "C4"), ("G3", "B3", "D4")]
        note_dur = 0.20
    elif name == "gameover":
        chords = [("A3", "C4", "E4"), ("F3", "A3", "C4"),
                  ("D3", "F3", "A3"), ("C3", "E3", "G3")]
        note_dur = 0.30
    else:  # menu
        chords = [("A3", "C4", "E4"), ("F3", "A3", "C4"),
                  ("C4", "E4", "G4"), ("G3", "B3", "D4")]
        note_dur = 0.22

    lead = []
    for (a, b, c) in chords:
        for f in (a, b, c, b):
            lead.extend(_tone(N[f], note_dur, "sine", 0.15, release=note_dur * 0.5))
    bass = []
    for (a, _b, _c) in chords:
        seg_len = note_dur * 4
        bass.extend(_tone(N[a] / 2, seg_len * 0.9, "sine", 0.11, release=seg_len * 0.3))
    return _mix([lead, bass])


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
    }

    def __init__(self, save_manager=None):
        global _INSTANCE
        _INSTANCE = self

        self.save_manager = save_manager
        self._sounds = {}          # 逻辑名 -> Sound（SFX）
        self._bgm_sounds = {}      # 逻辑名 -> Sound（合成兜底 BGM）
        self._last_play = {}       # 逻辑名 -> 上次播放时刻（节流用）
        self._current_bgm = None
        self._bgm_channel = None
        self._bgm_mode = None      # "music" | "sound" | None
        self._enabled = AUDIO_ENABLED

        self._ok = False
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(AUDIO_CHANNELS)
                self._ok = True
        except Exception:
            self._ok = False

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

    @staticmethod
    def _clamp01(v):
        return max(0.0, min(1.0, v))

    # ------------------------------------------------------------ SFX
    def play(self, name, volume=1.0, throttle=0.0):
        """播放一个音效。throttle>0 时对同名音效做最小间隔节流（秒）。"""
        if not (self._ok and self._enabled):
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
        """切换 BGM。同名幂等（直接返回），避免场景重进 / 拖窗口时反复重启音乐。"""
        if not (self._ok and self._enabled):
            return
        if self._current_bgm == name:
            return
        self._current_bgm = name
        self._stop_internal(0)

        path = self._find_file("bgm", self.BGM_FILES.get(name, name))
        if path:
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self.bgm_volume)
                pygame.mixer.music.play(-1, fade_ms=fade_ms)
                self._bgm_mode = "music"
                return
            except Exception:
                pass
        snd = self._get_bgm_sound(name)
        if snd is not None:
            try:
                snd.set_volume(self._clamp01(self.bgm_volume))
                self._bgm_channel = snd.play(-1)
                self._bgm_mode = "sound"
            except Exception:
                pass

    def stop_bgm(self, fade_ms=BGM_FADE_MS):
        if not self._ok:
            return
        self._current_bgm = None
        self._stop_internal(fade_ms)

    def _stop_internal(self, fade_ms=0):
        try:
            if self._bgm_mode == "music":
                if fade_ms > 0:
                    pygame.mixer.music.fadeout(fade_ms)
                else:
                    pygame.mixer.music.stop()
            elif self._bgm_channel is not None:
                self._bgm_channel.stop()
        except Exception:
            pass
        self._bgm_channel = None
        self._bgm_mode = None

    # ------------------------------------------------------------ 音量
    def set_bgm_volume(self, v, persist=True):
        self.bgm_volume = self._clamp01(float(v))
        if self._ok:
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
            st = self.save_manager.data.setdefault("settings", {})
            st["bgm_volume"] = self.bgm_volume
            st["sfx_volume"] = self.sfx_volume
            self.save_manager.save()
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
        if name in self._bgm_sounds:
            return self._bgm_sounds[name]
        snd = None
        try:
            snd = pygame.mixer.Sound(buffer=_to_bytes(_bgm_recipe(name)))
        except Exception:
            snd = None
        self._bgm_sounds[name] = snd
        return snd
