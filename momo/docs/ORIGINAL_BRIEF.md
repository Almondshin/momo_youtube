# 원본 작업 지시서 (사용자 제공, 2026-09-29)

> 이 문서는 사용자가 준 지시서 원문이다. 파이프라인의 모든 규칙은 여기서 나왔다.
> 수정하지 말고, 바뀐 규칙은 config.json / docs/PRODUCTION.md 에 반영한다.

# 아기토끼 모모(Momo) 키즈 채널 — 벤치마킹 → 에피소드 제작 자동화 프롬프트 (yt-dlp 버전)

━━━ 0단계 · 설정 ━━━
벤치마킹 채널: [채널 URL]          ← 영상 링크가 아니라 채널 링크
에피소드 번호: [ep02]
에피소드 주제: [비워두면 1단계 결과에서 3개 제안하고 승인받을 것]
제작 언어: 영어 + 한국어 (비주얼은 한 벌만 만들고, 음성·화면 텍스트만 두 벌)

작업 폴더 ./momo/ (없으면 생성):
  config.json              음성 ID, 폰트 경로, 크레딧 캡 등 고정값
  library/                 재사용 클립·고정 음성 (인트로/아웃트로/리액션/전환)
  assets/bgm/  assets/sfx/  assets/fonts/   내가 넣어둔 파일. 없으면 멈추고 알려줄 것
  episodes/[ep]/           manifest.json, images/, clips/, audio/{en,ko}/, out/

시작 전 확인:
· yt-dlp, ffmpeg, ffprobe, python3(Pillow) 설치 여부. yt-dlp는 `yt-dlp -U`로 최신화할 것
  (유튜브가 자주 바뀌어서 구버전은 목록 추출부터 실패한다)
· Claude Code에 Higgsfield MCP가 연결돼 있는지
· assets/fonts/에 한글을 지원하는 둥근 고딕 폰트(TTF/OTF)가 있는지 — 없으면 멈추고 요청

캐릭터 고정 블록 — 모든 이미지 프롬프트 맨 앞에 그대로 삽입 (`[Momo]` 자리):
"Momo, a chubby round baby bunny, soft cream-white fur, oversized floppy ears with pale pink inner ears,
 huge sparkly dark eyes, small pink nose, rosy cheeks, mint-green overalls with one yellow button,
 big expressive smile"
조연 (필요한 에피소드에서만): Ducky — "a tiny round yellow duckling with an orange beak, no clothes"
캐릭터 절대 규칙: 의상·색·비율을 바꾸지 말 것. 이야기상 우비 등은 멜빵바지 위에 덧입힌다.
노란 단추 하나는 항상 보이게 (이게 씬 간 일관성을 잡아주는 시그니처).

스타일 락 — 전 컷 동일, 모든 이미지 프롬프트 맨 뒤에 붙일 것:
"bright saturated 3D cartoon animation style, Pixar-like soft rounded shapes, clean simple background,
 one focal object per shot, eye-level or slightly low camera, soft even lighting,
 full-bleed edge-to-edge, no border, no frame, no vignette, no text, no letters, no numbers,
 no logos, no watermarks"
⚠️ 코코멜론·핑크퐁·페파피그 등 기존 IP의 캐릭터명·화풍을 프롬프트에 적지 말 것. 비슷하게 나오면 재생성.
⚠️ 무서운 요소, 어두운 장면, 번쩍이는 효과 금지. 2~5세가 보는 영상이다.

━━━ 1단계 · 채널 분석 (yt-dlp) ━━━
(a) 채널 목록
    yt-dlp --flat-playlist -J "[채널 URL]/videos" > channel.json
    · 최상위 channel_follower_count = 구독자 수, entries = 영상 목록(최신순)
    · 각 entry의 id / title / view_count / duration 사용
    · 영상이 2,000개를 넘으면 --playlist-end 2000까지만 받고 "일부 기준"이라고 명시
(b) 역대 인기 5개
    먼저 "[채널 URL]/videos?view=0&sort=p&flow=grid"로 인기순을 시도해보고,
    결과가 실제로 조회수 내림차순이면 그 상위 5개를, 아니면 (a) entries를 view_count 내림차순
    정렬한 상위 5개를 쓴다. 어느 쪽을 썼는지 명시.
(c) 최신 15개 = (a) entries 앞 15개
(d) 위 20개(중복 제외)는 개별 메타데이터를 추가로 받을 것:
    yt-dlp --skip-download -J <video_url>
    → upload_date, view_count, like_count, comment_count, duration, tags, description

⚠️ 봇 확인/403이 뜨면 --sleep-requests 1 추가 → 그래도 안 되면 --cookies-from-browser chrome
   → 그래도 안 되면 멈추고 에러 원문 그대로 보고
