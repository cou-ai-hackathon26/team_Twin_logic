# One-time setup on Windows (PowerShell):  .\setup.ps1
# Needs Python 3.10+, Node 20+ and ffmpeg (optional, for mp3/webm uploads).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "== Backend: Python virtual environment" -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) { python -m venv .venv }
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\pip install -r requirements.txt
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

Write-Host "== Speech model: download and export to ONNX int8 (fast CPU inference)" -ForegroundColor Cyan
if (-not (Test-Path "data\onnx\model.int8.onnx")) { .\.venv\Scripts\python -m scripts.export_onnx }

Write-Host "== Tests" -ForegroundColor Cyan
.\.venv\Scripts\python -m pytest -q

Write-Host "== Frontend: install and build" -ForegroundColor Cyan
Set-Location "$root\frontend"
npm install
npm run build

Set-Location $root
Write-Host "Done. Start with .\start.ps1 and open http://localhost:8000" -ForegroundColor Green
