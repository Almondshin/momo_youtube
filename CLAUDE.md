# CLAUDE.md

이 저장소는 키즈 채널 "Momo the Bunny" 제작 파이프라인이다. 2026-09-30 부터 **영어 전용**
(`config.languages = ["en"]`, 사용자 결정 — 지시서의 EN/KO 두 벌보다 우선). 작업은 전부 `momo/` 안에서 하고,
사용자에게는 한국어로 보고한다.

노래는 ep03 부터 **Suno Pro** 로 만든다 (사용자가 suno.com 에서 생성 → WAV·스템을 받아 줌. 공식 API 가 없고
약관이 자동화를 금지하므로 비공식 MCP·브라우저 자동화 금지). 곡 파일 한 곡에 맞춰 컷을 짜는 방법은
`momo/docs/PRODUCTION.md` (9) 와 `momo/song_track.py`.

## 규칙의 원천

- `momo/docs/ORIGINAL_BRIEF.md` — 사용자 원 지시서. 모든 규칙이 여기서 나온다. 수정하지 말 것.
- `momo/config.json` — 그 뒤 확정된 값(캐릭터 블록, 음성 ID, 크레딧 캡 …). 지시서와 다르면 config 가 최신 결정이다.
- `momo/docs/PRODUCTION.md` — 단계별 런북. **순서대로** 따르고, 승인 게이트([승인])와 중단 조건([중단])을 그대로 지킨다.
  사용자 승인 없이 다음 게이트로 넘어가지 말 것.
- 참고: `momo/docs/MANIFEST.md`(manifest 필드), `momo/docs/ARCHITECTURE.md`(구현 명세), `momo/docs/YOUTUBE_SETUP.md`.

## 세션 시작

```bash
pip install -r momo/requirements.txt
apt-get install -y ffmpeg fonts-nanum          # 웹 세션은 .claude/hooks/session-start.sh 가 대신 한다
git pull --rebase
python momo/doctor.py --ep <ep>                 # ✖ 가 있으면 멈추고 사용자에게 알린다
python momo/hf_jobs.py status --ep <ep> --library   # 이어서 하는 중이면 어디까지 됐는지
python momo/fetch_assets.py --ep <ep> --library     # 생성물 복원 (git 제외 파일)
```

명령은 저장소 루트에서 `python momo/<script>.py` 로 실행한다.

## 반드시 지킬 것

- **비밀값을 커밋하거나 채팅에 붙여넣지 않는다** (OAuth client secret, refresh token, API 키, `momo/.secrets/`).
  세션에서 필요하면 사용자에게 클라우드 환경 설정의 환경변수로 넣어 달라고 한다.
- **생성 미디어를 커밋하지 않는다** (images/, clips/, audio/, out/, library/clips·audio·sheets — gitignore 됨).
  URL 이 manifest.json / library.json 에 기록돼 있으면 `fetch_assets.py` 로 복원된다.
- **라이브러리 에셋을 다시 만들지 않는다** — `library/library.json` 에서 approved 인 캐릭터 시트·고정 클립 5종·
  고정 음성은 재생성 금지. 확정된 `config.voices` 도 바꾸지 않는다.
- **Higgsfield 생성 1건마다 즉시** `python momo/hf_jobs.py record …` 로 job_id·url·credits 를 기록한다.
  컨테이너는 언제든 사라진다.
- **승인된 배치마다** `momo/episodes/<ep>/manifest.json`(과 바뀌었으면 library.json, config.json)을 커밋·푸시한다.
- 생성 전에는 `python momo/estimate_credits.py --ep <ep>` — exit 2(에피소드 150 크레딧 초과 예상 — 2026-10-01 사용자 결정, ep08 부터)면 멈춘다.
  한도·플랜 권한 에러(`grace_daily_limit_reached` 등)는 재시도하지 말고 에러 원문 그대로 보고한다.
- 생성 결과는 Read 도구로 직접 본 뒤에 승인을 요청한다.
- 스크립트를 고치면 `bash momo/tests/run_all.sh` 를 통과시킨다. 코드 규칙은 ARCHITECTURE.md "공통 규칙".
