#!/usr/bin/env python3
"""Higgsfield API (공식 SDK higgsfield-client) — 키 확인, 클립 생성(run), API 결과 보관(archive).

MCP 는 구독 크레딧, API 는 별도 선불 잔액(USD)이다. API 로는 클립만 만든다 — 이미지는 MCP 그대로
(Nano Banana Pro + Elements 가 API 에 없음). 키는 저장소 루트의 .env.local (git 제외) 에 `HF_KEY=키ID:시크릿`.
실행 시점에만 읽어 환경변수로 넘기고, 값은 절대 출력하지 않는다. 채팅·커밋·로그에 키를 남기지 말 것.

사용 예
  python momo/hf_api.py check                                  # 인증 확인 (과금 없음): 404 정상 · 401 키 틀림 · 403 잔액 부족
  python momo/hf_api.py run --ep ep05 --kind clip --dry-run    # 보낼 payload·estimate 호출만 (네트워크·키 없이)
  python momo/hf_api.py run --ep ep05 --kind clip --cuts c02,c03 --max-usd 5 [--lang en] [--max-parallel 4]
  python momo/hf_api.py archive --ep ep05 [--dry-run]          # API 결과(약 7일 보관) → GitHub release media-ep05
  python momo/hf_api.py forget --ep ep05 --cut c02 [--lang en] --yes   # 접수 불명 제출 지움 (콘솔에서 확인 후)
  python momo/hf_api.py smoke                                  # 예제 Seedance 2.5 text-to-video 5초 — 과금됨

run
- 대상: `hf_jobs.py plan --kind clip` 과 같은 항목 (승인된 이미지가 있는 V 컷의 승인 안 된 클립, 모모 모습 검사 포함).
  모델: wan2_7 → wan/v2.7/image-to-video (립싱크 = audio_url) · seedance_2_0_mini, seedance_2_0 →
  bytedance/seedance-2.0/image-to-video · seedance_2_5 → bytedance/seedance-2.5/image-to-video
  (립싱크면 reference-to-video). 그 밖의 모델(kling…)과 여러 블록 나레이션 립싱크는 MCP 로.
- 입력: 시작·끝 이미지 = episodes/<ep>/images/<cut>.* 를 SDK upload_file 로 올린 주소 (안 되면 manifest 의 이미지 URL).
  립싱크 소리 = audio/refs/<cut>_<lang>.wav (노래 파일 에피소드 — 길이가 지금 컷 구간과 맞아야 함) 또는
  그 컷의 나레이션 블록 1개 (WAV 로 바꿔 올림 — API 업로드는 WAV 만 받는다).
- 제출 전 POST /estimate/<model> (과금 없음) → 예상 USD. 합계가 --max-usd 를 넘으면 아무것도 보내지 않는다 (exit 2).
- 제출: Idempotency-Key = ep/컷/종류/언어/시도 번호(+모델·시작 이미지)로 고정. body 를 먼저 GenRec.api_pending 에
  저장하고 보낸다 — 응답을 못 받았으면 다음 run 이 같은 키·body 로 다시 보내 원래 request_id 를 받는다 (중복 과금 없음).
  접수되면 즉시 job_id "api:<request_id>" 로 기록한다. credits 0 — 구독 credits.spent·캡은 그대로,
  USD 는 history 의 api.usd 와 manifest.credits.api_usd.
- 폴링 2초 → 10초 (지터), 요청마다 --deadline 초. completed → url 기록 + clips/ 에 받기 (fetch_assets 와 같은 검증).
  failed / nsfw / canceled → rejected (성공 아님, 과금 없음). 시간 초과·알 수 없는 상태·연결 오류 → generated(URL 없음)로
  남기고, 다음 run 이 새로 제출하지 않고 이어서 확인한다.
- API 잔액 부족 (HTTP 403) → 재시도 없이 새 제출을 멈추고 (이미 접수된 것은 끝까지 확인), 남은 항목을 MCP plan(JSON)으로
  출력한다 — 기존 구독 플랜으로 이어서 (사용자 지시).
- 종료 코드: 0 모두 완료 · 1 실패·미확인 있음 · 2 --max-usd 초과 (제출 없음) · 3 API 잔액 부족 → MCP 로.

archive
- API 결과 URL 은 7일쯤 뒤 지워질 수 있다. 받은 파일을 release media-<ep> 에 올리고 (gh, 내용 해시 이름) manifest 의
  url 을 그 주소로 바꾼다 → fetch_assets.py 가 계속 복원한다. 원래 주소는 history 의 api.output_url 에 남긴다.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
import threading
import time
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import httpx
except ImportError:  # higgsfield-client brings it; --dry-run works without
    httpx = None

import fetch_assets  # noqa: E402
import hf_jobs  # noqa: E402
import song_track  # noqa: E402
from momolib import release  # noqa: E402
from momolib.common import (AUDIO_EXTS, IMAGE_EXTS, MOMO_DIR, MomoError, Paths, add_root_arg,  # noqa: E402
                            check_ep, check_lang, find_media, get_paths, load_config, load_json, load_manifest,
                            main_wrapper, probe_duration, run, save_json, which)
from momolib.episode import song_track as track_of  # noqa: E402
from momolib.genrec import (FETCHABLE, KIND_EXTS, Slot, add_credits, apply_record, cut_slots,  # noqa: E402
                            episode_cap, episode_slots, now_iso)

ENV_FILE = MOMO_DIR.parent / ".env.local"
BASE_URL = "https://api.higgsfield.ai"
USER_AGENT = "momo-hf-api/1.0"
API_JOB = "api:"                      # GenRec job_id prefix of an API request
IDEM_NS = uuid.uuid5(uuid.NAMESPACE_URL, "momo_youtube/hf_api/idempotency")
RUNNING = ("queued", "in_progress")
FAILED = {"failed": "생성 실패", "nsfw": "검열(nsfw) — 입력이나 결과가 거부됨", "canceled": "취소됨"}
NO_CREDITS = (402, 403)               # 403 = "Insufficient credits" (API errors page); 402 on the agent API
SUBMIT_TRIES = 4                      # ambiguous submit (network / 408 / 429 / 5xx) → resend, same key + body
BUSY_TRIES = 6                        # 400 "Maximum number of concurrent requests" → wait, resend
POLL_FIRST, POLL_MAX, POLL_GROWTH = 2.0, 10.0, 1.5
DEADLINE = 1800.0
MAX_PARALLEL = 20                     # API concurrency of a launch key
SMOKE_MODEL = "bytedance/seedance-2.5/text-to-video"
SMOKE_ARGS = {"prompt": "A cinematic scene at sunset", "duration": 5, "resolution": "720p", "aspect_ratio": "16:9",
              "generate_audio": False}

# job outcomes
READY, HELD, NO_MONEY, DONE = "준비됨", "보류 (제출 안 함)", "API 잔액 부족", "완료"
PREP_FAIL, SUBMIT_FAIL, UNSURE = "준비 실패", "제출 실패", "접수 불명"
RUNNING_LATE, POLL_FAIL, UNKNOWN, NO_URL, RECORD_FAIL = "진행 중", "확인 실패", "알 수 없는 상태", "결과 URL 없음", "기록 실패"
TO_MCP = (HELD, NO_MONEY)


# ---------------------------------------------------------------- key

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


# ---------------------------------------------------------------- HTTP

class ApiError(Exception):
    """A Higgsfield API failure. code None = no HTTP response (network error, timeout)."""

    def __init__(self, code: int | None, detail: str, correlation: str | None = None):
        super().__init__(f"HTTP {code}: {detail}" if code else detail)
        self.code, self.detail, self.correlation = code, detail, correlation

    @property
    def no_credits(self) -> bool:
        return self.code in NO_CREDITS

    @property
    def ambiguous(self) -> bool:
        """A submit that may have been accepted — resend with the same Idempotency-Key and body."""
        return self.code is None or self.code >= 500 or self.code in (408, 409, 429)

    @property
    def busy(self) -> bool:
        return self.code == 400 and "concurrent" in self.detail.lower()


class PollTimeout(Exception):
    pass


def error_detail(r) -> str:
    """The API's own error text ({"detail": …} envelope), verbatim."""
    try:
        data = r.json()
    except ValueError:
        return (r.text or "").strip()[:500] or r.reason_phrase
    if isinstance(data, dict):
        d = data.get("detail") or data.get("details") or data.get("message") or data.get("error")
        if d:
            return d if isinstance(d, str) else json.dumps(d, ensure_ascii=False)[:500]
    return json.dumps(data, ensure_ascii=False)[:500]


