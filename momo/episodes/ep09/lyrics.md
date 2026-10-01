# ep09 "Vehicles" (탈것 소리) — lyrics v1.1 (2026-10-01, reviewed)

User direction (ep04, kept for every song): English lyrics on a Korean children's-song (동요) rhythm, for Korean
families whose toddlers (2–4) learn English. Topic: vehicles and their sounds, in the call-and-response format of
ep06 "Animal Sounds" (the best-received one). Momo asks "What does the car say?" and everyone answers "Beep, beep!
Beep, beep!", then the choir greets it "(Hello, car!)". The six vehicles are car (beep), bus (honk), train (choo),
fire truck (wee-woo), boat (toot) and airplane (zoom). The vehicles are simple toy-like shapes with **no faces**.
Momo waves at them, and Ducky rides along on the train in verse 2. This is a draft for the user's approval. The user
makes the song in Suno Pro (settings at the end), and the cut table is laid on that take's bar grid (PRODUCTION.md (9)).

Original lyrics. There are no brand or show names and no borrowed song lines. Nothing comes from "The Wheels on
the Bus": the bus says "honk", no line uses "round and round" or "all through the town", and the answers are
two-plus-two ("Beep, beep! Beep, beep!") rather than the "beep, beep, beep" triple. "Zoom, zoom" is used only as
the airplane's sound. "What does the X say?" is the plain picture-book question ep06 already used.

v1.1 review changes: "Wee-oo" → "Wee-woo" (the usual English toddler word; Suno could sing "wee-oh"). The final
chorus tag asks for the same tempo, because ep05's final chorus slowed down and that would break the lip-sync reuse.
`[End]` comes after the 2-bar outro, because ep06's take added a 31 s instrumental tail. The style now phrases the
vehicle sounds positively, and the exclude list blocks real sirens, horns and engine sounds. V2b is one 8 s shot, so
it never freezes. The CC take comes from the chorus with the longest window. In CC Momo is named last. V3c no longer
looks up while singing, and CB points without turning sideways.

Plan at ~124 BPM (one 4/4 bar ≈ 1.94 s). The credit cap is 150 from ep08, so the target is **1:45–2:00**, not
ep06's 2:15. Calibration: ep06's Suno v1 take used the same format with 192 words. It sang each 6-line chorus in
≈ 11 s (6 bars), each 4-line verse in ≈ 10–12 s and the 4-line bridge in ≈ 15 s, and it finished singing at 1:41.
ep09 has 198 words, so with a real 4-bar intro it lands at ≈ 1:50. The Suno take decides the real grid.

| Section | Bars | ≈ Time | Notes |
|---|---|---|---|
| Instrumental intro | 4 | 0:00–0:07.7 | no vocals; library greeting "Hi friends! It's Momo!" (L `intro_wave`) |
| Chorus 1 | 6 | –0:19.4 | six 1-bar lines → three 2-line shots (CA · CB · CC) |
| Verse 1 (car, bus) | 6 | –0:31.0 | question · answer · question · answer, one picture per line |
| Chorus 2 | 6 | –0:42.6 | reuse of CA · CB · CC (`clip_from`, placed by vocal cross-correlation) |
| Verse 2 (train + Ducky, fire truck) | 8 | –0:58.1 | 5 lines; Ducky rides in the train's open wagon |
| Chorus 3 | 6 | –1:09.7 | reuse |
| Verse 3 (boat, airplane) | 6 | –1:21.3 | |
| Bridge (review) | 8 | –1:36.8 | "Car says beep!", the name and the sound together; all reuse |
| Chorus 4 (final) | 6–8 | –1:52.3 | same tempo as the others; ep05's "final" chorus slowed to one line per 2 bars, and then the lip-sync takes cannot be reused |
| Outro | 2 | –1:56.1 | instrumental, final chord, `[End]`; library "Bye-bye, friends! See you next time!" (L `outro_bye`) |

Total ≈ 58–60 bars ≈ 1:52–1:56. Singing runs from the end of the intro to the outro, with **no instrumental break**.
ep05's Suno take filled verse 2, verse 3 and the bridge with a 41 s (22-bar) break, so every tag below asks for vocals
and the style says so too. ep06's take stopped singing at 100.8 s and then played a 31 s (16-bar) instrumental tail,
so the lyrics end with `[End]` after the 2-bar outro and the style asks for a short ending. If a tail still comes,
the video ends 2 bars after the last chord (`track.end`, as in ep06).

