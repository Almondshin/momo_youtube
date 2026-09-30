#!/usr/bin/env python3
"""새 에피소드 폴더 만들기: templates/manifest.template.json 복사 + images/ clips/ audio/{en,ko}/ out/.

템플릿에는 인트로(c01 intro_wave)·아웃트로(c02 outro_bye) L 컷만 있다. 고정 문장은 config.fixed_lines 로 채운다.
이미 manifest.json 이 있으면 거부 (생성 기록이 날아가지 않게). --force 면 manifest.json.bak 으로 백업 후 덮어쓴다.

사용 예
  python new_episode.py --ep ep03 --topic-en "Rainy Day" --topic-ko "비 오는 날"
  python new_episode.py --ep ep03 --force
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import (MomoError, active_langs, add_root_arg, check_ep, get_paths, load_config,  # noqa: E402
                            load_json, main_wrapper, save_json)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="새 에피소드 폴더와 manifest 만들기",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    ap.add_argument("--ep", required=True)
    ap.add_argument("--topic-en", default="")
    ap.add_argument("--topic-ko", default="")
    ap.add_argument("--force", action="store_true", help="기존 manifest.json 을 .bak 으로 백업하고 덮어씀")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    ep = check_ep(args.ep)
    cfg = load_config(paths)
    tpl_path = paths.templates / "manifest.template.json"
    m = load_json(tpl_path)
    target = paths.manifest(ep)
    if target.exists():
        if not args.force:
            raise MomoError(f"이미 있음: {target} — 생성 기록을 덮어쓰지 않게 거부 (정말 새로 만들려면 --force)")
        bak = target.with_name("manifest.json.bak")
        shutil.copy2(target, bak)
        print(f"△ 기존 manifest 백업 → {bak}")

    m["ep"] = ep
    m["status"] = "planning"
    m["topic"] = {"en": args.topic_en.strip(), "ko": args.topic_ko.strip()}
    if cfg["benchmark"].get("channel_url") and isinstance(m.get("benchmark"), dict):
        m["benchmark"]["channel_url"] = m["benchmark"].get("channel_url") or cfg["benchmark"]["channel_url"]
    for c in m.get("cuts") or []:
        la = c.get("library_audio")
        if la:  # 고정 문장은 config 가 기준
            c["narration"] = {lang: cfg["fixed_lines"][lang][la] for lang in active_langs(cfg)}
    save_json(target, m)
    for d in (paths.images(ep), paths.clips(ep), *(paths.audio(ep, lang) for lang in active_langs(cfg)), paths.out(ep)):
        d.mkdir(parents=True, exist_ok=True)
    print(f"✔ {ep} 준비됨: {paths.ep(ep)}")
    print("  manifest.json (인트로 c01 · 아웃트로 c02 만 있음), images/ clips/ audio/en/ audio/ko/ out/")
    print("다음:")
    print("  1. 1단계 분석 결과로 주제 승인 → manifest 의 topic·title·thumbnail·upload 채우기")
    print("  2. 컷 22~28개 (V 12~15 · S 6~8 · L 3~4, 5씬) 작성 — docs/MANIFEST.md")
    print(f"  3. python validate_manifest.py --ep {ep} --table   → plan.md 표를 보여주고 승인받기")
    print(f"  4. python estimate_credits.py --ep {ep}           → 캡 {cfg['credits']['episode_cap']:g} 확인")
    return 0


if __name__ == "__main__":
    main_wrapper(main)
