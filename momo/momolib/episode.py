"""manifest.json 해석 규칙: 나레이션 마커, 프롬프트 조립, 검증, 컷 타임라인.

manifest 의 컷(cut) 필드 요약 (자세한 건 docs/MANIFEST.md)
  id            "c01" ...                        (필수, 고유)
  scene         1..5                             (필수)
  type          "L" | "V" | "S"                  (필수)
  library_clip  L 컷: intro_wave|outro_bye|say_with_me|cheer|transition
  library_audio L 컷: "intro"|"outro" → library/audio/<lang>/<name>.* 고정 음성 사용
  narration     {"en": "...", "ko": "..."}      [pause 1.5] / [chant] 마커 허용
  keyword       {"en": "RED", "ko": "빨강"}     화면 키워드 (컷당 1개)
  image_prompt  "[Momo] ..."                     V/S 컷. [Momo] 블록·스타일 락은 자동 조립
  momo          false 로 두면 캐릭터 블록을 붙이지 않음 (사물만 나오는 컷)
  motion        V 컷 모션 지시 ("small hop in place")
  transition    이 컷으로 들어올 때 "fade"(0.3초 크로스페이드) | "cut". 기본: 씬 경계만 fade
  text_at       키워드 등장 시점(컷 시작 기준 초). 기본 0.5
  text_pos      "top"(기본) | "bottom"   — 모모 얼굴이 위쪽이면 bottom
  text_color    "white"(기본) | "yellow"
  duration      최소 길이 강제(초). 나레이션보다 짧게는 못 줄임
  lead / tail   nothing-but-picture seconds before / after the narration (default 0 / render.tail_pad)
                — e.g. a musical lead-in on the first cut, an outro tail for the BGM fade
  fill          how a V/L clip shorter than its cut is extended: "hold" (default — slow-mo ≤1.25x +
                hold the last frame, gentle push-in), "fit" (speed the whole clip to exactly the cut length,
                0.8–1.25x, longer or shorter — keeps an end_frame hand-off intact), "loop" (crossfade into
                another pass), "pingpong" (forward then reversed, the old behaviour)
  lipsync       true → one clip per language (clips/<cut>_<lang>.mp4), mouth driven by that narration
  lip_shift     song.track lip-sync: seconds the picture runs later than its audio window (+ = later, |x| ≤ 0.5)
                — fixes a clip whose mouth moves early/late (song_track.py lipsync); clip_from reuses inherit it
  nar_ref       {"en": {"media_id", "blocks": [block jobs]}} — lip-sync cut with several speech blocks: the
                blocks + [pause] silences in one imported file (hf_jobs.py narref)
  clip_model / clip_seconds / end_frame   continuous-animation clips: model override, generated length
                (number or {"en":…, "ko":…}), and a cut id whose approved image is the clip's last frame
  inset         테두리 제거용 인셋 크롭 비율(0.03~0.04). null=자동 감지, 0=끔
  sfx           [{"file": "pop.wav", "at": 0.5, "gain_db": -6}]
  gen / audio_src  생성 기록 (job_id, url, status, attempts) — fetch_assets.py 가 사용
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from .common import (AUDIO_EXTS, CUT_ID_RE, CUT_TYPES, IMAGE_EXTS, LANGS, LIBRARY_AUDIO, LIBRARY_CLIPS,
                     VIDEO_EXTS, MomoError, Paths, active_langs, check_ep, find_media, probe_duration)

# ---------------------------------------------------------------- 나레이션 마커

PAUSE_RE = re.compile(r"\[\s*pause(?:\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?))?\s*(?:s|sec|초)?\s*\]", re.I)
CHANT_RE = re.compile(r"\[\s*chant\s*\]", re.I)
ANY_MARKER_RE = re.compile(r"\[[^\]]*\]")
FILL_MODES = ("hold", "fit", "loop", "pingpong")  # cut.fill — see build.render_seg
WS_RE = re.compile(r"\s+")


@dataclass
class NarItem:
    kind: str                 # "speech" | "pause"
    text: str = ""            # TTS 로 보낼 문장 (마커 제거됨)
    seconds: float = 0.0      # pause 길이
    chant: bool = False       # [chant] 챈트 블록
    index: int = 0            # speech 블록 번호 (1부터) → audio/<lang>/<cut>_<index>.*


def _clean(chunk: str) -> str:
    return WS_RE.sub(" ", ANY_MARKER_RE.sub(" ", chunk)).strip()


def parse_narration(text: str | None, default_pause: float = 1.5, cut_chant: bool = False) -> list[NarItem]:
    """"Can you say red? [pause 1.5] Red!" → speech, pause(1.5), speech.

    [pause] 마커는 TTS 로 보내지 않고 조립 때 무음이 된다. 숫자가 없으면 default_pause.
    """
    items: list[NarItem] = []
    if not text:
        return items
    pos = 0
    chunks: list[tuple[str, float | None]] = []
    for m in PAUSE_RE.finditer(text):
        chunks.append((text[pos:m.start()], float(m.group(1)) if m.group(1) else default_pause))
        pos = m.end()
    chunks.append((text[pos:], None))
    n = 0
    for chunk, pause in chunks:
        clean = _clean(chunk)
        if clean:
            n += 1
            items.append(NarItem("speech", text=clean, chant=cut_chant or bool(CHANT_RE.search(chunk)), index=n))
        if pause is not None and pause > 0:
            items.append(NarItem("pause", seconds=pause))
    return items


def narration_text(cut: dict, lang: str) -> str:
    nar = cut.get("narration") or {}
    return (nar.get(lang) or "").strip() if isinstance(nar, dict) else ""


def narration_items(cut: dict, lang: str, cfg: dict) -> list[NarItem]:
    return parse_narration(narration_text(cut, lang), float(cfg["render"]["default_pause"]),
                           bool(cut.get("chant")))


def tts_blocks(cut: dict, lang: str, cfg: dict) -> list[NarItem]:
    """이 컷에서 TTS 로 생성해야 하는 블록. 라이브러리 고정 음성을 쓰는 L 컷은 빈 목록."""
    if cut.get("type") == "L" and cut.get("library_audio"):
        return []
    return [it for it in narration_items(cut, lang, cfg) if it.kind == "speech"]


def spoken_text(cut: dict, lang: str) -> str:
    """검증용: 마커를 모두 뺀 나레이션."""
    return _clean(narration_text(cut, lang))


# ---------------------------------------------------------------- 프롬프트 조립

def compose_image_prompt(cfg: dict, cut: dict) -> str:
    """[Momo] 캐릭터 블록을 맨 앞에, 스타일 락을 맨 뒤에 그대로 붙인다.

    - [Ducky]·[Croc]·[Shark] 등 조연 태그(config.character.tags)는 그 자리에서 조연 블록으로 치환
    - cut.momo == false 이고 [Momo] 태그가 없으면 캐릭터 블록 생략 (사물 클로즈업 등)
    """
    raw = (cut.get("image_prompt") or "").strip()
    has_tag = "[Momo]" in raw
    body = raw.replace("[Momo]", " ")
    tags = cfg["character"].get("tags") or {"[Ducky]": "ducky"}
    for tag, key in tags.items():  # 조연 태그는 그 자리에서 캐릭터 블록으로 치환 (블록 끝에 쉼표로 문장 분리)
        body = body.replace(tag, (cfg["character"].get(key) or "").strip().rstrip(",.") + ",")
    body = re.sub(r",\s*,", ",", body)
    body = WS_RE.sub(" ", body).strip(" ,.;")
    parts = []
    if has_tag or cut.get("momo", True):
        parts.append(cfg["character"]["momo"].strip().rstrip(",."))
        if cfg["character"].get("momo_reinforce"):  # 블록은 그대로 두고 자주 틀리는 부분만 덧붙여 고정
            parts.append(cfg["character"]["momo_reinforce"].strip().rstrip(",."))
    if body:
        parts.append(body)
    parts.append(cfg["style_lock"].strip().rstrip(",."))
    return ", ".join(p for p in parts if p)


def compose_motion_prompt(cfg: dict, cut: dict) -> str:
    motion = (cut.get("motion") or "").strip().rstrip(".")
    return f"{motion}. {cfg['video_prompt_suffix'].strip()}".strip()


# ---------------------------------------------------------------- 검증

FORBIDDEN_IP = ["cocomelon", "coco melon", "pinkfong", "pink fong", "baby shark", "peppa", "bluey",
                "paw patrol", "blippi", "little baby bum", "super simple songs", "hey bear", "pororo",
                "tayo", "robocar", "poli", "larva", "hello kitty", "sanrio", "miffy", "peter rabbit",
                "bugs bunny", "judy hopps", "zootopia", "disney", "dreamworks", "nintendo", "pokemon",
                "코코멜론", "핑크퐁", "아기상어", "페파", "뽀로로", "타요", "로보카", "폴리", "라바", "블루이"]
TEXT_WORDS = ["text", "letter", "letters", "word", "words", "sign", "signboard", "label", "caption",
              "written", "writing", "typography", "logo", "digits", "numerals", "subtitle", "banner"]
SCARY_WORDS = ["scary", "dark", "night", "monster", "ghost", "blood", "horror", "creepy", "storm",
               "lightning", "thunder", "flash", "flashing", "strobe", "fire", "explosion", "crying hard",
               "angry", "weapon", "knife", "gun"]
MOTION_RISK = ["camera", "zoom", "pan ", "dolly", "orbit", "tracking", "transform", "morph", "spin",
               "fast", "run across", "fly away"]


def _word_hit(text: str, words: list[str]) -> list[str]:
    low = f" {text.lower()} "
    hits = []
    for w in words:
        if re.search(r"(?<![a-z])" + re.escape(w.strip()) + r"(?![a-z])", low) if w.isascii() else w in low:
            hits.append(w.strip())
    return hits


def count_types(manifest: dict) -> dict[str, int]:
    counts = {t: 0 for t in CUT_TYPES}
    for c in manifest.get("cuts", []):
        if c.get("type") in counts:
            counts[c["type"]] += 1
    return counts


def _validate_track(cfg: dict, song: dict, tr: dict, cuts: list[dict]) -> tuple[list[str], list[str]]:
    """Rules only a finished-song (song.track) episode has."""
    from .genrec import clip_seconds  # genrec imports this module
    E: list[str] = []
    W: list[str] = []
    ana = tr.get("analysis")
    if not (isinstance(ana, dict) and all(isinstance(ana.get(k), (int, float)) for k in ("bpm", "downbeat0"))):
        E.append("song.track.analysis {bpm, downbeat0} 없음 — song_track.py analyze")
        return E, W
    if not any((ln.get("words") for ln in song.get("lyrics") or [] if isinstance(ln, dict))):
        W.append("song.lyrics 에 단어 시각이 없음 — 가사 자막이 안 나온다 (song_track.py lyrics)")
    for i, c in enumerate(cuts):
        at = c.get("cut_at")
        if at is not None and (not _is_num(at) or at < 0):
            E.append(f"{c.get('id')}: cut_at 은 노래 파일 기준 초 (0 이상)")
        elif at is not None and i == 0:
            W.append(f"{c.get('id')}: 첫 컷의 cut_at 은 쓰이지 않는다 (0 에서 시작)")
        ca = c.get("clip_at")
        if ca is not None and (not _is_num(ca) or ca < 0):
            E.append(f"{c.get('id')}: clip_at 은 0 이상의 초 (자기 클립의 시작 위치)")
    spans = track_spans(song, cuts)
    for c, (s, e) in zip(cuts, spans):
        if e - s < 0.4:
            E.append(f"{c.get('id')}: 컷 길이 {e - s:.2f}s — cut_at 이 앞 컷보다 늦어야 하고 0.4초 이상 (순서 확인)")
    by_id = {c.get("id"): c for c in cuts}
    length = tr.get("duration")
    if isinstance(length, (int, float)) and spans and spans[-1][1] > length - float(tr.get("start") or 0) + 0.05:
        E.append(f"컷 마디 합이 노래보다 김: 마지막 컷 끝 {spans[-1][1]:.2f}s > 노래 {length:.2f}s — bars 확인")
    for c, (s, e) in zip(cuts, spans):
        cid, t = c.get("id"), c.get("type")
        if t == "V" and spoken_text(c, "en"):
            W.append(f"{cid}: 노래 파일 에피소드의 V 컷 narration 은 쓰이지 않는다 (가사는 song.lyrics)")
        if t == "V" and c.get("lipsync"):
            if c.get("clip_model") != "wan2_7":
                W.append(f"{cid}: 립싱크 컷은 clip_model wan2_7 (오디오 레퍼런스로 입을 맞춤)")
            need = math.ceil(e - s - 1e-6)
            if clip_seconds(cfg, c, "en") < need:
                W.append(f"{cid}: clip_seconds {clip_seconds(cfg, c, 'en')} < 컷 {e - s:.2f}s — {need} 이상")
        cf = c.get("clip_from")
        if cf is not None:
            src = by_id.get((cf or {}).get("cut")) if isinstance(cf, dict) else None
            at = (cf or {}).get("at", 0) if isinstance(cf, dict) else None
            if src is None or src.get("type") != "V" or src.get("clip_from") or t != "V":
                E.append(f"{cid}: clip_from 은 {{\"cut\": <다른 V 컷(clip_from 없는)>, \"at\": 초}} — V 컷에서만")
            elif not isinstance(at, (int, float)) or isinstance(at, bool) or at < 0:
                E.append(f"{cid}: clip_from.at 은 0 이상의 초")
            else:
                have = clip_seconds(cfg, src, "en")
                if at + (e - s) > have + 0.05:
                    W.append(f"{cid}: clip_from {src['id']} {at}s~ 에 {e - s:.2f}s 가 안 남음 (원본 {have}s) "
                             f"— 끝부분이 느려지거나 멈춘다")
                if src.get("lipsync") and not c.get("lipsync_ok"):
                    W.append(f"{cid}: 립싱크 컷 {src['id']} 재사용 — 같은 노래 구간(후렴 복사)일 때만 입이 맞는다 "
                             f"(확인했으면 lipsync_ok: true)")
    return E, W


def validate_manifest(cfg: dict, manifest: dict) -> tuple[list[str], list[str]]:
    """(errors, warnings). errors 가 있으면 제작/조립을 진행하지 않는다."""
    E: list[str] = []
    W: list[str] = []
    rules = cfg["plan_rules"]
    try:
        check_ep(manifest.get("ep", ""))
    except MomoError as e:
        E.append(str(e))
    cuts = manifest.get("cuts") or []
    if not cuts:
        E.append("cuts 가 비어 있음")
        return E, W

    ids = [c.get("id") for c in cuts]
    for cid in ids:
        if not cid or not CUT_ID_RE.match(str(cid)):
            E.append(f"컷 id 형식 오류: {cid!r} (c01 형식)")
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        E.append(f"컷 id 중복: {sorted(dup)}")

    counts = count_types(manifest)
    n = len(cuts)
    if not rules["cuts_min"] <= n <= rules["cuts_max"]:
        W.append(f"총 컷 {n}개 — 목표 {rules['cuts_min']}~{rules['cuts_max']}")
    for t, key in (("V", "v_range"), ("S", "s_range"), ("L", "l_range")):
        lo, hi = rules[key]
        if not lo <= counts[t] <= hi:
            msg = f"{t} 컷 {counts[t]}개 — 목표 {lo}~{hi}"
            if t == "V" and counts[t] > hi:
                msg += " (V 가 15개를 넘으면 manifest.notes.v_over_reason 에 이유를 적고 승인받을 것)"
                if not (manifest.get("notes") or {}).get("v_over_reason"):
                    E.append(msg)
                    continue
            W.append(msg)

    prev_scene = 0
    for c in cuts:
        cid = c.get("id", "?")
        t = c.get("type")
        if t not in CUT_TYPES:
            E.append(f"{cid}: type 은 L/V/S 중 하나 ({t!r})")
            continue
        sc = c.get("scene")
        if not isinstance(sc, int) or sc < 1:
            E.append(f"{cid}: scene 은 1 이상의 정수")
        elif sc < prev_scene:
            E.append(f"{cid}: scene 순서가 거꾸로 감 ({prev_scene} → {sc})")
        else:
            prev_scene = sc
        if t == "L":
            if c.get("library_clip") not in LIBRARY_CLIPS:
                E.append(f"{cid}: L 컷 library_clip 은 {LIBRARY_CLIPS} 중 하나")
            la = c.get("library_audio")
            if la:
                if la not in LIBRARY_AUDIO:
                    E.append(f"{cid}: library_audio 는 {LIBRARY_AUDIO} 중 하나")
                else:
                    for lang in active_langs(cfg):
                        want = cfg["fixed_lines"][lang][la]
                        if spoken_text(c, lang) != want:
                            E.append(f"{cid}: {lang} 나레이션이 고정 문장과 다름 — {want!r} 이어야 함")
                        if PAUSE_RE.search(narration_text(c, lang)):
                            E.append(f"{cid}: 라이브러리 고정 음성 컷에는 [pause] 를 넣을 수 없음")
        else:
            if not (c.get("image_prompt") or "").strip():
                E.append(f"{cid}: {t} 컷에 image_prompt 없음")
            else:
                raw = c["image_prompt"]
                ip = _word_hit(raw, FORBIDDEN_IP)
                if ip:
                    E.append(f"{cid}: 기존 IP 이름 금지 {ip}")
                tw = _word_hit(raw, TEXT_WORDS)
                if tw:
                    W.append(f"{cid}: 이미지 프롬프트에 글자 유발 단어 {tw} — 텍스트는 조립에서 얹는다")
                sw = _word_hit(raw, SCARY_WORDS)
                if sw:
                    W.append(f"{cid}: 2~5세용 — 무섭거나 어두운 요소 의심 {sw}")
                if "[" in compose_image_prompt(cfg, c):
                    E.append(f"{cid}: 알 수 없는 [태그]가 프롬프트에 남음")
                if c.get("momo") is False and "[Momo]" not in raw:
                    W.append(f"{cid}: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인")
            if t == "V":
                mo = (c.get("motion") or "").strip()
                if not mo:
                    E.append(f"{cid}: V 컷에 motion 없음")
                else:
                    risk = _word_hit(mo, MOTION_RISK)
                    if risk:
                        W.append(f"{cid}: 모션 지시에 위험 단어 {risk} — 작게, 카메라 고정")
        for lang in active_langs(cfg):
            spoken = spoken_text(c, lang)
            if lang == "en":
                words = len(spoken.split())
                if words > rules["narration_max_words_en"]:
                    W.append(f"{cid}: EN 나레이션 {words}단어 (권장 ≤{rules['narration_max_words_en']})")
            else:
                chars = len(spoken.replace(" ", ""))
                if chars > rules["narration_max_chars_ko"]:
                    W.append(f"{cid}: KO 나레이션 {chars}자 (권장 ≤{rules['narration_max_chars_ko']})")
            kw = ((c.get("keyword") or {}).get(lang) or "").strip()
            if kw and (len(kw.split()) > 2 or re.search(r"[.!?,]", kw)):
                W.append(f"{cid}: {lang} 키워드는 1개 단어만 ({kw!r}) — 문장 자막 금지")
        if c.get("text_pos") not in (None, "top", "bottom"):
            E.append(f"{cid}: text_pos 는 top|bottom")
        if c.get("transition") not in (None, "fade", "cut"):
            E.append(f"{cid}: transition 은 fade|cut")
        if c.get("fill") not in (None,) + FILL_MODES:
            E.append(f"{cid}: fill 은 {'|'.join(FILL_MODES)}")
        for lang, ref in (c.get("nar_ref") or {}).items():
            if lang not in LANGS or not isinstance(ref, dict) or not ref.get("media_id") \
                    or not (isinstance(ref.get("blocks"), list) or isinstance(ref.get("window"), list)):
                E.append(f"{cid}: nar_ref.{lang} 는 {{media_id, blocks}} 또는 노래 파일이면 {{media_id, window, "
                         f"track_sha1}} (hf_jobs.py narref 로 기록)")
        for k in ("lead", "tail"):
            v = c.get(k)
            if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 5):
                E.append(f"{cid}: {k} 는 0~5 초")
        card = c.get("card")
        if card is not None and not (isinstance(card, dict) and str(card.get("word") or "").strip()):
            E.append(f"{cid}: card 는 {{\"word\": \"TOOTHBRUSH\", \"text\": \"It cleans our teeth!\"}}")
        if isinstance(manifest.get("song"), dict):
            bars = c.get("bars")
            if not isinstance(bars, int) or isinstance(bars, bool) or not 1 <= bars <= 16:
                E.append(f"{cid}: song 에피소드는 컷마다 bars (1~16 정수) 필요")
            beats = c.get("beats")
            if beats is not None and not (isinstance(beats, list) and all(
                    isinstance(b, (int, float)) and not isinstance(b, bool) and b >= 0 for b in beats)):
                E.append(f"{cid}: beats 는 가사 줄마다 시작 박 번호 목록 (예: [0, 8])")

    by_id = {c.get("id"): c for c in cuts}
    for c in cuts:
        v, cid = c.get("lip_shift"), c.get("id")
        if v is None:
            continue
        cf = c.get("clip_from") if isinstance(c.get("clip_from"), dict) else None
        lip_src = bool(cf and (by_id.get(cf.get("cut")) or {}).get("lipsync"))
        if not _is_num(v) or abs(v) > LIP_SHIFT_MAX:
            E.append(f"{cid}: lip_shift 는 -{LIP_SHIFT_MAX}~{LIP_SHIFT_MAX} 초 (+ = 화면을 늦게, 입이 일찍 움직이는 클립)")
        elif not (c.get("type") == "V" and (c.get("lipsync") or lip_src)):
            E.append(f"{cid}: lip_shift 는 립싱크 컷, 또는 립싱크 컷을 재사용하는 clip_from 컷에만")
        elif song_track(manifest.get("song")) is None:
            W.append(f"{cid}: lip_shift 는 노래 파일(song.track) 에피소드에서만 적용 — 무시됨")

    song = manifest.get("song")
    if song is not None:
        if not isinstance(song, dict):
            E.append("song 은 {bpm, beats_per_bar, music} 객체")
        else:
            bpm = song.get("bpm")
            if not isinstance(bpm, (int, float)) or not 60 <= bpm <= 180:
                E.append("song.bpm 은 60~180")
            if song.get("beats_per_bar") not in (None, 2, 3, 4, 6):
                E.append("song.beats_per_bar 는 2|3|4|6")
            ana = (song.get("music") or {}).get("analysis")
            if ana is not None and not (isinstance(ana, dict) and all(
                    isinstance(ana.get(k), (int, float)) for k in ("bpm", "downbeat0"))):
                E.append("song.music.analysis 는 {bpm, downbeat0} (preview_assets 가 계산)")
            tr = song_track(song)
            if song.get("track") is not None and tr is None:
                E.append("song.track 은 객체 (song_track.py import 로 기록)")
            if tr is not None:
                te, tw = _validate_track(cfg, song, tr, cuts)
                E += te
                W += tw

    first, last = cuts[0], cuts[-1]
    if not (first.get("type") == "L" and first.get("library_clip") == "intro_wave"):
        W.append("첫 컷은 L intro_wave(고정 인사) 권장")
    if not (last.get("type") == "L" and last.get("library_clip") == "outro_bye"):
        W.append("마지막 컷은 L outro_bye(고정 작별) 권장")
    scenes = sorted({c.get("scene") for c in cuts if isinstance(c.get("scene"), int)})
    if len(scenes) != rules["scenes"]:
        W.append(f"씬 {len(scenes)}개 — 목표 {rules['scenes']}개")

    # 핵심 단어 반복 (키워드가 나레이션에 최소 N번)
    for lang in active_langs(cfg):
        all_text = " ".join(spoken_text(c, lang) for c in cuts).lower()
        for kw in sorted({((c.get("keyword") or {}).get(lang) or "").strip() for c in cuts} - {""}):
            cnt = all_text.count(kw.lower())
            if cnt < rules["keyword_min_repeats"]:
                W.append(f"{lang} 키워드 {kw!r} 나레이션 반복 {cnt}회 (최소 {rules['keyword_min_repeats']})")

    # 썸네일 / 제목 / 업로드 메타
    th = manifest.get("thumbnail") or {}
    if th.get("cut") and th["cut"] not in ids:
        E.append(f"thumbnail.cut {th['cut']!r} 가 컷 목록에 없음")
    for lang in active_langs(cfg):
        tt = ((th.get("text") or {}).get(lang) or "").strip()
        if tt and len(tt.split()) > 3:
            W.append(f"썸네일 문구({lang}) 3단어 이하 권장: {tt!r}")
    up = manifest.get("upload") or {}
    for lang in active_langs(cfg):
        meta = up.get(lang) or {}
        title = meta.get("title") or (manifest.get("title") or {}).get(lang) or ""
        if title:
            if len(title) > 100:
                E.append(f"{lang} 제목 100자 초과 ({len(title)})")
            if "<" in title or ">" in title:
                E.append(f"{lang} 제목에 < > 사용 불가 (YouTube 거부)")
        desc = meta.get("description") or ""
        if len(desc.encode("utf-8")) > 5000:
            E.append(f"{lang} 설명 5000바이트 초과")
        if "<" in desc or ">" in desc:
            E.append(f"{lang} 설명에 < > 사용 불가 (YouTube 거부)")
        tags = meta.get("tags") or []
        tag_len = sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1)
        if tag_len > 500:
            E.append(f"{lang} 태그 총 길이 {tag_len}자 > 500")
    return E, W


# ---------------------------------------------------------------- 타임라인

@dataclass
class CutPlan:
    index: int
    id: str
    type: str
    scene: int
    cut: dict
    items: list[NarItem]
    speech_files: list[Path | None]
    speech_durs: list[float]
    nar_len: float            # 음성 + [pause] 합
    nar_offset: float         # 컷 시작 기준 나레이션 시작 (fade 로 들어오면 크로스페이드가 끝난 뒤)
    xf_in: float              # 이전 컷과 겹치는 크로스페이드 길이 (cut 이면 0)
    dur: float                # 컷 길이 (프레임 단위로 올림)
    start: float              # 전체 타임라인 기준 시작
    source: Path | None
    source_kind: str          # "video" | "image" | "placeholder"
    source_len: float | None
    keyword: str
    text_at: float
    text_pos: str
    text_color: str
    inset: float | None
    sfx: list[dict] = field(default_factory=list)
    estimated_audio: bool = False
    warnings: list[str] = field(default_factory=list)
    # song episodes: where each speech block (lyric line) sits, relative to the cut start
    block_starts: list[float] = field(default_factory=list)
    block_tempos: list[float] = field(default_factory=list)
    block_lens: list[float] = field(default_factory=list)
    card: dict | None = None      # word card {"word", "text"} shown beside the picture
    # song: (line, start, sung, until, word_at) — word_at None = words light by their share of characters
    lyrics: list[tuple] = field(default_factory=list)
    src_offset: float = 0.0       # start this far into the clip (clip_from.at, clip_at, or a lip-sync window offset)
    hold0: float = 0.0            # hold the clip's first frame this long before it plays (lip-sync timing)
    lip_shift: float = 0.0        # effective cut.lip_shift (own, or inherited from the clip_from source)
    lip_locked: bool = False      # mouth follows the audio: never time-stretched (lipsync, or clip_from of one)


SONG_TEMPO_MAX = 1.3   # a lyric line may be sped up this much to fit before the next line (atempo, same pitch)
SONG_GAP = 0.08        # silence kept before the next line / the cut end


def song_grid(song: dict) -> tuple[float, float]:
    """(beat, bar) seconds of a song episode."""
    beat = 60.0 / float(song["bpm"])
    return beat, beat * int(song.get("beats_per_bar") or 4)


LYRIC_HOLD = 1.2       # track songs: a lyric line stays up this long after its last word (unless the next starts)


def song_track(song: dict | None) -> dict | None:
    """manifest.song.track — a finished song (vocals + music in one file) the video is cut to, or None.

    Track songs have no per-line TTS: cuts sit on the song's bar grid (song.track.analysis), the karaoke
    captions come from song.lyrics (word times from alignment) and lip-sync refs are slices of the vocal stem.
    """
    t = (song or {}).get("track") if isinstance(song, dict) else None
    return t if isinstance(t, dict) else None


def bar_time(song: dict, k: int) -> float:
    """Song-file time (s) of bar line k (k = 0 is the first downbeat): analysis.downbeats[k] when measured,
    else downbeat0 + k·bar."""
    ana = (song_track(song) or {}).get("analysis") or {}
    _, bar = song_grid(song)
    downs = ana.get("downbeats") or []
    if k < len(downs):
        return float(downs[k])
    if downs:
        return float(downs[-1]) + (k - len(downs) + 1) * bar
    return float(ana.get("downbeat0") or 0.0) + k * bar


def track_spans(song: dict, cuts: list[dict]) -> list[tuple[float, float]]:
    """(start, end) of every cut in VIDEO time for a track song. Video t = song-file t − track.start.

    Cut i covers bars [k, k + bars): the first cut starts at 0 (it also holds any pickup before the first
    downbeat), the rest start on their bar line, the last one runs to track.end when that is later.
    A cut with `cut_at` (song-file seconds) starts there instead — on the sung line's pickup rather than the bar
    line — and the cut before it ends there.
    """
    tr = song_track(song) or {}
    t0 = float(tr.get("start") or 0.0)
    starts, k = [], 0
    for i, c in enumerate(cuts):
        bars = c.get("bars") if isinstance(c.get("bars"), int) and c.get("bars") > 0 else 1
        at = c.get("cut_at")
        starts.append(0.0 if i == 0 else (float(at) if _is_num(at) else bar_time(song, k)) - t0)
        k += bars
    end = bar_time(song, k) - t0
    if isinstance(tr.get("end"), (int, float)):
        end = max(end, float(tr["end"]) - t0)
    return [(round(s, 6), round(e, 6)) for s, e in zip(starts, starts[1:] + [end])]


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


LIP_SHIFT_MAX = 0.5


def lip_shift_of(cut: dict, by_id: dict) -> float:
    """cut.lip_shift, else the one of its clip_from source when that is a lip-sync cut (a reused take carries the
    same mouth timing). + = the picture runs later than the audio it was made for."""
    v = cut.get("lip_shift")
    if _is_num(v):
        return float(v)
    cf = cut.get("clip_from") if isinstance(cut.get("clip_from"), dict) else None
    src = by_id.get((cf or {}).get("cut")) or {}
    return float(src["lip_shift"]) if cf and src.get("lipsync") and _is_num(src.get("lip_shift")) else 0.0


def _clip_start(off: float) -> tuple[float, float]:
    """Clip time to show at the cut start → (src_offset, hold0): a negative one holds frame 0 that long."""
    off = round(off, 6)
    return max(0.0, off), max(0.0, -off)


def track_lines(song: dict) -> list[dict]:
    """song.lyrics with word times → [{"text", "words": [(word, t0, t1)], "t0", "t1", "until"}] in song time."""
    lines = []
    for ln in song.get("lyrics") or []:
        words = [(str(w[0]), float(w[1]), float(w[2])) for w in (ln.get("words") or []) if len(w) >= 3]
        if not words:
            continue
        lines.append({"text": " ".join(w for w, _, _ in words), "words": words,
                      "t0": words[0][1], "t1": max(t1 for _, _, t1 in words)})
    lines.sort(key=lambda d: d["t0"])
    for a, b in zip(lines, lines[1:] + [None]):
        a["until"] = min(b["t0"], a["t1"] + LYRIC_HOLD) if b else a["t1"] + LYRIC_HOLD
    return lines


def track_cut_lyrics(lines: list[dict], t0: float, start: float, dur: float) -> list[tuple]:
    """Karaoke lines of one cut: (text, start, sung, until, word_at) relative to the cut, word_at = share of the
    sung time before each word (from the aligned word starts)."""
    out = []
    for ln in lines:
        s = ln["t0"] - t0 - start
        until = ln["until"] - t0 - start
        if until <= 0 or s - LYRIC_LEAD_S >= dur:
            continue
        sung = max(1e-3, ln["t1"] - ln["t0"])
        word_at = [round((w0 - ln["t0"]) / sung, 4) for _, w0, _ in ln["words"]]
        out.append((ln["text"], round(s, 4), round(sung, 4), round(min(until, dur), 4), word_at))
    return out


LYRIC_LEAD_S = 0.25    # = render.LYRIC_LEAD (a line shows this long before it is sung)


def place_song_lines(cut: dict, items: list[NarItem], lens: list[float], song: dict,
                     dur: float) -> tuple[list[float], list[float], list[str]]:
    """Lyric lines of one cut → (start of each line relative to the cut, speed-up per line, warnings).

    cut.beats = [0, 8] puts line 1 on beat 0 and line 2 on beat 8 of the cut; missing entries start on the
    first beat after the previous line (+ any [pause] seconds). A line longer than the room before the next
    line (or the cut end) is sped up, at most SONG_TEMPO_MAX.
    """
    beat, _ = song_grid(song)
    want = [float(b) for b in (cut.get("beats") or [])]
    starts: list[float] = []
    end, pause, k = 0.0, 0.0, 0
    for it in items:
        if it.kind == "pause":
            pause += it.seconds
            continue
        if k < len(want):
            s = want[k] * beat
        elif k == 0:
            s = 0.0
        else:
            s = math.ceil((end + pause + SONG_GAP) / beat - 1e-6) * beat
        starts.append(round(s, 6))
        end, pause = s + lens[k], 0.0
        k += 1
    tempos, warns = [], []
    for i, (s, ln) in enumerate(zip(starts, lens)):
        stop = starts[i + 1] if i + 1 < len(starts) else dur
        room = stop - SONG_GAP - s
        tempo = 1.0
        if room <= 0:
            warns.append(f"{cut.get('id')}: 가사 {i + 1}줄 시작({s:.2f}s)이 컷 길이/다음 줄보다 늦음 — beats 확인")
        elif ln > room + 1e-6:
            tempo = ln / room
            if tempo > SONG_TEMPO_MAX:
                warns.append(f"{cut.get('id')}: 가사 {i + 1}줄 {ln:.2f}s 가 자리 {room:.2f}s 에 안 들어감 — "
                             f"줄을 줄이거나 bars 를 늘릴 것 (x{SONG_TEMPO_MAX} 까지만 빠르게)")
                tempo = SONG_TEMPO_MAX
        tempos.append(round(tempo, 4))
    return starts, tempos, warns


def estimate_speech(text: str, lang: str) -> float:
    """음성이 아직 없을 때(애니매틱) 쓰는 대략 길이."""
    if lang == "ko":
        return 0.3 + len(text.replace(" ", "")) / 4.0
    return 0.3 + len(text.split()) / 2.2


def _resolve_sfx(paths: Paths, cut: dict) -> tuple[list[dict], list[str]]:
    out, warn = [], []
    for s in cut.get("sfx") or []:
        if isinstance(s, str):
            s = {"file": s}
        name = str(s.get("file") or "")
        f = paths.sfx / name
        if not f.exists():
            stem = Path(name).stem
            f = find_media(paths.sfx, stem, AUDIO_EXTS) or f
        if not f.exists():
            warn.append(f"{cut.get('id')}: 효과음 {name!r} 없음 → 생략")
            continue
        out.append({"file": f, "at": float(s.get("at", 0.0)), "gain_db": float(s.get("gain_db", -6.0))})
    return out, warn


def plan_timeline(paths: Paths, cfg: dict, manifest: dict, lang: str,
                  allow_missing: bool = False) -> tuple[list[CutPlan], float, list[str]]:
    """컷 길이·시작 시각·키워드 타이밍을 매번 새로 계산한다.

    컷 길이 = max(크로스페이드 + lead + 나레이션(음성+pause) + tail(기본 tail_pad), min_cut, cut.duration)
      - V/L 컷에 나레이션이 없으면 클립 길이
      - 프레임 경계(1/fps)로 올림 → 영상·음성 싱크가 누적 오차 없이 맞음
    fade 로 들어오는 컷은 이전 컷과 xfade 초만큼 겹친다. 나레이션은 겹침이 끝난 뒤 시작하므로
    이전 컷 나레이션(끝에 tail_pad 여유)과 절대 겹치지 않는다.
    """
    ep = check_ep(manifest["ep"])
    r = cfg["render"]
    fps = int(r["fps"])
    tail = float(r["tail_pad"])
    min_cut = float(r["min_cut"])
    xfade = float(r["xfade"])
    song = manifest.get("song") if isinstance(manifest.get("song"), dict) and manifest["song"].get("bpm") else None
    track = song_track(song) if song else None
    if song:
        from .audio import speech_length  # numpy — only song episodes need it here
        _, bar = song_grid(song)
    if track:
        spans = track_spans(song, manifest["cuts"])
        tlines = track_lines(song)
        t_start = float(track.get("start") or 0.0)
        if not tlines:
            warnings_head = ["song.lyrics 에 단어 시각이 없음 — song_track.py lyrics 로 정렬 결과를 넣을 것 (가사 자막 없이 조립)"]
        else:
            warnings_head = []
    by_id = {c.get("id"): c for c in manifest["cuts"]}
    song_bars = 0          # bars before this cut — song cut starts/ends are rounded from the bar grid, no drift
    plans: list[CutPlan] = []
    warnings: list[str] = list(warnings_head) if track else []
    missing: list[str] = []
    start_f = 0
    prev_dur_f = 0
    prev_scene = None

    for i, c in enumerate(manifest["cuts"]):
        cid, t = c["id"], c["type"]
        scene = int(c.get("scene") or 0)
        items = narration_items(c, lang, cfg)

        # ---- 영상 소스
        source, kind, src_len, src_off, hold0 = None, "placeholder", None, 0.0, 0.0
        cf = c.get("clip_from") if isinstance(c.get("clip_from"), dict) else None
        # a lip-sync take (own, or reused) is never time-stretched; song.track ones may run lip_shift later
        locked = t == "V" and bool(c.get("lipsync") or (cf and (by_id.get(cf.get("cut")) or {}).get("lipsync")))
        ls = lip_shift_of(c, by_id) if locked and track else 0.0
        if t == "V" and cf:  # reuse another cut's clip (a part of it) — no new image or clip
            other = str(cf.get("cut") or "")
            source = find_media(paths.clips(ep), f"{other}_{lang}", VIDEO_EXTS) or find_media(paths.clips(ep), other,
                                                                                              VIDEO_EXTS)
            src_off, hold0 = _clip_start(float(cf.get("at") or 0.0) - ls)
            if source:
                kind = "video"
            else:
                missing.append(f"clips/{other}.mp4 ({cid} clip_from)")
        elif t == "L":
            source = find_media(paths.library_clips, c.get("library_clip", ""), VIDEO_EXTS)
            if source:
                kind = "video"
            else:
                missing.append(f"library/clips/{c.get('library_clip')}.mp4 ({cid})")
        elif t == "V":
            source = find_media(paths.clips(ep), f"{cid}_{lang}", VIDEO_EXTS) or find_media(paths.clips(ep), cid,
                                                                                            VIDEO_EXTS)
            win = ((c.get("nar_ref") or {}).get(lang) or {}).get("window") if track and c.get("lipsync") else None
            win = win if isinstance(win, list) and len(win) == 2 and all(_is_num(w) for w in win) else None
            if _is_num(c.get("clip_at")):
                off = float(c["clip_at"])
            elif win:  # the clip lip-syncs to its pinned vocal window, not to the cut
                off = spans[i][0] + t_start - float(win[0])
            else:
                off = 0.0
            src_off, hold0 = _clip_start(off - ls)   # lip_shift: show the clip ls later (+) / earlier (−)
            if win and not _is_num(c.get("clip_at")):
                e_song = spans[i][1] + t_start
                if hold0 > max(0.0, ls) + 0.02:  # a hold that lip_shift did not ask for
                    warnings.append(f"{cid}: 립싱크 창 {win[0]:.2f}s 보다 {hold0 - max(0.0, ls):.2f}s 먼저 시작 — "
                                    f"그동안 첫 프레임 정지")
                if e_song > float(win[1]) + ls + 0.15:
                    warnings.append(f"{cid}: 립싱크 창 끝 {win[1]:.2f}s 뒤 {e_song - float(win[1]) - ls:.2f}s 는 "
                                    f"레퍼런스가 무음 — 입이 닫힘")
            if source:
                kind = "video"
            else:
                img = find_media(paths.images(ep), cid, IMAGE_EXTS)
                missing.append(f"clips/{cid}.mp4")
                if allow_missing and img:
                    source, kind = img, "image"
        else:
            source = find_media(paths.images(ep), cid, IMAGE_EXTS)
            if source:
                kind = "image"
            else:
                missing.append(f"images/{cid}.png")
        if kind == "video" and source is not None:
            src_len = probe_duration(source)
            if src_off:
                if src_off >= src_len - 0.05:
                    raise MomoError(f"{cid}: 클립 시작 위치 {src_off:.2f}s (clip_from.at / clip_at / 립싱크 창) 가 "
                                    f"클립 길이 {src_len:.2f}s 이상")
                src_len -= src_off

        # ---- 음성
        speech = [it for it in items if it.kind == "speech"]
        files: list[Path | None] = []
        durs: list[float] = []
        estimated = False
        if t == "L" and c.get("library_audio"):
            if len(speech) != 1:
                raise MomoError(f"{cid}: 라이브러리 고정 음성 컷은 문장 1개여야 함")
            f = find_media(paths.library_audio(lang), c["library_audio"], AUDIO_EXTS)
            if not f:
                missing.append(f"library/audio/{lang}/{c['library_audio']}.mp3 ({cid})")
            files.append(f)
        else:
            for it in speech:
                f = find_media(paths.audio(ep, lang), f"{cid}_{it.index}", AUDIO_EXTS)
                if f is None and len(speech) == 1:
                    f = find_media(paths.audio(ep, lang), cid, AUDIO_EXTS)
                if f is None:
                    missing.append(f"audio/{lang}/{cid}_{it.index}.mp3")
                files.append(f)
        for it, f in zip(speech, files):
            if f is not None:
                durs.append(speech_length(f) if song else probe_duration(f))
            else:
                durs.append(estimate_speech(it.text, lang))
                estimated = True
        nar_len = sum(durs) + sum(it.seconds for it in items if it.kind == "pause")

        # ---- 전환
        if i == 0 or song:  # songs cut on the bar line (a crossfade would shift the beat grid)
            xf = 0.0
        else:
            tr = c.get("transition") or ("fade" if scene != prev_scene else "cut")
            xf = xfade if tr == "fade" else 0.0
        xf_f = int(round(xf * fps))
        xf = xf_f / fps

        # ---- 길이
        lead = float(c.get("lead") or 0.0)
        tail_c = tail if c.get("tail") is None else float(c["tail"])
        if nar_len > 0:
            base = xf + lead + nar_len + tail_c
        elif kind == "video" and src_len:
            base = src_len
        else:
            base = min_cut
        want = float(c.get("duration") or 0)
        if want and want < base - 1e-6:
            warnings.append(f"{cid}: duration {want}s 가 나레이션보다 짧아 {base:.2f}s 로 늘림")
        dur = max(base, min_cut, want)
        starts: list[float] = []
        tempos: list[float] = []
        if track:  # cut on the finished song's bar lines; lyrics come from the aligned song, not from TTS
            s0, s1 = spans[i]
            start_f, end_f = int(round(s0 * fps)), int(round(s1 * fps))
            dur_f = end_f - start_f
            if dur_f <= 0:
                raise MomoError(f"{cid}: 컷 길이가 0 — bars / song.track.analysis 확인")
            nar_off = xf + lead
            if speech:  # L cut with the library line spoken over the song
                starts, tempos = [nar_off], [1.0]
        elif song:
            bars = c.get("bars")
            if not isinstance(bars, int) or bars < 1:
                bars = max(1, math.ceil((nar_len + tail_c) / bar - 1e-6))
                warnings.append(f"{cid}: song 컷에 bars 없음 → {bars}마디로 계산")
            dur = bars * bar
            starts, tempos, sw = place_song_lines(c, items, durs, song, dur)
            warnings += sw
            nar_len = max((s + d / k for s, d, k in zip(starts, durs, tempos)), default=0.0)
            start_f = int(round(song_bars * bar * fps))
            song_bars += bars
            dur_f = int(round(song_bars * bar * fps)) - start_f
        else:
            dur_f = int(math.ceil(dur * fps - 1e-6))
            if i > 0:
                start_f = start_f + prev_dur_f - xf_f

        nar_offset = starts[0] if starts else xf + lead
        if c.get("lipsync") and not track:  # narration lip-sync: frame 0 holds until the narration starts
            hold0 = nar_offset
        kw = "" if song else (((c.get("keyword") or {}).get(lang)) or "").strip()  # songs show the lyrics instead
        lyrics = []
        if track:
            lyrics = track_cut_lyrics(tlines, t_start, start_f / fps, dur_f / fps)
            if speech:  # the library line (intro/outro) is captioned too
                lyrics = [(speech[0].text, starts[0], durs[0], dur_f / fps, None)] + lyrics
                nar_len = starts[0] + durs[0]
            else:
                nar_len = 0.0
        elif song:
            texts = [it.text for it in speech]
            ends = starts[1:] + [dur_f / fps]
            lyrics = [(tx, s, d / k, e, None) for tx, s, d, k, e in zip(texts, starts, durs, tempos, ends)]
        text_at = c.get("text_at")
        text_at = float(r["text_delay"]) if text_at is None else float(text_at)
        text_at = max(0.0, min(text_at, dur_f / fps - 0.5))
        inset = c.get("inset")
        sfx, sw = _resolve_sfx(paths, c)
        warnings += sw

        plans.append(CutPlan(
            index=i, id=cid, type=t, scene=scene, cut=c, items=items, speech_files=files,
            speech_durs=durs, nar_len=nar_len, nar_offset=nar_offset, xf_in=xf,
            dur=dur_f / fps,
            start=start_f / fps, source=source, source_kind=kind, source_len=src_len, keyword=kw,
            text_at=text_at, text_pos=c.get("text_pos") or "top", text_color=c.get("text_color") or "white",
            inset=None if inset is None else float(inset), sfx=sfx, estimated_audio=estimated,
            block_starts=[] if track else starts, block_tempos=[] if track else tempos,
            block_lens=[] if track else [d / k for d, k in zip(durs, tempos)], lyrics=lyrics,
            card=c.get("card") if isinstance(c.get("card"), dict) else None, src_offset=src_off, hold0=hold0,
            lip_shift=ls, lip_locked=locked))
        prev_dur_f = dur_f
        prev_scene = scene

    if missing:
        msg = "없는 파일 {}개:\n  - ".format(len(missing)) + "\n  - ".join(missing)
        if not allow_missing:
            raise MomoError(msg + "\n(애니매틱 미리보기는 --allow-missing)")
        warnings.append(msg)
    total = plans[-1].start + plans[-1].dur if plans else 0.0
    return plans, total, warnings
