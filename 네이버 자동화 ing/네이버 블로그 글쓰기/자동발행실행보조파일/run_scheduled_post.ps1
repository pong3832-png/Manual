param(
    [Parameter(Mandatory = $true)]
    [string]$PostType
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

    throw "Python executable not found. Install Python or update run_scheduled_post.ps1."
}

$pythonExe = Resolve-PythonExe
$scriptPath = Join-Path $scriptRoot "gemini_web_runner.py"
$env:COUPANG_CSV_PATH = Join-Path $projectRoot "skssj2627_db.csv"

Set-Location -LiteralPath $projectRoot
& $pythonExe $scriptPath --post-type $PostType --scheduled
exit $LASTEXITCODE
