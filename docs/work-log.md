# Work Log

## 2026-05-28

### 티스토리 자동화 ing

- 변경사항
  - `camp-platform/public/HTML편집.txt`: 티스토리 스킨 편집용 HTML에 AdSense 기본 로더와 본문 중간 자동 삽입 스크립트 추가.
  - 본문 중간 광고는 `#article-view` 로드 후 JS가 `.tistory-mid-adsense` 래퍼로 삽입하며, 슬롯은 `3825649038` 사용. 기존 `[##_revenue_article_upper_##]`, `[##_revenue_article_lower_##]`는 유지.
  - AdSense client 값은 `.env`의 기존 `VITE_ADSENSE_CLIENT`에서 파일에 치환했고, 원문 값은 문서/답변에 남기지 않음.
- 검증
  - `HTML편집.txt`에서 `ca-pub-` 존재, `__TISTORY_ADSENSE_CLIENT__` 미검출 확인.
  - `HTML편집.txt`에서 `3825649038`, `insertMidArticleAd`, `data-ad-slot`, `adsbygoogle.push` 존재 확인.
  - 실제 티스토리 스킨 저장/공개 글 확인은 아직 수행하지 않음.
- 다음 작업
  - `HTML편집.txt` 전체를 티스토리 관리자 `꾸미기 > 스킨 편집 > html 편집`에 반영.
  - 공개 글 확인은 `페이지 소스 보기`가 아니라 DevTools Elements에서 `.tistory-mid-adsense` 또는 `3825649038` 검색으로 확인.
  - 하단 슬롯과 구분이 필요하면 AdSense에서 본문 중간 전용 디스플레이 광고 단위를 새로 만든 뒤 `ADS_SLOT`만 교체.

## 2026-05-27

### 네이버 자동화 ing/네이버 블로그 글쓰기/skssj2628

- 변경사항
  - `skssj2628.py`의 실행 설정에서 네이버 비밀번호 문자열 리터럴을 제거하고, `--naver-password` 인자 또는 `NAVER_PASSWORD` 환경변수에서만 읽도록 보정.
  - `skssj2628.py`에 `--login`/`--gemini-login` 옵션을 추가해 Gemini 웹사이트 로그인 세션만 저장하고 발행 흐름 전 종료할 수 있게 보강.
  - `skssj2628.py`의 Gemini 모드 선택을 기존 사고 모델 selector에서 `Gemini 3.1 Pro` 텍스트 기반 선택 로직으로 변경.
  - `skssj2628.py`가 일반 `NAVER_ID`/`NAVER_PROFILE_PATH` 환경변수 영향으로 `skssj2627` 프로필을 쓰던 문제를 차단. 기본 네이버 ID를 `skssj2628`로 고정하고 계정 전용 `SKSSJ2628_NAVER_*` 변수만 우선 사용하도록 변경.
  - `skssj2628.py`에 `--naver-login` 옵션을 추가해 네이버 세션만 저장할 수 있게 보강.
  - `skssj2628(스케줄러).py`가 예약 작업 명령에 `--naver-id "skssj2628"`를 명시하도록 변경.
  - `skssj2628.py` 쿠팡 딥링크 실패 흐름 확인: 변환 실패 상품은 원본 링크를 쓰지 않고 다음 CSV 후보로 넘어가며, 현재 유사상품 API 검색 fallback은 없음.
- 검증
  - 하드코딩된 `naver_password` 문자열 리터럴 패턴 미검출.
  - `python -m py_compile "네이버 자동화 ing\네이버 블로그 글쓰기\skssj2628\skssj2628.py"` 통과.
  - `python "네이버 자동화 ing/네이버 블로그 글쓰기/skssj2628/skssj2628.py" --help`에서 `--login, --gemini-login` 옵션 노출 확인.
  - `skssj2628.py`에서 `Gemini 3.1 Pro` 선택 문자열 확인 및 구 `사고 모델` selector 미검출.
  - 일반 `os.getenv("NAVER_ID"` 패턴 미검출.
  - `python "네이버 자동화 ing/네이버 블로그 글쓰기/skssj2628/skssj2628.py" --help`에서 `--naver-login` 옵션 노출 확인.
  - `python -m py_compile "네이버 자동화 ing\네이버 블로그 글쓰기\skssj2628\skssj2628.py" "네이버 자동화 ing\네이버 블로그 글쓰기\skssj2628\skssj2628(스케줄러).py"` 통과.
  - `schtasks /Query /TN "NaverBlogAutoPost_skssj2628_01" /V /FO LIST` 확인: 기존 등록 작업은 아직 `--naver-id "skssj2628"`가 없는 예전 명령이었음.
  - `git diff --check -- "네이버 자동화 ing/네이버 블로그 글쓰기/skssj2628/skssj2628.py"` 통과. LF/CRLF 경고만 출력됨.
- 다음 작업
  - `skssj2628.py --naver-login`으로 `skssj2628` 네이버 세션 저장 후 `skssj2628(스케줄러).py --target-date auto`를 다시 실행해 기존 작업을 새 명령으로 재등록.
  - 재등록 후 `schtasks /Query`로 `NaverBlogAutoPost_skssj2628_01` 명령에 `--naver-id "skssj2628"`가 들어갔는지 확인.
  - 다음 `skssj2628` 실행 로그에서 네이버 프로필 경로가 `ChromeNaverBot_skssj2628`인지, Gemini가 임시 채팅 후 `Gemini 3.1 Pro`로 진행하는지 확인.
  - 쿠팡 딥링크 실패가 잦으면 유사상품 API 검색 fallback 추가 여부를 사용자와 합의.

### 티스토리 자동화 ing

