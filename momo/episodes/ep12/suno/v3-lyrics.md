# ep12 — Apple & Banana | MomoTime (v3)

Palette: kpop — preschool bubblegum action nursery rhyme, 116 bpm, little-girl-style female solo.
Language: English. 학습 목표는 **apple · banana 두 단어**다.
상태: 2026-11-05 사용자 피드백에 따라 여성 보컬·유아 율동 동요로 수정. v2는 목소리 때문에 사용자 거절. 어린 여자아이 음색을 요청한 v3 후보 생성 완료·실제 음색 확인 중.

## 사용자가 수정한 방향

- 추가 확인: 두 v2 후보 모두 목소리가 마음에 들지 않았으며, **어린 여자아이처럼 맑고 높고 귀여운 목소리**를 선택했다.
- v3는 가사·박자·구조를 v2와 같게 두고 보컬 음색 지시를 변경한다. v2 가사는 `suno/v2-lyrics.md`에 보존했다.

- “여자 목소리로 해주고”, “2살~4살이 듣는 동요는 아기상어, 바나나차차 이런건데”.
- 이전 남아 보컬·펑크 디스코 후보는 채택하지 않고 기록만 보존한다.
- 짧은 멜로디, 자주 돌아오는 후렴, 과일 이름과 박수·발 두드리기를 연결하는 율동 동요로 새로 만든다.
- 학습 카드는 APPLE·BANANA만 표시한다. clap·tap은 율동 지시이며 새 학습 카드로 추가하지 않는다.
- 116 BPM, 4음 안팎의 좁은 음역, 한 줄 약 2마디는 제작자의 구체화다. 실제 음악이 지키는지 검수한다.
- 24줄 × 2마디를 기준으로 약 99초를 요청한다. 목표 95~105초, 최종 허용 범위 60~120초.

## Style

```style
bright high little-girl solo singing voice, unmistakably small childlike FEMALE timbre, pure clear light head voice, sweet innocent youthful tone, cute playful crisp diction, straight tone with almost no vibrato, happy small energetic phrases, preschool action nursery rhyme for ages 2 to 4, playful bubblegum kids pop, 116 bpm, simple steady 4/4 bounce, major key, upfront dry vocal, original tiny four-note melody within a fifth, repeated notes and short stepwise phrases, identical catchy hook three times, each lyric line across two bars with space to copy, clear apple and ba-NA-na pronunciation, simple piano and marimba plucks, soft rounded bass, light kick and handclaps, sparse toy percussion, sing immediately within the first second, continuous sung sections with short breaths, brief final chord and clean natural ending, about 95 to 105 seconds
```

## Lyrics (Suno format)

```
[Chorus - immediate female singing, same simple hook each time]
Apple, apple, clap, clap, clap!
Apple, apple, tap, tap, tap!
Banana, banana, clap, clap, clap!
Banana, banana, tap, tap, tap!

[Verse 1 - simple sung phrases, no instrumental gap]
Apple, apple!
Hello, apple!
Apple, apple!
Clap with me!

[Chorus - exact same melody and rhythm]
Apple, apple, clap, clap, clap!
Apple, apple, tap, tap, tap!
Banana, banana, clap, clap, clap!
Banana, banana, tap, tap, tap!

[Verse 2 - same tune as Verse 1, no instrumental gap]
Banana, banana!
Hello, banana!
Banana, banana!
Clap with me!

[Final Chorus - exact same hook, no key change]
Apple, apple, clap, clap, clap!
Apple, apple, tap, tap, tap!
Banana, banana, clap, clap, clap!
Banana, banana, tap, tap, tap!

[Outro - short, sung]
Apple, apple!
Banana, banana!
Clap, clap, clap!
Bye-bye!

[End - final chord, stop]
```

## 제작 메모

- 공식 MCP에서 `vocal_gender: female`을 설정한다. 고정 나레이션 `config.voices`는 별도이므로 수정하지 않는다.
- 가사는 새로 작성했고, 참조곡의 음원·멜로디를 입력하거나 보컬을 복제하지 않는다.
- 참고 범위는 단순한 반복과 따라 하기 쉬운 동작이다. [YouTube의 아기상어 설명](https://blog.youtube/culture-and-trends/baby-shark/)도 반복성과 손동작을 설명한다.
  [뽀로로 공식 바나나차차 영상](https://www.youtube.com/watch?v=O9UO6z-7A0U)은 사용자가 제시한 방향의 참고 자료이며, 이 작업에서 음원을 내려받아 분석한 것은 아니다.
- 전주를 길게 확보하기보다 바로 후렴으로 시작한다. 모모 영상은 립싱크 없이 움직이고, 과일을 들고 뛰거나 먹지 않는다.
- v1 가사·요청·결과는 `suno/v1-*`에 남긴다. 이전 B곡의 다운로드 확인 요청은 이 변경으로 대체되었다.
- 새 음원은 여성 보컬, 쉬운 반복 선율, 과일 발음, 가사 대응, 과도한 간주, 자연스러운 끝맺음을 확인한 뒤 고른다.
