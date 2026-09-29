# manifest.json 레퍼런스

`episodes/<ep>/manifest.json` 하나가 에피소드의 기획(컷 표)과 생성 기록을 모두 담는다.
build·validate·estimate·hf_jobs·fetch_assets·upload 가 전부 이 파일을 읽는다.
필드 정의의 기준은 `momolib/episode.py` 상단 docstring 이고, 이 문서는 그 해설이다.

- 새로 만들기: `python momo/new_episode.py --ep ep03 --topic-en "Rainy Day" --topic-ko "비 오는 날"`
  (`templates/manifest.template.json` 복사 — 인트로 c01·아웃트로 c02 L 컷만 들어 있다.
  컷을 채울 때 아웃트로는 마지막 번호로 옮긴다: c01 … c24)
- 검사: `python momo/validate_manifest.py --ep ep03` (errors 가 있으면 exit 1, 제작·조립 진행 금지)
- 표 만들기: `python momo/validate_manifest.py --ep ep03 --table` → `episodes/ep03/plan.md`
- manifest 는 git 에 커밋한다. 이미지·클립·음성 파일은 git 제외 — 기록된 URL 로
  `python momo/fetch_assets.py --ep ep03` 가 언제든 복원한다.

## 1. 최상위 필드

| 필드 | 형식 | 설명 |
|---|---|---|
| `schema` | `1` | 형식 버전 |
| `ep` | `"ep03"` | `ep` + 숫자 2~3자리. 폴더 이름과 같아야 한다 |
| `status` | `planning` → `producing` → `assembled` → `uploaded` | planning = new_episode 직후, producing = 첫 생성 기록 때 hf_jobs.py 가 자동으로, assembled = build.py 가 조립에 성공하면 자동으로 (`--allow-missing` 애니매틱은 제외), uploaded = upload.py 가 자동으로 |
| `topic` | `{"en","ko"}` | 주제 (README·표에 사용) |
| `benchmark` | `{"channel_url","research_dir","chosen_axis"}` | 어떤 분석·어떤 축을 근거로 주제를 골랐는지 |
| `characters` | `["momo","ducky"]` | 등장 캐릭터 (기록용) |
| `title` | `{"en","ko"}` | 부모가 검색하는 키워드형 제목. `upload.<lang>.title` 이 비면 이 값으로 업로드, compile 챕터 제목에도 사용 |
| `thumbnail` | `{"cut","text":{"en","ko"},"text_pos"}` | 썸네일 원본 컷(모모 클로즈업 + 핵심 사물), 문구는 3단어 이하, `text_pos` top/bottom |
| `bgm` | `null` 또는 파일명 | `assets/bgm/` 기준 파일명. null 이면 `config.audio.bgm_file` → `assets/bgm/` 의 첫 파일 |
| `upload` | `{"en": {...}, "ko": {...}}` | 7단계 업로드 메타 — 아래 표 |
| `credits` | `{"estimate","spent","generations","regenerations"}` | `estimate` 는 `estimate_credits.py --save` 가 적는 예상치. 나머지는 `hf_jobs.py record` 가 자동 누적 |
| `notes` | `{"v_over_reason","approvals":[],"next_time":[]}` | V 컷 15개 초과 사유(없으면 validate error), 승인 기록(날짜 + 무엇을), 다음 편에 반영할 점(README 에 들어감) |
| `cuts` | `[컷, ...]` | 순서 = 재생 순서 |

`upload.<lang>`:

| 필드 | 규칙 (validate/upload 가 검사) |
|---|---|
| `title` | 100자 이하, `<` `>` 금지. 비면 `title[lang]` |
| `description` | 5000바이트 이하, `<` `>` 금지. 학습 포인트 3줄 + 해시태그 10개 |
| `tags` | 문자열 배열, 총 길이 500자 이하 (공백 있는 태그는 따옴표 2자 추가로 계산) |
| `playlist_id` | 넣으면 업로드 후 그 재생목록에 추가. null 이면 `config.youtube.playlist_id[lang]` |

## 2. 컷 필드

