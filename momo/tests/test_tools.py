#!/usr/bin/env python3
"""제작 보조 스크립트 테스트 — 임시 root 에서 네트워크 없이 (file:// 와 로컬 http.server).

사용: python3 momo/tests/test_tools.py        (실패가 있으면 exit 1)

대상: new_episode, validate_manifest(--table/--json), hf_jobs(plan image/clip/audio/library, voice-samples,
record, status), estimate_credits(합계·캡 초과 exit 2), fetch_assets(file://, http, 재시도, 확장자 결정, 검증 실패,
URL 변경 시 재다운로드, --library), doctor(폰트·BGM ✖, 비밀 값 비출력), episode_readme,
hf_api(Higgsfield API — httpx.MockTransport 위에서: payload 매핑, Idempotency-Key, 즉시 기록, 실패·nsfw, 403 → MCP plan,
재전송, dry-run, estimate 정산, archive).
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
import uuid
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MOMO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MOMO))

from PIL import Image  # noqa: E402

import doctor  # noqa: E402
import episode_readme  # noqa: E402
import estimate_credits  # noqa: E402
import fetch_assets  # noqa: E402
import hf_jobs  # noqa: E402
import new_episode  # noqa: E402
import validate_manifest  # noqa: E402
from momolib.common import MomoError, Paths, deep_merge, font_supports_hangul, load_config  # noqa: E402
from momolib.episode import compose_image_prompt, compose_motion_prompt  # noqa: E402

EP = "ep42"
FONT_CANDIDATES = [*sorted((MOMO / "assets/fonts").glob("*.ttf")),
                   Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
                   Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")]
CUTS = [
    {"id": "c01", "scene": 1, "type": "L", "library_clip": "intro_wave", "library_audio": "intro"},
    {"id": "c02", "scene": 1, "type": "V", "image_prompt": "[Momo] waving hello next to a red ball in a sunny meadow",
     "motion": "waves one paw", "keyword": {"en": "RED", "ko": "빨강"},
     "narration": {"en": "Look at the red ball! [pause 1] Red!", "ko": "빨간 공이야! [pause 1] 빨강!"}},
    {"id": "c03", "scene": 2, "type": "S", "momo": False,
     "image_prompt": "a shiny red ball on a soft pastel background",
     "keyword": {"en": "RED", "ko": "빨강"}, "narration": {"en": "Red ball. Red!", "ko": "빨간 공. 빨강!"}},
    {"id": "c04", "scene": 3, "type": "V", "image_prompt": "[Momo] and [Ducky] playing with a red ball on the grass",
     "motion": "small hop in place", "keyword": {"en": "RED", "ko": "빨강"},
     "narration": {"en": "Ducky likes red too!", "ko": "더키도 빨강을 좋아해!"}},
    {"id": "c05", "scene": 4, "type": "L", "library_clip": "say_with_me", "keyword": {"en": "RED", "ko": "빨강"},
     "narration": {"en": "Can you say red? [pause 1.5] Red!", "ko": "같이 말해볼까? [pause 1.5] 빨강!"}},
    {"id": "c06", "scene": 5, "type": "L", "library_clip": "outro_bye", "library_audio": "outro"},
]


# ---------------------------------------------------------------- 헬퍼

def run(mod, *args: str) -> tuple[int, str, str]:
    """스크립트 main 을 같은 프로세스에서 실행 → (exit code, stdout, stderr). MomoError 는 exit 1."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = mod.main(list(args)) or 0
        except MomoError as e:
            print(f"[중단] {e}", file=sys.stderr)
            code = 1
    return code, out.getvalue(), err.getvalue()


def call(mod, *args: str) -> tuple[int, str]:
    code, out, err = run(mod, *args)
    return code, out + err


def ok(mod, *args: str) -> str:
    code, out = call(mod, *args)
    assert code == 0, (mod.__name__, args, code, out)
    return out


def okj(mod, *args: str):
    """exit 0 + stdout 이 순수 JSON 이어야 함."""
    code, out, err = run(mod, *args)
    assert code == 0, (mod.__name__, args, code, out, err)
    return json.loads(out)


def fails(mod, *args: str, needle: str = "", code: int = 1) -> str:
    got, out = call(mod, *args)
    assert got == code, (mod.__name__, args, got, out)
    assert needle in out, (needle, out)
    return out


def rj(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def wj(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_wav(p: Path, seconds: float = 0.6, sr: int = 24000, freq: float = 440.0) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * sr)
    frames = b"".join(int(8000 * math.sin(2 * math.pi * freq * i / sr)).to_bytes(2, "little", signed=True)
                      for i in range(n))
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(frames)
    return p


def write_png(p: Path, color=(220, 60, 60), size=(96, 54), fmt: str = "PNG") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(p, fmt)
    return p


def write_mp4(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=64x36:r=10:d=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)], check=True)
    return p


def fresh_library(lib: dict) -> dict:
    """실제 library.json 의 진행 상태와 무관하게 — 시트만 승인, 클립·고정 음성·음성 샘플은 첫 편 전 상태로."""
    blank = {"status": "missing", "job_id": None, "url": None, "attempts": 0, "credits": 0}
    for rec in lib["clips"].values():
        for k in ("history", "reason"):
            rec.pop(k, None)
        rec.update(blank)
        rec["image"] = dict(blank)
    for lines in lib["audio"].values():
        for rec in lines.values():
            for k in ("history", "reason"):
                rec.pop(k, None)
            rec.update(blank)
    lib["voice_samples"] = []
    return lib


def make_root(tmp: Path, cfg_patch: dict | None = None, assets: bool = True) -> Path:
    """config/library/templates 복사 + 폰트·BGM + ep42 manifest (컷 6개, L3 V2 S1)."""
    root = tmp / "root"
    (root / "library").mkdir(parents=True)
    cfg = json.loads((MOMO / "config.json").read_text(encoding="utf-8"))
    cfg["voices"].update({"en": None, "ko": None})
    cfg["languages"] = ["en", "ko"]  # bilingual coverage; test_english_only checks ["en"]
    wj(root / "config.json", deep_merge(cfg, cfg_patch or {}))
    shutil.copytree(MOMO / "templates", root / "templates")
    lib = fresh_library(rj(MOMO / "library/library.json"))
    sheet = write_png(tmp / "remote/sheet.png", (250, 250, 250))
    for e in lib["character_sheets"].values():  # 테스트는 네트워크 없이 — 시트 URL 을 로컬 파일로
        e["url"] = sheet.as_uri()
    wj(root / "library/library.json", lib)
    if assets:
        font = next(p for p in FONT_CANDIDATES if p.exists() and font_supports_hangul(p))
        (root / "assets/fonts").mkdir(parents=True)
        shutil.copy2(font, root / "assets/fonts" / font.name)
        write_wav(root / "assets/bgm/bgm.wav", 2.0, 48000, 330)
    ok(new_episode, "--root", str(root), "--ep", EP, "--topic-en", "Red", "--topic-ko", "빨강")
    m = rj(root / "episodes" / EP / "manifest.json")
    cfg_now = load_config(Paths(root))
    cuts = copy.deepcopy(CUTS)
    for c in cuts:
        if c.get("library_audio"):
            c["narration"] = {lg: cfg_now["fixed_lines"][lg][c["library_audio"]] for lg in ("en", "ko")}
            c["keyword"] = {"en": "", "ko": ""}
    m.update({"cuts": cuts, "title": {"en": "Learn Red with Momo the Bunny", "ko": "모모와 빨강 배우기"},
              "thumbnail": {"cut": "c02", "text": {"en": "RED", "ko": "빨강"}, "text_pos": "top"},
              "notes": {"v_over_reason": None, "approvals": ["test"], "next_time": ["키워드를 더 크게"]}})
    m["upload"]["en"].update({"title": "Learn Red with Momo", "tags": ["red", "toddler"],
                              "description": "Learn red!\n\n#kids"})
    wj(root / "episodes" / EP / "manifest.json", m)
    return root


def manifest(root: Path) -> dict:
    return rj(root / "episodes" / EP / "manifest.json")


def cut(root: Path, cid: str) -> dict:
    return next(c for c in manifest(root)["cuts"] if c["id"] == cid)


def plan(root: Path, *args: str) -> dict:
    return okj(hf_jobs, "plan", "--root", str(root), *args)


def record(root: Path, *args: str) -> str:
    return ok(hf_jobs, "record", "--root", str(root), *args)


def set_voices(root: Path, en="v_en", ko="v_ko") -> None:
    cfg = rj(root / "config.json")
    cfg["voices"].update({"en": en, "ko": ko})
    wj(root / "config.json", cfg)


# ---------------------------------------------------------------- 테스트

def test_new_episode(tmp: Path) -> None:
    root = make_root(tmp)
    ep = root / "episodes" / EP
    for d in ("images", "clips", "audio/en", "audio/ko", "out"):
        assert (ep / d).is_dir(), d
    fails(new_episode, "--root", str(root), "--ep", EP, needle="이미 있음")
    ok(new_episode, "--root", str(root), "--ep", EP, "--force")
    m = manifest(root)
    assert m["ep"] == EP and m["status"] == "planning" and len(m["cuts"]) == 2, m
    assert (ep / "manifest.json.bak").exists()
    assert len(rj(ep / "manifest.json.bak")["cuts"]) == 6  # 백업은 덮어쓰기 전 내용
    fails(new_episode, "--root", str(root), "--ep", "ep2; rm", needle="형식")


