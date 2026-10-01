#!/usr/bin/env python3
"""Finished-song episodes (manifest.song.track): bring a song made outside Higgsfield into the pipeline.

The song (vocals + music in one file — Suno Pro WAV + stems since ep03, or ACE-Step on the local Mac) is the
episode's timeline: cuts sit on
its bar grid, the karaoke captions come from its aligned lyrics, lip-sync clips are driven by slices of its
vocal stem. Local tool → 0 credits; the files are hosted as GitHub release assets so fetch_assets.py (and the
momo-publish runner) can restore them.

  import    copy the chosen take (+ vocal stem) into episodes/<ep>/audio/, record song.track / song.vocals
  analyze   tempo + bar grid (momolib.audio.detect_beats) → song.track.analysis, song.bpm
  lyrics    aligned words (tools/align_lyrics.py output) → song.lyrics, word starts snapped to the vocal stem
            (momolib.lyrics_refine, default; --no-refine keeps whisper's times). Without --align: refine again
  sections  table of lyric lines by bar — use it to write the cuts' bars
  refs      vocal-stem slice per lip-sync cut → episodes/<ep>/audio/refs/<cut>_en.wav (audio_references)
  publish   upload song / vocals / refs to the release "media-<ep>" (gh) → song.track.url, song.vocals.url
  sync      preview a lip-sync clip with its vocal slice → out/sync/<cut>_sync.mp4
  lipsync   measure how late Momo's mouth is vs the voice in the built video, per singing shot (lip_shift hint)
  status    approve / reject the song (song.track + song.vocals)

Examples
  python momo/song_track.py import --ep ep03 --mix ~/ml/momo_ep03/suno/v1/song.wav \\
      --vocals ~/ml/momo_ep03/suno/v1/Vocals.wav --inst ~/ml/momo_ep03/suno/v1/Instrumental.wav --note "Suno v1"
  python momo/song_track.py analyze --ep ep03
  python momo/song_track.py lyrics --ep ep03 --align ~/ml/momo_ep03/full1/align_a_s202.json
  python momo/song_track.py lyrics --ep ep04                 # re-refine the current song.lyrics
  python momo/song_track.py sections --ep ep03
  python momo/song_track.py refs --ep ep03 && python momo/song_track.py publish --ep ep03
  python momo/song_track.py status --ep ep03 --approve
  python momo/song_track.py lipsync --ep ep04 [--cuts c03,c14]   # after build.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib import release  # noqa: E402
from momolib.common import (MomoError, add_root_arg, check_ep, check_lang, get_paths, load_config,  # noqa: E402
                            load_manifest, main_wrapper, probe_duration, run, save_json)
from momolib.episode import song_grid, song_track, track_lines, track_spans  # noqa: E402
from momolib.genrec import now_iso  # noqa: E402

REF_SR = 44100
GATE_DB = -35.0      # vocal-stem slice: 20 ms frames this far below the stem's loudest frame are muted
GATE_HOLD = 0.08     # … unless voice is within this many seconds (keeps consonants and breaths)
RAMP = 0.01
REF_MIN = 3.0        # s — shorter slices are padded with silence (wan2_7 fails on ~2 s audio references)
CUT_LEAD = 0.1       # s — a sung line's cut starts this long before its (refined) first word


def sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_flac(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ar", "48000", "-c:a", "flac", str(dst)])


def audio_dir(paths, ep: str) -> Path:
    return paths.ep(ep) / "audio"


def local_rec(sha1: str, extra: dict) -> dict:
    """GenRec for a locally made file: fetchable once it has a url (publish), 0 credits."""
    job = f"local:{sha1[:12]}"
    return {"status": "generated", "job_id": job, "url": None, "attempts": 1, "credits": 0, "reason": None,
            "sha1": sha1, **extra,
            "history": [{"job_id": job, "url": None, "status": "generated", "reason": None, "at": now_iso(),
                         "credits": 0}]}


def need_track(m: dict) -> dict:
    tr = song_track(m.get("song"))
    if tr is None:
        raise MomoError("manifest.song.track 없음 — 먼저 song_track.py import")
    return tr


# ---------------------------------------------------------------- import

def cmd_import(paths, cfg, args) -> int:
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    song = m.setdefault("song", {})
    old = song_track(song)
    if old and old.get("status") == "approved" and not args.force:
        raise MomoError("이미 승인된 노래가 있음 — 바꾸려면 --force (컷 bars·립싱크 레퍼런스를 다시 맞춰야 함)")
    mix, vocals = Path(args.mix).expanduser(), Path(args.vocals).expanduser()
    for f in (mix, vocals):
        if not f.exists():
            raise MomoError(f"파일 없음: {f}")
    d = audio_dir(paths, ep)
    if old:  # keep what the previous song was, then drop everything that was timed to it
        song.setdefault("history", []).append({k: song.get(k) for k in ("track", "vocals", "refs_urls")
                                                if song.get(k) is not None} | {"replaced_at": now_iso()})
        for k in ("lyrics", "refs_urls"):
            song.pop(k, None)
        for c in m.get("cuts") or []:
            if isinstance(c.get("nar_ref"), dict) and any("window" in r for r in c["nar_ref"].values()
                                                          if isinstance(r, dict)):
                c.pop("nar_ref")
        for f in (d / "refs").glob("*.wav") if (d / "refs").exists() else []:
            f.unlink()
    to_flac(mix, d / "song.flac")
    to_flac(vocals, d / "song_vocals.flac")
    if args.inst:
        to_flac(Path(args.inst).expanduser(), d / "song_inst.flac")  # local only: the beat grid is cleaner on it
    meta: dict = {"tool": args.tool, "source_file": mix.name}
    if args.note:
        meta["note"] = args.note
    if args.meta:
        tk = json.loads(Path(args.meta).expanduser().read_text())
        take = next((t for t in tk.get("takes") or [] if t.get("file") == mix.name), None)
        meta.update({k: tk.get(k) for k in ("dit", "lm", "bpm", "key") if tk.get(k) is not None})
        if take:
            meta.update({"seed": take.get("seed"), "caption": (tk.get("caps") or {}).get(take.get("cap"))})
    dur = probe_duration(d / "song.flac")
    track = local_rec(sha1_file(d / "song.flac"), {**meta, "duration": round(dur, 3), "start": 0.0})
    if old and old.get("analysis") and old.get("sha1") == track["sha1"]:
        track["analysis"] = old["analysis"]
    song["track"] = track
    song["vocals"] = local_rec(sha1_file(d / "song_vocals.flac"), {"of": track["sha1"]})
    song.setdefault("beats_per_bar", 4)
    if meta.get("bpm") and not song.get("bpm"):
        song["bpm"] = meta["bpm"]
    save_json(paths.manifest(ep), m)
    print(f"✔ {ep} 노래 가져옴: song.flac {dur:.2f}s (sha1 {track['sha1'][:12]}), song_vocals.flac")
    print("  다음: song_track.py analyze → lyrics → sections")
    return 0


# ---------------------------------------------------------------- analyze

def cmd_analyze(paths, cfg, args) -> int:
    from momolib import audio
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    song, tr = m["song"], need_track(m)
    inst = audio_dir(paths, ep) / "song_inst.flac"
    src = Path(args.inst).expanduser() if args.inst else (inst if inst.exists() else audio_dir(paths, ep) / "song.flac")
    hint = float(args.bpm or song.get("bpm") or tr.get("bpm") or 110)
    ana = audio.detect_beats(src, hint)
    bpb = int(song.get("beats_per_bar") or 4)
    bar = 60.0 / ana["bpm"] * bpb
    n = int((float(tr.get("duration") or probe_duration(src)) - ana["downbeat0"]) // bar) + 1
    rep = audio.drift_report(src, ana, n, bpb)
    if args.follow_tempo:
        ana["downbeats"], grid = audio.refine_downbeats(src, ana, n, bpb)
    else:
        ana["downbeats"] = [round(ana["downbeat0"] + k * bar, 4) for k in range(n)]
        grid = {"refined": False}
    ana["grid"] = {**grid, **rep}
    ana["source"] = "mix" if src.name == "song.flac" else "instrumental stem"
    tr["analysis"] = ana
    song["bpm"] = ana["bpm"]
    save_json(paths.manifest(ep), m)
    print(f"✔ 템포 {ana['bpm']:.3f} BPM, 첫 강박 {ana['downbeat0']:.3f}s, 마디 {bar:.3f}s × {n}, "
          f"신뢰도 {ana['confidence']} ({ana['source']})")
    secs = " ".join(f"{v:+.0f}" for v in rep["section_offsets_ms"])
    if grid.get("refined"):
        print(f"  △ --follow-tempo: 마디선을 실제 박에 맞춤 (최대 {grid['max_drift_ms']} ms)")
    elif rep["trend_ms"] is not None and abs(rep["trend_ms"]) > 50:
        print(f"  △ 박이 곡 끝으로 갈수록 {rep['trend_ms']:+.0f} ms 밀림 (구간별 {secs}) — --follow-tempo 로 다시 분석")
    else:
        print(f"  ✔ 곧은 격자 — 구간별 박 어긋남(ms) {secs}")
    if abs(ana["bpm"] - hint) > 2:
        print(f"  △ 요청 템포 {hint} 와 {ana['bpm'] - hint:+.2f} BPM 차이 — 실제 값으로 격자를 만든다")
    return 0


# ---------------------------------------------------------------- lyrics / sections

def read_align(path: Path) -> list[dict]:
    """tools/align_lyrics.py output → song.lyrics lines with whisper word times [word, t0, t1]."""
    data = json.loads(path.expanduser().read_text())
    lines = []
    for ln in data.get("lines") or []:
        words = [[str(w[0]), round(float(w[1]), 3), round(float(w[2]), 3)] for w in ln.get("words") or []]
        if words:
            lines.append({"text": ln.get("text") or " ".join(w[0] for w in words),
                          **({"section": ln["section"]} if ln.get("section") else {}), "words": words})
    if not lines:
        raise MomoError("정렬 결과에 단어 시각이 있는 줄이 없음")
    return lines


def print_refine(rep: dict) -> None:
    """Counts + the guards of a lyrics_refine report (Korean)."""
    sh = rep["shift_ms"]
    print(f"  보정 (보컬 스템 기준): 0.1초 넘게 옮긴 단어 {rep['moved']}개, 쉼표·긴 음 안에 찍혀 있던 단어 "
          f"{rep['loose']}개, 실제 발성에 붙은 단어 {rep['matched']}/{rep['words']}개 · 이동 중앙값 {sh['median']:+d} ms, "
          f"|이동| p90 {sh['p90_abs']} ms")
    if rep["early"]:
        print(f"  · 정렬보다 0.1초 넘게 앞당긴 단어 {len(rep['early'])}개: "
              + ", ".join("{} {:.2f}→{:.2f}".format(i["word"].strip(",.!?;:"), i["stamp"], i["t0"])
                          for i in rep["early"][:12]) + (" …" if len(rep["early"]) > 12 else ""))
    lag = [f for f in rep["flags"] if f["kind"] == "lag"]
    late = [f for f in rep["flags"] if f["kind"] == "phase" and f["beats"] > 0]
    early = [f for f in rep["flags"] if f["kind"] == "phase" and f["beats"] <= 0]
    if lag:
        print(f"  △ 자막이 목소리보다 늦을 수 있는 곳 {len(lag)}개 (쉼 뒤 발성이 다음 단어보다 0.1초 넘게 먼저) "
              f"— 보컬 스템 스펙트로그램으로 확인:")
        for f in lag:
            print(f"      {f['t']:7.2f}s 발성 → '{f['word']}' {f['t0']:.2f}s (+{f['ms']} ms)  "
                  f"[{f['line'] + 1}줄] {f['text']}")
    if late:
        print(f"  △ 같은 섹션의 다른 줄보다 늦게 시작하는 줄 {len(late)}개 (마디 위상이 0.5박 넘게 다름) — 확인:")
        for f in late:
            print(f"      {f['t']:7.2f}s 박 {f['beat'] + 1:.2f} (섹션 {f['section']} 중앙 {f['median'] + 1:.2f}, "
                  f"{f['beats']:+.2f}박)  [{f['line'] + 1}줄] {f['text']}")
    if early:
        print(f"  · 같은 섹션의 다른 줄보다 일찍 시작하는 줄 {len(early)}개 (다르게 부른 프레이즈면 무해): "
              + ", ".join(f"{f['line'] + 1}줄 {f['beats']:+.2f}박" for f in early))
    if not lag and not late:
        print("  ✔ 늦는 자막 경고 없음")


def cmd_lyrics(paths, cfg, args) -> int:
    from momolib import audio, lyrics_refine
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    song, tr = m["song"], need_track(m)
    if args.align:
        lines = read_align(Path(args.align))
    elif not args.refine:
        raise MomoError("--no-refine 은 --align 과 함께 (정렬 결과를 보정 없이 넣을 때)")
    else:
        lines = list(song.get("lyrics") or [])   # lines without word times are kept as they are
        if not any(ln.get("words") for ln in lines):
            raise MomoError("song.lyrics 에 단어 시각이 없음 — --align <tools/align_lyrics.py 결과> 로 넣을 것")
    if args.refine:
        stem = audio.vocals_file(paths, ep)
        if stem is None:
            raise MomoError("song_vocals 파일 없음 — import 또는 fetch_assets (보정 없이 넣으려면 --no-refine)")
        lines, rep = lyrics_refine.refine_file(lines, stem, song)
        tr["lyrics_refine"] = {"v": rep["v"], "vocals_sha1": sha1_file(stem), "moved": rep["moved"],
                               "loose": rep["loose"], "flags": rep["flags"]}
    else:
        rep = None
        tr.pop("lyrics_refine", None)
    song["lyrics"] = lines
    tr["lyrics_sha1"] = tr["sha1"]
    save_json(paths.manifest(ep), m)
    src = "정렬 결과에서" if args.align else "지금 song.lyrics 를 정렬 시각부터 다시 보정"
    print(f"✔ 가사 {len(lines)}줄, 단어 {sum(len(l.get('words') or []) for l in lines)}개 ({src}) → song.lyrics")
    if rep:
        print_refine(rep)
    else:
        print("  △ --no-refine: whisper 시각 그대로 — 줄 첫 단어가 최대 0.7초 일찍 켜질 수 있음")
    return 0


def bar_of(song: dict, t: float) -> float:
    """Song time → bar position (0 = first downbeat), fractional."""
    ana = song["track"]["analysis"]
    _, bar = song_grid(song)
    return (t - float(ana["downbeat0"])) / bar


def cmd_sections(paths, cfg, args) -> int:
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    song, tr = m["song"], need_track(m)
    if not tr.get("analysis"):
        raise MomoError("analyze 먼저")
    _, bar = song_grid(song)
    print(f"{ep}: {song['bpm']:.2f} BPM · 마디 {bar:.3f}s · 첫 강박 {tr['analysis']['downbeat0']:.3f}s · "
          f"노래 {tr.get('duration')}s (마디 {bar_of(song, float(tr.get('duration') or 0)):.1f}개)")
    if song.get("lyrics") and not tr.get("lyrics_refine"):
        print("△ 가사 시각이 보정되지 않음 (whisper 그대로) — song_track.py lyrics 로 보정한 뒤 cut_at 을 정할 것")
    print(f"{'마디':>6} {'박':>4} {'시각':>7} {'cut_at':>7}  가사   (cut_at = 첫 단어 − {CUT_LEAD} s)")
    for ln in track_lines(song):
        b = bar_of(song, ln["t0"])
        print(f"{math.floor(b + 1e-6) + 1:>6} {((b % 1) * int(song.get('beats_per_bar') or 4)) + 1:>4.1f} "
              f"{ln['t0']:>7.2f} {ln['t0'] - CUT_LEAD:>7.2f}  {ln['text']}  ({ln['t1'] - ln['t0']:.1f}s)")
    cuts = m.get("cuts") or []
    if cuts and all(isinstance(c.get("bars"), int) for c in cuts):
        spans = track_spans(song, cuts)
        print(f"\n컷 {len(cuts)}개 → 영상 {spans[-1][1]:.2f}s (평균 {spans[-1][1] / len(cuts):.2f}s)")
    return 0


# ---------------------------------------------------------------- refs / sync

def gate(x, sr: int):
    """Mute stem bleed between sung words: 20 ms frames far below the loudest frame, with short ramps."""
    import numpy as np
    hop = int(0.02 * sr)
    n = max(1, len(x) // hop)
    rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    on = db > db.max() + GATE_DB
    k = int(round(GATE_HOLD / 0.02))
    held = np.convolve(on.astype(float), np.ones(2 * k + 1), "same") > 0
    env = np.repeat(held.astype(np.float32), hop)
    env = np.concatenate([env, np.full(len(x) - len(env), env[-1] if len(env) else 1.0, np.float32)])
    r = max(1, int(RAMP * sr))
    env = np.convolve(env, np.ones(r) / r, "same").astype(np.float32)
    return x * env


def lipsync_cuts(m: dict, only: str | None) -> list[dict]:
    want = {c.strip() for c in (only or "").split(",") if c.strip()}
    return [c for c in m.get("cuts") or [] if c.get("type") == "V" and c.get("lipsync")
            and not c.get("clip_from") and (not want or c["id"] in want)]


def cmd_refs(paths, cfg, args) -> int:
    from momolib import audio
    from hf_jobs import track_window
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    need_track(m)
    stem = audio.vocals_file(paths, ep)
    if stem is None:
        raise MomoError("song_vocals 파일 없음 — import 또는 fetch_assets")
    x = audio.decode(stem, REF_SR, 1)[:, 0]
    out = audio_dir(paths, ep) / "refs"
    out.mkdir(parents=True, exist_ok=True)
    for c in lipsync_cuts(m, args.cuts):
        s, e = track_window(m, c["id"])
        seg = x[int(round(s * REF_SR)):int(round(e * REF_SR))]
        seg = gate(seg, REF_SR)
        if len(seg) < REF_MIN * REF_SR:  # the lip-sync model rejects audio under ~2 s: pad silence at the end
            import numpy as np
            seg = np.concatenate([seg, np.zeros(int(REF_MIN * REF_SR) - len(seg), seg.dtype)])
        dst = out / f"{c['id']}_en.wav"
        audio.write_wav(dst, seg, REF_SR, codec="pcm_s16le")
        print(f"✔ {dst.name}: 노래 {s:.3f}~{e:.3f}s ({e - s:.2f}s)")
    return 0


def cmd_sync(paths, cfg, args) -> int:
    """Lip-sync check: the clip with exactly the vocal slice it was driven by."""
    from momolib.common import VIDEO_EXTS, find_media
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    need_track(m)
    out = paths.out(ep) / "sync"
    out.mkdir(parents=True, exist_ok=True)
    for c in lipsync_cuts(m, args.cuts):
        clip = find_media(paths.clips(ep), f"{c['id']}_en", VIDEO_EXTS) or find_media(paths.clips(ep), c["id"],
                                                                                     VIDEO_EXTS)
        ref = audio_dir(paths, ep) / "refs" / f"{c['id']}_en.wav"
        if clip is None or not ref.exists():
            print(f"  · {c['id']}: 클립 또는 refs 없음 — 건너뜀")
            continue
        dst = out / f"{c['id']}_sync.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-i", str(ref), "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-shortest", str(dst)])
        print(f"✔ {dst}")
    return 0


def cmd_lipsync(paths, cfg, args) -> int:
    """How late Momo's mouth is vs the voice in the built video, per singing shot (momolib.lipsync)."""
    import numpy as np
    from momolib import audio, lipsync
    from momolib.episode import lip_shift_of
    ep, lang = check_ep(args.ep), check_lang(args.lang)
    m = load_manifest(paths, ep)
    need_track(m)
    tl_path = paths.out(ep) / f"{ep}_{lang}_timeline.json"
    if not tl_path.exists():
        raise MomoError(f"타임라인 없음: {tl_path} — build.py --ep {ep} --lang {lang} 먼저")
    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    stem = audio.vocals_file(paths, ep)
    if stem is None:
        raise MomoError("song_vocals 파일 없음 — import 또는 fetch_assets")
    want = {c.strip() for c in (args.cuts or "").split(",") if c.strip()}
    shots = [s for s in lipsync.shots(tl, m, paths.root) if not want or s["id"] in want]
    if not shots:
        raise MomoError("잴 샷이 없음 (립싱크 컷과 그 clip_from 재사용 컷만 잰다)")
    by_id = {c["id"]: c for c in m.get("cuts") or []}
    stale = [s["id"] for s in shots if abs(lip_shift_of(by_id.get(s["id"]) or {}, by_id) - s["lip_shift"]) > 1e-6]
    if stale:
        print(f"△ manifest 의 lip_shift 가 타임라인과 다름 ({', '.join(stale)}) — build 를 다시 돌린 뒤 잴 것")
    fps = int(tl.get("fps") or cfg["render"]["fps"])
    env = lipsync.audio_env(stem)
    cache = paths.out(ep) / "lipsync_cache"
    print(f"{ep} 립싱크 지연 (+ = 입이 늦음, 허용 {lipsync.OK_MS[0]}~{lipsync.OK_MS[1]} ms, "
          f"제안 목표 {lipsync.TARGET_MS} ms, 클립 {len(shots)}샷)")
    print(f"{'컷':4} {'재사용':5} {'시작':>7} {'길이':>5} | {'지연':>5} {'r':>5} {'margin':>6} {'신뢰':6} | "
          f"{'앞/뒤':>10} | {'self':>5} {'audio':>5} | {'눈':>4} | 판정")
    g = lambda d, k: "-" if not d or d.get(k) is None else d[k]  # noqa: E731
    rows = []
    for s in shots:
        if not s["clip"].exists():
            print(f"{s['id']:4} — 클립 없음 ({s['clip'].name}), 건너뜀 (fetch_assets)")
            continue
        r = lipsync.measure(s, env, cache)
        sh, lag = r["shown"], r["shown"].get("lag_ms")
        note = r["verdict"]
        if r["verdict"] == "fix" and sh["conf"] == "high":
            r["suggest"] = lipsync.suggest(lag, s["lip_shift"], fps)
            note += f" → lip_shift {r['suggest']:+.3f}" + (f" ({s['owner']})" if s["owner"] != s["id"] else "")
        elif r["verdict"] == "fix":
            note += " (신뢰도 보통 — 눈으로 확인)"
        h = "/".join(str(g(x, "lag_ms")) for x in r["halves"])
        print(f"{s['id']:4} {(s['reuse_of'] or ''):5} {s['start']:7.2f} {s['dur']:5.2f} | {g(sh, 'lag_ms'):>5} "
              f"{g(sh, 'r'):>5} {g(sh, 'margin'):>6} {g(sh, 'conf'):6} | {h:>10} | {g(r['self'], 'lag_ms'):>5} "
              f"{g(r['audio'], 'lag_ms'):>5} | {r['found']:4.2f} | {note}"
              + (f"  [지금 lip_shift {s['lip_shift']:+.3f}]" if s["lip_shift"] else ""))
        rows.append(r)
    # one lip_shift per clip: the cut that owns it (the source of reused takes, unless a reuse sets its own)
    owners: dict[str, list] = {}
    for r in rows:
        if r["verdict"] in ("ok", "fix") and r["shown"]["conf"] == "high":
            owners.setdefault(r["owner"], []).append(r)
    tips = []
    for owner, rs in owners.items():
        if any(r["verdict"] == "fix" for r in rs):
            med = float(np.median([r["shown"]["lag_ms"] for r in rs]))
            each = ", ".join("{} {:+d}".format(r["id"], r["shown"]["lag_ms"]) for r in rs)
            tips.append(f"{owner} lip_shift {lipsync.suggest(med, rs[0]['lip_shift'], fps):+.3f} "
                        f"({each} ms → 중앙 {med:+.0f})")
    n = {v: sum(r["verdict"] == v for r in rows) for v in ("ok", "fix", "unreliable")}
    print(f"\nok {n['ok']} · fix {n['fix']} · unreliable {n['unreliable']} (unreliable = 상관이 약하거나 앞/뒤가 "
          f"{lipsync.HALVES_MS} ms 넘게 다름 — 프레임을 눈으로 볼 것)")
    if tips:
        print("제안 (신뢰도 높은 샷만, manifest 에 넣고 build 후 다시 잴 것):")
        for t in tips:
            print(f"  {t}")
    if args.json:
        save_json(Path(args.json), rows)
        print(f"  → {args.json}")
    return 0


