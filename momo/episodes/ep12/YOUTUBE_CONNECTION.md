# YouTube 연결 점검 — 2026-11-05

영상 제작과 별개로 기존 GitHub Actions 인증을 확인했다. 빌드·업로드는 하지 않았다.

- 실행: https://github.com/Almondshin/momo_youtube/actions/runs/41968603856
- 영어 연결 결과: 실패, 인증 갱신 단계의 invalid_grant. 채널 이름·ID 확인까지 도달하지 못함.
- 도구 원문: `('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})`
- 토큰 만료·취소 또는 OAuth 클라이언트 불일치 가능성이 있으며 원인은 아직 구분하지 못했다.
- 재로그인으로 올바른 @MomoTimeSong 채널의 인증을 갱신한 뒤 채널 연결 검사를 다시 해야 한다.
- 비밀값은 출력하지 않았으며 로그 원본은 git 제외 audio/ 안에만 둔다.
- 업로드나 새 영상 공개는 실행하지 않았다. 미디어 제작·검수는 계속 가능하다.