def test_validate_table_and_json(tmp: Path) -> None:
    root = make_root(tmp)
    out = ok(validate_manifest, "--root", str(root), "--ep", EP, "--table")
    assert "✔ 통과" in out and "예상 길이 EN" in out, out
    md = (root / "episodes" / EP / "plan.md").read_text(encoding="utf-8")
    cfg = load_config(Paths(root))
    c02, c04 = CUTS[1], CUTS[3]
    assert compose_image_prompt(cfg, c02) in md and compose_motion_prompt(cfg, c02) in md
    assert cfg["character"]["ducky"] in compose_image_prompt(cfg, c04) and compose_image_prompt(cfg, c04) in md
    assert cfg["style_lock"] in md and "(라이브러리 `intro_wave` + 고정 음성 `intro`)" in md
    assert "| 컷 | 씬 | 타입 | 나레이션 EN | 나레이션 KO | 화면 키워드 EN / KO |" in md
    assert "V 2 (12~15)" in md and "S 1 (6~8)" in md and "L 3 (3~4)" in md, md[:800]
    assert "예상 길이: EN " in md and "음성 추정 포함" in md
    data = okj(validate_manifest, "--root", str(root), "--ep", EP, "--json")
    assert data["ok"] and not data["errors"] and data["counts"] == {"L": 3, "V": 2, "S": 1}
    assert data["durations"]["en"]["total"] > 10 and data["durations"]["ko"]["estimated"] is True
    fails(validate_manifest, "--root", str(root), "--ep", EP, "--strict", needle="--strict")

    m = manifest(root)
    m["cuts"][1]["motion"] = ""
    m["cuts"][2]["image_prompt"] = "a [Robot] with a ball"
    m["cuts"][3]["audio_src"] = {"en": {"5": {"status": "approved"}}}
    wj(root / "episodes" / EP / "manifest.json", m)
    out = fails(validate_manifest, "--root", str(root), "--ep", EP, "--table", needle="V 컷에 motion 없음")
    assert "알 수 없는 [태그]" in out and "['5']" in out, out
    assert "✖" in (root / "episodes" / EP / "plan.md").read_text(encoding="utf-8")


def test_plan_image_payloads(tmp: Path) -> None:
    root = make_root(tmp, {"higgsfield": {"max_parallel_images": 2}})
    cfg = load_config(Paths(root))
    hf = cfg["higgsfield"]
    momo_el, ducky_el = hf["momo_element_id"], hf["ducky_element_id"]
    assert momo_el and ducky_el
    p = plan(root, "--ep", EP, "--kind", "image")
    assert p["remaining"] == 3 and p["count"] == 2 and [i["cut"] for i in p["items"]] == ["c02", "c03"], p
    want = {"model": hf["image_model"], "prompt": f"<<<{momo_el}>>> " + compose_image_prompt(cfg, CUTS[1]),
            "aspect_ratio": "16:9", "resolution": hf["image_resolution"], "folder_id": hf["folder_id"]}
    it = p["items"][0]
    assert it["tool"] == "generate_image" and it["params"] == want, it
    assert "<<<" not in p["items"][1]["params"]["prompt"]  # momo:false 사물 컷
    rec = it["record"]
    assert "record" in rec and (f"--root {root}" in rec or f"--root {root.resolve()}" in rec) \
        and "--ep ep42 --cut c02 --kind image" in rec, rec  # macOS: /var → /private/var
    assert rec.endswith("--job-id <JOB_ID> --url '<URL>' --status generated"), rec
    everything = plan(root, "--ep", EP, "--kind", "image", "--all")
    c04 = everything["items"][2]["params"]["prompt"]
    assert everything["count"] == 3 and c04.startswith(f"<<<{momo_el}>>> <<<{ducky_el}>>> Momo, a chubby"), c04
    assert [i["cut"] for i in plan(root, "--ep", EP, "--kind", "image", "--cuts", "c04")["items"]] == ["c04"]
    assert plan(root, "--ep", EP, "--kind", "image", "--cuts", "c01")["blocked"]
    fails(hf_jobs, "plan", "--root", str(root), "--ep", EP, "--kind", "image", "--cuts", "c99", needle="c99")

    cfg_raw = rj(root / "config.json")  # Element 가 없으면 자리표시도 없다
    cfg_raw["higgsfield"].update({"momo_element_id": None, "ducky_element_id": None, "element_ids": {},
                                  "folder_id": None})
    wj(root / "config.json", cfg_raw)
    it = plan(root, "--ep", EP, "--kind", "image", "--cuts", "c04")["items"][0]
    assert it["params"]["prompt"] == compose_image_prompt(cfg, CUTS[3]) and "folder_id" not in it["params"], it


def test_record_flow_and_credits(tmp: Path) -> None:
    root = make_root(tmp)
    base = ["--ep", EP, "--cut", "c02", "--kind", "image"]
    out = record(root, *base, "--job-id", "j1", "--url", "file:///x1.png", "--status", "generated")
    assert "pending → generated" in out
    m = manifest(root)
    g = cut(root, "c02")["gen"]["image"]
    assert (g["status"], g["job_id"], g["attempts"], g["credits"], len(g["history"])) == ("generated", "j1", 1, 2, 1)
    assert m["credits"] == {"estimate": None, "spent": 2, "generations": 1, "regenerations": 0}, m["credits"]
    assert m["status"] == "producing"
    out = record(root, *base, "--job-id", "j1", "--url", "file:///x1.png", "--status", "generated")  # 같은 명령 재실행
    assert "다시 세지 않음" in out and manifest(root)["credits"]["spent"] == 2
    record(root, *base, "--status", "rejected", "--reason", "단추가 안 보임")
    g = cut(root, "c02")["gen"]["image"]
    assert g["status"] == "rejected" and g["history"][0]["reason"] == "단추가 안 보임" and g["reason"]
    record(root, *base, "--job-id", "j2", "--url", "file:///x2.png", "--status", "generated")
    cr = manifest(root)["credits"]
    assert (cr["spent"], cr["generations"], cr["regenerations"]) == (4, 2, 1), cr
    record(root, *base, "--status", "approved")
    record(root, *base, "--job-id", "j2", "--status", "approved")
    g = cut(root, "c02")["gen"]["image"]
    assert g["status"] == "approved" and g["attempts"] == 2 and g["credits"] == 4 and g["url"] == "file:///x2.png"
    assert [h["status"] for h in g["history"]] == ["rejected", "approved"]
    assert manifest(root)["credits"]["spent"] == 4
    fails(hf_jobs, "record", "--root", str(root), *base, "--job-id", "j3", "--status", "generated", needle="--force")
    record(root, *base, "--job-id", "j1", "--status", "approved")  # 예전 시도를 승인 → 그 결과로 전환
    g = cut(root, "c02")["gen"]["image"]
    assert g["job_id"] == "j1" and g["url"] == "file:///x1.png" and manifest(root)["credits"]["spent"] == 4

    # 처음 보는 job 을 바로 approved → 생성 1회로 센다 / 승인된 clip·audio 는 다시 세지 않음
    record(root, "--ep", EP, "--cut", "c02", "--kind", "clip", "--job-id", "k1", "--url", "u", "--status", "approved")
    clip = cut(root, "c02")["gen"]["clip"]
    assert clip["credits"] == 7.5 and clip["history"][0]["start_image"] == "j1", clip
    record(root, "--ep", EP, "--cut", "c02", "--kind", "clip", "--status", "approved")
    record(root, "--ep", EP, "--cut", "c03", "--kind", "audio", "--lang", "en", "--job-id", "a1", "--url", "u",
           "--status", "generated")
    record(root, "--ep", EP, "--cut", "c03", "--kind", "audio", "--lang", "en", "--status", "approved")
    assert cut(root, "c03")["audio_src"]["en"]["1"]["credits"] == 0.2
    cr = manifest(root)["credits"]
    assert (cr["spent"], cr["generations"]) == (11.7, 4), cr
    record(root, "--ep", EP, "--cut", "c02", "--kind", "audio", "--lang", "ko", "--block", "2", "--job-id", "a2",
           "--url", "u", "--status", "generated", "--credits", "0.5")
    assert manifest(root)["credits"]["spent"] == 12.2

    R = ["record", "--root", str(root), "--ep", EP]
    fails(hf_jobs, *R, "--cut", "c99", "--kind", "image", "--job-id", "x", "--status", "generated", needle="c99")
    fails(hf_jobs, *R, "--cut", "c03", "--kind", "clip", "--job-id", "x", "--status", "generated", needle="V 컷만")
    fails(hf_jobs, *R, "--cut", "c01", "--kind", "image", "--job-id", "x", "--status", "generated", needle="L 컷")
    fails(hf_jobs, *R, "--cut", "c01", "--kind", "audio", "--lang", "en", "--job-id", "x", "--status", "generated",
          needle="라이브러리 고정 음성")
    fails(hf_jobs, *R, "--cut", "c02", "--kind", "audio", "--lang", "en", "--job-id", "x", "--status", "generated",
          needle="--block")
    fails(hf_jobs, *R, "--cut", "c02", "--kind", "audio", "--lang", "en", "--block", "3", "--job-id", "x",
          "--status", "generated", needle="블록 3")
    fails(hf_jobs, *R, "--cut", "c04", "--kind", "image", "--status", "approved", needle="기록된 생성이 없음")
    fails(hf_jobs, *R, "--cut", "c04", "--kind", "image", "--status", "generated", needle="--job-id")
    fails(hf_jobs, "record", "--root", str(root), "--cut", "c04", "--kind", "image", "--job-id", "x",
          "--status", "generated", needle="--ep")
    assert manifest(root)["credits"]["spent"] == 12.2  # 거부된 기록은 아무것도 바꾸지 않는다


def momo_still(path: Path, eye_d: int) -> Path:
    """Synthetic Momo: cream head with two dark eyes (diameter eye_d, 120 px apart) above mint overalls."""
    import numpy as np
    a = np.zeros((716, 1284, 3), np.uint8)
    a[:] = (120, 190, 245)
    yy, xx = np.mgrid[:716, :1284]
    a[(yy - 250) ** 2 + (xx - 640) ** 2 < 170 ** 2] = (240, 228, 205)
    for cx in (580, 700):
        a[(yy - 240) ** 2 + (xx - cx) ** 2 < (eye_d / 2) ** 2] = (30, 25, 30)
    a[430:640, 530:750] = (150, 220, 190)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a).save(path)
    return path


