# AGENTS.md

## Project Overview

이 저장소 루트는 `C:\Users\itwill\자동화 공부`이며, 여러 자동화/개인 프로젝트가 함께 들어 있다. 이 파일은 루트 공통 기준이며, 하위 폴더에 별도 `AGENTS.md`가 있으면 루트 규칙 위에 프로젝트 전용 규칙으로 추가 적용한다.

기존 주요 운영 대상은 `토스 자동화` 폴더다. 단, 작업 시작 전에는 항상 실제 폴더 존재 여부와 현재 사용자 요청 범위를 먼저 확인한다.

`토스 자동화`는 토스 앱에서 수동으로 가져온 토스쇼핑 쉐어링크 상품을 CSV로 관리하고, ChatGPT 웹 프로젝트와 네이버 블로그 웹 에디터를 Selenium으로 조작해 네이버 블로그 상품형 정보글을 발행하는 자동화 프로젝트다.

핵심 전략은 단순 광고글 대량 발행이 아니라, 네이버 검색자가 구매 전에 고민하는 문제를 먼저 풀고 상품 선택 기준, 장점, 주의점, 맞는 사람/신중히 볼 사람, FAQ를 구성한 뒤 토스쇼핑 상세정보 확인으로 자연스럽게 연결하는 것이다.

현재 구현은 API 방식이 아니라 ChatGPT Pro 웹 세션을 사용한다. ChatGPT와 네이버는 각각 별도 Chrome 프로필을 사용해 로그인 세션을 유지한다.

이 프로젝트는 실제 네이버 발행을 수행할 수 있으므로 실행 명령은 위험 작업으로 취급한다. 코드 분석, 문법 검사, CSV 구조 확인은 안전 작업이다.

## Baseline Policy

- 루트 `AGENTS.md`는 전체 작업공간의 최상위 안전 규칙이다. 새 프로젝트를 가져오거나 하위 `AGENTS.md`를 만들 때도 이 파일의 금지/승인/민감정보 규칙을 약화하지 않는다.
- 이 파일은 통째로 재작성하지 않는다. 기존 규칙은 보존하고, 필요한 변경은 근거가 분명한 최소 패치로 추가/수정한다.
- 새로 가져오는 Git 프로젝트는 루트 규칙을 복사하지 않고, 해당 프로젝트 루트의 `AGENTS.md`에 프로젝트 전용 명령, 수정 금지 파일, 테스트/빌드/배포 주의만 보완한다.
- 새 프로젝트에 이미 `AGENTS.md`가 있으면 원본 의도를 먼저 읽고 보존한다. 로컬 보완이 필요하면 별도 섹션으로 추가하고, 충돌하는 규칙은 사용자 확인 전 임의로 덮어쓰지 않는다.
- 새 프로젝트 편입 시 먼저 `README`, 의존성 파일, 실행 스크립트, `.gitignore`, 민감 파일 패턴을 확인한다. 설치, 배포, 외부 API 활성화, 실제 자동화 실행은 사용자 승인 후 진행한다.
- 작업 범위는 사용자가 지정한 프로젝트로 제한한다. 루트 전체 검색은 가능하지만, 수정은 명시된 프로젝트와 관련 문서에만 한정한다.

## Repository Map

Git 루트:

```text
C:\Users\itwill\자동화 공부
```

토스 자동화 작업 대상(폴더가 존재하거나 복원된 경우):

```text
C:\Users\itwill\자동화 공부\토스 자동화
```

중요 경로:

| 경로 | 역할 | 주의 |
|---|---|---|
| `토스 자동화/src/toss.py` | 메인 실행 코드 | 실제 발행/브라우저 자동화 포함 |
| `토스 자동화/src/.env.example` | 환경변수 예시 | 실제 `src/.env` 값은 읽거나 문서화하지 말 것 |
| `토스 자동화/data/toss_products.csv` | 토스 상품 DB | 사용자가 준 수익 링크 포함 |
| `토스 자동화/data/publish_queue.csv` | 토스 상품 발행 순서 | 큐 순서 변경은 발행 전략 변경 |
| `토스 자동화/data/link_inbox.csv` | 원본 링크 수집 CSV | 토스 쉐어링크 원본 보존 |
| `토스 자동화/data/review_analysis.csv` | 리뷰/상품 분석 CSV | 분석 결과 보관 |
| `토스 자동화/prompts/` | 본문/제목/해시태그/링크 분석 프롬프트 보관본 | 현재 실행 프롬프트 일부는 `toss.py` 안에도 있음 |
| `토스 자동화/docs/` | 운영 규칙과 전략 문서 | PDF 원본 포함 |
| `토스 자동화/config/toss_product_schema.json` | CSV 필드/금지 표현/링크 규칙 | 도메인 규칙 근거 |
| `토스 자동화/src/자동발행상태기록파일/` | 실제 사용 이력, 선택 이력, 락, 로그 | 발행 상태에 영향 |
| `토스 자동화/runtime/` | 런타임 상태/로그/리포트/크롬 구조 | 세션/캐시성 파일 주의 |
| `토스 자동화/output/` | 초안/이미지 출력 위치 | 생성물 |
| `toss_chatgpt_profile` | ChatGPT Chrome 프로필 | 쿠키/세션 민감 |
| `toss_naver_profile` | Naver Chrome 프로필 | 쿠키/세션 민감 |
| `토스` | 현재 코드가 쓰지 않는 Chrome 프로필 데이터 성격 폴더 | 메인 아님 |

루트에는 `camp-platform`, `티스토리 자동화 ing`, `네이버 자동화 ing`, `크몽 전용`, `개인프로젝트`, `.사용설명서`, `docs` 등 다른 프로젝트/문서도 있다. 특정 프로젝트 작업 중에는 명시 요청 없이는 다른 프로젝트를 수정하지 않는다.

## Primary Entry Points

메인 CLI:

```text
토스 자동화/src/toss.py
```

실행 흐름:

1. `src/.env`와 OS 환경변수를 읽는다.
2. 네이버 ChromeDriver를 별도 프로필로 띄운다.
3. 네이버 로그인 세션을 확인한다.
4. `automation.lock`을 획득한다.
5. `data/toss_products.csv`와 `data/publish_queue.csv`에서 발행 상품을 고른다.
6. ChatGPT 토스 프로젝트 웹 세션을 띄운다.
7. 본문/해시태그/제목/이미지를 생성한다.
8. 네이버 블로그 에디터에 제목, 이미지, 본문을 입력한다.
9. 실제 발행 버튼을 누른다.
10. 사용 상품 이력을 JSON에 기록한다.
11. 락을 해제한다.

기타 진입점:

| 진입점 | 상태 |
|---|---|
| `토스 자동화/src/README.md` | 초기 설계 설명. 현재 구현과 일부 차이 있음 |
| `토스 자동화/PROJECT_CONTEXT.md` | 현재 운영 맥락 인수인계 문서 |
| `토스 자동화/prompts/*.md` | 프롬프트 보관본. 실제 실행 프롬프트는 `toss.py`도 확인 |

`package.json`, `pyproject.toml`, `requirements.txt`, Dockerfile, compose 파일은 `토스 자동화` 범위에서 확인되지 않았다. 의존성 파일은 확인 필요다.

## Common Commands

안전한 확인 명령:

```powershell
cd "C:\Users\itwill\자동화 공부"
python -m py_compile "토스 자동화\src\toss.py"
```

실행 중 프로세스 확인:

```powershell
Get-Process python,chromedriver -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime,Path
```

토스 범위 git 상태 확인:

```powershell
git status --short -- "토스 자동화"
```

untracked 파일을 나중에 Git에 올리기 전 확인:

```powershell
git status --short -- "AGENTS.md" "docs" "토스 자동화"
git status --short --untracked-files=all -- "토스 자동화"
```

전체 git 상태는 매우 크다. 먼저 요약만 본다:

```powershell
$all = git status --short
$tracked = git status --short --untracked-files=no
"total_status_lines=$($all.Count)"
"tracked_status_lines=$($tracked.Count)"
```

CSV 파일 빠른 확인:

```powershell
Import-Csv -LiteralPath "토스 자동화\data\toss_products.csv" | Select-Object product_name,main_keyword,toss_sharelink,category
```

실제 발행 실행 명령. 이 명령은 네이버 블로그 발행까지 진행할 수 있으므로 사용자 명시 승인 필요:

```powershell
cd "C:\Users\itwill\자동화 공부"

$env:PYTHONIOENCODING="utf-8"
$env:PYTHONUTF8="1"
$env:NAVER_PROFILE_PATH="C:\Users\itwill\자동화 공부\toss_naver_profile"
$env:CHATGPT_PROFILE_PATH="C:\Users\itwill\자동화 공부\toss_chatgpt_profile"
$env:TOSS_PRODUCTS_CSV_PATH="C:\Users\itwill\자동화 공부\토스 자동화\data\toss_products.csv"

python "토스 자동화\src\toss.py" --post-type 토스
```