- 변경사항
  - `golf/main_golf.py`: 티스토리 HTML 작성 순서를 고정하고, 건강식품 쿠팡 후보/API 보강/URL 사용 기록을 실패 시 고갈되지 않게 보정.
  - `golf/G스케줄러/golf_24h_random_15_scheduler.py`: 하루 14개, 골프 7개 + 건강식품 쿠팡 7개 기본값으로 변경하고 초과 예약 `_15` 정리 로직 추가.
  - 사용자 승인 후 골프/건강식품 공개 발행 스케줄 14개와 `scheduler.py --draft` 일반 티스토리 임시저장 스케줄 10개를 등록. 티스토리 세션은 `runtime/sessions/tistory/.session_ready`로 저장됨.
  - `main.py`: 쿠팡 상품 사용 처리/URL 로그/성과 주제 이력을 티스토리 작성 성공 후 확정하도록 이동. CSV 후보가 비어도 성과 주제 검색어 확장으로 API 보강을 시도.
  - `keyword_crawler.py`, `category_detail_crawler.py`: 새 크롤링 저장 시 `runtime/logs/used_coupang_urls.csv`의 과거 사용 상품 키와 DB 내부 중복을 제외. `keyword_crawler.py`는 `--query` 생략 시 콘솔 입력 지원.
  - `category_crawler.py`: 클릭 흐름을 `로켓배송 > 가전디지털 > 계절가전`까지만 수행하도록 변경. 마지막 대상 텍스트 클릭과 판매량순 정렬 클릭 제거.
  - `products_db_category.csv`: 기존 사용 불가 100행 제거 후 새로 크롤링한 100행 중 과거 사용 URL과 겹친 1행만 삭제. 현재 99행, 중복 0개.
  - 디버깅 Chrome은 `127.0.0.1:9222`, 현재 Chrome 148에는 `C:\Users\itwill\.wdm\drivers\chromedriver\win64\148.0.7778.178\chromedriver-win32\chromedriver.exe`를 명시해야 함.
- 검증
  - `py_compile` 통과: `main.py`, `golf/main_golf.py`, `golf_24h_random_15_scheduler.py`, `keyword_crawler.py`, `category_detail_crawler.py`, `category_crawler.py`.
  - 오프라인 monkeypatch 검증 통과: 실패 전 쿠팡 사용 처리 방지, 빈 DB 성과 주제 API 보강, 크롤러 과거 사용 URL 제외, `keyword_crawler.py` 입력 방식, `category_crawler.py` 클릭 순서.
  - `schtasks /Query`로 골프/건강식품 14개 스케줄과 일반 티스토리 draft 10개 및 `RefreshDaily` 등록 확인.
  - `products_db_category.csv` 재검사: 99행, 과거 사용 URL 중복 0, DB 내부 중복 0, 링크 파싱 실패 0.
  - `git diff --check` 통과. `docs/work-log.md` LF/CRLF 경고만 있음.
- 다음 작업
  - 새 세션 시작 시 최근 스케줄 로그에서 실패/성공을 먼저 확인: `runtime/logs/scheduled/`, `runtime/logs/scheduled_golf/`.
  - `products_db_category.csv`를 추가 크롤링하면 반드시 `used_coupang_urls.csv` 중복 검사 후 겹친 행만 제거하고 백업을 남긴다.
  - `category_crawler.py` 흐름은 계절가전까지만 클릭하는 현재 동작을 유지. 대상 텍스트 클릭/판매량순 정렬을 되돌리지 않는다.
  - 실제 쿠팡 API, 크롤링 대량 실행, 발행/스케줄러 재등록은 사용자 승인 후 진행.

## 2026-05-15

### 네이버 자동화 ing/네이버 블로그 글쓰기/skssj2628

- 변경사항
  - `skssj2628.py` 일상글을 장마습기, 냉방전기, 여름위생, 자취집관리, 생활정책돈관리 중심의 세부 검색 의도형 주제로 재지정.
  - 각 주제에 핵심 원리, 정확한 용어, 확인 순서, 실천 포인트, 실수, FAQ, 사실 확인 주의사항을 넣고 본문/제목 프롬프트가 이를 쓰도록 보강.
- 검증
  - `python -m py_compile "네이버 자동화 ing\네이버 블로그 글쓰기\skssj2628\skssj2628.py"` 통과.
  - `git diff --check -- "네이버 자동화 ing\네이버 블로그 글쓰기\skssj2628\skssj2628.py"` 통과. LF/CRLF 경고만 출력됨.
- 다음 작업
  - 다음 `skssj2628` 일상 발행 로그/실제 글에서 원인 설명, 정확한 용어 풀이, 확인 순서가 충분한지 확인.
  - 여전히 얕으면 주제별 본문 후검증 또는 재작성 조건 추가 검토.

### 네이버 자동화 ing/네이버 블로그 글쓰기/skssj2629

- 변경사항
  - `자동발행실행보조파일/run_refresh_schedule.ps1`: `RefreshDaily` 실행 시 `자동발행상태기록파일/logs/*_RefreshDaily.log`에 시작 시각, 프로젝트 경로, Python 경로, 스케줄러 파일 경로, refresh time, 실행 출력, 종료코드를 남기도록 추가.
  - Windows PowerShell이 UTF-8 BOM 없는 스크립트의 한글 파일명 리터럴을 잘못 읽을 수 있어 `skssj2629(스케줄러).py`와 상태 폴더를 한글 문자열로 직접 지정하지 않고 ASCII 패턴/기존 상태 파일로 찾도록 변경.
  - Python 출력 인코딩을 UTF-8로 고정해 이후 refresh 로그에서 한글 출력이 깨질 가능성을 줄임.
  - 사용자 승인 후 `run_refresh_schedule.ps1 -RefreshTime 00:05`를 실행해 2026-05-15 남은 시간 기준 `NaverBlogAutoPost_2629_01`~`10`과 `NaverBlogAutoPost_2629_RefreshDaily`를 재등록.
