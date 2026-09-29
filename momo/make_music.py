#!/usr/bin/env python3
"""Original BGM loop + sound effects, synthesized with numpy (no samples, no third-party music).

Everything is generated from code, so the result is the channel's own work — no license terms,
no Content ID claims. Output is deterministic (fixed seed): re-running gives identical files.

BGM "Momo's Morning" — 104 BPM, C major, 24 bars (A · B · A' with glockenspiel doubling), rendered
three times through the reverb and cut from the middle pass, so it loops without a seam.
Instruments: ukulele strum (Karplus-Strong), marimba melody with rolls, soft bass, kick, clap,
shaker, glockenspiel sparkles at phrase ends.

SFX (assets/sfx/*.wav): pop, sparkle, boing, whoosh, brush, swish, splash, chime.

  python momo/make_music.py                 # BGM + SFX into assets/bgm, assets/sfx
  python momo/make_music.py --only sfx      # just the sound effects
  python momo/make_music.py --out /tmp/x    # write <out>/bgm, <out>/sfx instead (tests)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import add_root_arg, get_paths, main_wrapper  # noqa: E402

SR = 48000
BPM = 104
BEAT = 60.0 / BPM
BAR = 4 * BEAT
BGM_NAME = "momo_morning"

# ---------------------------------------------------------------- music data

# chord per bar: (ukulele voicing GCEA as midi, bass root midi)
CHORDS = {
    "C": ([67, 60, 64, 72], 36),
    "G": ([67, 62, 67, 71], 43),
    "Am": ([69, 60, 64, 69], 45),
    "F": ([69, 60, 65, 69], 41),
    "Em": ([67, 64, 67, 71], 40),
}
PROG_A = ["C", "G", "Am", "F", "C", "F", "G", "C"]
PROG_B = ["F", "G", "Em", "Am", "F", "G", "C", "C"]

# melody per bar: (beat offset, length in beats, midi)
MEL_A = [
    [(0, 1, 67), (1, 1, 64), (2, 1, 67), (3, 1, 72)],
    [(0, 1, 71), (1, 1, 74), (2, 1, 71), (3, 1, 67)],
    [(0, 1, 69), (1, 1, 72), (2, 1, 76), (3, 1, 72)],
    [(0, 2, 69), (2, 1, 67), (3, 1, 65)],
    [(0, 1, 64), (1, 1, 67), (2, 1, 72), (3, 1, 76)],
    [(0, 1, 77), (1, 1, 76), (2, 1, 74), (3, 1, 72)],
    [(0, 2, 74), (2, 1, 71), (3, 1, 67)],
    [(0, 3, 72)],
]
MEL_B = [
    [(0, 1, 72), (1, 1, 69), (2, 1, 72), (3, 1, 77)],
    [(0, 1, 74), (1, 1, 71), (2, 1, 74), (3, 1, 79)],
    [(0, 1, 76), (1, 1, 74), (2, 1, 71), (3, 1, 67)],
    [(0, 1, 69), (1, 1, 72), (2, 2, 76)],
    [(0, 1, 77), (1, 1, 76), (2, 1, 72), (3, 1, 69)],
    [(0, 1, 67), (1, 1, 71), (2, 1, 74), (3, 1, 77)],
    [(0, 2, 76), (2, 2, 74)],
    [(0, 4, 72)],
]
# ukulele island strum: (beat, down?)
STRUM = [(0.0, True), (1.0, True), (1.5, False), (2.5, False), (3.0, True), (3.5, False)]
SPARKLE_BARS = {3, 7, 11, 15, 19, 23}  # 0-based bars ending a phrase


def hz(m: float) -> float:
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def t_axis(dur: float) -> np.ndarray:
    return np.arange(int(round(dur * SR))) / SR


def fft_filter(x: np.ndarray, lo: float | None = None, hi: float | None = None, soft: float = 0.25) -> np.ndarray:
    """Band-limit a (short) signal in the frequency domain with smooth edges."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1.0 / (1.0 + (lo / np.maximum(f, 1e-3)) ** (2 / soft))
    if hi:
        g *= 1.0 / (1.0 + (f / hi) ** (2 / soft))
    return np.fft.irfft(X * g, n)


