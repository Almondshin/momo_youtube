# YouTube 업로드 설정

`upload.py`(세션) 와 GitHub Action `momo-publish` 가 YouTube Data API v3 로 업로드하려면 한 번 설정이 필요하다.

```
Google Cloud 프로젝트 ─ YouTube Data API v3 사용
        │
        ├─ OAuth 동의 화면 (외부, 프로덕션 게시)
        └─ OAuth 클라이언트 (데스크톱 앱) → client_id / client_secret
                 │
   로컬 PC: youtube_auth.py (채널마다 브라우저 로그인) → refresh token
                 │
   비밀값 보관: GitHub 저장소 Secrets (Action)  /  Claude Code 클라우드 환경변수 (세션)
```

> 비밀값(client_secret, refresh token)은 **채팅에 붙여넣지 않는다**, **커밋하지 않는다**.
> `.gitignore` 가 `momo/.secrets/`, `client_secret*.json`, `*.token.json` 을 막고 있고,
> upload.py·doctor.py 는 값이 있는지만 확인하고 출력하지 않는다.

## 1. Google Cloud 프로젝트와 API

1. <https://console.cloud.google.com/> → 프로젝트 만들기 (예: `momo-uploader`).
2. API 및 서비스 → 라이브러리 → **YouTube Data API v3** → 사용.

## 2. OAuth 동의 화면

콘솔 메뉴 이름은 "OAuth 동의 화면" 또는 새 화면의 "Google 인증 플랫폼(Google Auth Platform)"(브랜딩 / 대상 / 데이터 액세스).

1. 사용자 유형: **외부(External)**. 앱 이름, 지원 이메일, 개발자 연락처 입력.
2. 범위(데이터 액세스): `https://www.googleapis.com/auth/youtube.upload`, `https://www.googleapis.com/auth/youtube`
   (후자는 재생목록 추가용).
3. 테스트 사용자: 채널을 소유·관리하는 본인 구글 계정을 추가.
4. 프로덕션 게시에는 브랜딩의 **앱 이름·지원 이메일·홈페이지 URL·개인정보처리방침 URL** 이 필요하다. 저장소 `docs/` 에
   페이지가 있다 — Settings → Pages → Deploy from a branch → (기본 브랜치) `/docs` → Save 후:
   홈페이지 `https://almondshin.github.io/momo_youtube/`, 개인정보처리방침 `…/privacy.html`, 서비스 약관 `…/terms.html`,
   승인된 도메인 `almondshin.github.io`. **로고는 올리지 않는다** (로고가 있으면 게시 전에 인증 심사가 필요).
5. **게시 상태를 "프로덕션(In production)"으로 바꾼다.** "테스트(Testing)" 상태 앱의 refresh token 은
   **7일 뒤 만료**되어 그 뒤 업로드가 `invalid_grant` 로 실패한다.
   - 민감한 범위라서 Google 검증을 요구하는 안내가 뜰 수 있다. 본인만 쓰는 앱은 검증 없이도 쓸 수 있고,
     로그인 때 "Google 에서 확인하지 않은 앱" 화면이 나오면 고급 → (앱 이름)(으)로 이동을 누른다
     (미검증 앱은 사용자 100명 한도 — 이 용도에는 충분).

## 3. OAuth 클라이언트 (데스크톱 앱)

사용자 인증 정보(또는 "클라이언트") → 만들기 → OAuth 클라이언트 ID → 애플리케이션 유형 **데스크톱 앱** →
JSON 다운로드 → `client_secret.json`. 저장소 밖이나 `momo/.secrets/` 에 둔다 (둘 다 git 제외).

## 4. refresh token 발급 — 로컬 PC 에서, 채널마다

브라우저 로그인이 필요하므로 Claude Code 클라우드 세션이 아니라 **내 PC** 에서 실행한다.

```bash
pip install -r momo/requirements.txt
python momo/youtube_auth.py --lang en --client-secrets client_secret.json
python momo/youtube_auth.py --lang ko --client-secrets client_secret.json     # KO 가 다른 채널일 때
```

- 브라우저에서 로그인하고 **올릴 채널(브랜드 계정)을 고른 뒤** 권한을 허용한다.
- 결과: `momo/.secrets/youtube_<lang>.json`. 스크립트가 GitHub Secrets 에 넣을 이름을 안내한다.
- 토큰 값을 화면에 보려면 `--print-token` (터미널 기록에 남으니 주의). 파일을 열어 봐도 된다.
- 원격 서버에서: `--no-browser --port 8080` 으로 URL 을 받고, 내 PC 에서 `ssh -L 8080:localhost:8080 <서버>` 후 URL 을 연다.
- EN/KO 를 **같은 채널**에 올리면 한 번만 발급해서 `YOUTUBE_REFRESH_TOKEN` 하나로 쓴다.
- 토큰이 폐기되면(비밀번호 변경, 권한 해제, 오래 미사용, 테스트 상태 7일) 다시 발급하고 Secrets 를 갱신한다.

