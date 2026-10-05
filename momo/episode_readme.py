#!/usr/bin/env python3
"""episodes/<ep>/README.md — 에피소드 기록 (7단계).

주제, 컷 수(타입별), 사용 크레딧·생성/재생성 횟수, 길이(EN/KO — out/<ep>_<lang>_timeline.json 이 있으면),
제목·설명·태그(EN/KO), 업로드 결과(youtube.json), 아동용(made for kids) 설정, 다음 편에 반영할 점.
다시 실행하면 덮어쓴다 — 메모는 manifest.notes(next_time, approvals)에 적는다.

사용 예
  python episode_readme.py --ep ep02
  python episode_readme.py --ep ep02 --stdout
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import (Paths, active_langs, add_root_arg, check_ep, episode_cfg, get_paths, load_config, load_json,  # noqa: E402
                            load_manifest, main_wrapper)
from momolib.episode import count_types  # noqa: E402
from momolib.genrec import episode_cap, episode_slots, status_of  # noqa: E402

KIDS_NOTE = ("이 영상은 YouTube 에서 반드시 **\"아동용(made for kids)\"** 으로 설정해야 한다 "
             "(2~5세 대상 키즈 채널 — 지시서 7단계). upload.py 는 config 와 상관없이 "
             "`status.selfDeclaredMadeForKids = true` 로 올린다. Studio 에서 직접 올릴 때는 "
             "'예, 아동용입니다'를 선택할 것.")


def mmss(sec: float) -> str:
    s = int(round(sec))
    return f"{s // 60}:{s % 60:02d}"


def md(text) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def length_line(paths: Paths, ep: str, lang: str) -> str:
    tl = paths.out(ep) / f"{ep}_{lang}_timeline.json"
    if not tl.exists():
        return "빌드 전 (validate_manifest.py 의 예상 길이 참고)"
    data = load_json(tl)
    total = float(data.get("total") or 0)
    s = f"{mmss(total)} ({total:.1f}초, 컷 {len(data.get('cuts') or [])}개"
    if data.get("allow_missing") or any(c.get("estimated_audio") for c in data.get("cuts") or []):
        s += ", 애니매틱/추정 음성 포함"
    if data.get("built_at"):
        s += f", 빌드 {data['built_at']}"
    return s + ")"


def generation_summary(paths: Paths, cfg: dict, m: dict) -> list[str]:
    slots = episode_slots(paths, cfg, m)
    out = []
    for kind, label in (("image", "컷 이미지"), ("clip", "V 클립"), ("audio", "음성 블록")):
        ss = [s for s in slots if s.kind == kind]
        if not ss:
            continue
        ok = sum(1 for s in ss if status_of(s.rec) == "approved")
        tries = sum(int(s.rec.get("attempts") or 0) for s in ss)
        cred = sum(float(s.rec.get("credits") or 0) for s in ss)
        out.append(f"| {label} | {ok}/{len(ss)} | {tries} | {cred:g} |")
    return out


def render(paths: Paths, cfg: dict, m: dict) -> str:
    cfg = episode_cfg(cfg, m)
    ep = m["ep"]
    topic, title = m.get("topic") or {}, m.get("title") or {}
    cr, notes = m.get("credits") or {}, m.get("notes") or {}
    counts = count_types(m)
    cuts = m.get("cuts") or []
    scenes = len({c.get("scene") for c in cuts})
    yt_path = paths.youtube_json(ep)
    yt = load_json(yt_path) if yt_path.exists() else {}
    cap = episode_cap(cfg, m)
    L = [f"# {ep} — {topic.get('ko') or '(주제 미정)'}" + (f" ({topic['en']})" if topic.get("en") else ""), "",
         f"> episode_readme.py 가 생성 ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC). "
         "다시 실행하면 덮어쓴다 — 메모는 manifest.notes 에.", "",
         "## 요약", "",
         "| 항목 | 값 |", "|---|---|",
         f"| 상태 | {md(m.get('status'))} |",
         f"| 주제 | {md(topic.get('ko'))} / {md(topic.get('en'))} |",
         f"| 컷 수 | {len(cuts)}개 (V {counts['V']} · S {counts['S']} · L {counts['L']}), 씬 {scenes}개 |",
         f"| 사용 크레딧 | {float(cr.get('spent') or 0):g} / 캡 {cap:g}"
         + (f" (예상 {cr['estimate']:g})" if isinstance(cr.get("estimate"), (int, float)) else "") + " |",
         f"| 생성 / 재생성 횟수 | {int(cr.get('generations') or 0)} / {int(cr.get('regenerations') or 0)} |"]
    if cr.get("api_generations") or cr.get("api_usd"):  # hf_api.py — the API's prepaid balance, not the cap
        L.append(f"| Higgsfield API | ${float(cr.get('api_usd') or 0):.2f} (생성 {int(cr.get('api_generations') or 0)}회,"
                 f" 구독 크레딧과 별개) |")
    for lang in active_langs(cfg):
        L.append(f"| 길이 {lang.upper()} | {md(length_line(paths, ep, lang))} |")
    L.append(f"| 썸네일 | {md((m.get('thumbnail') or {}).get('cut'))} — "
             + " / ".join(md(((m.get('thumbnail') or {}).get('text') or {}).get(lang)) for lang in active_langs(cfg)) + " |")

    L += ["", "## 아동용(made for kids) 설정", "", f"> {KIDS_NOTE}", ""]
    for lang in active_langs(cfg):
        rec = yt.get(lang) or {}
        if not rec.get("video_id"):
            L.append(f"- {lang.upper()}: 아직 업로드 전 — upload.py 로 올리면 아동용 true 로 자동 설정됨")
        elif rec.get("made_for_kids") is True:
            L.append(f"- {lang.upper()}: ✔ upload.py 가 selfDeclaredMadeForKids = true 로 업로드함 ({rec['video_id']})")
        else:
            L.append(f"- {lang.upper()}: △ youtube.json 에 아동용 기록이 없음 — YouTube Studio 에서 '아동용' 설정을 직접 확인")

    L += ["", "## 업로드 결과 (youtube.json)", ""]
    if any((yt.get(lang) or {}).get("video_id") for lang in active_langs(cfg)):
        L += ["| 언어 | 영상 | 공개 상태 | 예약 공개 | 업로드 시각 | 썸네일 | 재생목록 |", "|---|---|---|---|---|---|---|"]
        for lang in active_langs(cfg):
            r = yt.get(lang) or {}
            if not r.get("video_id"):
                L.append(f"| {lang.upper()} | (업로드 전) | | | | | |")
                continue
            privacy = f"삭제됨 ({r['deleted_at']})" if r.get("deleted_at") else r.get("privacy")
            L.append(f"| {lang.upper()} | [{r['video_id']}]({r.get('url') or ''}) | {md(privacy)} "
                     f"| {md(r.get('publish_at') or '—')} | {md(r.get('uploaded_at'))} "
                     f"| {'✔' if r.get('thumbnail_set') else '✖ (채널 인증 필요할 수 있음)'} "
                     f"| {md(r.get('playlist_id') or '—')} |")
    else:
        L.append("아직 업로드 전 — `python upload.py --ep " + ep + " --lang all` 또는 Actions momo-publish")

    L += ["", "## 제목·설명·태그"]
    up = m.get("upload") or {}
    for lang in active_langs(cfg):
        meta = up.get(lang) or {}
        L += ["", f"### {lang.upper()}", "",
              f"- 제목: {meta.get('title') or title.get(lang) or '(미정)'}",
              f"- 태그: {', '.join(meta.get('tags') or []) or '(없음)'}",
              "- 설명:", "", "```text", (meta.get("description") or "(없음)").strip(), "```"]

    L += ["", "## 생성 기록", "", "| 종류 | 승인 | 시도 | 크레딧 |", "|---|---:|---:|---:|"]
    L += generation_summary(paths, cfg, m)
    L.append("")
    L.append("라이브러리 L 컷은 0 크레딧 (라이브러리 클립·고정 음성 재사용). 자세한 진행표: "
             f"`python hf_jobs.py status --ep {ep}`")
    if notes.get("approvals"):
        L += ["", "## 승인 기록", ""] + [f"- {md(a)}" for a in notes["approvals"]]
    L += ["", "## 다음 편에 반영할 점", ""]
    L += [f"- {md(n)}" for n in notes.get("next_time") or []] or ["- (아직 없음 — manifest.notes.next_time 에 적기)"]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="에피소드 README.md 생성",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    ap.add_argument("--ep", required=True)
    ap.add_argument("--stdout", action="store_true", help="파일 대신 화면에")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    ep = check_ep(args.ep)
    text = render(paths, load_config(paths), load_manifest(paths, ep))
    if args.stdout:
        print(text, end="")
        return 0
    out = paths.ep(ep) / "README.md"
    out.write_text(text, encoding="utf-8")
    print(f"✔ {out}")
    return 0


if __name__ == "__main__":
    main_wrapper(main)
