# Python 실행 가이드

프로젝트 루트에서 전용 가상환경 Python과 `src` 패키지 경로를 함께 사용한다.

## 권장 실행

```powershell
cd "C:\Users\pong3\WORKING_HAPPY\티스토리 자동화 ing"
.\scripts\run_chatgpt_web.ps1
```

## 배치 실행

```text
scripts\run_chatgpt_web.bat
```

## 직접 실행

```powershell
cd "C:\Users\pong3\WORKING_HAPPY\티스토리 자동화 ing"
$env:PYTHONPATH = ".\src"
& '.\.venv\Scripts\python.exe' -m tistory_automation.main
```
