# ep25 기획표 — 당근 브로콜리 옥수수 (Carrot, Broccoli and Corn)

> validate_manifest.py --table 이 생성 (2026-11-26 23:23 UTC). 직접 고치지 말고 manifest.json 을 고친 뒤 다시 실행.

- 제목 EN: (미정)
- 제목 KO: 아삭아삭 채소 친구 🥕🌽 | 따라 부르는 채소 동요 | 모모타임
- 썸네일: c04 + 문구 "" / "당근 · 브로콜리 · 옥수수" (위치 bottom)
- 컷 33개 (목표 22~28) · V 33 (12~15) · S 0 (6~8) · L 0 (3~4) · 씬 5 (목표 5) — 씬별 7/7/7/7/5
- 예상 길이: KO 1:21 (80.8초, 실제 음성) — 목표 2~3분, build.py 가 실제 음성으로 다시 계산
- 생성할 것: 이미지 6장 (V 6 + S 0), V 클립 6개 (+ 재사용 27컷), 음성 블록 KO 0 (L 컷은 라이브러리)
- V 15개 초과 사유: Current short-song policy: reuse six approved non-lipsync sources, recut to the new song. No fixed spoken intro/outro.

## 검증

- △ 총 컷 33개 — 목표 22~28
- △ V 컷 33개 — 목표 12~15 (V 가 15개를 넘으면 manifest.notes.v_over_reason 에 이유를 적고 승인받을 것)
- △ S 컷 0개 — 목표 6~8
- △ L 컷 0개 — 목표 3~4
- △ c01: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c02: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c03: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c04: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c07: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
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
- △ c19: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c20: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c22: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c23: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c24: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c25: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c27: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c27: ko 키워드는 1개 단어만 ('당근 · 브로콜리 · 옥수수') — 문장 자막 금지
- △ c30: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c30: ko 키워드는 1개 단어만 ('당근 · 브로콜리 · 옥수수') — 문장 자막 금지
- △ c01: 첫 컷의 cut_at 은 쓰이지 않는다 (0 에서 시작)
- △ 첫 컷은 L intro_wave(고정 인사) 권장
- △ 마지막 컷은 L outro_bye(고정 작별) 권장
- △ ko 키워드 '당근' 나레이션 반복 0회 (최소 3)
- △ ko 키워드 '당근 · 브로콜리 · 옥수수' 나레이션 반복 0회 (최소 3)
- △ ko 키워드 '브로콜리' 나레이션 반복 0회 (최소 3)
- △ ko 키워드 '옥수수' 나레이션 반복 0회 (최소 3)
- △ 썸네일 문구(ko) 3단어 이하 권장: '당근 · 브로콜리 · 옥수수'

## 컷 표 — 노래 119.00 BPM, 컷은 마디 첫 박에서 바뀜

