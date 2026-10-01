# ep08 — 도형 (Shapes)

> episode_readme.py 가 생성 (2026-10-01 06:52 UTC). 다시 실행하면 덮어쓴다 — 메모는 manifest.notes 에.

## 요약

| 항목 | 값 |
|---|---|
| 상태 | uploaded |
| 주제 | 도형 / Shapes |
| 컷 수 | 26개 (V 24 · S 0 · L 2), 씬 5개 |
| 사용 크레딧 | 121 / 캡 150 |
| 생성 / 재생성 횟수 | 34 / 4 |
| 길이 EN | 1:45 (105.0초, 컷 26개, 빌드 2026-10-01T06:52:18+00:00) |
| 썸네일 | c02 — SHAPES! |

## 아동용(made for kids) 설정

> 이 영상은 YouTube 에서 반드시 **"아동용(made for kids)"** 으로 설정해야 한다 (2~5세 대상 키즈 채널 — 지시서 7단계). upload.py 는 config 와 상관없이 `status.selfDeclaredMadeForKids = true` 로 올린다. Studio 에서 직접 올릴 때는 '예, 아동용입니다'를 선택할 것.

- EN: ✔ upload.py 가 selfDeclaredMadeForKids = true 로 업로드함 (glKedSwOi6E)

## 업로드 결과 (youtube.json)

