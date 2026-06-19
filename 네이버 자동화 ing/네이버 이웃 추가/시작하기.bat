@echo off
chcp 65001 > nul
echo ==============================================
echo  Naver Neighbor Auto-Bot - Premium Edition
echo ==============================================
echo.
echo [시스템] 필요한 필수 구성요소를 점검합니다...
pip install customtkinter > nul 2>&1
echo [시스템] 준비 완료! 프리미엄 프로그램을 실행합니다.
echo.
python Premium_GUI.py
pause
