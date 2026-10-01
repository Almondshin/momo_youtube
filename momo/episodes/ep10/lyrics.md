# ep10 "Good Night" (잘 자요) — lyrics v1.1 (2026-10-01, reviewed)

User direction (ep04, kept for every song): English lyrics on a Korean children's-song (동요) rhythm, for Korean
families whose toddlers (2–4) learn English. This episode is a gentle bedtime dongyo (자장가 feel, but a sing-along,
not a slow lullaby): a bedtime routine in order — put on pajamas → read a story → hug Teddy → wave to the moon and
stars → close your eyes. It is calmer than ep04–ep07 (about 104 BPM instead of ~125, soft instruments) but keeps a
steady beat, because the user found ep02 slow (house format: singing ≥ 85 %, a new shot every 1–2 bars). It is
still a sing-along with call-and-response echoes, and it ends quietly with Momo asleep. Momo wears pajamas (option A
below, needs the user's OK) or her overalls (B), and keeps her look: big round head, huge round sparkly eyes, long
floppy ears hanging down. She always sings with her eyes **open**. Her eyes are closed only in the last shot, where
nobody on screen sings. Draft, not approved: the user makes the song in Suno Pro (settings at the end), and the
cut table is laid on that take's bar grid (PRODUCTION.md (9)).

Title: "Good Night Song with Momo the Bunny | Bedtime Routine for Toddlers". Thumbnail idea: shot CC (Momo and Ducky
on the bed, waving) with the text "GOOD NIGHT!".

Original lyrics. Nothing is borrowed from existing songs or books: no "Twinkle, twinkle…", "Rock-a-bye…", "Hush,
little baby…", "sleep tight", and no "good night, moon / good night, stars" list (that is the "Goodnight Moon" book's
device, so v1's "Night-night, moon! / Night-night, stars!" became "Wave to the moon! / Wave to the stars!" — an
action a toddler copies). The moon lines are "Look, the moon! (Hello, moon!)" and "Wave to the moon!". No brand or
show names. Lines are short and simple, so a toddler can repeat them.

## Momo's look in this episode (open choice for the user)

`config.character.rules[0]` says Momo's outfit, colours and proportions never change. Extra clothes go over the
overalls, and the two yellow buttons always show. Pajamas are an exception the user has to approve:

- **A (recommended):** soft mint-green pajamas in the same mint as the overalls, with a tiny white star print and a
  round collar. Two small yellow buttons sit high on the chest, one under each shoulder, where the overall
  strap buttons are (config: "two small yellow buttons on the shoulder straps"), so the scene signature stays. Face,
  fur, head and ears do not change. The auto-assembled `[Momo]` block says "mint-green overalls", so the image prompt
  has to say "dressed for bed in mint-green star-print pajamas instead of the overalls". Test this on the first image
  (5단계 (2)): the Momo element (character sheet) wears overalls and can pull them back. The on-model eye gate
  (≥ 0.65) applies as usual. **Budget guard:** if the first pajama image fails twice (the overalls come back, or the
  eye gate is below 0.65), stop and switch to B — trying A costs at most 4 credits.
- **B (the rule as it is):** Momo keeps the overalls in every shot, and the pajamas are a vocabulary object: folded
  on the bed (V1a), and in V1b Momo hugs the folded pajamas against her tummy ("Soft and cozy" is then about the
  pajamas). "Put on pajamas!" is sung to the child watching. Less risk to her look; the only mismatch is that she
  sleeps in her overalls in the END shot.
- **User decision 2026-10-01: A (mint star-print pajamas).** Switch to B only if the first pajama image fails twice.

## Plan

At ~104 BPM one 4/4 bar is ≈ 2.31 s, and 48 bars ≈ 1:51 — the "about 1 minute 50 seconds" the style asks for
(v1 asked for 98 BPM, which needs ≈ 1:58 for the same 48 bars, and a soft "lullaby" style pulls Suno slower, not
faster, so the take would drift past 2:00). Bouncy takes landed a little fast (ep04 asked for 124 and got 127.6);
for a soft song expect 100–106. The Suno take sets the real grid.

