#!/usr/bin/env python3
"""1단계 · 벤치마킹 채널 분석 (yt-dlp 또는 YouTube Data API v3).

사용 예
  python analyze_channel.py --url https://www.youtube.com/@채널핸들
  python analyze_channel.py --url <채널 URL> --backend api            # youtube.com 이 막힌 환경 (YOUTUBE_API_KEY)
  python analyze_channel.py --url <채널 URL> --sleep-requests --cookies-from-browser chrome
  python analyze_channel.py report --dir research/<slug> [--labels labels.json]   # 재계산만 (네트워크 없음)
  python analyze_channel.py --offline-json channel.json [--offline-popular popular.json] [--offline-meta DIR]

(a) --flat-playlist 목록(최신순, 상한 --limit) (b) 인기순(sort=p) 시도 → 내림차순 검사, 아니면 조회수 정렬
(c) 최신 15 (d) 합집합 20개 개별 메타 → 72시간 미만 제외, 30분+ 모음집 분리, 배수·비중·상태·축별 격차 계산.
출력 research/<slug>/: report.md, data.json, channel_summary.json, labels.template.json, meta/<id>.json,
raw/channel.json·raw/popular.json (git 제외).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import MomoError, add_root_arg, get_paths, load_config, load_json, main_wrapper, save_json  # noqa: E402
from momolib.research import (POPULAR_FETCH, YouTubeAPI, YtDlp, YtDlpError, analyze, build_summary,  # noqa: E402
                              channel_slug, flat_entries, fmt_int, fmt_x, labels_template, load_labels,
                              normalize_channel_url, parse_now, render_report, resolve_dir, trim_meta, update_ytdlp,
                              video_url, ytdlp_version)


def log(msg: str) -> None:
    print(msg, flush=True)


def union_ids(summary: dict, recent_n: int) -> list[str]:
    return list(dict.fromkeys([e["id"] for e in summary["entries"][:recent_n]] + summary["popular"]["ids"]))


def fetch_ytdlp(args, url: str, limit: int, bench: dict) -> tuple[dict, dict, dict]:
    yt = YtDlp(args.cookies, args.cookies_from_browser, args.sleep_requests, log=log)
    log(f"(a) 채널 목록: {url}/videos (최대 {limit}개)")
    flat = yt.run(["--flat-playlist", "-J", "--extractor-args", "youtubetab:approximate_date",
                   "--playlist-end", str(limit), f"{url}/videos"], "채널 목록", want_json=True)
    log(f"    {len(flat_entries(flat))}개 받음")
    log("(b) 인기순(sort=p) 시도")
    pop, note = None, None
    try:
        pop = yt.run(["--flat-playlist", "-J", "--playlist-end", str(POPULAR_FETCH),
                      f"{url}/videos?view=0&sort=p&flow=grid"], "인기순 목록", want_json=True)
    except YtDlpError as e:
        if e.bot:
            raise
        note = "인기순 목록 요청 실패: " + str(e).splitlines()[-1][:200]
        log(f"    {note}")
    summary = build_summary(flat, url=url, backend="ytdlp", source="yt-dlp", limit=limit,
                            top_n=bench["top_count"], popular_flat=pop, popular_note=note)
    log(f"    → {summary['popular']['method']}: {summary['popular']['note']}")
    ids = union_ids(summary, bench["recent_count"])
    log(f"(d) 개별 메타 {len(ids)}개")
    metas, failures = {}, []
    for n, vid in enumerate(ids, 1):
        try:
            info = yt.run(["--skip-download", "-J", "--no-playlist", video_url(vid)], f"메타 {vid}", want_json=True)
        except YtDlpError as e:
            if e.bot:
                raise
            failures.append({"id": vid, "error": str(e).splitlines()[-1][:300]})
            log(f"    [{n}/{len(ids)}] {vid} 실패 (건너뜀): {failures[-1]['error']}")
            continue
        metas[vid] = trim_meta(info)
        if summary["channel"]["subscribers"] is None and info.get("channel_follower_count"):
            summary["channel"]["subscribers"] = info["channel_follower_count"]
        log(f"    [{n}/{len(ids)}] {vid} {fmt_int(metas[vid].get('view_count'))}회")
    summary["meta_failures"] = failures
    summary["ytdlp"] = {"version": ytdlp_version(), "escalations": yt.escalations}
    return summary, metas, {"channel.json": flat, "popular.json": pop}


def fetch_api(url: str, limit: int, bench: dict) -> tuple[dict, dict, dict]:
    api = YouTubeAPI()
    log(f"(API) 채널·업로드 목록·영상 정보: {url} (최대 {limit}개)")
    flat, all_metas, raw = api.fetch(url, limit, log=log)
    summary = build_summary(flat, url=url, backend="api", source=f"YouTube Data API ({raw['playlist']})",
                            limit=limit, top_n=bench["top_count"])
    summary["api"] = {"playlist": raw["playlist"], "quota_units": raw["quota_units"]}
    metas = {i: all_metas[i] for i in union_ids(summary, bench["recent_count"]) if i in all_metas}
    log(f"    {summary['listed']}개, 쿼터 약 {raw['quota_units']} units")
    return summary, metas, {"channel.json": raw, "popular.json": None}


def fetch_offline(args, url: str | None, limit: int, bench: dict) -> tuple[dict, dict, dict]:
    src = Path(args.offline_json)
    flat = load_json(src)
    pop = load_json(Path(args.offline_popular)) if args.offline_popular else None
    summary = build_summary(flat, url=url, backend="ytdlp", source=f"offline:{src.name}", limit=limit,
                            top_n=bench["top_count"], popular_flat=pop,
                            popular_note=None if pop else "오프라인: 인기순 결과 없음")
    meta_dir = Path(args.offline_meta) if args.offline_meta else src.parent / "meta"
    metas = {}
    for vid in union_ids(summary, bench["recent_count"]):
        p = meta_dir / f"{vid}.json"
        if p.exists():
            metas[vid] = trim_meta(load_json(p))
    summary["meta_failures"] = [{"id": v, "error": "오프라인 메타 없음"}
                                for v in union_ids(summary, bench["recent_count"]) if v not in metas]
    return summary, metas, {"channel.json": flat, "popular.json": pop}


def write_outputs(out: Path, summary: dict, metas: dict, labels_arg: str | None, now, bench: dict) -> dict:
    labels_path = Path(labels_arg) if labels_arg else out / "labels.json"
    if labels_arg and not labels_path.is_absolute() and not labels_path.exists():
        labels_path = out / labels_arg
    if labels_arg and not labels_path.exists():
        raise MomoError(f"labels 파일 없음: {labels_arg}")
    labels = load_labels(labels_path) if labels_path.exists() else {}
    data = analyze(summary, metas, labels, now, bench)
    data["fetch"] = {"ytdlp": summary.get("ytdlp"), "api": summary.get("api"),
                     "meta_failures": summary.get("meta_failures") or []}
    old = out / "data.json"
    if old.exists():
        prev = load_json(old)
        if prev.get("samples"):
            data["samples"] = prev["samples"]
    save_json(old, data)
    (out / "report.md").write_text(render_report(data), encoding="utf-8")
    save_json(out / "labels.template.json", labels_template(data))

    ch, st, lg = data["channel"], data["status"], data["largest_gap_axis"]
    log("")
    log(f"채널: {ch.get('name')} · 구독자 {fmt_int(ch.get('subscribers'))} · 목록 {fmt_int(ch.get('listed'))}개"
        + (" (일부 기준)" if ch.get("partial") else ""))
    log(f"인기순 방법: {data['popular']['method']} · 72h 미만 제외 {len(data['excluded_new'])}개 · "
        f"모음집 {data['compilations']['count']}개 분리")
    log(f"채널 상태: {st['label']} (중앙값 비 {fmt_x(st['median_ratio'])}, 일평균 비 {fmt_x(st['daily_ratio'])})")
    log(f"역대 최고작 / 최근 단편 평균: {fmt_x(data['metrics']['best_vs_recent_avg'])}")
    log("격차 최대 축: " + (f"{lg['name']} ({lg['high']} vs {lg['low']} {fmt_x(lg['ratio'])})" if lg else "없음"))
    if labels:
        log(f"labels 적용: {len(data['labels_applied'])}개 ({labels_path})")
    failures = data["fetch"]["meta_failures"]
    if failures:
        log(f"개별 메타 없음 {len(failures)}개: {', '.join(f['id'] for f in failures)}")
    log(f"저장: {out / 'report.md'}")
    log(f"      {out / 'data.json'}, {out / 'labels.template.json'}")
    log("다음: labels.template.json → labels.json (썸네일 주인공) → report 재계산, 그 다음 sample_videos.py")
    return data


def cmd_report(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="analyze_channel.py report", description="저장된 수집 결과로 재계산 (네트워크 없음)")
    add_root_arg(ap)
    ap.add_argument("--dir", required=True, help="research/<slug> 폴더")
    ap.add_argument("--labels", help="labels.json (기본: <dir>/labels.json 이 있으면 사용)")
    ap.add_argument("--now", help="기준 시각 ISO8601 (기본: 이전 data.json 의 기준 시각)")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    bench = load_config(paths)["benchmark"]
    out = resolve_dir(paths, args.dir)
    summary_path = out / "channel_summary.json"
    if not summary_path.exists():
        raise MomoError(f"{summary_path} 없음 — 먼저 analyze_channel.py --url <채널> 로 수집")
    summary = load_json(summary_path)
    metas = {p.stem: load_json(p) for p in sorted((out / "meta").glob("*.json"))}
    prev_now = load_json(out / "data.json").get("now") if (out / "data.json").exists() else None
    now = parse_now(args.now or prev_now or summary.get("fetched_at"))
    write_outputs(out, summary, metas, args.labels, now, bench)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["report"]:
        return cmd_report(argv[1:])
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_root_arg(ap)
    ap.add_argument("--url", help="채널 URL (기본: config.benchmark.channel_url)")
    ap.add_argument("--backend", choices=("ytdlp", "api"), default="ytdlp")
    ap.add_argument("--out", help="출력 폴더 (기본: research/<slug>)")
    ap.add_argument("--limit", type=int, help="목록 상한 (기본: config.benchmark.playlist_end = 2000)")
    ap.add_argument("--sleep-requests", action="store_true", help="처음부터 --sleep-requests 1")
    ap.add_argument("--cookies", help="봇 확인 시 재시도에 쓸 cookies.txt")
    ap.add_argument("--cookies-from-browser", help="봇 확인 시 재시도에 쓸 브라우저 (예: chrome)")
    ap.add_argument("--now", help="기준 시각 ISO8601 (기본: 현재 UTC)")
    ap.add_argument("--labels", help="labels.json (기본: <out>/labels.json 이 있으면 사용)")
    ap.add_argument("--no-update", action="store_true", help="yt-dlp -U 생략")
    ap.add_argument("--offline-json", help="yt-dlp --flat-playlist -J 결과 파일로 분석 (네트워크 없음)")
    ap.add_argument("--offline-popular", help="(오프라인) sort=p 결과 파일")
    ap.add_argument("--offline-meta", help="(오프라인) <id>.json 개별 메타 폴더 (기본: offline-json 옆 meta/)")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    cfg = load_config(paths)
    bench = cfg["benchmark"]
    limit = args.limit or int(bench.get("playlist_end") or 2000)
    if limit < 1:
        raise MomoError("--limit 은 1 이상")
    url = args.url or bench.get("channel_url")
    url = normalize_channel_url(url) if url else None
    if not url and not args.offline_json:
        raise MomoError("--url 로 벤치마킹 채널 링크를 줘 (영상 링크가 아니라 채널 링크)")
    now = parse_now(args.now)

    if args.offline_json:
        summary, metas, raw = fetch_offline(args, url, limit, bench)
    else:
        if args.backend == "ytdlp" and not args.no_update:
            log("yt-dlp 최신화 시도 (yt-dlp -U)")
            update = update_ytdlp(log)
        else:
            update = None
        summary, metas, raw = (fetch_api(url, limit, bench) if args.backend == "api"
                               else fetch_ytdlp(args, url, limit, bench))
        if update:
            summary["ytdlp"]["update"] = update

    slug = channel_slug(url, fallback=summary["channel"].get("handle") or summary["channel"].get("id"))
    out = resolve_dir(paths, args.out) if args.out else paths.research / slug
    (out / "raw").mkdir(parents=True, exist_ok=True)
    for name, obj in raw.items():
        if obj is not None:
            save_json(out / "raw" / name, obj)
    save_json(out / "channel_summary.json", summary)
    meta_dir = out / "meta"
    if meta_dir.exists():
        shutil.rmtree(meta_dir)  # 이전 수집의 메타가 섞이지 않게
    for vid, m in metas.items():
        save_json(meta_dir / f"{vid}.json", m)
    write_outputs(out, summary, metas, args.labels, now, bench)
    return 0


if __name__ == "__main__":
    main_wrapper(main)
