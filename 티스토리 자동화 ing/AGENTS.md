# AGENTS.md

이 문서는 `티스토리 자동화 ing` 프로젝트를 다른 컴퓨터에서도 다시 세팅하고 유지보수할 수 있도록, 현재 `main.py` 중심 구조와 실행 규칙을 정리한 운영 문서다.

## 1. 프로젝트 목적

이 프로젝트는 다음 두 흐름을 자동화한다.

1. ChatGPT 웹에서 본문/제목/해시태그/이미지를 생성
2. 티스토리 HTML 에디터에 결과를 주입하고 발행

지원하는 기본 글 타입은 다음과 같다.

- `coupang`: 쿠팡 파트너스 상품 비교형 글
- `daily`: 일상/이슈형 글
- `golf/main_golf.py --post-type golf`: 골프 정보글
- `golf/main_golf.py --post-type health` 또는 `--post-type 건강식품`: `data/products/건강식품_db.csv` 기반 건강식품 쿠팡 글

## 2. 핵심 파일

### 메인 실행

- `src/tistory_automation/main.py`
  - 전체 자동화 엔트리포인트
  - ChatGPT 생성
  - 티스토리 로그인/에디터 진입
  - HTML 본문 입력
  - 태그 입력
  - 발행
  - 스케줄러 모드 로그 처리

### 스케줄러

- `src/tistory_automation/scheduler.py`
  - 하루 발행 시간표 생성
  - Windows 작업 스케줄러 등록

- `scripts/scheduled/run_scheduled_post.ps1`
  - 예약된 1회 발행 실행 래퍼

- `scripts/scheduled/run_refresh_schedule.ps1`
  - 매일 스케줄 재생성 래퍼

### 쿠팡 데이터 관련

- `src/tistory_automation/coupang/api.py`
  - 쿠팡 API 검색/딥링크
  - `main.py`의 쿠팡 글 생성 전에 상품 링크 보강

- `src/tistory_automation/pipeline/category_crawler.py`
  - 쿠팡 카테고리 크롤러
  - 현재는 `로켓배송 > 가전디지털 > 계절가전`까지만 클릭하고 크롤링
  - 과거 사용 URL과 DB 내부 중복 상품은 제외

- `category_crawler.py`
  - 루트 실행 래퍼
  - `python "category_crawler.py"`만으로 실행 가능

## 3. 주요 경로

`main.py` 내부 기준 핵심 경로:

- `config/`
  - 프롬프트, HTML 가이드

- `data/products/products_db_category.csv`
  - 크롤링된 상품 DB

- `runtime/logs/`
  - 일반 로그

- `runtime/logs/scheduled/`
  - 예약 발행 로그

- `runtime/outputs/generated_results/`
  - 최근 생성 결과 저장
  - `body.html`, `title_candidates.txt`, `hashtags.txt`, `image*_data_url.txt`

- `runtime/sessions/chatgpt/`
  - ChatGPT 크롬 세션

- `runtime/sessions/tistory/`
  - 티스토리 크롬 세션

- `runtime/scheduled_state/daily_schedule.json`
  - 예약 시간표 저장

## 4. `main.py` 전체 흐름

### 4-1. 실행 진입

`main.py`는 CLI 옵션을 파싱한 뒤, 항상 자동화 락을 먼저 잡는다.

락 파일:

- `C:\Users\pong3\WORKING_HAPPY\티스토리 자동화 ing\runtime\locks\automation.lock`

동시 실행 방지 목적이다.

현재는 다음 순서로 잠금을 처리한다.

1. `filelock`이 설치되어 있으면 `FileLock` 사용
2. 없으면 Windows `msvcrt.locking()` 기반 fallback 사용

추가로 임베디드 Python 환경에서 가끔 `unknown encoding: idna`가 나와서, 시작 시 `encodings.idna`를 강제 로드하도록 보정해두었다.

### 4-2. 로그인 세션

세션 구조:

- ChatGPT: `runtime/sessions/chatgpt`
- Tistory: `runtime/sessions/tistory`

관련 함수:

- `save_login_session()`
  - ChatGPT 세션 저장 후 Tistory 세션 저장까지 이어짐

- `save_tistory_session()`
  - 티스토리 글쓰기 화면까지 들어간 세션 저장

티스토리 세션은 `.session_ready` 마커 파일과 브라우저 데이터 존재 여부를 같이 확인한다.

### 4-3. 전체 자동 생성/발행

핵심 함수:

- `run_full_flow()`

동작 순서:

1. 저장된 ChatGPT 세션 확인
2. `post_type`이 `coupang`이면 상품 3개 선택
3. 필요 시 쿠팡 API로 링크 보강
4. ChatGPT 프로젝트 페이지 접속
5. 본문/제목/해시태그/이미지 생성
6. 생성 결과를 `runtime/outputs/generated_results`에 저장
7. 티스토리 세션 확인
8. 티스토리 에디터 진입
9. HTML 본문 입력
10. 태그 입력
11. 발행

### 4-4. 생성 결과 재사용 후 티스토리만 실행

핵심 함수:

- `run_tistory_only_flow()`

이미 저장된 결과물을 사용해서 티스토리 작성/발행만 다시 시도한다.

## 5. 쿠팡 글 생성 흐름

핵심 함수:

- `generate_article()`

순서:

1. 이미지 1 생성
2. 이미지 2 생성
3. 본문 HTML 생성
4. 제목 생성
5. 해시태그 생성
6. 결과 저장

중요 포인트:

- 본문 맨 위에 쿠팡 고지 문구를 강제로 맞춘다.
- 이미지 data URL은 결과 저장 후 티스토리 입력 직전에 실제 HTML에 치환된다.
- 본문 내 쿠팡 링크는 카드형 CTA로 후처리될 수 있다.

## 6. 일상 글 생성 흐름

핵심 함수:

- `generate_daily_article()`

순서:

1. 이미지 생성
2. 본문 생성
3. 메타 JSON에서 제목/태그 추출

일상 글에서는 본문 내 `[BASE64_IMAGE_1]`를 `%%IMAGE1_PLACEHOLDER%%`로 바꾸고, 티스토리 입력 직전에 data URL로 치환한다.

STEP 3에서 로그가 `응답 0자`로 반복되면 티스토리 임시저장 문제가 아니라 ChatGPT 응답 DOM 텍스트 추출 문제일 수 있다. `_wait_for_text()`와 최신 non-empty 응답 후보 추출 로직을 먼저 확인한다.

## 7. 티스토리 에디터 입력 구조

핵심 함수:

- `login_and_open_tistory_editor()`
- `write_tistory_html_post()`

### HTML 모드 관련

이 프로젝트에서 가장 중요한 포인트 중 하나다.

예전 문제:

- HTML 모드 전환 실패
- 그런데도 계속 진행
- 리치 에디터에 HTML 원문이 그대로 입력됨
- `<p>...</p>`가 본문 텍스트로 노출됨

현재 보정 방식:

- `_switch_tistory_editor_mode_strict()` 사용
- 실제 HTML textarea가 존재하는지 `_verify_tistory_editor_mode()`로 검증
- 검증 실패 시 계속 진행하지 않음

즉, HTML 모드 진입이 확인된 경우에만 본문 주입이 진행된다.

### 본문 입력 방식

- CodeMirror 직접 주입 시도
- 실패 시 textarea 입력 fallback
- 주입 뒤 DOM 변경 이벤트를 강제로 발생

### 발행 방식

발행 버튼 클릭 순서:

1. 완료 버튼
2. 공개 발행 버튼

## 8. 프롬프트 관리 규칙

프롬프트는 코드에 하드코딩하지 않고 아래 파일에서 읽는다.

- `config/prompts/chatgpt_web_prompts.json`
- `config/prompts/coupang_html_guide.md`

`main.py`는 실행 시 이 파일들을 읽어 다음 텍스트를 구성한다.

- 쿠팡 본문 프롬프트
- 제목 프롬프트
- 해시태그 프롬프트
- 이미지 프롬프트
- 일상 글 프롬프트

