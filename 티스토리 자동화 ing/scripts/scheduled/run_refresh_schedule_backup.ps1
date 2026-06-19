param(
    [string]$RefreshTime = "00:05"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SchedulerPy = Join-Path $ProjectRoot "src\tistory_automation\scheduler.py"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

$LogDir = Join-Path $ProjectRoot "runtime\logs\scheduled"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogDir "${Timestamp}_refresh.log"

function Write-Log {
    param([string]$Message)
    $Line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $Line
    Add-Content -Path $LogPath -Value $Line -Encoding UTF8
}

Write-Log "[refresh] Python=$Python"
Write-Log "[refresh] SchedulerPy=$SchedulerPy"
Write-Log "[refresh] RefreshTime=$RefreshTime"

if (!(Test-Path $Python)) {
    Write-Log "[ERROR] Python 실행 파일을 찾지 못했습니다: $Python"
    exit 1
}

if (!(Test-Path $SchedulerPy)) {
    Write-Log "[ERROR] scheduler.py를 찾지 못했습니다: $SchedulerPy"
    exit 1
}

Set-Location $ProjectRoot

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Write-Log "[refresh] scheduler.py 실행 시작"

& $Python $SchedulerPy --target-date auto --refresh-time $RefreshTime 2>&1 | Tee-Object -FilePath $LogPath -Append

$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0) {
    Write-Log "[refresh] 스케줄 재등록 완료"
} else {
    Write-Log "[ERROR] 스케줄 재등록 실패 | ExitCode=$ExitCode"
}

exit $ExitCode
