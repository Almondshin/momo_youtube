# ep06 "Animal Sounds on the Farm" — lyrics v1 (2026-10-01)

User direction (ep04, kept for every song): English lyrics on a Korean children's-song (동요) rhythm, for Korean
families whose toddlers (2–4) learn English. Topic: farm animals and their sounds — cow, sheep, pig, horse, Ducky
the duck, hen — as kindergarten call-and-response: Momo asks "What does the cow say?", everyone answers "Moo, moo,
moo!" and the choir greets the animal "(Hello, cow!)". Draft for the user's approval; the song is made by the user
in Suno Pro (settings at the end).

Plan at ~127 BPM (one 4/4 bar ≈ 1.88 s; ep04's style line gave 127.6 BPM). The Suno take decides the real grid.

| Section | Bars | ≈ Time | Notes |
|---|---|---|---|
| Instrumental intro | 4 | 0:00–0:07 | no vocals; library greeting "Hi friends! It's Momo!" (L `intro_wave`) |
| Chorus 1 | 8 | –0:23 | six 1-bar lines → three 2-line shots |
| Verse 1 (cow, sheep) | 8 | –0:38 | question · answer · question · answer, one picture per line |
| Chorus 2 | 8 | –0:53 | reuse of the chorus 1 takes (`clip_from`, placed by vocal cross-correlation) |
| Verse 2 (pig, horse) | 8 | –1:08 | |
| Chorus 3 | 8 | –1:23 | reuse |
| Verse 3 (Ducky, hen) | 8 | –1:38 | Ducky gets the big hops |
| Bridge (review) | 8 | –1:53 | "Cow says moo!" — name + sound together |
| Chorus 4 (final) | 8 | –2:08 | reuse, bigger arrangement |
| Outro | 3 | –2:13 | instrumental; library "Bye-bye, friends! See you next time!" (L `outro_bye`) |

Total ≈ 71 bars ≈ 2:13 (target 2:00–2:20).

Shots (cuts start on each sung line, `cut_at` ≈ first word − 0.1 s; every shot with Momo = wan2_7 lip-sync with
the action; animal shots = seedance 4 s, the animal stays in place and the motion goes to tails, ears, sparkles):

| Section | Line(s) | Picture | Action (no deformation) |
|---|---|---|---|
| Intro | — | L `intro_wave` (library) | — |
| Chorus A | Moo, moo! Baa, baa! / Oink, oink! Quack, quack! | Momo frontal at the white farm fence, red barn softly blurred behind | sings and claps her paws on each sound, both feet on the grass |
| Chorus B | Neigh, neigh! Cluck, cluck! / Hello, farm friends! (Hello!) | Momo frontal on the farm grass | sings, sways side to side, waves one paw at shoulder height below the ear |
| Chorus C | Sing with me! (Sing with me!) / Animal sounds on the farm! | Momo and Ducky side by side at the fence | Momo sways and sings; Ducky hops happily (the big move is Ducky's) |
| V1 | What does the cow say? | Momo frontal at the fence | points to her side with one paw at chest height, small curious head tilt |
| V1 | Moo, moo, moo! (Hello, cow!) | a chubby round black-and-white spotted baby cow by the white fence, card COW | cow stays in place; tail swishes, ears flick, butterflies flutter |
| V1 | What does the sheep say? | Momo frontal | points to the other side, gentle nod |
| V1 | Baa, baa, baa! (Hello, sheep!) | a fluffy round white lamb on the grass lawn with daisies, card SHEEP | lamb stays in place; sparkles twinkle on the wool, daisies sway |
| V2 | What does the pig say? | Momo frontal by the red barn | points to her side, gentle bounce on bent knees |
| V2 | Oink, oink, oink! (Hello, pig!) | a chubby round pink piglet with a curly tail on clean golden straw by the red barn door, card PIG | piglet stays in place; curly tail wiggles, sparkles twinkle |
| V2 | What does the horse say? | Momo frontal at the fence | small head tilt, points to the other side |
| V2 | Neigh, neigh, neigh! (Hello, horse!) | a chubby round brown baby horse with a soft golden mane by the white fence, card HORSE | horse stays in place; mane and tail sway in the breeze |
| V3 | What does the duck say? | Momo and Ducky side by side, frontal | Momo points to Ducky beside her, sways |
| V3 | Quack, quack, quack! (Hello, Ducky!) | Ducky on the farm grass, card DUCK | Ducky does big happy hops, flaps tiny wings |
| V3 | What does the hen say? | Momo frontal | claps once, then points to her side |
| V3 | Cluck, cluck, cluck! (Hello, hen!) | a round red-brown hen with a small red comb on straw beside a little wooden coop, card HEN | hen stays in place; feathers ruffle, sparkles twinkle |
| Bridge | Cow says moo! Sheep says baa! | cow and lamb side by side at the fence (or the two answer clips reused, one bar each) | both stay still; sparkles |
| Bridge | Pig says oink! Duck says quack! | piglet and Ducky side by side (or reuse) | Ducky hops, piglet's tail wiggles |
| Bridge | Horse says neigh! Hen says cluck! | horse and hen side by side (or reuse) | mane sways, hen's feathers ruffle |
| Bridge | Yay! We can sing them all! | Momo and Ducky frontal | Momo claps and bounces gently on bent knees; Ducky hops |
| Chorus 2–4 | (as chorus 1) | reuse A · B · C | — |
| Outro | — | L `outro_bye` (library) | — |

Word cards: COW · SHEEP · PIG · HORSE · DUCK · HEN (on the animal answer close-ups, the sound as the small text, e.g.
COW / "moo, moo, moo"); the bridge can show the same cards again as a review.

Lessons applied: `[Instrumental intro - 4 bars, no vocals]` first (Suno sang a count-in over the 2-bar intro twice);
chorus of short 1-bar lines paired into ~2-line shots; one clear picture per verse line with still animals; Momo only
claps, sways, nods, waves (paw below the ear), points, bounces on bent knees — hops go to Ducky; every answer line
carries real words "(Hello, cow!)" so the aligner has anchors (sung "Neigh"/"Baa" are often heard as "nay"/"bah").
No brand or IP names, no borrowed song lines.

## Suno style

```style
Korean children's song style in English, Korean kindergarten sing-along, bright bouncy 2/4 march feel, 124 bpm, major key, 4-bar instrumental intro with no vocals, children's choir with a bright young female lead, call-and-response: the lead asks and the choir answers with the animal sound, piano, bells, glockenspiel, xylophone, woodblock, hand claps, light snare, simple singable melody, animal sounds are sung short and on the beat, not sound effects, very clear English, full-length song about 2 minutes 15 seconds
```

## Lyrics (Suno format)

```
[Instrumental intro - 4 bars, no vocals]

[Chorus - bouncy, everyone sings]
Moo, moo! Baa, baa!
Oink, oink! Quack, quack!
Neigh, neigh! Cluck, cluck!
Hello, farm friends! (Hello!)
Sing with me! (Sing with me!)
Animal sounds on the farm!

[Verse 1 - lead asks, choir answers]
What does the cow say?
Moo, moo, moo! (Hello, cow!)
What does the sheep say?
Baa, baa, baa! (Hello, sheep!)

[Chorus - bouncy, everyone sings]
Moo, moo! Baa, baa!
Oink, oink! Quack, quack!
Neigh, neigh! Cluck, cluck!
Hello, farm friends! (Hello!)
Sing with me! (Sing with me!)
Animal sounds on the farm!

[Verse 2 - lead asks, choir answers]
What does the pig say?
Oink, oink, oink! (Hello, pig!)
What does the horse say?
Neigh, neigh, neigh! (Hello, horse!)

[Chorus - bouncy, everyone sings]
Moo, moo! Baa, baa!
Oink, oink! Quack, quack!
Neigh, neigh! Cluck, cluck!
Hello, farm friends! (Hello!)
Sing with me! (Sing with me!)
Animal sounds on the farm!

[Verse 3 - lead asks, choir answers]
What does the duck say?
Quack, quack, quack! (Hello, Ducky!)
What does the hen say?
Cluck, cluck, cluck! (Hello, hen!)

[Bridge - everyone together]
Cow says moo! Sheep says baa!
Pig says oink! Duck says quack!
Horse says neigh! Hen says cluck!
Yay! We can sing them all!

[Chorus - final, bigger]
Moo, moo! Baa, baa!
Oink, oink! Quack, quack!
Neigh, neigh! Cluck, cluck!
Hello, farm friends! (Hello!)
Sing with me! (Sing with me!)
Animal sounds on the farm!

[Outro - instrumental, final chord]
```

## Suno 설정 (사용자가 suno.com 에서 직접 입력)

Custom 켬 · Instrumental 끔 · 최신 모델. ep04 와 같은 설정이고 제목·스타일·가사·스타일 제외만 바뀝니다.

| 항목 | 값 | 이유 |
|---|---|---|
| 제목 (Title) | `Animal Sounds on the Farm` | |
| 가사 (Lyrics) | 위 "Lyrics (Suno format)" 블록 전체 — 첫 줄 `[Instrumental intro - 4 bars, no vocals]` 포함 | 전주 4마디에 채널 인사가 들어갑니다 |
| 스타일 (Styles) | 위 `style` 블록 문구 그대로 | 한국 동요 리듬 + 영어 가사, 124 bpm |
| 스타일 제외 | 아래 문구 붙여넣기 | 슬프거나 시끄러운 스타일, 말로 하는 인트로·카운트인, 실제 동물 효과음을 막습니다 |
| 보컬 성별 | 여성 | 밝은 여성 리드 + 어린이 합창 |
| 길이 | **2:15** (꼭 2:00 이상) | 목표 2:00~2:20. ep04 첫 시도가 37초로 나온 원인이 이 설정이었습니다 |
| Max 모드 | 켬 | 2분이 넘는 곡에서 목소리·스타일이 끝까지 일정해 립싱크·자막 맞추기에 유리합니다 |
| 기이함 | 낮게 (20~30%) | 높으면 실험적인 곡이 나옵니다. 동요는 평범하고 또렷하게 |
| 스타일 영향 | Strong(강하게) 쪽 | 스타일 문구를 제안이 아니라 지시로 따르게 합니다 |
| 다양성 | 가장 낮게 | Suno 가 스타일 문구를 스스로 바꾸지 않게 합니다 |
| 개인화 | 끔 | 계정 취향이 섞이지 않게, 매번 같은 조건으로 |
| 저장 위치 | Momo 작업 공간 | 나중에 찾기 편하게 |

스타일 제외에 붙여넣을 문구:

```text
sad, dark, rock, metal, rap, heavy bass, autotune, screaming, slow ballad, spoken word, count-in, sound effects
```

받은 곡: 마음에 드는 곡의 **WAV** (스템 Vocals·Instrumental 이 있으면 함께, 없으면 demucs 로 분리)를
`~/ml/momo_ep06/suno/v1/` 에 넣어 주세요. 고르기 전에 확인할 것: 처음 약 7초(전주 4마디) 동안 노래가 없어야 하고,
"Moo, moo! Baa, baa!" 로 시작해야 합니다. 부른 가사가 위와 다르면 ep04 처럼 이 파일 끝에 "Sung lyrics" 블록을
추가해 자막이 실제 노래를 따르게 합니다.
