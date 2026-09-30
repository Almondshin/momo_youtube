#!/usr/bin/env python3
"""Higgsfield MCP 생성 작업의 계획·기록·진행표 (5단계 — 중단돼도 이어서 할 수 있게).

Claude 는 plan 이 주는 {"tool", "params"} 를 MCP 도구에 그대로 넘기고, 끝나면 각 항목의 "record"
명령(<JOB_ID>, <URL> 채워서)으로 결과를 남긴다. 기록은 manifest.json / library.json 뿐이라
세션이 끊겨도 status 로 어디까지 했는지 보고 재개한다.

사용 예
  python hf_jobs.py plan --ep ep02 --kind image                  # 다음 묶음 (최대 max_parallel_images 장)
  python hf_jobs.py plan --ep ep02 --kind image --cuts c02,c03,c04
  python hf_jobs.py plan --ep ep02 --kind clip --all             # 이미지가 승인된 V 컷 전부
  python hf_jobs.py plan --ep ep02 --kind audio --lang en
  python hf_jobs.py plan --library [--kind sheet|image|clip|audio] [--ep ep02]
  python hf_jobs.py voice-samples --lang en --voices v1,v2,v3 [--text "..."]
  python hf_jobs.py record --ep ep02 --cut c03 --kind image --job-id J --url U --status generated
  python hf_jobs.py record --ep ep02 --cut c03 --kind image --status approved
  python hf_jobs.py record --ep ep02 --cut c03 --kind image --status rejected --reason "단추가 안 보임"
  python hf_jobs.py record --ep ep02 --cut c03 --kind audio --lang en --block 1 --job-id J --url U --status generated
  python hf_jobs.py record --library intro_wave --kind image --job-id J --url U --status generated --ep ep02
  python hf_jobs.py record --library intro --kind audio --lang en ...
  python hf_jobs.py record --sheet momo ...
  python hf_jobs.py record --voice-sample v1 --lang en --status approved    # config.voices.en 에 고정
  python hf_jobs.py narref --ep ep02 --cut c13 --lang en --media-id M     # 여러 블록 립싱크 컷
  python hf_jobs.py status --ep ep02 [--library] [--json]

- 크레딧 기본값은 config.higgsfield.unit_costs (이미지 2, 영상 해상도별, 음성 블록 0.2), --credits 로 덮어쓴다.
- 라이브러리 항목을 --ep 와 함께 기록하면 그 에피소드 크레딧에 합산한다 (첫 편 예산에 라이브러리 포함).
- 승인된 항목(특히 라이브러리)은 plan 에 나오지 않고, 새 결과로 덮으려면 record --force 가 필요하다.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import (LIBRARY_AUDIO, LIBRARY_CLIPS, MOMO_DIR, MomoError, Paths,  # noqa: E402
                            active_langs, add_root_arg, check_ep, check_lang, find_media, get_paths, load_config, load_json,
                            load_library, load_manifest, main_wrapper, save_json)
from momolib.episode import compose_image_prompt, compose_motion_prompt, tts_blocks  # noqa: E402
from momolib.genrec import (KIND_EXTS, NA, SYMBOL, Slot, add_credits, apply_record, char_tags,  # noqa: E402
                            characters_used, clip_cost, clip_seconds, cut_slots, element_prefix, episode_cap,
                            episode_slots,
                            estimate, library_slots, needs_generation, now_iso, status_of, stop_message,
                            unit_cost)

AUDIO_BATCH = 12  # generate_audio_batch 최대 / "12개 이상 동시 요청 금지"
SAMPLE_TEXT = {"en": "Hi friends! It's Momo! Can you say hello? Hello! Great job!",
               "ko": "안녕, 친구들! 나는 모모야! 같이 말해볼까? 안녕! 잘했어!"}
SHEET_PROMPT = ("Character turnaround model sheet of {tag}: front view, three-quarter view, side view and back view "
                "in one row, plus four facial expressions (happy, surprised, curious, sleepy) in a second row, "
                "plain pure white background, even spacing, full body, consistent proportions")
LIB_KIND = {"sheet": "sheet", "lib_image": "image", "lib_clip": "clip", "lib_audio": "audio"}


# ---------------------------------------------------------------- MCP params

def _folder(cfg: dict, p: dict) -> dict:
    if cfg["higgsfield"].get("folder_id"):
        p["folder_id"] = cfg["higgsfield"]["folder_id"]
    return p


def image_params(cfg: dict, prompt: str, prefix: str = "") -> dict:
    hf = cfg["higgsfield"]
    return _folder(cfg, {"model": hf["image_model"], "prompt": prefix + prompt,
                         "aspect_ratio": hf.get("aspect_ratio") or "16:9", "resolution": hf["image_resolution"]})


def clip_params(cfg: dict, prompt: str, start_job: str, cut: dict | None = None, lang: str | None = None,
                end_job: str | None = None, audio_job: str | None = None) -> dict:
    """Video payload. cut.clip_model picks another model (its fixed extras come from higgsfield.clip_models);
    end_job chains the clip into the next cut's frame, audio_job drives lip-sync (audio_references)."""
    hf = cfg["higgsfield"]
    model = (cut or {}).get("clip_model") or hf["video_model"]
    p = {"model": model, "prompt": prompt, "aspect_ratio": hf.get("aspect_ratio") or "16:9",
         "duration": clip_seconds(cfg, cut, lang)}
    extras = (hf.get("clip_models") or {}).get(model)
    p.update(extras if extras is not None else {"resolution": hf["video_resolution"]})
    medias = [{"role": "start_image", "value": start_job}]
    if end_job:
        medias.append({"role": "end_image", "value": end_job})
    if audio_job:
        medias.append({"role": "audio_references", "value": audio_job})
    p["medias"] = medias
    return _folder(cfg, p)


