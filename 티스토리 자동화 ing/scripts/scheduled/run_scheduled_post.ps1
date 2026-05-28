param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("daily", "coupang", "일상", "쿠팡")]
    [string]$PostType,

    [switch]$Draft
)

$ErrorActionPreference = "Stop"

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $Utf8NoBom
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$MainPy = Join-Path $ProjectRoot "src\tistory_automation\main.py"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

$LogDir = Join-Path $ProjectRoot "runtime\logs\scheduled"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

if ($PostType -eq "일상") {
    $NormalizedPostType = "daily"
} elseif ($PostType -eq "쿠팡") {
    $NormalizedPostType = "coupang"
} else {
    $NormalizedPostType = $PostType
}

$LogPath = Join-Path $LogDir "${Timestamp}_${NormalizedPostType}.log"

function Write-Log {
    param([string]$Message)
    $Line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $Line
    Add-Content -Path $LogPath -Value $Line -Encoding UTF8
}

Write-Log "[scheduler] PostType=$NormalizedPostType | Log=$LogPath"
Write-Log "[scheduler] Mode=draft"
Write-Log "[scheduler] Python=$Python"
Write-Log "[scheduler] MainPy=$MainPy"
Write-Log "[scheduler] ProjectRoot=$ProjectRoot"

if (!(Test-Path $Python)) {
    Write-Log "[ERROR] Python 실행 파일을 찾지 못했습니다: $Python"
    exit 1
}

if (!(Test-Path $MainPy)) {
    Write-Log "[ERROR] main.py를 찾지 못했습니다: $MainPy"
    exit 1
}

Set-Location $ProjectRoot

$env:PYTHONIOENCODING = "utf-8:replace"
$env:PYTHONUTF8 = "1"

Write-Log "[scheduler] main.py 실행 시작"

$MainArgs = @($MainPy, "--post-type", $NormalizedPostType, "--scheduled")
$MainArgs += "--draft"

& $Python @MainArgs 2>&1 | ForEach-Object {
    $Line = [string]$_
    Write-Host $Line
    Add-Content -Path $LogPath -Value $Line -Encoding UTF8
}

$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0) {
    Write-Log "[scheduler] main.py 실행 완료"
} else {
    Write-Log "[ERROR] main.py 실행 실패 | ExitCode=$ExitCode"
}

exit $ExitCode
