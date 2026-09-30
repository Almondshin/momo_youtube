#!/usr/bin/env python3
"""manifest.json 검사 (+ 4단계 기획표 plan.md 생성).

규칙은 momolib.episode.validate_manifest (컷·타입 개수, 프롬프트 금지어, 모션, 고정 문장, 업로드 메타 …)
+ 생성 기록 점검(나레이션이 바뀌어 남은 음성 기록 등). errors 가 있으면 exit 1 — 제작·조립 진행 금지.

사용 예
  python validate_manifest.py --ep ep02
  python validate_manifest.py --ep ep02 --table     # episodes/ep02/plan.md (4단계 표 + 예상 길이)
  python validate_manifest.py --ep ep02 --strict    # 경고도 실패로
  python validate_manifest.py --ep ep02 --json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import (LANGS, MomoError, Paths, active_langs, add_root_arg, check_ep, get_paths, load_config,  # noqa: E402
                            load_manifest, main_wrapper)
from momolib.episode import (compose_image_prompt, compose_motion_prompt, count_types, plan_timeline,  # noqa: E402
                             tts_blocks, validate_manifest)
from momolib.genrec import STATUSES  # noqa: E402


def record_warnings(cfg: dict, manifest: dict) -> list[str]:
    """생성 기록과 기획이 어긋난 곳 (나레이션·타입을 바꾼 뒤 남은 기록)."""
    W = []
    for c in manifest.get("cuts") or []:
        cid, t = c.get("id", "?"), c.get("type")
        gen = c.get("gen") or {}
        if gen.get("clip") and t != "V":
            W.append(f"{cid}: {t} 컷인데 gen.clip 기록이 있음 (타입을 바꿨으면 무시됨)")
        if gen.get("image") and t not in ("V", "S"):
            W.append(f"{cid}: {t} 컷인데 gen.image 기록이 있음")
        for kind, rec in gen.items():
            if isinstance(rec, dict) and rec.get("status", "pending") not in STATUSES:
                W.append(f"{cid}: gen.{kind}.status 값이 이상함 ({rec.get('status')!r})")
        for lang, recs in (c.get("audio_src") or {}).items():
            if lang not in LANGS or not isinstance(recs, dict):
                continue
            valid = {str(it.index) for it in tts_blocks(c, lang, cfg)}
            extra = sorted(set(recs) - valid, key=lambda k: (len(k), k))
            if extra:
                W.append(f"{cid}: {lang} 음성 기록 블록 {extra} 은 지금 나레이션에 없음 — 나레이션을 바꿨으면 음성 재생성")
    return W


def durations(paths: Paths, cfg: dict, manifest: dict) -> dict:
    """언어별 예상 길이. 음성이 없으면 글자 수 추정 (plan_timeline allow_missing)."""
    out = {}
    for lang in active_langs(cfg):
        try:
            plans, total, _ = plan_timeline(paths, cfg, manifest, lang, allow_missing=True)
        except MomoError as e:
            out[lang] = {"error": str(e)}
            continue
        out[lang] = {"total": round(total, 2), "estimated": any(p.estimated_audio for p in plans),
                     "cuts": {p.id: round(p.dur, 2) for p in plans}}
    return out


def mmss(sec: float) -> str:
    s = int(round(sec))
    return f"{s // 60}:{s % 60:02d}"


def md(text) -> str:
    return str(text or "").replace("|", "\\|").replace("\n", " ").strip()


def render_plan(cfg: dict, m: dict, errors: list[str], warns: list[str], durs: dict) -> str:
    rules = cfg["plan_rules"]
    cuts = m.get("cuts") or []
    counts = count_types(m)
    scenes: dict = {}
    for c in cuts:
        scenes[c.get("scene")] = scenes.get(c.get("scene"), 0) + 1
    topic, title, th = m.get("topic") or {}, m.get("title") or {}, m.get("thumbnail") or {}
    tt = th.get("text") or {}
    head = f"# {m['ep']} 기획표"
    if topic.get("ko") or topic.get("en"):
        head += f" — {topic.get('ko') or ''}" + (f" ({topic['en']})" if topic.get("en") else "")
    L = [head, "",
         f"> validate_manifest.py --table 이 생성 ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC). "
         "직접 고치지 말고 manifest.json 을 고친 뒤 다시 실행.", "",
         f"- 제목 EN: {title.get('en') or '(미정)'}",
         f"- 제목 KO: {title.get('ko') or '(미정)'}",
         f"- 썸네일: {th.get('cut') or '(미지정)'} + 문구 \"{tt.get('en', '')}\" / \"{tt.get('ko', '')}\""
         f" (위치 {th.get('text_pos') or 'top'})",
         f"- 컷 {len(cuts)}개 (목표 {rules['cuts_min']}~{rules['cuts_max']}) · "
         + " · ".join(f"{t} {counts[t]} ({rules[k][0]}~{rules[k][1]})"
                      for t, k in (("V", "v_range"), ("S", "s_range"), ("L", "l_range")))
         + f" · 씬 {len(scenes)} (목표 {rules['scenes']}) — 씬별 " + "/".join(str(n) for n in scenes.values())]
    parts = []
    for lang in active_langs(cfg):
        d = durs.get(lang) or {}
        if "total" in d:
            parts.append(f"{lang.upper()} {mmss(d['total'])} ({d['total']:.1f}초"
                         + (", 음성 추정 포함" if d["estimated"] else ", 실제 음성") + ")")
        else:
            parts.append(f"{lang.upper()} 계산 불가 — {d.get('error', '?').splitlines()[0]}")
    L.append("- 예상 길이: " + " · ".join(parts) + " — 목표 2~3분, build.py 가 실제 음성으로 다시 계산")
    blocks = {lang: sum(len(tts_blocks(c, lang, cfg)) for c in cuts) for lang in active_langs(cfg)}
    L.append(f"- 생성할 것: 이미지 {counts['V'] + counts['S']}장 (V {counts['V']} + S {counts['S']}), "
             f"V 클립 {counts['V']}개, 음성 블록 EN {blocks['en']} · KO {blocks['ko']} (L 컷은 라이브러리)")
    if (m.get("notes") or {}).get("v_over_reason"):
        L.append(f"- V 15개 초과 사유: {m['notes']['v_over_reason']}")
    L += ["", "## 검증", ""]
    L += [f"- ✖ {md(e)}" for e in errors] + [f"- △ {md(w)}" for w in warns]
    if not errors and not warns:
        L.append("- ✔ 문제 없음")
    L += ["", "## 컷 표", "",
          "| 컷 | 씬 | 타입 | 나레이션 EN | 나레이션 KO | 화면 키워드 EN / KO | 이미지 프롬프트 (조립된 전체) "
          "| 모션 지시 (V만) | 예상 길이 EN/KO |",
          "|---|---|---|---|---|---|---|---|---|"]
    for c in cuts:
        t = c.get("type")
        nar = c.get("narration") or {}
        kw = c.get("keyword") or {}
        kw_s = f"{kw.get('en') or '—'} / {kw.get('ko') or '—'}"
        if t == "L":
            prompt = f"(라이브러리 `{c.get('library_clip')}`" + (f" + 고정 음성 `{c['library_audio']}`)"
                                                               if c.get("library_audio") else ")")
        else:
            try:
                prompt = compose_image_prompt(cfg, c)
            except Exception as e:  # noqa: BLE001 — 표는 오류가 있어도 만든다
                prompt = f"(조립 실패: {e})"
        motion = compose_motion_prompt(cfg, c) if t == "V" and c.get("motion") else ""
        dl = "/".join(f"{durs[lang]['cuts'].get(c.get('id'), 0):.1f}" if "cuts" in durs.get(lang, {}) else "?"
                      for lang in active_langs(cfg))
        L.append(f"| {md(c.get('id'))} | {md(c.get('scene'))} | {md(t)} | {md(nar.get('en'))} | {md(nar.get('ko'))} "
                 f"| {md(kw_s)} | {md(prompt)} | {md(motion)} | {dl} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="manifest.json 검사 (+ plan.md)",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    ap.add_argument("--ep", required=True)
    ap.add_argument("--table", action="store_true", help="episodes/<ep>/plan.md 작성")
    ap.add_argument("--strict", action="store_true", help="경고도 실패로 (exit 1)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    cfg = load_config(paths)
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    errors, warns = validate_manifest(cfg, m)
    if m.get("ep") != ep:
        errors.insert(0, f"manifest.ep {m.get('ep')!r} 가 폴더 이름 {ep!r} 와 다름")
    warns += record_warnings(cfg, m)
    durs = durations(paths, cfg, m) if not errors else {lang: {"error": "manifest 오류를 고친 뒤 계산"} for lang in active_langs(cfg)}
    plan_path = None
    if args.table:
        plan_path = paths.ep(ep) / "plan.md"
        plan_path.write_text(render_plan(cfg, m, errors, warns, durs), encoding="utf-8")
    failed = bool(errors) or (args.strict and bool(warns))
    if args.json:
        print(json.dumps({"ep": ep, "ok": not failed, "errors": errors, "warnings": warns,
                          "counts": count_types(m), "cuts": len(m.get("cuts") or []),
                          "durations": {k: {kk: vv for kk, vv in v.items() if kk != "cuts"} for k, v in durs.items()},
                          "plan": str(plan_path) if plan_path else None}, ensure_ascii=False, indent=2))
        return 1 if failed else 0
    counts = count_types(m)
    print(f"{ep}: 컷 {len(m.get('cuts') or [])}개 (V {counts['V']} · S {counts['S']} · L {counts['L']})")
    for e in errors:
        print(f"  ✖ {e}")
    for w in warns:
        print(f"  △ {w}")
    for lang, d in durs.items():
        if "total" in d:
            print(f"  예상 길이 {lang.upper()}: {mmss(d['total'])} ({d['total']:.1f}초"
                  + (", 음성 추정 포함)" if d["estimated"] else ")"))
    if plan_path:
        print(f"  표 → {plan_path}")
    if errors:
        print(f"✖ 오류 {len(errors)}개 — 고치기 전에는 제작·조립 진행 금지")
    elif failed:
        print(f"✖ --strict: 경고 {len(warns)}개")
    else:
        print(f"✔ 통과 (경고 {len(warns)}개)")
    return 1 if failed else 0


if __name__ == "__main__":
    main_wrapper(main)
