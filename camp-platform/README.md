# camp-platform

체험단 캠페인을 모아 보여주는 반응형 웹 프로젝트입니다.
프론트는 React + Vite로 구성되어 있고, 크롤러는 여러 플랫폼을 수집해 `public/campaigns.json`과 Supabase 데이터를 갱신할 수 있습니다.

## Core Commands

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

추가 검증:

```powershell
npm run build
npm run lint
npm run crawl
```

## Project Structure

- `src/`: 프론트 애플리케이션 코드
- `public/`: 정적 공개 자산과 로컬 데이터 fallback
- `scripts/crawler/`: Node 기반 크롤러 진입점
- `scripts/ops/`: Windows 작업 스케줄러 및 운영 스크립트
- `docs/frontend/`: UI 방향성과 프론트 규칙
- `docs/crawler/`: 크롤링 운영 문서와 소스 인벤토리
- `docs/architecture/`: 구조 문서
- `docs/product/`: 제품 기획/초안 문서
- `docs/research/`: 크롤링 조사 자료와 HTML 스냅샷
- `database/supabase/`: Supabase 스키마

세부 구조는 `docs/architecture/project-structure.md`를 기준으로 봅니다.

## Data Flow

1. `npm run crawl`
2. `public/campaigns.json` 갱신
3. 환경변수가 있으면 Supabase `platforms`, `campaigns` 업서트
4. 프론트는 Supabase 우선, 필요 시 `public/campaigns.json` fallback 사용

## Source Of Truth

- 에이전트/작업 규칙: `AGENTS.md`
- 프론트 규칙: `docs/frontend/frontend-guide.md`
- UI 방향: `docs/frontend/design.md`
- 크롤러 운영: `docs/crawler/operations.md`
- 발매 체크리스트: `docs/release-checklist.md`
- 소스 인벤토리: `docs/crawler/source-inventory.md`
- DB 스키마: `database/supabase/schema.sql`

## Notes

- `.env`는 커밋하지 않습니다.
- `node_modules`, `dist`는 산출물입니다.
- `public/campaigns.json`은 로컬 fallback 확인에도 사용됩니다.