def sdk_code(exc: BaseException) -> int | None:
    return getattr(getattr(exc.__cause__, "response", None), "status_code", None)


class HfApi:
    """Higgsfield REST calls: our own httpx requests (Idempotency-Key header, the whole status JSON, our retries and
    deadline — the SDK has none of these) + the SDK's presigned upload_file. Thread-safe.
    Tests pass an httpx.Client on a MockTransport and an uploader from a mocked SDK client."""

    def __init__(self, http, uploader: Callable[[Path], str], sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic):
        self.http, self.uploader, self.sleep, self.clock = http, uploader, sleep, clock
        self._uploads: dict[tuple, str] = {}
        self._ulocks: dict[tuple, threading.Lock] = {}
        self._ulock = threading.Lock()

    def request(self, method: str, path: str, body: dict | None = None,
                headers: dict | None = None) -> tuple[dict, str | None]:
        """→ (JSON object, X-Correlation-ID). Raises ApiError (HTTP ≥ 400 with the API's text, or no response)."""
        try:
            r = self.http.request(method, path, json=body, headers=headers)
        except httpx.HTTPError as e:
            raise ApiError(None, f"연결 실패 — {type(e).__name__}: {e}") from e
        cid = r.headers.get("x-correlation-id")
        if r.status_code >= 400:
            raise ApiError(r.status_code, error_detail(r), cid)
        if not r.content:
            return {}, cid
        try:
            data = r.json()
        except ValueError as e:
            raise ApiError(None, f"JSON 이 아닌 응답 (HTTP {r.status_code}): {r.text[:200]}", cid) from e
        if not isinstance(data, dict):
            raise ApiError(None, f"예상 밖 응답 (HTTP {r.status_code}): {str(data)[:200]}", cid)
        return data, cid

    def status(self, rid: str) -> dict:
        return self.request("GET", f"/requests/{rid}/status")[0]

    def estimate(self, model: str, body: dict) -> tuple[float, float]:
        """POST /estimate/<model> — the price of this exact body, nothing is generated. → (usd, credits)."""
        data, _ = self.request("POST", f"/estimate/{model}", body)
        try:
            return float(data["usd"]), float(data["credits"])
        except (KeyError, TypeError, ValueError) as e:
            raise ApiError(200, f"estimate 응답을 읽을 수 없음: {json.dumps(data)[:200]}") from e

    def submit(self, model: str, body: dict, key: str) -> tuple[str, str | None]:
        """Generation POST with an Idempotency-Key. Ambiguous failures and the concurrency limit are resent with the
        same key and body (the API answers with the original request_id — no second charge). → (request_id, X-Correlation-ID).
        Raises ApiError: no_credits → stop; ambiguous after retries → maybe accepted (keep the pending intent)."""
        tries = busy = 0
        while True:
            try:
                data, cid = self.request("POST", f"/{model}", body, {"Idempotency-Key": key})
            except ApiError as e:
                if e.busy and busy < BUSY_TRIES:
                    busy += 1
                    self.sleep(POLL_MAX + random.uniform(0, 2))
                    continue
                tries += 1
                if e.ambiguous and tries < SUBMIT_TRIES:
                    self.sleep(2.0 ** tries + random.uniform(0, 0.5))
                    continue
                raise
            rid = data.get("request_id")
            if not rid:
                raise ApiError(None, f"request_id 없는 접수 응답: {json.dumps(data)[:200]}", cid)
            return str(rid), cid

    def wait(self, rid: str, deadline: float = DEADLINE) -> dict:
        """Poll the status until it is no longer queued / in_progress: 2 s → 10 s with jitter, network errors and 5xx
        retried until `deadline` s. → the status JSON (status lower-cased, 'cancelled' → 'canceled'); an unknown
        status is returned as is — the caller never counts it as success. Raises ApiError (401, 404 …) or PollTimeout."""
        end = self.clock() + deadline
        delay, last = POLL_FIRST, None
        while True:
            self.sleep(delay + random.uniform(0, 0.5))
            try:
                data = self.status(rid)
            except ApiError as e:
                if not e.ambiguous:
                    raise
                last = str(e)
            else:
                st = str(data.get("status") or "").lower()
                data["status"] = "canceled" if st == "cancelled" else st
                if data["status"] not in RUNNING:
                    return data
            if self.clock() + delay > end:
                raise PollTimeout(f"{deadline:.0f}초 안에 끝나지 않음" + (f" (마지막 오류: {last})" if last else ""))
            delay = min(delay * POLL_GROWTH, POLL_MAX)

    def upload(self, f: Path) -> str:
        """Public URL of a local file (SDK presigned upload: jpeg/png/webp/gif, wav, mp4), once per file per run."""
        st = f.stat()
        key = (str(f.resolve()), st.st_size, st.st_mtime_ns)
        with self._ulock:
            lk = self._ulocks.setdefault(key, threading.Lock())
        with lk:
            if key not in self._uploads:
                try:
                    self._uploads[key] = self.uploader(f)
                except Exception as e:  # noqa: BLE001 — SDK raises HiggsfieldClientError / httpx errors
                    raise ApiError(sdk_code(e), f"업로드 실패 ({f.name}): {type(e).__name__}: {e}") from e
            return self._uploads[key]


def make_api(timeout: float = 90.0) -> HfApi:
    """The real client (key from .env.local, never printed). Tests replace this function."""
    load_key()
    try:
        import higgsfield_client as hf
        from higgsfield_client.auth import get_credential_key
    except ImportError as e:
        raise MomoError("higgsfield-client 미설치 — pip install -r momo/requirements.txt") from e
    sdk = hf.SyncClient(timeout=timeout)
    http = httpx.Client(base_url=BASE_URL, timeout=timeout,
                        headers={"Authorization": f"Key {get_credential_key()}", "Content-Type": "application/json",
                                 "User-Agent": USER_AGENT})
    return HfApi(http, sdk.upload_file)


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


def output_url(result: dict) -> str | None:
    v = (result.get("video") or {}).get("url") if isinstance(result.get("video"), dict) else None
    return v if isinstance(v, str) and v.startswith("http") else media_url(result)


def no_credits_text(e: ApiError) -> str:
    return (f"API 잔액 부족 — 원문: {e} (재시도 안 함). API 잔액은 웹·MCP 구독 크레딧과 별개 "
            f"(console.higgsfield.ai 에서 충전)")


# ---------------------------------------------------------------- MCP → API payload

class Unsupported(Exception):
    """This item cannot go through the API → MCP (subscription)."""


