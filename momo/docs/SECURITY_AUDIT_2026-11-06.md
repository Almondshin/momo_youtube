# GitHub 토큰 노출 경고 조사 — 2026-11-06

## 결과

[Secret scanning 경고 #2](https://github.com/Almondshin/momo_youtube/security/secret-scanning/2)는 **오탐(false positive)**으로 확인하고 해결 처리했다. 처리 후 열린 secret-scanning 경고는 0건이다.

- 감지 분류: OpenVSX Access Token, validity=unknown.
- 위치: `momo/episodes/ep12/manifest.json`, 커밋 `b9e3dded11395b142b806e05062575b0e3d1d1ed`, 당시 268행.
- 실제 용도: `notes.korean_companion.full_song.selected_extension_id`에 저장한 **공개 Suno 음원 UUID**.
- 동일 값의 출처를 공식 `audio-extensions-create` 응답의 `clip_ids[1]`, `audio-wait` 응답의 `clips[1].id`와 `song_url`, 전체곡 `concat_clip_ids`에서 대조했다. 해당 근거는 `episodes/ep12/korean/chant_full/`의 생성·완료 응답에 있다.
- GitHub의 `publicly_leaked=true` 표시를 실제 자격증명의 유효성 확인으로 해석하지 않았다. 공개 저장소에서 찾은 값의 출처와 용도를 조사했다.
- GitHub 경고에 출처를 설명하는 resolution_comment를 남기고 `resolved / false_positive`로 변경했다. 감지 기능을 끄거나 유형 전체를 예외 처리하지 않았다.

## 추가 점검 범위

- 로컬에서 접근 가능한 Git refs 전체의 2 MB 이하 비바이너리 blob **910개** 검사.
- 현재 로컬 YouTube client secret·refresh token 3개 값의 정확 일치 검색과 Google OAuth·GitHub 토큰·개인키의 명확한 형식 검색: **발견 0**.
- 바이너리 blob 456개와 2 MB 초과 blob 2개는 이 텍스트 검사에서 제외했다. 모든 서비스의 모든 과거 비밀정보가 없다고 보증하는 전수 검사는 아니다.
- `momo/.secrets/`, `client_secret*.json`, `*.token.json`은 Git 제외 규칙에 있고 추적 파일 목록에 해당 비밀 파일이 없음을 확인했다.
- 원본 경고 API 응답은 `.secrets/security-audit-20261106/`에 권한 600으로 보관했다. 실제 비밀값을 채팅이나 이 문서에 쓰지 않았다.

## 후속 제작

이 경고는 인증 토큰이 아니므로 정상 YouTube/Suno 인증을 교체할 근거는 없었다. 음원 UUID는 생성물 복원과 제작 이력을 위한 데이터로 유지한다. 향후 유사 경고도 UUID 형식만으로 오탐 처리하지 않고 공식 생성 응답과 대조한다.

GitHub API의 false_positive 해결 방식: https://docs.github.com/en/rest/secret-scanning/secret-scanning#update-a-secret-scanning-alert
