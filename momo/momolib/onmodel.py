"""Momo on-model check — catches the "beady eyes / squashed face" drift (ep04 c33) before credits go into it.

Momo's look hangs on her huge round eyes. Per picture:
  1. find Momo by her mint overalls (the only mint thing in our sets) → x band + top of the overalls
  2. above them, eye candidates = dark compact blobs sitting in cream fur (Ducky's eyes sit in yellow, fence gaps
     and ear shadows are not compact); the eye PAIR = two blobs at the same height and of similar size
  3. r = mean eye size ÷ eye-to-eye distance, eye size = max(bbox w, h)
r does not change with position or zoom; max(w, h) survives blinks and head turns, and a head turn shrinks the
distance, so it can only push r up (no false alarms). Values are relative to the approved character sheet
(config.onmodel.canon_eye_ratio = 1.0). Below config.onmodel.eye_ratio_min the picture is off-model: ep04 c33 was
0.42, every approved ep04 shot ≥ 0.76.
Used by hf_jobs.py: `record --status approved` refuses an off-model image/clip, `plan --kind clip` blocks a clip
whose start image is off-model, `onmodel` prints the numbers. numpy + PIL + ffmpeg only.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

W = 1284            # analysis width (the clips' native width); height follows the picture
CLIP_FPS = 10       # clip frames sampled per second
WINDOW = 5          # rolling median over this many sampled frames (a blink or a squint is not a deformation)


def hsv(a: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """uint8 RGB → (hue 0–360, saturation 0–1, value 0–1)."""
    a = a.astype(np.float32) / 255
    mx, mn = a.max(-1), a.min(-1)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, (mx - mn) / np.maximum(mx, 1e-6), mx


def _blobs(mask: np.ndarray, min_px: int = 1) -> list[tuple[np.ndarray, np.ndarray]]:
    """4-connected components of a sparse mask → [(ys, xs)]."""
    todo, out = set(zip(*np.nonzero(mask))), []
    while todo:
        stack, comp = [todo.pop()], []
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for n in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if n in todo:
                    todo.remove(n)
                    stack.append(n)
        if len(comp) >= min_px:
            out.append(tuple(np.array(comp).T))
    return out


def eye_pair(rgb: np.ndarray) -> tuple[tuple, tuple] | None:
    """Momo's two eyes in one RGB frame → ((x, y, size, pixels), (x, y, size, pixels)), None when she or her eye
    pair is not found. x, y = eye centre, size = max(bbox w, h) in pixels (steps 1–2 of the module docstring)."""
    wf = rgb.shape[1]
    h, s, v = hsv(rgb)
    mint = _blobs(((h > 115) & (h < 170) & (s > 0.15) & (v > 0.35))[::4, ::4], 20)
    if not mint:
        return None
    ys, xs = max(mint, key=lambda b: len(b[0]))
    ox0, ox1, otop = xs.min() * 4, xs.max() * 4, ys.min() * 4
    pad = max(ox1 - ox0, 0.15 * wf)
    x0, x1 = int(max(0, ox0 - pad)), int(min(wf, ox1 + pad))
    fur = (h > 5) & (h < 60) & (s < 0.50) & (v > 0.45)
    eyes = []
    for by, bx in _blobs(v[:otop, x0:x1] < 0.42, 12):
        bx = bx + x0
        ya, yb, xa, xb = by.min(), by.max(), bx.min(), bx.max()
        bw, bh = xb - xa + 1, yb - ya + 1
        if max(bw, bh) > 0.12 * wf or len(by) / (bw * bh) - np.percentile(v[by, bx], 10) < 0.25:
            continue  # too big, or not a compact dark blob
        py, px = int(bh * .6), int(bw * .6)
        if fur[max(0, ya - py):yb + py + 1, max(0, xa - px):xb + px + 1].mean() < 0.30:
            continue  # not sitting in cream fur
        eyes.append(((xa + xb) / 2, (ya + yb) / 2, max(bw, bh), len(by)))
    best = None
    for i, e in enumerate(eyes):
        for f in eyes[i + 1:]:
            dx, dy = abs(e[0] - f[0]), abs(e[1] - f[1])
            if not 0.03 * wf < dx < 0.35 * wf or dy > 0.35 * dx:
                continue
            if max(e[3], f[3]) > 3 * min(e[3], f[3]) or max(e[2], f[2]) > 0.9 * dx:
                continue
            if best is None or min(e[3], f[3]) > best[0]:
                best = (min(e[3], f[3]), (e, f))
    return best[1] if best else None


def eye_ratio(rgb: np.ndarray) -> float:
    """Eye size ÷ eye distance of Momo in one RGB frame (absolute), NaN when she or her eye pair is not found."""
    pair = eye_pair(rgb)
    if pair is None:
        return math.nan
    e, f = pair
    return (e[2] + f[2]) / 2 / abs(e[0] - f[0])


def _still(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    return np.asarray(im.resize((W, round(im.height * W / im.width)), Image.LANCZOS))


def _frames(path: Path):
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    sw, sh = (int(v) for v in probe.stdout.strip().split(",")[:2])
    hh = round(sh * W / sw / 2) * 2
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={CLIP_FPS},scale={W}:{hh}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while len(buf := p.stdout.read(W * hh * 3)) == W * hh * 3:
        yield np.frombuffer(buf, np.uint8).reshape(hh, W, 3)
    p.wait()


def _verdict(cfg: dict, vals: list[float]) -> str:
    thr = float(cfg["onmodel"]["eye_ratio_min"])
    return "unmeasured" if not vals or any(math.isnan(x) for x in vals) else ("off" if min(vals) < thr else "ok")


def check_image(cfg: dict, path: Path) -> dict:
    """{"ratio", "verdict": ok|off|unmeasured} — ratio relative to the character sheet (1.0 = on-model)."""
    r = eye_ratio(_still(path)) / float(cfg["onmodel"]["canon_eye_ratio"])
    return {"ratio": round(r, 3) if not math.isnan(r) else None, "verdict": _verdict(cfg, [r])}


def check_clip(cfg: dict, path: Path) -> dict:
    """{"ratio" (median), "worst", "worst_t", "found", "verdict"} over frames sampled at CLIP_FPS; "worst" is the
    lowest rolling median (needs ≥ 3 measured frames in the window), so blinks and squints do not count."""
    canon = float(cfg["onmodel"]["canon_eye_ratio"])
    r = np.array([eye_ratio(f) for f in _frames(path)]) / canon
    found = float(np.isfinite(r).mean()) if len(r) else 0.0
    if found < 0.5:
        return {"ratio": None, "worst": None, "worst_t": None, "found": round(found, 2), "verdict": "unmeasured"}
    roll = np.full(len(r), np.nan)
    for i in range(len(r)):
        win = r[max(0, i - WINDOW // 2):i + WINDOW // 2 + 1]
        if np.isfinite(win).sum() >= 3:
            roll[i] = np.nanmedian(win)
    i = int(np.nanargmin(roll)) if np.isfinite(roll).any() else 0
    med, worst = float(np.nanmedian(r)), float(roll[i]) if np.isfinite(roll[i]) else float(np.nanmin(r))
    return {"ratio": round(med, 3), "worst": round(worst, 3), "worst_t": round(i / CLIP_FPS, 2),
            "found": round(found, 2), "verdict": _verdict(cfg, [med, worst])}


def describe(res: dict) -> str:
    """One-line Korean summary for CLI output."""
    if res["verdict"] == "unmeasured":
        return "눈을 못 찾음 — 얼굴을 직접 크게 볼 것"
    extra = f", 최저 {res['worst']:.2f} @{res['worst_t']:.1f}s" if res.get("worst") is not None else ""
    word = "모델과 다름 (눈이 작거나 얼굴이 눌림)" if res["verdict"] == "off" else "정상"
    return f"눈 비율 {res['ratio']:.2f}{extra} (시트 = 1.00) — {word}"