프롬프트를 수정해야 할 때는 먼저 `config/prompts`를 수정하고, 코드 쪽은 경로/키 이름이 바뀔 때만 수정한다.

## 9. 실행 명령

### 메인 실행

```powershell
Set-Location "C:\Users\pong3\WORKING_HAPPY\티스토리 자동화 ing"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
.venv\Scripts\python.exe -X utf8 -m tistory_automation.main
```

### 호환용 `--publish` 실행

```powershell
Set-Location "C:\Users\pong3\WORKING_HAPPY\티스토리 자동화 ing"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
.venv\Scripts\python.exe -X utf8 -m tistory_automation.main --publish
```

현재 `main.py`는 안전상 `--publish`가 들어와도 공개 발행하지 않고 대표이미지 지정 후 임시저장으로 마무리한다.

### 로그인 세션 저장

```powershell
Set-Location "C:\Users\pong3\WORKING_HAPPY\티스토리 자동화 ing"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
.venv\Scripts\python.exe -X utf8 -m tistory_automation.main --login
```

### 티스토리 세션만 저장

```powershell
Set-Location "C:\Users\pong3\WORKING_HAPPY\티스토리 자동화 ing"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
.venv\Scripts\python.exe -X utf8 -m tistory_automation.main --tistory-login-only
```

### 저장된 결과로 티스토리만 임시저장

```powershell
Set-Location "C:\Users\pong3\WORKING_HAPPY\티스토리 자동화 ing"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
.venv\Scripts\python.exe -X utf8 -m tistory_automation.main --resume-tistory --post-type coupang
```

## 10. 스케줄러 구조

### Python 스케줄러

- `src/tistory_automation/scheduler.py`

역할:

1. 당일/익일 랜덤 발행 시간 10개 생성
2. 글 타입 섞기
3. Windows 작업 스케줄러 등록
4. 매일 리프레시 작업도 등록

### PowerShell 래퍼

- `scripts/scheduled/run_scheduled_post.ps1`
- `scripts/scheduled/run_refresh_schedule.ps1`

최근 보정 내용:

- PowerShell UTF-8 입출력 강제
- `.venv\Scripts\python.exe` 우선 사용
- 고정 Python 경로는 fallback

이유:

- 작업 스케줄러에서 한글 깨짐 방지
- 다른 PC에서도 가상환경 우선 사용

## 11. 쿠팡 카테고리 크롤러 구조

실행 파일:

- 루트: `category_crawler.py`
- 본체: `src/tistory_automation/pipeline/category_crawler.py`

현재 동작:

1. `python "category_crawler.py"` 실행
2. 목표 건수 입력
3. 디버그 크롬이 없으면 정식 Chrome 자동 실행
4. 디버그 세션에 Selenium attach
5. `로켓배송 > 가전디지털 > 계절가전`
6. 계절가전 페이지에 보이는 상품을 수집
7. 입력한 건수만큼 저장

저장 컬럼:

- 상품명
- 키워드
- 쿠팡링크
- 카테고리
- 가격
- 할인율
- 로켓정보
- 평점
- 리뷰수
- 기타 메타 칼럼

최근 보정 내용:

- Chrome Beta가 아니라 정식 Chrome 사용
- 디버그 포트 없으면 자동 실행
- chromedriver 후보 순차 시도
- 2026-05-27 기준 계절가전 클릭 뒤 추가 대상 텍스트 클릭과 판매량순 정렬을 하지 않음
- 가격은 CSV 저장 시 `448,350원` 형식으로 저장

쿠팡 크롤러 공통 주의:

- `keyword_crawler.py`, `category_detail_crawler.py`, `category_crawler.py`로 새 상품을 저장한 뒤에는 `runtime/logs/used_coupang_urls.csv`와 상품 키 중복 여부를 확인한다.
- `keyword_crawler.py`는 `--query`를 생략하면 실행 중 콘솔에서 검색어를 입력받는다.
- 디버그 Chrome은 `COUPANG_DEBUGGER_ADDRESS=127.0.0.1:9222`를 사용한다. ChromeDriver 오류가 나면 현재 Chrome 메이저 버전에 맞는 `CHROMEDRIVER_PATH`를 먼저 지정한다. 2026-05-27 기준 Chrome 148은 `C:\Users\itwill\.wdm\drivers\chromedriver\win64\148.0.7778.178\chromedriver-win32\chromedriver.exe`를 사용했다.
- `products_db_category.csv`에서 사용 이력과 겹치는 행을 제거할 때는 먼저 `runtime/backups/products_db/`에 백업을 남긴다.

## 12. 다른 컴퓨터에서 재구성할 때 필수 조건

### 필수 설치

1. Windows
2. Chrome 정식 버전
3. Python
4. 프로젝트 `.venv`
5. Selenium 동작 가능한 chromedriver

### 필수 환경 변수 / `.env`

필요할 수 있는 값:

- `TISTORY_ID`
- `TISTORY_PASSWORD`
- `COUPANG_ACCESS_KEY`
- `COUPANG_SECRET_KEY`
- `COUPANG_SUB_ID`
- `COUPANG_API_ENABLED`

### 가상환경

가상환경은 프로젝트 로컬 `.venv`를 기준으로 맞춘다.

중요:

- 현재 일부 환경은 터미널 내장 Python을 베이스로 잡을 수 있다.
- 가능하면 다른 컴퓨터에서는 정식 설치 Python 기준으로 `.venv`를 새로 만드는 것이 안정적이다.

## 13. 유지보수 규칙

### 수정 전 확인

1. 경로가 `config`, `data`, `runtime`, `scripts`, `src` 중 어디에 속하는지 먼저 구분
2. 프롬프트 수정인지 코드 수정인지 먼저 분리
3. 티스토리 HTML 입력 로직 수정 시 HTML 모드 검증이 깨지지 않는지 확인
4. 스케줄러 수정 시 `.ps1` 래퍼도 같이 확인

### 수정 후 확인

최소한 아래는 확인한다.

```powershell
python -m py_compile src\tistory_automation\main.py
python -m py_compile src\tistory_automation\scheduler.py
python -m py_compile src\tistory_automation\pipeline\category_crawler.py
```

### 절대 규칙

- 세션 데이터는 `runtime/sessions` 밖으로 빼지 않는다.
- 생성 결과는 `runtime/outputs/generated_results`를 기준으로 유지한다.
- 프롬프트는 되도록 `config/prompts`에서 관리한다.
- 구조를 바꾸면 반드시 이 `AGENTS.md`를 같이 갱신한다.
- Git 동기화는 소스, 프롬프트 설정, 실행 스크립트, 문서, 테스트만 대상으로 한다. `data`, `runtime`, 세션, 로그, CSV, `.env`, 실제 광고 코드가 치환된 스킨 보관본은 올리지 않는다.

## 14. 최근 핵심 수정 이력

다른 컴퓨터에서 같은 구조를 재현할 때 특히 중요한 수정 사항:

1. 스케줄러 PowerShell UTF-8 강제
2. 스케줄러 Python 경로를 `.venv` 우선으로 변경
3. `filelock` 미설치 환경 fallback 추가
4. `idna` 코덱 강제 로드 보정 추가
5. 티스토리 HTML 모드 strict 검증 추가
6. category crawler에서 디버그 Chrome 자동 실행 추가
7. category crawler에서 판매량순 유지 URL 보정
8. category crawler 저장 컬럼에 가격/평점/리뷰수 추가

이 프로젝트를 다른 컴퓨터에서 다시 세팅할 때는, 먼저 이 문서 기준으로 폴더 구조와 실행 경로를 맞춘 뒤 `main.py`, `scheduler.py`, `category_crawler.py` 세 축이 모두 같은 규칙으로 움직이는지 확인한다.

## 15. 쿠팡 상품 중복 방지 규칙

