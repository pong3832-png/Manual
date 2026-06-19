param(
  [string]$TaskPrefix = "CampPlatformCrawl",
  [ValidatePattern('^\d{2}:\d{2}$')]
  [string]$MorningTime = "08:00",
  [ValidatePattern('^\d{2}:\d{2}$')]
  [string]$AfternoonTime = "17:00",
  [switch]$TwiceDaily
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$runnerPath = Join-Path $PSScriptRoot "run-crawl.ps1"
$taskCommand = '"powershell.exe" -NoProfile -ExecutionPolicy Bypass -File \"' + $runnerPath + '\"'

$taskConfigs = @(
  @{
    Name = "${TaskPrefix}_Morning"
    Time = $MorningTime
  }
)

if ($TwiceDaily) {
  $taskConfigs += @{
    Name = "${TaskPrefix}_Afternoon"
    Time = $AfternoonTime
  }
}

foreach ($task in $taskConfigs) {
  $createArgs = @(
    "/Create",
    "/F",
    "/SC", "DAILY",
    "/TN", $task.Name,
    "/TR", $taskCommand,
    "/ST", $task.Time,
    "/RL", "LIMITED"
  )

  & schtasks.exe @createArgs | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "failed to register scheduled task $($task.Name) with exit code $LASTEXITCODE"
  }
  Write-Host "registered scheduled task: $($task.Name) at $($task.Time)"
}

Write-Host "project root: $projectRoot"
Write-Host "runner: $runnerPath"
