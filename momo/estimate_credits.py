#!/usr/bin/env python3
"""5단계 프리플라이트: 이번 에피소드 예상 크레딧 (라이브러리 미완성분 + 에피소드 남은 생성 + 재생성 여유).

단가는 config.higgsfield.unit_costs (get_cost:true 로 확인한 값). 아직 승인되지 않았고 새로 만들어야 하는
항목(pending/rejected)만 센다 — 검토 대기(generated)는 이미 낸 비용이라 0, 승인된 것과 L 컷은 0.
예상 총액 = 이미 사용(manifest.credits.spent) + 남은 생성 + 재생성 여유(이미지·영상 × rate).
캡(config.credits.episode_cap)을 넘으면 exit 2 — 지시서의 중단 조건.

사용 예
  python estimate_credits.py --ep ep02
  python estimate_credits.py --ep ep02 --regen-rate 0.3 --json
  python estimate_credits.py --ep ep02 --save        # manifest.credits.estimate 에 적어 둠
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from momolib.common import (add_root_arg, check_ep, get_paths, load_config, load_library,  # noqa: E402
                            load_manifest, main_wrapper, save_json)
from momolib.genrec import estimate, stop_message  # noqa: E402


def fmt(x: float) -> str:
    return f"{x:,.1f}".rstrip("0").rstrip(".")


def render(est: dict, cfg: dict) -> str:
    u = est["unit"]
    hf = cfg["higgsfield"]
    checked = hf["unit_costs"].get("checked_at")
    lines = [f"# {est['ep']} 예상 크레딧",
             "",
             f"단가: 이미지 {fmt(u['image'])} · 영상 {hf.get('video_resolution')} {hf.get('video_duration')}초 "
             f"{fmt(u['clip'])} · 음성 블록 {fmt(u['audio'])}" + (f" (확인 {checked})" if checked else ""),
             "",
             "| 구분 | 항목 | 개수 | 단가 | 크레딧 |",
             "|---|---|---:|---:|---:|"]
    for r in est["rows"]:
        if r.count:
            lines.append(f"| {r.group} | {r.label} | {r.count} | {fmt(r.unit)} | {fmt(r.credits)} |")
    if not est["library_incomplete"]:
        lines.append("| 라이브러리 | 완성됨 (재생성 금지) | 0 | | 0 |")
    lines += [f"| 여유 | 재생성 {est['regen_rate'] * 100:g}% (이미지·영상) | | | {fmt(est['regen'])} |",
              f"| 기록 | 이미 사용 (manifest.credits.spent) | | | {fmt(est['spent'])} |",
              f"| **합계** | **예상 총액** | | | **{fmt(est['total'])}** |",
              ""]
    lines.append(f"- 남은 생성 {fmt(est['remaining'])} + 재생성 여유 {fmt(est['regen'])} + 이미 사용 {fmt(est['spent'])}"
                 f" = {fmt(est['total'])} / 캡 {fmt(est['cap'])}")
    lines.append(f"- 예상 생성 횟수 약 {est['generations']}회 — 힉스필드는 이미지·영상·음성을 하나의 생성 카운터로 센다 "
                 f"(크레딧과 별개로 일일 한도도 감시)")
    if est["review"]:
        lines.append(f"- 검토 대기 {len(est['review'])}개 (이미 지불, 0으로 계산): {', '.join(est['review'])}")
    rng = cfg["credits"].get("estimate_first_episode" if est["library_incomplete"] else "estimate_later_episode")
    if rng:
        kind = "첫 편(라이브러리 포함)" if est["library_incomplete"] else "이후 편"
        lines.append(f"- 참고: 지시서 예상 {kind} {rng[0]}~{rng[1]}")
    lines.append("- L 컷은 라이브러리 클립·고정 음성을 써서 0 크레딧")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="에피소드 예상 크레딧 (캡 초과면 exit 2)",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    add_root_arg(ap)
    ap.add_argument("--ep", required=True)
    ap.add_argument("--regen-rate", type=float, default=0.2, help="재생성 여유 비율 (기본 0.2)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--save", action="store_true", help="manifest.credits.estimate 에 합계 저장")
    args = ap.parse_args(argv)
    paths = get_paths(args)
    cfg = load_config(paths)
    ep = check_ep(args.ep)
    m = load_manifest(paths, ep)
    est = estimate(paths, cfg, m, load_library(paths), max(0.0, args.regen_rate))
    if args.json:
        out = {k: v for k, v in est.items() if k != "rows"}
        out["rows"] = [{"group": r.group, "label": r.label, "kind": r.kind, "count": r.count, "unit": r.unit,
                        "credits": r.credits} for r in est["rows"]]
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(render(est, cfg))
    if args.save:
        m.setdefault("credits", {})["estimate"] = round(est["total"], 1)
        save_json(paths.manifest(ep), m)
        print(f"\nmanifest.credits.estimate = {round(est['total'], 1)} 저장", file=sys.stderr)
    if est["over_cap"]:
        print(f"\n✖ {stop_message(est['total'], est['cap'])}\n"
              f"  줄일 방법: V 컷 일부를 S 로, 재생성 여유 확인, 라이브러리 재사용 — 사용자 승인 후 진행", file=sys.stderr)
        return 2
    print(f"\n✔ 캡 {fmt(est['cap'])} 이내 (여유 {fmt(est['cap'] - est['total'])})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    main_wrapper(main)