| 필드 | L | V | S | 설명 |
|---|:-:|:-:|:-:|---|
| `id` | ● | ● | ● | `c01`, `c02` … 고유. 파일 이름의 기준 |
| `scene` | ● | ● | ● | 1..5 정수. 줄어들면 error |
| `type` | ● | ● | ● | `L` 라이브러리 / `V` 영상(이미지→5초 클립) / `S` 정지(이미지 + 켄번즈) |
| `library_clip` | ● | | | `intro_wave` `outro_bye` `say_with_me` `cheer` `transition` 중 하나 |
| `library_audio` | ○ | | | `intro` / `outro` — 고정 음성(`library/audio/<lang>/`)을 쓴다. 나레이션이 `config.fixed_lines` 와 글자까지 같아야 하고 `[pause]` 금지 |
| `narration` | ○ | ○ | ○ | `{"en","ko"}`. 마커 `[pause 1.5]` `[chant]` 허용 (4절). EN 25단어·KO 40자 안팎 권장 |
| `chant` | ○ | ○ | ○ | `true` 면 이 컷 전체를 챈트 블록으로 표시 (`[chant]` 마커와 같은 효과) |
| `keyword` | ○ | ○ | ○ | `{"en":"RED","ko":"빨강"}` 화면 키워드 1개. 두 단어 초과·문장부호는 경고. 빈 문자열이면 텍스트 없음 |
| `image_prompt` | | ● | ● | 장면만 쓴다. 캐릭터 블록·스타일 락은 자동 조립 (3절) |
| `momo` | | ○ | ○ | `false` + `[Momo]` 태그 없음 → 캐릭터 블록 생략 (사물만 나오는 컷) |
| `motion` | | ● | | 작은 모션만: "small hop in place", "waves one paw", "ears bounce". camera/zoom/pan/morph/spin/fast 등은 경고 |
| `transition` | ○ | ○ | ○ | 이 컷으로 **들어올 때** `fade`(0.3초 크로스페이드) / `cut`. 기본: 씬이 바뀌면 fade, 같은 씬이면 cut. 첫 컷은 무시 |
| `text_at` | ○ | ○ | ○ | 키워드 등장 시점(컷 시작 기준 초). 기본 0.5, 최대 `컷 길이 − 0.5` 로 잘림 |
| `text_pos` | ○ | ○ | ○ | `top`(기본, 상단 25% 밴드 중앙) / `bottom`(하단 25% 밴드) — 모모 얼굴이 위쪽이면 bottom |
| `text_color` | ○ | ○ | ○ | `white`(기본) / `yellow` |
| `duration` | ○ | ○ | ○ | 최소 길이(초). 나레이션보다 짧게는 못 줄인다(경고 후 무시) |
| `lead` / `tail` | ○ | ○ | ○ | Picture-only seconds before / after the narration (0~5; default 0 / `render.tail_pad`). E.g. a musical lead-in on the first cut, a tail on the last cut for the BGM fade-out |
| `fill` | ○ | ○ |   | How a clip shorter than its cut is extended: `hold` (default — slow-mo ≤1.25x with motion interpolation, then hold the last frame, gentle push-in), `loop` (crossfade into a second pass), `pingpong` (old) |
| `inset` | ○ | ○ | ○ | 테두리 제거 인셋 크롭 비율. `null`(기본) = 자동 감지 후 감지되면 3.5%, `0` = 끔, `0.03`~`0.04` = 강제 |
| `sfx` | ○ | ○ | ○ | `[{"file":"pop.wav","at":0.5,"gain_db":-6}]` — `assets/sfx/` 파일, 컷 시작 + `at` 초. 파일이 없으면 경고 후 생략. Stock set from `make_music.py`: pop, sparkle, boing, whoosh, brush, swish, splash, chime |
| `gen` | | ● | ● | `{"image": GenRec, "clip": GenRec}` (clip 은 V 만) — hf_jobs.py 가 기록 |
| `audio_src` | ○ | ○ | ○ | `{"en": {"1": GenRec, "2": GenRec}, "ko": {...}}` — 키 = speech 블록 번호(문자열) |

● 필수 · ○ 선택. validate 가 error 로 막는 것: id 형식·중복, type, scene 역행, L 의 library_clip, V/S 의
image_prompt, V 의 motion, 기존 IP 이름(cocomelon, pinkfong, peppa, 뽀로로 …), 남은 `[태그]`,
text_pos/transition 값, library_audio 고정 문장 불일치, V>15 인데 `notes.v_over_reason` 없음,
thumbnail.cut 이 없는 컷, 제목·설명·태그 한도.
경고: 컷·타입·씬 개수 목표(22~28 / V 12~15 / S 6~8 / L 3~4 / 5씬), 나레이션 길이, 키워드 반복 3회 미만,
프롬프트의 글자 유발 단어(text, sign, label …)·무서운 단어(dark, storm, monster …), 모션 위험 단어,
첫 컷 intro_wave / 마지막 컷 outro_bye 아님, 썸네일 문구 3단어 초과.