class Blocked(Exception):
    """An input is missing (fetch_assets / song_track refs first)."""


@dataclass(frozen=True)
class ApiModel:
    endpoint: str
    min_s: int
    max_s: int
    resolutions: tuple[str, ...]


WAN27 = ApiModel("wan/v2.7/image-to-video", 2, 15, ("720p", "1080p"))
SD20 = ApiModel("bytedance/seedance-2.0/image-to-video", 4, 15, ("480p", "720p", "1080p", "4k"))
SD25 = ApiModel("bytedance/seedance-2.5/image-to-video", 4, 30, ("480p", "720p", "1080p"))
SD25_REF = ApiModel("bytedance/seedance-2.5/reference-to-video", 4, 30, ("480p", "720p", "1080p"))
API_MODELS = {"wan2_7": WAN27, "seedance_2_0_mini": SD20, "seedance_2_0": SD20, "seedance_2_5": SD25}


def api_payload(mcp_model: str, *, prompt: str, duration: int, resolution: str | None, image: str,
                end_image: str | None = None, audio: str | None = None,
                aspect_ratio: str = "16:9") -> tuple[str, dict, list[str]]:
    """MCP generate_video params → (API model id, JSON body, notes). image / end_image / audio are URLs (or
    placeholders filled after upload). Raises Unsupported when the API has no equivalent."""
    spec = API_MODELS.get(mcp_model)
    if spec is None:
        raise Unsupported(f"{mcp_model}: API 매핑 없음 — MCP 로 (API 는 {', '.join(API_MODELS)})")
    notes: list[str] = []
    seedance = spec is not WAN27
    if mcp_model == "seedance_2_5" and audio:
        if end_image:
            raise Unsupported("seedance_2_5 립싱크(reference-to-video)는 끝 프레임을 받지 않음 — MCP 로")
        spec = SD25_REF
        notes.append("seedance-2.5 reference-to-video: generate_audio=false 에서 audio_urls 로 입이 움직이는지 확인 전")
    elif audio and seedance:
        raise Unsupported(f"{mcp_model}: API image-to-video 에 오디오 레퍼런스가 없음 — MCP 로")
    res = resolution or "720p"
    if res not in spec.resolutions:
        raise Unsupported(f"{spec.endpoint}: 해상도 {res} 없음 ({'/'.join(spec.resolutions)})")
    d = int(duration)
    if d > spec.max_s:
        raise Unsupported(f"{spec.endpoint}: {d}초 — API 최대 {spec.max_s}초")
    if d < spec.min_s:
        notes.append(f"{d}초 → {spec.min_s}초 (API 최소 길이 — 조립은 필요한 만큼만 쓴다)")
        d = spec.min_s
    if mcp_model == "seedance_2_0_mini":
        notes.append("API 에 seedance mini 가 없어 seedance-2.0 으로 (품질·속도·비용이 다를 수 있음)")
    body: dict = {"prompt": prompt, "duration": d, "resolution": res}
    if spec is SD25_REF:
        body.update(image_urls=[image], audio_urls=[audio], aspect_ratio=aspect_ratio)
    else:
        body["image_url"] = image
        if end_image:
            body["end_image_url"] = end_image
        if audio:
            body["audio_url"] = audio
    if seedance:
        body["generate_audio"] = False  # the build lays its own sound (MCP clip_models: generate_audio false)
    return spec.endpoint, body, notes


def idem_key(ep: str, cut: str, kind: str, lang: str | None, attempt: int, model: str, start_job: str | None) -> str:
    """Idempotency-Key, stable per slot + attempt: a resend after a lost response reuses it (no second charge); the
    next attempt (after a recorded result) gets a new one."""
    return str(uuid.uuid5(IDEM_NS, "|".join([ep, cut, kind, lang or "-", str(attempt), model, start_job or "-"])))


def fill(body: dict, urls: dict[str, str]) -> dict:
    """Replace placeholder tokens ("<image>" …) in the body with uploaded URLs."""
    out = {}
    for k, v in body.items():
        if isinstance(v, str):
            out[k] = urls.get(v, v)
        elif isinstance(v, list):
            out[k] = [urls.get(x, x) if isinstance(x, str) else x for x in v]
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------- jobs

@dataclass
class Media:
    """One input of the body: a local file to upload first, a public URL as the fallback."""
    file: Path | None
    url: str | None
    wav: bool = False   # convert to WAV before the upload (the API upload takes audio/wav only)


@dataclass
class Job:
    key: str
    cut: str
    lang: str | None
    mcp_model: str = ""
    api_model: str = ""
    body: dict = field(default_factory=dict)
    media: dict[str, Media] = field(default_factory=dict)
    start_job: str | None = None
    attempt: int = 0
    idem: str = ""
    notes: list[str] = field(default_factory=list)      # plan notes (header, dry-run)
    events: list[str] = field(default_factory=list)     # what happened at run time (report)
    replay: bool = False         # body + key from GenRec.api_pending (a submit whose answer was lost)
    rid: str | None = None       # already accepted → poll only
    final: dict | None = None
    usd: float | None = None
    credits: float | None = None
    charged: float = 0.0         # USD recorded into credits.api_usd by this run
    outcome: str = READY
    detail: str = ""
    file: Path | None = None


def local_media(folder: Path, stem: str, exts, job_id: str | None) -> Path | None:
    """folder/stem.* unless .sources.json says it came from another job (an older attempt)."""
    f = find_media(folder, stem, exts)
    if f is None:
        return None
    src = load_json(folder / fetch_assets.SOURCES, default={}).get(f.name) or {}
    if job_id and src.get("job_id") and src["job_id"] != job_id:
        return None
    return f


def https(url) -> str | None:
    return url if isinstance(url, str) and url.startswith("https://") else None


def image_media(paths: Paths, ep: str, cut: dict) -> Media:
    img = (cut.get("gen") or {}).get("image") or {}
    f = local_media(paths.images(ep), cut["id"], IMAGE_EXTS, img.get("job_id"))
    if f is None and not https(img.get("url")):
        raise Blocked(f"{cut['id']} 승인 이미지의 파일·URL 이 없음 — fetch_assets.py --ep {ep} 먼저")
    return Media(f, https(img.get("url")))


def wav_seconds(f: Path) -> float:
    try:
        with wave.open(str(f), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, EOFError):
        return probe_duration(f)


def audio_media(paths: Paths, cfg: dict, m: dict, s: Slot) -> Media:
    """The lip-sync sound of a clip slot: the vocal-stem slice (finished song) or the cut's one narration block."""
    ep, cid, lang = m["ep"], s.cut["id"], s.lang
    if track_of(m.get("song")) is not None:
        f = paths.ep(ep) / "audio" / "refs" / f"{cid}_{lang}.wav"
        if not f.exists():
            raise Blocked(f"audio/refs/{f.name} 없음 — song_track.py refs --ep {ep} --cuts {cid}")
        win = hf_jobs.track_window(m, cid)
        want = max(win[1] - win[0], song_track.REF_MIN)
        got = wav_seconds(f)
        if abs(got - want) > 0.05:
            raise Blocked(f"audio/refs/{f.name} 길이 {got:.2f}s ≠ 지금 컷 구간 {win[0]:.3f}~{win[1]:.3f}s "
                          f"({want:.2f}s) — song_track.py refs --ep {ep} --cuts {cid} 다시")
        url = https((m["song"].get("refs_urls") or {}).get(f"{cid}_{lang}"))
        if url and f"_{song_track.sha1_file(f)[:8]}." not in url:
            url = None  # the published slice is from another take or window
        return Media(f, url)
    if isinstance(m.get("song"), dict):
        raise Unsupported("챈트 노래 에피소드의 립싱크는 박자에 맞춘 합친 가사(nar_ref)가 필요 — MCP 로")
    jobs = hf_jobs.nar_jobs(cfg, s.cut, lang)
    if len(jobs) != 1:
        raise Unsupported(f"나레이션 블록 {len(jobs)}개 — 합친 나레이션(nar_ref) 립싱크는 MCP 로")
    b = next(x for x in cut_slots(paths, cfg, ep, s.cut) if x.kind == "audio" and x.lang == lang)
    f = local_media(b.dest, b.stem, AUDIO_EXTS, b.rec.get("job_id"))
    url = https(b.rec.get("url"))
    if f is None and url is None:
        raise Blocked(f"{b.key} 파일·URL 이 없음 — fetch_assets.py --ep {ep} 먼저")
    return Media(f, url, wav=f is not None and f.suffix.lower() != ".wav")


