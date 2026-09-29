"""벤치마킹 1·2단계 공용: yt-dlp / Data API 수집, 지표 계산, 축 분류, 리포트, 자막(json3) 변환, 샷 통계.

데이터 흐름
  수집(yt-dlp flat-playlist | API | --offline-json) → channel_summary.json (+ meta/<id>.json)
  → analyze() → data.json / report.md / labels.template.json
  analyze() 는 네트워크 없이 channel_summary + meta + labels 만으로 다시 계산된다 (report 서브커맨드).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .common import MomoError, Paths

# ---------------------------------------------------------------- 상수

YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
UC_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
META_FIELDS = ("id", "title", "upload_date", "timestamp", "view_count", "like_count", "comment_count",
               "duration", "tags", "description", "thumbnail", "categories")
POPULAR_FETCH = 30          # sort=p 결과에서 내림차순을 검사할 개수
BOT_RE = re.compile(r"not a bot|sign in to confirm|HTTP Error 403|403 Forbidden|HTTP Error 429|"
                    r"Too Many Requests|rate[- ]?limit", re.I)
DEFAULT_BENCH = {"recent_count": 15, "top_count": 5, "min_age_hours": 72, "compilation_min_seconds": 1800}

UNCLASSIFIED = "미분류"
AXES = {"topic": "학습 소재", "format": "형식", "length_bucket": "길이 구간",
        "thumbnail_subject": "썸네일 주인공", "search_keyword": "제목 검색 키워드"}
LENGTH_BUCKETS = ("≤3분", "3~10분", "10~30분", "30분+")
THUMB_SUBJECTS = ("캐릭터 클로즈업", "사물", "텍스트 위주")
KW_YES, KW_NO = "포함", "미포함"

# 소재·형식 사전 (EN 은 단어 경계, 한글은 부분 문자열). 순서 = 동점 시 우선순위.
TOPICS: list[tuple[str, list[str]]] = [
    ("색", ["color", "colors", "colour", "colours", "rainbow", "red", "yellow", "blue", "green", "purple",
           "pink", "coloring", "색깔", "색상", "색칠", "무지개", "빨강", "빨간", "노랑", "노란", "파랑",
           "파란", "초록", "보라", "분홍"]),
    ("숫자", ["number", "numbers", "counting", "count", "123", "1 to 10", "one two three", "five little",
            "ten little", "math", "숫자", "수 세기", "세어", "하나 둘", "1부터"]),
    ("알파벳·단어", ["abc", "abcs", "alphabet", "phonics", "letter", "letters", "words", "first words",
                "vocabulary", "spelling", "알파벳", "한글", "가나다", "기역", "니은", "단어", "낱말", "파닉스"]),
    ("동물", ["animal", "animals", "dog", "dogs", "puppy", "cat", "cats", "kitten", "duck", "ducks", "cow",
            "pig", "farm", "zoo", "dinosaur", "dinosaurs", "shark", "elephant", "lion", "monkey",
            "old macdonald", "bird", "birds", "fish", "frog", "동물", "강아지", "고양이", "오리", "병아리",
            "공룡", "동물원", "농장", "상어", "코끼리", "사자", "원숭이", "개구리", "물고기"]),
    ("생활습관", ["brush", "teeth", "toothbrush", "bath", "bathtime", "potty", "wash hands",
              "wash your hands", "bedtime", "sleep", "rainy day", "rain", "clean up", "get dressed",
              "habits", "healthy habits", "manners", "boo boo", "sick", "doctor", "vegetables",
              "양치", "치카치카", "목욕", "손 씻", "손씻", "잠자리", "잘 자", "배변", "변기", "정리",
              "비 오는 날", "우비", "편식", "생활습관", "습관", "병원", "예절", "옷 입기"]),
    ("탈것", ["car", "cars", "truck", "trucks", "bus", "train", "trains", "fire truck", "police car",
            "excavator", "tractor", "vehicle", "vehicles", "airplane", "plane", "boat", "rocket",
            "ambulance", "자동차", "트럭", "버스", "기차", "소방차", "경찰차", "구급차", "포크레인",
            "굴착기", "탈것", "비행기", "중장비"]),
    ("감정", ["feeling", "feelings", "emotion", "emotions", "sad", "angry", "scared", "mad", "grumpy",
            "happy and you know it", "calm down", "crying", "감정", "기분", "슬퍼", "슬픈", "화가",
            "화났", "무서워", "기뻐", "행복", "울지"]),
]
TOPIC_OTHER = "기타"
FORMATS: list[tuple[str, list[str]]] = [
    ("모음집", ["compilation", "compilations", "+ more", "and more", "more nursery rhymes", "more kids songs",
             "hour", "hours", "non-stop", "nonstop", "collection", "marathon", "mix",
             "모음집", "동요 모음", "노래 모음", "연속 듣기", "연속듣기", "연속 재생", "이어 듣기",
             "모아 듣기", "모아듣기", "모아보기", "1시간"]),
    ("퀴즈·따라하기", ["quiz", "guess", "can you", "what is it", "what's this", "follow along",
                  "repeat after", "say it with", "find the", "hide and seek", "peekaboo", "peek-a-boo",
                  "which one", "퀴즈", "맞혀", "맞춰", "따라 해", "따라해", "따라하기", "따라 하기",
                  "찾아", "찾기", "어디 있", "누구일까", "뭘까", "무엇일까", "숨바꼭질", "까꿍", "같이 말해"]),
    ("스토리", ["story", "stories", "episode", "ep", "tale", "tales", "fairy tale", "adventure", "cartoon",
             "이야기", "동화", "에피소드", "모험", "애니메이션", "스토리", "만화"]),
    ("동요", ["song", "songs", "nursery rhyme", "nursery rhymes", "rhyme", "rhymes", "sing", "sing along",
            "sing-along", "lullaby", "lullabies", "music", "dance", "chant",
            "동요", "노래", "율동", "자장가", "챈트", "싱어롱", "댄스"]),
]
SEARCH_KEYWORDS = ["colors", "colours", "color", "numbers", "counting", "abc", "alphabet", "phonics", "shapes",
                   "toddler", "toddlers", "kids", "children", "baby", "babies", "nursery", "preschool",
                   "kindergarten", "learn", "learning", "educational",
                   "유아", "아기", "어린이", "동요", "키즈", "색깔", "숫자", "한글", "알파벳", "영어", "교육",
                   "놀이", "유치원", "배우기"]
ALLOWED_LABELS: dict[str, list] = {
    "topic": [t for t, _ in TOPICS] + [TOPIC_OTHER],
    "format": [f for f, _ in FORMATS] + [UNCLASSIFIED],
    "length_bucket": list(LENGTH_BUCKETS),
    "thumbnail_subject": list(THUMB_SUBJECTS) + [UNCLASSIFIED],
    "search_keyword": [True, False],
}

# 채널 상태 판정 기준 (최근 N 단편 vs 그 이전 3N 단편)
STATUS_RULE = {"growth_median": 1.0, "growth_daily": 3.0, "growth_daily_min_median": 0.7,
               "decline_median": 0.5, "decline_daily": 1.0, "decline_median_nodaily": 0.3}
STATUS_RULE_TEXT = ("성장: 중앙값 비 ≥ 1.0, 또는 (일평균 비 ≥ 3.0 이고 중앙값 비 ≥ 0.7) / "
                    "하락: 중앙값 비 < 0.5 이고 일평균 비 < 1.0 (일평균을 못 구하면 중앙값 비 < 0.3) / 그 외 정체. "
                    "최근 영상은 노출 기간이 짧아 누적 중앙값은 불리하고 일평균은 유리하므로 둘을 함께 본다.")


# ---------------------------------------------------------------- 시간·표시

def parse_now(value: str | None) -> datetime:
    """--now ISO8601 (Z 허용, 시간대 없으면 UTC). None 이면 현재 UTC."""
    if not value:
        return datetime.now(timezone.utc).replace(microsecond=0)
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as e:
        raise MomoError(f"--now 형식 오류: {value!r} (예: 2026-09-29T12:00:00Z)") from e
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iso(ts: float | None) -> str | None:
    return None if ts is None else datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def date_to_ts(yyyymmdd: str, end_of_day: bool = False) -> float | None:
    try:
        d = datetime.strptime(str(yyyymmdd), "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return d.timestamp() + (86399 if end_of_day else 0)


def parse_iso_duration(value: str | None) -> int | None:
    """ISO8601 기간 (PT1H2M3S, P1DT2H, P0D) → 초."""
    m = re.fullmatch(r"P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?", value or "")
    if not m or not value or value in ("P", "PT"):
        return None
    w, d, h, mi, s = (float(x) if x else 0.0 for x in m.groups())
    return int(round(w * 604800 + d * 86400 + h * 3600 + mi * 60 + s))


def fmt_int(n: float | None) -> str:
    return "—" if n is None else f"{int(round(n)):,}"


def fmt_x(r: float | None) -> str:
    return "—" if r is None else f"{r:.2f}배"


def fmt_pct(r: float | None) -> str:
    return "—" if r is None else f"{r * 100:.1f}%"


def fmt_dur(sec: float | None) -> str:
    if sec is None:
        return "—"
    s = int(round(sec))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_age(hours: float | None) -> str:
    if hours is None:
        return "—"
    return f"{hours:.0f}시간" if hours < 72 else f"{hours / 24:.0f}일"


def md(text: Any, limit: int = 70) -> str:
    """마크다운 표 셀용: | [ ] 이스케이프, 줄바꿈 제거, 길이 제한."""
    s = re.sub(r"\s+", " ", str(text if text is not None else "")).strip()
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return s.replace("\\", "\\\\").replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")


def video_url(vid: str) -> str:
    return f"https://www.youtube.com/watch?v={vid}"


def link(v: dict, limit: int = 60) -> str:
    return f"[{md(v.get('title') or v['id'], limit)}]({video_url(v['id'])})"


def _mean(xs: list[float]) -> float | None:
    return statistics.fmean(xs) if xs else None


def _median(xs: list[float]) -> float | None:
    return float(statistics.median(xs)) if xs else None


def _ratio(a: float | None, b: float | None) -> float | None:
    return None if a is None or not b else a / b


# ---------------------------------------------------------------- 채널 URL

def normalize_channel_url(url: str) -> str:
    """채널 링크 정규화. 영상 링크·유튜브 외 주소는 거부 (인자 주입 방지 겸용)."""
    raw = (url or "").strip()
    if raw.startswith("@"):
        raw = "https://www.youtube.com/" + raw
    if not re.match(r"^https?://", raw):
        raw = "https://" + raw
    u = urllib.parse.urlparse(raw)
    host = (u.hostname or "").lower()
    if host == "youtu.be" or u.path.startswith(("/watch", "/shorts/", "/live/", "/embed/")):
        raise MomoError(f"영상 링크가 아니라 채널 링크를 줘: {url} (예: https://www.youtube.com/@채널핸들)")
    if not (host == "youtube.com" or host.endswith(".youtube.com")):
        raise MomoError(f"유튜브 채널 주소가 아님: {url}")
    parts = [p for p in u.path.split("/") if p]
    if parts and parts[0].startswith("@"):
        parts = parts[:1]
    elif len(parts) >= 2 and parts[0] in ("channel", "c", "user"):
        parts = parts[:2]
    else:
        raise MomoError(f"채널 주소 형식을 알 수 없음: {url} (@핸들, /channel/UC..., /c/이름, /user/이름)")
    if not all(re.fullmatch(r"[^\s/?#&]+", p) for p in parts):
        raise MomoError(f"채널 주소에 허용되지 않는 문자: {url}")
    return "https://www.youtube.com/" + "/".join(parts)


def channel_slug(url: str | None = None, fallback: str | None = None) -> str:
    src = ""
    if url:
        src = urllib.parse.unquote(normalize_channel_url(url).rsplit("/", 1)[-1])
    src = src or fallback or "channel"
    slug = re.sub(r"[^\w.-]+", "-", src.lstrip("@").lower()).strip("-.")
    return slug or "channel"


def resolve_dir(paths: Paths, value: str) -> Path:
    """상대 경로: 현재 폴더 기준으로 있으면 그것, 아니면 --root 기준 (research/<slug>)."""
    p = Path(value).expanduser()
    if p.is_absolute():
        return p
    return p.resolve() if p.exists() else paths.root / p


# ---------------------------------------------------------------- yt-dlp

def ytdlp_cmd() -> list[str]:
    """MOMO_YTDLP(테스트·특수 설치) → PATH 의 yt-dlp → python -m yt_dlp."""
    if os.environ.get("MOMO_YTDLP"):
        return shlex.split(os.environ["MOMO_YTDLP"])
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    if importlib.util.find_spec("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    raise MomoError("yt-dlp 가 없음: pip install -U yt-dlp")


def _tail(text: str, n: int = 30) -> str:
    return "\n".join((text or "").strip().splitlines()[-n:])


def ytdlp_version() -> str | None:
    try:
        p = subprocess.run(ytdlp_cmd() + ["--version"], capture_output=True, text=True, timeout=60)
        return p.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired, MomoError):
        return None


def _pip_has_ytdlp() -> bool:
    try:
        q = subprocess.run([sys.executable, "-m", "pip", "show", "yt-dlp"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return q.returncode == 0 and "Name: yt-dlp" in q.stdout


def update_ytdlp(log: Callable[[str], None] = print) -> dict:
    """yt-dlp -U → pip 설치본이라 안 되면(또는 -U 가 실패했는데 pip 설치본이면) pip install -U yt-dlp.

    실패해도 계속 진행하고 결과만 기록한다.
    """
    res: dict[str, Any] = {"before": ytdlp_version()}
    try:
        p = subprocess.run(ytdlp_cmd() + ["-U"], capture_output=True, text=True, timeout=300)
        out = _tail(p.stdout + "\n" + p.stderr, 6)
        res["self_update"] = {"exit": p.returncode, "output": out}
        failed = p.returncode != 0 or "ERROR" in out
        if re.search(r"\bpip\b|pypi|package manager|cannot update", out, re.I) or (failed and _pip_has_ytdlp()):
            log(f"  yt-dlp -U 로 갱신 못함:\n{out}\n  → pip install -U yt-dlp 시도")
            q = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                               capture_output=True, text=True, timeout=600)
            res["pip"] = {"exit": q.returncode, "output": _tail(q.stdout + "\n" + q.stderr, 4)}
            if q.returncode != 0:
                log(f"  pip 갱신 실패 (계속 진행):\n{res['pip']['output']}")
        elif failed:
            log(f"  yt-dlp -U 실패 (계속 진행):\n{out}")
    except (OSError, subprocess.TimeoutExpired, MomoError) as e:
        res["error"] = str(e)
        log(f"  yt-dlp 갱신 시도 실패 (계속 진행): {e}")
    res["after"] = ytdlp_version()
    log(f"  yt-dlp 버전: {res['before']} → {res['after']}")
    return res


class YtDlp:
    """yt-dlp 실행기. 봇 확인/403/429 → --sleep-requests 1 → 쿠키 → 에러 원문으로 중단.

    한 번 올린 대응 단계(sleep, 쿠키)는 이후 호출에도 유지한다.
    """

    def __init__(self, cookies: str | None = None, cookies_from_browser: str | None = None,
                 sleep_requests: bool = False, log: Callable[[str], None] = print):
        self.cmd = ytdlp_cmd()
        self.sleep = sleep_requests
        self.cookie_args: list[str] = []
        if cookies:
            self.cookie_args += ["--cookies", str(cookies)]
        if cookies_from_browser:
            self.cookie_args += ["--cookies-from-browser", str(cookies_from_browser)]
        self.use_cookies = False
        self.log = log
        self.escalations: list[str] = []
        self.calls = 0

    def _opts(self) -> list[str]:
        opts = ["--no-progress"]
        if self.sleep:
            opts += ["--sleep-requests", "1"]
        if self.use_cookies:
            opts += self.cookie_args
        return opts

    def run(self, args: list[str], what: str, want_json: bool = False) -> Any:
        """성공하면 stdout(want_json 이면 파싱된 dict). 실패는 YtDlpError(bot=봇 차단 여부)."""
        tried = ["기본"] + (["--sleep-requests 1"] if self.sleep else []) + (["쿠키"] if self.use_cookies else [])
        while True:
            self.calls += 1
            try:
                p = subprocess.run(self.cmd + self._opts() + args, capture_output=True, text=True)
            except OSError as e:
                raise MomoError(f"yt-dlp 실행 실패 ({' '.join(self.cmd)}): {e}") from e
            if want_json:
                try:
                    data = json.loads(p.stdout) if p.stdout.strip() else None
                except json.JSONDecodeError:
                    data = None
                if isinstance(data, dict):
                    if p.returncode != 0:
                        self.log(f"  경고: yt-dlp 가 일부 오류를 냈지만 결과는 받음 ({what}):\n{_tail(p.stderr, 5)}")
                    return data
            elif p.returncode == 0:
                return p.stdout
            err = p.stderr or p.stdout
            if BOT_RE.search(err):
                if not self.sleep:
                    self.log(f"  봇 확인/403 감지 ({what}) → --sleep-requests 1 추가 후 재시도")
                    self.sleep = True
                    self.escalations.append("sleep-requests")
                    tried.append("--sleep-requests 1")
                    continue
                if self.cookie_args and not self.use_cookies:
                    self.log(f"  여전히 차단 ({what}) → 쿠키({' '.join(self.cookie_args)})로 재시도")
                    self.use_cookies = True
                    self.escalations.append("cookies")
                    tried.append("쿠키")
                    continue
                hint = "" if self.cookie_args else (
                    "\n→ 브라우저 쿠키로 재시도하려면 --cookies-from-browser chrome (또는 --cookies cookies.txt) 를 붙여 다시 실행.")
                if re.search(r"proxy|tunnel connection", err, re.I):
                    hint += "\n→ 프록시/네트워크에서 youtube.com 이 막힌 것으로 보임: 1단계는 --backend api (YOUTUBE_API_KEY) 로 대체 가능."
                raise YtDlpError(f"yt-dlp 차단으로 중단 ({what}). 시도: {' → '.join(tried)}{hint}\n"
                                 f"--- yt-dlp 에러 원문 ---\n{_tail(err, 40)}", bot=True)
            raise YtDlpError(f"yt-dlp 실패 ({what}, exit {p.returncode})\n--- yt-dlp 에러 원문 ---\n{_tail(err, 40)}",
                             bot=False)


class YtDlpError(MomoError):
    def __init__(self, msg: str, bot: bool):
        super().__init__(msg)
        self.bot = bot


def trim_meta(info: dict) -> dict:
    return {k: info.get(k) for k in META_FIELDS}


# ---------------------------------------------------------------- YouTube Data API v3

def _int(x: Any) -> int | None:
    return int(x) if x not in (None, "") else None


API_CATEGORIES = {"1": "Film & Animation", "10": "Music", "22": "People & Blogs", "24": "Entertainment",
                  "27": "Education"}


class YouTubeAPI:
    """urllib 로 Data API v3 호출. 키는 어떤 메시지에도 넣지 않는다."""

    def __init__(self, key: str | None = None, base: str | None = None):
        self.key = key or os.environ.get("YOUTUBE_API_KEY")
        if not self.key:
            raise MomoError("--backend api 에는 환경변수 YOUTUBE_API_KEY 가 필요함 "
                            "(Google Cloud 콘솔 → YouTube Data API v3 사용 설정 → API 키 발급)")
        self.base = (base or os.environ.get("MOMO_YT_API_BASE") or "https://www.googleapis.com/youtube/v3").rstrip("/")
        self.units = 0

    def get(self, endpoint: str, allow_404: bool = False, **params) -> dict | None:
        query = urllib.parse.urlencode({**{k: v for k, v in params.items() if v is not None}, "key": self.key})
        req = urllib.request.Request(f"{self.base}/{endpoint}?{query}", headers={"Accept": "application/json"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    self.units += 100 if endpoint == "search" else 1
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                if e.code == 404 and allow_404:
                    return None
                if e.code >= 500 and attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise MomoError(f"YouTube Data API 실패 ({endpoint}, HTTP {e.code})\n--- 응답 원문 ---\n"
                                f"{body.replace(self.key, '***')[:3000]}") from None
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise MomoError(f"YouTube Data API 접속 실패 ({endpoint}): "
                                f"{str(getattr(e, 'reason', e)).replace(self.key, '***')}") from None
        return None  # pragma: no cover

    def channel(self, url: str) -> dict:
        parts = normalize_channel_url(url).split("/")[3:]
        q: dict[str, str] = {}
        if parts[0].startswith("@"):
            q["forHandle"] = urllib.parse.unquote(parts[0])
        elif parts[0] == "channel":
            q["id"] = parts[1]
        elif parts[0] == "user":
            q["forUsername"] = parts[1]
        else:  # /c/이름 은 API 로 직접 못 찾음 → 검색 (100 units)
            s = self.get("search", part="snippet", q=urllib.parse.unquote(parts[1]), type="channel", maxResults=1)
            items = (s or {}).get("items") or []
            if not items:
                raise MomoError(f"채널을 찾지 못함: {url}")
            q["id"] = items[0]["snippet"]["channelId"]
        data = self.get("channels", part="snippet,statistics,contentDetails", **q) or {}
        if not data.get("items"):
            raise MomoError(f"채널을 찾지 못함 (API): {url}")
        return data["items"][0]

    def fetch(self, url: str, limit: int, log: Callable[[str], None] = print) -> tuple[dict, dict, dict]:
        """→ (yt-dlp flat-playlist 모양의 dict, {id: meta}, raw). entries 는 최신순."""
        ch = self.channel(url)
        cid = ch["id"]
        stats = ch.get("statistics") or {}
        uploads = (ch.get("contentDetails") or {}).get("relatedPlaylists", {}).get("uploads") or "UU" + cid[2:]
        # UULF = 긴 영상(= /videos 탭, 쇼츠·라이브 제외). 없으면 전체 업로드 목록.
        playlist, items, token, total = "UULF" + cid[2:], [], None, None
        while len(items) < limit:
            page = self.get("playlistItems", allow_404=True, part="contentDetails", playlistId=playlist,
                            maxResults=50, pageToken=token)
            if page is None:
                if playlist == uploads:
                    raise MomoError(f"업로드 목록을 찾지 못함 (API): {playlist}")
                log(f"  {playlist} 목록 없음 → 전체 업로드 목록({uploads}) 사용 (쇼츠 포함 가능)")
                playlist, items, token = uploads, [], None
                continue
            total = (page.get("pageInfo") or {}).get("totalResults", total)
            items += [it["contentDetails"]["videoId"] for it in page.get("items") or []]
            token = page.get("nextPageToken")
            if not token:
                break
        ids = list(dict.fromkeys(items))[:limit]
        entries, metas = [], {}
        for i in range(0, len(ids), 50):
            page = self.get("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50])) or {}
            for v in page.get("items") or []:
                sn, st, cd = v.get("snippet") or {}, v.get("statistics") or {}, v.get("contentDetails") or {}
                if sn.get("liveBroadcastContent") in ("live", "upcoming"):
                    continue
                ts = parse_now(sn["publishedAt"]).timestamp() if sn.get("publishedAt") else None
                thumbs = sn.get("thumbnails") or {}
                thumb = next((thumbs[k]["url"] for k in ("maxres", "standard", "high", "medium", "default")
                              if k in thumbs), None)
                meta = {"id": v["id"], "title": sn.get("title"),
                        "upload_date": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y%m%d") if ts else None,
                        "timestamp": int(ts) if ts else None, "view_count": _int(st.get("viewCount")),
                        "like_count": _int(st.get("likeCount")), "comment_count": _int(st.get("commentCount")),
                        "duration": parse_iso_duration(cd.get("duration")), "tags": sn.get("tags") or [],
                        "description": sn.get("description"), "thumbnail": thumb,
                        "categories": [API_CATEGORIES.get(sn.get("categoryId"), sn.get("categoryId"))]}
                metas[v["id"]] = meta
                entries.append({k: meta[k] for k in ("id", "title", "view_count", "duration", "timestamp")})
        entries.sort(key=lambda e: e.get("timestamp") or 0, reverse=True)
        subs = None if stats.get("hiddenSubscriberCount") else (int(stats["subscriberCount"])
                                                                 if stats.get("subscriberCount") else None)
        flat = {"channel_id": cid, "channel": (ch.get("snippet") or {}).get("title"),
                "uploader_id": (ch.get("snippet") or {}).get("customUrl"), "channel_follower_count": subs,
                "playlist_count": total, "entries": entries}
        raw = {"channel": ch, "playlist": playlist, "total_results": total, "quota_units": self.units}
        return flat, metas, raw


# ---------------------------------------------------------------- 수집 결과 정규화

def flat_entries(flat: dict | None) -> list[dict]:
    """flat-playlist entries 중 영상만 (id 11자). 중첩 플레이리스트는 펼친다."""
    out = []
    for e in (flat or {}).get("entries") or []:
        if not isinstance(e, dict):
            continue
        if e.get("_type") == "playlist" and e.get("entries"):
            out += flat_entries(e)
        elif YT_ID_RE.match(str(e.get("id") or "")):
            out.append(e)
    return out


def check_descending(entries: list[dict]) -> dict:
    """인기순 결과가 실제로 조회수 내림차순인지."""
    views = [e.get("view_count") for e in entries]
    known = [v for v in views if isinstance(v, (int, float))]
    inv = sum(1 for a, b in zip(known, known[1:]) if b > a)
    ok = len(known) >= min(5, len(entries)) and len(known) >= 2 and inv == 0
    return {"checked": len(known), "missing_views": len(views) - len(known), "inversions": inv, "descending": ok}


def _slim(e: dict) -> dict:
    out = {k: e.get(k) for k in ("id", "title", "view_count", "duration")}
    if e.get("timestamp"):
        out["timestamp"] = int(e["timestamp"])
    return out


def build_summary(flat: dict, *, url: str | None, backend: str, source: str, limit: int, top_n: int,
                  popular_flat: dict | None = None, popular_note: str | None = None,
                  fetched_at: datetime | None = None) -> dict:
    """flat-playlist(또는 API 가 만든 같은 모양) → channel_summary.json. 인기순 방법도 여기서 결정."""
    entries = [_slim(e) for e in flat_entries(flat) if e.get("live_status") not in ("is_upcoming", "is_live")]
    if not entries:
        raise MomoError("영상 목록이 비어 있음 (채널 URL 확인: /videos 탭에 영상이 있어야 함)")
    by_views = sorted((e for e in entries if e.get("view_count") is not None),
                      key=lambda e: e["view_count"], reverse=True)
    if backend == "api":
        popular = {"method": "api_sorted", "note": "API 로 목록 전체를 받아 조회수 내림차순 정렬",
                   "entries": by_views[:POPULAR_FETCH]}
    else:
        pop_entries = [_slim(e) for e in flat_entries(popular_flat)][:POPULAR_FETCH]
        chk = check_descending(pop_entries) if pop_entries else None
        if chk and chk["descending"]:
            popular = {"method": "sort=p", "note": "인기순(sort=p) 결과가 조회수 내림차순임을 확인",
                       "check": chk, "entries": pop_entries}
        else:
            why = popular_note or ("인기순(sort=p) 결과가 조회수 내림차순이 아님" if chk else "인기순 결과 없음")
            popular = {"method": "view_count_sort", "note": f"{why} → (a) 목록을 조회수 내림차순 정렬",
                       "check": chk, "entries": by_views[:POPULAR_FETCH]}
    popular["ids"] = [e["id"] for e in popular["entries"][:top_n]]
    total = flat.get("playlist_count")
    cid = flat.get("channel_id") or (flat.get("id") if UC_RE.match(str(flat.get("id") or "")) else None)
    return {
        "schema": 1,
        "fetched_at": iso((fetched_at or datetime.now(timezone.utc)).timestamp()),
        "backend": backend, "source": source,
        "channel": {"id": cid, "name": flat.get("channel") or flat.get("uploader") or flat.get("title"),
                    "handle": flat.get("uploader_id"), "url": url or flat.get("channel_url"),
                    "subscribers": flat.get("channel_follower_count")},
        "limit": limit, "listed": len(entries),
        "total_reported": total,
        "truncated": len(entries) >= limit or (isinstance(total, int) and total > len(entries)),
        "dates": "exact" if backend == "api" else ("approx" if any(e.get("timestamp") for e in entries) else "none"),
        "popular": popular,
        "entries": entries,
    }


# ---------------------------------------------------------------- 축 분류

_PAT: dict[str, re.Pattern] = {}


def _has(word: str, text: str) -> bool:
    if re.search(r"[가-힣]", word):
        return word in text
    pat = _PAT.get(word)
    if pat is None:
        pat = _PAT[word] = re.compile(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])")
    return bool(pat.search(text))


def _hits(words: list[str], text: str) -> list[str]:
    return [w for w in words if _has(w, text)]


def length_bucket(sec: float | None) -> str:
    if sec is None:
        return UNCLASSIFIED
    return "≤3분" if sec <= 180 else "3~10분" if sec <= 600 else "10~30분" if sec < 1800 else "30분+"


def classify(title: str | None, tags: list[str] | None, duration: float | None,
             comp_sec: int = 1800) -> tuple[dict, dict]:
    """제목(+태그)으로 자동 판정 → (axes, 근거 키워드). 제목 일치는 태그 일치의 2배 가중."""
    t, g = (title or "").lower(), " ".join(tags or []).lower()
    topic, best, topic_hits = TOPIC_OTHER, 0, []
    for label, words in TOPICS:
        th, gh = _hits(words, t), _hits(words, g)
        if 2 * len(th) + len(gh) > best:
            topic, best, topic_hits = label, 2 * len(th) + len(gh), th + [f"#{w}" for w in gh if w not in th]
    fmt, fmt_hits = UNCLASSIFIED, []
    if duration and duration >= comp_sec:
        fmt, fmt_hits = "모음집", [f"길이 {fmt_dur(duration)}"]
    else:
        for text, mark in ((t, ""), (g, "#")):  # 제목 우선, 없으면 태그
            for label, words in FORMATS:
                h = _hits(words, text)
                if h:
                    fmt, fmt_hits = label, [mark + w for w in h]
                    break
            if fmt_hits:
                break
    kw = _hits(SEARCH_KEYWORDS, t)
    axes = {"topic": topic, "format": fmt, "length_bucket": length_bucket(duration),
            "thumbnail_subject": UNCLASSIFIED, "search_keyword": bool(kw)}
    return axes, {"topic": topic_hits, "format": fmt_hits, "search_keyword": kw}


def load_labels(path: Path) -> dict[str, dict]:
    """labels.json → {id: {axis: 값}}. 빈 값은 자동 판정 유지, 허용값 밖이면 중단."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise MomoError(f"labels 파일을 읽을 수 없음: {path}: {e}") from e
    items = data.get("videos", data) if isinstance(data, dict) else data
    if isinstance(items, list):
        items = {str(it.get("id")): it for it in items if isinstance(it, dict)}
    out: dict[str, dict] = {}
    for vid, it in (items or {}).items():
        if not YT_ID_RE.match(str(vid)) or not isinstance(it, dict):
            continue
        ov = {}
        for axis, allowed in ALLOWED_LABELS.items():
            val = it.get(axis)
            if val is None or val == "":
                continue
            if axis == "search_keyword" and isinstance(val, str):
                val = {KW_YES: True, KW_NO: False, "true": True, "false": False}.get(val.strip().lower(), val)
            if val not in allowed:
                raise MomoError(f"labels: {vid}.{axis} = {val!r} 는 허용값이 아님 → {allowed}")
            ov[axis] = val
        if ov:
            out[str(vid)] = ov
    return out


