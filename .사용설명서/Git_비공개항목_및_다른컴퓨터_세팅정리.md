# Git 비공개 항목 및 다른 컴퓨터 세팅 정리

작성 기준일: 2026-04-24  
기준 위치: `C:\Users\itwill\자동화 공부`

이 문서는 현재 각 폴더의 `git 추적 상태`, `.gitignore`, 실제 파일 존재 상태를 기준으로 정리한 것입니다.

## 먼저 결론

세 폴더 모두 공통적으로:

- 코드 자체는 `git clone` 또는 `git pull`로 대부분 가져올 수 있습니다.
- 하지만 `개인정보`, `로그인 세션`, `로컬 가상환경`, `배포 연결 정보`, `일부 런타임 산출물`은 Git에 안 올라갑니다.
- 그래서 다른 컴퓨터에서 "코드만 받는 것"과 "지금 이 컴퓨터와 거의 같은 상태로 바로 자동화가 도는 것"은 다릅니다.

즉:

- 단순히 코드 작업만 할 거면: 카톡으로 폴더를 옮길 필요가 거의 없습니다.
- 로그인 상태까지 그대로 옮기고 싶으면: 일부 항목은 Git이 아니라 별도로 옮기거나 다시 로그인해야 합니다.
- 가장 안전한 방식은: `git clone` 후, 필요한 비밀값만 새 컴퓨터에 다시 넣고, 로그인은 새 컴퓨터에서 다시 하는 것입니다.

---

## 1. `camp-platform`

### 현재 Git에 안 올라가는 항목

현재 확인된 비추적/무시 항목:

- `.env`
- `.vercel/`
- `node_modules/`
- `dist/`
- `.cache/`
- `AGENTS.md`

의미:

- `.env`: Supabase, Kakao, 각 캠페인 플랫폼 쿠키/토큰/로그인 정보
- `.vercel/`: 현재 로컬 폴더가 어떤 Vercel 프로젝트에 연결돼 있는지에 대한 로컬 정보
- `node_modules/`: 설치된 npm 패키지
- `dist/`: 빌드 결과물
- `.cache/`: 로컬 캐시
- `AGENTS.md`: 로컬 운영 메모 성격 문서

### `.env`에 다시 넣어야 하는 값

`.env.example` 기준으로 필요한 대표 항목:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_KAKAO_MAP_APP_KEY`
- `KAKAO_REST_API_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `REVU_AUTHORIZATION`
- `REVIEWNOTE_COOKIE`
- `REVIEWPLACE_COOKIE`
- `DINNERQUEEN_COOKIE`
- `GANGNAM_COOKIE`
- `POPOMON_COOKIE`
- `MRBLOG_COOKIE`
- `MRBLOG_X_CSRF_TOKEN`
- `MRBLOG_LOGIN_ID`
- `MRBLOG_LOGIN_PASSWORD`

즉, 이 폴더는 코드만 받아서는 바로 동일하게 동작하지 않습니다. `.env` 값은 별도로 다시 채워야 합니다.

### 다른 컴퓨터에서 필요한 것

필수:

- Node.js `20.x`
- `npm install`

상황별 추가:

- 프론트 개발만 할 거면: `npm install` 후 `.env` 작성
- 크롤러까지 돌릴 거면: `.env` 작성이 필수
- Playwright 브라우저가 없어서 크롤링이 실패하면: Playwright 브라우저 설치가 추가로 필요할 수 있음

### 카톡으로 옮겨야 하나?

보통은 **아니요**.

권장 순서:

1. 새 컴퓨터에서 저장소 clone
2. `camp-platform` 폴더로 이동
3. `npm install`
4. `.env.example`를 참고해서 새 `.env` 작성
5. 필요하면 Vercel은 새 컴퓨터에서 다시 연결

다만 아래를 "그대로" 유지하고 싶으면 별도 이동이 필요할 수 있습니다.

- 기존 `.env` 내용
- 기존 `.vercel/` 연결 상태

하지만 `.env`는 카톡으로 보내는 것보다 직접 다시 넣는 방식이 더 안전합니다.

