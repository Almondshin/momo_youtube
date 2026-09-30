# ep03 주제 제안 (3단계 · 승인 필요)

**"이게 ep01 아니야?"에 대한 답:** 지시서 0단계의 설정값이 `에피소드 번호: [ep02]`였습니다(`momo/docs/ORIGINAL_BRIEF.md` 10행). ep01을 건너뛴 이유는 어디에도 적혀 있지 않습니다. 반면 도구 예시는 모두 ep01부터 시작합니다. 같은 지시서 226행의 `compile.py --lang en ep01 ep02 ep03`, `docs/PRODUCTION.md` 429행, `compile.py`·`upload.py` 예시가 그렇습니다. 그래서 헷갈리실 만합니다. 실제로 만든 편은 `momo/episodes/ep02` 하나뿐입니다. 올린 "Brush Your Teeth"가 채널의 첫 영상이고, 이번 편은 **두 번째 영상**입니다. 번호는 내부용이라 YouTube 제목에는 들어가지 않습니다(`episodes/ep02/youtube.json`의 title). **번호를 ep01부터 다시 매길지 정해 주세요.** 다시 매기면 ep02가 ep01이 되고, 이번 편이 ep02가 됩니다. 그대로 두면 이번 편은 ep03입니다.

## 벤치마크 확인: 최신 15개 중 상위 3개가 역대 성공작과 같은 포맷인가
두 채널 모두 역대 상위 5개에서 **축마다 따로 센 최다 값**은 다음과 같습니다(`research/*/report.md` §2·§9).
- 형식: **동요** (Cocomelon 5/5 · SSS 5/5)
- 소재: **생활습관** (2/5 · 2/5)
- 길이: **3분 이하** (3/5 · 5/5)

이 세 값은 조합을 센 것이 아닙니다. 세 값을 모두 갖춘 영상은 Cocomelon 1개(Bath Song), SSS 2개(This Is The Way, This Is The Way We Get Dressed)입니다. 최신 상위 3개 중에서는 두 채널 모두 **0개**입니다.
- **Cocomelon** (`research/cocomelon/report.md` §9)
  - Finger Family 1,200만 회: 동요·기타·3분 이하
  - Get Dressed & School 1,100만 회: 동요·생활습관·3~10분
  - Cody Ice Cream 830만 회: 동요·감정·3~10분
  - 셋 다 형식은 동요이고, 소재나 길이가 다릅니다. 격차가 가장 큰 축은 형식입니다. 동요 평균이 30분 미만 짧은 믹스의 3.16배입니다(§8).
- **Super Simple Songs** (`research/supersimplesongs/report.md` §9)
  - Top 20 Counting Songs 330만 회: 모음집·숫자·30분 이상
  - Sports! 320만 회: 동요·기타·3분 이하
  - Counting Up To 20 310만 회: 동요·숫자·3분 이하
  - 격차가 가장 큰 축은 길이입니다. 3분 이하가 1.13배이고, 영상 수는 4개 대 2개입니다(§8). 같은 §8에서 제목 검색 키워드 축도 1.13배로 동률입니다. `research/SUMMARY.md` §1은 이 격차를 '약함'으로 평가했습니다.
- **결론:** 형식은 지금처럼 **3분 이하 단일 동요**로 가고, 소재만 고릅니다.

