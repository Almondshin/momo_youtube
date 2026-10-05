# momo 파이프라인 구조 (구현 명세)

벤치마킹 → 기획 → 제작(Higgsfield MCP) → 조립(ffmpeg) → 유튜브 업로드까지를
**재실행 가능한 스크립트 + Claude 가 따라가는 런북**으로 나눈다.

- 스크립트로 되는 일: 채널 분석(yt-dlp), 자막·프레임 샘플링, manifest 검증, 크레딧 계산,
  생성 기록, 에셋 다운로드, 조립, 썸네일, 모음집, 업로드.
- Claude 가 MCP 로 하는 일: Higgsfield 이미지·영상·음성 생성, 결과를 눈으로 확인, 사용자 승인 받기.
  (docs/PRODUCTION.md 런북)

## 폴더

```
momo/
  config.json                 고정값 (캐릭터 블록, 스타일 락, 음성 ID, 폰트, 크레딧 캡, 렌더/오디오/유튜브 설정)
  requirements.txt
  momolib/common.py           경로(Paths), 설정 로드(load_config), JSON 입출력, run/probe, 폰트 탐색
  momolib/episode.py          나레이션 마커 파싱, 프롬프트 조립, manifest 검증, 컷 타임라인(plan_timeline)
  momolib/render.py           텍스트(키워드) 렌더, 켄번즈, 테두리 감지, 썸네일 — build/compile 공용
  momolib/audio.py            나레이션 타임라인, BGM 루프·덕킹, SFX, loudnorm — build/compile 공용
  momolib/vocal_onsets.py     보컬 스템 발성 시작 검출 (유성 150–3500 Hz / 자음 4–10 kHz flux, 피치) — numpy
  momolib/lyrics_refine.py    정렬(whisper) 단어 시작을 보컬 스템 발성에 맞춤 (song_track.py lyrics, 기본 켬)
  momolib/lipsync.py          조립된 영상의 립싱크 지연 측정 (song_track.py lipsync → cut.lip_shift 제안)
  momolib/tighten.py          노래 중간 보컬 없는 마디 잘라내기 + manifest 노래 시각 이동 (song_track.py tighten)
  youtube_delete.py           이 파이프라인이 올린 영상 삭제 (youtube.json 기록만, 사용자 요청 시) — Actions momo-youtube-delete
  momolib/song_style.py       Suno 스타일이 최근 편과 비슷한지·금지 후렴 검사 (song_track.py stylecheck)
  momolib/genrec.py           GenRec(생성 기록)·Slot·크레딧 계산 — hf_jobs/hf_api/fetch_assets/estimate 공용
  momolib/release.py          GitHub release(media-<ep>) 업로드 (gh) — song_track publish, hf_api archive 공용
  library/library.json        라이브러리 레지스트리 (캐릭터 시트, 고정 클립 5종, 고정 음성)
  library/{clips,audio/<lang>,sheets}/   (git 제외, URL 로 복원)
  assets/{bgm,sfx,fonts}/     사용자가 넣는 파일 (git 포함)
  templates/manifest.template.json
  episodes/<ep>/manifest.json 에피소드 기획 + 생성 기록 (git 포함)
  episodes/<ep>/{images,clips,audio/<lang>,out,.build}/   (git 제외)
  episodes/<ep>/youtube.json  업로드 결과 (git 포함)
  episodes/<ep>/README.md     에피소드 기록 (git 포함)
  episodes/<ep>/plan.md       4단계 표 (validate_manifest.py --table 이 생성)
  research/<slug>/            벤치마킹 결과 (report.md, data.json, meta/*.json, subs/*.txt 는 git 포함)
  research/<slug>/{raw,videos,frames}/   원본 영상·프레임·썸네일 (git 제외, 분석 후 삭제)
  compilations/               모음집 출력 (git 제외)
  tests/                      픽스처 생성 + 전체 테스트
  docs/                       ARCHITECTURE / PRODUCTION(런북) / MANIFEST / YOUTUBE_SETUP
```

## 공통 규칙 (모든 스크립트)

- `#!/usr/bin/env python3`, 파일 첫 docstring 에 용도와 사용 예. 표준 argparse.
- `from momolib.common import ...` 가 되도록 스크립트 맨 위에서
  `sys.path.insert(0, str(Path(__file__).resolve().parent))` (momo/ 를 path 에).
