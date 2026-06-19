# AGENTS.md

마지막 갱신: 2026-05-29 KST

이 문서는 `camp-platform` 저장소에서 Codex/Claude 같은 AI 코딩 에이전트가 다음 세션에 바로 이어서 작업하기 위한 실행 지침서다. 내용은 현재 파일, 코드, 설정, 스크립트 기준으로 작성했다. 확인하지 못했거나 코드로 단정할 수 없는 내용은 `확인 필요`로 표시한다.

## Project Overview

`camp-platform`은 여러 한국 체험단 캠페인을 모아 검색, 탐색, 지도 조회, 즐겨찾기, 신청 현황 관리를 제공하는 React/Vite 웹앱이다.

프론트엔드는 `src/main.jsx`에서 시작해 `src/app/App.jsx`가 전체 탭, 필터, 검색, 모달, 인증 상태를 조립한다. 캠페인 데이터는 Supabase가 설정되어 있으면 Supabase를 우선 조회하고, 없거나 비어 있으면 `public/campaigns.json`을 fallback으로 사용한다. 크롤러는 `scripts/crawler/crawl.cjs` 한 파일에 주요 플랫폼 수집, 상세 페이지 보강, Kakao 좌표 보강, 품질 게이트, JSON 발행, Supabase upsert 로직을 포함한다.

주요 화면은 홈, 지도, 탐색, 현황, 프로필, 운영 탭이다. `ops` 운영 탭은 `?ops=1` 또는 `localStorage.showOps=1`일 때만 보인다. 지도 화면은 Kakao Maps SDK를 사용하며, 좌표가 없거나 `coordinateSource`가 `unresolved`인 캠페인은 지도 표시에서 제외한다.

현재 패키지 이름은 `cheheommoa`이고 Node 엔진은 `20.x`다. Python, Docker, Make 기반 실행 진입점은 추적 파일 기준으로 발견되지 않았다.

## Repository Map

| 경로 | 역할 | 주의 |
| --- | --- | --- |
| `README.md` | 짧은 프로젝트 소개, 기본 명령, Source Of Truth 목록 | `AGENTS.md`를 작업 규칙으로 참조함 |
| `AGENTS.md` | AI 에이전트 작업 지침 | 이 파일을 먼저 읽고 시작 |
| `package.json` | npm scripts, 의존성, Node 엔진 | 실제 명령은 여기를 기준으로 함 |
| `package-lock.json` | npm lockfile | 의존성 변경 없으면 건드리지 말 것 |
| `.env.example` | 환경변수 템플릿 | 실제 비밀값 금지 |
| `.env` | 로컬 비밀키/쿠키/토큰 | git ignore 대상, 값 노출 금지 |
| `.gitignore` | `.env`, `node_modules`, `dist`, `.next`, `.cache`, `logs`, `*.log`, `.vercel` 제외 | 현재 `AGENTS.md`는 추적 가능하도록 ignore에서 제외됨 |
| `.vercelignore` | Vercel 업로드 제외 목록 | `docs/research`, 로그, env 제외 |
| `index.html` | Vite HTML 엔트리, SEO 메타, `#root` | 텍스트 인코딩 확인 필요 시 UTF-8로 읽기 |
| `vite.config.js` | Vite + React 플러그인 | 단순 설정 |
| `eslint.config.js` | ESLint flat config | `dist` ignore, JS/JSX lint |
| `vercel.json` | Vercel `framework=nextjs`, `outputDirectory=null`, build env `NODE_VERSION=20` 지정 | Vite 시절 `dist` output 설정이 남으면 Next 배포 실패 |
| `src/` | 프론트엔드 소스 | React/Vite/ESM |
| `src/app/` | 앱 셸, 전역 CSS, 컴팩트 UI CSS | `App.jsx`가 전체 상태 조립 |
| `src/pages/` | `HomePage`, `MapPage`, `ExplorePage`, `StatusPage`, `ProfilePage`, `OpsPage` | 탭 단위 UI |
| `src/features/` | campaigns, auth, user, map, ads 기능 코드 | 도메인 로직은 feature별로 유지 |
| `src/shared/` | Supabase API, 플랫폼/사이트 config, 공용 컴포넌트/자산 | 설정 변경 시 영향 큼 |
| `src/legacy/` | legacy Supabase client | 현재 주 경로는 `src/shared/api/supabase.js` |
| `public/` | 정적 자산과 런타임 JSON | 크롤러/광고 스크립트가 일부 파일을 갱신 |
| `public/campaigns.json` | 캠페인 fallback 및 public snapshot | 크롤러가 덮어씀, 수동 편집 주의 |
| `public/crawl-status.json` | 최신 크롤 실행 상태 | 크롤러가 덮어씀 |
| `public/data-quality.json` | 플랫폼별 데이터 품질 리포트 | 크롤러가 덮어씀 |
| `public/crawl-check.json` | `npm run crawl:check` 결과 | check 명령도 이 파일을 씀 |
| `public/ads.json` | 광고 슬롯 데이터 | Coupang sync가 덮어쓸 수 있음 |
| `scripts/crawler/` | 크롤러와 크롤 검증 스크립트 | 외부 API, 파일 쓰기, DB 쓰기 가능 |
| `scripts/ops/` | Windows PowerShell 운영/스케줄러 스크립트 | 스케줄러 등록은 승인 필요 |
| `scripts/ads/` | Coupang Partners 광고 동기화 | 외부 API 호출 및 `public/ads.json` 쓰기 |
| `database/supabase/` | Supabase schema/migrations | 운영 DB 적용은 승인 필요 |
| `docs/` | 구조, 프론트, 크롤러, 릴리즈, 제품, 연구 문서 | 일부 한국어가 콘솔에서 깨져 보일 수 있음 |
| `docs/work-log.md` | 날짜별 짧은 작업 로그와 다음 세션 인계 | 장문 요약 금지, 핵심 변경/검증/다음 작업만 기록 |
| `docs/crawler/new-source-intake.md` | 새 체험단 사이트/배송형/기자단 추가 전 사용자 입력 템플릿 | 새 크롤링 소스 구현 전 먼저 확인 |
| `marketing/` | 마케팅, 출시 메시지, 홍보 채널, SEO/콘텐츠 전략 | 런타임 코드와 분리하고 채널별 실험/문구는 이 폴더에서 관리 |
| `docs/research/crawl-source-snippets/` | 플랫폼 HTML/응답 샘플 | 대용량 파일 있음, 필요한 파일만 읽기 |
| `.cache/` | 크롤러 캐시, geocode cache, artifacts | git ignore, 삭제 전 승인 |
| `logs/` | `run-crawl.ps1` 크롤 로그 | git ignore, 삭제 전 승인 |
| `dist/` | `npm run build` 산출물 | git ignore, 재생성 가능 |
| `.next/` | Next.js build 산출물 | git ignore, 재생성 가능 |
| `node_modules/` | npm 의존성 | git ignore |
| `dev-server*.log`, `vite-dev.*.log` | 로컬 dev 서버 로그 | git ignore 패턴 대상 |
| `긴대화.txt`, `포포몬 리스폰스.txt` | 사용자 제공 분석 자료 | untracked, 삭제 금지 |

## Primary Entry Points

| 진입점 | 실행 방식 | 역할 |
| --- | --- | --- |
| `index.html` | Vite가 로드 | 브라우저 HTML 엔트리 |
| `src/main.jsx` | Vite module script | React root 생성 |
| `src/app/App.jsx` | React lazy pages | 전체 앱 셸, 라우트성 탭, 필터, 모달, Supabase user actions |
| `src/features/campaigns/hooks/useCampaigns.js` | App에서 호출 | Supabase 우선, `/campaigns.json` fallback, 5분 background refresh |
| `src/features/campaigns/lib/campaigns.js` | hooks/pages/components에서 사용 | 캠페인 정규화, 지역/좌표/중복/상태/필터 도메인 로직 |
| `src/pages/MapPage.jsx` | App tab | Kakao 지도, 좌표 필터, 클러스터, 지역/도시 필터 |
| `scripts/crawler/crawl.cjs` | `npm run crawl` | 전체 크롤러 main, 외부 요청, JSON 발행, Supabase sync |
| `scripts/crawler/backfill-dinnerqueen-provisions.cjs` | `npm run crawl:dinnerqueen:provision-backfill` | 디너의여왕 `point` backfill, public snapshot 쓰기, 기존 public `point`의 Supabase 동기화 보조. 기본 dry-run |
| `scripts/crawler/check-crawl.cjs` | `npm run crawl:check` | 크롤 결과 검증, `public/crawl-check.json` 작성 |
| `scripts/ads/sync-coupang-ads.cjs` | `npm run ads:*` | Coupang 광고 env check, dry-run, sync |
| `scripts/ops/run-crawl.ps1` | `npm run ops:crawl` | mutex/프로세스 중복 방지, preflight, 로그 기록 후 crawler 실행 |
| `scripts/ops/test-production-readiness.ps1` | `npm run ops:preflight` | env, node/npm, schema, snapshot, logs, scheduler 상태 점검 |
| `scripts/ops/register-crawl-task.ps1` | 직접 실행 | Windows `schtasks.exe`로 크롤 작업 등록 |
| `scripts/ops/check-crawl-task.ps1` | `npm run ops:check-task` | Windows scheduled task 조회 |
| `scripts/ops/check-supabase.cjs` | preflight option에서 호출 | Supabase `platforms`, `campaigns` 접근 확인 |

