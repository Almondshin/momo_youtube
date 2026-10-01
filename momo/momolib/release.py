"""GitHub release assets (gh CLI) — media made or kept outside Higgsfield's CDN, restored by fetch_assets.py from URL.

Used by song_track.py publish (song, vocal stem, lip-sync refs) and hf_api.py archive (API outputs, kept ~7 days by
Higgsfield). Release tag per episode: media-<ep>, a prerelease that is not a code release. Asset names are
content-addressed by the caller so a new file never overwrites a URL a manifest still points to.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .common import MomoError, run, which


def need_gh() -> None:
    if not which("gh"):
        raise MomoError("gh CLI 가 필요함 (GitHub 로그인된 로컬 맥에서 실행)")


def repo_slug() -> str:
    r = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    return r.stdout.decode().strip()


def ensure_release(tag: str, title: str, notes: str) -> None:
    """Create the prerelease `tag` unless it exists."""
    if subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode != 0:
        run(["gh", "release", "create", tag, "--prerelease", "--title", title, "--notes", notes])


def upload_assets(tag: str, files: dict[str, Path]) -> dict[str, str]:
    """Upload {asset name: local file} to the release (--clobber) → {asset name: download URL}."""
    for f in files.values():
        if not Path(f).exists():
            raise MomoError(f"파일 없음: {f}")
    if not files:
        return {}
    slug = repo_slug()
    with tempfile.TemporaryDirectory() as tmp:
        for name, f in files.items():
            shutil.copy(f, Path(tmp) / name)
        run(["gh", "release", "upload", tag, "--clobber", *[str(Path(tmp) / n) for n in files]])
    base = f"https://github.com/{slug}/releases/download/{tag}"
    return {n: f"{base}/{n}" for n in files}


def is_release_url(url: str | None) -> bool:
    return bool(url) and url.startswith("https://github.com/") and "/releases/download/" in url