- 모든 스크립트는 `add_root_arg(parser)` 로 `--root` 를 받고 `get_paths(args)` 로 경로를 얻는다.
  테스트는 임시 root 로 돌린다. 절대 `momo/` 경로를 하드코딩하지 말 것.
- 진입점은 `main_wrapper(main)`. 실패는 `MomoError` (메시지는 한국어, 외부 명령 에러 원문 포함).
- `--ep` 는 `check_ep()`, `--lang` 은 `check_lang()` 으로 검증 (Actions 입력 주입 방지 겸용).
- 사용자에게 보이는 출력은 한국어. 코드 식별자·주석은 짧게.
- Python 3.10+ 호환. 외부 의존성은 requirements.txt 에 있는 것만:
  `yt-dlp, Pillow, numpy, google-api-python-client, google-auth, google-auth-oauthlib, google-auth-httplib2,
  higgsfield-client` (Higgsfield API — 키는 저장소 루트 `.env.local` 의 `HF_KEY`, git 제외, 절대 출력·커밋 금지).
- 외부 도구: ffmpeg/ffprobe 6.x (ubuntu 24.04 apt 버전 기준). ffmpeg 필터 표현식 트릭 대신
  Python(Pillow/numpy)으로 계산할 수 있으면 그쪽을 택한다 (버전 차이·지터 방지).

## manifest.json

`momolib/episode.py` 상단 docstring 이 필드 정의의 기준. 요약:

```jsonc
{
  "ep": "ep02", "status": "planning|producing|assembled|uploaded",
  "topic": {"en","ko"}, "title": {"en","ko"},
  "thumbnail": {"cut": "c07", "text": {"en": "RED YELLOW BLUE", "ko": "빨강 노랑 파랑"}, "text_pos": "top|bottom"},
  "bgm": null | "파일명(assets/bgm/)",
  "upload": {"en": {"title","description","tags":[],"playlist_id"}, "ko": {...}},
  "credits": {"estimate", "spent", "generations", "regenerations",
              "api_usd", "api_credits", "api_generations"},   // api_* = hf_api.py (API 선불 잔액, 구독 캡과 별개)
  "notes": {"v_over_reason", "approvals": [], "next_time": []},
  "cuts": [ { "id","scene","type", ... ,
              "gen": {"image": GenRec, "clip": GenRec},
              "audio_src": {"en": {"1": GenRec, "2": GenRec}, "ko": {...}} } ]
}
GenRec = {"status": "pending|generated|approved|rejected", "job_id", "url", "attempts", "credits",
          "history": [{"job_id","url","status","reason"}]}
```

파일 이름 규칙 (build 는 이 규칙으로 파일을 찾는다 — manifest 에 경로를 쓰지 않는다):
- `images/<cut>.png|jpg|webp`, `clips/<cut>.mp4`
- `audio/<lang>/<cut>_<n>.wav|mp3|...` — n = 나레이션 speech 블록 번호(1부터, [pause] 로 나뉨)
- 라이브러리: `library/clips/<name>.mp4`, `library/audio/<lang>/<intro|outro>.*`, `library/sheets/<momo|ducky>.png`

## 타임라인 (momolib.episode.plan_timeline — 이미 구현됨, 그대로 사용)

- 컷 길이 = max(xf_in + 나레이션(음성+[pause]) + tail_pad(0.4), min_cut(3.0), cut.duration),
  나레이션 없는 V/L 은 클립 길이. 프레임(1/30s) 단위 올림.
- 전환: 이전 컷과 `xf_in` 초 겹침 (fade=0.3, cut=0). 기본은 씬 경계만 fade.
- `start[i] = start[i-1] + dur[i-1] - xf_in[i]`. 전체 길이 = 마지막 start + dur.
- 나레이션은 컷 시작 + nar_offset(= xf_in) 부터 speech/pause 순서대로 놓는다.
- 키워드는 컷 시작 + text_at (기본 0.5) 에 등장해서 컷 끝까지.

## build.py --ep <ep> --lang en|ko

출력: `episodes/<ep>/out/<ep>_<lang>.mp4`, `<ep>_<lang>_thumb.jpg`, `<ep>_<lang>_timeline.json`,
`--check` 시 `out/check_<lang>/` 에 컷별 확인 프레임 + contact sheet (`check_<lang>.jpg`).

