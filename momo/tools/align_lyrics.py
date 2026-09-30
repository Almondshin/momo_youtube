#!/usr/bin/env python3
"""Word times of known lyrics in a sung vocal stem → JSON for `song_track.py lyrics`.

Runs in the audio sidecar venv (mlx-whisper; not a momo dependency — nothing in momo/ imports this file):
  uv venv --python 3.12 ~/.venvs/momo-audio
  uv pip install --python ~/.venvs/momo-audio/bin/python mlx-whisper "demucs==4.0.1" "torch==2.8.*" "torchaudio==2.8.*" soundfile librosa
  ~/.venvs/momo-audio/bin/python momo/tools/align_lyrics.py --vocals song_vocals.wav --lyrics momo/episodes/ep03/lyrics.md --out align.json

How: whisper (large-v3-turbo) transcribes the stem with word timestamps, the lyric words are matched to the
heard words in order (edit-distance alignment, fuzzy word match), words that were not heard get times
interpolated inside their line. A line with no heard word at all is left out and reported, and runs of heard
words that match no lyric (the singer repeated or added a line) are reported with their times — fix the lyrics
text to what is actually sung and run again, so the captions always show what is heard.

Lyrics input: a .md with a ``` fenced block (the ACE-Step lyrics) or plain text; [Section] lines name the
section, (parentheses) mark backing voices — shown without the brackets.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

MODEL = "mlx-community/whisper-large-v3-turbo"


def read_lyrics(path: Path) -> list[dict]:
    text = path.read_text()
    m = re.search(r"```\n(.*?)```", text, re.S)
    body = m.group(1) if m else text
    lines, section = [], ""
    for raw in body.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("["):
            section = s.strip("[]").split(" - ")[0].strip()
            continue
        shown = re.sub(r"[()]", "", s).strip()
        lines.append({"text": shown, "section": section, "tokens": shown.split()})
    return lines


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


def similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    r = difflib.SequenceMatcher(a=a, b=b).ratio()
    return a == b or r >= 0.8 or (a[0] == b[0] and r >= 0.66)  # "sai"~"say", but rhymes like crunch/munch are not


def align(exp: list[str], got: list[str]) -> list[int | None]:
    """For each expected token, the index of the heard token it matches (or None). Global alignment:
    match +2 (fuzzy), mismatch −1, gap −1 — heard extras and missing lyric words are both gaps."""
    n, m = len(exp), len(got)
    score = [[0.0] * (m + 1) for _ in range(n + 1)]
    back = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        score[i][0], back[i][0] = -i, 1
    for j in range(1, m + 1):
        score[0][j], back[0][j] = -j, 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d = score[i - 1][j - 1] + (2.0 if similar(exp[i - 1], got[j - 1]) else -1.0)
            u, l = score[i - 1][j] - 1.0, score[i][j - 1] - 1.0
            best = max(d, u, l)
            score[i][j] = best
            back[i][j] = 0 if best == d else (1 if best == u else 2)
    out: list[int | None] = [None] * n
    i, j = n, m
    while i > 0 or j > 0:
        b = back[i][j] if i > 0 and j > 0 else (1 if i > 0 else 2)
        if b == 0:
            if similar(exp[i - 1], got[j - 1]):
                out[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif b == 1:
            i -= 1
        else:
            j -= 1
    return out


def fill_line(times: list[tuple[float, float] | None]) -> list[tuple[float, float]] | None:
    """Interpolate the words of one line that were not heard, from the heard ones around them."""
    known = [k for k, t in enumerate(times) if t is not None]
    if not known:
        return None
    avg = sum(times[k][1] - times[k][0] for k in known) / len(known)
    avg = min(max(avg, 0.18), 0.6)
    out = list(times)
    for k in range(len(out)):
        if out[k] is not None:
            continue
        prev = max((p for p in known if p < k), default=None)
        nxt = min((q for q in known if q > k), default=None)
        if prev is not None and nxt is not None:
            a, b = out[prev][1], out[nxt][0]
            span = max(0.05, b - a)
            step = span / (nxt - prev)
            s = a + step * (k - prev - 1)
            out[k] = (round(s, 3), round(s + step * 0.9, 3))
        elif prev is not None:
            s = out[prev][1] + 0.02 + avg * (k - prev - 1)
            out[k] = (round(s, 3), round(s + avg, 3))
        else:
            s = out[nxt][0] - avg * (nxt - k)
            out[k] = (round(max(0.0, s), 3), round(max(0.0, s) + avg * 0.9, 3))
    return out  # type: ignore[return-value]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocals", required=True)
    ap.add_argument("--lyrics", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()
    import mlx_whisper

    lines = read_lyrics(Path(a.lyrics))
    exp, owner = [], []
    for li, ln in enumerate(lines):
        for ti, tok in enumerate(ln["tokens"]):
            exp.append(norm(tok))
            owner.append((li, ti))
    prompt = " ".join(ln["text"] for ln in lines)[:600]
    r = mlx_whisper.transcribe(a.vocals, path_or_hf_repo=a.model, language="en", word_timestamps=True,
                               initial_prompt=prompt, condition_on_previous_text=False)
    heard = [(norm(w["word"]), float(w["start"]), float(w["end"])) for s in r["segments"] for w in s.get("words", [])]
    heard = [h for h in heard if h[0]]
    match = align(exp, [h[0] for h in heard])

    per_line: list[list[tuple[float, float] | None]] = [[None] * len(ln["tokens"]) for ln in lines]
    for k, j in enumerate(match):
        if j is not None:
            li, ti = owner[k]
            per_line[li][ti] = (round(heard[j][1], 3), round(heard[j][2], 3))
    out_lines, missing = [], []
    for ln, times in zip(lines, per_line):
        filled = fill_line(times)
        if filled is None:
            missing.append(ln["text"])
            continue
        # keep words in order even when whisper's times wobble
        fixed, last = [], 0.0
        for s, e in filled:
            s = max(s, last)
            e = max(e, s + 0.05)
            fixed.append((round(s, 3), round(e, 3)))
            last = s
        out_lines.append({"text": ln["text"], "section": ln["section"],
                          "words": [[tok, s, e] for tok, (s, e) in zip(ln["tokens"], fixed)],
                          "heard": sum(1 for t in times if t is not None), "of": len(times)})
    used = {j for j in match if j is not None}
    extra, run_ = [], []
    for j, h in enumerate(heard):
        if j not in used:
            run_.append(h)
        else:
            if len(run_) >= 3:
                extra.append({"t0": run_[0][1], "t1": run_[-1][2], "words": " ".join(x[0] for x in run_)})
            run_ = []
    if len(run_) >= 3:
        extra.append({"t0": run_[0][1], "t1": run_[-1][2], "words": " ".join(x[0] for x in run_)})
    acc = sum(1 for j in match if j is not None) / max(1, len(exp))
    report = {"lyric_words": len(exp), "heard_words": len(heard), "matched": round(acc, 3),
              "lines_missing": missing, "unmatched_heard_runs": extra}
    Path(a.out).write_text(json.dumps({"lines": out_lines, "report": report}, indent=1, ensure_ascii=False))
    print(f"matched {acc:.1%} of {len(exp)} lyric words, {len(out_lines)}/{len(lines)} lines timed")
    for t in missing:
        print(f"  ✖ not heard: {t}")
    for x in extra:
        print(f"  △ sung but not in lyrics {x['t0']:.2f}-{x['t1']:.2f}s: {x['words']}")
    for ln in out_lines:
        if ln["heard"] < ln["of"]:
            print(f"  · {ln['heard']}/{ln['of']} words heard: {ln['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