def make_job(paths: Paths, cfg: dict, m: dict, s: Slot, params: dict) -> Job:
    ep, cut, rec = m["ep"], s.cut, s.rec
    job = Job(key=s.key, cut=cut["id"], lang=s.lang, mcp_model=params["model"],
              start_job=((cut.get("gen") or {}).get("image") or {}).get("job_id"),
              attempt=int(rec.get("attempts") or 0) + 1)
    pend = rec.get("api_pending")
    if isinstance(pend, dict) and pend.get("attempt") == job.attempt and pend.get("key") and pend.get("body"):
        job.api_model, job.body, job.idem, job.replay = pend["model"], pend["body"], pend["key"], True
        job.notes.append(f"이전 실행에서 응답을 못 받은 제출 ({pend.get('at')}) — 같은 키·body 로 다시 보냄 (중복 과금 없음)")
        return job
    if job.mcp_model not in API_MODELS:
        raise Unsupported(f"{job.mcp_model}: API 매핑 없음 — MCP 로 (API 는 {', '.join(API_MODELS)})")
    job.media["<image>"] = image_media(paths, ep, cut)
    if cut.get("end_frame"):
        other = next(c for c in m["cuts"] if c.get("id") == cut["end_frame"])
        job.media["<end_image>"] = image_media(paths, ep, other)
    if s.lang:  # lip-sync clip (one per language)
        job.media["<audio>"] = audio_media(paths, cfg, m, s)
    job.api_model, job.body, notes = api_payload(
        job.mcp_model, prompt=params["prompt"], duration=params["duration"], resolution=params.get("resolution"),
        image="<image>", end_image="<end_image>" if "<end_image>" in job.media else None,
        audio="<audio>" if "<audio>" in job.media else None, aspect_ratio=params.get("aspect_ratio") or "16:9")
    job.notes += notes
    job.idem = idem_key(ep, cut["id"], "clip", s.lang, job.attempt, job.api_model, job.start_job)
    return job


def build_jobs(paths: Paths, cfg: dict, ep: str, cuts: str | None, lang: str | None) -> dict:
    """The API's work list: hf_jobs plan --kind clip items (api mode) + earlier API requests still without a result."""
    ns = argparse.Namespace(ep=ep, kind="clip", cuts=cuts, lang=lang, all=True)
    plan = hf_jobs.plan_episode(paths, cfg, ns, api=True)
    m = load_manifest(paths, ep)
    slots = {s.key: s for s in episode_slots(paths, cfg, m) if s.kind == "clip"}
    jobs, mcp, blocked, review = [], [], list(plan["blocked"]), []
    for it in plan["items"]:
        s = slots[it["key"]]
        try:
            jobs.append(make_job(paths, cfg, m, s, it["params"]))
        except Unsupported as e:
            mcp.append({"key": s.key, "cut": s.cut["id"], "lang": s.lang, "reason": str(e)})
        except Blocked as e:
            blocked.append(f"{s.key}: {e}")
    for key in plan["awaiting_review"]:
        s = slots.get(key)
        jid = str((s.rec if s else {}).get("job_id") or "")
        if s and jid.startswith(API_JOB) and not s.rec.get("url"):
            jobs.append(Job(key=s.key, cut=s.cut["id"], lang=s.lang, rid=jid[len(API_JOB):],
                            notes=["이전 실행에서 접수된 요청 — 새로 제출하지 않고 결과만 확인"]))
        else:
            review.append(key)
    return {"plan": plan, "jobs": jobs, "mcp": mcp, "blocked": blocked, "review": review}


# ---------------------------------------------------------------- manifest writes

def clip_slot(paths: Paths, cfg: dict, m: dict, cid: str, lang: str | None) -> Slot:
    cut = next((c for c in m.get("cuts") or [] if c.get("id") == cid), None)
    s = next((x for x in cut_slots(paths, cfg, m["ep"], cut) if x.kind == "clip" and x.lang == lang), None) \
        if cut else None
    if s is None:
        raise MomoError(f"{cid} clip{' ' + lang if lang else ''}: manifest 에 클립 자리가 없음 (실행 중에 바뀜?)")
    return s


class Ledger:
    """Every manifest write of a run: reload → change one clip GenRec → atomic save, under one lock (worker threads).
    A crash at any point leaves the pending intents and accepted request ids on disk."""

    def __init__(self, paths: Paths, cfg: dict, ep: str):
        self.paths, self.cfg, self.ep = paths, cfg, ep
        self.lock = threading.RLock()

    def update(self, job: Job, fn: Callable[[dict, dict], object]):
        with self.lock:
            m = load_manifest(self.paths, self.ep)
            rec = clip_slot(self.paths, self.cfg, m, job.cut, job.lang).ensure()
            out = fn(m, rec)
            save_json(self.paths.manifest(self.ep), m)
            return out

    def slot(self, job: Job) -> Slot:
        with self.lock:
            return clip_slot(self.paths, self.cfg, load_manifest(self.paths, self.ep), job.cut, job.lang)


def history_entry(rec: dict, jid: str) -> dict:
    hist = rec.setdefault("history", [])
    entry = next((h for h in reversed(hist) if h.get("job_id") == jid), None)
    if entry is None:
        entry = {"job_id": jid, "url": None, "status": "generated", "reason": None, "at": now_iso(), "credits": 0}
        hist.append(entry)
    return entry


def set_pending(job: Job):
    def fn(m: dict, rec: dict) -> None:
        rec["api_pending"] = {"key": job.idem, "model": job.api_model, "body": job.final, "attempt": job.attempt,
                              "at": now_iso()}
    return fn


def clear_pending(m: dict, rec: dict) -> None:
    rec.pop("api_pending", None)


def record_accepted(job: Job, cid: str | None):
    """= hf_jobs.py record --status generated --job-id api:<id> --credits 0, plus the API facts in the history."""
    def fn(m: dict, rec: dict) -> str:
        api = {"model": job.api_model, "request_id": job.rid, "idempotency_key": job.idem,
               "usd_est": job.usd, "credits_est": job.credits}
        if cid:
            api["correlation_id"] = cid
        delta, msg = apply_record(rec, "generated", job_id=API_JOB + job.rid, url=None, reason=None, cost=0.0,
                                  extra={"start_image": job.start_job, "api": api})
        rec.pop("api_pending", None)
        pin_track_window(m, job)
        cr = add_credits(m, delta)
        cr["api_generations"] = int(cr.get("api_generations") or 0) + delta["generations"]
        return msg
    return fn