⚠️ 업로드 후 72시간이 안 된 영상은 평균 계산에서 빼고, 뺐다는 걸 명시
⚠️ 30분 이상 모음집(compilation)은 별도 축으로 분리. 단편 평균과 섞지 말 것
   (키즈 채널은 모음집이 조회수를 독식하는 경우가 많아 섞으면 평균이 왜곡된다)

판정:
· 역대 최고작 / 최근 단편 평균의 배수
· 구독자 수 대비 조회수 배수 (역대 최고작, 최근 평균 각각)
· 역대 5개가 받아온 목록 총 조회수에서 차지하는 비중
· 채널 상태를 성장 / 정체 / 하락 중 하나로

최근 15개를 아래 축으로 분류해 축별 평균 조회수를 대조 (감이 아니라 숫자로):
· 학습 소재: 색 / 숫자 / 알파벳·단어 / 동물 / 생활습관(양치·목욕·비 오는 날) / 탈것 / 감정
· 형식: 동요 / 스토리 / 퀴즈·따라하기 / 모음집
· 길이 구간: ≤3분 / 3~10분 / 10~30분 / 30분+
· 썸네일 주인공: 캐릭터 클로즈업 / 사물 / 텍스트 위주
· 제목에 검색 키워드(colors, numbers, toddler, kids, nursery 등) 포함 여부
격차가 가장 큰 축을 원인으로 지목하고, 이번 에피소드 주제를 그 축에 맞춰 3개 제안 → 승인받을 것.
최신 15개 중 상위 3개가 역대 성공작과 같은 포맷인지도 비교.

━━━ 2단계 · 자막·영상 샘플 추출 ━━━
대상: 역대 1위 + 최근 1위, 두 편.
(a) 자막
    yt-dlp --skip-download --write-auto-subs --sub-lang "en,ko" --sub-format json3 -o "%(id)s" <url>
    → json3를 텍스트+타임코드로 변환. 자동 자막 특유의 중복 줄은 제거
    → 자막이 아예 없으면(동요 채널은 흔함) 건너뛰고 (b)만 진행, 건너뛰었다고 명시
(b) 프레임 샘플
    yt-dlp -f "bv*[height<=480]" -o "%(id)s.%(ext)s" <url>
    → ffmpeg로 균등 간격 프레임 추출 (총 30~40장이 되도록 간격 계산) → 직접 눈으로 보고 분석
    → ffmpeg select='gt(scene,0.3)'로 샷 전환 횟수를 세서 평균 샷 길이(초) 산출
(c) 썸네일
    https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg (없으면 hqdefault.jpg)
    역대 1위·2위 + 최근 1위·최하위, 최소 4장을 직접 보고 비교. 1장만 보고 패턴을 단정하지 말 것
⚠️ 받은 영상은 분석 용도로만 쓰고, 어떤 프레임도 재사용하지 말 것. 분석이 끝나면 삭제

━━━ 3단계 · 구조 분석 ━━━
· 오프닝 5초에 무엇이 먼저 나오는가 (캐릭터 인사 / 노래 / 사물 클로즈업)
· 평균 샷 길이(2단계 산출값)와 컷 전환 리듬
· 반복 구조: 같은 후렴·문장이 몇 번 반복되는지, 반복 간격
· 콜 앤 리스폰스: "따라 해봐" 뒤에 대기 구간이 있는지, 몇 초인지
· 한 화면당 학습 포인트 수 (사물 1개 원칙을 지키는지)
· 화면 텍스트: 키워드만 / 문장 자막 / 없음
· 캐릭터 노출 비율 (샘플 프레임 중 주인공이 보이는 비율)
· 제목과 썸네일 문구의 차이
· 시리즈 확장 방식 (에피소드 번호 / 소재 시리즈 / 모음집)

━━━ 4단계 · 에피소드 기획 ━━━
구조는 벤치마크를 따르되 내용은 새로 쓴다. 번역이 아니라 재창작.
· 길이: 2~3분(약 150초), 5개 씬, 씬당 4~6컷 → 총 22~28컷
· 씬 구성: ① 인사+문제 제기 → ② 학습 1 → ③ 학습 2 → ④ 학습 3(친구 등장 가능) → ⑤ 복습+작별
· 씬마다 학습 포인트 1개. 핵심 단어는 최소 3번 반복
· 콜 앤 리스폰스: "같이 말해볼까?" 뒤에 [pause 1.5] 마커.
  마커는 TTS에 보내지 않고 조립 때 무음으로 넣는다
· 노래 파트는 TTS가 부를 수 없으니 리듬감 있는 챈트로 쓰고 [chant] 마커 표시
· 인트로 첫 문장, 아웃트로 마지막 문장은 매 에피소드 동일 (라이브러리 클립과 짝):
  EN "Hi friends! It's Momo!"  /  "Bye-bye, friends! See you next time!"
  KO "안녕, 친구들! 나는 모모야!"  /  "친구들, 안녕! 다음에 또 만나!"

