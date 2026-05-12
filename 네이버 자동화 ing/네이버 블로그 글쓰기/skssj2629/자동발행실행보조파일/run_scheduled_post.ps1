param(
    [Parameter(Mandatory = $true)]
    [string]$PostType
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$scriptPath = Join-Path $projectRoot "skssj2629.py"

$env:NAVER_CONNECT_ID = "skssj2629"
$env:NAVER_CONNECT_CSV_PATH = Join-Path $projectRoot "skssj2629_naver.csv"

Set-Location -LiteralPath $projectRoot
& $pythonExe $scriptPath --post-type $PostType --scheduled
exit $LASTEXITCODE
