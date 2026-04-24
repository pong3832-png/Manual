## 2. Claude Code용 CLAUDE.md

> **사용법**: 프로젝트 루트에 `CLAUDE.md` 파일로 저장

```markdown
# CLAUDE.md — 프로젝트 컨텍스트

## 프로젝트 개요
- **목적**: 블로그 자동화, 체험단 플랫폼, 수익화 자동화 통합 개발
- **기술 스택**: Python 3.11+, Node.js 20+, Next.js, Selenium, Playwright
- **OS**: Windows 11
- **패키지 관리**: pip, npm
- **에디터**: VS Code + Gemini Code Assist

## 디렉토리 구조
```
자동화 공부/
├── 티스토리 자동화 ing/    # Python 기반 티스토리 블로그 자동 포스팅
├── 네이버 자동화 ing/      # 네이버 서로이웃/블로그 자동화
├── camp-platform/          # Next.js 체험단 플랫폼
├── 크몽 전용/              # 외주/판매용 자동화 스크립트
└── 개인프로젝트/           # 실험적 프로젝트
```

## 코딩 컨벤션
- **Python**: snake_case, docstring 필수, type hints 사용
- **JavaScript**: camelCase, ES6+ 문법
- **파일명**: 한국어 허용 (Windows 환경)
- **인코딩**: 모든 파일 UTF-8
- **커밋 메시지**: 한국어 허용, conventional commits 스타일 권장

## 자주 쓰는 명령어
| 명령어 | 용도 |
|--------|------|
| `python -m 티스토리자동화ing.scheduler` | 스케줄러 실행 |
| `npm run dev` | Next.js 개발 서버 |
| `npm run crawl` | 체험단 크롤러 실행 |
| `pip install -r requirements.txt` | Python 의존성 설치 |

## 알려진 이슈 & 주의사항
- Windows Task Scheduler에서 Python 스크립트 실행 시 경로에 공백이 있으면 따옴표 필수
- Selenium ChromeDriver 버전은 Chrome 브라우저 버전과 반드시 일치
- 티스토리 API 토큰은 환경변수로 관리 (.env 파일)
- 쿠팡파트너스 API key는 절대 코드에 하드코딩 금지
- ChatGPT 웹 자동화 시 로딩 대기 시간 충분히 확보 (최소 10초)

## 테스트
- Python: `pytest` 사용
- Node.js: 현재 테스트 미설정 (향후 vitest 도입 예정)

## 배포
- 로컬 실행 기반 (서버 배포 없음)
- Windows Task Scheduler로 자동 실행
- PowerShell 스크립트로 래핑
```