### 판단

- 코드 작업: Git만으로 충분
- 동일한 실행 환경 복원: `.env` 재설정 필요
- Vercel 연결까지 동일 복원: `.vercel/`을 복사하거나 새 컴퓨터에서 재연결 필요

---

## 2. `티스토리 자동화 ing`

### 현재 Git에 안 올라가는 항목

현재 확인된 비추적/무시 항목:

- `.env`
- `.env.example`
- `.venv/`
- `runtime/`
- `__pycache__/`
- `src/tistory_automation/__pycache__/`
- `src/tistory_automation/coupang/__pycache__/`
- `src/tistory_automation/pipeline/__pycache__/`
- `data/products/건강식품_db.csv`

의미:

- `.env`: 티스토리/쿠팡 계정 관련 민감값
- `.venv/`: 현재 컴퓨터에서 만든 Python 가상환경
- `runtime/`: 세션, 로그, 임시 상태, 실행 산출물
- `__pycache__/`: Python 캐시
- `data/products/건강식품_db.csv`: 현재 로컬 데이터 CSV

반대로 Git에 올라가 있는 핵심 파일:

- `requirements.txt`
- `pyproject.toml`
- `scripts/run_chatgpt_web.ps1`
- `src/tistory_automation/...`
- `data/products/products_db_category.csv`

### `.env`에 다시 넣어야 하는 값

현재 템플릿 기준:

- `TISTORY_ID`
- `TISTORY_PASSWORD`
- `COUPANG_ACCESS_KEY`
- `COUPANG_SECRET_KEY`
- `COUPANG_SUB_ID`
- `COUPANG_API_ENABLED`

즉, 계정/API 값은 새 컴퓨터에 다시 넣어야 합니다.

### 다른 컴퓨터에서 필요한 것

필수:

- Python `3.12+`
- 새 가상환경 생성
- 패키지 설치

실행 구조상 현재 스크립트는 프로젝트 내부의:

- `.venv\Scripts\python.exe`

를 직접 사용합니다. 그래서 새 컴퓨터에서는 `.venv`를 새로 만들어야 합니다.

추천 절차:

1. 저장소 clone
2. `티스토리 자동화 ing` 폴더로 이동
3. `python -m venv .venv`
4. `.venv\Scripts\pip install -r requirements.txt`
5. `.env` 작성
6. 필요하면 `.\scripts\run_chatgpt_web.ps1` 실행

### 카톡으로 옮겨야 하나?

경우를 나누면:

- 코드만 옮길 목적: **아니요**
- 현재 로그인 세션/실행 상태까지 그대로 옮기고 싶음: **일부는 별도 이동 또는 재로그인 필요**

특히 `runtime/`은 Git에 안 올라가므로, 여기에 들어 있는 항목은 자동으로 복원되지 않습니다.

대표적으로 영향이 큰 것:

- ChatGPT 세션
- Tistory 세션
- 실행 로그
- 스케줄 상태
- 임시 파일

이 프로젝트는 세션성 데이터가 `runtime/` 아래에 쌓이는 구조라서, 새 컴퓨터에서 완전히 같은 상태를 원하면:

- `runtime/`을 별도로 복사하거나
- 새 컴퓨터에서 다시 로그인/재실행

중 하나가 필요합니다.

### 가장 현실적인 권장 방식

- 카톡으로 전체 폴더를 보내는 방식은 비권장
- Git으로 코드만 받고
- 새 컴퓨터에서 `.venv` 재생성
- `.env` 재작성
- ChatGPT/Tistory 로그인은 새 컴퓨터에서 다시 진행

### 판단

- 코드 작업: Git만으로 충분
- 자동화 실행 복원: Python 설치 + `.venv` 재생성 + `.env` 작성 필요
- 로그인 상태까지 동일 복원: `runtime/` 별도 복사 또는 재로그인 필요

---

## 3. `네이버 자동화 ing`

이 폴더는 내부가 두 덩어리로 나뉩니다.