- 검증
  - `run_refresh_schedule.ps1` PowerShell 파서 검사 통과.
  - `run_refresh_schedule.ps1` 실행 종료코드 0.
  - `daily_schedule.json`이 `target_date=2026-05-15`, `generated_at=2026-05-15 09:29:24`로 갱신됨.
  - `schtasks /Query`로 `_01`~`_10` 다음 실행 시간이 2026-05-15 09:45~23:27, `RefreshDaily` 다음 실행 시간이 2026-05-16 00:05로 등록된 것을 확인.
- 다음 작업
  - 2026-05-16 00:05 이후 `*_RefreshDaily.log`와 작업 스케줄러 `Last Result`가 0인지 확인.
  - 다음 실패 시 새 refresh 로그의 `exit_code`와 Python 출력으로 원인을 확인.

## 2026-05-13

### 티스토리 자동화 ing

- 변경사항
  - `golf/main_golf.py`: 건강식품 쿠팡 본문 프롬프트를 짧은 전용 템플릿으로 분리해 ChatGPT 웹 본문 생성이 긴 인라인 스타일 지시와 전체 쿠팡 URL 때문에 멈추는 문제를 완화.
  - 건강식품 상품 요약에는 실제 쿠팡 URL 대신 `[PRODUCT_LINK_N]` 마커만 넣고, 생성 후 실제 URL로 치환하도록 변경.
  - 티스토리 인라인 스타일은 ChatGPT 출력에 강제하지 않고 로컬 후처리에서 `p/h2/h3/ul/li/a/img/strong`에 적용하도록 추가.
  - 쿠팡 고지문은 기존 문구가 있어도 제거 후 맨 위에 고정 스타일로 재삽입하도록 보강.
  - 건강식품 쿠팡 이미지 프롬프트를 전용 템플릿으로 분리. 상품명/키워드에서 레몬즙, 프로틴 드링크, 콘드로이친/영양제 등 제품군 단서를 뽑아 generic unbranded 이미지로 생성하게 변경.
  - 건강식품 이미지 생성 후 바로 본문 프롬프트를 넣지 않고, 골프 글처럼 ChatGPT 프로젝트 대화 화면을 다시 열고 입력창 안정화 후 본문 프롬프트를 전송하도록 변경.
  - 건강식품 이미지 프롬프트를 비교용 분위기 사진이 아니라 첫 번째 광고 상품 타입을 실제 사용하는 장면 중심으로 재수정. 예: 레몬즙은 물컵에 짜는 손, 프로틴은 마시거나 따르는 장면, 콘드로이친/영양제는 물과 함께 준비하는 장면.
  - 공개 발행 시 본문 업로드 이미지와 같은 파일을 발행창 대표이미지로 지정한다는 로그를 추가. 대표이미지 업로드 경로는 골프 글과 같은 발행창 `대표이미지 추가` input 방식 유지.
  - 사용자 요청으로 `golf_24h_random_15_scheduler.py --today-only --max-posts 14 --golf-posts 10 --health-posts 4`를 실행해 2026-05-13 남은 시간에 골프 10개, 건강식품 쿠팡 4개 공개 발행 작업을 등록.
  - `src/tistory_automation/main.py`: `--draft` 옵션을 추가하고, 발행하지 않는 경우에도 본문 이미지 업로드 후 발행창 대표이미지 지정까지 시도한 뒤 임시저장하도록 변경.
  - `src/tistory_automation/scheduler.py`, `scripts/scheduled/run_scheduled_post.ps1`, `scripts/scheduled/run_refresh_schedule.ps1`: `--draft`/`-Draft` 모드를 추가해 스케줄러가 공개 발행 대신 임시저장 작업으로 등록되도록 변경.
  - 사용자 요청으로 `scheduler.py --target-date auto --draft`를 실행해 `TistoryChatGPTAutoPost_01`~`10` 및 `TistoryChatGPTAutoPost_RefreshDaily`를 임시저장 모드로 등록.
  - `main.py` 쿠팡 임시저장 스케줄이 상품 선별 단계에서 바로 종료된 원인을 확인. CSV 후보는 미사용이어도 쿠팡 API 보강 결과가 `used_coupang_urls.csv`의 과거 사용 상품과 다시 겹치면서 2개 미만만 남는 문제였음.
  - `src/tistory_automation/coupang/api.py`: 쿠팡 API 상품 선택 시 호출자가 넘긴 사용 URL 키를 제외하도록 `excluded_url_keys`/`url_key_func` 옵션 추가.
  - `src/tistory_automation/main.py`: 쿠팡 API 보강 단계에 `used_coupang_urls.csv` 기반 상품 키를 넘기고, 2개 미만일 때 로그에 seed/enriched/used/chosen 개수를 남기도록 보강.
  - 사용자 피드백 반영: `main.py` 쿠팡 글의 고정 12개 후보 선별을 제거하고, CSV 미사용 상품을 순서대로 보면서 API 상품으로 치환해 3개가 채워지면 멈추도록 변경. API 검색 결과가 없으면 유사 검색으로 넘어가며, 유사 상품은 리뷰 수 우선으로 선택.
  - `main.py` 일반 쿠팡 글이 이미지 1 생성 후 이미지 2 생성 대기에서 타임아웃나는 문제를 확인. 일반 쿠팡 글도 생성 이미지는 1장만 쓰도록 `generate_article()`에서 이미지 2 생성 단계를 제거하고, 본문 프롬프트도 단일 이미지 기준으로 보정.
  - `main.py`, `golf/main_golf.py`: 스케줄 실행 중 오류가 나면 브라우저를 열어 두지 않고 닫도록 변경해 같은 `runtime/sessions/chatgpt` 프로필을 쓰는 다음 작업과 충돌하지 않게 보강.
