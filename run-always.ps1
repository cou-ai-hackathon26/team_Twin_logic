# Keeps PoraBondhu backend (:8000) and frontend (:5173) running in hidden windows.
# Each server restarts automatically if it stops. Logs: backend\data\always-*.log
# Started at Windows login by "PoraBondhu.vbs" in the Startup folder.
# Stop everything:  .\stop-always.ps1
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logs = "$root\backend\data"

function Test-Port([int]$port) {
    try { $c = New-Object Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $port); $c.Close(); return $true }
    catch { return $false }
}

if (-not (Test-Port 8000)) {
    $cmd = "`$env:PYTHONIOENCODING='utf-8'; Set-Location '$root\backend'; " +
           "while (`$true) { .\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app *>> '$logs\always-backend.log'; Start-Sleep 3 }"
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $cmd
}

if (-not (Test-Port 5173)) {
    $cmd = "Set-Location '$root\frontend'; " +
           "while (`$true) { npm run dev *>> '$logs\always-frontend.log'; Start-Sleep 3 }"
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $cmd
}