def pin_track_window(m: dict, job: Job) -> None:
    """A finished-song lip-sync clip made from audio/refs/<cut>_<lang>.wav: pin the vocal window it was driven by in
    cut.nar_ref (as hf_jobs.py narref does for MCP uploads) — the build plays the clip from that window's offset."""
    tr = track_of(m.get("song"))
    if tr is None or not job.lang or "<audio>" not in job.media:
        return
    cut = next((c for c in m.get("cuts") or [] if c.get("id") == job.cut), None)
    if cut is None or not cut.get("lipsync"):
        return
    cut.setdefault("nar_ref", {})[job.lang] = {
        "media_id": f"api-upload:audio/refs/{job.cut}_{job.lang}.wav", "track_sha1": tr.get("sha1"),
        "window": hf_jobs.track_window(m, job.cut), "at": now_iso()}


def record_completed(job: Job, url: str):
    """URL of the finished request + its charge (the estimate) into history.api and manifest.credits.api_usd."""
    def fn(m: dict, rec: dict) -> float:
        jid = API_JOB + job.rid
        if rec.get("job_id") == jid:
            apply_record(rec, "generated", job_id=jid, url=url, reason=None, cost=0.0)
        entry = history_entry(rec, jid)
        entry["url"] = url
        api = entry.setdefault("api", {})
        api["output_url"] = url
        if api.get("charged"):
            return 0.0
        usd = job.usd if job.usd is not None else api.get("usd_est")
        cred = job.credits if job.credits is not None else api.get("credits_est")
        api.update(usd=usd, credits=cred, charged=True)
        cr = m.setdefault("credits", {})
        cr["api_usd"] = round(float(cr.get("api_usd") or 0) + float(usd or 0), 4)
        cr["api_credits"] = round(float(cr.get("api_credits") or 0) + float(cred or 0), 4)
        return float(usd or 0)
    return fn


def record_failed(job: Job, status: str, error: str | None):
    """failed / nsfw / canceled → rejected (not charged — the API refunds), so the next plan offers it again."""
    def fn(m: dict, rec: dict) -> str:
        jid = API_JOB + job.rid
        reason = f"API {status}: {error or '결과 없음'}"
        if rec.get("job_id") == jid:
            apply_record(rec, "rejected", job_id=jid, url=None, reason=reason, cost=0.0)
        entry = history_entry(rec, jid)
        entry.update(status="rejected", reason=reason)
        entry.setdefault("api", {}).update(usd=0.0, charged=False)
        return reason
    return fn


# ---------------------------------------------------------------- run

class Run:
    def __init__(self, paths: Paths, cfg: dict, ep: str, api: HfApi, deadline: float, download: bool = True):
        self.paths, self.cfg, self.ep, self.api, self.deadline, self.download = paths, cfg, ep, api, deadline, download
        self.ledger = Ledger(paths, cfg, ep)
        self.stop = threading.Event()
        self.stop_error: ApiError | None = None
        self._out = threading.Lock()
        self._tmp = tempfile.TemporaryDirectory(prefix="momo_hf_api_")
        self.tmp = Path(self._tmp.name)

    def close(self) -> None:
        self._tmp.cleanup()

    def say(self, msg: str) -> None:
        with self._out:
            print(msg, flush=True)

    def out_of_credits(self, job: Job, e: ApiError, answered: bool = False) -> None:
        """answered: the API refused this job's own Idempotency-Key (not accepted) → MCP. A replay that was not
        resent (estimate refused) may still have been accepted earlier → held as UNSURE, never handed to MCP."""
        with self._out:
            if self.stop_error is None:
                self.stop_error = e
        self.stop.set()
        if job.replay and not answered:
            self.hold_replay(job, str(e))
        else:
            job.outcome, job.detail = NO_MONEY, f"{e} → MCP 로"
        self.say(f"  ✖ {job.key}: {no_credits_text(e)} — 새 제출을 멈춤")

    def hold(self, job: Job) -> None:
        if job.replay:
            self.hold_replay(job, "API 잔액 부족으로 다시 보내지 않음")
        else:
            job.outcome, job.detail = HELD, "API 잔액 부족으로 멈춤 → MCP 로"

    def hold_replay(self, job: Job, why: str) -> None:
        """A submit from an earlier run whose answer was lost may have been accepted (billed): MCP would make it a
        second time. Keep GenRec.api_pending; the next run resends the same key, or forget it after checking."""
        job.outcome = UNSURE
        job.detail = (f"이전 제출(Idempotency-Key {job.idem}) 접수 여부 불명 — {why}. MCP 로 넘기지 않음: 다음 run 이 같은 "
                      f"키로 다시 확인하거나, 콘솔(console.higgsfield.ai)에서 없음을 확인한 뒤 "
                      f"hf_api.py forget --ep {self.ep} --cut {job.cut}" + (f" --lang {job.lang}" if job.lang else ""))

    # -- phase A: uploads + estimate (both free)
    def prepare(self, job: Job) -> None:
        if job.rid:
            return
        try:
            if self.stop.is_set():
                self.hold(job)
                return
            if job.replay:
                job.final = job.body
            else:
                urls = {}
                for tok, md in job.media.items():
                    urls[tok] = self.input_url(job, tok, md)
                job.final = fill(job.body, urls)
            job.usd, job.credits = self.api.estimate(job.api_model, job.final)
        except ApiError as e:
            if e.no_credits:
                self.out_of_credits(job, e)
            else:
                job.outcome, job.detail = PREP_FAIL, str(e)
        except Exception as e:  # noqa: BLE001 — nothing is submitted in this phase; report it in the table
            job.outcome, job.detail = PREP_FAIL, f"{type(e).__name__}: {e}"

    def input_url(self, job: Job, tok: str, md: Media) -> str:
        if md.file is None:
            job.events.append(f"{tok}: 로컬 파일 없음 → manifest URL")
            return md.url
        try:
            f = md.file
            if md.wav:
                f = self.tmp / f"{job.cut}_{job.lang}_{md.file.stem}.wav"
                run(["ffmpeg", "-y", "-v", "error", "-i", str(md.file), "-ac", "1", "-c:a", "pcm_s16le", str(f)])
            return self.api.upload(f)
        except (ApiError, MomoError) as e:
            if md.url is None:
                raise
            job.events.append(f"{tok}: 업로드 안 됨 ({e}) → manifest URL")
            return md.url

    # -- phase B: submit → record → poll → record → download
    def execute(self, job: Job) -> None:
        try:
            if job.outcome != READY:
                return
            if not job.rid and not self.submit(job):
                return
            self.poll(job)
        except Exception as e:  # noqa: BLE001 — e.g. a manifest write failed (the clip changed under us)
            msg = str(e) if isinstance(e, MomoError) else f"{type(e).__name__}: {e}"
            if job.rid:  # accepted = billed: never lose the id
                msg += f" (접수된 request_id {job.rid} — 기록 확인 필요)"
            job.outcome, job.detail = RECORD_FAIL, msg
            self.say(f"  ✖ {job.key}: {msg}")

    def submit(self, job: Job) -> bool:
        if self.stop.is_set():
            self.hold(job)
            return False
        self.ledger.update(job, set_pending(job))
        try:
            job.rid, cid = self.api.submit(job.api_model, job.final, job.idem)
        except ApiError as e:
            if e.no_credits:  # the API refused this very key: not accepted
                self.ledger.update(job, clear_pending)
                self.out_of_credits(job, e, answered=True)
            elif e.ambiguous:  # maybe accepted: keep the intent — the next run resends the same key + body
                job.outcome, job.detail = UNSURE, f"{e} — 다음 run 이 같은 키로 다시 보내 확인 (중복 과금 없음)"
                self.say(f"  △ {job.key}: 접수 여부 불명 — {e}")
            else:
                self.ledger.update(job, clear_pending)
                job.outcome, job.detail = SUBMIT_FAIL, str(e)
                if e.code == 422 and "idempotency" in e.detail.lower():
                    job.detail += " — 이 키로 예전에 다른 body 가 접수됨: 콘솔(console.higgsfield.ai)에서 그 요청부터 확인"
                self.say(f"  ✖ {job.key}: 제출 거부 — {job.detail}")
            return False
        self.ledger.update(job, record_accepted(job, cid))
        self.say(f"  ↑ {job.key}: 접수 request_id {job.rid} → 기록 job_id {API_JOB}{job.rid}")
        return True

    def poll(self, job: Job) -> None:
        try:
            data = self.api.wait(job.rid, self.deadline)
        except PollTimeout as e:
            job.outcome, job.detail = RUNNING_LATE, f"{e} — 기록은 generated(URL 없음), 다음 run 이 이어서 확인"
            self.say(f"  △ {job.key}: {job.detail}")
            return
        except ApiError as e:
            job.outcome, job.detail = POLL_FAIL, f"{e} — 다음 run 이 다시 확인"
            self.say(f"  ✖ {job.key}: 상태 확인 실패 {e}")
            return
        st = data["status"]
        if st == "completed":
            url = output_url(data)
            if not url:
                job.outcome, job.detail = NO_URL, f"completed 인데 결과 URL 이 없음 (응답 키 {sorted(data)})"
                self.say(f"  ✖ {job.key}: {job.detail}")
                return
            job.charged = self.ledger.update(job, record_completed(job, url))
            job.outcome = DONE
            got = self.fetch(job, url)
            self.say(f"  ✔ {job.key}: 완료 {url}" + (f" → {got}" if got else ""))
        elif st in FAILED:
            reason = self.ledger.update(job, record_failed(job, st, data.get("error")))
            job.outcome, job.detail = FAILED[st], reason
            self.say(f"  ✖ {job.key}: {FAILED[st]} — 결과 없음, 성공 아님 (과금 없음) → rejected 로 기록: {reason}")
        else:
            job.outcome = UNKNOWN
            job.detail = f"status={st!r} — 성공으로 치지 않음. 기록은 generated(URL 없음), 다음 run 이 다시 확인"
            self.say(f"  △ {job.key}: {job.detail}")

    def fetch(self, job: Job, url: str) -> str | None:
        """Download into the clips folder like fetch_assets (verified with ffprobe) — API outputs expire (~7 days)."""
        if not self.download:
            return None
        if not which("ffprobe"):
            job.events.append(f"ffprobe 없음 — 받기는 fetch_assets.py --ep {self.ep}")
            return None
        slot = self.ledger.slot(job)
        try:
            final, desc = fetch_assets.download(url, slot)
        except fetch_assets.FetchError as e:
            job.events.append(f"받기 실패: {e} — fetch_assets.py --ep {self.ep} 로 다시 (URL 은 7일쯤 유효)")
            return None
        with self.ledger.lock:
            src = slot.dest / fetch_assets.SOURCES
            sources = load_json(src, default={})
            sources[final.name] = {"url": url, "job_id": API_JOB + job.rid}
            save_json(src, sources)
        job.file = final
        try:
            shown = final.relative_to(self.paths.root)
        except ValueError:
            shown = final
        return f"{shown} ({desc})"


