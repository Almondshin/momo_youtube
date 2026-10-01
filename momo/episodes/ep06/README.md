# ep06 — 동물 소리 (Animal Sounds)

> episode_readme.py 가 생성 (2026-10-01 02:21 UTC). 다시 실행하면 덮어쓴다 — 메모는 manifest.notes 에.

## 요약

| 항목 | 값 |
|---|---|
| 상태 | uploaded |
| 주제 | 동물 소리 / Animal Sounds |
| 컷 수 | 33개 (V 31 · S 0 · L 2), 씬 5개 |
| 사용 크레딧 | 75.5 / 캡 250 (예상 139.2) |
| 생성 / 재생성 횟수 | 35 / 3 |
| Higgsfield API | $2.70 (생성 8회, 구독 크레딧과 별개) |
| 길이 EN | 1:45 (105.3초, 컷 33개, 빌드 2026-10-01T02:21:19+00:00) |
| 썸네일 | c03 — ANIMAL SOUNDS! |

## 아동용(made for kids) 설정

> 이 영상은 YouTube 에서 반드시 **"아동용(made for kids)"** 으로 설정해야 한다 (2~5세 대상 키즈 채널 — 지시서 7단계). upload.py 는 config 와 상관없이 `status.selfDeclaredMadeForKids = true` 로 올린다. Studio 에서 직접 올릴 때는 '예, 아동용입니다'를 선택할 것.

- EN: ✔ upload.py 가 selfDeclaredMadeForKids = true 로 업로드함 (Yw7kZuzYS88)

## 업로드 결과 (youtube.json)

| 언어 | 영상 | 공개 상태 | 예약 공개 | 업로드 시각 | 썸네일 | 재생목록 |
|---|---|---|---|---|---|---|
| EN | [Yw7kZuzYS88](https://www.youtube.com/watch?v=Yw7kZuzYS88) | private | — | 2026-10-01T02:21:43Z | ✔ | — |

## 제목·설명·태그

### EN

- 제목: Animal Sounds Song with Momo the Bunny | Farm Animals Moo, Baa, Oink for Toddlers
- 태그: animal sounds, animal sounds song, farm animals, farm animals for kids, what does the cow say, kids songs, nursery rhymes, toddler songs, learn english for kids, english for toddlers, preschool songs, Momo the Bunny
- 설명:

```text
What does the cow say? Moo, moo, moo! Sing along with Momo the Bunny and Ducky on the farm and say hello to the cow, the sheep, the pig, the horse, Ducky the duck and the hen.

Animals and sounds in this song:
Cow - moo · Sheep - baa · Pig - oink
Horse - neigh · Duck - quack · Hen - cluck
Cow says moo! Sheep says baa! Yay, we can sing them all!

Made for toddlers and preschoolers (ages 2-5). Music and animation made with AI tools.

#animalsounds #farmanimals #kidssongs #nurseryrhymes #toddlersongs #learnenglish #englishforkids #preschool #singalong #MomotheBunny
```

## 생성 기록

| 종류 | 승인 | 시도 | 크레딧 |
|---|---:|---:|---:|
| 컷 이미지 | 16/16 | 19 | 38 |
| V 클립 | 16/16 | 16 | 37.5 |
| 음성 블록 | 2/2 | 2 | 0 |

라이브러리 L 컷은 0 크레딧 (라이브러리 클립·고정 음성 재사용). 자세한 진행표: `python hf_jobs.py status --ep ep06`

## 승인 기록

- 2026-10-01 사용자: ep05~07 병렬 제작·업로드 지시, 묻지 말고 진행
- 2026-10-01 노래 승인: Suno v1 'Animal Sounds on the Farm' (125.6 BPM, 파일 2:14, 가사 95.8%) — 사용자가 넣어 준 곡
- 2026-10-01 API 잔액 소진 → 사용자 지시 '모자르면 구독으로': ep06 남은 클립 8개를 구독(MCP)으로, c08·c15·c22 는 4초 + pingpong 으로 크레딧 맞춤

## 다음 편에 반영할 점

- Suno v1 은 노래를 100.8초에 끝내고 16마디(31초) 기악 아웃트로를 붙임 → 영상은 마디 55(105.3초)에서 끝냄 (노래 비율 92%, 길이 1:45). 다음 곡은 가사 끝 [Outro - 2 bars, final chord] 를 더 분명히, 또는 Suno 에서 곡 자르기
- 정렬기(whisper) 오류 3종: 후렴 3 'Sing with me' 를 앞 줄에 붙임, 'Hello, sheep/horse/hen' 의 Hello 를 1초 늦게, 후렴 3 'with' 를 보정이 다음 음에 붙임 — 후렴은 서로 같은 꼴이므로 다른 후렴과 비교해 고칠 것
- 검토(2026-10-01): 정렬기·note_end 가 놓친 경계 2곳 — 2음절 'Ducky' 의 '-y'(64.90–65.12) 와 레가토 'say'→'Neigh'(44.06) — c21·c15 cut_at 을 보컬 스템 엔벌로프로 옮김. 립싱크 모션은 마지막 주어가 모모여야 함 (동물·Ducky 뒤에 'sings' 가 오면 그쪽이 노래할 수 있음)