옵션: `--allow-missing`(애니매틱: 없는 클립은 이미지로, 없는 이미지는 컷 번호 카드로, 없는 음성은 무음 추정 길이),
`--check`, `--keep-temp`, `--thumbnail-only`, `--jobs N`(컷 세그먼트 병렬 렌더, 기본 min(4, CPU)).

1. `plan_timeline()` 으로 컷 계획.
2. 컷마다 세그먼트 `.build/<lang>/seg_<cut>.mp4` (1920x1080, 30fps, yuv420p, 무음, libx264 crf 12 veryfast):
   - 공통: 크롭-투-필(비율 유지 확대 후 중앙 크롭, 레터박스 금지). 테두리 인셋 크롭: `cut.inset` 숫자면 그 비율,
     null 이면 `render.detect_border()` 로 자동 감지해서 감지되면 `inset_default`(3.5%), 0 이면 끔.
   - V/L(video): 소스 클립을 그대로 사용 (켄번즈 금지). 필요 길이 > 클립 길이면 정방향 + 역방향(핑퐁) 1회,
     그래도 모자라면 마지막 프레임 정지(tpad clone). 짧으면 컷 길이에서 자름. fps 는 30 으로 변환.
   - S(image) 및 --allow-missing 의 image 대체: 켄번즈를 Python(Pillow)에서 프레임 단위 float 정밀도로 계산해
     ffmpeg stdin(rawvideo rgb24)으로 파이프. S 컷 순번 홀수=줌인, 짝수=줌아웃, 배율은 컷 id 해시로
     5~8% 사이 결정, 좌우 드리프트 ±1.5% 를 방향 교차, easeInOut. 빠른 움직임 금지.
     1920x1080 을 넘는 원본은 먼저 2x 여유(3840 폭) 이하로 줄여 속도 확보.
   - 키워드: `render.render_keyword_frames()` 가 만든 RGBA PNG 시퀀스(팝 애니메이션: 0.3초 동안
     scale 0.85→1.04→1.0, alpha 0→1, 이후 마지막 프레임 유지)를 overlay. 크기는 글자 높이 ≈ 화면 높이/8,
     폭이 90% 를 넘으면 축소. top 이면 상단 25% 밴드 중앙, bottom 이면 하단 25% 밴드 중앙.
     흰색/노란색 채움 + 두꺼운 검정 외곽선(Pillow stroke_width). 폰트는 `find_font(..., need_hangul=(lang=="ko"))`.
3. 세그먼트 연결: 한 번의 ffmpeg filter_complex 로 fade 는 `xfade=transition=fade:duration=xf:offset=...`,
   cut 은 `concat` — offset 은 plan 의 start 값(프레임 정수 기반)으로 계산해 누적 오차 없게.
4. 오디오 (`momolib/audio.py`, numpy):
   - 모든 음성 블록을 ffmpeg 로 48kHz mono float32 로 디코드 → 샘플 단위로 타임라인에 배치,
     [pause] 는 무음, `narration_gain_db` 적용.
   - BGM: manifest.bgm → config.audio.bgm_file → assets/bgm 첫 파일. 스테레오 48k 로 디코드, 전체 길이만큼 루프,
     기본 `bgm_gain_db`, 나레이션 구간(각 speech 블록 구간 ±attack/release)에서 `duck_db`(-16dB) 추가 감쇠,
     램프는 attack/release 초 선형(dB 도메인), 시작 페이드인·끝 페이드아웃.
     assets/bgm 이 비어 있으면 MomoError ("assets/bgm/ 에 BGM 을 넣어줘") — `--allow-missing` 일 때만 BGM 없이.
   - SFX: cut.sfx 를 컷 시작 + at 에 gain_db 로 믹스 (plan 에서 이미 없는 파일은 제외됨).
   - 믹스 → 48k 스테레오 WAV → ffmpeg loudnorm 2-pass (I=-14, TP=-1.5, LRA=11, 1차 측정값으로 2차 linear=true)
     → 48kHz 유지 (`-ar 48000` 을 loudnorm 뒤에 명시).