def axis_value(v: dict, axis: str) -> str:
    val = v["axes"][axis]
    return (KW_YES if val else KW_NO) if axis == "search_keyword" else val


# ---------------------------------------------------------------- 분석

def _rows(summary: dict, metas: dict, now_ts: float, bench: dict) -> list[dict]:
    """목록(최신순) + 개별 메타 병합 → 행. 업로드 시각이 없으면 앞(더 최신) 영상 기준으로 추정."""
    comp_sec, min_age = bench["compilation_min_seconds"], bench["min_age_hours"]
    listed = summary["entries"]
    listed_ids = {x["id"] for x in listed}
    extra = [e for e in summary.get("popular", {}).get("entries", [])
             if e["id"] not in listed_ids]  # 목록 밖(상한 초과분)의 인기작
    rows, known_old = [], False
    for i, e in enumerate(listed + extra):
        m = metas.get(e["id"]) or {}
        pick = lambda k: m.get(k) if m.get(k) is not None else e.get(k)  # noqa: E731
        ts, src = None, None
        if m.get("timestamp"):
            ts, src = float(m["timestamp"]), "meta"
        elif m.get("upload_date"):  # 날짜만 있으면 그날 끝으로 (72시간 제외를 보수적으로)
            ts, src = date_to_ts(m["upload_date"], end_of_day=True), "meta_date"
        elif e.get("timestamp"):
            ts, src = float(e["timestamp"]), "approx"
        in_list = i < len(listed)
        age = (now_ts - ts) / 3600 if ts is not None else None
        if age is not None:
            is_new = age < min_age
            known_old = known_old or (in_list and not is_new)
        elif in_list and known_old:
            is_new, src = False, "inferred"  # 목록은 최신순 → 이미 72h 지난 영상보다 뒤면 더 오래됨
        else:
            is_new = None
        dur = pick("duration")
        rows.append({
            "id": e["id"], "title": pick("title"), "view_count": pick("view_count"), "duration": dur,
            "like_count": m.get("like_count"), "comment_count": m.get("comment_count"), "tags": m.get("tags") or [],
            "timestamp": int(ts) if ts is not None else None, "date_source": src,
            "age_hours": round(age, 1) if age is not None else None, "is_new": is_new,
            "is_compilation": bool(dur and dur >= comp_sec), "list_index": i if in_list else None,
            "has_meta": bool(m),
        })
    return rows


