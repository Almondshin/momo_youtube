# assets/fonts — 화면 키워드·썸네일 폰트

**한글을 지원하는 둥근 고딕** TTF/OTF 를 넣는다. 영문 글자도 같은 폰트로 그린다.

현재 들어 있는 것: `NanumSquareRoundB.ttf` (나눔스퀘어라운드 Bold, SIL OFL 1.1 — `NanumSquareRound-OFL.txt`).
`config.json` 의 `fonts.keyword` / `fonts.thumbnail` 이 이 파일을 가리킨다.

## 후보

| 폰트 | 라이선스 | 비고 |
|---|---|---|
| 나눔스퀘어라운드 (NanumSquareRound) | SIL OFL 1.1 | 현재 사용. Bold/ExtraBold 권장 |
| 주아 (Jua, 배달의민족) | SIL OFL 1.1 | Google Fonts 에서 받을 수 있음. 두껍고 둥글어 아이용으로 잘 맞음 |
| 카페24 써라운드 (Cafe24 Ssurround) | 카페24 자체 무료 폰트 라이선스 | 상업적 이용·영상 사용 조건을 받기 전에 직접 확인 |

- 영상·썸네일(상업적 이용)에 쓸 수 있는 라이선스인지 확인하고, 라이선스 파일을 폰트 옆에 같이 둔다.
- 획이 가는 폰트는 두꺼운 검정 외곽선과 합쳐지면 뭉개진다 — Bold 이상을 쓴다.

## 어떻게 쓰이나

- build.py 가 `config.fonts.keyword`(썸네일은 `fonts.thumbnail`) → 이 폴더의 첫 폰트 순서로 찾는다.
  KO 버전은 '가' 글리프가 실제로 그려지는 폰트만 쓴다.
- 폰트를 바꾸면 `config.fonts` 의 경로(momo/ 기준, 예: `assets/fonts/Jua-Regular.ttf`)도 고친다.
- **한글 지원 폰트가 없으면 파이프라인이 멈춘다** (`doctor.py` ✖, build 는 "폰트가 없음 … 넣어줘" 에러).
- 확인: `python momo/doctor.py`, 그리고 `python momo/build.py --ep <ep> --lang ko --check` 의 확인 시트에서
  한글이 네모(두부)로 깨지지 않는지 본다.
