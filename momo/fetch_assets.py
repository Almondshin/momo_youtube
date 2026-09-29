#!/usr/bin/env python3
"""생성 결과 내려받기: manifest(·library.json) 의 GenRec.url → 파일 이름 규칙 경로.

- 대상: status 가 generated/approved 이고 url 이 있는 항목 (pending/rejected 는 건너뜀).
- --ep: images/<cut>.*, clips/<cut>.*, audio/<lang>/<cut>_<n>.*
- --library: library/clips/<name>.mp4, library/audio/<lang>/<intro|outro>.* (조립에 필요) +
  참고용 library/sheets/<name>.*, 클립 시작 이미지 library/clips/<name>.png, 음성 샘플 library/audio/<lang>/samples/.
  참고용 파일은 조립에 안 쓰므로 받지 못해도 경고(△)만 — 게시(Actions)가 막히지 않게.
- 확장자: URL 경로 → Content-Type → 파일 앞부분(매직 바이트) 순서로 결정.
- 받은 뒤 이미지는 Pillow, 영상·음성은 ffprobe 로 검증. 실패하면 3회까지 재시도 (4xx·프록시 거부는 바로 실패).
- 이미 파일이 있으면 건너뜀. 같은 폴더의 .sources.json 에 받은 URL 을 적어 두고, 기록된 URL 이 바뀌었으면
  (재생성·다른 시도 승인) 다시 받는다. --force 는 무조건 다시 받는다.
- http(s)://, file:// 지원. 끝에 실패 목록 표, (참고용 외) 실패가 있으면 exit 1.

사용 예
  python fetch_assets.py --ep ep02
  python fetch_assets.py --ep ep02 --library     # 라이브러리도 (Actions 에서 build 전에)
  python fetch_assets.py --library --force
"""
from __future__ import annotations

import argparse
import http.client
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import (MomoError, add_root_arg, check_ep, find_media, get_paths, load_config,  # noqa: E402
                            load_json, load_library, load_manifest, main_wrapper, probe, save_json, which)
from momolib.genrec import FETCHABLE, KIND_EXTS, Slot, episode_slots, library_slots  # noqa: E402

REF_GROUPS = ("sheet", "lib_image", "voice")  # 조립에 안 쓰는 참고용 (시트, 클립 시작 이미지, 음성 샘플)

RETRIES = 3
BACKOFF = 1.0      # 초, 시도마다 2배 (테스트가 0 으로 바꾼다)
TIMEOUT = 60
SOURCES = ".sources.json"
CTYPE_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/webp": ".webp",
             "video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm", "video/x-matroska": ".mkv",
             "audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/wav": ".wav", "audio/x-wav": ".wav",
             "audio/wave": ".wav", "audio/vnd.wave": ".wav", "audio/mp4": ".m4a", "audio/x-m4a": ".m4a",
             "audio/aac": ".aac", "audio/ogg": ".ogg", "audio/flac": ".flac", "audio/x-flac": ".flac",
             "audio/opus": ".opus"}


class FetchError(Exception):
    def __init__(self, msg: str, retry: bool = True):
        super().__init__(msg)
        self.retry = retry


def sniff(head: bytes, kind: str) -> str | None:
    if head.startswith(b"\x89PNG"):
        return ".png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return ".wav"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if kind == "audio" or brand.startswith(b"M4A"):
            return ".m4a"
        return ".mov" if brand == b"qt  " else ".mp4"
    if head.startswith(b"ID3") or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return ".mp3"
    if head.startswith(b"OggS"):
        return ".ogg"
    if head.startswith(b"fLaC"):
        return ".flac"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    return None


def pick_ext(url: str, ctype: str, head: bytes, kind: str) -> str:
    allowed = KIND_EXTS[kind]
    suffix = Path(unquote(urlparse(url).path)).suffix.lower()
    for ext in (suffix, CTYPE_EXT.get(ctype), sniff(head, kind)):
        if ext in allowed:
            return ext
    return allowed[0]


def verify(path: Path, kind: str) -> str:
    """받은 파일 검증 → 짧은 설명. 실패하면 FetchError."""
    if path.stat().st_size == 0:
        raise FetchError("빈 파일")
    if kind == "image":
        from PIL import Image
        try:
            with Image.open(path) as im:
                size, fmt = im.size, im.format
                im.verify()
        except Exception as e:  # noqa: BLE001 — Pillow 는 여러 예외를 낸다
            raise FetchError(f"이미지가 아님/손상: {e}") from e
        return f"{fmt} {size[0]}x{size[1]}"
    try:
        info = probe(path)
    except MomoError as e:
        raise FetchError(f"ffprobe 검증 실패: {e}") from e
    if kind == "clip" and not info.has_video:
        raise FetchError("영상 스트림 없음")
    if kind == "audio" and not info.has_audio:
        raise FetchError("음성 스트림 없음")
    return f"{info.duration:.2f}초" + (f" {info.width}x{info.height}" if info.has_video else "")


