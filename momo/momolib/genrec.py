"""GenRec(생성 기록) 공용 헬퍼 — hf_jobs.py · fetch_assets.py · estimate_credits.py · doctor.py 가 쓴다.

GenRec = {"status": "pending|generated|approved|rejected", "job_id", "url", "attempts", "credits", "reason",
          "history": [{"job_id", "url", "status", "reason", "at", "credits"}]}
- 에피소드: cut.gen.image / cut.gen.clip (V) / cut.audio_src[lang]["<블록 번호>"]
  lip-synced V cuts (cut.lipsync) have one clip per language instead: cut.gen.clip_en / cut.gen.clip_ko
- 라이브러리(library.json): character_sheets[name], clips[name].image(시작 이미지)와 clips[name](클립),
  audio[lang][intro|outro], voice_samples[] — 초기값 "missing" 은 pending 으로 본다.
- song episodes: manifest.song.music (AI instrumental, generate_audio sonilo_music)
- Slot = GenRec 하나의 위치(어느 dict 의 어느 경로) + 내려받을 파일 이름 규칙.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .common import (AUDIO_EXTS, IMAGE_EXTS, LANGS, LIBRARY_AUDIO, LIBRARY_CLIPS, VIDEO_EXTS, MomoError, Paths,
                     active_langs)
from .episode import tts_blocks

STATUSES = ("pending", "generated", "approved", "rejected")
FETCHABLE = ("generated", "approved")
KIND_EXTS = {"image": IMAGE_EXTS, "clip": VIDEO_EXTS, "audio": AUDIO_EXTS}
SYMBOL = {"approved": "✔", "generated": "●", "rejected": "✖", "pending": "·"}
NA = "—"
VOICE_SAMPLES_PER_LANG = 3


def new_rec() -> dict:
    return {"status": "pending", "job_id": None, "url": None, "attempts": 0, "credits": 0, "history": []}


def status_of(rec: dict | None) -> str:
    s = (rec or {}).get("status") or "pending"
    return s if s in STATUSES else "pending"  # "missing" 등


def needs_generation(rec: dict | None) -> bool:
    """새로 생성해야 하는가 (generated 는 이미 비용을 냈고 검토만 남음)."""
    return status_of(rec) in ("pending", "rejected")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("._") or "x"


# ---------------------------------------------------------------- 단가

def video_cost(cfg: dict) -> float:
    hf = cfg["higgsfield"]
    uc = hf["unit_costs"]
    res, dur = str(hf.get("video_resolution") or "720p"), int(hf.get("video_duration") or 5)
    key = f"video_{res}_{dur}s"
    if key in uc:
        return float(uc[key])
    if f"video_{res}_5s" in uc:
        return float(uc[f"video_{res}_5s"]) * dur / 5
    raise MomoError(f"config.higgsfield.unit_costs 에 {key} 단가가 없음 — get_cost:true 로 확인해서 적어줘")


def clip_seconds(cfg: dict, cut: dict | None, lang: str | None = None) -> int:
    """Generated clip length: cut.clip_seconds (number, or {"en": 8, "ko": 9}), else config video_duration."""
    cs = (cut or {}).get("clip_seconds")
    if isinstance(cs, dict):
        vals = [v for v in cs.values() if isinstance(v, (int, float))]
        cs = cs.get(lang) if lang in cs else (max(vals) if vals else None)
    return int(cs) if isinstance(cs, (int, float)) and cs > 0 else int(cfg["higgsfield"]["video_duration"])


def clip_cost(cfg: dict, cut: dict | None, lang: str | None = None) -> float:
    """Per-clip credits: per-second rate for cut.clip_model (unit_costs.per_second), else the 5 s Kling price."""
    model = (cut or {}).get("clip_model")
    rate = ((cfg["higgsfield"]["unit_costs"].get("per_second") or {}).get(model)) if model else None
    if rate is None:
        return video_cost(cfg)
    return round(float(rate) * clip_seconds(cfg, cut, lang), 4)


def music_cost(cfg: dict, rec: dict | None) -> float:
    """AI instrumental credits: per-second rate of its model × requested duration (rec.model / rec.duration)."""
    rec = rec or {}
    rate = (cfg["higgsfield"]["unit_costs"].get("per_second") or {}).get(rec.get("model") or "sonilo_music")
    if rate is None or not rec.get("duration"):
        raise MomoError("반주 크레딧을 계산할 수 없음 — --credits 로 get_cost 값을 줄 것")
    return round(float(rate) * float(rec["duration"]), 4)


def episode_cap(cfg: dict, manifest: dict | None) -> float:
    """manifest.credits.cap (a per-episode budget the user approved) overrides config.credits.episode_cap."""
    own = ((manifest or {}).get("credits") or {}).get("cap")
    return float(own) if isinstance(own, (int, float)) and own > 0 else float(cfg["credits"]["episode_cap"])


def unit_cost(cfg: dict, kind: str) -> float:
    uc = cfg["higgsfield"]["unit_costs"]
    if kind == "image":
        return float(uc["image"])
    if kind == "clip":
        return video_cost(cfg)
    if kind == "audio":
        return float(uc["audio_block"])
    raise MomoError(f"알 수 없는 종류: {kind}")


# ---------------------------------------------------------------- 캐릭터·Elements

def char_tags(cfg: dict) -> dict[str, str]:
    return cfg["character"].get("tags") or {"[Ducky]": "ducky"}


def has_momo(cut: dict) -> bool:
    return "[Momo]" in (cut.get("image_prompt") or "") or cut.get("momo", True) is not False


def cut_characters(cfg: dict, cut: dict) -> list[str]:
    raw = cut.get("image_prompt") or ""
    keys = ["momo"] if has_momo(cut) else []
    keys += [k for tag, k in char_tags(cfg).items() if tag in raw and k not in keys]
    return keys


def characters_used(cfg: dict, manifest: dict) -> list[str]:
    keys = ["momo"] + [k for k in manifest.get("characters") or [] if k != "momo"]
    for c in manifest.get("cuts") or []:
        keys += [k for k in cut_characters(cfg, c) if k not in keys]
    return list(dict.fromkeys(keys))


def element_id(cfg: dict, key: str) -> str | None:
    hf = cfg["higgsfield"]
    return hf.get(f"{key}_element_id") or (hf.get("element_ids") or {}).get(key) or None


def element_prefix(cfg: dict, cut: dict) -> str:
    """Higgsfield Elements 자리표시 "<<<id>>> " — 등록된 캐릭터만."""
    ids = [element_id(cfg, k) for k in cut_characters(cfg, cut)]
    return "".join(f"<<<{i}>>> " for i in ids if i)


# ---------------------------------------------------------------- Slot

@dataclass
class Slot:
    key: str             # 표시용 ("c03 image", "c03 audio en #2", "library intro_wave clip" ...)
    kind: str            # image | clip | audio
    group: str           # cut | sheet | lib_image | lib_clip | lib_audio | voice
    holder: dict
    path: tuple          # holder 안의 GenRec 경로 (() 이면 holder 자체가 GenRec)
    dest: Path           # 내려받을 폴더
    stem: str            # 파일 이름 (확장자 제외)
    cut: dict | None = None
    lang: str | None = None
    block: int | None = None
    text: str = ""       # 음성 블록 문장
    name: str = ""       # 라이브러리 이름

    @property
    def rec(self) -> dict:
        d = self.holder
        for k in self.path:
            d = d.get(k) if isinstance(d, dict) else None
        return d if isinstance(d, dict) else {}

    @property
    def status(self) -> str:
        return status_of(self.rec)

    def ensure(self) -> dict:
        """GenRec 이 없으면 만들어 붙이고 돌려준다."""
        d = self.holder
        for k in self.path:
            if not isinstance(d.get(k), dict):
                d[k] = {}
            d = d[k]
        for k, v in new_rec().items():
            d.setdefault(k, v)
        if d.get("status") not in STATUSES:
            d["status"] = "pending"
        return d


def cut_slots(paths: Paths, cfg: dict, ep: str, cut: dict) -> list[Slot]:
    cid, t = cut["id"], cut.get("type")
    out = []
    if t in ("V", "S"):
        out.append(Slot(f"{cid} image", "image", "cut", cut, ("gen", "image"), paths.images(ep), cid, cut=cut))
    if t == "V" and cut.get("lipsync"):  # mouth follows the narration → one clip per language
        for lang in active_langs(cfg):
            out.append(Slot(f"{cid} clip {lang}", "clip", "cut", cut, ("gen", f"clip_{lang}"), paths.clips(ep),
                            f"{cid}_{lang}", cut=cut, lang=lang))
    elif t == "V":
        out.append(Slot(f"{cid} clip", "clip", "cut", cut, ("gen", "clip"), paths.clips(ep), cid, cut=cut))
    for lang in active_langs(cfg):
        for it in tts_blocks(cut, lang, cfg):
            out.append(Slot(f"{cid} audio {lang} #{it.index}", "audio", "cut", cut, ("audio_src", lang, str(it.index)),
                            paths.audio(ep, lang), f"{cid}_{it.index}", cut=cut, lang=lang, block=it.index,
                            text=it.text))
    return out


def song_slots(paths: Paths, manifest: dict) -> list[Slot]:
    """manifest.song.music — the AI instrumental of a song episode → episodes/<ep>/audio/music.<ext>."""
    song = manifest.get("song")
    if not isinstance(song, dict):
        return []
    return [Slot("song music", "audio", "song", song, ("music",), paths.ep(manifest["ep"]) / "audio", "music")]


def episode_slots(paths: Paths, cfg: dict, manifest: dict) -> list[Slot]:
    return [s for c in manifest.get("cuts") or [] for s in cut_slots(paths, cfg, manifest["ep"], c)] \
        + song_slots(paths, manifest)


def library_slots(paths: Paths, cfg: dict, lib: dict) -> list[Slot]:
    """library.json 의 모든 GenRec. 표준 항목이 빠져 있으면 빈 항목을 만들어 둔다 (저장은 호출자가)."""
    out = []
    for name, e in (lib.setdefault("character_sheets", {})).items():
        out.append(Slot(f"sheet {name}", "image", "sheet", e, (), paths.library_sheets, name, name=name))
    clips = lib.setdefault("clips", {})
    for name in LIBRARY_CLIPS:
        clips.setdefault(name, {"file": f"clips/{name}.mp4"})
    for name, e in clips.items():
        out.append(Slot(f"library {name} image", "image", "lib_image", e, ("image",), paths.library_clips, name,
                        name=name))
        out.append(Slot(f"library {name} clip", "clip", "lib_clip", e, (), paths.library_clips, name, name=name))
    audio = lib.setdefault("audio", {})
    for lang in active_langs(cfg):
        for name in LIBRARY_AUDIO:
            e = audio.setdefault(lang, {}).setdefault(name, {"file": f"audio/{lang}/{name}.wav"})
            text = e.get("text") or cfg["fixed_lines"][lang][name]
            out.append(Slot(f"library audio {lang} {name}", "audio", "lib_audio", e, (), paths.library_audio(lang),
                            name, lang=lang, text=text, name=name))
    for i, e in enumerate(lib.setdefault("voice_samples", [])):
        lang = e.get("lang") if e.get("lang") in LANGS else "en"
        vid = str(e.get("voice_id") or e.get("name") or i)
        out.append(Slot(f"voice sample {lang} {vid}", "audio", "voice", e, (), paths.library_audio(lang) / "samples",
                        f"{i:02d}_{safe_name(vid)}", lang=lang, text=e.get("text") or "", name=vid))
    return out


def library_clip_done(entry: dict) -> bool:
    return status_of(entry) == "approved"


# ---------------------------------------------------------------- 기록

def apply_record(rec: dict, status: str, *, job_id: str | None, url: str | None, reason: str | None,
                 cost: float, force: bool = False, extra: dict | None = None) -> tuple[dict, str]:
    """GenRec 에 결과를 반영한다. → (manifest.credits 에 더할 값, 설명).

    - generated: 새 생성 1회 (attempts+1, credits+cost, 두 번째부터 재생성). 같은 job 을 다시 적으면 무시(URL 만 갱신).
    - approved/rejected: 기록된 job(기본: 마지막 job)의 판정만 바꾼다 → 크레딧 재계산 없음.
      처음 보는 job_id 면 생성 1회로 먼저 센 뒤 판정한다.
    """
    if status not in ("generated", "approved", "rejected"):
        raise MomoError(f"status 는 generated|approved|rejected: {status!r}")
    hist = rec.setdefault("history", [])
    known = {h.get("job_id") for h in hist} | {rec.get("job_id")}
    known.discard(None)
    delta = {"spent": 0.0, "generations": 0, "regenerations": 0}
    msgs = []
    new_job = bool(job_id) and job_id not in known
    if status == "generated" and not job_id:
        raise MomoError("generated 기록에는 --job-id 가 필요함 (MCP 응답의 job id)")
    if new_job:
        if status_of(rec) == "approved" and not force:
            raise MomoError("이미 승인된 항목 — 새로 생성한 결과로 바꾸려면 --force (라이브러리는 재생성 금지가 원칙)")
        regen = int(rec.get("attempts") or 0) > 0 or bool(hist)
        rec["attempts"] = int(rec.get("attempts") or 0) + 1
        rec["credits"] = round(float(rec.get("credits") or 0) + cost, 4)
        hist.append({"job_id": job_id, "url": url, "status": "generated", "reason": None, "at": now_iso(),
                     "credits": cost, **(extra or {})})
        rec["job_id"], rec["url"], rec["reason"] = job_id, url, None
        rec["status"] = "generated"
        delta = {"spent": cost, "generations": 1, "regenerations": int(regen)}
        msgs.append(f"생성 {rec['attempts']}회째" + (" (재생성)" if regen else "") + f", {cost:g} 크레딧")
    target = job_id or rec.get("job_id")
    if not target:
        raise MomoError("기록된 생성이 없음 — 먼저 --status generated --job-id ... 로 기록하거나 --job-id 를 줘")
    entry = next((h for h in reversed(hist) if h.get("job_id") == target), None)
    if entry is None:  # history 없이 job_id 만 있던 옛 기록
        entry = {"job_id": target, "url": rec.get("url"), "status": status_of(rec), "reason": None, "at": now_iso()}
        hist.append(entry)
    if url and entry.get("url") != url:
        entry["url"] = url
        if not new_job:
            msgs.append("URL 갱신")
    if status == "generated" and not new_job:
        msgs.append("이미 기록된 job — 크레딧은 다시 세지 않음")
    if target != rec.get("job_id"):  # 예전 시도를 승인하는 경우 그 결과로 되돌린다
        rec["job_id"], rec["url"] = target, entry.get("url")
        msgs.append("이전 시도로 전환")
    elif url:
        rec["url"] = url
    if status != "generated" or new_job:
        entry["status"] = status
        rec["status"] = status
    if reason:
        entry["reason"] = reason
        rec["reason"] = reason
    return delta, ", ".join(msgs)


def add_credits(manifest: dict, delta: dict) -> dict:
    cr = manifest.setdefault("credits", {})
    cr["spent"] = round(float(cr.get("spent") or 0) + delta["spent"], 4)
    cr["generations"] = int(cr.get("generations") or 0) + delta["generations"]
    cr["regenerations"] = int(cr.get("regenerations") or 0) + delta["regenerations"]
    if delta["generations"] and manifest.get("status") in (None, "planning"):
        manifest["status"] = "producing"
    return cr


# ---------------------------------------------------------------- 크레딧 추정

@dataclass
class Row:
    group: str        # 라이브러리 | 에피소드
    label: str
    count: int
    unit: float
    kind: str         # image | clip | audio

    @property
    def credits(self) -> float:
        return round(self.count * self.unit, 4)


def estimate(paths: Paths, cfg: dict, manifest: dict, lib: dict, regen_rate: float = 0.2) -> dict:
    """남은 생성분(pending/rejected)만 센다. generated(검토 대기)는 이미 낸 비용이라 0.

    예상 총액 = 이미 사용(manifest.credits.spent) + 라이브러리 미완성분 + 에피소드 남은 분 + 재생성 여유(이미지·영상).
    """
    img, vid, aud = unit_cost(cfg, "image"), video_cost(cfg), unit_cost(cfg, "audio")
    rows: list[Row] = []
    review: list[str] = []

    sheets = lib.get("character_sheets") or {}
    need_sheets = [k for k in characters_used(cfg, manifest) if needs_generation(sheets.get(k))]
    lslots = library_slots(paths, cfg, lib)
    lib_img = [s for s in lslots if s.group == "lib_image" and needs_generation(s.rec)
               and not library_clip_done(s.holder)]
    lib_clip = [s for s in lslots if s.group == "lib_clip" and needs_generation(s.rec)]
    lib_aud = [s for s in lslots if s.group == "lib_audio" and needs_generation(s.rec)]
    samples = 0
    for lang in active_langs(cfg):
        if not (cfg.get("voices") or {}).get(lang):
            done = sum(1 for s in lslots if s.group == "voice" and s.lang == lang and s.status != "pending")
            samples += max(0, VOICE_SAMPLES_PER_LANG - done)
    review += [s.key for s in lslots if s.status == "generated"]
    rows += [Row("라이브러리", f"캐릭터 시트 ({', '.join(need_sheets)})" if need_sheets else "캐릭터 시트",
                 len(need_sheets), img, "image"),
             Row("라이브러리", "라이브러리 클립 이미지", len(lib_img), img, "image"),
             Row("라이브러리", "라이브러리 클립 (V)", len(lib_clip), vid, "clip"),
             Row("라이브러리", "고정 음성 (인트로·아웃트로)", len(lib_aud), aud, "audio"),
             Row("라이브러리", "음성 샘플 (후보 3개 × 언어)", samples, aud, "audio")]

    eslots = episode_slots(paths, cfg, manifest)
    need = [s for s in eslots if needs_generation(s.rec)]
    review += [s.key for s in eslots if s.status == "generated"]
    n_v = sum(1 for s in need if s.kind == "image" and s.cut.get("type") == "V")
    n_s = sum(1 for s in need if s.kind == "image" and s.cut.get("type") == "S")
    need_clips = [s for s in need if s.kind == "clip"]
    clip_total = sum(clip_cost(cfg, s.cut, s.lang) for s in need_clips)
    rows += [Row("에피소드", f"컷 이미지 (V {n_v} + S {n_s})", n_v + n_s, img, "image"),
             Row("에피소드", "V 클립", len(need_clips),
                 round(clip_total / len(need_clips), 4) if need_clips else vid, "clip")]
    for lang in active_langs(cfg):
        rows.append(Row("에피소드", f"나레이션 블록 {lang.upper()}",
                        sum(1 for s in need if s.kind == "audio" and s.lang == lang), aud, "audio"))

    visual = [r for r in rows if r.kind in ("image", "clip")]
    regen = round(regen_rate * sum(r.credits for r in visual), 4)
    remaining = round(sum(r.credits for r in rows), 4)
    spent = float((manifest.get("credits") or {}).get("spent") or 0)
    total = round(spent + remaining + regen, 4)
    cap = episode_cap(cfg, manifest)
    gens = sum(r.count for r in rows) + math.ceil(regen_rate * sum(r.count for r in visual))
    lib_left = sum(r.count for r in rows if r.group == "라이브러리")
    return {"ep": manifest.get("ep"), "rows": rows, "review": review, "regen_rate": regen_rate, "regen": regen,
            "remaining": remaining, "spent": spent, "total": total, "cap": cap, "over_cap": total > cap + 1e-9,
            "generations": gens, "library_incomplete": lib_left > 0,
            "unit": {"image": img, "clip": vid, "audio": aud}}


def stop_message(total: float, cap: float) -> str:
    return (f"중단 조건 — 이번 에피소드 총 크레딧이 {cap:g}을 넘을 것 같음 (예상 {total:g}). "
            f"하나라도 걸리면 즉시 멈추고 에러 원문 그대로 보고할 것 — 사용자 승인 없이 생성을 계속하지 말 것.")
