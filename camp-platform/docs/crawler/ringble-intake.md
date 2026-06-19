# Ringble Crawler Intake

## Status

- 상태: 1차 크롤러 구현
- 접수일: 2026-05-28
- 구현 단계: 정적 HTTP 목록/상세 파싱 추가, `CRAWL_ONLY=ringble`로 제한 실행 가능
- 제안 `platformId`: `ringble`
- 제안 표시명: `링블`
- 우선 수집 타입: 방문형

## Source URLs

```text
사이트 이름: 링블
사이트 메인 URL: https://www.ringble.co.kr/
방문형 캠페인 목록 URL: https://www.ringble.co.kr/category.php?category=832
2페이지 URL: https://www.ringble.co.kr/category.php?start=2&category=832
3페이지 URL: https://www.ringble.co.kr/category.php?start=3&category=832
```

## Detail URL Samples

```text
https://www.ringble.co.kr/detail.php?number=275017&category=832
https://www.ringble.co.kr/detail.php?number=274871&category=832
https://www.ringble.co.kr/detail.php?number=275239&category=832
https://www.ringble.co.kr/detail.php?number=274969&category=832
```

## Pagination Notes

사용자 제보 기준으로 목록 하단 페이지 링크를 클릭해야 다음 페이지로 이동한다.

```html
<!-- 1페이지 -->
<div class="page_now"><a href="/category.php?start=1&amp;category=832" onfocus="this.blur()">1</a></div>

<!-- 2페이지 -->
<div class="page_nomal"><a href="/category.php?start=2&amp;category=832" onfocus="this.blur()">2</a></div>

<!-- 4페이지 -->
<div class="page_nomal"><a href="/category.php?start=4&amp;category=832" onfocus="this.blur()">4</a></div>
```

확인 필요:

- 사용자 확인 기준 2페이지는 `start=2`, 3페이지는 `start=3`이다.
- 직접 URL 생성 방식 `category.php?start=N&category=832`로 4페이지 이후도 접근 가능한지 확인한다.
- 실제 브라우저 스크롤/클릭이 필요한지, 정적 HTTP 요청만으로 목록 HTML을 받을 수 있는지 확인한다.

## Detail Field Sample

사용자 제공 상세 샘플:

```text
상세 URL: https://www.ringble.co.kr/detail.php?number=274969&category=832
제목: [충남/서산시] 소뜰 (식사권)
모집 기간: 26년 05월 26일(화) ~ 26년 06월 01일(월)
당첨자 발표일: 26년 06월 02일(화)
리뷰 등록기간: 26년 06월 03일(수) ~ 26년 06월 15일(월)
제공내역: [2인] 8만원 식사권 (*주문 시 된장찌개 주문 필수) + 링블포인트 2,000점
주소: https://naver.me/5qRkthtp
모집인원: 신청 4 / 모집 21
리뷰 채널: 확인 필요
종료 캠페인 URL: 못 찾음
```

HTML 단서:

- 제목 셀 class: `detail_page_title`
- 진행 정보 셀 class: `bloger_process_title`
- 모집 기간 id: `10`
- 당첨자 발표일 id: `20`
- 리뷰 등록기간 id: `30`
- 제공내역 영역 class: `font11`
- 모집 인원 텍스트 패턴: `신청 N / 모집 N`

파싱 주의:

- 날짜는 `26년 06월 01일(월)` 형식이므로 2000년대 연도로 정규화한다.
- 제목의 `[충남/서산시]`를 지역 힌트로 사용할 수 있다.
- 주소가 네이버 단축 URL 형태일 수 있으므로 실제 주소 텍스트가 별도 존재하는지 확인하고, 없으면 상세 URL/주소 원문을 보존한다.
- 제공내역에 현물 제공과 링블포인트가 함께 들어갈 수 있다.

## Expected Fields To Extract

방문형 캠페인으로 우선 처리하되, 상세 HTML에서 아래 필드를 확인한다.

- 캠페인 제목
- 상세 URL
- 신청 마감일 또는 D-day
- 모집 상태
- 제공내역
- 방문 주소
- 지역
- 카테고리
- 리뷰 채널
- 모집 인원
- 썸네일 이미지

## Missing Intake Items

구현 전에 있으면 좋은 자료:

- 목록 카드 화면 캡처
- 상세 상단 정보 화면 캡처
- 제공내역/방문 주소/신청기간 영역 캡처
- 모집 종료 캠페인 상세 URL 1개
- 로그인 없이 상세 정보가 보이는지 여부

## Implementation Notes

- 기존 순차 크롤러 `scripts/crawler/crawl.cjs`에 독립 platform 함수로 추가한다.
- 먼저 `CRAWL_ONLY=ringble` 제한 크롤 기준으로 설계한다.
- 직접 URL 접근이 가능하면 브라우저 자동화보다 HTTP HTML 파싱을 우선한다.
- 주소가 확인되면 기존 Kakao geocode pipeline에 태운다.
- 대량 요청, 로그인, 쿠키/토큰 사용, Supabase 쓰기는 사용자 승인 전 실행하지 않는다.
