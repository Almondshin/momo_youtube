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
from momolib.episode import NarItem, parse_narration, place_song_lines, plan_timeline  # noqa: E402

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
    t = tone(1.0, 220)
    assert np.array_equal(audio.declick(t, SR), t), "steady voice must be untouched"


def test_detect_beats(tmp: Path) -> None:
    f = audio.write_wav(tmp / "m.wav", music(40, 96), 22050)
    ana = audio.detect_beats(f, 100)
    assert abs(ana["bpm"] - 96) < 0.15, ana
    bar = 4 * 60 / 96
    off = ana["downbeat0"] % bar
    assert min(off, bar - off) < 0.12, ana  # beat 1 of the bar (beats are 0.625 s apart), onset lag ≤ ~0.1 s


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