def pan(x: np.ndarray, p: float) -> np.ndarray:
    a = (p + 1.0) * np.pi / 4.0
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def add(buf: np.ndarray, x: np.ndarray, at: float) -> None:
    i = int(round(at * SR))
    if i < 0:  # humanize jitter before t=0
        x, i = x[-i:], 0
    if i >= len(buf) or not len(x):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i]


# ---------------------------------------------------------------- instruments

def marimba(m: float, dur: float = 1.6) -> np.ndarray:
    f = hz(m)
    t = t_axis(dur)
    tau = 0.18 + 0.45 * (440.0 / f) ** 0.7
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
         + 0.30 * np.sin(2 * np.pi * 3.93 * f * t) * np.exp(-t / (tau * 0.35))
         + 0.10 * np.sin(2 * np.pi * 9.2 * f * t) * np.exp(-t / (tau * 0.12)))
    x *= np.minimum(1.0, t / 0.002)
    click = fft_filter(RNG.standard_normal(int(0.006 * SR)), 800, 4000) * np.hanning(int(0.006 * SR))
    x[: len(click)] += 0.08 * click
    return x


def glock(m: float, dur: float = 2.0) -> np.ndarray:
    f = hz(m)
    t = t_axis(dur)
    x = np.zeros_like(t)
    for ratio, amp, tau in ((1.0, 1.0, 1.1), (2.76, 0.40, 0.45), (5.40, 0.22, 0.2), (8.93, 0.10, 0.1)):
        x += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / tau)
    return x * np.minimum(1.0, t / 0.001)


_PLUCK: dict[int, np.ndarray] = {}


def pluck(m: int, dur: float = 1.4) -> np.ndarray:
    """Karplus-Strong, computed one delay-line period at a time (vectorised)."""
    if m in _PLUCK:
        return _PLUCK[m]
    N = int(round(SR / hz(m) - 0.5))
    n = int(dur * SR)
    y = np.zeros(n + N + 1)
    burst = RNG.uniform(-1, 1, N + 1)
    y[: N + 1] = np.convolve(burst, np.ones(3) / 3, mode="same")  # softer nylon-like attack
    d = 0.996
    i = N + 1
    while i < len(y):
        j = min(i + N, len(y))
        y[i:j] = d * 0.5 * (y[i - N:j - N] + y[i - N - 1:j - N - 1])
        i = j
    out = y[N + 1:]
    out = out / (np.max(np.abs(out)) + 1e-9)
    out *= np.exp(-np.arange(len(out)) / SR / 0.9)
    _PLUCK[m] = out
    return out


def bass(m: int, beats: float) -> np.ndarray:
    f = hz(m)
    dur = beats * BEAT
    t = t_axis(dur + 0.08)
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
    env = np.minimum(1.0, t / 0.012) * np.exp(-t / 0.7)
    env *= np.clip((dur + 0.08 - t) / 0.08, 0, 1)
    return np.tanh(1.3 * x * env) / np.tanh(1.3)


def kick() -> np.ndarray:
    t = t_axis(0.2)
    f = 62 + 70 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.08) * np.minimum(1.0, t / 0.002)


def clap() -> np.ndarray:
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    noise = fft_filter(RNG.standard_normal(n), 1100, 3500)
    env = np.zeros(n)
    for k, off in enumerate((0.0, 0.009, 0.018)):
        env += np.where(t >= off, np.exp(-(t - off) / (0.006 if k < 2 else 0.05)), 0.0)
    x = noise * env
    return x / (np.max(np.abs(x)) + 1e-9)


def shaker() -> np.ndarray:
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    x = fft_filter(RNG.standard_normal(n), 5000, 12000) * np.minimum(1.0, t / 0.008) * np.exp(-t / 0.03)
    return x / (np.max(np.abs(x)) + 1e-9)


