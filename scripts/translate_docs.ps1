# Translate this project's own README and CONTRIBUTING into Hindi and Kannada (run on the GPU laptop).
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\translate_docs.ps1
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
& .\.venv\Scripts\Activate.ps1

foreach ($file in "README.md", "CONTRIBUTING.md") {
    lessonlingo translate $file --to hin_Deva kan_Knda --mode light --offline --keep LessonLingo IndicTrans2 Whisper ffmpeg Gradio --out docs\i18n
}
Write-Host "Done. Ask a Hindi and a Kannada speaker to check docs\i18n before committing."
