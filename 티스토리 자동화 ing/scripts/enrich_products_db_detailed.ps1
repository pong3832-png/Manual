$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$env:PYTHONPATH = Join-Path $ProjectRoot "src"

Set-Location -LiteralPath $ProjectRoot
& $PythonPath -m tistory_automation.pipeline.enrich_products_db_detailed @args
