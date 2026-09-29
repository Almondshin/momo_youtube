# 벤치마킹 종합 — Cocomelon · Super Simple Songs (2026-09-29)

채널별 상세 수치는 [cocomelon/report.md](cocomelon/report.md), [supersimplesongs/report.md](supersimplesongs/report.md).

## 0. 수집 범위와 한계 (먼저 읽을 것)

| 항목 | 상태 | 비고 |
|---|---|---|
| (a) 채널 목록·구독자·조회수·길이 | ✔ | GitHub Actions 러너에서 yt-dlp `--flat-playlist` (세션 네트워크는 youtube.com 차단) |
| (b) 인기순 `sort=p` | ✔ 시도 → 내림차순 아님 | 두 채널 모두 목록을 조회수 내림차순 정렬로 대체 |
| (d) 영상별 메타 (좋아요·댓글·태그·설명·정확한 업로드일) | ✖ 차단 | 러너 IP 봇 확인. `--sleep-requests 1` 재시도도 실패 |
| 2단계 자막·영상 프레임·샷 길이 | ✖ 차단 | 같은 봇 확인 |
| 2단계 썸네일 | ✔ | 채널별 최신 15 + 역대 5 = 20장씩 직접 보고 분류 (`labels.json`) |

yt-dlp 에러 원문 (영상별 페이지 전부 동일):

```
ERROR: [youtube] e_04ZrNroTo: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies
```

→ 업로드 날짜는 목록의 대략값("N일 전"), 72시간 판정도 대략값 기준. 3단계 구조 분석(샷 길이·반복·콜앤리스폰스 대기)은
프레임·자막이 없어 **수치로 검증하지 못함**.

## 1. 판정 요약

| 항목 | Cocomelon | Super Simple Songs |
|---|---:|---:|
| 구독자 / 목록 영상 수 | 2.03억 / 1,351 | 4,700만 / 777 |
| 채널 상태 | 정체 (누적 중앙값 0.35배, 일평균 1.77배) | 정체 (0.46배, 1.40배) |
| 역대 최고작 | Wheels on the Bus 94억 | This Is The Way 25억 |
| 역대 최고작 / 최근 단편 평균 | 2,873배 | 1,147배 |
| 구독자 대비 — 최고작 / 최근 평균 | 46.3배 / 0.02배 | 53.2배 / 0.05배 |
| 역대 5개 비중 (목록 총 조회수) | 14.2% | 16.1% |
| 30분+ 모음집 (별도 축) | 496개, 목록 조회수의 26.8% | 295개, 18.6% (최신 15 중 7개) |
| 격차 최대 축 | **형식**: 단일 동요 3.83M vs 짧은 믹스 1.21M (3.16배) | **길이**: ≤3분 2.27M vs 3~10분 2.00M (1.13배, 약함) |

## 2. 공통 패턴

1. **역대 상위 10개(두 채널) 전부 단일 동요, 9개가 4분 이하.** 소재는 생활습관 4개(Bath Song, Yes Yes Vegetables,
   This Is The Way, Get Dressed), 탈것·동물·숫자·감정 각 1~2개. 모음집은 역대 상위 5에 0개.
2. **나이 보정(일평균 조회수)하면 최근 강세 소재가 보인다.**
   - Cocomelon: Finger Family(고전 동요) 42만/일, Get Dressed & School(생활습관) 35만/일,
     **Jump in the Puddles – Rainy Day(생활습관·비 오는 날) 33만/일(업로드 3일)**, Happy and You Know It(감정) 27만/일.
     약세: 종이인형·농장 역할놀이·잠자리 믹스 5~7만/일.
   - Super Simple Songs: **숫자 세기**가 최근 단편 중 최강 — Counting Up To 20 약 10만/일, Top 20 Counting 약 11만/일
     (나머지 단편 3~5만/일의 2배 이상). 역대 4위 Five Little Ducks 19억도 숫자+동물.
3. **썸네일: 단편은 100% 캐릭터 클로즈업(+사물 1개), 글자 없음.** 텍스트 위주 썸네일은 SSS 의 30분+ 모음집
   ("TOP 20 … SONGS / 50 MINS") 7개뿐이고 그 평균(134만)이 단편 평균(218만)보다 낮다.
   → 모모 썸네일: 모모 얼굴 크게 + 핵심 사물 1개 + 3단어 이하 문구(지시서 규칙과 일치).
