$ProjectRoot = Split-Path -Parent $PSScriptRoot
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
chcp.com 65001 > $null

$srcPath = Join-Path $ProjectRoot "src"
$venvSitePackages = Join-Path $ProjectRoot ".venv\Lib\site-packages"
$pythonPathParts = @($srcPath)
if (Test-Path $venvSitePackages) {
    $pythonPathParts += $venvSitePackages
}
$env:PYTHONPATH = ($pythonPathParts -join [System.IO.Path]::PathSeparator)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

function Test-PythonCandidate {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    try {
        & $Path -X utf8 -c "import selenium; import encodings.idna; print('ok')" *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$orangePython = "C:\Program Files\Orange\python.exe"
$fallbackPython = "C:\Users\pong3\AppData\Local\Programs\Python\Python314\python.exe"
$pythonCandidates = @($venvPython, $orangePython, $fallbackPython)
$PythonPath = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-PythonCandidate $candidate) {
        $PythonPath = $candidate
        break
    }
}

if (-not $PythonPath) {
    Write-Host "[runner] ERROR: No usable Python found. venv Python may be blocked by Windows Application Control."
    Start-Sleep -Seconds 120
    exit 1
}

Set-Location -LiteralPath $ProjectRoot
& $PythonPath -X utf8 -m tistory_automation.main @args
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host "[runner] ERROR. Exit code: $exitCode"
    Start-Sleep -Seconds 120
}
exit $exitCode
