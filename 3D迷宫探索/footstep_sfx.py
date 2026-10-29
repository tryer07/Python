# 脚步声音效合成器 —— 纯标准库（wave/struct/math/random），无需任何外部音频文件
# 在首次运行时生成 walk.wav / run.wav 到 assets/ 目录，之后直接复用

import math
import os
import random
import struct
import wave

SAMPLE_RATE = 22050


def _write_wave(path: str, samples: list[int]) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        frames = struct.pack("<" + "h" * len(samples), *samples)
        w.writeframes(frames)


def _synthesize(dur: float, thump_hz: float, noise_amp: float, decay: float) -> list[int]:
    """低频砰击 + 高频沙沙噪声叠加，指数衰减，得到一个短促的脚步声"""
    n = int(SAMPLE_RATE * dur)
    samples: list[int] = []
    prev = 0.0
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.exp(-decay * t)
        thump = math.sin(2 * math.pi * thump_hz * t)
        # 一阶低通的白噪声，模拟鞋底摩擦的沙沙声
        white = random.uniform(-1.0, 1.0)
        prev = prev * 0.6 + white * 0.4
        scratch = prev * noise_amp
        v = (thump * 0.6 + scratch) * env
        v = max(-1.0, min(1.0, v))
        samples.append(int(v * 32767 * 0.6))
    return samples


def ensure_footstep_sfx(assets_dir: str) -> dict[str, str]:
    """生成并返回 {walk, run} 两个 wav 的绝对路径；已存在则跳过生成"""
    os.makedirs(assets_dir, exist_ok=True)
    paths = {
        "walk": os.path.join(assets_dir, "footstep_walk.wav"),
        "run": os.path.join(assets_dir, "footstep_run.wav"),
    }
    if not os.path.exists(paths["walk"]):
        _write_wave(paths["walk"], _synthesize(dur=0.10, thump_hz=95, noise_amp=0.5, decay=28))
    if not os.path.exists(paths["run"]):
        _write_wave(paths["run"], _synthesize(dur=0.08, thump_hz=120, noise_amp=0.7, decay=36))
    return paths


if __name__ == "__main__":
    here = os.path.join(os.path.dirname(__file__), "assets")
    p = ensure_footstep_sfx(here)
    for name, fp in p.items():
        print(name, "->", fp, os.path.getsize(fp), "bytes")
