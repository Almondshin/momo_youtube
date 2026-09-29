#!/usr/bin/env python3
"""YouTube OAuth 1회 설정: 브라우저 로그인 → refresh token 을 .secrets/youtube_<lang>.json 에 저장.

사용 예
  python youtube_auth.py --lang en --client-secrets client_secret.json
  python youtube_auth.py --lang ko --client-secrets client_secret.json --port 8090 --no-browser
  YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... python youtube_auth.py --lang en    # client 를 env 로
  python youtube_auth.py --lang en --client-secrets client_secret.json --print-token   # 토큰을 화면에 (주의)

- OAuth 클라이언트 유형은 '데스크톱 앱'. 스코프: youtube.upload + youtube (재생목록 추가용).
- EN/KO 를 다른 채널에 올리면 언어마다 따로 실행하고, 로그인 화면에서 그 채널(브랜드 계정)을 고른다.
- 원격 서버: --no-browser 로 URL 을 받고, 내 PC 에서 `ssh -L 8080:localhost:8080 <서버>` 로 포트를 연결한 뒤 연다.
- 저장 후 GitHub Secrets 에 넣을 이름을 안내한다. 토큰 값은 --print-token 일 때만 출력.
자세한 절차: docs/YOUTUBE_SETUP.md
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib import youtube as yt  # noqa: E402
from momolib.common import (MomoError, add_root_arg, check_lang, get_paths, load_json, main_wrapper,  # noqa: E402
                            save_json)


def client_config(path: str | None) -> dict:
    """--client-secrets JSON({"installed": ...}) 또는 env YOUTUBE_CLIENT_ID/SECRET → InstalledAppFlow 설정."""
    if path:
        data = load_json(Path(path))
        conf = data.get("installed") or data.get("web") or {}
        if not (conf.get("client_id") and conf.get("client_secret")):
            raise MomoError(f"{path}: OAuth 클라이언트 JSON 이 아님 — Google Cloud Console → API 및 서비스 → "
                            f"사용자 인증 정보 → OAuth 클라이언트 ID(데스크톱 앱) → JSON 다운로드 ({yt.SETUP_DOC})")
        if "installed" not in data:
            print("△ '웹 애플리케이션' 유형 클라이언트 — '데스크톱 앱' 권장 (웹 유형은 redirect URI 등록 필요)")
        return data
    cid = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
    secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
    if not (cid and secret):
        raise MomoError("OAuth 클라이언트 정보 없음 — --client-secrets client_secret.json 을 주거나 "
                        f"env YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET 설정 ({yt.SETUP_DOC})")
    return {"installed": {"client_id": cid, "client_secret": secret, "auth_uri": yt.AUTH_URI,
                          "token_uri": yt.TOKEN_URI, "redirect_uris": ["http://localhost"]}}


def run_flow(conf: dict, port: int, open_browser: bool):
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise MomoError(f"google-auth-oauthlib 없음 — pip install -r requirements.txt ({e})") from e
    # 사용자가 일부 권한만 허용해도 oauthlib 가 예외를 던지지 않게 → 아래에서 직접 확인
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    flow = InstalledAppFlow.from_client_config(conf, scopes=yt.SCOPES)
    try:
        return flow.run_local_server(
            host="localhost", port=port, open_browser=open_browser,
            authorization_prompt_message="\n브라우저에서 아래 URL 을 열고, 업로드할 채널의 Google 계정으로 로그인해 "
                                         "모든 권한을 허용해줘:\n{url}\n",
            success_message="인증 완료 — 이 창을 닫고 터미널로 돌아가세요. (momo youtube_auth)",
            access_type="offline", prompt="consent")
    except OSError as e:
        raise MomoError(f"로컬 포트 {port} 를 열 수 없음 — --port 로 다른 포트 지정.\n  원문: {e}") from e
    except Exception as e:  # noqa: BLE001 — oauthlib 오류 원문 그대로
        raise MomoError(f"OAuth 인증 실패 (거부했거나 client 설정 오류).\n  원문: {type(e).__name__}: {e}") from e


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="YouTube 업로드용 refresh token 발급",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    ap.add_argument("--lang", required=True, help="en | ko — 이 언어 영상을 올릴 채널")
    ap.add_argument("--client-secrets", help="OAuth 클라이언트 JSON (없으면 env YOUTUBE_CLIENT_ID/SECRET)")
    ap.add_argument("--port", type=int, default=8080, help="로컬 리디렉션 포트 (기본 8080, 0 = 빈 포트)")
    ap.add_argument("--no-browser", action="store_true", help="브라우저를 열지 않고 URL 만 출력")
    ap.add_argument("--print-token", action="store_true", help="refresh token 값을 화면에 출력 (주의)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # 파이프로 받아도 인증 URL 이 바로 보이게
        sys.stdout.reconfigure(line_buffering=True)
    paths = get_paths(args)
    lang = check_lang(args.lang)
    conf = client_config(args.client_secrets)
    client = conf.get("installed") or conf.get("web")

    creds = run_flow(conf, args.port, not args.no_browser)
    if not creds.refresh_token:
        raise MomoError("refresh token 을 받지 못함 — Google 계정 → 보안 → 타사 앱 액세스에서 이 앱 권한을 "
                        "삭제한 뒤 다시 실행")
    granted = set(getattr(creds, "granted_scopes", None) or creds.scopes or yt.SCOPES)
    if yt.SCOPES[0] not in granted:
        raise MomoError("youtube.upload 권한이 허용되지 않음 — 동의 화면에서 모든 항목을 체크하고 다시 실행")
    if yt.SCOPES[1] not in granted:
        print("△ youtube 권한이 빠짐 — 업로드는 되지만 재생목록 추가는 실패한다")

    data = {"client_id": client["client_id"], "client_secret": client["client_secret"],
            "refresh_token": creds.refresh_token, "token_uri": yt.TOKEN_URI, "scopes": sorted(granted),
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "channel": None}
    try:
        service = yt.build_service(data)
        items = yt.execute(service.channels().list(part="snippet", mine=True), "채널 확인").get("items") or []
        if items:
            data["channel"] = {"id": items[0]["id"], "title": items[0]["snippet"]["title"]}
        else:
            print("△ 이 계정에 YouTube 채널이 없음 — 채널을 만들거나, 로그인 때 채널(브랜드 계정)을 골라 다시 실행")
    except Exception as e:  # noqa: BLE001 — 확인 실패여도 토큰은 저장
        print("△ 채널 확인 실패 (토큰은 저장함): " + (str(e) if isinstance(e, MomoError) else
                                                  yt.describe_error(e, "channels.list")))

    file = yt.secret_file(paths, lang)
    file.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(file.parent, 0o700)
    existed = file.exists()
    save_json(file, data)
    os.chmod(file, 0o600)

    var = f"YOUTUBE_REFRESH_TOKEN_{lang.upper()}"
    ch = data["channel"]
    print(f"\n✔ 저장{' (덮어씀)' if existed else ''}: {file} (권한 600, git 제외)")
    if ch:
        print(f"  채널: {ch['title']} ({ch['id']}) — [{lang}] 영상은 이 채널로 올라간다")
    print("\nGitHub Actions 에서 쓰려면 저장소 Settings → Secrets and variables → Actions 에 등록:")
    print("  YOUTUBE_CLIENT_ID        ← 파일의 client_id")
    print("  YOUTUBE_CLIENT_SECRET    ← 파일의 client_secret")
    print(f"  {var:<24} ← 파일의 refresh_token  (EN/KO 가 같은 채널이면 YOUTUBE_REFRESH_TOKEN 하나로도 됨)")
    print("gh CLI 로 값을 화면에 띄우지 않고 등록하는 예:")
    for key, name in (("refresh_token", var), ("client_id", "YOUTUBE_CLIENT_ID"),
                      ("client_secret", "YOUTUBE_CLIENT_SECRET")):
        print(f"  python3 -c \"import json;print(json.load(open('{file}'))['{key}'],end='')\" | gh secret set {name}")
    print(f"※ OAuth 동의 화면이 '테스트' 상태면 refresh token 이 7일 뒤 만료된다 → '프로덕션으로 게시' ({yt.SETUP_DOC})")
    if args.print_token:
        print(f"\n⚠ refresh token (화면·로그에 남지 않게 주의):\n{creds.refresh_token}")
    return 0


if __name__ == "__main__":
    main_wrapper(main)