def subscription_line(cfg: dict, m: dict) -> str:
    cr = m.get("credits") or {}
    return (f"구독 크레딧: 사용 {float(cr.get('spent') or 0):g} / 캡 {episode_cap(cfg, m):g} "
            f"— API 작업은 0 (구독 캡과 별개)")


def api_line(m: dict, now: float | None = None) -> str:
    cr = m.get("credits") or {}
    head = f"이번 실행 ${now:.2f} (완료분, estimate 기준) · " if now is not None else ""
    return (f"API 사용: {head}에피소드 누적 ${float(cr.get('api_usd') or 0):.2f} "
            f"(manifest.credits.api_usd, 생성 {int(cr.get('api_generations') or 0)}회)")


def job_view(paths: Paths, job: Job) -> dict:
    if job.rid:
        return {"key": job.key, "request_id": job.rid, "poll": f"GET {BASE_URL}/requests/{job.rid}/status",
                "notes": job.notes}

    def rel(p: Path | None) -> str | None:
        if p is None:
            return None
        try:
            return str(p.relative_to(paths.root))
        except ValueError:
            return str(p)
    v = {"key": job.key, "cut": job.cut, "lang": job.lang, "mcp_model": job.mcp_model, "api_model": job.api_model,
         "attempt": job.attempt, "idempotency_key": job.idem,
         "estimate": f"POST {BASE_URL}/estimate/{job.api_model}",
         "submit": f"POST {BASE_URL}/{job.api_model}  (Idempotency-Key: {job.idem})",
         "payload": job.body,
         "inputs": {tok: {"upload": rel(md.file), "as_wav": md.wav, "fallback_url": md.url}
                    for tok, md in job.media.items()},
         "notes": job.notes}
    if job.replay:
        v["replay"] = True
    return v


def mcp_plan(paths: Paths, cfg: dict, ep: str, cuts: list[str], lang: str | None) -> tuple[dict, str]:
    ns = argparse.Namespace(ep=ep, kind="clip", cuts=",".join(cuts), lang=lang, all=True)
    cmd = f"python momo/hf_jobs.py plan --ep {ep} --kind clip --cuts {','.join(cuts)}" + \
        (f" --lang {lang}" if lang else "") + " --all"
    return hf_jobs.plan_episode(paths, cfg, ns), cmd


def cmd_run(paths: Paths, cfg: dict, args) -> int:
    ep = check_ep(args.ep)
    if args.kind != "clip":
        raise MomoError(f"--kind {args.kind}: API 로는 클립만 — 이미지(Nano Banana Pro + Elements)·음성은 API 에 없어 "
                        f"MCP 로 (hf_jobs.py plan --kind {args.kind})")
    lang = check_lang(args.lang) if args.lang else None
    if not 1 <= args.max_parallel <= MAX_PARALLEL:
        raise MomoError(f"--max-parallel 은 1~{MAX_PARALLEL}")
    work = build_jobs(paths, cfg, ep, args.cuts, lang)
    jobs: list[Job] = work["jobs"]
    m = load_manifest(paths, ep)
    if args.dry_run:
        out = {"ep": ep, "kind": "clip", "dry_run": True, "base_url": BASE_URL, "max_parallel": args.max_parallel,
               "count": len(jobs), "items": [job_view(paths, j) for j in jobs], "mcp": work["mcp"],
               "blocked": work["blocked"], "awaiting_review": work["review"],
               "credits": {"subscription": work["plan"]["credits"],
                           "api_usd": float((m.get("credits") or {}).get("api_usd") or 0)},
               "notes": ["네트워크·키 없이 출력만. 실제 실행은 --dry-run 없이 (업로드·estimate 는 무료, 제출은 과금)",
                         "<image>/<end_image>/<audio> 는 실행 때 inputs 의 upload 파일을 올린 주소 (안 되면 fallback_url)"]}
        if (work["plan"]["credits"] or {}).get("stop"):
            out["notes"].append("credits.subscription.stop 은 남은 클립을 MCP(구독)로 만들 때의 예상 — API 작업은 구독 크레딧을 "
                                "쓰지 않는다 (API 잔액 부족으로 MCP 로 돌아가면 그때 적용)")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(f"▶ Higgsfield API — {ep} 클립 {len(jobs)}개 (동시 {args.max_parallel}개, 요청마다 최대 {args.deadline:.0f}초)")
    for j in jobs:
        what = f"이어서 확인 request_id {j.rid}" if j.rid else f"{j.mcp_model} → {j.api_model} {j.body.get('duration')}초"
        print(f"  · {j.key}: {what}" + "".join(f"\n      △ {n}" for n in j.notes))
    for b in work["blocked"]:
        print(f"  ⊘ {b}")
    for x in work["mcp"]:
        print(f"  → MCP {x['key']}: {x['reason']}")
    print(f"  {subscription_line(cfg, m)}")
    if not jobs:
        print("API 로 보낼 항목 없음")
        return finish_mcp(paths, cfg, ep, lang, work, [], None)

    r = Run(paths, cfg, ep, make_api(), args.deadline)
    try:
        return run_jobs(paths, cfg, ep, lang, work, jobs, r, args)
    finally:
        r.close()


