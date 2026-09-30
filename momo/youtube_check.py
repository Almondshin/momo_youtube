#!/usr/bin/env python3
"""YouTube connection check — no build, no upload, no quota beyond one channels.list per language.

Resolves the same credentials upload.py would use, refreshes an access token, and prints which channel it
reaches (title, id, audience default, long-upload status). Exit 1 if any language fails.

사용 예
  python youtube_check.py                  # en + ko
  python youtube_check.py --lang en
GitHub Actions: momo-youtube-check (workflow_dispatch) runs this with the repository Secrets.
Secret values are never printed — only variable names, channel title and id.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib import youtube as yt  # noqa: E402
from momolib.common import LANGS, MomoError, add_root_arg, check_lang, get_paths, main_wrapper  # noqa: E402

SCOPE_REASONS = {"insufficientPermissions", "ACCESS_TOKEN_SCOPE_INSUFFICIENT", "PERMISSION_DENIED"}


def check_lang_channel(paths, lang: str) -> dict:
    """{lang, source, id, title, made_for_kids, long_uploads} for one language (MomoError on failure)."""
    info, source = yt.resolve_credentials(paths, lang)
    service = yt.build_service(info)
    try:
        items = yt.execute(service.channels().list(part="snippet,status", mine=True), "채널 확인").get("items") or []
    except MomoError:
        raise
    except Exception as e:  # noqa: BLE001 — HttpError (API disabled, missing scope, …) → readable message
        reason, message = yt.error_reason(e)
        if yt.http_status(e) == 403 and (reason in SCOPE_REASONS or "insufficient" in message.lower()):
            # the token refreshed fine but was granted youtube.upload only: uploads work, channel lookup does not
            return {"lang": lang, "source": source, "upload_only": True}
        raise MomoError(yt.describe_error(e, "channels.list")) from e
    if not items:
        raise MomoError("이 계정에 YouTube 채널이 없음 — 로그인 때 모모 채널(브랜드 계정)을 골랐는지 확인하고 "
                        "refresh token 을 다시 발급")
    ch = items[0]
    st = ch.get("status") or {}
    return {"lang": lang, "source": source, "id": ch.get("id"), "title": (ch.get("snippet") or {}).get("title"),
            "made_for_kids": st.get("madeForKids"), "long_uploads": st.get("longUploadsStatus")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="YouTube 연결 점검 (업로드 없음)",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    ap.add_argument("--lang", default="all", help="en | ko | all (기본)")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    langs = list(LANGS) if args.lang == "all" else [check_lang(args.lang)]
    ok, seen = True, {}
    for lang in langs:
        try:
            r = check_lang_channel(paths, lang)
        except MomoError as e:
            ok = False
            print(f"✖ {lang}: {e}")
            continue
        if r.get("upload_only"):
            print(f"△ {lang}: 토큰 정상 · 자격증명 {r['source']} — 단, youtube.upload 권한만 있어 채널 이름 확인과 "
                  "재생목록 추가는 안 됨 (업로드·썸네일은 가능). youtube 권한까지 넣어 다시 발급 권장")
            continue
        seen[lang] = r["id"]
        kids = {True: "아동용", False: "아동용 아님 — Studio 에서 채널 기본값을 아동용으로"}.get(r["made_for_kids"], "미설정")
        print(f"✔ {lang}: 채널 「{r['title']}」 ({r['id']}) · 자격증명 {r['source']} · 채널 기본 시청자층 {kids}"
              f" · 15분 초과 업로드 {r['long_uploads'] or '?'}")
    if len(set(seen.values())) > 1:
        print("△ EN 과 KO 가 서로 다른 채널로 연결됨 — 의도한 것이 아니면 토큰을 확인")
    elif len(seen) > 1:
        print("= EN·KO 모두 같은 채널")
    return 0 if ok else 1


if __name__ == "__main__":
    main_wrapper(main)