현재 쿠팡 글 상품은 `data/products/products_db_category.csv`의 `used/post_title`와 `runtime/logs/used_coupang_urls.csv`의 URL 키를 함께 보고 중복을 막는다. 2026-05-27 기준 `main.py`는 상품 선정 직후 예약 사용 처리하지 않고, 티스토리 작성/임시저장 흐름이 성공한 뒤에만 상품 사용 처리와 URL 사용 로그, 성과 주제 사용 이력을 확정한다.

관련 구현 위치:

- `src/tistory_automation/main.py`
  - `select_products()`: CSV의 `used/post_title`뿐 아니라 `runtime/logs/used_coupang_urls.csv`의 쿠팡 URL 사용 이력도 함께 보고 후보를 제외한다.
  - `_coupang_product_key()`: `www.coupang.com/vp/products/...`와 `link.coupang.com/...pageKey=...`를 같은 상품 키로 정규화한다.
  - `_choose_unused_enriched_products()`: 쿠팡 API로 보강된 실제 상품 URL 기준으로 이미 사용한 상품과 이번 실행 내 중복 상품을 제외한다.
  - `prepare_coupang_api_products()`: CSV 후보가 비었더라도 성과 주제가 있으면 주제 검색어를 확장해 API 보강 후보를 시도한다.
  - `mark_products_as_used()`: 티스토리 작성 성공 후에만 `used=Y`와 `post_title`을 확정한다.
  - `log_product_coupang_urls()`: 티스토리 작성 성공 후에만 최종 쿠팡 링크를 URL 사용 로그에 기록한다.

유지보수 주의:

- 스케줄 실패를 조사할 때는 `runtime/logs/scheduled/*.log`의 `임시저장 완료`, `main.py 실행 완료`, `[오류]`를 먼저 대조한다.
- `products_db_category.csv`의 `used=Y`나 `post_title`를 대량 해제하지 않는다. 글이 없는 실패분인지 확인하고 사용자 승인 후 필요한 행만 복구한다.
- 크롤링으로 DB를 새로 채운 뒤에는 과거 `used_coupang_urls.csv`와 상품 키가 겹치는 행을 제거한다. 2026-05-27에는 새 계절가전 100행 중 1행이 겹쳐 백업 후 제거했고 최종 99행으로 정리했다.
- 쿠팡 API가 CSV 원본 링크와 다른 파트너스 링크를 붙일 수 있으므로, CSV의 `used` 컬럼만 믿으면 안 된다.
- 사용 URL 로그에는 상품 이미지 URL(`ads-partners.coupang.com/image1/...`)이 아니라 실제 클릭/파트너스 링크만 상품 중복 판단에 사용한다.

## 16. 티스토리 HTML 작성 순서 고정

티스토리 작성 플로우는 `write_tistory_html_post()`에서 아래 순서를 반드시 유지한다.

1. 카테고리 선택
2. HTML 모드 진입
3. ChatGPT 이미지 data URL을 `C:\Users\pong3\백업용`에 일회성 파일로 저장
4. 쿠팡 글은 첫 번째 쿠팡 링크 바로 아래에 `__TISTORY_NATIVE_IMAGE_SLOT_1__` 마커 삽입
5. 최종 HTML 모드 확인
6. 제목 입력
7. HTML 본문 주입
8. HTML 모드에서 `__TISTORY_NATIVE_IMAGE_SLOT_1__` 마커 선택
9. HTML 모드 상태에서 `//*[@id="attach-layer-btn"]` 클릭 후 `//*[@id="attach-image"]` 파일 input에 일회성 이미지 경로 전송
10. HTML 모드에서 이미지 마커 잔여 텍스트 제거
11. 페이지 맨 아래로 스크롤해서 해시태그 입력칸 찾기
12. 해시태그는 `태그 입력 -> Enter`를 태그마다 반복
13. 완료 버튼
14. 공개 발행 버튼

중요 규칙:

- 제목 입력 이후에 `_set_tistory_html_body(driver, "")`처럼 본문을 비우는 동작을 넣으면 안 된다.
- 공개 발행 플로우에서 `_upload_image_in_tistory_html_mode()`를 호출하면 안 된다. 이 함수는 내부에서 HTML 본문을 비우므로 기존 제목/본문 입력 흐름을 깨뜨릴 수 있다.
- 사진은 티스토리 HTML 모드에서 `attach-layer-btn` / `attach-image` 경로로 업로드한다. 기본모드 전환은 필요하지 않다.
- 쿠팡 글의 사진 위치는 첫 번째 쿠팡 링크 아래다. ChatGPT가 만든 이미지 placeholder 위치를 그대로 신뢰하지 않는다.
- 글 등록 시도 후 `C:\Users\pong3\백업용`에 만든 일회성 이미지 파일은 삭제한다.
- 사진 삽입 후 해시태그 입력 전에는 반드시 페이지 맨 아래로 한 번 스크롤하고, 태그 입력칸에 직접 `send_keys(tag)` 후 `ENTER`를 보낸다. `driver.switch_to.active_element`에 의존하면 포커스가 HTML 에디터에 남아 태그가 누락될 수 있다.
- 티스토리 발행 플로우에는 `data:image/...;base64`를 직접 넣지 않는다. 티스토리 HTML 모드가 `<img>`를 `&lt;img` 텍스트로 이스케이프해 본문이 깨질 수 있다.
- 발행 플로우에서는 이미지 placeholder를 본문에 남기지 않고, 네이티브 업로드용 마커로만 임시 사용한다.
- `&lt;img` 또는 `data:image/`가 최종 주입 직전 HTML에 남아 있으면 발행을 중단해야 한다. 깨진 본문을 억지로 공개발행하지 않는다.

## 17. 최근 세션 인수인계 규칙

- 의미 있는 운영 변경은 상위 `docs/work-log.md`에 `티스토리 자동화 ing` 섹션으로 짧게 남긴다.
- 2026-05-07 세션에서는 티스토리 코드 변경이 없었다. 다음 세션은 기존 `golf/main_golf.py` 해외 골프여행 글 품질과 실제 발행 결과를 먼저 확인한다.
- 티스토리 발행, 스케줄러 설치/삭제, 공개 발행 재시도는 사용자 명시 승인 후 진행한다. 현재 `golf/main_golf.py --post-type golf` 기본 실행은 공개 발행까지 진행하며, 임시저장만 필요하면 `--draft`를 붙인다.

## 18. 2026-05-08 운영 주의사항