5. mux: H.264 High, yuv420p, 30fps, `crf`/`preset` from config, `-movflags +faststart`, AAC `aac_bitrate` 48kHz.
   영상·음성 길이는 plan 의 total 과 1프레임 이내로 일치해야 한다 (검증하고 어긋나면 에러).
6. 썸네일: manifest.thumbnail.cut 의 원본 이미지(없으면 해당 컷 세그먼트 프레임) 크롭-투-필 1280x720 +
   thumbnail.text[lang] 크게(폭 90% 이내, 필요하면 2줄, 노란 채움 + 두꺼운 검정 외곽선), JPEG, 2MB 미만 보장.
7. `<ep>_<lang>_timeline.json`: 컷별 {id, type, start, dur, xf_in, nar_len, keyword, text_at, source, estimated_audio},
   total, fps, warnings. compile.py 와 README 가 사용.
8. `--check`: 각 컷의 (start + text_at + 0.5) 시점 프레임을 1280 폭으로 뽑아 check_<lang>/ 와 격자 contact sheet 로 저장
   → Claude 가 "텍스트가 얼굴을 가리는지 / 한글이 깨지는지" 눈으로 확인하는 용도.

## compile.py --lang en ep01 ep02 ... [--name NAME] [--title-prefix]

- 각 에피소드 `out/<ep>_<lang>.mp4` 사이에 `library/clips/transition.mp4` (1920x1080/30fps 로 정규화, 무음 → BGM 없음,
  assets/sfx 에 whoosh/transition 이 있으면 얹음) 삽입. 에피소드 파일이 없으면 먼저 build 하라고 에러.
- 출력: `compilations/<name>_<lang>.mp4` (+ loudnorm -14 재적용) 와 `<name>_<lang>_chapters.txt`
  (첫 줄 `0:00`, 각 에피소드 시작 시각 + 제목(manifest.title[lang] 또는 upload.title)). 챕터 규칙: 3개 이상, 각 10초 이상 — 안 맞으면 경고.
- 30분 이상이 되면 "모음집(compilation) 축" 이라는 안내 출력.

## analyze_channel.py (1단계)

`python analyze_channel.py --url <채널 URL> [--backend ytdlp|api] [--out research/<slug>] [--limit 2000]
 [--sleep-requests] [--cookies FILE] [--cookies-from-browser chrome] [--now ISO]`
`python analyze_channel.py report --dir research/<slug> [--labels labels.json]`  (재계산만, 네트워크 없음)

- 먼저 `yt-dlp -U` 시도 (pip 설치본이면 `pip install -U yt-dlp` 안내/시도). 실패해도 계속하되 로그.
- (a) `yt-dlp --flat-playlist -J "<url>/videos" [--playlist-end 2000]` → `raw/channel.json` (git 제외) 와
  `channel_summary.json` (id/title/view_count/duration, 구독자 수만). 2000 초과 여부를 기록하고 "일부 기준" 명시.
- (b) 인기순: `<url>/videos?view=0&sort=p&flow=grid` 시도 → 결과가 조회수 내림차순인지 검사 → 맞으면 상위 5,
  아니면 (a) 를 view_count 내림차순 정렬한 상위 5. 어느 쪽인지 data.json/report 에 기록.
- (c) 최신 15 = (a) entries 앞 15.
- (d) 합집합(≤20)은 `yt-dlp --skip-download -J <video_url>` → `meta/<id>.json` 에 필요한 필드만 저장
  (id,title,upload_date,timestamp,view_count,like_count,comment_count,duration,tags,description,thumbnail,categories).
- 에러 대응 순서: 봇 확인/403 → `--sleep-requests 1` 추가 재시도 → `--cookies-from-browser`/`--cookies` 가 주어졌으면 재시도
  → 그래도 실패하면 MomoError 로 **에러 원문 그대로** 출력하고 중단.
- `--backend api`: youtube.com 이 막힌 환경용. `YOUTUBE_API_KEY` 로 Data API v3 (channels.list → uploads 플레이리스트
  → playlistItems.list → videos.list) 로 같은 데이터 구조를 만든다. 인기순은 API 로 전체를 받아 정렬. report 에 백엔드 명시.
