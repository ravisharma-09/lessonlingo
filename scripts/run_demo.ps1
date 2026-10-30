# Start LessonLingo for the stage demo: offline, light model preloaded, browser opened.
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\run_demo.ps1 [-Mode quality]
param([ValidateSet("light", "quality")][string]$Mode = "light")

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
& .\.venv\Scripts\Activate.ps1

Write-Host "Checking that models are already on this computer..."
lessonlingo verify
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run 'lessonlingo setup' once while online, then try again."
    exit 1
}

Start-Process "http://127.0.0.1:7860"
lessonlingo app --offline --warm $Mode
