# camp-platform MVP 명세 및 DB 초안

## 1. 제품 한 줄 정의

`camp-platform`은 여러 체험단 사이트에 흩어진 캠페인을 한 곳에 모아 보여주고, 사용자가 저장·비교·지원 현황 관리까지 할 수 있게 만드는 메타 플랫폼이다.

초기 단계에서는 `실제 신청 대행 서비스`가 아니라 `통합 탐색 + 개인 관리 도구`로 시작한다.

## 2. MVP 범위

### 포함

- 여러 체험단 사이트의 캠페인 통합 수집
- 통합 목록 검색/필터/정렬
- 캠페인 상세 보기
- 외부 플랫폼 신청 페이지로 이동
- 즐겨찾기 저장
- 사용자의 지원 현황 기록/수정
- 마감 임박, 카테고리, 플랫폼 기준 탐색
- 기본 경쟁도 추정

### 제외

- 실제 신청 대행
- 외부 플랫폼 계정 연동 자동 신청
- 결제/정산 자동화
- 캠페인주(광고주) 직접 등록 포털
- 운영자 CMS 전체 구축

## 3. 핵심 사용자

### 1차 사용자

- 네이버 블로거
- 인스타그램/유튜브 리뷰어
- 체험단을 여러 사이트에서 반복적으로 찾는 개인 사용자

### 1차 문제

- 체험단 사이트가 흩어져 있다
- 어떤 캠페인이 오늘 마감인지 한눈에 보기 어렵다
- 내가 어디에 지원했고 결과가 어떤지 관리가 어렵다
- 경쟁도와 카테고리별 기회를 빠르게 판단하기 어렵다

## 4. MVP 핵심 가치

1. 한 번에 본다
- 여러 체험단 사이트 캠페인을 한 화면에서 모아 본다.

2. 빨리 고른다
- 마감일, 카테고리, 플랫폼, 경쟁도 기준으로 빠르게 추린다.

3. 잊지 않는다
- 즐겨찾기와 지원 현황을 기록해 개인 워크플로를 붙잡는다.

## 5. 현재 코드 기준 해석

현재 코드베이스는 아래 상태다.

- 프론트엔드: React + Vite
- 데이터 소스
  - 공개 캠페인 데이터: `public/campaigns.json`
  - 사용자 데이터: Supabase `profiles`, `favorites`, `applications`
- 현재 신청하기 동작은 외부 링크 열기만 수행
- `App.jsx`에 화면/상태/도메인 로직이 대부분 집중되어 있음
- `scripts/crawler/crawl.cjs`는 5개 플랫폼을 수집해 정적 JSON으로 저장

이 상태는 MVP 방향과 맞지만, 제품으로 키우려면 `정적 JSON 중심 구조`에서 `DB 중심 구조`로 넘어가야 한다.

## 6. MVP 화면 정의

### A. 홈 / 통합 캠페인 목록

목적:
- 오늘 지원할 캠페인을 빠르게 고르게 한다.

필수 요소:
- 검색
- 카테고리 필터
- 플랫폼 필터
- 마감순 / 경쟁도순 정렬
- 오늘 마감 배너
- 즐겨찾기 토글

### B. 캠페인 상세

목적:
- 지원 전에 캠페인 성격과 경쟁도를 판단하게 한다.

필수 요소:
- 플랫폼명
- 카테고리
- 마감일 / D-Day
- 신청수 / 예상 선정수
- 경쟁도 라벨
- 외부 신청 링크
- 즐겨찾기

### C. 내 현황

목적:
- 사용자가 자신의 체험단 활동을 한 화면에서 관리하게 한다.

필수 요소:
- 즐겨찾기 목록
- 지원 현황
- 상태 변경
- 간단한 선정률 분석

## 7. 수익화 방향 초안

MVP 이후 가장 현실적인 1차 수익화는 `개인 사용자 구독형`이다.

### 무료

- 통합 캠페인 목록 조회
- 기본 검색/필터
- 즐겨찾기 소량 저장
- 수동 현황 관리

### 유료

- 마감 임박 알림
- 경쟁도/카테고리 맞춤 추천
- 플랫폼별 선정률 분석 고도화
- 키워드/지역 저장 필터
- 더 많은 즐겨찾기 및 현황 관리
- 신규 캠페인 빠른 알림

그 다음 단계의 후보:
- 광고주/플랫폼 스폰서 노출
- 프리미엄 노출 슬롯
- B2B 리드 전달

## 8. 권장 DB 모델

MVP 기준 권장 테이블은 아래와 같다.

### 1. `platforms`

목적:
- 체험단 플랫폼 메타데이터 관리

주요 컬럼:
- `id` text primary key
- `name` text not null
- `base_url` text not null
- `description` text
- `color` text
- `emoji` text
- `is_active` boolean default true
- `created_at` timestamptz default now()

### 2. `campaigns`

목적:
- 통합 캠페인의 현재 스냅샷 저장

주요 컬럼:
- `id` uuid primary key
- `platform_id` text references platforms(id)
- `external_id` text not null
- `source_url` text not null
- `title` text not null
- `campaign_type` text
- `category` text
- `region` text
- `reward_text` text
- `apply_count` integer default 0
- `selected_count` integer default 0
- `competition_score` numeric
- `d_day` integer
- `status` text default 'open'
- `crawled_at` timestamptz not null
- `created_at` timestamptz default now()
- `updated_at` timestamptz default now()

제약:
- unique (`platform_id`, `external_id`)

### 3. `campaign_snapshots`

목적:
- 신청수, 마감일, 제목 변경 이력 저장