- 계산 (`--now` 로 기준 시각 고정 가능, 기본 현재 UTC):
  - 업로드 72시간 미만은 평균에서 제외하고 목록으로 명시. 30분(1800초) 이상은 모음집 축으로 분리.
  - 역대 최고작 / 최근 단편 평균 배수, 구독자 대비 조회수 배수(최고작, 최근 평균),
    역대 5개가 받아온 목록 총 조회수에서 차지하는 비중, 채널 상태(성장/정체/하락) + 판단 근거 수치
    (최근 15 단편 중앙값 vs 그 이전 45개 단편 중앙값, 일평균 조회수 비교).
  - 최근 15개 축 분류: 학습 소재(색/숫자/알파벳·단어/동물/생활습관/탈것/감정/기타), 형식(동요/스토리/퀴즈·따라하기/모음집),
    길이 구간(≤3분/3~10분/10~30분/30분+), 썸네일 주인공(캐릭터 클로즈업/사물/텍스트 위주 — 자동 판정 불가 → "미분류",
    labels.json 으로 Claude 가 눈으로 보고 채움), 제목 검색 키워드 포함 여부. EN/KO 키워드 사전으로 제목+태그 판정.
    labels.json 이 주는 값은 자동 판정을 덮어쓴다.
  - 축별 그룹 평균 조회수·개수, 축별 격차(최대 평균/최소 평균, n≥2 그룹 기준) → 격차가 가장 큰 축을 원인 후보로.
  - 최신 15 중 상위 3개가 역대 성공작과 같은 포맷(형식·소재·길이 구간)인지 비교.
- 출력: `data.json`(모든 수치), `report.md`(한국어 표), `labels.template.json`(20개 영상 id·제목·자동 판정값·빈 thumbnail_subject).

## sample_videos.py (2단계)

`python sample_videos.py --dir research/<slug> [--ids ID ...] [--frames 36] [--cleanup]`
- 기본 대상: data.json 의 역대 1위 + 최근 1위 (중복이면 1개).
- 자막: `yt-dlp --skip-download --write-auto-subs --write-subs --sub-lang "en,ko" --sub-format json3 -o "raw/%(id)s"`
  → json3 events → `[mm:ss.s] 텍스트` 줄, 자동 자막 중복(롤링) 줄 제거 → `subs/<id>.<lang>.txt`. 없으면 "건너뜀" 기록.
- 영상: `yt-dlp -f "bv*[height<=480]" -o "videos/%(id)s.%(ext)s"` → 균등 간격 프레임 30~40장 `frames/<id>/f_###.jpg`
  + contact sheet `frames/<id>_sheet.jpg` (Claude 가 보고 분석).
- 샷 전환: `ffmpeg -vf "select='gt(scene,0.3)',showinfo" -f null -` → 전환 시각 목록, 샷 수, 평균 샷 길이(초), 표준편차.
- 썸네일: 역대 1·2위 + 최근 1위·최하위(72시간 미만 제외) → `raw/thumbs/<id>.jpg` (maxresdefault → hqdefault 폴백).
- 결과는 `samples.json` 에 기록하고 data.json 의 samples 에 병합.
- `--cleanup`: videos/, frames/, raw/ 삭제 (분석 끝나면 반드시 실행 — 프레임 재사용 금지).

## 제작 보조 스크립트

- `new_episode.py --ep ep02 [--topic-en --topic-ko]` : 템플릿 복사, 폴더 생성, 이미 있으면 거부(--force 없으면).
- `validate_manifest.py --ep ep02 [--table] [--strict]` : errors/warnings 출력, errors 있으면 exit 1,
  `--table` 이면 `episodes/<ep>/plan.md` 에 4단계 표(| 컷 | 씬 | 타입 | 나레이션 EN | 나레이션 KO | 화면 키워드 EN / KO |
  이미지 프롬프트(조립된 전체) | 모션 지시 |) + 타입 개수 + 제목/썸네일 문구 + 예상 길이(음성 추정) 작성.
- `estimate_credits.py --ep ep02 [--regen-rate 0.2] [--json]` : config.higgsfield.unit_costs 로
  (라이브러리 미완성분: 시트, 클립 이미지+영상, 고정 음성 4개, 음성 샘플 6개) + (에피소드: 아직 approved 아닌 V/S 이미지,
  V 클립, 음성 블록 EN/KO) + 재생성 여유 → 표와 합계. `credits.episode_cap` 초과면 exit 2 와 "중단 조건" 문구.
