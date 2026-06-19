# Crawl Source Inventory

## Purpose

- 현재 어떤 소스가 `camp-platform` 크롤러에 연결되어 있는지 정리한다.
- 새 소스를 추가하거나 기존 소스가 실패할 때 기준 문서로 사용한다.
- UI 이슈와 수집 이슈를 구분할 때 먼저 확인하는 문서로 사용한다.

## Active Sources

현재 `scripts/crawler/crawl.cjs`에는 아래 플랫폼 크롤러가 연결되어 있다.

| Platform ID | Display Name | Note |
| --- | --- | --- |
| `reviewnote` | 리뷰노트 | 공개 목록 기반 |
| `mrblog` | 미블 | 공개 목록 기반, 세션 갱신 로직 포함 |
| `reviewplace` | 리뷰플레이스 | 공개 목록 기반 |
| `dinner` | 디너의여왕 | 공개 목록 기반, 전체/배송형 목록 수집 |
| `pavlo` | 파블로 | 공개 목록 기반 |
| `seouloba` | 서울오빠 | 공개 목록 기반 |
| `revu` | 레뷰 | API/인증 보조 가능성 있음 |
| `gangnam` | 강남맛집체험단 | 공개 목록 기반 |
| `popomon` | 포포몬 | API 호출 기반 |
| `comeplay` | 놀러와체험단 | 공개 목록 기반 |
| `tble` | 티블 | 공개 목록 기반 |
| `ringble` | 링블 | 공개 목록 기반, 방문형 `category=832` |
| `chvu` | 체험뷰 | 공개 목록/API 기반 |

## Candidate Sources

아래 소스는 사용자 제보 또는 조사 후보이며 아직 `scripts/crawler/crawl.cjs`에 연결되지 않았다.

| Proposed Platform ID | Display Name | Scope | Note |
| --- | --- | --- | --- |
| - | - | - | 현재 대기 후보 없음 |

## Triage Order

화면에서 특정 플랫폼이 적게 보이거나 안 보일 때는 아래 순서로 확인한다.

1. `public/campaigns.json`에 해당 `platformId` 데이터가 있는지 확인
2. `npm run crawl` 로그에서 `failed`, `duplicate-only page`, `auth required`, `0건` 같은 신호 확인
3. 필요하면 해당 소스의 요청 URL, 인증 상태, 파싱 선택자 점검

## Local Count Check

```powershell
@'
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync('public/campaigns.json', 'utf8'));
const campaigns = payload.campaigns || [];
const counts = new Map();
for (const c of campaigns) {
  const key = c.platformId || c.platform || 'unknown';
  counts.set(key, (counts.get(key) || 0) + 1);
}
console.log('total', campaigns.length);
for (const [k, v] of [...counts.entries()].sort((a, b) => b[1] - a[1])) {
  console.log(`${k}\t${v}`);
}
'@ | node
```

## Add New Source

- `scripts/crawler/crawl.cjs`에 플랫폼별 독립 함수로 추가한다.
- 전체 파이프라인을 막지 않도록 기존과 같은 독립 실행 구조를 유지한다.
- `platformId`, `platform`, `url`, `title`, `dDay`, `category` 필드는 일관되게 맞춘다.
- 조사 자료나 HTML 스냅샷은 `docs/research/crawl-source-snippets/` 아래에 둔다.

## Notes

- 인증이 필요한 소스는 환경변수와 운영 메모를 함께 갱신한다.
- 사용자 노출 문구를 바꾸면 `npm run build`, `npm run lint`로 바로 확인한다.