def audio_params(cfg: dict, text: str, lang: str, voice: str | None = None) -> dict:
    hf = cfg["higgsfield"]
    voice = voice or (cfg.get("voices") or {}).get(lang)
    if not voice:
        raise MomoError(f"config.voices.{lang} 가 아직 없음 — 먼저 음성 샘플을 만들고 승인받을 것:\n"
                        f"  list_voices 로 후보 3개 → python hf_jobs.py voice-samples --lang {lang} --voices a,b,c\n"
                        f"  → 승인한 것을 record --voice-sample <id> --lang {lang} --status approved (config 에 고정)")
    p = {"model": hf["audio_model"], "prompt": text, "voice_type": hf.get("voice_type") or "preset", "voice_id": voice}
    p.update(hf.get("audio_params") or {})  # 예: {"speech_rate": -10} (느린 톤)
    return _folder(cfg, p)


def record_hint(paths: Paths, target: list[str]) -> str:
    script = Path(__file__).resolve()
    try:
        script_s = str(script.relative_to(Path.cwd()))
    except ValueError:
        script_s = str(script)
    cmd = ["python3", script_s, "record"] + (["--root", str(paths.root)] if paths.root != MOMO_DIR else []) + target
    return shlex.join(cmd) + " --job-id <JOB_ID> --url '<URL>' --status generated"


def make_item(slot: Slot, tool: str, params: dict, hint: str) -> dict:
    rec = slot.rec
    item = {"key": slot.key, "cut": slot.cut["id"] if slot.cut else None, "name": slot.name or None,
            "kind": slot.kind, "lang": slot.lang, "block": slot.block, "status": slot.status,
            "attempts": int(rec.get("attempts") or 0), "tool": tool, "params": params, "record": hint}
    return {k: v for k, v in item.items() if v is not None}


def credit_check(paths: Paths, cfg: dict, manifest: dict | None, lib: dict) -> dict | None:
    if manifest is None:
        return None
    est = estimate(paths, cfg, manifest, lib)
    out = {"spent": est["spent"], "cap": est["cap"], "projected": est["total"]}
    if est["over_cap"]:
        out["stop"] = stop_message(est["total"], est["cap"])
    return out


# ---------------------------------------------------------------- plan

def plan_episode(paths: Paths, cfg: dict, args) -> dict:
    ep = check_ep(args.ep)
    if not args.kind or args.kind == "sheet":
        raise MomoError("에피소드 plan 은 --kind image|clip|audio 가 필요함 (시트는 --library)")
    m = load_manifest(paths, ep)
    ids = {c.get("id") for c in m.get("cuts") or []}
    want = [c.strip() for c in (args.cuts or "").split(",") if c.strip()]
    unknown = [c for c in want if c not in ids]
    if unknown:
        raise MomoError(f"manifest 에 없는 컷: {unknown}")
    lang = check_lang(args.lang) if args.lang else None
    items, review, blocked = [], [], []
    slots = [s for s in episode_slots(paths, cfg, m) if s.kind == args.kind
             and (not want or s.cut["id"] in want) and (lang is None or s.lang in (None, lang))]
    for cid in want:
        if not any(s.cut["id"] == cid for s in slots):
            blocked.append(f"{cid}: {args.kind} 대상 아님 (타입 {next(c['type'] for c in m['cuts'] if c['id'] == cid)})")
    for s in slots:
        if s.status == "approved":
            continue
        if s.status == "generated":
            review.append(s.key)
            continue
        cid = s.cut["id"]
        target = ["--ep", ep, "--cut", cid, "--kind", s.kind]
        if s.kind == "image":
            tool, params = "generate_image", image_params(cfg, compose_image_prompt(cfg, s.cut),
                                                          element_prefix(cfg, s.cut))
        elif s.kind == "clip":
            img = (s.cut.get("gen") or {}).get("image") or {}
            if status_of(img) != "approved" or not img.get("job_id"):
                blocked.append(f"{s.key}: 이미지 승인 전 ({status_of(img)}) — text-to-video 금지, 승인된 이미지로만")
                continue
            end_job, audio_job, why = clip_links(cfg, m, s)
            if why:
                blocked.append(f"{s.key}: {why}")
                continue
            tool, params = "generate_video", clip_params(cfg, compose_motion_prompt(cfg, s.cut), img["job_id"],
                                                         s.cut, s.lang, end_job, audio_job)
            if s.lang:
                target += ["--lang", s.lang]
        else:
            tool, params = "generate_audio", audio_params(cfg, s.text, s.lang)
            target += ["--lang", s.lang, "--block", str(s.block)]
        items.append(make_item(s, tool, params, record_hint(paths, target)))
    limit = AUDIO_BATCH if args.kind == "audio" else int(cfg["higgsfield"].get("max_parallel_images") or 4)
    notes = []
    if args.kind == "image":
        notes.append("이미지는 한 번에 3~4장씩만 병렬, 12장 이상 동시 요청 금지. 처음이면 1번 컷 1장 → 씬 1 의 3장 "
                     "순서로 보여주고 승인받을 것")
    if args.kind == "clip":
        notes.append("승인된 이미지를 start_image 로만 (text-to-video 금지). 결과 클립은 형태 변형·의상 변화·귀 개수 확인")
    if args.kind == "audio":
        notes.append("[pause] 마커는 보내지 않는다 (이미 블록으로 나뉨). KO 발음·억양이 부족하면 멈추고 알릴 것")
    notes.append("결과 확인 후: 같은 record 명령에 --status approved | rejected --reason \"...\" (job 이 같으면 크레딧 재계산 없음)")
    shown = items if args.all else items[:limit]
    return {"ep": ep, "kind": args.kind, "remaining": len(items), "count": len(shown),
            "batch_limit": None if args.all else limit, "items": shown,
            "awaiting_review": review, "blocked": blocked, "notes": notes,
            "credits": credit_check(paths, cfg, m, load_library(paths))}