## 4B. PC 없이 — OAuth Playground 로 refresh token 발급

로컬에 파이썬을 설치하기 어려우면 브라우저만으로 발급할 수 있다 (채널이 하나일 때 권장).

1. 3절 대신 OAuth 클라이언트를 **웹 애플리케이션** 유형으로 만들고, **승인된 리디렉션 URI** 에
   `https://developers.google.com/oauthplayground` 를 정확히 넣는다 (끝에 `/` 없이).
2. <https://developers.google.com/oauthplayground> → 오른쪽 위 ⚙ → **Use your own OAuth credentials** 체크 →
   Client ID / Client secret 입력 → Close. (Access type 은 기본값 Offline 그대로)
3. 왼쪽 Step 1 아래 입력칸 "Input your own scopes" 에
   `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube` → **Authorize APIs**.
4. 채널을 가진 구글 계정으로 로그인. 채널이 브랜드 계정이면 채널 선택 화면이 나오고, 채널이 계정 자체에 있으면
   선택 화면 없이 넘어간다 (정상). "Google 에서 확인하지 않은 앱" → 고급 → (앱 이름)(으)로 이동 → 권한 두 개 모두 허용.
5. Playground 로 돌아오면 Step 2 → **Exchange authorization code for tokens** → 같은 칸에 **Refresh token** 이 보인다
   (Step 3 으로 넘어가 접혔으면 "Step 2" 제목을 눌러 다시 연다). 이 값을 `YOUTUBE_REFRESH_TOKEN` 으로 쓴다.

자주 나는 오류:

- **403 access_denied** ("앱이 Google 인증 절차를 완료하지 않았습니다"): 동의 화면이 **테스트** 상태인데 로그인한 계정이
  테스트 사용자가 아니다 → 대상(Audience)에서 **앱 게시(프로덕션)** 하거나 테스트 사용자에 그 계정을 추가.
- **redirect_uri_mismatch**: 1번의 리디렉션 URI 가 다르거나, 데스크톱 앱 클라이언트를 넣었다.
- **invalid_client**: Client ID/secret 을 다른 클라이언트 것과 섞었다.

## 5. 비밀값 넣기

| 이름 | 값 | 필요할 때 |
|---|---|---|
| `YOUTUBE_CLIENT_ID` | client_secret.json 의 `client_id` | 업로드 |
| `YOUTUBE_CLIENT_SECRET` | client_secret.json 의 `client_secret` | 업로드 |
| `YOUTUBE_REFRESH_TOKEN_EN` / `YOUTUBE_REFRESH_TOKEN_KO` | 언어별 채널의 refresh token | EN/KO 채널이 다를 때 |
| `YOUTUBE_REFRESH_TOKEN` | 공통 refresh token | 한 채널에 둘 다 올릴 때 (언어별 값이 없으면 이것을 쓴다) |
| `YOUTUBE_API_KEY` | API 키 (사용자 인증 정보 → API 키, YouTube Data API v3 로 제한) | 선택: `analyze_channel.py --backend api` |

- **GitHub Actions** (`momo-publish`): 저장소 Settings → Secrets and variables → Actions → New repository secret.
- **Claude Code 클라우드 세션** (세션에서 `upload.py` 실행): 세션 제목 표시줄의 환경 메뉴 → Edit → 환경변수에 추가.
  새 세션부터 적용된다.
- **로컬**: env 가 없으면 upload.py 가 `momo/.secrets/youtube_<lang>.json` 을 쓴다.

upload.py 가 찾는 순서: `YOUTUBE_CLIENT_ID`·`YOUTUBE_CLIENT_SECRET` + `YOUTUBE_REFRESH_TOKEN_<LANG>` →
`YOUTUBE_REFRESH_TOKEN` → `momo/.secrets/youtube_<lang>.json`.

확인 (값은 출력되지 않는다):

```bash
python momo/doctor.py                                   # 자격증명 env 가 있는지
python momo/upload.py --ep ep02 --lang all --dry-run    # 요청 body 만 출력 (자격증명·네트워크 불필요)
python momo/youtube_check.py                            # 실제로 토큰을 받아 어느 채널에 연결되는지 (업로드 없음)
```

GitHub Secrets 를 넣은 뒤에는 Actions → **momo-youtube-check** → Run workflow (1분, 빌드·업로드 없음)로
채널 이름이 맞는지 먼저 확인하고, 그다음 momo-publish 로 올린다.

## 6. 할당량 (quota)

- 프로젝트당 기본 **10,000 units/일**, 태평양 시간 자정에 초기화. 초과하면 `quotaExceeded` → 다음 날 다시.
- `videos.insert`(업로드)가 가장 비싸다. 오랫동안 **1,600 units**(하루 약 6개)였고, 2025년 12월 개정으로
  약 100 units 로 내려갔다는 보고가 있다. 현재 값은 공식 계산표에서 확인:
  <https://developers.google.com/youtube/v3/determine_quota_cost>.
  `thumbnails.set`·`playlistItems.insert` 는 각 약 50 units.