- 검증
  - `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py` 통과.
  - `git diff --check -- "티스토리 자동화 ing/golf/main_golf.py"` 통과. LF/CRLF 경고만 출력됨.
  - `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py .\src\tistory_automation\scheduler.py` 통과.
  - `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py .\src\tistory_automation\coupang\api.py` 통과.
  - 외부 API 호출 없이 `_pick_best_api_product()`가 과거 사용 URL 키를 건너뛰고 다음 후보를 선택하는지 단위 확인.
  - 외부 API 호출 없이 유사 상품 선택이 순위보다 리뷰 수가 많은 상품을 우선 선택하는지 단위 확인.
  - `main.py`, `golf/main_golf.py` 문법 검사 통과.
  - 외부 API/브라우저 호출 없이 `main.py` 쿠팡 본문 프롬프트 생성 검증: `%%IMAGE2_PLACEHOLDER%%`, `이미지2`, `두 번째 이미지` 없음, 단일 이미지 규칙 포함.
  - `run_scheduled_post.ps1`, `run_refresh_schedule.ps1` PowerShell scriptblock 파서 검사 통과.
  - 브라우저 없이 함수 검증: 건강식품 본문 프롬프트 약 2,025자, 프롬프트 내 쿠팡 URL 없음, `%%IMAGE2_PLACEHOLDER%%` 없음, 링크 마커 치환 및 고지/제목/리스트 스타일 후처리 확인.
  - 사용자 요청 후 `.venv\Scripts\python.exe -X utf8 .\golf\main_golf.py --post-type health --draft` 실행. 건강식품 쿠팡 본문/제목/해시태그 생성, HTML 주입, 사진 업로드, 임시저장 완료. 공개 발행은 실행하지 않음.
  - 실행 중 티스토리 카테고리 `데이터분석하는 청년의 꿀템` 선택은 실패했으나 현재 선택값으로 임시저장까지 진행됨.
  - 건강식품 이미지 프롬프트 함수 검증: 약 1,335자, lemon/protein/supplement 제품군 단서 포함, `%%IMAGE2_PLACEHOLDER%%` 없음.
  - 건강식품 이미지 사용 장면 프롬프트 함수 재검증: 약 1,715자, 첫 상품 레몬즙 사용 장면 focus 포함, product use 지시 포함, `%%IMAGE2_PLACEHOLDER%%` 없음.
  - `schtasks /Query`로 `Tistory_Golf_24H_Random_15_01` 12:30 골프, `_04` 15:10 health, `_14` 23:39 골프 작업이 `Ready` 상태임을 확인.
  - `schtasks /Query`로 `TistoryChatGPTAutoPost_01`, `_10`, `TistoryChatGPTAutoPost_RefreshDaily`가 `Ready`이며 실행 명령에 `-Draft`가 포함됨을 확인.
- 다음 작업
  - 건강식품 쿠팡 글을 공개 발행하기 전 카테고리 선택 실패 원인을 확인한다.
  - 첫 임시저장 스케줄 실행분에서 대표이미지가 실제 임시글에 남는지 티스토리 관리자에서 확인한다.

## 2026-05-12

### 네이버 자동화 ing/네이버 블로그 글쓰기

- 변경사항
  - `네이버커넥팅.py`: Gemini 웹 세션 클래스를 ChatGPT 네이버 전용 프로젝트 세션으로 교체.
  - ChatGPT 프로젝트 URL을 `https://chatgpt.com/g/g-p-6a01727f21208191a66e53986f5cd0ae-neibeo-jeonyong/project`로 고정하고, `CHATGPT_PROFILE_PATH` 또는 기본 `~/ChromeChatGPTNaverConnectBot` 프로필을 사용하도록 추가.
  - `--login`/`--chatgpt-login` 옵션으로 ChatGPT 로그인 세션만 저장하고 종료하는 모드 추가.
  - 기본 네이버 쇼핑커넥트 CSV는 `skssj2629/skssj2629_naver.csv`로 변경.
  - 네이버커넥팅 기본 네이버 블로그 ID를 `skssj2629`로 고정하고, 공용 `NAVER_PROFILE_PATH` 대신 `NAVER_CONNECT_PROFILE_PATH` 또는 `ChromeNaverBot_skssj2629` 계정별 프로필을 쓰도록 변경.
  - `--naver-login` 옵션을 추가해 발행 없이 네이버 `skssj2629` 세션만 저장할 수 있게 변경.
  - 네이버 쇼핑커넥트 발행 성공 후 JSON 이력뿐 아니라 CSV의 `used`, `used_at`, `post_title` 컬럼도 갱신하도록 변경.
  - `skssj2629.py`에서 인용구 뒤 링크/해시태그가 인용구 안에 들어가지 않도록 인용구 탈출 후 일반 본문 서식으로 복귀하는 처리를 보강.
  - `skssj2629/skssj2629_naver.csv`에 사용자가 제공한 유아/출산/교구/아동패션 쇼핑커넥트 상품 24개를 추가.
  - `skssj2629/skssj2629_naver.csv`에 `평점`, `리뷰개수` 컬럼을 추가하고, 본문 프롬프트가 해당 값을 참고하되 보장 표현으로 쓰지 않도록 보강.
  - `skssj2629.py` 일상글/광고글 프롬프트를 "모든 것에 예민한 청담 사는 자녀 둔 어머니" 컨셉으로 조정. 일상글은 청담 미식, 호텔 티타임, 전시/공연, 키즈 클래스, 성분/소재를 따지는 육아 라이프스타일 중심으로 변경.
  - `skssj2629.py` 네이버 쇼핑커넥트 광고글이 평점/리뷰 개수를 본문 참고 정보로 자연스럽게 쓰고, 유아용품을 성분, 면 소재, 월령, 세척, 보관, 아이 동선 기준으로 평가하도록 보강.
  - `skssj2629.py`에 이유식/분유, 수유용품, 유아 스킨/위생, 유아 의류, 장난감/교구, 유아 식기/보관용품 상품군별 작성 가이드를 추가.
  - `skssj2629.py` 네이버 쇼핑커넥트 본문 프롬프트에 상품군별 전문용어 2~4개를 자연스럽게 사용하고, 바로 쉬운 말로 풀어 쓰는 규칙을 추가. 의학/효능 보장 표현은 계속 금지.
  - `skssj2629.py` 일상글/광고글 본문 프롬프트에 말투 리듬 규칙을 추가해 `~합니다`/`~됩니다` 반복을 줄이고, `~하더라고요`, `~거든요`, `~잖아요`, `~편이에요` 같은 청담 엄마 블로그 구어체를 섞도록 조정.
  - `skssj2629.py` 일상글/광고글 본문 프롬프트와 로컬 후처리에 한 줄 25자 안팎의 짧은 본문 흐름을 추가. URL, 해시태그, 네이버 입력 마커는 원형 유지하고, 상품명 텍스트는 바꾸지 않은 채 짧게 줄바꿈 가능.
  - `skssj2629/skssj2629(스케줄러).py`를 `skssj2629.py` 기준으로 수정. 작업명 prefix를 계정별로 분리하고, 발행 타입을 `일상`/`네이버`로 바꾸며, peer schedule 경로와 실행 대상 경로를 조정.
  - `skssj2629/자동발행실행보조파일/run_scheduled_post.ps1`, `run_refresh_schedule.ps1`를 추가해 스케줄러가 부모 폴더의 `제미나이웹.py`가 아니라 `skssj2629.py`와 `skssj2629(스케줄러).py`를 실행하도록 구성.
  - 사용자 승인 후 `skssj2629(스케줄러).py --target-date auto`를 실행해 `2026-05-12` 기준 `NaverBlogAutoPost_2629_01`~`10` 및 `NaverBlogAutoPost_2629_RefreshDaily`를 등록.
  - `AGENTS.md`와 `네이버 자동화 ing/AGENTS.md`에 `skssj2629` 전용 CSV/스케줄러/프롬프트 운영 규칙을 추가.
