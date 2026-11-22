# Public live demo from this laptop: a separate PoraBondhu instance on :8100
# (its own database in backend\data_public, so local test data is never exposed)
# published through ngrok's free static domain over HTTPS.
#
#   .\deploy\run-public.ps1 -Domain your-name.ngrok-free.app
#   .\deploy\run-public.ps1 -Stop
#
# Both processes run hidden and restart automatically if they stop.
# Logs: backend\data_public\public-*.log
param([string]$Domain = $env:PB_PUBLIC_DOMAIN, [int]$Port = 8100, [switch]$Stop)

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backend = "$root\backend"
$data = "$backend\data_public"
$marker = "PB_PUBLIC_DEMO"

if ($Stop) {
    Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
        Where-Object { $_.CommandLine -like "*$marker*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -Confirm:$false }
    Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -Confirm:$false }
    Write-Host "Public demo stopped."
    return
}
if (-not $Domain) { throw "Pass -Domain <your static ngrok domain> (dashboard.ngrok.com -> Domains)." }

# The app needs the speech model in data_public\onnx (hard links to data\onnx, no extra disk).
New-Item -ItemType Directory -Force "$data\onnx" | Out-Null
Get-ChildItem "$backend\data\onnx" -File | Where-Object { $_.Name -ne "model.onnx" } | ForEach-Object {
    $t = "$data\onnx\$($_.Name)"
    if (-not (Test-Path $t)) { New-Item -ItemType HardLink -Path $t -Target $_.FullName | Out-Null }
}
if (-not (Test-Path "$root\frontend\dist\index.html")) { Push-Location "$root\frontend"; npm run build; Pop-Location }

$server = "`$env:$marker='1'; `$env:PYTHONIOENCODING='utf-8'; `$env:PB_DATA_DIR='$data'; " +
          "`$env:PB_CTC_BACKEND='onnx-int8'; `$env:PB_PRELOAD_MODELS='true'; `$env:PB_DATABASE_URL=''; " +
          "Set-Location '$backend'; while (`$true) { .\.venv\Scripts\python -m uvicorn app.main:app " +
          "--host 127.0.0.1 --port $Port --proxy-headers --forwarded-allow-ips 127.0.0.1 *>> '$data\public-backend.log'; Start-Sleep 3 }"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $server

$tunnel = "`$env:$marker='1'; while (`$true) { ngrok http 127.0.0.1:$Port --url $Domain --log stdout *>> '$data\public-ngrok.log'; Start-Sleep 5 }"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $tunnel

Write-Host "Public demo starting: https://$Domain (local http://127.0.0.1:$Port)"