### L 컷의 두 가지 음성

- `library_audio` 가 있음(인트로·아웃트로): 라이브러리 고정 음성을 그대로 쓴다. 에피소드마다 생성하지 않는다.
- `library_audio` 가 없음(say_with_me, cheer 등): 클립만 라이브러리, 나레이션은 이 에피소드에서 TTS 로 만든다
  (`audio/<lang>/<cut>_<n>.*`).

## 3. 이미지 프롬프트 조립

`compose_image_prompt()` = `config.character.momo` + `, ` + 장면 + `, ` + `config.style_lock`.

- `[Momo]` 태그는 지워지고 캐릭터 블록이 맨 앞에 붙는다. 태그가 없어도 `momo` 가 false 가 아니면 붙는다.
- 조연 태그(`config.character.tags`: `[Ducky]` `[Croc]` `[Shark]`)는 그 자리에서 조연 블록으로 바뀐다.
- 모르는 `[태그]` 가 남으면 error.
- 글자·숫자·간판·로고는 쓰지 않는다. 텍스트는 전부 조립(build)에서 얹는다.
- Higgsfield Element 가 등록된 캐릭터(`config.higgsfield.element_ids`)가 나오는 컷이면 `hf_jobs.py plan` 이
  프롬프트 앞에 `<<<element_id>>>` 자리표시를 붙인다. manifest 에는 직접 쓰지 않는다.
- V 클립 프롬프트 = `motion` + `config.video_prompt_suffix` ("Keep the character design exactly the same. Static fixed camera …").

## 4. 나레이션 마커

```
"Red boots! Can you say boots? [pause 1.5] Boots! Great job!"
 └─ speech 블록 1 ──────────────┘  └ 무음 1.5초 ┘ └ speech 블록 2 ┘
```

- `[pause]` = 무음 `config.render.default_pause`(1.5초). 길이 지정: `[pause 1.5]` `[pause 2]` `[pause:2]`
  `[pause=2]` `[pause 1.5s]` `[pause 2초]` (대소문자 무관).
- `[pause]` 는 TTS 로 보내지 않는다. 문장을 블록으로 나누는 경계이고, 조립 때 그 자리에 무음이 들어간다.
  "같이 말해볼까?" 뒤의 따라 말하기 대기 구간이 이것이다.
- speech 블록 번호는 1부터. 블록마다 음성 파일 1개: `audio/<lang>/<cut>_<n>.*`.
  EN 과 KO 의 블록 수는 달라도 된다 (언어별로 따로 센다).
- `[chant]` = 이 블록은 노래 대신 리듬감 있게 읽는 챈트라는 표시. 마커 글자는 TTS 로 보내지 않는다.
  TTS 는 노래를 부를 수 없으므로 가사를 짧고 반복적인 챈트로 쓴다.
- 그 밖의 `[...]` 도 TTS 텍스트에서 지워진다. 무음이 되는 것은 `[pause]` 뿐이다.
- 인트로·아웃트로 고정 문장(`config.fixed_lines`)은 매 에피소드 동일하게 둔다.
- **음성을 만든 뒤 나레이션을 고치면** 그 컷의 블록을 `hf_jobs.py record … --kind audio --status rejected` 로 기록하고
  다시 생성한다. build 는 파일 이름(`<cut>_<n>`)으로만 음성을 찾으므로, 문장만 바뀌고 블록 수가 같으면 옛 음성이 그대로 들어간다.
  블록 수가 줄면 validate 가 남은 기록을 경고한다.

## 5. GenRec (생성 기록)

```jsonc
{
  "status": "pending",        // pending | generated | approved | rejected
  "job_id": null,             // 현재 채택된 시도의 Higgsfield job id
  "url": null,                // 그 결과 URL — fetch_assets 가 이걸 받는다
  "attempts": 0,              // 생성 횟수. 2 이상이면 재생성
  "credits": 0,               // 이 항목에 쓴 크레딧 누적
  "reason": null,             // 마지막 판정 사유 (거절 이유 등)
  "history": [                // 시도마다 1줄
    {"job_id": "...", "url": "...", "status": "rejected", "reason": "노란 단추가 가려짐",
     "at": "2026-10-01T09:12Z", "credits": 2}
  ]
}
```

