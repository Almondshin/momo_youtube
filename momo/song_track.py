#!/usr/bin/env python3
"""Finished-song episodes (manifest.song.track): bring a song made outside Higgsfield into the pipeline.

The song (vocals + music in one file — Suno Pro WAV + stems since ep03, or ACE-Step on the local Mac) is the
episode's timeline: cuts sit on
its bar grid, the karaoke captions come from its aligned lyrics, lip-sync clips are driven by slices of its
vocal stem. Local tool → 0 credits; the files are hosted as GitHub release assets so fetch_assets.py (and the
momo-publish runner) can restore them.

  import    copy the chosen take (+ vocal stem) into episodes/<ep>/audio/, record song.track / song.vocals
  analyze   tempo + bar grid (momolib.audio.detect_beats) → song.track.analysis, song.bpm
  lyrics    aligned words (tools/align_lyrics.py output) → song.lyrics
  sections  table of lyric lines by bar — use it to write the cuts' bars
  refs      vocal-stem slice per lip-sync cut → episodes/<ep>/audio/refs/<cut>_en.wav (audio_references)
  publish   upload song / vocals / refs to the release "media-<ep>" (gh) → song.track.url, song.vocals.url
  sync      preview a lip-sync clip with its vocal slice → out/sync/<cut>_sync.mp4
  status    approve / reject the song (song.track + song.vocals)

Examples
  python momo/song_track.py import --ep ep03 --mix ~/ml/momo_ep03/suno/v1/song.wav \\
      --vocals ~/ml/momo_ep03/suno/v1/Vocals.wav --inst ~/ml/momo_ep03/suno/v1/Instrumental.wav --note "Suno v1"
  python momo/song_track.py analyze --ep ep03
  python momo/song_track.py lyrics --ep ep03 --align ~/ml/momo_ep03/full1/align_a_s202.json
  python momo/song_track.py sections --ep ep03
  python momo/song_track.py refs --ep ep03 && python momo/song_track.py publish --ep ep03
  python momo/song_track.py status --ep ep03 --approve
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import (MomoError, add_root_arg, check_ep, get_paths, load_config, load_manifest,  # noqa: E402
                            main_wrapper, probe_duration, run, save_json, which)
from momolib.episode import song_grid, song_track, track_lines, track_spans  # noqa: E402
from momolib.genrec import now_iso  # noqa: E402

REF_SR = 44100
GATE_DB = -35.0      # vocal-stem slice: 20 ms frames this far below the stem's loudest frame are muted
GATE_HOLD = 0.08     # … unless voice is within this many seconds (keeps consonants and breaths)
RAMP = 0.01
REF_MIN = 3.0        # s — shorter slices are padded with silence (wan2_7 fails on ~2 s audio references)


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

def cmd_lyrics(paths, cfg, args) -> int:
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    need_track(m)
    data = json.loads(Path(args.align).expanduser().read_text())
    lines = []
    for ln in data.get("lines") or []:
        words = [[str(w[0]), round(float(w[1]), 3), round(float(w[2]), 3)] for w in ln.get("words") or []]
        if words:
            lines.append({"text": ln.get("text") or " ".join(w[0] for w in words),
                          **({"section": ln["section"]} if ln.get("section") else {}), "words": words})
    if not lines:
        raise MomoError("정렬 결과에 단어 시각이 있는 줄이 없음")
    m["song"]["lyrics"] = lines
    m["song"]["track"]["lyrics_sha1"] = m["song"]["track"]["sha1"]
    save_json(paths.manifest(ep), m)
    print(f"✔ 가사 {len(lines)}줄 (단어 {sum(len(l['words']) for l in lines)}개) → song.lyrics")
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
    print(f"{'마디':>6} {'박':>4} {'시각':>7}  가사")
    for ln in track_lines(song):
        b = bar_of(song, ln["t0"])
        print(f"{math.floor(b + 1e-6) + 1:>6} {((b % 1) * int(song.get('beats_per_bar') or 4)) + 1:>4.1f} "
              f"{ln['t0']:>7.2f}  {ln['text']}  ({ln['t1'] - ln['t0']:.1f}s)")
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


# ---------------------------------------------------------------- publish / status

def repo_slug() -> str:
    r = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    return r.stdout.decode().strip()


def cmd_publish(paths, cfg, args) -> int:
    """Upload the song, its vocal stem and the refs as release assets (tag media-<ep>) and record their URLs."""
    if not which("gh"):
        raise MomoError("gh CLI 가 필요함 (GitHub 로그인된 로컬 맥에서 실행)")
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    song, tr = m["song"], need_track(m)
    tag = args.tag or f"media-{ep}"
    slug = repo_slug()
    if subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode != 0:
        run(["gh", "release", "create", tag, "--prerelease", "--title", f"{ep} media (song, stems, lip-sync refs)",
             "--notes", "Locally made audio for the pipeline (fetch_assets.py). Not a code release."])
    d = audio_dir(paths, ep)
    files = {"song": d / "song.flac", "song_vocals": d / "song_vocals.flac"}
    files.update({f"ref_{p.stem}": p for p in sorted((d / "refs").glob("*.wav"))})
    with tempfile.TemporaryDirectory() as tmp:
        up = []
        for key, f in files.items():
            if not f.exists():
                raise MomoError(f"파일 없음: {f}")
            sha = sha1_file(f)[:8]
            name = f"{ep}_{key}_{sha}{f.suffix}"  # content-addressed: a new take never overwrites an old URL
            shutil.copy(f, Path(tmp) / name)
            up.append((key, name))
        run(["gh", "release", "upload", tag, "--clobber", *[str(Path(tmp) / n) for _, n in up]])
    base = f"https://github.com/{slug}/releases/download/{tag}"
    urls = {k: f"{base}/{n}" for k, n in up}
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
    p.add_argument("--align", required=True, help="tools/align_lyrics.py 결과 JSON")
    p = sub.add_parser("sections")
    p.add_argument("--ep", required=True)
    for name in ("refs", "sync"):
        p = sub.add_parser(name)
        p.add_argument("--ep", required=True)
        p.add_argument("--cuts", help="쉼표 구분 (기본: 립싱크 컷 전부)")
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
            "refs": cmd_refs, "sync": cmd_sync, "publish": cmd_publish, "status": cmd_status}[args.cmd](paths, cfg, args)


if __name__ == "__main__":
    main_wrapper(main)
