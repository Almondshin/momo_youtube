"""모든 momo 스크립트가 공유하는 경로·설정·입출력·ffprobe 헬퍼.

규칙
- 모든 스크립트는 `--root` 인자(기본: momo/ 폴더)를 받는다. 테스트는 임시 root 로 돌린다.
- config.json 에 빠진 키는 DEFAULT_CONFIG 로 채운다 (사용자 파일이 우선).
- 외부 명령 실패는 MomoError 로 올리고, 메시지에 stderr 꼬리를 그대로 붙인다
  ("에러 원문 그대로 보고" 원칙).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

MOMO_DIR = Path(__file__).resolve().parent.parent  # 저장소의 momo/ 폴더

LANGS = ("en", "ko")
CUT_TYPES = ("L", "V", "S")
LIBRARY_CLIPS = ("intro_wave", "outro_bye", "say_with_me", "cheer", "transition")
LIBRARY_AUDIO = ("intro", "outro")
EP_RE = re.compile(r"^ep\d{2,3}$")
CUT_ID_RE = re.compile(r"^c\d{2,3}$")

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv")
AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus")
FONT_EXTS = (".ttf", ".otf", ".ttc")


class MomoError(Exception):
    """사용자에게 그대로 보여줄 수 있는 실패. 스크립트 main 에서 잡아 exit 1."""


# ---------------------------------------------------------------- 설정

DEFAULT_CONFIG: dict[str, Any] = {
    "benchmark": {"channel_url": None, "playlist_end": 2000, "recent_count": 15, "top_count": 5,
                  "min_age_hours": 72, "compilation_min_seconds": 1800},
    "character": {"momo": "", "ducky": ""},
    "style_lock": "",
    "video_prompt_suffix": "Keep the character design exactly the same. Static fixed camera, no camera movement.",
    "fixed_lines": {"en": {"intro": "Hi friends! It's Momo!", "outro": "Bye-bye, friends! See you next time!"},
                    "ko": {"intro": "안녕, 친구들! 나는 모모야!", "outro": "친구들, 안녕! 다음에 또 만나!"}},
    "higgsfield": {"image_model": "nano_banana_pro", "video_model": "kling3_0_turbo", "video_duration": 5,
                   "audio_model": "seed_audio", "aspect_ratio": "16:9", "image_resolution": "2k",
                   "video_resolution": "720p", "max_parallel_images": 4,
                   "unit_costs": {"image": 2, "video_720p_5s": 7.5, "video_1080p_5s": 10, "audio_block": 0.2}},
    "voices": {"en": None, "ko": None},
    "credits": {"episode_cap": 250},
    "onmodel": {"canon_eye_ratio": 0.486, "eye_ratio_min": 0.65},
    "plan_rules": {"cuts_min": 22, "cuts_max": 28, "v_range": [12, 15], "s_range": [6, 8], "l_range": [3, 4],
                   "scenes": 5, "narration_max_words_en": 25, "narration_max_chars_ko": 40,
                   "keyword_min_repeats": 3},
    "fonts": {"keyword": None, "thumbnail": None},
    "render": {"width": 1920, "height": 1080, "fps": 30, "crf": 18, "preset": "medium", "xfade": 0.3,
               "tail_pad": 0.4, "min_cut": 3.0, "default_pause": 1.5, "text_height_ratio": 0.125,
               "text_band_ratio": 0.25, "text_delay": 0.5, "text_pop_seconds": 0.3,
               "text_colors": {"white": "#FFFFFF", "yellow": "#FFD83B"}, "text_stroke_ratio": 0.12,
               "kenburns_zoom": [0.05, 0.08], "kenburns_drift": 0.015, "inset_default": 0.035,
               "thumbnail_size": [1280, 720]},
    "audio": {"sample_rate": 48000, "bgm_file": None, "bgm_gain_db": -12.0, "duck_db": -16.0,
              "duck_attack": 0.15, "duck_release": 0.35, "bgm_fade_in": 1.0, "bgm_fade_out": 2.0,
              "narration_gain_db": 0.0, "loudness_lufs": -14.0, "true_peak": -1.5, "aac_bitrate": "192k"},
    "youtube": {"made_for_kids": True, "category_id": "27", "default_privacy": "private",
                "contains_synthetic_media": False, "notify_subscribers": True,
                "languages": {"en": "en", "ko": "ko"}, "playlist_id": {"en": None, "ko": None}},
}


def deep_merge(base: dict, override: dict) -> dict:
    """base 를 복사한 뒤 override 값으로 덮는다 (dict 는 재귀, 나머지는 교체)."""
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


# ---------------------------------------------------------------- 경로

@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def config(self) -> Path: return self.root / "config.json"
    @property
    def library(self) -> Path: return self.root / "library"
    @property
    def library_json(self) -> Path: return self.library / "library.json"
    @property
    def library_clips(self) -> Path: return self.library / "clips"
    @property
    def library_sheets(self) -> Path: return self.library / "sheets"
    def library_audio(self, lang: str) -> Path: return self.library / "audio" / lang
    @property
    def assets(self) -> Path: return self.root / "assets"
    @property
    def bgm(self) -> Path: return self.assets / "bgm"
    @property
    def sfx(self) -> Path: return self.assets / "sfx"
    @property
    def fonts(self) -> Path: return self.assets / "fonts"
    @property
    def episodes(self) -> Path: return self.root / "episodes"
    @property
    def research(self) -> Path: return self.root / "research"
    @property
    def compilations(self) -> Path: return self.root / "compilations"
    @property
    def secrets(self) -> Path: return self.root / ".secrets"
    @property
    def templates(self) -> Path: return self.root / "templates"

    def ep(self, ep: str) -> Path: return self.episodes / ep
    def manifest(self, ep: str) -> Path: return self.ep(ep) / "manifest.json"
    def images(self, ep: str) -> Path: return self.ep(ep) / "images"
    def clips(self, ep: str) -> Path: return self.ep(ep) / "clips"
    def audio(self, ep: str, lang: str) -> Path: return self.ep(ep) / "audio" / lang
    def out(self, ep: str) -> Path: return self.ep(ep) / "out"
    def build_tmp(self, ep: str, lang: str) -> Path: return self.ep(ep) / ".build" / lang
    def youtube_json(self, ep: str) -> Path: return self.ep(ep) / "youtube.json"


def add_root_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=os.environ.get("MOMO_ROOT", str(MOMO_DIR)),
                        help="momo 작업 폴더 (기본: 저장소의 momo/)")


def get_paths(args: argparse.Namespace) -> Paths:
    return Paths(Path(args.root).resolve())


def check_ep(ep: str) -> str:
    """에피소드 번호 검증 (ep01, ep02 ...). 셸/경로 주입 방지 겸용."""
    if not EP_RE.match(ep or ""):
        raise MomoError(f"에피소드 번호 형식이 잘못됨: {ep!r} (예: ep02)")
    return ep


def active_langs(cfg: dict) -> tuple[str, ...]:
    """Production languages — config.languages (e.g. ["en"]), default both. LANGS stays the supported set."""
    langs = tuple(lg for lg in (cfg.get("languages") or LANGS) if lg in LANGS)
    return langs or LANGS


def episode_cfg(cfg: dict, manifest: dict | None) -> dict:
    """cfg for one episode: manifest.languages (an episode made in another language than the channel's, e.g. the
    Korean ep11 on the English channel, user 2026-10-05) replaces config.languages."""
    langs = (manifest or {}).get("languages")
    if isinstance(langs, list) and langs and all(lg in LANGS for lg in langs):
        return {**cfg, "languages": list(langs)}
    return cfg


def check_lang(lang: str) -> str:
    if lang not in LANGS:
        raise MomoError(f"언어는 {LANGS} 중 하나여야 함: {lang!r}")
    return lang


# ---------------------------------------------------------------- JSON

def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        if default is not None:
            return copy.deepcopy(default)
        raise MomoError(f"파일 없음: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise MomoError(f"JSON 파싱 실패: {path}: {e}") from e


def save_json(path: Path, data: Any) -> None:
    """원자적 저장 (중간에 죽어도 기존 파일이 깨지지 않게)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=str(path.parent))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def load_config(paths: Paths) -> dict:
    user = load_json(paths.config, default={}) if paths.config.exists() else {}
    return deep_merge(DEFAULT_CONFIG, user)