- 검증
  - `네이버커넥팅.py` AST 문법 검사 통과.
  - `skssj2629.py` AST 문법 검사 통과.
  - `skssj2629(스케줄러).py` AST 문법 검사 통과.
  - `skssj2629` 스케줄 실행/리프레시 PowerShell 래퍼 2개 파서 검사 통과.
  - `schtasks /Query`로 `NaverBlogAutoPost_2629_01`, `NaverBlogAutoPost_2629_RefreshDaily`가 `Ready` 상태임을 확인.
  - `skssj2629/skssj2629_naver.csv` 확인: `rows=43`, `평점`/`리뷰개수` 컬럼 존재, 각 24개 값 populated.
  - `skssj2629.py` 짧은 본문 줄바꿈 변경 후 `py_compile` 통과.
  - `AGENTS.md`, `네이버 자동화 ing/AGENTS.md`, `skssj2629.py` 대상 `git diff --check` 통과. LF/CRLF 경고만 출력됨.
  - `docs/work-log.md` `git diff --check` 통과.
  - 실제 발행/삭제/외부 대량 호출은 실행하지 않음. 스케줄러 등록은 사용자 승인 후 실행.
- 주의
  - `네이버커넥팅.py`는 현재 루트 `.gitignore`의 `네이버 자동화 ing/네이버 블로그 글쓰기/*` 패턴에 의해 Git status에서 ignored로 표시되므로 `git diff --check` 대상에는 잡히지 않음.
- 다음 작업
  - 다음 스케줄 발행 로그에서 `skssj2629/자동발행상태기록파일/logs/` 확인: ChatGPT 세션, 네이버 세션, 인용구 밖 링크/해시태그, CSV used 처리, 말투 자연스러움, 짧은 줄 본문 흐름.
  - 다음 세션에서 `skssj2628.py`와 `제미나이웹.py` 본문 프롬프트도 `skssj2629.py`처럼 가독성 좋은 짧은 줄 흐름과 사람이 쓴 듯한 자연스러운 말투로 보강.
  - 첫 커넥트 수익/클릭이 보이면 상품군, 제목, 평점/리뷰, 링크 위치 기준으로 성과 CSV를 만들지 결정.

## 2026-05-08

### 티스토리 자동화 ing

- 세션 마감 요약
  - 변경: `main.py` 대표이미지 추가를 발행창 `input.inp_g` 업로드로 보강했고, `main_golf.py`는 ChatGPT 이미지 수집/HTML모드 업로드/발행창 대표이미지 업로드/본문 누락 검증/카테고리 자동선택을 보강했다.
  - 변경: 스케줄 등록 공통락 `runtime/locks/schedule_register.lock`을 추가했고, 실제 발행은 기존 공통 `automation.lock`으로 순서 처리한다. PowerShell 예약 실행 로그는 UTF-8 보존 방식으로 수정했다.
  - 변경: `main_golf.py`의 불필요한 쿠팡 파트너스 분기와 미추적 복사본 `golf/main_golf copy.py`를 제거했다. 쿠팡 글은 `src/tistory_automation/main.py`에서만 다룬다.
  - 검증: `py_compile` 통과(`main.py`, `main_golf.py`, `scheduler.py`, `golf_24h_random_15_scheduler.py`), 관련 `git diff --check` 통과, daily 1건 공개 발행 성공, 골프 스킨 제목 좌표 live 확인, `enrich_products_with_coupang_links` 잔존 없음 확인.
  - 다음: 골프 예약 발행 1건에서 본문 표/상세정보 누락 여부, 여러 이미지 본문 위치, 대표이미지 업로드, `C:\Users\itwill\백업용` 임시파일 정리, 예약 로그 UTF-8 출력 상태를 확인한다.

