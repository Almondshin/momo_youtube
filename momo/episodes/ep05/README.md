# ep05 — 무지개 색깔 (Rainbow Colors)

> episode_readme.py 가 생성 (2026-10-01 03:14 UTC). 다시 실행하면 덮어쓴다 — 메모는 manifest.notes 에.

## 요약

| 항목 | 값 |
|---|---|
| 상태 | uploaded |
| 주제 | 무지개 색깔 / Rainbow Colors |
| 컷 수 | 34개 (V 32 · S 0 · L 2), 씬 5개 |
| 사용 크레딧 | 140.5 / 캡 250 (예상 214.2) |
| 생성 / 재생성 횟수 | 51 / 3 |
| Higgsfield API | $2.00 (생성 5회, 구독 크레딧과 별개) |
| 길이 EN | 2:15 (134.7초, 컷 34개, 빌드 2026-10-01T03:12:29+00:00) |
| 썸네일 | c08 — RAINBOW COLORS! |

## 아동용(made for kids) 설정

> 이 영상은 YouTube 에서 반드시 **"아동용(made for kids)"** 으로 설정해야 한다 (2~5세 대상 키즈 채널 — 지시서 7단계). upload.py 는 config 와 상관없이 `status.selfDeclaredMadeForKids = true` 로 올린다. Studio 에서 직접 올릴 때는 '예, 아동용입니다'를 선택할 것.

- EN: ✔ upload.py 가 selfDeclaredMadeForKids = true 로 업로드함 (yi_fF0XJq7A)

## 업로드 결과 (youtube.json)

| 언어 | 영상 | 공개 상태 | 예약 공개 | 업로드 시각 | 썸네일 | 재생목록 |
|---|---|---|---|---|---|---|
| EN | [yi_fF0XJq7A](https://www.youtube.com/watch?v=yi_fF0XJq7A) | private | — | 2026-10-01T03:14:47Z | ✔ | — |

## 제목·설명·태그

### EN

- 제목: Rainbow Colors Song with Momo the Bunny | Learn Colors for Toddlers
- 태그: colors song, rainbow song, learn colors, colors for toddlers, rainbow colors, kids songs, nursery rhymes, toddler songs, learn english for kids, Momo the Bunny
- 설명:

```text
Rainbow, rainbow! Up in the sky! Sing the rainbow colors with Momo the Bunny and Ducky: red, orange, yellow, green, blue, purple. Find a red strawberry and an orange carrot, clap, clap, clap for red and sway for orange, then spot a yellow banana, a green leaf, a blue ball and purple grapes. Ding-dong-dang - rainbow colors, yay!

Colors in this song: red, orange, yellow, green, blue, purple

Made for toddlers and preschoolers (ages 2-5). Music and animation made with AI tools.
```

## 생성 기록

| 종류 | 승인 | 시도 | 크레딧 |
|---|---:|---:|---:|
| 컷 이미지 | 24/24 | 27 | 40 |
| V 클립 | 24/24 | 24 | 100.5 |
| 음성 블록 | 2/2 | 2 | 0 |

라이브러리 L 컷은 0 크레딧 (라이브러리 클립·고정 음성 재사용). 자세한 진행표: `python hf_jobs.py status --ep ep05`

## 승인 기록

- 2026-10-01 사용자: ep05~07 병렬 제작·업로드 지시, 묻지 말고 진행
- 2026-10-01 노래: Suno v1 'Rainbow Colors' (127.0 BPM, 2:14.7) — 사용자가 만들어 넣어 준 곡. 가사 45줄 중 22줄만 부름 (verse 2·3·bridge 대신 41초 간주), 정렬 97.5% (부른 가사 기준)
- 2026-10-01 동작 클립을 API Wan 2.7(초당 $0.10)으로 — API Seedance 2.0 은 3배 가격, 길이는 필요한 만큼(재사용 포함)
- 2026-10-01 정정: 구독 크레딧($26/500)이 API 보다 쌈 — 동작 클립은 구독 Seedance Mini(1 크레딧/초)로 되돌림

## 다음 편에 반영할 점

- Suno v1 이 verse 2·3·bridge 를 부르지 않고 41초 간주로 채움 (가사 45줄 중 22줄) — 테이크를 고를 때 정렬기를 '쓴 가사' 기준으로 먼저 돌려 커버리지를 볼 것
- align_lyrics.py: 17초 무음 인트로에서 whisper 가 첫 30초 창을 환각('A -B!' 반복)으로 채워 후렴 1 이 빠짐 — 보컬 구간만 잘라 정렬함 (scratchpad ep05/align_ep05.py)