- 1편 = 업로드 2개(EN/KO) + 썸네일 2 + 재생목록 2. 1,600 기준이면 약 3,400 units → **하루 2편 정도**가 한계다.
- `upload.py --force` 는 새 영상을 또 만들어 할당량을 쓴다 (`youtube.json` 에 video_id 가 있으면 기본은 건너뜀).
- 더 필요하면 Cloud Console 의 할당량 증설 요청(감사와 같은 양식)으로.

## 7. 중요 — 감사 전에는 API 업로드 영상이 비공개로 잠긴다

**2020-07-28 이후 만든 미검증 API 프로젝트**로 `videos.insert` 한 영상은 요청한 공개 상태와 상관없이
**비공개(private)로 잠긴다.** 잠긴 영상은 YouTube Studio 에서도 공개·일부공개로 바꿀 수 없다
(도움말: <https://support.google.com/youtube/answer/7300965>).

선택지:

1. **API 감사(audit) 신청** — <https://support.google.com/youtube/contact/yt_api_form>.
   통과하면 `--privacy public` / 예약 공개(`--publish-at`)가 그대로 동작한다. 신청 전후로 YouTube API 서비스 약관·
   개발자 정책을 지키는지(사용 목적, 데이터 처리) 설명해야 한다.
2. **감사 전까지**: API 업로드는 `private` 으로 올려 **검토용**으로만 쓴다 (업로드·썸네일·재생목록 동작 확인).
   공개본은 YouTube Studio 에서 직접 올린다 — 파일은 `episodes/<ep>/out/<ep>_<lang>.mp4`, `_thumb.jpg`,
   제목·설명·태그는 `episodes/<ep>/README.md`(또는 manifest.upload), 아동용 설정은 아래 8절대로.

감사를 통과한 뒤 권장 순서: `private` 업로드 → Studio 에서 영상·썸네일·아동용 표시 확인 → 공개 또는 예약으로 전환.

## 8. 채널·영상 설정

### 맞춤 썸네일

`thumbnails.set` 은 **인증된 채널**(전화번호 인증, Studio → 설정 → 채널 → 기능 사용 자격)에서만 된다.
안 되면 upload.py 가 경고만 하고 영상은 올라간다 → 인증 후 Studio 에서 `_thumb.jpg` 를 직접 올린다.

### 아동용(made for kids)

- upload.py 는 `status.selfDeclaredMadeForKids = true` 를 **항상** 넣는다 (config 가 false 여도 경고 후 true).
- 채널 기본값도 설정한다: Studio → 설정 → 채널 → 고급 설정 → 시청자층 "예, 아동용으로 설정합니다".
- 아동용 영상에서 꺼지거나 제한되는 것: 댓글, 맞춤 광고(비맞춤 광고만 → 수익 단가가 낮다), 알림 종,
  카드·최종 화면, 미니플레이어, 나중에 볼 동영상·재생목록 저장, 채널 워터마크, 슈퍼챗 등.
- 아동 대상 콘텐츠를 아동용으로 표시하지 않으면 미국 COPPA/FTC 등 법적 책임이 생길 수 있다. 2~5세 대상이므로 항상 아동용.

### 합성·변경 콘텐츠 공개 (`config.youtube.contains_synthetic_media`)

- YouTube 는 **실제처럼 보이는** 합성·변경 콘텐츠(실존 인물·장소·사건처럼 보이는 것)에 공개 표시를 요구한다.
  명백히 비현실적인 애니메이션·판타지는 보통 공개 대상이 아니다.
- 모모 에피소드는 3D 카툰이라 기본값 `false`. 사실적인 사람·실제 장소처럼 보이는 장면이 들어간 편은 `true` 로 바꾼다
  (upload.py 가 `status.containsSyntheticMedia` 를 넣는다). 판단은 최신 정책을 확인해서 편마다 한다:
  <https://support.google.com/youtube/answer/14328491>.

### 수익화 — 대량 생산·반복 콘텐츠 정책

- YouTube 파트너 프로그램은 템플릿으로 찍어낸 듯한 대량 생산·반복 콘텐츠(2025년부터 "inauthentic content")를
  수익 창출 대상에서 뺀다. AI 도구 사용 자체는 금지가 아니다.
- 이 파이프라인은 구조(인트로·아웃트로, 5씬, 챈트)가 매 편 같으므로 **내용은 편마다 의미 있게 새로** 만든다:
  새 주제·새 대본·새 장면 이미지, 단어만 바꾼 재탕 금지, 모음집은 기존 편 재사용이므로 비중을 조절한다.
- 정책: <https://support.google.com/youtube/answer/1311392>.