- 변경사항
  - `src/tistory_automation/main.py`: 기존 HTML 모드 사진 업로드 흐름은 유지하고, `완료` 클릭 후 발행창의 대표이미지 추가 파일 input(`input.inp_g`)에 같은 일회성 이미지 파일을 지정한 뒤 `공개 발행`을 누르도록 추가.
  - `scripts/scheduled/run_scheduled_post.ps1`: Windows 작업 스케줄러 로그에서 `main.py` 한글 출력이 깨지지 않도록 PowerShell 콘솔/파이프 인코딩을 UTF-8로 고정하고, `Tee-Object` 대신 `ForEach-Object + Add-Content -Encoding UTF8` 방식으로 Python 출력을 로그에 append하도록 변경.
  - `golf/main_golf.py`: 대표 이미지를 HTML 본문에 `data:image`로 직접 넣지 않고, `TISTORY_ONE_TIME_IMAGE_DIR` 기본값 `Path.home()/백업용`에 일회성 파일로 저장한 뒤 티스토리 HTML 모드에서 `attach-layer-btn` / `attach-image`로 업로드하도록 변경.
  - 골프 본문 저장 단계에서는 이미지 data URL을 본문 HTML에 삽입하지 않고, 티스토리 입력 직전 마커를 배치한 뒤 본문 주입 후 파일 업로드로 치환하도록 조정.
  - `golf/main_golf.py`: 해시태그 입력 후 발행 직전에 기본모드로 전환해 업로드된 첫 사진을 클릭하고 `.mce-represent-image-btn`을 눌러 대표 이미지로 설정하도록 추가.
  - `golf/main_golf.py`: 골프 본문이 데스크톱에서 앱 화면처럼 좁게 보이지 않도록 680px 고정폭 지시와 보정을 `width:100%; max-width:880px` 웹형 레이아웃으로 변경.
  - `golf/main_golf.py`: 티스토리 대표 이미지에서 좌우가 잘리지 않도록 이미지 프롬프트를 16:9 가로형에서 1:1 정사각형, 1200x1200, 중앙 70% 안전영역 구성으로 변경.
  - `golf/main_golf.py`: 사용자가 공유한 티스토리 스킨의 `article-view` 폭을 따르도록 생성 HTML의 `max-width:880px` 제한을 제거하고 `max-width:100%` 기준으로 변경.
  - `C:\Users\itwill\자동화 공부\tistory_golf_skin_fixed.html`: 글 제목이 본문 위에서 치우쳐 보이지 않도록 `article-header`와 `article-view`를 같은 카드 구조로 붙이고 좌측 패딩을 동일하게 맞춤.
  - `C:\Users\itwill\자동화 공부\tistory_golf_skin_fixed.html`: 기존 스킨의 `article-header` 상대 위치값 때문에 제목 박스가 오른쪽으로 503px 밀리던 문제를 `left:0`과 `::before` 오버레이 비활성화로 보정. 기존 글 본문 안의 `width: 680px` 인라인 스타일도 폭 보정 대상에 추가.
  - `golf/main_golf.py`: 골프 글 발행 시 제목/주제/본문을 기준으로 티스토리 카테고리를 자동 선택하도록 변경. 웰링턴CC, 트리니티클럽, 잭니클라우스GC 코리아, 골프장 비교, 해외/미국/일본/유럽 명문 골프장으로 분기하고 실패 시 상위 카테고리로 fallback.
  - `scripts/scheduled/*.ps1`: 예전 PC 경로 `C:\Users\pong3\WORKING_HAPPY\...`와 Python314 하드코딩을 제거하고, 스크립트 위치 기준 프로젝트 루트와 로컬 `.venv\Scripts\python.exe`를 사용하도록 변경.
  - `src/tistory_automation/scheduler.py`, `golf/G스케줄러/golf_24h_random_15_scheduler.py`: 여러 스케줄러가 동시에 예약표/Windows 작업을 등록하지 않도록 공통 `runtime/locks/schedule_register.lock`을 추가. 실제 발행용 `automation.lock`은 기존 구조 유지.
  - `golf/main_golf.py`: ChatGPT 본문 응답 DOM에 포함된 외부 이미지 태그를 최대 4장까지 감지해 본문 후처리 대상에 추가. 티스토리 입력 직전 원본 이미지 위치를 업로드 마커로 바꾸고 `Path.home()/백업용`에 저장한 파일을 HTML 모드에서 순서대로 네이티브 업로드한 뒤 임시 파일을 삭제하도록 변경.
  - `golf/main_golf.py`: 골프 글 발행 흐름에서 기본모드 대표이미지 설정을 사용하지 않도록 변경. 제목/본문/해시태그 입력 후 HTML 모드에서 생성 대표 이미지를 업로드하고, `완료` 클릭 후 발행창의 대표이미지 추가 파일 input(`.inp_g`)에 같은 이미지 파일을 지정한 뒤 공개 발행하도록 조정.
  - `golf/main_golf.py`: 티스토리 본문 주입 직후 실제 HTML 값이 `[Pasted Content ...]`로 바뀌었거나 표가 누락되었거나 길이가 비정상적으로 짧으면 발행을 중단하는 검증을 추가.