위 실행은 위험 명령이다. 자동 브라우저 2개를 띄우고, ChatGPT와 네이버에 접속하며, 최종적으로 게시글을 발행할 수 있다.

## Environment Variables

`토스 자동화/src/toss.py`는 `토스 자동화/src/.env`를 읽는다. 실제 `.env` 값은 비밀 정보일 수 있으므로 문서에 적지 말고, 필요하면 변수명만 다룬다.

| 변수 | 용도 | 필수 여부 |
|---|---|---|
| `NAVER_ID` | 네이버 ID | 선택. 저장 세션/수동 로그인 가능 |
| `NAVER_PASSWORD` | 네이버 비밀번호 | 선택. 수동 로그인 가능. 값 노출 금지 |
| `TOSS_PRODUCTS_CSV_PATH` | 토스 상품 CSV 경로 | 권장 |
| `COUPANG_CSV_PATH` | 기존 쿠팡 코드 호환 CSV 경로 | 선택 |
| `NAVER_PROFILE_PATH` | 네이버 Chrome 프로필 경로 | 권장 |
| `CHATGPT_PROFILE_PATH` | ChatGPT Chrome 프로필 경로 | 권장 |
| `CHATGPT_PROJECT_URL` | ChatGPT 토스 프로젝트 URL | 코드가 기본 URL로 검증/보정 |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 알림 봇 토큰 | 선택. 값 노출 금지 |
| `TELEGRAM_CHAT_ID` | 텔레그램 채팅 ID | 선택. 값 노출 금지 |
| `CHROMEDRIVER_PATH` | 수동 ChromeDriver 경로 | 선택 |
| `OPENAI_API_KEY` | API 방식 전환 시 예비용 | 현재 웹 방식에서는 사용 확인 필요 |
| `COUPANG_API_ENABLED` | 쿠팡 API 사용 여부 | 토스 CSV에서는 비활성 |
| `COUPANG_ACCESS_KEY` | 쿠팡 API 키 | 토스 작업에서는 보통 불필요. 값 노출 금지 |
| `COUPANG_SECRET_KEY` | 쿠팡 API 시크릿 | 값 노출 금지 |
| `COUPANG_API_DOMAIN` | 쿠팡 API 도메인 | 선택 |
| `COUPANG_API_TIMEOUT_SEC` | 쿠팡 API 타임아웃 | 선택 |
| `COUPANG_SEARCH_LIMIT` | 쿠팡 검색 제한 | 선택 |
| `COUPANG_IMAGE_SIZE` | 쿠팡 이미지 크기 | 선택 |
| `COUPANG_SUB_ID` | 쿠팡 Sub ID | 선택 |

현재 ChatGPT 프로젝트 기본 URL:

```text
https://chatgpt.com/g/g-p-69f9873757288191bc8ba187283e5b30-toseu-jeonyong/project
```

코드는 `CHATGPT_PROJECT_URL`에 줄바꿈/다른 URL이 들어오면 기본 토스 프로젝트 URL로 되돌린다.

## Data And Runtime Files

상품/큐 CSV:

| 파일 | 설명 | 주의 |
|---|---|---|
| `토스 자동화/data/toss_products.csv` | 발행 후보 상품 DB | 사용자가 준 수익 링크 보존 |
| `토스 자동화/data/publish_queue.csv` | 토스 발행 순서 | 상품 순서 변경은 운영 전략 변경 |
| `토스 자동화/data/link_inbox.csv` | 원본 링크 수집 | 원본 토스 링크 훼손 금지 |
| `토스 자동화/data/review_analysis.csv` | 리뷰/분석 데이터 | 추정값과 확인값 구분 필요 |

상태 파일:

| 파일 | 설명 |
|---|---|
| `토스 자동화/src/자동발행상태기록파일/coupang_used_products.json` | 실제 사용 처리된 상품 기록. 토스도 기존 쿠팡 호환 파일을 사용 |
| `토스 자동화/src/자동발행상태기록파일/coupang_selection_history.json` | 최근 선택 이력 |
| `토스 자동화/src/자동발행상태기록파일/coupang_angle_rotation.json` | 글 관점 회전 기록 |
| `토스 자동화/src/자동발행상태기록파일/automation.lock` | 중복 실행 방지 락 |
| `토스 자동화/src/자동발행상태기록파일/logs/` | 실행 로그 |
| `토스 자동화/runtime/state/*.json` | 초기 설계상 토스 상태 파일. 현재 실제 사용은 확인 필요 |

