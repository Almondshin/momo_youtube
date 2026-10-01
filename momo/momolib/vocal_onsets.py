"""Onsets of a sung vocal stem (numpy only) — where syllables start, for lyrics_refine.

Frames: 23 ms Hann window, 5 ms hop, frame time = window centre. Two bands, because the first sound of a word
is not always a vowel:
  V  150–3500 Hz  voiced energy (vowels, nasals, glides) — where the vowel / note of a syllable starts
  H  4–10 kHz     noise (s, sh, f, th, h, t/k/p bursts) — a sung sibilant starts 60–300 ms before its vowel
Onset strength per band = half-wave-rectified spectral flux of the log magnitude (only rising energy counts),
peaks picked against a moving median + k·MAD (adaptive threshold) and gated by band level (stem bleed /
reverb tails between words stay under the gate).

An onset *time* is the rising edge, not the flux peak: from a flux peak we walk back to where the band level
was still within RISE_DB of the local minimum before it (the audible start, ~10–30 ms before the steepest rise).

Pitch (normalised autocorrelation, 40 ms): a word that follows another without a gap ("se-ven-eight" sung
legato on one note) has no level dip, only a brief loss of periodicity (its consonant) or a pitch step; a held
note has neither. `Feats.steady()` tells the two apart, so legato onsets can be kept and vibrato inside a held
note dropped.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .common import MomoError

SR = 22050
HOP = 110            # 5 ms
WIN = 512            # 23 ms
DT = HOP / SR
V_BAND = (150.0, 3500.0)
H_BAND = (4000.0, 10000.0)
GATE_DB = -38.0      # a band frame this far under the stem's loud level (p99) is silence/bleed
RISE_DB = 3.0        # onset start = last frame before the peak still within this of the local minimum
MIN_SEP = 0.06       # s between two onsets of one band
F0_WIN = 882         # 40 ms pitch frames (same hop)
F0_RANGE = (120.0, 900.0)
JUMP_DB = 10.0       # a voiced level jump this big within JUMP_S is an onset even when the flux peak is masked
JUMP_S = 0.05


@dataclass
class Feats:
    t: np.ndarray        # frame centre times (s)
    lv: np.ndarray       # V band level, dB rel. to its p99
    lh: np.ndarray       # H band level, dB rel. to its p99
    fv: np.ndarray       # V band flux (rectified)
    fh: np.ndarray       # H band flux (rectified)
    midi: np.ndarray     # pitch (MIDI note, fractional)
    conf: np.ndarray     # periodicity 0..1 (normalised autocorrelation peak)

    def idx(self, t: float) -> int:
        return int(np.clip(np.searchsorted(self.t, t), 0, len(self.t) - 1))

    def steady(self, t: float, half: float = 0.04) -> bool:
        """A held note around t: periodic throughout and no pitch step (≥ 0.5 semitone)."""
        a, b = self.idx(t - half), self.idx(t + half) + 1
        c, m = self.conf[a:b], self.midi[a:b]
        return bool(c.min() >= 0.85 and np.ptp(m) < 0.5)


@dataclass
class Onset:
    t: float        # rising-edge time (s)
    t_peak: float   # flux peak time (s)
    band: str       # "V" or "H"
    strength: float # flux at the peak / band median of peaks
    level: float    # band level 30 ms after the peak (dB rel. p99)
    rise: float     # dB the band climbs: from its minimum in the 100 ms before to 30 ms after the peak


def _pitch(x: np.ndarray, sr: int, n: int) -> tuple[np.ndarray, np.ndarray]:
    lo, hi = int(sr / F0_RANGE[1]), int(sr / F0_RANGE[0])
    w = np.hanning(F0_WIN)
    xp = np.pad(x, (0, F0_WIN))
    off = (WIN - F0_WIN) // 2          # centre the pitch frame on the spectral frame
    f0, conf = np.zeros(n), np.zeros(n)
    for s in range(0, n, 2048):
        starts = np.clip(HOP * np.arange(s, min(n, s + 2048)) + off, 0, len(x) - 1)
        fr = xp[starts[:, None] + np.arange(F0_WIN)[None, :]] * w
        fr = fr - fr.mean(1, keepdims=True)
        ac = np.fft.irfft(np.abs(np.fft.rfft(fr, 2 * F0_WIN, axis=1)) ** 2, axis=1)[:, :F0_WIN]
        ac = ac / (ac[:, :1] + 1e-12)
        k = np.argmax(ac[:, lo:hi], axis=1) + lo
        r = np.arange(len(k))
        a, b, c = ac[r, k - 1], ac[r, k], ac[r, np.minimum(k + 1, F0_WIN - 1)]
        d = np.clip(0.5 * (a - c) / (a - 2 * b + c + 1e-12), -1, 1)
        f0[s:s + len(k)], conf[s:s + len(k)] = sr / (k + d), b
    return 69 + 12 * np.log2(np.maximum(f0, 1.0) / 440.0), conf


def features(x: np.ndarray, sr: int = SR) -> Feats:
    """Band levels, flux and pitch of a mono signal at SR."""
    if len(x) < WIN + 2 * HOP:
        raise MomoError(f"보컬이 너무 짧음 ({len(x) / sr:.2f}s)")
    n = 1 + (len(x) - WIN) // HOP
    w = np.hanning(WIN).astype(np.float32)
    freqs = np.fft.rfftfreq(WIN, 1 / sr)
    vb = (freqs >= V_BAND[0]) & (freqs < V_BAND[1])
    hb = (freqs >= H_BAND[0]) & (freqs < H_BAND[1])
    pw = np.empty((n, len(freqs)), np.float32)
    for s in range(0, n, 4096):
        idx = np.arange(WIN)[None, :] + HOP * np.arange(s, min(n, s + 4096))[:, None]
        pw[s:s + len(idx)] = np.abs(np.fft.rfft(x[idx] * w, axis=1)) ** 2
    db = 10 * np.log10(pw + 1e-10)
    db = np.maximum(db, np.percentile(db, 99.5) - 80)   # floor so digital silence does not make huge flux

    def level(band):
        e = 10 * np.log10(pw[:, band].sum(1) + 1e-10)
        return e - np.percentile(e, 99)

    def flux(band):
        d = np.diff(db[:, band], axis=0, prepend=db[:1, band])
        return np.maximum(0.0, d).mean(1)

    t = (np.arange(n) * HOP + WIN / 2) / sr
    midi, conf = _pitch(x, sr, n)
    return Feats(t, level(vb), level(hb), flux(vb), flux(hb), midi, conf)


def load(path: Path) -> Feats:
    """Features of a vocal stem file (decoded mono at SR)."""
    from .audio import decode
    return features(decode(path, SR, 1)[:, 0])


def _peaks(f: np.ndarray, lvl: np.ndarray, k: float = 1.5) -> list[int]:
    """Local maxima of flux f above median + k·MAD of the surrounding 0.6 s and above the level gate."""
    half = int(0.3 / DT)
    win = np.lib.stride_tricks.sliding_window_view(np.pad(f, half, mode="edge"), 2 * half + 1)[:, ::3]
    med = np.median(win, axis=1)
    thr = med + k * (np.median(np.abs(win - med[:, None]), axis=1) + 1e-6)
    cand = np.where((f[1:-1] > f[:-2]) & (f[1:-1] >= f[2:]) & (f[1:-1] > thr[1:-1]))[0] + 1
    after = int(0.03 / DT)
    cand = [i for i in cand if lvl[min(len(lvl) - 1, i + after)] > GATE_DB]  # audible right after the rise
    sep, keep = int(MIN_SEP / DT), []
    for i in sorted(cand, key=lambda i: -f[i]):  # non-max suppression
        if all(abs(i - j) > sep for j in keep):
            keep.append(i)
    return sorted(keep)


def _rise_start(i: int, lvl: np.ndarray) -> int:
    """Walk back from a flux peak to where the band level was within RISE_DB of the minimum before it."""
    lo = max(0, i - int(0.12 / DT))
    j0 = lo + int(np.argmin(lvl[lo:i + 1]))
    j = i
    while j > j0 and lvl[j - 1] > lvl[j0] + RISE_DB:
        j -= 1
    return j


def _jumps(lvl: np.ndarray) -> list[int]:
    """Frames where the band level climbs ≥ JUMP_DB over JUMP_S (steepest point of each climb)."""
    h = max(1, int(JUMP_S / DT / 2))
    d = np.zeros_like(lvl)
    d[h:-h] = lvl[2 * h:] - lvl[:-2 * h]
    cand = np.flatnonzero((d[1:-1] >= JUMP_DB) & (d[1:-1] >= d[:-2]) & (d[1:-1] > d[2:])) + 1
    sep, keep = int(MIN_SEP / DT), []
    for i in sorted(cand, key=lambda i: -d[i]):
        if all(abs(i - j) > sep for j in keep):
            keep.append(i)
    return sorted(keep)


def detect(fe: Feats) -> list[Onset]:
    """Onsets of both bands, time-sorted: flux peaks, plus steep level climbs of the voiced band (a flux peak can
    be masked by the consonant noise right before a vowel in a busy stretch)."""
    out: list[Onset] = []
    after, back = int(0.03 / DT), int(0.10 / DT)
    for band, f, lvl in (("V", fe.fv, fe.lv), ("H", fe.fh, fe.lh)):
        pk = _peaks(f, lvl)
        norm = float(np.median(f[pk])) if pk else 1.0
        if band == "V":
            pk = sorted(set(pk) | {i for i in _jumps(lvl) if lvl[min(len(lvl) - 1, i + after)] > GATE_DB})
        for i in pk:
            lv_after = float(lvl[min(len(lvl) - 1, i + after)])
            out.append(Onset(float(fe.t[_rise_start(i, lvl)]), float(fe.t[i]), band, float(f[i] / norm), lv_after,
                             lv_after - float(lvl[max(0, i - back):i + 1].min())))
    out.sort(key=lambda o: o.t)
    return out