def test_onmodel_gate(tmp: Path) -> None:
    from momolib import onmodel
    root = make_root(tmp)
    cfg = load_config(Paths(root))
    img = root / "episodes" / EP / "images" / "c02.png"
    good = onmodel.check_image(cfg, momo_still(tmp / "good.png", 60))
    bad = onmodel.check_image(cfg, momo_still(tmp / "bad.png", 20))
    assert good["verdict"] == "ok" and 0.9 < good["ratio"] < 1.15, good          # huge round eyes ≈ the sheet
    assert bad["verdict"] == "off" and bad["ratio"] < 0.5, bad                    # beady eyes (ep04 c33 was 0.42)
    blank = onmodel.check_image(cfg, write_png(tmp / "blank.png", (250, 250, 250)))
    assert blank["verdict"] == "unmeasured"                                       # no Momo → never blocks
    base = ["--ep", EP, "--cut", "c02", "--kind", "image"]
    record(root, *base, "--job-id", "j1", "--url", "file:///x1.png", "--status", "generated")
    momo_still(img, 20)
    fails(hf_jobs, "record", "--root", str(root), *base, "--status", "approved", needle="--off-model-ok")
    assert cut(root, "c02")["gen"]["image"]["status"] == "generated"
    out = record(root, *base, "--status", "approved", "--off-model-ok")           # looked at it: approve anyway
    assert "--off-model-ok 로 승인" in out and cut(root, "c02")["gen"]["image"]["off_model_ok"] is True
    set_voices(root)
    m = manifest(root)
    del next(c for c in m["cuts"] if c["id"] == "c02")["gen"]["image"]["off_model_ok"]
    wj(root / "episodes" / EP / "manifest.json", m)
    p = plan(root, "--ep", EP, "--kind", "clip", "--cuts", "c02", "--lang", "en")
    assert not p["items"] and any("시작 이미지의 모모" in b for b in p["blocked"]), p   # bad start frame = bad clip
    momo_still(img, 60)
    p = plan(root, "--ep", EP, "--kind", "clip", "--cuts", "c02", "--lang", "en")
    assert not any("시작 이미지의 모모" in b for b in p["blocked"]), p
    out = ok(hf_jobs, "onmodel", "--root", str(root), "--ep", EP)
    assert "✔ c02 image" in out and "모델과 다른 것 0개" in out, out


def test_hf_api_helpers(tmp: Path) -> None:
    import os
    import hf_api
    env = tmp / ".env.local"
    env.write_text("# comment\nHF_KEY='kid123:secret456'\n", encoding="utf-8")
    saved = {k: os.environ.pop(k, None) for k in ("HF_KEY", "HF_API_KEY", "HF_API_SECRET")}
    try:
        hf_api.load_key(env)
        assert os.environ["HF_KEY"] == "kid123:secret456"      # quotes stripped, never printed
        del os.environ["HF_KEY"]
        env.write_text("HF_KEY=\n", encoding="utf-8")
        try:
            hf_api.load_key(env)
            raise AssertionError("empty key must fail")
        except MomoError as e:
            assert "HF_KEY" in str(e) and "secret" not in str(e)
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
    assert hf_api.media_url({"status": "completed", "video": {"url": "https://x/v.mp4"}}) == "https://x/v.mp4"
    assert hf_api.media_url({"images": [{"url": "https://x/i.png"}]}) == "https://x/i.png"
    assert hf_api.media_url({"status": "completed"}) is None


def test_plan_clip_and_audio(tmp: Path) -> None:
    root = make_root(tmp)
    cfg = load_config(Paths(root))
    hf = cfg["higgsfield"]
    p = plan(root, "--ep", EP, "--kind", "clip")
    assert not p["items"] and len(p["blocked"]) == 2, p
    record(root, "--ep", EP, "--cut", "c02", "--kind", "image", "--job-id", "img-2", "--url", "u", "--status",
           "approved")
    p = plan(root, "--ep", EP, "--kind", "clip")
    assert [i["cut"] for i in p["items"]] == ["c02"] and len(p["blocked"]) == 1
    assert p["items"][0]["params"] == {
        "model": hf["video_model"], "prompt": compose_motion_prompt(cfg, CUTS[1]), "aspect_ratio": "16:9",
        "duration": hf["video_duration"], "resolution": hf["video_resolution"],
        "medias": [{"role": "start_image", "value": "img-2"}], "folder_id": hf["folder_id"]}, p["items"][0]
    assert "Keep the character design exactly the same" in p["items"][0]["params"]["prompt"]

    fails(hf_jobs, "plan", "--root", str(root), "--ep", EP, "--kind", "audio", "--lang", "en", needle="voice-samples")
    set_voices(root)
    p = plan(root, "--ep", EP, "--kind", "audio", "--lang", "en")
    keys = [i["key"] for i in p["items"]]
    assert keys == ["c02 audio en #1", "c02 audio en #2", "c03 audio en #1", "c04 audio en #1",
                    "c05 audio en #1", "c05 audio en #2"], keys
    first = p["items"][0]
    assert first["params"] == {"model": hf["audio_model"], "prompt": "Look at the red ball!", "voice_type": "preset",
                               "voice_id": "v_en", "folder_id": hf["folder_id"]}, first
    assert "--lang en --block 1 --job-id" in first["record"]
    assert all("[pause" not in i["params"]["prompt"] for i in p["items"])
    assert len(plan(root, "--ep", EP, "--kind", "audio")["items"]) == 12  # en + ko


def test_plan_lipsync_clips(tmp: Path) -> None:
    root = make_root(tmp)
    m = manifest(root)
    for c in m["cuts"]:
        if c["id"] in ("c02", "c04"):  # c02: two speech blocks per language, c04: one
            c.update({"lipsync": True, "clip_model": "wan2_7", "clip_seconds": {"en": 5, "ko": 4}})
    wj(root / "episodes" / EP / "manifest.json", m)
    for cid in ("c02", "c04"):
        record(root, "--ep", EP, "--cut", cid, "--kind", "image", "--job-id", f"img-{cid}", "--url", "u",
               "--status", "approved")
    p = plan(root, "--ep", EP, "--kind", "clip", "--lang", "en", "--all")
    assert not p["items"] and all("나레이션 승인 전" in b for b in p["blocked"]), p

    def approve_audio(cid: str, block: int, job: str) -> None:
        record(root, "--ep", EP, "--cut", cid, "--kind", "audio", "--lang", "en", "--block", str(block),
               "--job-id", job, "--url", "u", "--status", "approved", "--force")

    approve_audio("c04", 1, "a-c04-1")
    approve_audio("c02", 1, "a-c02-1")
    p = plan(root, "--ep", EP, "--kind", "clip", "--lang", "en", "--all")
    assert [i["key"] for i in p["items"]] == ["c04 clip en"], p  # c02 block 2 not approved yet
    it = p["items"][0]
    assert it["params"]["model"] == "wan2_7" and it["params"]["duration"] == 5, it
    assert {"role": "audio_references", "value": "a-c04-1"} in it["params"]["medias"], it
    assert "--lang en" in it["record"]

    approve_audio("c02", 2, "a-c02-2")
    p = plan(root, "--ep", EP, "--kind", "clip", "--lang", "en", "--all")
    assert any(b.startswith("c02 clip en") and "c02_nar_en.wav" in b for b in p["blocked"]), p
    fails(hf_jobs, "narref", "--root", str(root), "--ep", EP, "--cut", "c04", "--lang", "en", "--media-id", "x",
          needle="블록 2개 이상")
    fails(hf_jobs, "narref", "--root", str(root), "--ep", EP, "--cut", "c03", "--lang", "en", "--media-id", "x",
          needle="lipsync 컷이 아님")
    ok(hf_jobs, "narref", "--root", str(root), "--ep", EP, "--cut", "c02", "--lang", "en", "--media-id", "nar-c02")
    assert cut(root, "c02")["nar_ref"]["en"]["blocks"] == ["a-c02-1", "a-c02-2"]
    ok(validate_manifest, "--root", str(root), "--ep", EP)
    p = plan(root, "--ep", EP, "--kind", "clip", "--lang", "en", "--all")
    c02 = next(i for i in p["items"] if i["cut"] == "c02")
    assert {"role": "audio_references", "value": "nar-c02"} in c02["params"]["medias"], c02

    approve_audio("c02", 2, "a-c02-2b")  # a regenerated block voids the combined narration
    p = plan(root, "--ep", EP, "--kind", "clip", "--lang", "en", "--all")
    assert [i["cut"] for i in p["items"]] == ["c04"], p

    m = manifest(root)
    next(c for c in m["cuts"] if c["id"] == "c02")["nar_ref"]["ko"] = {"media_id": "x"}
    wj(root / "episodes" / EP / "manifest.json", m)
    fails(validate_manifest, "--root", str(root), "--ep", EP, needle="nar_ref.ko")


def test_english_only(tmp: Path) -> None:
    root = make_root(tmp, {"languages": ["en"]})
    set_voices(root)
    p = plan(root, "--ep", EP, "--kind", "audio", "--all")
    assert p["items"] and {i["params"]["voice_id"] for i in p["items"]} == {"v_en"}, p
    assert all(" audio en " in i["key"] for i in p["items"]), [i["key"] for i in p["items"]]
    out = ok(hf_jobs, "status", "--root", str(root), "--ep", EP)
    assert "음성 EN" in out and "음성 KO" not in out, out
    est = okj(estimate_credits, "--root", str(root), "--ep", EP, "--json")
    assert not any("KO" in r["label"] for r in est["rows"]), est["rows"]


