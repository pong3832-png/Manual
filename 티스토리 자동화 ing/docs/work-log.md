# Work Log

## 2026-05-28 - 티스토리 자동화 ing

### 오늘 변경

- `runtime/logs/scheduled_golf/`에서 2026-05-26 오후, 2026-05-27, 2026-05-28 최신 health/golf 예약 로그를 상태 키워드 중심으로 점검.
- `runtime/logs/scheduled/20260528_163801_daily.log`, `20260528_163825_daily.log`: `main.py` daily draft가 STEP 3 제목/해시태그 추출에서 ChatGPT 응답 `0자`로 타임아웃되어 티스토리 임시저장 단계까지 못 간 것 확인.
- `src/tistory_automation/main.py`: ChatGPT 응답 DOM의 마지막 요소가 빈 컨테이너일 때도 새 응답 후보 중 실제 텍스트가 있는 요소를 찾아 읽도록 수정. Selenium `.text`가 비면 `innerText/textContent`도 fallback으로 확인.
- `tests/test_chatgpt_response_wait.py`: 빈 tail 응답 요소 때문에 `_wait_for_text()`가 타임아웃되는 회귀 케이스 추가.
- 최근 health 글은 본문/제목/해시태그/대표이미지/공개 발행까지 완료되지만, `데이터분석하는 청년의 꿀템` 카테고리 항목을 찾지 못해 현재 선택값으로 발행되는 경고가 반복됨.
- 최근 golf 글은 대부분 공개 발행 완료. 다만 `20260526_164601_golf.log`는 본문 상세도 부족, `20260528_002200_golf.log`는 사전 리서치 브리프의 `예상 금액` 부족으로 중단됨.
- `golf/main_golf.py`: 해외 골프여행 사전 리서치 브리프가 검증에 실패하면 기존 브리프와 누락 사유를 포함한 보강 프롬프트를 1회 전송하고 다시 검증하도록 추가.
- `camp-platform/public/HTML편집.txt`: 티스토리 스킨 편집용 HTML에 AdSense 기본 로더와 `#article-view` 본문 중간 자동 삽입 스크립트 추가. 슬롯은 `3825649038`, 기존 상단/하단 티스토리 광고 치환값은 유지.

### 검증

