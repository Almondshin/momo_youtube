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
| c01 | 1 | 1–1 | 0:00.0–0:02.0 | 움직임 |  | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, full body in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. The table is out of frame. Feet grounded, arms relaxed, body and both yellow shoulder buttons clearly visible, happy gentle closed-mouth smile. No fruit or other characters. Match the exact bunny face, overalls and peach-mint playroom from the reference. Both feet and both floppy ears fully visible. Remove the table and fruit; keep the same room, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo gently sways left and right, feet stay on the floor, tiny ear sway. Small rhythmic body movement, gentle closed-mouth smile throughout, no singing or talking. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c02 | 1 | 2–2 | 0:02.0–0:04.1 | 움직임 | Cat cat Meow meow | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, seated on the left in a bright pastel playroom with a soft peach wall, mint furniture and a clean cream floor, soft even lighting. On the right sits one small round orange kitten with two softly pointed ears, a cream muzzle and belly, gentle round eyes and a curved orange tail. Momo gently presents the kitten with one low open paw. Both yellow buttons and both long floppy ears fully visible. The kitten is the sole learning subject. Full bodies visible, open lower foreground. Gentle closed-mouth smiles, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo makes one small welcoming paw gesture toward the seated kitten and blinks. The kitten blinks once and gently curls its tail. All mouths stay closed; no singing or talking. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c03 | 1 | 3–3 | 0:04.1–0:06.1 | 움직임 | Dog dog Woof woof | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, seated on the left in a bright pastel playroom with a soft peach wall, mint furniture and a clean cream floor, soft even lighting. On the right sits one small round golden puppy with short floppy tan ears, a cream muzzle and belly, a small rounded brown nose and a short wagging tail. Momo gently presents the puppy with one low open paw. Match the same bunny proportions and room as the reference. Both yellow buttons and both long floppy ears fully visible. The puppy is the sole learning subject. Full bodies visible, open lower foreground. Gentle closed-mouth smiles, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo makes one small welcoming paw gesture toward the seated puppy and blinks. The puppy blinks once and gently wags its tail. All mouths stay closed; no singing or talking. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c04 | 1 | 4–4 | 0:06.1–0:08.2 | 움직임 | Cat cat Meow meow | Medium close-up of one small round orange kitten with two softly pointed ears, a cream muzzle and belly, gentle round eyes and a curved orange tail, sitting on the cream floor in a bright pastel playroom with a soft peach wall, mint furniture and a clean cream floor, soft even lighting. Match the kitten markings and proportions in the reference. Entire head, both ears, front paws and curved tail visible. Kitten centered, uncluttered lower foreground. Only the kitten in frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | The seated kitten blinks slowly and gently curls its tail. Its shape and markings stay unchanged. Keep the mouth closed. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c05 | 1 | 5–5 | 0:08.2–0:10.0 | 움직임 | Dog dog Woof woof | Medium close-up of one small round golden puppy with short floppy tan ears, a cream muzzle and belly, a small rounded brown nose and a short wagging tail, sitting on the cream floor in a bright pastel playroom with a soft peach wall, mint furniture and a clean cream floor, soft even lighting. Match the puppy markings and proportions in the reference. Entire head, both ears, front paws and short tail visible. Puppy centered, uncluttered lower foreground. Only the puppy in frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | The seated puppy blinks slowly and gently wags its tail. Its shape and markings stay unchanged. Keep the mouth closed. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c06 | 1 | 6–6 | 0:10.0–0:12.2 | 재사용 c02 0s~ | Meow meow Meow meow |  |  | 0 |
| c07 | 1 | 7–7 | 0:12.2–0:14.1 | 재사용 c03 0s~ | Woof woof Woof woof |  |  | 0 |
| c08 | 1 | 8–8 | 0:14.1–0:16.3 | 재사용 c04 0s~ | Meow meow Meow meow |  |  | 0 |
| c09 | 2 | 9–9 | 0:16.3–0:18.3 | 재사용 c05 0s~ | Woof woof Woof woof |  |  | 0 |
| c10 | 2 | 10–10 | 0:18.3–0:20.4 | 재사용 c02 0s~ | Cat cat Meow meow |  |  | 0 |
| c11 | 2 | 11–11 | 0:20.4–0:22.3 | 재사용 c03 0s~ | Dog dog Woof woof |  |  | 0 |
| c12 | 2 | 12–12 | 0:22.3–0:24.4 | 재사용 c04 0s~ | Cat cat Meow meow |  |  | 0 |
| c13 | 2 | 13–13 | 0:24.4–0:26.4 | 재사용 c05 0s~ | Dog dog Woof woof |  |  | 0 |
| c14 | 2 | 14–14 | 0:26.4–0:28.5 | 재사용 c02 0s~ | Cat cat Meow meow |  |  | 0 |
| c15 | 2 | 15–15 | 0:28.5–0:30.4 | 재사용 c03 0s~ | Dog dog Woof woof |  |  | 0 |
| c16 | 2 | 16–16 | 0:30.4–0:32.6 | 움직임 | Clap clap Meow meow | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, standing upright at the center of the same peach and mint playroom as the reference. Wide full-body framing from the top of both ears down to both feet, with generous visible floor below the feet and headroom above the ears. Both feet planted on the floor. Both hands are separated in front of the lower belly below the overall pocket, ready for a clap; both yellow shoulder strap buttons are clearly visible above the hands. Lips gently closed with a small soft smile, no open mouth. Head upright. The same exact face and outfit as the reference. No fruit or extra characters. No table in the foreground, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo performs three clearly separated claps at waist height: paws open apart, touch briefly, then open apart again, repeating smoothly. Keep elbows down and paws low in front of the shorts throughout; both yellow shoulder buttons stay fully visible above the paws. Each contact is brief, with an obvious open position between claps. The feet stay planted, head upright, lips closed with a gentle smile. Preserve exactly the face, floppy ears, outfit and body proportions of the first frame. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c17 | 3 | 17–17 | 0:32.6–0:34.6 | 재사용 c16 0s~ | Clap clap Woof woof |  |  | 0 |
| c18 | 3 | 18–18 | 0:34.6–0:36.6 | 재사용 c02 0s~ | Cat cat Meow meow |  |  | 0 |
| c19 | 3 | 19–19 | 0:36.6–0:38.6 | 재사용 c03 0s~ | Dog dog Woof woof |  |  | 0 |
| c20 | 3 | 20–20 | 0:38.6–0:40.7 | 재사용 c04 0s~ | Cat cat Meow meow |  |  | 0 |
| c21 | 3 | 21–21 | 0:40.7–0:42.5 | 재사용 c05 0s~ | Dog dog Woof woof |  |  | 0 |
| c22 | 3 | 22–22 | 0:42.5–0:44.7 | 재사용 c02 0s~ | Meow meow Meow meow |  |  | 0 |
| c23 | 3 | 23–23 | 0:44.7–0:46.6 | 재사용 c03 0s~ | Woof woof Woof woof |  |  | 0 |
| c24 | 3 | 24–24 | 0:46.6–0:48.8 | 재사용 c04 0s~ | Meow meow Meow meow |  |  | 0 |
| c25 | 4 | 25–25 | 0:48.8–0:50.8 | 재사용 c05 0s~ | Woof woof Woof woof |  |  | 0 |
| c26 | 4 | 26–26 | 0:50.8–0:52.9 | 재사용 c02 0s~ | Cat cat Meow meow |  |  | 0 |
| c27 | 4 | 27–27 | 0:52.9–0:54.9 | 재사용 c03 0s~ | Dog dog Woof woof |  |  | 0 |
| c28 | 4 | 28–28 | 0:54.9–0:56.9 | 재사용 c04 0s~ | Cat cat Meow meow |  |  | 0 |
| c29 | 4 | 29–29 | 0:56.9–0:59.0 | 재사용 c05 0s~ | Dog dog Woof woof |  |  | 0 |
| c30 | 4 | 30–30 | 0:59.0–1:01.0 | 재사용 c02 0s~ | Cat Meow meow |  |  | 0 |
| c31 | 4 | 31–31 | 1:01.0–1:03.0 | 재사용 c03 0s~ | Dog Woof woof |  |  | 0 |
| c32 | 4 | 32–32 | 1:03.0–1:05.5 | 재사용 c04 0s~ | Cat cat Meow meow |  |  | 0 |
| c33 | 5 | 33–33 | 1:05.5–1:09.0 | 재사용 c05 0s~ | Dog dog Woof woof |  |  | 0 |
| c34 | 5 | 34–34 | 1:09.0–1:11.1 | 재사용 c02 0s~ | cat Meow meow |  |  | 0 |
| c35 | 5 | 35–35 | 1:11.1–1:13.1 | 재사용 c03 0s~ | Dog dog Woof woof |  |  | 0 |
| c36 | 5 | 36–36 | 1:13.1–1:15.1 | 재사용 c04 0s~ | Cat Meow meow |  |  | 0 |
| c37 | 5 | 37–37 | 1:15.1–1:17.3 | 재사용 c05 0s~ | Dog Woof woof |  |  | 0 |
