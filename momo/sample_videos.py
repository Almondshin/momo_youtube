#!/usr/bin/env python3
"""2단계 · 벤치마크 영상 샘플: 자막(json3 → 타임코드 텍스트), 균등 프레임 + contact sheet, 샷 전환 통계, 썸네일.

사용 예
  python sample_videos.py --dir research/<slug>                 # 대상: data.json 의 역대 1위 + 최근 1위
  python sample_videos.py --dir research/<slug> --ids VIDEOID1 VIDEOID2 --frames 36
  python sample_videos.py --dir research/<slug> --cleanup       # 분석 끝나면 반드시: videos/ frames/ raw/ 삭제

오프라인·테스트 훅
  --local-video FILE   다운로드 대신 FILE 을 모든 대상의 영상으로 사용
  --local-subs DIR     자막 다운로드 대신 DIR/<id>.<lang>.json3 사용
  --no-thumbs          썸네일 받지 않음

출력: subs/<id>.<lang>.txt, frames/<id>/f_###.jpg, frames/<id>_sheet.jpg, raw/thumbs/<id>.jpg,
samples.json (+ data.json 의 samples, report.md 에 샘플 표). 받은 영상·프레임은 분석용으로만 쓰고 재사용 금지.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from momolib.common import MomoError, add_root_arg, get_paths, load_json, main_wrapper, probe, run, save_json  # noqa: E402
from momolib.research import (YT_ID_RE, YtDlp, YtDlpError, fmt_dur, fmt_mmss, iso, json3_to_text,  # noqa: E402
                              parse_showinfo, render_report, resolve_dir, shot_stats, video_url)

VIDEO_FORMAT = "bv*[height<=480]/b[height<=480]/w"
SCENE_THRESHOLD = 0.3
FRAMES_RANGE = (30, 40)
THUMB_NAMES = ("maxresdefault.jpg", "hqdefault.jpg")


def log(msg: str) -> None:
    print(msg, flush=True)


def tmpl(folder: Path, pattern: str) -> str:
    """yt-dlp -o 템플릿: 폴더 경로의 % 는 이스케이프."""
    return str(folder).replace("%", "%%") + os.sep + pattern


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


# ---------------------------------------------------------------- 자막

def get_subs(d: Path, vid: str, yt: YtDlp | None, local_subs: Path | None) -> dict:
    raw = d / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    if local_subs:
        for f in local_subs.glob(f"{vid}.*.json3"):
            shutil.copy(f, raw / f.name)
    else:
        yt.run(["--skip-download", "--write-auto-subs", "--write-subs", "--sub-lang", "en,ko",
                "--sub-format", "json3", "--no-playlist", "-o", tmpl(raw, "%(id)s"), video_url(vid)], f"자막 {vid}")
    res: dict[str, dict] = {}
    for f in sorted(raw.glob(f"{vid}.*.json3")):
        lang = f.name[len(vid) + 1:-len(".json3")]
        try:
            text, n = json3_to_text(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            res[lang] = {"skipped": f"json3 파싱 실패: {e}"}
            continue
        out = d / "subs" / f"{vid}.{lang}.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        res[lang] = {"file": str(out.relative_to(d)), "lines": n}
    for lang in ("en", "ko"):
        res.setdefault(lang, {"skipped": "자막 없음 → 건너뜀"})
    return res


# ---------------------------------------------------------------- 영상·프레임·샷

def get_video(d: Path, vid: str, yt: YtDlp | None, local_video: Path | None) -> Path:
    folder = d / "videos"
    folder.mkdir(parents=True, exist_ok=True)

    def found() -> Path | None:
        return next((p for p in sorted(folder.glob(f"{vid}.*")) if p.suffix not in (".part", ".ytdl")
                     and p.stat().st_size > 0), None)

    if not found():
        if local_video:
            shutil.copy(local_video, folder / f"{vid}{local_video.suffix}")
        else:
            yt.run(["-f", VIDEO_FORMAT, "--no-playlist", "-o", tmpl(folder, "%(id)s.%(ext)s"), video_url(vid)],
                   f"영상 {vid}")
    path = found()
    if not path:
        raise MomoError(f"영상 파일을 찾지 못함: {folder}/{vid}.*")
    return path


def extract_frames(video: Path, duration: float, n: int, out_dir: Path) -> list[tuple[Path, float]]:
    """균등 간격 n 장 (구간 가운데 시점). 끝 부근에서 실패하면 1초 앞에서 다시."""
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True)
    frames = []
    for i in range(n):
        t = (i + 0.5) * duration / n
        out = out_dir / f"f_{i + 1:03d}.jpg"
        for tt in (t, max(0.0, t - 1.0)):
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{tt:.3f}", "-i", video, "-map", "0:v:0",
                 "-frames:v", "1", "-q:v", "3", out])
            if out.exists() and out.stat().st_size > 0:
                frames.append((out, tt))
                break
    return frames


def contact_sheet(frames: list[tuple[Path, float]], out: Path, cols: int = 6, cell_w: int = 320) -> Path:
    if not frames:
        raise MomoError("contact sheet 를 만들 프레임이 없음")
    with Image.open(frames[0][0]) as im:
        cell_h = max(1, round(cell_w * im.height / im.width))
    rows, pad = math.ceil(len(frames) / cols), 6
    sheet = Image.new("RGB", (cols * cell_w + (cols + 1) * pad, rows * cell_h + (rows + 1) * pad), (24, 24, 24))
    draw, font = ImageDraw.Draw(sheet), _font(18)
    for i, (p, t) in enumerate(frames):
        x, y = pad + (i % cols) * (cell_w + pad), pad + (i // cols) * (cell_h + pad)
        with Image.open(p) as im:
            sheet.paste(im.convert("RGB").resize((cell_w, cell_h), Image.LANCZOS), (x, y))
        label = f"{i + 1:02d}  {fmt_mmss(t)}"
        box = draw.textbbox((x + 6, y + 4), label, font=font)
        draw.rectangle((box[0] - 4, box[1] - 2, box[2] + 4, box[3] + 2), fill=(0, 0, 0))
        draw.text((x + 6, y + 4), label, fill=(255, 255, 255), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, "JPEG", quality=85)
    return out


def detect_shots(video: Path, duration: float, threshold: float = SCENE_THRESHOLD) -> dict:
    proc = run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-map", "0:v:0",
                "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"])
    cuts = parse_showinfo(proc.stderr.decode("utf-8", "replace"))
    return {"threshold": threshold, **shot_stats(cuts, duration)}


# ---------------------------------------------------------------- 썸네일

def fetch_thumbnail(vid: str, dest: Path, base: str | None = None) -> dict:
    """maxresdefault → hqdefault. 120px 이하 자리표시 이미지는 없는 것으로 본다."""
    base = (base or os.environ.get("MOMO_YT_THUMB_BASE") or "https://i.ytimg.com/vi").rstrip("/")
    errors = []
    for name in THUMB_NAMES:
        try:
            with urllib.request.urlopen(f"{base}/{vid}/{name}", timeout=20) as r:
                blob = r.read()
        except urllib.error.HTTPError as e:
            errors.append(f"{name}: HTTP {e.code}")
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            errors.append(f"{name}: {getattr(e, 'reason', e)}")
            continue
        try:
            with Image.open(io.BytesIO(blob)) as im:
                im.load()
                if im.width <= 120:
                    errors.append(f"{name}: 자리표시 이미지({im.width}x{im.height})")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                im.convert("RGB").save(dest, "JPEG", quality=92)
                return {"source": name.split(".")[0], "width": im.width, "height": im.height}
        except OSError as e:
            errors.append(f"{name}: 이미지 아님 ({e})")
    return {"error": "; ".join(errors)}


def ascii_role(role: str) -> str:
    """시트 라벨용 (기본 폰트에 한글이 없음)."""
    m = re.match(r"(역대|최근) (\d+)위", role)
    if m:
        return ("ALL-TIME" if m.group(1) == "역대" else "RECENT") + f" #{m.group(2)}"
    return {"최근 최하위": "RECENT LOWEST"}.get(role, "")


def thumbs_sheet(items: list[dict], d: Path, out: Path) -> Path | None:
    ok = [t for t in items if t.get("file")]
    if not ok:
        return None
    cw, ch, pad = 640, 360, 8
    cols = 2
    rows = math.ceil(len(ok) / cols)
    sheet = Image.new("RGB", (cols * cw + (cols + 1) * pad, rows * (ch + 30) + (rows + 1) * pad), (24, 24, 24))
    draw, font = ImageDraw.Draw(sheet), _font(20)
    for i, t in enumerate(ok):
        x, y = pad + (i % cols) * (cw + pad), pad + (i // cols) * (ch + 30 + pad)
        with Image.open(d / t["file"]) as im:
            sheet.paste(im.convert("RGB").resize((cw, ch), Image.LANCZOS), (x, y + 30))
        draw.text((x, y + 4), f"{i + 1}. {ascii_role(t['role'])}  {t['id']}", fill=(255, 255, 255), font=font)
    sheet.save(out, "JPEG", quality=85)
    return out


# ---------------------------------------------------------------- 정리

def cleanup(d: Path) -> int:
    removed = []
    for name in ("videos", "frames", "raw"):
        p = d / name
        if p.exists():
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            shutil.rmtree(p)
            removed.append(f"{name}/ ({size / 1e6:.1f}MB)")
    stamp = iso(time.time())
    for f in (d / "samples.json", d / "data.json"):
        if f.exists():
            data = load_json(f)
            target = data if f.name == "samples.json" else data.get("samples")
            if isinstance(target, dict):
                target["cleaned_up_at"] = stamp
                save_json(f, data)
    log("삭제: " + (", ".join(removed) if removed else "지울 것 없음") + " — 받은 영상·프레임은 재사용 금지")
    return 0


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_root_arg(ap)
    ap.add_argument("--dir", required=True, help="research/<slug> 폴더 (analyze_channel.py 결과)")
    ap.add_argument("--ids", nargs="+", help="대상 영상 ID (기본: data.json 의 역대 1위 + 최근 1위)")
    ap.add_argument("--frames", type=int, default=36, help="균등 프레임 수 (30~40, 기본 36)")
    ap.add_argument("--cleanup", action="store_true", help="videos/ frames/ raw/ 삭제만 하고 끝")
    ap.add_argument("--sleep-requests", action="store_true")
    ap.add_argument("--cookies")
    ap.add_argument("--cookies-from-browser")
    ap.add_argument("--local-video", help="(테스트/오프라인) 다운로드 대신 이 영상 파일")
    ap.add_argument("--local-subs", help="(테스트/오프라인) <id>.<lang>.json3 가 있는 폴더")
    ap.add_argument("--no-thumbs", action="store_true", help="썸네일 받지 않음")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    d = resolve_dir(paths, args.dir)
    if not d.is_dir():
        raise MomoError(f"폴더 없음: {d}")
    if args.cleanup:
        return cleanup(d)
    data_path = d / "data.json"
    if not data_path.exists():
        raise MomoError(f"{data_path} 없음 — 먼저 analyze_channel.py 로 1단계를 실행")
    data = load_json(data_path)
    videos = data.get("videos") or {}

    if args.ids:
        bad = [i for i in args.ids if not YT_ID_RE.match(i)]
        if bad:
            raise MomoError(f"영상 ID 형식이 아님: {bad}")
        targets = [{"id": i, "role": "지정", "reason": None} for i in dict.fromkeys(args.ids)]
    else:
        targets = (data.get("targets") or {}).get("sample") or []
        if not targets:
            raise MomoError("data.json 에 샘플 대상이 없음 — --ids 로 지정")
    n_frames = min(max(args.frames, FRAMES_RANGE[0]), FRAMES_RANGE[1])
    if n_frames != args.frames:
        log(f"프레임 수는 {FRAMES_RANGE[0]}~{FRAMES_RANGE[1]}장 → {n_frames}장으로 조정")
    local_video = Path(args.local_video).resolve() if args.local_video else None
    local_subs = Path(args.local_subs).resolve() if args.local_subs else None
    for p in (local_video, local_subs):
        if p and not p.exists():
            raise MomoError(f"없음: {p}")
    yt = None
    if not (local_video and local_subs):
        yt = YtDlp(args.cookies, args.cookies_from_browser, args.sleep_requests, log=log)

    results = []
    for t in targets:
        vid = t["id"]
        r = {"id": vid, "role": t.get("role"), "reason": t.get("reason"),
             "title": (videos.get(vid) or {}).get("title"), "errors": []}
        log(f"■ {r['role']} {vid} {r['title'] or ''}".rstrip())
        try:
            r["subs"] = get_subs(d, vid, yt, local_subs)
            log("  자막: " + ", ".join(f"{k} {v['lines']}줄" if "lines" in v else f"{k} {v['skipped']}"
                                     for k, v in r["subs"].items()))
        except YtDlpError as e:
            if e.bot:
                raise
            r["subs"] = {}
            r["errors"].append(f"자막: {e}")
            log(f"  자막 실패 (건너뜀): {str(e).splitlines()[-1]}")
        try:
            path = get_video(d, vid, yt, local_video)
        except YtDlpError as e:
            if e.bot:
                raise
            r["errors"].append(f"영상: {e}")
            log(f"  영상 실패: {str(e).splitlines()[-1]}")
            results.append(r)
            continue
        info = probe(path)
        r["video"] = {"file": str(path.relative_to(d)), "duration": round(info.duration, 3),
                      "width": info.width, "height": info.height, "fps": round(info.fps, 3)}
        frames = extract_frames(path, info.duration, n_frames, d / "frames" / vid)
        sheet = contact_sheet(frames, d / "frames" / f"{vid}_sheet.jpg")
        r["frames"] = {"count": len(frames), "dir": f"frames/{vid}", "sheet": str(sheet.relative_to(d)),
                       "interval_sec": round(info.duration / n_frames, 3),
                       "times": [round(tt, 2) for _, tt in frames]}
        r["shots"] = detect_shots(path, info.duration)
        sh = r["shots"]
        log(f"  영상 {fmt_dur(info.duration)} {info.width}x{info.height} · 프레임 {len(frames)}장 → {sheet}")
        log(f"  샷 {sh['shot_count']}개 (전환 {sh['cut_count']}회), 평균 {sh['mean_shot_sec']}초, "
            f"표준편차 {sh['stdev_shot_sec']}초")
        results.append(r)

    thumbs = []
    if not args.no_thumbs:
        for t in (data.get("targets") or {}).get("thumbs") or []:
            dest = d / "raw" / "thumbs" / f"{t['id']}.jpg"
            res = fetch_thumbnail(t["id"], dest)
            item = {"id": t["id"], "role": t["role"], **res}
            if "source" in res:
                item["file"] = str(dest.relative_to(d))
            thumbs.append(item)
            log(f"  썸네일 {t['role']} {t['id']}: {res.get('source') or res.get('error')}")
        sheet = thumbs_sheet(thumbs, d, d / "raw" / "thumbs" / "thumbs_sheet.jpg")
        if sheet:
            log(f"  썸네일 비교 시트: {sheet}")

    samples = {"generated_at": iso(time.time()), "frames_requested": n_frames,
               "scene_threshold": SCENE_THRESHOLD, "targets": results, "thumbnails": thumbs, "cleaned_up_at": None}
    save_json(d / "samples.json", samples)
    data["samples"] = samples
    save_json(data_path, data)
    (d / "report.md").write_text(render_report(data), encoding="utf-8")
    log(f"저장: {d / 'samples.json'} (data.json·report.md 에 병합)")
    log("프레임 시트·썸네일을 직접 보고 3단계 구조 분석 → 끝나면 반드시 --cleanup")
    failed = [r for r in results if "video" not in r]
    if failed and len(failed) == len(results):
        raise MomoError("모든 대상 영상 처리 실패:\n" + "\n".join(e for r in failed for e in r["errors"]))
    return 0


if __name__ == "__main__":
    main_wrapper(main)