컷 타입 3종 — 비용이 여기서 갈린다:
· L = 라이브러리. 인트로/아웃트로/리액션/전환. 이미 있으면 생성 안 함, 0크레딧
· V = 영상 컷 (승인된 이미지 → 5초 클립). 모모가 움직여야 하는 컷: 점프, 손 흔들기, 사물 집기, 등장
· S = 정지 컷 (+조립 시 미세 줌). 사물 클로즈업, 배경, 복습 나열 화면
비율 목표: V 12~15개, S 6~8개, L 3~4개. V가 15개를 넘으면 이유를 적고 승인받을 것

표로 정리하고 manifest.json으로도 저장:
| 컷 | 씬 | 타입 | 나레이션 EN | 나레이션 KO | 화면 키워드 EN / KO | 이미지 프롬프트 (EN, [Momo]+스타일 락 포함) | 모션 지시 (V만) |

⚠️ 나레이션은 문장 짧게. 한 컷당 EN 25단어·KO 40자 안팎. 어른 톤 설명 금지
⚠️ 화면 키워드는 컷당 1개 (색 이름, 숫자, 사물 이름). 문장 자막은 쓰지 않는다
⚠️ 이미지 프롬프트에 글자·숫자·간판을 넣지 말 것. 텍스트는 전부 조립에서 얹는다
⚠️ 모션 지시는 작게: "small hop in place", "waves one paw", "ears bounce".
   카메라 이동·급격한 움직임·형태 변형 금지

제목·썸네일:
· 제목(EN/KO)은 부모가 검색하는 키워드형
  예: "Learn Colors with Momo the Bunny | Red, Yellow, Blue for Toddlers"
· 썸네일 문구는 3단어 이하로 크게. 예: "RED YELLOW BLUE" / "빨강 노랑 파랑"
· 썸네일로 쓸 컷을 하나 지정 (모모 클로즈업 + 핵심 사물)

━━━ 5단계 · 제작 (Higgsfield) ━━━
순서를 반드시 지켜줘.

(0) 프리플라이트
    · get_cost:true로 이미지·영상·음성 단가 확인, show_plans_and_credits로 플랜 확인
    · library/에 이미 있는 클립·음성을 확인해 재생성 대상에서 제외
    · 총 소요 크레딧을 계산해서 보고 (예상: 첫 편 200~250, 이후 편 120~160)

(1) 캐릭터 시트 — library/에 없을 때만, 첫 편 1회
    · 모모 턴어라운드 1장: front / three-quarter / side / back + 표정 4종, 흰 배경, 16:9
    · 보여주고 승인 → 승인본을 Higgsfield Elements(reference element)로 등록
      등록이 안 되면 매 생성 호출에 reference image로 직접 첨부.
      그것도 안 되면 캐릭터 고정 블록을 프롬프트 맨 앞에 그대로 반복
    · Ducky가 나오는 에피소드면 같은 방식으로 1장

(2) 1번 컷 1장만 생성 (nano_banana_pro, 16:9) → 한도 통과 여부 검증

(3) 통과하면 씬 1의 컷 3장까지 생성 → 3장을 함께 보여주고 승인받을 것.
    1장으로는 스타일·캐릭터 일관성을 판단할 수 없으니 반드시 3장. 승인 전엔 넘어가지 마.

(4) 승인되면 그 3장 중 V 타입만 영상으로
    · kling3_0_turbo, duration 5, aspect_ratio 16:9
    · 승인된 이미지를 start_image로 넣을 것. text-to-video로 새로 뽑지 마 (화풍이 어긋난다)
    · 프롬프트에 "keep the character design exactly the same" 포함
    · 모션은 manifest의 모션 지시만. 카메라 고정
    → 클립을 보여주고 승인. 형태 변형·의상 변화·귀 개수 이상이 있으면 재생성

(5) 나머지 컷
    · 이미지는 한 번에 3~4장씩만 병렬. 12장 이상 동시 요청 금지
    · V 타입은 이미지 승인 후 영상 변환, S 타입은 이미지로 끝

(6) 라이브러리 — 첫 편에서만 생성
    intro_wave(인사하며 손 흔들기), outro_bye(작별 인사), say_with_me(고개 끄덕임),
    cheer(박수), transition(깡충 뛰어 화면 밖으로) — 각 5초 클립
    → library/에 그 이름 그대로 저장. 이후 에피소드에서는 재생성 금지