def load_manifest(paths: Paths, ep: str) -> dict:
    return load_json(paths.manifest(check_ep(ep)))


def load_library(paths: Paths) -> dict:
    return load_json(paths.library_json, default={"clips": {}, "audio": {"en": {}, "ko": {}},
                                                   "character_sheets": {}})


# ---------------------------------------------------------------- 파일 찾기

def find_media(folder: Path, stem: str, exts: Iterable[str]) -> Path | None:
    """folder/stem.<ext> 중 처음 존재하는 파일 (확장자 우선순위 = exts 순서)."""
    for ext in exts:
        p = folder / f"{stem}{ext}"
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def list_files(folder: Path, exts: Iterable[str]) -> list[Path]:
    if not folder.is_dir():
        return []
    exts = tuple(e.lower() for e in exts)
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts
                  and not p.name.startswith("."))


# ---------------------------------------------------------------- 외부 명령

def which(name: str) -> str | None:
    return shutil.which(name)


def run(cmd: list[str], *, capture: bool = True, input_bytes: bytes | None = None,
        cwd: Path | None = None, quiet: bool = False) -> subprocess.CompletedProcess:
    """명령 실행. 실패하면 stderr 꼬리를 담아 MomoError."""
    if not quiet and os.environ.get("MOMO_VERBOSE"):
        print("+", " ".join(str(c) for c in cmd), file=sys.stderr)
    try:
        proc = subprocess.run([str(c) for c in cmd], input=input_bytes, cwd=cwd,
                              stdout=subprocess.PIPE if capture else None,
                              stderr=subprocess.PIPE if capture else None)
    except FileNotFoundError as e:
        raise MomoError(f"명령을 찾을 수 없음: {cmd[0]} (설치 필요)") from e
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", "replace")
        tail = "\n".join(err.strip().splitlines()[-25:])
        raise MomoError(f"명령 실패 (exit {proc.returncode}): {' '.join(str(c) for c in cmd[:6])} ...\n{tail}")
    return proc


