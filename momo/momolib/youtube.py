"""YouTube Data API v3 공용 헬퍼 — upload.py / youtube_auth.py / doctor.py 가 쓴다.

- 자격증명: env YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET + YOUTUBE_REFRESH_TOKEN_<LANG>
  → YOUTUBE_REFRESH_TOKEN → <root>/.secrets/youtube_<lang>.json (youtube_auth.py 가 만든 파일).
  어떤 값도 출력하지 않는다 (메시지에는 변수 이름·파일 경로만).
- google 라이브러리는 실제로 API 를 부를 때만 import 한다 (--dry-run·테스트는 자격증명·네트워크 없이 동작).
- 5xx·네트워크 오류는 지수 백오프로 재시도, 그 외 HTTP 오류는 원문을 담아 MomoError.
"""
from __future__ import annotations

import http.client
import json
import os
import random
import time
from pathlib import Path
from typing import Any, Callable

from .common import MomoError, Paths, check_lang, load_json

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SETUP_DOC = "docs/YOUTUBE_SETUP.md"
CHUNK_SIZE = 8 * 1024 * 1024
MAX_RETRIES = 8
RETRY_STATUSES = {500, 502, 503, 504}
PRIVACY = ("private", "unlisted", "public")

# 테스트가 바꿔 끼운다 (재시도 대기 없이)
_sleep: Callable[[float], None] = time.sleep


def video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


# ---------------------------------------------------------------- 메타데이터 검증

def check_upload_meta(title: str, description: str, tags: list[str], label: str) -> list[str]:
    """episode.validate_manifest 와 같은 규칙 + 빈 제목. 오류 문장 목록 (비어 있으면 통과)."""
    errs = []
    if not title.strip():
        errs.append(f"{label} 제목이 비어 있음")
    if len(title) > 100:
        errs.append(f"{label} 제목 100자 초과 ({len(title)})")
    if "<" in title or ">" in title:
        errs.append(f"{label} 제목에 < > 사용 불가 (YouTube 거부)")
    if len(description.encode("utf-8")) > 5000:
        errs.append(f"{label} 설명 5000바이트 초과 ({len(description.encode('utf-8'))})")
    if "<" in description or ">" in description:
        errs.append(f"{label} 설명에 < > 사용 불가 (YouTube 거부)")
    tag_len = sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1)
    if tag_len > 500:
        errs.append(f"{label} 태그 총 길이 {tag_len}자 > 500")
    bad = [t for t in tags if "<" in t or ">" in t]
    if bad:
        errs.append(f"{label} 태그에 < > 사용 불가: {bad}")
    return errs


# ---------------------------------------------------------------- 자격증명

def secret_file(paths: Paths, lang: str) -> Path:
    return paths.secrets / f"youtube_{check_lang(lang)}.json"


def resolve_credentials(paths: Paths, lang: str, env: dict | None = None) -> tuple[dict, str]:
    """({client_id, client_secret, refresh_token}, 출처 설명). 없으면 이름만 담은 MomoError."""
    env = os.environ if env is None else env
    token_vars = (f"YOUTUBE_REFRESH_TOKEN_{lang.upper()}", "YOUTUBE_REFRESH_TOKEN")
    file = secret_file(paths, lang)
    saved = load_json(file) if file.exists() else {}
    env_client = {"client_id": env.get("YOUTUBE_CLIENT_ID", "").strip(),
                  "client_secret": env.get("YOUTUBE_CLIENT_SECRET", "").strip()}
    file_client = {k: str(saved.get(k) or "").strip() for k in ("client_id", "client_secret")}

    token, source, client = "", "", env_client
    for var in token_vars:
        if env.get(var, "").strip():
            token, source = env[var].strip(), f"환경변수 {var}"
            break
    if not token and saved.get("refresh_token"):
        # 파일의 refresh token 은 같은 파일의 client 로 발급된 것 → 파일 client 우선
        token, source = str(saved["refresh_token"]).strip(), str(file)
        client = file_client if all(file_client.values()) else env_client
    if not all(client.values()):
        client = {k: client[k] or env_client[k] or file_client[k] for k in client}

    missing = [n for n, v in (("YOUTUBE_CLIENT_ID", client["client_id"]),
                              ("YOUTUBE_CLIENT_SECRET", client["client_secret"])) if not v]
    if not token:
        missing.append(f"{token_vars[0]} (또는 {token_vars[1]})")
    if missing:
        raise MomoError(
            f"YouTube 자격증명 없음 [{lang}] — 없는 항목: {', '.join(missing)}\n"
            f"  · GitHub Actions: 저장소 Settings → Secrets and variables → Actions 에 위 이름으로 등록\n"
            f"  · 로컬: python youtube_auth.py --lang {lang} --client-secrets client_secret.json"
            f" → {file} 생성\n"
            f"  자세한 절차: {SETUP_DOC}")
    return {**client, "refresh_token": token}, source


def credentials_source(paths: Paths, lang: str) -> str | None:
    """doctor 용: 자격증명이 어디서 오는지 (값 없이). 없으면 None."""
    try:
        return resolve_credentials(paths, lang)[1]
    except MomoError:
        return None


