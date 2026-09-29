#!/usr/bin/env python3
"""7단계 자동 업로드: 완성본 → YouTube (아동용 고정, 썸네일, 재생목록, youtube.json 기록).

사용 예
  python upload.py --ep ep02 --lang all --dry-run          # 요청 body·파일만 출력 (자격증명·네트워크 없음)
  python upload.py --ep ep02 --lang en                     # privacy 기본값 = config.youtube.default_privacy
  python upload.py --ep ep02 --lang ko --privacy unlisted --no-thumbnail
  python upload.py --ep ep02 --lang all --publish-at 2026-10-03T18:00+09:00   # 예약 공개 (private + publishAt)
  python upload.py --compilation ep01-ep03 --lang en --title "Learn Colors with Momo | 30 min" \\
      [--description-file desc.txt] [--tags "colors,kids"] [--thumbnail thumb.jpg] [--playlist-id PL...]

- 메타: manifest.upload[lang] (title 이 비면 manifest.title[lang]). validate_manifest 와 같은 규칙으로 검증.
- status.selfDeclaredMadeForKids 는 항상 true (아동용 채널). containsSyntheticMedia 는 config 가 true 일 때만.
- 이미 youtube.json[lang].video_id 가 있으면 건너뜀. --force 는 새 영상을 하나 더 만든다 (기존 영상은 남음).
- 자격증명: env YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN_<LANG> → YOUTUBE_REFRESH_TOKEN
  → .secrets/youtube_<lang>.json (youtube_auth.py 로 생성). 값은 출력하지 않는다. 설정: docs/YOUTUBE_SETUP.md
- 모음집: compilations/<NAME>_<lang>.mp4, 설명 끝에 <NAME>_<lang>_chapters.txt, 기록은 compilations/<NAME>_youtube.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib import youtube as yt  # noqa: E402
from momolib.common import (LANGS, MomoError, Paths, add_root_arg, check_ep, check_lang, get_paths,  # noqa: E402
                            load_config, load_json, load_manifest, main_wrapper, save_json)

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")
THUMB_MAX = 2 * 1024 * 1024
AUDIT_NOTE = ("※ API 프로젝트가 YouTube 감사(audit)를 통과하기 전이면 API 로 올린 영상은 비공개로 잠긴다 "
              f"(공개/일부공개로 바꿀 수 없음) → {yt.SETUP_DOC}")


@dataclass
class Job:
    lang: str
    label: str
    video: Path
    thumb: Path | None
    title: str
    description: str
    tags: list[str]
    playlist_id: str | None
    record: Path          # youtube.json (lang 별 기록)
    ep: str | None = None


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_publish_at(value: str, now: datetime | None = None) -> str:
    """ISO8601(시간대 필수) → UTC RFC3339 'YYYY-MM-DDTHH:MM:SSZ'. 과거면 오류."""
    s = value.strip()
    if s[-1:] in ("Z", "z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise MomoError(f"--publish-at 형식 오류: {value!r} (예: 2026-10-03T18:00+09:00 또는 2026-10-03T09:00Z)") from e
    if dt.tzinfo is None:
        raise MomoError(f"--publish-at 에 시간대를 붙여줘: {value!r} (한국 시간은 +09:00, UTC 는 Z)")
    now = now or datetime.now(timezone.utc)
    if dt <= now:
        raise MomoError(f"--publish-at 이 과거임: {value} (= {utc_iso(dt)}, 지금 {utc_iso(now)})")
    return utc_iso(dt)


def clean_tags(tags) -> list[str]:
    return [str(t).strip() for t in (tags or []) if str(t).strip()]


def build_body(cfg: dict, job: Job, privacy: str, publish_at: str | None) -> tuple[dict, list[str]]:
    """videos.insert 요청 body. (body, 경고)."""
    y = cfg["youtube"]
    warns = []
    if y.get("made_for_kids") is not True:
        warns.append("config.youtube.made_for_kids 가 true 가 아니지만 아동용 채널이므로 true 로 올림")
    status = {"privacyStatus": "private" if publish_at else privacy, "selfDeclaredMadeForKids": True}
    if publish_at:
        status["publishAt"] = publish_at
    if y.get("contains_synthetic_media") is True:
        status["containsSyntheticMedia"] = True
    lang_code = (y.get("languages") or {}).get(job.lang) or job.lang
    snippet = {"title": job.title, "description": job.description, "categoryId": str(y.get("category_id") or "27"),
               "defaultLanguage": lang_code, "defaultAudioLanguage": lang_code}
    if job.tags:
        snippet["tags"] = job.tags
    return {"snippet": snippet, "status": status}, warns


# ---------------------------------------------------------------- 작업 목록

def episode_jobs(paths: Paths, cfg: dict, ep: str, langs: list[str]) -> list[Job]:
    m = load_manifest(paths, ep)
    jobs = []
    for lang in langs:
        meta = (m.get("upload") or {}).get(lang) or {}
        title = (meta.get("title") or (m.get("title") or {}).get(lang) or "").strip()
        out = paths.out(ep)
        jobs.append(Job(lang, f"{ep} [{lang}]", out / f"{ep}_{lang}.mp4", out / f"{ep}_{lang}_thumb.jpg", title,
                        (meta.get("description") or "").strip(), clean_tags(meta.get("tags")),
                        meta.get("playlist_id") or (cfg["youtube"].get("playlist_id") or {}).get(lang),
                        paths.youtube_json(ep), ep))
    return jobs


def compilation_job(paths: Paths, cfg: dict, args: argparse.Namespace, langs: list[str]) -> Job:
    name = args.compilation
    if not NAME_RE.match(name):
        raise MomoError(f"--compilation 이름은 영문/숫자/_-. 만: {name!r}")
    if len(langs) != 1:
        raise MomoError("모음집은 --lang en 또는 --lang ko 로 하나씩 올린다 (제목이 언어마다 다름)")
    if not args.title:
        raise MomoError("모음집 업로드는 --title 필요 (예: --title \"Learn Colors with Momo | 30 min\")")
    lang = langs[0]
    desc = args.description or ""
    if args.description_file:
        f = Path(args.description_file)
        if not f.is_file():
            raise MomoError(f"--description-file 없음: {f}")
        desc = f.read_text(encoding="utf-8")
    chapters = paths.compilations / f"{name}_{lang}_chapters.txt"
    if chapters.exists():
        desc = (desc.strip() + "\n\n" if desc.strip() else "") + chapters.read_text(encoding="utf-8").strip()
    else:
        print(f"△ 챕터 파일 없음: {chapters} — 설명에 챕터 없이 올림")
    thumb = Path(args.thumbnail) if args.thumbnail else paths.compilations / f"{name}_{lang}_thumb.jpg"
    return Job(lang, f"모음집 {name} [{lang}]", paths.compilations / f"{name}_{lang}.mp4", thumb, args.title.strip(),
               desc.strip(), clean_tags((args.tags or "").split(",")),
               args.playlist_id or (cfg["youtube"].get("playlist_id") or {}).get(lang),
               paths.compilations / f"{name}_youtube.json")


# ---------------------------------------------------------------- 업로드

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def mb(n: int) -> str:
    return f"{n / 1e6:.1f} MB"


def progress_printer(label: str):
    t0 = time.time()
    last = [-1]

    def show(done: int, total: int) -> None:
        pct = int(done * 100 / total) if total else 0
        if pct != last[0]:
            last[0] = pct
            rate = done / max(time.time() - t0, 1e-6) / 1e6
            print(f"  ↑ {label} {pct:3d}% ({mb(done)} / {mb(total)}, {rate:.1f} MB/s)", flush=True)
    return show


def step_summary(line: str) -> None:
    """GitHub Actions 실행 요약에 한 줄 추가 (로컬에서는 아무것도 안 함)."""
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def print_plan(job: Job, body: dict, thumb: Path | None, notify: bool) -> None:
    print(f"  영상: {job.video}" + (f" ({mb(job.video.stat().st_size)})" if job.video.exists() else " (없음)"))
    print(f"  요청 videos.insert — part=snippet,status, notifySubscribers={str(notify).lower()}, "
          f"resumable, 청크 {yt.CHUNK_SIZE // (1024 * 1024)} MB, 재시도 최대 {yt.MAX_RETRIES}회")
    print("  body = " + json.dumps(body, ensure_ascii=False, indent=2).replace("\n", "\n  "))
    if thumb:
        print(f"  요청 thumbnails.set — videoId=<업로드 후 ID>, 파일 {thumb} ({thumb.stat().st_size // 1024} KB)")
    else:
        print("  썸네일: 설정 안 함")
    if job.playlist_id:
        pl = {"snippet": {"playlistId": job.playlist_id,
                          "resourceId": {"kind": "youtube#video", "videoId": "<업로드 후 ID>"}}}
        print("  요청 playlistItems.insert — part=snippet, body = " + json.dumps(pl, ensure_ascii=False))
    print(f"  기록: {job.record} [{job.lang}]")


def pick_thumbnail(job: Job, enabled: bool) -> Path | None:
    if not enabled or job.thumb is None:
        return None
    if not job.thumb.is_file():
        print(f"△ 썸네일 없음: {job.thumb} — 썸네일 없이 올림 (build.py --thumbnail-only 로 생성)")
        return None
    if job.thumb.stat().st_size >= THUMB_MAX:
        print(f"△ 썸네일이 2MB 이상 ({mb(job.thumb.stat().st_size)}) — YouTube 제한으로 건너뜀")
        return None
    return job.thumb


def set_thumbnail(service, video_id: str, thumb: Path) -> bool:
    try:
        yt.execute(service.thumbnails().set(videoId=video_id, media_body=yt.media_file(thumb, "image/jpeg", False)),
                   "썸네일 설정")
        return True
    except Exception as e:  # noqa: BLE001 — 썸네일 실패는 경고만
        if not (isinstance(e, MomoError) or yt.http_status(e)):
            raise
        print("△ " + yt.describe_error(e, "썸네일 설정") + "\n  영상 업로드는 성공 — 썸네일만 빠짐.")
        if yt.http_status(e) == 403:
            print("  맞춤 썸네일은 채널 인증(전화번호) 후에만 된다 — YouTube Studio → 설정 → 채널 → 기능 사용 자격.\n"
                  f"  인증 후 YouTube Studio 에서 이 파일을 직접 올릴 것: {thumb}")
        return False


def add_to_playlist(service, video_id: str, playlist_id: str) -> bool:
    body = {"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
    try:
        yt.execute(service.playlistItems().insert(part="snippet", body=body), "재생목록 추가")
        return True
    except Exception as e:  # noqa: BLE001
        if not (isinstance(e, MomoError) or yt.http_status(e)):
            raise
        print("△ " + yt.describe_error(e, f"재생목록 {playlist_id} 추가"))
        return False


def upload_one(paths: Paths, cfg: dict, job: Job, body: dict, thumb: Path | None) -> dict:
    records = load_json(job.record) if job.record.exists() else {}
    prev = records.get(job.lang) or {}
    info, source = yt.resolve_credentials(paths, job.lang)
    print(f"  자격증명: {source}")
    service = yt.build_service(info)
    size = job.video.stat().st_size
    digest = sha256(job.video)
    notify = bool(cfg["youtube"].get("notify_subscribers", True))
    request = service.videos().insert(part="snippet,status", body=body, notifySubscribers=notify,
                                      media_body=yt.media_file(job.video, "video/mp4"))
    print(f"  업로드 시작 ({mb(size)})", flush=True)
    resp = yt.resumable_upload(request, f"{job.label} 영상 업로드", on_progress=progress_printer(job.lang))
    vid = resp["id"]
    st = resp.get("status") or {}
    wanted = body["status"]["privacyStatus"]
    actual = st.get("privacyStatus") or wanted
    if actual != wanted:
        print(f"△ 요청한 공개 상태 {wanted} → 실제 {actual}. {AUDIT_NOTE}")
    if st.get("madeForKids") is False or st.get("selfDeclaredMadeForKids") is False:
        print("△ 응답에서 아동용(made for kids)이 false — YouTube Studio 에서 '아동용'으로 직접 확인할 것")
    rec = {"video_id": vid, "url": yt.video_url(vid), "title": body["snippet"]["title"], "privacy": actual,
           "publish_at": body["status"].get("publishAt"), "uploaded_at": utc_iso(datetime.now(timezone.utc)),
           "made_for_kids": True, "thumbnail_set": False, "playlist_id": None, "file_sha256": digest}
    if prev.get("video_id"):
        rec["previous_video_ids"] = prev.get("previous_video_ids", []) + [prev["video_id"]]
    records[job.lang] = rec
    save_json(job.record, records)  # 썸네일·재생목록이 실패해도 중복 업로드 안 되게 먼저 기록
    print(f"  영상 ID {vid} 기록 → {job.record}")

    if thumb:
        rec["thumbnail_set"] = set_thumbnail(service, vid, thumb)
    if job.playlist_id and add_to_playlist(service, vid, job.playlist_id):
        rec["playlist_id"] = job.playlist_id
    save_json(job.record, records)
    if job.ep:
        m = load_manifest(paths, job.ep)
        m["status"] = "uploaded"
        save_json(paths.manifest(job.ep), m)
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="완성본을 YouTube 에 업로드 (아동용 고정)",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--ep", help="에피소드 (episodes/<ep>/out/<ep>_<lang>.mp4)")
    src.add_argument("--compilation", metavar="NAME", help="모음집 (compilations/<NAME>_<lang>.mp4)")
    ap.add_argument("--lang", required=True, help="en | ko | all")
    ap.add_argument("--privacy", choices=yt.PRIVACY, help="기본: config.youtube.default_privacy")
    ap.add_argument("--publish-at", metavar="ISO8601", help="예약 공개 시각 (시간대 필수) → private + publishAt(UTC)")
    ap.add_argument("--dry-run", action="store_true", help="요청 body·파일만 출력 (자격증명·네트워크 없음)")
    ap.add_argument("--force", action="store_true", help="이미 올린 언어도 다시 올림 (새 영상)")
    ap.add_argument("--no-thumbnail", action="store_true")
    g = ap.add_argument_group("모음집 전용")
    g.add_argument("--title")
    g.add_argument("--description")
    g.add_argument("--description-file")
    g.add_argument("--tags", help="쉼표 구분")
    g.add_argument("--thumbnail", help="기본: compilations/<NAME>_<lang>_thumb.jpg (있으면)")
    g.add_argument("--playlist-id", help="기본: config.youtube.playlist_id[lang]")
    args = ap.parse_args(argv)

    paths = get_paths(args)
    cfg = load_config(paths)
    langs = list(LANGS) if args.lang == "all" else [check_lang(args.lang)]
    privacy = args.privacy or cfg["youtube"].get("default_privacy") or "private"
    if privacy not in yt.PRIVACY:
        raise MomoError(f"config.youtube.default_privacy 는 {yt.PRIVACY} 중 하나: {privacy!r}")
    publish_at = parse_publish_at(args.publish_at) if args.publish_at else None
    if publish_at and privacy != "private":
        print(f"△ --publish-at 이 있으면 private 로 올리고 {publish_at} 에 공개(public)로 바뀐다 "
              f"(--privacy {privacy} 무시)")
    if args.ep:
        extra = [o for o in ("title", "description", "description_file", "tags", "thumbnail", "playlist_id")
                 if getattr(args, o)]
        if extra:
            raise MomoError(f"--{extra[0].replace('_', '-')} 는 --compilation 전용 (에피소드 메타는 manifest.upload)")
        jobs = episode_jobs(paths, cfg, check_ep(args.ep), langs)
    else:
        jobs = [compilation_job(paths, cfg, args, langs)]

    errs = [e for j in jobs for e in yt.check_upload_meta(j.title, j.description, j.tags, j.label)]
    if errs:
        raise MomoError("업로드 메타데이터 오류:\n  - " + "\n  - ".join(errs))

    done = []
    for job in jobs:
        print(f"\n━━ {job.label}" + (" — DRY RUN (자격증명·네트워크 사용 안 함)" if args.dry_run else ""))
        prev = ((load_json(job.record) if job.record.exists() else {}).get(job.lang) or {})
        if prev.get("video_id") and not args.force:
            print(f"= 이미 업로드됨: {prev.get('url') or prev['video_id']} — 건너뜀 "
                  "(--force 로 다시 올리면 새 영상이 하나 더 생김)")
            continue
        body, warns = build_body(cfg, job, privacy, publish_at)
        for w in warns:
            print(f"△ {w}")
        if not job.description:
            print("△ 설명이 비어 있음 — 학습 포인트 3줄 + 해시태그 10개 권장")
        thumb = pick_thumbnail(job, not args.no_thumbnail)
        if args.dry_run:
            if not job.video.is_file():
                print(f"△ 영상 없음 — 실제 업로드 전에 {'build.py' if job.ep else 'compile.py'} 필요")
            print_plan(job, body, thumb, bool(cfg["youtube"].get("notify_subscribers", True)))
            continue
        if not job.video.is_file():
            hint = f"build.py --ep {job.ep} --lang {job.lang}" if job.ep else "compile.py"
            raise MomoError(f"영상 파일 없음: {job.video} — 먼저 {hint}")
        if prev.get("video_id"):
            print(f"△ --force: 기존 영상 {prev['video_id']} 은 그대로 남는다 (필요하면 YouTube Studio 에서 삭제)")
        rec = upload_one(paths, cfg, job, body, thumb)
        done.append((job, rec))
        when = f", {rec['publish_at']} 공개 예약" if rec["publish_at"] else ""
        step_summary(f"- {job.label}: [{rec['title']}]({rec['url']}) — {rec['privacy']}{when}, 아동용")

    if args.dry_run:
        print("\n✔ DRY RUN 끝 — 아무것도 올리지 않음. 아동용(made for kids)=true 로 설정됨.")
        if privacy != "private" or publish_at:
            print(f"  {AUDIT_NOTE}")
        return 0
    if done:
        print("\n✔ 업로드 완료 — 아동용(made for kids) 설정됨")
        for job, rec in done:
            when = f" → {rec['publish_at']} (UTC) 공개 예약" if rec["publish_at"] else ""
            print(f"  {job.label}: {rec['url']} ({rec['privacy']}{when}), 썸네일 "
                  f"{'설정' if rec['thumbnail_set'] else '안 됨'}"
                  + (f", 재생목록 {rec['playlist_id']}" if rec["playlist_id"] else ""))
        if any(rec["privacy"] != "private" or rec["publish_at"] for _, rec in done):
            print(f"  {AUDIT_NOTE}")
    return 0


if __name__ == "__main__":
    main_wrapper(main)