## Common Commands

프로젝트 루트:

```powershell
Set-Location "C:\Users\itwill\자동화 공부\camp-platform"
```

일반 설치/실행:

```powershell
npm install
npm run dev
npm run preview
```

로컬 Kakao 지도 확인은 5173 포트를 기본으로 쓴다:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

`npm run preview`는 보통 `npm run build` 이후 `dist/`를 확인할 때 쓴다.

문법 검사/빌드:

```powershell
npm run lint
npm run build
npm run qa:smoke
npm run qa:auth
```

개별 Node 스크립트 문법 확인:

```powershell
node --check scripts/crawler/crawl.cjs
node --check scripts/crawler/check-crawl.cjs
node --check scripts/ads/sync-coupang-ads.cjs
node --check scripts/ops/check-supabase.cjs
```

크롤 결과 확인:

```powershell
npm run crawl:check
```

주의: `crawl:check`는 읽기 전용이 아니다. `public/crawl-check.json`을 갱신하고, 실패 시 exit code `1`, 경고 시 exit code `2`를 설정한다.

운영 상태 점검:

```powershell
npm run ops:preflight
npm run ops:check-task
```

Coupang 광고 env 확인:

```powershell
npm run ads:check:coupang
```

Coupang 광고 dry-run:

```powershell
npm run ads:sync:coupang -- --dry-run
```

로그인/세션 저장:

- 별도 npm 로그인 명령은 없다.
- 프론트 로그인은 Supabase Auth를 브라우저에서 사용한다.
- 크롤러는 `MRBLOG_LOGIN_ID`/`MRBLOG_LOGIN_PASSWORD`, `REVU_LOGIN_ID`/`REVU_LOGIN_PASSWORD` 또는 쿠키/토큰 환경변수를 사용할 수 있다.
- 코드상 세션/토큰 캐시 경로가 존재한다: `.cache/mrblog-storage-state.json`, `.cache/revu-auth-token.json`. 현재 파일 존재 여부는 실행 시점에 확인할 것.

로그인 QA:

- `npm run qa:auth`는 실제 Supabase Auth에 로그인하고 `profiles`, `applications`, `ad_events`에 테스트 데이터를 쓸 수 있다. 테스트 계정으로만 실행한다.
- `QA_EMAIL`, `QA_PASSWORD`는 PowerShell env로만 주입하고 문서/채팅/커밋에 남기지 않는다.
- `qa:auth` 실행 후 `Remove-Item Env:\QA_EMAIL, Env:\QA_PASSWORD, Env:\QA_ALLOW_NETWORK_DENIED -ErrorAction SilentlyContinue`로 현재 셸 env를 정리한다.
- 로컬 sandbox에서 외부 요청 차단이 진단을 방해할 때만 `QA_ALLOW_NETWORK_DENIED=1`을 쓴다. 배포 URL QA에서는 켜지 않는다.

테스트:

- `package.json`에 `test` script 없음.
- `rg` 기준 test runner 설정 또는 test file은 발견되지 않음.
- 테스트 프레임워크 도입 여부는 확인 필요.

위험 명령은 아래 Safety Rules의 승인 조건을 따른다.

## Environment Variables

값은 문서나 채팅에 쓰지 말고 변수명만 다룬다. `.env.example`은 템플릿이고 `.env`는 비밀 파일이다.

### Frontend

| 변수 | 용도 | 필수 여부 |
| --- | --- | --- |
| `VITE_SUPABASE_URL` | 프론트 Supabase URL | 인증/DB 기능에는 필요, 없으면 disabled client/fallback |
| `VITE_SUPABASE_ANON_KEY` | 프론트 Supabase anon key | 인증/DB 기능에는 필요 |
| `VITE_CAMPAIGN_DB_REFRESH_ENABLED` | `1`/`true`면 캠페인 목록을 Supabase에서 읽고 주기 refresh한다. 기본 `0`은 `/campaigns.json` 정적 snapshot 우선 | 선택, Supabase egress 절감용 |
| `VITE_KAKAO_MAP_APP_KEY` | Kakao Maps JavaScript SDK | 지도 기능에는 필요 |
| `VITE_PUBLIC_SITE_NAME` | 사이트명 | 선택 |
| `VITE_PUBLIC_SITE_URL` | canonical/public URL | 선택, 없으면 browser origin fallback |
| `VITE_PUBLIC_CONTACT_EMAIL` | 문의 mailto/legal copy | 선택, 없으면 안내 문구 표시 |
| `VITE_PUBLIC_OPERATOR_NAME` | 운영자명/legal copy | 선택 |

### Crawler And Supabase

| 변수 | 용도 | 필수 여부 |
| --- | --- | --- |
| `SUPABASE_URL` | crawler/ops Supabase URL 대체 키 | 선택, `VITE_SUPABASE_URL`도 사용 가능 |
| `SUPABASE_SERVICE_ROLE_KEY` | crawler Supabase upsert/RPC/update | DB sync에는 필요, 없으면 DB upsert skip |
| `SUPABASE_BATCH_SIZE` | Supabase upsert batch size | 선택 |
| `SUPABASE_OPERATION_ATTEMPTS` | Supabase retry 횟수 | 선택 |
| `SUPABASE_RETRY_DELAY_MS` | Supabase retry delay | 선택 |
| `KAKAO_REST_API_KEY` | Kakao address/keyword geocoding | 좌표 보강에는 필요, 없으면 geocoding skip |
| `KAKAO_GEOCODE_CONCURRENCY` | geocode 병렬 수 | 선택 |
| `KAKAO_GEOCODE_BATCH_DELAY_MS` | geocode batch delay | 선택, `.env.example`에는 없음 |
| `CRAWL_ONLY` | 특정 platform만 실행 | 선택, 예: `popomon` |
| `DINNERQUEEN_LIST_SCOPE` | 디너의여왕 목록 범위 제한. `delivery`면 배송형만, `all`이면 전체 목록만, 미지정이면 전체+배송형 | 선택, 배송형 파서 검증용 |
| `CRAWLER_TIMEOUT_MS` | crawler timeout | 선택 |
| `CRAWLER_ARTIFACT_DIR` | artifacts 출력 경로 | 선택, 기본 `.cache/crawl-artifacts` |
| `CRAWLER_HEADLESS` | Playwright rendered fetch headless 제어 | 선택, `0`이면 visible |

### Crawler Quality And Lifecycle

| 변수 | 용도 | 필수 여부 |
| --- | --- | --- |
| `QUALITY_GATE_MODE` | `early`, `warn`, disabled류 모드 | 선택 |
| `QUALITY_GATE_MIN_COORDINATE_PCT` | fresh 좌표 하드 기준 | 선택 |
| `QUALITY_GATE_WARN_COORDINATE_PCT` | 좌표 경고 기준 | 선택 |
| `QUALITY_GATE_WARN_ADDRESS_PCT` | 주소 경고 기준 | 선택 |
| `QUALITY_GATE_MIN_COORDINATE_SAMPLE` | 좌표 gate 최소 샘플 | 선택 |
| `QUALITY_GATE_MAX_PLATFORM_DROP_PCT` | 플랫폼 count drop 기준 | 선택 |
| `QUALITY_GATE_MIN_PLATFORM_BASELINE` | 플랫폼 baseline 기준 | 선택 |
| `CAMPAIGN_STALE_WARN_DAYS` | preserved stale 표시 기준 | 선택 |
| `CAMPAIGN_STALE_HIDE_DAYS` | 오래된 preserved 숨김 기준 | 선택 |

