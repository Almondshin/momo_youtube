# ep14 기획표 — 고양이와 강아지 (Cat and Dog)

> validate_manifest.py --table 이 생성 (2026-11-06 02:16 UTC). 직접 고치지 말고 manifest.json 을 고친 뒤 다시 실행.

- 제목 EN: Cat, Cat! Dog, Dog! | Animal Sounds Song | Momo Time
- 제목 KO: 고양이·강아지 영어 동요
- 썸네일: c02 + 문구 "CAT & DOG" / "고양이 강아지" (위치 top)
- 컷 37개 (목표 22~28) · V 37 (12~15) · S 0 (6~8) · L 0 (3~4) · 씬 5 (목표 5) — 씬별 8/8/8/8/5
- 예상 길이: EN 1:17 (77.3초, 실제 음성) — 목표 2~3분, build.py 가 실제 음성으로 다시 계산
- 생성할 것: 이미지 6장 (V 6 + S 0), V 클립 6개 (+ 재사용 31컷), 음성 블록 EN 0 (L 컷은 라이브러리)
- V 15개 초과 사유: Short repeated song phrases use 37 playback cuts, but only four new 5-second animal clips; approved dance/clap clips are reused. No 37-clip generation. Source plan approval pending.

## 검증

- △ 총 컷 37개 — 목표 22~28
- △ V 컷 37개 — 목표 12~15 (V 가 15개를 넘으면 manifest.notes.v_over_reason 에 이유를 적고 승인받을 것)
- △ S 컷 0개 — 목표 6~8
- △ L 컷 0개 — 목표 3~4
- △ c04: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c05: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c08: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c09: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c12: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c13: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c20: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c21: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c24: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c25: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c28: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c29: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c32: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c33: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c36: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c37: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ 첫 컷은 L intro_wave(고정 인사) 권장
- △ 마지막 컷은 L outro_bye(고정 작별) 권장
- △ en 키워드 'CAT' 나레이션 반복 0회 (최소 3)
- △ en 키워드 'DOG' 나레이션 반복 0회 (최소 3)

## 컷 표 — 노래 118.10 BPM, 컷은 마디 첫 박에서 바뀜

| 컷 | 씬 | 마디 | 시각 | 종류 | 부르는 가사 | 이미지 프롬프트 (조립된 전체) | 모션 지시 | 새로 만들 것 |
|---|---|---|---|---|---|---|---|---|
| c01 | 0.00–1.99 | dance | — | Opening beat |
| c02 | 1.99–4.10 | cat_wide | CAT | Cat cat Meow meow |
| c03 | 4.10–6.09 | dog_wide | DOG | Dog dog Woof woof |
| c04 | 6.09–8.17 | cat_close | CAT | Cat cat Meow meow |
| c05 | 8.17–10.00 | dog_close | DOG | Dog dog Woof woof |
| c06 | 10.00–12.22 | cat_wide | CAT | Meow meow Meow meow |
| c07 | 12.22–14.07 | dog_wide | DOG | Woof woof Woof woof |
| c08 | 14.07–16.29 | cat_close | CAT | Meow meow Meow meow |
| c09 | 16.29–18.32 | dog_close | DOG | Woof woof Woof woof |
| c10 | 18.32–20.36 | cat_wide | CAT | Cat cat Meow meow |
| c11 | 20.36–22.31 | dog_wide | DOG | Dog dog Woof woof |
| c12 | 22.31–24.43 | cat_close | CAT | Cat cat Meow meow |
| c13 | 24.43–26.44 | dog_close | DOG | Dog dog Woof woof |
| c14 | 26.44–28.50 | cat_wide | CAT | Cat cat Meow meow |
| c15 | 28.50–30.44 | dog_wide | DOG | Dog dog Woof woof |
| c16 | 30.44–32.60 | clap | — | Clap clap Meow meow |
| c17 | 32.60–34.56 | clap | — | Clap clap Woof woof |
| c18 | 34.56–36.62 | cat_wide | CAT | Cat cat Meow meow |
| c19 | 36.62–38.63 | dog_wide | DOG | Dog dog Woof woof |
| c20 | 38.63–40.68 | cat_close | CAT | Cat cat Meow meow |
| c21 | 40.68–42.48 | dog_close | DOG | Dog dog Woof woof |
| c22 | 42.48–44.70 | cat_wide | CAT | Meow meow Meow meow |
| c23 | 44.70–46.58 | dog_wide | DOG | Woof woof Woof woof |
| c24 | 46.58–48.80 | cat_close | CAT | Meow meow Meow meow |
| c25 | 48.80–50.83 | dog_close | DOG | Woof woof Woof woof |
| c26 | 50.83–52.87 | cat_wide | CAT | Cat cat Meow meow |
| c27 | 52.87–54.88 | dog_wide | DOG | Dog dog Woof woof |
| c28 | 54.88–56.94 | cat_close | CAT | Cat cat Meow meow |
| c29 | 56.94–58.98 | dog_close | DOG | Dog dog Woof woof |
| c30 | 58.98–61.01 | cat_wide | CAT | Cat Meow meow |
| c31 | 61.01–62.97 | dog_wide | DOG | Dog Woof woof |
| c32 | 62.97–65.55 | cat_close | CAT | Cat cat Meow meow |
| c33 | 65.55–69.00 | dog_close | DOG | Dog dog Woof woof |
| c34 | 69.00–71.14 | cat_wide | CAT | cat Meow meow |
| c35 | 71.14–73.13 | dog_wide | DOG | Dog dog Woof woof |
| c36 | 73.13–75.08 | cat_close | CAT | Cat Meow meow |
| c37 | 75.08–77.28 | dog_close | DOG | Dog Woof woof |

## 제작 기록

네 이미지와 네 5초 클립을 제작해 담당자가 직접 검수했다. 총 28크레딧, 재생성 없음. 원본 클립은 모두 1280×720, 24fps, 121프레임, 무음이며, 편집에서는 1.8~3.45초만 사용해 끝 프레임 정지나 반복 루프를 피한다. 승인된 기존 춤·박수 클립 두 개를 함께 재사용한다.
