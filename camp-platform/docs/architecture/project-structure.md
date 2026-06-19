# Project Structure

## Purpose

이 문서는 `camp-platform` 폴더 구조의 의도를 설명합니다.
목표는 루트 혼잡을 줄이고, 프론트/크롤러/문서/DB 자산을 역할별로 빠르게 찾게 하는 것입니다.

## Top Level Layout

| Path | Purpose |
| --- | --- |
| `src/` | 프론트 애플리케이션 코드 |
| `public/` | 정적 자산과 로컬 데이터 fallback |
| `scripts/crawler/` | Node 크롤러 진입점 |
| `scripts/ops/` | 운영 보조 스크립트 |
| `docs/frontend/` | UI 방향과 프론트 규칙 |
| `docs/crawler/` | 크롤링 운영 문서 |
| `docs/architecture/` | 구조 및 설계 보조 문서 |
| `docs/product/` | 제품 기획 및 초안 문서 |
| `docs/research/` | 조사 자료, HTML 스냅샷, 실험 메모 |
| `database/supabase/` | 스키마와 DB 자산 |
| `.cache/` | 인증/좌표 캐시 등 로컬 캐시 |

## Why This Shape

- 앱 코드와 운영 자산을 분리해 탐색 비용을 줄인다.
- 크롤러 코드와 운영 스크립트를 분리해 책임을 명확히 한다.
- 설계 문서, 제품 초안, 조사 자료를 분리해 문서 성격을 구분한다.
- DB 자산을 루트에서 빼내어 런타임 코드와 혼동하지 않게 한다.

## Working Rules

- 새 프론트 규칙은 `docs/frontend/`에 둔다.
- 크롤링 운영 문서는 `docs/crawler/`에 둔다.
- HTML 스냅샷이나 조사 자료는 `docs/research/`에 둔다.
- 데이터베이스 스키마는 `database/supabase/`에 둔다.
- 루트에는 실행 진입점과 필수 설정 파일만 남긴다.

## Frontend Structure

| Path | Purpose |
| --- | --- |
| `src/app/` | 앱 셸과 앱 전용 스타일 |
| `src/pages/` | 탭/페이지 단위 화면 |
| `src/features/` | auth, campaigns, map, user 같은 기능별 코드 |
| `src/shared/api/` | 공통 API 클라이언트 |
| `src/shared/config/` | 공통 설정과 표시 상수 |
| `src/shared/assets/` | 공통 자산 |
| `src/legacy/` | 과거 잔재나 비교용 파일 |
