#!/usr/bin/env python3
"""youtube.com 이 막힌 세션을 위한 벤치마킹 원격 수집 (GitHub Actions 러너에서 yt-dlp 실행).

흐름
  1) 세션:   python remote_research.py keygen          → momo/.secrets/research_key.pem (비공개, git 제외)
                                                       + research/research_pub.pem (공개키, 커밋)
  2) 세션:   research/requests/<이름>.json 커밋·푸시     → .github/workflows/momo-research.yml 실행
  3) 러너:   python remote_research.py fetch --request ... → 목록·메타·자막 텍스트·샷 통계는 브랜치에 커밋,
             프레임/썸네일 시트는 공개키로 암호화해 momo-research-sealed 브랜치에만 올림
             (공개 저장소에 타 채널 프레임 원본을 올리지 않기 위함)
  4) 세션:   git fetch origin momo-research-sealed && python remote_research.py unseal
             → research/<slug>/frames/ (git 제외) 에 복호화 → Claude 가 보고 분석 → sample_videos.py --cleanup 로 삭제
  5) 세션:   python analyze_channel.py --offline-json research/<slug>/raw/channel.json \
               --offline-popular research/<slug>/raw/popular.json --offline-meta research/<slug>/meta

요청 파일 예 (research/requests/bench1.json):
  {"channels": [{"slug": "cocomelon", "url": "https://www.youtube.com/@CoComelon"}],
   "limit": 2000, "top": 5, "recent": 15, "samples": true, "frames": 36}
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import MomoError, add_root_arg, get_paths, main_wrapper, save_json  # noqa: E402

META_KEYS = ("id", "title", "upload_date", "timestamp", "release_timestamp", "view_count", "like_count",
             "comment_count", "duration", "tags", "description", "thumbnail", "categories", "channel",
             "channel_id", "channel_follower_count", "uploader", "availability", "live_status", "language")
FLAT_TOP_KEYS = ("id", "channel", "channel_id", "title", "uploader", "uploader_id", "uploader_url",
                 "channel_url", "channel_follower_count", "playlist_count", "description")
ENTRY_KEYS = ("id", "title", "view_count", "duration", "url", "upload_date", "timestamp", "live_status")
BOT_RE = re.compile(r"(confirm you.re not a bot|HTTP Error 403|HTTP Error 429|Sign in to confirm)", re.I)


class Log:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lines: list[str] = []

    def __call__(self, msg: str) -> None:
        print(msg, flush=True)
        self.lines.append(msg)
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def ytdlp(args: list[str], log: Log, what: str, want_json: bool = False):
    """yt-dlp 실행. 봇 확인/403/429 면 --sleep-requests 1 로 1회 재시도, 그래도 실패하면 원문을 남기고 예외."""
    base = ["yt-dlp", "--no-warnings", "--retries", "3"]
    last = ""
    for attempt, extra in enumerate(([], ["--sleep-requests", "1"])):
        proc = subprocess.run(base + extra + args, capture_output=True, text=True)
        if proc.returncode == 0:
            return json.loads(proc.stdout) if want_json else proc.stdout
        last = proc.stderr.strip()
        log(f"  [{what}] 실패 (시도 {attempt + 1}): " + "\n    ".join(last.splitlines()[-6:]))
        if not BOT_RE.search(last):
            break
    raise MomoError(f"{what} 실패 — yt-dlp 원문:\n{last[-2000:]}")


def trim_flat(d: dict) -> dict:
    out = {k: d.get(k) for k in FLAT_TOP_KEYS if d.get(k) is not None}
    out["entries"] = [{k: e.get(k) for k in ENTRY_KEYS if e.get(k) is not None}
                      for e in (d.get("entries") or []) if e and e.get("id")]
    return out


def json3_to_text(path: Path) -> str:
    """자동 자막 json3 → "[mm:ss.s] 텍스트" (롤링 중복 줄 제거)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    lines, prev = [], ""
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = re.sub(r"\s+", " ", "".join(s.get("utf8", "") for s in segs)).strip()
        if not text or text == prev or (prev and prev.endswith(text)):
            continue
        t = ev.get("tStartMs", 0) / 1000
        lines.append(f"[{int(t // 60):02d}:{t % 60:04.1f}] {text}")
        prev = text
    return "\n".join(lines) + "\n"


def scene_cuts(video: Path, threshold: float = 0.3) -> list[float]:
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
                           f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
                          capture_output=True, text=True)
    return [float(m) for m in re.findall(r"pts_time:([0-9.]+)", proc.stderr)]


