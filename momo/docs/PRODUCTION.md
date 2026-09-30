# 제작 런북 — Claude 가 에피소드 1편을 만드는 순서

규칙의 원천은 `docs/ORIGINAL_BRIEF.md`(사용자 지시서 원문, 수정 금지)와 `config.json`(그 뒤 확정된 값 —
예: 멜빵 단추 2개, 조연 Toto·Sunny, 음성 ID). 둘이 다르면 config 가 최신 결정이다.
이 문서는 그 규칙을 **순서대로 실행하는 절차**다. 단계를 건너뛰거나 순서를 바꾸지 않는다.

표기
- **[승인]** 사용자에게 보여주고 승인받기 전에는 다음으로 넘어가지 않는다. 승인되면
  `manifest.notes.approvals` 에 `"2026-10-01 c02~c04 이미지 승인"` 처럼 한 줄 남긴다.
- **[중단]** 즉시 멈추고 에러 원문을 그대로 보고한다 (보고 형식은 [중단 조건과 실패 처리](#중단-조건과-실패-처리--5단계-내내-적용)).
- 명령은 **저장소 루트**에서 `python momo/<script>.py …` 로 실행한다. 경로 인자(`research/<slug>`)는 `momo/` 기준.
- `ep02` 는 실제 에피소드 번호로 바꿔 쓴다. 필드 정의는 [MANIFEST.md](MANIFEST.md).

---

## 0. 세션 준비 · 점검 (매 세션 시작)

컨테이너는 언제든 사라진다. 커밋된 것(manifest·library.json·config·research 결과)만 남고,
이미지·클립·음성은 기록된 URL 로 다시 받는다.

```bash
git pull --rebase                                   # Action·다른 세션의 커밋 받기
pip install -r momo/requirements.txt
apt-get install -y ffmpeg fonts-nanum               # root 가 아니면 sudo
python momo/doctor.py --ep ep02                     # 에피소드가 아직 없으면 --ep 생략
python momo/hf_jobs.py status --ep ep02 --library   # 이어서 하는 중이면: 어디까지 됐는지
python momo/fetch_assets.py --ep ep02 --library     # 생성물 복원
```

- Claude Code 웹 세션은 `.claude/hooks/session-start.sh` 가 pip/apt 설치를 대신한다.
- doctor 의 **✖**(한글 폰트 없음, BGM 없음, ffmpeg 필터 없음 등)는 **[중단]** — 사용자에게 무엇을 어디에
  넣어야 하는지 알린다 (`assets/fonts/README.md`, `assets/bgm/README.md`). **△** 는 보고만 하고 진행.
- yt-dlp 는 `python momo/doctor.py --update-ytdlp` 로 최신화한다 (유튜브가 자주 바뀐다).

### Higgsfield MCP 점검

1. `mcp__higgsfield__*` 도구가 없으면 **[중단]** — "Claude Code 에 Higgsfield MCP 를 연결해 달라"고 요청.
2. `mcp__higgsfield__balance` → 남은 크레딧·플랜.
3. `mcp__higgsfield__show_plans_and_credits` → 플랜 한도 확인. 구매·업그레이드는 사용자가 결정한다.
4. 단가 확인 — `get_cost: true` 는 **제출하지 않고** 비용만 돌려준다:

   | 호출 | params | 기준 단가 |
   |---|---|---|
   | `mcp__higgsfield__generate_image` | `{"model":"nano_banana_pro","prompt":"cost check","aspect_ratio":"16:9","resolution":"2k","get_cost":true}` | 2 |
   | `mcp__higgsfield__generate_video` | `{"model":"kling3_0_turbo","prompt":"cost check","duration":5,"aspect_ratio":"16:9","resolution":"720p","get_cost":true}` | 7.5 (1080p 는 10) |
   | `mcp__higgsfield__generate_audio` | `{"model":"seed_audio","prompt":"Hi friends!","voice_type":"preset","voice_id":"<list_voices 의 아무 id>","get_cost":true}` | 0.2 / 블록 |

   다르면 `config.higgsfield.unit_costs`(와 `checked_at`)를 고치고 커밋한다 — estimate_credits 가 이 값을 쓴다.

**영상은 720p 가 기본이다.** 1080p(10크레딧)로 뽑으면 첫 편(에피소드 V 13 + 라이브러리 5 = 클립 18개)이
+45크레딧이 되어 캡 250 을 넘는다. build.py 가 1920x1080 으로 크롭-투-필 업스케일한다.

---

## 1. 채널 분석 (1단계)

벤치마킹 채널 URL(영상 링크가 아니라 **채널** 링크)이 없으면 사용자에게 묻는다. 기록 위치: `config.benchmark`.

```bash
python momo/analyze_channel.py --url https://www.youtube.com/@채널핸들          # → research/<slug>/
```

- 스크립트가 `yt-dlp -U` 시도 → (a) 목록 (b) 인기순 `sort=p` 시도·내림차순 검사 (c) 최신 15 (d) 20개 개별 메타 →
  72시간 미만 제외, 30분+ 모음집 분리, 배수·비중·채널 상태·축별 격차 계산 → `report.md`, `data.json`, `labels.template.json`.
- 봇 확인/403 은 스크립트가 `--sleep-requests 1` 로 재시도한다. 그래도 실패하면 사용자에게 쿠키 사용 여부를 묻고
  `--cookies-from-browser chrome` 또는 `--cookies cookies.txt` 로 다시. 그래도 실패하면 **[중단]**, 에러 원문 그대로 보고.
- **youtube.com 이 막힌 세션**(Claude Code 클라우드가 그렇다):
  - `--backend api` — `YOUTUBE_API_KEY` 환경변수로 Data API v3 사용 (www.googleapis.com 은 열려 있음).
    (a)~(d) 수치는 나오지만 자막·프레임은 못 받는다.
  - 원격 수집 — GitHub Actions 러너에서 yt-dlp 실행 (`momo-research` 워크플로):
    ```bash
    python momo/remote_research.py keygen      # 이 세션에만 비공개키 생성 (새 세션이면 다시)
    # research/requests/<이름>.json 작성 → 커밋·푸시 → Action 이 실행되고 결과를 커밋
    git pull --rebase
    # 프레임·썸네일 시트(암호화)는 momo-research-sealed 브랜치에만 있다 → research/<slug>/frames/ (git 제외)로 복호화
    git fetch origin momo-research-sealed
    mkdir -p /tmp/sealed && git archive origin/momo-research-sealed | tar -x -C /tmp/sealed
    python momo/remote_research.py unseal --sealed /tmp/sealed
    # 받아 온 목록으로 분석 (meta 는 offline-json 옆 meta/ 를 쓴다)
    python momo/analyze_channel.py --offline-json research/<slug>/channel_flat.json \
        --offline-popular research/<slug>/popular_flat.json --out research/<slug>
    ```
    요청 파일 형식은 `remote_research.py` docstring 과 `research/requests/*.json` 참고
    (`"thumbs_all": true` 면 최신 15 + 역대 5 썸네일 시트가 와서 아래 labels 작업에 쓴다).
    비공개키는 keygen 한 세션에만 있으므로, 수집 요청과 unseal 은 같은 세션에서 한다.
    러너 IP 도 봇 확인에 걸릴 수 있다 (영상별 메타·자막·프레임). 걸리면 에러 원문을 기록하고 사용자에게 선택지를 준다:
    API 키 / 로컬 PC 에서 실행 후 커밋 / 해당 항목 "미검증"으로 진행.

**썸네일 주인공 축은 자동 판정이 안 된다.** `labels.template.json` 을 `labels.json` 으로 복사하고, 20개 영상의 썸네일을
**Read 도구로 직접 보고** `thumbnail_subject`(캐릭터 클로즈업 / 사물 / 텍스트 위주)를 채운다. 자동 판정(topic·format)이
틀렸으면 같이 고친다. 썸네일은 `https://i.ytimg.com/vi/<id>/hqdefault.jpg`(또는 `meta/<id>.json` 의 thumbnail)를
`research/<slug>/raw/thumbs/`(git 제외)에 받아서 보거나, 원격 수집의 썸네일 시트를 본다. 그다음 재계산 (네트워크 없음):

```bash
python momo/analyze_channel.py report --dir research/<slug>          # labels.json 자동 적용
```

## 2. 자막·영상 샘플 (2단계)

```bash
python momo/sample_videos.py --dir research/<slug>                  # 역대 1위 + 최근 1위
python momo/sample_videos.py --dir research/<slug> --ids ID1 ID2    # 대상 직접 지정
```

- 자막(json3 → `subs/<id>.<lang>.txt`, 없으면 "건너뜀" 기록), 프레임 30~40장 + `frames/<id>_sheet.jpg`,
  샷 전환 통계, 썸네일 4장(역대 1·2위 + 최근 1위·최하위) → `raw/thumbs/<id>.jpg`.
- `frames/<id>_sheet.jpg` 와 썸네일 4장 이상을 **Read 로 직접 본다**. 1장만 보고 패턴을 단정하지 않는다.
- 분석이 끝나면 **반드시** 삭제 (프레임 재사용 금지):
  ```bash
  python momo/sample_videos.py --dir research/<slug> --cleanup
  ```

## 3. 구조 분석 → 주제 제안 (3단계)

`research/<slug>/structure.md` 에 아래 항목을 **숫자와 근거**로 쓴다 (측정 못 한 항목은 "미검증 — 이유").

- [ ] 오프닝 5초에 무엇이 먼저 나오는가 (캐릭터 인사 / 노래 / 사물 클로즈업)
- [ ] 평균 샷 길이(2단계 값)와 컷 전환 리듬
- [ ] 반복 구조: 같은 후렴·문장이 몇 번, 어떤 간격으로 반복되는가
- [ ] 콜 앤 리스폰스: "따라 해봐" 뒤 대기 구간이 있는가, 몇 초인가
- [ ] 한 화면당 학습 포인트 수 (사물 1개 원칙)
- [ ] 화면 텍스트: 키워드만 / 문장 자막 / 없음
- [ ] 캐릭터 노출 비율 (샘플 프레임 중 주인공이 보이는 비율)
- [ ] 제목과 썸네일 문구의 차이
- [ ] 시리즈 확장 방식 (에피소드 번호 / 소재 시리즈 / 모음집)

벤치마크가 여러 채널이면 `research/SUMMARY.md` 에 종합한다.

**주제 3개 제안** — `report.md` 의 격차가 가장 큰 축(원인 후보)에 맞춘다. 각 안에: 축·근거 수치, 씬 ②③④ 학습 포인트,
화면 키워드 EN/KO, 제목 EN/KO(부모 검색 키워드형), 썸네일 문구(3단어 이하), 제작 위험(캐릭터 일관성·사물 개수 등).
최신 15 중 상위 3개가 역대 성공작과 같은 포맷인지 비교도 함께 보고한다.

**[승인]** 주제 선택. 승인 전에는 4단계로 가지 않는다.

---

## 4. 에피소드 기획 (4단계)

```bash
python momo/new_episode.py --ep ep02 --topic-en "Brush Your Teeth" --topic-ko "양치하기"
```

`episodes/ep02/manifest.json` 의 `cuts` 를 채운다 (필드는 [MANIFEST.md](MANIFEST.md)).
템플릿의 c02(아웃트로)는 마지막 번호로 옮긴다. 지시서 규칙:

- 2~3분(약 150초), 5씬, 씬당 4~6컷 → 22~28컷. 씬: ① 인사+문제 제기 ② 학습1 ③ 학습2 ④ 학습3(친구 가능) ⑤ 복습+작별.
- 씬마다 학습 포인트 1개, 핵심 단어 3번 이상 반복. 벤치마크 구조를 따르되 **번역이 아니라 재창작**.
- 콜 앤 리스폰스 뒤 `[pause 1.5]`, 노래 파트는 `[chant]` 챈트.
- 첫 컷 L `intro_wave` + `library_audio: intro`, 마지막 컷 L `outro_bye` + `library_audio: outro` (고정 문장 그대로).
- 타입 비율 V 12~15 · S 6~8 · L 3~4. **V 가 15개를 넘으면** `notes.v_over_reason` 에 이유를 쓰고 따로 승인.
- 나레이션 EN 25단어·KO 40자 안팎, 짧게, 어른 톤 설명 금지. 화면 키워드는 컷당 1개(문장 자막 금지).
- 이미지 프롬프트: 장면만 (캐릭터 블록·스타일 락은 자동). 글자·숫자·간판·기존 IP 이름·무서운/어두운 요소 금지.
  키워드가 들어갈 자리를 위해 "clear empty space in the upper third of the frame" 같은 여백을 요청한다.
- 모션은 작게("small hop in place", "waves one paw", "ears bounce"). 카메라 이동·급격한 움직임·형태 변형 금지.
- 제목(EN/KO) 키워드형, 썸네일 컷 1개(모모 클로즈업 + 핵심 사물) + 문구 3단어 이하.

```bash
python momo/validate_manifest.py --ep ep02 --table     # errors 0 이 될 때까지 고친다 → episodes/ep02/plan.md
python momo/estimate_credits.py --ep ep02               # 예상 크레딧 (첫 편 200~250, 이후 120~160)
python momo/build.py --ep ep02 --lang en --allow-missing   # (선택) 크레딧 0 애니매틱으로 길이·리듬 확인
```

사용자에게 `plan.md` 의 컷 표(컷 · 씬 · 타입 · 나레이션 EN · 나레이션 KO · 화면 키워드 EN / KO · 이미지 프롬프트 · 모션 지시),
타입 개수, 제목·썸네일 문구, 예상 길이, 예상 크레딧, 남은 경고를 보여준다.

**[승인]** 기획표. 승인되면 `notes.approvals` 기록, manifest·plan.md 커밋·푸시.

---

## 5. 제작 — Higgsfield (5단계, 순서 고정 (0)→(7))

### 중단 조건과 실패 처리 — 5단계 내내 적용

지시서 원문 (그대로 지킨다):

> ⚠️ 중단 조건 — 하나라도 걸리면 즉시 멈추고 에러 원문 그대로 보고
> · 이번 에피소드 총 크레딧이 250을 넘을 것 같을 때
> · 일일 생성 한도 / 플랜 권한 에러 (grace_daily_limit_reached 등)
> · 크레딧이 남아 있어도 생성 횟수 한도는 별개다. 둘 다 감시할 것
> · 힉스필드는 이미지·음성·영상을 하나의 생성 카운터로 센다
> ⚠️ 실패 시: 어느 컷까지 성공했는지 표로 정리하고, 성공분은 버리지 말고 보존한 뒤 재개 방법을 알려줄 것

실행 방법:

- 크레딧 캡: 매 배치 전 `estimate_credits.py` (exit 2 = 중단). `hf_jobs.py plan` 도 예상치(`credits.projected`)가 캡을
  넘으면 ✖ 중단 문구와 함께 exit 2 — 그 payload 는 쓰지 않는다. `--allow-over-cap` 은 사용자가 캡 초과를 명시적으로 승인했을 때만.
  실제 사용량은 `manifest.credits.spent` 와 `mcp__higgsfield__balance` 로 대조한다.
- 한도·권한 에러(`grace_daily_limit_reached` 등, 어떤 generate_* 에러든): **재시도하지 않는다.** 에러 메시지를
  코드 블록에 원문 그대로 붙인다. 우회하려고 모델·해상도를 바꾸지 않는다.
- 크레딧이 남아 있어도 생성 횟수 한도는 따로다. 이미지·음성·영상이 같은 카운터를 쓴다 —
  음성 블록(1편 약 50개)도 1회씩 센다.

실패 보고 절차:

```bash
python momo/hf_jobs.py status --ep ep02 --library      # 컷별 image/clip/audio(en,ko) 상태표 + 크레딧 + 다음 작업
git add momo/episodes/ep02/manifest.json momo/library/library.json momo/config.json
git commit -m "ep02 5단계 중단: <이유>" && git push      # 성공분 기록 보존
```

사용자에게: ① 에러 원문 ② status 표(어느 컷까지 성공) ③ 사용 크레딧/남은 예상치 ④ 재개 방법 —
"한도가 풀린 뒤(또는 플랜 조정 뒤) 새 세션에서 `git pull` → `doctor.py` → `hf_jobs.py status` →
`hf_jobs.py plan …` 이 승인 안 된 항목만 다시 내준다". 생성된 파일은 URL 이 기록돼 있어 `fetch_assets.py` 로 복원된다.

### 모든 생성에 공통인 루프

1. **예산**: `python momo/estimate_credits.py --ep ep02` — exit 2(캡 초과 예상)면 **[중단]**.
2. **payload**: `python momo/hf_jobs.py plan --ep ep02 --kind image [--cuts c05,c06,c07]` (`--cuts` 가 없으면 다음 묶음,
   최대 `max_parallel_images` 4장). 출력의 각 item 은 `{"tool", "params", "record"}` 다.
   `params` 를 `mcp__higgsfield__<tool>` 에 **그대로** 넘긴다. 프롬프트를 손으로 고쳐 쓰지 않는다 — 고칠 게 있으면
   manifest 를 고치고 plan 을 다시 뽑는다. (캐릭터 블록·스타일 락·Element 자리표시 `<<<element_id>>>`·`folder_id` 는
   plan 이 이미 넣었다.) `awaiting_review`(생성됐지만 검토 전)·`blocked`(선행 승인 필요) 목록도 확인한다.
3. **생성**: 아래 표의 도구. `use_unlim` 은 넣지 않는다 (사용자가 명시적으로 원할 때만). 응답이 `unlim_choice` 면 사용자에게 묻는다.
   응답이 `recovery_tool` 을 주면 그것부터 호출한다.
4. **대기**: 배치는 `mcp__higgsfield__jobs_wait`(최대 12개, `timeout_seconds` 15 — `all_terminal` 이 될 때까지 반복).
   전송 타임아웃이 나면 **재제출하지 않는다** — 받은 job_id 의 결과부터 확인한다 (중복 과금 방지).
5. **즉시 기록** (컨테이너가 사라져도 남도록, 생성 1건마다 바로) — item 의 `record` 명령에 job_id·url 을 채워 실행:
   ```bash
   python momo/hf_jobs.py record --ep ep02 --cut c05 --kind image --job-id <JOB_ID> --url '<URL>' --status generated
   ```
   크레딧은 `config.higgsfield.unit_costs` 로 자동 기록된다 (다르게 차감됐으면 `--credits N`).
6. **받기**: `python momo/fetch_assets.py --ep ep02` (라이브러리도 받으려면 `--library` 추가).
7. **직접 보기**: 이미지는 Read 도구로 파일을 연다 (`momo/episodes/ep02/images/c05.png`).
   클립은 프레임 시트를 만들어 Read:
   ```bash
   ffmpeg -v error -y -i momo/episodes/ep02/clips/c05.mp4 -vf "fps=2,scale=384:-2,tile=5x2" -frames:v 1 /tmp/c05_clip.jpg
   ```
   모모가 나오는 이미지는 **얼굴을 원본 크기로 잘라서도** 본다 (축소 시트에서는 구슬 눈을 놓친다 — ep04 c33).
   음성은 Claude 가 들을 수 없다 — 길이(`ffprobe`)로 이상치만 보고, 판단은 사용자에게 맡긴다.
   사용자에게는 `mcp__higgsfield__job_display`(1건) / `mcp__higgsfield__show_generation_by_ids`(배치)로 위젯을 띄워 보여준다.
8. **승인 결과 기록**:
   ```bash
   python momo/hf_jobs.py record --ep ep02 --cut c05 --kind image --status approved
   python momo/hf_jobs.py record --ep ep02 --cut c06 --kind image --status rejected --reason "노란 단추가 안 보임"
   ```
   **모모 모습 검사(가드레일)**: 모모가 나오는 컷의 이미지·클립은 승인할 때 눈 비율(`momolib/onmodel.py`, 캐릭터
   시트 = 1.00)을 자동으로 잰다. `config.onmodel.eye_ratio_min`(0.65) 아래면 승인이 거부된다 — 구슬 눈·눌린 얼굴.
   직접 크게 보고 정말 괜찮을 때만 `--off-model-ok`. 클립 `plan` 도 시작 이미지가 걸리면 그 클립을 `blocked` 로 막는다
   (클립은 시작 이미지를 그대로 따라간다). 한꺼번에 보려면 `python momo/hf_jobs.py onmodel --ep ep02`.
   거절분은 2번부터 다시 (재생성 횟수는 자동 집계). 승인된 항목을 다시 만들려면 `record … --force` 가 필요하다 — 쓰지 말 것.
9. **커밋**: 승인 배치마다
   ```bash
   git add momo/episodes/ep02/manifest.json momo/library/library.json momo/config.json
   git commit -m "ep02 5단계(5): c05~c07 이미지 승인" && git push
   ```

| 용도 | 도구 | 핵심 params (plan 이 채운다) |
|---|---|---|
| 이미지 1장 | `mcp__higgsfield__generate_image` | `model: nano_banana_pro`, `aspect_ratio: "16:9"`, `resolution: "2k"`, `prompt`, `folder_id` — 2크레딧 |
| 이미지 여러 장 | `mcp__higgsfield__generate_image_batch` | `requests: [{index, params}]` — **한 번에 3~4장만. 12장 이상 동시 요청 금지** |
| 클립 | `mcp__higgsfield__generate_video` | `model: kling3_0_turbo`, `duration: 5`, `aspect_ratio: "16:9"`, `resolution: "720p"`, `medias: [{role: "start_image", value: <승인 이미지 job_id>}]` — 7.5크레딧 |
| 음성 | `mcp__higgsfield__generate_audio` / `generate_audio_batch` | `model: seed_audio`, `voice_type: "preset"`, `voice_id`, `prompt`(블록 문장) + `config.higgsfield.audio_params`(예: `speech_rate`, `pitch_rate`) — 0.2크레딧/블록 |
| 결과 대기 | `mcp__higgsfield__jobs_wait` | `jobs: [{index, job_id}]` 최대 12 |
| 사용자에게 보이기 | `mcp__higgsfield__job_display` / `show_generation_by_ids` | job id |

모델이 `medias` role 을 거부하면 `mcp__higgsfield__models_explore` 로 그 모델의 `medias[].roles` 를 확인한다.
`medias[].value` 에는 URL 이 아니라 job_id/media_id 를 넣는다.

### (0) 프리플라이트

1. 0절의 Higgsfield 점검(balance, 플랜, get_cost 단가)을 했는지 확인.
2. `python momo/hf_jobs.py status --ep ep02 --library` — 라이브러리에 이미 있는 것(시트·클립·고정 음성)은 재생성 대상에서 빠진다.
3. `python momo/estimate_credits.py --ep ep02 --save` — 표와 합계를 사용자에게 보고한다 (`--save` 가 `manifest.credits.estimate` 에 기록).
   예상: 첫 편 200~250, 이후 편 120~160. exit 2 면 **[중단]**.
4. 에피소드마다 1회 프로젝트 생성: `mcp__higgsfield__list_workspaces` 로 workspace 확인 →
   `mcp__higgsfield__create_project {"name": "Momo ep02", "workspace_id": "…", "idempotency_key": "momo-ep02"}` →
   `project_id`, `default_folder_id` 를 `config.higgsfield.project_id` / `folder_id` (+ `workspace_id`)에 저장·커밋.
   plan 이 이 `folder_id` 를 모든 payload 에 넣는다. 같은 에피소드를 새 세션에서 이어갈 때는 저장된 값을 재사용한다.
5. `manifest.status` 는 첫 생성을 기록할 때 hf_jobs.py 가 `producing` 으로 바꾼다.

첫 편에서 라이브러리 항목(시트·라이브러리 클립·고정 음성·음성 샘플)을 기록할 때는 `--ep ep02` 를 붙인다 —
그 에피소드 크레딧(캡 250)에 합산된다.

### (1) 캐릭터 시트 — `library.json` 의 `character_sheets.momo` 가 approved 가 아닐 때만 (첫 편 1회)

1. `mcp__higgsfield__get_workflow_instructions {"workflow": "character-sheet"}` 를 먼저 읽는다 (지시서 규칙이 우선).
2. `python momo/hf_jobs.py plan --library --kind sheet --ep ep02` → `generate_image`
   (front / three-quarter / side / back + 표정 4종, 흰 배경, 16:9).
3. `python momo/hf_jobs.py record --sheet momo --job-id <JOB_ID> --url '<URL>' --status generated --ep ep02` →
   `python momo/fetch_assets.py --ep ep02 --library` → `momo/library/sheets/momo.png` 를 Read.
4. 확인: 의상·색·비율, 노란 단추(`config.character.rules`), 귀 2개, 글자 없음, 기존 IP 와 닮지 않음.
5. **[승인]** → `python momo/hf_jobs.py record --sheet momo --status approved --ep ep02`.
6. Element 등록: `mcp__higgsfield__show_reference_elements {"action": "create", "name": "momo",
   "medias": [{"id": "<시트 job_id>", "url": "<시트 url>", "type": "image_job"}]}` → 받은 id 를
   `config.higgsfield.element_ids.momo`(와 `momo_element_id`), `library.json` 의 `character_sheets.momo.element_id` 에 저장·커밋.
   이후 `hf_jobs.py plan` 이 그 캐릭터가 나오는 컷의 프롬프트 앞에 `<<<element_id>>>` 를 자동으로 넣는다.
   - 등록이 안 되면 → 매 생성 호출의 `medias` 에 시트를 참조 이미지로 첨부.
   - 그것도 안 되면 → 캐릭터 고정 블록을 프롬프트 맨 앞에 그대로 반복 (기본 조립이 이미 그렇게 한다).
7. Ducky(또는 다른 조연)가 나오는 에피소드면 같은 방식으로 1장 (`--sheet ducky`, `element_ids.ducky`).

### (2) 첫 컷 1장 — 한도 통과 검증

manifest 의 첫 V/S 컷(보통 c02, c01 은 인트로 L) **1장만** 생성한다:
`python momo/hf_jobs.py plan --ep ep02 --kind image --cuts c02` → `generate_image` → 기록 → 받기 → Read.
플랜 권한·일일 한도 에러 없이 생성되는지, 실제 차감 크레딧이 단가와 같은지(`balance` 전후) 확인한다.
에러면 **[중단]**. 사용자에게 보여주고 진행 여부를 확인한다.

### (3) 씬 1 의 3장 — 함께 보고 승인

씬 1 의 V/S 컷을 (2)의 1장 포함 **3장까지** 만든다 (`plan … --cuts c03,c04` → `generate_image_batch`).
3장을 **함께** 보여준다 — 1장으로는 스타일·캐릭터 일관성을 판단할 수 없다.

**[승인]** 3장. 승인 전에는 넘어가지 않는다. 한 장이 거절되면 그 컷만 재생성해서 3장 세트로 다시 보여준다.

### (4) 그 3장 중 V 타입만 클립으로

```bash
python momo/hf_jobs.py plan --ep ep02 --kind clip --cuts c02,c03    # 이미지가 approved 인 V 컷만 나온다
```

- `generate_video`: `kling3_0_turbo`, `duration 5`, `16:9`, `720p`, 승인된 이미지를 **start_image** 로.
  **text-to-video 로 새로 뽑지 않는다** (화풍이 어긋난다). plan 은 이미지 승인 전인 컷을 `blocked` 로 빼고 내주지 않는다.
- 프롬프트 = manifest 의 모션 지시 + "Keep the character design exactly the same. Static fixed camera …" (자동 조립). 카메라 고정.
- 클립은 수 분 걸린다 — `jobs_wait` 를 반복. 기록: `record --ep ep02 --cut c02 --kind clip --job-id … --url … --status generated`.
- 프레임 시트를 Read 로 보고 확인: 형태 변형, 의상 변화, 귀 개수 이상, 카메라 이동, 빠른 움직임, 번쩍임.
  하나라도 있으면 재생성 (manifest 의 모션 문구를 더 작게).

**[승인]** 클립 하나하나.

### (5) 나머지 컷

- 이미지: `plan --ep ep02 --kind image`(다음 묶음) 로 **3~4장씩** `generate_image_batch` → 기록 → 받기 → Read →
  **[승인]** (그룹 단위) → 커밋. 12장 이상 동시 요청 금지.
- V 타입은 이미지 승인 후 클립으로 (`plan --kind clip`) → **[승인]** 클립마다. S 타입은 이미지로 끝.
- 그룹마다 `estimate_credits.py` 로 남은 예상치를 확인한다.

### (6) 라이브러리 클립 — 첫 편에서만

`intro_wave`(손 흔들며 인사) · `outro_bye`(작별) · `say_with_me`(고개 끄덕임) · `cheer`(박수) · `transition`(깡충 뛰어 화면 밖으로), 각 5초.
`library.json` 에서 approved 인 것은 **절대 재생성하지 않는다** (plan 에 나오지 않는다).

```bash
python momo/hf_jobs.py plan --library --kind image --ep ep02     # 미완성 클립의 시작 이미지
python momo/hf_jobs.py record --library intro_wave --kind image --job-id <JOB_ID> --url '<URL>' --status generated --ep ep02
python momo/hf_jobs.py plan --library --kind clip --ep ep02      # 시작 이미지가 approved 인 것만
python momo/hf_jobs.py record --library intro_wave --kind clip --job-id <JOB_ID> --url '<URL>' --status generated --ep ep02
python momo/fetch_assets.py --ep ep02 --library                  # → library/clips/<이름>.mp4
```

이미지·클립 모두 에피소드 컷과 같은 확인 → **[승인]**.

### (7) 음성 — seed_audio

**음성 선택 (첫 편 1회. `config.voices.en/ko` 가 이미 있으면 건너뛰고 절대 바꾸지 않는다)**

1. `mcp__higgsfield__list_voices`(`size` 100, `next_cursor` 로 넘김) → EN·KO 각각 후보 3개
   (아이에게 맞는 따뜻한 목소리, KO 는 한국어 원어민 음색).
2. 톤: 따뜻하고 약간 높은 음, 느린 속도, 문장 끝을 올리는 말투. 필요하면 `config.higgsfield.audio_params` 에
   튜닝 값(예: `{"speech_rate": -10, "pitch_rate": 5}` — 범위는 `models_explore(type: "audio")` 로 확인)을 넣는다.
   이 값은 샘플과 모든 블록에 똑같이 들어간다.
3. 같은 문장으로 후보마다 1블록씩 샘플:
   ```bash
   python momo/hf_jobs.py voice-samples --lang en --voices <id1>,<id2>,<id3> --ep ep02
   python momo/hf_jobs.py voice-samples --lang ko --voices <id1>,<id2>,<id3> --ep ep02
   ```
   → payload 6개를 `generate_audio_batch` 로 → `jobs_wait` → 각 item 의 `record --voice-sample <id> --lang … --status generated`
   → `fetch_assets.py --ep ep02 --library` (`library/audio/<lang>/samples/`).
4. `show_generation_by_ids` 로 사용자에게 들려준다. **[승인]** 언어별 1개.
5. 승인: `python momo/hf_jobs.py record --voice-sample <id> --lang en --status approved --ep ep02` →
   `config.voices.en` 에 고정된다 (KO 도 같게). 커밋. 이후 에피소드에서 바꾸지 않는다.

**KO 음성 품질이 부족하면**(발음 뭉개짐, 억양 어색 — 후보 3개 모두) **[중단]** 하고 알린다. 다른 프리셋, 튜닝 값,
다른 엔진(`text2speech_v2` + variant) 중 무엇을 할지는 사용자가 정한다.

**고정 문장 (첫 편 1회)** — 인트로·아웃트로 EN/KO 4블록:

```bash
python momo/hf_jobs.py plan --library --kind audio --ep ep02
python momo/hf_jobs.py record --library intro --kind audio --lang en --job-id <JOB_ID> --url '<URL>' --status generated --ep ep02
python momo/fetch_assets.py --ep ep02 --library          # → library/audio/<lang>/<intro|outro>.*
```

사용자가 들어보고 **[승인]** → `record … --status approved`. 이후 에피소드에서는 재생성하지 않는다.

**에피소드 블록** — `[pause]` 로 나뉜 speech 블록 단위. 마커는 보내지 않는다 (plan 이 이미 뺀다).

```bash
python momo/hf_jobs.py plan --ep ep02 --kind audio --lang en        # --all 이면 전부
python momo/hf_jobs.py record --ep ep02 --cut c03 --kind audio --lang en --block 1 --job-id <JOB_ID> --url '<URL>' --status generated
python momo/fetch_assets.py --ep ep02
```

- `generate_audio_batch` 는 호출당 최대 12개. 씬 1 분량을 먼저 만들어 사용자에게 들려주고 **[승인]** 받은 뒤 나머지를 만든다.
- **음성 블록도 생성 1회로 센다** — 1편에 약 50블록이라 일일 생성 횟수 한도에 가장 먼저 걸릴 수 있다.

### (8) Song episodes (`manifest.song`, since ep02) — English only

1. Lyrics: one short line per speech block (`[pause 0.1]` separates lines), `bars` per cut (2 or 4), `beats`
   for the line starts, `card` on vocabulary close-ups. `validate_manifest.py` must pass.
2. Instrumental: `generate_audio` model `sonilo_music`, prompt with the tempo/instruments and "no vocals",
   `duration` ≥ total + 5 s → record immediately with `hf_jobs.py record --ep <ep> --song-music --job-id J
   --status generated` (add `--url` when done; credits = per-second rate × duration).
3. Lines: `hf_jobs.py plan --ep <ep> --kind audio --all` → generate_audio_batch (≤12; on `429 rate_limit_reached`
   stop and resume later in small batches) → record each job.
4. Push → momo-previews: `song_music_analysis` gives the real tempo/downbeat — copy it into
   `song.music.analysis` and set `song.bpm` to that tempo (no time-stretch). `<cut>_nar_en.wav` files are the
   lip-sync references.
5. **[승인]** Preview build (`momo-publish`, `upload: false`) → send the 720p copy → the user approves the song
   (lyrics, voice, music, captions) before any lip-sync clip is regenerated.
6. Lip-sync cuts: media_import_url each `<cut>_nar_en.wav` (raw.githubusercontent.com on momo-previews) →
   `hf_jobs.py narref` → `plan --kind clip` → generate → review mouth vs voice → approve → final build.

### (9) Finished-song episodes (`manifest.song.track`, since ep03) — the house format

Real sung nursery song, tight cuts: ~120 BPM, a new shot every 1–2 bars on the downbeat, singing ≥85 % of the
runtime (user decision 2026-09-30 after ep02 felt slow). The song comes from **Suno Pro** (user's plan since
2026-09-30; no official API — the user makes it on suno.com, never an unofficial MCP/automation, Suno's terms
forbid bots). Steps (all local, 0 Higgsfield credits until 6):

1. Lyrics: `episodes/<ep>/lyrics.md` (fenced block with [Intro]/[Chorus]/[Verse]/[Bridge]/[Outro] tags,
   (parentheses) = backing voices / echoes) + a style line. Give both to the user to paste into Suno (Custom).
2. **[승인]** The user picks a take and puts its WAV + stems (Vocals, Instrumental) in
   `~/ml/<ep>/suno/<take>/`. Check it: `tools/align_lyrics.py` (sidecar venv) must hear ≥95 % of the lyric words
   and report no "sung but not in lyrics" runs — otherwise fix `lyrics.md` to what is sung and re-align.
3. `song_track.py import --ep <ep> --mix … --vocals … --inst … --note "Suno …"` → `analyze` (tempo, bar grid,
   drift) → `lyrics --align …` → `sections` (lyric lines by bar).
4. Cuts: `bars` per cut from `sections` (first cut = intro to the first sung downbeat, L `intro_wave` with the
   library line; last cut = L `outro_bye` to `track.end`). Frontal Momo during singing = lip-sync (`wan2_7`,
   `clip_seconds` = ceil(window)); wide / object / listening shots = `seedance_2_0_mini` 4 s; repeats =
   `clip_from`. Word cards on the vocabulary close-ups. `validate_manifest.py --table` → plan.md,
   `estimate_credits.py` (cap 250).
5. **[승인]** plan.md (cut table with the lyrics under each cut, credits).
6. Images → clips as in 5단계 (one image, then scene 1, then the rest). Lip-sync clips: `song_track.py refs` →
   `publish` (release `media-<ep>`: song, vocals, refs) → media_import_url each ref URL → `hf_jobs.py narref`
   (window + track sha1 are pinned) → `plan --kind clip`. Review with `song_track.py sync` (clip + its slice).
7. `song_track.py status --approve` once the song is final, then build / publish as usual (the runner restores
   the song and stems from the release assets).

Lessons from ep03 (apply from ep04):
- Lyrics start with `[Intro - 2 bars, ukulele and hand claps]` so the library greeting has room (the ep03 Suno take
  sang from 1.6 s and the intro line had to go).
- Suno stems are optional — `demucs --two-stems vocals -n htdemucs_ft` on the Mac gives vocals + instrumental.
- Image prompts for songs: no "clear empty wall space in the upper third" (captions sit at the bottom; it caused flat
  bands) and no "holding X up high" framings (twice a stacked double-frame seam). Object close-ups name the set
  ("the pastel kitchen with mint cabinets softly blurred behind") so backgrounds match.
- Lip-sync refs upload straight to Higgsfield (`media_upload` presigned PUT, mp3) — no public hosting needed until
  publish; refs shorter than 3 s are padded (wan2_7 failed twice on a 1.93 s reference).
- Failed generations are not charged: reconcile `credits.spent` with `balance` at the end.

Lessons from ep04 (apply from ep05):
- Suno sang a count-in instead of the 2-bar intro again — put `[Instrumental intro - 4 bars, no vocals]` before the
  first sung line and check the take's first vocal onset before cutting.
- Counting shots (seedance): "the N objects drift / sway" pulls separate objects together (two clouds merged, 2 of 3
  tries). Keep the objects still and give the motion to something else ("sparkles twinkle, the leaves rustle, the
  clouds stay completely still with the same gap"). Check counts on frames across the whole cut, not only the start.
- Object close-ups: say what the object looks like ("pink daisies with yellow centers and green stems in the grass
  lawn with visible grass blades") — bare "pink flowers on plain grass" gave balloon shapes on a flat green floor.
- Lip-sync close-ups: a paw raised near the head can hide an ear (c20) — keep the paw "beside the cheek below the
  ear" and add "both long ears fully visible". Mid-air jump stills lift an ear — use "knees bent, ready to jump".
- A declined Higgsfield preset suggestion submits nothing; resend the same item with `declined_preset_id`.
- ep04 v1 felt unnatural (user): 51 one-bar cuts, the picture changed on the bar line while lines start ~0.4–0.8 s
  earlier (pickups), and 29 cuts had singing with Momo's mouth closed. v2 (the format from ep05 on):
  - cuts start on each sung line (`cut_at` ≈ first word − 0.1 s — check the vocal stem, the aligner can be 0.3 s off);
  - every shot where Momo is visible is a wan2_7 lip-sync clip with the action in the prompt (sings + claps/hops);
  - chorus lines are paired into 3.5–4 s shots; object shots use the whole motion clip;
  - reused lip-sync takes are placed by cross-correlating the vocal-stem loudness with the source window
    (chorus 3 was sung 0.3–0.46 s later than the aligner said).
- ep04 c33 ("Six little hops!") deformed: beady eyes, a wide flat head. The cause was the **start image** (a 3/4 walking
  stride with small eyes, from "both ready to hop"), and wan2_7 kept it from frame 0. Fixes now in the pipeline: the
  on-model gate above (c33 was 0.42; every other ep04 Momo shot is 0.75 or higher). Momo lip-sync start images are
  frontal with both feet on the ground. The motion opens with an identity sentence in positive wording ("Momo keeps
  exactly the same look as the first frame: big round head, huge round sparkly eyes with big white highlights…").
  Big moves like hops go to Ducky, and Momo "bounces gently on bent knees with both feet on the grass".

---

## 6. 조립 (6단계)

```bash
python momo/build.py --ep ep02 --lang en --check
python momo/build.py --ep ep02 --lang ko --check
```

출력: `episodes/ep02/out/ep02_<lang>.mp4`, `_thumb.jpg`, `_timeline.json`, `check_<lang>/check_<lang>.jpg`(컷별 확인 프레임 시트).

Read 로 확인하고, 고칠 것은 **manifest 에서** 고친 뒤 다시 build 한다 (바뀐 컷만 다시 렌더된다).

| 확인 | 어디서 | 고치는 법 |
|---|---|---|
| 키워드가 모모 얼굴을 가리는가 | `check_<lang>.jpg` | `text_pos: "bottom"`, 또는 `text_at` 조정 |
| 한글이 깨지는가(네모 두부) | `check_ko.jpg`, `ep02_ko_thumb.jpg` | `assets/fonts/` 에 한글 둥근 고딕, `config.fonts` |
| 이미지 테두리·액자 | `check_*.jpg` | `inset: 0.035` (자동 감지가 놓쳤을 때), 잘못 잘리면 `inset: 0` |
| 컷 사이 음성이 끊기거나 비는가 | `_timeline.json` 의 `warnings`, `estimated_audio: true` 인 컷 | 빠진 음성 생성·fetch, 긴 컷은 `duration` 조정 |
| 컷이 너무 짧거나 길다 | `_timeline.json` 의 `dur`, 전체 `total`(목표 약 150초) | `duration`, 나레이션 문장 |
| 썸네일 | `ep02_<lang>_thumb.jpg` | `thumbnail.cut`, `thumbnail.text`, `thumbnail.text_pos` |

완성본은 처음부터 끝까지 확인한다. Claude 는 영상 전체 프레임 시트로 흐름을 보고:

```bash
ffmpeg -v error -y -i momo/episodes/ep02/out/ep02_ko.mp4 -vf "fps=1/3,scale=320:-2,tile=8x8" -frames:v 1 /tmp/ep02_ko_full.jpg
```

소리(음성 끊김, KO 발음, BGM 덕킹)는 **사용자가 직접 들어보고** 확인하게 한다. build.py 가 조립에 성공하면
`manifest.status` 를 `assembled` 로 바꾼다 (애니매틱 제외) — 확인이 끝나면 manifest 를 커밋.

모음집(선택): `python momo/compile.py --lang en ep01 ep02 ep03 [--name NAME] [--title-prefix]`
→ `compilations/<name>_<lang>.mp4` + `_chapters.txt`(설명란 챕터).

## 7. 업로드 (7단계)

1. `manifest.upload.en` / `ko` 작성:
   - `title`: 부모 검색 키워드형, 100자 이하 (예: "Brush Your Teeth Song with Momo the Bunny | Morning Routine for Toddlers").
   - `description`: 한 줄 소개 + **학습 포인트 3줄** + 마무리 한 줄 + **해시태그 10개**. `<` `>` 금지.
   - `tags`: 10~15개, 총 500자 이하.
2. 검사와 기록:
   ```bash
   python momo/validate_manifest.py --ep ep02
   python momo/upload.py --ep ep02 --lang all --dry-run      # 요청 body 확인 (자격증명 불필요)
   python momo/episode_readme.py --ep ep02                    # episodes/ep02/README.md
   ```
   `notes.next_time` 에 다음 편에 반영할 점을 적는다.
3. 사용자에게 제목·설명·태그를 EN/KO 각각 출력하고, **"아동용 콘텐츠(made for kids)로 설정된다"** 는 점을 명시한다
   (upload.py 가 `selfDeclaredMadeForKids: true` 를 항상 넣는다. 댓글 꺼짐·맞춤 광고 없음 등 영향은 YOUTUBE_SETUP.md).
4. manifest·README 커밋·푸시. 그다음 둘 중 하나로 업로드:

**A. 세션에서 바로** — 클라우드 환경 설정의 환경변수에 `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`,
`YOUTUBE_REFRESH_TOKEN`(또는 `_EN` / `_KO`)이 있어야 한다. 비밀값을 채팅으로 받지 않는다.

```bash
python momo/upload.py --ep ep02 --lang all --privacy private
python momo/episode_readme.py --ep ep02
git add momo/episodes/ep02/youtube.json momo/episodes/ep02/README.md momo/episodes/ep02/manifest.json
git commit -m "ep02 업로드 기록" && git push          # youtube.json 을 반드시 커밋 (중복 업로드 방지)
```

**B. GitHub Action `momo-publish`** — 저장소 Secrets 필요. 러너가 fetch_assets → build → 업로드 → youtube.json·README 커밋을 한다.
Secrets 를 처음 넣었거나 바꿨으면 먼저 **momo-youtube-check** (`momo-youtube-check.yml`, 입력 `langs`)로 연결된 채널을 확인한다.
러너는 manifest·library.json 에 기록된 URL 로 에셋을 받으므로, 승인본이 전부 기록된 manifest 를 **먼저 푸시**해야 한다.
GitHub MCP 로:

```
mcp__github__actions_run_trigger {"method": "run_workflow", "owner": "<owner>", "repo": "<repo>",
  "workflow_id": "momo-publish.yml", "ref": "<현재 브랜치>",
  "inputs": {"ep": "ep02", "langs": "en,ko", "privacy": "private", "publish_at": "", "upload": "true"}}
```

또는 GitHub 의 Actions 탭 → momo-publish → Run workflow. 진행은 `mcp__github__actions_list` / `actions_get` /
`get_job_logs` 로 보고, 끝나면 `git pull --rebase` 로 기록 커밋을 받는다. (owner/repo 는 `git remote -v` 로 확인)

**공개 전략**: 먼저 `private` 로 올리고 → YouTube Studio 에서 영상·썸네일·아동용 설정을 확인 → 공개 또는 예약으로 전환한다.
예약은 `--publish-at 2026-10-03T18:00+09:00`(Action 입력 `publish_at`).
단, API 프로젝트가 **감사(audit)를 통과하기 전**에는 API 로 올린 영상이 비공개로 **잠겨서** Studio 에서도 공개로 못 바꾼다.
그동안 API 업로드는 검토용으로만 쓰고, 공개본은 사용자가 Studio 에서 `out/` 의 mp4·썸네일로 직접 올린다 —
[YOUTUBE_SETUP.md 7절](YOUTUBE_SETUP.md#7-중요--감사-전에는-api-업로드-영상이-비공개로-잠긴다).

- 이미 `youtube.json[lang].video_id` 가 있으면 건너뛴다. `--force` 는 새 영상을 하나 더 만든다.
- `--allow-missing` 애니매틱으로 만든 완성본은 upload.py·compile.py 가 거부한다 — 에셋을 받고 다시 build.
- 모음집: `python momo/upload.py --compilation NAME --lang en --title "…" [--tags "a,b"] [--thumbnail <jpg>]`
  (챕터가 설명에 붙는다. compile.py 는 썸네일을 만들지 않으므로 `--thumbnail` 로 지정 — 없으면 썸네일 없이 올린다).

---

## 부록 A. 새 세션에서 이어하기

```bash
git pull --rebase
python momo/doctor.py --ep ep02
python momo/hf_jobs.py status --ep ep02 --library
python momo/fetch_assets.py --ep ep02 --library
```

status 가 컷별 상태표와 **다음 작업** 목록(검토 대기 ●, 생성할 이미지·클립·음성, 내려받을 파일)을 준다.
검토 대기(●)부터 보여주고 승인받은 뒤, 5단계의 (0)~(7) 순서에서 멈춘 자리로 돌아가 공통 루프를 계속한다.
`manifest.notes.approvals` 로 어떤 게이트를 통과했는지 확인한다. Higgsfield 프로젝트는 `config.higgsfield.folder_id` 를 재사용한다.

## 부록 B. 세션 네트워크 제한

- **youtube.com / i.ytimg.com 차단** → 1단계의 `--backend api` 또는 `momo-research` 원격 수집.
- **Higgsfield 결과 CDN 차단**(`fetch_assets.py` 가 403/CONNECT 실패. 예: `d8j0ntlcm91z4.cloudfront.net`,
  `productionresultssa0.blob.core.windows.net`):
  - 권장: 사용자에게 알린다 — 클라우드 환경 설정(세션 제목 표시줄의 환경 메뉴 → Edit)의 Network access 에서
    그 호스트를 허용하거나 접근 수준을 넓힌다. 새 세션부터 적용된다.
  - 그동안 보기만 하려면: manifest/library.json 을 커밋·푸시 → `momo-preview` Action 이 미리보기(이미지 JPEG,
    클립 프레임 6장 시트)를 `momo-previews` 브랜치에 올린다 →
    ```bash
    git fetch origin momo-previews && mkdir -p /tmp/previews && git archive origin/momo-previews | tar -x -C /tmp/previews
    ```
    → `/tmp/previews/ep02/c05_image.jpg`, `/tmp/previews/library/sheet_momo.jpg` 등을 Read (`index.json` 에 목록).
  - 조립은 파일이 있어야 하므로 네트워크 허용 전에는 `momo-publish` 를 `upload: false` 로 돌려 러너에서 build 하고
    아티팩트(mp4·썸네일·timeline·확인 시트 `check_<lang>.jpg`)를 사용자가 받아 확인한다.
    같은 결과가 `momo-out` 브랜치(강제 푸시, 이력 없음)에도 올라가므로 세션에서 받아 Read·SendUserFile 할 수 있다:
    `git fetch origin momo-out && git archive origin/momo-out | tar -x -C /tmp/out`.
  - BGM 이 아직 없으면 `no_bgm: true` 로 확인용 빌드만 한다 (`build.py --allow-missing`, BGM 무음, 업로드 단계는 항상 건너뜀).
    최종본은 BGM 을 넣은 뒤 `no_bgm: false` 로 다시 돌린다.
