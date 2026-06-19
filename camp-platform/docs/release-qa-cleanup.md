# Release QA And Cleanup

## 목적

정식 출시 전 확인은 코드 검증, 로그인 후 핵심 흐름, 운영 데이터 안전성, 폴더 정리 순서로 나눈다. 삭제, 배포, 크롤, Supabase 직접 쓰기, 스케줄러 등록은 별도 승인 없이는 실행하지 않는다.

## 현재 QA 단계

### 1. 코드 게이트

- `npm.cmd run lint`
- `npm.cmd run build`
- `git diff --check`
- `npm.cmd run qa:smoke`

통과해야 다음 단계로 넘어간다.

### 2. 로그인 전 화면

- 홈 캠페인 노출
- 탐색 검색/카테고리/지역 반영
- 지도 첫 진입 확대 안내
- 현황/마이 로그인 안내
- 개인정보/약관/문의 모달

로컬 샌드박스처럼 외부 네트워크가 막힌 환경에서는 다음처럼 외부 리소스 차단 오류만 허용한다.

```powershell
$env:QA_ALLOW_NETWORK_DENIED="1"
npm.cmd run qa:smoke
Remove-Item Env:\QA_ALLOW_NETWORK_DENIED
```

배포 URL 또는 실제 사용자 환경 QA에서는 `QA_ALLOW_NETWORK_DENIED`를 켜지 않는다.

### 3. 로그인 후 핵심 흐름

테스트 계정 또는 사용자가 승인한 실제 계정으로만 확인한다.

- 마이: 이름과 대표 채널 주소 저장
- 마이: 저장 후 프로필 완성도와 사이드바 이름 반영
- 탐색/상세: 신청 버튼 클릭 시 `지원 페이지 열림`으로 기록
- 현황: `지원완료`, `선정`, `리뷰 작성중`, `완료`, `미선정` 상태 변경
- 현황: 메모와 리뷰 URL 저장
- 현황: 즐겨찾기 해제
- 로그아웃 후 보호 화면으로 복귀

반복 QA는 테스트 계정 환경변수를 설정한 뒤 실행한다. 비밀번호는 문서나 Git에 남기지 않는다.

```powershell
$env:QA_EMAIL="test@example.com"
$env:QA_PASSWORD="test-password"
$env:QA_PROFILE_NAME="QA 자동검증"
$env:QA_PROFILE_BLOG_URL="https://blog.naver.com/cheheommoa-qa"
npm.cmd run qa:auth
Remove-Item Env:\QA_EMAIL, Env:\QA_PASSWORD, Env:\QA_PROFILE_NAME, Env:\QA_PROFILE_BLOG_URL -ErrorAction SilentlyContinue
```

`qa:auth`는 원문 플랫폼으로 이동하는 `window.open`을 차단하고 앱 내부 저장 흐름만 확인한다.

### 4. 운영 데이터 안전성

- 운영 DB에 테스트 데이터가 남는지 확인한다.
- 테스트 계정이 아니라 실제 계정으로 확인했다면 변경한 프로필/지원 상태를 사용자가 의도한 상태로 유지한다.
- 임의로 Supabase rows를 삭제하지 않는다.

## 폴더 정리 기준

### 보존

- `src/`
- `public/`
- `scripts/`
- `database/`
- `docs/`
- `package.json`, `package-lock.json`
- `AGENTS.md`, `README.md`, `.env.example`

### 커밋 후보

- `src/pages/ProfilePage.jsx`
- `src/pages/StatusPage.jsx`
- `src/app/App.jsx`
- `src/app/App.css`
- `src/features/user/hooks/useUserActivity.js`
- 광고/PWA/Supabase migration 관련 신규 파일
- `docs/work-log.md`
- 이 문서

### 정리 후보

아래 항목은 대부분 재생성 가능하거나 로컬 실행 로그다. 실제 삭제 전 사용자 승인이 필요하다.

- `dist/`
- `.cache/`
- `logs/`
- 루트의 `*.log`
- `.vercel/`

### 주의 후보

- `.env`는 비밀 파일이므로 읽기/출력/커밋 금지.
- `public/campaigns.json`, `public/crawl-status.json`, `public/data-quality.json`은 런타임 데이터라 임의 되돌림 금지.
- `AI identity prompt.md`는 현재 변경 상태지만 이번 작업 범위 밖이다.

## 출시 전 의사결정 순서

1. 코드 게이트 통과
2. 로그인 후 QA를 테스트 계정으로 수행
3. QA 결과를 `docs/work-log.md`에 기록
4. 정리 후보 삭제/보존을 사용자 승인으로 결정
5. 커밋 후보만 선별
6. 사용자 승인 후 배포
