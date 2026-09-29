#!/usr/bin/env python3
"""1·2단계 (analyze_channel.py / sample_videos.py / momolib.research) 오프라인 테스트.

실행: python3 momo/tests/test_research.py [테스트이름 ...]
pytest·네트워크 불필요 (ffmpeg/ffprobe 필요). yt-dlp 는 MOMO_YTDLP 로 가짜 스크립트를 쓰고,
Data API·썸네일 서버는 127.0.0.1 의 http.server 로 흉내 낸다.
"""
from __future__ import annotations

import http.server
import io
import json
import os
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import traceback
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

MOMO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MOMO))

from PIL import Image  # noqa: E402

from momolib import research as R  # noqa: E402
from momolib.common import MomoError  # noqa: E402

FIX = MOMO / "tests" / "fixtures" / "research"
NOW = "2026-09-20T12:00:00Z"
NOW_DT = R.parse_now(NOW)
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def load(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def fixture_summary(**kw) -> dict:
    opts = dict(url="https://www.youtube.com/@tinytotssing", backend="ytdlp", source="test", limit=2000, top_n=5,
                popular_flat=load(FIX / "channel_popular.json"), fetched_at=NOW_DT)
    opts.update(kw)
    return R.build_summary(load(FIX / "channel.json"), **opts)


def fixture_metas() -> dict:
    return {p.stem: R.trim_meta(load(p)) for p in (FIX / "meta").glob("*.json")}


def new_root(tmp: Path) -> Path:
    root = tmp / "root"
    root.mkdir(parents=True)
    shutil.copy(MOMO / "config.json", root / "config.json")
    return root


def script(name: str, *args: str, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    e = {**os.environ, **(env or {})}
    p = subprocess.run([sys.executable, str(MOMO / name), *args], capture_output=True, text=True, env=e)
    if check and p.returncode != 0:
        raise AssertionError(f"{name} {args} exit {p.returncode}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p


def approx(a, b, tol=1e-6):
    return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(b))


class Server:
    """127.0.0.1 임시 HTTP 서버. handler(path, query) → (status, content_type, bytes)."""

    def __init__(self, handler):
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                u = urllib.parse.urlparse(self.path)
                outer.requests.append(self.path)
                status, ctype, body = handler(u.path, dict(urllib.parse.parse_qsl(u.query)))
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.requests: list[str] = []
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()


FAKE_YTDLP = r'''#!/usr/bin/env python3
import json, os, shutil, sys
from pathlib import Path
args = sys.argv[1:]
fix = Path(os.environ["FAKE_FIX"])
mode = os.environ.get("FAKE_MODE", "ok")
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\n")
def die(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)
def opt(name):
    return args[args.index(name) + 1] if name in args else None
if args == ["--version"]:
    print("2026.08.19"); sys.exit(0)
if args == ["-U"]:
    print(os.environ.get("FAKE_UPDATE_MSG", "Latest version: stable@2026.08.19\nyt-dlp is up to date")); sys.exit(0)
BOT = ("ERROR: [youtube:tab] @tinytotssing: Sign in to confirm you’re not a bot. Use --cookies-from-browser "
       "or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ  RAW-MARKER-7731")
has_cookies = "--cookies" in args or "--cookies-from-browser" in args
if mode == "bot_until_sleep" and "--sleep-requests" not in args: die(BOT)
if mode == "bot_until_cookies" and not has_cookies: die(BOT)
if mode == "always_bot": die(BOT)
if mode == "broken": die("ERROR: Unsupported URL: https://www.youtube.com/@tinytotssing RAW-MARKER-4410")
url = args[-1]
vid = url.split("v=")[-1] if "watch?v=" in url else None
if "--flat-playlist" in args:
    name = "channel_popular.json" if "sort=p" in url else "channel.json"
    if "sort=p" in url and mode == "no_popular_sort":
        name = "channel.json"
    data = json.loads((fix / name).read_text(encoding="utf-8"))
    if opt("--playlist-end"):
        data["entries"] = data["entries"][:int(opt("--playlist-end"))]
    print(json.dumps(data)); sys.exit(0)
if "--write-auto-subs" in args:
    out = opt("-o").replace("%(id)s", vid)
    found = list((fix / "subs").glob(vid + ".*.json3"))
    for f in found:
        shutil.copy(f, out + f.name[len(vid):])
    if not found:
        print("[info] There are no subtitles for the requested languages")
    sys.exit(0)
if "--skip-download" in args and "-J" in args:
    p = fix / "meta" / (vid + ".json")
    if not p.exists() or vid in os.environ.get("FAKE_UNAVAILABLE", ""):
        die("ERROR: [youtube] " + vid + ": Private video. Sign in if you've been granted access to this video")
    print(p.read_text(encoding="utf-8")); sys.exit(0)
if "-f" in args:
    out = opt("-o").replace("%(id)s", vid).replace("%(ext)s", "mp4")
    shutil.copy(os.environ["FAKE_VIDEO"], out); sys.exit(0)
die("fake yt-dlp: unhandled " + " ".join(args))
'''


def fake_env(tmp: Path, mode: str = "ok", **extra) -> dict:
    fake = tmp / "fake_ytdlp.py"
    if not fake.exists():
        fake.write_text(FAKE_YTDLP, encoding="utf-8")
    log = tmp / f"ytdlp_{mode}.log"
    log.unlink(missing_ok=True)
    return {"MOMO_YTDLP": f"{shlex.quote(sys.executable)} {shlex.quote(str(fake))}", "FAKE_FIX": str(FIX),
            "FAKE_MODE": mode, "FAKE_LOG": str(log), **extra}


def fake_calls(env: dict) -> list[list[str]]:
    p = Path(env["FAKE_LOG"])
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def make_cards_video(path: Path) -> list[float]:
    """색 카드 + testsrc2(움직임) 5샷 영상. 반환: 기대 전환 시각."""
    specs = [("color=c=red:", 2.0), ("color=c=blue:", 1.5), ("testsrc2=", 3.0), ("color=c=yellow:", 1.0),
             ("color=c=black:", 2.5)]
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for src, dur in specs:
        cmd += ["-f", "lavfi", "-i", f"{src}s=640x360:r=25:d={dur}"]
    cmd += ["-filter_complex", "".join(f"[{i}]" for i in range(len(specs))) + f"concat=n={len(specs)}:v=1:a=0[v]",
            "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True)
    t, cuts = 0.0, []
    for _, dur in specs[:-1]:
        t += dur
        cuts.append(t)
    return cuts


def jpeg(w: int, h: int, color=(200, 80, 80)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "JPEG")
    return buf.getvalue()


# ================================================================ 단위

@test
def test_helpers():
    assert R.parse_iso_duration("PT2M45S") == 165
    assert R.parse_iso_duration("PT1H2M3S") == 3723
    assert R.parse_iso_duration("P1DT2H") == 93600
    assert R.parse_iso_duration("PT45.5S") == 46
    assert R.parse_iso_duration("P0D") == 0
    assert R.parse_iso_duration("") is None and R.parse_iso_duration("garbage") is None

    ok = {"https://www.youtube.com/@Pinkish/videos": "https://www.youtube.com/@Pinkish",
          "@handle": "https://www.youtube.com/@handle",
          "youtube.com/channel/UCtInYt0tsS1ngA10ngF1xtr/featured?x=1":
              "https://www.youtube.com/channel/UCtInYt0tsS1ngA10ngF1xtr",
          "https://m.youtube.com/c/SomeName": "https://www.youtube.com/c/SomeName",
          "https://www.youtube.com/user/old": "https://www.youtube.com/user/old"}
    for src, want in ok.items():
        assert R.normalize_channel_url(src) == want, (src, R.normalize_channel_url(src))
    for bad in ("https://www.youtube.com/watch?v=abcdefghijk", "https://youtu.be/abcdefghijk",
                "https://www.youtube.com/shorts/abcdefghijk", "https://example.com/@x", "https://www.youtube.com/"):
        try:
            R.normalize_channel_url(bad)
        except MomoError:
            continue
        raise AssertionError(f"거부해야 함: {bad}")
    assert R.channel_slug("https://www.youtube.com/@TinyTots") == "tinytots"
    assert R.channel_slug("https://www.youtube.com/@%ED%86%A0%EB%81%BC") == "토끼"
    assert R.channel_slug(None, "@x_y") == "x_y"

    assert R.fmt_mmss(0) == "00:00.0" and R.fmt_mmss(59.96) == "01:00.0" and R.fmt_mmss(4521.34) == "75:21.3"
    assert [R.length_bucket(x) for x in (180, 181, 600, 1799, 1800, None)] == \
        ["≤3분", "3~10분", "3~10분", "10~30분", "30분+", R.UNCLASSIFIED]
    assert R.md("a | b [c]") == "a \\| b \\[c\\]"
    assert R.parse_now("2026-09-20T12:00:00Z") == datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
    assert R.parse_now("2026-09-20T21:00:00+09:00").timestamp() == NOW_DT.timestamp()
    assert R.parse_now("2026-09-20 12:00").tzinfo is not None

    chk = R.check_descending([{"view_count": v} for v in (9, 9, 5, 3, 1)])
    assert chk["descending"] and chk["inversions"] == 0
    assert not R.check_descending([{"view_count": v} for v in (9, 10, 5, 3, 1)])["descending"]
    assert not R.check_descending([{"view_count": None}] * 6)["descending"]


@test
def test_classify():
    ax, m = R.classify("Colors Song for Toddlers | Learn Red, Yellow, Blue", ["kids songs"], 165)
    assert (ax["topic"], ax["format"], ax["length_bucket"], ax["search_keyword"]) == ("색", "동요", "≤3분", True)
    assert "toddlers" in m["search_keyword"]
    ax, _ = R.classify("동물 소리 퀴즈! 누구일까요? | 유아 동요", [], 200)
    assert (ax["topic"], ax["format"]) == ("동물", "퀴즈·따라하기")
    ax, _ = R.classify("Five Little Ducks | Counting Song for Kids", [], 170)
    assert ax["topic"] == "숫자"  # counting 2개 > ducks 1개
    ax, _ = R.classify("인기 동요 모음 45분 연속 듣기", [], 2710)
    assert ax["format"] == "모음집" and ax["length_bucket"] == "30분+"
    ax, m = R.classify("Old MacDonald Had a Farm", ["nursery rhymes"], 155)
    assert ax["format"] == "동요" and m["format"][0].startswith("#") and ax["search_keyword"] is False
    ax, _ = R.classify("양치 송 | 치카치카 생활습관", [], 150)
    assert ax["topic"] == "생활습관"
    ax, _ = R.classify("한글 모음 배우기", [], 150)  # '모음'(모음자)은 모음집이 아님
    assert ax["topic"] == "알파벳·단어" and ax["format"] == R.UNCLASSIFIED
    ax, _ = R.classify("Rainbow Bus Story", [], 300)
    assert ax["format"] == "스토리"
    ax, _ = R.classify("Something", [], 100)
    assert ax["topic"] == R.TOPIC_OTHER and ax["thumbnail_subject"] == R.UNCLASSIFIED


@test
def test_json3_dedupe():
    text, n = R.json3_to_text(load(next((FIX / "subs").glob("*.en.json3"))))
    assert text.splitlines() == [
        "[00:00.5] [Music]",
        "[00:02.0] red, red, what do you see?",
        "[00:04.1] I see a yellow sun",
        "[00:06.1] looking at me",
        "[00:08.2] round and round",
        "[00:10.0] round and round",
        "[00:11.8] round and round",
        "[00:13.6] Can you say blue?",
        "[00:19.0] Blue!",
        "[01:05.5] Bye bye, friends!",
    ], text
    assert n == 10
    text, n = R.json3_to_text(load(next((FIX / "subs").glob("*.ko.json3"))))
    assert text.splitlines() == ["[00:01.0] 안녕 친구들", "[00:03.0] 오늘은 색깔을 배워요", "[00:05.0] 빨강!",
                                 "[00:07.0] 빨강!"], text
    assert R.json3_to_text({"events": []}) == ("", 0)


@test
def test_shots_parse():
    err = ("[Parsed_showinfo_1 @ 0x55] n:   0 pts:  51200 pts_time:2       duration: 512 fmt:yuv420p\n"
           "[Parsed_showinfo_1 @ 0x55] n:   1 pts:  90112 pts_time:3.52    duration: 512\n"
           "frame=  250 fps=0.0 q=-0.0 Lsize=N/A time=00:00:09.96\n")
    assert R.parse_showinfo(err) == [2.0, 3.52]
    st = R.shot_stats([2.0, 3.52, 99.0], 10.0)
    assert st["cut_count"] == 2 and st["shot_count"] == 3
    assert approx(st["mean_shot_sec"], 10 / 3, 1e-3)
    assert approx(st["stdev_shot_sec"], round(statistics.pstdev([2.0, 1.52, 6.48]), 3), 1e-3)
    assert R.shot_stats([], 5.0)["shot_count"] == 1


def _status_rows(recent, prev, recent_age=20, prev_age=200):
    rows = []
    for i, v in enumerate(recent + prev):
        rows.append({"list_index": i, "is_compilation": False, "is_new": False, "view_count": v,
                     "age_hours": (recent_age if i < len(recent) else prev_age) * 24, "id": f"v{i}"})
    return rows


@test
def test_status_rule():
    S = lambda rec, prev, **kw: R._status(_status_rows(rec, prev, **kw), 0, 15)  # noqa: E731
    assert S([300] * 15, [200] * 45)["label"] == "성장"                        # 중앙값 비 1.5
    assert S([160] * 15, [200] * 45, recent_age=10)["label"] == "성장"         # 0.8, 일평균 16
    assert S([120] * 15, [200] * 45)["label"] == "정체"                        # 0.6
    assert S([60] * 15, [200] * 45, recent_age=100)["label"] == "하락"         # 0.3, 일평균 0.6
    assert S([60] * 15, [200] * 45, recent_age=20)["label"] == "정체"          # 0.3 이지만 일평균 3.0
    assert S([100] * 10, [])["label"] == "판단 불가" and S([100] * 2, [])["recent_n"] == 2
    st = S([100] * 15, [200] * 45)
    assert st["recent_n"] == 15 and st["prev_n"] == 45 and approx(st["median_ratio"], 0.5)
    # 날짜가 없으면 일평균 없이 중앙값 비 < 0.3 만 하락
    rows = _status_rows([50] * 15, [200] * 45)
    for r in rows:
        r["age_hours"] = None
    st = R._status(rows, 0, 15)
    assert st["daily_ratio"] is None and st["label"] == "하락"


# ================================================================ 분석 (고정 픽스처)

@test
def test_analyze_fixture():
    flat = load(FIX / "channel.json")
    entries = flat["entries"]
    metas = fixture_metas()
    d = R.analyze(fixture_summary(), metas, now=NOW_DT)
    views = {e["id"]: (metas[e["id"]]["view_count"] if e["id"] in metas else e["view_count"]) for e in entries}

    # 인기순: sort=p 결과가 내림차순 → 그 상위 5
    pop = load(FIX / "channel_popular.json")["entries"]
    assert d["popular"]["method"] == "sort=p" and d["popular"]["check"]["descending"]
    assert d["top"] == sorted([e["id"] for e in pop[:5]], key=lambda i: -views[i])
    assert d["top"][0] == "tts060VidI0"

    # 72시간 미만 3개 제외, 모음집 6개 분리
    new_ids = [m["id"] for m in metas.values() if (NOW_DT.timestamp() - m["timestamp"]) / 3600 < 72]
    assert sorted(x["id"] for x in d["excluded_new"]) == sorted(new_ids) and len(new_ids) == 3
    comps = [e["id"] for e in entries if e["duration"] >= 1800]
    assert d["compilations"]["count"] == len(comps) == 6

    # 최근 단편 평균 (최신 15 중 72h 미만·모음집 제외)
    rs = [e["id"] for e in entries[:15] if e["id"] not in new_ids and e["duration"] < 1800]
    avg = statistics.fmean(views[i] for i in rs)
    m = d["metrics"]
    assert m["recent_short_n"] == len(rs) == 10 and approx(m["recent_short_avg"], avg)
    assert approx(m["best_vs_recent_avg"], views["tts060VidI0"] / avg)
    assert m["best_short"]["id"] == "tts040VidO0"
    assert approx(m["best_short_vs_recent_avg"], views["tts040VidO0"] / avg)
    assert approx(m["best_per_subscriber"], views["tts060VidI0"] / 1240000)
    assert approx(m["recent_avg_per_subscriber"], avg / 1240000)
    assert approx(m["top_share"], sum(views[i] for i in d["top"]) / sum(views.values()))

    # 채널 상태: 최근 15 단편 vs 이전 45 단편 (독립 계산)
    shorts = [e["id"] for e in entries if e["duration"] < 1800 and e["id"] not in new_ids]
    rm, pm = statistics.median(views[i] for i in shorts[:15]), statistics.median(views[i] for i in shorts[15:60])
    st = d["status"]
    assert st["recent_ids"] == shorts[:15] and st["prev_ids"] == shorts[15:60]
    assert approx(st["recent_median"], rm) and approx(st["prev_median"], pm)
    assert st["daily_ratio"] is not None and st["daily_ratio"] > 1.0 and st["median_ratio"] < 0.5
    assert st["label"] == "정체"

    # 축: 학습 소재 격차가 가장 큼 (색 4개 vs 동물 3개)
    topic = d["axes"]["topic"]
    color = [i for i in rs if d["videos"][i]["axes"]["topic"] == "색"]
    animal = [i for i in rs if d["videos"][i]["axes"]["topic"] == "동물"]
    assert len(color) == 4 and len(animal) == 3
    want = statistics.fmean(views[i] for i in color) / statistics.fmean(views[i] for i in animal)
    assert approx(topic["gap"]["ratio"], want) and topic["gap"]["high"] == "색"
    assert d["largest_gap_axis"]["axis"] == "topic"
    assert d["axes"]["thumbnail_subject"]["gap"] is None
    fmt_groups = {(g["value"], g["separate"]): g["n"] for g in d["axes"]["format"]["groups"]}
    assert fmt_groups[("모음집", True)] == 2  # 최신 15의 30분+ 모음집은 별도 행
    assert sum(g["n"] for g in topic["groups"]) == 10  # 소재 축은 단편만

    # 최신 상위 3 vs 역대 포맷
    t3 = d["top3_vs_alltime"]
    assert t3["alltime_modes"] == {"format": "모음집", "topic": "색", "length_bucket": "30분+"}
    assert [x["id"] for x in t3["recent_top3"]] == ["tts012VidM2", "tts005VidF5", "tts006VidG6"]
    assert [x["same_format_as_alltime"] for x in t3["recent_top3"]] == [False, True, False]

    # 2단계 대상: 1위가 30분+ 모음집 → 단편 1위로
    assert [t["id"] for t in d["targets"]["sample"]] == ["tts040VidO0", "tts006VidG6"]
    th = d["targets"]["thumbs"]
    assert [t["role"] for t in th] == ["역대 1위", "역대 2위", "최근 1위", "최근 최하위"]
    assert len({t["id"] for t in th}) == 4 and th[3]["id"] == "tts011VidL1"
    assert len(d["videos"]) == 20

    md = R.render_report(d)
    for s in ("채널 상태 | **정체**", "sort=p", "72시간 미만", "모음집 축", "격차가 가장 큰 축", "학습 소재",
              "\\| Learn Colors", "최신 상위 3"):
        assert s in md, s
    tpl = R.labels_template(d)
    assert len(tpl["videos"]) == 20 and all(v["thumbnail_subject"] == "" for v in tpl["videos"].values())
    assert tpl["videos"]["tts003VidD3"]["topic"] == "색"


@test
def test_popular_fallback_and_truncation():
    # sort=p 가 최신순 그대로 돌아오면 → 목록 조회수 정렬
    s = fixture_summary(popular_flat=load(FIX / "channel.json"))
    assert s["popular"]["method"] == "view_count_sort" and not s["popular"]["check"]["descending"]
    entries = load(FIX / "channel.json")["entries"]
    assert s["popular"]["ids"] == [e["id"] for e in sorted(entries, key=lambda e: -e["view_count"])[:5]]
    s = fixture_summary(popular_flat=None, popular_note="오프라인")
    assert s["popular"]["method"] == "view_count_sort" and "오프라인" in s["popular"]["note"]
    # 예정 프리미어·라이브 중은 목록에서 뺀다 (조회수 없음, 최신 15 자리 차지 방지)
    flat = load(FIX / "channel.json")
    flat["entries"].insert(0, {**flat["entries"][0], "id": "tts999Upcom", "view_count": None,
                               "live_status": "is_upcoming"})
    s = R.build_summary(flat, url=None, backend="ytdlp", source="t", limit=2000, top_n=5)
    assert s["listed"] == 70 and s["entries"][0]["id"] == "tts000VidA0"
    # 상한에 걸리면 일부 기준
    flat = load(FIX / "channel.json")
    flat["entries"] = flat["entries"][:40]
    s = R.build_summary(flat, url=None, backend="ytdlp", source="t", limit=40, top_n=5,
                        popular_flat=load(FIX / "channel_popular.json"))
    assert s["truncated"]
    d = R.analyze(s, fixture_metas(), now=NOW_DT)
    assert d["channel"]["partial"] and "일부 기준" in R.render_report(d)
    assert "tts060VidI0" in d["top"]  # 목록 밖(60번째)이지만 인기순에는 있음
    assert d["metrics"]["listed_total_views"] > sum(e["view_count"] for e in flat["entries"]) - 1


@test
def test_age_inference():
    flat = load(FIX / "channel.json")
    for e in flat["entries"]:
        e.pop("timestamp", None)
    s = R.build_summary(flat, url=None, backend="ytdlp", source="t", limit=2000, top_n=5,
                        popular_flat=load(FIX / "channel_popular.json"))
    assert s["dates"] == "none"
    metas = fixture_metas()
    for vid in ("tts000VidA0", "tts009VidJ9"):  # 첫 영상과 중간 영상의 메타가 없다고 가정
        metas.pop(vid)
    d = R.analyze(s, metas, now=NOW_DT)
    v = d["videos"]
    assert v["tts000VidA0"]["is_new"] is None and d["unknown_age"] == ["tts000VidA0"]
    assert v["tts009VidJ9"]["is_new"] is False and v["tts009VidJ9"]["date_source"] == "inferred"
    assert v["tts001VidB1"]["is_new"] is True
    assert d["status"]["prev_daily_median"] is None  # 이전 45개는 날짜 없음
    # upload_date 만 있으면 그날 끝으로 보수 판정 (71시간 전 날짜 → 제외)
    m = fixture_metas()
    m["tts003VidD3"].pop("timestamp")
    m["tts003VidD3"]["upload_date"] = datetime.fromtimestamp(NOW_DT.timestamp() - 71 * 3600,
                                                             timezone.utc).strftime("%Y%m%d")
    d = R.analyze(fixture_summary(), m, now=NOW_DT)
    assert d["videos"]["tts003VidD3"]["is_new"] is True


@test
def test_labels(tmp: Path):
    lab = {"_안내": "x", "videos": {
        "tts003VidD3": {"thumbnail_subject": "캐릭터 클로즈업"}, "tts006VidG6": {"thumbnail_subject": "캐릭터 클로즈업"},
        "tts009VidJ9": {"thumbnail_subject": "텍스트 위주"}, "tts014VidO4": {"thumbnail_subject": "캐릭터 클로즈업"},
        "tts004VidE4": {"thumbnail_subject": "사물"}, "tts007VidH7": {"thumbnail_subject": "사물"},
        "tts008VidI8": {"thumbnail_subject": "사물", "topic": "감정", "search_keyword": "미포함"},
        "tts010VidK0": {"thumbnail_subject": "사물", "topic": ""},
    }}
    p = tmp / "labels.json"
    p.write_text(json.dumps(lab, ensure_ascii=False), encoding="utf-8")
    labels = R.load_labels(p)
    assert labels["tts008VidI8"] == {"thumbnail_subject": "사물", "topic": "감정", "search_keyword": False}
    assert labels["tts010VidK0"] == {"thumbnail_subject": "사물"}
    d = R.analyze(fixture_summary(), fixture_metas(), labels, now=NOW_DT)
    v = d["videos"]["tts008VidI8"]
    assert v["axes"]["topic"] == "감정" and v["axes_auto"]["topic"] == "생활습관"
    assert v["labeled"] == ["search_keyword", "thumbnail_subject", "topic"]
    th = d["axes"]["thumbnail_subject"]
    assert th["gap"] and th["gap"]["high"] == "캐릭터 클로즈업" and th["gap"]["low"] == "사물"
    assert {g["value"]: g["n"] for g in th["groups"]} == {"캐릭터 클로즈업": 3, "텍스트 위주": 1, "사물": 4,
                                                           R.UNCLASSIFIED: 2}
    lab["videos"]["tts003VidD3"]["format"] = "뮤직비디오"
    p.write_text(json.dumps(lab, ensure_ascii=False), encoding="utf-8")
    try:
        R.load_labels(p)
    except MomoError as e:
        assert "허용값" in str(e)
    else:
        raise AssertionError("허용값 밖 label 은 거부해야 함")


# ================================================================ CLI (오프라인)

@test
def test_cli_offline_and_report(tmp: Path):
    root = new_root(tmp)
    p = script("analyze_channel.py", "--root", str(root), "--offline-json", str(FIX / "channel.json"),
               "--offline-popular", str(FIX / "channel_popular.json"), "--now", NOW)
    out = root / "research" / "tinytotssing"
    assert "채널 상태: 정체" in p.stdout and "격차 최대 축: 학습 소재" in p.stdout
    for f in ("report.md", "data.json", "channel_summary.json", "labels.template.json"):
        assert (out / f).exists(), f
    assert not (out / "raw").exists()  # 오프라인 입력은 복사하지 않음
    assert len(list((out / "meta").glob("*.json"))) == 20
    meta = load(out / "meta" / "tts003VidD3.json")
    assert set(meta) == set(R.META_FIELDS)  # 필요한 필드만
    summ = load(out / "channel_summary.json")
    assert set(summ["entries"][0]) <= {"id", "title", "view_count", "duration", "timestamp"}
    assert summ["channel"]["subscribers"] == 1240000
    d = load(out / "data.json")
    assert d["now"] == NOW and d["popular"]["method"] == "sort=p" and d["status"]["label"] == "정체"

    # labels.json 을 채우고 report 로 재계산 (네트워크 없음, 기준 시각 유지, samples 보존)
    tpl = load(out / "labels.template.json")
    for vid in tpl["videos"]:
        tpl["videos"][vid]["thumbnail_subject"] = "캐릭터 클로즈업" if vid < "tts008" else "사물"
    (out / "labels.json").write_text(json.dumps(tpl, ensure_ascii=False), encoding="utf-8")
    d["samples"] = {"marker": 1}
    (out / "data.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    p = script("analyze_channel.py", "report", "--dir", "research/tinytotssing", "--root", str(root))
    assert "labels 적용" in p.stdout
    d2 = load(out / "data.json")
    assert d2["now"] == NOW and d2["samples"] == {"marker": 1}
    assert d2["axes"]["thumbnail_subject"]["gap"] is not None
    assert "캐릭터 클로즈업" in (out / "report.md").read_text(encoding="utf-8")

    p = script("analyze_channel.py", "report", "--dir", str(tmp / "nope"), "--root", str(root), check=False)
    assert p.returncode == 1 and "channel_summary.json 없음" in p.stderr
    p = script("analyze_channel.py", "--root", str(root), "--url", "https://www.youtube.com/watch?v=abcdefghijk",
               check=False)
    assert p.returncode == 1 and "채널 링크" in p.stderr


@test
def test_offline_remote_layout(tmp: Path):
    """remote_research.py 가 받아온 배치 (research/<slug>/raw + meta) 에서 제자리 분석. 입력은 그대로 둔다."""
    root = new_root(tmp)
    out = root / "research" / "tinytotssing"
    (out / "raw").mkdir(parents=True)
    shutil.copy(FIX / "channel.json", out / "raw" / "channel.json")
    shutil.copy(FIX / "channel_popular.json", out / "raw" / "popular.json")
    shutil.copytree(FIX / "meta", out / "meta")
    before = {p.name: p.read_bytes() for p in (out / "meta").glob("*.json")}
    raw_before = (out / "raw" / "channel.json").read_bytes()
    elsewhere = tmp / "cwd"
    elsewhere.mkdir()
    p = subprocess.run([sys.executable, str(MOMO / "analyze_channel.py"), "--root", str(root),
                        "--offline-json", "research/tinytotssing/raw/channel.json",
                        "--offline-popular", "research/tinytotssing/raw/popular.json", "--now", NOW],
                       capture_output=True, text=True, cwd=elsewhere)
    assert p.returncode == 0, p.stderr
    assert {p.name: p.read_bytes() for p in (out / "meta").glob("*.json")} == before
    assert (out / "raw" / "channel.json").read_bytes() == raw_before
    d = load(out / "data.json")
    assert d["popular"]["method"] == "sort=p" and d["status"]["label"] == "정체" and not d["fetch"]["meta_failures"]
    assert d["videos"]["tts003VidD3"]["tags"] == ["colors", "kids songs"]  # 메타(../meta)를 찾아 씀
    script("analyze_channel.py", "report", "--dir", str(out), "--root", str(root))
    assert load(out / "data.json")["metrics"] == d["metrics"]


# ================================================================ yt-dlp 경로 (가짜 yt-dlp)

@test
def test_ytdlp_pipeline(tmp: Path):
    root = new_root(tmp)
    env = fake_env(tmp, "ok", FAKE_UNAVAILABLE="tts047VidV7")
    p = script("analyze_channel.py", "--root", str(root), "--url", "https://www.youtube.com/@tinytotssing/videos",
               "--now", NOW, "--limit", "2000", env=env)
    calls = fake_calls(env)
    assert calls[0] == ["--version"] and calls[1] == ["-U"]  # 갱신 시도 먼저
    flat = next(c for c in calls if "--flat-playlist" in c and c[-1].endswith("/videos"))
    assert flat[-1] == "https://www.youtube.com/@tinytotssing/videos"
    assert "youtubetab:approximate_date" in flat and flat[flat.index("--playlist-end") + 1] == "2000"
    assert any(c[-1].endswith("/videos?view=0&sort=p&flow=grid") for c in calls)
    metas = [c for c in calls if "--skip-download" in c and "-J" in c]
    assert len(metas) == 20 and not any("--sleep-requests" in c for c in calls)
    d = load(root / "research" / "tinytotssing" / "data.json")
    assert d["popular"]["method"] == "sort=p" and d["backend"] == "ytdlp"
    assert d["fetch"]["meta_failures"][0]["id"] == "tts047VidV7" and "Private video" in \
        d["fetch"]["meta_failures"][0]["error"]
    assert d["fetch"]["ytdlp"]["update"]["self_update"]["exit"] == 0
    assert "개별 메타 없음 1개" in p.stdout

    # sort=p 가 먹히지 않는 경우
    env = fake_env(tmp, "no_popular_sort")
    script("analyze_channel.py", "--root", str(root), "--url", "@tinytotssing", "--now", NOW, "--no-update",
           "--out", str(tmp / "o2"), env=env)
    d = load(tmp / "o2" / "data.json")
    assert d["popular"]["method"] == "view_count_sort" and "내림차순이 아님" in d["popular"]["note"]
    assert fake_calls(env)[0] != ["-U"]


@test
def test_ytdlp_escalation(tmp: Path):
    root = new_root(tmp)
    url = "https://www.youtube.com/@tinytotssing"
    # 1) 봇 확인 → --sleep-requests 1 로 재시도하면 통과 (이후 호출도 sleep 유지)
    env = fake_env(tmp, "bot_until_sleep")
    p = script("analyze_channel.py", "--root", str(root), "--url", url, "--now", NOW, "--no-update",
               "--out", str(tmp / "a"), env=env)
    calls = [c for c in fake_calls(env) if c != ["--version"]]
    assert "--sleep-requests" not in calls[0] and all("--sleep-requests" in c for c in calls[1:])
    assert "--sleep-requests 1 추가" in p.stdout
    assert load(tmp / "a" / "data.json")["fetch"]["ytdlp"]["escalations"] == ["sleep-requests"]
    # 2) sleep 으로도 안 되면 쿠키로
    cookies = tmp / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n")
    env = fake_env(tmp, "bot_until_cookies")
    script("analyze_channel.py", "--root", str(root), "--url", url, "--now", NOW, "--no-update",
           "--cookies", str(cookies), "--out", str(tmp / "b"), env=env)
    calls = [c for c in fake_calls(env) if c != ["--version"]]
    assert "--cookies" not in calls[0] and "--sleep-requests" in calls[1] and "--cookies" not in calls[1]
    assert calls[2][calls[2].index("--cookies") + 1] == str(cookies)
    assert load(tmp / "b" / "data.json")["fetch"]["ytdlp"]["escalations"] == ["sleep-requests", "cookies"]
    # 3) 쿠키까지 실패 → 에러 원문 그대로 중단
    env = fake_env(tmp, "always_bot")
    p = script("analyze_channel.py", "--root", str(root), "--url", url, "--now", NOW, "--no-update",
               "--cookies-from-browser", "chrome", "--out", str(tmp / "c"), env=env, check=False)
    assert p.returncode == 1
    assert "Sign in to confirm you’re not a bot" in p.stderr and "RAW-MARKER-7731" in p.stderr
    assert "기본 → --sleep-requests 1 → 쿠키" in p.stderr
    assert len(fake_calls(env)) == 3 and not (tmp / "c").exists()
    # 4) 쿠키가 없으면 안내와 함께 중단 (2회 시도)
    env = fake_env(tmp, "always_bot")
    p = script("analyze_channel.py", "--root", str(root), "--url", url, "--no-update", env=env, check=False)
    assert p.returncode == 1 and "--cookies-from-browser chrome" in p.stderr and len(fake_calls(env)) == 2
    # 5) 봇이 아닌 에러는 재시도 없이 원문으로 중단
    env = fake_env(tmp, "broken")
    p = script("analyze_channel.py", "--root", str(root), "--url", url, "--no-update", env=env, check=False)
    assert p.returncode == 1 and "RAW-MARKER-4410" in p.stderr and len(fake_calls(env)) == 1


@test
def test_update_pip_branch(tmp: Path):
    fake_py = tmp / "fake_python.sh"
    pip_log = tmp / "pip.log"
    fake_py.write_text(f"#!/bin/sh\necho \"$@\" >> {shlex.quote(str(pip_log))}\n"
                       'case "$3" in show) echo "Name: yt-dlp";; '
                       "install) echo 'Successfully installed yt-dlp-2099.1.1';; esac\n")
    fake_py.chmod(0o755)

    def update(msg: str | None) -> tuple[dict, list[str], list[str]]:
        env = fake_env(tmp, "ok", **({"FAKE_UPDATE_MSG": msg} if msg else {}))
        pip_log.unlink(missing_ok=True)
        saved_env, saved_exe = dict(os.environ), sys.executable
        os.environ.update(env)
        sys.executable = str(fake_py)
        try:
            msgs: list[str] = []
            res = R.update_ytdlp(msgs.append)
        finally:
            sys.executable = saved_exe
            os.environ.clear()
            os.environ.update(saved_env)
        return res, msgs, pip_log.read_text().splitlines() if pip_log.exists() else []

    # -U 가 pip 설치본이라고 알려주면 바로 pip
    res, msgs, pip = update("ERROR: You installed yt-dlp with pip or using the wheel from PyPi; Use that to update")
    assert res["pip"]["exit"] == 0 and "Successfully installed" in res["pip"]["output"]
    assert pip == ["-m pip install -U yt-dlp"] and res["after"] == "2026.08.19"
    assert any("pip install -U yt-dlp" in m for m in msgs)
    # -U 가 네트워크 등으로 실패 + pip 설치본이면 pip
    res, msgs, pip = update("ERROR: Unable to obtain version info ([SSL: CERTIFICATE_VERIFY_FAILED]); "
                            "Please try again later")
    assert pip == ["-m pip show yt-dlp", "-m pip install -U yt-dlp"] and res["pip"]["exit"] == 0
    # 최신이면 pip 안 건드림
    res, msgs, pip = update(None)
    assert pip == [] and "pip" not in res and res["self_update"]["exit"] == 0


# ================================================================ Data API 백엔드 (로컬 흉내)

def api_handler(key: str):
    flat = load(FIX / "channel.json")
    metas = {p.stem: load(p) for p in (FIX / "meta").glob("*.json")}
    cid = flat["channel_id"]
    ids = [e["id"] for e in flat["entries"]] + ["tts999Upcom"]
    by_id = {e["id"]: e for e in flat["entries"]}

    def iso_dur(s):
        h, rem = divmod(int(s), 3600)
        m, s = divmod(rem, 60)
        return f"PT{h}H{m}M{s}S" if h else f"PT{m}M{s}S"

    def video(vid):
        if vid == "tts999Upcom":
            return {"id": vid, "snippet": {"title": "Premiere", "publishedAt": "2026-09-21T00:00:00Z",
                                           "liveBroadcastContent": "upcoming"},
                    "statistics": {}, "contentDetails": {"duration": "P0D"}}
        e, m = by_id[vid], metas.get(vid, {})
        ts = m.get("timestamp") or e["timestamp"]
        return {"id": vid, "snippet": {
            "title": e["title"], "publishedAt": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tags": m.get("tags", []), "description": m.get("description", ""), "categoryId": "27",
            "liveBroadcastContent": "none",
            "thumbnails": {"high": {"url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}}},
            "statistics": {"viewCount": str(m.get("view_count") or e["view_count"]), "likeCount": "10"},
            "contentDetails": {"duration": iso_dur(e["duration"])}}

    def handler(path, q):
        J = lambda code, obj: (code, "application/json", json.dumps(obj).encode())  # noqa: E731
        if q.get("key") == "quotakey":
            return J(403, {"error": {"code": 403, "message": "The request cannot be completed because you have "
                                     "exceeded your quota.", "errors": [{"reason": "quotaExceeded"}]}})
        if q.get("key") != key:
            return J(400, {"error": {"code": 400, "message": "API key not valid."}})
        ep = path.rsplit("/", 1)[-1]
        if ep == "channels":
            assert q.get("forHandle") == "@tinytotssing", q
            return J(200, {"items": [{"id": cid, "snippet": {"title": flat["channel"], "customUrl": "@tinytotssing"},
                                      "statistics": {"subscriberCount": "1240000", "hiddenSubscriberCount": False},
                                      "contentDetails": {"relatedPlaylists": {"uploads": "UU" + cid[2:]}}}]})
        if ep == "playlistItems":
            if q["playlistId"].startswith("UULF"):
                return J(404, {"error": {"code": 404, "errors": [{"reason": "playlistNotFound"}]}})
            start = int(q.get("pageToken") or 0)
            page = ids[start:start + int(q["maxResults"])]
            body = {"items": [{"contentDetails": {"videoId": v}} for v in page],
                    "pageInfo": {"totalResults": len(ids)}}
            if start + len(page) < len(ids):
                body["nextPageToken"] = str(start + len(page))
            return J(200, body)
        if ep == "videos":
            return J(200, {"items": [video(v) for v in q["id"].split(",")]})
        return J(404, {"error": {"code": 404}})

    return handler


@test
def test_api_backend(tmp: Path):
    root = new_root(tmp)
    key = "testkey-SECRET-123"
    with Server(api_handler(key)) as srv:
        env = {"MOMO_YT_API_BASE": srv.url + "/youtube/v3", "YOUTUBE_API_KEY": key}
        p = script("analyze_channel.py", "--root", str(root), "--url", "https://www.youtube.com/@tinytotssing",
                   "--backend", "api", "--now", NOW, env=env)
        assert key not in p.stdout + p.stderr and "UULF" in p.stdout
        out = root / "research" / "tinytotssing"
        d = load(out / "data.json")
        assert d["backend"] == "api" and d["popular"]["method"] == "api_sorted"
        assert d["top"] == ["tts060VidI0", "tts040VidO0", "tts033VidH3", "tts020VidU0", "tts047VidV7"]
        assert d["channel"]["subscribers"] == 1240000 and d["channel"]["dates"] == "exact"
        assert d["channel"]["listed"] == 70  # 예정 라이브(upcoming) 제외
        assert d["status"]["label"] == "정체" and d["largest_gap_axis"]["axis"] == "topic"
        m = load(out / "meta" / "tts003VidD3.json")
        assert m["duration"] == 165 and m["tags"] == ["colors", "kids songs"] and m["categories"] == ["Education"]
        for f in out.rglob("*.json"):
            assert key not in f.read_text(encoding="utf-8"), f
        assert "YouTube Data API v3" in (out / "report.md").read_text(encoding="utf-8")
        # API 에러는 응답 원문 그대로 (키는 가림)
        p = script("analyze_channel.py", "--root", str(root), "--url", "@tinytotssing", "--backend", "api",
                   env={**env, "YOUTUBE_API_KEY": "quotakey"}, check=False)
        assert p.returncode == 1 and "quotaExceeded" in p.stderr and "HTTP 403" in p.stderr
        assert "quotakey" not in p.stderr
    p = script("analyze_channel.py", "--root", str(root), "--url", "@x", "--backend", "api",
               env={"YOUTUBE_API_KEY": ""}, check=False)
    assert p.returncode == 1 and "YOUTUBE_API_KEY" in p.stderr


# ================================================================ 2단계

def thumb_handler(path, q):
    parts = path.strip("/").split("/")  # vi/<id>/<name>
    vid, name = parts[1], parts[2]
    if vid == "tts060VidI0":
        return 200, "image/jpeg", jpeg(1280, 720)
    if vid == "tts012VidM2" and name == "maxresdefault.jpg":
        return 200, "image/jpeg", jpeg(120, 90, (128, 128, 128))  # 자리표시
    if name == "hqdefault.jpg" and vid != "tts011VidL1":
        return 200, "image/jpeg", jpeg(480, 360)
    return 404, "text/plain", b"not found"


@test
def test_sample_videos_local(tmp: Path):
    root = new_root(tmp)
    script("analyze_channel.py", "--root", str(root), "--offline-json", str(FIX / "channel.json"),
           "--offline-popular", str(FIX / "channel_popular.json"), "--now", NOW)
    out = root / "research" / "tinytotssing"
    video = tmp / "cards.mp4"
    want_cuts = make_cards_video(video)
    with Server(thumb_handler) as srv:
        p = script("sample_videos.py", "--root", str(root), "--dir", "research/tinytotssing",
                   "--local-video", str(video), "--local-subs", str(FIX / "subs"), "--frames", "50",
                   env={"MOMO_YT_THUMB_BASE": srv.url + "/vi"})
    assert "40장으로 조정" in p.stdout
    s = load(out / "samples.json")
    assert [t["id"] for t in s["targets"]] == ["tts040VidO0", "tts006VidG6"]
    for t in s["targets"]:
        sh = t["shots"]
        assert sh["cut_count"] == len(want_cuts) == 4 and sh["shot_count"] == 5, sh
        assert all(abs(a - b) < 0.1 for a, b in zip(sh["cut_times"], want_cuts)), sh["cut_times"]
        assert approx(sh["mean_shot_sec"], 2.0, 0.02) and sh["stdev_shot_sec"] > 0.5
        assert t["frames"]["count"] == 40 and len(list((out / t["frames"]["dir"]).glob("f_*.jpg"))) == 40
        with Image.open(out / t["frames"]["sheet"]) as im:
            assert im.width > 1900 and im.height > 1000
        assert abs(t["video"]["duration"] - 10.0) < 0.1
    en = s["targets"][0]["subs"]
    assert en["en"]["lines"] == 10 and "skipped" in en["ko"]
    assert (out / "subs" / "tts040VidO0.en.txt").read_text(encoding="utf-8").startswith("[00:00.5] [Music]")
    assert s["targets"][1]["subs"]["ko"]["lines"] == 4
    th = {t["id"]: t for t in s["thumbnails"]}
    assert th["tts060VidI0"]["source"] == "maxresdefault" and th["tts060VidI0"]["width"] == 1280
    assert th["tts040VidO0"]["source"] == "hqdefault"
    assert th["tts012VidM2"]["source"] == "hqdefault"  # 자리표시 maxres → hq 폴백
    assert "error" in th["tts011VidL1"] and "HTTP 404" in th["tts011VidL1"]["error"]
    assert (out / "raw" / "thumbs" / "tts060VidI0.jpg").exists() and (out / "raw/thumbs/thumbs_sheet.jpg").exists()
    d = load(out / "data.json")
    assert d["samples"]["targets"][0]["shots"]["shot_count"] == 5
    assert "샘플 분석 (2단계)" in (out / "report.md").read_text(encoding="utf-8")

    # 정리: videos/ frames/ raw/ 삭제, 기록 남김, 재계산은 계속 가능
    p = script("sample_videos.py", "--root", str(root), "--dir", str(out), "--cleanup")
    assert "삭제" in p.stdout
    assert not any((out / n).exists() for n in ("videos", "frames", "raw"))
    assert load(out / "samples.json")["cleaned_up_at"] and load(out / "data.json")["samples"]["cleaned_up_at"]
    script("analyze_channel.py", "report", "--dir", str(out), "--root", str(root))
    d = load(out / "data.json")
    assert d["samples"]["targets"][0]["shots"]["cut_count"] == 4 and d["status"]["label"] == "정체"


@test
def test_sample_videos_ytdlp(tmp: Path):
    root = new_root(tmp)
    script("analyze_channel.py", "--root", str(root), "--offline-json", str(FIX / "channel.json"), "--now", NOW)
    out = root / "research" / "tinytotssing"
    video = tmp / "cards.mp4"
    make_cards_video(video)
    env = fake_env(tmp, "ok", FAKE_VIDEO=str(video))
    p = script("sample_videos.py", "--root", str(root), "--dir", str(out), "--ids", "tts040VidO0", "tts003VidD3",
               "--no-thumbs", env=env)
    calls = fake_calls(env)
    subs = [c for c in calls if "--write-auto-subs" in c]
    assert len(subs) == 2 and subs[0][subs[0].index("--sub-lang") + 1] == "en,ko"
    assert subs[0][subs[0].index("--sub-format") + 1] == "json3" and "--write-subs" in subs[0]
    assert subs[0][subs[0].index("-o") + 1] == str(out / "raw" / "%(id)s")
    dl = [c for c in calls if "-f" in c]
    assert len(dl) == 2 and dl[0][dl[0].index("-f") + 1].startswith("bv*[height<=480]")
    assert (out / "videos" / "tts040VidO0.mp4").exists()
    s = load(out / "samples.json")
    assert s["targets"][1]["subs"] == {"en": {"skipped": "자막 없음 → 건너뜀"}, "ko": {"skipped": "자막 없음 → 건너뜀"}}
    assert s["targets"][1]["shots"]["shot_count"] == 5 and s["targets"][0]["role"] == "지정"
    assert "en 자막 없음" in p.stdout
    # 봇 차단은 샘플 단계에서도 원문으로 중단
    env = fake_env(tmp, "always_bot", FAKE_VIDEO=str(video))
    p = script("sample_videos.py", "--root", str(root), "--dir", str(out), "--ids", "tts009VidJ9", "--no-thumbs",
               env=env, check=False)
    assert p.returncode == 1 and "RAW-MARKER-7731" in p.stderr
    p = script("sample_videos.py", "--root", str(root), "--dir", str(out), "--ids", "--exec=rm", check=False)
    assert p.returncode != 0


# ================================================================ 실행기

def main() -> int:
    only = set(sys.argv[1:])
    failed = 0
    base = Path(tempfile.mkdtemp(prefix="momo_research_test_"))
    for fn in TESTS:
        if only and fn.__name__ not in only:
            continue
        tmp = base / fn.__name__
        tmp.mkdir()
        try:
            fn(tmp) if fn.__code__.co_argcount else fn()
            print(f"✔ {fn.__name__}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"✖ {fn.__name__}\n{traceback.format_exc()}")
    if not failed:
        shutil.rmtree(base, ignore_errors=True)
    else:
        print(f"임시 폴더 유지: {base}")
    print(f"\n{'실패 ' + str(failed) + '개' if failed else '모두 통과'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
