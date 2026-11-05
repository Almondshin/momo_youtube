# ep12 기획표 — 사과와 바나나 (Apple & Banana)

> validate_manifest.py --table 이 생성 (2026-11-05 06:22 UTC). 직접 고치지 말고 manifest.json 을 고친 뒤 다시 실행.

- 제목 EN: Apple & Banana Song for Toddlers | Learn Fruit Words | MomoTime
- 제목 KO: (미정)
- 썸네일: c01 + 문구 "APPLE & BANANA" / "" (위치 bottom)
- 컷 35개 (목표 22~28) · V 34 (12~15) · S 0 (6~8) · L 1 (3~4) · 씬 5 (목표 5) — 씬별 10/10/2/8/5
- 예상 길이: EN 1:30 (90.0초, 실제 음성) — 목표 2~3분, build.py 가 실제 음성으로 다시 계산
- 생성할 것: 이미지 6장 (V 6 + S 0), V 클립 6개 (+ 재사용 28컷), 음성 블록 EN 0 (L 컷은 라이브러리)
- V 15개 초과 사유: 90초 노래의 짧은 반복 가사에 맞춘 34개 V 편집 컷. 실제 신규 생성은 시작 이미지 6장과 5초 클립 6개뿐이며, 나머지는 clip_from으로 재사용한다. 2026-11-05 사용자 기획 승인.

## 검증

- △ 총 컷 35개 — 목표 22~28
- △ V 컷 34개 — 목표 12~15 (V 가 15개를 넘으면 manifest.notes.v_over_reason 에 이유를 적고 승인받을 것)
- △ S 컷 0개 — 목표 6~8
- △ L 컷 1개 — 목표 3~4
- △ c02: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c02: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c05: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c05: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c06: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c06: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c12: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c12: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c15: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c15: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c16: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c16: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c25: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c25: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c26: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c26: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c31: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c31: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c32: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c32: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ 첫 컷은 L intro_wave(고정 인사) 권장
- △ en 키워드 'APPLE' 나레이션 반복 0회 (최소 3)
- △ en 키워드 'BANANA' 나레이션 반복 0회 (최소 3)

## 컷 표 — 노래 113.76 BPM, 컷은 마디 첫 박에서 바뀜

