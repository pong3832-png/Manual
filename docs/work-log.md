# Work Log

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
