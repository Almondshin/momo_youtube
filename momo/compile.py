#!/usr/bin/env python3
"""모음집: 에피소드 완성본들을 transition 클립으로 이어 붙이고 유튜브 챕터 텍스트를 만든다.

사용 예
  python compile.py --lang en ep01 ep02 ep03
  python compile.py --lang ko ep01 ep02 ep03 --name colors_best --title-prefix

- 입력: episodes/<ep>/out/<ep>_<lang>.mp4 (없거나 애니매틱(--allow-missing) 빌드면 build.py 를 다시 돌리라고 멈춤)
- 에피소드 사이에 library/clips/transition.mp4 (1920x1080/30fps 로 정규화, 원래 소리는 버림 → BGM 없음,
  assets/sfx 에 whoosh/transition 효과음이 있으면 얹음)
- 출력: compilations/<name>_<lang>.mp4 (loudnorm -14 LUFS 재적용), compilations/<name>_<lang>_chapters.txt
  (첫 줄 0:00, 각 에피소드 시작 시각 + 제목). --title-prefix 는 제목 앞에 에피소드 번호(EP02)를 붙인다.
- 챕터 규칙(3개 이상, 각 10초 이상)이 안 맞으면 경고. 30분 이상이면 모음집(compilation) 축 안내.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib import audio, render  # noqa: E402
from momolib.common import (AUDIO_EXTS, VIDEO_EXTS, MomoError, add_root_arg, check_ep, check_lang,  # noqa: E402
                            find_media, fmt_ts, get_paths, list_files, load_config, load_json, load_manifest, main_wrapper,
                            probe_duration, run)

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")


def ep_title(paths, ep: str, lang: str, prefix: bool) -> str:
    m = load_manifest(paths, ep)
    t = (m.get("title") or {}).get(lang) or ((m.get("upload") or {}).get(lang) or {}).get("title") or ep
    return f"{ep.upper()} {t}" if prefix else t


def find_whoosh(paths) -> Path | None:
    return next((f for f in list_files(paths.sfx, AUDIO_EXTS)
                 if "whoosh" in f.stem.lower() or "transition" in f.stem.lower()), None)


def main() -> int:
    ap = argparse.ArgumentParser(description="에피소드 모음집 + 챕터")
    add_root_arg(ap)
    ap.add_argument("--lang", required=True, help="en | ko")
    ap.add_argument("eps", nargs="+", help="에피소드 번호 (순서대로)")
    ap.add_argument("--name", help="출력 이름 (기본: 첫ep-끝ep)")
    ap.add_argument("--title-prefix", action="store_true", help="챕터 제목 앞에 에피소드 번호")
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()
    paths = get_paths(args)
    lang = check_lang(args.lang)
    eps = [check_ep(e) for e in args.eps]
    name = args.name or f"{eps[0]}-{eps[-1]}"
    if not NAME_RE.match(name):
        raise MomoError(f"--name 은 영문/숫자/_-. 만: {name!r}")
    cfg = load_config(paths)
    r, a = cfg["render"], cfg["audio"]
    W, H, fps, sr = int(r["width"]), int(r["height"]), int(r["fps"]), int(a["sample_rate"])
    t0 = time.time()

    files = [paths.out(ep) / f"{ep}_{lang}.mp4" for ep in eps]
    missing = [ep for ep, f in zip(eps, files) if not f.exists()]
    if missing:
        raise MomoError("에피소드 완성본이 없음 — 먼저 build 하세요:\n  "
                        + "\n  ".join(f"python build.py --ep {ep} --lang {lang}" for ep in missing))
    animatic = [ep for ep in eps if (load_json(paths.out(ep) / f"{ep}_{lang}_timeline.json", default={})
                                     .get("allow_missing"))]
    if animatic:
        raise MomoError(f"애니매틱(--allow-missing) 빌드는 모음집에 넣지 않는다: {', '.join(animatic)} — 다시 build")
    frames = []
    for f in files:
        st = render.video_stream(f)
        if (st.get("width"), st.get("height"), st.get("r_frame_rate")) != (W, H, f"{fps}/1"):
            raise MomoError(f"{f.name}: {st.get('width')}x{st.get('height')} {st.get('r_frame_rate')} — "
                            f"build.py 출력 규격({W}x{H} {fps}fps)이 아님, 다시 build 하세요")
        frames.append(int(st.get("nb_frames") or round(float(st["duration"]) * fps)))

    k = len(files)
    trans = find_media(paths.library_clips, "transition", VIDEO_EXTS)
    t_frames = 0
    if k > 1:
        if not trans:
            raise MomoError(f"전환 클립 없음: {paths.library_clips}/transition.mp4 (fetch_assets.py --library)")
        t_frames = max(1, int(probe_duration(trans) * fps))
    whoosh = find_whoosh(paths) if k > 1 else None

    tmp = paths.compilations / ".build" / f"{name}_{lang}"
    tmp.mkdir(parents=True, exist_ok=True)
    print(f"▶ 모음집 {name} [{lang}] 에피소드 {k}개, 전환 클립 {t_frames / fps:.2f}s"
          + (f" + 효과음 {whoosh.name}" if whoosh else ""))

    # ---- 오디오: 에피소드 소리 + 전환(무음/효과음)을 샘플 단위로 이어 붙인 뒤 loudnorm
    ain, graph, seq = [], [], []
    for i, f in enumerate(files):
        ain += ["-i", str(f)]
        n = round(frames[i] / fps * sr)
        graph.append(f"[{i}:a]aresample={sr},aformat=sample_fmts=flt:channel_layouts=stereo,"
                     f"apad=whole_len={n},atrim=end_sample={n}[a{i}]")
    tn = round(t_frames / fps * sr)
    if k > 1:
        if whoosh:
            ain += ["-i", str(whoosh)]
            graph.append(f"[{k}:a]aresample={sr},aformat=sample_fmts=flt:channel_layouts=stereo,volume=-6dB,"
                         f"apad=whole_len={tn},atrim=end_sample={tn},asplit={k - 1}"
                         + "".join(f"[w{j}]" for j in range(k - 1)))
        else:
            graph += [f"anullsrc=r={sr}:cl=stereo,atrim=end_sample={tn},aformat=sample_fmts=flt[w{j}]"
                      for j in range(k - 1)]
    for i in range(k):
        seq.append(f"[a{i}]")
        if i < k - 1:
            seq.append(f"[w{i}]")
    graph.append("".join(seq) + f"concat=n={len(seq)}:v=0:a=1[aout]")
    premix = tmp / "premix.wav"
    run(["ffmpeg", "-y", "-v", "error", "-nostdin", *ain, "-filter_complex", ";".join(graph), "-map", "[aout]",
         "-c:a", "pcm_f32le", str(premix)])
    total_frames = sum(frames) + t_frames * (k - 1)
    total = total_frames / fps
    wav = tmp / "mix.wav"
    ln = audio.loudnorm(premix, wav, cfg, round(total * sr))

    # ---- 영상: 에피소드는 그대로, 전환 클립은 크롭-투-필 1920x1080/30fps 로 맞춰 concat
    vg = [f"[{i}:v]settb=1/{fps},setpts=PTS-STARTPTS,format=yuv420p[e{i}]" for i in range(k)]
    vin = [x for f in files for x in ("-i", str(f))]
    if k > 1:
        st = render.video_stream(trans)
        cw, ch, cx, cy = render.fill_box_int(int(st["width"]), int(st["height"]), W, H, 0.0)
        vin += ["-i", str(trans)]
        vg.append(f"[{k}:v]setpts=PTS-STARTPTS,crop={cw}:{ch}:{cx}:{cy},fps={fps},"
                  f"scale={W}:{H}:flags=lanczos:{render.in_matrix(st)}{render.TO_709},setsar=1,format=yuv420p,"
                  f"tpad=stop_mode=clone:stop_duration=1,trim=end_frame={t_frames},settb=1/{fps},"
                  f"setpts=PTS-STARTPTS,split={k - 1}" + "".join(f"[t{j}]" for j in range(k - 1)))
    vseq = []
    for i in range(k):
        vseq.append(f"[e{i}]")
        if i < k - 1:
            vseq.append(f"[t{i}]")
    vg.append("".join(vseq) + f"concat=n={len(vseq)}:v=1:a=0,format=yuv420p[vout]")
    n_in = k + (1 if k > 1 else 0)
    out_tmp = tmp / f"{name}_{lang}.mp4"
    print(f"인코딩 (crf {r['crf']}, preset {r['preset']}) — 총 {fmt_ts(total)}")
    run(["ffmpeg", "-y", "-v", "error", "-nostdin", *vin, "-i", str(wav), "-filter_complex", ";".join(vg),
         "-map", "[vout]", "-map", f"{n_in}:a", "-c:v", "libx264", "-profile:v", "high", "-preset", str(r["preset"]),
         "-crf", str(r["crf"]), "-pix_fmt", "yuv420p", "-r", str(fps), "-g", str(fps * 2), *render.COLOR_TAGS,
         "-c:a", "aac", "-b:a", str(a["aac_bitrate"]), "-ar", str(sr), "-ac", "2", "-movflags", "+faststart",
         str(out_tmp)])
    render.verify_output(out_tmp, total, cfg)
    paths.compilations.mkdir(parents=True, exist_ok=True)
    out = paths.compilations / f"{name}_{lang}.mp4"
    os.replace(out_tmp, out)

    # ---- 챕터
    lines, starts, t = [], [], 0
    for i, ep in enumerate(eps):
        starts.append(t / fps)
        lines.append(f"{fmt_ts(t / fps)} {ep_title(paths, ep, lang, args.title_prefix)}")
        t += frames[i] + (t_frames if i < k - 1 else 0)
    chapters = paths.compilations / f"{name}_{lang}_chapters.txt"
    chapters.write_text("\n".join(lines) + "\n", encoding="utf-8")
    lens = [b - s for s, b in zip(starts, starts[1:] + [total])]
    if k < 3 or min(lens) < 10:
        print(f"△ 유튜브 챕터 규칙(3개 이상, 각 10초 이상)에 맞지 않음 — 챕터 {k}개, 가장 짧은 {min(lens):.1f}s "
              "→ 설명란에 넣어도 챕터로 표시되지 않을 수 있음")
    if not args.keep_temp:
        shutil.rmtree(tmp, ignore_errors=True)
        try:
            tmp.parent.rmdir()  # 비었을 때만
        except OSError:
            pass

    print(f"\n✔ {out} ({out.stat().st_size / 1e6:.1f} MB, {fmt_ts(total)})")
    print(f"  챕터: {chapters.name}")
    for line in lines:
        print(f"    {line}")
    print(f"  loudnorm: 입력 {ln.get('input_i')} → 출력 {ln.get('output_i')} LUFS ({ln.get('normalization_type')})")
    if total >= float(cfg["benchmark"]["compilation_min_seconds"]):
        print("  ※ 30분 이상 — 채널 분석 기준 '모음집(compilation) 축' 영상입니다 (단편 평균과 따로 봄).")
    print(f"  시간: {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    main_wrapper(main)