- `.venv\Scripts\python.exe -X utf8 -m py_compile .\golf\main_golf.py` 통과.
- `.venv\Scripts\python.exe -m unittest tests.test_chatgpt_response_wait` 통과.
- `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과.
- `git diff --check -- "티스토리 자동화 ing/golf/main_golf.py"` 통과. LF→CRLF 경고만 있음.
- `HTML편집.txt`에서 `ca-pub-` 존재, `__TISTORY_ADSENSE_CLIENT__` 미검출, `3825649038`/`insertMidArticleAd`/`adsbygoogle.push` 존재 확인. 실제 티스토리 스킨 저장/공개 글 확인은 아직 안 함.

### 다음 세션

- health 카테고리 경고를 고치려면 실제 티스토리 카테고리명 또는 카테고리 DOM을 확인한 뒤 `TISTORY_COUPANG_CATEGORY_NAME`/fallback만 최소 수정한다.
- 다음 `TistoryChatGPTAutoPost_*` daily/coupang draft 로그에서 STEP 3 이후 티스토리 임시저장까지 이어지는지 확인한다.
- golf 리서치 보강 재시도 후에도 `예상 금액` 또는 상세도 부족이 반복되는지 다음 `scheduled_golf` 로그에서 확인한다.
- `HTML편집.txt` 전체를 티스토리 관리자 스킨 HTML에 반영한 뒤, 공개 글 DevTools Elements에서 `.tistory-mid-adsense` 또는 `3825649038`로 본문 중간 삽입 여부를 확인한다. JS 삽입 방식이라 페이지 소스 보기에는 중간 위치가 안 보일 수 있다.

## 2026-05-26 - 티스토리 자동화 ing

### 오늘 변경

- `main.py`: daily 이력 파일이 문자열 배열이어도 읽도록 수정해 `str object has no attribute get` 즉시 종료를 해결. 쿠팡 상품 선택은 A등급 부족 시 B/C/등급 없음 후보까지 fallback.
- `golf/main_golf.py`: 건강식품 후보 선택도 A등급 부족 시 B/C 미사용 후보까지 fallback.
- `keyword_crawler.py`: 건강식품 DB 직접 append용으로 리뷰 1,000개 이상, 평점 4.3 이상 필터 적용. 기존 CSV 헤더 순서 보존, A/B 추천등급 자동 입력, 새 쿠팡 검색 DOM 가격/평점/리뷰 추출 fallback 보강.
- `golf/건강식품_db.csv`: 디버그 Chrome 9222로 `중년 단백질 보충제` 검색 결과 37행 추가. 백업: `runtime/backups/health_db/건강식품_db_20260526_175026.csv`.

### 검증

- 재현 테스트 통과: daily 문자열 이력 로드, `main.py`/`main_golf.py` A등급 고갈 fallback, `keyword_crawler.py` 리뷰/평점 필터와 헤더 보존/A-B 등급 입력.
- 실제 크롤링: 1페이지 56개 추출, 필터/중복 제거 후 37개 append. 최종 `golf/건강식품_db.csv` 194행, 새 행 `used/post_title` 비어 있음, A 19개/B 18개. 2페이지는 로딩 실패로 skip.
- `py_compile` 통과: `src/tistory_automation/main.py`, `golf/main_golf.py`, `src/tistory_automation/pipeline/keyword_crawler.py`.
- `git diff --check` 통과. `main_golf.py` LF→CRLF 경고만 있음.

### 다음 세션

- 작업 목표: 티스토리 자동화 ing 후속 점검 및 안정화.
- 시작 절차: `AGENTS.md`와 `docs/work-log.md`를 먼저 읽고, 현재 `git status`만 확인한다. 전체 폴더 재분석은 하지 않는다.
- `runtime/logs/scheduled_golf/`에서 2026-05-26 오후 health/golf 작업이 새 세션과 확장된 건강식품 DB로 성공했는지 확인.
- 실패 작업이 있으면 로그 기준으로 티스토리 로그인/세션, ChatGPT 생성, 건강식품 API 상품 URL 확보, 후보 부족/중복 사용 로그, 발행창/대표이미지/HTML 입력 문제로 나눠 원인을 분류한다.
- 건강식품 DB를 더 채울 때는 `keyword_crawler.py --query ... --output-csv golf\건강식품_db.csv`를 쓰되, 실행 전 백업을 남기고 Chrome/ChromeDriver 메이저 버전 일치를 확인.
- `main.py` 쿠팡 글은 `products_db_category.csv` 후보가 URL 사용 로그 기준 0개라 계속 종료될 수 있다. 새 상품 수집 또는 `RESERVED` 복구 범위는 로그/임시글 대조 후 사용자 승인 필요.
- 수정이 필요하면 관련 파일만 열고 최소 수정한다. 수정 후 `py_compile` 또는 가능한 가장 작은 검증 명령만 실행한다.

## 2026-05-15 - 티스토리 자동화 ing

### 오늘 변경

- `main.py`: Chrome 148 환경에서 147 ChromeDriver를 먼저 잡던 문제 보정. 설치된 Chrome 메이저와 맞는 캐시 드라이버를 우선 사용.
- `main.py`, `scheduler.py`, `scripts/scheduled/*.ps1`: `main.py` 계열은 `--publish`/스케줄러 경로까지 모두 공개 발행하지 않고 임시저장으로 고정.
- `main.py`, `config/prompts/chatgpt_web_prompts.json`: daily 글은 히타/나고야/가나자와/이토시마처럼 세분화 여행 주제를 먼저 고르고, 같은 주제를 이미지/본문/메타 프롬프트에 주입.
- `main.py`: 티스토리 글쓰기 진입 시 `작성하던 글`/`이어서 작성` DOM 팝업이 보이는 경우에만 `ESC`로 닫도록 추가.
- 운영 확인: 18:05 `TistoryChatGPTAutoPost_08`은 `main.py --post-type coupang --scheduled --draft` 실행 직후 실패. `products_db_category.csv`는 100행 중 `used=Y` 96개, `post_title=RESERVED...` 65개, 실제 제목 31개, 미사용 표시 4개였고 남은 4개도 `used_coupang_urls.csv` 기준 이미 사용된 URL 키라 후보 0개로 종료.
- 원인 확인: `main.py`가 쿠팡 상품 선정 직후 `RESERVED ...`로 `mark_products_as_used()`를 먼저 호출한다. 이후 ChatGPT/티스토리 단계 실패 시 글이 작성되지 않아도 `used=Y`가 남고, `--draft` 성공분도 최종 제목 갱신 조건이 `publish` 안에 있어 `RESERVED`로 남을 수 있다.

### 검증

- `py_compile` 통과: `src/tistory_automation/main.py`, `src/tistory_automation/scheduler.py`.
- 프롬프트 JSON 파싱 통과, 샘플 daily 주제 조립/validator 통과.
- 실제 `--resume-tistory --post-type daily` 실행 성공: ChromeDriver `148.0.7778.167`, HTML 모드/이미지/태그/대표이미지 입력 후 `임시저장 버튼 클릭 완료`.
- `git diff --check` 통과. LF→CRLF 경고만 있음.
- 18:05 실패 조사: `schtasks /Query /TN TistoryChatGPTAutoPost_08`에서 `Last Result=1`, `runtime/logs/scheduled/20260515_180500_coupang.log`와 `20260515_180501_coupang.log`에서 상품 후보 단계 종료 확인. 인라인 Python으로 `_ordered_available_product_rows()` 결과 `seed_pool_count=0` 확인.
- `RESERVED` 대조: `products_db_category.csv`의 `RESERVED` 65개 중 로그상 임시저장 성공 확인 2개, 오류 확인 47개, 현재 로그 미확인 16개로 집계. 사용 기록 복구는 중복 발행 위험이 있으므로 로그/임시글 대조 후 사용자 승인 필요.

### 다음 세션

- 다음 예약 실행 로그에서 148 ChromeDriver 사용 여부와 `임시저장 버튼 클릭 완료`가 계속 찍히는지 확인.
- 새 daily 글이 넓은 `여행 준비`가 아니라 세부 지역/권역 제목으로 나오는지 티스토리 임시글 1~2개 확인.
- `golf/main_golf.py`는 이전부터 수정 상태였고 오늘 건드리지 않음.
- `main.py` 쿠팡 사용 처리 구조 수정 필요: 상품 선정 직후 `used=Y`를 확정하지 말고 별도 예약 상태를 쓰거나 실패 시 롤백한다. 티스토리 임시저장 성공 후에만 `used=Y`와 URL 사용 로그를 확정하고, `--draft` 성공분도 최종 제목 또는 성공 상태로 갱신하게 바꾼다.
- 수정 전 복구 범위 결정: `RESERVED` 사용 이력은 임시저장 성공/실패 로그와 티스토리 임시글 존재 여부를 대조한 뒤, 글이 없는 상품만 사용자 승인 후 미사용으로 되돌린다.

## 2026-05-12 - 티스토리 자동화 ing

### 오늘 변경

- `golf/main_golf.py`: ChatGPT 이미지 생성 후 본문 단계 멈춤 대응. 이미지 저장 후 본문 생성용 프로젝트 대화로 이동, 긴 프롬프트 CDP/클립보드/JS 입력 검증, 실행용 골프 본문 프롬프트 압축.
- `golf/main_golf.py`: 기본 실행은 공개 발행, 임시저장은 `--draft`. 대표이미지는 발행창 `div.inner_box input.inp_g`에 본문과 같은 이미지 파일을 다시 지정.
- `golf/main_golf.py`: 골프 이미지 프롬프트는 40~50대 고급 중년 골퍼/동행자 1~4명 허용. 골프 본문 프롬프트는 전문 용어를 쉬운 설명과 실제 확인 기준으로 연결하도록 보강.
- `golf/main_golf.py`: `--post-type health`/`건강식품`/`coupang` 추가. `data/products/건강식품_db.csv`가 없으면 `golf/건강식품_db.csv`를 사용하며, 건강식품 글은 대표 후보 1개 + 상황별 대안 1~2개 비교 구조.
- `src/tistory_automation/coupang/api.py`: 건강식품 쿠팡 글은 CSV 일반 링크로 fallback하지 않는다. API 상품 URL이 없으면 유사 건강식품 키워드로 재검색하고, 리뷰수/평점이 있으면 우선 점수화한다. 최종 API URL이 없으면 후보 제외.
- `golf/G스케줄러/golf_24h_random_15_scheduler.py`: 스케줄러가 개별 작업마다 `post_type`을 배정. 기본 15개는 골프 10개 + 건강식품 5개, 옵션은 `--golf-posts`, `--health-posts`.
- 스케줄러 등록: 부모 작업 `Tistory_Golf_24H_Random_15`은 2026-05-13 00:05부터 매일 `--max-posts 15 --golf-posts 10 --health-posts 5`. 오늘 개별 작업 10개는 14:30 golf, 15:32 health, 16:40 golf, 17:52 golf, 18:50 health, 19:24 health, 20:55 health, 21:28 health, 22:09 golf, 23:35 golf. 11~15번은 Disabled 유지.

### 검증

- `.venv\Scripts\python.exe -m py_compile` 통과: `golf/main_golf.py`, `golf/G스케줄러/golf_24h_random_15_scheduler.py`, `src/tistory_automation/coupang/api.py`.
- `git diff --check` 통과.
- `--today-only --max-posts 10 --golf-posts 5 --health-posts 5 --dry-run`에서 비율 배정 확인 후 실제 등록.
- `schtasks /Query`로 부모 작업, 1번 golf, 2번 health, 10번 golf 및 11/12/15번 Disabled 확인.
- `golf/건강식품_db.csv` 157행과 필수 컬럼 확인. 샘플 프롬프트 조립에서 건강식품/골프 전문성 규칙 포함 확인.

### 다음 세션

- 먼저 `runtime/logs/scheduled_golf/`, `runtime/logs/golf_24h_random_15/`, 티스토리 실제 글 목록에서 오늘 14:30 이후 작업 성공 여부 확인.
- health 작업 실패 시 쿠팡 API 검색/유사 검색 결과와 “API URL 없는 후보 제외” 로그를 먼저 본다. CSV 일반 링크 fallback은 다시 넣지 않는다.
- 골프 본문이 다시 이미지 이후 멈추면 `runtime/logs/chatgpt_web_runs_golf.csv`, `runtime/outputs/generated_results_golf/`, 실행 중 `pythonw/chromedriver` 중복 여부를 확인한다.
- 스케줄러 재등록/비활성화/삭제, 공개 발행 재시도, 사용 기록 삭제는 사용자 명시 승인 후 진행한다.
- 18:34 확인: 15:32 health는 이미지 2 생성에서 `스트리밍이 중지되었습니다` 후 타임아웃, 17:52 golf는 Task Scheduler `Last Result: 101`이며 실행 로그 없음. 이후 health 흐름은 이미지 1장만 생성하도록 변경했다.

## 2026-05-11 - 티스토리 자동화 ing

### 다음 세션 핵심

- 현재 티스토리 `main.py`/`main_golf.py` 관련 Windows 작업 스케줄러는 모두 비활성 상태다. 재개 전 `TistoryChatGPTAutoPost_*`, `Tistory_Golf_24H_Random*`, `TestPythonW`가 `Disabled`인지 확인하고, 사용자 승인 없이는 재활성화하지 않는다.
- 골프 글은 `golf/main_golf.py` 전용, 쿠팡/일상 글은 `src/tistory_automation/main.py` 전용이다. daily 프롬프트에 골프 축을 다시 넣지 않는다.
- 오늘 검증: `main.py`/`main_golf.py` py_compile 통과, 프롬프트 JSON 파싱 통과, daily 골프 금지어 샘플 차단, 스케줄러 33개 `Disabled`/`Next Run Time=N/A` 및 관련 실행 프로세스 없음 확인.
- 다음 작업: 사용자가 자동화 재개를 원하면 스케줄러 재활성화 범위부터 합의한다. 재개 후 첫 골프 실행은 `runtime/logs/scheduled_golf/` 최신 로그에서 `STEP 3/5` 본문 생성 통과 여부를 확인한다.

- `src/tistory_automation/main.py`: 쿠팡 글 생성 프롬프트에 정량 비교, 단점/주의점, 맞는 사람, 신중히 볼 사람, 판단 근거 필수 조건을 추가.
- `src/tistory_automation/main.py`: 쿠팡 본문 생성 직후 품질 validator를 추가해 정량 비교, 단점, 대상 독자, 근거가 부족하면 중단하고 1회 재작성하도록 보정.
- `src/tistory_automation/main.py`: 상품 요약에 가격, 할인율, 평점, 리뷰수, 배송/설치 정보를 포함해 ChatGPT가 확인 가능한 비교 근거를 쓰도록 보강.
- `src/tistory_automation/main.py`, `config/prompts/chatgpt_web_prompts.json`: 쿠팡 제목에서 상품명 3개 강제 삽입을 제거하고 대표 키워드·독자 문제·선택 기준 중심 제목으로 변경.
- `src/tistory_automation/main.py`: 쿠팡 제휴 링크 후처리를 추가해 모든 쿠팡 링크에 `rel="sponsored nofollow noopener"`와 `target="_blank"`가 붙도록 보정하고 발행 직전 검증을 추가.
- `src/tistory_automation/main.py`: 쿠팡 링크는 상품별 상세 설명 뒤 1회씩만 남기도록 실행 프롬프트를 보강하고, 같은 상품 제휴 링크가 반복되면 뒤쪽 중복 링크를 제거하며 최종 링크 수가 상품 수를 넘으면 중단하도록 추가. CTA 문구도 `최저가/구매하기`보다 약한 `상세 정보 확인` 계열로 완화.
- `config/prompts/chatgpt_web_prompts.json`: 쿠팡 이미지 프롬프트를 특정 제품명/모델/브랜드/패키지 재현이 아닌 로고 없는 중립 비교·사용 상황 이미지로 변경.
- `config/prompts/chatgpt_web_prompts.json`: daily 이미지/본문 프롬프트를 광범위한 오늘 이슈가 아니라 골프여행 준비, 여행 준비·비용, 생활용품/쿠팡 선택 기준 안의 생활형 정보 주제로 제한.
- `golf/main_golf.py`: 골프 사전 리서치 응답에 내부용 확인처 로그 블록을 요구하고 `research_source_log.md`로 별도 저장하도록 추가. 본문 작성용 `research_brief.txt`에서는 확인처 로그를 제거하고 원본은 `research_brief_with_sources.txt`에 보존.
- `golf/main_golf.py`: `data/golf_topic_performance.csv` 또는 `GOLF_TOPIC_PERFORMANCE_CSV_PATH` CSV가 있으면 Search Console/수동 성과 행을 우선 점수화해 골프 주제를 자동 선택하도록 추가. CSV가 없거나 유효 후보가 없으면 기존 ChatGPT/랜덤 주제 선택으로 fallback.
- `golf/main_golf.py`: 기본 실행을 자동 발행이 아니라 티스토리 임시저장으로 변경. `--publish`를 명시한 경우에만 발행하고, `publish=False` 흐름에서는 에디터의 `임시저장` 버튼을 클릭하도록 추가.
- `golf/main_golf.py`: 골프 이미지 생성 뒤 본문 HTML 생성이 멈추는 문제를 줄이기 위해 본문 단계 안정화 보강. 리서치 브리프는 시간·지명·비용·보험·수하물 핵심만 압축해 본문 프롬프트에 넣고, 본문 생성 전 ChatGPT 프로젝트 화면을 재진입하며 실패 시 1회 재시도하도록 추가. 기존 상세도 validator는 유지.
- `src/tistory_automation/main.py`: 쿠팡 글을 제휴 링크 중심 광고글이 아니라 애드센스에도 안전한 편집형 구매 전 체크 가이드로 만들기 위해 작성 기준/확인 범위 문단 자동 삽입, 첫 제휴 링크 전 정보량 검증, 구매 압박 문구 차단, 상품 수 대비 링크 부족/과다 검증을 추가.
- `src/tistory_automation/main.py`, `config/prompts/chatgpt_web_prompts.json`: 쿠팡 body 프롬프트의 이미지/링크 배치/본문 구성 섹션을 구매 전 판단 가이드 구조로 재작성. 하단 링크 재정리와 전체 링크 묶음은 금지하고, 첫 링크 전 선택 기준·정량 비교축·가격/리뷰/배송 확인법을 충분히 쓰도록 변경.
- `src/tistory_automation/main.py`: 쿠팡 상품 요약에 제품별 `선정 이유`를 자동 생성해 포함하고, 본문 프롬프트와 validator에서 상품별 선정 이유가 부족하면 실패하도록 추가.
- `src/tistory_automation/main.py`: 쿠팡 글 품질 점수 리포트 저장 추가. 글자 수, 첫 링크 전 정보량, 제휴 링크 수/rel, 정량 비교, 선정 이유, 단점, 맞는 사람/신중히 볼 사람, 근거, 구매 압박 문구를 100점 기준으로 점수화해 `runtime/reports/coupang_quality/`와 최신 생성 결과에 JSON으로 저장.
- `src/tistory_automation/main.py`: `data/coupang_topic_performance.csv` 또는 `COUPANG_TOPIC_PERFORMANCE_CSV_PATH` 성과 CSV가 있으면 클릭/노출/CTR/순위/수익/쿠팡 클릭/전환/우선순위를 점수화해 쿠팡 주제를 먼저 고르고, 해당 주제와 매칭되는 상품을 우선 선택하도록 추가. CSV가 없거나 매칭 상품이 부족하면 기존 상품 기준으로 자동 fallback.
- `src/tistory_automation/main.py`: 쿠팡 CTA 카드 디자인과 문구를 중립화. 강한 주황 그라데이션, 빨간 가격, 구매형 CTA 대신 회색 정보 확인 카드와 `가격과 옵션 확인`, `상세 스펙 확인`, `리뷰 수 확인` 계열 문구로 통일하고 기존/인라인 카드 후처리도 중립 스타일로 보정.
- `src/tistory_automation/main.py`: 쿠팡 글 작성 기준 문구를 정교화. `공개 상품 정보`, `작성일`, `상세페이지`, `최신`, `변동`, `최종 구매 전`을 필수 확인 문구로 두고, 약한 기존 작성 기준 문단은 후처리에서 중립적인 최신 정보 확인 문단으로 교체하도록 추가.
- `src/tistory_automation/main.py`, `config/prompts/chatgpt_web_prompts.json`: 쿠팡 프롬프트/검증 정합성 보완. 원본 body 프롬프트의 작성 기준 문구를 최신 문구와 맞추고, 성과 CSV의 `conversion` 단수 컬럼을 점수화 대상에 추가하며, `바로가기`를 구매 압박 금지어에 추가.
- `data/coupang_topic_performance.csv`, `data/golf_topic_performance.csv`: 초기 블로그용 외부 시드 성과 CSV 생성. 실제 Search Console 성과가 부족한 단계라 `external_seed`와 `priority` 중심으로 계절가전 쿠팡 키워드, 골프여행 비용·보험·수하물 키워드를 먼저 자동 선택하도록 준비.
- `src/tistory_automation/main.py`: 쿠팡 성과 CSV 주제 반복 방지 추가. 선택된 주제는 `runtime/state/coupang_used_topics.json`에 정규화 키로 저장하고, 기본 14일 동안 같은 주제를 후보에서 제외하도록 보강. 모든 후보가 쿨다운 중이면 자동화가 멈추지 않도록 최고점 후보로 fallback.
- `src/tistory_automation/main.py`, `config/prompts/chatgpt_web_prompts.json`: 골프 주제가 `main.py` daily 흐름에서 생성되는 문제를 원복. daily 프롬프트에서 골프여행/골프백 축을 제거하고 일반 여행·생활용품 축만 허용. daily 결과에 골프, 골프백, 라운딩, 그린피, 캐디 등 금지어가 감지되면 발행 전 중단하도록 validator 추가.
- 검증: `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과.
- 검증: 편집형 쿠팡 글 보강 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과.
- 검증: 쿠팡 body 프롬프트 재작성 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과, JSON 파싱 통과, 실제 조립/원본 프롬프트에서 기존 하단 링크 묶음 문구 제거 확인.
- 검증: 제품별 선정 이유 필수화 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과, 상품 요약/본문 프롬프트에 선정 이유 요구가 포함되는지 확인.
- 검증: 품질 점수 리포트 추가 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과, 로컬 샘플 HTML 분석 점수 100점/통과 확인.
- 검증: 성과 CSV 기반 주제 선택 추가 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과, 샘플 성과 행 점수화/상품 매칭/프롬프트 키워드 반영 확인.
- 검증: CTA 카드 중립화 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과, 샘플 카드/인라인 링크 변환에서 주황 그라데이션/구매 압박 문구 제거 및 중립 CTA 포함 확인.
- 검증: 작성 기준 문구 정교화 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과, 샘플 HTML에서 약한 작성 기준 문단이 필수 문구를 포함한 단일 정교화 문단으로 교체되는지 확인.
- 검증: 쿠팡 프롬프트/검증 정합성 보완 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과, `config/prompts/chatgpt_web_prompts.json` JSON 파싱 통과, 최신 작성 기준 문구/`conversion`/`바로가기` 반영 확인.
- 검증: 초기 외부 시드 CSV 생성 후 `data/coupang_topic_performance.csv` 15행, `data/golf_topic_performance.csv` 12행 CSV 파싱 통과. `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py`, `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py` 통과.
- 검증: 쿠팡 topic 반복 방지 보강 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과, 인메모리 사용 이력으로 동일 주제 쿨다운 판정 `True`와 다음 후보 선택 확인, 성과 CSV 주제 선택 정상 동작 확인.
- 검증: main.py daily 골프 분리 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py` 통과, `config/prompts/chatgpt_web_prompts.json` JSON 파싱 통과, daily 금지어 validator 샘플 차단 확인. 수정 전 프롬프트로 실행 중이던 `main.py --post-type daily --scheduled --publish`와 연결 chromedriver는 사용자 승인 후 중단.
- 검증: `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py` 통과.
- 검증: 기본 임시저장 변경 후 `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py` 통과.
- 검증: 골프 본문 단계 안정화 보강 후 `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py` 통과, 최신 실패 사례 기준 본문 프롬프트 길이 17,575자 → 8,954자로 감소 확인, 압축 리서치에 시간표·비용 수치·수하물/보험 핵심 포함 확인.
- 검증: `config/prompts/chatgpt_web_prompts.json` JSON 파싱 통과.
- 검증: `config/prompts/chatgpt_web_prompts.json` daily 프롬프트 범위 축소 후 JSON 파싱 통과.
- 다음 세션: 티스토리 자동화 재개 전 스케줄러 재활성화 범위부터 사용자와 합의한다. 현재는 33개 모두 비활성 상태라 자동 실행되지 않는다. 재개 후 첫 골프 실행은 `runtime/logs/scheduled_golf/` 최신 로그에서 `STEP 3/5` 본문 생성이 통과하는지 확인한다.
- 운영 주의: 골프 본문 안정화 작업에서 상세도 validator를 우회하지 말 것. 본문 프롬프트를 줄일 때도 시간표, 예상 비용, 이동수단, 골프장 후보, 식당/관광, 보험·수하물 핵심은 유지한다.
- 운영 변경: 사용자 요청으로 티스토리 `main.py`/`main_golf.py` 관련 Windows 작업 스케줄러 33개를 삭제하지 않고 비활성화. 대상은 `TistoryChatGPTAutoPost_*`, `TistoryChatGPTAutoPost_RefreshDaily`, `Tistory_Golf_24H_Random*`, `TestPythonW`. 검증 시 모두 `Disabled`, `Next Run Time=N/A`, 관련 실행 프로세스 없음.

## 2026-05-08 - 티스토리 자동화 ing

- `golf/main_golf.py`: ChatGPT 프롬프트 전송 검증 추가. 전송 후 입력창이 비워졌는지 확인하고, 텍스트 응답 대기 중 자동 재전송은 중복 본문 생성을 막기 위해 제거.
- `golf/main_golf.py`: `--private` 옵션 추가. 비공개 발행 1건 테스트 성공: `사이판 골프여행 골프백 수하물 보험, 3박5일 비용 기준`.
- `golf/main_golf.py`: 해외 골프여행 리서치 금액 검증에서 `$`, `US$`, `USD` 접두 표기도 인식하도록 보정.
- 검증: `py_compile golf/main_golf.py`, `git diff --check -- golf/main_golf.py` 통과. 실제 비공개 발행은 이미지 생성, 본문 사진 업로드, 대표이미지 추가, 비공개 선택까지 완료.
- 다음 세션: `/92` 같은 시간대별 동선 표가 접히는 문제를 스킨 CSS로 본문 폭/테이블 가로 스크롤 개선. 이후 `main_golf.py` 프롬프트에서 일정표를 5열 이하로 줄이는 보정 검토.

## 2026-05-13 - 티스토리 자동화 ing

- `src/tistory_automation/main.py`: 쿠팡 본문 프롬프트를 축소. HTML 인라인 스타일 전체 규칙과 긴 중복 품질 조건을 ChatGPT 입력에서 제거하고, 본문 구조/금지어/링크 마커 중심의 짧은 프롬프트로 교체.
- `src/tistory_automation/main.py`: 쿠팡 링크를 `[PRODUCT_LINK_1]` 마커로 보내고 생성 후 실제 파트너스 URL로 로컬 치환하도록 변경. 긴 URL 3개가 본문 프롬프트에 직접 들어가던 부담을 제거.
- `src/tistory_automation/main.py`: 쿠팡 본문 후처리에서 p/h2/h3/ul/li/blockquote/figure/img/div 주요 태그 인라인 스타일을 자동 보정하고, 고지문은 항상 스타일 포함 첫 줄로 정규화.
- `src/tistory_automation/main.py`: API 치환 상품을 성과 주제어 기준으로 한 번 더 필터링. 에어컨 주제에 오븐/차량 거치대처럼 무관한 API 상품이 섞이는 케이스를 제외.
- `src/tistory_automation/main.py`: 쿠팡 대표사진 업로드 마커를 첫 쿠팡 링크 뒤가 아니라 본문 `%%IMAGE1_PLACEHOLDER%%` 위치에 우선 배치하도록 변경.
- 검증: `티스토리 자동화 ing\.venv\Scripts\python.exe -X utf8 -m py_compile 티스토리 자동화 ing/src/tistory_automation/main.py` 통과. 샘플 쿠팡 본문 프롬프트 길이 1,763자, `IMAGE2_PLACEHOLDER` 미포함, `[PRODUCT_LINK_1]` 포함 확인.
- `src/tistory_automation/main.py`: 쿠팡 이미지 생성과 이미지 base64 보관이 끝난 뒤 본문 프롬프트 전송 전 10초 고정 대기 추가. 이미지 직후 너무 빠른 텍스트 프롬프트 전송으로 ChatGPT 스트리밍이 중지되는지 확인하기 위한 안정화 변경.
- 검증: 10초 대기 추가 후 `티스토리 자동화 ing\.venv\Scripts\python.exe -X utf8 -m py_compile 티스토리 자동화 ing/src/tistory_automation/main.py` 통과.
- `src/tistory_automation/main.py`: 사용자 관찰 결과를 반영해 쿠팡 이미지 보관 후 10초 대기 뒤 ChatGPT 대화창을 1회 새로고침하고 입력창 안정화 후 본문 프롬프트를 전송하도록 변경.
- 검증: 새로고침 안정화 추가 후 `티스토리 자동화 ing\.venv\Scripts\python.exe -X utf8 -m py_compile 티스토리 자동화 ing/src/tistory_automation/main.py` 통과. 같은 시각 기존 실행은 `image -> body -> title -> hashtags` 로그까지 진행 확인.
- `src/tistory_automation/main.py`: 새로고침 위치를 사용자 관찰 흐름에 맞게 재조정. 이제 쿠팡 이미지를 보관한 뒤 10초 대기하고 본문 프롬프트를 먼저 전송한 다음, ChatGPT의 스트리밍 중지 문구가 감지되고 사라진 시점에만 대화창을 1회 새로고침한다. 본문 단계는 중복 전송 방지를 위해 45초 자동 재전송을 끈다.
- 검증: 새로고침 위치 재조정 후 `티스토리 자동화 ing\.venv\Scripts\python.exe -X utf8 -m py_compile 티스토리 자동화 ing/src/tistory_automation/main.py` 통과.
- `src/tistory_automation/main.py`: 성과 주제 API 치환에서 주제 관련 상품이 2개 미만이면 같은 주제 검색어/파생 검색어로 추가 API 보강하도록 변경. 에어컨 주제에서 API가 냉장고/전기레인지 등 무관 상품을 반환해 필터링된 뒤 비교 상품이 1개만 남는 실패를 보완.
- 검증: 주제 검색어 보강 추가 후 `티스토리 자동화 ing\.venv\Scripts\python.exe -X utf8 -m py_compile 티스토리 자동화 ing/src/tistory_automation/main.py` 통과.
- `golf/main_golf.py`: 건강식품 쿠팡 글의 이미지 후 본문 단계에 main.py와 같은 안정화 흐름 적용. 이미지 1장 보관 뒤 10초 대기하고 본문 프롬프트를 먼저 전송한 다음, ChatGPT 스트리밍 중지 문구가 감지되고 사라지면 대화창을 1회 새로고침해 응답을 이어 받는다.
- 검증: `티스토리 자동화 ing\.venv\Scripts\python.exe -X utf8 -m py_compile 티스토리 자동화 ing/golf/main_golf.py` 통과.
- `golf/main_golf.py`: 건강식품 쿠팡 본문 후처리 인라인 스타일의 글자 크기 확대. 본문 `<p>` 15px→16px, 리스트 `<li>` 14px→15px, 소제목 `<h2>` 19px→21px, 소소제목 `<h3>` 16px→18px로 조정.
- 검증: 글자 크기 조정 후 `티스토리 자동화 ing\.venv\Scripts\python.exe -X utf8 -m py_compile 티스토리 자동화 ing/golf/main_golf.py` 통과.
- `config/prompts/chatgpt_web_prompts.json`: 쿠팡 이미지 프롬프트에 `{keyword}`와 `{product_names}` 입력을 추가. 글 대상 상품명을 시각 맥락으로 반영하되, 로고/텍스트/실제 제품 외형 복제 금지는 유지.
- 검증: `config/prompts/chatgpt_web_prompts.json` JSON 파싱 통과, `.venv\Scripts\python.exe -X utf8 -m py_compile .\src\tistory_automation\main.py` 통과, `git diff --check` 통과.

### 다음 세션 인수인계

- 오늘 핵심 변경: `main.py` 쿠팡 본문 프롬프트 축소, 쿠팡 링크 마커 치환, 이미지 1장 흐름, API 주제 관련성 필터/보강, 이미지 후 본문 전송 안정화 적용. `main_golf.py` health도 같은 안정화 흐름을 적용했고 건강식품 본문 글자 크기를 확대.
- 검증: `main.py`/`main_golf.py` `py_compile` 통과. `main.py --post-type coupang --draft`는 임시저장 성공, `main_golf.py --post-type health --publish`는 공개 발행 성공. 마지막 확인 기준 잔여 `chromedriver` 없음.
- 운영 주의: `main.py` 쿠팡글은 임시저장 운영, `main_golf.py --post-type health`는 건강식품 쿠팡 공개 발행 가능. `G스케줄러`의 health 작업은 `--publish`로 등록될 수 있으니 실행/비활성화/재등록 전 사용자 확인 필요.
- 다음 작업: 남은 `Tistory_Golf_24H_Random*` health 로그에서 같은 스트리밍 중지 후 새로고침 흐름이 통과하는지 확인. health 발행을 중단하거나 임시저장으로 바꿀지 사용자와 정책 결정. 카테고리 선택 경고가 반복되면 티스토리 카테고리 선택 로직만 별도 점검.
- 추가 변경: 이미지 뒤 첫 본문 프롬프트 안정화 로직을 `main.py` 일상/쿠팡, `main_golf.py` 골프/health/일상 전체에 적용. 스트리밍 중지 문구가 사라지면 즉시 새로고침하지 않고 3초 대기 후 새로고침한다. 정상 응답이 시작되면 새로고침 감시는 종료한다.
- 검증: 전체 적용 후 `티스토리 자동화 ing\.venv\Scripts\python.exe -X utf8 -m py_compile 티스토리 자동화 ing/src/tistory_automation/main.py`, `티스토리 자동화 ing\.venv\Scripts\python.exe -X utf8 -m py_compile 티스토리 자동화 ing/golf/main_golf.py` 통과. 잔여 `chromedriver` 없음.