def test_status_text_json_and_cli(tmp: Path) -> None:
    root = make_root(tmp)
    record(root, "--ep", EP, "--cut", "c02", "--kind", "image", "--job-id", "i2", "--url", "u", "--status", "approved")
    record(root, "--ep", EP, "--cut", "c03", "--kind", "image", "--job-id", "i3", "--url", "u", "--status",
           "generated")
    record(root, "--ep", EP, "--cut", "c04", "--kind", "image", "--job-id", "i4", "--url", "u", "--status", "rejected")
    out = ok(hf_jobs, "status", "--root", str(root), "--ep", EP, "--library")
    for needle in ("✔", "●", "✖", "—", "L·", "다음 작업", "검토 대기 1개", "c03 image", "클립 생성 가능 1개",
                   "config.voices.en 미설정", "캡 250", "라이브러리 (library.json)", "momo ✔"):
        assert needle in out, (needle, out)
    st = okj(hf_jobs, "status", "--root", str(root), "--ep", EP, "--json")["episode"]
    rows = {r["id"]: r for r in st["cuts"]}
    assert rows["c02"]["image"] == "approved" and rows["c03"]["image"] == "generated"
    assert rows["c04"]["image"] == "rejected" and rows["c03"]["clip"] == "n/a"
    assert rows["c01"]["clip"] == "library:pending" and rows["c02"]["audio"]["en"] == ["pending", "pending"]
    assert st["credits"]["spent"] == 6 and st["credits"]["generations"] == 3

    # CLI: --root 는 서브커맨드 앞·뒤·MOMO_ROOT 어디서든
    script = str(MOMO / "hf_jobs.py")
    env = {**os.environ, "MOMO_ROOT": str(root)}
    for cmd in ([script, "status", "--ep", EP], [script, "--root", str(root), "status", "--ep", EP],
                [script, "status", "--root", str(root), "--ep", EP]):
        r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True,
                           env=env if "--root" not in cmd else {**os.environ, "MOMO_ROOT": str(tmp / "nowhere")})
        assert r.returncode == 0 and "c03" in r.stdout, (cmd, r.stdout, r.stderr)
    r = subprocess.run([sys.executable, script, "status", "--ep", "ep99"], capture_output=True, text=True, env=env)
    assert r.returncode == 1 and "[중단]" in r.stderr, r.stderr


def test_library_and_voice_samples(tmp: Path) -> None:
    root = make_root(tmp)
    cfg = load_config(Paths(root))
    p = plan(root, "--library")
    kinds = [(i["kind"], i["name"]) for i in p["items"]]
    assert kinds == [("image", n) for n in ("intro_wave", "outro_bye", "say_with_me", "cheer", "transition")], kinds
    assert all(i["params"]["prompt"].startswith(f"<<<{cfg['higgsfield']['momo_element_id']}>>> Momo")
               for i in p["items"])
    assert "sheet momo" in p["approved"] and any("voice" in b for b in p["blocked"]), p
    assert not any(i["kind"] == "sheet" for i in p["items"])  # 승인된 시트는 재생성 금지
    hint = plan(root, "--library", "--ep", EP, "--kind", "image")["items"][0]["record"]
    assert "--library intro_wave --kind image --ep ep42" in hint, hint

    L = ["--library", "intro_wave"]
    record(root, *L, "--kind", "image", "--job-id", "li1", "--url", "u", "--status", "approved", "--ep", EP)
    assert manifest(root)["credits"]["spent"] == 2  # --ep 면 첫 편 크레딧에 합산
    lib = rj(root / "library/library.json")
    assert lib["clips"]["intro_wave"]["image"]["status"] == "approved"
    clip = plan(root, "--library", "--kind", "clip")
    assert [i["name"] for i in clip["items"]] == ["intro_wave"]
    assert clip["items"][0]["params"]["medias"] == [{"role": "start_image", "value": "li1"}]
    record(root, *L, "--kind", "clip", "--job-id", "lc1", "--url", "u", "--status", "approved")
    assert rj(root / "library/library.json")["clips"]["intro_wave"]["status"] == "approved"
    assert manifest(root)["credits"]["spent"] == 2  # --ep 없이 기록하면 에피소드 크레딧과 별도
    assert "intro_wave" not in json.dumps(plan(root, "--library", "--kind", "image")["items"])
    fails(hf_jobs, "record", "--root", str(root), "--sheet", "momo", "--job-id", "new", "--status", "generated",
          needle="--force")
    fails(hf_jobs, "record", "--root", str(root), "--library", "nope", "--kind", "clip", "--job-id", "x",
          "--status", "generated", needle="라이브러리 클립 이름이 아님")
    fails(hf_jobs, "plan", "--root", str(root), "--library", "--kind", "audio", needle="voice-samples")

    vs = okj(hf_jobs, "voice-samples", "--root", str(root), "--lang", "en", "--voices", "a,b,c")
    assert [i["params"]["voice_id"] for i in vs["items"]] == ["a", "b", "c"]
    assert len({i["params"]["prompt"] for i in vs["items"]}) == 1  # 같은 문장
    assert "--voice-sample b --lang en" in vs["items"][1]["record"]
    assert len(rj(root / "library/library.json")["voice_samples"]) == 3
    record(root, "--voice-sample", "b", "--lang", "en", "--job-id", "vb", "--url", "u", "--status", "approved")
    assert rj(root / "config.json")["voices"]["en"] == "b"
    fails(hf_jobs, "voice-samples", "--root", str(root), "--lang", "en", "--voices", "x", needle="이미 고정")
    fails(hf_jobs, "record", "--root", str(root), "--voice-sample", "c", "--lang", "en", "--job-id", "vc",
          "--status", "approved", needle="바꾸지 말 것")
    p = plan(root, "--library", "--kind", "audio", "--lang", "en")
    assert [i["name"] for i in p["items"]] == ["intro", "outro"]
    assert p["items"][0]["params"]["prompt"] == cfg["fixed_lines"]["en"]["intro"]
    assert p["items"][0]["params"]["voice_id"] == "b"
    record(root, "--library", "intro", "--kind", "audio", "--lang", "en", "--job-id", "la", "--url", "u",
           "--status", "generated")
    assert rj(root / "library/library.json")["audio"]["en"]["intro"]["status"] == "generated"
    lst = okj(hf_jobs, "status", "--root", str(root), "--library", "--json")["library"]
    assert lst["voices"]["en"] == "b" and lst["clips"]["intro_wave"] == {"image": "approved", "clip": "approved"}

    # 이 편에 처음 나오는 조연 → 시트 payload (캐릭터 블록, 모모 블록·Element 없음)
    lib = rj(root / "library/library.json")
    lib["character_sheets"].pop("croc", None)
    wj(root / "library/library.json", lib)
    m = manifest(root)
    m["cuts"][2]["image_prompt"] += " next to [Croc]"
    wj(root / "episodes" / EP / "manifest.json", m)
    items = plan(root, "--library", "--ep", EP, "--kind", "sheet")["items"]
    assert [i["name"] for i in items] == ["croc"], items
    prompt = items[0]["params"]["prompt"]
    assert prompt.startswith("Character turnaround model sheet of " + cfg["character"]["croc"]), prompt
    assert "<<<" not in prompt and cfg["character"]["momo"] not in prompt
    assert "--sheet croc --ep ep42" in items[0]["record"]
    record(root, "--sheet", "croc", "--job-id", "s1", "--url", "u", "--status", "generated", "--ep", EP)
    assert rj(root / "library/library.json")["character_sheets"]["croc"]["status"] == "generated"


def test_estimate_credits(tmp: Path) -> None:
    root = make_root(tmp)
    est = okj(estimate_credits, "--root", str(root), "--ep", EP, "--json")
    rows = {r["label"]: r for r in est["rows"]}
    # 라이브러리: 클립 이미지 5×2 + 클립 5×7.5 + 고정 음성 4×0.2 + 샘플 6×0.2 = 49.5
    # 에피소드: 이미지 3×2 + V 클립 2×7.5 + 음성 (EN 6 + KO 6)×0.2 = 23.4, 재생성 0.2×(10+37.5+6+15) = 13.7
    assert rows["라이브러리 클립 (V)"]["count"] == 5 and rows["음성 샘플 (후보 3개 × 언어)"]["count"] == 6
    assert rows["컷 이미지 (V 2 + S 1)"]["credits"] == 6 and rows["V 클립"]["credits"] == 15
    assert rows["나레이션 블록 EN"]["count"] == 6 and rows["나레이션 블록 KO"]["count"] == 6
    assert abs(est["remaining"] - 72.9) < 1e-6 and abs(est["regen"] - 13.7) < 1e-6, est
    assert abs(est["total"] - 86.6) < 1e-6 and not est["over_cap"] and est["library_incomplete"]
    text = ok(estimate_credits, "--root", str(root), "--ep", EP, "--save")
    assert "| **합계** | **예상 총액** | | | **86.6** |" in text and "캡 250 이내" in text, text
    assert manifest(root)["credits"]["estimate"] == 86.6

    record(root, "--ep", EP, "--cut", "c02", "--kind", "image", "--job-id", "a", "--url", "u", "--status",
           "generated")  # 검토 대기 = 이미 지불 → 남은 분에서 빠지고 spent 로
    est = okj(estimate_credits, "--root", str(root), "--ep", EP, "--json", "--regen-rate", "0")
    assert est["review"] == ["c02 image"] and abs(est["total"] - (72.9 - 2 + 2)) < 1e-6, est

    cfg = rj(root / "config.json")
    cfg["credits"]["episode_cap"] = 50
    wj(root / "config.json", cfg)
    out = fails(estimate_credits, "--root", str(root), "--ep", EP, needle="중단 조건", code=2)
    assert "50을 넘을 것 같음" in out and "즉시 멈추고" in out, out
    code, _ = call(hf_jobs, "plan", "--root", str(root), "--ep", EP, "--kind", "image")
    assert code == 2  # 캡 초과면 plan 도 멈춘다
    assert plan(root, "--ep", EP, "--kind", "image", "--allow-over-cap")["credits"]["stop"]