# ---------------------------------------------------------------- publish / status

def cmd_publish(paths, cfg, args) -> int:
    """Upload the song, its vocal stem and the refs as release assets (tag media-<ep>) and record their URLs."""
    release.need_gh()
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    song, tr = m["song"], need_track(m)
    tag = args.tag or f"media-{ep}"
    release.ensure_release(tag, f"{ep} media (song, stems, lip-sync refs)",
                           "Locally made audio for the pipeline (fetch_assets.py). Not a code release.")
    d = audio_dir(paths, ep)
    files = {"song": d / "song.flac", "song_vocals": d / "song_vocals.flac"}
    files.update({f"ref_{p.stem}": p for p in sorted((d / "refs").glob("*.wav"))})
    names = {}
    for key, f in files.items():
        if not f.exists():
            raise MomoError(f"파일 없음: {f}")
        names[key] = f"{ep}_{key}_{sha1_file(f)[:8]}{f.suffix}"  # content-addressed: a new take never overwrites
    by_name = release.upload_assets(tag, {names[k]: f for k, f in files.items()})
    up = list(names.items())
    urls = {k: by_name[n] for k, n in up}
    for rec, key in ((tr, "song"), (song["vocals"], "song_vocals")):
        rec["url"] = urls[key]
        for h in rec.get("history") or []:
            if h.get("job_id") == rec.get("job_id"):
                h["url"] = urls[key]
    refs = {k[4:]: u for k, u in urls.items() if k.startswith("ref_")}
    song["refs_urls"] = refs
    save_json(paths.manifest(ep), m)
    print(f"✔ release {tag}: {len(up)}개 업로드")
    for k, u in refs.items():
        print(f"  {k}: {u}")
    print("  다음: 각 ref URL → media_import_url → hf_jobs.py narref --ep … --cut … --lang en --media-id …")
    return 0