def reverb_ir(seconds: float = 1.6, rt60: float = 0.9) -> np.ndarray:
    t = t_axis(seconds)
    decay = np.exp(-6.9 * t / rt60)
    irs = []
    for _ in range(2):
        ir = fft_filter(RNG.standard_normal(len(t)), 200, 6500) * decay
        for dt, g in ((0.011, 0.5), (0.019, 0.4), (0.027, 0.3), (0.041, 0.25)):
            ir[int(dt * SR)] += g * (1 if RNG.random() > 0.5 else -1)
        ir[: int(0.005 * SR)] = 0.0
        irs.append(ir / np.sqrt(np.sum(ir ** 2)))
    return np.stack(irs, axis=1)


def convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    n = len(x) + len(ir) - 1
    size = 1 << (n - 1).bit_length()
    out = np.zeros((n, 2))
    for c in range(2):
        out[:, c] = np.fft.irfft(np.fft.rfft(x[:, c], size) * np.fft.rfft(ir[:, c], size), size)[:n]
    return out


# ---------------------------------------------------------------- BGM

def humanize(at: float, spread: float = 0.004) -> float:
    return at + float(RNG.normal(0.0, spread))


def vel(base: float, spread: float = 0.08) -> float:
    return base * (1.0 + float(RNG.uniform(-spread, spread)))


def render_cycle(buf_dry: dict[str, np.ndarray], t0: float) -> None:
    """One 24-bar pass (A · B · A') starting at t0, into per-bus stereo buffers."""
    bars = [(c, mel, False) for c, mel in zip(PROG_A, MEL_A)]
    bars += [(c, mel, False) for c, mel in zip(PROG_B, MEL_B)]
    bars += [(c, mel, True) for c, mel in zip(PROG_A, MEL_A)]
    for b, (chord, mel, doubled) in enumerate(bars):
        ts = t0 + b * BAR
        voicing, root = CHORDS[chord]
        # ukulele strum (down = G→A string order, up = reverse, 11 ms between strings)
        for beat, down in STRUM:
            order = voicing if down else voicing[::-1]
            v = vel(0.9 if down else 0.6)
            for k, m in enumerate(order):
                add(buf_dry["uke"], pan(pluck(m) * v * 0.55, -0.35), humanize(ts + beat * BEAT + k * 0.011))
        # bass: root (1.5) · fifth (1) · root (1)
        for beat, length, step in ((0, 1.5, 0), (2, 1.0, 7), (3, 1.0, 0)):
            add(buf_dry["bass"], pan(bass(root + step, length) * vel(0.8), 0.0), ts + beat * BEAT)
        # drums
        for beat in (0, 2):
            add(buf_dry["drums"], pan(kick() * 0.6, 0.0), ts + beat * BEAT)
        for beat in (1, 3):
            add(buf_dry["drums"], pan(clap() * vel(0.28), 0.05), humanize(ts + beat * BEAT, 0.003))
        for k in range(8):
            add(buf_dry["drums"], pan(shaker() * vel(0.10 if k % 2 else 0.06), 0.4 if k % 2 else -0.4),
                humanize(ts + k * BEAT / 2, 0.005))
        # marimba melody (+ soft lower octave), rolls on notes of 2+ beats
        for beat, length, m in mel:
            at = ts + beat * BEAT
            if length >= 2:
                n_roll = int(length * 4) - 1
                for r in range(n_roll):
                    a = 0.55 if r == 0 else 0.22 * (1 - r / n_roll) + 0.12
                    add(buf_dry["mel"], pan(marimba(m) * vel(a, 0.12), 0.15), humanize(at + r * BEAT / 4, 0.006))
            else:
                add(buf_dry["mel"], pan(marimba(m) * vel(0.55), 0.15), humanize(at))
            add(buf_dry["mel"], pan(marimba(m - 12) * vel(0.16), 0.1), humanize(at))
            if doubled:
                add(buf_dry["glock"], pan(glock(m + 12) * vel(0.16), 0.35), humanize(at))
        if b in SPARKLE_BARS:
            top = voicing[1] + 24
            for k, step in enumerate((0, 4, 7, 12)):
                add(buf_dry["glock"], pan(glock(top + step) * 0.18, 0.4), ts + 3 * BEAT + k * BEAT / 4)


