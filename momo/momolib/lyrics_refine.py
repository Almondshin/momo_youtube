"""Snap aligned lyric word starts (tools/align_lyrics.py: whisper + DP) to where they are sung in the vocal stem.

Used by `song_track.py lyrics` (on by default). numpy only.

Why: whisper (word_timestamps) tends to start a word right where the previous word ended. A word sung after a
rest or after a held note (the first word of most lines) is then stamped inside that rest / held note, up to
0.7 s before it is sung (ep04: 79 of 238 words, median 205 ms early); words stamped at a sung onset are fine
(median +17 ms). The karaoke line appears LYRIC_LEAD before its first stamp and each word lights at its stamp,
so the error is seen directly: line and first word run ahead of the voice.

How:
 1. Syllable starts (vocal_onsets): a voiced onset (150–3500 Hz flux peak climbing ≥ RISE_MIN dB), or a legato
    one (strong flux, no dip) unless the pitch track says it sits inside a held note.
 2. Consonants: the lyric spelling says how a word starts. s/sh/f/th/ch start with noise up to 0.3 s before the
    vowel, h up to 0.2 s, t/k/p/b/d/g with a burst + aspiration ≤ 0.15 s; vowels and w/y/l/m/n/r start with the
    voice. The word start is the earliest matching 4–10 kHz onset before its vowel, else the voiced onset.
 3. One monotonic alignment of all syllables of the song (words split into sung syllables: seven = 2,
    Ding-dong-dang = 3) to the syllable starts: each takes a distinct start (≥ MIN_STEP apart) or none.
    Score = onset salience − ½(d/τ)², d = start − stamp. τ is 0.12 s for earlier-than-stamped; for later it is
    0.18 s, or 0.40 s when no syllable starts within NEAR of the stamp (the stamp sits in a rest or a held note).
 4. A voiced onset after a rest (> REST_S under REST_DB, reaching ≥ REST_ONSET_DB) that a line starts after is
    sung by that line: leaving it without a syllable costs KEEP_REST (else a late whisper stamp leaves the caption
    behind the voice — ep04 Verse 2 "Look around" lit 0.36 s late). Not when the last stamp before the onset is
    loose (that word moves onto it by itself) and not mid-line (a stray onset there would pull a whole phrase
    early). When a line's first word moves > NEAR earlier onto such an onset, whisper stamped that phrase late:
    the rest of the phrase (up to the next rest onset) is re-stamped by the same amount and aligned again.
 5. A word with no taken start moves with the median shift of its line. Word ends are clipped to the next word;
    a line's last word ends where its note falls 18 dB (caption hold is measured from there).

Words are stored [word, t0, t1, t_whisper]: refining always starts again from t_whisper, so it is idempotent.
Guards (report only, values are not changed): "lag" — a rest onset no syllable took, more than LAG_S before the
next word start (the caption trails the voice there); "phase" — a line starting more than PHASE_BEATS off the
bar phase of the other lines with the same section label (+ = later than them: check that one first).
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np

from . import vocal_onsets as vo

REFINE_V = 1            # song.track.lyrics_refine.v — bump when the rules change

RISE_MIN = 5.0          # dB — a voiced onset climbs this much from the 100 ms before it
LEGATO_FLUX = 1.1       # a legato onset (no dip) needs a flux peak this strong (× median peak) …
LEGATO_DB = -12.0       # … at this level (dB rel. loud), and must not sit inside a steady note
VOICED_DB = -20.0       # dB — a sung vowel reaches this 30 ms after its rise
CONS_LEAD = {"fric": 0.30, "h": 0.20, "stop": 0.15}  # s — longest consonant lead before the vowel, by class
AMBIG_LEAD = 0.15       # s — longest lead when the boundary is hidden in noise shared with the previous word
CONS_DB = -20.0         # dB — a sung consonant's noise is this loud (a breath before a phrase is quieter)
CLOSURE = 0.06          # s — the noise of a consonant cluster may pause this long (s-k-y, s-t-omps)
SEARCH = (-0.5, 0.9)    # s — a syllable start is looked for this far around its stamp
TAU_EARLY, TAU_LATE, TAU_LOOSE = 0.12, 0.18, 0.40  # s — see 3.
NEAR = 0.10             # s
KEEP = {"loose": 2.0, "word": 1.0, "inner": 0.4}  # score lost by leaving a unit without a syllable start
MIN_STEP = 0.09         # s — two taken syllable starts (vowels) are at least this far apart
REST_S = 0.15           # s — a rest: the voiced band stays under REST_DB this long …
REST_DB = -30.0         # dB rel. loud
REST_ONSET_DB = -12.0   # … and the onset after it reaches this level: someone sings there
KEEP_REST = 4.0         # score lost by leaving such an onset without a syllable
SHIFT_ROUNDS = 3        # re-alignments for late-stamped phrases (4.)
END_MAX = 2.0           # s — longest word span assumed from the stamps
LAG_S = 0.10            # lag guard
PHASE_BEATS = 0.5       # bar-phase guard
VOICED_TH = {"the", "this", "that", "then", "there", "they", "them", "these", "those", "than", "though"}


def onset_class(tok: str) -> str:
    """How a word starts, from its spelling: "fric" / "h" / "stop" / "" (the voice starts with the word)."""
    w = re.sub(r"[^a-z]", "", tok.lower())
    if not w or w in VOICED_TH:
        return ""
    if re.match(r"(sh|ch|th|s|f|z|c[eiy])", w):
        return "fric"
    if w[0] == "h":
        return "h"
    return "stop" if w[0] in "ptkcqbdgj" else ""


def syllables(tok: str) -> int:
    """Sung syllables of one lyric token (vowel groups; silent final e; -le; hyphen parts count separately)."""
    n = 0
    for part in re.split(r"-", tok):
        w = re.sub(r"[^a-z]", "", part.lower())
        if not w:
            continue
        c = len(re.findall(r"[aeiouy]+", ("" if w[0] == "y" else w[0]) + w[1:]))
        if w.endswith("e") and not w.endswith("le") and c > 1:
            c -= 1
        if w.endswith("le") and len(w) > 2 and w[-3] not in "aeiouy" and c == 1:
            c = 2
        n += max(1, c)
    return max(1, n)


def noisy_coda(tok: str) -> bool:
    """The word ends in a consonant that makes 4–10 kHz noise (six, hops, clap, count, grass …)."""
    return bool(re.search(r"(s|x|z|f|sh|ch|th|ce|se|t|te|k|ke|p|pe)$", re.sub(r"[^a-z]", "", tok.lower())))


def _after_rest(fe: vo.Feats, t: float) -> bool:
    a, b = fe.idx(t - REST_S), fe.idx(t - 0.01)
    return b - a >= int(REST_S / vo.DT) - 3 and float(np.mean(fe.lv[a:b] < REST_DB)) >= 0.9


def syllable_starts(fe: vo.Feats, ons: list[vo.Onset]) -> list[dict]:
    """[{t (vowel onset), cons [(consonant onset, joined to the previous word)], sal, rest}] in time order."""
    V = []
    for o in ons:
        if o.band != "V" or o.level <= VOICED_DB:
            continue
        if o.rise >= RISE_MIN or (o.strength >= LEGATO_FLUX and o.level > LEGATO_DB and not fe.steady(o.t_peak)):
            if V and o.t - V[-1].t < 0.08:  # one vowel entry can peak twice: keep the bigger rise
                if o.rise > V[-1].rise:
                    V[-1] = o
                continue
            V.append(o)
    H = [o for o in ons if o.band == "H" and o.rise >= 6.0 and o.level >= CONS_DB]
    gap_max = int(CLOSURE / vo.DT)
    out = []
    for n, v in enumerate(V):
        iv = fe.idx(v.t)
        after = V[n - 1].t_peak + 0.03 if n else -1.0            # not before the previous vowel
        cons = []
        for h in H:
            if not (max(after, v.t - max(CONS_LEAD.values())) <= h.t < v.t - 0.015):
                continue
            ih, ip = fe.idx(h.t), fe.idx(h.t_peak)
            if ip >= iv or np.percentile(fe.lv[ih:iv], 80) > v.level - 10:  # no vowel between it and ours
                continue
            quiet = fe.lh[ip:iv] < vo.GATE_DB                      # noise pauses (closures) up to CLOSURE
            runs = np.diff(np.flatnonzero(np.diff(np.r_[0, quiet.astype(int), 0])))[::2] if quiet.any() else []
            if len(runs) and max(runs) > gap_max:
                continue
            # noise running on from the previous vowel (six-seven): the word boundary is somewhere inside it
            a = fe.idx(V[n - 1].t_peak) if n else ih
            silent = (np.maximum(fe.lv[a:ih], fe.lh[a:ih]) < vo.GATE_DB).any()
            cons.append((round(h.t, 3), bool(n and not silent and v.t - V[n - 1].t < 0.8)))
        out.append({"t": round(v.t, 3), "cons": cons, "legato": v.rise < RISE_MIN,
                    "sal": 0.4 if v.rise < RISE_MIN else min(v.rise, 30.0) / 10.0,
                    "rest": v.level >= REST_ONSET_DB and _after_rest(fe, v.t)})
    return out


def word_start(ev: dict, cls: str, after_noise: bool = False) -> float:
    """Start of a word whose first vowel is ev: its consonant when the spelling has one there (the earliest
    consonant onset within the class's lead). When the previous word ends in a noisy consonant and the noise
    runs on into this word without a silence ("hops! Six!", "six, seven"), the earliest onset may still be the
    previous word's coda: take the latest one, at most AMBIG_LEAD before the vowel (errs late, not early)."""
    lead = CONS_LEAD.get(cls, 0.0)
    ok = [(c, joined) for c, joined in ev["cons"] if ev["t"] - c <= lead]
    if not ok:
        return ev["t"]
    return max(ok[-1][0], ev["t"] - AMBIG_LEAD) if after_noise and ok[0][1] else ok[0][0]


def cost(d: float, kind: str) -> float:
    tau = TAU_EARLY if d < 0 else (TAU_LOOSE if kind == "loose" else TAU_LATE)
    return (0.25 if kind == "inner" else 0.5) * (d / tau) ** 2


def align(units: list[dict], ev: list[dict]) -> list[int | None]:
    """Monotonic alignment of syllable units to syllable starts (DP over [unit, last start taken]).

    Each unit takes a start ≥ MIN_STEP after the previous taken one, or none (−KEEP[kind]); every "must" onset
    (rule 4) left untaken costs KEEP_REST. Column c = ev[c − 1] is the last start taken; with C[c] = must onsets
    in ev[:c], skipping ev[c:j] costs KEEP_REST·(C[j] − C[c]), so the best predecessor is a prefix maximum of
    prev + KEEP_REST·C. O(units × starts)."""
    tv = np.array([e["t"] for e in ev])
    sal = np.array([e["sal"] for e in ev])
    M = len(ev)
    if not M:
        return [None] * len(units)
    C = KEEP_REST * np.concatenate([[0.0], np.cumsum([1.0 if e.get("must") else 0.0 for e in ev])])
    lim = np.searchsorted(tv, tv - MIN_STEP, side="right")  # predecessor columns allowed: 0 .. lim[j]
    prev = np.full(M + 1, -1e18)
    prev[0] = 0.0
    took = np.zeros((len(units), M + 1), bool)
    frm = np.zeros((len(units), M + 1), np.int32)
    for u, un in enumerate(units):
        cur = prev - KEEP[un["kind"]]
        adj = prev + C
        arg = np.zeros(M + 1, np.int32)
        for k in range(1, M + 1):
            arg[k] = k if adj[k] >= adj[arg[k - 1]] else arg[k - 1]
        lo, hi = np.searchsorted(tv, [un["x"] + SEARCH[0], un["x"] + SEARCH[1]])
        for j in range(lo, hi):
            d = tv[j] - un["x"]
            if un["kind"] != "inner":  # the stamp may mark the consonant or the vowel: the nearer one counts
                dc = word_start(ev[j], un["cls"], un["after_noise"]) - un["x"]
                d = dc if abs(dc) < abs(d) else d
            p = arg[lim[j]]
            v = adj[p] - C[j] + sal[j] * (0.5 if un["kind"] == "inner" else 1.0) - cost(d, un["kind"])
            if v > cur[j + 1]:
                cur[j + 1], took[u, j + 1], frm[u, j + 1] = v, True, p
        prev = cur
    col, pick = int(np.argmax(prev + C)), [None] * len(units)
    for u in range(len(units) - 1, -1, -1):
        if took[u, col]:
            pick[u], col = col - 1, int(frm[u, col])
    return pick


def note_end(fe: vo.Feats, t_from: float, t_max: float) -> float:
    """Where the note after t_from falls 18 dB under its peak (≤ t_max)."""
    a, b = fe.idx(t_from), fe.idx(t_max)
    if b - a < 3:
        return t_max
    seg = fe.lv[a:b]
    pk = int(np.argmax(seg[:max(1, int(0.4 / vo.DT))]))
    below = np.flatnonzero(seg[pk:] < seg[pk] - 18)
    return float(fe.t[a + pk + below[0]]) if len(below) else t_max


def stamp(w: list) -> float:
    """The aligner's (whisper) start of a stored word: [w, t0, t1, t_whisper] or, before refining, [w, t0, t1]."""
    return float(w[3]) if len(w) >= 4 and isinstance(w[3], (int, float)) else float(w[1])


def _units(words: list[dict], near: np.ndarray) -> list[dict]:
    units = []
    for i, w in enumerate(words):
        nxt = words[i + 1]["x"] if i + 1 < len(words) else w["x"] + END_MAX
        span = max(0.05, min(nxt, w["x"] + END_MAX) - w["x"])
        j = np.searchsorted(near, w["x"] - NEAR)
        loose = not (j < len(near) and near[j] <= w["x"] + NEAR)  # stamped in a rest / a held note
        for s in range(w["n"]):
            units.append({"w": i, "cls": w["cls"], "after_noise": w["after_noise"], "x": w["x"] + span * s / w["n"],
                          "kind": "inner" if s else ("loose" if loose else "word")})
    return units


def _moved(e: dict, w: dict, x: float) -> float:
    """How far a word taking start e moves from stamp x — to its consonant or its vowel, whichever is nearer
    (whisper stamps s-words on the vowel; the noise before it is not a late stamp)."""
    dc, dv = word_start(e, w["cls"], w["after_noise"]) - x, e["t"] - x
    return dc if abs(dc) < abs(dv) else dv


def _late_phrases(words: list[dict], units: list[dict], pick: list, ev: list[dict], rest_t: np.ndarray) -> bool:
    """Rule 4: a word pulled > NEAR earlier onto a rest onset → re-stamp the rest of its phrase. True if changed."""
    changed = False
    for un, p in zip(units, pick):
        if un["kind"] == "inner" or p is None or not ev[p].get("must"):
            continue
        w = words[un["w"]]
        d = _moved(ev[p], w, w["x"])
        if d >= -NEAR:
            continue
        k = np.searchsorted(rest_t, ev[p]["t"] + MIN_STEP)
        stop = rest_t[k] - NEAR if k < len(rest_t) else math.inf
        for x in words[un["w"] + 1:]:
            if x["line"] != w["line"] or x["a"] >= stop:
                break
            if not x["shifted"]:
                x["x"], x["shifted"], changed = x["a"] + d, True, True
    return changed


def bar_phase(t: float, downs: list[float], bar: float, bpb: int) -> float:
    """Beat position of song time t inside its bar (0 … bpb), from the analysed bar lines."""
    if not downs:
        return 0.0
    k = int(np.searchsorted(downs, t, side="right")) - 1
    if k < 0:
        return ((t - downs[0]) / bar * bpb) % bpb
    if k + 1 < len(downs):
        return (t - downs[k]) / (downs[k + 1] - downs[k]) * bpb
    return ((t - downs[-1]) / bar * bpb) % bpb


def phase_guard(lines: list[dict], song: dict | None) -> list[dict]:
    """Lines whose start is > PHASE_BEATS off the bar phase of the other lines of their section."""
    ana = ((song or {}).get("track") or {}).get("analysis") or {}
    if not (ana.get("bpm") and isinstance(ana.get("downbeat0"), (int, float))):
        return []
    bpb = int((song or {}).get("beats_per_bar") or 4)
    bar = 60.0 / float(ana["bpm"]) * bpb
    downs = [float(x) for x in ana.get("downbeats") or []] or [float(ana["downbeat0"])]
    groups: dict[str, list] = {}
    for li, ln in enumerate(lines):
        if not ln.get("words"):
            continue
        t = float(ln["words"][0][1])
        sec = " ".join(str(ln.get("section") or "").split())
        if sec:  # unlabelled lines are not compared
            groups.setdefault(sec, []).append((li, t, bar_phase(t, downs, bar, bpb)))
    out = []
    wrap = lambda d: (d + bpb / 2) % bpb - bpb / 2  # noqa: E731
    for sec, g in groups.items():
        if len(g) < 3:
            continue
        ang = np.array([p for _, _, p in g]) * 2 * np.pi / bpb
        ref = math.atan2(np.sin(ang).mean(), np.cos(ang).mean()) * bpb / (2 * np.pi)
        dev = [wrap(p - ref) for _, _, p in g]
        med = float(np.median(dev))
        for (li, t, p), d in zip(g, dev):
            if abs(wrap(d - med)) > PHASE_BEATS:
                out.append({"kind": "phase", "line": li, "t": round(t, 3), "section": sec, "beat": round(p, 2),
                            "median": round((ref + med) % bpb, 2), "beats": round(wrap(d - med), 2),
                            "text": lines[li].get("text") or ""})
    return sorted(out, key=lambda f: f["t"])


def refine(lyrics: list[dict], fe: vo.Feats, ons: list[vo.Onset] | None = None,
           song: dict | None = None) -> tuple[list[dict], dict]:
    """→ (copy of song.lyrics with words [word, t0, t1, t_whisper], report).

    report = {"v", "words", "matched", "loose", "moved", "shift_ms", "early": [...], "flags": [lag + phase guards],
    "info": per word}. Refining a refined copy gives the same result (always from t_whisper)."""
    ons = vo.detect(fe) if ons is None else ons
    ev = syllable_starts(fe, ons)
    near = np.array(sorted([e["t"] for e in ev] + [c for e in ev for c, _ in e["cons"]]))
    rest_t = np.array([e["t"] for e in ev if e["rest"]])
    words = [{"line": li, "k": k, "text": str(w[0]), "a": stamp(w), "cls": onset_class(str(w[0])),
              "n": syllables(str(w[0])), "shifted": False}
             for li, ln in enumerate(lyrics) for k, w in enumerate(ln.get("words") or [])]
    words.sort(key=lambda w: w["a"])
    for i, w in enumerate(words):
        w["x"] = w["a"]
        w["after_noise"] = i > 0 and noisy_coda(words[i - 1]["text"])
        j = np.searchsorted(near, w["a"] - NEAR)
        w["loose"] = not (j < len(near) and near[j] <= w["a"] + NEAR)
    stamps = np.array([w["a"] for w in words])
    for e in ev:  # rule 4 — only where a line starts after the rest and no loose stamp waits for the onset
        k = int(np.searchsorted(stamps, e["t"])) - 1  # (a loose word before it moves onto it by itself)
        e["must"] = bool(e["rest"] and k + 1 < len(words) and words[k + 1]["k"] == 0
                         and (k < 0 or not words[k]["loose"]))
    for _ in range(SHIFT_ROUNDS):
        units = _units(words, near)
        pick = align(units, ev)
        if not _late_phrases(words, units, pick, ev, rest_t):
            break
    taken = set()
    for un, p in zip(units, pick):
        if p is not None:
            taken.add(p)
        if un["kind"] != "inner":
            w = words[un["w"]]
            w["ev"] = p
            w["t0"] = word_start(ev[p], w["cls"], w["after_noise"]) if p is not None else None
            w["vowel"] = ev[p]["t"] if p is not None else None
            w["d"] = _moved(ev[p], w, w["a"]) if p is not None else None
    for w in words:  # no start taken: ride with the line
        if w["t0"] is None:
            sh = [x["t0"] - x["a"] for x in words if x["line"] == w["line"] and x["ev"] is not None]
            w["t0"] = w["a"] + (float(np.median(sh)) if sh else 0.0)
    for a, b in zip(words, words[1:]):
        b["t0"] = max(b["t0"], a["t0"] + 0.05)
    out = [dict(ln, words=[list(x[:3]) for x in ln.get("words") or []]) for ln in lyrics]
    for i, w in enumerate(words):
        nxt = words[i + 1]["t0"] if i + 1 < len(words) else w["t0"] + END_MAX
        last = i + 1 == len(words) or words[i + 1]["line"] != w["line"]
        if last:
            end = note_end(fe, w["vowel"] or w["t0"], min(nxt, w["t0"] + END_MAX))
        else:
            e = min(words[i + 1]["a"], w["a"] + END_MAX)
            end = min(e + (w["t0"] - w["a"]), nxt)
        out[w["line"]]["words"][w["k"]] = [w["text"], round(w["t0"], 3), round(max(end, w["t0"] + 0.05), 3),
                                           round(w["a"], 3)]
    # lag guard: a rest onset no word took, with the next word starting > LAG_S after it
    starts = np.array([w["t0"] for w in words])
    flags = []
    lo, hi = (starts[0] - SEARCH[1], starts[-1] + END_MAX) if len(starts) else (0.0, 0.0)
    for j, e in enumerate(ev):
        if not e["rest"] or j in taken or not lo <= e["t"] <= hi:
            continue
        k = int(np.searchsorted(starts, e["t"] - 0.02))
        if k < len(words) and LAG_S < starts[k] - e["t"] < 1.0:
            w = words[k]
            flags.append({"kind": "lag", "line": w["line"], "t": round(e["t"], 3), "word": w["text"],
                          "t0": round(w["t0"], 3), "ms": round((w["t0"] - e["t"]) * 1000),
                          "text": lyrics[w["line"]].get("text") or ""})
    flags += phase_guard(out, song)
    moved = np.array([w["t0"] - w["a"] for w in words]) if words else np.zeros(1)
    info = [{"line": w["line"], "word": w["text"], "stamp": round(w["a"], 3), "t0": round(w["t0"], 3),
             "vowel": w["vowel"], "class": w["cls"], "loose": w["loose"], "matched": w["ev"] is not None,
             "rest": w["ev"] is not None and ev[w["ev"]]["rest"]} for w in words]
    report = {"v": REFINE_V, "words": len(words), "matched": sum(i["matched"] for i in info),
              "loose": sum(i["loose"] for i in info), "moved": int((np.abs(moved) > 0.1).sum()) if words else 0,
              "shift_ms": {"median": round(float(np.median(moved)) * 1000),
                           "p90_abs": round(float(np.percentile(np.abs(moved), 90)) * 1000)},
              "early": [i for w, i in zip(words, info) if w["d"] is not None and w["d"] < -NEAR],
              "flags": sorted(flags, key=lambda f: (f["t"], f["kind"])), "info": info}
    return out, report


def refine_file(lyrics: list[dict], vocals: Path, song: dict | None = None) -> tuple[list[dict], dict]:
    """refine() on a vocal stem file."""
    return refine(lyrics, vo.load(vocals), song=song)
