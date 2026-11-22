# Stops the always-on PoraBondhu servers started by run-always.ps1 (until next login).
# To stop auto-start completely, also delete PoraBondhu.vbs from:
#   shell:startup  (%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup)
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -match "uvicorn app.main:app|npm run dev" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
foreach ($port in 8000, 5173) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
Write-Host "PoraBondhu servers stopped."
