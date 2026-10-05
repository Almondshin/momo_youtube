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
import unicodedata
from pathlib import Path

MODEL = "mlx-community/whisper-large-v3-turbo"
MAX_WORD = 2.0  # s — a sung word (even a held note) is shorter than this


def read_lyrics(path: Path) -> list[dict]:
    text = path.read_text()
    blocks = [b for tag, b in re.findall(r"```(\w*)\n(.*?)```", text, re.S) if not tag and "[" in b]
    body = blocks[-1] if blocks else text  # the untagged block with [Section] tags (a ```style block is skipped)
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


NUMBER_WORDS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six",
                "7": "seven", "8": "eight", "9": "nine", "10": "ten"}


def norm(w: str) -> str:
    w = re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))
    return NUMBER_WORDS.get(w, w)  # whisper often writes sung numbers as digits


# Korean (--language ko): sung Korean liaises ("아인이도" is heard and written "아이니도"), so words are compared as
# jamo with the silent initial ㅇ dropped and each final consonant written as the initial it becomes.
FINAL_TO_INITIAL = dict(zip("\u11a8\u11a9\u11ab\u11ae\u11af\u11b7\u11b8\u11ba\u11bb\u11bd\u11be\u11bf\u11c0\u11c1\u11c2",
                            "\u1100\u1101\u1102\u1103\u1105\u1106\u1107\u1109\u110a\u110c\u110e\u110f\u1110\u1111\u1112"))


def ko_norm(w: str) -> str:
    out = []
    for ch in unicodedata.normalize("NFD", w):
        o = ord(ch)
        if 0x1100 <= o <= 0x1112:
            if o != 0x110B:                       # ㅇ as an initial is silent
                out.append(ch)
        elif 0x1161 <= o <= 0x1175:
            out.append(ch)
        elif 0x11A8 <= o <= 0x11C2:
            out.append(FINAL_TO_INITIAL.get(ch, ch))
    return "".join(out)


def align_chars(exp: list[str], got: list[str]) -> list[int | None]:
    """Expected token k → heard word j by matching their jamo in order (whisper merges and splits Korean words, so
    word-to-word matching fails). A token takes the heard word holding most of its matched jamo, at least half."""
    a, a_own, b, b_own = [], [], [], []
    for k, t in enumerate(exp):
        a += list(t)
        a_own += [k] * len(t)
    for j, t in enumerate(got):
        b += list(t)
        b_own += [j] * len(t)
    votes: list[dict[int, int]] = [{} for _ in exp]
    for blk in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        if blk.size < 2:
            continue
        for i in range(blk.size):
            k, j = a_own[blk.a + i], b_own[blk.b + i]
            votes[k][j] = votes[k].get(j, 0) + 1
    out: list[int | None] = []
    for k, v in enumerate(votes):
        best = max(v, key=v.get) if v else None
        out.append(best if best is not None and sum(v.values()) * 2 >= len(exp[k]) else None)
    return out