def make_bgm() -> np.ndarray:
    cycle = 24 * BAR
    n = int(round(3 * cycle * SR)) + SR * 2
    buses = {k: np.zeros((n, 2)) for k in ("uke", "bass", "drums", "mel", "glock")}
    for c in range(3):
        render_cycle(buses, c * cycle)
    gains = {"uke": 0.30, "bass": 0.26, "drums": 0.40, "mel": 0.46, "glock": 0.30}
    sends = {"uke": 0.22, "bass": 0.04, "drums": 0.08, "mel": 0.25, "glock": 0.35}
    dry = sum(buses[k] * gains[k] for k in buses)
    wet_in = sum(buses[k] * gains[k] * sends[k] for k in buses)
    wet = convolve(wet_in, reverb_ir())[:n]
    mix = dry + wet
    i0 = int(round(cycle * SR))
    loop = mix[i0: i0 + int(round(cycle * SR))]   # middle pass: reverb tails of the previous pass included
    loop = np.stack([fft_filter(loop[:, c], 50, None, 0.5) for c in range(2)], axis=1)  # no sub rumble on small speakers
    loop = np.tanh(loop / (np.max(np.abs(loop)) + 1e-9) * 1.1) / np.tanh(1.1)
    return loop * 10 ** (-3 / 20)


# ---------------------------------------------------------------- SFX

def sfx_pop() -> np.ndarray:
    t = t_axis(0.16)
    f = 380 * (950 / 380) ** np.minimum(1.0, t / 0.06)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.2 * np.sin(2 * ph)) * np.minimum(1.0, t / 0.003) * np.exp(-t / 0.045)
    return pan(x, 0.0)


def sfx_sparkle() -> np.ndarray:
    out = np.zeros((int(1.6 * SR), 2))
    for k, m in enumerate((84, 88, 91, 96, 100)):
        add(out, pan(glock(m, 1.4) * (0.6 - k * 0.06), -0.4 + k * 0.2), k * 0.05)
    n = len(out)
    shimmer = fft_filter(RNG.standard_normal(n), 7000, 14000) * np.exp(-np.arange(n) / SR / 0.35) * 0.05
    out += pan(shimmer, 0.2)
    return out + 0.25 * convolve(out, reverb_ir(1.2, 0.8))[:n]


def sfx_boing() -> np.ndarray:
    t = t_axis(0.7)
    f = 150 + 190 * np.exp(-t / 0.10)
    f *= 1 + 0.12 * np.sin(2 * np.pi * 13 * t) * np.exp(-t / 0.3)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.minimum(1.0, t / 0.004) * np.exp(-t / 0.28)
    return pan(np.tanh(1.5 * x), 0.0)


def moving_band(n: int, fc, width: float = 0.5) -> np.ndarray:
    """Noise through a band-pass whose centre follows fc(t_normalised) — STFT overlap-add."""
    frame, hop = 1024, 256
    x = RNG.standard_normal(n + frame)
    out = np.zeros(n + frame)
    win = np.hanning(frame)
    f = np.fft.rfftfreq(frame, 1.0 / SR)
    for s in range(0, n, hop):
        c = fc(s / n)
        g = np.exp(-0.5 * (np.log(np.maximum(f, 1.0) / c) / width) ** 2)
        out[s:s + frame] += np.fft.irfft(np.fft.rfft(x[s:s + frame] * win) * g, frame) * win
    return out[:n]


def sfx_whoosh() -> np.ndarray:
    n = int(0.7 * SR)
    x = moving_band(n, lambda p: 350 * (2600 / 350) ** np.sin(np.pi * min(p, 1.0) * 0.9), 0.55)
    x *= np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    return np.stack([x * np.linspace(1.0, 0.4, n), x * np.linspace(0.4, 1.0, n)], axis=1)


def sfx_brush() -> np.ndarray:
    n = int(1.3 * SR)
    x = np.zeros(n)
    for k in range(7):
        m = int(0.16 * SR)
        burst = fft_filter(RNG.standard_normal(m), 2500 if k % 2 else 3200, 9000) * np.sin(np.pi * np.linspace(0, 1, m)) ** 2
        add(x, burst * (0.8 if k % 2 else 1.0), k * 0.17)
    return pan(x, 0.0)


