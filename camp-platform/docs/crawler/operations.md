# Crawl Operations

마지막 갱신: 2026-05-07 KST

## Purpose

이 문서는 `camp-platform` 운영 DB와 크롤러 자동 실행을 관리하는 기준 절차입니다.

## Current Operating Mode

출시 전 운영 기준은 기존 순차 크롤러입니다. 병렬 수집/merge/publish 경로는 제거했으므로 사용하지 않습니다.

현재 PC 기준 프로젝트 경로:

```text
C:\Users\itwill\자동화 공부\camp-platform
```

## Required Environment

운영 크롤러에서 필수로 보는 `.env` 항목:

```env
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
VITE_KAKAO_MAP_APP_KEY=
KAKAO_REST_API_KEY=
```

플랫폼별 인증값은 가능하면 채웁니다. 값이 없는 플랫폼은 일부 상세 수집이 실패하거나 적게 수집될 수 있습니다.

```env
REVU_AUTHORIZATION=
REVIEWNOTE_COOKIE=
REVIEWPLACE_COOKIE=
DINNERQUEEN_COOKIE=
GANGNAM_COOKIE=
POPOMON_COOKIE=
MRBLOG_COOKIE=
MRBLOG_X_CSRF_TOKEN=
MRBLOG_LOGIN_ID=
MRBLOG_LOGIN_PASSWORD=
```

출시 발행 게이트 기본값:

```env
QUALITY_GATE_MODE=early
QUALITY_GATE_MIN_SUCCESSFUL_PLATFORM_PCT=70
QUALITY_GATE_MIN_COORDINATE_PCT=70
QUALITY_GATE_WARN_COORDINATE_PCT=80
QUALITY_GATE_WARN_ADDRESS_PCT=70
QUALITY_GATE_MIN_COORDINATE_SAMPLE=20
QUALITY_GATE_MAX_PLATFORM_DROP_PCT=80
QUALITY_GATE_MIN_PLATFORM_BASELINE=20
```

게이트가 막히면 새 `public/campaigns.json`과 Supabase 반영을 건너뛰고 이전 정상 데이터를 유지합니다.

## Preflight

운영 배포/스케줄 등록 전에 먼저 점검합니다. 값 자체는 출력하지 않고 설정 여부만 확인합니다.

```powershell
Set-Location "C:\Users\itwill\자동화 공부\camp-platform"
npm run ops:preflight
```

운영 필수 조건을 강하게 검사하려면:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\ops\test-production-readiness.ps1 -RequireSupabase -RequireKakao -RequireScheduler -CheckSupabaseConnection
```

확인 항목:

- `.env` 존재 여부
- Node/npm 및 `node_modules`
- Supabase URL/anon/service role 키 설정 여부
- Kakao 지도/REST 키 설정 여부
- Supabase 스키마 파일의 핵심 테이블/함수
- Supabase 클라이언트에서 `campaigns`/`platforms` 테이블 접근 가능 여부
- `public/campaigns.json` 최신성
- 최신 크롤 로그
- Windows 작업 스케줄러 등록 상태

## Run Manually

프로젝트 루트에서:

```powershell
Set-Location "C:\Users\itwill\자동화 공부\camp-platform"
npm run ops:crawl
```

사용자에게 실행 코드만 줄 때는 절대 경로 1줄을 우선 사용합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\itwill\자동화 공부\camp-platform\scripts\ops\run-crawl.ps1"
```

직접 실행도 가능:

```powershell
npm run crawl
```

실행 로그는 `logs/crawl-YYYY-MM-DD_HHMMSS.log` 형식으로 저장됩니다.

`run-crawl.ps1`은 전역 실행 잠금과 기존 `node scripts/crawler/crawl.cjs` 프로세스 감지를 사용합니다. 오전 작업이 아직 끝나지 않았는데 오후 작업이 시작되면 새 작업은 로그에 skip 기록만 남기고 종료됩니다.