def phrase_chunks(x, sr: int = 16000, gap: float = 0.25, max_len: float = 10.0) -> list[tuple[int, int]]:
    """Sample ranges of the vocal stem cut in its quiet gaps, each at most max_len s. Whisper run over a whole
    repetitive children's song in Korean loops on a hallucinated line; short phrases it hears well."""
    import numpy as np
    hop = int(0.02 * sr)
    n = len(x) // hop
    if n == 0:
        return []
    rms = np.sqrt((x[:n * hop].reshape(n, hop).astype(np.float64) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    voiced = db > db.max() - 35
    cuts, run = [0], 0
    for i, v in enumerate(voiced):
        if not v:
            run += 1
            continue
        if run * 0.02 >= gap and i - run > 0:
            cuts.append((i - run // 2) * hop)
        run = 0
    cuts.append(len(x))
    out, start, prev = [], cuts[0], cuts[0]
    for c in cuts[1:]:
        if (c - start) / sr > max_len and prev > start:
            out.append((start, prev))
            start = prev
        prev = c
    out.append((start, len(x)))
    return [(a, b) for a, b in out if voiced[a // hop:max(a // hop + 1, b // hop)].any()]


def transcribe_chunked(path: str, model: str, language: str) -> list[dict]:
    """Whisper words [{word, start, end}] over phrase_chunks of the stem, in song time."""
    import mlx_whisper
    from mlx_whisper.audio import SAMPLE_RATE, load_audio
    import numpy as np
    x = np.array(load_audio(path), dtype=np.float32)
    words = []
    for a, b in phrase_chunks(x, SAMPLE_RATE):
        r = mlx_whisper.transcribe(x[a:b], path_or_hf_repo=model, language=language, word_timestamps=True,
                                   condition_on_previous_text=False, temperature=0.0)
        off = a / SAMPLE_RATE
        words += [{"word": w["word"], "start": w["start"] + off, "end": w["end"] + off}
                  for s in r["segments"] for w in s.get("words", [])]
    return words


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


MAX_GAP = 2.5  # s — a word heard this long after the previous word of the same line is a mismatch


def drop_outliers(times: list[tuple[float, float] | None]) -> list[tuple[float, float] | None]:
    """Forget heard times that jump far from their line neighbours (whisper matched a word elsewhere)."""
    out = list(times)
    known = [k for k, t in enumerate(out) if t is not None]
    for a, b in zip(known, known[1:]):
        if out[a] is not None and out[b] is not None and out[b][0] - out[a][1] > MAX_GAP * (b - a):
            # keep the side that agrees with the rest of the line
            after = [out[k][0] for k in known if k > b and out[k] is not None]
            if after and after[0] - out[b][1] <= MAX_GAP:
                out[a] = None
            else:
                out[b] = None
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
    ap.add_argument("--language", default="en", choices=("en", "ko"), help="ko: Korean lyrics (jamo matching)")
    ap.add_argument("--fill-missing", action="store_true",
                    help="a line whisper did not hear at all, between two timed lines, is spread evenly over the gap "
                         "(only when you checked on the stem that it IS sung — otherwise it hides a skipped line)")
    a = ap.parse_args()
    import mlx_whisper

    lines = read_lyrics(Path(a.lyrics))
    ko = a.language == "ko"
    exp, owner = [], []
    for li, ln in enumerate(lines):
        for ti, tok in enumerate(ln["tokens"]):
            if ko:
                exp.append(ko_norm(tok))
                owner.append((li, ti))
                continue
            for part in [p for p in re.split(r"-", tok) if norm(p)] or [tok]:  # "Ding-dong-dang!" is heard as 3 words
                exp.append(norm(part))
                owner.append((li, ti))
    prompt = " ".join(ln["text"] for ln in lines)[:600]
    if ko:  # Korean: phrase by phrase, no prompt (one long pass loops on a hallucinated line)
        words = transcribe_chunked(a.vocals, a.model, a.language)
    else:
        r = mlx_whisper.transcribe(a.vocals, path_or_hf_repo=a.model, language=a.language, word_timestamps=True,
                                   initial_prompt=prompt, condition_on_previous_text=False)
        words = [w for s in r["segments"] for w in s.get("words", [])]
    if ko:
        heard = [(w["word"].strip(), float(w["start"]), float(w["end"])) for w in words if ko_norm(w["word"])]
        match = align_chars(exp, [ko_norm(h[0]) for h in heard])
    else:
        heard = [(norm(w["word"]), float(w["start"]), float(w["end"])) for w in words]
        heard = [h for h in heard if h[0]]
        match = align(exp, [h[0] for h in heard])

    per_line: list[list[tuple[float, float] | None]] = [[None] * len(ln["tokens"]) for ln in lines]
    for k, j in enumerate(match):
        if j is not None:
            li, ti = owner[k]
            s0, e0 = round(heard[j][1], 3), round(heard[j][2], 3)
            prev = per_line[li][ti]  # parts of one hyphenated token: first start, last end
            per_line[li][ti] = (min(prev[0], s0), max(prev[1], e0)) if prev else (s0, e0)
    out_lines, missing, interpolated = [], [], []
    fills = [fill_line(drop_outliers(times)) for times in per_line]
    if a.fill_missing:
        for i, f in enumerate(fills):
            if f is None and 0 < i < len(fills) - 1 and fills[i - 1] and fills[i + 1]:
                t0, t1 = fills[i - 1][-1][1], fills[i + 1][0][0]
                n = len(lines[i]["tokens"])
                if t1 - t0 >= 0.2 * n:
                    step = (t1 - t0) / n
                    fills[i] = [(t0 + k * step, t0 + (k + 1) * step) for k in range(n)]
                    interpolated.append(lines[i]["text"])
    for ln, times, filled in zip(lines, per_line, fills):
        if filled is None:
            missing.append(ln["text"])
            continue
        # keep words in order even when whisper's times wobble
        fixed, last = [], 0.0
        for s, e in filled:
            s = max(s, last)
            e = min(max(e, s + 0.05), s + MAX_WORD)  # whisper can stretch a last word over a long outro
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
              "lines_missing": missing, "lines_interpolated": interpolated, "unmatched_heard_runs": extra}
    Path(a.out).write_text(json.dumps({"lines": out_lines, "report": report}, indent=1, ensure_ascii=False))
    print(f"matched {acc:.1%} of {len(exp)} lyric words, {len(out_lines)}/{len(lines)} lines timed")
    for t in missing:
        print(f"  ✖ not heard: {t}")
    for t in interpolated:
        print(f"  △ not heard, spread over the gap (--fill-missing): {t}")
    for x in extra:
        print(f"  △ sung but not in lyrics {x['t0']:.2f}-{x['t1']:.2f}s: {x['words']}")
    for ln in out_lines:
        if ln["heard"] < ln["of"]:
            print(f"  · {ln['heard']}/{ln['of']} words heard: {ln['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
