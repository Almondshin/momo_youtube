# ep13 기획표 — 사과 톡! 바나나 통! (Apple Tap Banana Bounce — Korean)

> validate_manifest.py --table 이 생성 (2026-11-05 22:59 UTC). 직접 고치지 말고 manifest.json 을 고친 뒤 다시 실행.

- 제목 EN: (미정)
- 제목 KO: 사과 톡! 바나나 통! | 박수 치며 배우는 과일 동요 | 모모타임 MomoTime
- 썸네일: c01 + 문구 "" / "사과 바나나" (위치 top)
- 컷 37개 (목표 22~28) · V 36 (12~15) · S 0 (6~8) · L 1 (3~4) · 씬 5 (목표 5) — 씬별 7/8/7/8/7
- 예상 길이: KO 1:22 (81.6초, 실제 음성) — 목표 2~3분, build.py 가 실제 음성으로 다시 계산
- 생성할 것: 이미지 6장 (V 6 + S 0), V 클립 6개 (+ 재사용 30컷), 음성 블록 KO 0 (L 컷은 라이브러리)
- V 15개 초과 사유: 36 V edit cuts reuse six approved ep12 source clips. User authorized common visuals for Korean production; 0 new generations.

## 검증

- △ 총 컷 37개 — 목표 22~28
- △ V 컷 36개 — 목표 12~15 (V 가 15개를 넘으면 manifest.notes.v_over_reason 에 이유를 적고 승인받을 것)
- △ S 컷 0개 — 목표 6~8
- △ L 컷 1개 — 목표 3~4
- △ c07: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c07: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c08: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c08: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c19: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c19: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c20: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c20: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c23: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c23: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c24: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c24: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c31: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c31: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ c32: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c32: 모션 지시에 위험 단어 ['zoom'] — 작게, 카메라 고정
- △ 첫 컷은 L intro_wave(고정 인사) 권장
- △ ko 키워드 '바나나' 나레이션 반복 0회 (최소 3)
- △ ko 키워드 '사과' 나레이션 반복 0회 (최소 3)

## 컷 표 — 노래 117.98 BPM, 컷은 마디 첫 박에서 바뀜