`run-crawl.ps1`은 기본적으로 Supabase/Kakao 필수 키 사전 점검을 수행합니다. 긴급히 로컬 스냅샷만 갱신해야 하면 다음처럼 건너뜁니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\ops\run-crawl.ps1 -SkipPreflight
```

주의: `npm run crawl`은 preflight와 중복 실행 방지 없이 바로 crawler를 실행합니다. 운영 확인 목적이면 `run-crawl.ps1` 또는 `npm run ops:crawl`을 우선합니다.

## After Crawl Checks

크롤이 끝난 뒤 먼저 상태 파일만 읽습니다. 실행 산출물을 수동 수정하지 않습니다.

```powershell
Get-Content -Raw -Encoding UTF8 "C:\Users\itwill\자동화 공부\camp-platform\public\crawl-status.json"
```

```powershell
Get-Content -Raw -Encoding UTF8 "C:\Users\itwill\자동화 공부\camp-platform\public\data-quality.json"
```

```powershell
Get-Content -Raw -Encoding UTF8 "C:\Users\itwill\자동화 공부\camp-platform\.cache\crawl-artifacts\quality-gate.json"
```

빠른 요약만 볼 때:

```powershell
$status = Get-Content -Raw -Encoding UTF8 "C:\Users\itwill\자동화 공부\camp-platform\public\crawl-status.json" | ConvertFrom-Json
$status | Select-Object status,startedAt,completedAt,successfulPlatforms,failedPlatforms
```

```powershell
$quality = Get-Content -Raw -Encoding UTF8 "C:\Users\itwill\자동화 공부\camp-platform\.cache\crawl-artifacts\quality-gate.json" | ConvertFrom-Json
$quality | Select-Object status,canPublish,checkedAt
```

확인 순서:

1. `crawl-status.json`의 `status`가 `completed`인지 확인합니다.
2. quality gate의 `canPublish`가 true인지 확인합니다.
3. `failedCrawls`와 blocking failure가 있으면 플랫폼명을 먼저 확인합니다.
4. `data-quality.json`에서 전체 캠페인 수, 좌표/주소 품질, 플랫폼별 급락을 확인합니다.
5. `gangnam`, `reviewplace`, 포포몬 D-day, 좌표 warning을 별도 확인합니다.
6. 통과 후 홈/탐색/지도/모바일 QA로 넘어갑니다.

## Register Scheduled Tasks

하루 1회:

```powershell
Set-Location "C:\Users\itwill\자동화 공부\camp-platform"
powershell -ExecutionPolicy Bypass -File .\scripts\ops\register-crawl-task.ps1
```

하루 2회:

```powershell
Set-Location "C:\Users\itwill\자동화 공부\camp-platform"
powershell -ExecutionPolicy Bypass -File .\scripts\ops\register-crawl-task.ps1 -TwiceDaily
```

기본 등록 시간:

- 오전 `08:00`
- 오후 `17:00`

시간을 바꿔 등록해야 하면 `-MorningTime "08:30"` 또는 `-AfternoonTime "18:00"`처럼 명시합니다.

기본 작업 이름:

- `CampPlatformCrawl_Morning`
- `CampPlatformCrawl_Afternoon`

등록 후에는 반드시 강한 점검을 통과시킵니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\ops\test-production-readiness.ps1 -RequireSupabase -RequireKakao -RequireScheduler -CheckSupabaseConnection
```

## Check Scheduled Tasks

```powershell
Set-Location "C:\Users\itwill\자동화 공부\camp-platform"
npm run ops:check-task
```

다른 prefix를 쓰는 경우:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ops\check-crawl-task.ps1 -TaskPrefix MyTask
```

## Verification

확인 포인트:

1. `logs/`에 크롤 로그가 생성되는지
2. `public/campaigns.json`의 `updatedAt`이 갱신되는지
3. 인증이 필요한 소스가 다음 실행에서 복구되는지
4. 실패 로그가 특정 플랫폼명과 함께 남는지
5. Supabase `campaigns` 테이블의 `crawled_at`이 갱신되는지
6. `status='closed'` 처리가 마감 공고에 적용되는지

## Launch Crawl Policy

MVP 출시 기간에는 하루 2회 자동 크롤을 기본 운영값으로 둡니다.

- 오전 `08:00`: 하루 시작 전 신규/마감 캠페인 반영
- 오후 `17:00`: 업무시간 중 추가/마감 캠페인 반영
- 성공 플랫폼 비율이 70% 미만이면 새 데이터를 발행하지 않고 이전 정상 데이터를 유지
- 좌표 기준 70%와 경고 기준 80%는 지도 품질 경고로 기록한다. 홈/탐색에서 사용할 수 있는 캠페인은 좌표가 없어도 발행 후보가 될 수 있다.
- 주소 경고 기준은 70%
- 특정 플랫폼의 open 캠페인 수가 이전 공개 데이터 대비 80% 이상 급락하면 해당 플랫폼은 이번 발행에서 격리하고 이전 공개 데이터를 보존한다.
- 실패 플랫폼은 `public/crawl-status.json`, `public/data-quality.json`, 로그, quality gate artifact에서 운영자가 확인

Windows 작업 스케줄러는 이 컴퓨터가 완전히 꺼져 있으면 지정 시각에 실행되지 않습니다. 절전 상태에서는 Windows 전원 설정과 작업의 wake 설정에 따라 깨울 수 있지만, 완전 종료 상태에서는 08:00 정각 실행을 보장할 수 없습니다. 출시 초기에는 로컬 스케줄러로 데이터 품질과 실패 패턴을 확인하고, 안정화 후에는 VPS/클라우드 서버 cron으로 이전합니다. 클라우드 이전 전까지는 PC 전원, 절전, 인터넷 연결 상태를 운영 리스크로 취급합니다.

## Operational Baseline

출간 전 최소 기준:

- `npm run build` 통과
- `npm run ops:preflight` 통과
- `test-production-readiness.ps1 -RequireSupabase -RequireKakao -RequireScheduler -CheckSupabaseConnection` 통과
- 하루 2회 크롤 작업 등록
- 첫 수동 크롤 1회 성공
- quality gate `successful_platform_rate` 70% 이상
- 플랫폼 급락 격리, 이전 데이터 보존, 좌표/주소 경고가 로그와 artifact에 기록되는지 확인
- 로그에서 반복 실패 플랫폼 확인 및 쿠키 갱신