- `네이버 블로그 글쓰기`
- `네이버 이웃 추가`

### 현재 Git에 안 올라가는 항목

현재 확인된 비추적/무시 항목:

- `네이버 블로그 글쓰기/.env`
- `네이버 블로그 글쓰기/__pycache__/`
- `네이버 블로그 글쓰기/자동발행상태기록파일/logs/`
- `네이버 블로그 글쓰기/자동발행실행보조파일/__pycache__/`
- `네이버 이웃 추가/build/Premium_Neighbor_Bot/localpycs/`

추가로 `.gitignore` 규칙상 Git에 안 올라가게 설계된 것:

- `ChromeGeminiBot*`
- `ChromeNaverBot*`
- `.env`, `.env.*`
- 각종 `__pycache__`
- 로그 파일
- 임시 이미지

### 반대로 이미 Git에 올라가 있는 중요한 항목

이미 추적 중인 파일:

- `네이버 블로그 글쓰기/products_db.csv`
- `네이버 블로그 글쓰기/자동발행상태기록파일/*.json`
- `네이버 블로그 글쓰기/스케줄러.py`
- `네이버 블로그 글쓰기/제미나이웹.py`
- `네이버 블로그 글쓰기/개발환경설정파일/requirements.txt`
- `네이버 블로그 글쓰기/자동발행실행보조파일/*.ps1`
- `네이버 이웃 추가/dist/Premium_Neighbor_Bot.exe`
- `네이버 이웃 추가/build/...` 대부분

이 말은:

- `products_db.csv`는 Git으로 내려받아집니다.
- 자동발행 상태 JSON도 Git으로 내려받아집니다.
- 따라서 예전보다 "상태 이어받기"가 쉬운 편입니다.

### 새 컴퓨터에서 다시 넣어야 하는 값

문서와 코드 기준으로 필요한 대표 항목:

- `NAVER_ID`
- `NAVER_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

이 값들은 Git으로 안 옵니다.

### 중요한 추가 포인트 1: Chrome 로그인 프로필

이 프로젝트는 다음 프로필 폴더를 사용합니다.

- `C:\Users\<사용자명>\ChromeGeminiBot`
- `C:\Users\<사용자명>\ChromeNaverBot_<네이버아이디>`

이 폴더들은 Git에 안 올라갑니다.

즉, 새 컴퓨터에서 자동화를 완전히 같은 상태로 바로 돌리고 싶다면:

- 이 프로필 폴더를 직접 복사하거나
- 새 컴퓨터에서 Gemini/네이버에 다시 로그인해야 합니다.

권장 방식은 **새 컴퓨터에서 다시 로그인**입니다.  
프로필 폴더 통복사는 환경 차이 때문에 실패할 수도 있습니다.

### 중요한 추가 포인트 2: Python 경로 하드코딩

현재 아래 파일에는 Python 경로가 하드코딩돼 있습니다.

- `네이버 블로그 글쓰기/자동발행실행보조파일/run_scheduled_post.ps1`
- `네이버 블로그 글쓰기/자동발행실행보조파일/run_refresh_schedule.ps1`

현재 경로 형식:

- `C:\Users\itwill\AppData\Local\Programs\Python\Python313\python.exe`

따라서 새 컴퓨터에서는:

- Python 설치 경로가 다르면 이 부분을 수정해야 합니다.

이건 Git으로 받아도 자동 해결되지 않습니다.

### 다른 컴퓨터에서 필요한 것

`네이버 블로그 글쓰기` 기준 필수:

- Python 설치
- `pip install -r "네이버 블로그 글쓰기\개발환경설정파일\requirements.txt"`
- 환경변수 또는 `.env` 설정
- Chrome 설치
- 네이버/Gemini 로그인

`requirements.txt` 기준 패키지:

- `selenium`
- `Pillow`
- `requests`
- `pyperclip`
- `schedule`

`네이버 이웃 추가`는 상황이 다릅니다.

- 이미 `dist/Premium_Neighbor_Bot.exe`가 Git에 올라가 있으므로
- "실행만" 할 거면 Python 없이도 가능할 수 있습니다.
- 하지만 소스 수정이나 재빌드를 하려면 별도 Python 환경을 다시 맞춰야 합니다.

### 카톡으로 옮겨야 하나?

정리하면:

- 코드만 옮길 목적: **아니요**
- 네이버/Gemini 로그인 상태까지 그대로 옮길 목적: **일부는 별도 복사 필요**

카톡 또는 외부 복사로 옮길 수 있는 대표 항목:

- `C:\Users\<기존사용자>\ChromeGeminiBot`
- `C:\Users\<기존사용자>\ChromeNaverBot_<네이버아이디>`

하지만 권장도는 낮습니다.  
가장 안정적인 방식은 새 컴퓨터에서 다시 로그인하는 것입니다.

### 판단

- 코드 작업: Git만으로 충분
- 블로그 자동화 실행: Python 설치 + 패키지 설치 + 환경변수 입력 + Chrome 로그인 필요
- 로그인 상태까지 즉시 복원: Chrome 프로필 별도 복사 필요할 수 있음
- 스케줄러까지 복원: Python 경로 하드코딩 수정 필요 가능성 높음

---

## 카톡으로 옮겨야 하는 것 / 안 옮겨도 되는 것

### 카톡이나 USB 등으로 별도 이동이 "필요할 수 있는" 것

- 각 폴더의 실제 `.env`
- `camp-platform/.vercel/`
- `티스토리 자동화 ing/runtime/`
- `C:\Users\<사용자명>\ChromeGeminiBot`
- `C:\Users\<사용자명>\ChromeNaverBot_<네이버아이디>`

### 보통은 옮기지 말고 새 컴퓨터에서 다시 만드는 것이 좋은 것

- `.venv/`
- `node_modules/`
- `dist/`
- `.cache/`
- `__pycache__/`
- 각종 로그 폴더

이유:

- 컴퓨터마다 경로가 다름
- 버전 차이 문제 발생 가능
- 용량만 크고 복원 안정성은 낮음

---

## 폴더별 추천 복원 방식

### `camp-platform`

추천:

1. Git으로 받기
2. Node.js 20 설치
3. `npm install`
4. `.env` 수동 작성
5. 필요 시 Vercel 재연결

### `티스토리 자동화 ing`

추천:

1. Git으로 받기
2. Python 3.12+ 설치
3. `python -m venv .venv`
4. `pip install -r requirements.txt`
5. `.env` 수동 작성
6. 새 컴퓨터에서 로그인/실행

### `네이버 자동화 ing`

추천:

1. Git으로 받기
2. Python 설치
3. `requirements.txt` 패키지 설치
4. 환경변수 또는 `.env` 다시 설정
5. Chrome 설치
6. 네이버/Gemini 새 로그인
7. `run_scheduled_post.ps1`, `run_refresh_schedule.ps1`의 Python 경로 확인

---

## 가장 정확한 한 줄 요약

- `camp-platform`: 코드만 Git으로 충분, 실행하려면 `.env`는 다시 넣어야 함
- `티스토리 자동화 ing`: 코드만 Git으로 충분, 실행하려면 `.venv` 재생성 + `.env` + 세션 재로그인 필요
- `네이버 자동화 ing`: 코드와 일부 상태 JSON은 Git으로 충분, 하지만 계정정보/Chrome 로그인 프로필/Python 경로는 별도 처리 필요

---

## 내가 보기엔 가장 안전한 운영 방식

카톡으로 폴더 전체를 자주 옮기는 방식보다 아래가 더 안전합니다.

1. 코드는 무조건 Git으로 이동
2. 비밀값은 새 컴퓨터에 직접 다시 입력
3. 로그인 세션은 가능하면 새 컴퓨터에서 다시 로그인
4. 가상환경과 패키지는 새 컴퓨터에서 재설치
5. 하드코딩된 경로만 마지막에 점검

이 방식이 개인정보 노출 위험도 가장 낮고, 나중에 어디가 문제인지 찾기도 가장 쉽습니다.
