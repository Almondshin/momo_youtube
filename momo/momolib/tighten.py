"""Cut whole instrumental bars out of mid-song vocal gaps of a track song (song_track.py tighten).

Suno often leaves a 1–2 bar turnaround between sections. On screen that is seconds of video where nobody sings,
and the user called it out (2026-10-01: "중간에 영상만 있는 텀이 존재한다"). A bar line-to-bar line slice is
cut only when:
- it lies wholly inside a gap between sung words, with KEEP_S of air left on both sides;
- the vocal stem is quiet there (no ad-lib or echo that the lyrics miss);
- the shot it falls in does not sing again after it (so lip-sync stays in step);
- that shot keeps at least one bar.

The song files are cut on the bar lines with a short equal-power crossfade. Every song-time field of the
manifest then moves with them: lyric words, cut_at, cut bars, analysis downbeats, track.end, nar_ref windows.
The removed ranges (in the old time) are kept in song.track.edits, so a later `song_track.py lyrics --align`
maps the aligner's times too.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .common import MomoError, probe_duration, run
from .episode import _is_num, bar_time, song_grid, song_track, track_spans

KEEP_S = 0.3        # s of the gap kept after the last sung word and before the next one
VOCAL_DB = -30.0    # a bar is "quiet" when every 20 ms frame of the vocal stem stays this far below its loudest
XFADE = 0.03        # s — equal-power crossfade at each join (on the bar line, so the beat stays put)
FRAME = 0.02


def map_time(t: float, removed: list[tuple[float, float]]) -> float:
    """Old song time → new song time. A time inside a removed range lands on the join."""
    shift = 0.0
    for a, b in removed:
        if t >= b:
            shift += b - a
        elif t > a:
            return a - shift
        else:
            break
    return t - shift


def bar_lines(song: dict) -> list[float]:
    """Song-file times of every bar line up to the end of the file."""
    tr = song_track(song) or {}
    end = float(tr.get("duration") or tr.get("end") or 0.0)
    out, k = [], 0
    while (t := bar_time(song, k)) <= end + 1e-6 and k < 10000:
        out.append(t)
        k += 1
    return out


def sung_words(song: dict) -> list[tuple[float, float]]:
    """(start, end) of every sung word with a time, by start."""
    ws = [(float(w[1]), float(w[2])) for ln in song.get("lyrics") or [] for w in ln.get("words") or []
          if len(w) >= 3 and _is_num(w[1]) and _is_num(w[2])]
    return sorted(ws)


def frame_db(x: np.ndarray, sr: int) -> np.ndarray:
    """20 ms RMS of a mono signal in dB relative to its loudest frame."""
    hop = max(1, int(FRAME * sr))
    n = max(1, len(x) // hop)
    rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    return db - db.max()


def _lipsync_cut(c: dict, by_id: dict) -> bool:
    if c.get("lipsync"):
        return True
    cf = c.get("clip_from") if isinstance(c.get("clip_from"), dict) else None
    return bool(cf and (by_id.get(cf.get("cut")) or {}).get("lipsync"))


def plan(m: dict, stem: np.ndarray | None, sr: int, keep: float = KEEP_S) -> tuple[list[tuple[float, float]], list[dict]]:
    """Bars to remove (old song time, sorted) and a report per mid-song gap that could hold a bar."""
    song = m["song"]
    tr = song_track(song) or {}
    _, bar = song_grid(song)
    lines = bar_lines(song)
    words = sung_words(song)
    if len(words) < 2:
        return [], []
    cuts = m.get("cuts") or []
    by_id = {c.get("id"): c for c in cuts}
    t0 = float(tr.get("start") or 0.0)
    spans = [(s + t0, e + t0) for s, e in track_spans(song, cuts)] if cuts else []
    db = frame_db(stem, sr) if stem is not None and len(stem) else None
    word_starts = [w[0] for w in words]
    bars_left = {c.get("id"): c.get("bars") for c in cuts if isinstance(c.get("bars"), int)}
    removed, report = [], []
    end = words[0][1]
    for s, e in words[1:]:
        g0, g1 = end, s
        end = max(end, e)
        if g1 - g0 < bar + 2 * keep:
            continue
        rep = {"gap": [round(g0, 3), round(g1, 3)], "removed": [], "refused": []}
        for k in range(len(lines) - 1):
            a, b = lines[k], lines[k + 1]
            if a < g0 + keep or b > g1 - keep:
                continue
            why = None
            if db is not None:
                i0, i1 = int(a / FRAME), max(int(a / FRAME) + 1, int(b / FRAME))
                peak = float(db[i0:i1].max()) if i1 <= len(db) else 0.0
                if peak > VOCAL_DB:
                    why = f"보컬 스템 {peak:.0f} dB (기준 {VOCAL_DB:.0f})"
            i = next((j for j, (cs, ce) in enumerate(spans) if cs <= a < ce), None)
            if why is None and i is not None:
                c, (cs, ce) = cuts[i], spans[i]
                if b > ce + 1e-6:
                    why = f"{c.get('id')} 와 다음 컷에 걸침"
                elif _lipsync_cut(c, by_id) and any(b <= x < ce for x in word_starts):
                    why = f"{c.get('id')} (립싱크) 가 이 마디 뒤에도 노래함"
                elif isinstance(bars_left.get(c.get("id")), int) and bars_left[c.get("id")] - 1 < 1:
                    why = f"{c.get('id')} 가 1마디 미만이 됨"
            if why:
                rep["refused"].append([round(a, 3), round(b, 3), why])
                continue
            if i is not None and isinstance(bars_left.get(cuts[i].get("id")), int):
                bars_left[cuts[i].get("id")] -= 1
            rep["removed"].append([round(a, 3), round(b, 3)])
            removed.append((a, b))
        if rep["removed"] or rep["refused"]:
            cut = sum(b - a for a, b in rep["removed"])
            rep["left"] = round(g1 - g0 - cut, 3)
            report.append(rep)
    return sorted(removed), report


def apply(m: dict, removed: list[tuple[float, float]], old_sha1: str, new_sha1: str) -> dict:
    """Move every song-time field of the manifest onto the cut song. Returns {cut id: bars removed}."""
    song = m["song"]
    tr = song_track(song)
    removed = sorted(removed)
    rt = lambda t: round(map_time(float(t), removed), 4)  # noqa: E731
    cuts = m.get("cuts") or []
    t0 = float(tr.get("start") or 0.0)
    spans = [(s + t0, e + t0) for s, e in track_spans(song, cuts)] if cuts else []
    less: dict[str, int] = {}
    for a, b in removed:
        i = next((j for j, (cs, ce) in enumerate(spans) if cs <= a < ce), None)
        if i is None:
            continue
        c = cuts[i]
        if isinstance(c.get("bars"), int):
            c["bars"] -= 1
        less[c["id"]] = less.get(c["id"], 0) + 1
    for ln in song.get("lyrics") or []:
        for w in ln.get("words") or []:
            for j in range(1, len(w)):
                if _is_num(w[j]):
                    w[j] = rt(w[j])
    for c in cuts:
        if _is_num(c.get("cut_at")):
            c["cut_at"] = rt(c["cut_at"])
        for ref in (c.get("nar_ref") or {}).values():
            if isinstance(ref, dict) and isinstance(ref.get("window"), list) and ref.get("track_sha1") == old_sha1:
                ref["window"] = [round(map_time(float(x), removed), 3) for x in ref["window"]]
                ref["track_sha1"] = new_sha1
    if _is_num(tr.get("end")):
        tr["end"] = rt(tr["end"])
    ana = tr.get("analysis") or {}
    for k in ("beat0", "downbeat0"):
        if _is_num(ana.get(k)):
            ana[k] = rt(ana[k])
    if ana.get("downbeats"):
        downs = []
        for t in (rt(x) for x in ana["downbeats"]):
            if not downs or t - downs[-1] > 1e-3:
                downs.append(t)
        ana["downbeats"] = downs
    for f in (tr.get("lyrics_refine") or {}).get("flags") or []:
        for k in ("t", "t0"):
            if _is_num(f.get(k)):
                f[k] = rt(f[k])
    tr.setdefault("edits", []).append({"from_sha1": old_sha1, "removed": [[round(a, 4), round(b, 4)] for a, b in removed]})
    return less


def map_lines(lines: list[dict], edits: list[dict]) -> list[dict]:
    """Aligner output in the original song time → the time of the song after its edits (song.track.edits)."""
    for ed in edits or []:
        rm = sorted((float(a), float(b)) for a, b in ed.get("removed") or [])
        for ln in lines:
            for w in ln.get("words") or []:
                for j in range(1, len(w)):
                    if _is_num(w[j]):
                        w[j] = round(map_time(float(w[j]), rm), 3)
    return lines


def cut_signal(x: np.ndarray, sr: int, removed: list[tuple[float, float]]) -> np.ndarray:
    """x (samples × channels) without the removed ranges; each join is an equal-power crossfade on the cut point."""
    h = max(1, int(XFADE * sr / 2))
    out, pos = [], 0
    fade = np.linspace(0.0, np.pi / 2, 2 * h, dtype=np.float32)[:, None]
    tail = None
    for a, b in sorted(removed):
        ia, ib = int(round(a * sr)), int(round(b * sr))
        if ia - h < pos or ib + h > len(x):
            raise MomoError(f"자를 구간 {a:.2f}–{b:.2f}s 가 파일 경계·다른 구간과 겹침")
        out.append(x[pos:ia - h] if tail is None else np.concatenate([tail, x[pos:ia - h]]))
        tail = x[ia - h:ia + h] * np.cos(fade) + x[ib - h:ib + h] * np.sin(fade)
        pos = ib + h
    out.append(x[pos:] if tail is None else np.concatenate([tail, x[pos:]]))
    return np.concatenate(out).astype(np.float32)


def channels_of(path: Path) -> int:
    proc = run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels",
                "-of", "csv=p=0", str(path)])
    out = proc.stdout.decode() if isinstance(proc.stdout, bytes) else str(proc.stdout)
    return int(out.strip() or 1)


def edit_file(path: Path, removed: list[tuple[float, float]], sr: int = 48000) -> float:
    """Rewrite an audio file without the removed ranges (same name and format). Returns the new duration."""
    from . import audio
    ch = channels_of(path)
    x = cut_signal(audio.decode(path, sr, ch), sr, removed)
    codec = {".flac": "flac", ".wav": "pcm_s16le"}.get(path.suffix.lower())
    if codec is None:
        raise MomoError(f"{path.name}: flac / wav 만 자를 수 있음")
    tmp = path.with_name(path.stem + ".tighten" + path.suffix)
    audio.write_wav(tmp, x, sr, codec=codec)
    tmp.replace(path)
    return probe_duration(path)