### Platform Auth/Cookies

| 변수 | 용도 | 필수 여부 |
| --- | --- | --- |
| `REVIEWNOTE_COOKIE` | Reviewnote 요청 쿠키 | 선택 |
| `REVIEWNOTE_FORBIDDEN_COOLDOWN_HOURS` | Reviewnote 403 이후 재시도 cooldown 시간. 기본 12 | 선택 |
| `REVIEWNOTE_IGNORE_COOLDOWN` | Reviewnote cooldown 무시 재검증 플래그. 임시 수동 확인용 | 선택 |
| `REVIEWPLACE_COOKIE` | Reviewplace 요청 쿠키 | 선택 |
| `DINNERQUEEN_COOKIE` | Dinnerqueen 요청 쿠키 | 선택 |
| `GANGNAM_COOKIE` | Gangnam 요청 쿠키 | 선택 |
| `POPOMON_COOKIE` | Popomon 요청 쿠키 | 선택 |
| `MRBLOG_COOKIE` | Mrblog 쿠키 | 선택 |
| `MRBLOG_X_CSRF_TOKEN` | Mrblog CSRF | 선택 |
| `MRBLOG_LOGIN_ID`, `MRBLOG_EMAIL`, `MRBLOG_USERNAME` | Mrblog login id aliases | 선택 |
| `MRBLOG_LOGIN_PASSWORD`, `MRBLOG_PASSWORD` | Mrblog password aliases | 선택 |
| `MRBLOG_HEADLESS` | Mrblog Playwright headless 제어 | 선택 |
| `REVU_AUTHORIZATION` | Revu authorization | 선택 |
| `REVU_COOKIE` | Revu cookie fallback | 선택 |
| `REVU_LOGIN_ID`, `REVU_EMAIL` | Revu login id aliases | 선택 |
| `REVU_LOGIN_PASSWORD`, `REVU_PASSWORD` | Revu password aliases | 선택 |
| `REVU_HEADLESS` | Revu Playwright headless 제어 | 선택 |

### Detail Enrichment

| 변수 | 용도 | 필수 여부 |
| --- | --- | --- |
| `DETAIL_ENRICH_CONCURRENCY` | 공통 detail enrich 병렬 수 | 선택 |
| `DINNERQUEEN_DETAIL_ENRICH_CONCURRENCY` | Dinnerqueen detail 병렬 수 | 선택 |
| `DINNERQUEEN_DETAIL_ENRICH_LIMIT` | Dinnerqueen detail 제한 | 선택 |
| `DINNERQUEEN_DETAIL_TIMEOUT_MS` | Dinnerqueen detail timeout | 선택 |
| `DINNERQUEEN_PROVISION_BACKFILL_LIMIT` | 디너의여왕 혜택 backfill 처리 수. 기본 25 | 선택 |
| `DINNERQUEEN_PROVISION_BACKFILL_CONCURRENCY` | 디너의여왕 혜택 backfill 병렬 수. 기본 4 | 선택 |
| `DINNERQUEEN_PROVISION_BACKFILL_TIMEOUT_MS` | 디너의여왕 혜택 backfill 상세 timeout. 기본 15000 | 선택 |
| `DINNERQUEEN_PROVISION_BACKFILL_WRITE_PUBLIC` | `1`이면 `public/campaigns.json`에 backfill 결과 반영 | 선택, 쓰기 승인 필요 |
| `DINNERQUEEN_PROVISION_BACKFILL_SYNC_SUPABASE` | `1`이면 Supabase `campaigns.reward_text`에 backfill 결과 upsert | 선택, DB 쓰기 승인 필요 |
| `DINNERQUEEN_PROVISION_BACKFILL_SYNC_EXISTING_PUBLIC` | `1`이면 재크롤 없이 기존 public snapshot의 Dinnerqueen `point`를 Supabase upsert 대상으로 사용 | 선택, DB 쓰기 승인 필요 |
| `POPOMON_RENDERED_DETAIL_ENRICH_LIMIT` | Popomon rendered detail 제한 | 선택 |
| `POPOMON_RENDERED_DETAIL_ENRICH_CONCURRENCY` | Popomon rendered detail 병렬 수 | 선택 |
| `POPOMON_RENDERED_DETAIL_TIMEOUT_MS` | Popomon rendered detail timeout | 선택 |
| `SEOULOBA_DETAIL_ENRICH_LIMIT` | Seouloba detail 제한 | 선택 |
| `SEOULOBA_DETAIL_TIMEOUT_MS` | Seouloba detail timeout | 선택 |
| `CHVU_DETAIL_ENRICH_LIMIT` | Chvu detail 제한 | 선택 |
| `CHVU_DETAIL_ENRICH_CONCURRENCY` | Chvu detail 병렬 수 | 선택, `.env.example`에는 없음 |
| `CHVU_DETAIL_ENRICH_MODE` | Chvu detail 대상 모드 | 선택, `.env.example`에는 없음 |
| `CHVU_DETAIL_TIMEOUT_MS` | Chvu detail timeout | 선택 |

### Coupang Ads

| 변수 | 용도 | 필수 여부 |
| --- | --- | --- |
| `COUPANG_PARTNERS_ACCESS_KEY` | Coupang Partners API access key | sync에는 필수 |
| `COUPANG_PARTNERS_SECRET_KEY` | Coupang Partners API secret key | sync에는 필수 |
| `COUPANG_PARTNERS_SUB_ID` | tracking sub id | 선택 |
| `COUPANG_PARTNERS_BASE_URL` | API host | 선택 |
| `COUPANG_PARTNERS_API_BASE_PATH` | API path | 선택 |
| `COUPANG_PARTNERS_DISCLOSURE` | 광고 고지 문구 | 선택 |
| `COUPANG_AD_KEYWORDS` | 광고 생성 키워드 CSV | 선택 |
| `COUPANG_AD_SLOTS` | 광고 슬롯 CSV | 선택 |
| `COUPANG_AD_PRODUCT_LIMIT` | keyword/slot product limit | 선택 |
| `COUPANG_AD_PER_SLOT` | slot당 생성 수 | 선택 |
| `COUPANG_AD_IMAGE_SIZE` | 이미지 크기 | 선택 |
| `COUPANG_AD_REPLACE_EXISTING` | 기존 Coupang 광고 대체 여부 | 선택 |

규칙: Coupang secret 값은 절대 `VITE_` prefix를 붙이지 않는다. 일반 쿠팡 링크 금지 정책은 코드/문서에서 명시적으로 발견되지 않았으므로 확인 필요. 현재 코드는 Coupang Partners API로 생성한 product/deeplink URL과 disclosure를 `public/ads.json`에 저장한다.

## Data And Runtime Files

| 경로 | 생성/수정 주체 | 설명 | 주의 |
| --- | --- | --- | --- |
| `public/campaigns.json` | `scripts/crawler/crawl.cjs`, `npm run build`가 dist로 복사 | 서비스 fallback 캠페인 snapshot | 크롤러가 atomic write로 덮어씀 |
| `public/crawl-status.json` | crawler | 최신 크롤 상태, quality gate, Supabase sync 상태 | 크롤 중/후 계속 갱신 |
| `public/data-quality.json` | crawler | 좌표/주소/중복/stale 품질 리포트 | 대용량, 필요한 key만 읽기 |
| `public/crawl-check.json` | `scripts/crawler/check-crawl.cjs` | check 결과 | `npm run crawl:check`가 갱신 |
| `public/ads.json` | ads sync 또는 수동 | 광고 슬롯 데이터 | `ads:sync:coupang`이 일부 광고를 대체 |
| `.cache/kakao-geocode-cache.json` | crawler | Kakao geocode cache | 삭제 시 geocode 비용/시간 증가 |
| `.cache/crawl-artifacts/raw-campaigns.json` | crawler | raw crawl artifact | git ignore |
| `.cache/crawl-artifacts/clean-campaigns.json` | crawler | fresh clean campaigns | git ignore |
| `.cache/crawl-artifacts/publish-candidate.json` | crawler | quality gate 전후 publish 후보 | git ignore |
| `.cache/crawl-artifacts/published-campaigns.json` | crawler | 실제 publish snapshot artifact | git ignore |
| `.cache/crawl-artifacts/quality-gate.json` | crawler | gate 결과 | git ignore |
| `.cache/crawl-artifacts/duplicates.json` | crawler | hidden duplicate groups | git ignore |
| `.cache/crawl-artifacts/stale-campaigns.json` | crawler | preserved/stale/expired hidden 정보 | git ignore |
| `.cache/mrblog-storage-state.json` | crawler code path | Mrblog browser session cache | 존재 여부 확인 필요, secret 취급 |
| `.cache/revu-auth-token.json` | crawler code path | Revu auth token cache | 존재 여부 확인 필요, secret 취급 |
| `logs/crawl-*.log` | `scripts/ops/run-crawl.ps1` | 운영 크롤 로그 | 삭제 전 승인 |
| `dev-server.log`, `dev-server.err.log`, `vite-dev.*.log` | 로컬 개발 | dev server 로그 | 삭제 전 승인 |
| `dist/` | `npm run build` | 정적 build 산출물 | 재생성 가능하지만 배포 확인 중이면 보존 |
| `.next/` | `npm run build` | Next.js build 산출물 | 재생성 가능하지만 배포 확인 중이면 보존 |
| `.env` | 사용자/운영자 | 실제 비밀키/토큰/쿠키 | 절대 출력/커밋 금지 |

