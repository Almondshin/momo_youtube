# ep10 — 잘 자요 (Good Night)

> episode_readme.py 가 생성 (2026-10-01 06:37 UTC). 다시 실행하면 덮어쓴다 — 메모는 manifest.notes 에.

## 요약

| 항목 | 값 |
|---|---|
| 상태 | uploaded |
| 주제 | 잘 자요 / Good Night |
| 컷 수 | 25개 (V 25 · S 0 · L 0), 씬 5개 |
| 사용 크레딧 | 129.5 / 캡 150 (예상 135.6) |
| 생성 / 재생성 횟수 | 33 / 3 |
| 길이 EN | 1:50 (110.0초, 컷 25개, 빌드 2026-10-01T06:37:24+00:00) |
| 썸네일 | c04 — GOOD NIGHT! |

## 아동용(made for kids) 설정

> 이 영상은 YouTube 에서 반드시 **"아동용(made for kids)"** 으로 설정해야 한다 (2~5세 대상 키즈 채널 — 지시서 7단계). upload.py 는 config 와 상관없이 `status.selfDeclaredMadeForKids = true` 로 올린다. Studio 에서 직접 올릴 때는 '예, 아동용입니다'를 선택할 것.

- EN: ✔ upload.py 가 selfDeclaredMadeForKids = true 로 업로드함 (HVu4fmbxmPE)

## 업로드 결과 (youtube.json)

| 언어 | 영상 | 공개 상태 | 예약 공개 | 업로드 시각 | 썸네일 | 재생목록 |
|---|---|---|---|---|---|---|
| EN | [HVu4fmbxmPE](https://www.youtube.com/watch?v=HVu4fmbxmPE) | private | — | 2026-10-01T06:37:48Z | ✔ | — |

## 제목·설명·태그

### EN

- 제목: Good Night Song with Momo the Bunny | Bedtime Routine for Toddlers
- 태그: good night song, bedtime song, bedtime routine, bedtime songs for kids, sleepy song, kids songs, nursery rhymes, toddler songs, learn english for kids, english for toddlers, preschool songs, Momo the Bunny
- 설명:

```text
Sleepy, sleepy, time for bed! Get ready for bed with Momo the Bunny and Ducky: put on soft pajamas, read a story, give Teddy a big warm hug and snuggle up. Look at the moon and the stars, wave good night and close your eyes. Sweet dreams!

Bedtime routine in this song:
Pajamas - soft and cozy · Book - story time · Teddy - a big warm hug
Moon and stars - wave good night · Close your eyes - good night!

Made for toddlers and preschoolers (ages 2-5). Music and animation made with AI tools.

#goodnightsong #bedtimesong #bedtimeroutine #kidssongs #nurseryrhymes #toddlersongs #learnenglish #englishforkids #singalong #MomotheBunny
```

## 생성 기록

| 종류 | 승인 | 시도 | 크레딧 |
|---|---:|---:|---:|
| 컷 이미지 | 15/15 | 16 | 32 |
| V 클립 | 15/15 | 17 | 97.5 |
| 음성 블록 | 2/2 | 2 | 0 |

라이브러리 L 컷은 0 크레딧 (라이브러리 클립·고정 음성 재사용). 자세한 진행표: `python hf_jobs.py status --ep ep10`

## 승인 기록

- 2026-10-01 사용자: 모모 옷 = 민트색 별무늬 잠옷 (옵션 A, 노란 단추 2개 유지; 첫 이미지 2회 실패 시 멜빵바지로)
- 2026-10-01 사용자: 엔딩 = 잠든 장면으로 끝 (낮 배경 outro_bye 인사 없음)
- 2026-10-01 노래: Suno v1 'Good Night' (104.0 BPM, 1:50, 첫 목소리 9.1 s) — 워크플로 지시에 '사용자 승인 곡'으로 전달됨, song_track.py status --approve 로 기록

## 다음 편에 반영할 점

- Suno v1 은 후렴 4번째 줄 '(Good night!)' 메아리를 후렴 4개 모두에서 안 부르고 'night' 을 1박 끌었음 → lyrics.md 끝 'Sung lyrics' 블록. 절(verse)은 한 줄 1마디(4마디, 계획 6마디), 절 2 뒤 1마디 쉼(55.3–57.5 s).
- 아웃트로가 2마디 요청에 비해 15 s (반주 95–104 s + 마지막 화음 페이드 110 s) → 잠든 END 컷 20 s (Seedance 10 s, fill loop), 노래 비율 ≈ 78% (전주 9 s + 아웃트로 15 s). 다음 곡은 '[Outro - 2 bars, final chord]' 를 더 강하게, 또는 Suno 에서 끝을 자를 것.
- 가사 정렬: align_lyrics.py 한 번에 전체 스템 → 91.8% (후렴 4 끝을 놓침). 섹션별 정렬(~/ml/momo_ep10/suno/v1/tools/align_sliced.py, 절 3 은 프롬프트 없이 두 조각) → 97.8%, 노래 안 된 가사 없음.
- 보정기(lyrics_refine)가 레가토 음절(온셋 미검출)에서 단어를 0.1–0.6 s 늦게 찍음: 'moon!' 73.32(실제 72.85), 메아리 'Hello, Teddy' 0.3–0.5 s 등 → 스펙트로그램으로 확인해 tools/lyrics_fix.py 로 고침 (후렴 2–4 는 후렴 1 + 마디 이동). song_track.py lyrics 를 다시 돌리면 lyrics_fix.py 도 다시.
- END(잠든 모모, 눈 감음)는 눈 비율 게이트로 잴 수 없음 — 승인 때 직접 크게 보고 --off-model-ok. 잠옷 첫 이미지가 2번 실패(멜빵바지가 돌아오거나 눈 게이트 < 0.65)하면 멜빵바지로 전환 (사용자 결정).