def clip_links(cfg: dict, m: dict, s: Slot) -> tuple[str | None, str | None, str | None]:
    """(end_image job, audio_references job, reason it is blocked) for an episode clip slot.

    cut.end_frame = "c11" → that cut's approved image is the end frame (continuous hand-off).
    Lip-sync clips use the language's approved narration as audio_references: the block's own job for one
    block, else cut.nar_ref.<lang> (all blocks + [pause] silences in one file, imported — see cmd_narref).
    """
    end_job = None
    ef = s.cut.get("end_frame")
    if ef:
        other = next((c for c in m.get("cuts") or [] if c.get("id") == ef), None)
        img = ((other or {}).get("gen") or {}).get("image") or {}
        if status_of(img) != "approved" or not img.get("job_id"):
            return None, None, f"end_frame {ef} 이미지가 승인 전"
        end_job = img["job_id"]
    if not s.lang:
        return end_job, None, None
    jobs = nar_jobs(cfg, s.cut, s.lang)
    if not jobs:
        return None, None, f"{s.lang} 나레이션 승인 전 — 립싱크는 승인된 음성으로만"
    if len(jobs) == 1:
        return end_job, jobs[0], None
    ref = (s.cut.get("nar_ref") or {}).get(s.lang) or {}
    if not ref.get("media_id") or ref.get("blocks") != jobs:
        return None, None, (f"{s.lang} 음성 블록 {len(jobs)}개 — 합친 나레이션 필요: momo-previews 의 "
                            f"{s.cut['id']}_nar_{s.lang}.wav → media_import_url → hf_jobs.py narref")
    return end_job, ref["media_id"], None


def nar_jobs(cfg: dict, cut: dict, lang: str) -> list[str]:
    """Approved narration block jobs in block order ([] unless every speech block is approved)."""
    blocks = (cut.get("audio_src") or {}).get(lang) or {}
    recs = [blocks.get(str(it.index)) or {} for it in tts_blocks(cut, lang, cfg)]
    if not recs or any(status_of(r) != "approved" or not r.get("job_id") for r in recs):
        return []
    return [r["job_id"] for r in recs]


def sheet_prompt(cfg: dict, name: str, entry: dict) -> str:
    if entry.get("prompt_full"):
        return entry["prompt_full"]
    tag = "[Momo]" if name == "momo" else next((t for t, k in char_tags(cfg).items() if k == name), None)
    raw = entry.get("prompt") or SHEET_PROMPT.format(tag=tag or cfg["character"].get(name) or "")
    if not (tag or entry.get("prompt") or cfg["character"].get(name)):
        raise MomoError(f"시트 {name}: prompt 도 config.character.{name} 블록도 없음")
    return compose_image_prompt(cfg, {"image_prompt": raw, "momo": entry.get("momo", name == "momo")})