## 후보 3개 비교
| 항목 | ① 채소 먹기 ★추천 | ② 비 오는 날 | ③ 박수 액션송 |
|---|---|---|---|
| 소재 축 | 생활습관(식습관), 동요 3분 이하 | 생활습관(날씨), 동요 3분 이하. `SUMMARY.md` §4가 원래 ep03으로 권장 | 감정·동작 따라 하기, 동요 3분 이하 |
| 씬 ②③④ 학습 | CARROT 아삭 / BROCCOLI 작은 나무 / CORN 나눠 먹기 + 더키 | BOOTS 쿵쿵 / UMBRELLA 펴기 / PUDDLE 작게 첨벙 + 더키 | CLAP 박수 / NOD 끄덕 / HOP 깡충 + 더키 |
| 후렴 | *Crunch, munch, veggie lunch! Happy tummy, crunch, crunch, crunch!* | *Drip, drop, rain on top! Stomp, stomp, SPLASH!* | *Happy, happy, clap, clap, clap!* (nod·hop으로 반복) |
| 따라 하기 | 앙 씹는 흉내, 배 토닥 | 발 구르기, 작은 점프, 두 팔로 우산 모양 | 박수, 끄덕, 제자리 깡충 |
| 단어 카드 | carrot · broccoli · corn | boots · umbrella · puddle | clap · nod · hop |
| 제목 EN | Crunchy Veggies Song with Momo the Bunny \| Carrot, Broccoli and Corn for Toddlers | Rainy Day Song with Momo the Bunny \| Boots, Umbrella and Puddles for Toddlers | Clap Your Hands Song with Momo the Bunny \| Happy Action Song for Toddlers |
| 썸네일 | CRUNCHY VEGGIES! | RAINY DAY! | CLAP CLAP! |
| 조연 | 더키 (승인된 캐릭터라 추가 비용 0) | 더키 (첨벙만, 노래는 안 함) | 더키 |
| 컷 구성 | 22컷: L 7 + V 15. L은 intro·outro + say_with_me×2·cheer×2·transition (2컷 재사용) | 22컷: L 6 + V 16. L은 intro·outro + say_with_me×2·cheer·transition (1컷 재사용). V 16이라 따로 승인 필요 | 23컷(씬 ①에 1컷 추가): L 7 + V 16. L은 intro·outro + cheer×2·say_with_me×2·transition (2컷 재사용). V 16이라 따로 승인 필요 |
| 립싱크 가정 | ep02 비율 적용: V 중 약 45%(약 7컷), 그중 절반이 10초 | 같음 (약 7컷) | 같음 (약 7컷) |
| 예상 크레딧 (ep02 실측 기준, 미확정) | 1차 약 179 → 여유 20% 약 212 → ep02 재생성률 28% 약 225 | 1차 약 190 → 20% 약 225 → 30% 약 243 (캡까지 약 7) | 1차 약 190 → 20% 약 225 → 28% 약 239 |

- **"라이브러리(L)"**는 이미 승인된 재사용 클립이고, **"새 영상(V)"**은 이번에 새로 만드는 클립입니다.
  - 승인된 라이브러리 클립은 intro_wave·outro_bye·say_with_me·cheer·transition **5종뿐**입니다(`momo/library/library.json`).
  - 모두 5초짜리이고 립싱크가 없습니다(1개 7.5크레딧 = config의 `video_720p_5s`). 그래서 입이 노래에 맞지 않습니다.
  - 그래서 세 안 모두 **중간 L 컷(①③ 5개, ② 4개)에서는 모모가 노래하거나 말하지 않습니다.** 간주나 따라 하기 대기 구간에만 씁니다.
  - ep02에서도 기획표의 L 컷 c08(say_with_me)과 c14(cheer)가 노래 버전에서 wan2_7 립싱크 V 컷으로 바뀌었습니다(`episodes/ep02/plan.md` → `manifest.json`의 c08 clip_en 28.5, c14 15.0).
- **중간 L 컷에 가사가 들어가는 경우:** 그 컷들을 립싱크 V로 새로 만들어야 합니다. 그러면 세 안 모두 L 2 + V 20 이상이 됩니다. 1차 약 234, 여유 20%를 넣으면 약 278 이상으로 캡 250을 넘습니다. `estimate_credits.py`가 exit 2로 멈추는 중단 조건입니다.
- **크레딧 계산식** (ep02 실측, `episodes/ep02/manifest.json`)
  - ep02에서 승인된 새 V 22컷의 시각물 비용은 240입니다. 이미지 44 + 립싱크 wan2_7 10컷 112.5(10초 5컷·5초 5컷) + 립싱크 없는 클립 12컷 83.5입니다. **V 1컷당 10.91**입니다.
  - 여기에 음성 약 6(ep02 승인 31블록 × 0.2 = 6.2)을 더합니다.
  - 반주 약 9.7도 더합니다(sonilo 0.0625/초 × 약 155초 가정. ep02는 170초에 10.63).
  - 단가 출처는 `config.higgsfield.unit_costs`입니다.
  - 10초 립싱크를 쓰지 않으면 더 쌉니다. 클립 평균이 약 7.1이면 ① 1차가 약 152입니다. 다만 이것은 측정하지 않은 가정입니다. ep02에서는 립싱크 10컷 중 5컷이 10초였습니다.