- 검증
  - `src/tistory_automation/main.py` 대표이미지 추가 변경 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\main.py`, `git diff --check -- .\src\tistory_automation\main.py` 통과.
  - `main.py --post-type daily --publish` 수동 실행. 제목 `AI가 일상이 된 시대, 카페 노트북 풍경이 달라진 이유`로 일상글 생성, HTML 모드 사진 업로드, 해시태그 입력, 발행창 대표이미지 파일 지정, 공개 발행 완료.
  - 스케줄러 로그 인코딩 변경 후 `run_scheduled_post.ps1` scriptblock 파싱 통과, 동일 파이프 방식의 한글 테스트 로그 UTF-8 저장/조회 정상, `git diff --check -- .\scripts\scheduled\run_scheduled_post.ps1` 통과.
  - `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py` 통과.
  - 대표 이미지 설정 추가 후 `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py`, `git diff --check -- golf\main_golf.py` 통과.
  - 웹형 본문 폭 조정 후 `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py`, `git diff --check -- golf\main_golf.py` 통과.
  - 대표 이미지 비율 프롬프트 수정 후 `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py`, `git diff --check -- golf\main_golf.py` 통과.
  - 스킨 폭 연동 조정 후 `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py`, `git diff --check -- golf\main_golf.py` 통과.
  - 스킨 복붙 파일에서 제목/본문 정렬 보정 CSS 선택자 확인.
  - 라이브 URL `https://jxbooklove.tistory.com/88`에서 브라우저 계산 좌표 확인: 보정 전 제목 박스 `x=527`, 보정 CSS 임시 주입 후 `x=24`, 제목 텍스트와 본문 시작선 `x=67` 일치.
  - 카테고리 자동 선택 변경 후 `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py`, `git diff --check -- golf\main_golf.py`, 로컬 카테고리 판정 함수 테스트 통과.
  - scheduled PowerShell 래퍼 4개에서 `pong3`, `WORKING_HAPPY`, `Python314` 문자열 미검출. `[scriptblock]::Create(...)` 문법 검사 통과. 계산된 프로젝트 루트와 `.venv` Python 존재 확인.
  - 스케줄러 등록 락 추가 후 `.venv\Scripts\python.exe -m py_compile .\src\tistory_automation\scheduler.py .\golf\G스케줄러\golf_24h_random_15_scheduler.py`, `git diff --check -- ...` 통과.
  - ChatGPT 본문 이미지 처리 추가 후 `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py`, `git diff --check -- .\golf\main_golf.py`, 샘플 `<img>` 후보 추출/마커 치환 로컬 테스트 통과.
  - 발행창 대표이미지 추가 흐름 변경 후 `.venv\Scripts\python.exe -m py_compile .\golf\main_golf.py`, `git diff --check -- .\golf\main_golf.py` 통과. 최근 저장된 `body.html`에 `<table>`은 있고 `[Pasted Content]`는 없는 것 확인.
- 다음 작업
  - 사용자 승인 후 저장된 결과로 티스토리 작성 화면에서 사진이 마커 위치에 네이티브 업로드되는지 1회 확인.
  - 다음 자동 발행에서 대표 이미지 버튼 클릭까지 정상 동작하는지 로그와 실제 글 썸네일 확인.
  - 다음 자동 발행 글에서 본문 폭이 웹 화면에서 과하게 좁지 않은지 실제 글 화면 확인.
  - 다음 자동 발행 글 대표 썸네일에서 골프장/클럽하우스/카트 등 주요 피사체가 좌우 크롭되지 않는지 확인.
  - 다음 골프 발행에서 ChatGPT 응답에 보이는 외부 이미지 여러 장이 본문 위치별로 업로드되고, 작업 후 `C:\Users\itwill\백업용`의 일회성 파일이 정리되는지 확인.

## 2026-05-07

### 네이버 자동화 ing/네이버 블로그 글쓰기

- 변경사항
  - `skssj2628/skssj2628.py`: 일상/쿠팡 이미지 프롬프트에 20대 성인 한국인 여성 등장 조건 추가, 쿠팡 링크는 본문 중간 1회 유지, 이미지 클립보드 검증 후 붙여넣기 방어 추가.
  - `skssj2628/skssj2628.py`: 인용구는 기본값 제외 후 인용구 2~6 스타일만 선택하도록 변경. 빈 `[인용구]`는 툴바 열기 전 건너뜀.
  - `skssj2628/skssj2628.py`: 쿠팡 해시태그 프롬프트를 상품명/품목/사용상황/구매 기준 중심으로 보정.
  - `제미나이웹.py`: 일상 이미지에 사람 등장 조건 추가, 쿠팡 링크 2회 정책 유지, 이미지 클립보드 검증과 전역 락 경로 정리 적용.
  - `스케줄러.py`, `skssj2628/skssj2628(스케줄러).py`: 두 계정 발행 시간이 최소 30분 이상 벌어지도록 peer schedule 확인 로직 추가.
  - `COUPANG_CSV_PATH=products_db.csv`가 `제미나이웹.py` 기본 DB 선택을 덮어쓰던 문제는 사용자 환경변수 삭제로 해결. 사용자 확인 결과 실행 정상.
- 검증
  - `git diff --check -- skssj2628/skssj2628.py` 통과.
  - `skssj2628/skssj2628.py` AST 문법 검사 통과. Codex 셸에는 `python`이 PATH에 없어 `티스토리 자동화 ing/.venv/Scripts/python.exe`로 확인.
  - 이전 확인: `제미나이웹.py`, `skssj2628.py`, 양쪽 스케줄러 AST 검사 통과.
- 다음 작업
  - `skssj2628.py`로 일상/쿠팡 각 1건 테스트해 인용구 2~6 표시, 빈 인용구 미발생, 중간 링크 1회 위치 확인.
  - 필요하면 `제미나이웹.py`에도 `skssj2628.py`와 같은 인용구 2~6 선택 로직을 별도 적용.
  - `skssj2626` 좋아요 표시 문제는 코드보다 네이버 `공감 허용` 설정을 먼저 확인.
  - 코드/프롬프트 변경은 사용자가 승인한 범위만 진행.

### 티스토리 자동화 ing

- 변경사항
  - 오늘 티스토리 코드 변경 없음. 문서 인수인계만 갱신.
- 검증
  - 오늘 티스토리 실행/문법 검사는 새로 수행하지 않음.
