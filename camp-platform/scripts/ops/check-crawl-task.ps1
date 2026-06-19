param(
  [string]$TaskPrefix = "CampPlatformCrawl"
)

$ErrorActionPreference = "Stop"

$taskNames = @(
  "${TaskPrefix}_Morning",
  "${TaskPrefix}_Afternoon"
)

foreach ($taskName in $taskNames) {
  try {
    & schtasks.exe /Query /FO LIST /V /TN $taskName
    Write-Host ""
  }
  catch {
    Write-Warning "scheduled task not found: $taskName"
  }
}