- **재생성 여유**는 이미지와 영상에만 붙습니다(`momolib/genrec.py` estimate). ep02의 품질 재생성률은 28%입니다.
  - 계산: (이미지 9장 18 + 클립 4건 49.5) ÷ 240.
  - 노래 리메이크로 버린 102와 대체된 kling 클립 45는 품질 문제가 아니라서 뺐습니다.
  - `estimate_credits.py`에는 반주 행이 없어서 반주는 따로 더했습니다.
  - 주제가 승인되면 manifest를 만들고 `estimate_credits.py`로 확정합니다.
- **한도:** 한 편 한도는 250입니다(`config.credits.episode_cap`). 참고로 ep02는 승인된 결과물만 합쳐도 256.83이었습니다(이미지 44 + 클립 196 + 음성 6.2 + 반주 10.63). 실제 지출은 671.93이고, 한도를 690으로 올렸습니다(`episodes/ep02/manifest.json` credits).
- **지시서 예상치와의 차이:** 지시서의 이후 편 예상치는 120~160입니다(`ORIGINAL_BRIEF.md` 143행). ep02 실측 단가로 계산하면 세 안 모두 1차(179·190)부터 이 범위를 넘습니다.
  - 143행에는 이 예상치의 전제가 적혀 있지 않습니다.
  - 다만 지시서의 비율 목표에는 S(정지) 컷 6~8개가 들어 있습니다(120행). ep02 리메이크 이후에는 S 컷이 0개입니다(`manifest.json` notes.remake_2026_09_29: 전 컷 애니메이션 + 립싱크).
  - 이것이 차이의 원인으로 보입니다(추론).
- **검사 경고:** S 0개와 L 6~7개는 권장 범위(S 6~8, L 3~4) 밖이라, 세 안 모두 검사(validate)에서 경고가 2건 뜹니다(`momolib/episode.py`). V 16인 ②·③은 `notes.v_over_reason`에 이유를 적지 않으면 에러가 납니다.

### ① 채소 먹기: 추천
- **근거 수치**
  - Cocomelon 역대 5위 'Yes Yes Vegetables Song' 34억 회, 4:08 (`research/cocomelon/report.md` §2). 길이는 3~10분 구간입니다.
  - 같은 곡 모음집 14억 회 (§5)
  - SSS 'Do You Like Broccoli Ice Cream?' 11억 회, 2:43 (`research/supersimplesongs/channel_flat.json`)
  - 최근 모멘텀: ②와 같은 방법으로 계산했습니다(아래 참고). Cocomelon 최신 15개에는 채소 영상이 없습니다.
    - Cocomelon 'Fruits and Vegetables Song' 1.98억 회, 7:12, 약 1년 전. 일평균 약 54만 이하로 226개 중 1위입니다.
    - Cocomelon 'Yes Yes Vegetables \| The Hungry Easter Bunny' 1,500만 회, 약 153일 전. 일평균 약 9.8만으로 37위입니다.
    - SSS 'Healthy Eating Song for Kids \| I Love Eating Vegetables' 650만 회, 약 123일 전. 일평균 약 5.3만으로 SSS 단편 42개 중 16위입니다.
    - 계산 방법: `research/*/channel_flat.json`에서 직접 계산했습니다. 30분 미만이고, 올라온 지 72시간이 지났고, 약 1년 안에 올라온 영상만 셌습니다. 날짜가 대략값이어서, '약 1년 전'으로 잡힌 영상의 일평균은 실제보다 높게 나왔을 수 있습니다(상한값).
  - Cocomelon 최신 15개에서 생활습관 소재 평균은 344만 회입니다(5개, 중앙값 140만, 기타 소재 대비 1.08배, `report.md` §7).
    - 5개 중 1개는 비 오는 날 영상(Jump in the Puddles)이고, 2개는 짧은 믹스입니다.
    - 그래서 ①만이 아니라 ①·② 공통 근거입니다.