| 언어 | 영상 | 공개 상태 | 예약 공개 | 업로드 시각 | 썸네일 | 재생목록 |
|---|---|---|---|---|---|---|
| EN | [glKedSwOi6E](https://www.youtube.com/watch?v=glKedSwOi6E) | private | — | 2026-10-01T06:52:41Z | ✔ | — |

## 제목·설명·태그

### EN

- 제목: Shapes Song with Momo the Bunny | Circle, Square, Triangle for Toddlers
- 태그: shapes song, shapes for kids, learn shapes, circle square triangle, shapes for toddlers, kids songs, nursery rhymes, toddler songs, learn english for kids, english for toddlers, preschool songs, Momo the Bunny
- 설명:

```text
Circle, square, triangle, star and heart! Find shapes everywhere with Momo the Bunny and Ducky: the round sun, a square window, a triangle slice of watermelon, a star in the night sky and a heart-shaped cookie.

Shapes in this song:
Circle - the sun · Square - the window · Triangle - a slice of watermelon
Star - a star in the night sky · Heart - a heart cookie
Draw a shape in the air and sing along: shapes are everywhere!

Made for toddlers and preschoolers (ages 2-5). Music and animation made with AI tools.

#shapes #shapessong #learnshapes #kidssongs #nurseryrhymes #toddlersongs #learnenglish #englishforkids #preschool #MomotheBunny
```

## 생성 기록

| 종류 | 승인 | 시도 | 크레딧 |
|---|---:|---:|---:|
| 컷 이미지 | 15/15 | 19 | 38 |
| V 클립 | 15/15 | 15 | 83 |
| 음성 블록 | 2/2 | 2 | 0 |

라이브러리 L 컷은 0 크레딧 (라이브러리 클립·고정 음성 재사용). 자세한 진행표: `python hf_jobs.py status --ep ep08`

## 승인 기록

- 2026-10-01 노래: Suno v2 'Shapes Everywhere with Momo' (125.2 BPM, 1:49.9, 2.0초부터 노래·95.7초까지) — 사용자 승인 곡으로 전달받음 (v1 59.6초 테이크는 거절)
- 2026-10-01 시작 이미지 15장 승인 (생산 에이전트의 on-model 게이트 — 원본 크기·얼굴 크롭으로 확인, 사용자 확인 전): c02~c08, c12~c15, c19~c22 · 거절·재생성 4회 (c02 1, c08 3) · 38 크레딧
- 2026-10-01 클립 15개 승인 (생산 에이전트의 검토 — fps=2 프레임 시트·얼굴 원본 크기 크롭·song_track sync·on-model 게이트, 사용자 확인 전): 립싱크 c02 c03 c04 c06 c08 c13 c15 c20 c21 · 동작 c05 c07 c12 c14 c19 c22 · 재생성 0회 · 클립 83 크레딧 (에피소드 합계 121 / 캡 150)

## 다음 편에 반영할 점

- Suno v2 는 전주 없이 2.0초부터 불렀다 ([Instrumental intro - 4 bars] 무시) → 인사 c01 은 lead 0 으로 2.12초 컷 안에 (목소리 0.06–2.04초). 라이브러리 intro.wav 가 3.58초라 노래가 3.9초까지 −6 dB 덕킹됨 — 첫 줄이 조금 작게 들리면 song.duck_db 조정
- 가사 정렬: 전체 스템 whisper 는 메아리 절반을 못 들음(84.7%). 섹션별 whisper(scratchpad ep08/align_sliced.py) 는 절 메아리를 모두 들었지만 후렴 2 를 놓침 → 후렴 4개가 같은 녹음(상관 r 0.89–0.96)이라 후렴 1 기준 한 틀로 맞춤(merge_align.py, chorus_seed.py)
- 보정(refine)이 같은 녹음의 후렴 4개에서 빠른 메아리·레가토 단어를 서로 다른 onset 에 붙임 (‘and’ 0.2초, ‘love’ 0.24초 늦게) → 음높이(pyin)·엔벌로프로 확인한 틀로 15단어 고정 (chorus_fix.py). song_track.py lyrics 를 다시 돌리면 이 고정이 풀린다
- Suno 가 노래 뒤 13초 기악 아웃트로를 붙임 → 영상은 마디 54(105.0초)에서 페이드로 끝냄 (노래 비율 89%)
- 이미지: 'plain smooth shapes' 만으로는 nano_banana 가 도형·사물에 눈·입을 그림 (c02 1차) → 'with no faces, no eyes and no mouths'. 해·수박·별·쿠키 프롬프트에도 미리 'no face' 를 넣어 모두 1회에 통과
- 이미지: 모모 뒤 '정사각형 창문' 은 3번 실패 (세로로 긴 창+위 잘림 ×2, 가로 창살·뒤에 창 하나 더 ×1). 4번째 'small square window about as big as her head … one single undivided glass pane with no cross bars, no muntins … the only window in the picture' + 'full body … in the centre of the frame' 로 통과 — 그래도 가로:세로 ≈ 0.85·약간 비스듬함 (재생성 한도 4회 소진으로 승인)
- 이미지: 'both paws together … ready to clap' 은 두 번 다 앞발이 노란 단추 2개를 가림 (ep06 c02 와 같음) — 'in front of her tummy … buttons clearly visible' 문구도 무시됨. c02 는 그대로 승인 (박수 동작 컷). 단추가 꼭 보여야 하면 'both arms relaxed down at her sides' 로 시작
- 이미지: c15 침실 창의 별이 끈에 매달린 장식처럼 그려짐 (하늘에 흐린 점 몇 개) — 별 모양·세트는 맞아 승인. c20 눈 비율 0.67 (넓은 얼굴 클로즈업, 크롭으로 보면 정상)
- 클립: wan2_7 이 'traces a circle / a heart in the air' 를 빛나는 원 고리(c06)·분홍 하트 선(c20)으로 공중에 그려 줌 — 도형 학습에 잘 맞아 승인. 단어 카드(왼쪽)와 일부 겹침
- 클립: c04 (재사용 c11·c18·c25) 는 프롬프트에 'beak closed' 가 있어도 Ducky 가 메아리 '(Draw a shape!)' 와 'We love shapes, hooray!' 에서 부리를 벌려 같이 노래함 — 모모도 끝까지 노래해서(입 닫힘 0.27초) 승인. 둘이 같이 부르는 후렴은 괜찮지만, 모모만 부르게 하려면 Ducky 를 화면 밖으로
- 클립: c15 'points up toward the round window … without turning her head' → 1.2~1.8초에 고개를 창 쪽으로 30° 돌림 (얼굴은 3/4 로 보이고 눈·귀 정상, 입 계속 움직임) — 승인
- MCP: wan2_7 배치 항목에 'IN THE DARK' 프리셋 추천(submission_failed, 과금 없음)이 4번 — declined_preset_id 24bae836-2c4a-48e0-89b6-49fcc0b21612 로 다시 보내면 통과
- 조립: 인트로 덕킹 구간이 intro.wav 전체 길이(3.58초, 목소리는 0.06~2.04초)라 첫 노래 줄 'Circle, square, triangle!'(2.22~3.97초)이 같은 녹음의 후렴 2~4보다 약 7 dB 작음 (빌드 측정 −5.0 dB vs +2.2 dB, 원곡 대비). 고치려면 momolib/audio.build_narration 의 speech span 을 voiced_bounds 로 자르거나 song.duck_db 를 줄일 것 (사용자 결정)