| Section | Bars | ≈ Time | Notes |
|---|---|---|---|
| Instrumental intro | 4 | 0:00–0:09 | no vocals. Library greeting "Hi friends! It's Momo!" (L `intro_wave`) |
| Chorus 1 | 6 | –0:23 | six 1-bar lines → three 2-line shots (CA · CB · CC) |
| Verse 1 (pajamas, story) | 6 | –0:37 | 2 echo lines (2 bars, object shots) + 2 plain lines (1 bar, Momo sings) |
| Chorus 2 | 6 | –0:51 | reuses CA · CB · CC (`clip_from`, placed by vocal cross-correlation) |
| Verse 2 (Teddy, Ducky) | 6 | –1:05 | same pattern |
| Chorus 3 | 6 | –1:18 | reuse |
| Verse 3 (moon, stars) | 6 | –1:32 | 2 echo lines (object shots) + 2 short lines paired into one Momo shot |
| Chorus 4 (final, softer) | 6 | –1:46 | lines 1–4 the same (reuse CA · CB). Lines 5–6 are the quiet ending "Close your eyes… Good night, Momo" over the sleeping shot. Only the last line slows down (+ ≈ 1–2 s) |
| Outro | 2 | –1:51 (–1:53 with the slow last line) | instrumental final chord. Library "Bye-bye, friends! See you next time!" (L `outro_bye`) |

Total ≈ 48 bars. There is **no instrumental break** after the intro. ep05's Suno take had a 41 s break, so the style
says "no instrumental break, singing all the way through", and every tag after the intro is a sung section.

## Shots

Set (used in every bedroom shot so the backgrounds match): "Momo's cozy bedroom at night: soft lavender-blue walls,
a small round window showing a deep-blue night sky with a crescent moon and little golden stars, a small white
wooden bed with a soft pale-pink blanket and a round white pillow, a fluffy cream rug, a little bedside table with a
warm glowing night-light; warm soft lamplight keeps the room bright and cozy, never dark". This is ep02 c02's
"soft pastel bedroom with a round window", at night. The blanket is pink, not yellow (v1), so yellow Ducky stands out
on it (V2c, V2d, CC, END) and the mint pajamas stand out in V1a. The round window is always **beside** Momo, never
straight behind her, so she can point or wave toward it while still facing the viewer.

Kinds:

- **LS** = wan2_7 lip-sync. Momo is frontal and sings with her **eyes open**. When standing, both feet are on the
  floor; in bed, she sits up and faces the viewer. Both long ears are fully visible and hang down beside the cheeks.
  Her paws stay at chest height, or beside the cheek below the ear. The motion prompt starts with the identity
  sentence ("Momo keeps exactly the same look as the first frame: big round head, huge round sparkly eyes with big
  white highlights…"). She uses small gestures only: sway, nod, wave, point, clap softly, hug, pat. Ducky gets the
  hops. She always looks at the viewer, also when she points at a book or a window. The image and motion prompts of
  a singing shot never say "sleepy", "yawn", "drowsy", "tired" or "resting her head" (those pull half-closed eyes,
  yawns and a tilted head); they say "calm cozy smile, eyes wide open". The word "sleepy" is in the song, not in the
  picture. In two-character shots Ducky's beak stays closed, and the two sit apart (touching characters can merge).
- **MO** = seedance_2_0_mini, about 4 s. The object stays completely still. The motion goes to sparkles, the
  night-light glow, twinkling stars or a drifting cloud.
- **RE** = reuse (`clip_from`, 0 credits).
- **L** = library clip.

| Shot | Sung line(s) | Bars | Kind | On screen / action | Card | New image | LS s |
|---|---|---:|---|---|---|---:|---:|
| L1 | (4-bar intro) | 4 | L `intro_wave` | library greeting | — | 0 | 0 |
| CA | Sleepy, sleepy, time for bed! / Sleepy, sleepy, rest your head! | 2 | LS | Momo sitting up in the small white bed, frontal, the pink blanket over her legs; sways gently side to side. On "rest your head" she pats the round white pillow beside her with one paw, still looking at the viewer. Eyes wide open. (v1 had her laying her head on her paws "like a pillow": that is the sleep gesture, the model closes the eyes and tilts the head, and this shot is reused in all four choruses) | — | 1 | 5 |
| CB | The moon is up, the stars are bright! / Good night, good night! (Good night!) | 2 | LS | Momo standing on the fluffy rug, frontal, both feet on the floor, the round window with the moon and stars beside her; points toward the window with one paw held out to the side at shoulder height, away from the ears, still facing the viewer; then waves gently at shoulder height below the ear on "good night" (v1: window behind her and pointing up — that turns her round and lifts the paw to the ears) | — | 1 | 5 |
| CC | Night-night, friends! (Night-night!) / Sweet dreams, good night! | 2 | LS, two characters | Momo and Ducky sitting side by side on the bed, a little apart, frontal; Momo waves one paw below the ear and sways; Ducky flaps its tiny wings and does a small hop on the blanket (the big move is Ducky's), beak closed | — | 1 | 5 |
| V1a | Put on pajamas! (Pajamas!) | 2 | MO | a neatly folded set of soft mint-green pajamas with a tiny white star print and two small yellow buttons, on the pink blanket, the bedroom softly blurred behind; the pajamas stay still, sparkles twinkle | PAJAMAS | 1 | 0 |
| V1b | Soft and cozy, cozy, cozy! | 1 | LS | Momo standing on the rug, frontal, both feet on the floor, big cozy smile, sways side to side. A: in her pajamas, both paws resting on her tummy below the two yellow buttons. B: in her overalls, hugging the folded mint pajamas low against her tummy (mouth and the two yellow buttons fully visible). (v1 "hugs herself with both paws crossed" — crossed short arms come out as extra or fused limbs) | — | 1 | 3 |
| V1c | Here is a book! (Story time!) | 2 | MO | one small picture book with a plain soft-blue cover showing a simple yellow crescent-moon picture, no letters, lying on the round white pillow, the bedroom blurred behind; the book stays still, sparkles twinkle | BOOK | 1 | 0 |
| V1d | Read, read, read a story! | 1 | LS | Momo sitting up in bed, frontal, the open picture book on her lap below her chin (simple pictures of a moon and a star, no letters, no words); she looks at the viewer, not down at the book, points at the page with one paw and nods (looking down = eyes half-closed and a tilted head, which fails the eye gate) | — | 1 | 3 |
| — | Chorus 2 | 6 | RE | CA · CB · CC | — | 0 | 0 |
| V2a | Here is Teddy! (Hello, Teddy!) | 2 | MO | a small soft light-brown teddy bear with round ears and a cream muzzle, sitting on the round white pillow, the bedroom blurred behind; the teddy stays still, sparkles twinkle | TEDDY | 1 | 0 |
| V2b | Hug, hug, a big warm hug! | 1 | LS | Momo sitting on the bed, frontal, hugging Teddy low against her tummy (her mouth and the two yellow buttons fully visible above Teddy); sways side to side | — | 1 | 3 |
| V2c | Hello, Ducky! (Quack, quack!) | 2 | MO (Ducky only) | Ducky on the pink blanket by the pillow; does two big happy hops on the blanket and flaps its tiny wings; the bed stays still. Momo sings off screen | — | 1 | 0 |
| V2d | Snuggle, snuggle, snuggle up! | 1 | LS, two characters | Momo and Ducky sitting up side by side under the pink blanket against the pillow, a little apart, frontal; Momo sways gently and pats the blanket, Ducky sways along beside her, beak closed. Eyes open (v1 "Ducky nestles against her arm" — touching characters can merge) | — | 1 | 3 |
| — | Chorus 3 | 6 | RE | CA · CB · CC | — | 0 | 0 |
| V3a | Look, the moon! (Hello, moon!) | 2 | MO | a big glowing pale-yellow crescent moon (a plain moon, no face) in the deep-blue night sky above soft round treetops, full-bleed (not framed by the window); the moon stays completely still, its soft glow pulses, tiny stars twinkle, a thin cloud drifts slowly | MOON | 1 | 0 |
| V3b | Look, the stars! (Hello, stars!) | 2 | MO | many small golden five-pointed stars across the deep-blue night sky above the treetops, the crescent moon softly blurred at the edge; the stars stay in place and twinkle (not a counting shot) | STARS | 1 | 0 |
| V3c | Wave to the moon! / Wave to the stars! | 2 | LS | Momo by the round window, waist-up, frontal, the window beside her with the moon and stars in it; she keeps facing the viewer and waves one paw toward the window at shoulder height below the ear on "moon", then the other paw on "stars" (the toddler waves along) | — | 1 | 5 |
| — | Chorus 4, lines 1–4 | 4 | RE | CA · CB | — | 0 | 0 |
| END | Close your eyes, (close your eyes,) / Good night, Momo. (Good night.) | 2–3 | MO, **not lip-sync** | Momo and Ducky fast asleep in the small white bed under the pink blanket, seen from the front at a slight high angle, Momo on her back with her head on the round white pillow and her face toward the viewer. Momo's eyes are gently closed, with a peaceful little smile; she hugs Teddy, and both long ears rest on the pillow. Ducky sleeps beside her. Through the round window: the crescent moon and golden stars. Motion: chests rise and fall slowly, the stars twinkle, the night-light glows softly. **Eyes stay closed, mouths stay closed — nobody on screen sings** (the choir sings to Momo). The only closed-eye shot. The eye gate cannot measure closed eyes, so check this shot by eye | — | 1 | 0 |
| L2 | (2-bar outro) | 2 | — | **User decision 2026-10-01: no library goodbye** — the END sleeping shot holds to the end of the song | — | 0 | 0 |

**Estimate:** 15 new images (8 LS + 7 MO) and ≈ 32 s of new lip-sync. At 104 BPM a 1-bar line is ≈ 2.3 s →
3 s clip (refs shorter than 3 s are padded) and a 2-bar shot ≈ 4.6 s → 5 s: 4 × 5 (CA, CB, CC, V3c) + 4 × 3 (V1b,
V1d, V2b, V2d) = 32 s. With the real windows (pickups, a slower take) expect 32–38 s; even if Suno stretches every
chorus to 8 bars the three chorus shots grow to ≈ 6 s each, ≈ 41 s, still under 45 s. Everything else is reuse or
library. Rough credits (config unit costs: image 2, wan2_7 1.5/s, seedance mini 1/s): images 15 × 2 = 30, lip-sync
32–38 s × 1.5 = 48–57, MO 6 × 4 s + END 6 s = 30. That is ≈ 108–117, or ≈ 130–140 with the 20 % regeneration
margin, under the cap of 150. Pajamas A can add up to 4 credits for its test (above). `estimate_credits.py`
decides once the cut table exists.

Word cards: PAJAMAS · BOOK · TEDDY · MOON · STARS, on the object close-ups. The small text is the sung word in
lower case, e.g. MOON / "hello, moon".

Lessons applied:

- `[Instrumental intro - 4 bars, no vocals]` comes first, because Suno sang a count-in over a short intro (ep03,
  ep04).
- There is no instrumental break after the intro (ep05). The outro is 2 bars at most.
- The chorus is short 1-bar lines paired into 2-line shots, so 3 of the 4 choruses are free reuse.
- Each verse line is one clear picture. The vocabulary objects stay still and the sparkles move (ep04).
- Object close-ups name the set, so the backgrounds match (ep03).
- Momo only sways, nods, waves, points, hugs or pats, with her paws below the ears, and the hops go to Ducky
  (ep04 c20 and c33).
- Every echo carries real words ("(Hello, moon!)", "(Story time!)"), so the aligner has anchors.
- Lip-sync start images are frontal (ep04 c33), Momo looks at the viewer in every singing shot, and no singing
  shot uses a sleep gesture or the words sleepy / yawn / tired in its prompts (review of v1).
- The final chorus keeps lines 1–4 at the same tempo, so the chorus-1 takes can be reused. Only the last line
  slows down.
- The style says "bedtime sing-along … soft and calm but not slow" and a steady 4/4, not "lullaby" or "swaying
  lilt": in Suno those pull the tempo down and into a 3/4 or 6/8 waltz feel, which stretches each line over 2 bars
  (double the lip-sync seconds). "waltz" and "slow ballad" are in the exclude list.

Open for the user:

1. Pajamas A or B (above). A is recommended; without an answer, B (the outfit rule as it is).
2. The library clips are daytime: `intro_wave` is a sunny meadow and `outro_bye` is a golden-afternoon meadow. So
   after the END shot, Momo is awake again and waving goodbye. The house format keeps them (0 credits). The other
   choice is to end on the sleeping shot without the outro greeting, which changes the format.

## Suno style

```style
Korean children's song style in English, Korean kindergarten bedtime sing-along, gentle and warm, soft and calm but not slow, 104 bpm, steady gentle 4/4 beat, major key, 4-bar instrumental intro with music box and soft piano and no vocals, warm clear young female lead with a soft children's choir, call-and-response echoes, soft piano, music box, celesta, glockenspiel, soft strings, light shaker, simple singable original melody, one short line per bar, short clear phrases, very clear English, no instrumental break, singing all the way through, steady tempo, only the very last line slows down and ends quietly, short 2-bar instrumental outro with a final chord, full-length song about 1 minute 50 seconds
```

## Lyrics (Suno format)

```
[Instrumental intro - 4 bars, no vocals]

[Chorus - soft and gentle, everyone sings]
Sleepy, sleepy, time for bed!
Sleepy, sleepy, rest your head!
The moon is up, the stars are bright!
Good night, good night! (Good night!)
Night-night, friends! (Night-night!)
Sweet dreams, good night!

[Verse 1 - lead sings, choir echoes softly]
Put on pajamas! (Pajamas!)
Soft and cozy, cozy, cozy!
Here is a book! (Story time!)
Read, read, read a story!

[Chorus - soft and gentle, everyone sings]
Sleepy, sleepy, time for bed!
Sleepy, sleepy, rest your head!
The moon is up, the stars are bright!
Good night, good night! (Good night!)
Night-night, friends! (Night-night!)
Sweet dreams, good night!

[Verse 2 - lead sings, choir echoes softly]
Here is Teddy! (Hello, Teddy!)
Hug, hug, a big warm hug!
Hello, Ducky! (Quack, quack!)
Snuggle, snuggle, snuggle up!

[Chorus - soft and gentle, everyone sings]
Sleepy, sleepy, time for bed!
Sleepy, sleepy, rest your head!
The moon is up, the stars are bright!
Good night, good night! (Good night!)
Night-night, friends! (Night-night!)
Sweet dreams, good night!

[Verse 3 - lead sings, choir echoes softly]
Look, the moon! (Hello, moon!)
Look, the stars! (Hello, stars!)
Wave to the moon!
Wave to the stars!

[Chorus - final, softer, same tempo]
Sleepy, sleepy, time for bed!
Sleepy, sleepy, rest your head!
The moon is up, the stars are bright!
Good night, good night! (Good night!)
Close your eyes, (close your eyes,)
Good night, Momo. (Good night.)

[Outro - instrumental, 2 bars, final chord]
```

## Suno 설정

suno.com → Create → **Custom** 모드에서 아래 순서대로 넣는다. ep06·ep07 과 같은 설정이고 제목·스타일·가사·스타일 제외·길이만 다르다.

| 항목 | 넣을 값 | 이유 |
|---|---|---|
| **Custom** | 켬 | 가사와 스타일을 직접 넣기 위해 |
| **Instrumental** | 끔 | 노래(보컬)가 있어야 한다 |
| **모델** | 최신 모델 | |
| **제목** | `Good Night` | |
| **스타일** | 위 `## Suno style` 블록 전체를 그대로 붙여넣기 | 잠자리 동요(자장가 느낌이지만 느린 자장가는 아님), 104 BPM, 4/4, 4마디 전주, 간주 없음 |
| **가사** | 위 `## Lyrics (Suno format)` 블록 전체를 그대로 붙여넣기 (대괄호 태그 포함) | 첫 줄 `[Instrumental intro - 4 bars, no vocals]` 는 인트로 인사 자리 |
| **스타일 제외** | 아래 문구 붙여넣기 | 슬프거나 어둡거나 시끄러운 스타일, 속삭이는 목소리, 허밍, 카운트인, 간주·솔로, 느린 발라드, 왈츠(3박), 긴 아웃트로·페이드아웃을 막는다 |
| **보컬 성별** | 여성 | 따뜻하고 또렷한 여성 리드와 어린이 합창 |
| **길이** | **1:50** (1:45~2:00). 정확히 고를 수 없으면 자동 | 가사가 104 BPM 에서 약 48마디, 약 1:51 분량이다 |
| **Max 모드** | 켬 | 곡 끝까지 목소리·스타일이 같게 유지돼 립싱크·자막 맞추기에 유리하다 |
| **기이함** | 낮게 (20~30%) | 동요는 평범하고 또렷해야 한다 |
| **스타일 영향** | Strong 쪽으로 | 스타일 문구("no instrumental break" 포함)를 제안이 아니라 지시로 따르게 한다 |
| **다양성** | 최저 | 높이면 Suno 가 스타일 문구를 스스로 바꾼다 |
| **개인화** | 끔 | 계정 취향이 섞이지 않게 한다 |
| **저장 위치** | "Momo" 작업 공간 | 나중에 찾기 편하다 |

스타일 제외에 붙여넣을 문구:

```text
sad, dark, scary, rock, metal, rap, EDM, heavy bass, heavy drums, autotune, screaming, whisper, humming, spoken word, count-in, instrumental break, interlude, solo, slow ballad, waltz, long outro, fade out, sound effects
```

곡을 고를 때 확인할 것:

- **전주:** 첫 목소리가 약 9초 뒤(4마디)에 나와야 한다. 전주에 카운트인·허밍·말소리가 없어야 한다.
- **간주 없음:** 첫 소절부터 마지막 "Good night." 까지 노래가 계속 이어져야 한다. 줄 사이 숨 고르기 말고 목소리가 5초(2마디) 넘게 끊기는 곳이 있으면 다른 곡을 고른다. ep05 첫 곡에는 41초짜리 간주가 있었다.
- **박자:** "하나-둘-셋-넷" 4박으로 들려야 한다. "쿵-짝-짝" 3박 왈츠나 흔들의자처럼 출렁이는 6/8 이면 한 줄이 2마디로 늘어나니 다른 곡을 고른다.
- **빠르기:** 한 줄이 약 2.3초(1마디) 안에 불려야 한다. 곡이 2:10 을 넘으면 한 줄을 2마디로 늘여 부른 곡이다. 그러면 립싱크 초가 두 배가 되어 크레딧 캡 150 을 넘기 쉬우니 다른 곡을 고른다.
- **Verse 3:** "Wave to the moon! / Wave to the stars!" 가 그대로 불려야 한다. "Good night, moon" 처럼 바뀌어 불리면(유명 그림책 문구) 다른 곡을 고른다.
- **마지막 후렴:** 앞 네 줄("Sleepy, sleepy…" ~ "Good night, good night!")이 다른 후렴과 같은 빠르기여야 앞 후렴의 립싱크 영상을 다시 쓸 수 있다. 느려지는 건 마지막 줄 "Good night, Momo." 하나만 괜찮다.
- **목소리:** 자장가라도 속삭이지 않고 가사가 또렷하게 들려야 한다. 자막 맞추기와 립싱크에 필요하다.
- **끝:** 마지막 "Good night." 뒤에 연주만 나오는 부분이 3초 이상, 6초 이하여야 한다. 그 자리에 "Bye-bye, friends!" 인사가 들어간다.
- **다운로드:** 마음에 드는 곡의 WAV 를 받아 `~/ml/momo_ep10/suno/v1/` 에 넣는다. 스템(Vocals, Instrumental)은 있으면 함께 넣고, 없으면 이 맥에서 demucs 로 분리한다. 부른 가사가 위와 다르면 ep04·ep07 처럼 이 파일 끝에 "Sung lyrics" 블록을 덧붙여 자막이 실제 노래를 따르게 한다.

## Sung lyrics — Suno v1 take (what the captions show; alignment reads this last block)

Suno v1 (approved by the user, 104.0 BPM, 1:50): the 4-bar intro is instrumental (first vocal at 9.3 s, on the
downbeat). In every chorus line 4 is sung "Good night, good night!" with the last "night" held for about a beat and
no "(Good night!)" echo; "Night-night, friends!" follows right after it (whisper on each chorus alone hears only the
two "good night"s, e.g. chorus 1: Good 15.95, night 16.24, good 17.17, night 17.30–18.38, Night 18.64). Everything
else is sung as written. The verses are sung one line per bar (4 bars, not 6), there is one bar of rest before
chorus 3 (55.3–57.6 s), and the last word ends at 94.7 s, followed by about 9 s of instrumental outro and a 6 s fade
(ends at 110.0 s).

```
[Instrumental intro - 4 bars, no vocals]

[Chorus - soft and gentle, everyone sings]
Sleepy, sleepy, time for bed!
Sleepy, sleepy, rest your head!
The moon is up, the stars are bright!
Good night, good night!
Night-night, friends! (Night-night!)
Sweet dreams, good night!

[Verse 1 - lead sings, choir echoes softly]
Put on pajamas! (Pajamas!)
Soft and cozy, cozy, cozy!
Here is a book! (Story time!)
Read, read, read a story!

[Chorus - soft and gentle, everyone sings]
Sleepy, sleepy, time for bed!
Sleepy, sleepy, rest your head!
The moon is up, the stars are bright!
Good night, good night!
Night-night, friends! (Night-night!)
Sweet dreams, good night!

[Verse 2 - lead sings, choir echoes softly]
Here is Teddy! (Hello, Teddy!)
Hug, hug, a big warm hug!
Hello, Ducky! (Quack, quack!)
Snuggle, snuggle, snuggle up!

[Chorus - soft and gentle, everyone sings]
Sleepy, sleepy, time for bed!
Sleepy, sleepy, rest your head!
The moon is up, the stars are bright!
Good night, good night!
Night-night, friends! (Night-night!)
Sweet dreams, good night!

[Verse 3 - lead sings, choir echoes softly]
Look, the moon! (Hello, moon!)
Look, the stars! (Hello, stars!)
Wave to the moon!
Wave to the stars!

[Chorus - final, softer, same tempo]
Sleepy, sleepy, time for bed!
Sleepy, sleepy, rest your head!
The moon is up, the stars are bright!
Good night, good night!
Close your eyes, (close your eyes,)
Good night, Momo. (Good night.)

[Outro - instrumental]
```
