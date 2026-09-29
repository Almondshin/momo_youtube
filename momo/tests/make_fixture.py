#!/usr/bin/env python3
"""테스트 픽스처: 완전한 합성 momo root 를 만든다 (validate → build en/ko → compile → upload --dry-run 용).

사용 예
  python momo/tests/make_fixture.py --root /tmp/momo_fx               # 기본 에셋 + ep99
  python momo/tests/make_fixture.py --root /tmp/momo_fx --force       # 픽스처 폴더를 지우고 다시
  python momo/tests/make_fixture.py --root /tmp/momo_fx --episodes 2  # ep99, ep98 (compile 테스트)
  python momo/tests/make_fixture.py --root /tmp/momo_fx --ep ep97     # 기존 픽스처에 ep97 추가

만드는 것
- config.json / library/library.json / templates/ 복사 (저장소 momo/ 에서)
- assets/fonts: 한글 지원 시스템 폰트 (NanumSquareRound → Nanum → wqy-zenhei → Noto CJK 순으로 탐색)
- assets/bgm: 화음 사인파 20초, assets/sfx: pop.wav, whoosh.wav
- library: 클립 5종(testsrc2 1280x720 24fps 5초, 클립마다 다른 색), 고정 음성(사인 비프 1.2~2초), 캐릭터 시트
- episodes/<ep>: 컷 24개(L4 V13 S7, 씬 5) — [pause]/[chant], top/bottom/yellow 텍스트, 테두리 있는 이미지 1장,
  나레이션 > 5초 V 컷(핑퐁) 1개, > 10초 V 컷(프리즈) 1개, 효과음 1개, 비율이 다른 이미지들,
  1280x720 24fps 클립, EN/KO 길이가 다른 사인 비프 음성 블록
- _remote/: 위 에셋의 원본 사본. manifest/library 의 url 이 file:// 로 이곳을 가리킨다 (fetch_assets 테스트).
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from momolib.common import (MOMO_DIR, MomoError, add_root_arg, check_ep, font_supports_hangul,  # noqa: E402
                            get_paths, load_json, main_wrapper, run, save_json)
from momolib.episode import estimate_speech, parse_narration  # noqa: E402
from momolib.render import crop_to_fill  # noqa: E402

MARKER = ".momo_fixture"
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
    "/usr/share/fonts/truetype/nanum/NanumSquareRoundEB.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
LIB_COLORS = {"intro_wave": "0x66cc88", "outro_bye": "0xffaa44", "say_with_me": "0xffe066",
              "cheer": "0xff88bb", "transition": "0x66bbff"}
LIB_AUDIO_LEN = {"en": {"intro": 1.4, "outro": 1.9}, "ko": {"intro": 1.7, "outro": 2.0}}
IMAGE_SIZES = [(1536, 864), (1024, 1024), (1344, 768), (2048, 1152), (1280, 960), (1536, 864), (832, 1248)]
MOTIONS = ["small hop in place", "waves one paw", "ears bounce gently", "nods head gently",
           "picks up the object slowly", "claps paws softly"]

TOPICS = [
    {"en": ["red", "yellow", "blue"], "ko": ["빨강", "노랑", "파랑"], "oe": ["apple", "banana", "ball"],
     "ok": ["사과", "바나나", "공"], "theme": ("colors", "색깔"),
     "rgb": [(226, 48, 48), (250, 204, 40), (42, 112, 230)],
     "title": ("Learn Colors with Momo the Bunny | Red, Yellow, Blue for Toddlers",
               "모모와 색깔 배우기 | 빨강 노랑 파랑 | 유아 색깔 놀이")},
    {"en": ["one", "two", "three"], "ko": ["하나", "둘", "셋"], "oe": ["star", "cup", "cake"],
     "ok": ["별", "컵", "케이크"], "theme": ("numbers", "숫자"),
     "rgb": [(240, 120, 40), (60, 170, 90), (150, 80, 200)],
     "title": ("Count 1 2 3 with Momo the Bunny | Numbers for Toddlers",
               "모모와 숫자 세기 | 하나 둘 셋 | 유아 숫자 놀이")},
    {"en": ["circle", "star", "heart"], "ko": ["동그라미", "별", "하트"], "oe": ["cookie", "sticker", "pillow"],
     "ok": ["쿠키", "스티커", "베개"], "theme": ("shapes", "모양"),
     "rgb": [(230, 90, 150), (250, 190, 40), (70, 160, 220)],
     "title": ("Learn Shapes with Momo the Bunny | Circle, Star, Heart for Kids",
               "모모와 모양 배우기 | 동그라미 별 하트 | 유아 모양 놀이")},
]

# 컷 24개 스켈레톤. kw: a/b/c/theme, obj: 사물 번호, beeps: 음성 블록 길이 고정(초)
SKELETON = [
    dict(scene=1, type="L", library_clip="intro_wave", library_audio="intro"),
    dict(scene=1, type="V", en="Look! Momo found a magic box.", ko="와! 모모가 마법 상자를 찾았어.",
         img="[Momo] standing next to a small gift box on a sunny meadow"),
    dict(scene=1, type="S", en="What is inside? Let's find out together!", ko="안에 뭐가 있을까? 같이 보자!",
         img="[Momo] peeking into an open gift box, soft pastel background"),
    dict(scene=1, type="V", en="Three fun {theme} are hiding here!", ko="재미있는 {ktheme} 세 개가 숨어 있어!",
         kw="theme", img="[Momo] pointing at three toys on a soft rug", color="yellow"),
    dict(scene=2, type="V", en="Look! This is {a}. {Ac}!", ko="봐! 이건 {ka}! {ka}!", kw="a", obj=0,
         color="yellow", img="[Momo] holding a {a} {oa} with both paws, close-up, empty sky above"),
    dict(scene=2, type="S", en="[chant] {Ac}, {a}, {a} {oa}!", ko="[chant] {ka}, {ka}, {ka} {koa}!", kw="a",
         obj=0, momo=False, img="a shiny {a} {oa} on a soft pastel background, close-up"),
    dict(scene=2, type="L", library_clip="say_with_me", en="Can you say {a}? [pause 1.5] {Ac}!",
         ko="같이 말해볼까? {ka}! [pause 1.5] 잘했어!", kw="a"),
    dict(scene=2, type="V", en="Momo holds the {a} {oa} up high. [pause 1] So pretty! {Ac}!",
         ko="모모가 {ka} {koa}를 번쩍 들었어. [pause 1] 예쁘다! {ka}!", kw="a", obj=0,
         beeps={"en": [3.1, 1.3], "ko": [3.5, 1.5]}, img="[Momo] lifting a {a} {oa} above the head"),
    dict(scene=2, type="V", en="Momo gives the {oa} a little hug.", ko="모모가 {koa}를 꼭 안아.", kw="a", obj=0,
         pos="bottom", img="[Momo] hugging a {a} {oa}, lots of sky above"),
    dict(scene=3, type="V", en="Now look over here. What is this? [pause 2] It is {b}! A big {b} {ob}!",
         ko="이제 여기를 봐. 이건 뭘까? [pause 2] {kb}이야! 커다란 {kb} {kob}!", kw="b", obj=1, color="yellow",
         beeps={"en": [4.4, 4.1], "ko": [4.9, 4.5]}, img="[Momo] looking at a big {b} {ob} on the grass"),
    dict(scene=3, type="S", en="{Bc} {ob}! {Bc}!", ko="{kb} {kob}! {kb}!", kw="b", obj=1, momo=False, border=True,
         size=(1536, 864), img="a big {b} {ob} on a soft pastel background, close-up"),
    dict(scene=3, type="V", en="Momo smiles at the {b} {ob}.", ko="모모가 {kb} {kob}를 보고 웃어.", kw="b", obj=1,
         clip_audio=True, img="[Momo] smiling at a {b} {ob}"),
    dict(scene=3, type="V", en="Can you find {b}? [pause 1.5] Yes, {b}!", ko="{kb}을 찾아볼까? [pause 1.5] 맞아, {kb}!",
         kw="b", obj=1, pos="bottom", img="[Momo] searching for a {b} {ob} behind a bush, sky above"),
    dict(scene=3, type="S", en="[chant] {Bc}, {b}, {b} {ob}!", ko="[chant] {kb}, {kb}, {kb} {kob}!", kw="b", obj=1,
         transition="fade", text_at=1.0, img="[Momo] sitting beside a {b} {ob}, soft pastel background"),
    dict(scene=4, type="V", en="Pop! Here comes {c}!", ko="뿅! {kc}이 나왔어!", kw="c", obj=2,
         sfx=[{"file": "pop.wav", "at": 0.4, "gain_db": -4}], img="[Momo] surprised by a {c} {oc} appearing"),
    dict(scene=4, type="S", en="{Cc} {oc}. {Cc}!", ko="{kc} {koc}. {kc}!", kw="c", obj=2, momo=False, color="yellow",
         img="a round {c} {oc} on a soft pastel background, close-up"),
    dict(scene=4, type="V", en="Ducky loves {c} too!", ko="덕키도 {kc}을 좋아해!", kw="c", obj=2, ducky=True,
         img="[Momo] and [Ducky] playing with a {c} {oc} in a meadow"),
    dict(scene=4, type="L", library_clip="cheer", en="Yay! {Cc}! You did it!", ko="야호! {kc}! 잘했어!", kw="c"),
    dict(scene=4, type="V", en="Momo rolls the {c} {oc}.", ko="모모가 {kc} {koc}을 굴려.", kw="c", obj=2,
         pos="bottom", img="[Momo] gently pushing a {c} {oc} on the grass"),
    dict(scene=5, type="S", en="{Ac}, {b}, and {c}! So many {theme}! [chant]",
         ko="{ka}, {kb}, {kc}! {ktheme}이 많아! [chant]", kw="theme", transition="cut",
         img="[Momo] with a {a} {oa}, a {b} {ob} and a {c} {oc} in a row"),
    dict(scene=5, type="V", en="We learned three {theme} today!", ko="오늘 {ktheme} 세 개를 배웠어!", kw="theme",
         img="[Momo] jumping happily in a sunny meadow"),
    dict(scene=5, type="S", en="Say them with me! [pause 1.5] {Ac}, {b}, {c}!",
         ko="같이 말해볼까? [pause 1.5] {ka}, {kb}, {kc}!", img="[Momo] standing in front of three toys, pastel background"),
    dict(scene=5, type="V", en="Momo is so happy. Thank you for playing!", ko="모모는 정말 행복해. 같이 놀아줘서 고마워!",
         img="[Momo] waving in a sunny meadow", motion="waves one paw"),
    dict(scene=5, type="L", library_clip="outro_bye", library_audio="outro"),
]


def h01(*parts) -> float:
    """결정적 0..1 난수 (실행마다 같은 픽스처)."""
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def file_url(p: Path) -> str:
    return p.resolve().as_uri()


def genrec(ep: str, key: str, url: str, credits: float) -> dict:
    job = f"fx-{ep}-{key}"
    return {"status": "approved", "job_id": job, "url": url, "attempts": 1, "credits": credits,
            "history": [{"job_id": job, "url": url, "status": "approved", "reason": None}]}


# ---------------------------------------------------------------- 오디오 합성

def write_wav(path: Path, x: np.ndarray, sr: int) -> Path:
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32767).astype("<i2")
    ch = 1 if pcm.ndim == 1 else pcm.shape[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


def beep(dur: float, sr: int, f0: float, seed: float) -> np.ndarray:
    """말소리 흉내 사인 비프 (음절 박자로 진폭 변화)."""
    t = np.arange(int(round(dur * sr))) / sr
    syl = 3.6 + seed * 1.2
    env = 0.25 + 0.75 * np.abs(np.sin(np.pi * syl * t))
    tone = np.sin(2 * np.pi * f0 * t) + 0.35 * np.sin(4 * np.pi * f0 * t) + 0.12 * np.sin(6 * np.pi * f0 * t)
    x = tone * env
    edge = min(len(x) // 2, int(0.015 * sr))
    if edge:
        ramp = np.linspace(0, 1, edge)
        x[:edge] *= ramp
        x[-edge:] *= ramp[::-1]
    return 0.5 * x / (np.max(np.abs(x)) or 1.0)


def to_mp3(wav: Path) -> Path:
    mp3 = wav.with_suffix(".mp3")
    try:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-c:a", "libmp3lame", "-q:a", "4", str(mp3)])
    except MomoError:
        return wav  # mp3 인코더가 없으면 wav 유지
    wav.unlink()
    return mp3


def make_audio_assets(root: Path) -> None:
    sr = 48000
    t = np.arange(int(0.18 * sr)) / sr
    pop = np.sin(2 * np.pi * (1300 - 2600 * t) * t) * np.exp(-t * 28)
    write_wav(root / "assets/sfx/pop.wav", 0.7 * pop, sr)
    n = int(0.7 * sr)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(n)
    k = np.ones(40) / 40
    swell = np.sin(np.pi * np.arange(n) / n) ** 2
    whoosh = np.convolve(noise, k, mode="same") * swell
    write_wav(root / "assets/sfx/whoosh.wav", 0.8 * whoosh / np.max(np.abs(whoosh)), sr)
    # BGM: C-E-G 화음 + 박자감 (20초, 스테레오)
    expr = ("0.18*(sin(2*PI*261.63*t)+0.8*sin(2*PI*329.63*t)+0.7*sin(2*PI*392*t))*(0.65+0.35*sin(2*PI*2*t))"
            "+0.12*sin(2*PI*130.81*t)*(0.5+0.5*sin(PI*t))")
    (root / "assets/bgm").mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"aevalsrc=exprs='{expr}|{expr.replace('392', '392.4')}':s=44100:d=20",
         "-c:a", "aac", "-b:a", "160k", str(root / "assets/bgm/fixture_bgm.m4a")])


# ---------------------------------------------------------------- 그림

def draw_bunny(d: ImageDraw.ImageDraw, cx: float, by: float, u: float) -> None:
    cream, pink, mint = (252, 247, 238), (250, 180, 190), (150, 222, 195)
    for sx in (-1, 1):  # 귀
        ex = cx + sx * 0.09 * u
        d.ellipse([ex - 0.055 * u, by - 1.02 * u, ex + 0.055 * u, by - 0.62 * u], fill=cream, outline=(200, 190, 180))
        d.ellipse([ex - 0.028 * u, by - 0.96 * u, ex + 0.028 * u, by - 0.68 * u], fill=pink)
    d.ellipse([cx - 0.25 * u, by - 0.42 * u, cx + 0.25 * u, by], fill=cream, outline=(200, 190, 180))  # 몸
    d.chord([cx - 0.25 * u, by - 0.42 * u, cx + 0.25 * u, by], 20, 160, fill=mint)                    # 멜빵바지
    d.ellipse([cx - 0.03 * u, by - 0.2 * u, cx + 0.03 * u, by - 0.14 * u], fill=(255, 215, 40))       # 노란 단추
    d.ellipse([cx - 0.21 * u, by - 0.76 * u, cx + 0.21 * u, by - 0.34 * u], fill=cream, outline=(200, 190, 180))
    for sx in (-1, 1):
        ex = cx + sx * 0.08 * u
        d.ellipse([ex - 0.035 * u, by - 0.6 * u, ex + 0.035 * u, by - 0.52 * u], fill=(30, 25, 30))
        d.ellipse([ex - 0.012 * u, by - 0.59 * u, ex + 0.008 * u, by - 0.57 * u], fill=(255, 255, 255))
        d.ellipse([cx + sx * 0.15 * u - 0.03 * u, by - 0.49 * u, cx + sx * 0.15 * u + 0.03 * u, by - 0.45 * u],
                  fill=(255, 190, 200))
    d.ellipse([cx - 0.02 * u, by - 0.5 * u, cx + 0.02 * u, by - 0.47 * u], fill=pink)


def draw_duck(d: ImageDraw.ImageDraw, cx: float, by: float, u: float) -> None:
    d.ellipse([cx - 0.12 * u, by - 0.18 * u, cx + 0.12 * u, by], fill=(255, 220, 60))
    d.ellipse([cx - 0.07 * u, by - 0.3 * u, cx + 0.07 * u, by - 0.16 * u], fill=(255, 220, 60))
    d.polygon([(cx + 0.06 * u, by - 0.24 * u), (cx + 0.13 * u, by - 0.22 * u), (cx + 0.06 * u, by - 0.2 * u)],
              fill=(250, 140, 30))
    d.ellipse([cx + 0.01 * u, by - 0.27 * u, cx + 0.035 * u, by - 0.245 * u], fill=(20, 20, 20))


def draw_image(size: tuple[int, int], spec: dict, rgb, label: str, font_path: Path, seed: float) -> Image.Image:
    W, H = size
    hue_top = np.array([150 + 60 * seed, 205 + 30 * seed, 250])
    t = np.linspace(0, 1, H)[:, None, None]
    grad = hue_top * (1 - t) + np.array([235, 245, 255]) * t
    im = Image.fromarray(np.broadcast_to(grad, (H, W, 3)).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im)
    d.ellipse([-0.3 * W, 0.68 * H, 1.3 * W, 1.6 * H], fill=(140, 205, 120))  # 언덕
    u = H * 0.5
    if spec.get("momo", True):
        draw_bunny(d, W * 0.42, H * 0.93, u)
    if spec.get("ducky"):
        draw_duck(d, W * 0.2, H * 0.94, u)
    if rgb is not None:
        r = min(W, H) * (0.16 if spec.get("momo", True) else 0.26)
        ox, oy = (W * 0.74, H * 0.72) if spec.get("momo", True) else (W * 0.5, H * 0.6)
        d.ellipse([ox - r, oy - r, ox + r, oy + r], fill=rgb, outline=(60, 60, 60), width=max(2, int(r * 0.04)))
        d.ellipse([ox - r * 0.5, oy - r * 0.6, ox - r * 0.15, oy - r * 0.3], fill=(255, 255, 255))
    font = ImageFont.truetype(str(font_path), max(14, H // 40))
    d.text((W * 0.04, H * 0.9), label, font=font, fill=(40, 60, 40))
    if spec.get("border"):  # 생성 이미지에 가끔 생기는 크림색 액자 테두리
        bw, bh = int(W * 0.025), int(H * 0.025)
        cream = (246, 240, 226)
        for box in ([0, 0, W, bh], [0, H - bh, W, H], [0, 0, bw, H], [W - bw, 0, W, H]):
            d.rectangle(box, fill=cream)
        d.rectangle([bw, bh, W - bw - 1, H - bh - 1], outline=(150, 140, 120), width=max(2, W // 400))
    return im


def pipe_frames(cmd: list[str], frames) -> None:
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for fr in frames:
            proc.stdin.write(fr)
        proc.stdin.close()
    except BrokenPipeError:
        pass
    err = proc.stderr.read().decode("utf-8", "replace")
    if proc.wait() != 0:
        raise MomoError(f"ffmpeg 실패: {' '.join(cmd[:6])} ...\n{err[-1500:]}")


def make_clip(image: Image.Image, out: Path, with_audio: bool) -> None:
    """이미지 기반 1280x720 24fps 5초 클립. 흰 공이 좌→우로, 아래 진행 막대 (핑퐁/정지 확인용)."""
    W, H, n = 1280, 720, 120
    base = crop_to_fill(image, (W, H))

    def frames():
        for f in range(n):
            fr = base.copy()
            d = ImageDraw.Draw(fr)
            x = W * (0.1 + 0.8 * f / (n - 1))
            d.ellipse([x - 22, H * 0.84 - 22, x + 22, H * 0.84 + 22], fill=(255, 255, 255), outline=(0, 0, 0), width=3)
            d.rectangle([0, H - 10, int(W * (f + 1) / n), H], fill=(230, 40, 160))
            yield fr.tobytes()

    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", "24",
           "-i", "-"]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", "sine=f=660:d=5", "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)]
    out.parent.mkdir(parents=True, exist_ok=True)
    pipe_frames(cmd, frames())


# ---------------------------------------------------------------- 기본 에셋

def find_hangul_font() -> Path:
    cands = [Path(p) for p in FONT_CANDIDATES]
    if shutil.which("fc-list"):
        out = subprocess.run(["fc-list", ":lang=ko", "file"], capture_output=True, text=True).stdout
        cands += [Path(line.split(":")[0].strip()) for line in out.splitlines() if line.strip()]
    for p in cands:
        if p.exists() and font_supports_hangul(p):
            return p
    raise MomoError("한글 지원 폰트를 찾지 못함 — `apt install fonts-nanum` 필요")


def make_base(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / MARKER).write_text("momo test fixture — make_fixture.py 가 만든 폴더 (지워도 됨)\n", encoding="utf-8")
    cfg = load_json(MOMO_DIR / "config.json")
    cfg["voices"].update({"en": "fixture_voice_en", "ko": "fixture_voice_ko"})
    save_json(root / "config.json", cfg)
    shutil.copytree(MOMO_DIR / "templates", root / "templates", dirs_exist_ok=True)
    font = find_hangul_font()
    (root / "assets/fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(font, root / "assets/fonts" / font.name)
    print(f"  폰트: {font}")
    make_audio_assets(root)

    lib = load_json(MOMO_DIR / "library/library.json")
    remote = root / "_remote/library"
    for name, color in LIB_COLORS.items():
        src = remote / "clips" / f"{name}.mp4"
        src.parent.mkdir(parents=True, exist_ok=True)
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=24:d=5",
             "-vf", f"drawbox=x=0:y=0:w=iw:h=ih:color={color}@0.45:t=fill", "-c:v", "libx264", "-preset",
             "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", str(src)])
        rec = lib["clips"][name]
        rec.update(genrec("lib", name, file_url(src), 7.5))
        rec["image"] = genrec("lib", name + "-img", file_url(src), 2)
    for lang, lines in LIB_AUDIO_LEN.items():
        for name, dur in lines.items():
            src = write_wav(remote / "audio" / lang / f"{name}.wav", beep(dur, 44100, 300 if lang == "en" else 340,
                                                                          h01(lang, name)), 44100)
            lib["audio"][lang][name].update(genrec("lib", f"{lang}-{name}", file_url(src), 0.2))
    for name in ("momo", "ducky"):
        src = remote / "sheets" / f"{name}.png"
        src.parent.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGB", (1536, 864), (255, 255, 255))
        d = ImageDraw.Draw(sheet)
        for i in range(4):
            (draw_bunny if name == "momo" else draw_duck)(d, 200 + i * 380, 800, 600)
        sheet.save(src)
        lib["character_sheets"][name].update(genrec("lib", f"sheet-{name}", file_url(src), 2))
    save_json(root / "library/library.json", lib)
    shutil.copytree(remote, root / "library", dirs_exist_ok=True)


# ---------------------------------------------------------------- 에피소드

def fmt(text: str, m: dict) -> str:
    return text.format(**m) if text else text


def make_episode(root: Path, ep: str, topic_idx: int) -> None:
    tp = TOPICS[topic_idx % len(TOPICS)]
    cfg = load_json(root / "config.json")
    font = next((root / "assets/fonts").iterdir())
    a, b, c = tp["en"]
    m = {"a": a, "b": b, "c": c, "Ac": a.capitalize(), "Bc": b.capitalize(), "Cc": c.capitalize(),
         "ka": tp["ko"][0], "kb": tp["ko"][1], "kc": tp["ko"][2], "oa": tp["oe"][0], "ob": tp["oe"][1],
         "oc": tp["oe"][2], "koa": tp["ok"][0], "kob": tp["ok"][1], "koc": tp["ok"][2],
         "theme": tp["theme"][0], "ktheme": tp["theme"][1]}
    kw_map = {"a": (a.upper(), tp["ko"][0]), "b": (b.upper(), tp["ko"][1]), "c": (c.upper(), tp["ko"][2]),
              "theme": (tp["theme"][0].upper(), tp["theme"][1])}
    epdir = root / "episodes" / ep
    remote = root / "_remote" / ep
    cuts = []
    n_img = 0
    for i, sk in enumerate(SKELETON):
        cid = f"c{i + 1:02d}"
        cut = {"id": cid, "scene": sk["scene"], "type": sk["type"]}
        if sk["type"] == "L":
            cut["library_clip"] = sk["library_clip"]
            if sk.get("library_audio"):
                cut["library_audio"] = sk["library_audio"]
                cut["narration"] = {lg: cfg["fixed_lines"][lg][sk["library_audio"]] for lg in ("en", "ko")}
        if "narration" not in cut:
            cut["narration"] = {"en": fmt(sk["en"], m), "ko": fmt(sk["ko"], m)}
        kw = kw_map.get(sk.get("kw"))
        cut["keyword"] = {"en": kw[0], "ko": kw[1]} if kw else {"en": "", "ko": ""}
        for key, field in (("pos", "text_pos"), ("color", "text_color"), ("transition", "transition"),
                           ("text_at", "text_at"), ("sfx", "sfx")):
            if key in sk:
                cut[field] = sk[key]
        if sk["type"] != "L":
            cut["image_prompt"] = fmt(sk["img"], m)
            if sk.get("momo") is False:
                cut["momo"] = False
            if sk.get("border"):
                cut["inset"] = None  # 자동 감지 경로
            cut["gen"] = {}
            size = sk.get("size") or IMAGE_SIZES[n_img % len(IMAGE_SIZES)]
            n_img += 1
            rgb = tp["rgb"][sk["obj"]] if "obj" in sk else None
            img = draw_image(size, sk, rgb, f"{ep} {cid} {size[0]}x{size[1]}", font, h01(ep, cid))
            src = remote / "images" / f"{cid}.png"
            src.parent.mkdir(parents=True, exist_ok=True)
            img.save(src)
            cut["gen"]["image"] = genrec(ep, f"{cid}-img", file_url(src), 2)
            if sk["type"] == "V":
                cut["motion"] = sk.get("motion") or MOTIONS[i % len(MOTIONS)]
                clip = remote / "clips" / f"{cid}.mp4"
                make_clip(img, clip, bool(sk.get("clip_audio")))
                cut["gen"]["clip"] = genrec(ep, f"{cid}-clip", file_url(clip), 7.5)
        if not cut.get("library_audio"):
            cut["audio_src"] = {}
            for lang in ("en", "ko"):
                items = [it for it in parse_narration(cut["narration"][lang]) if it.kind == "speech"]
                fixed = (sk.get("beeps") or {}).get(lang)
                recs = {}
                for k, it in enumerate(items):
                    dur = fixed[k] if fixed else max(0.8, estimate_speech(it.text, lang) * (0.8 + 0.4 * h01(ep, cid, lang, k)))
                    sr = 24000 if lang == "en" else 44100
                    f0 = 280 + 60 * h01(ep, cid, k) if lang == "en" else 330 + 60 * h01(ep, cid, k)
                    wav = write_wav(remote / "audio" / lang / f"{cid}_{it.index}.wav", beep(dur, sr, f0, h01(cid, lang)), sr)
                    if h01(ep, cid, lang, "fmt") < 0.15:
                        wav = to_mp3(wav)
                    recs[str(it.index)] = genrec(ep, f"{cid}-{lang}-{it.index}", file_url(wav), 0.2)
                cut["audio_src"][lang] = recs
        cuts.append(cut)

    title_en, title_ko = tp["title"]
    hashtags = "#kidslearning #toddler #preschool #nurseryrhymes #momothebunny #learnwithmomo #kids " \
               "#babylearning #educational #" + tp["theme"][0]
    manifest = {
        "schema": 1, "ep": ep, "status": "producing",
        "topic": {"en": f"Learn {tp['theme'][0]}: {a}, {b}, {c}", "ko": f"{tp['theme'][1]} 배우기: {' '.join(tp['ko'])}"},
        "benchmark": {"channel_url": None, "research_dir": None, "chosen_axis": "학습 소재"},
        "characters": ["momo", "ducky"],
        "title": {"en": title_en, "ko": title_ko},
        "thumbnail": {"cut": "c05", "text": {"en": f"{a} {b} {c}".upper(), "ko": " ".join(tp["ko"])}, "text_pos": "top"},
        "bgm": None,
        "upload": {
            "en": {"title": title_en, "tags": [a, b, c, tp["theme"][0], "toddler", "kids", "learning", "momo"],
                   "description": f"Learn {tp['theme'][0]} with Momo the Bunny!\n\n"
                                  f"- {a.capitalize()}: the {tp['oe'][0]}\n- {b.capitalize()}: the {tp['oe'][1]}\n"
                                  f"- {c.capitalize()}: the {tp['oe'][2]}\n\n{hashtags}", "playlist_id": None},
            "ko": {"title": title_ko, "tags": tp["ko"] + [tp["theme"][1], "유아", "어린이", "모모"],
                   "description": f"모모와 함께 {tp['theme'][1]}을 배워요!\n\n"
                                  f"- {tp['ko'][0]}: {tp['ok'][0]}\n- {tp['ko'][1]}: {tp['ok'][1]}\n"
                                  f"- {tp['ko'][2]}: {tp['ok'][2]}\n\n{hashtags}", "playlist_id": None},
        },
        "credits": {"estimate": 150, "spent": 0, "generations": 0, "regenerations": 0},
        "notes": {"v_over_reason": None, "approvals": ["fixture"], "next_time": ["fixture: 실제 에피소드 아님"]},
        "cuts": cuts,
    }
    save_json(epdir / "manifest.json", manifest)
    shutil.copytree(remote, epdir, dirs_exist_ok=True)


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="momo 테스트 픽스처 생성")
    add_root_arg(ap)
    ap.add_argument("--ep", default="ep99", help="첫 에피소드 번호 (기본 ep99)")
    ap.add_argument("--episodes", type=int, default=1, help="만들 에피소드 수 (ep99, ep98, ep97 ...)")
    ap.add_argument("--force", action="store_true", help="픽스처 폴더를 지우고 다시 만듦")
    args = ap.parse_args()
    root = get_paths(args).root
    if root == MOMO_DIR or MOMO_DIR.is_relative_to(root) or root.is_relative_to(MOMO_DIR):
        raise MomoError(f"픽스처는 저장소 밖 임시 폴더에만 만들 수 있음: {root} (--root 지정)")
    first = check_ep(args.ep)
    num = int(first[2:])
    if args.episodes < 1 or num - args.episodes + 1 < 1:
        raise MomoError("--episodes 값이 잘못됨")
    eps = [f"ep{num - k:0{len(first) - 2}d}" for k in range(args.episodes)]

    is_fixture = (root / MARKER).exists()
    if root.exists() and any(root.iterdir()) and not is_fixture:
        raise MomoError(f"비어 있지 않은 폴더이고 픽스처도 아님 — 건드리지 않음: {root}")
    if args.force and is_fixture:
        shutil.rmtree(root)
        is_fixture = False
    for ep in eps:
        if (root / "episodes" / ep).exists():
            raise MomoError(f"{ep} 가 이미 있음 (--force 로 전체 재생성)")
    if not is_fixture:
        print(f"픽스처 기본 에셋 생성: {root}")
        make_base(root)
    for ep in eps:
        print(f"에피소드 {ep} 생성")
        make_episode(root, ep, int(ep[2:]) % 3)
    print(f"✔ 픽스처 준비됨: {root} ({', '.join(eps)})")
    return 0


if __name__ == "__main__":
    main_wrapper(main)
