#!/bin/bash
# Claude Code on the web 세션 시작 시 momo 파이프라인 도구를 설치한다 (멱등).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

apt_install() {
  local missing=()
  command -v ffmpeg >/dev/null 2>&1 || missing+=(ffmpeg)
  [ -f /usr/share/fonts/truetype/nanum/NanumGothic.ttf ] || missing+=(fonts-nanum)
  [ ${#missing[@]} -eq 0 ] && return 0
  if ! apt-get install -y -q "${missing[@]}" >/dev/null 2>&1; then
    apt-get update -q >/dev/null 2>&1 || true
    apt-get install -y -q "${missing[@]}" >/dev/null 2>&1 || echo "[momo] apt 설치 실패: ${missing[*]}" >&2
  fi
}

apt_install
python3 -m pip install -q --disable-pip-version-check -r momo/requirements.txt 2>&1 | grep -v "Running pip as the 'root' user" || true

echo "[momo] ffmpeg: $(ffmpeg -version 2>/dev/null | head -1 | cut -d' ' -f3), yt-dlp: $(yt-dlp --version 2>/dev/null || echo 없음)" >&2
