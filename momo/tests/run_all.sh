#!/usr/bin/env bash
# momo 전체 테스트 — 합성 픽스처 root 에서 파이프라인 전 단계를 돌리고 결과물을 검증한다 (로컬·CI 공용).
#
# 사용: bash momo/tests/run_all.sh
#   MOMO_TEST_DIR=/path   픽스처 root·로그를 이 폴더에 남김 (CI 아티팩트용). 없으면 임시 폴더 (성공 시 삭제)
#   MOMO_KEEP=1           임시 폴더를 성공해도 남김
#   PYTHON=python3.11     파이썬 지정 (기본 python3)
#
# 순서: 단위 테스트(tests/test_*.py) → 픽스처(ep99, ep98) → validate → estimate → hf_jobs status → doctor(경고만)
#       → fetch_assets(file:// 에서 복원) → build ep99 en/ko --check → build ep98 en → compile en ep98 ep99
#       → upload --dry-run (에피소드·모음집, 자격증명 없이) → episode_readme → ffprobe·loudness 검증.
# 한 단계가 실패해도 (픽스처 제외) 나머지를 계속 돌리고 마지막에 PASS/FAIL 요약, 실패가 있으면 exit 1.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOMO="$(dirname "$HERE")"
PY="${PYTHON:-python3}"

if [ -n "${MOMO_TEST_DIR:-}" ]; then
  WORK="$MOMO_TEST_DIR"; KEEP=1
else
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/momo_test.XXXXXX")"; KEEP="${MOMO_KEEP:-0}"
fi
ROOT="$WORK/root"
LOGS="$WORK/logs"
rm -rf "$LOGS"
mkdir -p "$LOGS"

# 어떤 스크립트가 --root 를 빠뜨려도 저장소 momo/ 를 건드리지 않게 (add_root_arg 기본값)
export MOMO_ROOT="$ROOT"
# dry-run 이 자격증명 없이 도는지 확인하려고 비운다
unset YOUTUBE_CLIENT_ID YOUTUBE_CLIENT_SECRET YOUTUBE_REFRESH_TOKEN YOUTUBE_REFRESH_TOKEN_EN YOUTUBE_REFRESH_TOKEN_KO

N=0; FAILS=0; WARNS=0
RESULTS=()

cleanup() {
  if [ "$KEEP" = 1 ] || [ "$FAILS" -gt 0 ]; then
    echo "작업 폴더 보존: $WORK"
  else
    rm -rf "$WORK"
  fi
}
trap cleanup EXIT

