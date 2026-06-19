param(
  [string]$LogDir = "logs",
  [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$resolvedLogDir = Join-Path $projectRoot $LogDir
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logPath = Join-Path $resolvedLogDir "crawl-$timestamp.log"
$lockName = "Global\CampPlatformCrawl"
$mutex = $null
$hasLock = $false

New-Item -ItemType Directory -Force -Path $resolvedLogDir | Out-Null

function Test-ExistingCrawlerProcess {
  try {
    $crawlerProcesses = Get-CimInstance Win32_Process -Filter "name='node.exe'" -ErrorAction Stop |
      Where-Object {
        $_.CommandLine -match "scripts[\\/]+crawler[\\/]+crawl\.cjs"
      }

    return @($crawlerProcesses).Count -gt 0
  }
  catch {
    Write-Warning "Could not inspect existing crawler processes: $($_.Exception.Message)"
    return $false
  }
}

try {
  $mutex = [System.Threading.Mutex]::new($false, $lockName)
  $hasLock = $mutex.WaitOne(0)
}
catch [System.Threading.AbandonedMutexException] {
  $hasLock = $true
}

if (-not $hasLock -or (Test-ExistingCrawlerProcess)) {
  $message = "[$(Get-Date -Format s)] another crawl is already running. skipped this run."
  $message | Set-Content -LiteralPath $logPath -Encoding UTF8
  Write-Warning $message
  if ($hasLock -and $mutex) {
    $mutex.ReleaseMutex()
  }
  if ($mutex) {
    $mutex.Dispose()
  }
  exit 0
}

Push-Location $projectRoot

try {
  if (-not (Test-Path ".env")) {
    Write-Warning ".env file not found. The crawler may run without required secrets."
  }

  if (-not $SkipPreflight) {
    $preflightPath = Join-Path $PSScriptRoot "test-production-readiness.ps1"
    if (Test-Path -LiteralPath $preflightPath) {
      & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $preflightPath -RequireSupabase -RequireKakao
      $preflightExitCode = if ($LASTEXITCODE -ne $null) { $LASTEXITCODE } else { 0 }
      if ($preflightExitCode -ne 0) {
        throw "production readiness preflight failed with exit code $preflightExitCode"
      }
    }
  }

  $npmCmd = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
  if (-not $npmCmd) {
    throw "npm.cmd was not found in PATH."
  }

  Write-Host "[$(Get-Date -Format s)] crawl started"
  Write-Host "log file: $logPath"

  & $npmCmd.Source "run" "crawl" 2>&1 | Tee-Object -FilePath $logPath
  $exitCode = if ($LASTEXITCODE -ne $null) { $LASTEXITCODE } else { 0 }

  if ($exitCode -ne 0) {
    throw "crawl failed with exit code $exitCode"
  }

  Write-Host "[$(Get-Date -Format s)] crawl finished"
}
finally {
  Pop-Location
  if ($hasLock -and $mutex) {
    $mutex.ReleaseMutex()
  }
  if ($mutex) {
    $mutex.Dispose()
  }
}