- `pending` 아직 생성 안 함 → `generated` 생성됨(확인·승인 전) → `approved` 승인 / `rejected` 거절(재생성 대상).
- 손으로 고치지 말고 `hf_jobs.py record` 로만 갱신한다. record 가 attempts·credits·history 와
  `manifest.credits`(spent / generations / regenerations)를 한 번에 맞추고, 첫 생성 때 `status` 를 `producing` 으로 바꾼다.
  - `--status generated --job-id J --url U`: 새 시도 1회 (크레딧은 `config.higgsfield.unit_costs`, `--credits` 로 덮기).
    같은 job 을 다시 적으면 크레딧을 두 번 세지 않는다.
  - `--status approved|rejected [--reason …]`: 마지막 시도의 판정만 바꾼다. `--job-id` 로 예전 시도를 골라 승인하면
    그 시도로 되돌린다.
  - 이미 approved 인 항목에 새 job 을 기록하려면 `--force` (라이브러리는 재생성 금지가 원칙).
- fetch_assets 는 status 가 generated/approved 이고 url 이 있는 항목만 받는다. URL 이 바뀌면 다시 받는다.
- 위치: 컷 이미지 `cut.gen.image`, V 클립 `cut.gen.clip`, 음성 `cut.audio_src[lang][블록번호]`.
- 라이브러리(`library/library.json`)도 같은 모양이다 (초기 status `missing` = pending):
  `character_sheets.<momo|ducky|…>`(+ `element_id`), `clips.<이름>.image`(클립 시작 이미지)와
  `clips.<이름>` 자체(클립), `audio.<lang>.<intro|outro>`, `voice_samples[]`(음성 후보 샘플, `lang`·`voice_id`·`text` 포함).
  라이브러리 항목을 `--ep <ep>` 와 함께 기록하면 그 에피소드 크레딧에 합산된다 (첫 편).

## 6. 파일 이름 규칙

build 는 이 규칙으로 파일을 찾는다. manifest 에 경로를 쓰지 않는다.

| 무엇 | 경로 (momo/ 기준) | 확장자 |
|---|---|---|
| 컷 이미지 (V/S) | `episodes/<ep>/images/<cut>.png` | png jpg jpeg webp |
| V 클립 | `episodes/<ep>/clips/<cut>.mp4` | mp4 mov webm mkv |
| 나레이션 블록 | `episodes/<ep>/audio/<lang>/<cut>_<n>.wav` (블록이 1개면 `<cut>.wav` 도 허용) | wav mp3 m4a aac ogg flac opus |
| 라이브러리 클립 | `library/clips/<intro_wave\|outro_bye\|say_with_me\|cheer\|transition>.mp4` | 영상 |
| 고정 음성 | `library/audio/<lang>/<intro\|outro>.wav` | 음성 |
| 캐릭터 시트 | `library/sheets/<momo\|ducky\|…>.png` | 이미지 |
| BGM / SFX / 폰트 | `assets/bgm/`, `assets/sfx/<manifest sfx 의 file>`, `assets/fonts/` | |
| 출력 | `episodes/<ep>/out/<ep>_<lang>.mp4`, `_thumb.jpg`, `_timeline.json`, `check_<lang>/` | |

같은 이름에 확장자가 여러 개면 표의 순서(png → jpg …)로 첫 번째를 쓴다.

## 7. 컷 길이와 타임라인 (`plan_timeline`, 매 build 마다 재계산)

```
xf_in   = 0.3  (이 컷으로 fade 로 들어오면) / 0 (cut, 또는 첫 컷)
nar_len = speech 블록 실제 길이 합 + [pause] 합     (음성이 아직 없으면 글자 수로 추정)
dur     = max(xf_in + nar_len + 0.4, 3.0, cut.duration)    → 1/30초 단위로 올림
          나레이션 없는 V/L 은 소스 클립 길이 (그래도 최소 3.0)
start[i]= start[i-1] + dur[i-1] − xf_in[i]
total   = start[마지막] + dur[마지막]
```

- **크로스페이드 겹침**: fade 로 들어오는 컷은 앞 컷의 마지막 0.3초와 겹친다. 그래서 전체 길이는
  컷 길이 합보다 (fade 수 × 0.3초) 짧다.
- **나레이션 오프셋**: 나레이션은 `컷 시작 + xf_in` 부터 놓는다. 겹치는 0.3초 동안은 앞 컷의
  0.4초 여유(tail_pad) 구간이므로 두 컷의 음성이 절대 겹치지 않는다. 컷 길이에 `xf_in` 을 더하는 이유가 이것이다.
