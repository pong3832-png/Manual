@echo off
chcp 65001 >nul
title 인스타그램 크롤러 실행

echo ============================================
echo  인스타그램 해시태그 크롤러 GUI  v2.0
echo ============================================
echo.

:: 라이브러리 설치 여부 확인
python -c "import selenium" 2>nul
if errorlevel 1 (
    echo [설치 중] 필요한 라이브러리를 설치합니다...
    pip install -r requirements.txt
    echo.
)

echo [시작] 프로그램을 실행합니다...
python instagram_gui.py

pause
