"""Keep the Suno songs from sounding alike (song_track.py stylecheck).

ep04–ep09 all used nearly the same style line (Korean kindergarten sing-along, bouncy 2/4 march, 124 bpm,
choir, piano / bells / glockenspiel / xylophone / claps). The user heard it (2026-10-01: "비슷한 동요로만 생성된다").
A new episode's ```style block is compared with the recent episodes on its musical words only: the house
phrases every song shares (clear English, simple singable melody, 4-bar intro …) are left out. Lyrics must not
bring back the "Ding-dong-dang" refrain either.
"""
from __future__ import annotations

import re
from pathlib import Path

MAX_SIMILAR = 0.30   # Jaccard of musical words — ep04–ep09 sit at 0.40–0.74 with each other, ep10's lullaby ≤ 0.20
RECENT = 6           # episodes to compare with
STOP = set("a an and the with of in on to no not but all way very through every each its it is are for from by as at "
           "into only up down be".split())
HOUSE = set("""korean children children's song style english kindergarten sing-along bedtime intro instrumental 4-bar bar
bars vocals vocal major key simple singable melody clear full every verse chorus order sung break beat steady tempo young
lead bright female male choir call-and-response echoes echo answer answers asks words counting hold length about minute
minutes seconds full-length song phrases short bpm singing sings outro ending final chord last same 2-bar""".split())
BANNED = [(re.compile(r"\bding[\s,-]*dong", re.I), "Ding-dong-dang 후렴 (사용자: 그만 나왔으면)")]


def fenced(md: str) -> list[tuple[str, str]]:
    """(info string, body) of every ``` fenced block, in order."""
    out, info, body = [], None, []
    for line in md.splitlines():
        if line.startswith("```"):
            if info is None:
                info, body = line[3:].strip(), []
            else:
                out.append((info, "\n".join(body)))
                info = None
        elif info is not None:
            body.append(line)
    return out


def style_text(md: str) -> str | None:
    return next((b.strip() for i, b in fenced(md) if i == "style"), None)


def words(style: str) -> set[str]:
    """Musical words of a style line: genre, instruments, tempo, feel."""
    return {w for w in re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", style.lower())
            if w not in STOP and w not in HOUSE and len(w) > 2}


def similarity(a: str, b: str) -> float:
    wa, wb = words(a), words(b)
    return len(wa & wb) / len(wa | wb) if wa | wb else 0.0


def banned(md: str) -> list[str]:
    """Banned refrains found in the sung lyrics blocks (the style block and notes do not count)."""
    found = []
    for info, block in fenced(md):
        if info not in ("", "text"):
            continue
        for rx, why in BANNED:
            if rx.search(block):
                found.append(why)
    return sorted(set(found))


def recent_styles(episodes: Path, ep: str, last: int = RECENT) -> list[tuple[str, str]]:
    """(ep, style) of the `last` episodes before `ep` that have a lyrics.md style block."""
    def num(name: str) -> int:
        return int(re.sub(r"\D", "", name) or 0)
    out = []
    for d in sorted((p for p in episodes.glob("ep*") if p.is_dir() and num(p.name) < num(ep)), key=lambda p: num(p.name)):
        f = d / "lyrics.md"
        s = style_text(f.read_text(encoding="utf-8")) if f.exists() else None
        if s:
            out.append((d.name, s))
    return out[-last:]