4. **제목**: 두 채널 모두 `곡명 | 설명 | 채널명` 구조에 kids / nursery rhymes / toddlers / counting 등 검색어 포함.

## 3. 원인 축 → 이번 에피소드 방향

두 채널의 격차 축(형식: 단일 동요 > 믹스, 길이: ≤3분)은 같은 방향을 가리킨다:
**2~3분짜리 단일 주제 동요형(TTS 는 챈트) 에피소드 + 부모 검색어가 들어간 제목**. 지시서의 150초·5씬 구조와 일치.

## 4. 주제 제안 3개 (승인 필요)

| | A. 양치하기 (추천) | B. 비 오는 날 | C. 숫자 1~5 세기 |
|---|---|---|---|
| 소재 축 | 생활습관(양치) | 생활습관(비 오는 날) + 색 | 숫자 |
| 근거 | SSS 역대 1위(양치 썸네일) 25억, 생활습관이 역대 상위 10 중 4개 | Cocomelon 최근 Rainy Day 33만/일 (최신 15 중 3위) | SSS 최근 단편 최강(숫자 약 10만/일), Five Little Ducks 19억 |
| 씬 ②③④ 학습 포인트 | 칫솔·치약 → 위아래 → 동글동글(+Ducky) | 노란 우비 → 빨간 장화 → 파란 우산(+Ducky 웅덩이) | 하나·둘 → 셋 → 넷·다섯(+Ducky) |
| 화면 키워드 EN / KO | BRUSH · UP · DOWN · RINSE / 칫솔 · 위아래 · 동글동글 · 헹구기 | RAINCOAT · BOOTS · UMBRELLA / 우비 · 장화 · 우산 | ONE … FIVE / 하나 … 다섯 |
| 제목 EN | Brush Your Teeth Song with Momo the Bunny \| Morning Routine for Toddlers | Rainy Day Song with Momo the Bunny \| Raincoat, Boots, Umbrella for Toddlers | Count to 5 with Momo the Bunny \| Numbers 1 to 5 for Toddlers |
| 제목 KO | 양치 동요 \| 치카치카 이 닦기 \| 아기토끼 모모 | 비 오는 날 동요 \| 우비·장화·우산 \| 아기토끼 모모 | 숫자 세기 1~5 \| 하나 둘 셋 \| 아기토끼 모모 |
| 썸네일 문구 | BRUSH BRUSH! / 치카치카! | RAINY DAY! / 비 오는 날! | 1 2 3 4 5 / 하나 둘 셋 |
| 제작 위험 | 낮음 — 의상 그대로, 얼굴 클로즈업 위주. 치약 튜브는 "라벨 없음"으로 | 중간 — 우비가 노란 단추를 가릴 수 있음(우비 앞을 열어 단추 노출), 어두운 비 장면 금지 → 밝은 여우비 | 중간 — 이미지 모델이 사물 개수를 틀리기 쉬워 재생성 증가 가능 |

**추천: A (양치하기)** — 역대 근거가 가장 크고, 첫 편(라이브러리·캐릭터 시트를 함께 만드는 편)에서
캐릭터 일관성 위험이 가장 낮다. B 는 최근 모멘텀이 가장 좋아서 다음 편(ep03)으로 권장.

## 5. 남은 일 / 막힌 일

- 3단계 구조 분석은 자막·프레임이 있어야 수치로 할 수 있음. 선택지:
  1. `YOUTUBE_API_KEY` 를 GitHub Secret 으로 → (d) 영상별 메타(좋아요·댓글·태그·정확한 날짜)는 해결. 자막·프레임은 여전히 불가.
  2. 브라우저 쿠키(cookies.txt, **보조 구글 계정** 권장)를 GitHub Secret 으로 → 러너 yt-dlp 재시도. 계정 제재 위험이 있어 권장도 낮음.
  3. 로컬 PC(가정용 IP)에서 `python momo/sample_videos.py` 실행 후 결과 커밋.
  4. 2단계 없이 진행 — 구조는 지시서 기본값(150초·5씬·[pause 1.5]·키워드 1개/컷)을 따르고, 벤치마크 구조 검증은 "미수행"으로 기록.
- 분석이 끝나면 복호화한 썸네일 시트(`research/*/frames/`, git 제외)는 `sample_videos.py --cleanup` 으로 삭제.
