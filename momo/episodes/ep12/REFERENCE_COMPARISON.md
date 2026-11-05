# ep12 기준곡 중심 비교 — 2026-11-05

## 사용자 기준

[사용자가 고른 기준곡](https://suno.com/song/1d8d324e-fcde-4cf6-a961-4442e1e50303), **7.5/10**.
공유 링크 `https://suno.com/s/BUx5U88mdSg7XyeI`의 실제 연결 주소를 확인했다.
처음 만든 후보 B이며, 지금까지 다른 스타일로 바꾼 곡들보다 이 곡이 좋다는 평가다.

여성/어린 여자아이 음색 선호만 분리해 최적화하지 않는다. 전체적인 곡의 매력과 기준곡의 느낌을 우선한다.
기준곡 자체는 비교 출발점이며 아직 최종 채택·다운로드 승인은 아니다.

## 비교 설계

| 그룹 | 유지하는 것 | 바꾸는 것 | 생성 방식 |
|---|---|---|---|
| A 원래 느낌 유지 | 원곡 가사·선율·템포·남아 느낌 보컬·그루브 | 작은 음질·전환 다듬기 | 원본 음원 영향 0.88, 스타일 영향 0.45 |
| B 후렴·리듬 강화 | 원곡 가사·선율·템포·남아 느낌 보컬 | 킥·박수와 베이스의 리듬을 더 뚜렷하게 | 원본 음원 영향 0.76, 스타일 영향 0.72 |
| C 여자 보컬 | 원곡 가사·선율·템포·반주 느낌 | 밝고 귀여운 여자 보컬 쪽으로 변화 | 원본 음원 영향 0.62, 스타일 영향 0.82 |

각 2곡, 총 6곡을 목표로 공식 `audio-covers-create`를 사용한다. 기준곡의 가사와 곡 ID를 직접 입력한다.
위 영향 수치와 편곡은 제작자 선택이다. 요청 내용대로 실제 결과가 나왔는지 듣고 비교해야 한다.
아직 어느 곡도 승인 상태로 기록하지 않는다. 별도 Max Mode나 다운로드 크레딧을 사용하지 않는다.

## 직전 리듬 시안 (기준곡 선택 전에 제출됨)

- [v5 시안 1](https://suno.com/song/a903f44f-f815-436c-b584-8bcc065f6095), 32.40초.
- [v5 시안 2](https://suno.com/song/ff9f0c7d-01b4-4df2-8ac1-00b6401456a3), 31.76초.

위 두 곡은 이전 리듬 탐색 이력으로 보존하며, 이번 기준곡 중심 6곡과 구분한다.
v1~v5 누적 생성 50크레딧, 다운로드 0개. 비교 묶음의 비용은 생성 후 실제 잔액 차이로 추가 기록한다.

## 완료된 후보

| 후보 | 방향 | 길이 | 듣기 |
|---|---|---:|---|
| A1 | 원래 느낌 유지 | 97.00초 | [Suno](https://suno.com/song/88efa6c3-04f4-4018-9e51-05270f668cd0) |
| A2 | 원래 느낌 유지 | 52.64초 | [Suno](https://suno.com/song/5dae3e4b-86e3-4d89-9065-e071254cd458) |
| B1 | 후렴·리듬 강화 | 46.36초 | [Suno](https://suno.com/song/b2dc38ab-7ac5-4350-80a4-33bae2bac9f0) |
| B2 | 후렴·리듬 강화 | 46.76초 | [Suno](https://suno.com/song/0ee0d4ec-f881-44fa-9d4a-ead99202d0e9) |
| C1 | 여자 보컬 | 50.36초 | [Suno](https://suno.com/song/f7193ad9-d88c-40a5-9f72-3522f47efc54) |
| C2 | 여자 보컬 | 52.00초 | [Suno](https://suno.com/song/eeab06e7-fbcb-41de-b3bb-f1a73e2df327) |

A1 외 다섯 후보는 1분 미만으로 생성되었다. 비교용 음원이며 최종 1~2분 완성곡 기준을 충족했다고 표시하지 않는다.
보컬·곡 느낌에 대한 사용자 선택 후 채택 곡의 완성 길이·편집 필요성을 검토한다.

## 실제 비용

이번 커버 요청 3회, 완료된 후보 6개에 **30크레딧**을 사용했다.
생성 잔액 2,450 → 2,420. ep12 전체 누적 **80크레딧**. 다운로드 잔액 20, 다운로드·Higgsfield 사용은 0.
근거: `suno/usage-before-ref01.json`, `suno/usage-after-ref01.json`.

## 청취 분석 메모 (사용자 판단을 대체하지 않음)

Suno `audio-listen`의 평가다. 기준곡을 함께 들으며 계산한 유사도는 아니며, 최종 승인·정렬·실제 파일 검사를 대신하지 않는다.

| 후보 | 분석에서 묘사한 목소리 | 주된 우려 |
|---|---|---|
| A1 | Light, warm adult male-sounding voice; polished and lightly processed, not strongly artificial | About 16 seconds of instrumental-only middle passage interrupts the momentum / Ending is cut during the reverb tail |
| A2 |  |  |
| B1 | Male/boy-like, bright and youthful, polished with a slightly synthetic edge | Ending cuts off during the final phrase / Slightly synthetic vocal quality |
| B2 |  |  |
| C1 | Youthful, girl-like, bright and playful; fairly natural, polished delivery | Clip ends without a musical resolution |
| C2 |  |  |

먼저 들어볼 추천: **C1**(밝고 비교적 자연스러운 여자아이 느낌), **B1**(밝은 남아 느낌·뚜렷한 리듬).
분석에서 여섯 후보 모두 끝맺음이 잘린 것으로 평가되었다. A1에는 약 16초 간주도 지적되었다.
따라서 비교 후 채택한 곡의 마무리·길이·간주를 수정하고 실제 파일로 확인해야 한다. 현재 최종 제작 가능 판정은 0개다.

## 사용자 선택

2026-11-05 사용자: **“C2가 가장 괜찮아”**. C2를 길이·마무리 보완의 기준으로 선택했다.
제작자의 C1 추천보다 사용자의 C2 선택이 우선한다. C2의 실제 목소리와 곡 느낌을 유지한다.
