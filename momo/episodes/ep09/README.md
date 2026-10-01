# ep09 — 탈것 소리 (Vehicle Sounds)

> episode_readme.py 가 생성 (2026-10-01 06:33 UTC). 다시 실행하면 덮어쓴다 — 메모는 manifest.notes 에.

## 요약

| 항목 | 값 |
|---|---|
| 상태 | uploaded |
| 주제 | 탈것 소리 / Vehicle Sounds |
| 컷 수 | 30개 (V 28 · S 0 · L 2), 씬 5개 |
| 사용 크레딧 | 127 / 캡 150 (예상 139.8) |
| 생성 / 재생성 횟수 | 34 / 4 |
| 길이 EN | 1:40 (100.4초, 컷 30개, 빌드 2026-10-01T06:32:56+00:00) |
| 썸네일 | c04 — BEEP BEEP! |

## 아동용(made for kids) 설정

> 이 영상은 YouTube 에서 반드시 **"아동용(made for kids)"** 으로 설정해야 한다 (2~5세 대상 키즈 채널 — 지시서 7단계). upload.py 는 config 와 상관없이 `status.selfDeclaredMadeForKids = true` 로 올린다. Studio 에서 직접 올릴 때는 '예, 아동용입니다'를 선택할 것.

- EN: ✔ upload.py 가 selfDeclaredMadeForKids = true 로 업로드함 (Do-0nkw4enM)

## 업로드 결과 (youtube.json)

| 언어 | 영상 | 공개 상태 | 예약 공개 | 업로드 시각 | 썸네일 | 재생목록 |
|---|---|---|---|---|---|---|
| EN | [Do-0nkw4enM](https://www.youtube.com/watch?v=Do-0nkw4enM) | private | — | 2026-10-01T06:33:22Z | ✔ | — |

## 제목·설명·태그

### EN

- 제목: Vehicle Sounds Song with Momo the Bunny | Car, Bus, Train, Fire Truck for Toddlers
- 태그: vehicle sounds, vehicle sounds song, vehicles for kids, car bus train, fire truck song, what does the car say, kids songs, nursery rhymes, toddler songs, learn english for kids, english for toddlers, Momo the Bunny
- 설명:

```text
What does the car say? Beep, beep! Sing along with Momo the Bunny and Ducky by the road and say hello to the car, the bus, the train, the fire truck, the boat and the airplane.

Vehicles and sounds in this song:
Car - beep, beep · Bus - honk, honk · Train - choo, choo
Fire truck - wee-woo · Boat - toot, toot · Airplane - zoom, zoom
Car says beep! Bus says honk! And Ducky says quack, quack!

Made for toddlers and preschoolers (ages 2-5). Music and animation made with AI tools.

#vehiclesounds #vehiclesforkids #kidssongs #nurseryrhymes #toddlersongs #learnenglish #englishforkids #preschool #singalong #MomotheBunny
```

## 생성 기록

| 종류 | 승인 | 시도 | 크레딧 |
|---|---:|---:|---:|
| 컷 이미지 | 15/15 | 18 | 36 |
| V 클립 | 15/15 | 16 | 91 |
| 음성 블록 | 2/2 | 2 | 0 |

라이브러리 L 컷은 0 크레딧 (라이브러리 클립·고정 음성 재사용). 자세한 진행표: `python hf_jobs.py status --ep ep09`

## 승인 기록

- 2026-10-01 노래: Suno v1 'Vehicle Sounds' (122.0 BPM, 파일 1:49.7) — 워크플로 지시에 '사용자 승인 곡'으로 전달됨, song_track.py status --approve 로 기록

## 다음 편에 반영할 점

- Suno v1 이 후렴 4개 중 3번째를 통째로 건너뜀 (태그·스타일에 반복 지시가 있어도) — 곡 고를 때 후렴 횟수를 세고, 다음 가사는 후렴 태그에 '[Chorus 3 - same as before]' 처럼 번호를 붙여 볼 것
- '[Instrumental intro - 4 bars, no vocals]' 를 넣었는데도 전주가 1.5마디(첫 목소리 2.94s) — 인사(1.98s)가 겨우 들어감
- 섹션 사이마다 ≈ 3.5s(1.8마디) 기악 틈 — 앞 컷이 덮게 계획 (CC 8s 립싱크, 탈것 6–8s)