def run_jobs(paths: Paths, cfg: dict, ep: str, lang: str | None, work: dict, jobs: list[Job], r: Run, args) -> int:
    with ThreadPoolExecutor(max_workers=args.max_parallel) as pool:
        list(pool.map(r.prepare, jobs))
    fresh = [j for j in jobs if not j.rid and j.outcome == READY]
    total = sum(j.usd or 0 for j in fresh)
    print(f"\n예상 비용 (POST /estimate, 과금 없음): ${total:.2f} — 제출 {len(fresh)}개")
    for j in fresh:
        print(f"  {j.key}: ${j.usd:.3f} ({j.credits:g} credits)" + (" · 재전송" if j.replay else ""))
    if args.max_usd is not None and total > args.max_usd + 1e-9 and not r.stop.is_set():
        print(f"\n✖ 예상 ${total:.2f} > --max-usd ${args.max_usd:.2f} — 아무것도 보내지 않음 "
              f"(항목을 줄이거나 사용자 승인 후 한도를 올릴 것)", file=sys.stderr)
        return 2
    if fresh or any(j.rid for j in jobs):
        print("\n생성 (접수되면 바로 manifest 에 기록):")
    with ThreadPoolExecutor(max_workers=args.max_parallel) as pool:
        list(pool.map(r.execute, jobs))
    return report(paths, cfg, ep, lang, work, jobs, r)


def report(paths: Paths, cfg: dict, ep: str, lang: str | None, work: dict, jobs: list[Job], r: Run) -> int:
    m = load_manifest(paths, ep)
    print(f"\n결과 (API, {ep}):")
    print("| 항목 | 결과 | request_id | 예상 USD | 파일·사유 |")
    print("|---|---|---|---|---|")
    for j in jobs:
        mark = "✔" if j.outcome == DONE else ("→" if j.outcome in TO_MCP else "✖")
        what = str(j.file.relative_to(paths.root)) if j.file else j.detail
        usd = f"${j.usd:.3f}" if j.usd is not None else "-"
        print(f"| {j.key} | {mark} {j.outcome} | {j.rid or '-'} | {usd} | {what} |")
    for j in jobs:
        for n in j.events:
            print(f"  △ {j.key}: {n}")
    print(f"\n{api_line(m, sum(j.charged for j in jobs))}")
    print(subscription_line(cfg, m))
    done = [j for j in jobs if j.outcome == DONE]
    if done:
        print(f"\n다음: 클립을 직접 보고 승인 — hf_jobs.py record --ep {ep} --cut <컷> --kind clip [--lang en] "
              f"--status approved|rejected. API 결과는 7일쯤 보관 → 승인 후 python momo/hf_api.py archive --ep {ep}")
    redo = [j for j in jobs if j.outcome in (UNSURE, RUNNING_LATE, POLL_FAIL, UNKNOWN, NO_URL)]
    if redo:
        print(f"이어서 확인: python momo/hf_api.py run --ep {ep} --kind clip --cuts "
              f"{','.join(dict.fromkeys(j.cut for j in redo))} (새로 제출하지 않음)")
    code = finish_mcp(paths, cfg, ep, lang, work, [j for j in jobs if j.outcome in TO_MCP], r.stop_error)
    if code:
        return code
    return 0 if all(j.outcome == DONE for j in jobs) else 1


def finish_mcp(paths: Paths, cfg: dict, ep: str, lang: str | None, work: dict, held: list[Job],
               stop_error: ApiError | None) -> int:
    """Items for the subscription (MCP): what the API cannot do, and — after HTTP 403 — everything not submitted."""
    if stop_error is None:
        if work["mcp"]:
            cuts = list(dict.fromkeys(x["cut"] for x in work["mcp"]))
            print(f"\nMCP 로 할 항목 {len(work['mcp'])}개 (API 매핑 없음): "
                  f"python momo/hf_jobs.py plan --ep {ep} --kind clip --cuts {','.join(cuts)} --all")
        return 0
    cuts = list(dict.fromkeys([j.cut for j in held] + [x["cut"] for x in work["mcp"]]))
    print(f"\n✖ {no_credits_text(stop_error)}", file=sys.stderr)
    if not cuts:
        print("남은 항목 없음 (이미 접수된 것은 위 결과대로)", file=sys.stderr)
        return 3
    plan, cmd = mcp_plan(paths, cfg, ep, cuts, lang)
    print(f"\n→ 남은 {len(cuts)}개 컷은 기존 구독 플랜(MCP)으로 이어서: 아래 각 item 의 params 를 "
          f"mcp__higgsfield__generate_video 에 그대로 넘기고 끝나면 record 명령 (다시 뽑기: {cmd})")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 3


# ---------------------------------------------------------------- archive

def cmd_archive(paths: Paths, cfg: dict, args) -> int:
    """API outputs → release media-<ep>, manifest URLs rewritten to the release (fetch_assets keeps working)."""
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    tag = args.tag or f"media-{ep}"
    todo: list[tuple[Slot, Path | None, str]] = []
    notes, fails = [], []
    sources: dict[Path, dict] = {}
    for s in episode_slots(paths, cfg, m):
        rec = s.rec
        jid = str(rec.get("job_id") or "")
        if not jid.startswith(API_JOB) or s.status not in FETCHABLE:
            continue
        url = rec.get("url")
        if not url:
            notes.append(f"{s.key}: 아직 결과 없음 — hf_api.py run 으로 확인")
            continue
        if release.is_release_url(url):
            notes.append(f"{s.key}: 이미 보관됨")
            continue
        src = sources.setdefault(s.dest, load_json(s.dest / fetch_assets.SOURCES, default={}))
        f = find_media(s.dest, s.stem, KIND_EXTS[s.kind])
        prov = (src.get(f.name) or {}) if f else {}
        if f is None or not (prov.get("url") == url or prov.get("job_id") == jid):
            # not here, an older attempt's file, or a file of unknown origin: the release URL replaces the API URL
            # for good, so only a file known to be this job's result is uploaded — get it while the API URL works
            if args.dry_run:
                todo.append((s, None, url))
                continue
            try:
                f, _ = fetch_assets.download(url, s)
            except fetch_assets.FetchError as e:
                fails.append(f"{s.key}: {url} — {e}")
                continue
            src[f.name] = {"url": url, "job_id": jid}
            save_json(s.dest / fetch_assets.SOURCES, src)  # true even if the release upload below fails
        todo.append((s, f, url))
    print(f"API 결과 보관 — {ep} → release {tag} ({len(todo)}개)")
    for n in notes:
        print(f"  · {n}")
    for x in fails:
        print(f"  ✖ 받기 실패 {x}")
    if args.dry_run:
        for s, f, url in todo:
            print(f"  ↑ {s.key}: {f.name if f else '(먼저 받음)'} ← {url}")
        return 1 if fails else 0
    if not todo:
        print("보관할 API 결과 없음")
        return 1 if fails else 0
    release.need_gh()
    names = {f"{ep}_{s.stem}_{song_track.sha1_file(f)[:8]}{f.suffix}": (s, f, url) for s, f, url in todo}
    release.ensure_release(tag, f"{ep} media (song, stems, lip-sync refs, API clips)",
                           "Media for the pipeline (fetch_assets.py): local audio and Higgsfield API outputs, "
                           "which the API keeps only ~7 days. Not a code release.")
    urls = release.upload_assets(tag, {n: f for n, (_, f, _) in names.items()})
    for n, (s, f, old) in names.items():
        new = urls[n]
        rec = s.rec
        entry = history_entry(rec, rec["job_id"])
        entry["url"] = new
        entry.setdefault("api", {})["output_url"] = old
        rec["url"] = new
        sources.setdefault(s.dest, load_json(s.dest / fetch_assets.SOURCES, default={}))[f.name] = \
            {"url": new, "job_id": rec["job_id"]}
        print(f"  ✔ {s.key}: {new}")
    save_json(paths.manifest(ep), m)
    for dest, data in sources.items():
        save_json(dest / fetch_assets.SOURCES, data)
    print(f"✔ {len(names)}개 보관, manifest url 갱신 — manifest.json 을 커밋·푸시할 것")
    return 1 if fails else 0


