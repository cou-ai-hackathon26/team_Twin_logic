# Calibrate on FLEURS tuning speakers, then benchmark on FLEURS test speakers.
# Watch progress in another terminal:  .venv\Scripts\python -m scripts.progress
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$d = "data\eval_fleurs"
$a = "--recordings $d\recordings.csv --annotations $d\annotations.csv"
Remove-Item "$d\calibrate.log", "$d\benchmark.log" -ErrorAction SilentlyContinue
# cmd redirection keeps the logs UTF-8 (PowerShell 5.1 would write UTF-16)
cmd /c ".venv\Scripts\python.exe -u -m scripts.calibrate $a > $d\calibrate.log 2>&1"
if ($LASTEXITCODE -ne 0) { exit 1 }
cmd /c ".venv\Scripts\python.exe -u -m scripts.benchmark $a --label ""FLEURS bn_in: real adult speech, simulated reading errors"" > $d\benchmark.log 2>&1"