# step <이름> <명령...> — 출력은 로그 파일로, 실패하면 로그 꼬리를 보여준다.
# (|| 안에서 부른 함수는 set -e 가 꺼지므로 단계 함수는 실패를 직접 return 한다)
run_step() {
  local soft="$1" name="$2"; shift 2
  N=$((N + 1))
  local log; log="$LOGS/$(printf '%02d' "$N")_${name//[^A-Za-z0-9_.-]/_}.log"
  local t0=$SECONDS rc=0
  printf '▶ %s%*s ' "$name" $((44 - ${#name})) ''   # 바이트가 아니라 글자 수로 맞춤 (한글)
  "$@" >"$log" 2>&1 || rc=$?
  local dt=$((SECONDS - t0))
  if [ "$rc" -eq 0 ]; then
    printf 'PASS  %4ss\n' "$dt"; RESULTS+=("PASS  $name")
  elif [ "$soft" = 1 ]; then
    printf 'WARN  %4ss (exit %s, 경고만)\n' "$dt" "$rc"; RESULTS+=("WARN  $name  (exit $rc)"); WARNS=$((WARNS + 1))
    tail -n 12 "$log" | sed 's/^/    │ /'
  else
    printf 'FAIL  %4ss (exit %s)\n' "$dt" "$rc"; RESULTS+=("FAIL  $name  (exit $rc) → $log"); FAILS=$((FAILS + 1))
    tail -n 25 "$log" | sed 's/^/    │ /'
  fi
  return 0
}
step() { run_step 0 "$@"; }
soft_step() { run_step 1 "$@"; }

# py <스크립트> <인자...> — 아직 없는 스크립트(다른 작업 진행 중)는 이유를 남기고 실패
py() {
  local script="$MOMO/$1"; shift
  if [ ! -f "$script" ]; then
    echo "스크립트 없음: ${script#"$MOMO"/} — 이 단계는 해당 파일이 있어야 한다"
    return 127
  fi
  "$PY" "$script" "$@"
}

summary() {
  echo
  echo "━━━━━━━━━━━━━━━━ 요약 ━━━━━━━━━━━━━━━━"
  printf '%s\n' "${RESULTS[@]}"
  echo "결과: $((N - FAILS - WARNS)) PASS / $FAILS FAIL / $WARNS WARN   (로그: $LOGS)"
  if [ "$FAILS" -gt 0 ]; then echo "✖ FAIL"; else echo "✔ PASS"; fi
}

# ---------------------------------------------------------------- 단계 함수

validate_step() {
  py validate_manifest.py --root "$ROOT" --ep ep99 --table || return
  test -s "$ROOT/episodes/ep99/plan.md" || { echo "✖ --table 인데 plan.md 가 없음"; return 1; }
}

# ep98 의 이미지·클립·음성과 라이브러리 transition 클립을 지우고 manifest/library 의 file:// URL 로 복원
fetch_step() {
  local ep="$ROOT/episodes/ep98" lib="$ROOT/library/clips/transition.mp4" before after rc=0
  before=$(find "$ep/images" "$ep/clips" "$ep/audio" -type f | wc -l)
  rm -rf "$ep/images" "$ep/clips" "$ep/audio" "$lib"
  py fetch_assets.py --root "$ROOT" --ep ep98 --library || rc=$?
  after=$(find "$ep/images" "$ep/clips" "$ep/audio" -type f 2>/dev/null | wc -l)
  echo "복원: ep98 파일 $after / $before, transition.mp4 $([ -s "$lib" ] && echo 있음 || echo 없음)"
  if [ "$rc" -ne 0 ] || [ "$after" -lt "$before" ] || [ ! -s "$lib" ]; then
    # 뒤 단계(build ep98, compile)가 fetch 실패에 끌려 실패하지 않게 픽스처 원본으로 되돌린다
    cp -r "$ROOT/_remote/ep98/." "$ep/"
    cp "$ROOT/_remote/library/clips/transition.mp4" "$lib"
    echo "✖ fetch_assets 가 파일을 모두 복원하지 못함 (exit $rc) — 픽스처 원본으로 되돌림"
    return 1
  fi
}

upload_dry_step() {
  local out
  out=$(py upload.py --root "$ROOT" --ep ep99 --lang all --dry-run) || { echo "$out"; return 1; }
  echo "$out"
  [ "$(grep -c '"selfDeclaredMadeForKids": true' <<<"$out")" -eq 2 ] || { echo "✖ en/ko 둘 다 아동용 true 여야 함"; return 1; }
  [ ! -e "$ROOT/episodes/ep99/youtube.json" ] || { echo "✖ dry-run 인데 youtube.json 이 생김"; return 1; }
}

upload_compilation_step() {
  local out
  out=$(py upload.py --root "$ROOT" --compilation ep98-ep99 --lang en --title "Momo Test Compilation" \
        --tags "kids,colors" --dry-run) || { echo "$out"; return 1; }
  echo "$out"
  grep -q '0:00 ' <<<"$out" || { echo "✖ 설명에 챕터(0:00 ...)가 붙지 않음"; return 1; }
}

readme_step() {
  py episode_readme.py --root "$ROOT" --ep ep99 || return
  test -s "$ROOT/episodes/ep99/README.md" || { echo "✖ README.md 가 없음"; return 1; }
}

# 완성본 규격: 1920x1080, 30fps, yuv420p, H.264, AAC 48kHz, 길이 = timeline total ±1프레임, -14 LUFS ±1
check_outputs() {
  "$PY" - "$ROOT" <<'PYEOF'
import json, re, subprocess, sys
from pathlib import Path

from PIL import Image

root = Path(sys.argv[1])
FPS, W, H, SR, LUFS = 30, 1920, 1080, 48000, -14.0
fails = []

def fail(msg):
    fails.append(msg)
    print("✖ " + msg)

def ffprobe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)

def loudness(p):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-map", "0:a:0",
                        "-af", "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None

def check_video(p, timeline=None):
    if not p.exists():
        return fail(f"{p.relative_to(root)}: 없음 (앞 단계 실패)")
    d = ffprobe(p)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    name = p.name
    if not v or not a:
        return fail(f"{name}: 영상/음성 스트림 없음")
    got = {"codec": v["codec_name"], "size": f"{v['width']}x{v['height']}", "fps": v["r_frame_rate"],
           "avg_fps": v["avg_frame_rate"], "pix": v["pix_fmt"], "acodec": a["codec_name"], "sr": a["sample_rate"]}
    want = {"codec": "h264", "size": f"{W}x{H}", "fps": f"{FPS}/1", "avg_fps": f"{FPS}/1", "pix": "yuv420p",
            "acodec": "aac", "sr": str(SR)}
    for k in want:
        if got[k] != want[k]:
            fail(f"{name}: {k} = {got[k]} (기대 {want[k]})")
    vdur, adur = float(v.get("duration") or 0), float(a.get("duration") or 0)
    if timeline:
        total = float(json.loads(timeline.read_text(encoding="utf-8"))["total"])
        if abs(vdur - total) > 1 / FPS + 1e-3:
            fail(f"{name}: 영상 길이 {vdur:.3f}s ≠ timeline {total:.3f}s (±1프레임)")
        if abs(adur - total) > 1 / FPS + 1024 / SR:
            fail(f"{name}: 음성 길이 {adur:.3f}s ≠ timeline {total:.3f}s (±1프레임)")
    lu = loudness(p)
    if lu is None or abs(lu - LUFS) > 1.0:
        fail(f"{name}: 라우드니스 {lu} LUFS (기대 {LUFS}±1)")
    print(f"  {name}: {got['size']} {got['fps']} {got['pix']} {got['codec']} / {got['acodec']} {got['sr']}Hz, "
          f"영상 {vdur:.2f}s 음성 {adur:.2f}s, {lu} LUFS")

for ep, lang in (("ep99", "en"), ("ep99", "ko"), ("ep98", "en")):
    out = root / "episodes" / ep / "out"
    check_video(out / f"{ep}_{lang}.mp4", out / f"{ep}_{lang}_timeline.json")
    thumb = out / f"{ep}_{lang}_thumb.jpg"
    if not thumb.exists():
        fail(f"{thumb.name}: 없음")
    else:
        with Image.open(thumb) as im:
            if im.format != "JPEG" or im.size != (1280, 720) or thumb.stat().st_size >= 2 * 1024 * 1024:
                fail(f"{thumb.name}: {im.format} {im.size} {thumb.stat().st_size}B (기대 JPEG 1280x720 <2MB)")
for lang in ("en", "ko"):
    if not list((root / "episodes/ep99/out").glob(f"**/check_{lang}*.jpg")):
        fail(f"ep99 {lang}: --check contact sheet(check_{lang}*.jpg) 없음")

comp = root / "compilations" / "ep98-ep99_en.mp4"
check_video(comp)
chapters = root / "compilations" / "ep98-ep99_en_chapters.txt"
lines = chapters.read_text(encoding="utf-8").splitlines() if chapters.exists() else []
if len(lines) != 2 or not lines[0].startswith("0:00 "):
    fail(f"{chapters.name}: 챕터 2줄, 첫 줄 0:00 이어야 함 — {lines}")

print("✔ 출력 규격 통과" if not fails else f"✖ {len(fails)}건 실패")
sys.exit(1 if fails else 0)
PYEOF
}

# ---------------------------------------------------------------- 실행

echo "momo 전체 테스트 — 작업 폴더 $WORK"
echo "  $("$PY" --version 2>&1), $(ffmpeg -hide_banner -version 2>/dev/null | head -1 || echo 'ffmpeg 없음')"
echo

for t in "$HERE"/test_*.py; do
  [ -e "$t" ] || continue
  step "unit: tests/$(basename "$t")" "$PY" "$t"
done

step "make_fixture --episodes 2 (ep99, ep98)" "$PY" "$HERE/make_fixture.py" --root "$ROOT" --force --episodes 2
if [ ! -f "$ROOT/episodes/ep99/manifest.json" ]; then
  echo "픽스처를 만들지 못해 나머지 단계를 건너뜀"
  summary
  exit 1
fi

step "validate_manifest --ep ep99 --table" validate_step
step "estimate_credits --ep ep99" py estimate_credits.py --root "$ROOT" --ep ep99
step "hf_jobs status --ep ep99" py hf_jobs.py status --ep ep99   # --root 위치가 서브커맨드마다 달라 MOMO_ROOT 로 전달
soft_step "doctor --ep ep99 --ci" py doctor.py --root "$ROOT" --ep ep99 --ci
step "fetch_assets --ep ep98 --library (복원)" fetch_step
step "build ep99 en --check" py build.py --root "$ROOT" --ep ep99 --lang en --check
step "build ep99 ko --check" py build.py --root "$ROOT" --ep ep99 --lang ko --check
step "build ep98 en" py build.py --root "$ROOT" --ep ep98 --lang en
step "compile --lang en ep98 ep99" py compile.py --root "$ROOT" --lang en ep98 ep99
step "upload --ep ep99 --lang all --dry-run" upload_dry_step
step "upload --compilation ep98-ep99 --dry-run" upload_compilation_step
step "episode_readme --ep ep99" readme_step
step "출력 규격 (ffprobe·loudness)" check_outputs

summary
[ "$FAILS" -eq 0 ]
