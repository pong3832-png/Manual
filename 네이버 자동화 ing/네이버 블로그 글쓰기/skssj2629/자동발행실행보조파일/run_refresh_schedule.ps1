param(
    [Parameter(Mandatory = $true)]
    [string]$RefreshTime
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot
$pythonExe = (Get-Command python -ErrorAction Stop).Source
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$scriptPath = Get-ChildItem -LiteralPath $projectRoot -File -Filter "skssj2629(*).py" |
    Select-Object -First 1 -ExpandProperty FullName
$stateDir = Get-ChildItem -LiteralPath $projectRoot -Directory |
    Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName "daily_schedule.json")) -or
        (Test-Path -LiteralPath (Join-Path $_.FullName "logs"))
    } |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $scriptPath) {
    throw "Scheduler script was not found under $projectRoot"
}

if (-not $stateDir) {
    throw "State directory was not found under $projectRoot"
}

$logDir = Join-Path $stateDir "logs"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDir "${timestamp}_RefreshDaily.log"

New-Item -ItemType Directory -Force -Path $logDir -ErrorAction Stop | Out-Null

function Write-RefreshLog {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Message
    )

    Add-Content -LiteralPath $logPath -Value $Message -Encoding UTF8 -ErrorAction Stop
}

Set-Location -LiteralPath $projectRoot
Write-RefreshLog "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] RefreshDaily start"
Write-RefreshLog "project_root=$projectRoot"
Write-RefreshLog "python=$pythonExe"
Write-RefreshLog "script=$scriptPath"
Write-RefreshLog "refresh_time=$RefreshTime"

try {
    & $pythonExe $scriptPath --target-date auto --refresh-time $RefreshTime 2>&1 | ForEach-Object {
        Write-RefreshLog ([string]$_)
    }
    $exitCode = $LASTEXITCODE
} catch {
    Write-RefreshLog "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] exception=$($_.Exception.Message)"
    exit 1
}

Write-RefreshLog "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] exit_code=$exitCode"
exit $exitCode