def probe_duration(video: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "default=nw=1:nk=1", str(video)], capture_output=True, text=True).stdout
    return float(out.strip() or 0)


def contact_sheet(images: list[Path], labels: list[str], out: Path, cols: int, cell_w: int) -> None:
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for p in images]
    cell_h = int(cell_w * 9 / 16)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + 22)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(zip(ims, labels)):
        im.thumbnail((cell_w, cell_h))
        x, y = (i % cols) * cell_w, (i // cols) * (cell_h + 22)
        sheet.paste(im, (x + (cell_w - im.width) // 2, y))
        draw.text((x + 4, y + cell_h + 4), lab, fill="black")
    sheet.save(out, "JPEG", quality=85)


def seal(src: Path, pubkey: Path, out_dir: Path) -> None:
    """파일마다 무작위 AES 키로 암호화하고, 그 키를 RSA-OAEP 공개키로 감싼다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    key = os.urandom(32).hex()
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-in", str(src),
                    "-out", str(out_dir / (src.name + ".enc")), "-pass", "stdin"],
                   input=key.encode(), check=True)
    subprocess.run(["openssl", "pkeyutl", "-encrypt", "-pubin", "-inkey", str(pubkey),
                    "-pkeyopt", "rsa_padding_mode:oaep", "-out", str(out_dir / (src.name + ".key.enc"))],
                   input=key.encode(), check=True)


def download(url: str, dest: Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=30) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        return dest.stat().st_size > 2000
    except Exception:
        return False


def fetch_channel(ch: dict, req: dict, research: Path, pubkey: Path, sealed: Path, work: Path) -> dict:
    slug = re.sub(r"[^a-z0-9_-]", "", ch["slug"].lower())
    url = ch["url"].rstrip("/")
    base = research / slug
    log = Log(base / "fetch_log.txt")
    log(f"== {slug} ({url}) — {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    log("yt-dlp " + subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True).stdout.strip())
    limit = int(req.get("limit", 2000))
    result = {"slug": slug, "ok": False}

    flat = ytdlp(["--flat-playlist", "-J", "--extractor-args", "youtubetab:approximate_date",
                  "--playlist-end", str(limit), f"{url}/videos"], log, "채널 목록", want_json=True)
    flat_t = trim_flat(flat)
    flat_t["_fetched_at"] = int(time.time())
    flat_t["_limit"] = limit
    save_json(base / "channel_flat.json", flat_t)  # raw/ 는 git 제외라 여기 저장
    entries = flat_t["entries"]
    log(f"(a) 목록 {len(entries)}개, 구독자 {flat_t.get('channel_follower_count')}")
    try:
        pop = ytdlp(["--flat-playlist", "-J", "--playlist-end", "50", f"{url}/videos?view=0&sort=p&flow=grid"],
                    log, "인기순 목록", want_json=True)
        save_json(base / "popular_flat.json", trim_flat(pop))
    except MomoError as e:
        log(f"(b) 인기순 요청 실패 → 조회수 정렬로 대체: {str(e).splitlines()[0]}")

    top_n, recent_n = int(req.get("top", 5)), int(req.get("recent", 15))
    by_views = sorted((e for e in entries if e.get("view_count") is not None), key=lambda e: -e["view_count"])
    recent = entries[:recent_n]
    ids = list(dict.fromkeys([e["id"] for e in recent] + [e["id"] for e in by_views[:top_n]]))
    metas = {}
    if not req.get("meta", True):
        ids = []
    log(f"(d) 개별 메타 {len(ids)}개")
    for vid in ids:
        try:
            m = ytdlp(["--skip-download", "-J", "--sleep-requests", "1", f"https://www.youtube.com/watch?v={vid}"],
                      log, f"메타 {vid}", want_json=True)
            metas[vid] = {k: m.get(k) for k in META_KEYS if m.get(k) is not None}
            save_json(base / "meta" / f"{vid}.json", metas[vid])
        except MomoError as e:
            log(f"    메타 {vid} 건너뜀: {str(e).splitlines()[0]}")
    result["meta"] = len(metas)

    if req.get("samples", True) and by_views:
        top1 = by_views[0]["id"]
        recent_top = max(recent, key=lambda e: e.get("view_count") or 0)["id"] if recent else top1
        samples = {}
        for role, vid in (("all_time_top", top1), ("recent_top", recent_top)):
            if vid in samples:
                samples[vid]["roles"].append(role)
                continue
            samples[vid] = s = {"roles": [role], "title": metas.get(vid, {}).get("title")}
            vdir = work / vid
            vdir.mkdir(parents=True, exist_ok=True)
            try:
                ytdlp(["--skip-download", "--write-auto-subs", "--write-subs", "--sub-lang", "en,ko",
                       "--sub-format", "json3", "-o", str(vdir / "%(id)s"), f"https://www.youtube.com/watch?v={vid}"],
                      log, f"자막 {vid}")
            except MomoError as e:
                log(f"    자막 {vid} 실패: {str(e).splitlines()[0]}")
            s["subs"] = {}
            for f in sorted(vdir.glob("*.json3")):
                lang = f.name.split(".")[-2]
                out = base / "subs" / f"{vid}.{lang}.txt"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json3_to_text(f), encoding="utf-8")
                s["subs"][lang] = str(out.relative_to(research.parent))
            if not s["subs"]:
                log(f"    자막 없음 ({vid}) — 건너뜀 (동요 채널은 흔함)")
            try:
                ytdlp(["-f", "bv*[height<=480]", "-o", str(vdir / "video.%(ext)s"),
                       f"https://www.youtube.com/watch?v={vid}"], log, f"영상 {vid}")
                video = next(p for p in vdir.glob("video.*") if p.suffix != ".part")
            except (MomoError, StopIteration) as e:
                log(f"    영상 {vid} 다운로드 실패 — 프레임/샷 분석 불가: {str(e).splitlines()[0] if str(e) else ''}")
                continue
            dur = probe_duration(video)
            cuts = scene_cuts(video)
            bounds = [0.0] + cuts + [dur]
            shots = [b - a for a, b in zip(bounds, bounds[1:]) if b > a]
            s["shots"] = {"duration": round(dur, 2), "cuts": [round(c, 2) for c in cuts], "count": len(shots),
                          "mean": round(statistics.mean(shots), 2) if shots else None,
                          "median": round(statistics.median(shots), 2) if shots else None,
                          "stdev": round(statistics.pstdev(shots), 2) if len(shots) > 1 else 0.0,
                          "threshold": 0.3}
            n = max(30, min(40, int(req.get("frames", 36))))
            step = dur / n
            fdir = vdir / "frames"
            fdir.mkdir(exist_ok=True)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-vf",
                            f"fps=1/{step:.4f},scale=480:-2", "-frames:v", str(n), str(fdir / "f_%03d.jpg")],
                           check=True)
            frames = sorted(fdir.glob("f_*.jpg"))
            labels = [f"{int((i + .5) * step // 60)}:{(i + .5) * step % 60:04.1f}" for i in range(len(frames))]
            sheet = work / f"{slug}_{vid}_frames.jpg"
            contact_sheet(frames, labels, sheet, cols=6, cell_w=320)
            seal(sheet, pubkey, sealed / slug)
            s["frames"] = {"count": len(frames), "interval": round(step, 2), "sealed": f"{slug}/{sheet.name}.enc"}
            log(f"    {vid}: {dur:.0f}s, 샷 {len(shots)}개, 평균 {s['shots']['mean']}s, 프레임 {len(frames)}장")
        result["samples"] = samples
        save_json(base / "remote_samples.json", samples)

    if req.get("thumbs", True) and by_views:
        # (c) 썸네일: 역대 1·2위 + 최근 1위·최하위 (72시간 미만 제외)
        now = time.time()
        def ts(e):
            return metas.get(e["id"], {}).get("timestamp") or e.get("timestamp")
        old_recent = [e for e in recent if not (ts(e) and now - ts(e) < 72 * 3600)]
        picks = [("역대1", by_views[0]["id"])]
        if len(by_views) > 1:
            picks.append(("역대2", by_views[1]["id"]))
        if old_recent:
            picks.append(("최근1", max(old_recent, key=lambda e: e.get("view_count") or 0)["id"]))
            picks.append(("최근최하", min(old_recent, key=lambda e: e.get("view_count") or 0)["id"]))
        tdir = work / "thumbs"
        tdir.mkdir(exist_ok=True)
        got, labs = [], []
        for lab, vid in picks:
            dest = tdir / f"{vid}.jpg"
            if download(f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg", dest) or \
               download(f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", dest):
                views = next((e.get("view_count") for e in entries if e["id"] == vid), None)
                got.append(dest)
                labs.append(f"{lab} {vid} {views:,}" if views else f"{lab} {vid}")
        if got:
            sheet = work / f"{slug}_thumbs.jpg"
            contact_sheet(got, labs, sheet, cols=2, cell_w=640)
            seal(sheet, pubkey, sealed / slug)
            save_json(base / "remote_thumbs.json", {"picks": picks, "sealed": f"{slug}/{sheet.name}.enc"})
        log(f"(썸네일) {len(got)}장 시트")
    result["ok"] = True
    log("완료")
    return result


def cmd_fetch(args) -> int:
    paths = get_paths(args)
    req_path = Path(args.request)
    req = json.loads(req_path.read_text(encoding="utf-8"))
    pubkey = Path(args.pubkey) if args.pubkey else paths.research / "research_pub.pem"
    if not pubkey.exists():
        raise MomoError(f"공개키 없음: {pubkey} — 세션에서 'python momo/remote_research.py keygen' 후 커밋")
    sealed = Path(args.sealed_dir)
    work = Path(tempfile.mkdtemp(prefix="momo_research_"))
    failures = []
    for ch in req.get("channels", []):
        try:
            r = fetch_channel(ch, req, paths.research, pubkey, sealed, work)
            print(json.dumps(r, ensure_ascii=False)[:500])
        except MomoError as e:
            failures.append(f"{ch.get('slug')}: {e}")
            print(f"[실패] {ch.get('slug')}: {e}", file=sys.stderr)
    shutil.rmtree(work, ignore_errors=True)  # 원본 영상·프레임은 러너에서도 즉시 삭제
    if failures:
        raise MomoError("일부 채널 수집 실패:\n" + "\n".join(failures))
    return 0


def cmd_keygen(args) -> int:
    paths = get_paths(args)
    priv = paths.secrets / "research_key.pem"
    pub = paths.research / "research_pub.pem"
    if priv.exists() and pub.exists() and not args.force:
        print(f"이미 있음: {priv} / {pub} (새로 만들려면 --force)")
        return 0
    paths.secrets.mkdir(parents=True, exist_ok=True)
    pub.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072",
                    "-out", str(priv)], check=True, capture_output=True)
    os.chmod(priv, 0o600)
    subprocess.run(["openssl", "pkey", "-in", str(priv), "-pubout", "-out", str(pub)], check=True)
    print(f"비공개키: {priv} (git 제외 — 이 세션에서만 복호화 가능)\n공개키: {pub} (커밋할 것)")
    return 0


def cmd_unseal(args) -> int:
    paths = get_paths(args)
    priv = paths.secrets / "research_key.pem"
    if not priv.exists():
        raise MomoError(f"비공개키 없음: {priv} — keygen 한 세션에서만 풀 수 있음. 새 세션이면 keygen 후 수집을 다시 요청")
    src = Path(args.sealed)
    n = 0
    for enc in sorted(src.rglob("*.jpg.enc")):
        slug = enc.parent.name
        out_dir = paths.research / slug / "frames"
        out_dir.mkdir(parents=True, exist_ok=True)
        key = subprocess.run(["openssl", "pkeyutl", "-decrypt", "-inkey", str(priv), "-pkeyopt",
                              "rsa_padding_mode:oaep", "-in", str(enc.with_name(enc.name[:-4] + ".key.enc"))],
                             check=True, capture_output=True).stdout
        out = out_dir / enc.name[:-4]
        subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", str(enc), "-out", str(out),
                        "-pass", "stdin"], input=key, check=True)
        print(f"복호화: {out}")
        n += 1
    if not n:
        raise MomoError(f"{src} 에 *.jpg.enc 가 없음 — git fetch origin momo-research-sealed 후 worktree/checkout 경로를 지정")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_root_arg(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen", help="복호화용 키 쌍 생성 (세션에서)")
    k.add_argument("--force", action="store_true")
    f = sub.add_parser("fetch", help="요청 파일대로 수집 (GitHub Actions 러너에서)")
    f.add_argument("--request", required=True)
    f.add_argument("--pubkey")
    f.add_argument("--sealed-dir", required=True, help="암호화된 시트를 둘 폴더 (러너 임시 폴더)")
    u = sub.add_parser("unseal", help="암호화된 프레임·썸네일 시트 복호화 (세션에서)")
    u.add_argument("--sealed", required=True, help="momo-research-sealed 브랜치를 체크아웃한 폴더")
    args = ap.parse_args()
    return {"keygen": cmd_keygen, "fetch": cmd_fetch, "unseal": cmd_unseal}[args.cmd](args)


if __name__ == "__main__":
    main_wrapper(main)