- `hf_jobs.py` — MCP 생성 작업의 계획·기록·진행표. Claude 는 이것으로 payload 를 받고 결과를 기록한다.
  - `plan --ep ep02 --kind image|clip|audio [--lang en] [--cuts c02,c03] [--all]` → 아직 approved 가 아닌 항목의
    MCP payload JSON 목록 (model, prompt(조립 완료), aspect_ratio, resolution, duration, medias 자리표시, voice_id/voice_type,
    folder_id). clip 은 image 가 approved 인 V 컷만. audio 는 tts_blocks() 기준, voice 는 config.voices[lang].
  - `plan --library [--kind sheet|image|clip|audio]` → 라이브러리 미완성분 payload.
  - `record --ep ep02 --cut c03 --kind image|clip [--job-id --url] --status generated|approved|rejected [--reason] [--credits N]`
    `record --ep ep02 --cut c03 --kind audio --lang en --block 1 ...`
    `record --library intro_wave --kind image|clip ...`, `record --library intro --kind audio --lang en ...`,
    `record --sheet momo ...` → GenRec 갱신(history 추가, attempts+1, generated 일 때 credits 누적,
    같은 항목 두 번째 생성부터 regenerations+1), manifest.credits 갱신. 원자적 저장.
  - `status --ep ep02 [--library]` → 컷별 image/clip/audio(en,ko) 상태표 + 크레딧 합계 + 남은 작업 (중단 후 재개용).
- `fetch_assets.py --ep ep02 [--library] [--force]` : GenRec.url 이 있고 status 가 generated/approved 인 항목을
  규칙 경로로 다운로드 (urllib, 재시도 3회, Content-Type/확장자로 확장자 결정, 다운로드 후 PIL/ffprobe 로 검증).
  이미 있으면 건너뜀. 실패 목록을 끝에 표로.
- `hf_api.py` — Higgsfield **API**(공식 SDK `higgsfield-client`, 별도 선불 잔액·USD)로 클립 생성. MCP(구독)와 같은 기록을 쓴다.
  - `check` : 없는 request id 의 status 조회 (과금 없음) → 404 키 정상 / 401 키 틀림(exit 1) / 403 잔액 부족(exit 3, 키는 정상).
  - `run --ep ep05 --kind clip [--cuts] [--lang] [--dry-run] [--max-parallel 4] [--max-usd N] [--deadline 1800]` :
    항목 = `hf_jobs.plan_episode(..., api=True)` (clip 만 — 노래 파일 컷은 nar_ref 대신 `audio/refs/<cut>_<lang>.wav` 를 직접
    올리므로 MCP media id 가 필요 없다). 모델 매핑 `api_payload()`: wan2_7 → `wan/v2.7/image-to-video`
    (image_url·audio_url·end_image_url·duration 2–15·720p|1080p), seedance_2_0_mini|2_0 → `bytedance/seedance-2.0/image-to-video`
    (4–15초, generate_audio false), seedance_2_5 → `bytedance/seedance-2.5/image-to-video`, 립싱크면 `…/reference-to-video`
    (image_urls·audio_urls). 매핑 없는 모델·여러 블록 나레이션 → MCP 목록. 입력 파일은 SDK `upload_file`(presigned PUT,
    WAV 만 — 그 밖의 음성은 ffmpeg 로 WAV 변환) → 안 되면 manifest URL. 로컬 파일은 `.sources.json` 의 job_id 가 승인 job 과
    같을 때만 쓴다. refs 는 길이 = max(컷 구간, 3초) 를 확인.
  - 요청 흐름 (`HfApi`, 스레드 풀): 업로드 → `POST /estimate/<model>`(과금 없음, --max-usd 확인) → GenRec.`api_pending`
    {key, model, body, attempt} 저장 → `POST /<model>` + `Idempotency-Key`(uuid5: ep|cut|kind|lang|attempt|model|시작 이미지 job;
    408/429/5xx/네트워크는 같은 키·body 로 최대 4회, 400 동시 요청 한도는 대기 후 재전송) → 접수 즉시 `apply_record(generated,
    job_id "api:<request_id>", cost 0)` + history.api {model, request_id, idempotency_key, usd_est, credits_est, correlation_id},
    credits.api_generations → 폴링 2초→10초(지터)·deadline → completed: url 기록, history.api.{usd,credits,charged},
    credits.api_usd 누적, `fetch_assets.download` 로 clips/ 에 받기 / failed·nsfw·canceled: rejected (과금 없음) /
    시간 초과·모르는 상태·연결 오류: generated(URL 없음) 유지 → 다음 run 이 폴링만 이어서. 접수 여부 불명이면 api_pending 이
    남고 다음 run 이 같은 키·body 를 재전송 (원래 request_id, 중복 과금 없음; 409 = 같은 키 처리 중 → 접수 불명).
    api_pending 이 남은 클립은 `hf_jobs.plan_episode`(MCP) 가 blocked 로 막고, 403 폴백 plan 에도 넣지 않는다 (재전송 못 한
    replay 는 UNSURE). 콘솔에서 접수 안 됨을 확인한 뒤에만 `forget --ep --cut [--lang] --yes` 로 지운다.
  - HTTP 403(402) = 잔액 부족: 재시도 없이 새 제출 중단, 남은 항목을 `hf_jobs.plan_episode` JSON(MCP plan)으로 출력, exit 3.
    exit 2 = --max-usd 초과(제출 없음), 1 = 실패·미확인 있음. 구독 `credits.spent`·캡 계산은 API 작업에 영향받지 않는다.
  - `archive --ep ep05 [--tag] [--dry-run]` : job_id 가 `api:` 이고 generated/approved 인 항목의 파일(없거나 `.sources.json` 상
    그 job·URL 의 파일이 아니면 그 URL 에서 먼저 받음)을
    release `media-<ep>` 에 `<ep>_<stem>_<sha1 8자>.<ext>` 로 올리고 GenRec.url·history.url 을 그 주소로 (원래 주소는
    history.api.output_url), `.sources.json` 도 갱신 → fetch_assets 가 그대로 복원.
