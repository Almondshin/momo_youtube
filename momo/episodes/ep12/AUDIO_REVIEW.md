# ep12 v1 음원 후보 검수 — 2026-11-05

**이전 버전 기록.** 사용자가 여성 보컬·유아 율동 동요로 수정을 요청해 v1은 사용 보류했다.
아래 B 추천과 다운로드 확인 대기는 당시 상태이며, 현재는 v2 새 후보를 제작한다.

공식 Suno MCP `audio-create` 1회로 두 후보를 만들었다. 생성 크레딧 사용량은 **10**, 잔액은 **2,490**이다.
다운로드는 아직 실행하지 않았다. 다운로드 크레딧은 **20**개다.

| 항목 | 후보 A | 후보 B |
|---|---|---|
| 듣기 | [A](https://suno.com/song/364d25d8-bf8f-4636-8942-692b1e5483ea) | [B](https://suno.com/song/1d8d324e-fcde-4cf6-a961-4442e1e50303) |
| 길이 | 98.80초 | 98.76초 |
| 분석 템포 / 조성 | 113.9 BPM / C major | 113.1 BPM / C major |
| Suno 청취 분석의 발음 평가 | apple·banana 명확, 자연스러운 강세 | apple·banana 명확, 자연스러운 강세 |
| 청취 분석의 적합도 | 8/10 | 9/10 |
| 청취 분석의 가창 비율 추정 | 약 65% | 약 85% |
| 주요 우려 | 후반 짧은 가창 사이 공백, 긴 끝 반주 | 중간 약 8.7초 간주, 긴 끝 반주 |
| 현재 판단 | 대안으로 보존 | **다운로드·편집 검토 우선 후보** |

청취 분석은 Suno `audio-listen`의 평가다. 에이전트가 직접 청취한 판단이나 사용자의 최종 승인이 아니다.
가창 비율은 추정치이며 로컬 보컬 스템으로 확인하기 전에는 제작 기준 통과로 판정하지 않는다.
특히 후보 A는 청취 분석의 마지막 가창 시각(약 93.45초)과 가사 정렬의 마지막 시각(84.759초)이 달라 재확인이 필요하다.

## 후보 B의 편집 확인 지점

- Suno 가사 정렬: 첫 단어 1.220초, 마지막 단어 종료 90.246초.
- 브리지 마지막 단어 종료 59.894초 → 마지막 후렴 시작 68.614초: **8.720초 공백**.
- 마지막 가창 뒤 약 8.514초가 남는다. 실제 잔향·마지막 코드와 가창 유무를 확인한 뒤 끝 길이를 정한다.
- 원본을 보존하고 로컬 스템·박자 분석으로 간주를 마디 단위로 줄일 수 있는지 확인한다.
  편집 후 단어 타이밍을 다시 계산한다. 아직 편집 범위나 최종 길이는 확정하지 않았다.
- 원문 가사를 기준으로 한 Suno 정렬 성공이 실제 가창의 완전 일치를 증명하지는 않는다.
  독립 음성 인식과 보컬 신호로 누락·추가 가창을 확인해야 한다.

## 다운로드 확인 대기

2026-11-05 후보 B의 WAV에 `audio-download`를 `confirm` 없이 호출했다. 응답:

```json
{"status":"requires_credit","format":"wav","credits_remaining":20,"message":"Downloading this song uses one of the user's suno.com download credits. Ask them first, then call again with confirm: true."}
```

사용자에게 **1 다운로드 크레딧 사용**을 확인 요청했다. 답변 전에는 `confirm: true`를 호출하지 않는다.
추가 결제·플랜 변경은 없다. 다른 URL로 원본 다운로드 확인을 우회하지 않는다.

## 재개에 필요한 기록

- 제출 인자 및 중복 방지 키: `suno/v1-request.json`
- 생성·완료 응답: `suno/v1-create-response.json`, `suno/v1-wait-response.json`
- 실제 사용량: `suno/usage-before.json`, `suno/usage-after-v1.json`
- 후보별 평가·분석·정렬: `suno/v1-{1,2}-listen-result.json`, `-analysis.json`, `-alignment.json`
- 후보 B 줄 단위 임시 타이밍: `suno/v1-2-lines-provisional.json` (최종 타이밍 아님)
- 다운로드 사전 응답: `suno/v1-2-download-preflight.json`

성공한 두 곡을 다시 생성하지 않는다. 다음 작업은 다운로드 확인을 받은 뒤 기존 후보를 받아 검수·편집하는 것이다.
