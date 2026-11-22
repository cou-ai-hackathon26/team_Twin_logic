# Run PoraBondhu locally:  .\start.ps1          (app at http://localhost:8000)
#                          .\start.ps1 -Dev     (hot-reload frontend at http://localhost:5173)
param([switch]$Dev)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONIOENCODING = "utf-8"

if ($Dev) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
    Set-Location "$root\backend"
    .\.venv\Scripts\python -m uvicorn app.main:app --port 8000 --reload --reload-dir app
} else {
    if (-not (Test-Path "$root\frontend\dist\index.html")) {
        Set-Location "$root\frontend"; npm run build
    }
    Set-Location "$root\backend"
    Start-Process "http://localhost:8000"
    .\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
