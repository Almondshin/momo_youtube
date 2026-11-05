# YouTube 연결 점검 — 2026-11-05

## 재인증 완료

- 채널: **Momo Time / @MomoTimeSong** (`UCAI7Voo0OwG-7sr1eZeN7dA`). 실제 channels.list 결과로 확인.
- 로컬 `youtube_check.py --lang en` 성공.
- GitHub Secrets의 클라이언트 ID·클라이언트 보안 비밀번호·refresh token 갱신 완료.
- GitHub Actions 연결 점검 성공: https://github.com/Almondshin/momo_youtube/actions/runs/41982889643
- 새 인증 정보는 git 제외 `.secrets/`와 GitHub Secrets에 보관.
- 기존 클라이언트에 새 보안 비밀번호를 추가했다. 이전 보안 비밀번호는 다른 사용처를 확인하지 못했으므로 중지·삭제하지 않았다.

## 남은 장기 운영 설정

- OAuth 앱 게시 상태: **테스트 중**. 외부 앱의 이 상태에서 발급된 refresh token은 7일 뒤 만료된다.
- 공식 문서: https://developers.google.com/identity/protocols/oauth2/#expiration
- Google Cloud는 브랜딩 구성을 완료해야 앱을 게시할 수 있다고 표시한다. 홈페이지·개인정보처리방침·약관 URL은 비어 있다. 임의의 URL이나 정책을 등록하지 않았다.
- 운영 상태 전환과 YouTube API 감사(audit)는 별개다. 현재 인증 성공을 자동 공개 가능으로 해석하면 안 된다.

## 이전 오류 기록

- 이전 서버 점검: https://github.com/Almondshin/momo_youtube/actions/runs/41968603856
- 원문: `invalid_grant: Bad Request`.
- 로컬 다운로드 파일로 재인증했을 때 `invalid_client`. 다운로드 파일의 보안 비밀번호와 Cloud에 등록된 비밀번호가 달랐음을 확인했다.
- 새 비밀번호로 인증 코드를 교환한 뒤 채널 확인과 서버 검사를 통과했다.

## ep12 업로드

- 비공개 업로드 완료: https://www.youtube.com/watch?v=zuj_D5y978A
- API에서 처리 완료, 아동용 true, 비공개 상태 및 업로드 채널 확인. 썸네일 설정 완료.
- Studio 화면 확인은 Google 본인 인증 화면에서 대기. 공개 전환은 하지 않았다.
