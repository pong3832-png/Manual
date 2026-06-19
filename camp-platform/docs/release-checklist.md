# Release Checklist

CheheomMoa를 공개 배포하기 전 확인할 항목입니다.

## How To Use This Checklist

이 체크리스트는 출시를 늦추기 위한 문서가 아니라, 출시 직전에 빠뜨리기 쉬운 항목을 줄이기 위한 QA 게이트입니다.

- P0 항목은 공개 전 통과해야 합니다.
- P1 항목은 출시 직후 바로 보완할 수 있지만, 공개 전에 확인하면 사용자 이탈을 줄입니다.
- P2 항목은 출시 후 안정화 단계에서 처리합니다.
- 크롤링, 배포, 스케줄러 등록, 외부 API 쓰기 작업은 사용자가 직접 실행하거나 명시 승인한 경우에만 진행합니다.

## Launch Decision Gate

아래 조건을 만족하면 방문형 MVP 공개 후보로 봅니다.

- [ ] 최신 순차 크롤 결과가 quality gate까지 완료됨.
- [ ] 성공 플랫폼 비율이 70% 이상임.
- [ ] 좌표 품질이 낮은 경우 지도 가능 수와 위치 미확인 수가 화면에 명확히 표시됨.
- [ ] 특정 플랫폼 open 수가 이전 대비 80% 이상 급락하면 이번 결과를 격리하고 이전 공개 데이터를 보존함.
- [ ] 홈, 탐색, 지도에서 캠페인 목록이 비어 있지 않음.
- [ ] `기타` 카테고리 비중이 첫 화면 경험을 해치지 않음.
- [ ] 마감 지난 캠페인이 open 목록에 남지 않음.
- [ ] 신청 버튼이 실제 원본 캠페인 페이지로 열림.
- [ ] 모바일 폭에서 홈, 탐색, 지도, 상세 모달의 버튼/텍스트가 겹치지 않음.
- [ ] 개인정보처리방침, 이용약관, 문의 링크가 접근 가능함.

공개 보류 조건입니다.

- [ ] 최신 데이터가 없거나 크롤/quality gate가 실패함.
- [ ] 성공 플랫폼 비율이 70% 미만임.
- [ ] 특정 플랫폼 open 수가 급락했는데 이전 공개 데이터 보존 없이 새 결과로 덮어쓰려 함.
- [ ] 홈/탐색에서 대부분의 캠페인이 `기타`로 보임.
- [ ] 신청 버튼 또는 상세 모달이 열리지 않음.
- [ ] 지도 키, Supabase 설정, 인증 리다이렉트 중 하나가 production에서 깨짐.
- [ ] 비밀키, 쿠키, service role key가 public 코드나 문서에 노출됨.

## Current Production Values

현재 운영 배포 기준값입니다.

```text
Production URL: https://camp-platform-liart.vercel.app
Future Custom Domain: https://cheheommoa.com
Android Package Name: com.cheheommoa.app
Contact Email: pong3832@gmail.com
```

Kakao Developers에는 현재 production URL이 이미 JavaScript SDK 도메인으로 등록되어 있습니다. 커스텀 도메인을 나중에 연결하면 `https://cheheommoa.com`도 추가 등록합니다.

## 1. Required Environment

Vercel 프로젝트의 production 환경변수에 아래 값을 설정합니다.

Frontend:

```text
VITE_SUPABASE_URL
VITE_SUPABASE_ANON_KEY
VITE_KAKAO_MAP_APP_KEY
VITE_PUBLIC_SITE_NAME=CheheomMoa
VITE_PUBLIC_SITE_URL=https://camp-platform-liart.vercel.app
VITE_PUBLIC_CONTACT_EMAIL=pong3832@gmail.com
VITE_PUBLIC_OPERATOR_NAME=CheheomMoa
```

Crawler and operations:

```text
SUPABASE_SERVICE_ROLE_KEY
KAKAO_REST_API_KEY
MRBLOG_COOKIE or MRBLOG_LOGIN_ID / MRBLOG_LOGIN_PASSWORD
REVU_AUTHORIZATION or REVU_LOGIN_ID / REVU_LOGIN_PASSWORD
```

Optional crawler headers:

