"""Lip-sync meter for finished-song episodes: how late Momo's mouth is against the sung vocal, per shot.

Per singing shot of the built timeline (own lip-sync clips + clip_from reuses of them):
  mouth(t) = share of mouth-interior pixels (dark, or saturated red) in a box under Momo's eye pair
             (onmodel.eye_pair per frame at the clip's own frame rate; box scaled by the eye distance)
  voice(t) = RMS loudness of the vocal stem at the same SONG time
             (= track.start + cut start + hold0 + clip time − clip_offset)
  lag      = argmax_L corr(mouth(t), voice(t − L)), L in −500…+500 ms, parabolic peak; + = mouth LATE.
Confidence: r (peak Pearson), margin = r − best r more than 150 ms away (beats are ~470 ms apart, so a peak one
beat off is the usual ambiguity), halves = two sub-windows whose lags must agree within HALVES_MS.
Diagnostics: self = mouth vs the clip's own audio track (the lip-sync model's own lag), audio = clip audio vs the
stem at this placement less the intended lip_shift (placement error; ~0 when the timeline is right).

What it can and cannot tell: the slope is validated (picture delayed +200 ms → the lag reads +199 ms median,
−167 ms → −167 ms on ep04), the absolute zero is not — "dark pixels under the eyes" vs loudness need not peak at
0 ms for a natural mouth. So the target is the middle of the tolerance window (OK_MS, after ITU-R BT.1359: sound
may trail the picture ~125 ms, lead it ~45 ms), and a lip_shift is suggested only for confident shots.
numpy + PIL + ffmpeg only.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np

from . import onmodel
from .common import MomoError, probe

HOP = 0.01                       # analysis grid (s)
LAGS = np.arange(-50, 51) * HOP  # −500 … +500 ms
SR = 16000
OK_MS = (-120, 40)               # verdict "ok" window (ms, + = mouth late)
TARGET_MS = -70                  # lip_shift suggestions aim here (middle of OK_MS)
MAX_MS = 300                     # a larger lag is not believed
HALVES_MS = 80
LIP_SHIFT_MAX = 0.5              # = manifest cut.lip_shift limit
CACHE_V = 1


def eye_frame(rgb: np.ndarray) -> tuple[float, float, float] | None:
    """(x, y) between Momo's eyes and the eye distance, or None."""
    pair = onmodel.eye_pair(rgb)
    if pair is None:
        return None
    e, f = pair
    return (e[0] + f[0]) / 2, (e[1] + f[1]) / 2, math.hypot(e[0] - f[0], e[1] - f[1])


def mouth_open(rgb: np.ndarray, x: float, y: float, d: float) -> float:
    """Share of dark / saturated-red pixels in the mouth box under the eyes (0 … 1), NaN for an empty box."""
    box = rgb[max(0, int(y + 0.38 * d)):max(0, int(y + 1.0 * d)), max(0, int(x - 0.45 * d)):max(0, int(x + 0.45 * d))]
    if not box.size:
        return math.nan
    h, s, v = onmodel.hsv(box)
    return float(((v < 0.45) | ((s > 0.35) & ((h < 20) | (h > 330)))).mean())


def _frames(path: Path):
    info = probe(path)
    w, h = info.width, info.height
    if not (w and h and info.fps):
        raise MomoError(f"영상 스트림을 읽을 수 없음: {path}")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-"], stdout=subprocess.PIPE)
    try:
        while len(b := p.stdout.read(w * h * 3)) == w * h * 3:
            yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    finally:
        p.stdout.close()
        p.wait()