- `golf/main_golf.py`는 골프 글과 40~50대 골퍼 독자층에 맞춘 건강식품 쿠팡 글을 함께 처리한다. 건강식품 쿠팡 글은 `--post-type health`, `--post-type 건강식품`, `--post-type coupang`으로 실행하며, 기본 DB는 `data/products/건강식품_db.csv`다. 이 파일이 없으면 `golf/건강식품_db.csv`를 fallback으로 사용하고, 다른 위치는 `HEALTH_PRODUCT_DB_PATH` 환경변수로 지정한다.
- 건강식품 쿠팡 글은 쿠팡 API 보강을 전제로 하므로 `COUPANG_API_ENABLED=1`, `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY`가 필요하다. 건강식품 프롬프트는 질병 치료·예방·효능 보장·체중감량 보장 표현을 금지하고, 성분표·섭취량·가격·리뷰·주의사항 비교 중심으로 작성한다.
- 건강식품 쿠팡 글은 CSV 원본 `쿠팡링크`만으로 발행하지 않는다. 쿠팡 API 상품 URL을 확보하지 못하면 건강식품 핵심어로 유사 상품을 재검색하고, 그래도 최종 API URL이 없으면 해당 후보를 제외한다. 수익 추적이 깨질 수 있으므로 CSV 일반 링크 fallback을 다시 넣지 않는다.
- 건강식품 쿠팡 글은 ChatGPT 이미지 생성 안정성을 위해 대표 이미지 1장만 생성한다. 이미지 2장 흐름으로 되돌리면 `스트리밍이 중지되었습니다` 이후 본문 단계가 밀릴 수 있으므로 먼저 단일 이미지 안정성을 확인한다.
- 골프 본문은 전문 용어를 신뢰도 장식처럼 나열하지 않는다. 세컨드 샷, 페어웨이 안착률, 레귤러 온, 그린 스피드, 언듈레이션, 도그레그, 레이업, 캐리 거리, 런, 해저드, 벙커 턱, 핀 포지션, 라이, 카트 동선, 티오프 간격 등은 쉬운 설명과 실제 확인 기준으로 연결한다.
- 티스토리 대표이미지는 `완료` 클릭 후 발행창의 대표이미지 추가 영역(`div.inner_box` 안의 `input.inp_g`, `span.txt_thumb=대표이미지 추가`)을 클릭하고, 같은 일회성 이미지 파일을 `input.inp_g`에 지정하는 방식이 현재 기준이다. 골프 발행 흐름에서는 기본모드 전환 후 `.mce-represent-image-btn`을 누르는 방식으로 되돌리지 않는다.
- 스케줄 등록은 `runtime/locks/schedule_register.lock`을 공통으로 사용하고, 실제 발행은 `runtime/locks/automation.lock`을 공통으로 사용한다. 여러 PowerShell이 동시에 떠도 등록/발행 작업이 순서대로 지나가야 한다.
- 골프/건강식품 스케줄러는 `--today-only --max-posts N --golf-posts G --health-posts H`로 현재 시각부터 오늘 23:59 안에만 N개 개별 작업을 만들 수 있다. 기본 부모 작업 `Tistory_Golf_24H_Random_15`는 내일부터 매일 15개를 만들며 기본 비율은 골프 10개, 건강식품 쿠팡 글 5개다.
- 예약 실행 PowerShell 로그는 UTF-8 보존이 중요하다. `run_scheduled_post.ps1`의 `ForEach-Object + Add-Content -Encoding UTF8` 출력 방식을 `Tee-Object` 중심으로 되돌리면 한글 로그가 다시 깨질 수 있다.
- `golf/main_golf.py`의 ChatGPT 프롬프트 전송은 전송 버튼 클릭 후 입력창이 비워졌는지 확인해야 한다. `_wait_for_text()`에서 같은 프롬프트를 자동 재전송하면 본문이 여러 번 생성되므로 되돌리지 않는다.
- `golf/main_golf.py` 예약 실행에서 티스토리 로그인 화면으로 이동하면 수동 로그인을 기다리지 않는다. 저장 세션 자동 복귀 확인 후에도 글쓰기 화면이 아니면 실패로 남기고, 다음 실행 전 티스토리 세션 저장/검증을 먼저 한다.
- `golf/main_golf.py` ChromeDriver는 설치된 Chrome 메이저 버전과 맞는 캐시 드라이버를 우선 사용한다. Chrome 업데이트 후 브라우저가 바로 닫히거나 세션 생성이 실패하면 오래된 `CHROMEDRIVER_PATH`보다 현재 Chrome 메이저 후보가 먼저 잡히는지 확인한다.
- 골프 글 비공개 테스트는 `--publish --private`로 실행한다. 비공개 버튼을 찾지 못하면 공개 발행 위험이 있으므로 중단해야 한다.
- 해외 골프여행 금액 검증은 `원/만원/바트/엔/달러`뿐 아니라 `$`, `US$`, `USD` 접두 표기도 금액으로 센다.
- 티스토리 글 표가 두 줄로 접히는 문제는 먼저 스킨 CSS의 본문 폭과 table 가로 스크롤로 해결한다. 프롬프트는 보조로 시간대별 동선 표를 5열 이하(`Day`, `시간`, `일정`, `이동·비용`, `확인처`)로 제한한다.
- 기존 글과 향후 글 전체에 공통 AdSense를 적용할 때는 티스토리 스킨 HTML을 수정한다. `camp-platform/public/HTML편집.txt`는 스킨 편집용 보관본이며, 로컬 `public` 폴더에 두는 것만으로 실제 블로그에 적용되지 않는다.
- 본문 중간 광고는 스킨 JS가 `#article-view` 안에 `.tistory-mid-adsense`를 삽입하는 방식이다. 확인은 공개 글의 `페이지 소스 보기`가 아니라 DevTools Elements에서 `.tistory-mid-adsense` 또는 `data-ad-slot`을 검색한다.
- AdSense `ca-pub-*` 값은 문서/답변/로그에 원문 전체를 남기지 않는다. 스킨 보관본에 반영할 때는 `.env` 값을 치환하거나 마스킹해서 다룬다.

