# momo — 아기토끼 모모(Momo the Bunny) 키즈 채널 제작 파이프라인

벤치마킹 → 기획 → 생성(Higgsfield MCP) → 조립(ffmpeg) → YouTube 업로드를 **재실행 가능한 스크립트**와
**Claude 가 따라가는 런북**으로 나눈 파이프라인. 비주얼은 한 벌, 음성·화면 키워드만 EN/KO 두 벌로 만든다.

```
 1 채널 분석      analyze_channel.py ─► research/<slug>/report.md, data.json
 2 샘플           sample_videos.py   ─► 자막·프레임 시트·샷 통계 (분석 후 --cleanup)
 3 구조 분석      Claude             ─► structure.md + 주제 3개 제안          ── [승인]
 4 기획           new_episode.py → manifest.json → validate_manifest.py --table ── [승인]
 5 생성           hf_jobs.py plan ─► Higgsfield MCP (이미지·클립·음성) ─► hf_jobs.py record
                  ─► fetch_assets.py ─► Claude 가 직접 보고                   ── [승인] 단계마다
 6 조립           build.py --lang en|ko --check ─► out/<ep>_<lang>.mp4 + 썸네일 + 확인 시트
 7 업로드         upload.py (세션) 또는 GitHub Action momo-publish ─► youtube.json
    (선택)        compile.py ─► 모음집 + 챕터
```

## 빠른 시작

모든 명령은 저장소 루트에서 실행한다.

```bash
# 설치 (Claude Code 웹 세션은 .claude/hooks/session-start.sh 가 자동으로)
pip install -r momo/requirements.txt
apt-get install -y ffmpeg fonts-nanum

# 점검 — ✖ 가 있으면 멈추고 해결 (폰트·BGM 은 assets/*/README.md)
python momo/doctor.py

# 1~3 벤치마킹
python momo/analyze_channel.py --url https://www.youtube.com/@채널핸들
python momo/analyze_channel.py report --dir research/<slug>          # labels.json 반영 재계산
python momo/sample_videos.py --dir research/<slug>
python momo/sample_videos.py --dir research/<slug> --cleanup

# 4 기획
python momo/new_episode.py --ep ep03 --topic-en "Rainy Day" --topic-ko "비 오는 날"
python momo/validate_manifest.py --ep ep03 --table
python momo/estimate_credits.py --ep ep03

# 5 생성 (Claude 가 MCP 로 — docs/PRODUCTION.md)
python momo/hf_jobs.py plan --ep ep03 --kind image --cuts c02
python momo/hf_jobs.py record --ep ep03 --cut c02 --kind image --job-id <JOB_ID> --url '<URL>' --status generated
python momo/fetch_assets.py --ep ep03 --library
python momo/hf_jobs.py status --ep ep03
#   클립은 Higgsfield API(별도 선불 잔액)로도 — 잔액 부족(exit 3)이면 출력된 MCP plan 으로 구독 플랜에서 이어서
python momo/hf_api.py run --ep ep03 --kind clip --dry-run
python momo/hf_api.py run --ep ep03 --kind clip --max-usd 5
python momo/hf_api.py archive --ep ep03          # 승인 후 7일 안에 (API 결과 보관 기간)

# 6 조립
python momo/build.py --ep ep03 --lang en --check
python momo/build.py --ep ep03 --lang ko --check

# 7 업로드
python momo/episode_readme.py --ep ep03
python momo/upload.py --ep ep03 --lang all --dry-run
python momo/upload.py --ep ep03 --lang all --privacy private
```

원격 실행: GitHub Actions → **momo-publish** (ep, langs, privacy, publish_at, upload, no_bgm) — 에셋 복원 → 조립 → 업로드 → 기록 커밋.
연결 점검: **momo-youtube-check** — Secrets 의 토큰으로 어느 채널에 올라갈지만 확인 (1분, 업로드 없음).

## 무엇이 자동이고 무엇이 승인인가

