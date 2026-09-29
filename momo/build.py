#!/usr/bin/env python3
"""6단계 조립: manifest + 에셋 → episodes/<ep>/out/<ep>_<lang>.mp4 (+ 썸네일, 타임라인, 확인 시트).

사용 예
  python build.py --ep ep02 --lang en
  python build.py --ep ep02 --lang ko --check           # 컷별 확인 프레임 + contact sheet
  python build.py --ep ep02 --lang en --allow-missing   # 애니매틱: 없는 클립→이미지, 없는 이미지→컷 카드, 없는 음성→무음
  python build.py --ep ep02 --lang ko --thumbnail-only
  옵션: --jobs N (세그먼트 병렬, 기본 min(4, CPU)), --keep-temp, --no-cache

컷 길이·텍스트 타이밍은 매번 manifest 와 음성 파일 길이로 다시 계산한다 (episode.plan_timeline).
컷 세그먼트는 .build/<lang>/seg_<cut>.mp4 에 캐시되고 입력·파라미터 해시(seg_<cut>.json)가 같으면
다시 렌더하지 않는다 → 음성 하나를 다시 뽑으면 그 컷만 다시 렌더된다.
--keep-temp 가 없으면 세그먼트 캐시만 남기고 나머지 임시 파일(키워드 PNG, 믹스 WAV 등)은 지운다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib import audio, render  # noqa: E402
from momolib.common import (IMAGE_EXTS, VIDEO_EXTS, MomoError, add_root_arg, check_ep, check_lang,  # noqa: E402
                            find_font, find_media, get_paths, load_config, load_manifest,
                            main_wrapper, run, save_json)
from momolib.episode import CutPlan, plan_timeline, validate_manifest  # noqa: E402

SEG_VERSION = 1                      # 세그먼트 렌더 방식이 바뀌면 올린다 (캐시 무효화)
SEG_ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p"]
COLOR_TAGS, TO_709 = render.COLOR_TAGS, render.TO_709
_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


# ---------------------------------------------------------------- 세그먼트

def file_sig(p: Path | None) -> list | None:
    if p is None:
        return None
    st = p.stat()
    return [str(p), st.st_size, st.st_mtime_ns]


@dataclass
class Seg:
    plan: CutPlan
    frames: int
    text_at_f: int
    kb: dict | None
    path: Path
    meta: Path
    key: str = ""
    info: dict = field(default_factory=dict)
    cached: bool = False


def make_segs(plans: list[CutPlan], cfg: dict, tmp: Path, font: Path) -> list[Seg]:
    r = cfg["render"]
    fps = int(r["fps"])
    render_keys = ("width", "height", "fps", "text_height_ratio", "text_band_ratio", "text_pop_seconds",
                   "text_colors", "text_stroke_ratio", "kenburns_zoom", "kenburns_drift", "inset_default")
    s_ord = 0
    segs = []
    for p in plans:
        kb = None
        if p.type == "S":
            s_ord += 1
        if p.source_kind == "image":
            kb = render.kenburns_params(p.id, s_ord if p.type == "S" else p.index + 1, cfg)
        frames = int(round(p.dur * fps))
        seg = Seg(p, frames, int(round(p.text_at * fps)), kb, tmp / f"seg_{p.id}.mp4", tmp / f"seg_{p.id}.json")
        seg.key = hashlib.sha1(json.dumps({
            "v": SEG_VERSION, "type": p.type, "kind": p.source_kind, "src": file_sig(p.source),
            "frames": frames, "inset": p.inset, "kb": kb, "kw": p.keyword, "pos": p.text_pos,
            "color": p.text_color, "text_at": seg.text_at_f, "font": file_sig(font) if p.keyword else None,
            "card": card_lines(p) if p.source_kind == "placeholder" else None,
            "render": {k: r[k] for k in render_keys}}, sort_keys=True, default=str).encode()).hexdigest()
        segs.append(seg)
    return segs


def card_lines(p: CutPlan) -> list[str]:
    what = f"library clip: {p.cut.get('library_clip')}" if p.type == "L" else "NO IMAGE (animatic)"
    speech = " / ".join(it.text for it in p.items if it.kind == "speech")
    return [f"{p.id}  {p.type}", what, speech[:60] + ("…" if len(speech) > 60 else "")]


def resolve_inset(p: CutPlan, cfg: dict, sample) -> float:
    """cut.inset 숫자면 그 값, null 이면 테두리 자동 감지 → inset_default, 0 이면 끔."""
    if p.inset is not None:
        return max(0.0, min(0.2, p.inset))
    return float(cfg["render"]["inset_default"]) if render.detect_border(sample()) else 0.0


def overlay_graph(base: str, seg: Seg, cfg: dict, kw_input: int | None) -> str:
    """base 체인(라벨 없음) 뒤에 키워드 overlay 를 붙여 [v] 로 끝나는 그래프."""
    if kw_input is None:
        return base + ",format=yuv420p[v]"
    y, _ = render.band_geometry(cfg, seg.plan.text_pos)
    at = seg.text_at_f / int(cfg["render"]["fps"])
    return (f"{base}[base];[{kw_input}:v]scale={TO_709},format=yuva420p,setpts=PTS-STARTPTS+{at:.6f}/TB[kw];"
            f"[base][kw]overlay=0:{y}:eof_action=repeat:format=yuv420,format=yuv420p[v]")


def keyword_inputs(seg: Seg, cfg: dict, font: Path, work: Path) -> list[str]:
    p = seg.plan
    frames = render.render_keyword_frames(p.keyword, font, cfg, p.text_pos, p.text_color, work / f"kw_{p.id}")
    if not frames:
        return []
    return ["-framerate", str(cfg["render"]["fps"]), "-start_number", "0",
            "-i", str(frames[0].parent / "kw_%03d.png")]


def run_piped(cmd: list[str], frames) -> None:
    """rawvideo 프레임을 ffmpeg stdin 으로 흘려 넣는다."""
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err)
        try:
            for fr in frames:
                proc.stdin.write(fr)
            proc.stdin.close()
        except BrokenPipeError:
            pass  # ffmpeg 가 먼저 죽음 → 아래에서 stderr 로 보고
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        code = proc.wait()
        if code != 0:
            err.seek(0)
            tail = "\n".join(err.read().decode("utf-8", "replace").strip().splitlines()[-20:])
            raise MomoError(f"ffmpeg 실패 (exit {code}): {' '.join(cmd[:8])} ...\n{tail}")


def render_seg(seg: Seg, cfg: dict, font: Path, work: Path) -> None:
    p = seg.plan
    r = cfg["render"]
    W, H, fps = int(r["width"]), int(r["height"]), int(r["fps"])
    part = seg.path.with_name(seg.path.stem + ".part.mp4")
    kw = keyword_inputs(seg, cfg, font, work)
    kw_idx = 1 if kw else None
    out = ["-map", "[v]", "-frames:v", str(seg.frames), "-an", *SEG_ENC, "-r", str(fps), *COLOR_TAGS, str(part)]
    head = ["ffmpeg", "-y", "-v", "error", "-nostdin"]
    need = seg.frames / fps

    if p.source_kind == "video":
        st = render.video_stream(p.source)
        sw, sh = int(st["width"]), int(st["height"])
        L = float(p.source_len or 0.0)
        inset = resolve_inset(p, cfg, lambda: render.grab_frame(p.source, min(1.0, L / 2)))
        cw, ch, cx, cy = render.fill_box_int(sw, sh, W, H, inset)
        chain = f"[0:v]setpts=PTS-STARTPTS,crop={cw}:{ch}:{cx}:{cy}"
        mode = "clip"
        if need > L + 0.5 / fps:  # 나레이션이 더 길다 → 정방향 + 역방향 1회, 그래도 모자라면 정지
            rev = min(L, need - L + 0.2)
            chain += (f",split[fw][bw];[bw]trim=start={max(0.0, L - rev):.4f},setpts=PTS-STARTPTS,reverse[rv];"
                      f"[fw][rv]concat=n=2:v=1:a=0")
            mode = "pingpong" if need <= 2 * L else "pingpong+freeze"
        elif need < L - 0.5 / fps:
            mode = "trim"
        chain += (f",fps={fps},scale={W}:{H}:flags=lanczos:{render.in_matrix(st)}{TO_709},setsar=1,"
                  f"tpad=stop_mode=clone:stop_duration={need + 1:.3f}")
        run(head + ["-i", str(p.source)] + kw + ["-filter_complex", overlay_graph(chain, seg, cfg, kw_idx)] + out)
    elif p.source_kind == "image":
        im = render.load_image(p.source)
        inset = resolve_inset(p, cfg, lambda: im)
        kb = seg.kb
        mode = f"kenburns {'in' if kb['zoom_in'] else 'out'} {kb['zoom'] * 100:.1f}%"
        cmd = head + ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(fps), "-i", "-"]
        cmd += kw + ["-filter_complex", overlay_graph(f"[0:v]scale={TO_709}", seg, cfg, kw_idx)] + out
        run_piped(cmd, render.kenburns_frames(im, seg.frames, (W, H), kb["zoom"], kb["zoom_in"],
                                              kb["drift"], kb["drift_dir"], inset))
    else:
        inset, mode = 0.0, "placeholder"
        card = work / f"card_{p.id}.png"
        render.placeholder_card(card_lines(p), (W, H), font).save(card)
        run(head + ["-loop", "1", "-framerate", str(fps), "-i", str(card)] + kw
            + ["-filter_complex", overlay_graph(f"[0:v]scale={TO_709}", seg, cfg, kw_idx)] + out)

    got = int(render.video_stream(part).get("nb_frames") or 0)
    if got != seg.frames:
        raise MomoError(f"{p.id}: 세그먼트 프레임 수 {got} ≠ 계획 {seg.frames}")
    os.replace(part, seg.path)
    seg.info = {"key": seg.key, "frames": seg.frames, "inset": inset, "mode": mode,
                "rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    save_json(seg.meta, seg.info)


def render_all(segs: list[Seg], cfg: dict, font: Path, work: Path, jobs: int, use_cache: bool) -> None:
    todo = []
    for s in segs:
        if use_cache and s.path.exists() and s.meta.exists():
            try:
                meta = json.loads(s.meta.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                meta = {}
            if meta.get("key") == s.key:
                s.info, s.cached = meta, True
                continue
        todo.append(s)
    log(f"세그먼트 {len(segs)}개 — 캐시 {len(segs) - len(todo)}개, 렌더 {len(todo)}개 (병렬 {jobs})")
    if not todo:
        return
    todo.sort(key=lambda s: -s.frames * (3 if s.plan.source_kind == "image" else 1))  # 오래 걸리는 것부터
    done = 0
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(_timed, render_seg, s, cfg, font, work): s for s in todo}
        for fut in as_completed(futs):
            s = futs[fut]
            try:
                secs = fut.result()
            except Exception as e:
                for f in futs:
                    f.cancel()
                if isinstance(e, MomoError):
                    raise MomoError(f"{s.plan.id} 세그먼트 렌더 실패: {e}") from e
                raise
            done += 1
            log(f"  [{done}/{len(todo)}] {s.plan.id} {s.plan.type} {s.frames / int(cfg['render']['fps']):5.2f}s "
                f"{s.info['mode']}{' inset' if s.info['inset'] else ''} ({secs:.1f}s)")


def _timed(fn, *a) -> float:
    t = time.time()
    fn(*a)
    return time.time() - t


# ---------------------------------------------------------------- 연결 + mux

def join_graph(plans: list[CutPlan], fps: int) -> str:
    """xfade(fade) 는 plan.start 를 offset 으로, 하드컷 묶음은 concat. 전부 1/fps 타임베이스로 정수 프레임."""
    parts = [f"[{i}:v]settb=1/{fps},setpts=PTS-STARTPTS[s{i}]" for i in range(len(plans))]
    blocks: list[list[int]] = []
    for i, p in enumerate(plans):
        if i == 0 or p.xf_in > 0:
            blocks.append([i])
        else:
            blocks[-1].append(i)
    labels = []
    for b, idx in enumerate(blocks):
        if len(idx) == 1:
            labels.append(f"s{idx[0]}")
        else:
            parts.append("".join(f"[s{i}]" for i in idx) + f"concat=n={len(idx)}:v=1:a=0,settb=1/{fps}[b{b}]")
            labels.append(f"b{b}")
    cur = labels[0]
    for b in range(1, len(blocks)):
        p = plans[blocks[b][0]]
        parts.append(f"[{cur}][{labels[b]}]xfade=transition=fade:duration={p.xf_in:.6f}:offset={p.start:.6f}[x{b}]")
        cur = f"x{b}"
    parts.append(f"[{cur}]format=yuv420p[vout]")
    return ";".join(parts)


def mux(segs: list[Seg], plans: list[CutPlan], wav: Path, out: Path, cfg: dict) -> None:
    r, a = cfg["render"], cfg["audio"]
    fps = int(r["fps"])
    cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin"]
    for s in segs:
        cmd += ["-i", str(s.path)]
    cmd += ["-i", str(wav), "-filter_complex", join_graph(plans, fps), "-map", "[vout]", "-map", f"{len(segs)}:a",
            "-c:v", "libx264", "-profile:v", "high", "-preset", str(r["preset"]), "-crf", str(r["crf"]),
            "-pix_fmt", "yuv420p", "-r", str(fps), "-g", str(fps * 2), *COLOR_TAGS,
            "-c:a", "aac", "-b:a", str(a["aac_bitrate"]), "-ar", str(a["sample_rate"]), "-ac", "2",
            "-movflags", "+faststart", str(out)]
    run(cmd)


# ---------------------------------------------------------------- 썸네일 / 확인 시트 / 타임라인

def build_thumbnail(paths, cfg: dict, manifest: dict, ep: str, lang: str, tmp: Path,
                    allow_missing: bool) -> Path:
    th = manifest.get("thumbnail") or {}
    cuts = {c["id"]: c for c in manifest["cuts"]}
    cid = th.get("cut")
    if cid not in cuts:
        cid = next((c["id"] for c in manifest["cuts"] if c["type"] in ("V", "S")
                    and find_media(paths.images(ep), c["id"], IMAGE_EXTS)), manifest["cuts"][0]["id"])
        log(f"△ thumbnail.cut 이 지정되지 않음 → {cid} 사용")
    cut = cuts[cid]
    text = ((th.get("text") or {}).get(lang) or "").strip()
    img_path = find_media(paths.images(ep), cid, IMAGE_EXTS)
    clip = (find_media(paths.library_clips, cut.get("library_clip", ""), VIDEO_EXTS) if cut["type"] == "L"
            else find_media(paths.clips(ep), cid, VIDEO_EXTS))
    seg = tmp / f"seg_{cid}.mp4"
    if img_path:
        im = render.load_image(img_path)
    elif clip:
        im = render.grab_frame(clip, 1.0)
    elif seg.exists():
        im = render.grab_frame(seg, 0.0)  # 세그먼트 0프레임: 키워드 등장 전
    elif allow_missing:
        im = render.placeholder_card([cid, "THUMBNAIL"], (1920, 1080), None)
    else:
        raise MomoError(f"썸네일 컷 {cid} 의 이미지가 없음: {paths.images(ep)}/{cid}.png")
    inset = 0.0
    if img_path or clip:
        inset = cut["inset"] if cut.get("inset") is not None else (
            float(cfg["render"]["inset_default"]) if render.detect_border(im) else 0.0)
    need_hangul = lang == "ko" or bool(render.HANGUL_RE.search(text))
    font = find_font(paths, cfg, "thumbnail", need_hangul=need_hangul)
    out = paths.out(ep) / f"{ep}_{lang}_thumb.jpg"
    render.make_thumbnail(im, text, font, cfg, out, pos=th.get("text_pos") or "top", inset=float(inset))
    return out


def check_sheet(final: Path, plans: list[CutPlan], out_dir: Path, lang: str, font: Path, fps: int) -> Path:
    d = out_dir / f"check_{lang}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    want = [min(int(round((p.start + p.text_at + 0.5) * fps)), int(round((p.start + p.dur) * fps)) - 1)
            for p in plans]
    uniq = sorted(set(want))
    sel = "+".join(f"eq(n,{f})" for f in uniq)
    run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(final), "-vf", f"select='{sel}',scale=1280:-2",
         "-fps_mode", "passthrough", "-q:v", "3", str(d / "_%03d.jpg")])
    items = []
    for p, f in zip(plans, want):
        src = d / f"_{uniq.index(f) + 1:03d}.jpg"
        dst = d / f"{p.id}.jpg"
        shutil.copyfile(src, dst)
        kw = f" [{p.keyword}]" if p.keyword else ""
        items.append((dst, f"{p.id} {p.type} {f / fps:6.2f}s{kw} {p.text_pos}"))
    for f in d.glob("_*.jpg"):
        f.unlink()
    return render.contact_sheet(items, d / f"check_{lang}.jpg", font, cols=4, thumb_w=480)


def rel(paths, p: Path | None) -> str | None:
    if p is None:
        return None
    try:
        return str(p.resolve().relative_to(paths.root))
    except ValueError:
        return str(p)


def write_timeline(paths, ep: str, lang: str, plans, segs, total: float, fps: int, warnings: list[str],
                   extra: dict) -> Path:
    cuts = []
    for p, s in zip(plans, segs):
        cuts.append({"id": p.id, "type": p.type, "scene": p.scene, "start": round(p.start, 4),
                     "dur": round(p.dur, 4), "xf_in": round(p.xf_in, 4), "nar_len": round(p.nar_len, 3),
                     "keyword": p.keyword, "text_at": round(p.text_at, 3), "text_pos": p.text_pos,
                     "source": rel(paths, p.source), "source_kind": p.source_kind,
                     "estimated_audio": p.estimated_audio, "inset": s.info.get("inset"),
                     "render": s.info.get("mode")})
    data = {"ep": ep, "lang": lang, "fps": fps, "total": round(total, 4), "total_frames": int(round(total * fps)),
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cuts": cuts,
            "warnings": warnings, **extra}
    out = paths.out(ep) / f"{ep}_{lang}_timeline.json"
    save_json(out, data)
    return out


def cleanup(tmp: Path, plans: list[CutPlan], keep: bool) -> None:
    if keep:
        return
    live = {p.id for p in plans}
    for f in tmp.iterdir():
        if f.is_dir():
            shutil.rmtree(f, ignore_errors=True)
        elif f.name.startswith("seg_") and f.suffix in (".mp4", ".json") and f.stem[4:] in live:
            continue
        else:
            f.unlink(missing_ok=True)


# ---------------------------------------------------------------- main

def mmss(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:05.2f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="에피소드 조립 (ffmpeg)")
    add_root_arg(ap)
    ap.add_argument("--ep", required=True)
    ap.add_argument("--lang", required=True, help="en | ko")
    ap.add_argument("--allow-missing", action="store_true", help="애니매틱: 없는 에셋을 대체해서 조립")
    ap.add_argument("--check", action="store_true", help="컷별 확인 프레임 + contact sheet")
    ap.add_argument("--keep-temp", action="store_true", help=".build 임시 파일을 모두 남김")
    ap.add_argument("--thumbnail-only", action="store_true")
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    ap.add_argument("--no-cache", action="store_true", help="세그먼트 캐시 무시하고 전부 다시 렌더")
    args = ap.parse_args()
    paths = get_paths(args)
    ep, lang = check_ep(args.ep), check_lang(args.lang)
    if args.jobs < 1:
        raise MomoError("--jobs 는 1 이상")
    cfg = load_config(paths)
    manifest = load_manifest(paths, ep)
    errors, warns = validate_manifest(cfg, manifest)
    if errors:
        raise MomoError("manifest 오류 (validate_manifest.py 로 확인):\n  - " + "\n  - ".join(errors))
    tmp = paths.build_tmp(ep, lang)
    tmp.mkdir(parents=True, exist_ok=True)
    out_dir = paths.out(ep)
    out_dir.mkdir(parents=True, exist_ok=True)
    fps = int(cfg["render"]["fps"])
    t0 = time.time()

    if args.thumbnail_only:
        th = build_thumbnail(paths, cfg, manifest, ep, lang, tmp, args.allow_missing)
        log(f"✔ 썸네일: {th} ({th.stat().st_size // 1024} KB)")
        return 0

    plans, total, pwarn = plan_timeline(paths, cfg, manifest, lang, allow_missing=args.allow_missing)
    font = find_font(paths, cfg, "keyword", need_hangul=(lang == "ko"))
    if audio.find_bgm(paths, cfg, manifest) is None and not args.allow_missing:
        raise MomoError(f"BGM 없음: assets/bgm/ 에 BGM 을 넣어줘 ({paths.bgm})")
    log(f"▶ {ep} [{lang}] 컷 {len(plans)}개, 총 {mmss(total)} ({int(round(total * fps))}프레임), 폰트 {font.name}")
    for w in pwarn:
        log(f"△ {w}")

    segs = make_segs(plans, cfg, tmp, font)
    render_all(segs, cfg, font, tmp, args.jobs, not args.no_cache)
    t_seg = time.time()

    log("오디오 믹스 (나레이션 + BGM 덕킹 + 효과음 → loudnorm)")
    wav = tmp / "mix.wav"
    ainfo = audio.build_mix(paths, cfg, manifest, plans, total, wav, args.allow_missing)
    for w in ainfo.pop("warnings"):
        log(f"△ {w}")
    ln = ainfo["loudnorm"]
    if ln.get("normalization_type") not in ("linear", "silent"):
        log(f"△ loudnorm 이 {ln.get('normalization_type')} 모드로 동작 (피크가 높음)")
    t_aud = time.time()

    log(f"최종 인코딩 (xfade/concat 연결, crf {cfg['render']['crf']}, preset {cfg['render']['preset']})")
    final_tmp = tmp / f"{ep}_{lang}.mp4"
    mux(segs, plans, wav, final_tmp, cfg)
    vinfo = render.verify_output(final_tmp, total, cfg)
    final = out_dir / f"{ep}_{lang}.mp4"
    os.replace(final_tmp, final)
    t_mux = time.time()

    thumb = build_thumbnail(paths, cfg, manifest, ep, lang, tmp, args.allow_missing)
    warnings = list(pwarn) + [f"validate: {w}" for w in warns]
    tl = write_timeline(paths, ep, lang, plans, segs, total, fps, warnings,
                        {"allow_missing": args.allow_missing, "audio": ainfo, "output": vinfo})
    sheet = check_sheet(final, plans, out_dir, lang, font, fps) if args.check else None
    cleanup(tmp, plans, args.keep_temp)

    if not args.allow_missing and manifest.get("status") in (None, "planning", "producing"):
        manifest["status"] = "assembled"
        save_json(paths.manifest(ep), manifest)
    log(f"\n✔ {final} ({final.stat().st_size / 1e6:.1f} MB, {mmss(total)})")
    log(f"  썸네일 {thumb.name}, 타임라인 {tl.name}" + (f", 확인 시트 {rel(paths, sheet)}" if sheet else ""))
    log(f"  loudnorm: 입력 {ln.get('input_i')} → 출력 {ln.get('output_i')} LUFS ({ln.get('normalization_type')})")
    log(f"  시간: 세그먼트 {t_seg - t0:.1f}s, 오디오 {t_aud - t_seg:.1f}s, 인코딩 {t_mux - t_aud:.1f}s, "
        f"전체 {time.time() - t0:.1f}s")
    if args.allow_missing:
        log("  (애니매틱 — 업로드용 아님)")
    return 0


if __name__ == "__main__":
    main_wrapper(main)