| 컷 | 씬 | 마디 | 시각 | 종류 | 부르는 가사 | 이미지 프롬프트 (조립된 전체) | 모션 지시 | 새로 만들 것 |
|---|---|---|---|---|---|---|---|---|
| c01 | 1 | 1–1 | 0:00.0–0:02.5 | 움직임 · 카드 CARROT | 당근 당근 아삭아삭 | close-up of one bright orange carrot with fresh green leaves on a small white plate on the round wooden table, the bright pastel kitchen with soft mint-green cabinets softly blurred behind, clear empty space on the left side of the frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | the carrot gives a small happy wiggle, tiny sparkles twinkle around it. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c02 | 1 | 2–2 | 0:02.5–0:04.5 | 움직임 · 카드 BROCCOLI | 브로콜리 쏙쏙쏙 | close-up of one fresh green broccoli floret that looks like a tiny tree, standing on a small white plate on the round wooden table, the bright pastel kitchen with soft mint-green cabinets softly blurred behind, clear empty space on the right side of the frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | the broccoli floret sways gently like a tiny tree in a soft breeze, tiny sparkles twinkle. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c03 | 1 | 3–3 | 0:04.5–0:06.3 | 움직임 · 카드 CORN | 옥수수 톡톡 톡톡 | close-up of one sweet yellow corn cob with green husk leaves on a small white plate on the round wooden table, the bright pastel kitchen with soft mint-green cabinets softly blurred behind, clear empty space on the left side of the frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | the corn cob gives a small happy wiggle, golden sparkles twinkle. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c04 | 1 | 4–4 | 0:06.3–0:08.5 | 움직임 | 채소 친구 냠냠냠 | close-up of one small white plate on the round wooden table holding exactly three vegetables side by side: one orange carrot, one green broccoli floret and one yellow corn cob, the bright pastel kitchen with soft mint-green cabinets softly blurred behind, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | the three vegetables give small happy wiggles one after another, soft sparkles twinkle. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c07 | 1 | 5–5 | 0:08.5–0:11.0 | 재사용 c01 0.18s~ · 카드 CARROT | 당근 당근 반가워 |  |  | 0 |
| c08 | 1 | 6–6 | 0:11.0–0:13.7 | 재사용 c01 0.36s~ · 카드 CARROT | 길쭉 당근 흔들흔들 |  |  | 0 |
| c09 | 1 | 7–7 | 0:13.7–0:16.5 | 재사용 c04 0s~ | 길쭉 당근 흔들흔들 |  |  | 0 |
| c10 | 2 | 8–8 | 0:16.5–0:20.0 | 재사용 c02 0.18s~ · 카드 BROCCOLI | 브로콜리 반가워 |  |  | 0 |
| c11 | 2 | 9–9 | 0:20.0–0:22.3 | 재사용 c02 0.36s~ · 카드 BROCCOLI | 작은 나무 흔들흔들 |  |  | 0 |
| c12 | 2 | 10–10 | 0:22.3–0:24.6 | 재사용 c04 0s~ |  |  |  | 0 |
| c13 | 2 | 11–11 | 0:24.6–0:26.7 | 재사용 c01 0.18s~ · 카드 CARROT | 당근 당근 아삭아삭 |  |  | 0 |
| c14 | 2 | 12–12 | 0:26.7–0:28.2 | 재사용 c02 0.36s~ · 카드 BROCCOLI | 브로콜리 쏙쏙쏙 |  |  | 0 |
| c15 | 2 | 13–13 | 0:28.2–0:30.5 | 재사용 c03 0s~ · 카드 CORN | 옥수수 톡톡 톡톡 |  |  | 0 |
| c16 | 2 | 14–14 | 0:30.5–0:32.6 | 재사용 c04 0.18s~ | 채소 친구 냠냠냠 |  |  | 0 |
| c17 | 3 | 15–15 | 0:32.6–0:34.6 | 재사용 c03 0.36s~ · 카드 CORN | 옥수수야 반가워 |  |  | 0 |
| c18 | 3 | 16–16 | 0:34.6–0:36.6 | 재사용 c04 0s~ |  |  |  | 0 |
| c19 | 3 | 17–17 | 0:36.6–0:38.7 | 재사용 c03 0.18s~ · 카드 CORN | 노란 알이 톡톡톡 |  |  | 0 |
| c20 | 3 | 18–18 | 0:38.7–0:40.8 | 재사용 c04 0.36s~ |  |  |  | 0 |
| c06 | 3 | 19–19 | 0:40.8–0:43.8 | 움직임 | 두 손 모아 짝짝짝 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, and Ducky, a tiny round yellow duckling with an orange beak, no clothes, full body wide shot in a bright cheerful pastel kitchen with soft mint-green cabinets and a small round wooden table, warm morning light, both with arms and wings up in celebration, a bowl of colorful vegetables on the table behind, clear empty pastel wall space in the upper third of the frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | both do small happy hops in place to the beat, Ducky flaps its wings, soft sparkles, Momo's mouth stays in a closed smile, both long floppy ears stay hanging down beside the cheeks the whole time. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c05 | 3 | 20–20 | 0:43.8–0:46.3 | 움직임 | 모모랑 춤을 춰요 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, full body wide shot in a bright cheerful pastel kitchen with soft mint-green cabinets and a small round wooden table, warm morning light, standing on a round soft rug, both arms up in excitement, clear empty pastel wall space in the upper third of the frame, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | does two small happy hops in place to the beat, arms swing gently, mouth in a closed smile, both long floppy ears stay hanging down beside the cheeks the whole time. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + seedance_2_0_mini 4초 (4) |
| c21 | 3 | 21–21 | 0:46.3–0:48.8 | 재사용 c06 0.36s~ | 모모랑 춤을 춰요 |  |  | 0 |
| c22 | 4 | 22–22 | 0:48.8–0:50.9 | 재사용 c01 0s~ · 카드 CARROT | 당근 당근 아삭아삭 |  |  | 0 |
| c23 | 4 | 23–23 | 0:50.9–0:52.4 | 재사용 c02 0.18s~ · 카드 BROCCOLI | 브로콜리 쏙쏙쏙 |  |  | 0 |
| c24 | 4 | 24–24 | 0:52.4–0:54.6 | 재사용 c03 0.36s~ · 카드 CORN | 옥수수 톡톡 톡톡 |  |  | 0 |
| c25 | 4 | 25–25 | 0:54.6–0:57.5 | 재사용 c04 0s~ | 채소 친구 냠냠냠 |  |  | 0 |
| c26 | 4 | 26–26 | 0:57.5–1:00.4 | 재사용 c05 0.18s~ |  |  |  | 0 |
| c27 | 4 | 27–27 | 1:00.4–1:02.6 | 재사용 c04 0.36s~ | 당근 브로콜리 옥수수 |  |  | 0 |
| c28 | 4 | 28–28 | 1:02.6–1:04.9 | 재사용 c05 0s~ | 당근 브로콜리 옥수수 |  |  | 0 |
| c29 | 5 | 29–29 | 1:04.9–1:07.7 | 재사용 c05 0.18s~ | 다 같이 흔들흔들 |  |  | 0 |
| c30 | 5 | 30–30 | 1:07.7–1:11.5 | 재사용 c04 0.179s~ | 당근 브로콜리 옥수수 |  |  | 0 |
| c31 | 5 | 31–31 | 1:11.5–1:14.6 | 재사용 c05 0s~ | 내일 또 만나 안녕 |  |  | 0 |
| c32 | 5 | 32–32 | 1:14.6–1:17.7 | 재사용 c06 0.18s~ | 내일 또 만나 안녕 |  |  | 0 |
| c33 | 5 | 33–33 | 1:17.7–1:20.8 | 재사용 c06 0.36s~ |  |  |  | 0 |