| 자동 (스크립트) | Claude 가 MCP 로 / 사용자 승인 필요 |
|---|---|
| 채널 목록·메타·자막·프레임·샷 통계 수집, 축별 격차 계산 | 썸네일 주인공 분류(labels.json), 구조 분석, **주제 3개 → 승인** |
| manifest 검증, 기획표(plan.md), 크레딧 예상·캡 검사 | 컷 대본 작성, **기획표 승인** (V>15 는 사유 + 승인) |
| MCP payload 조립(캐릭터 블록·스타일 락·Element), 생성 기록, 에셋 다운로드 | Higgsfield 생성, **캐릭터 시트 / 첫 컷 / 씬1 3장 / 클립마다 / 이미지 그룹 / 음성 샘플 승인** |
| 컷 길이·텍스트 타이밍 재계산, 켄번즈·핑퐁·크로스페이드, 덕킹·loudnorm, 썸네일, 확인 시트 | 확인 시트를 보고 manifest 수정, 완성본 시청(사용자) |
| 업로드(아동용 고정, 썸네일, 재생목록, 중복 방지), README 기록 | 업로드 메타 작성, 공개 전환(Studio) |

중단 조건(지시서): 에피소드 크레딧 250 초과 예상, 일일 생성 한도·플랜 권한 에러(`grace_daily_limit_reached` 등),
생성 횟수 한도(이미지·음성·영상 공통 카운터) → 즉시 멈추고 에러 원문 보고.

## 비용 (Higgsfield 크레딧, 2026-09-29 확인 — `config.higgsfield.unit_costs`)

| 항목 | 모델 | 단가 |
|---|---|---:|
| 이미지 1장 (16:9, 2k) | nano_banana_pro | 2 |
| 클립 5초 720p (기본) | kling3_0_turbo | 7.5 |
| 클립 5초 1080p | kling3_0_turbo | 10 |
| 음성 1블록 | seed_audio | 0.2 |

| 에피소드 | 예상 | 내역 |
|---|---:|---|
| 첫 편 | 200~250 | 캐릭터 시트 + 라이브러리 클립 5개(이미지+영상) + 고정 음성 4 + 음성 샘플 6 + 컷 이미지 ~20 + V 클립 12~15 + 나레이션 ~50블록 + 재생성 여유 |
| 이후 편 | 120~160 | 컷 이미지 ~20 + V 클립 12~15 + 나레이션 ~50블록 + 재생성 여유 |

캡은 편당 250 (`config.credits.episode_cap`). 1080p 클립은 첫 편을 캡 위로 올리므로 기본은 720p (조립 때 1080p 로 업스케일).

## 폴더

```
momo/
  config.json              고정값: 캐릭터 블록·스타일 락·음성 ID·폰트·크레딧 캡·렌더/오디오/유튜브 설정
  requirements.txt
  *.py                     단계별 CLI (위 빠른 시작)
  momolib/                 공용 모듈: common(경로·설정), episode(마커·프롬프트·검증·타임라인), render, audio, youtube, research
  library/library.json     라이브러리 기록 (캐릭터 시트, 고정 클립 5종, 고정 음성) — 파일은 git 제외, URL 로 복원
  assets/{bgm,sfx,fonts}/  사용자가 넣는 파일 (git 포함) — 폰트·BGM 이 없으면 멈춘다
  templates/               manifest 템플릿
  episodes/<ep>/           manifest.json, plan.md, README.md, youtube.json (git) + images/ clips/ audio/ out/ (git 제외)
  research/<slug>/         벤치마킹 결과 (report.md, data.json, labels.json, structure.md …) — 원본 영상·프레임은 git 제외
  compilations/            모음집 출력 (git 제외)
  tests/                   합성 픽스처 + 전체 테스트 (bash momo/tests/run_all.sh)
  docs/                    문서
```

## 문서

| 문서 | 내용 |
|---|---|
| [docs/ORIGINAL_BRIEF.md](docs/ORIGINAL_BRIEF.md) | 사용자 원 지시서 — 모든 규칙의 원천 (수정 금지) |
| [docs/PRODUCTION.md](docs/PRODUCTION.md) | 단계별 런북: 명령, MCP 호출, 승인 게이트, 중단 조건, 재개 |
| [docs/MANIFEST.md](docs/MANIFEST.md) | manifest.json 필드, 파일 이름 규칙, 마커, 컷 길이 계산, 예시 |
| [docs/YOUTUBE_SETUP.md](docs/YOUTUBE_SETUP.md) | Google Cloud·OAuth·Secrets·할당량·감사·아동용 설정 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 구현 명세 (스크립트 동작, 규칙) |

테스트: `bash momo/tests/run_all.sh` (합성 픽스처로 validate → build en/ko → compile → upload --dry-run, 출력 규격 검증).
CI 는 `.github/workflows/momo-ci.yml` (Python 3.11 전체 테스트 + 최소 지원 버전 3.10 단위 테스트).