- speech → pause → speech 순서 그대로 샘플 단위로 배치하고, 마지막 블록 뒤 0.4초가 여유다.
- 키워드는 `컷 시작 + text_at` 에 팝 애니메이션(0.3초)으로 나타나 컷 끝까지 남는다.
- 프레임 단위로 올려서 계산하므로 영상·음성 길이가 누적 오차 없이 맞는다 (build 가 1프레임 이내로 검증).
- EN 과 KO 는 음성 길이가 달라서 타임라인·총 길이가 각각 다르다.

V 클립(5초)과 컷 길이의 관계:

| 필요한 길이 | 처리 |
|---|---|
| ≤ 5초 | 컷 길이에서 자른다 |
| 5~10초 | 정방향 + 역방향(핑퐁) 1회 이어 붙이고 자른다 |
| > 10초 | 핑퐁 뒤 마지막 프레임을 정지(tpad)해서 채운다 |

S 컷은 5~8% 줌인/줌아웃(S 순번 홀짝 교차) + ±1.5% 좌우 드리프트. V/L 에는 켄번즈를 쓰지 않는다.

### 계산 예 (아래 8절 예시, EN — 음성 길이는 가정값)

| 컷 | 전환 | 음성 | 계산 | dur | start |
|---|---|---|---|---|---|
| c01 L intro | 첫 컷 | 1.80 | max(0 + 1.80 + 0.4, 3.0) | 3.000 | 0.000 |
| c02 V | cut (같은 씬) | 2.60 | max(0 + 2.60 + 0.4, 3.0) | 3.000 | 3.000 |
| c03 S | fade (씬 1→2) | 2.10 + [1.5] + 1.35 = 4.95 | 0.3 + 4.95 + 0.4 = 5.65 → 170프레임 | 5.667 | 3.000 + 3.000 − 0.3 = 5.700 |
| c04 L cheer | `transition: cut` | 2.40 | max(0 + 2.40 + 0.4, 3.0, duration 5.0) | 5.000 | 5.700 + 5.667 = 11.367 |
| c05 L outro | fade (씬 2→3) | 1.90 | max(0.3 + 1.90 + 0.4, 3.0) | 3.000 | 11.367 + 5.000 − 0.3 = 16.067 |

total = 16.067 + 3.000 = **19.067초** (컷 길이 합 19.667초 − fade 2번 × 0.3초).

c03 의 나레이션은 6.000초(5.700 + 0.3)에 시작해 블록1 6.00–8.10, 무음 8.10–9.60, 블록2 9.60–10.95,
여유 후 11.367초에 끝난다. 키워드 BOOTS 는 5.700 + 1.0 = 6.700초에 화면 하단(`text_pos: bottom`)에 등장.
c02 의 5초 클립은 3.0초에서 잘린다.

실제 값은 `episodes/<ep>/out/<ep>_<lang>_timeline.json`(컷별 start, dur, xf_in, nar_len, text_at, estimated_audio)과
`validate_manifest.py --table` 의 예상 길이로 확인한다.

## 8. 전체 예시 (타입별 1컷 이상, 5컷)

형식 설명용이라 validate 는 컷·씬 개수 경고만 낸다 (error 없음).