def cmd_status(paths, cfg, args) -> int:
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    song, tr = m["song"], need_track(m)
    if args.approve == args.reject:
        raise MomoError("--approve 또는 --reject 중 하나")
    st = "approved" if args.approve else "rejected"
    for rec in (tr, song.get("vocals") or {}):
        rec["status"] = st
        rec["reason"] = args.reason
        for h in rec.get("history") or []:
            if h.get("job_id") == rec.get("job_id"):
                h["status"], h["reason"] = st, args.reason
    save_json(paths.manifest(ep), m)
    print(f"✔ {ep} 노래 {st}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="노래 파일(song.track) 에피소드 도구",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("import")
    p.add_argument("--ep", required=True)
    p.add_argument("--mix", required=True)
    p.add_argument("--vocals", required=True, help="보컬 스템 (demucs vocals.wav)")
    p.add_argument("--inst", help="반주 스템 (있으면 박자 분석에 씀, 로컬에만 둠)")
    p.add_argument("--meta", help="생성 기록 JSON (ACE-Step takes.json)")
    p.add_argument("--tool", default="suno", help="만든 도구 (suno | ace-step-1.5 …)")
    p.add_argument("--note", help="곡 메모 (Suno 곡 제목·버전 등)")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("analyze")
    p.add_argument("--ep", required=True)
    p.add_argument("--inst", help="반주 스템 (박자 검출이 더 정확)")
    p.add_argument("--bpm", type=float, help="템포 힌트")
    p.add_argument("--follow-tempo", action="store_true", help="템포가 흔들리는 곡: 박 추적으로 마디선을 맞춤")
    p = sub.add_parser("lyrics")
    p.add_argument("--ep", required=True)
    p.add_argument("--align", help="tools/align_lyrics.py 결과 JSON (없으면 지금 song.lyrics 를 다시 보정)")
    p.add_argument("--refine", action=argparse.BooleanOptionalAction, default=True,
                   help="단어 시작을 보컬 스템의 실제 발성에 맞춤 (기본 켬)")
    p = sub.add_parser("sections")
    p.add_argument("--ep", required=True)
    for name in ("refs", "sync"):
        p = sub.add_parser(name)
        p.add_argument("--ep", required=True)
        p.add_argument("--cuts", help="쉼표 구분 (기본: 립싱크 컷 전부)")
    p = sub.add_parser("lipsync")
    p.add_argument("--ep", required=True)
    p.add_argument("--lang", default="en")
    p.add_argument("--cuts", help="쉼표 구분 (기본: 립싱크 컷과 그 재사용 컷 전부)")
    p.add_argument("--json", help="샷별 결과를 이 JSON 파일로")
    p = sub.add_parser("publish")
    p.add_argument("--ep", required=True)
    p.add_argument("--tag")
    p = sub.add_parser("status")
    p.add_argument("--ep", required=True)
    p.add_argument("--approve", action="store_true")
    p.add_argument("--reject", action="store_true")
    p.add_argument("--reason")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    cfg = load_config(paths)
    return {"import": cmd_import, "analyze": cmd_analyze, "lyrics": cmd_lyrics, "sections": cmd_sections,
            "refs": cmd_refs, "sync": cmd_sync, "lipsync": cmd_lipsync, "publish": cmd_publish,
            "status": cmd_status}[args.cmd](paths, cfg, args)


if __name__ == "__main__":
    main_wrapper(main)
