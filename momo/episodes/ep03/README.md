# ep03 — (주제 미정) (Crunchy Veggies)

> episode_readme.py 가 생성 (2026-09-30 10:40 UTC). 다시 실행하면 덮어쓴다 — 메모는 manifest.notes 에.

## 요약

| 항목 | 값 |
|---|---|
| 상태 | uploaded |
| 주제 |  / Crunchy Veggies |
| 컷 수 | 31개 (V 30 · S 0 · L 1), 씬 5개 |
| 사용 크레딧 | 193.5 / 캡 250 (예상 205.2) |
| 생성 / 재생성 횟수 | 52 / 6 |
| 길이 EN | 1:54 (113.5초, 컷 31개, 빌드 2026-09-30T10:40:06+00:00) |
| 썸네일 | c04 — CRUNCHY VEGGIES! |

## 아동용(made for kids) 설정

> 이 영상은 YouTube 에서 반드시 **"아동용(made for kids)"** 으로 설정해야 한다 (2~5세 대상 키즈 채널 — 지시서 7단계). upload.py 는 config 와 상관없이 `status.selfDeclaredMadeForKids = true` 로 올린다. Studio 에서 직접 올릴 때는 '예, 아동용입니다'를 선택할 것.

- EN: ✔ upload.py 가 selfDeclaredMadeForKids = true 로 업로드함 (bXK0XfxA0Pk)

## 업로드 결과 (youtube.json)

| 언어 | 영상 | 공개 상태 | 예약 공개 | 업로드 시각 | 썸네일 | 재생목록 |
|---|---|---|---|---|---|---|
| EN | [bXK0XfxA0Pk](https://www.youtube.com/watch?v=bXK0XfxA0Pk) | private | — | 2026-09-30T10:40:48Z | ✔ | — |

## 제목·설명·태그

### EN

- 제목: Crunchy Veggies Song with Momo the Bunny | Carrot, Broccoli and Corn for Toddlers
- 태그: kids songs, nursery rhymes, toddler songs, vegetables song, healthy eating for kids, carrot, broccoli, corn, learn english for kids, Momo the Bunny
- 설명:

```text
Sing along with Momo the Bunny! Crunch crunch, munch munch — let's eat our veggies! Learn three vegetables: carrot, broccoli and corn, and say each word with Momo and Ducky.

Words in this song: carrot · broccoli · corn

Made for toddlers and preschoolers (ages 2-5). Music and animation made with AI tools.
```

## 생성 기록

| 종류 | 승인 | 시도 | 크레딧 |
|---|---:|---:|---:|
| 컷 이미지 | 23/23 | 26 | 52 |
| V 클립 | 23/23 | 26 | 141.5 |
| 음성 블록 | 2/2 | 2 | 0 |

라이브러리 L 컷은 0 크레딧 (라이브러리 클립·고정 음성 재사용). 자세한 진행표: `python hf_jobs.py status --ep ep03`

## 승인 기록

- 2026-09-30 주제 승인: ① 채소 먹기 (Crunchy Veggies — carrot · broccoli · corn, 조연 Ducky)
- 2026-09-30 형식 승인: 120 BPM · 약 2:02 (61마디) · 컷 38개 평균 3.2초 · 노래 비중 85~90% · 후렴 4회 · 반복 후렴 구간 영상 재사용
- 2026-09-30 노래 방식 승인: ACE-Step 1.5 로컬 생성(보컬 포함, 크레딧 0) — 가수 목소리는 밝은 여성 보컬, 인트로·아웃트로는 라이브러리 Gracie
- 2026-09-30 노래 승인: 후보 1 (ACE-Step b_s202, 120.005 BPM, 2:06) — 사용자 선택
- 2026-09-30 노래 소스 변경: Suno Pro (사용자 결정) — ACE-Step 후보 1 은 보류, 컷 구성은 Suno 곡에 맞춰 다시 짠다
- 2026-09-30 기획표 승인: Suno v1 곡, 컷 31개(립싱크 16·움직임 8·재사용 6·L 1), 1:54, 예상 171 (여유 포함 205)
- 2026-09-30 첫 3장 승인 (c01·c02·c03 이미지)
- 2026-09-30 이미지 23장 승인 (c04·c14·c23 재생성본 포함)
- 2026-09-30 클립 23개 검수 후 승인 (사용자: 묻지 말고 진행) — c05 서버 실패 2회(1.93초 레퍼런스→3초 패딩), c12 귀 솟음 재생성

## 다음 편에 반영할 점

- Suno 곡이 1.6초에 바로 시작해 라이브러리 인트로 인사(Hi friends! It's Momo!)를 넣을 자리가 없음 — 다음 곡은 스타일/가사에 '[Intro - 2 bars]' 로 짧은 전주를 요청할 것
