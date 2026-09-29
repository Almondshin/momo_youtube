#!/usr/bin/env python3
"""생성 결과 미리보기 (GitHub Actions 러너에서 실행 — 세션이 Higgsfield CDN 에 못 닿을 때).

library.json 과 episodes/*/manifest.json 에 기록된 생성 결과 URL 을 받아
작은 미리보기(이미지 ≤1280px JPEG, 영상은 프레임 6장 시트, 음성은 길이만)를 만든다.
.github/workflows/momo-preview.yml 이 결과를 momo-previews 브랜치에 강제 푸시하고,
세션은 `git fetch origin momo-previews` 후 이미지를 직접 본다.

사용 예
  python preview_assets.py --out /tmp/previews            # 전부
  python preview_assets.py --out /tmp/previews --ep ep02  # 라이브러리 + ep02
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import EP_RE, add_root_arg, get_paths, load_json, main_wrapper  # noqa: E402

def iter_records(paths, only_ep: str | None):
    """(이름, kind, GenRec) — kind: image | video | audio."""
    lib = load_json(paths.library_json, default={})
    for name, rec in (lib.get("character_sheets") or {}).items():
        yield f"library/sheet_{name}", "image", rec
    for name, rec in (lib.get("clips") or {}).items():
        yield f"library/clip_{name}_image", "image", rec.get("image") or {}
        yield f"library/clip_{name}", "video", rec
    for lang, recs in (lib.get("audio") or {}).items():
        for name, rec in recs.items():
            yield f"library/audio_{lang}_{name}", "audio", rec
    for i, rec in enumerate(lib.get("voice_samples") or []):
        yield f"library/voice_{rec.get('lang', 'xx')}_{i:02d}_{rec.get('name', '')}", "audio", rec
    for mpath in sorted(paths.episodes.glob("*/manifest.json")):
        ep = mpath.parent.name
        if not EP_RE.match(ep) or (only_ep and ep != only_ep):
            continue
        m = load_json(mpath)
        for c in m.get("cuts", []):
            gen = c.get("gen") or {}
            yield f"{ep}/{c['id']}_image", "image", gen.get("image") or {}
            yield f"{ep}/{c['id']}_clip", "video", gen.get("clip") or {}
            for lang, blocks in (c.get("audio_src") or {}).items():
                for n, rec in blocks.items():
                    yield f"{ep}/{c['id']}_audio_{lang}_{n}", "audio", rec
            # 재생성 비교용: 직전 시도도 같이 (history 마지막 2개)
            for j, h in enumerate((gen.get("image") or {}).get("history", [])[-3:-1]):
                yield f"{ep}/{c['id']}_image_prev{j}", "image", h


def fetch(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "momo-preview"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())


def preview_image(src: Path, out: Path) -> str:
    from PIL import Image
    im = Image.open(src)
    size = im.size
    im = im.convert("RGB")
    im.thumbnail((1280, 1280))
    im.save(out, "JPEG", quality=82)
    return f"{size[0]}x{size[1]}"


def preview_video(src: Path, out: Path) -> str:
    from PIL import Image
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(src)],
                           capture_output=True, text=True, check=True)
    info = json.loads(probe.stdout)
    st = (info.get("streams") or [{}])[0]
    dur = float(info.get("format", {}).get("duration") or 0)
    tmp = Path(tempfile.mkdtemp())
    frames = []
    for i in range(6):
        t = dur * (i + 0.5) / 6
        f = tmp / f"f{i}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
                        "-vf", "scale=426:-2", str(f)], check=True)
        frames.append(Image.open(f).convert("RGB"))
    w, h = frames[0].size
    sheet = Image.new("RGB", (w * 3, h * 2), "white")
    for i, fr in enumerate(frames):
        sheet.paste(fr, ((i % 3) * w, (i // 3) * h))
    sheet.save(out, "JPEG", quality=80)
    return f"{st.get('width')}x{st.get('height')} {st.get('r_frame_rate')} {dur:.2f}s"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_root_arg(ap)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ep")
    args = ap.parse_args()
    paths = get_paths(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp())
    index = []
    for name, kind, rec in iter_records(paths, args.ep):
        url = rec.get("url")
        if not url:
            continue
        dest_dir = out / Path(name).parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        raw = work / (Path(name).name + Path(url.split("?")[0]).suffix)
        try:
            fetch(url, raw)
            if kind == "image":
                meta = preview_image(raw, dest_dir / f"{Path(name).name}.jpg")
            elif kind == "video":
                meta = preview_video(raw, dest_dir / f"{Path(name).name}.jpg")
            else:
                d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                    "default=nw=1:nk=1", str(raw)], capture_output=True, text=True).stdout.strip()
                meta = f"{float(d or 0):.2f}s"
            index.append({"name": name, "kind": kind, "status": rec.get("status"), "job_id": rec.get("job_id"),
                          "meta": meta})
            print(f"✔ {name} ({kind}) {meta}")
        except Exception as e:  # 하나 실패해도 나머지는 계속
            index.append({"name": name, "kind": kind, "error": str(e)[:300]})
            print(f"✖ {name}: {e}", file=sys.stderr)
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    main_wrapper(main)