현재 public crawl 상태는 파일의 timestamp를 직접 확인한다. 크롤 중에는 `public/crawl-status.json`, `public/data-quality.json`, `.cache/crawl-artifacts/*`, `logs/*`를 수동 수정하지 않는다.

확인 우선순위:

- `public/crawl-status.json`의 `status`, `startedAt`, `completedAt`, `failedCrawls`
- `.cache/crawl-artifacts/quality-gate.json`의 `status`, `canPublish`, `blockingFailures`
- `public/data-quality.json`의 전체 캠페인 수, 좌표/주소 품질, 플랫폼별 품질
- `public/crawl-check.json`은 크롤보다 오래된 결과일 수 있으므로 항상 timestamp로 비교한다.

## Operational Rules

데이터 우선순위:

- 프론트는 `isSupabaseConfigured`가 true이면 Supabase `campaigns`/`platforms`를 먼저 조회한다.
- Supabase rows가 없거나 초기 로드 실패 시 `/campaigns.json` fallback을 사용한다.
- Supabase 조회는 `.eq("status", "open")`, `d_day` ascending, page size 1000으로 가져온다.
- 오래된 DB 스키마에서 location/date columns가 없으면 stable core columns로 retry한다.

캠페인 노출 규칙:

- `isCampaignOpen(campaign)`은 `status !== "closed"`이고 `dDay >= 0`이어야 true다.
- `normalizeCampaignDDay`로 D-day를 정규화한다.
- `collapseDuplicateCampaigns`가 중복 캠페인 대표를 선택한다.
- 서비스 방향은 좌표 완성도보다 여러 체험단 사이트를 한곳에서 카테고리별로 고르게 비교하는 데 둔다. 탐색/홈 목록은 플랫폼 분산 노출을 우선하고, 지도 좌표 품질은 보조 품질 지표로 취급한다.
- 탐색 화면 UX는 쿠팡/네이버 검색처럼 첫 화면에서 검색창, 빠른 탐색, 카테고리, 첫 결과가 바로 보여야 한다. 큰 설명 hero나 상단 광고가 첫 결과를 접히게 만들면 안 된다.
- 모바일 탐색 기본 상태에서 지역/정렬은 접고, 활성 조건이 있을 때만 펼친다. 카드/모달의 주요 클릭 영역은 최소 40px, 신청 CTA는 44px 이상을 유지한다.
- 상세 모달은 Toss식 바텀시트 전환을 쓰되 시트와 하단 CTA 영역은 불투명한 표면으로 처리해 뒤 화면 텍스트가 비치지 않게 한다.
- 캠페인 필터 구조는 1차 `유형`(`전체`, `방문형`, `배송형`)과 2차 세부 `카테고리`(`맛집`, `뷰티`, `생활용품` 등)를 분리한다. `배송형`을 세부 `category`로 덮어쓰지 말고 `campaignType=delivery`, `campaignMode=배송형`으로 보존한다.
- `/app?tab=explore&type=delivery` 같은 공유 링크는 `tab`과 `type` 쿼리를 유지해야 한다. 관련 변경 후에는 `scripts/qa/app-routing-fixture.mjs`와 `scripts/qa/delivery-category-fixture.mjs`를 함께 확인한다.
- 지도는 `hasValidCoordinates`, `coordinateSource !== "unresolved"`, `platformId !== "pavlo"` 조건을 사용한다.
- 지도 표시 후보에는 정밀 좌표 source와 주소 기반 지오코딩 좌표(`kakao_address`)를 포함한다. 좌표가 추정 수준인 `kakao_keyword*`, `derived`, `unresolved`는 품질 리스크로 보고 무리하게 핀으로 늘리지 않는다.
- `MapPage.jsx`는 전국 첫 화면에서 우선순위 160개만 표시하고, 지역/도시 선택 후에는 최대 300개까지 표시한다. 대량 좌표를 한 번에 모두 그리기보다 클러스터와 목록 탐색을 우선한다.
- Kakao Developers Web 플랫폼 도메인은 로컬 5173 기준 `http://localhost:5173`, `http://127.0.0.1:5173`과 실제 배포 도메인을 확인한다.

크롤러 발행 규칙:

- `CRAWL_ONLY`가 있으면 platform id 또는 label이 일치하는 crawler만 실행한다.
- 활성 crawler: `reviewnote`, `mrblog`, `reviewplace`, `dinner`, `pavlo`, `seouloba`, `revu`, `gangnam`, `popomon`, `comeplay`, `tble`, `ringble`, `chvu`.
- 각 platform crawl 후 geocode pass와 pipeline artifact write가 진행된다.
- 출시/운영 기준은 기존 순차 크롤러를 유지한다.
- 병렬 수집/merge/publish 운영 경로는 제거했다. 병렬 npm 스크립트, 병렬 PowerShell 스크립트, crawler worker merge 모드를 사용하지 않는다.
- 현재 운영 전략은 하루 1회 전체 13개 순차 크롤을 기준으로 한다. 코드 수정 검증은 전체 크롤 전에 `CRAWL_ONLY`로 수정 플랫폼만 제한 크롤한다.
- Codex/AI 에이전트는 크롤 명령을 직접 실행하지 않는다. 크롤은 오래 걸려 세션을 막으므로, 필요한 환경변수와 명령만 사용자에게 제공하고 사용자가 별도 터미널에서 실행한다.
- 디너의여왕 배송형만 검증할 때는 `$env:CRAWL_ONLY="dinner"; $env:DINNERQUEEN_LIST_SCOPE="delivery"; npm.cmd run crawl`을 사용한다. 운영 기본은 `DINNERQUEEN_LIST_SCOPE` 미지정 상태의 전체+배송형 수집이다.
- 2026-05-29 라이브 Network 확인 기준 디너의여왕 배송형은 `/taste/taste_list` page 1~2 합계 41개이고 사용자가 41개가 맞다고 확인했다. `has_next=false`에서 중단하는 현재 배송형 페이징을 기준으로 본다.
- 새 체험단 사이트, 배송형, 기자단 소스를 추가하기 전에는 `docs/crawler/new-source-intake.md` 형식으로 URL 샘플, 필드 위치, 로그인 필요 여부를 먼저 받는다. 비밀번호, 쿠키, 토큰 값은 채팅에 붙여넣지 않고 필요한 경우 `.env` 변수명만 정한다.
- 디너의여왕 `point`는 2026-05-26 public snapshot 기준 3,616/3,616건 채움 상태다. 전체 크롤이 다시 돌 때 새 결과의 `point`가 비면 이전 public snapshot 값을 보존하는 로직을 유지한다. `qa:dinnerqueen:point-preserve`로 회귀 확인한다.
- 디너의여왕 `point`를 보강할 때는 전체 크롤 반복보다 `npm run crawl:dinnerqueen:provision-backfill`을 먼저 쓴다. 기본은 dry-run이며, public 쓰기 `--write-public`, 기존 public 기반 DB 동기화 `--sync-existing-public --sync-supabase`는 사용자 승인 후 실행한다.
- Supabase 동기화가 `exceed_egress_quota` 또는 project restricted로 실패하면 반복 재시도하지 말고 quota/프로젝트 제한 해소를 먼저 요청한다. 운영 화면은 DB의 빈 Dinnerqueen `point`를 배포된 `/campaigns.json`으로 병합하는 fallback이 있다.
- 프론트 캠페인 목록은 Supabase egress 절감을 위해 기본적으로 `/campaigns.json`을 우선 사용한다. DB 캠페인 목록 refresh가 꼭 필요할 때만 `VITE_CAMPAIGN_DB_REFRESH_ENABLED=1`을 설정한다.
- 현재 운영 SEO origin은 무료 Vercel alias `https://camp-platform-liart.vercel.app`이다. custom domain 비용/DNS를 보류한 상태이므로 canonical, sitemap, robots, OG URL, SEO 랜딩 내부 링크, Search Console/Search Advisor 제출은 이 origin 기준으로 맞춘다.
- `cheheommoa.com`은 나중에 실제 등록/DNS 연결이 끝난 뒤에만 공식 SEO 도메인으로 전환한다. 전환 시 env/canonical/sitemap 확인 후 재배포하고 검색엔진 제출 대상을 갱신한다.
- `public/googlee0f5f1649e1592a4.html`와 `public/naver1f22d1c4fe7f26bc2b5b94fbf0ee2629.html`은 검색엔진 소유권 확인 유지 파일이므로 해당 속성을 쓰는 동안 삭제하지 않는다.
- SEO 랜딩은 실제 `public/campaigns.json`에 매칭 데이터가 있는 검색 조합부터 추가한다. 빈 페이지 양산은 피하고, 예를 들어 `/리뷰노트-체험단`은 매칭 캠페인이 생기기 전까지 제외한다.
- Google Search Console/Naver Search Advisor의 기본 사이트 등록과 sitemap 제출은 사용자가 완료했다. 같은 제출을 반복 안내하지 말고, 다음에는 sitemap 상태, URL inspection/수집 상태, 실제 `site:` 검색 결과를 확인한다. Google URL inspection quota 초과가 나오면 당일 반복 요청하지 않고 다음 날 재시도한다.
- Next.js app route가 `src/app/sitemap.js`와 `src/app/robots.js`에서 `/sitemap.xml`, `/robots.txt`를 생성하므로 `public/sitemap.xml` 또는 `public/robots.txt`만 고쳐서는 production 응답이 바뀌지 않을 수 있다. sitemap/robots 변경 시 동적 route와 `scripts/qa/seo-landing-fixture.mjs`도 같이 확인한다.
- Search Console에서 sitemap이 `가져올 수 없음`으로 남으면 같은 URL을 반복 제출하기 전에 해당 sitemap 행의 세부 오류를 먼저 확인한다. 현재 우회 제출 대상은 `sitemap-pages.xml`이며, 세부 오류가 없으면 다음 fallback은 URL 한 줄씩 담는 `sitemap.txt` 추가다.
- 작업트리가 dirty일 때 Vercel production 배포가 필요하면 현재 폴더를 그대로 올리지 말고, 커밋된 `HEAD`를 별도 clean worktree로 체크아웃한 뒤 `.vercel/project.json`만 복사해서 배포한다. 그래야 `public/*.json`, `package.json`, 사용자 작업물이 의도치 않게 production에 포함되지 않는다.
- `public/crawl-status.json`가 `blocked`이거나 `supabaseSync.status`가 `skipped`인 산출물은 그대로 커밋/배포하지 않는다. 단, 2026-05-26 Dinnerqueen `point` public snapshot 보강과 Vercel production 배포는 완료됐고, Supabase DB 동기화만 quota 제한으로 보류됐다.
- 증분 크롤은 아직 구현하지 않았다. 도입하더라도 일일 전체 크롤을 대체하지 말고 D-0~D-3, 신규 캠페인, 좌표/주소 누락, 최근 실패/수정 플랫폼 보강 용도로 설계한다.
- 실패한 platform은 `failedCrawls`에 기록되고, 이전 snapshot의 해당 platform 데이터는 보존될 수 있다.
- 성공 platform 비율 70%는 발행 hard gate다.
- 좌표 완성도는 전체 발행 hard gate나 출시 우선순위가 아니라 지도 보조 품질 지표다.
- 특정 platform의 open 캠페인 수가 이전 공개 데이터 대비 80% 이상 급락하면 이번 결과를 격리하고 이전 공개 데이터를 보존한다.
- 특정 platform의 주소 또는 좌표 수가 이전 공개 데이터 대비 80% 이상 급락하면 이번 결과를 격리하고 이전 공개 데이터를 보존한다.
- fresh crawl에 주소/좌표가 없더라도 같은 platform/id의 이전 공개 캠페인에 정상 주소/좌표가 있으면 lifecycle 단계에서 carry-forward한다. Supabase upsert도 이 lifecycle 데이터를 사용한다.
- `qualityGate.canPublish`가 false면 `public/campaigns.json`을 갱신하지 않고 Supabase sync도 skip한다.
- `qualityGate.canPublish`가 true일 때만 `publishCampaignSnapshot`으로 `public/campaigns.json`을 갱신한다.
- Supabase가 설정되어 있고 gate가 통과하면 lifecycle이 반영된 fresh 캠페인을 `upsertToSupabase(...)`로 올린 뒤 `closeExpiredCampaigns()`, `closeMissingCampaigns(successfulCrawls, crawlStartedAt)`가 실행된다.
- `closeMissingCampaigns`는 성공한 platform에 대해 이번 crawl 시작 전 `crawled_at`을 가진 open rows를 `closed`로 바꾼다.

종료 캠페인 처리:

- crawler의 `applyCampaignDetailState`, `extractDetailDeadlineInfo`, `detectClosedCampaignDetail`이 상세 HTML에서 마감/종료/신청불가와 과거 deadline을 탐지한다.
- 닫힌 캠페인은 `status="closed"`와 음수 `dDay`로 Supabase mapping된다.
- 프론트도 `isCampaignOpen`으로 closed/음수 D-day를 제거한다.
- `popomon`은 API의 `C_regi_end_date_count`를 우선 D-day로 사용하고, 없을 때 `C_regi_end_date`를 KST 기준으로 계산한다. 기존 publish 단계 1일 앞당김 보정은 사용하지 않는다. `C_regi_end_date=2026-05-08`은 KST 5월 8일 마감으로 보아 2026-05-07에는 D-1이어야 한다.
- `comeplay`는 publish 정규화 단계에서 D-day를 1일 앞당기지 않는다. 상세 페이지의 `리뷰어 신청`/`체험단 신청` 기간을 application deadline으로 우선 사용하고, 과거 snapshot의 `comeplay_minus_one` 보정 표시는 발행 직전에 제거하고 되돌린다.
- `chvu`는 Next.js 정적 HTML이 아니라 `/v2/campaigns` 목록 API의 `closeAt`/`status`를 우선 신뢰한다. 상세 보강은 `/v2/campaigns/{campaignId}` API를 먼저 사용하고, HTML/rendered fallback은 API 보강 실패 시에만 보조로 사용한다. `closeAt=2026-05-07T15:00:00Z`처럼 KST 다음날 0시를 뜻하는 값은 해당 KST 날짜 마감으로 보아 2026-05-07에는 D-1이어야 한다.
- `chvu`에서 `status`가 `completed` 등 종료 상태이거나 `closeAt`이 과거면 closed 처리한다. 마감일을 못 찾은 `D-99` 기본값 캠페인은 open으로 발행하지 않는다. 이전 snapshot의 `D-99` 비율이 높으면 플랫폼 급락 baseline을 신뢰하지 않고 새 결과로 정리한다.
- `reviewplace`는 목록 D-day를 신뢰하고 상세 페이지는 주소 보강 중심으로 사용한다.
- `reviewnote` 목록 API(`/api/v2/campaigns`)는 정확 주소/좌표 source로 보지 않는다. 정확 주소/좌표는 `REVIEWNOTE_COOKIE`가 있을 때 `/api/campaign?id=...` 상세 API의 `address1/address2/lat/lng`만 사용한다.
- `reviewnote`가 첫 요청부터 403이면 `.cache/reviewnote-forbidden-cooldown.json`에 cooldown을 기록하고, cooldown 중에는 네트워크 요청 없이 실패/보존 처리한다. 일반 브라우저에서도 403이면 반복 재시도하지 않는다.
- `reviewnote` 상세 API가 403을 연속 반환하면 circuit breaker가 남은 상세 요청을 중단한다. 새 쿠키로 제한 크롤을 먼저 검증하고, 403이 반복되면 `REVIEWNOTE_DETAIL_ENRICH_CONCURRENCY=1`, `REVIEWNOTE_DETAIL_BATCH_DELAY_MS=3000~5000`으로 낮춰 재시도한다.
- `gangnam`은 상세 페이지 닫힘 문구보다 미래 `sourceEndedAt`이 있으면 open 상태를 우선한다. 상세 일정표에서는 `리뷰 등록기간`/`캠페인 결과발표`가 아니라 `.cmp_info`의 `캠페인 신청기간` 같은 신청/모집/접수 기간을 application deadline으로 우선 사용한다.
- 시간/타임존이 포함된 ISO timestamp를 다시 D-day로 계산할 때는 날짜 부분만 잘라 KST 0시로 재해석하지 않는다. `2026-05-09T15:00:00.000Z`처럼 KST 다음날 0시를 뜻하는 값은 원본 timestamp 그대로 해석해야 한다.
- 확인 필요: `scripts/crawler/crawl.cjs` 수정 시각이 `public/campaigns.json` 최신 생성 시각보다 늦어서, 최신 상세 종료 로직이 public snapshot에 반영됐는지 재크롤 후 확인해야 한다.

