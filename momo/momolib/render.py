"""화면 그리기 공용 함수 — build.py / compile.py 가 쓴다.

- 크롭-투-필 (비율 유지 확대 후 중앙 크롭, 레터박스 금지) + 테두리 인셋
- detect_border(): 이미지 가장자리 테두리 프레임 자동 감지 (보수적)
- render_keyword_frames(): 키워드 팝 애니메이션 RGBA 밴드 PNG 시퀀스
- kenburns_frames(): S 컷 켄번즈 프레임 (Pillow float 정밀도, rawvideo rgb24 로 ffmpeg 에 파이프)
- make_thumbnail(), placeholder_card(), contact_sheet()
- ffmpeg 영상 헬퍼: 프레임 추출, 색공간(bt709) 인자, 출력 검증
"""
from __future__ import annotations

import colorsys
import hashlib
import io
import math
import re
from pathlib import Path
from typing import Iterator

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .common import MomoError, ffprobe_json, run

HANGUL_RE = re.compile(r"[ᄀ-ᇿ㄰-㆏가-힣]")
STROKE_COLOR = (0, 0, 0)


# ---------------------------------------------------------------- 이미지 / 크롭

def load_image(path: Path) -> Image.Image:
    """RGB 로 읽는다 (EXIF 회전 반영, 투명 영역은 흰 배경)."""
    try:
        im = ImageOps.exif_transpose(Image.open(path))
        im.load()
    except Exception as e:  # PIL 은 여러 종류의 예외를 던진다
        raise MomoError(f"이미지를 열 수 없음: {path}: {e}") from e
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return im.convert("RGB")


def fill_box(sw: float, sh: float, dw: float, dh: float, inset: float = 0.0) -> tuple[float, float, float, float]:
    """원본(sw×sh)에서 인셋을 뺀 뒤 dw:dh 비율로 중앙 크롭할 영역 (x, y, w, h), float."""
    x, y = sw * inset, sh * inset
    w, h = sw - 2 * x, sh - 2 * y
    if w / h > dw / dh:
        nw = h * dw / dh
        x += (w - nw) / 2
        w = nw
    else:
        nh = w * dh / dw
        y += (h - nh) / 2
        h = nh
    return x, y, w, h