def plan_library(paths: Paths, cfg: dict, args) -> dict:
    lib = load_library(paths)
    m = load_manifest(paths, check_ep(args.ep)) if args.ep else None
    used = characters_used(cfg, m) if m else None
    for k in used or []:  # 이 편에 처음 나오는 조연은 시트부터 (기록은 record --sheet 가 만든다)
        if cfg["character"].get(k) and k not in lib.setdefault("character_sheets", {}):
            lib["character_sheets"][k] = {"file": f"sheets/{k}.png", "momo": k == "momo"}
    lang = check_lang(args.lang) if args.lang else None
    items, review, blocked, done = [], [], [], []
    for s in library_slots(paths, cfg, lib):
        kind = LIB_KIND.get(s.group)
        if kind is None or (args.kind and kind != args.kind) or (lang and s.lang and s.lang != lang):
            continue
        if kind == "sheet" and used is not None and s.name not in used:
            continue
        if s.status == "approved":
            done.append(s.key)  # 라이브러리는 한 번 승인되면 재생성 금지
            continue
        if s.status == "generated":
            review.append(s.key)
            continue
        e = s.holder
        if kind == "sheet":
            target = ["--sheet", s.name]
            tool, params = "generate_image", image_params(cfg, sheet_prompt(cfg, s.name, e))
        elif kind == "image":
            if not e.get("image_prompt"):
                blocked.append(f"{s.key}: library.json 에 image_prompt 없음")
                continue
            pseudo = {"image_prompt": e["image_prompt"], "momo": e.get("momo", True)}
            target = ["--library", s.name, "--kind", "image"]
            tool, params = "generate_image", image_params(cfg, compose_image_prompt(cfg, pseudo),
                                                          element_prefix(cfg, pseudo))
        elif kind == "clip":
            img = e.get("image") or {}
            if status_of(img) != "approved" or not img.get("job_id") or not e.get("motion"):
                blocked.append(f"{s.key}: " + (f"시작 이미지 승인 전 ({status_of(img)})" if e.get("motion")
                                               else "library.json 에 motion 없음"))
                continue
            target = ["--library", s.name, "--kind", "clip"]
            tool, params = "generate_video", clip_params(cfg, compose_motion_prompt(cfg, {"motion": e.get("motion")}),
                                                         img["job_id"])
        else:
            if not (cfg.get("voices") or {}).get(s.lang) and args.kind != "audio":
                blocked.append(f"{s.key}: config.voices.{s.lang} 미설정 — voice-samples 먼저")
                continue
            target = ["--library", s.name, "--kind", "audio", "--lang", s.lang]
            tool, params = "generate_audio", audio_params(cfg, s.text, s.lang)
        if m:
            target += ["--ep", m["ep"]]
        items.append(make_item(s, tool, params, record_hint(paths, target)))
    notes = ["라이브러리는 첫 편에서 한 번만 만든다. 승인된 항목은 다시 만들지 않는다 (plan 에서 제외)."]
    if not m:
        notes.append("--ep 를 주면 record 명령에 --ep 가 붙어 그 에피소드 크레딧에 합산된다")
    return {"library": True, "kind": args.kind, "count": len(items), "items": items, "awaiting_review": review,
            "blocked": blocked, "approved": done, "notes": notes, "credits": credit_check(paths, cfg, m, lib)}


def cmd_plan(paths: Paths, cfg: dict, args) -> int:
    if not args.library and not args.ep:
        raise MomoError("plan 에는 --ep 또는 --library 가 필요함")
    out = plan_library(paths, cfg, args) if args.library else plan_episode(paths, cfg, args)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    stop = (out.get("credits") or {}).get("stop")
    if stop and not args.allow_over_cap:
        print(f"\n✖ {stop}\n  (사용자가 캡 초과를 승인했으면 --allow-over-cap)", file=sys.stderr)
        return 2
    return 0


# ---------------------------------------------------------------- voice-samples

def find_voice_entry(lib: dict, lang: str, voice: str) -> dict | None:
    return next((e for e in reversed(lib.get("voice_samples") or [])
                 if e.get("lang") == lang and str(e.get("voice_id")) == voice), None)