- **추천 이유**
  - 역대 조회수(34억·11억)와 최근 일평균(226개 중 1위, 상한값) 모두 채소·음식 소재가 강합니다.
  - 새 영상이 15개라 권장 범위(12~15) 안입니다. 따로 승인받을 필요가 없고, ②·③(V 16)보다 1차 비용이 약 11 적습니다.
  - ep02 사물 클로즈업 5컷(c04·c05·c07·c16·c20)의 실측 결과입니다(`episodes/ep02/manifest.json` cuts[].gen).
    - 이 중 단어 카드가 붙은 컷은 c05·c07·c16입니다.
    - 영상(seedance_2_0_mini) 5개는 모두 첫 시도에 통과했습니다.
    - 이미지는 3장(c04·c07·c20)이 장면·소품 불일치로 한 번씩 다시 만들어졌습니다.
    - 합계 47크레딧입니다(이미지 16 + 영상 31).
  - 덧입는 옷이 없어서 단추가 가려질 위험이 없고, 토끼와 당근은 잘 어울립니다.
- **제작 위험**
  - 노래하는 입으로는 씹을 수 없습니다. 먹는 장면과 노래 장면을 다른 컷으로 나눕니다.
  - 음식은 측정한 적이 없습니다. 다만 ep02 사물 클로즈업 이미지는 5장 중 3장을 다시 만들었습니다.
    - c04: 칫솔컵이 작고 욕실 디자인이 c03과 다름
    - c07: c05와 다른 칫솔로 나옴
    - c20: 소품 3개가 작게 보임
  - 이번에 걱정되는 점은 두 가지입니다. 당근·브로콜리·옥수수가 컷마다 같은 모양으로 유지되는지(c07 사례), 그리고 복습 나열 컷에서 채소 3개가 작아지거나 개수가 틀리지 않는지(c20 사례)입니다. 그래서 재생성 여유를 ep02 실측 28%(약 225)로 잡았습니다.
  - 가사는 새로 씁니다(`ORIGINAL_BRIEF.md` 105행). Cocomelon의 'Yes Yes' 문형, "안 먹다가 먹어 보는" 줄거리, "배고픈 토끼" 설정(Hungry Easter Bunny)은 쓰지 않습니다.
  - Cocomelon에 이미 'Yum Yum Vegetables Song'(2.72억 회, 7:44)과 'Yummy Peas Song'(820만 회)이 있습니다(`research/cocomelon/channel_flat.json`). 그래서 제목·후렴·썸네일에 yum/yummy를 쓰지 않고 'Crunchy Veggies'와 'Crunch, munch'로 바꿨습니다.
  - 기본 효과음 세트에 'crunch'가 없습니다. 있는 것은 pop, sparkle, boing, whoosh, brush, swish, splash, chime입니다(`docs/MANIFEST.md`).
  - 라이브러리 클립이 5종뿐이라 L 7컷이면 2컷 이상을 재사용합니다. 반복처럼 보일 수 있습니다.

### ② 비 오는 날
- **근거 수치**
  - Cocomelon 'Jump in the Puddles'는 하루 약 33만 회입니다.
    - 계산: `research/cocomelon/data.json`의 view_count 1,100,000, age_hours 79.3.
    - date_source가 'approx'(업로드 시각이 대략값)라 근사치입니다.
    - 순위: `research/SUMMARY.md` §2(33만/일), §4(최신 15개 중 3위). 위와 같은 방법으로 226개 중 6위입니다.
  - 다만 올라온 지 3.3일 된 6:18짜리 영상 하나에 기댄 수치입니다. 같은 방법으로 계산한 다른 비 영상은 이렇습니다.
    - 'Rain Rain Go Away! \| NEW JJ's Animal Time' 1,000만 회, 약 153일 전, 일평균 약 6.5만, 72위
    - "JJ's Rain Boots Song!" 1,700만 회, 일평균 약 4.7만, 90~92위 동률. 날짜가 '약 1년 전' 대략값이라 최근 영상으로 보기 어렵습니다.
  - 역대 수치: 'Rain Rain Go Away' 15억 회, 'Yes Yes Dress for the Rain' 4.06억 회 (`research/cocomelon/channel_flat.json`)
  - 생활습관 평균 344만 회: ①·② 공통 근거입니다(① 참고).