def mouth_series(path: Path, cache: Path | None = None) -> tuple[np.ndarray, np.ndarray, float]:
    """(frame times in clip seconds, mouth openness per frame, share of frames with the eye pair found).

    Missed frames are filled from their neighbours, then a 5-frame rolling median steadies the eye position.
    Cached per clip file (size + mtime) when cache is a folder."""
    st = path.stat()
    ck = cache / f"mouth_v{CACHE_V}_{path.stem}_{st.st_size}_{st.st_mtime_ns}.npz" if cache else None
    if ck is not None and ck.exists():
        z = np.load(ck)
        return z["t"], z["m"], float(z["found"])
    fps = probe(path).fps
    frames = list(_frames(path))
    if not frames:
        raise MomoError(f"프레임을 읽지 못함: {path}")
    eyes = np.array([eye_frame(f) or (np.nan,) * 3 for f in frames], float)
    ok = np.isfinite(eyes[:, 0])
    found = float(ok.mean())
    if ok.sum() >= 2:
        idx = np.arange(len(eyes))
        for j in range(3):
            eyes[:, j] = np.interp(idx, idx[ok], eyes[ok, j])
        eyes = np.array([np.median(eyes[max(0, i - 2):i + 3], 0) for i in idx])
    m = np.array([mouth_open(f, *e) if np.isfinite(e[2]) else np.nan for f, e in zip(frames, eyes)])
    t = np.arange(len(frames)) / fps
    if ck is not None:
        ck.parent.mkdir(parents=True, exist_ok=True)
        np.savez(ck, t=t, m=m, found=found)
    return t, m, found


def envelope(x: np.ndarray, sr: int = SR) -> np.ndarray:
    """RMS loudness on the HOP grid (sample i centred at (i + 0.5)·HOP), 30 ms smoothing."""
    k = int(sr * HOP)
    n = len(x) // k
    e = np.sqrt((x[:n * k].reshape(n, k).astype(np.float64) ** 2).mean(1))
    return np.convolve(e, np.ones(3) / 3, "same")


def audio_env(path: Path) -> np.ndarray:
    from .audio import decode
    return envelope(decode(path, SR, 1)[:, 0])


def env_at(env: np.ndarray, t: np.ndarray) -> np.ndarray:
    return np.interp(t, (np.arange(len(env)) + 0.5) * HOP, env, left=0.0, right=0.0)


def lag_of(ts: np.ndarray, sig: np.ndarray, env: np.ndarray, a: float, b: float) -> dict:
    """Best L (s) with sig(t) ~ env(t − L) over song time [a, b]; ts = song time of each sig sample.
    → {"lag_ms", "r", "margin", "alt_ms", "conf": high|medium|low|none, "n_s"}."""
    ok = np.isfinite(sig)
    grid = np.arange(a, b, HOP)
    if ok.sum() < 10 or len(grid) < 40:
        return {"lag_ms": None, "r": None, "margin": None, "alt_ms": None, "conf": "none", "n_s": round(b - a, 2)}
    m = np.interp(grid, ts[ok], sig[ok])
    with np.errstate(invalid="ignore", divide="ignore"):
        rs = np.array([np.corrcoef(m, env_at(env, grid - L))[0, 1] for L in LAGS])
    rs = np.nan_to_num(rs, nan=-1.0)
    i = int(np.argmax(rs))
    d = 0.0
    if 0 < i < len(rs) - 1 and (den := rs[i - 1] - 2 * rs[i] + rs[i + 1]) < 0:
        d = 0.5 * (rs[i - 1] - rs[i + 1]) / den
    far = np.abs(LAGS - LAGS[i]) > 0.15
    j = int(np.argmax(np.where(far, rs, -9)))
    r, margin = float(rs[i]), float(rs[i] - rs[j])
    conf = ("low" if r < 0.3 or margin < 0.05 or i in (0, len(rs) - 1) else
            "high" if r >= 0.5 and margin >= 0.15 else "medium")
    return {"lag_ms": int(round((LAGS[i] + d * HOP) * 1000)), "r": round(r, 2), "margin": round(margin, 2),
            "alt_ms": int(round(LAGS[j] * 1000)), "conf": conf, "n_s": round(b - a, 2)}