def sfx_swish() -> np.ndarray:
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    body = moving_band(n, lambda p: 500 + 350 * np.sin(2 * np.pi * 3.0 * p * 1.4), 0.6)
    body *= (0.6 + 0.4 * np.sin(2 * np.pi * 3.0 * t)) * np.sin(np.pi * t / t[-1])
    out = pan(body, -0.1)
    for _ in range(9):
        at = float(RNG.uniform(0.1, 1.2))
        bt = t_axis(0.05)
        f0 = float(RNG.uniform(350, 700))
        blip = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 2.5 * bt / bt[-1])) / SR) * np.sin(np.pi * bt / bt[-1])
        add(out, pan(blip * 0.25, float(RNG.uniform(-0.5, 0.5))), at)
    return out


def sfx_splash() -> np.ndarray:
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    x = fft_filter(RNG.standard_normal(n), 700, 5000) * np.minimum(1.0, t / 0.004) * np.exp(-t / 0.12)
    pt = int(0.012 * SR)
    x[:pt] += np.hanning(pt) * 0.8
    out = pan(x, 0.0)
    for _ in range(5):
        bt = t_axis(0.035)
        f0 = float(RNG.uniform(900, 1600))
        drop = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 1.5 * bt / bt[-1])) / SR) * np.sin(np.pi * bt / bt[-1])
        add(out, pan(drop * 0.2, float(RNG.uniform(-0.6, 0.6))), float(RNG.uniform(0.1, 0.45)))
    return out


def sfx_chime() -> np.ndarray:
    out = np.zeros((int(1.6 * SR), 2))
    add(out, pan(glock(91, 1.5) * 0.6, -0.2), 0.0)
    add(out, pan(glock(96, 1.5) * 0.6, 0.2), 0.12)
    return out + 0.25 * convolve(out, reverb_ir(1.2, 0.8))[: len(out)]


SFX = {"pop": sfx_pop, "sparkle": sfx_sparkle, "boing": sfx_boing, "whoosh": sfx_whoosh,
       "brush": sfx_brush, "swish": sfx_swish, "splash": sfx_splash, "chime": sfx_chime}


# ---------------------------------------------------------------- output

def write_wav(path: Path, x: np.ndarray, peak_db: float = -3.0, fade_out: bool = True) -> Path:
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (peak_db / 20)
    fade = min(len(x) // 4, int(0.004 * SR)) if fade_out else 0  # a loop must not dip at its seam
    if fade:
        x[-fade:] *= np.linspace(1.0, 0.0, fade)[:, None]
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def encode_bgm(wav: Path, dst: Path) -> Path:
    """FLAC: lossless and sample-exact (AAC pads ~20 ms, which would put a gap in every loop).
    Keeps the wav when ffmpeg is missing."""
    if not shutil.which("ffmpeg"):
        return wav
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "flac", str(dst)], check=True)
    wav.unlink()
    return dst


RNG = np.random.default_rng(20260929)


def main() -> int:
    global RNG
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_root_arg(ap)
    ap.add_argument("--only", choices=["bgm", "sfx"], help="make just one of the two")
    ap.add_argument("--out", help="write <out>/bgm and <out>/sfx instead of assets/")
    args = ap.parse_args()
    paths = get_paths(args)
    bgm_dir = Path(args.out) / "bgm" if args.out else paths.bgm
    sfx_dir = Path(args.out) / "sfx" if args.out else paths.sfx
    if args.only != "sfx":
        RNG = np.random.default_rng(20260929)
        loop = make_bgm()
        wav = write_wav(bgm_dir / f"{BGM_NAME}.wav", loop, -1.0, fade_out=False)
        out = encode_bgm(wav, bgm_dir / f"{BGM_NAME}.flac")
        print(f"✔ BGM {out} ({len(loop) / SR:.1f}s loop, {BPM} BPM)")
    if args.only != "bgm":
        for name, fn in SFX.items():
            RNG = np.random.default_rng(sum(map(ord, name)))  # per-effect seed: stable when the list changes
            print(f"✔ SFX {write_wav(sfx_dir / f'{name}.wav', fn())}")
    return 0


if __name__ == "__main__":
    main_wrapper(main)
