# ep23 기획표 — 나비와 꽃 (Butterfly and Flower)

> validate_manifest.py --table 이 생성 (2026-11-23 00:56 UTC). 직접 고치지 말고 manifest.json 을 고친 뒤 다시 실행.

- 제목 EN: (미정)
- 제목 KO: 팔랑 나비, 활짝 꽃 🦋🌸 | 따라 부르는 동요 | 모모타임
- 썸네일: c01 + 문구 "" / "나비와 꽃" (위치 bottom)
- 컷 28개 (목표 22~28) · V 28 (12~15) · S 0 (6~8) · L 0 (3~4) · 씬 5 (목표 5) — 씬별 5/4/4/7/8
- 예상 길이: KO 1:39 (99.2초, 실제 음성) — 목표 2~3분, build.py 가 실제 음성으로 다시 계산
- 생성할 것: 이미지 10장 (V 10 + S 0), V 클립 10개 (+ 재사용 18컷), 음성 블록 KO 0 (L 컷은 라이브러리)
- V 15개 초과 사유: Agent plan under standing authorization: ten unique five-second sources, recut and reused to song phrases. No lip sync or freeze extension. Pair-wide cap 150; ep23 owns all shared generation spend.

## 검증

- △ V 컷 28개 — 목표 12~15 (V 가 15개를 넘으면 manifest.notes.v_over_reason 에 이유를 적고 승인받을 것)
- △ S 컷 0개 — 목표 6~8
- △ L 컷 0개 — 목표 3~4
- △ c01: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c01: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c03: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c03: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c05: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c05: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c08: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c08: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c10: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c10: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c02: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c02: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c02: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c07: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c07: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c11: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c11: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c12: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c12: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c13: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c13: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c14: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c14: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c15: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c15: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c04: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c04: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c04: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c16: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c16: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c06: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c06: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c17: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c17: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c18: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c18: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c19: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c19: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c19: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c20: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c20: 캐릭터 블록 생략 컷 (momo:false) — 모모가 안 나오는 컷이 맞는지 확인
- △ c20: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c21: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c21: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c22: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c22: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c23: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c23: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c24: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c24: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c25: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c25: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c26: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c26: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c09: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c09: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c27: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c27: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ c28: 이미지 프롬프트에 글자 유발 단어 ['text', 'caption'] — 텍스트는 조립에서 얹는다
- △ c28: 모션 지시에 위험 단어 ['camera', 'fast'] — 작게, 카메라 고정
- △ 첫 컷은 L intro_wave(고정 인사) 권장
- △ 마지막 컷은 L outro_bye(고정 작별) 권장
- △ ko 키워드 '꽃' 나레이션 반복 0회 (최소 3)
- △ ko 키워드 '나비' 나레이션 반복 0회 (최소 3)

## 컷 표 — 노래 113.03 BPM, 컷은 마디 첫 박에서 바뀜