## 19. 2026-05-15 `main.py` 운영 주의사항

- `src/tistory_automation/main.py` 계열은 현재 공개 발행하지 않는다. `--publish`와 `--resume-tistory-publish`가 들어와도 대표이미지 지정 후 임시저장으로 마무리한다.
- `src/tistory_automation/scheduler.py`, `scripts/scheduled/run_scheduled_post.ps1`, `scripts/scheduled/run_refresh_schedule.ps1`도 항상 `--draft`/`-Draft`를 붙인다. 스케줄러 등록/재등록 전에는 이 동작을 되돌리지 않는다.
- `main.py` ChromeDriver는 설치된 Chrome 메이저 버전과 일치하는 캐시 드라이버를 먼저 사용한다. Chrome 업데이트 후 티스토리 창이 닫히거나 `window_handles` 타임아웃이 나면 드라이버 후보 1순위가 현재 Chrome 메이저와 맞는지 먼저 확인한다.
- `main.py` 예약 실행에서 티스토리 로그인 화면으로 이동하면 수동 로그인을 기다리지 않는다. 저장 세션 자동 복귀 확인 후에도 글쓰기 화면이 아니면 `--tistory-login-only`로 세션을 다시 저장한다.
- 쿠팡 성과 주제 API 치환은 비교 상품 2개를 최소 기준으로 진행할 수 있다. 예약 로그가 `API 상품 확정 2/3` 전후에서 끝나면 티스토리 임시저장 문제가 아니라 ChatGPT/Tistory 진입 전 상품 치환 단계 실패로 먼저 본다.
- `daily` 글은 넓은 `여행 준비`가 아니라 히타, 나고야, 가나자와, 이토시마처럼 지역/권역 단위의 세분화 여행 주제를 코드가 먼저 고른다. 이미지/본문/메타 프롬프트가 같은 세부 주제를 공유해야 하며, 제목에는 세부 지역 키워드가 들어가야 한다.
- 티스토리 글쓰기 진입 시 `작성하던 글`/`이어서 작성`/`작성하시겠습니까` DOM 팝업이 보이는 경우에만 `ESC`로 닫는다. 다른 팝업이나 발행창 동작에 무조건 `ESC`를 보내지 않는다.

## 20. 2026-05-26 건강식품 DB 크롤링 주의사항

- 건강식품 후보를 직접 보강할 때는 `src/tistory_automation/pipeline/keyword_crawler.py`를 사용하고, 출력은 `golf/건강식품_db.csv`로 지정할 수 있다. 실행 전 `runtime/backups/health_db/`에 백업을 남긴다.
- `keyword_crawler.py`는 현재 건강식품 DB 직접 append 기준으로 리뷰 1,000개 이상, 평점 4.3 이상만 저장한다. 리뷰 3,000개 이상 및 평점 4.5 이상은 `추천등급=A`, 그 외 통과 후보는 `추천등급=B`로 기록한다.
- 기존 `golf/건강식품_db.csv` 헤더 순서를 보존해서 append해야 한다. 새 크롤러나 임시 스크립트를 만들 때 컬럼 순서가 다르면 바로 붙이지 말고 기존 헤더 기준으로 매핑한다.
- 디버그 Chrome은 `COUPANG_DEBUGGER_ADDRESS=127.0.0.1:9222`를 사용한다. Chrome 업데이트 후 크롤러 attach 실패가 나면 `CHROMEDRIVER_PATH`가 현재 Chrome 메이저 버전과 맞는지 먼저 확인한다.
- 건강식품 크롤링은 쿠팡 페이지 접근/검색 결과 수집이므로 사용자가 요청한 범위의 소량 키워드부터 실행한다. 대량 쿼리 반복이나 외부 API 대량 호출은 사용자 승인 후 진행한다.