def _eligible(r: dict) -> bool:
    return not r["is_new"] and r["view_count"] is not None


def _group_table(videos: list[dict], axis: str, separate: bool = False) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for v in videos:
        groups.setdefault(axis_value(v, axis), []).append(v)
    rows = [{"value": k, "n": len(vs), "mean_views": _mean([v["view_count"] for v in vs]),
             "median_views": _median([v["view_count"] for v in vs]), "ids": [v["id"] for v in vs],
             "separate": separate} for k, vs in groups.items()]
    return sorted(rows, key=lambda g: -(g["mean_views"] or 0))


def _status(rows: list[dict], now_ts: float, n: int) -> dict:
    shorts = [r for r in rows if r["list_index"] is not None and not r["is_compilation"] and _eligible(r)]
    recent, prev = shorts[:n], shorts[n:4 * n]

    def daily(group):
        vals = [r["view_count"] / max(r["age_hours"] / 24, 1.0) for r in group if r["age_hours"] is not None]
        return _median(vals) if len(vals) >= max(3, len(group) // 2) else None

    rm, pm = _median([r["view_count"] for r in recent]), _median([r["view_count"] for r in prev])
    rd, pd = daily(recent), daily(prev)
    mr, dr = _ratio(rm, pm), _ratio(rd, pd)
    R = STATUS_RULE
    if mr is None or len(recent) < 3 or len(prev) < 3:
        label = "판단 불가"
    elif mr >= R["growth_median"] or (dr is not None and dr >= R["growth_daily"] and mr >= R["growth_daily_min_median"]):
        label = "성장"
    elif (dr is not None and mr < R["decline_median"] and dr < R["decline_daily"]) or \
            (dr is None and mr < R["decline_median_nodaily"]):
        label = "하락"
    else:
        label = "정체"
    return {"label": label, "recent_n": len(recent), "prev_n": len(prev),
            "recent_median": rm, "prev_median": pm, "median_ratio": mr,
            "recent_daily_median": rd, "prev_daily_median": pd, "daily_ratio": dr,
            "recent_ids": [r["id"] for r in recent], "prev_ids": [r["id"] for r in prev],
            "rule": R, "rule_text": STATUS_RULE_TEXT}


def analyze(summary: dict, metas: dict[str, dict], labels: dict[str, dict] | None = None,
            now: datetime | None = None, bench: dict | None = None) -> dict:
    """channel_summary + meta + labels → data.json (모든 수치). 네트워크 없음."""
    bench = {**DEFAULT_BENCH, **{k: v for k, v in (bench or {}).items() if k in DEFAULT_BENCH}}
    labels = labels or {}
    now = now or datetime.now(timezone.utc)
    now_ts = now.timestamp()
    n_recent, n_top, comp_sec = bench["recent_count"], bench["top_count"], bench["compilation_min_seconds"]
    rows = _rows(summary, metas, now_ts, bench)
    by_id = {r["id"]: r for r in rows}
    listed = [r for r in rows if r["list_index"] is not None]

    pop = summary.get("popular") or {}
    top_ids = [i for i in pop.get("ids") or [] if i in by_id][:n_top]
    if not top_ids:
        top_ids = [r["id"] for r in sorted((r for r in listed if r["view_count"] is not None),
                                           key=lambda r: -r["view_count"])[:n_top]]
    top = sorted((by_id[i] for i in top_ids), key=lambda r: -(r["view_count"] or 0))
    recent = listed[:n_recent]

    for r in {r["id"]: r for r in recent + top}.values():
        auto, matched = classify(r["title"], r["tags"], r["duration"], comp_sec)
        final = {**auto, **labels.get(r["id"], {})}
        r.update(axes=final, axes_auto=auto, matched=matched,
                 labeled=sorted(k for k in final if final[k] != auto[k]))
    for rank, r in enumerate(top, 1):
        r["popular_rank"] = rank
    for rank, r in enumerate(recent, 1):
        r["recent_rank"] = rank

    recent_el = [r for r in recent if _eligible(r)]
    recent_shorts = [r for r in recent_el if not r["is_compilation"]]
    recent_avg = _mean([r["view_count"] for r in recent_shorts])
    best = top[0] if top else None
    shorts_all = [r for r in rows if not r["is_compilation"] and r["view_count"] is not None]
    best_short = max(shorts_all, key=lambda r: r["view_count"], default=None)
    subs = (summary.get("channel") or {}).get("subscribers")
    listed_total = sum(r["view_count"] for r in rows if r["view_count"] is not None)
    top_total = sum(r["view_count"] or 0 for r in top)
    brief = lambda r: None if r is None else {k: r.get(k) for k in ("id", "title", "view_count", "duration")}  # noqa: E731

    comps = [r for r in listed if r["is_compilation"] and r["view_count"] is not None]
    comp_el = [r for r in comps if not r["is_new"]]
    comp_mean = _mean([r["view_count"] for r in comp_el])
    compilations = {
        "min_seconds": comp_sec, "count": len(comps), "eligible_n": len(comp_el),
        "mean_views": comp_mean, "median_views": _median([r["view_count"] for r in comp_el]),
        "total_views": sum(r["view_count"] for r in comps),
        "share_of_listed_total": _ratio(sum(r["view_count"] for r in comps), listed_total),
        "mean_vs_recent_short_avg": _ratio(comp_mean, recent_avg),
        "in_top": [r["id"] for r in top if r["is_compilation"]],
        "in_recent": [r["id"] for r in recent if r["is_compilation"]],
        "top": [brief(r) for r in sorted(comps, key=lambda r: -r["view_count"])[:5]],
    }

    shorts_ax = [r for r in recent_el if not r["is_compilation"]]
    comps_ax = [r for r in recent_el if r["is_compilation"]]
    axes: dict[str, dict] = {}
    for axis, name in AXES.items():
        groups = _group_table(shorts_ax, axis)
        if axis in ("format", "length_bucket") and comps_ax:
            groups += _group_table(comps_ax, axis, separate=True)
        cmp_groups = [g for g in groups if not g["separate"] and g["value"] != UNCLASSIFIED and g["n"] >= 2]
        gap = None
        if len(cmp_groups) >= 2:
            hi = max(cmp_groups, key=lambda g: g["mean_views"])
            lo = min(cmp_groups, key=lambda g: g["mean_views"])
            gap = {"ratio": _ratio(hi["mean_views"], lo["mean_views"]), "abs": hi["mean_views"] - lo["mean_views"],
                   "high": hi["value"], "low": lo["value"], "high_mean": hi["mean_views"], "low_mean": lo["mean_views"]}
        note = None
        if gap is None:
            note = ("labels.json 으로 썸네일 주인공을 채워야 비교 가능" if axis == "thumbnail_subject" and
                    all(g["value"] == UNCLASSIFIED for g in groups) else "n≥2 인 그룹이 2개 미만이라 비교 불가")
        axes[axis] = {"name": name, "groups": groups, "gap": gap, "note": note}
    ranked = sorted(((a, x["gap"]) for a, x in axes.items() if x["gap"] and x["gap"]["ratio"] is not None),
                    key=lambda t: (t[1]["ratio"], t[1]["abs"]), reverse=True)
    largest = {"axis": ranked[0][0], "name": AXES[ranked[0][0]], **ranked[0][1]} if ranked else None

    cmp_axes = ("format", "topic", "length_bucket")
    modes = {a: Counter(r["axes"][a] for r in top).most_common(1)[0][0] for a in cmp_axes} if top else {}
    top3 = sorted(recent_el, key=lambda r: -r["view_count"])[:3]
    top3_rows = [{"id": r["id"], "title": r["title"], "view_count": r["view_count"],
                  **{a: r["axes"][a] for a in cmp_axes},
                  "same_count": {a: sum(1 for t in top if t["axes"][a] == r["axes"][a]) for a in cmp_axes},
                  "matches_mode": {a: r["axes"][a] == modes.get(a) for a in cmp_axes}} for r in top3]
    for x in top3_rows:
        x["same_format_as_alltime"] = all(x["matches_mode"].values())

    # 2단계 대상: 역대 1위 + 최근 1위. 30분+ 모음집이면 단편 1위로 (에피소드 구조 분석용).
    def pick(cands: list[dict], role: str) -> dict | None:
        if not cands:
            return None
        first = cands[0]
        short = next((r for r in cands if not r["is_compilation"]), None)
        if first["is_compilation"] and short:
            return {"id": short["id"], "role": role, "reason": f"1위({first['id']})가 30분+ 모음집이라 단편 1위로 대체"}
        return {"id": first["id"], "role": role, "reason": None}

    alltime = pick(top + sorted(shorts_all, key=lambda r: -r["view_count"]), "역대 1위")
    recent1 = pick(sorted(recent_el, key=lambda r: -r["view_count"]), "최근 1위")
    sample = [t for t in (alltime, recent1) if t]
    if len(sample) == 2 and sample[0]["id"] == sample[1]["id"]:
        sample = [{**sample[0], "role": "역대 1위 = 최근 1위"}]
    # 썸네일: 역대 1·2위 + 최근 1위·최하위, 겹치면 다음 순위로 채워 최소 4장
    recent_sorted = sorted(recent_el, key=lambda r: -r["view_count"])
    must = [(r, f"역대 {i}위") for i, r in enumerate(top[:2], 1)]
    if recent_sorted:
        must += [(recent_sorted[0], "최근 1위"), (recent_sorted[-1], "최근 최하위")]
    fill = [(r, f"역대 {i}위") for i, r in enumerate(top[2:], 3)] + \
           [(r, f"최근 {i}위") for i, r in enumerate(recent_sorted[1:-1], 2)]
    thumbs: list[dict] = []
    for r, role in must + fill:
        if len(thumbs) >= 4 and (r, role) in fill:
            break
        if r["id"] not in {t["id"] for t in thumbs}:
            thumbs.append({"id": r["id"], "role": role, "title": r["title"]})

    ch = summary.get("channel") or {}
    keep = ("id", "title", "view_count", "like_count", "comment_count", "duration", "timestamp", "date_source",
            "age_hours", "is_new", "is_compilation", "list_index", "has_meta", "tags", "axes", "axes_auto",
            "matched", "labeled", "popular_rank", "recent_rank")
    videos = {r["id"]: {**{k: r.get(k) for k in keep}, "upload": iso(r["timestamp"]), "url": video_url(r["id"])}
              for r in recent + top}
    return {
        "schema": 1,
        "generated_at": iso(time.time()),
        "now": iso(now_ts),
        "backend": summary.get("backend"), "source": summary.get("source"),
        "channel": {**ch, "listed": summary.get("listed"), "limit": summary.get("limit"),
                    "truncated": summary.get("truncated"), "total_reported": summary.get("total_reported"),
                    "partial": bool(summary.get("truncated")), "dates": summary.get("dates")},
        "bench": bench,
        "popular": {"method": pop.get("method"), "note": pop.get("note"), "check": pop.get("check"), "ids": top_ids},
        "top": [r["id"] for r in top],
        "recent": [r["id"] for r in recent],
        "excluded_new": [{"id": r["id"], "title": r["title"], "age_hours": r["age_hours"],
                          "view_count": r["view_count"]} for r in listed if r["is_new"]],
        "unknown_age": [r["id"] for r in recent if r["is_new"] is None],
        "metrics": {
            "best_overall": brief(best), "best_short": brief(best_short),
            "recent_short_avg": recent_avg, "recent_short_n": len(recent_shorts),
            "recent_short_ids": [r["id"] for r in recent_shorts],
            "best_vs_recent_avg": _ratio(best and best["view_count"], recent_avg),
            "best_short_vs_recent_avg": _ratio(best_short and best_short["view_count"], recent_avg),
            "subscribers": subs,
            "best_per_subscriber": _ratio(best and best["view_count"], subs),
            "recent_avg_per_subscriber": _ratio(recent_avg, subs),
            "listed_total_views": listed_total, "top_total_views": top_total,
            "top_share": _ratio(top_total, listed_total),
        },
        "compilations": compilations,
        "status": _status(rows, now_ts, n_recent),
        "axes": axes,
        "largest_gap_axis": largest,
        "top3_vs_alltime": {"alltime_modes": modes, "recent_top3": top3_rows,
                            "n_same_format": sum(1 for x in top3_rows if x["same_format_as_alltime"])},
        "targets": {"sample": sample, "thumbs": thumbs},
        "labels_applied": sorted(v for v in labels if v in videos),
        "videos": videos,
    }


# ---------------------------------------------------------------- 리포트

def render_report(d: dict) -> str:
    ch, m, st, comp = d["channel"], d["metrics"], d["status"], d["compilations"]
    V = d["videos"]
    L: list[str] = []
    add = L.append
    backend = {"ytdlp": "yt-dlp", "api": "YouTube Data API v3"}.get(d.get("backend"), d.get("backend"))
    add(f"# 벤치마킹 리포트 — {md(ch.get('name') or ch.get('handle') or '채널', 80)}")
    add("")
    add(f"- 채널: {ch.get('url') or '—'} ({ch.get('handle') or ch.get('id') or ''})")
    add(f"- 기준 시각(UTC): {d['now']} · 수집 백엔드: **{backend}** ({d.get('source')})")
    part = f" — **일부 기준** (상한 {fmt_int(ch.get('limit'))}개까지만 받음)" if ch.get("partial") else ""
    add(f"- 목록: {fmt_int(ch.get('listed'))}개{part} · 구독자: {fmt_int(ch.get('subscribers'))}")
    no_meta = [vid for vid, v in V.items() if not v.get("has_meta", True)] if isinstance(V, dict) else []
    n_meta = len(V) - len(no_meta) if isinstance(V, dict) else 0
    dates = {"exact": "정확(API)", "approx": f"목록은 대략(yt-dlp approximate_date), 개별 메타 {n_meta}개는 정확",
             "none": f"개별 메타 {n_meta}개만 정확, 나머지는 목록 순서로 추정"}.get(ch.get("dates"), ch.get("dates"))
    add(f"- 업로드 시각: {dates}")
    if no_meta:
        add(f"- ⚠️ 개별 메타 없음 {len(no_meta)}개 — 좋아요·댓글·태그·정확한 업로드 시각 미수집, "
            "목록의 대략 날짜·조회수로만 계산")
    add("")
    add("## 1. 판정 요약")
    add("")
    add("| 항목 | 값 | 근거 |")
    add("|---|---|---|")
    add(f"| 채널 상태 | **{st['label']}** | 최근 {st['recent_n']} 단편 중앙값 {fmt_int(st['recent_median'])} vs "
        f"이전 {st['prev_n']} 단편 {fmt_int(st['prev_median'])} ({fmt_x(st['median_ratio'])}), "
        f"일평균 {fmt_int(st['recent_daily_median'])} vs {fmt_int(st['prev_daily_median'])} ({fmt_x(st['daily_ratio'])}) |")
    bo, bs = m["best_overall"], m["best_short"]
    add(f"| 역대 최고작 / 최근 단편 평균 | {fmt_x(m['best_vs_recent_avg'])} | "
        f"{fmt_int(bo and bo['view_count'])} / {fmt_int(m['recent_short_avg'])} (단편 {m['recent_short_n']}개 평균) |")
    add(f"| 역대 최고 단편 / 최근 단편 평균 | {fmt_x(m['best_short_vs_recent_avg'])} | "
        f"{fmt_int(bs and bs['view_count'])} / {fmt_int(m['recent_short_avg'])} |")
    add(f"| 구독자 대비 — 역대 최고작 | {fmt_x(m['best_per_subscriber'])} | "
        f"{fmt_int(bo and bo['view_count'])} / 구독자 {fmt_int(m['subscribers'])} |")
    add(f"| 구독자 대비 — 최근 단편 평균 | {fmt_x(m['recent_avg_per_subscriber'])} | "
        f"{fmt_int(m['recent_short_avg'])} / 구독자 {fmt_int(m['subscribers'])} |")
    add(f"| 역대 {len(d['top'])}개 비중 | {fmt_pct(m['top_share'])} | "
        f"{fmt_int(m['top_total_views'])} / 목록 총 {fmt_int(m['listed_total_views'])} |")
    lg = d["largest_gap_axis"]
    add(f"| 격차 최대 축 (원인 후보) | **{lg['name'] if lg else '—'}** | " +
        (f"{md(lg['high'])} 평균 {fmt_int(lg['high_mean'])} vs {md(lg['low'])} 평균 {fmt_int(lg['low_mean'])} "
         f"({fmt_x(lg['ratio'])})" if lg else "비교 가능한 축 없음") + " |")
    add(f"| 모음집 축 (30분+) | {comp['count']}개 | 평균 {fmt_int(comp['mean_views'])} "
        f"(최근 단편 평균의 {fmt_x(comp['mean_vs_recent_short_avg'])}), 목록 조회수의 {fmt_pct(comp['share_of_listed_total'])} |")
    t3 = d["top3_vs_alltime"]
    add(f"| 최신 상위 3 vs 역대 포맷 | {t3['n_same_format']}/{len(t3['recent_top3'])}개 동일 | "
        f"역대 최다 포맷: {' · '.join(md(v) for v in t3['alltime_modes'].values()) or '—'} |")
    add("")
    add(f"- 평균 계산에서 72시간 미만 영상 {len(d['excluded_new'])}개 제외, 30분 이상 모음집은 별도 축으로 분리.")
    add(f"- 판정 기준: {st['rule_text']}")
    add("")

    pm = d["popular"]
    add(f"## 2. 역대 인기 {len(d['top'])}개")
    add("")
    add(f"방법: **{pm['method']}** — {pm['note']}")
    if pm.get("check"):
        c = pm["check"]
        add(f"(인기순 결과 검사: {c['checked']}개 중 역순 {c['inversions']}회, 조회수 없음 {c['missing_views']}개)")
    add("")
    add("| 순위 | 제목 | 조회수 | 길이 | 업로드 | 형식 | 소재 | 길이 구간 |")
    add("|---|---|---:|---:|---|---|---|---|")
    for i in d["top"]:
        v = V[i]
        add(f"| {v['popular_rank']} | {link(v)} | {fmt_int(v['view_count'])} | {fmt_dur(v['duration'])} | "
            f"{(v['upload'] or '—')[:10]} | {md(v['axes']['format'])} | {md(v['axes']['topic'])} | "
            f"{md(v['axes']['length_bucket'])} |")
    add("")

    add(f"## 3. 최신 {len(d['recent'])}개 (축 분류)")
    add("")
    add("| # | 제목 | 조회수 | 길이 | 경과 | 소재 | 형식 | 길이 구간 | 썸네일 | 검색 키워드 | 비고 |")
    add("|---|---|---:|---:|---:|---|---|---|---|---|---|")
    for i in d["recent"]:
        v = V[i]
        a = v["axes"]
        note = []
        if v["is_new"]:
            note.append("72h 미만·평균 제외")
        elif v["is_new"] is None:
            note.append("업로드 시각 미상")
        if v["is_compilation"]:
            note.append("모음집 축")
        if v["labeled"]:
            note.append("labels: " + ",".join(AXES[k] for k in v["labeled"]))
        kw = ", ".join(v["matched"]["search_keyword"]) if a["search_keyword"] else ""
        kw_cell = f"{KW_YES} ({md(kw, 40)})" if kw else (KW_YES if a["search_keyword"] else KW_NO)
        add(f"| {v['recent_rank']} | {link(v, 50)} | {fmt_int(v['view_count'])} | {fmt_dur(v['duration'])} | "
            f"{fmt_age(v['age_hours'])} | {md(a['topic'])} | {md(a['format'])} | {md(a['length_bucket'])} | "
            f"{md(a['thumbnail_subject'])} | {kw_cell} | {'; '.join(note)} |")
    add("")
    add("자동 판정 근거 키워드(#은 태그에서 찾음):")
    add("")
    for i in d["recent"]:
        v = V[i]
        mt = v["matched"]
        add(f"- `{i}` 소재: {', '.join(mt['topic']) or '없음→기타'} / 형식: {', '.join(mt['format']) or '없음→미분류'}")
    add("")

    add("## 4. 72시간 미만 (평균에서 제외)")
    add("")
    if d["excluded_new"]:
        add("| 제목 | 경과 | 조회수 |")
        add("|---|---:|---:|")
        for x in d["excluded_new"]:
            add(f"| {link(x)} | {fmt_age(x['age_hours'])} | {fmt_int(x['view_count'])} |")
    else:
        add("없음")
    if d["unknown_age"]:
        add("")
        add(f"업로드 시각을 알 수 없어 평균에 포함한 영상: {', '.join(d['unknown_age'])}")
    add("")

    add("## 5. 모음집 축 (30분 이상, 단편 평균과 분리)")
    add("")
    add(f"- 목록 내 {comp['count']}개 (72h 제외 후 {comp['eligible_n']}개), 평균 {fmt_int(comp['mean_views'])}, "
        f"중앙값 {fmt_int(comp['median_views'])}, 목록 총 조회수의 {fmt_pct(comp['share_of_listed_total'])}")
    add(f"- 역대 {len(d['top'])}개 중 모음집 {len(comp['in_top'])}개, 최신 {len(d['recent'])}개 중 {len(comp['in_recent'])}개")
    if comp["top"]:
        add("")
        add("| 제목 | 조회수 | 길이 |")
        add("|---|---:|---:|")
        for x in comp["top"]:
            add(f"| {link(x)} | {fmt_int(x['view_count'])} | {fmt_dur(x['duration'])} |")
    add("")

    add("## 6. 채널 상태 판단 근거")
    add("")
    add("| 구분 | 영상 수 | 조회수 중앙값 | 일평균 조회수 중앙값 |")
    add("|---|---:|---:|---:|")
    add(f"| 최근 단편 | {st['recent_n']} | {fmt_int(st['recent_median'])} | {fmt_int(st['recent_daily_median'])} |")
    add(f"| 그 이전 단편 | {st['prev_n']} | {fmt_int(st['prev_median'])} | {fmt_int(st['prev_daily_median'])} |")
    add(f"| 비 (최근/이전) | | {fmt_x(st['median_ratio'])} | {fmt_x(st['daily_ratio'])} |")
    add("")
    add(f"→ **{st['label']}**. (72시간 미만·모음집 제외, 목록 순서 기준)")
    add("")

    add(f"## 7. 축별 평균 조회수 (최신 {len(d['recent'])}개, 72h 미만 제외)")
    add("")
    add("단편만 비교한다. 30분+ 모음집은 형식·길이 축에 '별도' 행으로만 표시하고 격차 계산에서 뺀다. "
        "격차 = n≥2 그룹의 최대 평균 / 최소 평균 (미분류 제외).")
    for axis, ax in d["axes"].items():
        add("")
        add(f"### {ax['name']}")
        add("")
        add("| 그룹 | 개수 | 평균 조회수 | 중앙값 | 영상 |")
        add("|---|---:|---:|---:|---|")
        for g in ax["groups"]:
            label = md(g["value"]) + (" — 30분+ 모음집 (별도 축, 격차 제외)" if g["separate"] else "")
            add(f"| {label} | {g['n']} | {fmt_int(g['mean_views'])} | {fmt_int(g['median_views'])} | "
                f"{', '.join('`' + i + '`' for i in g['ids'])} |")
        gp = ax["gap"]
        add("")
        add(f"격차: {md(gp['high'])} vs {md(gp['low'])} = **{fmt_x(gp['ratio'])}** (차이 {fmt_int(gp['abs'])})"
            if gp else f"격차: — ({ax['note']})")
    add("")

    add("## 8. 격차가 가장 큰 축 → 원인 후보")
    add("")
    ranked = sorted(((ax["name"], ax["gap"]) for ax in d["axes"].values() if ax["gap"]),
                    key=lambda t: -(t[1]["ratio"] or 0))
    if ranked:
        add("| 순위 | 축 | 격차(배) | 높은 그룹 | 낮은 그룹 |")
        add("|---|---|---:|---|---|")
        for i, (name, gp) in enumerate(ranked, 1):
            add(f"| {i} | {name} | {fmt_x(gp['ratio'])} | {md(gp['high'])} ({fmt_int(gp['high_mean'])}) | "
                f"{md(gp['low'])} ({fmt_int(gp['low_mean'])}) |")
        add("")
        add(f"→ 원인 후보: **{lg['name']}** — 이번 에피소드 주제 3개는 '{md(lg['high'])}' 쪽으로 제안하고 승인받는다.")
    else:
        add("비교 가능한 축이 없음 (그룹별 영상 수 부족).")
    add("")

    add("## 9. 최신 상위 3 vs 역대 성공작 포맷")
    add("")
    modes = t3["alltime_modes"]
    add(f"역대 {len(d['top'])}개의 최다 값 — 형식: {md(modes.get('format'))} · 소재: {md(modes.get('topic'))} · "
        f"길이: {md(modes.get('length_bucket'))}")
    add("")
    add(f"| 제목 | 조회수 | 형식 | 소재 | 길이 구간 | 역대 {len(d['top'])}개 중 같은 형식/소재/길이 | 역대 포맷과 동일 |")
    add("|---|---:|---|---|---|---|---|")
    for x in t3["recent_top3"]:
        sc = x["same_count"]
        add(f"| {link(x)} | {fmt_int(x['view_count'])} | {md(x['format'])} | {md(x['topic'])} | "
            f"{md(x['length_bucket'])} | {sc['format']}/{sc['topic']}/{sc['length_bucket']} | "
            f"{'예' if x['same_format_as_alltime'] else '아니오'} |")
    add("")

    tg = d["targets"]
    add("## 10. 다음 단계")
    add("")
    add("1. `labels.template.json` 을 `labels.json` 으로 복사 → 썸네일을 직접 보고 `thumbnail_subject`"
        f"({' / '.join(THUMB_SUBJECTS)}) 를 채우고, 틀린 자동 판정은 고친다 → "
        "`python analyze_channel.py report --dir <이 폴더>` 로 재계산.")
    add("2. `python sample_videos.py --dir <이 폴더>` — 자막·프레임·샷 길이·썸네일 비교 (2단계). 대상: " +
        ", ".join(f"{t['role']} `{t['id']}`" + (f" ({t['reason']})" if t.get("reason") else "") for t in tg["sample"]))
    add("   썸네일 비교 대상: " + ", ".join(f"{t['role']} `{t['id']}`" for t in tg["thumbs"]))
    add("3. 분석이 끝나면 `python sample_videos.py --dir <이 폴더> --cleanup` (영상·프레임 삭제, 재사용 금지).")
    if d.get("samples"):
        add("")
        add(render_samples(d["samples"]))
    return "\n".join(L).rstrip() + "\n"


def render_samples(s: dict) -> str:
    L = ["## 11. 샘플 분석 (2단계)", "", "| 역할 | 영상 | 길이 | 샷 수 | 평균 샷(초) | 표준편차 | 자막 |",
         "|---|---|---:|---:|---:|---:|---|"]
    for t in s.get("targets") or []:
        sh = t.get("shots") or {}
        subs = ", ".join(f"{k}: {v['lines']}줄" if "lines" in v else f"{k}: {v.get('skipped')}"
                         for k, v in (t.get("subs") or {}).items()) or "—"
        L.append(f"| {t.get('role')} | {link(t)} | {fmt_dur((t.get('video') or {}).get('duration'))} | "
                 f"{sh.get('shot_count', '—')} | {sh.get('mean_shot_sec', '—')} | {sh.get('stdev_shot_sec', '—')} | "
                 f"{md(subs, 80)} |")
    if s.get("thumbnails"):
        L += ["", "썸네일: " + ", ".join(f"{t['role']} `{t['id']}` ({t.get('source') or t.get('error')})"
                                        for t in s["thumbnails"])]
    return "\n".join(L)


def labels_template(d: dict) -> dict:
    vids = {}
    for vid, v in d["videos"].items():
        roles = ([f"역대 {v['popular_rank']}"] if v.get("popular_rank") else []) + \
                ([f"최신 {v['recent_rank']}"] if v.get("recent_rank") else [])
        vids[vid] = {"title": v["title"], "role": " / ".join(roles), **v["axes_auto"], "thumbnail_subject": ""}
    return {"_안내": "썸네일을 직접 보고 thumbnail_subject 를 채운 뒤 labels.json 으로 저장하고 "
                   "`python analyze_channel.py report --dir <폴더>` 로 재계산. 값은 자동 판정을 덮어쓴다 (빈 값 = 자동 유지).",
            "_허용값": dict(ALLOWED_LABELS),
            "videos": vids}


# ---------------------------------------------------------------- 자막 (json3)

def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower())).strip()