세션/캐시:

| 경로 | 설명 |
|---|---|
| `C:\Users\itwill\자동화 공부\toss_chatgpt_profile` | ChatGPT 로그인 세션 |
| `C:\Users\itwill\자동화 공부\toss_naver_profile` | 네이버 로그인 세션 |
| `토스 자동화/runtime/chrome/` | 크롬 런타임 구조. 과거 세션/캐시성 파일 포함 가능 |
| `C:\Users\itwill\자동화 공부\토스` | 현재 코드가 쓰지 않는 크롬 프로필 데이터 성격 |

생성물:

| 경로 | 설명 |
|---|---|
| `토스 자동화/output/drafts/` | 초안 저장 위치 |
| `토스 자동화/output/images/` | 생성 이미지 저장 위치 |
| `토스 자동화/src/__pycache__/` | Python 캐시 |

민감 파일:

- `*.env`, `.env`, `src/.env`
- Chrome 프로필 폴더 전체
- 쿠키, 로그인 데이터, `Local State`, `Default/Network/Cookies`
- 실행 로그에 계정/링크/상태가 들어갈 수 있음
- CSV에 실제 수익 링크가 들어 있음

## Operational Rules

토스쇼핑 쉐어링크 규칙:

- 반드시 토스쇼핑 쉐어링크를 사용한다.
- 일반 공유 링크를 수익 링크처럼 바꾸거나 대체하지 않는다.
- 글에는 필수 광고 고지문이 들어가야 한다.
- 자동 앱 실행, 강제 클릭, 플로팅 배너, 무작위 DM/SMS/댓글 유도 금지.
- 토스 공식, 공식 특가, 최저가, 무조건 추천, 인생템, 역대급 같은 표현 금지.
- 의료/치료/질병 개선/체중감량/효능 보장 표현 금지.

코드 운영 규칙:

- 토스 CSV는 `publish_queue.csv` 순서를 우선한다.
- 토스 CSV가 감지되면 쿠팡 API는 비활성화된다.
- 발행 성공 후 `coupang_used_products.json`에 사용 기록을 남긴다.
- 같은 상품 재발행은 사용 기록 삭제 후 가능하지만 사용자 승인 필요.
- 상품 링크는 본문 중간 이후와 마지막에 2회 삽입된다.
- 상단 링크는 광고성 신호가 강하다는 이유로 넣지 않는다.
- 해시태그는 ChatGPT 결과를 그대로 쓰지 않고 로컬 보정 함수가 상품군별 태그를 우선 배치한다.
- 약한 제목은 로컬 보정 함수가 더 클릭 가능한 제목으로 교체한다.
- 빈 인용구는 `repair_quote_markers()`와 네이버 입력 단계에서 보정한다.
- 이미지 생성은 렌더링 안정화, 크기 안정화, 흰 화면 검사 후 저장한다.

ChatGPT 웹 규칙:

- 최초 진입 때만 토스 프로젝트 URL을 확인한다.
- 이후 ChatGPT가 대화 URL로 바뀌는 것은 정상이며, 같은 세션 입력창이 준비되면 계속 진행한다.
- 사람 확인/로그인 화면은 자동 우회하지 않는다. 사용자가 직접 처리해야 한다.
- 본문 긴 프롬프트는 붙여넣기 후 최소 10초 대기하고 전송한다.
- 제목/해시태그처럼 짧은 프롬프트는 입력창 글자 수 안정화 확인 후 전송한다.

네이버 규칙:

- 네이버 로그인 세션은 `toss_naver_profile`을 재사용한다.
- 저장 세션이 없거나 만료되면 브라우저에서 사용자가 직접 로그인한다.
- 자동 발행 명령은 실제 공개 게시글을 만들 수 있으므로 사용자 승인 필요.

## Safety Rules

절대 하지 말 것:

- `main.py`, `main_golf.py` 수정. 사용자가 명시적으로 금지했다.
- 실제 `.env` 값, 토큰, 비밀번호, 쿠키, 세션 파일 내용을 출력하거나 문서화.
- `git reset --hard`, `git checkout --`, 대량 삭제, 세션 폴더 삭제를 임의 실행.
- 토스 수익 링크를 일반 링크로 대체.
- 사용자가 삭제하겠다고 한 게시글 외 임의 네이버 게시글 수정/삭제.
- `node_modules`, `dist`, `build`, Chrome profile, cache를 임의 정리.
- 다른 프로젝트(`camp-platform`, `티스토리 자동화 ing`, `네이버 자동화 ing`, `크몽 전용`, `개인프로젝트`)를 현재 작업 범위 밖에서 임의 수정.

