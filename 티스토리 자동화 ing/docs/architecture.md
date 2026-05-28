# Architecture

이 프로젝트는 아래 원칙으로 나뉜다.

- `src/tistory_automation`: 실제 실행 코드
- `config/prompts`: 사람이 관리하는 프롬프트 설정
- `data/products`: 기준 CSV 데이터
- `runtime`: 로그, 세션, 생성 결과 같은 실행 산출물
- `scripts`: PowerShell/BAT 실행 진입점
- `docs`: 운영 문서와 AGENT 자료
