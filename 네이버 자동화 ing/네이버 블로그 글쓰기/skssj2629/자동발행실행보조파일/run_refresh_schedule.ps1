param(
    [Parameter(Mandatory = $true)]
    [string]$RefreshTime
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$scriptPath = Join-Path $projectRoot "skssj2629(스케줄러).py"

Set-Location -LiteralPath $projectRoot
& $pythonExe $scriptPath --target-date auto --refresh-time $RefreshTime
exit $LASTEXITCODE