```json
{
  "schema": 1,
  "ep": "ep03",
  "status": "producing",
  "topic": {"en": "Rainy Day", "ko": "비 오는 날"},
  "benchmark": {"channel_url": "https://www.youtube.com/@CoComelon", "research_dir": "research/cocomelon",
                "chosen_axis": "소재: 생활습관(비 오는 날) — 최근 일평균 조회수 상위"},
  "characters": ["momo", "ducky"],
  "title": {"en": "Rainy Day Song with Momo the Bunny | Raincoat, Boots, Umbrella for Toddlers",
            "ko": "비 오는 날 동요 | 우비·장화·우산 | 아기토끼 모모"},
  "thumbnail": {"cut": "c02", "text": {"en": "RAINY DAY!", "ko": "비 오는 날!"}, "text_pos": "top"},
  "bgm": null,
  "upload": {
    "en": {"title": "", "description": "", "tags": [], "playlist_id": null},
    "ko": {"title": "", "description": "", "tags": [], "playlist_id": null}
  },
  "credits": {"estimate": 142.6, "spent": 11.7, "generations": 5, "regenerations": 1},
  "notes": {"v_over_reason": null, "approvals": ["2026-10-01 4단계 기획표 승인"], "next_time": []},
  "cuts": [
    {
      "id": "c01", "scene": 1, "type": "L",
      "library_clip": "intro_wave", "library_audio": "intro",
      "narration": {"en": "Hi friends! It's Momo!", "ko": "안녕, 친구들! 나는 모모야!"},
      "keyword": {"en": "", "ko": ""}
    },
    {
      "id": "c02", "scene": 1, "type": "V",
      "narration": {"en": "Look! A yellow raincoat! Raincoat!", "ko": "이것 봐! 노란 우비야! 우비!"},
      "keyword": {"en": "RAINCOAT", "ko": "우비"},
      "image_prompt": "[Momo] wearing an open yellow raincoat over the overalls, standing in a bright garden during a light sun shower, clear sky space in the upper third of the frame",
      "motion": "small hop in place, ears bounce",
      "text_color": "yellow",
      "sfx": [{"file": "pop.wav", "at": 0.5, "gain_db": -6}],
      "gen": {
        "image": {"status": "approved", "job_id": "11111111-1111-4111-8111-111111111111",
                  "url": "https://cdn.example/c02_v2.png", "attempts": 2, "credits": 4,
                  "history": [
                    {"job_id": "00000000-0000-4000-8000-000000000001", "url": "https://cdn.example/c02_v1.png",
                     "status": "rejected", "reason": "노란 단추가 우비에 가려짐"},
                    {"job_id": "11111111-1111-4111-8111-111111111111", "url": "https://cdn.example/c02_v2.png",
                     "status": "approved", "reason": ""}]},
        "clip": {"status": "generated", "job_id": "22222222-2222-4222-8222-222222222222",
                 "url": "https://cdn.example/c02.mp4", "attempts": 1, "credits": 7.5,
                 "history": [{"job_id": "22222222-2222-4222-8222-222222222222", "url": "https://cdn.example/c02.mp4",
                              "status": "generated", "reason": ""}]}
      },
      "audio_src": {
        "en": {"1": {"status": "approved", "job_id": "33333333-3333-4333-8333-333333333333",
                     "url": "https://cdn.example/c02_en_1.wav", "attempts": 1, "credits": 0.2, "history": []}},
        "ko": {"1": {"status": "pending", "job_id": null, "url": null, "attempts": 0, "credits": 0, "history": []}}
      }
    },
    {
      "id": "c03", "scene": 2, "type": "S",
      "narration": {"en": "Red boots! Can you say boots? [pause 1.5] Boots! Great job!",
                    "ko": "빨간 장화! 장화, 따라 해볼까? [pause 1.5] 장화! 잘했어!"},
      "keyword": {"en": "BOOTS", "ko": "장화"},
      "image_prompt": "a pair of shiny red rain boots standing on soft green grass next to a small clear puddle, plain pastel background",
      "momo": false,
      "text_pos": "bottom",
      "text_at": 1.0,
      "inset": null
    },
    {
      "id": "c04", "scene": 2, "type": "L",
      "library_clip": "cheer",
      "narration": {"en": "[chant] Raincoat, boots, splash, splash, splash!",
                    "ko": "[chant] 우비, 장화, 첨벙첨벙 첨벙!"},
      "keyword": {"en": "SPLASH", "ko": "첨벙"},
      "transition": "cut",
      "duration": 5.0
    },
    {
      "id": "c05", "scene": 3, "type": "L",
      "library_clip": "outro_bye", "library_audio": "outro",
      "narration": {"en": "Bye-bye, friends! See you next time!", "ko": "친구들, 안녕! 다음에 또 만나!"},
      "keyword": {"en": "", "ko": ""}
    }
  ]
}
```

이 예시에서 필요한 파일:

| 컷 | 파일 |
|---|---|
| c01 | `library/clips/intro_wave.mp4`, `library/audio/{en,ko}/intro.wav` |
| c02 | `images/c02.png`, `clips/c02.mp4`, `audio/en/c02_1.wav`, `audio/ko/c02_1.wav`, `assets/sfx/pop.wav`(없으면 생략) |
| c03 | `images/c03.png`, `audio/en/c03_1.wav` + `c03_2.wav`, `audio/ko/c03_1.wav` + `c03_2.wav` |
| c04 | `library/clips/cheer.mp4`, `audio/en/c04_1.wav`, `audio/ko/c04_1.wav` (library_audio 가 없으므로 TTS) |
| c05 | `library/clips/outro_bye.mp4`, `library/audio/{en,ko}/outro.wav` |

파일이 아직 없으면 `python momo/build.py --ep ep03 --lang en --allow-missing` 로 애니매틱을 볼 수 있다
(없는 클립 → 이미지, 없는 이미지 → 컷 번호 카드, 없는 음성 → 추정 길이 무음).