# ---------------------------------------------------------------- forget

def cmd_forget(paths: Paths, cfg: dict, args) -> int:
    """Drop a clip's GenRec.api_pending (a submit whose answer was lost) after the user checked on the console that
    the API never accepted it — otherwise hf_jobs plan keeps that clip away from MCP (double billing)."""
    ep = check_ep(args.ep)
    lang = check_lang(args.lang) if args.lang else None
    m = load_manifest(paths, ep)
    s = clip_slot(paths, cfg, m, args.cut, lang)
    pend = s.rec.get("api_pending")
    if not isinstance(pend, dict):
        print(f"{s.key}: 접수 불명인 API 제출 없음")
        return 0
    print(f"{s.key}: Idempotency-Key {pend.get('key')} ({pend.get('model')}, {pend.get('at')}, 시도 {pend.get('attempt')})")
    if not args.yes:
        print("콘솔(console.higgsfield.ai)에서 이 제출이 접수되지 않았음을 확인했으면 --yes 로 다시 실행 "
              "(접수됐으면 그 request_id 로 hf_jobs.py record --job-id api:<request_id> --credits 0)")
        return 1
    s.rec.pop("api_pending", None)
    save_json(paths.manifest(ep), m)
    print(f"✔ {s.key}: api_pending 지움 — 이제 hf_jobs.py plan(MCP) 또는 hf_api.py run 으로 새로 만들 수 있음")
    return 0


# ---------------------------------------------------------------- check / smoke

def cmd_check(paths: Paths, cfg: dict, args) -> int:
    api = make_api()
    try:
        api.status(str(uuid.uuid4()))  # an id that cannot exist: auth is checked first, nothing is generated
    except ApiError as e:
        if e.code == 404:
            print("✔ Higgsfield API 키 정상 (인증 통과 — 없는 작업 조회라 404, 과금 없음)")
            return 0
        if e.code == 401:
            raise MomoError(f"Higgsfield API 키가 거부됨 — 원문: {e}. .env.local 의 HF_KEY(키ID:시크릿) 확인") from e
        if e.no_credits:
            print(f"△ 키는 정상 (인증 통과) — 그러나 {no_credits_text(e)}. 클립은 MCP(구독)로 만들 것")
            return 3
        raise MomoError(f"Higgsfield API 확인 실패 — 원문: {e}") from e
    print("✔ Higgsfield API 응답 (인증 통과)")
    return 0


def cmd_smoke(paths: Paths, cfg: dict, args) -> int:
    api = make_api()
    try:
        usd, credits = api.estimate(SMOKE_MODEL, SMOKE_ARGS)
        print(f"▶ {SMOKE_MODEL} {SMOKE_ARGS} — 과금되는 생성 1건 (예상 ${usd:.3f}, {credits:g} credits)")
        rid, _ = api.submit(SMOKE_MODEL, dict(SMOKE_ARGS), str(uuid.uuid4()))
        print(f"  접수 request_id {rid}")
        data = api.wait(rid)
    except ApiError as e:
        raise MomoError(no_credits_text(e) if e.no_credits else f"Higgsfield API 요청 실패 — 원문: {e}") from e
    except PollTimeout as e:
        raise MomoError(f"작업 {rid}: {e}") from e
    if data["status"] != "completed":
        raise MomoError(f"작업 {rid}: {FAILED.get(data['status'], '완료되지 않음')} (status={data['status']!r}) "
                        f"{data.get('error') or ''} — 결과 없음, 성공 아님")
    url = output_url(data)
    if not url:
        raise MomoError(f"작업 {rid}: completed 인데 결과 URL 이 없음 — 응답 키 {sorted(data)}")
    print(f"✔ 완료 (request_id {rid})\n  video: {url}")
    return 0


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Higgsfield API (SDK) — 키 확인 · 클립 생성 · 결과 보관",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def subparser(name: str, help_: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_)
        p.add_argument("--root", default=argparse.SUPPRESS, help="momo 작업 폴더 (앞에 줘도 됨)")
        return p

    subparser("check", "인증만 확인 (과금 없음)")
    subparser("smoke", "Seedance 2.5 text-to-video 5초 예제 (과금)")
    p = subparser("run", "hf_jobs plan --kind clip 항목을 API 로 생성 (제출은 과금)")
    p.add_argument("--ep", required=True)
    p.add_argument("--kind", default="clip", choices=["clip", "image", "audio"], help="API 는 clip 만")
    p.add_argument("--cuts", help="쉼표 구분 컷 id")
    p.add_argument("--lang")
    p.add_argument("--dry-run", action="store_true", help="payload·estimate 호출만 출력 (네트워크·키 없이)")
    p.add_argument("--max-parallel", type=int, default=4, help=f"동시 요청 수 (기본 4, 최대 {MAX_PARALLEL})")
    p.add_argument("--max-usd", type=float, help="estimate 합계가 이보다 크면 아무것도 보내지 않음")
    p.add_argument("--deadline", type=float, default=DEADLINE, help="요청마다 결과를 기다릴 최대 초 (기본 1800)")
    p = subparser("archive", "API 결과를 GitHub release media-<ep> 로 옮기고 manifest url 갱신")
    p.add_argument("--ep", required=True)
    p.add_argument("--tag")
    p.add_argument("--dry-run", action="store_true")
    p = subparser("forget", "접수 불명인 API 제출(api_pending)을 지움 — 콘솔에서 접수 안 됨을 확인한 뒤에만")
    p.add_argument("--ep", required=True)
    p.add_argument("--cut", required=True)
    p.add_argument("--lang")
    p.add_argument("--yes", action="store_true", help="콘솔에서 접수 안 됨을 확인했음")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    cfg = load_config(paths)
    return {"check": cmd_check, "smoke": cmd_smoke, "run": cmd_run, "archive": cmd_archive,
            "forget": cmd_forget}[args.cmd](paths, cfg, args)


if __name__ == "__main__":
    main_wrapper(main)