- 다음 작업
  - 이전 세션의 `golf/main_golf.py` 해외 골프여행 품질 보강 결과가 실제 발행 글에서 시간표/동선/금액 중심으로 나오는지 확인.
  - 티스토리 발행/스케줄러 실행은 사용자 명시 승인 후 진행.
  - HTML 작성 순서와 이미지 업로드 규칙은 `티스토리 자동화 ing/AGENTS.md` 기준 유지.

## 2026-05-06

### 네이버 자동화 ing/네이버 블로그 글쓰기

- `skssj2628/skssj2628.py`
  - 빈 `[인용구]`/자리표시자 인용구 방지 프롬프트와 런타임 검사 추가.
  - 제목 입력 실패 원인 `element click intercepted` 대응: 제목 영역 포커스 재시도와 클립보드 붙여넣기 입력으로 보강.
  - 네이버 인용구 툴바 사용 제거. `[인용구]...[/인용구]`는 일반 문단 `“...”` + 색/굵기 처리로 입력하고, `[목록주제]`도 일반 굵은 문단으로 처리.
  - git 푸시 전 하드코딩된 네이버 비밀번호 기본값 제거. 이후 비밀번호는 `NAVER_PASSWORD` 환경변수 또는 대화형 입력 사용.
  - 16:25 스케줄러 실패는 `일상` 글 제목 클릭 실패였고, 16:40 `일상` 1건 수동 실행은 발행 성공.
- `제미나이웹.py`
  - `skssj2628.py`와 동일하게 빈 인용구 방지, 제목 입력 보강, 네이버 인용구 툴바 사용 제거 적용.
  - 쿠팡 수익 최적화 보강: 후보 상품 선택 점수에 가격대, 리뷰수, 평점, 로켓/배송 정보, 롱테일 키워드, 시즌성을 반영.
  - 초반 수익 글에서 성과가 난 `구체적 사용 맥락 -> 구매 전 기준 -> 자연스러운 상세정보 확인` 구조를 프롬프트에 반영하되, 직접 사용/정착/내돈내산 표현은 금지.
  - CTA 링크 블록을 `구매 전 상세정보 확인`, `현재 가격과 후기 확인`으로 바꾸고 첫 링크를 문제 설명 뒤 첫 구분선 다음에 더 빨리 배치.
  - 제목/해시태그 로컬 보정 추가: 과장·실사용 오해 표현을 막고 상품군별 비교 축이 들어간 롱테일 제목과 태그로 보강.
- `skssj2628/skssj2628.py`
  - `제미나이웹.py`와 동일한 쿠팡 수익 최적화 로직 적용.
  - 딥링크 변환 성공 로그에서 파트너스 URL 원문을 출력하지 않고 상품명만 출력하도록 변경.
- `제미나이웹.py`, `skssj2628/skssj2628.py`
  - 네이버 비밀번호 입력을 실행 시작 전에 강제하지 않도록 변경.
  - 저장된 Chrome 네이버 프로필 세션을 먼저 확인하고, 세션이 만료된 경우에만 열린 브라우저에서 수동 로그인을 기다리게 조정.
  - `제미나이웹.py` 기본 네이버 ID를 공개 블로그 ID인 `skssj2627`로 설정해 기존 `ChromeNaverBot_skssj2627` 프로필을 바로 재사용하도록 보정.
- `skssj2627_db.csv`
  - 여름/장마/냉방/제습/벌레 관련 상품만 남기고, 사용 처리된 상품 제거.
  - 백업: `네이버 자동화 ing/네이버 블로그 글쓰기/skssj2627_db.backup_20260506_125009.csv`
  - 결과: 133개 중 86개 유지, 47개 제거.
- 검증
  - `py_compile` 통과: `skssj2628/skssj2628.py`, `제미나이웹.py`
  - 최근 로그 확인: `제미나이웹.py` 16:15 발행 성공, `skssj2628.py` 16:25 실패, 16:40 수동 실행 성공.
- 다음 작업
  - 다음 스케줄러 실행분에서 빈 인용구 박스가 더 이상 생기지 않는지 실제 블로그 화면 확인.
  - 필요하면 `skssj2628.py`를 새 인용구 처리 방식 적용 후 1건 더 테스트.
  - `skssj2627_db.csv`는 쿠팡 링크 DB라 원격 푸시 제외. 필요 시 별도 비공개 저장소/암호화 백업으로 관리.

### 티스토리 자동화 ing/golf

- `golf/main_golf.py`
  - 골프 글 방향을 해외 골프여행 90%, 국내 골프장 10% 중심으로 조정.
  - 제목 앞 `2026` 자동 제거 처리 추가.
  - 해외 골프여행 글에 사전 리서치 브리프 단계 추가.
  - 본문 생성 전 `3박5일/4박6일 시간표`, 공항/호텔/골프장 동선, 교통수단, 예상 비용, 식당/관광 후보, 보험/수하물 정보를 먼저 만들게 변경.
  - 해외 일정형 글이 시간표, 금액, 공항/호텔/골프장, 이동수단, 식당/관광, 보험/수하물을 빠뜨리면 1회 재작성하고, 그래도 부족하면 중단하도록 검증 추가.
- 스케줄러
  - `G스케줄러/golf_24h_random_15_scheduler.py --install` 실행.
  - `--max-posts 15`로 2026-05-06~2026-05-07 다음 24시간 계획 재등록.
- 검증
  - `py_compile` 통과: `golf/main_golf.py`
  - 스케줄러 parent task `Tistory_Golf_24H_Random_15` Ready 확인.
- 다음 작업
  - 다음 발행 글이 실제 일정/동선/금액 중심으로 나오는지 `jxbooklove.tistory.com`에서 확인.
  - 리서치 브리프가 너무 일반적으로 나오면 목적지별 고정 후보 데이터 또는 별도 검색 수집 단계를 추가 검토.