def verdict(shown: dict, halves: list[dict]) -> str:
    """ok (inside OK_MS) | fix (outside, and the reading is stable) | unreliable."""
    lag, h = shown.get("lag_ms"), [x.get("lag_ms") for x in halves]
    if lag is None or shown["conf"] in ("low", "none") or abs(lag) > MAX_MS or None in h \
            or abs(h[0] - h[1]) > HALVES_MS:
        return "unreliable"
    return "ok" if OK_MS[0] <= lag <= OK_MS[1] else "fix"


def suggest(lag_ms: float, current: float, fps: int) -> float:
    """lip_shift (s, + = picture later) that moves a measured lag to TARGET_MS, on whole frames."""
    ls = current + (TARGET_MS - lag_ms) / 1000.0
    ls = round(ls * fps) / fps
    return round(max(-LIP_SHIFT_MAX, min(LIP_SHIFT_MAX, ls)), 3)


def shots(timeline: dict, manifest: dict, root: Path) -> list[dict]:
    """Singing shots of a built timeline: own lip-sync clips and clip_from reuses of them."""
    mc = {c["id"]: c for c in manifest.get("cuts") or []}
    t_start = float(((manifest.get("song") or {}).get("track") or {}).get("start") or 0.0)
    out = []
    for c in timeline.get("cuts") or []:
        m = mc.get(c["id"]) or {}
        src = ((m.get("clip_from") or {}) if isinstance(m.get("clip_from"), dict) else {}).get("cut")
        own = bool(m.get("lipsync")) and not src
        if not (own or (src and (mc.get(src) or {}).get("lipsync"))) or c.get("source_kind") != "video" \
                or not c.get("source"):
            continue
        hold0 = c["hold0"] if "hold0" in c else (float(c.get("nar_offset") or 0.0) if own else 0.0)  # old timelines
        out.append({"id": c["id"], "clip": root / c["source"], "start": float(c["start"]) + t_start,
                    "dur": float(c["dur"]), "off": float(c.get("clip_offset") or 0.0), "hold0": float(hold0 or 0.0),
                    "lip_shift": float(c.get("lip_shift") or 0.0), "reuse_of": src,
                    "owner": c["id"] if (own or isinstance(m.get("lip_shift"), (int, float))) else src})
    return out


def measure(shot: dict, stem: np.ndarray, cache: Path | None = None, diagnostics: bool = True) -> dict:
    """Lag of one shot (see shots()) against the vocal-stem envelope `stem` (audio_env of song_vocals)."""
    t, m, found = mouth_series(shot["clip"], cache)
    base = shot["start"] + shot["hold0"] - shot["off"]          # song time of clip time 0
    T = t[-1] + (t[1] - t[0] if len(t) > 1 else 0.0)            # clip length
    a0, a1 = shot["start"], min(shot["start"] + shot["dur"], base + T)   # what the viewer sees of this clip
    shown = lag_of(base + t, m, stem, a0, a1)
    # two looks that must agree: first / last 60 % of the shown part, or for a short shot the first / last 1.8 s
    # of the whole clip at this placement
    lo, hi, L = (a0, a1, 0.6 * (a1 - a0)) if a1 - a0 >= 2.4 else (base, base + T, min(1.8, T))
    halves = [lag_of(base + t, m, stem, lo, lo + L), lag_of(base + t, m, stem, hi - L, hi)]
    own, aud = {}, {}
    if diagnostics:
        try:
            cenv = audio_env(shot["clip"])     # the clip's own audio = the vocal slice it was driven by
        except MomoError:
            cenv = None
        if cenv is not None and len(cenv) > 40:
            own = lag_of(t, m, cenv, 0.0, min(T, len(cenv) * HOP))
            abase = base - shot["lip_shift"]   # where the clip's audio belongs: without the intended picture shift
            aud = lag_of(abase + (np.arange(len(cenv)) + 0.5) * HOP, cenv, stem, a0, a0 + shot["dur"])
    return {**{k: v for k, v in shot.items() if k != "clip"}, "clip": shot["clip"].name, "found": round(found, 2),
            "shown": shown, "halves": halves, "self": own, "audio": aud, "verdict": verdict(shown, halves)}