## Shots

Each cut starts on its sung line (`cut_at` ≈ first word − 0.1 s).
- **LS** = wan2_7 lip-sync. Momo is frontal with both feet on the ground, her paws at chest height below the
  cheeks, and both long ears fully visible and hanging down. Her eyes are open and on the viewer the whole time, never
  closed while singing. She sings with one small gesture: clap, sway, nod, wave (paw at shoulder height below the
  ear), point, trace a shape, or a gentle bounce on bent knees. The motion prompt opens with the identity sentence.
  Momo is the **last** subject named in it ("…; Momo sings and claps"). In the ep06 review, a character named after
  Momo could take the singing.
- **MO** = seedance_2_0_mini. One simple toy-like vehicle with **no face** (no eyes, no mouth) and no letters,
  numbers, logos, signs or plates. It has plain windows and nobody at the wheel. It sits on the left or right half
  of the frame, which leaves room for the word card. The vehicle **stays in place**: it never drives across the
  frame, because wheels and bodies warp. The motion goes to lights that blink, puffs of steam, water ripples,
  clouds drifting behind, or sparkles. Clip length = ceil(window); seedance takes 4–15 s.
- **RE** = reuse (`clip_from`, 0 credits).

Sets (named in every prompt so the backgrounds match). No text, signs, letters or numbers anywhere in any set:
- *Toy town road*: a smooth light-gray road with soft green grass verges, small round trees and pastel houses
  softly blurred behind, bright blue sky.
- *Train hill*: a green grassy hill with a short toy railway track on wooden sleepers.
- *Lake*: a calm blue lake with a small wooden dock and green hills behind.
- *Sky*: a bright blue sky with soft white clouds.

