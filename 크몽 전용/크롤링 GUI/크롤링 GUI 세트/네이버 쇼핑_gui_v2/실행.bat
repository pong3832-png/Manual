@echo off
chcp 65001 >nul
title 네이버 쇼핑 크롤러 실행

echo ============================================
echo  네이버 쇼핑 자동화 크롤러 GUI  v1.0
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
python naver_shopping_gui.py

pause