def ffprobe_json(path: Path) -> dict:
    proc = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    return json.loads(proc.stdout.decode("utf-8", "replace") or "{}")


def _parse_rate(rate: str | None) -> float:
    if not rate or rate in ("0/0", "0"):
        return 0.0
    if "/" in rate:
        n, d = rate.split("/", 1)
        return float(n) / float(d) if float(d) else 0.0
    return float(rate)


@dataclass
class MediaInfo:
    path: Path
    duration: float
    width: int = 0
    height: int = 0
    fps: float = 0.0
    has_video: bool = False
    has_audio: bool = False


def probe(path: Path) -> MediaInfo:
    data = ffprobe_json(path)
    fmt_dur = float(data.get("format", {}).get("duration") or 0.0)
    info = MediaInfo(path=path, duration=fmt_dur)
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and not info.has_video:
            # 앨범아트(attached_pic)는 영상으로 치지 않는다
            if (s.get("disposition") or {}).get("attached_pic"):
                continue
            info.has_video = True
            info.width = int(s.get("width") or 0)
            info.height = int(s.get("height") or 0)
            info.fps = _parse_rate(s.get("avg_frame_rate")) or _parse_rate(s.get("r_frame_rate"))
            if s.get("duration"):
                info.duration = float(s["duration"])
        elif s.get("codec_type") == "audio":
            info.has_audio = True
            if not info.has_video and s.get("duration"):
                info.duration = float(s["duration"])
    if info.duration <= 0:
        raise MomoError(f"길이를 읽을 수 없음: {path}")
    return info


def probe_duration(path: Path) -> float:
    return probe(path).duration


# ---------------------------------------------------------------- 폰트

def font_supports_hangul(font_path: Path) -> bool:
    """'가' 글리프가 .notdef(두부)와 다르게 그려지면 한글 지원으로 본다."""
    from PIL import ImageFont
    try:
        font = ImageFont.truetype(str(font_path), 64)
    except OSError:
        return False
    def mask_bytes(ch: str) -> bytes | None:
        m = font.getmask(ch)
        return bytes(m) if m.getbbox() else None
    ga = mask_bytes("가")
    if ga is None:
        return False
    tofu = mask_bytes("\U000F0000")  # 사설 영역 → 대부분 폰트에서 .notdef
    return ga != tofu


def find_font(paths: Paths, cfg: dict, purpose: str = "keyword", need_hangul: bool = False) -> Path:
    """config.fonts[purpose] → assets/fonts/ 의 첫 폰트. 없으면 멈추고 알린다."""
    configured = (cfg.get("fonts") or {}).get(purpose)
    candidates: list[Path] = []
    if configured:
        p = Path(configured)
        candidates.append(p if p.is_absolute() else paths.root / p)
    candidates += list_files(paths.fonts, FONT_EXTS)
    for p in candidates:
        if not p.exists():
            continue
        if need_hangul and not font_supports_hangul(p):
            continue
        return p
    need = "한글을 지원하는 " if need_hangul else ""
    raise MomoError(f"{need}폰트가 없음: {paths.fonts}/ 에 둥근 고딕 TTF/OTF 를 넣어줘 "
                    f"(예: Jua, NanumSquareRound, Cafe24 Ssurround). config.fonts.{purpose} 로 지정도 가능.")


# ---------------------------------------------------------------- 기타

def fmt_ts(seconds: float) -> str:
    """유튜브 챕터용 타임스탬프 (M:SS 또는 H:MM:SS)."""
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def main_wrapper(fn) -> None:
    """스크립트 진입점: MomoError 는 원문 그대로 출력하고 exit 1."""
    try:
        code = fn()
    except MomoError as e:
        print(f"\n[중단] {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[중단] 사용자 취소", file=sys.stderr)
        sys.exit(130)
    sys.exit(code or 0)
