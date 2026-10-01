#!/usr/bin/env python3
"""Song episodes — lyric placement, click removal, beat detection, karaoke overlay and a tiny song build;
finished-song episodes — lyric refining on a synthetic vocal stem, lip_shift / hold0 timing, the lip-sync meter
on a synthetic face clip.

사용: python3 momo/tests/test_song.py        (실패가 있으면 exit 1)

The build test makes a 3-cut song at 320x180 / 10 fps (fast): synthetic instrumental at 96 BPM fitted to
100 BPM, sine "voice" lines, testsrc clips — and checks bar-exact cut lengths, lyric timing and the mix.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

MOMO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MOMO))

import numpy as np  # noqa: E402

from momolib import audio, render  # noqa: E402
from momolib.common import Paths, deep_merge, font_supports_hangul, load_config  # noqa: E402
from momolib.episode import (NarItem, parse_narration, place_song_lines, plan_timeline, track_cut_lyrics,  # noqa: E402
                             track_lines, track_spans, validate_manifest)

SR = 48000
SONG = {"bpm": 100, "beats_per_bar": 4}
FONTS = [*sorted((MOMO / "assets/fonts").glob("*.ttf")), Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")]


def tone(seconds: float, freq: float, sr: int = SR, amp: float = 0.3) -> np.ndarray:
    t = np.arange(int(seconds * sr)) / sr
    env = np.minimum(1.0, np.minimum(t / 0.02, (seconds - t) / 0.05))
    return (amp * np.sin(2 * np.pi * freq * t) * env).astype(np.float32)


def speech_like(seconds: float, lead: float = 0.3, tail: float = 0.4, click_at: float | None = None) -> np.ndarray:
    """Silence, a voiced stretch, silence — optionally a 3 ms click in the trailing silence."""
    x = np.concatenate([np.zeros(int(lead * SR), np.float32), tone(seconds, 220),
                        np.zeros(int(tail * SR), np.float32)])
    if click_at is not None:
        i = int(click_at * SR)
        x[i:i + int(0.003 * SR)] = 0.6
    return x


def music(seconds: float, bpm: float, sr: int = 22050) -> np.ndarray:
    """Chords that change every bar (C F G C …) + a kick on every beat, louder on beat 1."""
    beat = 60.0 / bpm
    n = int(seconds * sr)
    x = np.zeros(n, np.float32)
    chords = [(261.6, 329.6, 392.0), (349.2, 440.0, 523.3), (392.0, 493.9, 587.3), (261.6, 329.6, 392.0)]
    t = np.arange(n) / sr
    bar_idx = (t // (4 * beat)).astype(int) % 4
    for k in range(3):
        f = np.array([c[k] for c in chords])[bar_idx]
        x += 0.08 * np.sin(2 * np.pi * np.cumsum(f) / sr).astype(np.float32)
    kick_t = np.arange(0, int(0.12 * sr)) / sr
    kick = np.sin(2 * np.pi * (60 + 80 * np.exp(-kick_t / 0.03)) * kick_t) * np.exp(-kick_t / 0.05)
    for b in range(int(seconds / beat)):
        i = int(b * beat * sr)
        amp = 0.9 if b % 4 == 0 else 0.45
        x[i:i + len(kick)] += (amp * kick[:n - i]).astype(np.float32)
    return x


# ---------------------------------------------------------------- 단위

def test_place_song_lines(tmp: Path) -> None:
    beat = 0.6
    items = parse_narration("Brush up, brush down! [pause 1] Brush all around!")
    starts, tempos, warns = place_song_lines({"id": "c1"}, items, [1.5, 1.4], SONG, 4.8)
    assert starts[0] == 0.0 and not warns, (starts, warns)
    # line 2: after line 1 (1.5 s) + [pause 1] + gap → first beat at or after 2.58 s = beat 5 (3.0 s)
    assert math.isclose(starts[1], 5 * beat), starts
    assert tempos == [1.0, 1.0], tempos
    starts, tempos, warns = place_song_lines({"id": "c1", "beats": [0, 4]}, items, [3.0, 1.0], SONG, 4.8)
    assert starts == [0.0, 2.4] and tempos[0] > 1.0 and not warns, (starts, tempos, warns)  # sped up to fit
    starts, tempos, warns = place_song_lines({"id": "c1", "beats": [0, 4]}, items, [5.0, 1.0], SONG, 4.8)
    assert tempos[0] == 1.3 and warns and "안 들어감" in warns[0], (tempos, warns)


def test_clean_speech_removes_tail_click(tmp: Path) -> None:
    x = speech_like(1.0, click_at=1.5)
    y = audio.clean_speech(x, SR)
    assert len(y) == len(x)
    assert np.abs(y[int(1.45 * SR):]).max() < 1e-6, "click in the trailing silence must be gone"
    assert np.abs(y[int(0.5 * SR):int(1.1 * SR)]).max() > 0.2, "voice must stay"
    z = audio.clean_speech(x, SR, trim=True)
    assert 1.0 <= len(z) / SR <= 1.1, len(z) / SR
    assert audio.voiced_bounds(np.zeros(SR, np.float32), SR) is None
    w = speech_like(1.0, tail=0.4)  # a click right after the last word, inside the kept tail
    w[int(1.315 * SR):int(1.319 * SR)] = 0.6
    assert np.abs(audio.clean_speech(w, SR)[int(1.31 * SR):int(1.33 * SR)]).max() < 0.05
    w = speech_like(1.0, tail=0.4)  # a longer (15 ms) click just after the voice
    w[int(1.32 * SR):int(1.335 * SR)] = 0.6
    assert np.abs(audio.clean_speech(w, SR)[int(1.31 * SR):int(1.345 * SR)]).max() < 0.05
    t = tone(1.0, 220)
    assert np.array_equal(audio.declick(t, SR), t), "steady voice must be untouched"
    syll = np.concatenate([np.concatenate([tone(0.12, 300), np.zeros(int(0.06 * SR), np.float32)]) for _ in range(6)])
    assert np.abs(audio.declick(syll, SR) - syll).max() < 1e-6, "short syllables are not clicks"


def test_detect_beats(tmp: Path) -> None:
    f = audio.write_wav(tmp / "m.wav", music(40, 96), 22050)
    ana = audio.detect_beats(f, 100)
    assert abs(ana["bpm"] - 96) < 0.15, ana
    bar = 4 * 60 / 96
    off = ana["downbeat0"] % bar
    assert min(off, bar - off) < 0.12, ana  # beat 1 of the bar (beats are 0.625 s apart), onset lag ≤ ~0.1 s


def test_refine_downbeats(tmp: Path) -> None:
    sr = 22050
    beats = [0.5]
    for j in range(1, 4 * 30):  # 30 bars that slow from 120 to ~117 BPM and back (a wandering human-ish tempo)
        bpm = 120 - 3 * math.sin(math.pi * j / 120)
        beats.append(beats[-1] + 60 / bpm)
    n = int((beats[-1] + 2) * sr)
    x = np.zeros(n, np.float32)
    kick_t = np.arange(int(0.12 * sr)) / sr
    kick = (np.sin(2 * np.pi * (60 + 80 * np.exp(-kick_t / 0.03)) * kick_t) * np.exp(-kick_t / 0.05)).astype(np.float32)
    for j, t in enumerate(beats):
        i = int(t * sr)
        x[i:i + len(kick)] += (0.9 if j % 4 == 0 else 0.45) * kick[:n - i]
    f = audio.write_wav(tmp / "drift.wav", x, sr)
    ana = {"bpm": 60 * (len(beats) - 1) / (beats[-1] - beats[0]), "downbeat0": beats[0]}
    downs, st = audio.refine_downbeats(f, ana, 30)
    true = np.array(beats[::4][:30])
    straight = np.array([beats[0] + k * 240 / ana["bpm"] for k in range(30)])

    def spread(t):  # onset detection has a constant bias; what matters is following the wandering tempo
        e = np.asarray(t) - true
        return float(np.abs(e - np.median(e)).max())
    assert st["refined"] and spread(downs) < 0.03 < 0.06 < spread(straight), (st, spread(downs), spread(straight))
    rep = audio.drift_report(f, ana, 30)
    assert rep["trend_ms"] > 30, rep  # the straight grid walks off this song → the report shows it
    steady = audio.write_wav(tmp / "m.wav", music(40, 96), 22050)
    a2 = audio.detect_beats(steady, 100)
    _, st2 = audio.refine_downbeats(steady, a2, 14)
    assert not st2["refined"], st2
    rep2 = audio.drift_report(steady, a2, 14)
    assert abs(rep2["trend_ms"] or 0) < 20, rep2


def test_overlay_frames(tmp: Path) -> None:
    root = tmp / "root"
    cfg = load_config(Paths(root)) if (root / "config.json").exists() else json.loads((MOMO / "config.json").read_text())
    cfg = deep_merge(cfg, {"render": {"width": 640, "height": 360, "fps": 10}})
    font = next(p for p in FONTS if p.exists())
    lines = [("Brush up brush down", 0.0, 2.0, 2.4), ("All around", 2.4, 1.0, 4.8)]
    pat = render.render_song_overlay(lines, {"word": "cup", "text": "Holds water"}, 0.3, font, cfg, 48, tmp / "ov")
    frames = sorted((tmp / "ov").glob("ov_*.png"))
    assert pat is not None and len(frames) == 48
    states = sorted((tmp / "ov").glob("state_*.png"))
    assert 6 <= len(states) < 48, len(states)  # distinct states rendered once, the rest hard-linked
    lay = render.LyricLine("Brush up brush down", font, cfg)
    assert [lay.lit(p) for p in (-1, 0.0, 0.3, 0.99)] == [0, 1, 2, 4]
    assert render.render_song_overlay([], None, 0.0, font, cfg, 10, tmp / "none") is None
    # words light WORD_LEAD (0.05 s) early: "two" sung at 0.93 s is lit on the 0.9 s frame (10 fps), not at 1.0 s
    render.render_song_overlay([("One two", 0.0, 2.0, 2.4, [0.0, 0.465])], None, 0.0, font, cfg, 24, tmp / "lead")
    f = lambda i: tmp / "lead" / f"ov_{i:05d}.png"  # noqa: E731 — equal states are hard links to one PNG
    assert render.WORD_LEAD == 0.05 and f(9).samefile(f(10)) and not f(8).samefile(f(9))


# ---------------------------------------------------------------- 작은 노래 빌드

def make_song_root(tmp: Path) -> Path:
    root = tmp / "root"
    ep = root / "episodes" / "ep90"
    for d in ("clips", "images", "audio/en", "out"):
        (ep / d).mkdir(parents=True)
    cfg = json.loads((MOMO / "config.json").read_text(encoding="utf-8"))
    cfg = deep_merge(cfg, {"languages": ["en"], "render": {"width": 320, "height": 180, "fps": 10}})
    (root / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    shutil.copytree(MOMO / "templates", root / "templates")
    (root / "library").mkdir()
    (root / "library/library.json").write_text(json.dumps({"character_sheets": {}, "clips": {}, "audio": {}}))
    font = next(p for p in FONTS if p.exists() and font_supports_hangul(p))
    (root / "assets/fonts").mkdir(parents=True)
    shutil.copy2(font, root / "assets/fonts" / font.name)
    (root / "assets/sfx").mkdir(parents=True)
    audio.write_wav(root / "assets/sfx/pop.wav", tone(0.2, 880), SR)
    audio.write_wav(ep / "audio/music.wav", music(30, 96), 22050)
    cuts = []
    lines = {"c01": ["Hello hello, it's Momo!"], "c02": ["Brush up brush down", "brush all around!"],
             "c03": ["Bye bye friends!"]}
    lens = {"c01": [1.6], "c02": [1.2, 1.3], "c03": [1.0]}
    for i, cid in enumerate(("c01", "c02", "c03")):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=320x180:r=10:d=4",
                        "-pix_fmt", "yuv420p", str(ep / "clips" / f"{cid}.mp4")], check=True)
        for k, ln in enumerate(lens[cid], 1):
            audio.write_wav(ep / "audio/en" / f"{cid}_{k}.wav", speech_like(ln), SR)
        cuts.append({"id": cid, "scene": i + 1, "type": "V", "image_prompt": "[Momo] waving in a meadow",
                     "motion": "waves one paw", "bars": 2, "narration": {"en": " [pause 0.1] ".join(lines[cid])},
                     **({"beats": [0, 4], "card": {"word": "brush", "text": "Up and down"}} if cid == "c02" else {}),
                     **({"sfx": [{"file": "pop.wav", "at": 0.3}]} if cid == "c01" else {})})
    m = {"ep": "ep90", "status": "producing", "topic": {"en": "Song"}, "title": {"en": "Song test"},
         "song": {**SONG, "music": {"status": "approved", "url": None}}, "cuts": cuts,
         "thumbnail": {"cut": "c02", "text": {"en": "SONG"}}, "upload": {"en": {"title": "Song test"}}}
    (ep / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return root


def test_song_build(tmp: Path) -> None:
    root = make_song_root(tmp)
    paths = Paths(root)
    cfg = load_config(paths)
    m = json.loads((root / "episodes/ep90/manifest.json").read_text())
    plans, total, warns = plan_timeline(paths, cfg, m, "en")
    assert math.isclose(total, 3 * 2 * 2.4), total  # 3 cuts × 2 bars × 2.4 s
    assert [p.start for p in plans] == [0.0, 4.8, 9.6] and all(p.xf_in == 0 for p in plans)
    c2 = plans[1]
    assert c2.block_starts == [0.0, 2.4] and len(c2.lyrics) == 2 and c2.card, (c2.block_starts, c2.lyrics)
    assert c2.lyrics[0][0] == "Brush up brush down" and math.isclose(c2.lyrics[0][3], 2.4)
    assert 1.1 < c2.block_lens[0] < 1.4, c2.block_lens  # trimmed voice, not the file with its silences
    assert not plans[0].keyword

    r = subprocess.run([sys.executable, str(MOMO / "build.py"), "--root", str(root), "--ep", "ep90", "--lang", "en",
                        "--jobs", "2"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    tl = json.loads((root / "episodes/ep90/out/ep90_en_timeline.json").read_text())
    assert tl["total_frames"] == 144 and tl["audio"]["music"]["tempo_ratio"] > 1.03, tl["audio"]
    assert [ly["at"] for ly in tl["cuts"][1]["lyrics"]] == [0.0, 2.4], tl["cuts"][1]
    mp4 = root / "episodes/ep90/out/ep90_en.mp4"
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                        capture_output=True, text=True, check=True)
    assert abs(float(pr.stdout) - 14.4) < 0.1, pr.stdout
    a = audio.decode(mp4, SR, 1)[:, 0]
    assert np.abs(a).max() < 0.95 and np.sqrt((a ** 2).mean()) > 0.01  # music + voice, no clipping


# ---------------------------------------------------------------- 노래 파일(song.track) 에피소드

TRACK_SONG = {"bpm": 120.0, "beats_per_bar": 4,
              "track": {"status": "approved", "sha1": "abc123", "duration": 14.0, "start": 0.0, "end": 13.0,
                        "analysis": {"bpm": 120.0, "downbeat0": 0.5, "confidence": 9.0}},
              "vocals": {"status": "approved", "sha1": "def456"},
              "lyrics": [{"text": "Crunch crunch munch", "words": [["Crunch", 0.9, 1.2], ["crunch", 1.3, 1.6],
                                                                  ["munch", 1.8, 2.4]]},
                         {"text": "Carrot!", "words": [["Carrot!", 4.6, 5.3]]},
                         {"text": "Yellow corn", "words": [["Yellow", 9.0, 9.5], ["corn", 9.6, 10.4]]}]}


def track_cuts() -> list[dict]:
    base = {"image_prompt": "[Momo] in a kitchen", "motion": "sings to the viewer"}
    return [{"id": "c01", "scene": 1, "type": "V", "bars": 2, **base},
            {"id": "c02", "scene": 2, "type": "V", "bars": 1, "lipsync": True, "clip_model": "wan2_7",
             "clip_seconds": 4, **base},
            {"id": "c03", "scene": 2, "type": "V", "bars": 1, "clip_from": {"cut": "c02", "at": 2.0},
             "lipsync_ok": True, **base},
            {"id": "c04", "scene": 3, "type": "V", "bars": 2, "card": {"word": "corn", "text": "Yellow and sweet"},
             **base}]


def test_track_spans_and_lyrics(tmp: Path) -> None:
    spans = track_spans(TRACK_SONG, track_cuts())
    # bar = 2 s from downbeat 0.5: c01 holds the pickup (0 → bar 2), the last cut runs to track.end
    assert spans == [(0.0, 4.5), (4.5, 6.5), (6.5, 8.5), (8.5, 13.0)], spans
    lines = track_lines(TRACK_SONG)
    assert [ln["text"] for ln in lines] == ["Crunch crunch munch", "Carrot!", "Yellow corn"]
    assert math.isclose(lines[0]["until"], 2.4 + 1.2) and math.isclose(lines[1]["until"], 5.3 + 1.2)
    ly = track_cut_lyrics(lines, 0.0, 4.5, 2.0)  # c02
    assert len(ly) == 1 and ly[0][0] == "Carrot!" and math.isclose(ly[0][1], 0.1), ly
    first = track_cut_lyrics(lines, 0.0, 0.0, 4.5)[0]
    assert first[4] == [0.0, round(0.4 / 1.5, 4), round(0.9 / 1.5, 4)], first  # measured word starts
    font = next(p for p in FONTS if p.exists())
    cfg = json.loads((MOMO / "config.json").read_text())
    lay = render.LyricLine(first[0], font, cfg, first[4])
    assert [lay.lit(p) for p in (0.0, 0.3, 0.7)] == [1, 2, 3]


def test_track_lines_refined_words(tmp: Path) -> None:
    """Refined lyrics store [word, t0, t1, t_whisper]: the 4th element changes nothing downstream."""
    song = json.loads(json.dumps(TRACK_SONG))
    for ln in song["lyrics"]:
        ln["words"] = [w + [round(w[1] - 0.2, 3)] for w in ln["words"]]
    assert track_lines(song) == track_lines(TRACK_SONG)
    a, b = track_lines(song), track_lines(TRACK_SONG)
    assert track_cut_lyrics(a, 0.0, 0.0, 4.5) == track_cut_lyrics(b, 0.0, 0.0, 4.5)
    cfg = json.loads((MOMO / "config.json").read_text())
    cfg["languages"] = ["en"]
    assert not validate_manifest(cfg, {"ep": "ep91", "song": song, "cuts": track_cuts()})[0]


# ---------------------------------------------------------------- lyrics refine (vocal-stem onsets)

VSR = 22050


def sung(seconds: float, f0: float = 300.0, amp: float = 0.25) -> np.ndarray:
    """A sung vowel: harmonics of f0 up to ~3 kHz, 10 ms attack, 20 ms release."""
    t = np.arange(int(seconds * VSR)) / VSR
    env = np.minimum(1.0, np.minimum(t / 0.01, (seconds - t) / 0.02))
    x = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 11))
    return (amp * x * env / 2).astype(np.float32)


def hiss(seconds: float, amp: float = 0.08) -> np.ndarray:
    """An "s": noise in 4.5–9.5 kHz only."""
    n = int(seconds * VSR)
    spec = np.fft.rfft(np.random.default_rng(1).standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / VSR)
    spec[(f < 4500) | (f > 9500)] = 0
    x = np.fft.irfft(spec, n)
    env = np.minimum(1.0, np.arange(n) / (0.005 * VSR))
    return (amp * x / np.abs(x).max() * env).astype(np.float32)


def vocal(parts: list[tuple[float, np.ndarray]], total: float) -> np.ndarray:
    x = np.zeros(int(total * VSR), np.float32)
    for t, s in parts:
        i = int(round(t * VSR))
        x[i:i + len(s)] += s[:len(x) - i]
    return x


# stem: One 0.5 | rest | all 1.6 | rest | s~sun 2.6 (hiss) 2.78 (vowel) | rest |
#       Look 4.0 (160 ms), closure 120 ms, up 4.28 (long)
REF_STEM = [(0.5, sung(0.4)), (1.6, sung(0.4, 350)), (2.6, hiss(0.19)), (2.78, sung(0.42, 330)),
            (4.0, sung(0.16, 330)), (4.28, sung(0.62, 300))]
# whisper-like stamps: "all" glued to the end of "One" (in the rest), "sun" on its vowel, the last line LATE
REF_LYRICS = [{"text": "One", "section": "Verse", "words": [["One", 0.5, 0.9]]},
              {"text": "all sun", "section": "Verse", "words": [["all", 0.95, 1.9], ["sun", 2.78, 3.2]]},
              {"text": "Look up", "section": "Verse", "words": [["Look", 4.3, 4.6], ["up", 4.62, 4.9]]}]


def test_refine_lyrics(tmp: Path) -> None:
    from momolib import lyrics_refine as lr, vocal_onsets as vo
    fe = vo.features(vocal(REF_STEM, 5.5))
    ons = vo.detect(fe)
    out, rep = lr.refine(REF_LYRICS, fe, ons)
    t0 = {w[0]: w[1] for ln in out for w in ln["words"]}
    want = {"One": 0.5, "all": 1.6, "sun": 2.6, "Look": 4.0, "up": 4.28}
    assert all(abs(t0[w] - t) < 0.035 for w, t in want.items()), t0
    assert [w[3] for ln in out for w in ln["words"]] == [0.5, 0.95, 2.78, 4.3, 4.62]  # t_whisper kept
    assert all(len(w) == 4 and w[1] < w[2] for ln in out for w in ln["words"])
    assert out[1]["section"] == "Verse" and out[1]["text"] == "all sun"
    assert rep["loose"] == 2 and rep["moved"] == 4 and not [f for f in rep["flags"] if f["kind"] == "lag"], rep
    again, _ = lr.refine(out, fe, ons)   # always from t_whisper → the same result
    assert again == out
    # without the rest rule (the prototype), the late line stays late and the lag guard reports it
    keep = lr.KEEP_REST, lr.SHIFT_ROUNDS
    lr.KEEP_REST, lr.SHIFT_ROUNDS = 0.0, 1
    try:
        old, rep0 = lr.refine(REF_LYRICS, fe, ons)
    finally:
        lr.KEEP_REST, lr.SHIFT_ROUNDS = keep
    assert old[2]["words"][0][1] > 4.2, old[2]
    lag = [f for f in rep0["flags"] if f["kind"] == "lag"]
    assert len(lag) == 1 and abs(lag[0]["t"] - 4.0) < 0.035 and lag[0]["word"] == "Look" and lag[0]["ms"] > 100, lag
    assert lr.syllables("Ding-dong-dang!") == 3 and lr.syllables("seven,") == 2 and lr.syllables("little") == 2
    assert [lr.onset_class(w) for w in ("Six", "How", "two", "One", "the")] == ["fric", "h", "stop", "", ""]


def test_refine_phase_guard(tmp: Path) -> None:
    from momolib import lyrics_refine as lr
    song = {"bpm": 120.0, "beats_per_bar": 4, "track": {"analysis": {"bpm": 120.0, "downbeat0": 0.0,
                                                                     "downbeats": [2.0 * k for k in range(12)]}}}
    starts = [1.75, 3.75, 5.75, 8.1, 9.75]   # pickups on beat 3.5 of the bar before; the 4th comes 0.7 beat late
    lines = [{"text": f"line {i}", "section": "Verse 1", "words": [[f"w{i}", t, t + 0.4]]}
             for i, t in enumerate(starts)]
    flags = lr.phase_guard(lines, song)
    assert [(f["line"], f["beats"]) for f in flags] == [(3, 0.7)], flags
    assert lr.phase_guard(lines, {"bpm": 120}) == []   # no bar grid → no guard


def test_song_track_lyrics_cli(tmp: Path) -> None:
    root = make_track_root(tmp)
    ep = root / "episodes/ep91"
    st = [sys.executable, str(MOMO / "song_track.py"), "--root", str(root), "lyrics", "--ep", "ep91"]
    m = json.loads((ep / "manifest.json").read_text())
    m["song"]["lyrics"].append({"text": "(hum)"})            # a line without word times survives a re-refine
    (ep / "manifest.json").write_text(json.dumps(m))
    r = subprocess.run(st, capture_output=True, text=True)   # no --align: refine the current song.lyrics
    assert r.returncode == 0, r.stdout + r.stderr
    m = json.loads((ep / "manifest.json").read_text())
    hum = m["song"]["lyrics"][-1]
    assert hum["text"] == "(hum)" and not hum.get("words"), hum
    words = [w for ln in m["song"]["lyrics"] for w in ln.get("words") or []]
    assert all(len(w) == 4 for w in words) and [w[3] for w in words] == [
        w[1] for ln in TRACK_SONG["lyrics"] for w in ln["words"]], words
    assert all(abs(w[1] - w[3]) < 0.04 for w in words), words   # stamps sit on the synthetic notes already
    rec = m["song"]["track"]["lyrics_refine"]
    assert set(rec) == {"v", "vocals_sha1", "moved", "loose", "flags"} and len(rec["vocals_sha1"]) == 40, rec
    assert "보정" in r.stdout, r.stdout
    al = tmp / "align.json"   # --align: whisper times shifted early (in the rest) → back on the notes
    al.write_text(json.dumps({"lines": [{"text": ln["text"], "words": [[w[0], w[1] - 0.25, w[2]] for w in ln["words"]]}
                                        for ln in TRACK_SONG["lyrics"]]}))
    r = subprocess.run(st + ["--align", str(al)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    m = json.loads((ep / "manifest.json").read_text())
    got = [w[1] for ln in m["song"]["lyrics"] for w in ln["words"]]
    true = [w[1] for ln in TRACK_SONG["lyrics"] for w in ln["words"]]
    assert all(abs(a - b) < 0.04 for a, b in zip(got, true)), (got, true)
    r = subprocess.run(st + ["--align", str(al), "--no-refine"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    m = json.loads((ep / "manifest.json").read_text())
    assert all(len(w) == 3 for ln in m["song"]["lyrics"] for w in ln["words"])
    assert "lyrics_refine" not in m["song"]["track"]
    sec = [sys.executable, str(MOMO / "song_track.py"), "--root", str(root), "sections", "--ep", "ep91"]
    r = subprocess.run(sec, capture_output=True, text=True)
    assert r.returncode == 0 and "보정되지 않음" in r.stdout and "cut_at" in r.stdout, r.stdout + r.stderr
    r = subprocess.run(st + ["--no-refine"], capture_output=True, text=True)
    assert r.returncode != 0 and "--align" in r.stdout + r.stderr


# ---------------------------------------------------------------- lip-sync meter

def face(open_: float, w: int = 320, h: int = 240) -> np.ndarray:
    """A Momo-like frame for onmodel.eye_pair: cream fur, mint overalls, two dark eyes, a dark mouth whose height
    follows open_ (0 … 1)."""
    yy, xx = np.mgrid[0:h, 0:w]
    im = np.empty((h, w, 3), np.uint8)
    im[:] = (240, 226, 200)
    im[170:, 90:230] = (120, 220, 180)
    for cx in (130, 190):
        im[(xx - cx) ** 2 + (yy - 80) ** 2 <= 12 ** 2] = (30, 25, 35)
    im[((xx - 160) / 18.0) ** 2 + ((yy - 125) / (2 + 14 * open_)) ** 2 <= 1] = (90, 20, 30)
    return im


def syllable_env(t: np.ndarray) -> np.ndarray:
    """Sung syllables every 0.37 s with uneven loudness (0 … 1)."""
    out = np.zeros_like(t)
    for k, s in enumerate(np.arange(0.3, 3.6, 0.37)):
        out += (0.5 + 0.125 * ((k * 7) % 5)) * np.clip((t - s) / 0.03, 0, 1) * np.clip((s + 0.22 - t) / 0.05, 0, 1)
    return out


def test_lipsync_meter(tmp: Path) -> None:
    from momolib import lipsync
    # 1. the correlation alone: a mouth curve 120 ms behind the voice reads +120 ms, confidently
    t = np.arange(0, 4, 1 / 30)
    ts = np.arange(0, 6, 1 / lipsync.SR)
    env = lipsync.envelope(np.sin(2 * np.pi * 220 * ts) * syllable_env(ts))
    r = lipsync.lag_of(t, syllable_env(t - 0.12), env, 0.0, 3.6)
    assert abs(r["lag_ms"] - 120) <= 10 and r["conf"] == "high", r
    # 2. a synthetic clip whose mouth moves 100 ms after the voice, placed at song time 5.0
    fps, lag = 30, 0.1
    clip = tmp / "c02_en.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "320x240",
                          "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(clip)],
                         stdin=subprocess.PIPE)
    for o in np.clip(syllable_env(np.arange(int(4 * fps)) / fps - lag), 0, 1):
        p.stdin.write(face(float(o)).tobytes())
    p.stdin.close()
    assert p.wait() == 0
    ts = np.arange(int(10 * lipsync.SR)) / lipsync.SR
    stem = lipsync.envelope((np.sin(2 * np.pi * 220 * ts) * syllable_env(ts - 5.0)).astype(np.float32))
    shot = {"id": "c02", "clip": clip, "start": 5.0, "dur": 3.5, "off": 0.0, "hold0": 0.0, "lip_shift": 0.0,
            "reuse_of": None, "owner": "c02"}
    res = lipsync.measure(shot, stem, tmp / "cache", diagnostics=False)
    assert res["found"] == 1.0 and abs(res["shown"]["lag_ms"] - 100) <= 20, res
    assert res["verdict"] == "fix" and res["shown"]["conf"] == "high", res   # +100 ms is outside −120 … +40
    assert lipsync.suggest(res["shown"]["lag_ms"], 0.0, fps) == round(round(-0.17 * fps) / fps, 3)  # → −70 ms
    held = lipsync.measure(dict(shot, hold0=0.1), stem, tmp / "cache", diagnostics=False)   # cached series
    assert abs(held["shown"]["lag_ms"] - res["shown"]["lag_ms"] - 100) <= 15, held   # hold0 delays the picture
    early = lipsync.measure(dict(shot, off=0.2), stem, tmp / "cache", diagnostics=False)   # start 0.2 s in
    assert abs(early["shown"]["lag_ms"] - res["shown"]["lag_ms"] + 200) <= 15, early
    assert lipsync.verdict({"lag_ms": -60, "conf": "high"}, [{"lag_ms": -50}, {"lag_ms": -70}]) == "ok"
    assert lipsync.verdict({"lag_ms": -60, "conf": "high"}, [{"lag_ms": 50}, {"lag_ms": -70}]) == "unreliable"
    assert lipsync.verdict({"lag_ms": -160, "conf": "low"}, [{"lag_ms": -150}, {"lag_ms": -170}]) == "unreliable"
    # 3. shots(): own lip-sync cuts and reuses of them, the reuse's lip_shift owned by its source
    man = {"song": {"track": {"start": 0.0}}, "cuts": [
        {"id": "c01", "type": "L"}, {"id": "c02", "type": "V", "lipsync": True, "lip_shift": 0.1},
        {"id": "c03", "type": "V", "clip_from": {"cut": "c02", "at": 0.0}}, {"id": "c04", "type": "V"}]}
    tl = {"cuts": [{"id": c, "start": i * 2.0, "dur": 2.0, "source": f"episodes/ep91/clips/{c}.mp4",
                    "source_kind": "video", "hold0": 0.1 if c in ("c02", "c03") else 0.0,
                    **({"lip_shift": 0.1} if c in ("c02", "c03") else {})}
                   for i, c in enumerate(("c01", "c02", "c03", "c04"))]}
    got = lipsync.shots(tl, man, tmp)
    assert [(s["id"], s["owner"], s["reuse_of"], s["hold0"], s["lip_shift"]) for s in got] == [
        ("c02", "c02", None, 0.1, 0.1), ("c03", "c02", "c02", 0.1, 0.1)], got


def test_track_validate_and_slots(tmp: Path) -> None:
    from momolib.genrec import cut_slots, song_slots
    cfg = json.loads((MOMO / "config.json").read_text())
    cfg["languages"] = ["en"]
    m = {"ep": "ep91", "song": json.loads(json.dumps(TRACK_SONG)), "cuts": track_cuts()}
    errors, warns = validate_manifest(cfg, m)
    assert not errors, errors
    m["cuts"][2]["clip_from"] = {"cut": "c03", "at": 0}  # itself a clip_from cut → error
    errors, _ = validate_manifest(cfg, m)
    assert any("clip_from" in e for e in errors), errors
    m["cuts"][2]["clip_from"] = {"cut": "c02", "at": 3.5}  # 2 s from 3.5 s of a 4 s clip → warning
    _, warns = validate_manifest(cfg, m)
    assert any("안 남음" in w for w in warns), warns
    paths = Paths(tmp)
    assert cut_slots(paths, cfg, "ep91", m["cuts"][2]) == []  # reused clip → no image, no clip of its own
    assert [s.stem for s in song_slots(paths, m)] == ["song", "song_vocals"]
    sys.path.insert(0, str(MOMO))
    import hf_jobs
    assert hf_jobs.track_window(m, "c02") == [4.5, 6.5]
    slot = next(s for s in cut_slots(paths, cfg, "ep91", m["cuts"][1]) if s.kind == "clip")
    _, ref, why = hf_jobs.clip_links(cfg, m, slot)
    assert ref is None and "노래 보컬" in why, why
    m["cuts"][1]["nar_ref"] = {"en": {"media_id": "M1", "track_sha1": "abc123", "window": [4.5, 6.5]}}
    assert hf_jobs.clip_links(cfg, m, slot)[1:] == ("M1", None)
    m["cuts"][0]["bars"] = 3  # the grid moved → the pinned slice is stale
    assert hf_jobs.clip_links(cfg, m, slot)[1] is None


def test_align_lyrics(tmp: Path) -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location("align_lyrics", MOMO / "tools/align_lyrics.py")
    al = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(al)
    exp = ["crunch", "crunch", "munch", "munch", "can", "you", "say", "carrot"]
    got = ["crunch", "munch", "munch", "la", "la", "can", "you", "sai", "carrot"]  # one missing, extras, a typo
    m = al.align(exp, got)
    assert sorted(m[:2], key=str) == [0, None] and m[2:] == [1, 2, 5, 6, 7, 8], m  # either "crunch" was the lost one
    assert not al.similar("crunch", "munch") and al.similar("carrots", "carrot")
    filled = al.fill_line([(1.0, 1.2), None, (1.6, 1.8)])
    assert filled[1][0] >= 1.2 and filled[1][1] <= 1.6, filled
    assert al.fill_line([None, None]) is None
    assert al.drop_outliers([(104.6, 106.3), (106.3, 106.8), (134.7, 134.8)])[2] is None  # "you!" matched in the outro
    (tmp / "l.md").write_text("x\n```\n[Verse 1]\nCan you say carrot?\n(Carrot!)\n```\n")
    lines = al.read_lyrics(tmp / "l.md")
    assert [(ln["section"], ln["text"]) for ln in lines] == [("Verse 1", "Can you say carrot?"),
                                                             ("Verse 1", "Carrot!")]
    (tmp / "l2.md").write_text("```style\nkids song\n```\n\n```\n[Chorus]\nOne, two!\n```\n")
    assert [ln["text"] for ln in al.read_lyrics(tmp / "l2.md")] == ["One, two!"]  # the style block is skipped
    assert al.norm("10") == "ten" and al.norm("Three!") == "three"


def test_track_cut_at(tmp: Path) -> None:
    cuts = track_cuts()
    cuts[1]["cut_at"] = 4.3   # c02 starts on the sung pickup (0.2 s before its bar line) — c01 ends there
    cuts[3]["cut_at"] = 8.8   # c04 starts 0.3 s after its bar line — c03 runs on
    assert track_spans(TRACK_SONG, cuts) == [(0.0, 4.3), (4.3, 6.5), (6.5, 8.8), (8.8, 13.0)]
    cfg = json.loads((MOMO / "config.json").read_text())
    cfg["languages"] = ["en"]
    m = {"ep": "ep91", "song": json.loads(json.dumps(TRACK_SONG)), "cuts": cuts}
    errors, _ = validate_manifest(cfg, m)
    assert not errors, errors
    cuts[2]["cut_at"] = 4.5   # before c02's start → c02 would be 0.2 s → error
    errors, _ = validate_manifest(cfg, m)
    assert any("cut_at" in e for e in errors), errors
    cuts[2]["cut_at"] = "6.5"
    errors, _ = validate_manifest(cfg, m)
    assert any("cut_at 은" in e for e in errors), errors


def test_track_lipsync_window_offset(tmp: Path) -> None:
    root = make_track_root(tmp)
    paths = Paths(root)
    cfg = load_config(paths)
    m = json.loads((root / "episodes/ep91/manifest.json").read_text())
    m["cuts"][1]["nar_ref"] = {"en": {"media_id": "M1", "track_sha1": "abc123", "window": [4.5, 6.5]}}
    m["cuts"][1]["cut_at"] = 4.8     # starts 0.3 s into its pinned vocal window → the clip starts 0.3 s in
    plans, _, warns = plan_timeline(paths, cfg, m, "en")
    assert math.isclose(plans[1].src_offset, 0.3) and plans[1].hold0 == 0.0, (plans[1].src_offset, warns)
    m["cuts"][1]["cut_at"] = 4.2     # starts before the window → hold the first frame 0.3 s
    m["cuts"][2]["cut_at"] = 7.0     # ends 0.5 s after the window → the reference is silent there
    plans, _, warns = plan_timeline(paths, cfg, m, "en")
    assert plans[1].src_offset == 0.0 and math.isclose(plans[1].hold0, 0.3), plans[1]
    assert plans[1].nar_offset == 0.0, plans[1].nar_offset  # the hold is no longer folded into nar_offset
    assert any("첫 프레임 정지" in w for w in warns) and any("입이 닫힘" in w for w in warns), warns
    m["cuts"][1]["clip_at"] = 0.5    # explicit start into its own clip wins (e.g. a count-in reusing the chorus take)
    m["cuts"][0]["clip_at"] = 1.0
    plans, _, _ = plan_timeline(paths, cfg, m, "en")
    assert plans[1].src_offset == 0.5 and plans[0].src_offset == 1.0


def test_track_lip_shift(tmp: Path) -> None:
    """cut.lip_shift: + = picture later. Window case off = cut start − window start − ls, clip_at − ls,
    clip_from at − ls (inherited from a lip-sync source); src_offset = max(0, off), hold0 = max(0, −off)."""
    root = make_track_root(tmp)
    paths = Paths(root)
    cfg = load_config(paths)
    m = json.loads((root / "episodes/ep91/manifest.json").read_text())
    c02, c03 = m["cuts"][1], m["cuts"][2]
    c02["nar_ref"] = {"en": {"media_id": "M1", "track_sha1": "abc123", "window": [4.5, 6.5]}}
    spans = track_spans(m["song"], m["cuts"])
    c02["lip_shift"] = 0.1           # c02 starts on its window → hold frame 0 for 0.1 s, nothing to warn about
    plans, _, warns = plan_timeline(paths, cfg, m, "en")
    p2, p3 = plans[1], plans[2]
    assert p2.src_offset == 0.0 and math.isclose(p2.hold0, 0.1) and p2.lip_shift == 0.1, (p2.src_offset, p2.hold0)
    assert not any("첫 프레임 정지" in w for w in warns), warns
    assert p2.lip_locked and p3.lip_locked and not plans[0].lip_locked and not plans[3].lip_locked
    assert math.isclose(p3.src_offset, 1.9) and p3.hold0 == 0.0 and p3.lip_shift == 0.1  # clip_from at 2.0, inherited
    assert track_spans(m["song"], m["cuts"]) == spans  # cut boundaries never move
    c03["clip_from"]["at"] = 0.0
    p3 = plan_timeline(paths, cfg, m, "en")[0][2]
    assert p3.src_offset == 0.0 and math.isclose(p3.hold0, 0.1), (p3.src_offset, p3.hold0)
    c03["clip_from"]["at"] = 0.3
    p3 = plan_timeline(paths, cfg, m, "en")[0][2]
    assert math.isclose(p3.src_offset, 0.2) and p3.hold0 == 0.0, p3.src_offset
    c03["lip_shift"] = 0.0           # its own value wins over the source's
    p3 = plan_timeline(paths, cfg, m, "en")[0][2]
    assert math.isclose(p3.src_offset, 0.3) and p3.lip_shift == 0.0
    c02["lip_shift"] = -0.1          # picture earlier: start 0.1 s into the clip
    p2 = plan_timeline(paths, cfg, m, "en")[0][1]
    assert math.isclose(p2.src_offset, 0.1) and p2.hold0 == 0.0
    c02["lip_shift"], c02["clip_at"] = 0.1, 0.5   # clip_at − ls
    p2 = plan_timeline(paths, cfg, m, "en")[0][1]
    assert math.isclose(p2.src_offset, 0.4) and p2.hold0 == 0.0
    del c02["clip_at"]
    c02["cut_at"] = 4.2              # 0.3 s before the window + ls 0.1 → hold 0.4, of which 0.3 s is unasked → warn
    _, _, warns = plan_timeline(paths, cfg, m, "en")
    assert any("첫 프레임 정지" in w and "0.30s" in w for w in warns), warns
    c03["cut_at"] = 6.8              # c02 ends 0.3 s after its window: silent beyond win1 + ls + 0.15 = 6.75
    _, _, warns = plan_timeline(paths, cfg, m, "en")
    assert any("입이 닫힘" in w for w in warns), warns
    c02["lip_shift"] = 0.2           # … unless the picture runs that much later (6.85)
    _, _, warns = plan_timeline(paths, cfg, m, "en")
    assert not any("입이 닫힘" in w for w in warns), warns
    # validation: a number within ±0.5 s, only on lip-sync cuts and on clip_from reuses of one
    cfg2 = json.loads((MOMO / "config.json").read_text())
    cfg2["languages"] = ["en"]
    assert not validate_manifest(cfg2, m)[0]
    for cid, v in (("c02", 0.6), ("c02", "0.1"), ("c02", True), ("c01", 0.1), ("c04", 0.1)):
        mm = json.loads(json.dumps(m))
        next(c for c in mm["cuts"] if c["id"] == cid)["lip_shift"] = v
        errors, _ = validate_manifest(cfg2, mm)
        assert any("lip_shift" in e for e in errors), (cid, v, errors)
    mm = json.loads(json.dumps(m))
    mm["cuts"][1]["lipsync"] = False  # c03's source is no lip-sync cut any more
    errors, _ = validate_manifest(cfg2, mm)
    assert any(e.startswith("c03: lip_shift") for e in errors), errors
    # every cut's segment key has hold0 (a reuse re-renders when its source's lip_shift changes) and the lock
    import build
    font = next(p for p in FONTS if p.exists())
    c03.pop("lip_shift")
    c03["clip_from"]["at"] = 0.0
    keys = []
    for ls in (0.0, 0.1):
        c02["lip_shift"] = ls
        plans, _, _ = plan_timeline(paths, cfg, m, "en")
        keys.append({s.plan.id: s.key for s in build.make_segs(plans, cfg, tmp, font)})
    assert keys[0]["c03"] != keys[1]["c03"] and keys[0]["c01"] == keys[1]["c01"], keys


def make_track_root(tmp: Path) -> Path:
    root = tmp / "root"
    ep = root / "episodes" / "ep91"
    for d in ("clips", "images", "audio/en", "out"):
        (ep / d).mkdir(parents=True)
    cfg = json.loads((MOMO / "config.json").read_text(encoding="utf-8"))
    cfg = deep_merge(cfg, {"languages": ["en"], "render": {"width": 320, "height": 180, "fps": 10}})
    (root / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    shutil.copytree(MOMO / "templates", root / "templates")
    (root / "library").mkdir()
    (root / "library/library.json").write_text(json.dumps({"character_sheets": {}, "clips": {}, "audio": {}}))
    font = next(p for p in FONTS if p.exists() and font_supports_hangul(p))
    (root / "assets/fonts").mkdir(parents=True)
    shutil.copy2(font, root / "assets/fonts" / font.name)
    bed = music(14, 120, SR)
    voc = np.zeros_like(bed)
    for ln in TRACK_SONG["lyrics"]:
        for _, a, b in ln["words"]:
            voc[int(a * SR):int(a * SR) + len(tone(b - a, 330))] += tone(b - a, 330)
    audio.write_wav(ep / "audio/song.wav", np.stack([bed + voc, bed + voc], axis=1) * 0.7, SR)
    audio.write_wav(ep / "audio/song_vocals.wav", voc, SR)
    for cid, d in (("c01", 5), ("c02", 4), ("c04", 5)):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=320x180:r=10:d={d}",
                        "-pix_fmt", "yuv420p", str(ep / "clips" / (f"{cid}_en.mp4" if cid == "c02" else f"{cid}.mp4"))],
                       check=True)
    m = {"ep": "ep91", "status": "producing", "topic": {"en": "Veggies"}, "title": {"en": "Track test"},
         "song": json.loads(json.dumps(TRACK_SONG)), "cuts": track_cuts(),
         "thumbnail": {"cut": "c04", "text": {"en": "VEGGIES"}}, "upload": {"en": {"title": "Track test"}}}
    (ep / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return root


def test_track_build(tmp: Path) -> None:
    root = make_track_root(tmp)
    paths = Paths(root)
    cfg = load_config(paths)
    mf = root / "episodes/ep91/manifest.json"
    m = json.loads(mf.read_text())
    m["cuts"][1]["lip_shift"] = 0.1           # c02's picture 0.1 s later; c03 reuses c02 from 2.5 − 0.1 s
    m["cuts"][2]["clip_from"]["at"] = 2.5     # 1.6 s of clip left for a 2 s cut: held, never slowed (lip-sync)
    mf.write_text(json.dumps(m))
    plans, total, warns = plan_timeline(paths, cfg, m, "en")
    assert math.isclose(total, 13.0) and [p.start for p in plans] == [0.0, 4.5, 6.5, 8.5], (total, warns)
    assert math.isclose(plans[2].src_offset, 2.4) and plans[2].source.name == "c02_en.mp4"
    assert math.isclose(plans[1].hold0, 0.1) and plans[1].src_offset == 0.0
    assert not any(p.block_starts for p in plans) and plans[3].card
    r = subprocess.run([sys.executable, str(MOMO / "build.py"), "--root", str(root), "--ep", "ep91", "--lang", "en",
                        "--jobs", "2"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    tl = json.loads((root / "episodes/ep91/out/ep91_en_timeline.json").read_text())
    assert tl["total_frames"] == 130 and tl["audio"]["track"]["file"] == "song.wav", tl["audio"]
    assert tl["audio"].get("music") is None and tl["audio"]["bgm"] is None
    assert tl["cuts"][2]["clip_offset"] == 2.4 and tl["cuts"][1]["lyrics"][0]["text"] == "Carrot!", tl["cuts"][1:3]
    assert tl["cuts"][1]["hold0"] == 0.1 and tl["cuts"][2]["lip_shift"] == 0.1 and tl["cuts"][0]["hold0"] == 0.0
    assert "x1.00" in tl["cuts"][2]["render"], tl["cuts"][2]["render"]   # a reused lip-sync take is not slowed
    r = subprocess.run([sys.executable, str(MOMO / "song_track.py"), "--root", str(root), "lipsync", "--ep", "ep91"],
                       capture_output=True, text=True)   # testsrc clips: no Momo to measure → unreliable, no crash
    assert r.returncode == 0 and "unreliable 2" in r.stdout, r.stdout + r.stderr
    mp4 = root / "episodes/ep91/out/ep91_en.mp4"
    a = audio.decode(mp4, SR, 1)[:, 0]
    assert abs(len(a) / SR - 13.0) < 0.1 and np.sqrt((a ** 2).mean()) > 0.02

    r = subprocess.run([sys.executable, str(MOMO / "song_track.py"), "--root", str(root), "refs", "--ep", "ep91"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    ref = audio.decode(root / "episodes/ep91/audio/refs/c02_en.wav", SR, 1)[:, 0]
    assert abs(len(ref) / SR - 3.0) < 0.01  # the 2 s cut window of the vocal stem, padded to REF_MIN (3 s)
    assert np.abs(ref[:int(0.05 * SR)]).max() < 1e-3 < np.abs(ref[int(0.2 * SR):int(0.7 * SR)]).max()  # gated


def main() -> int:
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        with tempfile.TemporaryDirectory(prefix="momo_song_test_") as d:
            try:
                fn(Path(d))
                print(f"✔ {name}")
            except Exception:  # noqa: BLE001
                failed.append(name)
                print(f"✖ {name}")
                traceback.print_exc()
    print(f"\ntest_song: {len(tests) - len(failed)}/{len(tests)} 통과" + (f" — 실패: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