```text
REVIEWNOTE_COOKIE
REVIEWPLACE_COOKIE
DINNERQUEEN_COOKIE
GANGNAM_COOKIE
POPOMON_COOKIE
```

Coupang Partners API 값은 서버/로컬 작업 환경에만 설정합니다. 절대 `VITE_` 접두사를 붙이지 않습니다.

## 2. External Console Registration

Kakao Developers:

- 앱 > 플랫폼 > Web 플랫폼 사이트 도메인에 `https://camp-platform-liart.vercel.app`이 등록되어 있는지 확인합니다.
- 로컬 지도 테스트가 필요하면 `http://localhost:5173`도 함께 등록합니다.
- JavaScript 키가 Vercel의 `VITE_KAKAO_MAP_APP_KEY`와 같은지 확인합니다.

Supabase Auth:

- Authentication > URL Configuration > Site URL을 `https://camp-platform-liart.vercel.app`으로 설정합니다.
- Redirect URLs에 아래 값을 추가합니다.

```text
https://camp-platform-liart.vercel.app
https://camp-platform-liart.vercel.app/*
http://localhost:5173
http://localhost:5173/*
```

이 설정을 하지 않으면 배포 도메인에서 로그인, 회원가입 이메일 확인, 비밀번호 재설정 리다이렉트가 실패할 수 있습니다.

## 3. Preflight

배포 직전 로컬에서 실행합니다.

```powershell
npm run lint
npm run build
npm run ops:preflight
npm run crawl:check
```

`npm run crawl:check`가 `WARN`이어도 공개는 가능하지만, 지도 품질을 위해 좌표 완성률과 주소 완성률을 먼저 확인합니다. 좌표가 없는 캠페인은 지도에 표시되지 않으므로 홈/탐색 화면 품질과 별도로 지도 품질을 봐야 합니다.

## 3-1. Data QA

순차 크롤이 끝난 뒤 확인합니다.

```powershell
Get-Content -Raw -Encoding UTF8 "C:\Users\itwill\자동화 공부\camp-platform\public\crawl-status.json"
Get-Content -Raw -Encoding UTF8 "C:\Users\itwill\자동화 공부\camp-platform\public\data-quality.json"
Get-Content -Raw -Encoding UTF8 "C:\Users\itwill\자동화 공부\camp-platform\.cache\crawl-artifacts\quality-gate.json"
```

요약 확인:

```powershell
$status = Get-Content -Raw -Encoding UTF8 "C:\Users\itwill\자동화 공부\camp-platform\public\crawl-status.json" | ConvertFrom-Json
$gate = Get-Content -Raw -Encoding UTF8 "C:\Users\itwill\자동화 공부\camp-platform\.cache\crawl-artifacts\quality-gate.json" | ConvertFrom-Json
$status | Select-Object status,startedAt,completedAt,successfulPlatforms,failedPlatforms
$gate | Select-Object status,canPublish,checkedAt
```

확인 기준:

- `crawl-status.json`의 `status`가 `completed`인지 확인합니다.
- quality gate의 `canPublish`가 true인지 확인합니다.
- `successfulPlatforms` 또는 quality gate의 성공 플랫폼 비율이 70% 이상인지 확인합니다.
- 실패 플랫폼이 있어도 어떤 플랫폼인지 기록하고, 홈/탐색의 핵심 카테고리 경험이 유지되는지 확인합니다.
- `data-quality.json`에서 좌표/주소 품질을 확인하고, 지도 화면의 커버리지/위치 미확인 표시가 실제 수치와 맞는지 확인합니다.
- `기타` 카테고리가 첫 화면과 주요 전체보기 흐름을 지배하지 않는지 확인합니다.

## 3-2. Product QA

로컬 또는 preview URL에서 확인합니다.

- 홈:
  - 전체 캠페인 보기 버튼이 탐색으로 이동합니다.
  - 지도 보기 버튼이 지도 화면으로 이동합니다.
  - 카테고리/지역 전체보기 버튼이 해당 조건의 탐색 결과로 이동합니다.
  - 전체 캠페인 수, 통합 플랫폼 수, 최근 확인 기준이 보입니다.

- 탐색:
  - 검색어 입력, 시도, 시군구, 카테고리, 정렬, 빠른 탐색이 동작합니다.
  - 카테고리 칩에 개수가 표시됩니다.
  - 현재 조건으로 지도 보기 버튼이 지도 화면으로 이동합니다.
  - 조건 초기화 버튼이 검색/필터/정렬을 기본값으로 되돌립니다.

