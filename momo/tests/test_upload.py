#!/usr/bin/env python3
"""upload.py 오프라인 테스트 — 가짜 YouTube 서비스(빌더 교체)로 네트워크·자격증명 없이 검증한다.

사용: python3 momo/tests/test_upload.py        (실패가 있으면 exit 1)

확인하는 것: 요청 body(아동용 true 고정, publishAt UTC 변환, 합성 미디어 플래그), dry-run 은 자격증명 불필요,
이미 올린 언어 건너뜀/--force, 503·연결 끊김 재시도 후 성공, 재시도 소진, 썸네일 실패는 경고,
youtube.json 기록, 자격증명 우선순위(env LANG → env 공통 → .secrets 파일), 비밀 값 비출력, 메타 검증, 모음집,
youtube_check(채널 확인·오류·자격증명 없음).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

MOMO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MOMO))

import httplib2  # noqa: E402
from googleapiclient.errors import HttpError  # noqa: E402
from googleapiclient.http import MediaUploadProgress  # noqa: E402

import upload  # noqa: E402
from momolib import youtube as yt  # noqa: E402
from momolib.common import MomoError, Paths, deep_merge  # noqa: E402

EP = "ep42"
SECRET = {"YOUTUBE_CLIENT_ID": "cid-SENTINEL-1", "YOUTUBE_CLIENT_SECRET": "csec-SENTINEL-2",
          "YOUTUBE_REFRESH_TOKEN_EN": "rt-en-SENTINEL-3", "YOUTUBE_REFRESH_TOKEN": "rt-all-SENTINEL-4"}
VIDEO_SIZE = 20 * 1024 * 1024  # 8MB 청크 3개


def http_error(status: int, reason: str, message: str) -> HttpError:
    body = {"error": {"code": status, "message": message, "errors": [{"reason": reason, "message": message}]}}
    return HttpError(httplib2.Response({"status": str(status)}), json.dumps(body).encode(), uri="https://fake")


# ---------------------------------------------------------------- 가짜 서비스

class FakeRequest:
    def __init__(self, svc: "FakeService", name: str):
        self.svc, self.name = svc, name

    def execute(self):
        errs = self.svc.errors.get(self.name) or []
        if errs:
            raise errs.pop(0)
        return self.svc.results.get(self.name, {})


class FakeUpload:
    """videos.insert resumable 요청. svc.script 순서대로 오류를 내고, 그 외엔 청크 하나씩 진행."""

    def __init__(self, svc: "FakeService", kw: dict):
        self.svc, self.kw, self.sent = svc, kw, 0

    def next_chunk(self):
        action = self.svc.script.pop(0) if self.svc.script else "ok"
        if action == "ok":
            media = self.kw["media_body"]
            self.sent = min(media.size(), self.sent + media.chunksize())
            if self.sent < media.size():
                return MediaUploadProgress(self.sent, media.size()), None
            self.svc.uploads += 1
            return None, {"id": f"vid{self.svc.uploads}",
                          "status": {"privacyStatus": self.kw["body"]["status"]["privacyStatus"],
                                     "madeForKids": True}}
        if action == "reset":
            raise ConnectionResetError("connection reset by peer")
        raise action


class FakeResource:
    def __init__(self, svc: "FakeService", name: str):
        self.svc, self.name = svc, name

    def _call(self, method: str, kw: dict):
        name = f"{self.name}.{method}"
        self.svc.calls.append((name, kw))
        return FakeUpload(self.svc, kw) if name == "videos.insert" else FakeRequest(self.svc, name)

    def insert(self, **kw):
        return self._call("insert", kw)

    def set(self, **kw):
        return self._call("set", kw)

    def list(self, **kw):
        return self._call("list", kw)


class FakeService:
    def __init__(self, script=(), errors=None, results=None):
        self.script = list(script)
        self.errors = errors or {}
        self.results = results or {}
        self.calls: list[tuple[str, dict]] = []
        self.uploads = 0
        self.infos: list[dict] = []

    def videos(self):
        return FakeResource(self, "videos")

    def thumbnails(self):
        return FakeResource(self, "thumbnails")

    def playlistItems(self):  # noqa: N802 — API 이름 그대로
        return FakeResource(self, "playlistItems")

    def channels(self):
        return FakeResource(self, "channels")

    def names(self) -> list[str]:
        return [n for n, _ in self.calls]


# ---------------------------------------------------------------- 도우미

SLEEPS: list[float] = []


def install(svc: FakeService | None) -> None:
    def builder(info):
        if svc is None:
            raise AssertionError("dry-run 인데 서비스 빌더가 불렸음")
        svc.infos.append(dict(info))
        return svc
    yt.build_service = builder
    yt._sleep = SLEEPS.append


@contextlib.contextmanager
def env(**values):
    saved = {k: v for k, v in os.environ.items() if k.startswith("YOUTUBE_")}
    for k in saved:
        del os.environ[k]
    os.environ.update(values)
    try:
        yield
    finally:
        for k in [k for k in os.environ if k.startswith("YOUTUBE_")]:
            del os.environ[k]
        os.environ.update(saved)


def make_root(tmp: Path, cfg_patch: dict | None = None, upload_patch: dict | None = None) -> Path:
    root = tmp / "root"
    cfg = json.loads((MOMO / "config.json").read_text(encoding="utf-8"))
    (root / "episodes" / EP / "out").mkdir(parents=True)
    (root / "config.json").write_text(json.dumps(deep_merge(cfg, cfg_patch or {})), encoding="utf-8")
    up = {"en": {"title": "Learn Colors with Momo the Bunny | Red, Yellow, Blue for Toddlers",
                 "description": "Learn colors!\n\n#kids #toddler", "tags": ["colors", "toddler", "kids song"],
                 "playlist_id": "PLfakeEN"},
          "ko": {"title": "", "description": "모모와 색깔 배우기\n\n#유아", "tags": ["색깔"], "playlist_id": None}}
    manifest = {"ep": EP, "status": "assembled", "title": {"en": "t-en", "ko": "모모와 색깔 배우기 | 빨강 노랑 파랑"},
                "upload": deep_merge(up, upload_patch or {}), "cuts": []}
    (root / "episodes" / EP / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    for lang in ("en", "ko"):
        with open(root / "episodes" / EP / "out" / f"{EP}_{lang}.mp4", "wb") as f:
            f.write(b"\0\0\0\x18ftypmp42" + lang.encode())
            f.truncate(VIDEO_SIZE)
        (root / "episodes" / EP / "out" / f"{EP}_{lang}_thumb.jpg").write_bytes(b"\xff\xd8\xff\xe0fakejpeg")
    return root


def run(root: Path, *args: str) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = upload.main(["--root", str(root), *args])
    assert code == 0, (code, buf.getvalue())
    return buf.getvalue()


def raises(fn, *needles: str) -> str:
    try:
        fn()
    except MomoError as e:
        for n in needles:
            assert n in str(e), (n, str(e))
        return str(e)
    raise AssertionError("MomoError 가 나야 함")


def record(root: Path) -> dict:
    return json.loads((root / "episodes" / EP / "youtube.json").read_text(encoding="utf-8"))


def call(svc: FakeService, name: str) -> dict:
    return next(kw for n, kw in svc.calls if n == name)


# ---------------------------------------------------------------- 테스트

def test_publish_at_conversion(tmp: Path) -> None:
    assert upload.parse_publish_at("2030-01-02T09:00+09:00") == "2030-01-02T00:00:00Z"
    assert upload.parse_publish_at("2030-01-02T00:00:00Z") == "2030-01-02T00:00:00Z"
    assert upload.parse_publish_at("2030-01-02 09:30:15.5+09:00") == "2030-01-02T00:30:15Z"
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    raises(lambda: upload.parse_publish_at("2026-10-01T09:00+09:00", now=now), "과거")
    raises(lambda: upload.parse_publish_at("2030-01-02T09:00"), "시간대")
    raises(lambda: upload.parse_publish_at("next friday"), "형식")


def test_body_made_for_kids_always(tmp: Path) -> None:
    cfg = json.loads((MOMO / "config.json").read_text(encoding="utf-8"))
    job = upload.Job("ko", "t", Path("v.mp4"), None, "제목", "설명", ["a"], None, Path("y.json"))
    c1 = deep_merge(cfg, {"youtube": {"made_for_kids": False, "contains_synthetic_media": False}})
    body, warns = upload.build_body(c1, job, "public", None)
    assert body["status"] == {"privacyStatus": "public", "selfDeclaredMadeForKids": True}, body
    assert warns and "made_for_kids" in warns[0]
    assert body["snippet"]["defaultLanguage"] == body["snippet"]["defaultAudioLanguage"] == "ko"
    assert body["snippet"]["categoryId"] == "27" and body["snippet"]["tags"] == ["a"]
    c2 = deep_merge(cfg, {"youtube": {"contains_synthetic_media": True}})
    body, warns = upload.build_body(c2, job, "public", "2030-01-02T00:00:00Z")
    assert not warns
    assert body["status"] == {"privacyStatus": "private", "selfDeclaredMadeForKids": True,
                              "publishAt": "2030-01-02T00:00:00Z", "containsSyntheticMedia": True}, body


def test_dry_run_needs_no_credentials(tmp: Path) -> None:
    root = make_root(tmp)
    install(None)
    with env():
        out = run(root, "--ep", EP, "--lang", "all", "--dry-run", "--privacy", "public",
                  "--publish-at", "2031-05-05T10:00+09:00")
    assert '"selfDeclaredMadeForKids": true' in out and '"publishAt": "2031-05-05T01:00:00Z"' in out, out
    assert '"privacyStatus": "private"' in out and "public" not in out.split("body =")[1].split("기록")[0]
    assert str(root / "episodes" / EP / "out" / f"{EP}_ko.mp4") in out and "thumbnails.set" in out
    assert "PLfakeEN" in out and "모모와 색깔 배우기 | 빨강 노랑 파랑" in out  # ko 제목은 manifest.title 로 대체
    assert not (root / "episodes" / EP / "youtube.json").exists()


def test_refuses_animatic_build(tmp: Path) -> None:
    root = make_root(tmp)
    (root / "episodes" / EP / "out" / f"{EP}_ko_timeline.json").write_text('{"allow_missing": true}', encoding="utf-8")
    install(None)
    with env(**SECRET):
        raises(lambda: upload.main(["--root", str(root), "--ep", EP, "--lang", "all"]), "애니매틱", f"{EP} [ko]")
        assert "애니매틱" in run(root, "--ep", EP, "--lang", "ko", "--dry-run")  # dry-run 은 경고만
    assert not (root / "episodes" / EP / "youtube.json").exists()


def test_upload_retry_then_success_and_record(tmp: Path) -> None:
    root = make_root(tmp)
    svc = FakeService(script=[http_error(503, "backendError", "Backend Error"), "ok", "reset", "ok", "ok"])
    install(svc)
    SLEEPS.clear()
    with env(**SECRET):
        out = run(root, "--ep", EP, "--lang", "en", "--privacy", "unlisted")
    assert len(SLEEPS) == 2, SLEEPS
    assert svc.infos == [{"client_id": "cid-SENTINEL-1", "client_secret": "csec-SENTINEL-2",
                          "refresh_token": "rt-en-SENTINEL-3"}], "언어별 토큰이 공통 토큰보다 우선"
    ins = call(svc, "videos.insert")
    assert ins["part"] == "snippet,status" and ins["notifySubscribers"] is True
    assert ins["body"]["status"]["selfDeclaredMadeForKids"] is True
    assert ins["media_body"].resumable() and ins["media_body"].chunksize() == 8 * 1024 * 1024
    assert call(svc, "thumbnails.set")["videoId"] == "vid1"
    assert call(svc, "playlistItems.insert")["body"]["snippet"]["playlistId"] == "PLfakeEN"
    rec = record(root)["en"]
    video = root / "episodes" / EP / "out" / f"{EP}_en.mp4"
    assert rec["video_id"] == "vid1" and rec["url"].endswith("vid1") and rec["privacy"] == "unlisted"
    assert rec["thumbnail_set"] is True and rec["playlist_id"] == "PLfakeEN" and rec["publish_at"] is None
    assert rec["file_sha256"] == hashlib.sha256(video.read_bytes()).hexdigest() and rec["uploaded_at"].endswith("Z")
    manifest = json.loads((root / "episodes" / EP / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "uploaded"
    assert "감사(audit)" in out and "100%" in out
    assert not any(v in out for v in SECRET.values()), "비밀 값이 출력됨"


def test_real_http_request_resumes_after_503(tmp: Path) -> None:
    """가짜 서비스가 아니라 googleapiclient 의 실제 HttpRequest + 목 HTTP 로 resumable 재개 경로 확인."""
    from googleapiclient.http import HttpMockSequence, HttpRequest
    from googleapiclient.model import JsonModel
    video = tmp / "v.mp4"
    with open(video, "wb") as f:
        f.truncate(VIDEO_SIZE)
    err = '{"error": {"code": 503, "message": "Backend Error", "errors": [{"reason": "backendError"}]}}'
    http = HttpMockSequence([
        ({"status": "503"}, err),                                               # 세션 시작 실패 → 재시도
        ({"status": "200", "location": "https://upload.example/s1"}, ""),
        ({"status": "308", "range": "bytes=0-8388607"}, ""),                    # 청크 1
        ({"status": "503"}, err),                                               # 청크 2 실패
        ({"status": "308", "range": "bytes=0-8388607"}, ""),                    # 서버 상태 조회
        ({"status": "308", "range": "bytes=0-16777215"}, ""),                   # 청크 2 재전송
        ({"status": "200"}, '{"id": "vidR"}'),                                  # 청크 3 완료
    ])
    req = HttpRequest(http, JsonModel().response, "https://upload.example/videos?uploadType=resumable",
                      method="POST", body="{}", headers={"content-type": "application/json"},
                      resumable=yt.media_file(video, "video/mp4"))
    install(None)
    SLEEPS.clear()
    seen: list[int] = []
    with contextlib.redirect_stdout(io.StringIO()):
        resp = yt.resumable_upload(req, "t", on_progress=lambda done, total: seen.append(done))
    assert resp == {"id": "vidR"} and len(SLEEPS) == 2 and seen == [8388608, 16777216], (resp, SLEEPS, seen)


def test_skip_when_already_uploaded(tmp: Path) -> None:
    root = make_root(tmp)
    (root / "episodes" / EP / "youtube.json").write_text(json.dumps({"en": {"video_id": "old1", "url": "u"}}))
    svc = FakeService()
    install(svc)
    with env(**SECRET):
        out = run(root, "--ep", EP, "--lang", "en")
        assert "이미 업로드됨" in out and svc.calls == [], out
        run(root, "--ep", EP, "--lang", "en", "--force", "--no-thumbnail")
    assert svc.names() == ["videos.insert", "playlistItems.insert"], svc.names()
    rec = record(root)["en"]
    assert rec["video_id"] == "vid1" and rec["previous_video_ids"] == ["old1"] and rec["thumbnail_set"] is False


def test_thumbnail_failure_is_warning(tmp: Path) -> None:
    root = make_root(tmp)
    err = http_error(403, "forbidden", "The authenticated user doesn't have permissions to upload thumbnails.")
    svc = FakeService(errors={"thumbnails.set": [err]})
    install(svc)
    with env(**SECRET):
        out = run(root, "--ep", EP, "--lang", "en")
    rec = record(root)["en"]
    assert rec["video_id"] == "vid1" and rec["thumbnail_set"] is False and rec["playlist_id"] == "PLfakeEN"
    assert "채널 인증" in out and "doesn't have permissions" in out, out


def test_retry_exhausted_and_fatal_errors(tmp: Path) -> None:
    root = make_root(tmp)
    install(FakeService(script=[http_error(503, "backendError", "down")] * 9))
    SLEEPS.clear()
    with env(**SECRET):
        raises(lambda: run(root, "--ep", EP, "--lang", "en"), "재시도 8회", "down")
        assert len(SLEEPS) == 8
        svc = FakeService(script=[http_error(403, "quotaExceeded", "The request cannot be completed")])
        install(svc)
        SLEEPS.clear()
        raises(lambda: run(root, "--ep", EP, "--lang", "en"), "할당량", "403", "cannot be completed")
        assert SLEEPS == []
    assert not (root / "episodes" / EP / "youtube.json").exists()


def test_credentials_resolution(tmp: Path) -> None:
    root = make_root(tmp)
    svc = FakeService()
    install(svc)
    with env():
        msg = raises(lambda: run(root, "--ep", EP, "--lang", "ko"), "YOUTUBE_CLIENT_ID",
                     "YOUTUBE_REFRESH_TOKEN_KO", "docs/YOUTUBE_SETUP.md")
        assert svc.calls == [] and "SENTINEL" not in msg
    secrets = root / ".secrets"
    secrets.mkdir()
    (secrets / "youtube_ko.json").write_text(json.dumps({"client_id": "file-cid", "client_secret": "file-sec",
                                                         "refresh_token": "file-rt"}))
    with env(YOUTUBE_CLIENT_ID="env-cid"):
        out = run(root, "--ep", EP, "--lang", "ko", "--no-thumbnail")
    assert svc.infos[-1] == {"client_id": "file-cid", "client_secret": "file-sec", "refresh_token": "file-rt"}
    assert "youtube_ko.json" in out and "file-rt" not in out
    with env(**SECRET):
        run(root, "--ep", EP, "--lang", "ko", "--force", "--no-thumbnail")
    assert svc.infos[-1]["refresh_token"] == "rt-all-SENTINEL-4" and svc.infos[-1]["client_id"] == "cid-SENTINEL-1"


def test_metadata_validation(tmp: Path) -> None:
    install(None)
    with env(**SECRET):
        root = make_root(tmp / "a", upload_patch={"en": {"title": "Momo <3 Colors"}})
        raises(lambda: run(root, "--ep", EP, "--lang", "en", "--dry-run"), "< >")
        root = make_root(tmp / "b", upload_patch={"ko": {"description": "가" * 1700}})
        raises(lambda: run(root, "--ep", EP, "--lang", "all"), "5000바이트")
        root = make_root(tmp / "c", upload_patch={"en": {"tags": ["x" * 60] * 9}})
        raises(lambda: run(root, "--ep", EP, "--lang", "en"), "태그 총 길이")


def test_compilation_dry_run(tmp: Path) -> None:
    root = make_root(tmp)
    comp = root / "compilations"
    comp.mkdir()
    (comp / "best_en.mp4").write_bytes(b"fake")
    (comp / "best_en_chapters.txt").write_text("0:00 Colors\n2:35 Numbers\n5:10 Shapes\n", encoding="utf-8")
    install(None)
    with env():
        out = run(root, "--compilation", "best", "--lang", "en", "--title", "Momo Best | 8 min",
                  "--description", "Three songs.", "--tags", "kids, colors", "--dry-run")
        raises(lambda: run(root, "--compilation", "best", "--lang", "all", "--title", "x", "--dry-run"), "하나씩")
        raises(lambda: run(root, "--ep", EP, "--lang", "en", "--title", "x", "--dry-run"), "--compilation 전용")
    assert '"description": "Three songs.\\n\\n0:00 Colors\\n2:35 Numbers\\n5:10 Shapes"' in out, out
    assert '"tags": [\n' in out and "best_youtube.json" in out


def test_youtube_check(tmp: Path) -> None:
    import youtube_check
    root = make_root(tmp)

    def check(*args: str) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = youtube_check.main(["--root", str(root), *args])
        return code, buf.getvalue()

    ch = {"items": [{"id": "UCmomo", "snippet": {"title": "Momo the Bunny"},
                     "status": {"madeForKids": True, "longUploadsStatus": "allowed"}}]}
    svc = FakeService(results={"channels.list": ch})
    install(svc)
    with env(**SECRET):
        code, out = check()
    assert code == 0 and out.count("Momo the Bunny") == 2 and "같은 채널" in out, out
    assert "YOUTUBE_REFRESH_TOKEN_EN" in out and "SENTINEL" not in out, out
    assert [i["refresh_token"] for i in svc.infos] == ["rt-en-SENTINEL-3", "rt-all-SENTINEL-4"]
    assert svc.calls[0] == ("channels.list", {"part": "snippet,status", "mine": True})

    install(FakeService(results={"channels.list": {"items": []}}))
    with env(**SECRET):
        code, out = check("--lang", "ko")
    assert code == 1 and "채널이 없음" in out, out

    install(FakeService(errors={"channels.list": [http_error(403, "forbidden", "API not enabled")]}))
    with env(**SECRET):
        code, out = check("--lang", "en")
    assert code == 1 and "API not enabled" in out and "SENTINEL" not in out, out

    install(None)
    with env():
        code, out = check("--lang", "en")
    assert code == 1 and "YOUTUBE_CLIENT_ID" in out, out


def test_auth_saves_secret_file(tmp: Path) -> None:
    import youtube_auth

    class Creds:
        refresh_token = "rt-SENTINEL-5"
        granted_scopes = scopes = list(yt.SCOPES)
    flows: list = []
    orig = youtube_auth.run_flow
    youtube_auth.run_flow = lambda conf, port, open_browser: flows.append((conf, port, open_browser)) or Creds()
    svc = FakeService(results={"channels.list": {"items": [{"id": "UC123", "snippet": {"title": "Momo EN"}}]}})
    install(svc)
    root = tmp / "root"
    try:
        with env(YOUTUBE_CLIENT_ID="cid-SENTINEL-6", YOUTUBE_CLIENT_SECRET="sec-SENTINEL-7"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                assert youtube_auth.main(["--root", str(root), "--lang", "en", "--no-browser", "--port", "0"]) == 0
            out = buf.getvalue()
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                youtube_auth.main(["--root", str(root), "--lang", "en", "--print-token"])
    finally:
        youtube_auth.run_flow = orig
    conf, port, open_browser = flows[0]
    assert conf["installed"]["client_id"] == "cid-SENTINEL-6" and port == 0 and open_browser is False
    f = root / ".secrets" / "youtube_en.json"
    data = json.loads(f.read_text())
    assert (f.stat().st_mode & 0o777) == 0o600 and (f.parent.stat().st_mode & 0o777) == 0o700
    assert data["refresh_token"] == "rt-SENTINEL-5" and data["channel"] == {"id": "UC123", "title": "Momo EN"}
    assert "YOUTUBE_REFRESH_TOKEN_EN" in out and "Momo EN" in out and "SENTINEL" not in out, out
    assert "rt-SENTINEL-5" in buf.getvalue()
    with env():  # 저장된 파일만으로 업로드 자격증명이 풀려야 함
        assert yt.resolve_credentials(Paths(root), "en")[0]["refresh_token"] == "rt-SENTINEL-5"


def main() -> int:
    originals = (yt.build_service, yt._sleep)
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        with tempfile.TemporaryDirectory(prefix="momo_upload_test_") as d:
            try:
                fn(Path(d))
                print(f"✔ {name}")
            except Exception:  # noqa: BLE001
                failed.append(name)
                print(f"✖ {name}")
                traceback.print_exc()
            finally:
                yt.build_service, yt._sleep = originals
    print(f"\ntest_upload: {len(tests) - len(failed)}/{len(tests)} 통과" + (f" — 실패: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
