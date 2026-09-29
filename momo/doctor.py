#!/usr/bin/env python3
"""작업 환경 점검 — 지시서 "시작 전 확인" + Actions 의 doctor --ci.

✔ 정상 · △ 경고(진행 가능) · ✖ 멈춰야 함 → 하나라도 있으면 exit 1.
확인: yt-dlp(버전·최신화), ffmpeg/ffprobe(libx264, xfade, loudnorm, tpad, reverse), Python 모듈,
assets/fonts 한글 지원 폰트, assets/bgm, assets/sfx(선택), library 상태, config.voices,
YouTube 자격증명(이름만, 값은 출력하지 않음), --ep 면 manifest 검증 + 생성 진행 + 없는 에셋 목록.

사용 예
  python doctor.py
  python doctor.py --ep ep02
  python doctor.py --update-ytdlp            # yt-dlp -U (pip 설치본이면 pip install -U yt-dlp)
  python doctor.py --ep ep02 --ci            # 비대화형, GitHub Actions 주석(::error::) 출력
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import (AUDIO_EXTS, FONT_EXTS, LANGS, LIBRARY_AUDIO, LIBRARY_CLIPS, MomoError,  # noqa: E402
                            Paths, add_root_arg, check_ep, find_font, find_media, get_paths, list_files,
                            load_config, load_library, load_manifest, main_wrapper, probe, which)
from momolib.genrec import FETCHABLE, KIND_EXTS, characters_used, episode_slots, status_of  # noqa: E402

STOP = "없으면 멈추고 알려줄 것"
MODULES = [("PIL", "Pillow"), ("numpy", "numpy"), ("yt_dlp", "yt-dlp"),
           ("googleapiclient", "google-api-python-client"), ("google.auth", "google-auth"),
           ("google_auth_oauthlib", "google-auth-oauthlib"), ("google_auth_httplib2", "google-auth-httplib2")]
FFMPEG_FILTERS = ("xfade", "loudnorm", "tpad", "reverse")
CRED_ENV = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN",
            "YOUTUBE_REFRESH_TOKEN_EN", "YOUTUBE_REFRESH_TOKEN_KO")
YTDLP_MAX_AGE_DAYS = 60


class Report:
    def __init__(self, ci: bool):
        self.ci = ci and bool(os.environ.get("GITHUB_ACTIONS"))
        self.n = {"✔": 0, "△": 0, "✖": 0}

    def section(self, title: str) -> None:
        print(f"\n[{title}]")

    def _emit(self, mark: str, msg: str) -> None:
        self.n[mark] += 1
        print(f"  {mark} {msg}")
        if self.ci and mark != "✔":
            level = "error" if mark == "✖" else "warning"
            print(f"::{level}::{msg.splitlines()[0]}")

    def ok(self, msg: str) -> None:
        self._emit("✔", msg)

    def warn(self, msg: str) -> None:
        self._emit("△", msg)

    def fail(self, msg: str) -> None:
        self._emit("✖", msg)

    def note(self, msg: str) -> None:
        print(f"  · {msg}")


def cmd_out(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


# ---------------------------------------------------------------- 도구

def check_ytdlp(r: Report, update: bool) -> None:
    exe = which("yt-dlp")
    base = [exe] if exe else ([sys.executable, "-m", "yt_dlp"] if importlib.util.find_spec("yt_dlp") else None)
    if not base:
        r.fail("yt-dlp 없음 — pip install -r requirements.txt (1·2단계 채널 분석에 필요)")
        return
    if update:
        code, out = cmd_out(base + ["-U"], timeout=180)
        tail = out.strip().splitlines()[-1] if out.strip() else ""
        if "pip" in out.lower() or code != 0:
            code2, out2 = cmd_out([sys.executable, "-m", "pip", "install", "-q", "-U", "yt-dlp"], timeout=300)
            if code2 == 0:
                r.ok("yt-dlp 최신화: pip install -U yt-dlp")
            else:
                r.warn(f"yt-dlp 최신화 실패 (계속 진행) — 원문: {tail or out.strip()[-300:]} / pip: "
                       f"{out2.strip().splitlines()[-1] if out2.strip() else code2}")
        else:
            r.ok(f"yt-dlp -U: {tail}")
    code, out = cmd_out(base + ["--version"])
    ver = out.strip().splitlines()[0] if code == 0 and out.strip() else ""
    if not ver:
        r.fail(f"yt-dlp 실행 실패 — 원문: {out.strip()[-300:]}")
        return
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", ver)
    age = (date.today() - date(int(m[1]), int(m[2]), int(m[3]))).days if m else None
    if age is not None and age > YTDLP_MAX_AGE_DAYS:
        r.warn(f"yt-dlp {ver} — {age}일 지난 버전. 유튜브가 자주 바뀌어 구버전은 목록 추출부터 실패 → --update-ytdlp")
    else:
        r.ok(f"yt-dlp {ver}")


def check_ffmpeg(r: Report) -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if not which(tool):
            r.fail(f"{tool} 없음 — apt install ffmpeg (6.x)")
    if not which("ffmpeg"):
        return
    _, ver = cmd_out(["ffmpeg", "-hide_banner", "-version"])
    _, enc = cmd_out(["ffmpeg", "-hide_banner", "-encoders"])
    _, flt = cmd_out(["ffmpeg", "-hide_banner", "-filters"])
    filters = {ln.split()[1] for ln in flt.splitlines() if len(ln.split()) > 2 and re.match(r"^ [.A-Z|]{2,3} ", ln)}
    missing = [f for f in FFMPEG_FILTERS if f not in filters]
    if not re.search(r"\blibx264\b", enc):
        missing.insert(0, "libx264")
    mv = re.search(r"ffmpeg version (\S+)", ver)
    head = f"ffmpeg {mv[1] if mv else '?'}"
    if missing:
        r.fail(f"{head} — 없는 기능: {', '.join(missing)} (ubuntu 24.04 apt ffmpeg 권장)")
    else:
        r.ok(f"{head} (libx264, {', '.join(FFMPEG_FILTERS)})")


def check_python(r: Report) -> None:
    if sys.version_info < (3, 10):
        r.fail(f"Python {sys.version.split()[0]} — 3.10 이상 필요")
    else:
        r.ok(f"Python {sys.version.split()[0]}")
    missing = [pkg for mod, pkg in MODULES if importlib.util.find_spec(mod) is None]
    if missing:
        r.fail(f"Python 모듈 없음: {', '.join(missing)} — pip install -r requirements.txt")
    else:
        r.ok("Python 모듈: " + ", ".join(pkg for _, pkg in MODULES))


# ---------------------------------------------------------------- 에셋

def check_fonts(r: Report, paths: Paths, cfg: dict) -> None:
    files = list_files(paths.fonts, FONT_EXTS)
    for purpose in ("keyword", "thumbnail"):
        conf = (cfg.get("fonts") or {}).get(purpose)
        if conf and not (Path(conf) if Path(conf).is_absolute() else paths.root / conf).exists():
            r.warn(f"config.fonts.{purpose} = {conf} 파일이 없음 → assets/fonts 의 다른 폰트로 대체")
    seen = set()
    for purpose in ("keyword", "thumbnail"):
        try:
            f = find_font(paths, cfg, purpose, need_hangul=True)
        except MomoError:
            r.fail(f"assets/fonts/ 에 한글을 지원하는 둥근 고딕 폰트(TTF/OTF)가 없음 — {STOP} "
                   f"(있는 폰트: {', '.join(p.name for p in files) or '없음'})")
            return
        if f not in seen:
            seen.add(f)
            r.ok(f"폰트 ({purpose}): {f.name} — 한글 지원")


def check_bgm(r: Report, paths: Paths, cfg: dict, manifest: dict | None) -> None:
    name = (manifest or {}).get("bgm") or cfg["audio"].get("bgm_file")
    if name:
        p = Path(name) if Path(name).is_absolute() else paths.bgm / name
        if not p.exists():
            r.fail(f"BGM 파일 없음: {p} (manifest.bgm / config.audio.bgm_file) — {STOP}")
            return
    else:
        files = list_files(paths.bgm, AUDIO_EXTS)
        if not files:
            r.fail(f"assets/bgm/ 에 BGM 이 없음 — 사용자가 넣어두는 파일, {STOP}")
            return
        p = files[0]
    if not which("ffprobe"):
        r.warn(f"BGM: {p.name} (ffprobe 없어 검증 못 함)")
        return
    try:
        info = probe(p)
    except MomoError as e:
        r.fail(f"BGM 을 읽을 수 없음: {p.name} — {e}")
        return
    if not info.has_audio:
        r.fail(f"BGM 에 음성 스트림이 없음: {p.name}")
    else:
        r.ok(f"BGM: {p.name} ({info.duration:.1f}초, 영상 길이만큼 루프)")


def check_sfx(r: Report, paths: Paths, manifest: dict | None) -> None:
    files = list_files(paths.sfx, AUDIO_EXTS)
    if files:
        r.ok(f"SFX {len(files)}개: {', '.join(p.name for p in files[:8])}")
    else:
        r.note("assets/sfx/ 없음 (선택 — manifest 의 sfx 는 생략됨)")
    for c in (manifest or {}).get("cuts") or []:
        for s in c.get("sfx") or []:
            name = str(s.get("file") if isinstance(s, dict) else s)
            if not (paths.sfx / name).exists() and not find_media(paths.sfx, Path(name).stem, AUDIO_EXTS):
                r.warn(f"{c.get('id')}: 효과음 {name!r} 없음 → 조립 때 생략")


def check_library(r: Report, paths: Paths, cfg: dict, lib: dict, manifest: dict | None) -> None:
    sheets = lib.get("character_sheets") or {}
    need = characters_used(cfg, manifest) if manifest else ["momo"]
    bad = [k for k in need if status_of(sheets.get(k)) != "approved"]
    if bad:
        r.warn(f"캐릭터 시트 미승인: {', '.join(bad)} → hf_jobs.py plan --library --kind sheet")
    else:
        r.ok("캐릭터 시트 승인: " + ", ".join(need))

    def group(label: str, items: list[tuple[str, dict, Path | None]]) -> None:
        approved = [n for n, rec, _ in items if status_of(rec) == "approved"]
        have = [n for n, _, f in items if f]
        missing_files = [n for n, rec, f in items if status_of(rec) in FETCHABLE and not f]
        if len(approved) == len(items) and len(have) == len(items):
            r.ok(f"{label} {len(items)}/{len(items)} 승인·파일 있음")
            return
        msg = f"{label}: 승인 {len(approved)}/{len(items)}, 파일 {len(have)}/{len(items)}"
        if missing_files:
            msg += f" — 파일 없음 {', '.join(missing_files)} → fetch_assets.py --library 로 복원"
        if len(approved) < len(items):
            msg += " — 첫 편에서 한 번만 생성 (hf_jobs.py plan --library)"
        r.warn(msg)

    clips = lib.get("clips") or {}
    group("라이브러리 클립", [(n, clips.get(n) or {}, find_media(paths.library_clips, n, KIND_EXTS["clip"]))
                         for n in LIBRARY_CLIPS])
    audio = lib.get("audio") or {}
    group("고정 음성", [(f"{lang}/{n}", (audio.get(lang) or {}).get(n) or {},
                      find_media(paths.library_audio(lang), n, AUDIO_EXTS)) for lang in LANGS for n in LIBRARY_AUDIO])
    if manifest:
        used = {c.get("library_clip") for c in manifest.get("cuts") or [] if c.get("type") == "L"}
        gone = sorted(n for n in used if n and not find_media(paths.library_clips, n, KIND_EXTS["clip"]))
        if gone:
            r.warn(f"이 에피소드가 쓰는 라이브러리 클립 파일 없음: {', '.join(gone)} (build 전에 fetch_assets --library)")


def check_config(r: Report, cfg: dict) -> None:
    voices = cfg.get("voices") or {}
    for lang in LANGS:
        if voices.get(lang):
            r.ok(f"config.voices.{lang} = {voices[lang]} (고정 — 바꾸지 말 것)")
        else:
            r.warn(f"config.voices.{lang} 미설정 — list_voices 후보 3개 → hf_jobs.py voice-samples → 승인 후 고정")
    hf = cfg["higgsfield"]
    if hf.get("momo_element_id") or (hf.get("element_ids") or {}).get("momo"):
        r.ok("Higgsfield Element (momo) 등록됨 — plan 프롬프트에 <<<id>>> 자동 삽입")
    else:
        r.warn("Higgsfield Element (momo) 없음 — 캐릭터 시트 승인 후 등록 (안 되면 캐릭터 고정 블록만으로 진행)")
    checked = (hf.get("unit_costs") or {}).get("checked_at")
    r.note(f"단가 확인일: {checked or '기록 없음'} (get_cost:true 로 재확인) · Higgsfield MCP 연결은 Claude 가 balance 로 확인")


def check_youtube(r: Report, paths: Paths) -> None:
    present = [n for n in CRED_ENV if os.environ.get(n, "").strip()]
    try:
        from momolib.youtube import credentials_source
    except ImportError:
        credentials_source = None
    for lang in LANGS:
        src = credentials_source(paths, lang) if credentials_source else None
        if src:
            r.ok(f"YouTube 자격증명 [{lang}]: {src}")
        else:
            r.warn(f"YouTube 자격증명 [{lang}] 없음 — 업로드 전 docs/YOUTUBE_SETUP.md "
                   f"(YOUTUBE_CLIENT_ID/SECRET + YOUTUBE_REFRESH_TOKEN_{lang.upper()} 또는 youtube_auth.py)")
    r.note("설정된 환경변수(이름만): " + (", ".join(present) or "없음"))


# ---------------------------------------------------------------- 에피소드

def check_episode(r: Report, paths: Paths, cfg: dict, m: dict) -> None:
    from momolib.episode import plan_timeline, validate_manifest
    errors, warns = validate_manifest(cfg, m)
    for e in errors:
        r.fail(f"manifest: {e}")
    if not errors:
        r.ok(f"manifest 검증 통과 (컷 {len(m.get('cuts') or [])}개, 경고 {len(warns)}개 — validate_manifest.py 로 확인)")
        if warns:
            r.warn(f"manifest 경고 {len(warns)}개: " + " / ".join(warns[:3]) + (" …" if len(warns) > 3 else ""))
    slots = episode_slots(paths, cfg, m)
    left = [s.key for s in slots if status_of(s.rec) != "approved"]
    if left:
        r.warn(f"생성·승인 미완료 {len(left)}/{len(slots)}개 (예: {', '.join(left[:5])}) → hf_jobs.py status --ep {m['ep']}")
    else:
        r.ok(f"생성 기록 {len(slots)}개 모두 승인")
    if errors:
        return
    for lang in LANGS:
        try:
            _, total, warn = plan_timeline(paths, cfg, m, lang, allow_missing=True)
        except MomoError as e:
            r.warn(f"{lang} 타임라인 계산 실패 — {e}")
            continue
        missing = next((w for w in warn if w.startswith("없는 파일")), None)
        if missing:
            lines = missing.splitlines()
            listed = [ln.strip("- ").strip() for ln in lines[1:]]
            r.warn(f"{lang} 에셋 {lines[0].rstrip(':')} — {', '.join(listed[:10])}{' …' if len(listed) > 10 else ''}"
                   f" → fetch_assets.py --ep {m['ep']} --library (아직 생성 전이면 hf_jobs.py)")
        else:
            r.ok(f"{lang} 에셋 모두 있음 (예상 길이 {total:.1f}초)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="작업 환경 점검 (✖ 가 있으면 exit 1)",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    ap.add_argument("--ep")
    ap.add_argument("--update-ytdlp", action="store_true", help="yt-dlp -U (pip 설치본이면 pip install -U)")
    ap.add_argument("--ci", action="store_true", help="비대화형 (GitHub Actions 주석 출력)")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    cfg = load_config(paths)
    r = Report(args.ci)
    m = load_manifest(paths, check_ep(args.ep)) if args.ep else None
    print(f"momo doctor — {paths.root}" + (f" (에피소드 {args.ep})" if args.ep else ""))

    r.section("도구")
    check_python(r)
    check_ytdlp(r, args.update_ytdlp)
    check_ffmpeg(r)
    r.section("assets (사용자가 넣는 파일)")
    check_fonts(r, paths, cfg)
    check_bgm(r, paths, cfg, m)
    check_sfx(r, paths, m)
    r.section("라이브러리")
    check_library(r, paths, cfg, load_library(paths), m)
    r.section("설정")
    check_config(r, cfg)
    check_youtube(r, paths)
    if m is not None:
        r.section(f"에피소드 {args.ep}")
        check_episode(r, paths, cfg, m)

    print(f"\n결과: ✖ {r.n['✖']} · △ {r.n['△']} · ✔ {r.n['✔']}")
    if r.n["✖"]:
        print("✖ 멈춰야 할 항목이 있음 — 위 ✖ 를 해결한 뒤 다시 실행 (지시서: 없으면 멈추고 알려줄 것)")
        return 1
    print("✔ 진행 가능" + (" (△ 경고 확인)" if r.n["△"] else ""))
    return 0


if __name__ == "__main__":
    main_wrapper(main)