def test_fetch_file_urls(tmp: Path) -> None:
    root = make_root(tmp)
    remote = tmp / "remote"
    png, jpg = write_png(remote / "c02.png"), write_png(remote / "c02_v2.jpg", (10, 200, 10), fmt="JPEG")
    mp4, wav = write_mp4(remote / "c02.mp4"), write_wav(remote / "a.wav")
    E = ["--ep", EP]
    record(root, *E, "--cut", "c02", "--kind", "image", "--job-id", "i", "--url", png.as_uri(), "--status", "approved")
    record(root, *E, "--cut", "c02", "--kind", "clip", "--job-id", "c", "--url", mp4.as_uri(), "--status", "generated")
    record(root, *E, "--cut", "c02", "--kind", "audio", "--lang", "en", "--block", "1", "--job-id", "a",
           "--url", wav.as_uri(), "--status", "approved")
    record(root, *E, "--cut", "c03", "--kind", "image", "--job-id", "r", "--url", png.as_uri(), "--status", "rejected")
    out = ok(fetch_assets, "--root", str(root), "--ep", EP)
    ep = root / "episodes" / EP
    assert (ep / "images/c02.png").exists() and (ep / "clips/c02.mp4").exists() and (ep / "audio/en/c02_1.wav").exists()
    assert not (ep / "images/c03.png").exists(), "rejected 는 받지 않음"
    assert "받음 3" in out, out
    assert "받음 0" in ok(fetch_assets, "--root", str(root), "--ep", EP)  # 이미 있으면 건너뜀
    assert "받음 3" in ok(fetch_assets, "--root", str(root), "--ep", EP, "--force")

    record(root, *E, "--cut", "c02", "--kind", "image", "--job-id", "i2", "--url", jpg.as_uri(), "--status",
           "approved", "--force")  # 재생성 결과를 승인 → URL 이 바뀌었으니 다시 받고 옛 확장자는 치움
    out = ok(fetch_assets, "--root", str(root), "--ep", EP)
    assert "URL 바뀜" in out and (ep / "images/c02.jpg").exists() and not (ep / "images/c02.png").exists(), out
    assert rj(ep / "images/.sources.json")["c02.jpg"]["url"] == jpg.as_uri()

    record(root, *E, "--cut", "c04", "--kind", "image", "--job-id", "i4", "--url", (remote / "gone.png").as_uri(),
           "--status", "approved")
    out = fails(fetch_assets, "--root", str(root), "--ep", EP, needle="실패 목록")
    assert "| c04 image |" in out and "gone.png" in out, out

    # --library: 클립·고정 음성 + 참고용(시트·시작 이미지). 참고용 실패는 경고만 (exit 0)
    record(root, "--library", "transition", "--kind", "clip", "--job-id", "t", "--url", mp4.as_uri(),
           "--status", "approved")
    record(root, "--library", "transition", "--kind", "image", "--job-id", "ti", "--url", png.as_uri(),
           "--status", "approved")
    record(root, "--library", "outro", "--kind", "audio", "--lang", "ko", "--job-id", "o", "--url", wav.as_uri(),
           "--status", "approved")
    lib_json = rj(root / "library/library.json")
    lib_json["character_sheets"]["ducky"]["url"] = (remote / "gone_sheet.png").as_uri()
    wj(root / "library/library.json", lib_json)
    out = ok(fetch_assets, "--root", str(root), "--library")
    lib = root / "library"
    assert (lib / "clips/transition.mp4").exists() and (lib / "audio/ko/outro.wav").exists()
    assert (lib / "sheets/momo.png").exists() and (lib / "clips/transition.png").exists()
    assert not (lib / "sheets/ducky.png").exists() and "참고용 실패 1" in out and "sheet ducky (참고용)" in out, out
    record(root, "--library", "cheer", "--kind", "clip", "--job-id", "ch", "--url", (remote / "gone.mp4").as_uri(),
           "--status", "approved")
    fails(fetch_assets, "--root", str(root), "--library", needle="| library cheer clip |")
    fails(fetch_assets, "--root", str(root), needle="--ep 또는 --library")