- 지도:
  - 지도 가능 수, 위치 미확인 수, 좌표 커버리지가 표시됩니다.
  - 카테고리와 지역 필터가 지도 결과에 반영됩니다.
  - 마커 클릭 시 오른쪽 목록과 선택 카드가 갱신됩니다.
  - 좌표 없는 캠페인은 지도에는 없지만 탐색에서 확인할 수 있다는 흐름이 유지됩니다.

- 카드/상세:
  - 카드에서 제목, 지역, 카테고리, 혜택, D-day, 모집/신청, 경쟁률, 신청 버튼이 보입니다.
  - 카드 클릭 시 상세 모달이 열립니다.
  - 신청 버튼은 원본 캠페인 페이지를 새 창으로 엽니다.
  - 즐겨찾기는 로그인 전에는 로그인 안내로 이어집니다.

- 모바일:
  - 390px 폭에서 홈, 탐색, 지도, 상세 모달 버튼과 텍스트가 겹치지 않습니다.
  - 하단 내비게이션이 주요 버튼을 가리지 않습니다.

## 4. Supabase Database Patch

회원가입 시 입력한 이름과 블로그 URL을 `profiles`에 저장하려면 운영 Supabase SQL Editor에서 아래 파일의 SQL을 한 번 실행합니다.

```text
database/supabase/migrations/20260505_profile_signup_metadata.sql
```

## 5. Data Freshness

- `public/campaigns.json`은 Supabase 장애 또는 빈 응답 시 사용하는 fallback 데이터입니다.
- 정식 공개 전 `public/campaigns.json`의 `generatedAt`, `updatedAt`, 또는 캠페인별 `crawledAt`이 24시간 이내인지 확인합니다.
- 크롤 중 일부 플랫폼이 실패해도 성공한 플랫폼의 최신 데이터는 보존되어야 합니다.
- 크롤러는 각 플랫폼 종료 직후 Kakao geocode를 시도합니다. 크롤이 중간에 멈춰도 이미 성공한 플랫폼의 좌표 보강 결과가 남아야 합니다.

## 6. Public UX

- 일반 사용자 내비게이션에서 `운영` 탭은 숨깁니다.
- 운영 화면은 `?ops=1` 또는 `localStorage.showOps=1`일 때만 노출합니다.
- Supabase가 비어 있거나 일시 실패해도 사용자는 공개 fallback 데이터를 볼 수 있어야 합니다.
- 회원가입 시 이름과 블로그 URL이 `profiles`에 저장되는지 확인합니다.
- 개인정보처리방침, 이용약관, 문의 링크가 데스크톱과 모바일에서 접근 가능해야 합니다.
- 광고 문의 배너가 placeholder 주소로 연결되지 않아야 합니다.

## 7. Post-Deploy Smoke Test

배포 URL에서 아래 경로를 확인합니다.

```text
/
/?legal=privacy
/?legal=terms
/?contact=1
/?ops=1
/robots.txt
/sitemap.xml
/site.webmanifest
```

SEO/PWA 확인:

- 브라우저 탭 제목이 `CheheomMoa | 전국 체험단 캠페인 모음`으로 표시됩니다.
- `site.webmanifest`가 200으로 열리고 `display`가 `standalone`입니다.
- `robots.txt`에서 production sitemap을 가리킵니다.
- 공유 미리보기용 `og:title`, `og:description`, `og:url`, `og:locale`이 HTML에 있습니다.
- 모바일에서 홈 화면 추가 시 앱 이름이 `CheheomMoa`로 표시됩니다.

화면별 확인:

- 홈: 오늘 마감, 저경쟁, 최신 캠페인 섹션이 표시됩니다.
- 탐색: 검색, 지역, 카테고리, 정렬 필터가 동작합니다.
- 지도: Kakao 도메인 설정이 맞고, 좌표 없는 캠페인은 제외됩니다.
- 현황/마이: 로그인 전 안내와 로그인 모달이 정상입니다.
- 회원가입: 가입 직후 또는 이메일 확인 후 이름/블로그 URL이 마이페이지에 표시됩니다.
