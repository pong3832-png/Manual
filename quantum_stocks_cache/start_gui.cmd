@echo off
setlocal

cd /d "%~dp0"
set "QSC_GUI_URL=http://127.0.0.1:8766"

if not exist ".\.venv\Scripts\python.exe" (
  echo Python virtual environment not found: .\.venv\Scripts\python.exe
  echo Create or restore the local environment before starting the GUI.
  pause
  exit /b 1
)

if not exist ".\web\dist\index.html" (
  if not exist ".\web\node_modules" (
    echo Web dependencies not found: .\web\node_modules
    echo Run npm.cmd install in the web folder first.
    pause
    exit /b 1
  )
  pushd ".\web"
  call npm.cmd run build
  if errorlevel 1 (
    popd
    pause
    exit /b 1
  )
  popd
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$url=$env:QSC_GUI_URL; " ^
  "$open=$false; " ^
  "try { $client=[Net.Sockets.TcpClient]::new(); $task=$client.ConnectAsync('127.0.0.1',8766); $open=$task.Wait(400); $client.Close() } catch { $open=$false }; " ^
  "if (-not $open) { Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k','cd /d ""%CD%"" && "".\\.venv\\Scripts\\python.exe"" "".\\scripts\\run_web_app.py""') -WorkingDirectory (Get-Location).Path; Start-Sleep -Seconds 5 }; " ^
  "Start-Process $url"

endlocal