def json3_rows(data: dict) -> list[tuple[float, float, list[str]]]:
    """json3 events → (시작초, 길이초, 줄 목록). 빈 이벤트(창 정의, 줄바꿈 append)는 건너뜀."""
    out = []
    for ev in data.get("events") or []:
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs)
        rows = [re.sub(r"\s+", " ", r).strip() for r in text.split("\n")]
        rows = [r for r in rows if r]
        if rows:
            out.append((ev.get("tStartMs", 0) / 1000.0, (ev.get("dDurationMs") or 0) / 1000.0, rows))
    return out


def dedupe_rolling(events: list[tuple[float, float, list[str]]]) -> list[tuple[float, str]]:
    """자동 자막의 롤링 중복 제거. 동요의 진짜 반복(다른 시각의 같은 줄)은 남긴다.

    - 여러 줄 이벤트의 앞줄이 직전에 낸 줄들과 같으면 (캐리오버) 버림
    - 직전 줄이 화면에 있는 동안 그 줄 + 새 단어로 자라나면 직전 줄을 교체
    - 같은 줄이 아주 짧은 전환 이벤트(<0.3초)나 같은 시각에 다시 나오면 버림
    """
    lines: list[dict] = []
    for t, d, rows in events:
        norms = [_norm_text(r) for r in rows]
        skip = 0
        if len(rows) > 1:
            for j in range(min(len(rows), len(lines)), 0, -1):
                if norms[:j] == [x["norm"] for x in lines[-j:]]:
                    skip = j
                    break
        for row, norm in list(zip(rows, norms))[skip:]:
            if not norm:
                continue
            last = lines[-1] if lines else None
            if last and len(rows) == 1:
                if t <= last["end"] + 0.05 and norm.startswith(last["norm"] + " "):
                    last.update(text=row, norm=norm, end=max(last["end"], t + d))
                    continue
                if norm == last["norm"] and (d < 0.3 or abs(t - last["t"]) < 0.05):
                    last["end"] = max(last["end"], t + d)
                    continue
            lines.append({"t": t, "end": t + d, "text": row, "norm": norm})
    return [(x["t"], x["text"]) for x in lines]


