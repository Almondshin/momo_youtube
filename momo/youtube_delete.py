#!/usr/bin/env python3
"""Delete a YouTube video this pipeline uploaded and the user asked to remove (e.g. an older take of a remade episode).

Only ids recorded in episodes/<ep>/youtube.json[lang] can be deleted: an old take listed in previous_video_ids, or the current
video_id with --current. Deleting is permanent, so this runs only on the user's explicit request (CLAUDE.md). The result is
recorded in youtube.json[lang].deleted ([{video_id, at}]); a 404 (already gone) is recorded the same way.

  python momo/youtube_delete.py --ep ep11 --lang ko --video-id DYUVrjMgRkM
GitHub Actions: momo-youtube-delete (the OAuth secrets live there).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib import youtube as yt  # noqa: E402
from momolib.common import (MomoError, add_root_arg, check_ep, check_lang, get_paths, load_json,  # noqa: E402
                            main_wrapper, save_json)

VIDEO_ID_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def deletable(rec: dict, video_id: str, current: bool) -> str | None:
    """Why video_id may NOT be deleted from this youtube.json record (None = it may)."""
    if len(video_id) != 11 or not set(video_id) <= VIDEO_ID_CHARS:
        return f"YouTube 영상 id 형식이 아님: {video_id!r}"
    if video_id == rec.get("video_id"):
        return None if current else "지금 기록된 영상(video_id) — 정말 지우려면 --current"
    if video_id in (rec.get("previous_video_ids") or []):
        return None
    return "youtube.json 에 이 파이프라인이 올린 영상으로 기록돼 있지 않음 — 지우지 않는다"


def record_deleted(rec: dict, video_id: str) -> dict:
    gone = [d for d in rec.get("deleted") or [] if d.get("video_id") != video_id]
    rec["deleted"] = gone + [{"video_id": video_id, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}]
    rec["previous_video_ids"] = [v for v in rec.get("previous_video_ids") or [] if v != video_id]
    if rec.get("video_id") == video_id:
        rec["deleted_at"] = rec["deleted"][-1]["at"]
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="이 파이프라인이 올린 YouTube 영상 삭제 (사용자 요청 시에만)")
    add_root_arg(ap)
    ap.add_argument("--ep", required=True)
    ap.add_argument("--lang", required=True)
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--current", action="store_true", help="지금 기록된 video_id 를 지울 때")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    ep, lang = check_ep(args.ep), check_lang(args.lang)
    path = paths.youtube_json(ep)
    data = load_json(path) if path.exists() else {}
    rec = data.get(lang) or {}
    why = deletable(rec, args.video_id, args.current)
    if why:
        raise MomoError(f"{ep} {lang} {args.video_id}: {why}")
    if args.dry_run:
        print(f"= {ep} {lang}: {args.video_id} 삭제 가능 (--dry-run)")
        return 0
    info, source = yt.resolve_credentials(paths, lang)
    service = yt.build_service(info)
    try:
        yt.execute(service.videos().delete(id=args.video_id), f"영상 삭제 {args.video_id}")
        print(f"✔ {ep} {lang}: {args.video_id} 삭제 ({source})")
    except Exception as e:  # noqa: BLE001
        if yt.http_status(e) != 404:
            raise
        print(f"= {ep} {lang}: {args.video_id} 는 이미 없음 (404) — 삭제로 기록")
    data[lang] = record_deleted(rec, args.video_id)
    save_json(path, data)
    return 0


if __name__ == "__main__":
    main_wrapper(main)
