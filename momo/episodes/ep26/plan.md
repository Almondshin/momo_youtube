# ep26 기획표 — 당근 브로콜리 옥수수 (Carrot, Broccoli and Corn)

> validate_manifest.py --table 이 생성 (2026-11-26 23:23 UTC). 직접 고치지 말고 manifest.json 을 고친 뒤 다시 실행.

- 제목 EN: Carrot, Broccoli, Corn! 🥕🌽 | Veggie Dance Song for Toddlers | Momo Time
- 제목 KO: (미정)
- 썸네일: c04 + 문구 "CARROT · BROCCOLI · CORN" / "" (위치 bottom)
- 컷 35개 (목표 22~28) · V 35 (12~15) · S 0 (6~8) · L 0 (3~4) · 씬 5 (목표 5) — 씬별 8/7/7/8/5
- 예상 길이: EN 1:20 (79.9초, 실제 음성) — 목표 2~3분, build.py 가 실제 음성으로 다시 계산
- 생성할 것: 이미지 6장 (V 6 + S 0), V 클립 6개 (+ 재사용 29컷), 음성 블록 EN 0 (L 컷은 라이브러리)
- V 15개 초과 사유: Current short-song policy: reuse six approved non-lipsync sources, recut to the new song. No fixed spoken intro/outro.

## 검증

- △ 총 컷 35개 — 목표 22~28
- △ V 컷 35개 — 목표 12~15 (V 가 15개를 넘으면 manifest.notes.v_over_reason 에 이유를 적고 승인받을 것)
- △ S 컷 0개 — 목표 6~8
- △ L 컷 0개 — 목표 3~4
- △ c01: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c04: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c02: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c07: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c03: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c08: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c09: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c10: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c11: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c12: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c13: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c14: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c15: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c16: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c17: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c18: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c20: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c25: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c26: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c27: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c28: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c29: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c31: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c31: en 키워드는 1개 단어만 ('CARROT · BROCCOLI · CORN') — 문장 자막 금지
- △ c33: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c33: en 키워드는 1개 단어만 ('CARROT · BROCCOLI · CORN') — 문장 자막 금지
- △ c01: 첫 컷의 cut_at 은 쓰이지 않는다 (0 에서 시작)
- △ 첫 컷은 L intro_wave(고정 인사) 권장
- △ 마지막 컷은 L outro_bye(고정 작별) 권장
- △ en 키워드 'BROCCOLI' 나레이션 반복 0회 (최소 3)
- △ en 키워드 'CARROT' 나레이션 반복 0회 (최소 3)
- △ en 키워드 'CARROT · BROCCOLI · CORN' 나레이션 반복 0회 (최소 3)
- △ en 키워드 'CORN' 나레이션 반복 0회 (최소 3)
- △ 썸네일 문구(en) 3단어 이하 권장: 'CARROT · BROCCOLI · CORN'

## 컷 표 — 노래 110.01 BPM, 컷은 마디 첫 박에서 바뀜