def fmt_mmss(t: float) -> str:
    tenths = int(round(t * 10))
    return f"{tenths // 600:02d}:{(tenths % 600) / 10:04.1f}"


def json3_to_text(data: dict) -> tuple[str, int]:
    lines = dedupe_rolling(json3_rows(data))
    return "".join(f"[{fmt_mmss(t)}] {text}\n" for t, text in lines), len(lines)


# ---------------------------------------------------------------- 샷

SHOWINFO_RE = re.compile(r"Parsed_showinfo.*?\bpts_time:\s*([0-9]+(?:\.[0-9]+)?)")


def parse_showinfo(stderr: str) -> list[float]:
    return [float(x) for x in SHOWINFO_RE.findall(stderr or "")]


def shot_stats(cuts: list[float], duration: float) -> dict:
    cuts = sorted(c for c in cuts if 0.0 < c < duration)
    bounds = [0.0] + cuts + [duration]
    lengths = [b - a for a, b in zip(bounds, bounds[1:]) if b - a > 0]
    return {"cut_times": [round(c, 3) for c in cuts], "cut_count": len(cuts), "shot_count": len(lengths),
            "mean_shot_sec": round(statistics.fmean(lengths), 3) if lengths else None,
            "stdev_shot_sec": round(statistics.pstdev(lengths), 3) if lengths else None,
            "min_shot_sec": round(min(lengths), 3) if lengths else None,
            "max_shot_sec": round(max(lengths), 3) if lengths else None}