def download_once(url: str, slot: Slot) -> tuple[Path, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "momo-fetch/1.0"})
    slot.dest.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".dl_", dir=str(slot.dest))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    ctype = resp.headers.get_content_type() if resp.headers else ""
                    want = resp.headers.get("Content-Length") if resp.headers else None
                    shutil.copyfileobj(resp, f, 1 << 20)
            except urllib.error.HTTPError as e:
                raise FetchError(f"HTTP {e.code} {e.reason}", retry=e.code >= 500 or e.code in (408, 429)) from e
            except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
                reason = getattr(e, "reason", None)
                final = isinstance(reason, FileNotFoundError) or "Tunnel connection failed" in str(reason or e)
                raise FetchError(f"연결 실패: {reason or e!r}", retry=not final) from e
        got = tmp.stat().st_size
        if want and want.isdigit() and int(want) != got:
            raise FetchError(f"불완전한 다운로드 ({got}/{want} 바이트)")
        with open(tmp, "rb") as f:
            head = f.read(32)
        ext = pick_ext(url, ctype, head, slot.kind)
        desc = verify(tmp, slot.kind)
        final = slot.dest / f"{slot.stem}{ext}"
        for other in KIND_EXTS[slot.kind]:  # 확장자가 다른 옛 파일은 build 가 먼저 집을 수 있어 치운다
            old = slot.dest / f"{slot.stem}{other}"
            if other != ext and old.exists():
                old.unlink()
        os.replace(tmp, final)
        return final, desc
    finally:
        if tmp.exists():
            tmp.unlink()


def download(url: str, slot: Slot) -> tuple[Path, str]:
    scheme = urlparse(url).scheme.lower()
    if scheme not in ("http", "https", "file"):
        raise FetchError(f"지원하지 않는 URL 형식: {scheme or '(없음)'}", retry=False)
    for attempt in range(1, RETRIES + 1):
        try:
            return download_once(url, slot)
        except FetchError as e:
            if not e.retry or attempt == RETRIES:
                raise FetchError(f"{e} ({attempt}회 시도)", retry=False) from e
            time.sleep(BACKOFF * 2 ** (attempt - 1))
    raise AssertionError("unreachable")


def rel(paths, p: Path) -> str:
    try:
        return str(p.relative_to(paths.root))
    except ValueError:
        return str(p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GenRec URL → 규칙 경로로 내려받기",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    ap.add_argument("--ep")
    ap.add_argument("--library", action="store_true", help="library.json 항목도")
    ap.add_argument("--force", action="store_true", help="이미 있어도 다시 받기")
    args = ap.parse_args(argv)
    if not args.ep and not args.library:
        raise MomoError("--ep 또는 --library 가 필요함")
    paths = get_paths(args)
    cfg = load_config(paths)
    slots: list[Slot] = []
    if args.library:
        slots += library_slots(paths, cfg, load_library(paths))
    if args.ep:
        slots += episode_slots(paths, cfg, load_manifest(paths, check_ep(args.ep)))
    todo = [s for s in slots if s.status in FETCHABLE]
    if any(s.kind != "image" for s in todo) and not which("ffprobe"):
        raise MomoError("ffprobe 가 없어 영상·음성을 검증할 수 없음 — ffmpeg 설치 필요")

    counts = {"받음": 0, "건너뜀": 0}
    fails: list[tuple[Slot, str, str]] = []
    sources_cache: dict[Path, dict] = {}
    print(f"에셋 내려받기 — {args.ep or ''}{' + 라이브러리' if args.library else ''} ({len(todo)}개 대상)")
    for s in todo:
        url = s.rec.get("url")
        src_file = s.dest / SOURCES
        sources = sources_cache.setdefault(src_file, load_json(src_file, default={}))
        existing = find_media(s.dest, s.stem, KIND_EXTS[s.kind])
        if not url:
            if existing:
                counts["건너뜀"] += 1
                print(f"  = {s.key}: URL 없음, 로컬 파일 사용 ({rel(paths, existing)})")
            else:
                fails.append((s, "-", f"{s.status} 인데 URL 기록이 없음"))
            continue
        known = (sources.get(existing.name) or {}).get("url") if existing else None
        if existing and not args.force and known in (None, url):
            counts["건너뜀"] += 1
            continue
        why = "다시 받음" if args.force and existing else ("URL 바뀜" if existing else "")
        try:
            final, desc = download(url, s)
        except FetchError as e:
            fails.append((s, url, str(e)))
            print(f"  {'△' if s.group in REF_GROUPS else '✖'} {s.key}: {e}")
            continue
        sources[final.name] = {"url": url, "job_id": s.rec.get("job_id")}
        save_json(src_file, sources)
        counts["받음"] += 1
        print(f"  ↓ {s.key} → {rel(paths, final)} ({desc}{', ' + why if why else ''})")
    hard = [f for f in fails if f[0].group not in REF_GROUPS]
    waiting = sum(1 for s in slots if s.status not in FETCHABLE)
    print(f"\n결과: 받음 {counts['받음']} · 건너뜀(이미 있음) {counts['건너뜀']} · 실패 {len(hard)}"
          + (f" · 참고용 실패 {len(fails) - len(hard)} (조립과 무관, 경고만)" if len(fails) > len(hard) else "")
          + f" · 아직 생성/승인 전 {waiting}")
    if fails:
        print("\n실패 목록:")
        print("| 항목 | 경로 | URL | 원인 |")
        print("|---|---|---|---|")
        for slot, url, err in fails:
            ref = " (참고용)" if slot.group in REF_GROUPS else ""
            print(f"| {slot.key}{ref} | {rel(paths, slot.dest / slot.stem)}.* | {url} | {err} |")
        print("\n재시도: 같은 명령을 다시 실행 (받은 파일은 건너뜀). URL 이 만료됐으면 Higgsfield 에서 결과 URL 을 다시 받아 "
              "hf_jobs.py record ... --url 로 갱신")
    if hard:
        return 1
    print("✔ 완료" + (" (참고용 파일 일부 못 받음)" if fails else ""))
    return 0


if __name__ == "__main__":
    main_wrapper(main)