- **제작 위험**
  - ep02의 작은 물 모션은 영상 2개 모두 첫 시도에 통과했습니다. c04 수도꼭지 물방울과 c16 컵 물결(둘 다 seedance)입니다. c18 물 뱉기는 이미지에만 있었고, 클립 모션은 몸 기울이기였습니다(역시 1회 통과). 빗줄기와 웅덩이 첨벙은 측정한 적이 없어서 여유를 30%(약 243)로 잡았습니다.
  - **안전 규칙:** 밝은 여우비(햇살 + 가는 비)로만 연출합니다. 회색·어두운 하늘, 천둥·번개, 번쩍임은 금지입니다(`ORIGINAL_BRIEF.md` 40행, `SUMMARY.md` 68행). 프롬프트에 dark·storm·thunder·lightning·flash를 쓰지 않습니다. 이 단어들은 검사 경고 대상입니다(`momolib/episode.py` 154~155행 SCARY_WORDS).
  - 우산이 펴지는 동작은 형태가 바뀌는 동작이라, 형태 변형 금지 규칙에 걸립니다(`PRODUCTION.md` 154행).
  - 우비는 멜빵바지 위에 덧입어야 하는데, 입히면 노란 단추 2개가 가려질 수 있습니다. 그래서 기본안에서는 뺐습니다(`config.character.rules[0]`·`[1]`).
  - 우산이나 점프 동작에서 귀가 설 수 있습니다. ep02에서 c02·c06·c09가 이 이유로 거절됐습니다.
  - 새 영상이 16개라 이유를 적고 따로 승인받아야 합니다. 여유 30%면 캡 250까지 약 7밖에 남지 않습니다.
  - 라이브러리 L 6컷이라 1컷 이상을 재사용합니다.

### ③ 박수 액션송 (Clap Your Hands)
- **근거 수치**
  - SSS 역대 5위 'If You're Happy And You Know It' 13억 회, 1:38 (`research/supersimplesongs/report.md` §2)
  - SSS 'Hello Hello! Can You Clap Your Hands?' 1.72억 회 (`research/supersimplesongs/channel_flat.json`)
- **장점**
  - 박수·끄덕 따라 하기 대기 구간을 노래하지 않는 L 클립에 그대로 둘 수 있습니다. cheer는 '박수 + 작은 점프', say_with_me는 '끄덕'입니다(`library.json`의 motion).
  - 그래서 "중간 L 컷에서는 노래하지 않는다"는 가정이 세 안 중 가장 자연스럽습니다.
  - ep02 c19는 대기 구간에서도 입이 계속 움직여 거절됐는데, 이 문제를 피할 수 있습니다.
  - 비용은 23컷 기준으로 ②와 비슷하고, ①보다 약 11 비쌉니다.
- **제작 위험**
  - 배우는 게 동사 3개뿐이라 학습 가치가 가장 낮습니다.
  - 끄덕·점프 동작에서 귀가 설 수 있습니다.
  - 라이브러리 클립이 5종뿐이라 L 7컷이면 2컷 이상을 재사용합니다(cheer·say_with_me 각 2회). 반복처럼 보일 수 있습니다.
  - 씬 ①이 3컷이라 한 컷을 더 넣어야 합니다(`PRODUCTION.md` 146행: 씬당 4~6컷). 그래서 23컷입니다.
    - 추가 컷을 V로 넣으면 V 16이 되어 이유를 적고 따로 승인받아야 합니다. 비용은 약 11 늘어납니다. 표는 이 기준입니다.
    - L로 넣으면 비용은 ①과 같지만(179·212·225), L이 8컷이 되어 재사용이 3컷 이상으로 늘어납니다.
  - 제목의 'Clap Your Hands'가 SSS 곡명 'Hello Hello! Can You Clap Your Hands?'와 일부 겹칩니다.
- **3번째로 고른 이유:** '기분 표현'과 '숫자 세기'도 검토했습니다.
  - 기분 표현은 근거(SSS If You're Happy 13억)가 이 안과 겹칩니다.
  - 숫자 세기는 이미지 모델이 사물 개수를 틀리기 쉬워 재생성이 늘 수 있습니다(`SUMMARY.md` 68행).
  - 두 안의 크레딧은 컷 구성을 짜지 않아서 측정하지 않았습니다.
  - 이 안은 따라 하기 구간을 노래하지 않는 라이브러리 클립에 맞출 수 있어서 골랐습니다.

**[승인 요청]** ①·②·③ 중 하나를 골라 주세요. 번호(ep03 유지, 또는 ep01부터 다시 매기기)도 함께 정해 주세요. 승인 전에는 4단계(기획표)로 넘어가지 않습니다.