def build_service(info: dict) -> Any:
    """refresh token → 액세스 토큰 → youtube v3 서비스 (discovery 문서는 라이브러리 내장본 사용)."""
    try:
        import google_auth_httplib2
        import httplib2
        from google.auth.exceptions import RefreshError, TransportError
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as e:
        raise MomoError(f"Google API 라이브러리 없음 — pip install -r requirements.txt ({e})") from e
    creds = Credentials(None, refresh_token=info["refresh_token"], client_id=info["client_id"],
                        client_secret=info["client_secret"], token_uri=TOKEN_URI)
    try:
        creds.refresh(google_auth_httplib2.Request(httplib2.Http(timeout=60)))
    except RefreshError as e:
        raise MomoError(
            f"refresh token 으로 액세스 토큰을 받지 못함 (만료·취소, 또는 client 와 짝이 안 맞음).\n"
            f"  OAuth 동의 화면이 '테스트' 상태면 refresh token 은 7일 뒤 만료된다 → '프로덕션'으로 게시 후\n"
            f"  youtube_auth.py 로 다시 발급 ({SETUP_DOC}).\n  원문: {e}") from e
    except TransportError as e:
        raise MomoError(f"oauth2.googleapis.com 연결 실패 — 네트워크 확인.\n  원문: {e}") from e
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------- 오류 분류

def http_status(exc: BaseException) -> int | None:
    """googleapiclient HttpError(ResumableUploadError 포함) 의 HTTP 상태."""
    status = getattr(getattr(exc, "resp", None), "status", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def error_reason(exc: BaseException) -> tuple[str, str]:
    """HttpError 본문의 (reason, message). 파싱 못 하면 ("", "")."""
    content = getattr(exc, "content", b"") or b""
    try:
        err = json.loads(content.decode("utf-8") if isinstance(content, bytes) else content).get("error", {})
    except (ValueError, AttributeError):
        return "", ""
    if not isinstance(err, dict):
        return "", str(err)
    errors = err.get("errors") or [{}]
    return str(errors[0].get("reason") or err.get("status") or ""), str(err.get("message") or "")


def is_retryable(exc: BaseException) -> bool:
    status = http_status(exc)
    if status is not None:
        return status in RETRY_STATUSES
    if isinstance(exc, (FileNotFoundError, PermissionError, IsADirectoryError)):
        return False
    if isinstance(exc, (OSError, http.client.HTTPException)):  # 연결 끊김·타임아웃·SSL
        return True
    try:
        import httplib2
        return isinstance(exc, httplib2.HttpLib2Error)
    except ImportError:
        return False


HINTS = {
    "quotaExceeded": "YouTube Data API 일일 할당량 초과 — 태평양 시간 자정에 초기화된다.",
    "uploadLimitExceeded": "채널 업로드 횟수 한도 초과 — 시간이 지나면 풀린다.",
    "insufficientPermissions": "토큰 권한 부족 — youtube_auth.py 로 다시 발급 (youtube.upload + youtube 스코프).",
    "youtubeSignupRequired": "이 Google 계정에 YouTube 채널이 없음 — 채널을 먼저 만들 것.",
    "invalidPublishAt": "publishAt 이 잘못됨 — 미래 시각이어야 하고 privacy 는 private 이어야 한다.",
    "authError": "인증 실패 — refresh token 을 다시 발급할 것.",
}


def describe_error(exc: BaseException, what: str) -> str:
    status = http_status(exc)
    reason, message = error_reason(exc)
    head = f"{what} 실패" + (f" (HTTP {status}{' ' + reason if reason else ''})" if status else "")
    hint = HINTS.get(reason) or ("인증 실패 — refresh token 을 다시 발급할 것." if status == 401 else "")
    return "\n  ".join(x for x in (head, hint, f"원문: {message or exc}") if x)


# ---------------------------------------------------------------- 요청 실행

def _backoff(attempt: int, exc: BaseException, what: str, max_retries: int) -> None:
    if attempt > max_retries:
        raise MomoError(f"{what}: 재시도 {max_retries}회 모두 실패.\n  원문: {exc}") from exc
    delay = min(64.0, 2.0 ** attempt) * (0.5 + random.random() / 2)
    status = http_status(exc)
    label = f"HTTP {status}" if status else type(exc).__name__
    print(f"  △ 일시 오류 ({label}) — {delay:.1f}초 후 재시도 ({attempt}/{max_retries})", flush=True)
    _sleep(delay)


def execute(request: Any, what: str, max_retries: int = 5) -> dict:
    """일반 요청 execute() + 일시 오류 재시도."""
    attempt = 0
    while True:
        try:
            return request.execute()
        except Exception as e:  # noqa: BLE001 — 분류 후 재발생
            if not is_retryable(e):
                raise
            attempt += 1
            _backoff(attempt, e, what, max_retries)


def resumable_upload(request: Any, what: str, max_retries: int = MAX_RETRIES,
                     on_progress: Callable[[int, int], None] | None = None) -> dict:
    """videos.insert 같은 resumable 요청을 청크 단위로 끝까지 올린다. 진행이 있으면 재시도 횟수 초기화."""
    attempt = 0
    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
        except Exception as e:  # noqa: BLE001
            if not is_retryable(e):
                if http_status(e) is not None:
                    raise MomoError(describe_error(e, what)) from e
                raise
            attempt += 1
            _backoff(attempt, e, what, max_retries)
            continue
        if status is not None:
            attempt = 0
            if on_progress:
                on_progress(int(status.resumable_progress), int(status.total_size or 0))
    if not isinstance(response, dict) or "id" not in response:
        raise MomoError(f"{what}: 응답에 id 가 없음 — 원문: {response!r}")
    return response


def media_file(path: Path, mimetype: str, resumable: bool = True) -> Any:
    from googleapiclient.http import MediaFileUpload
    return MediaFileUpload(str(path), mimetype=mimetype, chunksize=CHUNK_SIZE, resumable=resumable)
