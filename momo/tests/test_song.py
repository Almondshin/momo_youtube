#!/usr/bin/env python3
"""Song episodes — lyric placement, click removal, beat detection, karaoke overlay and a tiny song build.

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
    steady = audio.write_wav(tmp / "m.wav", music(40, 96), 22050)
    a2 = audio.detect_beats(steady, 100)
    _, st2 = audio.refine_downbeats(steady, a2, 14)
    assert not st2["refined"], st2


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
    (tmp / "l.md").write_text("x\n```\n[Verse 1]\nCan you say carrot?\n(Carrot!)\n```\n")
    lines = al.read_lyrics(tmp / "l.md")
    assert [(ln["section"], ln["text"]) for ln in lines] == [("Verse 1", "Can you say carrot?"),
                                                             ("Verse 1", "Carrot!")]


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
    m = json.loads((root / "episodes/ep91/manifest.json").read_text())
    plans, total, warns = plan_timeline(paths, cfg, m, "en")
    assert math.isclose(total, 13.0) and [p.start for p in plans] == [0.0, 4.5, 6.5, 8.5], (total, warns)
    assert plans[2].src_offset == 2.0 and plans[2].source.name == "c02_en.mp4"
    assert not any(p.block_starts for p in plans) and plans[3].card
    r = subprocess.run([sys.executable, str(MOMO / "build.py"), "--root", str(root), "--ep", "ep91", "--lang", "en",
                        "--jobs", "2"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    tl = json.loads((root / "episodes/ep91/out/ep91_en_timeline.json").read_text())
    assert tl["total_frames"] == 130 and tl["audio"]["track"]["file"] == "song.wav", tl["audio"]
    assert tl["audio"].get("music") is None and tl["audio"]["bgm"] is None
    assert tl["cuts"][2]["clip_offset"] == 2.0 and tl["cuts"][1]["lyrics"][0]["text"] == "Carrot!", tl["cuts"][1:3]
    mp4 = root / "episodes/ep91/out/ep91_en.mp4"
    a = audio.decode(mp4, SR, 1)[:, 0]
    assert abs(len(a) / SR - 13.0) < 0.1 and np.sqrt((a ** 2).mean()) > 0.02

    r = subprocess.run([sys.executable, str(MOMO / "song_track.py"), "--root", str(root), "refs", "--ep", "ep91"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    ref = audio.decode(root / "episodes/ep91/audio/refs/c02_en.wav", SR, 1)[:, 0]
    assert abs(len(ref) / SR - 2.0) < 0.01  # exactly the cut window of the vocal stem
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