| 컷 | 씬 | 마디 | 시각 | 종류 | 부르는 가사 | 이미지 프롬프트 (조립된 전체) | 모션 지시 | 새로 만들 것 |
|---|---|---|---|---|---|---|---|---|
| c01 | 1 | 1–1 | 0:00.0–0:05.0 | 움직임 | 팔랑팔랑 나비, 이리 와 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, Momo stands at the left of a cream garden path, watching one friendly golden-yellow butterfly hover at paw height on the right. The butterfly has two symmetrical rounded pairs of wings with small coral tips and a tiny brown body. No flowers in this shot. Bright clean pastel storybook garden, soft sky blue background, rolling mint hills, soft diffuse daylight, single continuous full-bleed 16:9 scene. Keep subjects above the bottom 22 percent, which is clear low-detail grass for a caption. No text, symbols, borders, watermark, extra animals or extra learning objects, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo takes two gentle bouncing steps toward the butterfly and lifts one paw to greet it. Butterfly traces a small smooth arc. Ears bounce naturally, mouth stays in a closed smile. Smooth preschool 3D animation, preserve anatomy and colors. No lip sync, speech, subtitles, fast camera motion or sudden cuts. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + kling3_0_turbo 5초 (7.5) |
| c03 | 1 | 2–2 | 0:05.0–0:09.2 | 움직임 | 예쁜 꽃이 활짝 반겨요 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, Momo stands beside one large simple coral-pink daisy with a warm yellow center, a sturdy green stem and exactly two green leaves growing from a small soil patch. The flower is at Momo waist height. No butterfly. Bright clean pastel storybook garden, soft sky blue background, rolling mint hills, soft diffuse daylight, single continuous full-bleed 16:9 scene. Keep subjects above the bottom 22 percent, which is clear low-detail grass for a caption. No text, symbols, borders, watermark, extra animals or extra learning objects, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo steps sideways twice to the beat and warmly presents the flower with an open paw. The flower gently sways in the breeze; feet lift and land naturally. Smooth preschool 3D animation, preserve anatomy and colors. No lip sync, speech, subtitles, fast camera motion or sudden cuts. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + kling3_0_turbo 5초 (7.5) |
| c05 | 1 | 3–3 | 0:09.2–0:13.4 | 움직임 | 팔랑팔랑 나비, 빙글빙글 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, Full-body Momo on the cream garden path, paws spread low like wings, one golden-yellow coral-tipped butterfly floating to the right. Clear space around all limbs and ears. No flowers. Bright clean pastel storybook garden, soft sky blue background, rolling mint hills, soft diffuse daylight, single continuous full-bleed 16:9 scene. Keep subjects above the bottom 22 percent, which is clear low-detail grass for a caption. No text, symbols, borders, watermark, extra animals or extra learning objects, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo performs a clear child-friendly wing dance: two side steps while both paws lift and lower together, a tiny soft hop, then settles. The butterfly flutters nearby. No talking or singing. Smooth preschool 3D animation, preserve anatomy and colors. No lip sync, speech, subtitles, fast camera motion or sudden cuts. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + kling3_0_turbo 5초 (7.5) |
| c08 | 1 | 4–4 | 0:13.4–0:15.5 | 움직임 | 꽃 옆에서 같이 춤춰요 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, Full-body Momo beside the single coral-pink daisy, arms relaxed, generous empty space around the character and flower. No butterfly. Bright clean pastel storybook garden, soft sky blue background, rolling mint hills, soft diffuse daylight, single continuous full-bleed 16:9 scene. Keep subjects above the bottom 22 percent, which is clear low-detail grass for a caption. No text, symbols, borders, watermark, extra animals or extra learning objects, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo dances a clear two-step side to side and makes one little quarter turn back toward the flower, ears and overalls following the body naturally. Flower sways to the beat. Smooth preschool 3D animation, preserve anatomy and colors. No lip sync, speech, subtitles, fast camera motion or sudden cuts. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + kling3_0_turbo 5초 (7.5) |
| c10 | 1 | 5–5 | 0:15.5–0:17.6 | 움직임 |  | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, Momo next to one coral-pink daisy, facing the viewer in a friendly full-body pose, both feet and long floppy ears visible. No butterfly. Bright clean pastel storybook garden, soft sky blue background, rolling mint hills, soft diffuse daylight, single continuous full-bleed 16:9 scene. Keep subjects above the bottom 22 percent, which is clear low-detail grass for a caption. No text, symbols, borders, watermark, extra animals or extra learning objects, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo makes two small cheerful bounces on both feet then waves to the viewer, while the daisy sways softly. Natural ear follow-through, no lip movement. Smooth preschool 3D animation, preserve anatomy and colors. No lip sync, speech, subtitles, fast camera motion or sudden cuts. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + kling3_0_turbo 5초 (7.5) |
| c02 | 2 | 6–6 | 0:17.6–0:21.9 | 움직임 | 작은 나비 날개 펴고 | One single golden-yellow butterfly with coral-tipped rounded wings hovers over a soft mint-green meadow. Its whole wings and small body are clearly visible, no flower or character. Bright clean pastel storybook garden, soft sky blue background, rolling mint hills, soft diffuse daylight, single continuous full-bleed 16:9 scene. Keep subjects above the bottom 22 percent, which is clear low-detail grass for a caption. No text, symbols, borders, watermark, extra animals or extra learning objects, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | The butterfly flutters its symmetrical wings and floats in one graceful shallow figure-eight, remaining centered and entirely visible. Smooth preschool 3D animation, preserve anatomy and colors. No lip sync, speech, subtitles, fast camera motion or sudden cuts. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + kling3_0_turbo 5초 (7.5) |
| c07 | 2 | 7–7 | 0:21.9–0:26.2 | 움직임 | 살랑살랑 날아와요 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, Momo full-body in three-quarter view at the left, on a broad cream garden path, one golden-yellow butterfly ahead on the right at eye height. No flowers. Bright clean pastel storybook garden, soft sky blue background, rolling mint hills, soft diffuse daylight, single continuous full-bleed 16:9 scene. Keep subjects above the bottom 22 percent, which is clear low-detail grass for a caption. No text, symbols, borders, watermark, extra animals or extra learning objects, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo walks three small springy steps following the butterfly along the path, with natural alternating feet and arm swing. Butterfly drifts ahead. Gentle slow lateral camera follow, both remain fully visible. Smooth preschool 3D animation, preserve anatomy and colors. No lip sync, speech, subtitles, fast camera motion or sudden cuts. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + kling3_0_turbo 5초 (7.5) |
| c11 | 2 | 8–8 | 0:26.2–0:30.5 | 재사용 c05 0s~ | 우리 팔도 활짝 펴고 |  |  | 0 |
| c12 | 2 | 9–9 | 0:30.5–0:34.6 | 재사용 c01 0s~ | 나비처럼 움직여요 |  |  | 0 |
| c13 | 3 | 10–10 | 0:34.6–0:39.0 | 재사용 c07 0s~ | 팔랑팔랑 나비, 이리 와 |  |  | 0 |
| c14 | 3 | 11–11 | 0:39.0–0:43.2 | 재사용 c03 0s~ | 예쁜 꽃이 활짝 반겨요 |  |  | 0 |
| c15 | 3 | 12–12 | 0:43.2–0:47.5 | 재사용 c05 0s~ | 팔랑팔랑 나비, 빙글빙글 |  |  | 0 |
| c04 | 3 | 13–13 | 0:47.5–0:51.6 | 움직임 | 꽃 옆에서 같이 춤춰요 | Close view of one large coral-pink daisy with a round warm yellow center, simple thick petals, a green stem and two leaves. Plain mint meadow and soft sky behind it. No characters or insects. Bright clean pastel storybook garden, soft sky blue background, rolling mint hills, soft diffuse daylight, single continuous full-bleed 16:9 scene. Keep subjects above the bottom 22 percent, which is clear low-detail grass for a caption. No text, symbols, borders, watermark, extra animals or extra learning objects, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | The flower makes a smooth gentle left-right sway with a subtle bob, keeping its petals and stem shape consistent. Smooth preschool 3D animation, preserve anatomy and colors. No lip sync, speech, subtitles, fast camera motion or sudden cuts. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + kling3_0_turbo 5초 (7.5) |
| c16 | 4 | 14–14 | 0:51.6–0:55.9 | 재사용 c03 0s~ | 분홍 꽃이 고개 끄덕 |  |  | 0 |
| c06 | 4 | 15–15 | 0:55.9–1:00.1 | 움직임 | 향기 맡고 웃어 봐요 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, Momo crouches comfortably to the left of the single coral-pink daisy, both eyes visible in three-quarter view. Two yellow overall buttons visible, nose near but not touching the flower. No butterfly. Bright clean pastel storybook garden, soft sky blue background, rolling mint hills, soft diffuse daylight, single continuous full-bleed 16:9 scene. Keep subjects above the bottom 22 percent, which is clear low-detail grass for a caption. No text, symbols, borders, watermark, extra animals or extra learning objects, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | Momo gently leans forward to smell the flower, then straightens with a happy closed smile and a small delighted body bounce. The flower nods softly. Smooth preschool 3D animation, preserve anatomy and colors. No lip sync, speech, subtitles, fast camera motion or sudden cuts. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + kling3_0_turbo 5초 (7.5) |
| c17 | 4 | 16–16 | 1:00.1–1:02.3 | 재사용 c08 0s~ | 두 발 살짝 옆으로 쿵 |  |  | 0 |
| c18 | 4 | 17–17 | 1:02.3–1:04.4 | 재사용 c10 0s~ | 두 발 살짝 옆으로 쿵 |  |  | 0 |
| c19 | 4 | 18–18 | 1:04.4–1:08.7 | 재사용 c04 0s~ | 꽃 옆에서 흔들어요 |  |  | 0 |
| c20 | 4 | 19–19 | 1:08.7–1:10.8 | 재사용 c02 0s~ | 나비 따라 팔랑팔랑 |  |  | 0 |
| c21 | 4 | 20–20 | 1:10.8–1:13.1 | 재사용 c08 0s~ | 꽃을 보고 활짝활짝 |  |  | 0 |
| c22 | 5 | 21–21 | 1:13.1–1:17.2 | 재사용 c05 0s~ | 팔랑팔랑 나비, 이리 와 |  |  | 0 |
| c23 | 5 | 22–22 | 1:17.2–1:21.4 | 재사용 c03 0s~ | 예쁜 꽃이 활짝 반겨요 |  |  | 0 |
| c24 | 5 | 23–23 | 1:21.4–1:25.6 | 재사용 c07 0s~ | 팔랑팔랑 나비, 빙글빙글 |  |  | 0 |
| c25 | 5 | 24–24 | 1:25.6–1:27.8 | 재사용 c08 0s~ | 꽃 옆에서 같이 춤춰요 |  |  | 0 |
| c26 | 5 | 25–25 | 1:27.8–1:29.9 | 재사용 c10 0s~ | 꽃 옆에서 같이 춤춰요 |  |  | 0 |
| c09 | 5 | 26–26 | 1:29.9–1:32.0 | 움직임 | 나비 안녕, 꽃도 안녕 | Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears, huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with two small yellow buttons on the shoulder straps, big expressive smile, both long floppy ears always hang down beside the cheeks, the ears never stand upright, Momo stands on the cream garden path with one paw raised at shoulder height, one golden-yellow butterfly hovering above the other low open paw. No flowers. Bright clean pastel storybook garden, soft sky blue background, rolling mint hills, soft diffuse daylight, single continuous full-bleed 16:9 scene. Keep subjects above the bottom 22 percent, which is clear low-detail grass for a caption. No text, symbols, borders, watermark, extra animals or extra learning objects, bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background, one focal object per shot, eye-level or slightly low camera, soft even lighting, full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers, no logos, no watermarks | The butterfly rises in a gentle arc while Momo follows it with the eyes and waves one paw twice, then takes one soft happy step. Keep mouth closed and both buttons visible. Smooth preschool 3D animation, preserve anatomy and colors. No lip sync, speech, subtitles, fast camera motion or sudden cuts. Keep the character design exactly the same. Static fixed camera, no camera movement, no zoom, no morphing, gentle small motion only. | 이미지 + kling3_0_turbo 5초 (7.5) |
| c27 | 5 | 27–27 | 1:32.0–1:34.2 | 재사용 c10 0s~ | 나비 안녕, 꽃도 안녕 / 다음에 또 같이 놀자 |  |  | 0 |
| c28 | 5 | 28–28 | 1:34.2–1:39.2 | 재사용 c03 0s~ | 다음에 또 같이 놀자 |  |  | 0 |