def fill_box_int(sw: int, sh: int, dw: int, dh: int, inset: float = 0.0) -> tuple[int, int, int, int]:
    """ffmpeg crop 용 정수(짝수) 영역."""
    x, y, w, h = fill_box(sw, sh, dw, dh, inset)
    iw = max(2, int(w) // 2 * 2)
    ih = max(2, int(h) // 2 * 2)
    ix = min(sw - iw, max(0, int(round(x + (w - iw) / 2))))
    iy = min(sh - ih, max(0, int(round(y + (h - ih) / 2))))
    return iw, ih, ix, iy


def crop_to_fill(im: Image.Image, size: tuple[int, int], inset: float = 0.0,
                 resample=Image.LANCZOS) -> Image.Image:
    x, y, w, h = fill_box(im.width, im.height, size[0], size[1], inset)
    return im.resize(size, resample, box=(x, y, x + w, y + h))


def detect_border(img: Image.Image) -> bool:
    """가장자리 테두리 프레임이 있으면 True.

    보수적 판정: 네 변 중 3변 이상에서 (1) 바깥쪽 0.5~8% 가 균일한 단색 띠이고
    (2) 그 안쪽에서 색이 뚜렷하게 바뀌며 (3) 띠 색들이 서로 비슷할 때만.
    깨끗한 풀블리드 이미지(단색 배경 포함)는 띠가 끝없이 이어지거나 한두 변만 해당돼 걸리지 않는다.
    """
    im = img.convert("RGB")
    im.thumbnail((480, 480), Image.BILINEAR)
    a = np.asarray(im, dtype=np.float32)
    uni, same, step = 9.0, 16.0, 28.0
    found: list[np.ndarray] = []
    t = a.transpose(1, 0, 2)
    for lines in (a, a[::-1], t, t[::-1]):
        n = lines.shape[0]
        lo, hi = max(2, math.ceil(n * 0.005)), max(3, int(n * 0.08))
        chunk = lines[:hi + 6]
        means = chunk.mean(axis=1)
        stds = chunk.std(axis=1).mean(axis=1)
        edge = means[0]
        k = 0
        while k < len(chunk) and stds[k] < uni and np.linalg.norm(means[k] - edge) < same:
            k += 1
        if not lo <= k <= hi:
            continue
        inner = range(k, min(k + 5, len(chunk)))
        if any(np.linalg.norm(means[j] - edge) > step or stds[j] > 2.5 * uni for j in inner):
            found.append(edge)
    if len(found) < 3:
        return False
    return max(float(np.linalg.norm(p - q)) for p in found for q in found) < 40.0


# ---------------------------------------------------------------- 텍스트

def load_font(font_path: Path, size: float) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(font_path), max(8, int(round(size))))
    except OSError as e:
        raise MomoError(f"폰트를 열 수 없음: {font_path}: {e}") from e


def parse_color(color: str, cfg: dict) -> tuple[int, int, int]:
    hexv = (cfg["render"].get("text_colors") or {}).get(color, color)
    try:
        return Image.new("RGB", (1, 1), hexv).getpixel((0, 0))
    except ValueError as e:
        raise MomoError(f"알 수 없는 텍스트 색: {color!r}") from e


def fit_font(font_path: Path, lines: list[str], glyph_h: float, max_w: float,
             stroke_ratio: float) -> tuple[ImageFont.FreeTypeFont, int]:
    """기준 글자('가' 또는 'H') 높이가 glyph_h 가 되게, 가장 긴 줄이 max_w 를 넘으면 축소."""
    ref = "가" if any(HANGUL_RE.search(s) for s in lines) else "H"
    probe = load_font(font_path, 200)
    l, t, r, b = probe.getbbox(ref)
    size = 200 * glyph_h / max(1, b - t)
    for _ in range(4):
        font = load_font(font_path, size)
        stroke = max(2, int(round(font.size * stroke_ratio)))
        widest = max(_width(font, s, stroke) for s in lines)
        if widest <= max_w:
            return font, stroke
        size *= max_w / widest * 0.99
    return font, stroke


def _width(font: ImageFont.FreeTypeFont, s: str, stroke: int) -> int:
    l, _, r, _ = font.getbbox(s, stroke_width=stroke)
    return r - l


def text_image(text: str, font: ImageFont.FreeTypeFont, fill, stroke: int,
               shadow: int = 0) -> Image.Image:
    """글자 + 두꺼운 검정 외곽선 RGBA (여백 최소). shadow>0 이면 아래쪽 그림자."""
    l, t, r, b = font.getbbox(text, stroke_width=stroke)
    pad = 4 + shadow
    size = (r - l + 2 * pad, b - t + 2 * pad)
    org = (pad - l, pad - t)
    # 외곽선 마스크: FreeType stroker 가 겹친 윤곽에서 남기는 바늘구멍을 closing(5x5)으로 메운다
    outline = Image.new("L", size, 0)
    ImageDraw.Draw(outline).text(org, text, font=font, fill=255, stroke_width=stroke, stroke_fill=255)
    outline = outline.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    if shadow:
        sh = Image.new("L", size, 0)
        sh.paste(outline.point(lambda v: v * 150 // 255), (int(shadow * 0.4), shadow))
        im.paste((0, 0, 0, 255), mask=sh)
    black = Image.new("RGBA", size, STROKE_COLOR + (255,))
    black.putalpha(outline)
    im.alpha_composite(black)
    ImageDraw.Draw(im).text(org, text, font=font, fill=fill)
    return im


def band_geometry(cfg: dict, pos: str) -> tuple[int, int]:
    """키워드 밴드의 (y, 높이). top=상단 25%, bottom=하단 25%."""
    r = cfg["render"]
    H = int(r["height"])
    band_h = int(round(H * float(r["text_band_ratio"])))
    return (H - band_h if pos == "bottom" else 0), band_h


def _ease(p: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, p)))


def pop_curve(p: float) -> tuple[float, float]:
    """팝 진행도 p(0..1) → (scale, alpha). 0.85 → 1.04 (60%) → 1.0, alpha 0→1 (60%)."""
    if p <= 0.6:
        scale = 0.85 + 0.19 * _ease(p / 0.6)
    else:
        scale = 1.04 - 0.04 * _ease((p - 0.6) / 0.4)
    return scale, _ease(p / 0.6)


def render_keyword_frames(text: str, font_path: Path, cfg: dict, pos: str, color: str,
                          out_dir: Path) -> list[Path]:
    """키워드 팝 애니메이션 RGBA PNG 시퀀스 (밴드 크기: 화면 폭 × 밴드 높이).

    마지막 프레임이 최종 상태(scale 1, alpha 1) — overlay eof_action=repeat 로 컷 끝까지 유지.
    """
    text = (text or "").strip()
    if not text:
        return []
    r = cfg["render"]
    W, fps = int(r["width"]), int(r["fps"])
    _, band_h = band_geometry(cfg, pos)
    glyph_h = int(r["height"]) * float(r["text_height_ratio"])
    font, stroke = fit_font(font_path, [text], glyph_h, W * 0.9 / 1.04, float(r["text_stroke_ratio"]))
    base = text_image(text, font, parse_color(color, cfg), stroke)
    if base.height * 1.04 > band_h:  # 밴드를 넘치면 밴드에 맞춘다
        k = band_h / (base.height * 1.04)
        base = base.resize((max(1, int(base.width * k)), max(1, int(base.height * k))), Image.LANCZOS)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("kw_*.png"):
        old.unlink()
    n = max(2, int(round(float(r["text_pop_seconds"]) * fps)) + 1)
    paths = []
    for i in range(n):
        scale, alpha = pop_curve(i / (n - 1))
        im = base if scale == 1.0 else base.resize(
            (max(1, round(base.width * scale)), max(1, round(base.height * scale))), Image.LANCZOS)
        if alpha < 1.0:
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda v, a=alpha: int(v * a + 0.5)))
        canvas = Image.new("RGBA", (W, band_h), (0, 0, 0, 0))
        canvas.paste(im, ((W - im.width) // 2, (band_h - im.height) // 2))
        p = out_dir / f"kw_{i:03d}.png"
        canvas.save(p, compress_level=1)
        paths.append(p)
    return paths


# ---------------------------------------------------------------- 켄번즈

def kenburns_params(cut_id: str, ordinal: int, cfg: dict) -> dict:
    """S 컷 순번 홀수=줌인, 짝수=줌아웃. 배율은 컷 id 해시로 zoom 범위 안에서. 드리프트 방향 교차."""
    lo, hi = (float(v) for v in cfg["render"]["kenburns_zoom"])
    h = int(hashlib.md5(cut_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return {"zoom": round(lo + (hi - lo) * h, 4), "zoom_in": ordinal % 2 == 1,
            "drift": float(cfg["render"]["kenburns_drift"]), "drift_dir": 1 if ordinal % 2 == 1 else -1}


def kenburns_frames(im: Image.Image, n: int, size: tuple[int, int], zoom: float, zoom_in: bool,
                    drift: float, drift_dir: int, inset: float = 0.0) -> Iterator[bytes]:
    """rgb24 프레임 n 장. 줌(1→1+zoom 또는 반대)과 좌우 드리프트(화면 폭의 drift 만큼)를 easeInOut 으로.

    원본은 먼저 최대 배율에서 1:1 이 되는 크기(≤ 2x 여유)로 한 번 리샘플하고,
    프레임마다 float 박스로 resize 해서 서브픽셀 정밀도로 움직인다 (정수 스냅 떨림 없음).
    """
    W, H = size
    z0 = 1.0 + drift                      # 드리프트 여유 (가장자리 노출 방지)
    zmax = z0 * (1.0 + zoom)
    SW, SH = int(math.ceil(W * zmax)), int(math.ceil(H * zmax))
    x, y, w, h = fill_box(im.width, im.height, W, H, inset)
    src = im.resize((SW, SH), Image.LANCZOS, box=(x, y, x + w, y + h))
    for f in range(n):
        e = _ease(f / (n - 1)) if n > 1 else 0.0
        z = z0 * (1.0 + zoom * (e if zoom_in else 1.0 - e))
        rw, rh = SW / z, SH / z
        cx = SW / 2 + drift_dir * (e - 0.5) * drift * SW / z
        cx = min(max(cx, rw / 2), SW - rw / 2)
        x0, y0 = cx - rw / 2, (SH - rh) / 2
        yield src.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + rw, y0 + rh)).tobytes()


# ---------------------------------------------------------------- 카드 / 썸네일 / contact sheet

def placeholder_card(lines: list[str], size: tuple[int, int], font_path: Path | None) -> Image.Image:
    """애니매틱용 컷 번호 카드 (없는 이미지 대신)."""
    seed = int(hashlib.md5((lines[0] if lines else "").encode()).hexdigest()[:6], 16)
    hue = (seed % 360) / 360.0
    bg = tuple(int(c * 255) for c in colorsys.hls_to_rgb(hue, 0.82, 0.55))
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    W, H = size
    m = int(H * 0.04)
    d.rectangle([m, m, W - m, H - m], outline=(90, 90, 90), width=max(2, H // 180))
    if font_path is None:
        return im
    y = H * 0.30
    for i, line in enumerate(l for l in lines if l):
        gh = H * (0.16 if i == 0 else 0.055)
        font, _ = fit_font(font_path, [line], gh, W * 0.86, 0.0)
        l, t, r, b = font.getbbox(line)
        d.text(((W - (r - l)) / 2 - l, y - t), line, font=font, fill=(40, 40, 40))
        y += (b - t) + H * 0.05
    return im


def _split_two(text: str) -> list[list[str]]:
    words = text.split()
    layouts = [[text]]
    for i in range(1, len(words)):
        layouts.append([" ".join(words[:i]), " ".join(words[i:])])
    return layouts


def make_thumbnail(image: Image.Image, text: str, font_path: Path, cfg: dict, out_path: Path,
                   pos: str = "top", inset: float = 0.0, max_bytes: int = 2_000_000) -> Path:
    """1280x720 JPEG. 문구는 크게(폭 90% 이내, 필요하면 2줄), 노란 채움 + 두꺼운 검정 외곽선."""
    W, H = (int(v) for v in cfg["render"]["thumbnail_size"])
    im = crop_to_fill(image, (W, H), inset).convert("RGBA")
    text = " ".join((text or "").split())
    if text:
        fill = parse_color("yellow", cfg)
        best = None
        for lines in _split_two(text):
            # 1줄은 글자 높이 ≤ 20% H, 2줄은 줄당 ≤ 17% H
            gh = H * (0.20 if len(lines) == 1 else 0.17)
            font, stroke = fit_font(font_path, lines, gh, W * 0.9, 0.14)
            imgs = [text_image(s, font, fill, stroke, shadow=max(3, stroke // 2)) for s in lines]
            balance = max(i.width for i in imgs) - min(i.width for i in imgs)
            score = (font.size * (1.0 if len(lines) == 1 else 0.9), -balance)
            if best is None or score > best[0]:
                best = (score, imgs)
        imgs = best[1]
        gap = -int(imgs[0].height * 0.12)
        total = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
        margin = int(H * 0.04)
        y = margin if pos != "bottom" else H - margin - total
        for t in imgs:
            im.alpha_composite(t, ((W - t.width) // 2, max(0, y)))
            y += t.height + gap
    rgb = im.convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for q in (92, 88, 84, 80, 74, 68, 60):
        rgb.save(out_path, "JPEG", quality=q, optimize=True, progressive=True)
        if out_path.stat().st_size < max_bytes:
            return out_path
    raise MomoError(f"썸네일을 2MB 미만으로 줄이지 못함: {out_path}")


def contact_sheet(items: list[tuple[Path, str]], out_path: Path, font_path: Path | None = None,
                  cols: int = 4, thumb_w: int = 480) -> Path:
    """(이미지, 라벨) 목록 → 격자 JPEG. 라벨은 각 칸 아래."""
    if not items:
        raise MomoError("contact sheet 에 넣을 이미지가 없음")
    thumb_h = thumb_w * 9 // 16
    label_h = 34
    rows = math.ceil(len(items) / cols)
    sheet = Image.new("RGB", (cols * thumb_w + (cols + 1) * 6, rows * (thumb_h + label_h) + (rows + 1) * 6),
                      (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    font = load_font(font_path, 20) if font_path else ImageFont.load_default()
    for i, (p, label) in enumerate(items):
        r, c = divmod(i, cols)
        x = 6 + c * (thumb_w + 6)
        y = 6 + r * (thumb_h + label_h + 6)
        sheet.paste(crop_to_fill(load_image(p), (thumb_w, thumb_h), 0.0, Image.BILINEAR), (x, y))
        d.text((x + 4, y + thumb_h + 5), label, font=font, fill=(235, 235, 235))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, "JPEG", quality=88)
    return out_path


# ---------------------------------------------------------------- ffmpeg 영상 헬퍼

COLOR_TAGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
TO_709 = "out_color_matrix=bt709:out_range=tv"   # scale 필터 인자: RGB/YUV → bt709 limited


def grab_frame(path: Path, t: float) -> Image.Image:
    proc = run(["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{max(0.0, t):.3f}", "-i", str(path),
                "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"])
    if not proc.stdout:
        raise MomoError(f"프레임을 뽑지 못함: {path} @ {t:.2f}s")
    return Image.open(io.BytesIO(proc.stdout)).convert("RGB")


def video_stream(path: Path) -> dict:
    for s in ffprobe_json(path).get("streams", []):
        if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic"):
            return s
    raise MomoError(f"영상 스트림 없음: {path}")


def in_matrix(stream: dict) -> str:
    """scale 필터 입력 행렬. 태그 없는 HD 소스는 bt709 로 본다 (swscale 기본 bt601 로 색이 틀어지는 것 방지)."""
    if stream.get("color_space") in ("bt709", "bt470bg", "smpte170m", "bt2020nc", "bt2020c"):
        return ""
    return "in_color_matrix=" + ("bt709:" if int(stream.get("height") or 0) >= 720 else "bt601:")


def verify_output(path: Path, total: float, cfg: dict) -> dict:
    """1920x1080 / fps / yuv420p / h264 / aac 48k, 영상·음성 길이 = total ± 1프레임. 어긋나면 MomoError."""
    r = cfg["render"]
    fps = int(r["fps"])
    streams = ffprobe_json(path).get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not v or not a:
        raise MomoError(f"출력에 영상/음성 스트림이 없음: {path}")
    want = {"codec_name": "h264", "width": int(r["width"]), "height": int(r["height"]), "pix_fmt": "yuv420p",
            "r_frame_rate": f"{fps}/1"}
    problems = [f"영상 {k}={v.get(k)!r} (기대 {w!r})" for k, w in want.items() if v.get(k) != w]
    sr = int(cfg["audio"]["sample_rate"])
    if a.get("codec_name") != "aac" or int(a.get("sample_rate") or 0) != sr:
        problems.append(f"음성 {a.get('codec_name')} {a.get('sample_rate')}Hz (기대 aac {sr})")
    vdur, adur = float(v.get("duration") or 0), float(a.get("duration") or 0)
    tol = 1.0 / fps + 1e-3
    if abs(vdur - total) > tol:
        problems.append(f"영상 길이 {vdur:.3f}s ≠ 계획 {total:.3f}s")
    if abs(adur - total) > tol:
        problems.append(f"음성 길이 {adur:.3f}s ≠ 계획 {total:.3f}s")
    if problems:
        raise MomoError(f"출력 검증 실패 ({path.name}):\n  - " + "\n  - ".join(problems))
    return {"video_duration": vdur, "audio_duration": adur, "frames": int(v.get("nb_frames") or 0)}