좌표 품질 규칙:

- crawler는 Kakao REST address/keyword search를 사용한다.
- `KAKAO_REST_API_KEY`가 없으면 Kakao geocoding을 skip한다.
- coordinate quality는 코드상 `html`, `naver`, `kakao_tile`, `*_api` 계열을 exact, `kakao_address`를 geocoded, `kakao_keyword*`를 estimated로 분류한다.
- `derived`, `unresolved`, known bad coordinate는 지도 품질 리스크다.
- 리뷰노트에 과거 잘못 들어간 부산 센텀서로 30 계열 주소/좌표는 known-bad로 취급한다. 이 값이 다시 보이면 public/Supabase 반영 전에 원인을 먼저 확인한다.

광고 규칙:

- `useAds`는 `/ads.json`을 `cache: "no-store"`로 읽는다.
- 광고 click/view event는 localStorage `cheheommoa_ad_events`에 최대 200개까지 저장하고, Supabase `ad_events` insert를 시도한다. 기존 `cheommoa_ad_events` 값은 읽을 때 새 key로 이전한다.
- 광고 선택은 브라우저 localStorage `cheheommoa_ad_interests`의 최근 카테고리/지역 신호를 사용해 fallback Coupang 광고를 고른다. 신호는 서버로 보내지 않고, 화면 중간에서 자동으로 바꾸지 않는다.
- `COUPANG_AD_REPLACE_EXISTING=1`이면 generated Coupang 광고나 provider가 `coupang`인 기존 광고를 대체할 수 있다. `managedBy: "manual"` 또는 `preserve: true`인 광고는 보존된다.

프로필/채널 연동 규칙:

- 마이페이지 채널 연동은 `profiles`의 수동 백업값을 저장하면서, 유튜브는 서버 API(`/api/social/youtube-sync`)와 `social_connections`/`social_metrics`를 통해 공개 지표를 동기화하는 구조다.
- 유튜브 동기화는 서버 전용 `YOUTUBE_API_KEY`, Supabase service role, 로그인 access token 검증이 필요하다. 운영 DB migration 적용, Vercel env 등록, 실제 YouTube API 호출 검증은 사용자 명시 승인 후 진행한다.
- 네이버 블로그 이웃수/방문자와 인스타그램 팔로워 자동 갱신은 아직 구현하지 않는다. 네이버/인스타그램 API, OAuth, 크롤링, 브라우저 자동화는 외부 호출/계정 연동 작업이므로 사용자 명시 승인 전에는 실행하지 않는다.
- `database/supabase/migrations/20260515_profiles_social_channels.sql`은 마이페이지 채널/신청 멘트 저장용 컬럼 migration이다. 이 migration이 운영 DB에 적용되기 전에는 배포해도 새 프로필 필드 저장이 실패할 수 있다.
- `database/supabase/migrations/20260515_social_connections.sql`은 유튜브/향후 SNS 연결과 지표 히스토리용 migration이다. 이 migration과 `YOUTUBE_API_KEY`가 운영에 준비되기 전에는 유튜브 연동 버튼이 실패할 수 있다.
- 신청 멘트 템플릿은 `profiles.application_message_template`에 저장하고, 지원 버튼 클릭 시 클립보드 복사 보조 용도로만 사용한다. 외부 플랫폼에 자동 제출하지 않는다.

분석 이벤트 규칙:

- 사용자 행동 분석은 `analytics_events`에 최소 이벤트만 저장한다. 탭 보기, 홈 탐색 클릭, 탐색 필터, 캠페인 상세 열기, 즐겨찾기, 신청 버튼, legal 열기, 분석 수집 동의/거부가 현재 허용 범위다.
- 검색어 원문, 비밀번호, 쿠키, 외부 플랫폼 로그인 정보, 결제 정보는 분석 이벤트에 저장하지 않는다. 검색은 사용 여부와 길이만 저장하고, `page_path`의 `q` 값과 인증 hash 토큰도 마스킹한다.
- 로그인 사용자는 `user_id`, 비로그인 사용자는 브라우저 localStorage 기반 임의 `anonymous_id`와 세션 ID로 구분한다. 개인정보 처리방침의 분석 수집 토글을 끄면 일반 분석 이벤트 전송을 중단한다.
- `database/supabase/migrations/20260513_analytics_events.sql`은 운영 DB 적용 전 사용자 승인이 필요하다. 적용 전 배포해도 이벤트 insert 실패는 사용자 화면에 노출하지 않는다.
- 운영 탭의 분석 요약은 `get_analytics_dashboard_summary` RPC로 집계값만 읽는다. 원본 row select는 열지 않고, dashboard RPC는 authenticated 사용자에게만 grant한다.
- `database/supabase/migrations/20260513_analytics_dashboard_summary.sql`도 운영 DB 적용 전 사용자 승인이 필요하다. 적용 전에는 운영 탭에 RPC 미적용/로그인 필요 안내가 보일 수 있다.
- 외부 판매/제공 가능한 데이터는 개인을 알아볼 수 없는 집계 리포트로만 설계한다. `user_id`, `anonymous_id`, `session_id`, 원본 `page_path`, 개별 사용자 여정, 검색어 원문, 쿠키/토큰/계정 정보는 외부 제공 대상이 아니다.
- 데이터 상품화는 최소 표본 기준, 기간 집계, 카테고리/지역/플랫폼 단위 요약, 비식별 처리, 개인정보 처리방침/동의 범위 확인을 통과한 별도 export/report 레이어에서만 진행한다. 운영 DB 원본 테이블을 그대로 다운로드하거나 판매하지 않는다.
- 판매/제공용 첫 집계 RPC는 `database/supabase/migrations/20260513_analytics_market_report.sql`의 `get_analytics_market_report`다. 기본 기준은 최근 30일, 최소 이벤트 20건, 최소 고유 브라우저 5개이며 SQL 내부에서 `min_events >= 10`, `min_browsers >= 5`로 강제한다.
- 운영 탭의 판매용 리포트 준비 상태 패널은 `get_analytics_dashboard_summary` 집계값으로 현재 표본 충족 여부만 보여준다. 실제 외부 제공/판매용 데이터 export의 권한 기준은 service role 전용 `get_analytics_market_report`를 기준으로 본다.
- 저장형 시장 리포트는 `database/supabase/migrations/20260513_analytics_market_report_archive.sql`을 기준으로 한다. `analytics_market_reports`와 `analytics_market_report_items`에는 기준을 넘은 집계값만 저장하고, 운영탭 생성/목록/다운로드 RPC는 `analytics_report_admins` allowlist 사용자에게만 허용한다.
- 시장 리포트 운영 정책은 `docs/product/analytics-market-report.md`를 기준으로 본다. 새 데이터 상품을 만들 때는 이 문서의 허용/금지 항목과 표본 기준을 먼저 확인한다.
- 데이터 수익화 보강 우선순위는 캠페인 노출 이벤트, 지원 상태/메모/리뷰 URL 이벤트, 지도 필터/핀/클러스터 이벤트, UTM/referrer 유입 추적, 리포트 생성/다운로드 감사 로그 순서로 본다.
- 새 분석 이벤트 타입을 추가할 때는 프론트 allowlist, `analytics_events` check constraint/migration, 운영 요약 RPC, 시장 리포트 RPC, 개인정보처리방침/동의 문구를 함께 확인한다.
- 캠페인 노출 이벤트는 과도한 row 폭증을 막기 위해 IntersectionObserver 기반으로 중복/빈도 제한을 둔다. 검색어 원문, 쿠키, 외부 계정값, 개별 사용자 여정 export는 계속 금지한다.
- 운영/판매용 지표 RPC와 저장형 리포트 접근은 가능한 한 `analytics_report_admins` allowlist 기준으로 제한한다. 권한을 더 넓히는 변경은 사용자 확인 후 진행한다.

