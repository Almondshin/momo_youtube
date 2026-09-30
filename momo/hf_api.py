#!/usr/bin/env python3
"""Higgsfield API (공식 SDK higgsfield-client) — 키 확인과 Seedance 2.5 예제.

키는 저장소 루트의 .env.local (git 제외) 에 `HF_KEY=키ID:시크릿` 으로 둔다. 이 스크립트는 키를 실행 시점에만 읽어
환경변수로 넘기고, 값은 절대 출력하지 않는다. 채팅·커밋·로그에 키를 남기지 말 것.

사용 예
  python momo/hf_api.py check     # 인증만 확인 (없는 작업 ID 조회 → 404 = 키 정상, 401 = 키 틀림) — 과금 없음
  python momo/hf_api.py smoke     # 예제: bytedance/seedance-2.5/text-to-video 5초 720p 16:9 — 과금됨
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import MOMO_DIR, MomoError, add_root_arg, main_wrapper  # noqa: E402

ENV_FILE = MOMO_DIR.parent / ".env.local"
SMOKE_MODEL = "bytedance/seedance-2.5/text-to-video"
SMOKE_ARGS = {"prompt": "A cinematic scene at sunset", "duration": 5, "resolution": "720p", "aspect_ratio": "16:9"}


def load_key(env_file: Path = ENV_FILE) -> None:
    """HF_KEY (or HF_API_KEY + HF_API_SECRET) into os.environ from .env.local unless already set. Never prints it."""
    if os.getenv("HF_KEY") or (os.getenv("HF_API_KEY") and os.getenv("HF_API_SECRET")):
        return
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.strip().partition("=")
            if sep and k.strip() in ("HF_KEY", "HF_API_KEY", "HF_API_SECRET") and not k.strip().startswith("#"):
                v = v.strip().strip("'\"")
                if v:
                    os.environ[k.strip()] = v
    if not os.getenv("HF_KEY") and not (os.getenv("HF_API_KEY") and os.getenv("HF_API_SECRET")):
        raise MomoError(f"Higgsfield API 키 없음 — {env_file.name} 에 HF_KEY=키ID:시크릿 을 직접 넣을 것 "
                        f"(채팅에 붙여넣지 말 것)")


def _client():
    load_key()
    try:
        import higgsfield_client as hf
    except ImportError as e:
        raise MomoError("higgsfield-client 미설치 — pip install -r momo/requirements.txt") from e
    return hf


def _http_code(exc: BaseException) -> int | None:
    return getattr(getattr(exc.__cause__, "response", None), "status_code", None)


def cmd_check(args) -> int:
    hf = _client()
    try:
        hf.status(str(uuid.uuid4()))  # an id that cannot exist: auth is checked first, nothing is generated
    except hf.HiggsfieldClientError as e:
        code = _http_code(e)
        if code == 404:
            print("✔ Higgsfield API 키 정상 (인증 통과 — 없는 작업 조회라 404, 과금 없음)")
            return 0
        if code in (401, 403):
            raise MomoError(f"Higgsfield API 키가 거부됨 (HTTP {code}) — .env.local 의 HF_KEY 확인") from e
        raise MomoError(f"Higgsfield API 확인 실패 (HTTP {code}): {e}") from e
    print("✔ Higgsfield API 응답 (인증 통과)")
    return 0


def media_url(result: dict) -> str | None:
    """First generated media URL in a completed result (video/videos/images/output…)."""
    stack = [result]
    while stack:
        cur = stack.pop(0)
        if isinstance(cur, dict):
            u = cur.get("url")
            if isinstance(u, str) and u.startswith("http"):
                return u
            stack.extend(v for k, v in cur.items() if k != "url")
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


def run_request(model: str, arguments: dict) -> tuple[str, dict]:
    """Submit and wait. → (request_id, result). Raises MomoError unless the request completed."""
    hf = _client()
    rid: list[str] = []
    try:
        result = hf.subscribe(model, arguments=arguments, on_enqueue=rid.append)
    except hf.HiggsfieldClientError as e:
        raise MomoError(f"Higgsfield API 요청 실패 (HTTP {_http_code(e)}): {e}") from e
    status = str(result.get("status") or "").lower()
    request_id = rid[0] if rid else str(result.get("request_id") or "?")
    if status != "completed":
        why = {"failed": "생성 실패", "nsfw": "검열(부적절 판정)", "canceled": "취소됨", "cancelled": "취소됨"}
        raise MomoError(f"Higgsfield API 작업 {request_id}: {why.get(status, '완료되지 않음')} (status={status or '?'}) "
                        f"— 결과 없음, 성공 아님")
    return request_id, result


def cmd_smoke(args) -> int:
    print(f"▶ {SMOKE_MODEL} {SMOKE_ARGS} — 과금되는 생성 1건")
    rid, result = run_request(SMOKE_MODEL, dict(SMOKE_ARGS))
    url = media_url(result)
    if not url:
        raise MomoError(f"작업 {rid}: completed 인데 결과 URL 이 없음 — 응답 키 {sorted(result)}")
    print(f"✔ 완료 (request_id {rid})\n  video: {url}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Higgsfield API (SDK) 키 확인·예제",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="인증만 확인 (과금 없음)")
    sub.add_parser("smoke", help="Seedance 2.5 text-to-video 5초 예제 (과금)")
    args = ap.parse_args(argv)
    return {"check": cmd_check, "smoke": cmd_smoke}[args.cmd](args)


if __name__ == "__main__":
    main_wrapper(main)