class Handler(BaseHTTPRequestHandler):
    hits: dict[str, int] = {}
    files: dict[str, tuple[bytes, str]] = {}

    def do_GET(self):  # noqa: N802
        Handler.hits[self.path] = Handler.hits.get(self.path, 0) + 1
        if self.path.startswith("/flaky") and Handler.hits[self.path] == 1:
            self.send_error(503, "busy")
            return
        body, ctype = Handler.files.get(self.path.split("?")[0], (None, None))
        if body is None:
            self.send_error(404, "not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # 조용히
        pass


def test_fetch_http_retry_and_ext(tmp: Path) -> None:
    root = make_root(tmp)
    remote = tmp / "remote"
    Handler.hits, Handler.files = {}, {
        "/img/abc": (write_png(remote / "x.png").read_bytes(), "image/png"),
        "/flaky/voice": (write_wav(remote / "v.wav").read_bytes(), "application/octet-stream"),
        "/bad.png": (b"<html>oops</html>", "text/html"),
    }
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    old = fetch_assets.BACKOFF
    fetch_assets.BACKOFF = 0
    try:
        E = ["--ep", EP]
        record(root, *E, "--cut", "c02", "--kind", "image", "--job-id", "1", "--url", f"{base}/img/abc?sig=1",
               "--status", "approved")
        record(root, *E, "--cut", "c02", "--kind", "audio", "--lang", "en", "--block", "1", "--job-id", "2",
               "--url", f"{base}/flaky/voice", "--status", "generated")
        record(root, *E, "--cut", "c03", "--kind", "image", "--job-id", "3", "--url", f"{base}/bad.png",
               "--status", "approved")
        record(root, *E, "--cut", "c04", "--kind", "image", "--job-id", "4", "--url", f"{base}/missing.png",
               "--status", "approved")
        out = fails(fetch_assets, "--root", str(root), "--ep", EP, needle="실패 목록")
    finally:
        fetch_assets.BACKOFF = old
        srv.shutdown()
        srv.server_close()
    ep = root / "episodes" / EP
    assert (ep / "images/c02.png").exists(), out            # 확장자 없는 URL → Content-Type
    assert (ep / "audio/en/c02_1.wav").exists(), out        # octet-stream → 매직 바이트
    assert Handler.hits["/flaky/voice"] == 2, Handler.hits  # 503 뒤 재시도
    assert Handler.hits["/missing.png"] == 1, Handler.hits  # 404 는 재시도 안 함
    assert Handler.hits["/bad.png"] == 3, Handler.hits      # 검증 실패는 3회까지
    assert "| c03 image |" in out and "이미지가 아님" in out and "| c04 image |" in out and "HTTP 404" in out, out
    assert not list((ep / "images").glob("c03.*")) and not list((ep / "images").glob(".dl_*")), "실패 흔적 남음"


# ---------------------------------------------------------------- hf_api (Higgsfield API) — offline, nothing billed

API_BASE = "https://api.higgsfield.ai"


class FakeApi:
    """api.higgsfield.ai + its upload storage on an httpx.MockTransport.

    terminal: status JSON after `running` in_progress polls (a callable(rid, path) may pick it per request);
    submit: HTTP codes of successive generation POSTs (the last repeats); request_id = uuid5(Idempotency-Key), so a
    resend with the same key gets the same id like the real API. on_poll(rid, n) runs before each status answer."""

    def __init__(self, terminal=None, submit=(200,), running: int = 1, usd: str = "0.250", credits: str = "4.000",
                 on_poll=None, status_code: int = 200):
        self.terminal, self.submit, self.running, self.on_poll = terminal, submit, running, on_poll
        self.usd, self.credits, self.status_code = usd, credits, status_code
        self.posts: list[dict] = []
        self.estimates: list[tuple[str, dict]] = []
        self.uploads: list[str] = []
        self.polls: dict[str, int] = {}
        self.models: dict[str, str] = {}
        self.lock = threading.Lock()

    def __call__(self, req):
        with self.lock:
            return self.handle(req)

    def handle(self, req):
        import httpx
        path = req.url.path
        if req.url.host == "upload.example":
            assert "authorization" not in req.headers, "API 키가 저장소 PUT 에 실림"
            return httpx.Response(200)
        body = json.loads(req.content) if req.content else None
        if path == "/files/generate-upload-url":
            n = len(self.uploads)
            self.uploads.append(body["content_type"])
            return httpx.Response(200, json={"public_url": f"https://cdn.example/in/{n}",
                                             "upload_url": f"https://upload.example/{n}",
                                             "content_type": body["content_type"],
                                             "upload_headers": {"Content-Type": body["content_type"],
                                                                "x-amz-tagging": "retention=temporary"}})
        if path.startswith("/estimate/"):
            self.estimates.append((path[len("/estimate/"):], body))
            return httpx.Response(200, json={"credits": self.credits, "usd": self.usd})
        if req.method == "GET" and path.startswith("/requests/"):
            rid = path.split("/")[2]
            if self.status_code != 200:
                return httpx.Response(self.status_code, json={"detail": f"mock {self.status_code}"})
            n = self.polls[rid] = self.polls.get(rid, 0) + 1
            if self.on_poll:
                self.on_poll(rid, n)
            if n <= self.running:
                return httpx.Response(200, json={"status": "in_progress", "request_id": rid})
            t = self.terminal(rid, self.models.get(rid)) if callable(self.terminal) else self.terminal
            return httpx.Response(200, json={"request_id": rid, **t})
        if req.method == "POST":
            code = self.submit[min(len(self.posts), len(self.submit) - 1)]
            key = req.headers.get("idempotency-key")
            self.posts.append({"model": path[1:], "key": key, "body": body})
            if code != 200:
                detail = "not_enough_credits" if code == 403 else f"mock {code}"
                return httpx.Response(code, json={"detail": detail}, headers={"x-correlation-id": "corr-err"})
            rid = str(uuid.uuid5(uuid.NAMESPACE_OID, key))
            self.models[rid] = path[1:]
            return httpx.Response(200, json={"status": "queued", "request_id": rid,
                                             "status_url": f"{API_BASE}/requests/{rid}/status",
                                             "cancel_url": f"{API_BASE}/requests/{rid}/cancel"},
                                  headers={"x-correlation-id": "corr-1"})
        return httpx.Response(404, json={"detail": f"unexpected {req.method} {req.url}"})


@contextlib.contextmanager
def fake_api(fake: FakeApi):
    """hf_api.make_api → our HTTP client + the real SDK upload_file, both on the MockTransport (no key, no network)."""
    import httpx
    import higgsfield_client
    import hf_api
    sdk = higgsfield_client.SyncClient(api_key="test-key")
    sdk.__dict__["_client"] = httpx.Client(transport=httpx.MockTransport(fake), base_url=API_BASE,
                                           headers={"Authorization": "Key test-key"})
    sdk.__dict__["_upload_client"] = httpx.Client(transport=httpx.MockTransport(fake))
    http = httpx.Client(transport=httpx.MockTransport(fake), base_url=API_BASE)
    saved = hf_api.make_api
    hf_api.make_api = lambda timeout=90.0: hf_api.HfApi(http, sdk.upload_file, sleep=lambda s: None)
    try:
        yield
    finally:
        hf_api.make_api = saved


@contextlib.contextmanager
def served(files: dict[str, Path]):
    """Result videos over local http (API outputs are https URLs; fetch_assets downloads them)."""
    Handler.hits, Handler.files = {}, {k: (p.read_bytes(), "video/mp4") for k, p in files.items()}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()


def api_root(tmp: Path) -> Path:
    """English ep42: c02 seedance_2_0_mini 3 s (API minimum 4 s), c04 wan2_7 lip-sync on its one narration block.
    Images approved (and on disk), c04's voice approved (an mp3 URL, a WAV on disk)."""
    root = make_root(tmp, {"languages": ["en"]})
    m = manifest(root)
    for c in m["cuts"]:
        if c["id"] == "c02":
            c.update(clip_model="seedance_2_0_mini", clip_seconds=3)
        if c["id"] == "c04":
            c.update(lipsync=True, clip_model="wan2_7", clip_seconds={"en": 4})
    wj(root / "episodes" / EP / "manifest.json", m)
    for cid in ("c02", "c04"):
        record(root, "--ep", EP, "--cut", cid, "--kind", "image", "--job-id", f"img-{cid}", "--url",
               f"https://cdn.example/{cid}.png", "--status", "approved")
        write_png(root / "episodes" / EP / "images" / f"{cid}.png")
    record(root, "--ep", EP, "--cut", "c04", "--kind", "audio", "--lang", "en", "--block", "1", "--job-id", "a-c04",
           "--url", "https://cdn.example/c04_1.mp3", "--status", "approved")
    write_wav(root / "episodes" / EP / "audio" / "en" / "c04_1.wav", 1.5)
    return root


def clip_rec(root: Path, cid: str, key: str = "clip") -> dict:
    return cut(root, cid)["gen"].get(key) or {}


def test_hf_api_payloads(tmp: Path) -> None:
    import hf_api
    model, body, notes = hf_api.api_payload("wan2_7", prompt="p", duration=3, resolution="720p", image="I",
                                            end_image="E", audio="A")
    assert model == "wan/v2.7/image-to-video" and not notes, notes
    assert body == {"prompt": "p", "duration": 3, "resolution": "720p", "image_url": "I", "end_image_url": "E",
                    "audio_url": "A"}, body
    model, body, notes = hf_api.api_payload("seedance_2_0_mini", prompt="p", duration=3, resolution="720p", image="I")
    assert model == "bytedance/seedance-2.0/image-to-video", model
    assert body == {"prompt": "p", "duration": 4, "resolution": "720p", "image_url": "I", "generate_audio": False}
    assert any("4초" in n for n in notes) and any("mini" in n for n in notes), notes
    model, body, _ = hf_api.api_payload("seedance_2_5", prompt="p", duration=5, resolution=None, image="I")
    assert model == "bytedance/seedance-2.5/image-to-video" and "aspect_ratio" not in body, body
    model, body, _ = hf_api.api_payload("seedance_2_5", prompt="p", duration=5, resolution="720p", image="I", audio="A")
    assert model == "bytedance/seedance-2.5/reference-to-video", model
    assert body["image_urls"] == ["I"] and body["audio_urls"] == ["A"] and body["aspect_ratio"] == "16:9", body
    for kw in ({"mcp_model": "kling3_0_turbo"}, {"mcp_model": "seedance_2_0", "audio": "A"},
               {"mcp_model": "seedance_2_5", "audio": "A", "end_image": "E"}, {"mcp_model": "wan2_7", "duration": 20},
               {"mcp_model": "wan2_7", "resolution": "480p"}):
        args = {"prompt": "p", "duration": 5, "resolution": "720p", "image": "I", **kw}
        try:
            hf_api.api_payload(args.pop("mcp_model"), **args)
            raise AssertionError(f"Unsupported 이어야 함: {kw}")
        except hf_api.Unsupported:
            pass
    k = hf_api.idem_key("ep05", "c02", "clip", "en", 1, "wan/v2.7/image-to-video", "img")
    assert k == hf_api.idem_key("ep05", "c02", "clip", "en", 1, "wan/v2.7/image-to-video", "img")  # stable
    others = {hf_api.idem_key("ep05", "c02", "clip", "en", 2, "wan/v2.7/image-to-video", "img"),
              hf_api.idem_key("ep05", "c03", "clip", "en", 1, "wan/v2.7/image-to-video", "img"),
              hf_api.idem_key("ep05", "c02", "clip", None, 1, "wan/v2.7/image-to-video", "img"),
              hf_api.idem_key("ep05", "c02", "clip", "en", 1, "wan/v2.7/image-to-video", "img2")}
    assert k not in others and len(others) == 4 and str(uuid.UUID(k)) == k
    assert hf_api.fill({"a": "<image>", "b": ["<audio>", "x"], "d": 4}, {"<image>": "U1", "<audio>": "U2"}) == \
        {"a": "U1", "b": ["U2", "x"], "d": 4}
    e = hf_api.ApiError
    assert e(403, "not_enough_credits").no_credits and not e(403, "x").ambiguous
    assert e(None, "net").ambiguous and e(503, "x").ambiguous and e(429, "x").ambiguous and not e(422, "x").ambiguous
    assert e(400, "Maximum number of concurrent requests (4) has been reached").busy and not e(400, "bad").busy
    assert hf_api.output_url({"status": "completed", "video": {"url": "https://x/v.mp4"}}) == "https://x/v.mp4"


def test_hf_api_wait_backoff_and_errors(tmp: Path) -> None:
    import httpx
    import hf_api
    t = [0.0]
    sleeps: list[float] = []

    def sleep(s: float) -> None:
        sleeps.append(s)
        t[0] += s
    fake = FakeApi(terminal={"status": "completed"}, running=10 ** 6)
    api = hf_api.HfApi(httpx.Client(transport=httpx.MockTransport(fake), base_url=API_BASE), str,
                       sleep=sleep, clock=lambda: t[0])
    try:
        api.wait("r1", deadline=60)
        raise AssertionError("시간 초과여야 함")
    except hf_api.PollTimeout as e:
        assert "60초" in str(e)
    assert 2.0 <= sleeps[0] <= 2.5 and max(sleeps) <= 10.5 and sleeps[3] > sleeps[0], sleeps  # 2 s → 10 s
    assert t[0] <= 60 + 10.5, t

    calls = {"n": 0}

    def flaky(req):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("network down", request=req)
        if calls["n"] == 2:
            return httpx.Response(502, json={"detail": "bad gateway"})
        return httpx.Response(200, json={"status": "Cancelled", "request_id": "r2"})
    api = hf_api.HfApi(httpx.Client(transport=httpx.MockTransport(flaky), base_url=API_BASE), str,
                       sleep=lambda s: None)
    assert api.wait("r2")["status"] == "canceled" and calls["n"] == 3  # network error and 5xx: keep polling
    api = hf_api.HfApi(httpx.Client(transport=httpx.MockTransport(FakeApi(status_code=404)), base_url=API_BASE),
                       str, sleep=lambda s: None)
    try:
        api.wait("r3")
        raise AssertionError("404 는 바로 실패해야 함")
    except hf_api.ApiError as e:
        assert e.code == 404


def test_hf_api_run_completed(tmp: Path) -> None:
    import hf_api
    root = api_root(tmp)
    spent0 = manifest(root)["credits"]["spent"]
    seen = []

    def on_poll(rid: str, n: int) -> None:  # the request id is on disk before the first status poll
        if n == 1:
            m = rj(root / "episodes" / EP / "manifest.json")
            recs = [g for c in m["cuts"] for g in (c.get("gen") or {}).values() if g.get("job_id") == f"api:{rid}"]
            assert len(recs) == 1 and recs[0]["status"] == "generated" and not recs[0]["url"], recs
            assert "api_pending" not in recs[0] and m["credits"]["spent"] == spent0, recs
            seen.append(rid)
    with served({"/out/v.mp4": write_mp4(tmp / "remote/v.mp4")}) as base:
        fake = FakeApi(terminal={"status": "completed", "video": {"url": f"{base}/out/v.mp4"}}, on_poll=on_poll)
        with fake_api(fake):
            code, out = call(hf_api, "run", "--root", str(root), "--ep", EP, "--kind", "clip", "--max-parallel", "2")
    assert code == 0, out
    assert len(seen) == 2 and len(fake.posts) == 2, (seen, fake.posts)
    assert sorted(fake.uploads) == ["audio/x-wav", "image/png", "image/png"] or \
        sorted(fake.uploads) == ["audio/wav", "image/png", "image/png"], fake.uploads
    by = {p["model"]: p for p in fake.posts}
    sd = by["bytedance/seedance-2.0/image-to-video"]
    assert sd["body"]["duration"] == 4 and sd["body"]["generate_audio"] is False, sd
    assert sd["body"]["image_url"].startswith("https://cdn.example/in/"), sd   # uploaded, not the manifest URL
    assert sd["key"] == hf_api.idem_key(EP, "c02", "clip", None, 1, sd["model"], "img-c02"), sd
    wan = by["wan/v2.7/image-to-video"]
    assert wan["body"]["audio_url"].startswith("https://cdn.example/in/") and wan["body"]["duration"] == 4, wan
    assert wan["key"] == hf_api.idem_key(EP, "c04", "clip", "en", 1, wan["model"], "img-c04"), wan
    assert sorted((m, json.dumps(b, sort_keys=True)) for m, b in fake.estimates) == \
        sorted((p["model"], json.dumps(p["body"], sort_keys=True)) for p in fake.posts)  # estimate = same body
    m = manifest(root)
    rec = clip_rec(root, "c02")
    assert rec["status"] == "generated" and rec["job_id"].startswith("api:") and rec["url"] == f"{base}/out/v.mp4"
    api = rec["history"][-1]["api"]
    assert api["usd"] == 0.25 and api["credits"] == 4.0 and api["charged"] and api["correlation_id"] == "corr-1", api
    assert rec["history"][-1]["start_image"] == "img-c02" and rec["credits"] == 0, rec
    assert m["credits"]["spent"] == spent0 and m["credits"]["api_usd"] == 0.5 and m["credits"]["api_generations"] == 2
    ep = root / "episodes" / EP
    assert (ep / "clips/c02.mp4").exists() and (ep / "clips/c04_en.mp4").exists(), list((ep / "clips").iterdir())
    assert rj(ep / "clips/.sources.json")["c02.mp4"]["job_id"] == rec["job_id"]
    assert "API 사용: 이번 실행 $0.50" in out and f"구독 크레딧: 사용 {spent0:g} / 캡 250" in out, out
    assert "API: $0.50 (생성 2회" in ok(hf_jobs, "status", "--root", str(root), "--ep", EP)
    assert "| Higgsfield API | $0.50 (생성 2회" in ok(episode_readme, "--root", str(root), "--ep", EP, "--stdout")
    with fake_api(FakeApi()):
        out = ok(hf_api, "run", "--root", str(root), "--ep", EP)
    assert "API 로 보낼 항목 없음" in out, out   # generated with a URL = awaiting review, nothing resent


def test_hf_api_failed_nsfw_unknown(tmp: Path) -> None:
    import hf_api
    root = api_root(tmp)
    fake = FakeApi(terminal=lambda rid, model: {"status": "failed", "error": "Generation failed"} if "seedance" in model
                   else {"status": "nsfw"})
    with fake_api(fake):
        code, out = call(hf_api, "run", "--root", str(root), "--ep", EP)
    assert code == 1 and "성공 아님" in out and "생성 실패" in out and "검열" in out, out
    c02, c04 = clip_rec(root, "c02"), clip_rec(root, "c04", "clip_en")
    assert c02["status"] == "rejected" and c02["reason"] == "API failed: Generation failed", c02
    assert c04["status"] == "rejected" and c04["reason"].startswith("API nsfw"), c04
    assert c02["history"][-1]["api"]["charged"] is False and not manifest(root)["credits"].get("api_usd"), c02
    assert not list((root / "episodes" / EP / "clips").glob("c0*")), "실패인데 파일이 생김"
    dry = okj(hf_api, "run", "--root", str(root), "--ep", EP, "--cuts", "c02", "--dry-run")
    it = dry["items"][0]
    assert it["attempt"] == 2 and it["idempotency_key"] not in {p["key"] for p in fake.posts}, dry  # new attempt, new key

    root2 = api_root(tmp / "b")
    fake = FakeApi(terminal={"status": "exploded", "video": {"url": "https://cdn.example/o.mp4"}})
    with fake_api(fake):
        code, out = call(hf_api, "run", "--root", str(root2), "--ep", EP, "--cuts", "c02")
    assert code == 1 and "알 수 없는 상태" in out and "성공으로 치지 않음" in out, out
    rec = clip_rec(root2, "c02")
    assert rec["status"] == "generated" and rec["job_id"].startswith("api:") and not rec["url"], rec
    with served({"/out/v.mp4": write_mp4(tmp / "remote/v.mp4")}) as base:
        fake2 = FakeApi(terminal={"status": "completed", "video": {"url": f"{base}/out/v.mp4"}})
        with fake_api(fake2):
            code, out = call(hf_api, "run", "--root", str(root2), "--ep", EP, "--cuts", "c02")
    assert code == 0 and not fake2.posts and not fake2.estimates, (out, fake2.posts)  # resumed: poll only
    assert clip_rec(root2, "c02")["url"] == f"{base}/out/v.mp4" and "이어서 확인" in out, out
    assert manifest(root2)["credits"]["api_usd"] == 0.25  # charge taken from the estimate stored at submit


def test_hf_api_403_falls_back_to_mcp(tmp: Path) -> None:
    import hf_api
    root = api_root(tmp)
    fake = FakeApi(submit=(403,))
    with fake_api(fake):
        code, out = call(hf_api, "run", "--root", str(root), "--ep", EP, "--max-parallel", "1")
    assert code == 3, out
    assert len(fake.posts) == 1, fake.posts   # no retry, nothing else submitted
    assert "not_enough_credits" in out and "API 잔액 부족" in out and "구독 플랜(MCP)" in out, out
    plan_json, _ = json.JSONDecoder().raw_decode(out[out.index("\n{", out.index("구독 플랜(MCP)")) + 1:])
    assert sorted(i["cut"] for i in plan_json["items"]) == ["c02", "c04"], plan_json
    assert all(i["tool"] == "generate_video" and "--job-id <JOB_ID>" in i["record"] for i in plan_json["items"])
    for cid, key in (("c02", "clip"), ("c04", "clip_en")):
        rec = clip_rec(root, cid, key)
        assert rec.get("status", "pending") == "pending" and "api_pending" not in rec, rec
    assert not manifest(root)["credits"].get("api_generations")


def test_hf_api_resend_after_lost_answer(tmp: Path) -> None:
    import hf_api
    root = api_root(tmp)
    fake = FakeApi(submit=(503,))
    with fake_api(fake):
        code, out = call(hf_api, "run", "--root", str(root), "--ep", EP, "--cuts", "c02")
    assert code == 1 and "접수 여부 불명" in out, out
    assert len(fake.posts) == hf_api.SUBMIT_TRIES and len({json.dumps(p["body"]) for p in fake.posts}) == 1
    assert len({p["key"] for p in fake.posts}) == 1, fake.posts  # SDK-style retries reuse the key + body
    pend = clip_rec(root, "c02")["api_pending"]
    assert pend["key"] == fake.posts[0]["key"] and pend["body"] == fake.posts[0]["body"] and pend["attempt"] == 1
    ok(validate_manifest, "--root", str(root), "--ep", EP)   # the pending intent is a valid GenRec extra
    with served({"/out/v.mp4": write_mp4(tmp / "remote/v.mp4")}) as base:
        fake2 = FakeApi(terminal={"status": "completed", "video": {"url": f"{base}/out/v.mp4"}})
        with fake_api(fake2):
            code, out = call(hf_api, "run", "--root", str(root), "--ep", EP, "--cuts", "c02")
    assert code == 0, out
    assert fake2.posts == [{"model": pend["model"], "key": pend["key"], "body": pend["body"]}], fake2.posts
    assert not fake2.uploads and "같은 키·body" in out, out   # the stored body is resent as is (no new upload)
    rec = clip_rec(root, "c02")
    assert "api_pending" not in rec and rec["attempts"] == 1 and rec["url"], rec


def test_hf_api_dry_run_and_kinds(tmp: Path) -> None:
    import hf_api
    root = api_root(tmp)
    m = manifest(root)
    m["cuts"][1]["clip_model"] = "kling3_0_turbo"   # c02 → no API mapping
    wj(root / "episodes" / EP / "manifest.json", m)

    def boom(*a, **k):
        raise AssertionError("dry-run 이 API 클라이언트를 만듦")
    saved, hf_api.make_api = hf_api.make_api, boom
    try:
        d = okj(hf_api, "run", "--root", str(root), "--ep", EP, "--dry-run")
    finally:
        hf_api.make_api = saved
    assert [i["key"] for i in d["items"]] == ["c04 clip en"], d
    it = d["items"][0]
    assert it["api_model"] == "wan/v2.7/image-to-video" and it["payload"]["image_url"] == "<image>", it
    assert it["payload"]["audio_url"] == "<audio>" and it["inputs"]["<audio>"]["as_wav"] is False, it
    assert it["inputs"]["<image>"]["upload"] == f"episodes/{EP}/images/c04.png", it
    assert it["inputs"]["<image>"]["fallback_url"] == "https://cdn.example/c04.png", it
    assert it["estimate"] == f"POST {API_BASE}/estimate/wan/v2.7/image-to-video", it
    assert it["idempotency_key"] == hf_api.idem_key(EP, "c04", "clip", "en", 1, it["api_model"], "img-c04")
    assert d["mcp"] and d["mcp"][0]["key"] == "c02 clip" and "API 매핑 없음" in d["mcp"][0]["reason"], d
    assert "api_pending" not in clip_rec(root, "c04", "clip_en"), "dry-run 이 manifest 를 바꿈"
    (root / "episodes" / EP / "audio/en/c04_1.wav").unlink()
    write_wav(root / "episodes" / EP / "audio/en/c04_1.mp3")  # not a WAV → converted before the upload
    d = okj(hf_api, "run", "--root", str(root), "--ep", EP, "--dry-run")
    assert d["items"][0]["inputs"]["<audio>"]["as_wav"] is True, d
    fails(hf_api, "run", "--root", str(root), "--ep", EP, "--kind", "image", needle="클립만")
    fails(hf_api, "run", "--root", str(root), "--ep", EP, "--max-parallel", "21", needle="1~20")


def test_hf_api_check_codes(tmp: Path) -> None:
    import hf_api
    root = make_root(tmp, assets=False)
    for code, want, needle in ((404, 0, "키 정상"), (401, 1, "거부됨"), (403, 3, "잔액 부족")):
        with fake_api(FakeApi(status_code=code)):
            got, out = call(hf_api, "check", "--root", str(root))
        assert got == want and needle in out, (code, got, out)
    assert "HTTP 403" in out and "거부됨" not in out and "키는 정상" in out, out  # 403 = no credits, not a bad key


def test_hf_api_track_song_refs(tmp: Path) -> None:
    import hf_api
    import song_track
    from momolib import release
    root = make_root(tmp, {"languages": ["en"]})
    m = manifest(root)
    m["song"] = {"bpm": 120.0, "beats_per_bar": 4,
                 "track": {"status": "approved", "sha1": "abc123", "duration": 14.0, "start": 0.0, "end": 13.0,
                           "analysis": {"bpm": 120.0, "downbeat0": 0.5, "confidence": 9.0}, "job_id": "local:abc"},
                 "vocals": {"status": "approved", "sha1": "def456", "job_id": "local:def"}}
    base = {"image_prompt": "[Momo] in a kitchen", "motion": "sings to the viewer"}
    m["cuts"] = [{"id": "c01", "scene": 1, "type": "V", "bars": 2, "clip_model": "seedance_2_0_mini", **base},
                 {"id": "c02", "scene": 2, "type": "V", "bars": 1, "lipsync": True, "clip_model": "wan2_7",
                  "clip_seconds": {"en": 3}, **base},
                 {"id": "c03", "scene": 2, "type": "V", "bars": 2, "clip_model": "seedance_2_0_mini", **base}]
    wj(root / "episodes" / EP / "manifest.json", m)  # c02 = bar 2 → [4.5, 6.5] s of the song
    record(root, "--ep", EP, "--cut", "c02", "--kind", "image", "--job-id", "img-c02", "--url",
           "https://cdn.example/c02.png", "--status", "approved")
    write_png(root / "episodes" / EP / "images/c02.png")
    mcp = plan(root, "--ep", EP, "--kind", "clip", "--all")
    assert not mcp["items"] and any("노래 보컬" in b for b in mcp["blocked"]), mcp  # MCP needs a media id
    refs = root / "episodes" / EP / "audio/refs"
    write_wav(refs / "c02_en.wav", 2.0)   # 2 s: the window, but refs pad to 3 s → stale
    d = okj(hf_api, "run", "--root", str(root), "--ep", EP, "--dry-run")
    assert not d["items"] and any("c02_en.wav 길이 2.00s" in b for b in d["blocked"]), d
    write_wav(refs / "c02_en.wav", 3.0)
    d = okj(hf_api, "run", "--root", str(root), "--ep", EP, "--dry-run")
    it = d["items"][0]
    assert it["key"] == "c02 clip en" and it["inputs"]["<audio>"]["upload"] == f"episodes/{EP}/audio/refs/c02_en.wav"
    assert it["inputs"]["<audio>"]["fallback_url"] is None and it["payload"]["duration"] == 3, it

    # song_track publish goes through momolib.release (shared with hf_api archive)
    d_audio = root / "episodes" / EP / "audio"
    for n in ("song.flac", "song_vocals.flac"):
        (d_audio / n).write_bytes(b"fLaC" + n.encode())
    got = {}
    saved = release.need_gh, release.ensure_release, release.upload_assets
    release.need_gh = lambda: None
    release.ensure_release = lambda tag, title, notes: got.setdefault("tag", tag)
    release.upload_assets = lambda tag, files: {n: f"https://github.com/o/r/releases/download/{tag}/{n}" for n in files}
    try:
        ok(song_track, "--root", str(root), "publish", "--ep", EP)
    finally:
        release.need_gh, release.ensure_release, release.upload_assets = saved
    s = manifest(root)["song"]
    sha = song_track.sha1_file(refs / "c02_en.wav")[:8]
    assert got["tag"] == f"media-{EP}" and s["refs_urls"]["c02_en"].endswith(f"/{EP}_ref_c02_en_{sha}.wav"), s
    d = okj(hf_api, "run", "--root", str(root), "--ep", EP, "--dry-run")
    assert d["items"][0]["inputs"]["<audio>"]["fallback_url"] == s["refs_urls"]["c02_en"], d  # same slice → fallback


def test_hf_api_archive(tmp: Path) -> None:
    import hf_api
    from momolib import release
    root = api_root(tmp)
    ep = root / "episodes" / EP
    up: dict[str, bytes] = {}
    saved = release.need_gh, release.ensure_release, release.upload_assets
    release.need_gh = lambda: None
    release.ensure_release = lambda tag, title, notes: None

    def upload(tag, files):
        up.update({n: Path(f).read_bytes() for n, f in files.items()})
        return {n: f"https://github.com/o/r/releases/download/{tag}/{n}" for n in files}
    release.upload_assets = upload
    try:
        with served({"/out/v.mp4": write_mp4(tmp / "remote/v.mp4")}) as base:
            with fake_api(FakeApi(terminal={"status": "completed", "video": {"url": f"{base}/out/v.mp4"}})):
                ok(hf_api, "run", "--root", str(root), "--ep", EP)
            (ep / "clips/c04_en.mp4").unlink()   # not here any more → archive gets it while the API URL works
            out = ok(hf_api, "archive", "--root", str(root), "--ep", EP, "--dry-run")
            assert "(먼저 받음)" in out and not up, out
            out = ok(hf_api, "archive", "--root", str(root), "--ep", EP)
        assert sorted(n.split("_")[1] for n in up) == ["c02", "c04"], up
        rec = clip_rec(root, "c02")
        assert release.is_release_url(rec["url"]) and f"/media-{EP}/{EP}_c02_" in rec["url"], rec
        assert rec["history"][-1]["url"] == rec["url"] and rec["history"][-1]["api"]["output_url"].endswith("/v.mp4")
        assert rj(ep / "clips/.sources.json")["c02.mp4"]["url"] == rec["url"]
        out = ok(fetch_assets, "--root", str(root), "--ep", EP)   # files match the new URLs → nothing to fetch
        assert "받음 0" in out, out
        out = ok(hf_api, "archive", "--root", str(root), "--ep", EP)
        assert "이미 보관됨" in out and "보관할 API 결과 없음" in out, out
    finally:
        release.need_gh, release.ensure_release, release.upload_assets = saved


def test_doctor(tmp: Path) -> None:
    root = make_root(tmp)
    secrets = {"YOUTUBE_CLIENT_ID": "cid-SENTINEL-1", "YOUTUBE_CLIENT_SECRET": "sec-SENTINEL-2",
               "YOUTUBE_REFRESH_TOKEN_EN": "rt-SENTINEL-3"}
    saved = {k: os.environ.get(k) for k in [*secrets, "YOUTUBE_REFRESH_TOKEN", "YOUTUBE_REFRESH_TOKEN_KO"]}
    os.environ.update(secrets)
    for k in ("YOUTUBE_REFRESH_TOKEN", "YOUTUBE_REFRESH_TOKEN_KO"):
        os.environ.pop(k, None)
    try:
        code, out = call(doctor, "--root", str(root), "--ep", EP, "--ci")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    assert code == 0, out
    assert "SENTINEL" not in out and "YOUTUBE_CLIENT_ID" in out, out
    for needle in ("✔ 폰트", "한글 지원", "✔ BGM: bgm.wav", "ffmpeg", "yt-dlp", "config.voices.en 미설정",
                   "YouTube 자격증명 [en]", "YouTube 자격증명 [ko] 없음", "manifest 검증 통과", "에셋 없는 파일"):
        assert needle in out, (needle, out)

    shutil.rmtree(root / "assets/bgm")
    out = fails(doctor, "--root", str(root), needle="assets/bgm/ 에 BGM 이 없음")
    assert "멈추고 알려줄 것" in out and "✖ 멈춰야 할 항목" in out, out
    for f in (root / "assets/fonts").iterdir():
        f.unlink()
    out = fails(doctor, "--root", str(root), needle="한글을 지원하는 둥근 고딕 폰트")
    m = manifest(root)
    m["cuts"][1]["type"] = "X"
    wj(root / "episodes" / EP / "manifest.json", m)
    write_wav(root / "assets/bgm/bgm.wav")
    out = fails(doctor, "--root", str(root), "--ep", EP, needle="✖ manifest: c02: type")


def test_episode_readme(tmp: Path) -> None:
    root = make_root(tmp)
    record(root, "--ep", EP, "--cut", "c02", "--kind", "image", "--job-id", "i", "--url", "u", "--status", "approved")
    out_dir = root / "episodes" / EP / "out"
    wj(out_dir / f"{EP}_en_timeline.json", {"ep": EP, "lang": "en", "total": 95.5, "fps": 30,
                                            "cuts": [{"id": "c01", "estimated_audio": False}], "warnings": []})
    wj(root / "episodes" / EP / "youtube.json",
       {"en": {"video_id": "VID123", "url": "https://www.youtube.com/watch?v=VID123", "privacy": "private",
               "publish_at": None, "uploaded_at": "2026-09-29T10:00:00Z", "made_for_kids": True,
               "thumbnail_set": True, "playlist_id": None}})
    ok(episode_readme, "--root", str(root), "--ep", EP)
    md = (root / "episodes" / EP / "README.md").read_text(encoding="utf-8")
    for needle in ("# ep42 — 빨강 (Red)", "V 2 · S 1 · L 3", "| 사용 크레딧 | 2 / 캡 250", "| 생성 / 재생성 횟수 | 1 / 0 |",
                   "| 길이 EN | 1:36 (95.5초", "| 길이 KO | 빌드 전", "아동용(made for kids)",
                   "EN: ✔ upload.py 가 selfDeclaredMadeForKids = true", "KO: 아직 업로드 전",
                   "[VID123](https://www.youtube.com/watch?v=VID123)", "- 제목: Learn Red with Momo",
                   "- 태그: red, toddler", "#kids", "- 키워드를 더 크게", "| 컷 이미지 | 1/3 | 1 | 2 |"):
        assert needle in md, (needle, md)
    assert ok(episode_readme, "--root", str(root), "--ep", EP, "--stdout").startswith("# ep42")


def main() -> int:
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        with tempfile.TemporaryDirectory(prefix="momo_tools_test_") as d:
            try:
                fn(Path(d))
                print(f"✔ {name}")
            except Exception:  # noqa: BLE001
                failed.append(name)
                print(f"✖ {name}")
                traceback.print_exc()
    print(f"\ntest_tools: {len(tests) - len(failed)}/{len(tests)} 통과" + (f" — 실패: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