## Safety Rules

배송형 크롤러 운영:

- 전체 크롤이 이미 실행 중이면 끝날 때까지 `CRAWL_ONLY=...` 같은 제한 크롤을 새로 시작하지 않는다. 제한 크롤도 공용 crawler artifact/public snapshot을 쓰므로 실행 중인 크롤과 상태가 섞일 수 있다.
- 새 배송형 소스는 먼저 작은 parser fixture를 추가/보강하고 `node --check scripts/crawler/crawl.cjs`를 통과시킨 뒤, 사용자 터미널에서 제한 live crawl을 실행해 개수를 비교한다. 개수가 맞기 전에는 snapshot 발행/배포하지 않는다.

절대 하지 말 것:

- `.env`, 쿠키, 토큰, service role key, Coupang secret 값을 출력/문서화/커밋하지 않는다.
- `SUPABASE_SERVICE_ROLE_KEY`, `COUPANG_PARTNERS_SECRET_KEY` 같은 server-only secret에 `VITE_` prefix를 붙이지 않는다.
- 사용자 변경을 임의로 `git reset`, `git checkout --`, `git clean`, 삭제로 되돌리지 않는다.
- `public/campaigns.json`, `public/data-quality.json`, `.cache`, `logs`, `dist`, `.next`를 임의 삭제하지 않는다.
- `node_modules`나 lockfile을 의존성 변경 없이 건드리지 않는다.
- 대용량 `docs/research/crawl-source-snippets/*` 전체를 무작정 읽지 않는다.
- `agent-browser`를 앱 기능, 크롤러 대체, 외부 사이트 자동 조작, 로그인 세션 수집 용도로 사용하지 않는다.

사용자 명시 승인 필요:

- `npm run crawl`
- `npm run crawl:dinnerqueen:provision-backfill` 중 `--write-public`, `--sync-supabase`, `--sync-existing-public` 또는 관련 `DINNERQUEEN_PROVISION_BACKFILL_*` 쓰기/DB 동기화 env를 켠 실행
- `npm run ops:crawl`
- `$env:CRAWL_ONLY="..."; npm run crawl`
- `powershell ... scripts/ops/run-crawl.ps1 -SkipPreflight`
- `powershell ... scripts/ops/register-crawl-task.ps1`
- `npm run ads:sync:coupang`
- Supabase SQL schema/migration을 실제 DB에 적용
- production 배포 또는 Vercel 설정 변경
- 테스트 계정이 아닌 실제 계정으로 `npm run qa:auth` 또는 로그인 후 쓰기 QA 실행
- `git push`, force push, reset, clean, stash 등 작업물에 영향이 큰 git 명령
- 캐시/로그/public JSON 삭제 또는 대량 재생성
- `agent-browser` 설치, Chrome 다운로드, 브라우저 자동 QA 실행

외부 API/브라우저 자동화:

- crawler는 여러 외부 사이트, Kakao REST API, Supabase를 호출한다.
- Mrblog/Revu/일부 rendered detail은 Playwright Chromium을 실행한다.
- `CRAWLER_HEADLESS=0`, `MRBLOG_HEADLESS=0`, `REVU_HEADLESS=0`은 visible browser를 띄울 수 있으므로 승인 없이 사용하지 않는다.
- `npm run ads:sync:coupang -- --dry-run`은 파일을 쓰지 않지만 Coupang API를 호출할 수 있으므로 네트워크/API 사용으로 취급한다.
- `agent-browser`는 출시 전후 QA 보조 도구로만 쓴다. 허용 범위는 `https://camp-platform-liart.vercel.app`, 로컬 preview/dev URL, 필요한 정적 asset 확인에 한정한다.
- `agent-browser` 사용 시 `--allowed-domains`로 우리 도메인과 필요한 CDN/API만 제한하고, `--content-boundaries`, `--max-output`을 켠다.
- `agent-browser` state/session/profile/cookie 파일은 민감 정보로 취급한다. 저장하지 않는 것을 기본으로 하고, 저장이 필요하면 사용자 승인 후 git ignore 대상 경로에만 둔다.
- `agent-browser`는 화면 깨짐, 모바일 viewport, 지도 표시, console error, PWA/광고 로드 확인에만 사용한다. 크롤, 계정 로그인 자동화, 외부 서비스 조작, 대량 요청에는 사용하지 않는다.
- 같은 `agent-browser` session에는 명령을 병렬로 보내지 말고 순차 실행한다. Windows sandbox home에서는 CDP channel이 닫힐 수 있으므로 실제 사용자 환경에서 실행하고, 종료 시 `agent-browser --session <name> close`로 세션을 닫는다.

스케줄러:

- `register-crawl-task.ps1`은 `schtasks.exe /Create /F`로 Windows scheduled task를 생성/덮어쓴다.
- 기본 task 이름은 `CampPlatformCrawl_Morning`, `CampPlatformCrawl_Afternoon`이다.
- 기본 시간은 08:00, `-TwiceDaily` 사용 시 17:00도 추가한다.
- 현재 실제 등록 상태는 `npm run ops:check-task`로 확인 필요.

## Coding Conventions

- frontend는 ESM/React functional component 스타일이다.
- crawler/ops Node scripts는 `.cjs` CommonJS 스타일이다.
- `package.json`에 `"type": "module"`이 있으므로 새 Node script가 CommonJS이면 `.cjs` 확장자를 사용한다.
- CSS는 `src/index.css`, `src/app/App.css`, `src/app/compact-ui.css` 중심이다.
- ESLint는 JS/JSX에 적용되며 `no-unused-vars`가 error다. 대문자/언더스코어 패턴 `^[A-Z_]` 변수는 ignore된다.
- 한국어 텍스트 파일은 UTF-8로 다룬다. PowerShell `Get-Content` 출력이 깨져 보여도 파일 자체가 깨졌다고 단정하지 말고 Node `fs.readFileSync(path, "utf8")`로 재확인한다.
- 프론트 데이터 shaping은 페이지에 중복 구현하지 말고 `src/features/campaigns/lib/campaigns.js` 또는 hook에 둔다.
- Supabase 없는 환경에서도 앱이 fallback으로 읽히는 구조를 유지한다.
- crawler 수정은 `scripts/crawler/crawl.cjs`의 기존 platform별 함수와 공통 pipeline을 존중해서 최소 범위로 한다.
- generated/runtime JSON은 코드가 쓰는 산출물이다. 수동 수정은 사용자 요청이 있을 때만 한다.
- 의미 있는 작업을 마친 뒤에는 `docs/work-log.md`에 변경사항, 검증 결과, 다음 세션에서 이어갈 작업만 짧게 남긴다.
- 마케팅, 홍보 문구, SEO/콘텐츠 전략 작업은 기본적으로 `marketing/` 아래에서 진행한다.
- SEO 구조 전환 설계는 `docs/superpowers/specs/2026-05-27-nextjs-seo-ssg-design.md`를 기준으로 한다.
- Next.js 빌드 산출물 `.next/`는 커밋하지 않는다. 검증에는 사용하되 필요 시 재생성 가능한 산출물로 본다.

## Public UI Trust Checks

- Public home/app card trust changes should keep display shaping in `src/features/campaigns/lib/campaigns.js` or SEO helpers, not duplicated inside page/card components.
- Before commit/deploy for this area, run `node .\scripts\qa\campaign-display-fixture.mjs`, `node .\scripts\qa\seo-landing-fixture.mjs`, targeted ESLint for touched files, and `npm.cmd run build`.
- Do not stage runtime `public/*.json`, `.cache` screenshots, or `ui-*.png` screenshots with UI trust/code commits unless the user explicitly chooses that snapshot/artifact.

## Verification Checklist

문서만 수정한 경우:

- `AGENTS.md`가 저장소 루트에 있는지 확인.
- `git status --short AGENTS.md docs/work-log.md .gitignore`로 추적 상태 확인.

프론트 코드 수정 후:

```powershell
npm run lint
npm run build
npm run qa:smoke
npm run qa:auth
```

수동 확인:

