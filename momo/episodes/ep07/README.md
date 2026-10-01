# ep07 — 손 씻기 (Wash Your Hands)

> episode_readme.py 가 생성 (2026-10-01 03:21 UTC). 다시 실행하면 덮어쓴다 — 메모는 manifest.notes 에.

## 요약

| 항목 | 값 |
|---|---|
| 상태 | uploaded |
| 주제 | 손 씻기 / Wash Your Hands |
| 컷 수 | 33개 (V 31 · S 0 · L 2), 씬 5개 |
| 사용 크레딧 | 113.5 / 캡 250 |
| 생성 / 재생성 횟수 | 39 / 3 |
| Higgsfield API | $2.70 (생성 6회, 구독 크레딧과 별개) |
| 길이 EN | 2:15 (135.0초, 컷 33개, 빌드 2026-10-01T03:20:21+00:00) |
| 썸네일 | c03 — WASH YOUR HANDS! |

## 아동용(made for kids) 설정

> 이 영상은 YouTube 에서 반드시 **"아동용(made for kids)"** 으로 설정해야 한다 (2~5세 대상 키즈 채널 — 지시서 7단계). upload.py 는 config 와 상관없이 `status.selfDeclaredMadeForKids = true` 로 올린다. Studio 에서 직접 올릴 때는 '예, 아동용입니다'를 선택할 것.

- EN: ✔ upload.py 가 selfDeclaredMadeForKids = true 로 업로드함 (x3tNObwCLK8)

## 업로드 결과 (youtube.json)

| 언어 | 영상 | 공개 상태 | 예약 공개 | 업로드 시각 | 썸네일 | 재생목록 |
|---|---|---|---|---|---|---|
| EN | [x3tNObwCLK8](https://www.youtube.com/watch?v=x3tNObwCLK8) | private | — | 2026-10-01T03:21:50Z | ✔ | — |

## 제목·설명·태그

### EN

- 제목: Wash Your Hands Song with Momo the Bunny | Handwashing Routine for Toddlers
- 태그: wash your hands song, handwashing song, hand washing for kids, healthy habits for kids, kids songs, nursery rhymes, toddler songs, learn english for kids, english for toddlers, Momo the Bunny
- 설명:

```text
Splish, splash, water on! Rub, rub, rub your hands! Wash your hands with Momo the Bunny and Ducky: turn the water on, add soap, rub round and round and count to ten, rinse the bubbles away and pat them dry. Squeaky clean! When do we wash our hands? After we play and before we eat!

Handwashing steps in this song: water, soap, rub, count to 10, rinse, dry

Made for toddlers and preschoolers (ages 2-5). Music and animation made with AI tools.
```

## 생성 기록

| 종류 | 승인 | 시도 | 크레딧 |
|---|---:|---:|---:|
| 컷 이미지 | 18/18 | 20 | 40 |
| V 클립 | 18/18 | 19 | 73.5 |
| 음성 블록 | 2/2 | 2 | 0 |

라이브러리 L 컷은 0 크레딧 (라이브러리 클립·고정 음성 재사용). 자세한 진행표: `python hf_jobs.py status --ep ep07`

## 승인 기록

- 2026-10-01 사용자: ep05~07 병렬 제작·업로드 지시, 묻지 말고 진행
- 2026-10-01 노래 승인: Suno v1 'Wash Your Hands' (125.0 BPM, 2:15) — 사용자가 만들어 넣어 준 곡
- 2026-10-01 동작 클립을 API Wan 2.7(초당 $0.10)으로 — API Seedance 2.0 은 3배 가격, 길이는 필요한 만큼(재사용 포함)
- 2026-10-01 정정: 구독 크레딧($26/500)이 API 보다 쌈 — 동작 클립은 구독 Seedance Mini(1 크레딧/초)로 되돌림

## 다음 편에 반영할 점

- 가사 정렬: align_lyrics.py 가 135초 스템 전체를 한 번에 들으면 whisper 가 후렴 1 에서 반복 환각('shine shine…') 또는 무음 전주 환각을 내고 실행마다 결과가 달랐다 (94.8% → 83.4%). 섹션별로 잘라 들은 정렬(97.6%)을 썼다 — ~/ml/momo_ep07/suno/v1/tools/align_sliced.py
- Suno 가 후렴 끝 'Wash your hands, hooray!' 를 두 번 불렀다 — 가사에 반복 줄을 미리 써 두면 컷 계획이 맞는다
- 후렴 4개가 같은 녹음(후렴 1 기준 16/32/52마디 뒤, 보컬 상관 r≥0.9) — 후렴 단어 시각은 4개 중앙값으로 맞춤 (~/ml/momo_ep07/suno/v1/tools/chorus_seed.py → align.json), 컷 계획은 tools/plan07.py