def cmd_voice_samples(paths: Paths, cfg: dict, args) -> int:
    lang = check_lang(args.lang)
    voices = list(dict.fromkeys(v.strip() for v in (args.voices or "").split(",") if v.strip()))
    if not voices:
        raise MomoError("--voices 에 list_voices 로 고른 후보 id 를 쉼표로 (보통 3개)")
    fixed = (cfg.get("voices") or {}).get(lang)
    if fixed and not args.force:
        raise MomoError(f"config.voices.{lang} = {fixed!r} 로 이미 고정됨 — 이후 에피소드에서 바꾸지 말 것 "
                        f"(정말 바꾸려면 --force)")
    text = (args.text or SAMPLE_TEXT[lang]).strip()
    lib = load_library(paths)
    samples = lib.setdefault("voice_samples", [])
    items = []
    for v in voices:
        e = find_voice_entry(lib, lang, v)
        if e is None or (e.get("text") != text and status_of(e) == "pending"):
            if e is None:
                e = {"lang": lang, "voice_id": v, "name": v}
                samples.append(e)
            e["text"] = text
            e.setdefault("status", "pending")
        slot = Slot(f"voice sample {lang} {v}", "audio", "voice", e, (), paths.library_audio(lang), v, lang=lang,
                    text=text, name=v)
        if status_of(e) in ("generated", "approved"):
            continue
        target = ["--voice-sample", v, "--lang", lang] + (["--ep", check_ep(args.ep)] if args.ep else [])
        items.append(make_item(slot, "generate_audio", audio_params(cfg, text, lang, voice=v),
                               record_hint(paths, target)))
    save_json(paths.library_json, lib)
    notes = ["같은 문장으로 후보마다 1블록씩. 톤: 따뜻하고 약간 높은 음, 느린 속도, 문장 끝을 올리는 말투",
             f"승인한 후보: record --voice-sample <id> --lang {lang} --status approved → config.voices.{lang} 에 고정"]
    if len(voices) != 3:
        notes.append(f"지시서는 후보 3개 — 지금 {len(voices)}개")
    print(json.dumps({"lang": lang, "text": text, "count": len(items), "items": items, "notes": notes},
                     ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------- record

def cut_slot(paths: Paths, cfg: dict, m: dict, args) -> Slot:
    cut = next((c for c in m.get("cuts") or [] if c.get("id") == args.cut), None)
    if cut is None:
        raise MomoError(f"manifest 에 없는 컷: {args.cut!r} (있는 컷: {', '.join(c.get('id', '?') for c in m['cuts'])})")
    kind, t, cid = args.kind, cut.get("type"), cut["id"]
    if not kind:
        raise MomoError("--kind image|clip|audio 필요")
    if kind == "image" and t not in ("V", "S"):
        raise MomoError(f"{cid} 는 {t} 컷 — image 는 V/S 컷만 (L 은 라이브러리 클립)")
    if kind == "clip" and t != "V":
        raise MomoError(f"{cid} 는 {t} 컷 — clip 은 V 컷만")
    lang, block = None, None
    if kind == "clip" and cut.get("lipsync"):
        if not args.lang:
            raise MomoError(f"{cid} 는 lipsync 컷 — clip 은 언어별: --lang en|ko 필요")
        lang = check_lang(args.lang)
    if kind == "audio":
        if not args.lang:
            raise MomoError("audio 는 --lang en|ko 필요")
        lang = check_lang(args.lang)
        blocks = [it.index for it in tts_blocks(cut, lang, cfg)]
        if not blocks:
            why = " — 라이브러리 고정 음성 컷 (record --library intro|outro --kind audio)" if cut.get("library_audio") \
                else " — 나레이션 없음"
            raise MomoError(f"{cid} {lang}: 생성할 음성 블록이 없음{why}")
        if args.block is None and len(blocks) > 1:
            raise MomoError(f"{cid} {lang}: 블록이 {len(blocks)}개 — --block 1..{len(blocks)} 필요")
        block = args.block or blocks[0]
        if block not in blocks:
            raise MomoError(f"{cid} {lang}: 블록 {block} 없음 (있는 블록: {blocks})")
    return next(s for s in cut_slots(paths, cfg, m["ep"], cut) if s.kind == kind and s.lang == lang
                and s.block == block)


def library_slot(paths: Paths, cfg: dict, lib: dict, args) -> Slot:
    if args.sheet:
        if args.kind not in (None, "image"):
            raise MomoError("--sheet 은 image 만")
        sheets = lib.setdefault("character_sheets", {})
        if args.sheet not in sheets:
            if args.sheet in ("tags", "rules") or not cfg["character"].get(args.sheet):
                raise MomoError(f"모르는 캐릭터 시트: {args.sheet!r} (config.character 에 블록이 있어야 함)")
            sheets[args.sheet] = {"file": f"sheets/{args.sheet}.png", "momo": args.sheet == "momo"}
        group, name, lang = "sheet", args.sheet, None
    elif args.voice_sample:
        if not args.lang:
            raise MomoError("--voice-sample 은 --lang 필요")
        lang, name, group = check_lang(args.lang), args.voice_sample, "voice"
        if find_voice_entry(lib, lang, name) is None:
            lib.setdefault("voice_samples", []).append(
                {"lang": lang, "voice_id": name, "name": name, "text": args.text or SAMPLE_TEXT[lang]})
    else:
        name = args.library
        if args.kind in ("image", "clip"):
            if name not in (lib.get("clips") or {}) and name not in LIBRARY_CLIPS:
                raise MomoError(f"라이브러리 클립 이름이 아님: {name!r} ({', '.join(LIBRARY_CLIPS)})")
            group, lang = ("lib_image" if args.kind == "image" else "lib_clip"), None
        elif args.kind == "audio":
            if name not in LIBRARY_AUDIO:
                raise MomoError(f"라이브러리 음성은 {LIBRARY_AUDIO} 중 하나: {name!r}")
            if not args.lang:
                raise MomoError("라이브러리 audio 는 --lang 필요")
            group, lang = "lib_audio", check_lang(args.lang)
        else:
            raise MomoError("--library 는 --kind image|clip|audio 필요")
    for s in reversed(library_slots(paths, cfg, lib)):
        if s.group == group and s.name == name and (lang is None or s.lang == lang):
            return s
    raise MomoError(f"라이브러리 항목을 찾지 못함: {group} {name}")


def fix_voice(paths: Paths, lang: str, voice: str, force: bool) -> str:
    raw = load_json(paths.config, default={}) if paths.config.exists() else {}
    cur = (raw.get("voices") or {}).get(lang)
    if cur and cur != voice and not force:
        raise MomoError(f"config.voices.{lang} 이 이미 {cur!r} — 이후 에피소드에서 바꾸지 말 것 (정말 바꾸려면 --force)")
    raw.setdefault("voices", {})[lang] = voice
    save_json(paths.config, raw)
    return f"config.voices.{lang} = {voice!r} 고정"


def cmd_record(paths: Paths, cfg: dict, args) -> int:
    targets = [x for x in (args.cut, args.library, args.sheet, args.voice_sample) if x]
    if len(targets) != 1:
        raise MomoError("대상은 --cut / --library / --sheet / --voice-sample 중 하나")
    m = load_manifest(paths, check_ep(args.ep)) if args.ep else None
    lib = None
    if args.cut:
        if m is None:
            raise MomoError("--cut 에는 --ep 필요")
        slot = cut_slot(paths, cfg, m, args)
    else:
        lib = load_library(paths)
        slot = library_slot(paths, cfg, lib, args)
    if args.credits is not None:
        cost = float(args.credits)
    elif slot.kind == "clip" and slot.cut is not None:
        cost = clip_cost(cfg, slot.cut, slot.lang)
    else:
        cost = unit_cost(cfg, slot.kind)
    extra = None
    if slot.kind == "clip":
        img = (slot.cut.get("gen") or {}).get("image") if slot.cut else slot.holder.get("image")
        extra = {"start_image": (img or {}).get("job_id")}
    prev = slot.status
    rec = slot.ensure()
    delta, msg = apply_record(rec, args.status, job_id=args.job_id, url=args.url, reason=args.reason, cost=cost,
                              force=args.force, extra=extra)
    lines = [f"✔ {slot.key}: {prev} → {rec['status']}" + (f" ({msg})" if msg else "")]
    if slot.group == "voice" and args.status == "approved":
        lines.append("  " + fix_voice(paths, slot.lang, slot.name, args.force))
    if slot.kind == "image" and slot.cut and slot.cut.get("type") == "V" and delta["generations"]:
        clip = (slot.cut.get("gen") or {}).get("clip")
        if clip and status_of(clip) != "pending":
            lines.append(f"  △ {slot.cut['id']} 클립은 이전 이미지로 만든 것 — 새 이미지 승인 후 클립도 다시 생성")
    if lib is not None:
        save_json(paths.library_json, lib)
    if m is not None:
        cr = add_credits(m, delta)
        if m.get("status") in (None, "planning"):
            m["status"] = "producing"
        save_json(paths.manifest(m["ep"]), m)
        cap = episode_cap(cfg, m)
        lines.append(f"  {m['ep']} 크레딧: 사용 {cr['spent']:g} / 캡 {cap:g} "
                     f"(생성 {cr['generations']}회, 재생성 {cr['regenerations']}회)")
        if cr["spent"] > cap:
            lines.append(f"✖ {stop_message(cr['spent'], cap)}")
    elif delta["generations"]:
        lines.append(f"  (라이브러리 {cost:g} 크레딧 — --ep 를 주면 그 에피소드 크레딧에 합산)")
    print("\n".join(lines))
    return 0


# ---------------------------------------------------------------- status

def local_file(slot: Slot) -> Path | None:
    return find_media(slot.dest, slot.stem, KIND_EXTS[slot.kind])


def episode_status(paths: Paths, cfg: dict, m: dict, lib: dict) -> dict:
    ep = m["ep"]
    lclips = lib.get("clips") or {}
    laudio = lib.get("audio") or {}
    rows, slots = [], []
    for c in m.get("cuts") or []:
        cs = cut_slots(paths, cfg, ep, c)
        slots += cs
        by = {(s.kind, s.lang): [] for s in cs}
        for s in cs:
            by[(s.kind, s.lang)].append(s)
        t = c.get("type")
        row = {"id": c.get("id"), "type": t, "scene": c.get("scene")}
        row["image"] = by[("image", None)][0].status if ("image", None) in by else "n/a"
        if t == "L":
            row["clip"] = "library:" + status_of(lclips.get(c.get("library_clip")))
        else:
            clips = [x for x in cs if x.kind == "clip"]
            order = ("pending", "rejected", "generated", "approved")  # show the least-done language
            row["clip"] = min((x.status for x in clips), key=order.index) if clips else "n/a"
        row["audio"] = {}
        for lang in active_langs(cfg):
            if t == "L" and c.get("library_audio"):
                row["audio"][lang] = ["library:" + status_of((laudio.get(lang) or {}).get(c["library_audio"]))]
            else:
                row["audio"][lang] = [s.status for s in by.get(("audio", lang), [])]
        rows.append(row)

    def ids(pred) -> list[str]:
        return [s.key for s in slots if pred(s)]

    review = ids(lambda s: s.status == "generated")
    img_todo = ids(lambda s: s.kind == "image" and needs_generation(s.rec))
    clip_ready = ids(lambda s: s.kind == "clip" and needs_generation(s.rec)
                     and status_of((s.cut.get("gen") or {}).get("image")) == "approved")
    clip_wait = ids(lambda s: s.kind == "clip" and needs_generation(s.rec)
                    and status_of((s.cut.get("gen") or {}).get("image")) != "approved")
    audio_todo = {lang: len(ids(lambda s: s.kind == "audio" and s.lang == lang and needs_generation(s.rec)))
                  for lang in active_langs(cfg)}
    to_fetch = ids(lambda s: s.status in ("generated", "approved") and s.rec.get("url") and not local_file(s))
    lib_left = [s.key for s in library_slots(paths, cfg, lib) if s.group in ("lib_image", "lib_clip", "lib_audio")
                and s.status != "approved" and not (s.group == "lib_image" and status_of(s.holder) == "approved")]
    lib_left += [f"sheet {k}" for k in characters_used(cfg, m)
                 if status_of((lib.get("character_sheets") or {}).get(k)) != "approved"]

    nxt = []
    if review:
        nxt.append(f"검토 대기 {len(review)}개 (●): {', '.join(review)} → 보여주고 record --status approved|rejected")
    if lib_left:
        nxt.append(f"라이브러리 미완성 {len(lib_left)}개 → hf_jobs.py plan --library --ep {ep}")
    if img_todo:
        nxt.append(f"이미지 생성 {len(img_todo)}장: {', '.join(k.split()[0] for k in img_todo)} "
                   f"→ hf_jobs.py plan --ep {ep} --kind image")
    if clip_ready:
        nxt.append(f"클립 생성 가능 {len(clip_ready)}개 (이미지 승인됨): {', '.join(k.split()[0] for k in clip_ready)} "
                   f"→ hf_jobs.py plan --ep {ep} --kind clip")
    if clip_wait:
        nxt.append(f"클립 대기 {len(clip_wait)}개 (이미지 승인 전): {', '.join(k.split()[0] for k in clip_wait)}")
    for lang in active_langs(cfg):
        if audio_todo[lang]:
            v = (cfg.get("voices") or {}).get(lang)
            nxt.append(f"음성 {lang.upper()} {audio_todo[lang]}블록 → hf_jobs.py plan --ep {ep} --kind audio --lang {lang}"
                       + ("" if v else f" (config.voices.{lang} 미설정 — voice-samples 먼저)"))
    if to_fetch:
        nxt.append(f"내려받기 필요 {len(to_fetch)}개 → fetch_assets.py --ep {ep} --library")
    if not nxt:
        nxt.append(f"생성 모두 완료 → fetch_assets.py --ep {ep} --library → build.py --ep {ep} --lang en|ko --check")
    est = estimate(paths, cfg, m, lib)
    cr = m.get("credits") or {}
    credits = {"spent": float(cr.get("spent") or 0), "cap": est["cap"], "generations": int(cr.get("generations") or 0),
               "regenerations": int(cr.get("regenerations") or 0), "projected": est["total"]}
    if est["over_cap"]:
        credits["stop"] = stop_message(est["total"], est["cap"])
    return {"ep": ep, "status": m.get("status"), "cuts": rows, "credits": credits, "next": nxt}


def library_status(cfg: dict, lib: dict) -> dict:
    return {"sheets": {k: status_of(v) for k, v in (lib.get("character_sheets") or {}).items()},
            "clips": {k: {"image": status_of(v.get("image")), "clip": status_of(v)}
                      for k, v in (lib.get("clips") or {}).items()},
            "audio": {lang: {k: status_of(v) for k, v in ((lib.get("audio") or {}).get(lang) or {}).items()}
                      for lang in active_langs(cfg)},
            "voice_samples": [{"lang": e.get("lang"), "voice_id": e.get("voice_id"), "status": status_of(e)}
                              for e in lib.get("voice_samples") or []],
            "voices": {lang: (cfg.get("voices") or {}).get(lang) for lang in active_langs(cfg)}}


def cell(v: str) -> str:
    if v == "n/a":
        return NA
    if v.startswith("library:"):
        return "L" + SYMBOL[v.split(":", 1)[1]]
    return SYMBOL[v]


def pad(s: str, width: int) -> str:
    """한글(전각) 폭을 2 로 세서 맞춘다."""
    w = sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s)
    return s + " " * max(1, width - w)


def print_episode_status(st: dict) -> None:
    print(f"{st['ep']} 생성 현황 (manifest.status: {st['status']})\n")
    langs = list(st["cuts"][0]["audio"]) if st["cuts"] else ["en"]
    head = ["컷", "타입", "이미지", "클립"] + [f"음성 {lang.upper()}" for lang in langs]
    rows = [[r["id"], r["type"], cell(r["image"]), cell(r["clip"])]
            + ["".join(cell(x) for x in r["audio"][lang]) or NA for lang in langs] for r in st["cuts"]]
    widths = [6, 6, 8, 6] + [10] * len(langs)
    for r in [head] + rows:
        print("  " + "".join(pad(str(v), w) for v, w in zip(r, widths)).rstrip())
    print("\n  범례: ✔ 승인 · ● 생성됨(검토 대기) · ✖ 거절 · · 대기 · — 해당 없음 · L=라이브러리")
    cr = st["credits"]
    print(f"\n크레딧: 사용 {cr['spent']:g} / 캡 {cr['cap']:g} (생성 {cr['generations']}회, 재생성 {cr['regenerations']}회)"
          f" · 예상 총액 {cr['projected']:g} (estimate_credits.py)")
    if cr.get("stop"):
        print(f"✖ {cr['stop']}")
    print("\n다음 작업:")
    for i, n in enumerate(st["next"], 1):
        print(f"  {i}. {n}")


def print_library_status(lst: dict) -> None:
    print("\n라이브러리 (library.json)")
    print("  캐릭터 시트: " + " · ".join(f"{k} {SYMBOL[v]}" for k, v in lst["sheets"].items()))
    print("  클립 (이미지/클립): " + " · ".join(f"{k} {SYMBOL[v['image']]}/{SYMBOL[v['clip']]}"
                                         for k, v in lst["clips"].items()))
    print("  고정 음성: " + " | ".join(f"{lang} " + " ".join(f"{k} {SYMBOL[v]}" for k, v in d.items())
                                    for lang, d in lst["audio"].items()))
    vs = lst["voice_samples"]
    print("  음성 샘플: " + (" · ".join(f"{e['lang']} {e['voice_id']} {SYMBOL[e['status']]}" for e in vs) or "없음"))
    print("  config.voices: " + ", ".join(f"{k} {v or '미설정'}" for k, v in lst["voices"].items()))


def cmd_narref(paths: Paths, cfg: dict, args) -> int:
    """Pin the imported combined narration (all blocks + pauses) of a multi-block lip-sync cut.

    The file comes from momo-previews (<ep>/<cut>_nar_<lang>.wav, built by preview_assets.py) and is
    imported with media_import_url. The block jobs are stored with it, so a regenerated block voids it.
    """
    ep, lang = check_ep(args.ep), check_lang(args.lang)
    m = load_manifest(paths, ep)
    cut = next((c for c in m.get("cuts") or [] if c.get("id") == args.cut), None)
    if cut is None:
        raise MomoError(f"manifest 에 없는 컷: {args.cut}")
    if not cut.get("lipsync"):
        raise MomoError(f"{args.cut}: lipsync 컷이 아님")
    jobs = nar_jobs(cfg, cut, lang)
    if len(jobs) < 2:
        raise MomoError(f"{args.cut} {lang}: 승인된 음성 블록 {len(jobs)}개 — 합친 나레이션은 블록 2개 이상 + 전부 승인일 때만")
    cut.setdefault("nar_ref", {})[lang] = {"media_id": args.media_id, "blocks": jobs, "at": now_iso()}
    save_json(paths.manifest(ep), m)
    print(f"✔ {args.cut} nar_ref {lang} = {args.media_id} (블록 {len(jobs)}개)")
    return 0


def cmd_status(paths: Paths, cfg: dict, args) -> int:
    if not args.ep and not args.library:
        raise MomoError("status 에는 --ep 또는 --library 가 필요함")
    lib = load_library(paths)
    out = {}
    if args.ep:
        out["episode"] = episode_status(paths, cfg, load_manifest(paths, check_ep(args.ep)), lib)
    if args.library:
        out["library"] = library_status(cfg, lib)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if "episode" in out:
        print_episode_status(out["episode"])
    if "library" in out:
        print_library_status(out["library"])
    return 0


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Higgsfield MCP 생성 계획·기록·진행표",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def subparser(name: str, help_: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_)
        p.add_argument("--root", default=argparse.SUPPRESS, help="momo 작업 폴더 (앞에 줘도 됨)")
        return p

    p = subparser("plan", "MCP payload 목록 (아직 승인 안 된 항목)")
    p.add_argument("--ep")
    p.add_argument("--library", action="store_true", help="라이브러리 미완성분")
    p.add_argument("--kind", choices=["sheet", "image", "clip", "audio"])
    p.add_argument("--lang")
    p.add_argument("--cuts", help="쉼표 구분 컷 id")
    p.add_argument("--all", action="store_true", help="묶음 제한 없이 전부")
    p.add_argument("--allow-over-cap", action="store_true", help="사용자가 크레딧 캡 초과를 승인했을 때만")

    p = subparser("voice-samples", "음성 후보 샘플 payload (같은 문장, 후보마다 1블록)")
    p.add_argument("--lang", required=True)
    p.add_argument("--voices", required=True, help="list_voices 로 고른 후보 id, 쉼표 구분 (보통 3개)")
    p.add_argument("--text", help="샘플 문장 (기본: 인트로 + 따라 말하기)")
    p.add_argument("--ep", help="record 명령에 붙여 이 에피소드 크레딧에 합산")
    p.add_argument("--force", action="store_true", help="config.voices 가 이미 고정돼 있어도")

    p = subparser("record", "생성 결과 기록")
    p.add_argument("--ep")
    p.add_argument("--cut")
    p.add_argument("--library", metavar="NAME", help="intro_wave … (image|clip) 또는 intro|outro (audio)")
    p.add_argument("--sheet", metavar="NAME")
    p.add_argument("--voice-sample", metavar="VOICE_ID")
    p.add_argument("--kind", choices=["image", "clip", "audio"])
    p.add_argument("--lang")
    p.add_argument("--block", type=int)
    p.add_argument("--job-id")
    p.add_argument("--url")
    p.add_argument("--status", required=True, choices=["generated", "approved", "rejected"])
    p.add_argument("--reason")
    p.add_argument("--credits", type=float, help="이번 생성 크레딧 (기본: unit_costs)")
    p.add_argument("--text", help="voice-sample 문장 (처음 기록할 때)")
    p.add_argument("--force", action="store_true", help="승인된 항목을 새 결과로 덮기 / voices 변경")

    p = subparser("narref", "여러 블록 립싱크 컷의 합친 나레이션 media_id 고정")
    p.add_argument("--ep", required=True)
    p.add_argument("--cut", required=True)
    p.add_argument("--lang", required=True)
    p.add_argument("--media-id", required=True, help="media_import_url 결과")

    p = subparser("status", "컷별 진행표 + 크레딧 + 다음 작업")
    p.add_argument("--ep")
    p.add_argument("--library", action="store_true")
    p.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    paths = get_paths(args)
    cfg = load_config(paths)
    return {"plan": cmd_plan, "voice-samples": cmd_voice_samples, "record": cmd_record,
            "narref": cmd_narref, "status": cmd_status}[args.cmd](paths, cfg, args)


if __name__ == "__main__":
    main_wrapper(main)