사용자 승인 필요:

- `python "토스 자동화\src\toss.py" --post-type 토스`
- 네이버 블로그 실제 발행/수정/삭제
- `Stop-Process`로 실행 중인 자동화 프로세스 종료
- `coupang_used_products.json` 사용 기록 삭제
- Chrome 프로필 폴더 이동/삭제/백업
- 스케줄러 등록/삭제
- 외부 API 호출을 활성화하는 변경
- Git 커밋/스태시/리셋/클린

Git 작업 주의:

- `untracked`는 Git이 아직 추적하지 않는 새 파일/폴더라는 뜻이며, 실행에는 문제 없지만 커밋/원격 백업에는 포함되지 않는다.
- `AGENTS.md`, `docs/`, `토스 자동화/`는 현재 untracked로 보일 수 있다.
- `토스 자동화/`를 통째로 `git add` 하지 않는다. 세션, 로그, 캐시, CSV 수익 링크 등 민감/런타임 파일이 섞일 수 있다.
- Git에 올릴 때는 먼저 `.gitignore`를 확인/보강하고, 코드와 문서만 선별해서 `git add` 한다.
- 권장 선별 대상은 `AGENTS.md`, `docs/work-log.md`, `토스 자동화/src/toss.py`, `토스 자동화/PROJECT_CONTEXT.md`, 필요한 `토스 자동화/prompts/*.md`, 필요한 설정 예시/문서 파일이다.
- Chrome 프로필, `.env`, 로그, 캐시, `__pycache__`, 실제 쿠키/세션, 불필요한 런타임 산출물은 Git에 올리지 않는다.
- Git 커밋 또는 GitHub push는 사용자에게 먼저 확인한다.
- `git clean`은 untracked 파일을 삭제할 수 있으므로 사용자 승인 없이 실행하지 않는다.

브라우저 자동화 주의:

- 정상 실행 시 네이버 ChromeDriver와 ChatGPT ChromeDriver 두 개가 뜬다.
- 두 창은 같은 Python 프로세스 안에서 움직이므로 서로 락 경쟁하지 않는다.
- `python.exe`가 두 개 이상 살아 있으면 중복 실행으로 락 대기/충돌이 생길 수 있다.

다른 자동화 폴더 운영 메모:

- `네이버 자동화 ing/네이버 블로그 글쓰기/skssj2628/skssj2628.py`와 `네이버 자동화 ing/네이버 블로그 글쓰기/제미나이웹.py`는 실제 네이버 공개 발행을 수행한다. 수동 실행, 스케줄러 등록/삭제, 발행 재시도는 사용자 명시 승인 후 진행한다.
- `skssj2628.py`는 네이버 에디터 인용구 툴바(`button[data-name="quotation"]`)를 의도적으로 사용해 인용구 2~6만 선택한다. 기본 인용구 `default`를 다시 넣지 말고, 빈 `[인용구]`는 툴바를 열기 전에 건너뛰어야 한다.
- `skssj2628.py` 일상글은 넓은 일기형 주제 대신 세부 검색 의도형 주제를 유지한다. 주제별 핵심 원리, 정확한 용어, 확인 순서, 실천 포인트, FAQ, 사실 확인 주의사항을 보존하고, 정책/요금/날씨 수치는 공식 확인 없이 단정하지 않는다.
- `제미나이웹.py`의 인용구 로직은 `skssj2628.py`와 다를 수 있다. 인용구 스타일을 맞출 때는 먼저 실제 `insert_quotation()` 구현을 확인하고, 두 파일을 동일하다고 가정하지 않는다.
- `네이버 자동화 ing/네이버 블로그 글쓰기/skssj2629/skssj2629.py`는 네이버 쇼핑커넥트 `skssj2629` 전용 발행 파일이다. 기본 CSV는 `skssj2629/skssj2629_naver.csv`이고, 수동 발행 실행은 사용자 명시 승인 후 진행한다.
- `skssj2629.py`의 일상/광고 프롬프트는 "성분·소재·동선까지 따지는 청담 사는 자녀 둔 어머니" 컨셉을 유지한다. 전문용어는 쉬운 말로 풀고, `~하더라고요`, `~거든요`, `~잖아요` 같은 자연스러운 블로그 말투를 섞는다.
- `skssj2629.py`의 일상/광고 본문은 너무 짧게 끊지 않고 일반 본문 줄을 40자 안팎으로 나누는 모바일형 흐름을 유지한다. URL, 해시태그, 네이버 입력 마커는 줄바꿈 보정에서 원형을 보존하고, 상품명 텍스트는 임의 변경하지 않는다.
- `skssj2629/skssj2629(스케줄러).py`는 Windows 작업 `NaverBlogAutoPost_2629_*`와 `NaverBlogAutoPost_2629_RefreshDaily`를 관리한다. 등록/삭제/변경은 사용자 명시 승인 후 진행하고, 보조 스크립트는 같은 폴더의 `skssj2629/자동발행실행보조파일/`을 사용한다.
- 네이버 자동화는 전역 클립보드를 공유한다. 이미지 붙여넣기는 클립보드에 이미지가 올라간 것을 확인한 뒤에만 수행하고, 프롬프트 텍스트가 남은 상태에서 `Ctrl+V`가 실행되지 않게 한다.
- 네이버 ID/비밀번호, 텔레그램 토큰, 쿠팡 API 키, 티스토리 계정값은 코드에 기본값으로 넣지 않는다. 필요한 값은 `.env` 또는 OS 환경변수에서 읽게 한다.
- `COUPANG_CSV_PATH`는 계정별 기본 CSV 선택을 덮어쓸 수 있으므로 명시적으로 필요할 때만 설정한다. 특히 `products_db.csv` 같은 오래된 값이 남으면 `제미나이웹.py`가 잘못된 DB를 찾을 수 있다.
- `skssj2628.py`의 현재 쿠팡 링크 정책은 본문 중간 1회다. 마지막 1회로 옮기거나 링크 횟수를 바꾸려면 사용자와 성과 기준/A-B 테스트 방향을 먼저 합의한다.
- `네이버 자동화 ing/네이버 블로그 글쓰기/*/자동발행상태기록파일/logs/`는 발행 성공/실패 판단의 1차 근거다. 스케줄러 이슈를 볼 때는 최근 로그와 `automation.lock`, 실행 중 `python/chromedriver` 프로세스를 먼저 확인한다.
- `네이버 자동화 ing/네이버 블로그 글쓰기/*_db.csv`에는 제휴/상품 링크가 들어갈 수 있다. 정리 작업 시 백업을 먼저 만들고, 링크 원문은 문서나 답변에 노출하지 않는다.
- `티스토리 자동화 ing/golf/main_golf.py`와 `G스케줄러`는 실제 티스토리 발행/스케줄 등록에 연결된다. 실행, 등록, 삭제는 사용자 명시 승인 후 진행한다.
- `티스토리 자동화 ing/golf/main_golf.py`의 해외 골프여행 글은 사전 리서치 브리프와 상세도 검증을 거쳐야 한다. 시간표, 이동수단, 예상 금액, 골프장 후보, 식당/관광, 보험/수하물 정보가 빠진 글은 발행 흐름에서 막는 방향을 유지한다.
- `티스토리 자동화 ing/golf/main_golf.py`에서 이미지 생성 뒤 본문 HTML 생성이 멈추면 먼저 `runtime/logs/scheduled_golf/*.log`, `runtime/logs/chatgpt_web_runs_golf.csv`, 실행 중 `pythonw/chromedriver` 중복 여부를 확인한다. 본문 프롬프트를 줄이더라도 `validate_golf_research_brief()`와 `validate_golf_travel_specificity()`를 우회하지 않는다.
- 골프 본문 프롬프트에는 원본 리서치 브리프 전체를 다시 넣지 말고, 시간표·지명·이동수단·예상 금액·골프장 후보·식당/관광·보험/수하물 핵심을 압축한 본문용 브리프를 사용한다. 품질 저하를 막기 위해 비용 수치, 시간대, 보험·수하물 체크가 압축본에 남아 있는지 확인한다.
- `티스토리 자동화 ing/src/tistory_automation/main.py`는 쿠팡/일상 전용이다. 골프, 골프여행, 골프백, 라운딩, 그린피, 캐디 등 골프 주제는 `티스토리 자동화 ing/golf/main_golf.py`와 `G스케줄러`에서만 생성한다. daily 프롬프트에 골프 축을 다시 넣지 않는다.
- `티스토리 자동화 ing/src/tistory_automation/main.py`와 `golf/main_golf.py`는 일상/쿠팡/골프/health 모두 이미지 확보 후 첫 본문 프롬프트 전송 전에 10초 대기하고, 본문 프롬프트 전송 후 ChatGPT 스트리밍 중지 문구가 사라지면 3초 더 기다린 뒤 새로고침 1회로 안정화한다. 본문 프롬프트를 보내기 전에 새로고침하거나 같은 프롬프트를 자동 재전송하지 않는다.
- 티스토리 기존 글과 향후 글 전체에 공통 광고를 넣을 때는 자동화 본문 HTML보다 티스토리 스킨 편집을 우선한다. `camp-platform/public/HTML편집.txt`는 스킨 편집용 보관본이며, 로컬 `public` 폴더에 두는 것만으로 실제 티스토리에 적용되지 않는다.
- 티스토리 본문 중간 AdSense 삽입은 `#article-view` 로드 후 JS가 `.tistory-mid-adsense`를 추가하는 방식이다. 공개 글 확인은 `페이지 소스 보기`보다 DevTools Elements에서 `.tistory-mid-adsense` 또는 해당 `data-ad-slot`을 검색한다.
- AdSense `ca-pub-*` 값은 공개 소스에 노출될 수 있는 게시자 ID지만 문서/답변/로그에는 원문 전체를 남기지 않는다. 필요하면 `.env` 값으로 치환하거나 마스킹해서 다룬다.
- `golf/main_golf.py --post-type health`는 건강식품 쿠팡 글이며 `G스케줄러`에서 `--publish`로 등록되면 공개 발행된다. 건강식품 쿠팡글을 멈추려면 `golf_24h_random_15_current.json`와 `Tistory_Golf_24H_Random*` 작업의 `--post-type health --publish` 여부를 확인하고 사용자 승인 후 비활성화/재등록한다.
- `golf/main_golf.py` 건강식품 쿠팡 본문은 프롬프트가 `style` 생성을 금지하고 `_style_coupang_html_for_tistory()`가 인라인 스타일을 후처리한다. 글자 크기 조정은 프롬프트보다 이 후처리 스타일 값을 먼저 확인한다.
- 현재 `티스토리 자동화 ing`의 Windows 작업 스케줄러 `TistoryChatGPTAutoPost_*`, `TistoryChatGPTAutoPost_RefreshDaily`, `Tistory_Golf_24H_Random*`, `TestPythonW`는 사용자 요청으로 비활성화된 상태다. 다시 켜거나 재등록하려면 사용자 명시 승인 후 진행한다.