- `/` 홈 캠페인 표시
- 탐색 검색/지역/도시/category/sort/preset 동작
- 지도 화면 Kakao key 누락/도메인 오류 상태와 정상 상태
- campaign detail modal 열림
- auth modal 및 Supabase 미설정 fallback
- `?legal=privacy`, `?legal=terms`, `?contact=1`
- `?ops=1` 운영 탭 노출
- 모바일 폭에서 텍스트/버튼 겹침 없음

크롤러 코드 수정 후:

```powershell
node --check scripts/crawler/crawl.cjs
```

실제 크롤은 사용자 승인 후 platform 제한으로 먼저 실행:

```powershell
$env:CRAWL_ONLY="popomon"
npm run crawl
```

크롤 후 확인:

- `public/crawl-status.json`의 `status`, `completedAt`, `failedCrawls`
- `public/data-quality.json`의 platform별 coordinate/address completeness
- `.cache/crawl-artifacts/quality-gate.json`의 `status`, `canPublish`
- `public/campaigns.json`의 `updatedAt`, campaign count
- Supabase sync status
- closed campaign이 open으로 남지 않는지

광고 스크립트 수정 후:

```powershell
node --check scripts/ads/sync-coupang-ads.cjs
npm run ads:check:coupang
npm run ads:sync:coupang -- --dry-run
```

`ads:sync:coupang` 실제 쓰기 실행은 사용자 승인 필요.

운영 스크립트 수정 후:

```powershell
node --check scripts/ops/check-supabase.cjs
npm run ops:preflight
npm run ops:check-task
```

PowerShell 스크립트는 별도 테스트 프레임워크가 없다. 실제 scheduler 생성/크롤 실행은 승인 필요.

## Handoff Notes

다음 세션에서 먼저 읽을 파일:

1. `AGENTS.md`
2. `docs/work-log.md`
3. `git status --short`
4. `package.json`
5. 변경하려는 영역의 실제 파일
6. 데이터/크롤 관련이면 `public/crawl-status.json`, `public/data-quality.json`, `.cache/crawl-artifacts/quality-gate.json`
7. 운영 관련이면 `scripts/ops/run-crawl.ps1`, `scripts/ops/test-production-readiness.ps1`
8. DB 관련이면 `database/supabase/schema.sql`와 해당 migration

현재 이어갈 핵심:

- 병렬 수집/merge/publish 구조는 제거했다. 다음 크롤 검증은 사용자 승인 후 기존 순차 크롤러(`npm run crawl` 또는 `npm run ops:crawl`) 기준으로 진행한다.
- 이전 병렬 수집 run `20260506-153328`은 품질 비교용 과거 산출물로만 취급하고 운영 입력으로 사용하지 않는다.
- 리뷰노트는 쿠키 문제가 아니라 IP 차단 상태로 확인됐다. 2026-05-15 11:42 KST 기준 7일 동안 reviewnote 크롤을 돌리지 않고, 2026-05-22 11:42 KST 이후 일반 브라우저 접근이 풀렸는지 먼저 확인한 뒤 사용자 승인으로 제한 크롤을 재검증한다.
- `.cache/reviewnote-forbidden-cooldown.json`은 2026-05-22T02:42:10.473Z까지 reviewnote 네트워크 요청을 막도록 갱신했다. 이 날짜 전에는 `REVIEWNOTE_IGNORE_COOLDOWN=1`로 우회하지 않는다.
- 2026-05-22 이후 재검증 시에는 먼저 브라우저에서 reviewnote가 403이 아닌지 확인하고, 통과할 때만 새 `REVIEWNOTE_COOKIE` 반영과 `CRAWL_ONLY=reviewnote` 제한 크롤을 고려한다.
- 리뷰노트가 안정되면 사용자 승인 후 전체 순차 크롤을 돌려 `dinner`, `popomon`, `seouloba` 제한값이 시간과 품질에 미친 영향을 확인한다.
- 디너의여왕 혜택은 `public/campaigns.json` 기준 3,616/3,616건 채워졌다. 다음 작업은 Supabase quota 제한 해소 후 `DINNERQUEEN_PROVISION_BACKFILL_LIMIT=0 npm.cmd run crawl:dinnerqueen:provision-backfill -- --sync-existing-public --sync-supabase`를 재실행해 DB `reward_text`까지 맞추는 것이다.
- 2026-05-26 Vercel production 배포 완료: `dpl_8D1F1L9WhvTyVFbrkP583sQPh3Rc`, alias `https://camp-platform-liart.vercel.app`. Windows 스케줄러 재등록은 별도 승인 후 진행한다.

현재 git 상태 기준 주의:

- 작업트리는 dirty 상태다. 다음 세션은 `git status --short`로 최신 목록을 다시 확인한다.
- 현재 핵심 변경 축은 크롤러 순차 운영 안정화, 홈/탐색/지도/카드 UX, 출시 문서, SEO/PWA다.
- `public/crawl-status.json`, `public/data-quality.json`은 실행 결과 파일이므로 사용자가 만든 상태를 임의 revert하지 않는다.
- 새 파일로 `docs/launch-priorities.md`, `public/sitemap.xml`가 있다.
- 관련 없는 사용자 작업물은 임의 수정/삭제/revert 금지.

자주 깨지는 부분:

- Kakao map key 누락 또는 Kakao Developers 도메인 미등록.
- 로컬 dev 서버 포트가 5173이 아니면 Kakao 도메인 등록과 어긋나 지도가 안 뜰 수 있다.
- Supabase production schema가 local schema보다 오래되어 location/date columns가 없을 수 있음. 프론트/crawler 모두 fallback이 일부 있지만 DB migration 확인 필요.
- source site HTML/API 변경으로 platform crawler 파싱 실패.
- 쿠키/토큰 만료로 auth-dependent crawler 성능 저하.
- 리뷰노트는 목록 API가 200이어도 상세 API가 403이면 정확 주소/좌표가 나오지 않는다. 목록 응답 성공만으로 좌표 수집 성공으로 판단하지 않는다.
- `public/crawl-check.json`이 최신 crawl보다 오래되어 오판하는 경우.
- `public/*.json` 대용량 파일 diff/출력으로 터미널이 느려지는 경우.
- PowerShell 콘솔에서 한국어가 깨져 보이는 경우.

확인 필요:

- 실제 production deploy는 Vercel로 추정되지만 `package.json`에 deploy script는 없다. 배포 방식은 Vercel dashboard/Git integration 여부 확인 필요.
- Windows scheduled task의 현재 등록 상태는 `npm run ops:check-task` 실행 전에는 단정하지 않는다.
- 최신 `scripts/crawler/crawl.cjs` 변경이 `public/campaigns.json`과 Supabase에 모두 반영됐는지는 최신 크롤 후 확인 필요.
- 자동화 테스트 도입 여부는 현재 코드 기준으로 없음.

## 작성 근거

이 문서는 다음 파일/명령을 직접 확인해 작성했다.

- `rg --files`
- `git status --short`
- `git log -5 --oneline --decorate`
- `README.md`
- 기존 `AGENTS.md`
- `.env.example`
- `.gitignore`
- `.vercelignore`
- `package.json`
- `vite.config.js`
- `vercel.json`
- `eslint.config.js`
- `index.html`
- `src/main.jsx`
- `src/app/App.jsx`
- `src/features/campaigns/hooks/useCampaigns.js`
- `src/features/campaigns/lib/campaigns.js`
- `src/features/map/hooks/useKakaoMapLoader.js`
- `src/pages/MapPage.jsx`
- `src/pages/OpsPage.jsx`
- `src/features/ads/lib/ads.js`
- `src/features/ads/hooks/useAds.js`
- `src/shared/api/supabase.js`
- `src/shared/config/site.js`
- `src/shared/config/platforms.js`
- `scripts/crawler/crawl.cjs`
- `scripts/crawler/check-crawl.cjs`
- `scripts/ads/sync-coupang-ads.cjs`
- `scripts/ops/run-crawl.ps1`
- `scripts/ops/test-production-readiness.ps1`
- `scripts/ops/register-crawl-task.ps1`
- `scripts/ops/check-crawl-task.ps1`
- `scripts/ops/check-supabase.cjs`
- `database/supabase/schema.sql`
- `docs/crawler/operations.md`
- `docs/release-checklist.md`
- `docs/coupang-partners-env.md`
- `public/crawl-status.json`
- `public/data-quality.json`
- `public/crawl-check.json`
- `.cache/crawl-artifacts/*` 파일 목록
- `logs/`, `dist/`, `.cache/` 파일 목록
