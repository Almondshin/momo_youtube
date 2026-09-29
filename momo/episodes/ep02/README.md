# ep02 — 양치하기 (Brush Your Teeth)

> episode_readme.py 가 생성 (2026-09-29 12:27 UTC). 다시 실행하면 덮어쓴다 — 메모는 manifest.notes 에.

## 요약

| 항목 | 값 |
|---|---|
| 상태 | producing |
| 주제 | 양치하기 / Brush Your Teeth |
| 컷 수 | 24개 (V 13 · S 7 · L 4), 씬 5개 |
| 사용 크레딧 | 225 / 캡 250 (예상 238.8) |
| 생성 / 재생성 횟수 | 117 / 12 |
| 길이 EN | 2:35 (154.9초, 컷 24개, 애니매틱/추정 음성 포함, 빌드 2026-09-29T12:22:53+00:00) |
| 길이 KO | 2:27 (146.7초, 컷 24개, 애니매틱/추정 음성 포함, 빌드 2026-09-29T12:26:53+00:00) |
| 썸네일 | c23 — BRUSH BRUSH! / 치카치카! |

## 아동용(made for kids) 설정

> 이 영상은 YouTube 에서 반드시 **"아동용(made for kids)"** 으로 설정해야 한다 (2~5세 대상 키즈 채널 — 지시서 7단계). upload.py 는 config 와 상관없이 `status.selfDeclaredMadeForKids = true` 로 올린다. Studio 에서 직접 올릴 때는 '예, 아동용입니다'를 선택할 것.

- EN: 아직 업로드 전 — upload.py 로 올리면 아동용 true 로 자동 설정됨
- KO: 아직 업로드 전 — upload.py 로 올리면 아동용 true 로 자동 설정됨

## 업로드 결과 (youtube.json)

아직 업로드 전 — `python upload.py --ep ep02 --lang all` 또는 Actions momo-publish

## 제목·설명·태그

### EN

- 제목: Brush Your Teeth Song with Momo the Bunny | Morning Routine for Toddlers
- 태그: brush your teeth song, brushing teeth for kids, toddler songs, kids songs, nursery rhymes, morning routine for kids, healthy habits for kids, preschool learning, Momo the Bunny, tooth brushing song, learning videos for toddlers, baby songs
- 설명:

```text
Brush, brush, up and down! Join Momo the Bunny and Ducky for a happy morning tooth-brushing routine. A gentle say-along chant for toddlers and preschoolers (ages 2-5).

What we learn today:
1. A toothbrush and just a tiny dot of toothpaste
2. Brush up and down - top teeth and bottom teeth
3. Sip, swish and rinse with a cup of water

Say it with Momo and brush together every morning and every night!

#BrushYourTeeth #ToddlerLearning #KidsSongs #NurseryRhymes #MorningRoutine #PreschoolLearning #HealthyHabits #MomoTheBunny #BabySongs #LearnWithMomo
```

### KO

- 제목: 양치 동요 | 치카치카 이 닦기 | 아기토끼 모모
- 태그: 양치 동요, 치카치카, 이 닦기, 유아 동요, 키즈 동요, 생활습관 동요, 아침 습관, 유아 교육, 아기토끼 모모, 양치 습관, 어린이 동요
- 설명:

```text
치카치카, 위로 아래로! 아기토끼 모모와 오리 더키가 아침 양치 습관을 알려줘요. 2~5세 아이를 위한 따라 말하기 챈트예요.

오늘 배우는 것:
1. 칫솔과 콩알만큼의 치약
2. 윗니는 위로, 아랫니는 아래로 치카치카
3. 물을 머금고 오물오물, 퉤! 헹구기

아침에도 밤에도 모모랑 같이 이를 닦아요!

#양치동요 #치카치카 #유아동요 #키즈송 #생활습관 #아침습관 #유아교육 #아기토끼모모 #양치습관 #모모랑배워요
```

## 생성 기록

| 종류 | 승인 | 시도 | 크레딧 |
|---|---:|---:|---:|
| 컷 이미지 | 20/20 | 29 | 58 |
| V 클립 | 13/13 | 13 | 97.5 |
| 음성 블록 | 50/50 | 50 | 10 |

라이브러리 L 컷은 0 크레딧 (라이브러리 클립·고정 음성 재사용). 자세한 진행표: `python hf_jobs.py status --ep ep02`

## 승인 기록

- 2026-09-29 주제 A(양치하기) 승인
- 2026-09-29 2단계 생략·기본 구조 진행 승인
- 2026-09-29 4단계 기획표(plan.md) 승인 — 사물 5컷 캐릭터 블록 생략 해석 포함
- 2026-09-29 폰트: 나눔스퀘어라운드 Bold (OFL)
- 2026-09-29 캐릭터 시트 승인: 모모(1차, 멜빵 단추 2개 시그니처), 더키, 토토(악어), 써니(상어) → Elements 등록
- 2026-09-29 씬1: c02 승인, c03(표정)·c04(욕실 일관성) 재생성 결정 / 잉코 시트 승인·Elements 등록
- 2026-09-29 욕실 세트 묘사 고정(sets.bathroom) — 욕실 컷 프롬프트에 반영
- 2026-09-29 씬1 이미지 3장(c02·c03·c04) 승인 → c02·c03 영상 변환
- 2026-09-29 c02·c03 클립 승인 → 씬2 이미지 진행
- 2026-09-29 씬2 이미지 4장(c05·c06·c07·c09) 승인 → c06·c09 영상 + 씬3 이미지
- 2026-09-29 c06·c09 클립, 씬3 이미지 4장 승인 → c10~c12 클립 + 씬4 이미지

## 다음 편에 반영할 점

- (아직 없음 — manifest.notes.next_time 에 적기)