(7) 음성 (seed_audio)
    · list_voices로 EN·KO 각각 후보 3개 → 같은 문장으로 1블록씩 샘플 → 승인
    · 승인된 voice id를 config.json에 고정. 이후 에피소드에서 바꾸지 말 것
    · 톤: 따뜻하고 약간 높은 음, 느린 속도, 문장 끝을 올리는 말투
    · [pause] 마커 기준으로 문장을 쪼개 블록 단위로 생성. 마커 자체는 보내지 말 것
    · 인트로·아웃트로 고정 문장은 library/audio/{en,ko}/에 1회만 생성해 재사용
    · KO 음성 품질이 부족하면(발음 뭉개짐, 억양 어색) 멈추고 알려줄 것

⚠️ 중단 조건 — 하나라도 걸리면 즉시 멈추고 에러 원문 그대로 보고
· 이번 에피소드 총 크레딧이 250을 넘을 것 같을 때
· 일일 생성 한도 / 플랜 권한 에러 (grace_daily_limit_reached 등)
· 크레딧이 남아 있어도 생성 횟수 한도는 별개다. 둘 다 감시할 것
· 힉스필드는 이미지·음성·영상을 하나의 생성 카운터로 센다
⚠️ 실패 시: 어느 컷까지 성공했는지 표로 정리하고, 성공분은 버리지 말고 보존한 뒤 재개 방법을 알려줄 것

━━━ 6단계 · 조립 (ffmpeg, 재실행 가능 스크립트) ━━━
build.py --ep [ep] --lang en|ko 로 실행되게 만들어줘.
manifest.json과 assets를 읽어 컷 길이·텍스트 타이밍을 매번 자동 재계산할 것.
음성을 다시 뽑아도 스크립트만 다시 돌리면 되게.

컷 길이:
· 기본 = 해당 언어 나레이션 길이 + 0.4초 여유 + [pause] 무음 합계, 최소 3초
· 언어마다 길이가 다르므로 EN·KO 타임라인은 각각 계산
V 컷:
· 5초 클립을 그대로 사용. 켄번즈 적용하지 말 것
· 나레이션이 5초보다 길면 클립을 정방향→역방향(핑퐁)으로 한 번 이어 붙이고,
  그래도 모자라면 마지막 프레임을 정지시켜 채울 것
· 짧으면 나레이션 끝에서 자를 것
S 컷:
· 5~8% 줌인/줌아웃 홀짝 교차 + 아주 느린 좌우 드리프트. 빠른 움직임 금지
L 컷:
· library/ 클립 + library/audio/ 고정 음성 사용. 새로 만들지 말 것
전환: 0.3초 크로스페이드 또는 컷. 화려한 와이프 금지

화면 텍스트 (문장 자막이 아니라 키워드):
· 컷당 키워드 1개, 화면 높이의 약 1/8 크기
· 상단 중앙 안전영역(상단 25% 밴드)에 배치. 모모 얼굴 위에 올리지 말 것
· 둥근 고딕(assets/fonts/), 흰색 또는 노란색 채움 + 두꺼운 검정 외곽선, 살짝 커지며 등장
· manifest에 text_at(초)가 있으면 그 시점에, 없으면 컷 시작 0.5초 후
· KO 버전은 한글이 깨지지 않는지 렌더링 결과를 직접 확인

오디오:
· 나레이션 + assets/bgm/ 루프. BGM은 나레이션 아래로 -16dB 덕킹, 시작·끝 페이드
· assets/sfx/가 있으면 manifest의 sfx 컬럼 위치에 삽입 (없으면 생략)
· 최종 loudnorm -14 LUFS, 48kHz

출력:
· 1920x1080 / 30fps / H.264 yuv420p / AAC → episodes/[ep]/out/[ep]_en.mp4, [ep]_ko.mp4
· 이미지·클립 해상도가 다르면 크롭-투-필로 통일. 레터박스 금지
· 이미지에 테두리 프레임이 생겼으면 3~4% 인셋 크롭으로 제거
· 썸네일: 4단계에서 지정한 컷 이미지 + 썸네일 문구 → 1280x720 JPG (EN/KO 각각)
· 완성본은 처음부터 끝까지 직접 확인: 텍스트가 얼굴을 가리는지, 컷 사이 음성이 끊기는지, 한글이 깨지는지

모음집 (선택): compile.py --lang en ep01 ep02 ep03 ...
· 에피소드 사이에 library/transition 클립 삽입
· 유튜브 설명란용 챕터 타임스탬프 텍스트도 같이 출력

━━━ 7단계 · 업로드 메모 ━━━
· 제목·설명·태그를 EN/KO 각각 출력 (설명에는 학습 포인트 3줄 + 해시태그 10개)
· 유튜브 업로드 시 "아동용 콘텐츠(made for kids)"로 설정해야 한다는 점을 명시
· episodes/[ep]/README.md에 기록: 주제, 컷 수, 사용 크레딧, 재생성 횟수, 다음 편에 반영할 점

━━━ 추가 요청 (같은 메시지) ━━━
깃허브 저장소는 momo 로 작업하고, 유튜브에 업로드까지 자동화 됐으면 좋겠어.