- `doctor.py [--ep ep02] [--update-ytdlp] [--ci]` : yt-dlp(버전), ffmpeg/ffprobe(libx264, xfade, loudnorm),
  Python 모듈, assets/fonts 한글 지원 폰트, assets/bgm 파일, assets/sfx(선택), library 상태, config.voices,
  (ep 가 있으면) manifest 검증 + 에셋 존재 여부, YouTube 자격증명 env 존재 여부(값은 출력 금지).
  멈춰야 할 항목(폰트/BGM 없음 등)은 ✖, 경고는 △, 정상은 ✔. ✖ 가 있으면 exit 1.
- `episode_readme.py --ep ep02` : episodes/<ep>/README.md — 주제, 컷 수(타입별), 사용 크레딧, 생성/재생성 횟수,
  길이(EN/KO, timeline.json 있으면), 제목·설명·태그(EN/KO), 업로드 결과(youtube.json), "아동용(made for kids) 설정",
  다음 편에 반영할 점(notes.next_time).

## upload.py (7단계 자동 업로드)

`python upload.py --ep ep02 --lang en|ko|all [--privacy private|unlisted|public] [--publish-at ISO8601]
 [--dry-run] [--force] [--no-thumbnail]`
`python upload.py --compilation NAME --lang en --title ... ` (모음집 업로드, chapters.txt 를 설명에 붙임)

- 메타: manifest.upload[lang] (title 없으면 manifest.title[lang]). 설명·태그 검증(validate_manifest 규칙 재사용).
- `status.selfDeclaredMadeForKids = true` 고정 (config.youtube.made_for_kids 가 false 여도 경고 후 true — 아동용 채널).
  `containsSyntheticMedia` 는 config 가 true 일 때만 넣는다. categoryId, defaultLanguage/defaultAudioLanguage.
  `--publish-at` 이면 privacyStatus=private + publishAt (UTC 로 변환).
- 자격증명: env `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN_<LANG>` → 없으면
  `YOUTUBE_REFRESH_TOKEN` → 없으면 `momo/.secrets/youtube_<lang>.json`. 어떤 값도 출력하지 않는다.
