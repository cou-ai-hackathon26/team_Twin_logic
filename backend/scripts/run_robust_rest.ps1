Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUNBUFFERED = "1"
foreach ($f in "unseen", "skipcut") {
  $r = "data\eval_robust\$f"
  cmd /c ".venv\Scripts\python.exe -u -m scripts.benchmark --recordings $r\recordings.csv --annotations $r\annotations.csv --no-whisper --no-latest --systems porabondhu --name robust_$f --label ""robustness: $f (FLEURS test speakers, 100 recordings)"" > $r.log 2>&1"
}
"ALL DONE" | Out-File -Encoding ascii data\eval_100_done.txt
