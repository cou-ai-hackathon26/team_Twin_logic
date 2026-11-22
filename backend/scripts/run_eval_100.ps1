# Faster evaluation: wide calibration on the tuning speakers, then 100 held-out test recordings
# (three systems), then the robustness families (PoraBondhu only). Watch: python -m scripts.progress
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$d = "data\eval_fleurs"
$a = "--recordings $d\recordings.csv --annotations $d\annotations.csv"
cmd /c ".venv\Scripts\python.exe -u -m scripts.calibrate_wide $a --save > $d\calibrate_wide.log 2>&1"
Remove-Item "$d\benchmark.log" -ErrorAction SilentlyContinue
cmd /c ".venv\Scripts\python.exe -u -m scripts.benchmark $a --limit 100 --name fleurs_test100 --label ""FLEURS bn_in test speakers, first 100 recordings: real adult speech, simulated reading errors"" > $d\benchmark.log 2>&1"
cmd /c ".venv\Scripts\python.exe -u -m scripts.make_robustness_sets --n 100 > data\eval_robust_build.log 2>&1"
foreach ($f in "original", "childlike", "unseen", "skipcut") {
  $r = "data\eval_robust\$f"
  cmd /c ".venv\Scripts\python.exe -u -m scripts.benchmark --recordings $r\recordings.csv --annotations $r\annotations.csv --no-whisper --no-latest --systems porabondhu --name robust_$f --label ""robustness: $f (FLEURS test speakers, 100 recordings)"" > $r.log 2>&1"
}
"ALL DONE" | Out-File -Encoding ascii data\eval_100_done.txt