## Coding Conventions

- 주 코드는 단일 Python 파일 `토스 자동화/src/toss.py`에 있다.
- Python 3.10 이상 필요. 코드에서 `sys.version_info < (3, 10)`을 검사한다.
- 현재 로컬 실행은 Python 3.14 경로가 보였다. 다른 환경은 확인 필요.
- 한글 문자열과 경로가 많으므로 UTF-8 기준으로 읽고 편집한다.
- PowerShell 실행 시 콘솔 인코딩 문제 방지를 위해 `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`을 설정한다.
- 수동 코드 편집은 최소 범위로 한다.
- `.env.example`, `README.md`, `PROJECT_CONTEXT.md`, `AGENTS.md`에는 비밀값을 쓰지 않는다.
- CSV는 Excel로 열면 인코딩/따옴표가 바뀔 수 있으므로 주의한다.
- 토스 작업에서 기존 쿠팡 함수/파일명이 남아 있다. 이름만 쿠팡이고 토스 호환 경로로 쓰는 부분이 있으므로 무작정 이름 변경하지 않는다.
- `prompts/*.md`는 보관본이고, 실제 실행 프롬프트는 `toss.py` 안에도 있다. 프롬프트 수정 시 둘 중 어느 경로가 실제 실행되는지 확인한다.

확인된 Python 외부 패키지 import:

```text
selenium
Pillow
requests
pyperclip
schedule
filelock
```

`토스 자동화` 전용 `requirements.txt`는 확인되지 않았다. 새 환경 설치 절차는 확인 필요다.

## Verification Checklist

코드 수정 후 최소 확인:

```powershell
python -m py_compile "토스 자동화\src\toss.py"
```

환경/상태 확인:

```powershell
Get-Process python,chromedriver -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime,Path
git status --short -- "토스 자동화"
```

CSV 확인:

```powershell
Import-Csv -LiteralPath "토스 자동화\data\toss_products.csv" | Select-Object product_name,main_keyword,toss_sharelink,category
Get-Content -Encoding UTF8 -LiteralPath "토스 자동화\data\publish_queue.csv"
```

발행 전 체크:

- `toss.py` 문법 검사 통과
- `python.exe` 중복 실행 없음
- `chromedriver.exe` 이전 실행 잔여 없음 또는 사용자가 이해하고 있음
- `coupang_used_products.json`에서 같은 상품 사용 여부 확인
- ChatGPT 프로젝트 URL 로그가 기본 토스 프로젝트 URL인지 확인
- 네이버 로그인 세션 정상 여부 확인
- 사용자가 발행 실행을 명시 승인했는지 확인

테스트/빌드:

- `토스 자동화` 범위에 자동 테스트, lint, build 스크립트는 확인되지 않았다.
- 현재 가능한 검증은 `py_compile`과 수동 CSV/상태 확인이다.

## Handoff Notes

토스 자동화 작업을 이어갈 때 다음 세션에서 먼저 읽을 파일:

1. `AGENTS.md`
2. `docs/work-log.md`
3. `토스 자동화/PROJECT_CONTEXT.md`
4. `토스 자동화/src/toss.py`
5. `토스 자동화/data/publish_queue.csv`
6. `토스 자동화/data/toss_products.csv`
7. `토스 자동화/src/자동발행상태기록파일/coupang_used_products.json`
8. `토스 자동화/docs/toss_sharelink_rules.md`
9. `토스 자동화/src/.env.example`

운영 규칙:

- 의미 있는 코드/운영 변경을 한 세션은 `docs/work-log.md`에 짧게 남긴다.
- 새 운영 규칙, 안전 규칙, 실행 명령, 민감 파일 주의사항이 생기면 `AGENTS.md`도 함께 갱신한다.
- work log는 장문 회고가 아니라 다음 CLI 세션이 바로 이어갈 수 있는 변경사항, 검증 결과, 다음 작업만 적는다.

Git 상태 주의:

- Git 루트는 `C:\Users\itwill\자동화 공부`.
- 전체 `git status --short`는 과거 확인 시점에 약 799줄이었다. 현재 값은 작업 전 다시 확인한다.
- 추적 파일 변경도 과거 확인 시점에 약 754줄로 많았고, 대부분 `camp-platform`, `node_modules`, 기타 프로젝트 변경/삭제가 섞여 있었다.
- `토스 자동화`가 현재 루트에 없거나 untracked로 보일 수 있으므로, 작업 전 `Test-Path`와 `git status --short -- "토스 자동화"`로 확인한다.
- 어떤 변경도 임의로 revert/reset/delete 하지 말 것.

최근 `토스 자동화` 주요 변경 파일:

- `토스 자동화/src/toss.py`
- `토스 자동화/PROJECT_CONTEXT.md`
- `토스 자동화/prompts/naver_product_post_prompt.md`
- `토스 자동화/prompts/naver_title_prompt.md`
- `토스 자동화/prompts/naver_hashtag_prompt.md`
- `토스 자동화/src/자동발행상태기록파일/*.json`
- `토스 자동화/data/*.csv`

확인 필요:

- 새 PC/새 Python 환경에서 필요한 정확한 `requirements.txt`
- `runtime/state/toss_*.json`와 `src/자동발행상태기록파일/*.json`의 장기 통합 여부
- `토스 자동화/runtime/chrome/naver` 과거 세션 폴더의 보존/삭제 여부
- 루트의 `토스` 폴더를 백업 보관할지 삭제할지

## 확인한 근거 파일

토스 자동화 관련 내용은 다음 파일과 명령 결과를 근거로 작성했다. 현재 루트에 해당 파일이 있는지는 작업 전 다시 확인한다.

- `git rev-parse --show-toplevel`
- `rg --files "토스 자동화"`
- `rg --files -g ...` 루트 구조 확인
- `git status --short -- "토스 자동화"`
- 전체 `git status --short` 라인 수 요약
- `토스 자동화/README.md`
- `토스 자동화/PROJECT_CONTEXT.md`
- `토스 자동화/.gitignore`
- `토스 자동화/src/.env.example`
- `토스 자동화/src/README.md`
- `토스 자동화/src/toss.py`
- `토스 자동화/config/toss_product_schema.json`
- `토스 자동화/data/*.csv`
- `토스 자동화/docs/*.md`
- `토스 자동화/prompts/*.md`
- `토스 자동화/src/자동발행상태기록파일/*.json`