| 컷 | 씬 | 마디 | 시각 | 종류 | 부르는 가사 | 이미지 프롬프트 (조립된 전체) | 모션 지시 | 새로 만들 것 |
|---|---|---|---|---|---|---|---|---|
| c01 | 1 | 1–1 | 0:00.0–0:02.5 | 움직임 | 사과 사과 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, beside the low round cream table in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. Exactly one red apple resting on the table. Momo gently points toward it. Both yellow shoulder buttons and both floppy ears clearly visible. Fruit unobstructed, uncluttered lower foreground, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo gently points at the single apple, blinks once and makes a tiny nod. The apple stays still on the table. Keep a gentle closed-mouth smile throughout, no singing or talking. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c02 | 1 | 2–2 | 0:02.5–0:03.5 | 움직임 | 바나나 바나나 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, beside the low round cream table in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. Exactly one whole curved yellow banana resting on the table, not a bunch. Momo gently points toward it. Both yellow shoulder buttons and floppy ears visible. Fruit unobstructed, uncluttered lower foreground, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo gently points at the one banana, blinks once and makes a tiny nod. The banana stays still on the table. Keep a gentle closed-mouth smile throughout, no singing or talking. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c03 | 1 | 3–3 | 0:03.5–0:07.6 | 움직임 | 톡톡 사과 / 통통 바나나 / 사과 톡 / 바나나 통 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, full body in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. The table is out of frame. Feet grounded, arms relaxed, body and both yellow shoulder buttons clearly visible, happy gentle closed-mouth smile. No fruit or other characters. Match the exact bunny face, overalls and peach-mint playroom from the reference. Both feet and both floppy ears fully visible. Remove the table and fruit; keep the same room, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo gently sways left and right, feet stay on the floor, tiny ear sway. Small rhythmic body movement, gentle closed-mouth smile throughout, no singing or talking. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c04 | 1 | 4–4 | 0:07.6–0:09.5 | 움직임 | 톡톡 통통 / 짝짝짝 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, standing upright at the center of the same peach and mint playroom as the reference. Wide full-body framing from the top of both ears down to both feet, with generous visible floor below the feet and headroom above the ears. Both feet planted on the floor. Both hands are separated in front of the lower belly below the overall pocket, ready for a clap; both yellow shoulder strap buttons are clearly visible above the hands. Lips gently closed with a small soft smile, no open mouth. Head upright. The same exact face and outfit as the reference. No fruit or extra characters. No table in the foreground, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo performs three clearly separated claps at waist height: paws open apart, touch briefly, then open apart again, repeating smoothly. Keep elbows down and paws low in front of the shorts throughout; both yellow shoulder buttons stay fully visible above the paws. Each contact is brief, with an obvious open position between claps. The feet stay planted, head upright, lips closed with a gentle smile. Preserve exactly the face, floppy ears, outfit and body proportions of the first frame. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c05 | 1 | 5–5 | 0:09.5–0:12.6 | 재사용 c03 0s~ | 톡톡 톡톡 / 통통 통통 / 모모랑 같이 |  |  | 0 |
| c06 | 1 | 6–6 | 0:12.6–0:15.6 | 재사용 c04 0s~ | 짝짝짝 |  |  | 0 |
| c07 | 1 | 7–7 | 0:15.6–0:16.7 | 움직임 | 사과 사과 | Close-up of exactly one red apple with a short brown stem on the low round cream table in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. Same apple shape, lighting and set as the Momo apple shot, recognizable rounded apple silhouette. No characters in frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Smooth digital zoom-in from 100% to 118% over 5 seconds with gentle ease-in/ease-out. The apple, background and lighting stay unchanged; no generated motion. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c08 | 2 | 8–8 | 0:16.7–0:17.7 | 움직임 | 바나나 바나나 | Close-up of exactly one whole curved yellow banana on the low round cream table in a bright pastel playroom with a soft peach wall, mint accent furniture and a low round cream table, softly lit, single full-bleed scene. Same banana shape, lighting and set as the Momo banana shot. Smooth intact peel, not a bunch. No characters in frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Smooth digital zoom-in from 100% to 118% over 5 seconds with gentle ease-in/ease-out. The banana, background and lighting stay unchanged; no generated motion. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 5초 (5) |
| c09 | 2 | 9–9 | 0:17.7–0:21.7 | 재사용 c03 0s~ | 톡톡 사과 / 통통 바나나 / 사과 톡 / 바나나 통 |  |  | 0 |
| c10 | 2 | 10–10 | 0:21.7–0:23.7 | 재사용 c04 0s~ | 톡톡 통통 / 짝짝짝 |  |  | 0 |
| c11 | 2 | 11–11 | 0:23.7–0:25.8 | 재사용 c03 0s~ | 사과 바나나 |  |  | 0 |
| c12 | 2 | 12–12 | 0:25.8–0:27.9 | 재사용 c04 0s~ | 짝짝짝 |  |  | 0 |
| c13 | 2 | 13–13 | 0:27.9–0:28.9 | 재사용 c01 0s~ | 사과 사과 |  |  | 0 |
| c14 | 2 | 14–14 | 0:28.9–0:29.9 | 재사용 c02 0s~ | 바나나 바나나 |  |  | 0 |
| c15 | 2 | 15–15 | 0:29.9–0:33.8 | 재사용 c03 0s~ | 톡톡 사과 / 통통 바나나 / 사과 톡 / 바나나 통 |  |  | 0 |
| c16 | 3 | 16–16 | 0:33.8–0:36.0 | 재사용 c04 0s~ | 톡톡 통통 / 짝짝짝 |  |  | 0 |
| c17 | 3 | 17–17 | 0:36.0–0:39.1 | 재사용 c03 0s~ | 톡톡 톡톡 / 통통 통통 / 모모랑 같이 |  |  | 0 |
| c18 | 3 | 18–18 | 0:39.1–0:42.0 | 재사용 c04 0s~ | 짝짝짝 |  |  | 0 |
| c19 | 3 | 19–19 | 0:42.0–0:43.2 | 재사용 c07 0s~ | 사과 사과 |  |  | 0 |
| c20 | 3 | 20–20 | 0:43.2–0:44.1 | 재사용 c08 0s~ | 바나나 바나나 |  |  | 0 |
| c21 | 3 | 21–21 | 0:44.1–0:48.1 | 재사용 c03 0s~ | 톡톡 사과 / 통통 바나나 / 사과 톡 / 바나나 통 |  |  | 0 |
| c22 | 3 | 22–22 | 0:48.1–0:50.2 | 재사용 c04 0s~ | 톡톡 통통 / 짝짝짝 |  |  | 0 |
| c23 | 4 | 23–23 | 0:50.2–0:52.3 | 재사용 c07 0s~ | 사과 사과 / 톡톡톡 |  |  | 0 |
| c24 | 4 | 24–24 | 0:52.3–0:54.2 | 재사용 c08 0s~ | 바나나 바나나 / 통통통 |  |  | 0 |
| c25 | 4 | 25–25 | 0:54.2–0:55.3 | 재사용 c01 0s~ | 사과 사과 |  |  | 0 |
| c26 | 4 | 26–26 | 0:55.3–0:56.3 | 재사용 c02 0s~ | 바나나 바나나 |  |  | 0 |
| c27 | 4 | 27–27 | 0:56.3–1:00.3 | 재사용 c03 0s~ | 톡톡 사과 / 통통 바나나 / 사과 톡 / 바나나 통 |  |  | 0 |
| c28 | 4 | 28–28 | 1:00.3–1:02.4 | 재사용 c04 0s~ | 톡톡 통통 / 짝짝짝 |  |  | 0 |
| c29 | 4 | 29–29 | 1:02.4–1:05.4 | 재사용 c03 0s~ | 톡톡 톡톡 / 통통 통통 / 모모랑 같이 |  |  | 0 |
| c30 | 4 | 30–30 | 1:05.4–1:08.5 | 재사용 c04 0s~ | 짝짝짝 |  |  | 0 |
| c31 | 5 | 31–31 | 1:08.5–1:09.6 | 재사용 c07 0s~ | 사과 |  |  | 0 |
| c32 | 5 | 32–32 | 1:09.6–1:10.6 | 재사용 c08 0s~ | 바나나 바나나 |  |  | 0 |
| c33 | 5 | 33–33 | 1:10.6–1:14.3 | 재사용 c03 0s~ | 톡톡 사과 / 통통 바나나 / 사과 톡 / 바나나 통 |  |  | 0 |
| c34 | 5 | 34–34 | 1:14.3–1:16.6 | 재사용 c04 0s~ | 톡톡 통통 / 짝짝짝 |  |  | 0 |
| c35 | 5 | 35–35 | 1:16.6–1:18.7 | 재사용 c03 0s~ | 사과 바나나 |  |  | 0 |
| c36 | 5 | 36–36 | 1:18.7–1:20.2 | 재사용 c04 0s~ | 짝짝짝 |  |  | 0 |
| c37 | 5 | 37–37 | 1:20.2–1:21.6 | L `outro_bye` |  | (라이브러리) |  | — |