- google-api-python-client resumable 업로드(청크 8MB), 5xx/네트워크 에러 지수 백오프 재시도(최대 8회), 진행률 출력.
- 썸네일 `thumbnails.set` (실패하면 경고: 채널 인증 필요할 수 있음), `playlist_id` 있으면 playlistItems.insert.
- 결과를 `youtube.json[lang]` = {video_id, url, privacy, publish_at, uploaded_at, thumbnail_set, playlist_id, file_sha256}.
  이미 video_id 가 있으면 `--force` 없이는 건너뜀 (중복 업로드 방지). manifest.status 는 "uploaded".
  사용자가 YouTube 에서 지운 영상은 기록을 지우지 않고 `deleted_at`(날짜)·`deleted_note` 를 붙인다 — video_id 가 남아
  자동 재업로드되지 않고, README 의 공개 상태 칸이 "삭제됨 (날짜)" 이 된다.
- `--dry-run`: 자격증명·네트워크 없이 요청 body 를 출력만.
- 안내: API 프로젝트가 감사(audit) 전이면 YouTube 가 업로드 영상을 비공개로 잠근다 → docs/YOUTUBE_SETUP.md.

## youtube_auth.py

`python youtube_auth.py --lang en --client-secrets client_secret.json [--port 8080] [--no-browser]`
InstalledAppFlow(run_local_server) → scopes `youtube.upload` + `youtube` → refresh token 을
`momo/.secrets/youtube_<lang>.json` 에 저장하고 GitHub Secrets 에 넣을 이름을 안내 (값을 화면에 출력할지는 `--print-token` 일 때만).

## GitHub Actions

- `.github/workflows/momo-ci.yml`: push/PR 에서 `momo/**` 변경 시 — apt `ffmpeg fonts-nanum`, pip requirements,
  `bash momo/tests/run_all.sh` (픽스처 root 에서 validate → build en/ko → compile → upload --dry-run).
- `.github/workflows/momo-publish.yml`: `workflow_dispatch` 입력 ep, langs(en,ko), privacy, publish_at, upload(bool).
  입력은 전부 env 로 넘기고 스크립트가 검증 (`${{ }}` 를 run 문자열에 직접 넣지 말 것 — 주입 방지).
  단계: checkout → python 3.11 → apt ffmpeg → pip → doctor --ci → fetch_assets(--library 포함) → build(lang 별) →
  artifact 업로드(mp4, jpg, timeline, 7일) → upload.py(시크릿: YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN[_EN/_KO]) →
  youtube.json·README.md 커밋 푸시 (permissions: contents: write, concurrency 로 같은 ep 동시 실행 방지).

## 테스트

- `tests/make_fixture.py --root <tmp>`: config.json/library.json/templates 복사, 시스템 폰트(한글 지원: fonts-nanum 또는
  wqy-zenhei 등 자동 탐색) 를 assets/fonts 로 복사, ffmpeg 로 BGM(화음 사인파 20초)·sfx(pop) 생성,
  library 클립 5종(testsrc2 1280x720 24fps 5초, 컷마다 다른 색)·고정 음성(사인 비프, 길이 1.2~2초),
  ep99 manifest (컷 24개: L4 V13 S7, 씬 5, [pause]/[chant] 포함, 텍스트 top/bottom/yellow 섞기, 한 컷은 테두리 있는 이미지,
  한 V 컷은 나레이션 > 5초(핑퐁 경로), 한 V 컷은 > 10초(프리즈 경로), sfx 1개), 이미지(Pillow 도형 1536x864 등 비율 다르게),
  클립, 음성 블록(사인 비프 길이 다양 — en/ko 길이 다르게).
- `tests/run_all.sh`: 위 픽스처로 전체 실행 + 결과 검증(ffprobe: 1920x1080, 30fps, yuv420p, h264, aac 48k, 길이=timeline total±1프레임,
  loudness ≈ -14 LUFS ±1), validate/estimate/hf_jobs/fetch_assets(로컬 file:// 또는 http.server)/upload --dry-run.
- `tests/test_tools.py` 의 hf_api 테스트는 네트워크·키·과금 없이 돈다: `FakeApi`(httpx.MockTransport)가 업로드·estimate·제출·
  status 를 흉내 내고, SDK `SyncClient` 의 httpx 클라이언트를 같은 MockTransport 로 바꿔 실제 SDK upload 경로도 탄다.
  `hf_api.make_api` 와 `momolib.release` 함수는 테스트에서 바꿔 끼운다.