| 컷 | 씬 | 마디 | 시각 | 종류 | 부르는 가사 | 이미지 프롬프트 (조립된 전체) | 모션 지시 | 새로 만들 것 |
|---|---|---|---|---|---|---|---|---|
| c01 | 1 | 1–1 | 0:00.0–0:02.4 | 움직임 · 카드 CARROT | Carrot, carrot, wiggle with me | close-up of one bright orange carrot with fresh green leaves on a small white plate on the round wooden table, the bright pastel kitchen with soft mint-green cabinets softly blurred behind, clear empty space on the left side of the frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | the carrot gives a small happy wiggle, tiny sparkles twinkle around it. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c04 | 1 | 2–2 | 0:02.4–0:04.7 | 움직임 | Carrot, carrot, wiggle with me | close-up of one small white plate on the round wooden table holding exactly three vegetables side by side: one orange carrot, one green broccoli floret and one yellow corn cob, the bright pastel kitchen with soft mint-green cabinets softly blurred behind, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | the three vegetables give small happy wiggles one after another, soft sparkles twinkle. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c02 | 1 | 3–3 | 0:04.7–0:06.9 | 움직임 · 카드 BROCCOLI | Broccoli, bounce like a little tree | close-up of one fresh green broccoli floret that looks like a tiny tree, standing on a small white plate on the round wooden table, the bright pastel kitchen with soft mint-green cabinets softly blurred behind, clear empty space on the right side of the frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | the broccoli floret sways gently like a tiny tree in a soft breeze, tiny sparkles twinkle. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c07 | 1 | 4–4 | 0:06.9–0:09.2 | 재사용 c04 0s~ | Broccoli, bounce like a little tree |  |  | 0 |
| c03 | 1 | 5–5 | 0:09.2–0:11.3 | 움직임 · 카드 CORN | Corn, corn, tap, tap, tap | close-up of one sweet yellow corn cob with green husk leaves on a small white plate on the round wooden table, the bright pastel kitchen with soft mint-green cabinets softly blurred behind, clear empty space on the left side of the frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | the corn cob gives a small happy wiggle, golden sparkles twinkle. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c05 | 1 | 6–6 | 0:11.3–0:13.5 | 움직임 | Wiggle and bounce and clap, clap, clap | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, full body wide shot in a bright cheerful pastel kitchen with soft mint-green cabinets and a small round wooden table, warm morning light, standing on a round soft rug, both arms up in excitement, clear empty pastel wall space in the upper third of the frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | does two small happy hops in place to the beat, arms swing gently, mouth in a closed smile, both long floppy ears stay hanging down beside the cheeks the whole time. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c06 | 1 | 7–7 | 0:13.5–0:15.7 | 움직임 |  | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, and Ducky, a tiny round yellow duckling with an orange beak, no clothes, full body wide shot in a bright cheerful pastel kitchen with soft mint-green cabinets and a small round wooden table, warm morning light, both with arms and wings up in celebration, a bowl of colorful vegetables on the table behind, clear empty pastel wall space in the upper third of the frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | both do small happy hops in place to the beat, Ducky flaps its wings, soft sparkles, Momo's mouth stays in a closed smile, both long floppy ears stay hanging down beside the cheeks the whole time. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c08 | 1 | 8–8 | 0:15.7–0:17.9 | 재사용 c01 0.18s~ · 카드 CARROT | Carrot, carrot, long and bright |  |  | 0 |
| c09 | 2 | 9–9 | 0:17.9–0:20.0 | 재사용 c04 0.36s~ |  |  |  | 0 |
| c10 | 2 | 10–10 | 0:20.0–0:22.2 | 재사용 c01 0s~ · 카드 CARROT | Wiggle to the left, wiggle to the right |  |  | 0 |
| c11 | 2 | 11–11 | 0:22.2–0:24.4 | 재사용 c04 0.18s~ |  |  |  | 0 |
| c12 | 2 | 12–12 | 0:24.4–0:26.7 | 재사용 c02 0.36s~ · 카드 BROCCOLI | Broccoli, broccoli, little green tree |  |  | 0 |
| c13 | 2 | 13–13 | 0:26.7–0:28.9 | 재사용 c02 0s~ · 카드 BROCCOLI | Bounce, bounce, bounce with me |  |  | 0 |
| c14 | 2 | 14–14 | 0:28.9–0:31.0 | 재사용 c01 0.18s~ · 카드 CARROT | Carrot, carrot, wiggle with me |  |  | 0 |
| c15 | 2 | 15–15 | 0:31.0–0:33.1 | 재사용 c04 0.36s~ | Carrot, carrot, wiggle with me |  |  | 0 |
| c16 | 3 | 16–16 | 0:33.1–0:35.3 | 재사용 c02 0s~ · 카드 BROCCOLI | Broccoli, bounce like a little tree |  |  | 0 |
| c17 | 3 | 17–17 | 0:35.3–0:37.5 | 재사용 c04 0.18s~ | Broccoli, bounce like a little tree |  |  | 0 |
| c18 | 3 | 18–18 | 0:37.5–0:39.7 | 재사용 c03 0.36s~ · 카드 CORN | Corn, corn, tap, tap, tap |  |  | 0 |
| c19 | 3 | 19–19 | 0:39.7–0:41.9 | 재사용 c05 0s~ | Wiggle and bounce and clap, clap, clap |  |  | 0 |
| c20 | 3 | 20–20 | 0:41.9–0:44.1 | 재사용 c03 0.18s~ · 카드 CORN | Corn, corn, yellow and sweet |  |  | 0 |
| c21 | 3 | 21–21 | 0:44.1–0:46.2 | 재사용 c05 0.36s~ | Tap, tap, tap your little feet |  |  | 0 |
| c22 | 3 | 22–22 | 0:46.2–0:48.4 | 재사용 c06 0s~ | Wiggle your shoulders, wave hello |  |  | 0 |
| c23 | 4 | 23–23 | 0:48.4–0:50.6 | 재사용 c05 0.18s~ | Clap your hands and here we go |  |  | 0 |
| c24 | 4 | 24–24 | 0:50.6–0:52.8 | 재사용 c06 0.36s~ | Clap your hands and here we go |  |  | 0 |
| c25 | 4 | 25–25 | 0:52.8–0:55.0 | 재사용 c01 0s~ · 카드 CARROT | Carrot, carrot, wiggle with me |  |  | 0 |
| c26 | 4 | 26–26 | 0:55.0–0:57.2 | 재사용 c04 0.18s~ | Carrot, carrot, wiggle with me |  |  | 0 |
| c27 | 4 | 27–27 | 0:57.2–0:59.3 | 재사용 c02 0.36s~ · 카드 BROCCOLI | Broccoli, bounce like a little tree |  |  | 0 |
| c28 | 4 | 28–28 | 0:59.3–1:01.5 | 재사용 c04 0s~ | Broccoli, bounce like a little tree |  |  | 0 |
| c29 | 4 | 29–29 | 1:01.5–1:03.7 | 재사용 c03 0.18s~ · 카드 CORN | Corn, corn, tap, tap, tap |  |  | 0 |
| c30 | 4 | 30–30 | 1:03.7–1:06.0 | 재사용 c05 0.36s~ | Wiggle and bounce and clap, clap, clap |  |  | 0 |
| c31 | 5 | 31–31 | 1:06.0–1:08.1 | 재사용 c04 0s~ | Carrot, broccoli, corn, hooray |  |  | 0 |
| c32 | 5 | 32–32 | 1:08.1–1:10.3 | 재사용 c05 0.18s~ | Thank you for a happy day |  |  | 0 |
| c33 | 5 | 33–33 | 1:10.3–1:12.4 | 재사용 c04 0.36s~ | Carrot, broccoli, corn, goodbye |  |  | 0 |
| c34 | 5 | 34–34 | 1:12.4–1:16.2 | 재사용 c05 0s~ | Wave your hands up to the sky |  |  | 0 |
| c35 | 5 | 35–35 | 1:16.2–1:19.9 | 재사용 c06 0.18s~ |  |  |  | 0 |
