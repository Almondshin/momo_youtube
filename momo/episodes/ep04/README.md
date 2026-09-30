# ep04 — (주제 미정) (Count to Ten)

> episode_readme.py 가 생성 (2026-09-30 23:19 UTC). 다시 실행하면 덮어쓴다 — 메모는 manifest.notes 에.

## 요약

| 항목 | 값 |
|---|---|
| 상태 | uploaded |
| 주제 |  / Count to Ten |
| 컷 수 | 40개 (V 38 · S 0 · L 2), 씬 5개 |
| 사용 크레딧 | 244.5 / 캡 250 (예상 207.6) |
| 생성 / 재생성 횟수 | 68 / 9 |
| 길이 EN | 2:16 (136.0초, 컷 40개, 빌드 2026-09-30T23:16:53+00:00) |
| 썸네일 | c07 — COUNT TO 10! |

## 아동용(made for kids) 설정

> 이 영상은 YouTube 에서 반드시 **"아동용(made for kids)"** 으로 설정해야 한다 (2~5세 대상 키즈 채널 — 지시서 7단계). upload.py 는 config 와 상관없이 `status.selfDeclaredMadeForKids = true` 로 올린다. Studio 에서 직접 올릴 때는 '예, 아동용입니다'를 선택할 것.

- EN: ✔ upload.py 가 selfDeclaredMadeForKids = true 로 업로드함 (IvuL26c91DY)

## 업로드 결과 (youtube.json)

| 언어 | 영상 | 공개 상태 | 예약 공개 | 업로드 시각 | 썸네일 | 재생목록 |
|---|---|---|---|---|---|---|
| EN | [IvuL26c91DY](https://www.youtube.com/watch?v=IvuL26c91DY) | private | — | 2026-09-30T23:19:08Z | ✔ | — |

## 제목·설명·태그

### EN

- 제목: Count to Ten Song with Momo the Bunny | Numbers 1 to 10 for Toddlers
- 태그: counting song, numbers song, count to 10, 1 to 10, kids songs, nursery rhymes, toddler songs, learn english for kids, english for toddlers, Momo the Bunny
- 설명:

```text
Count from 1 to 10 with Momo the Bunny and Ducky! One, two, three, four, five — six, seven, eight, nine, ten! Count one sun, two clouds, three apples, four blocks and five flowers, then hop, clap, stomp, nod and jump to ten. Ding-dong-dang — we can count to ten!

Numbers in this song: 1 2 3 4 5 6 7 8 9 10

Made for toddlers and preschoolers (ages 2-5). Music and animation made with AI tools.
```

## 생성 기록

| 종류 | 승인 | 시도 | 크레딧 |
|---|---:|---:|---:|
| 컷 이미지 | 25/25 | 29 | 58 |
| V 클립 | 25/25 | 30 | 152.5 |
| 음성 블록 | 2/2 | 2 | 0 |

라이브러리 L 컷은 0 크레딧 (라이브러리 클립·고정 음성 재사용). 자세한 진행표: `python hf_jobs.py status --ep ep04`

## 승인 기록

- 2026-09-30 주제 승인: 숫자 세기 1~5 (Count to Five) — 사용자 선택
- 2026-09-30 형식: ep03 과 같은 노래 형식 (Suno Pro 곡, 컷 1~3마디, 립싱크 + 움직임 + 재사용)
- 2026-09-30 방향 변경 (사용자): 영어 가사 + 한국 동요 리듬, 1~10 세기 — 1~5 사물, 6~10 동작
- 2026-09-30 노래 승인: Suno v1 'Count to Ten' (127.6 BPM, 2:20, 가사 99.2%) — 사용자가 넣어 준 곡
- 2026-09-30 기획 진행: 컷 51개(새 클립 26 · 재사용 21 · L 2), 2:16, 예상 171.5 (여유 포함 207.6) — 사용자 지시 '묻지 말고 끝까지'
- 2026-09-30 v1 비공개 업로드 SJQlbE6_hDk → 사용자 '더 자연스럽게': 가사-화면 어긋남·입 안 움직임·전환 빠름/반복·움직임 어색 모두 선택 → v2 재편집 (+51 크레딧, 예상 248.2/250)

## 다음 편에 반영할 점

- Suno 가 전주(2마디) 대신 카운트인을 불러 인트로 인사가 또 빠짐 — 다음 곡은 가사 첫 줄 전에 '[Instrumental intro 4 bars]' 로 더 분명히
- 구름 2개 컷: seedance 가 두 물체를 서로 끌어당김(3번 중 2번 붙음) — 물체는 고정, 움직임은 반짝이·잎사귀에 줄 것
- 크레딧 정산 2026-09-30: 잔액 400.87 → 213.87 = 187.0 (manifest 기록 187 과 일치)
- 크레딧 정산 v2 2026-09-30: 잔액 213.87 → 162.87 = 51.0 (manifest 기록과 일치), ep04 합계 238/250
- 처음부터 v2 방식으로: 컷은 가사 줄 시작점(cut_at), 모모가 보이는 컷은 전부 립싱크(노래+동작), 후렴은 2줄 1샷, 재사용 립싱크는 보컬 상관으로 위치
