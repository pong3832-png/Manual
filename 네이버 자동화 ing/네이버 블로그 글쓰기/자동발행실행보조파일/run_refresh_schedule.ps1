param(
    [Parameter(Mandatory = $true)]
    [string]$RefreshTime
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot

function Resolve-PythonExe {
    $explicitPython = "C:\Users\itwill\AppData\Local\Programs\Python\Python313\python.exe"
    if (Test-Path -LiteralPath $explicitPython) {
        return $explicitPython
    }

    $pathPython = Get-Command python -ErrorAction SilentlyContinue
    if ($pathPython) {
        return $pathPython.Source
    }

    throw "Python executable not found. Install Python or update run_refresh_schedule.ps1."
}

$pythonExe = Resolve-PythonExe
$scriptPath = Join-Path $scriptRoot "scheduler_runner.py"

Set-Location -LiteralPath $projectRoot
& $pythonExe $scriptPath --target-date auto --refresh-time $RefreshTime
exit $LASTEXITCODE