| Shot | Bars | Sung line(s) | Kind | On screen · action | New |
|---|---|---|---|---|---|
| L1 | 4 | (intro) | L `intro_wave` | library greeting | — |
| CA | 2 | Beep, beep! Honk, honk! / Choo, choo! Wee-woo! | LS | Momo full body, frontal, on the grass beside the toy town road; sings and claps her paws on every sound, both feet on the grass | image + LS 4 s |
| CB | 2 | Toot, toot! Zoom, zoom! / Here they come! (Here they come!) | LS | Momo medium shot, frontal, at the roadside; sways side to side, then on "Here they come" points to her side with one paw at chest height while her face and body stay toward the viewer | image + LS 4 s |
| CC | 2 | Wave hello! (Hello!) / Let's go for a ride! | LS, two characters | Momo and Ducky side by side on the grass by the road, both frontal. The motion prompt puts Ducky first: Ducky hops happily beside her and flaps its wings with its beak closed (Ducky does the big move). Then Momo, named last, sings, waves one paw at shoulder height below the ear, then claps once. Make this take on the chorus whose CC window is longest (usually the final one, where "ride!" can be held before the outro) and reuse it in the other three, so no chorus ends on a frozen frame | image + LS 4–5 s |
| V1a | 1 | What does the car say? | LS | Momo medium shot, frontal, at the roadside; points to her side with one paw at chest height, small curious head tilt | image + LS 3 s |
| V1b | 1–2 | Beep, beep! Beep, beep! (Hello, car!) | MO · card CAR | one small round shiny red toy car with big round black wheels and round headlights, no face, parked on the left half of the road; the car stays still, its headlights blink twice, sparkles twinkle | image + MO 4 s |
| V1c | 1 | What does the bus say? | LS | Momo frontal beside a small plain wooden bench at the roadside (no sign or post); waves one paw at shoulder height below the ear (waving to the bus) | image + LS 3 s |
| V1d | 2 | Honk, honk! Honk, honk! (Hello, bus!) | MO · card BUS | one chubby round yellow bus with big plain windows and plain sides, no sign, no face, stopped on the right half of the road; the bus stays still, its round lights blink, a leaf drifts past, sparkles | image + MO 5 s |
| — | 6 | Chorus 2 | RE | CA · CB · CC | 0 |
| V2a | 1 | What does the train say? | LS | Momo frontal on the train hill beside the toy track; points to her side with one paw at chest height, gentle nod | image + LS 3 s |
| V2b | 4 | Choo, choo! Choo, choo! (Hello, train!) / Who is on the train? (Ducky! Quack, quack!) | MO · card TRAIN | a little red toy steam engine with a round black chimney, no face, pulling one open blue wagon on the short track, on the left half of the frame; **Ducky sits in the open wagon**, facing the viewer, with its head and tiny wings above the side. The train stays in place and white puffs of steam rise from the chimney the whole time. For the first half Ducky only sways gently; in the second half it bobs and flaps its tiny wings happily (the big move is Ducky's; seedance cannot hit the word "Ducky!", so the second half is enough). One continuous shot over both lines with `clip_seconds` = ceil(window) ≈ 8 s, so it never freezes. Do not split it, because a 16th image would break the budget | image + MO ≈ 8 s |
| V2c | 1 | What does the fire truck say? | LS | Momo frontal at the roadside; claps once, then points to her side with one paw at chest height, both feet on the grass | image + LS 3 s |
| V2d | 2 | Wee-woo! Wee-woo! (Hello, fire truck!) | MO · card FIRE TRUCK | one chubby round red fire truck with a short white ladder on top and one round light on the roof, no face, no letters, parked on the right half of the road; the truck stays still, the roof light glows and blinks, sparkles | image + MO 5 s |
| — | 6 | Chorus 3 | RE | CA · CB · CC | 0 |
| V3a | 1 | What does the boat say? | LS | Momo frontal on the grass at the lake's edge by the small wooden dock; waves one paw at shoulder height below the ear | image + LS 3 s |
| V3b | 1–2 | Toot, toot! Toot, toot! (Hello, boat!) | MO · card BOAT | one small round red-and-white toy boat with a little yellow chimney, no face, on the calm blue lake, left half of the frame; the boat stays in place and bobs gently on small ripples, a small white puff from the chimney, sparkles on the water | image + MO 4 s |
| V3c | 1 | What does the airplane say? | LS | Momo frontal on the grassy hill under the blue sky; eyes on the viewer, she traces a small swooping curve in front of her chest with one paw, like a little airplane flying. The paw stays at chest height, away from the ears, and she does not look up while singing | image + LS 3 s |
| V3d | 2 | Zoom, zoom! Zoom, zoom! (Hello, airplane!) | MO · card AIRPLANE | one chubby round white toy airplane with blue wings and a red propeller on the nose, no face, no letters, in the bright blue sky on the right half of the frame; the plane stays in place, its propeller spins, and soft white clouds drift slowly past behind it (this gives the feel of flying) | image + MO 5 s |
| B1 | 1 + 1 | Car says beep! / Bus says honk! | RE · cards CAR, BUS | V1b, then V1d, one bar each | 0 |
| B2 | 1 + 1 | Train says choo! / Fire truck says wee-woo! | RE · cards TRAIN, FIRE TRUCK | V2b from 0 s (steam, Ducky still), then V2d | 0 |
| B3 | 1 + 1 | Boat says toot! / Airplane says zoom! | RE · cards BOAT, AIRPLANE | V3b, then V3d | 0 |
| B4 | 2 | And Ducky says quack, quack! | RE | V2b's second half, where Ducky flaps in the wagon (`clip_from.at` ≈ 4–5 s, picked on the frames) | 0 |
| — | 6–8 | Chorus 4 (final) | RE + CC source | CA · CB reused; CC is the source take when its window here is the longest | 0 |
| L2 | 2 | (outro) | L `outro_bye` | library goodbye | — |

About 33 cuts in all: 2 L, 15 new and 16 RE.

| New | Count | Credits |
|---|---|---|
| Images | **15** (9 Momo: CA, CB, CC and the six questions; 6 vehicles) × 2 | 30 |
| Lip-sync wan2_7 | **≈ 31 s** (CA 4 + CB 4 + CC 4–5 + 6 questions × 3) × 1.5 | ≈ 47 |
| Motion seedance_2_0_mini | 6 vehicle clips: 4 + 5 + 8 + 5 + 4 + 5 ≈ 31 s × 1 | ≈ 31 |
| Reuse (choruses 2–4, bridge) | 16 cuts | 0 |
| **Total** | | **≈ 108** (≈ 135 with a 25 % retry margin; cap 150) |

There is room for regenerations but not for a 16th image. `estimate_credits.py` decides once the cut table is in
the manifest. If a chorus window comes out longer than a take, reuse the take from the chorus with the longest window
instead of making a new image.

Word cards: CAR · BUS · TRAIN · FIRE TRUCK · BOAT · AIRPLANE, on the vehicle answer shots, with the sound as the
small text (e.g. CAR / "beep, beep"). The bridge shows the same cards again as a review. Thumbnail idea: V2b
(Ducky on the train) or CC, with the text "BEEP, BEEP! CHOO, CHOO!".

Lessons applied:
- `[Instrumental intro - 4 bars, no vocals]` comes first, because Suno sang a count-in over a 2-bar intro twice.
- No break or interlude anywhere after the intro (ep05). The tags ask only for singing, and the style says "no
  instrumental break, singing all the way through".
- The final chorus keeps the same tempo (ep05's slowed down), so its lip-sync takes can be reused.
- The outro is 2 bars, then `[End]` (ep06 had a 31 s tail).
- Chorus lines are 1 bar each and pair into ~4 s shots.
- Each verse line has one clear picture, and the vehicles stay in place.
- Momo's gestures are all small, her eyes stay on the viewer, and she is named last in every lip-sync prompt (ep06).
  The big moves go to Ducky, the steam, the water and the clouds.
- Every answer carries real words ("(Hello, bus!)"), so the aligner has anchors. Sung sounds like "Wee-woo" and
  "Toot" are often heard as other words.
- Ducky's ride-along line shares the train shot, so the image budget stays at 15.

## Suno style

```style
Korean children's song style in English, Korean kindergarten sing-along, bright bouncy 2/4 march feel, 124 bpm, steady tempo all the way through, major key, 4-bar instrumental intro with piano and bells and no vocals, children's choir with a bright young female lead, call-and-response: the lead asks and the choir answers with the vehicle sound, piano, bells, glockenspiel, xylophone, woodblock, hand claps, light snare, simple singable melody, short clear phrases, the choir sings each vehicle sound as short words on the beat, very clear English, no instrumental break, singing all the way through, the last chorus keeps the same tempo, short 2-bar instrumental ending on the final chord, full-length song about 1 minute 50 seconds
```

## Lyrics (Suno format)

```
[Instrumental intro - 4 bars, no vocals]

[Chorus - bouncy, everyone sings]
Beep, beep! Honk, honk!
Choo, choo! Wee-woo!
Toot, toot! Zoom, zoom!
Here they come! (Here they come!)
Wave hello! (Hello!)
Let's go for a ride!

[Verse 1 - lead asks, choir answers]
What does the car say?
Beep, beep! Beep, beep! (Hello, car!)
What does the bus say?
Honk, honk! Honk, honk! (Hello, bus!)

[Chorus - bouncy, everyone sings]
Beep, beep! Honk, honk!
Choo, choo! Wee-woo!
Toot, toot! Zoom, zoom!
Here they come! (Here they come!)
Wave hello! (Hello!)
Let's go for a ride!

[Verse 2 - lead asks, choir answers]
What does the train say?
Choo, choo! Choo, choo! (Hello, train!)
Who is on the train? (Ducky! Quack, quack!)
What does the fire truck say?
Wee-woo! Wee-woo! (Hello, fire truck!)

[Chorus - bouncy, everyone sings]
Beep, beep! Honk, honk!
Choo, choo! Wee-woo!
Toot, toot! Zoom, zoom!
Here they come! (Here they come!)
Wave hello! (Hello!)
Let's go for a ride!

[Verse 3 - lead asks, choir answers]
What does the boat say?
Toot, toot! Toot, toot! (Hello, boat!)
What does the airplane say?
Zoom, zoom! Zoom, zoom! (Hello, airplane!)

[Bridge - everyone sings together]
Car says beep! Bus says honk!
Train says choo! Fire truck says wee-woo!
Boat says toot! Airplane says zoom!
And Ducky says quack, quack!

[Chorus - final, same tempo, everyone sings]
Beep, beep! Honk, honk!
Choo, choo! Wee-woo!
Toot, toot! Zoom, zoom!
Here they come! (Here they come!)
Wave hello! (Hello!)
Let's go for a ride!

[Outro - instrumental, 2 bars, final chord]
[End]
```

## Suno 설정 (사용자가 suno.com 에서 직접 입력)

suno.com → Create → **Custom** 모드에서 넣습니다. ep06·ep07 과 같은 설정이고, 바뀌는 것은 제목·스타일·가사·
스타일 제외·길이입니다. 크레딧 캡이 150 으로 내려가서 곡을 2:00 이하로 짧게 잡았습니다.

| 항목 | 값 | 이유 |
|---|---|---|
| **Custom** | 켬 | 가사와 스타일을 직접 넣습니다 |
| **Instrumental** | 끔 | 노래(보컬)가 있어야 합니다 |
| **모델** | 최신 모델 | |
| **제목 (Title)** | `Vehicle Sounds` | |
| **가사 (Lyrics)** | 위 "Lyrics (Suno format)" 블록 전체 (대괄호 태그 포함). 첫 줄 `[Instrumental intro - 4 bars, no vocals]` 부터 마지막 줄 `[End]` 까지 넣습니다 | 전주 4마디에 채널 인사가 들어갑니다. `[End]` 는 곡을 마지막 화음에서 끝내게 합니다 |
| **스타일 (Styles)** | 위 `style` 블록 문구 그대로 | 한국 동요 리듬 + 영어 가사, 124 BPM, 간주 없이 끝까지 같은 빠르기로 노래 |
| **스타일 제외** | 아래 문구 붙여넣기 | 슬프거나 시끄러운 스타일, 카운트인을 막습니다. 실제 사이렌·경적·엔진 효과음, 간주·솔로·브레이크다운, 템포 변화도 막습니다 |
| **보컬 성별** | 여성 | 밝은 여성 리드 + 어린이 합창 |
| **길이** | **1:50** (1:45~2:00). 정확히 고를 수 없으면 자동 | 가사가 124 BPM 에서 약 58~60마디 분량입니다. 같은 형식의 ep06 은 단어 192개를 1:41 에 다 불렀습니다 |
| **Max 모드** | 켬 | 곡 끝까지 목소리와 스타일이 일정해서 립싱크·자막 맞추기에 유리합니다 |
| **기이함** | 낮게 (20~30%) | 동요는 평범하고 또렷하게 |
| **스타일 영향** | Strong 쪽 | 스타일 문구를 제안이 아니라 지시로 따르게 합니다 |
| **다양성** | 가장 낮게 | Suno 가 스타일 문구를 스스로 바꾸지 않게 합니다 |
| **개인화** | 끔 | 계정 취향이 섞이지 않게 합니다 |
| **저장 위치** | "Momo" 작업 공간 | 나중에 찾기 편합니다 |

스타일 제외에 붙여넣을 문구:

```text
sad, dark, rock, metal, rap, heavy bass, autotune, screaming, slow ballad, spoken word, count-in, sound effects, siren, car horn, engine noise, instrumental break, interlude, guitar solo, breakdown, tempo change
```

곡을 고를 때 확인할 것:

- **전주:** 첫 목소리가 약 7~8초(4마디) 뒤에 나오는 곡이 가장 좋습니다. 4초(2마디)보다 빨리 나오면 고르지 마세요.
  그 자리에 인사 "Hi friends! It's Momo!" 가 들어갑니다 (ep06 v1 은 4초로 통과했습니다). 전주에 카운트인이나 말소리가
  없어야 하고, 노래는 "Beep, beep! Honk, honk!" 로 시작해야 합니다.
- **간주 없음:** 전주 뒤로는 노래가 끝까지 이어져야 합니다. 후렴과 절 사이에 연주만 나오는 부분이 1마디(약 2초)보다
  길면 그 곡은 고르지 마세요. ep05 v1 은 41초 간주로 verse 2·3 과 bridge 를 통째로 건너뛰었습니다.
- **여섯 탈것:** car·bus → train·Ducky·fire truck → boat·airplane 순서로 다 부르는지, bridge 네 줄
  ("Car says beep!" … "And Ducky says quack, quack!")도 부르는지 확인합니다.
- **소리말:** "Wee-woo! Wee-woo!" 와 "Toot, toot!" 가 효과음이 아니라 노래로 들려야 합니다. 실제 사이렌·경적·기차 소리가
  섞이면 안 됩니다. 답은 "Beep, beep! Beep, beep!" 처럼 두 번씩 두 묶음입니다.
- **마지막 후렴:** 앞 후렴들과 같은 빠르기여야 합니다. ep05 v1 처럼 마지막 후렴이 느려지면(한 줄에 2마디) 그 곡은
  고르지 마세요. 후렴 립싱크 컷을 다시 쓸 수 없어서 크레딧이 캡을 넘습니다.
- **끝:** 마지막 "Let's go for a ride!" 뒤에 연주만 나오는 부분이 3~4초(2마디) 있어야 합니다. 그 자리에
  "Bye-bye, friends!" 인사가 들어갑니다. 연주가 그보다 길게 이어져도(ep06 v1 은 31초) 탈락은 아닙니다. 영상은
  마지막 화음 2마디 뒤에서 끝냅니다 (`track.end`).
- **다운로드:** 마음에 드는 곡의 **WAV** 를 `~/ml/momo_ep09/suno/v1/` 에 넣어 주세요. 스템(Vocals, Instrumental)이
  있으면 함께 넣고, 없으면 이 맥에서 demucs 로 분리합니다. 부른 가사가 위와 다르면 ep04·ep07 처럼 이 파일 끝에
  "Sung lyrics" 블록을 추가해서 자막이 실제 노래를 따르게 합니다 (정렬기는 태그 없는 가사 블록 중 마지막 것을 읽습니다).

## Sung lyrics — Suno v1 take (what the captions show; alignment reads this last block)

Suno v1 "Vehicle Sounds" (approved by the user, 122.0 BPM, 1:49.7). It sings every line as written, but it
**skips chorus 3**: verse 2 ends at ≈ 58.3 s and verse 3 starts at ≈ 62 s after a 1.5-bar gap. The order is
Chorus, Verse 1, Chorus, Verse 2, Verse 3, Bridge, final Chorus. Other differences from the plan: the instrumental
intro is ≈ 1.5 bars (the first vocal is at ≈ 3.0 s, not 7.7 s), each section is followed by a ≈ 1.5-bar
instrumental gap (≈ 3 s), and the singing ends at ≈ 94.2 s with a ≈ 15 s instrumental tail.

```
[Instrumental intro]

[Chorus]
Beep, beep! Honk, honk!
Choo, choo! Wee-woo!
Toot, toot! Zoom, zoom!
Here they come! (Here they come!)
Wave hello! (Hello!)
Let's go for a ride!

[Verse 1]
What does the car say?
Beep, beep! Beep, beep! (Hello, car!)
What does the bus say?
Honk, honk! Honk, honk! (Hello, bus!)

[Chorus]
Beep, beep! Honk, honk!
Choo, choo! Wee-woo!
Toot, toot! Zoom, zoom!
Here they come! (Here they come!)
Wave hello! (Hello!)
Let's go for a ride!

[Verse 2]
What does the train say?
Choo, choo! Choo, choo! (Hello, train!)
Who is on the train? (Ducky! Quack, quack!)
What does the fire truck say?
Wee-woo! Wee-woo! (Hello, fire truck!)

[Verse 3]
What does the boat say?
Toot, toot! Toot, toot! (Hello, boat!)
What does the airplane say?
Zoom, zoom! Zoom, zoom! (Hello, airplane!)

[Bridge]
Car says beep! Bus says honk!
Train says choo! Fire truck says wee-woo!
Boat says toot! Airplane says zoom!
And Ducky says quack, quack!

[Chorus - final]
Beep, beep! Honk, honk!
Choo, choo! Wee-woo!
Toot, toot! Zoom, zoom!
Here they come! (Here they come!)
Wave hello! (Hello!)
Let's go for a ride!

[Outro - instrumental]
```