주요 컬럼:
- `id` uuid primary key
- `campaign_id` uuid references campaigns(id) on delete cascade
- `title` text
- `apply_count` integer
- `selected_count` integer
- `d_day` integer
- `status` text
- `captured_at` timestamptz default now()

### 4. `profiles`

목적:
- 사용자 프로필

주요 컬럼:
- `id` uuid primary key references auth.users(id)
- `name` text
- `blog_url` text
- `level` text default '브론즈'
- `points` integer default 0
- `plan_id` uuid null
- `created_at` timestamptz default now()
- `updated_at` timestamptz default now()

### 5. `favorites`

목적:
- 사용자가 저장한 캠페인

주요 컬럼:
- `id` uuid primary key
- `user_id` uuid references auth.users(id) on delete cascade
- `campaign_id` uuid references campaigns(id) on delete cascade
- `created_at` timestamptz default now()

제약:
- unique (`user_id`, `campaign_id`)

현재 코드의 `campaign_title`, `campaign_url`, `platform` 등의 중복 저장은 MVP에선 가능하지만, 장기적으로는 `campaign_id` 중심 참조로 줄이는 게 낫다.

### 6. `applications`

목적:
- 사용자의 지원 활동 추적

주요 컬럼:
- `id` uuid primary key
- `user_id` uuid references auth.users(id) on delete cascade
- `campaign_id` uuid references campaigns(id) on delete cascade
- `status` text default 'applied'
- `applied_at` timestamptz default now()
- `selected_at` timestamptz
- `completed_at` timestamptz
- `memo` text
- `review_url` text

권장 상태값:
- `saved`
- `applied`
- `under_review`
- `selected`
- `review_writing`
- `completed`
- `rejected`

제약:
- unique (`user_id`, `campaign_id`)

### 7. `alerts`

목적:
- 사용자 맞춤 알림 설정

주요 컬럼:
- `id` uuid primary key
- `user_id` uuid references auth.users(id) on delete cascade
- `keyword` text
- `category` text
- `platform_id` text null references platforms(id)
- `max_competition_score` numeric null
- `is_active` boolean default true
- `created_at` timestamptz default now()

### 8. `plans`

목적:
- 구독 플랜 정의

주요 컬럼:
- `id` uuid primary key
- `code` text unique
- `name` text
- `price_monthly` integer
- `features` jsonb
- `is_active` boolean default true

### 9. `subscriptions`

목적:
- 사용자 구독 상태 관리

주요 컬럼:
- `id` uuid primary key
- `user_id` uuid references auth.users(id)
- `plan_id` uuid references plans(id)
- `status` text
- `started_at` timestamptz
- `ends_at` timestamptz
- `billing_provider` text
- `billing_reference` text

## 9. 데이터 흐름 권장안

### 현재

`scripts/crawler/crawl.cjs` -> `public/campaigns.json` -> 프론트 fetch

### 다음 단계

`scripts/crawler/crawl.cjs` -> Supabase `campaigns` upsert -> 프론트가 DB에서 조회

권장 이유:
- 정적 배포 없이 데이터 갱신 가능
- 사용자 맞춤 필터/정렬과 결합 쉬움
- 경쟁도, 이력, 알림 기능 확장 쉬움

## 10. 구현 우선순위

### Phase 1

- `campaigns`, `platforms`, `favorites`, `applications`, `profiles` 스키마 정리
- `scripts/crawler/crawl.cjs` 결과를 DB upsert로 전환
- 프론트 목록을 JSON 대신 Supabase에서 읽기

### Phase 2

- `campaign_snapshots` 저장
- 경쟁도 계산 정교화
- 마감 임박 알림
- 즐겨찾기/현황 UX 보강

### Phase 3

- 유료 플랜
- 고급 알림/추천
- 운영자용 데이터 관리 화면

## 11. 코드 구조 다음 과제

현재 가장 먼저 해야 할 리팩터링:

1. `App.jsx` 분해
- `pages/`
- `components/`
- `lib/`
- `hooks/`

2. 도메인 타입/정규화 정리
- platform
- campaign
- favorite
- application

3. 크롤러와 앱 데이터 계약 고정
- 필수 필드명 통일
- category/type/status enum 정의

## 12. 바로 다음 액션

이 문서 기준으로 바로 이어갈 다음 작업은 아래 순서가 적절하다.

1. Supabase SQL 스키마 작성
2. `scripts/crawler/crawl.cjs`를 DB upsert 구조로 전환
3. 프론트를 `campaigns.json` 의존에서 Supabase 조회로 전환
4. `App.jsx` 분리

## 13. 구현 메모

- 현재 저장소에는 `database/supabase/schema.sql` 초안 파일이 추가되어 있다.
- 현재 `scripts/crawler/crawl.cjs`는 `public/campaigns.json` 저장을 유지하면서, `SUPABASE_SERVICE_ROLE_KEY`가 있을 때만 `platforms`, `campaigns` 업서트를 시도하도록 확장되었다.
- 현재 프론트는 `campaigns.json` fallback을 제거했고, `campaigns` 테이블을 우선이 아니라 사실상 유일한 운영 데이터 소스로 사용한다.
- 이 SQL은 현재 프론트가 이미 사용하는 `profiles`, `favorites`, `applications` 구조를 최대한 깨지 않도록 작성했다.
- 즉시 바꾸지 않은 부분:
  - `favorites.campaign_id`
  - `applications.campaign_id`
- 위 두 컬럼은 현재 프론트가 `text` 기반 캠페인 식별값을 저장하고 있어, 우선 호환성을 위해 `text`로 유지했다.
- 향후 DB 중심으로 옮길 때는 `campaigns.id(uuid)` 중심 참조로 단계적으로 마이그레이션하는 게 맞다.