| 컷 | 씬 | 마디 | 시각 | 종류 | 부르는 가사 | 이미지 프롬프트 (조립된 전체) | 모션 지시 | 새로 만들 것 |
|---|---|---|---|---|---|---|---|---|
| c01 | 1 | 1–2 | 0:00.0–0:05.6 | 움직임 | Apple, apple! / Here is an apple. | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, beside the low round cream table in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. Exactly one red apple resting on the table. Momo gently points toward it. Both yellow shoulder buttons and both floppy ears clearly visible. Fruit unobstructed, uncluttered lower foreground, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo gently points at the single apple, blinks once and makes a tiny nod. The apple stays still on the table. Keep a gentle closed-mouth smile throughout, no singing or talking. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c02 | 1 | 3–4 | 0:05.6–0:09.2 | 움직임 | Apple, apple! / I see an apple. | Close-up of exactly one red apple with a short brown stem on the low round cream table in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. Same apple shape, lighting and set as the Momo apple shot, recognizable rounded apple silhouette. No characters in frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Smooth digital zoom-in from 100% to 118% over 5 seconds with gentle ease-in/ease-out. The apple, background and lighting stay unchanged; no generated motion. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c03 | 1 | 5–5 | 0:09.2–0:11.1 | 재사용 c01 0s~ | Apple, apple! |  |  | 0 |
| c04 | 1 | 6–6 | 0:11.1–0:13.5 | 움직임 | Banana, banana! | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, beside the low round cream table in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. Exactly one whole curved yellow banana resting on the table, not a bunch. Momo gently points toward it. Both yellow shoulder buttons and floppy ears visible. Fruit unobstructed, uncluttered lower foreground, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo gently points at the one banana, blinks once and makes a tiny nod. The banana stays still on the table. Keep a gentle closed-mouth smile throughout, no singing or talking. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c05 | 1 | 7–7 | 0:13.5–0:15.3 | 재사용 c02 0s~ | Apple, apple! |  |  | 0 |
| c06 | 1 | 8–8 | 0:15.3–0:17.7 | 움직임 | Banana, banana! | Close-up of exactly one whole curved yellow banana on the low round cream table in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. Same banana shape, lighting and set as the Momo banana shot. Smooth intact peel, not a bunch. No characters in frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Smooth digital zoom-in from 100% to 118% over 5 seconds with gentle ease-in/ease-out. The banana, background and lighting stay unchanged; no generated motion. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c07 | 1 | 9–9 | 0:17.7–0:19.1 | 재사용 c01 0s~ | Apple, apple! |  |  | 0 |
| c08 | 1 | 10–10 | 0:19.1–0:21.7 | 움직임 | Sing along with me. | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, full body in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. The table is out of frame. Feet grounded, arms relaxed, body and both yellow shoulder buttons clearly visible, happy gentle closed-mouth smile. No fruit or other characters. Match the exact bunny face, overalls and peach-mint playroom from the reference. Both feet and both floppy ears fully visible. Remove the table and fruit; keep the same room, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo gently sways left and right, feet stay on the floor, tiny ear sway. Small rhythmic body movement, gentle closed-mouth smile throughout, no singing or talking. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c09 | 1 | 11–11 | 0:21.7–0:23.6 | 재사용 c04 0s~ | Banana, banana! |  |  | 0 |
| c10 | 1 | 12–12 | 0:23.6–0:25.9 | 움직임 | Sing and clap with me! | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, standing upright at the center of the same peach and mint playroom as the reference. Wide full-body framing from the top of both ears down to both feet, with generous visible floor below the feet and headroom above the ears. Both feet planted on the floor. Both hands are separated in front of the lower belly below the overall pocket, ready for a clap; both yellow shoulder strap buttons are clearly visible above the hands. Lips gently closed with a small soft smile, no open mouth. Head upright. The same exact face and outfit as the reference. No fruit or extra characters. No table in the foreground, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo performs three clearly separated claps at waist height: paws open apart, touch briefly, then open apart again, repeating smoothly. Keep elbows down and paws low in front of the shorts throughout; both yellow shoulder buttons stay fully visible above the paws. Each contact is brief, with an obvious open position between claps. The feet stay planted, head upright, lips closed with a gentle smile. Preserve exactly the face, floppy ears, outfit and body proportions of the first frame. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c11 | 2 | 13–14 | 0:25.9–0:30.1 | 재사용 c04 0s~ | Banana, banana! / Here is a banana. |  |  | 0 |
| c12 | 2 | 15–16 | 0:30.1–0:34.6 | 재사용 c06 0s~ | Banana, banana! / I see a banana. |  |  | 0 |
| c13 | 2 | 17–17 | 0:34.6–0:36.4 | 재사용 c01 0s~ | Apple, apple! |  |  | 0 |
| c14 | 2 | 18–18 | 0:36.4–0:38.8 | 재사용 c04 0s~ | Banana, banana! |  |  | 0 |
| c15 | 2 | 19–19 | 0:38.8–0:40.6 | 재사용 c02 0s~ | Apple, apple! |  |  | 0 |
| c16 | 2 | 20–20 | 0:40.6–0:43.0 | 재사용 c06 0s~ | Banana, banana! |  |  | 0 |
| c17 | 2 | 21–21 | 0:43.0–0:44.4 | 재사용 c01 0s~ | Apple, apple! |  |  | 0 |
| c18 | 2 | 22–22 | 0:44.4–0:47.0 | 재사용 c08 0s~ | Sing along with me. |  |  | 0 |
| c19 | 2 | 23–23 | 0:47.0–0:48.9 | 재사용 c04 0s~ | Banana, banana! |  |  | 0 |
| c20 | 2 | 24–24 | 0:48.9–0:51.5 | 재사용 c10 0s~ | Sing and clap with me! |  |  | 0 |
| c21 | 3 | 25–26 | 0:51.5–0:55.5 | 재사용 c01 0s~ | Apple, apple! / Can you say apple? |  |  | 0 |
| c22 | 3 | 27–28 | 0:55.5–0:59.9 | 재사용 c04 0s~ | Banana, banana! / Can you say banana? |  |  | 0 |
| c23 | 4 | 29–29 | 0:59.9–1:01.7 | 재사용 c01 0s~ | Apple, apple! |  |  | 0 |
| c24 | 4 | 30–30 | 1:01.7–1:04.1 | 재사용 c04 0s~ | Banana, banana! |  |  | 0 |
| c25 | 4 | 31–31 | 1:04.1–1:05.9 | 재사용 c02 0s~ | Apple, apple! |  |  | 0 |
| c26 | 4 | 32–32 | 1:05.9–1:08.3 | 재사용 c06 0s~ | Banana, banana! |  |  | 0 |
| c27 | 4 | 33–33 | 1:08.3–1:09.8 | 재사용 c01 0s~ | Apple, apple! |  |  | 0 |
| c28 | 4 | 34–34 | 1:09.8–1:12.3 | 재사용 c08 0s~ | Sing along with me. |  |  | 0 |
| c29 | 4 | 35–35 | 1:12.3–1:14.2 | 재사용 c04 0s~ | Banana, banana! |  |  | 0 |
| c30 | 4 | 36–36 | 1:14.2–1:16.8 | 재사용 c10 0s~ | Sing and clap with me! |  |  | 0 |
| c31 | 5 | 37–37 | 1:16.8–1:18.6 | 재사용 c02 0s~ | Apple, apple! |  |  | 0 |
| c32 | 5 | 38–38 | 1:18.6–1:21.0 | 재사용 c06 0s~ | Banana, banana! |  |  | 0 |
| c33 | 5 | 39–39 | 1:21.0–1:22.8 | 재사용 c01 0s~ | Apple, apple! |  |  | 0 |
| c34 | 5 | 40–40 | 1:22.8–1:25.2 | 재사용 c04 0s~ | Banana, banana! |  |  | 0 |
| c35 | 5 | 41–41 | 1:25.2–1:30.0 | L `outro_bye` | Apple, banana! / Bye-bye, bye-bye! | (라이브러리) |  | — |
