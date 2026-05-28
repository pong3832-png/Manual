@echo off
set "PROJECT_ROOT=%~dp0.."

pushd "%PROJECT_ROOT%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_ROOT%\scripts\run_chatgpt_web.ps1" %*
popd
pause
