# LessonLingo Automated Setup Script for PowerShell
$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "               LessonLingo - Setup Wizard" -ForegroundColor Cyan
Write-Host "    Free lessons in your language. Offline once set up." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location -Path $PSScriptRoot

# 1. Detect Python 3.11
Write-Host "[1/6] Checking for Python 3.11..." -ForegroundColor Yellow
$PythonCmd = $null

try {
    $ver = & py -3.11 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $PythonCmd = "py -3.11"
    }
} catch {}

if (-not $PythonCmd) {
    try {
        $ver = & python --version 2>&1
        if ($ver -match "3\.11") {
            $PythonCmd = "python"
        }
    } catch {}
}

if (-not $PythonCmd) {
    Write-Warning "Python 3.11 was not detected."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "[*] Attempting to install Python 3.11 via winget..." -ForegroundColor Green
        winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        $PythonCmd = "py -3.11"
    } else {
        Write-Error "Please install Python 3.11 manually from https://www.python.org/downloads/release/python-3119/ and re-run this script."
        exit 1
    }
}

Write-Host "[*] Using Python: $PythonCmd" -ForegroundColor Green

# 2. Virtual Environment
Write-Host "`n[2/6] Preparing Python virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path -Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "[*] Creating .venv..." -ForegroundColor Green
    if ($PythonCmd -eq "py -3.11") {
        py -3.11 -m venv .venv
    } else {
        python -m venv .venv
    }
} else {
    Write-Host "[*] Existing virtual environment found." -ForegroundColor Green
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& .\.venv\Scripts\Activate.ps1

Write-Host "[*] Upgrading pip..." -ForegroundColor Green
python -m pip install --upgrade pip

# 3. PyTorch Detection
Write-Host "`n[3/6] Configuring PyTorch..." -ForegroundColor Yellow
$hasNvidia = $false
try {
    $null = & nvidia-smi 2>&1
    if ($LASTEXITCODE -eq 0) { $hasNvidia = $true }
} catch {}

if ($hasNvidia) {
    Write-Host "[*] NVIDIA GPU detected. Installing PyTorch with CUDA 12.4 support..." -ForegroundColor Green
    python -m pip install torch --index-url https://download.pytorch.org/whl/cu124
} else {
    Write-Host "[*] No NVIDIA GPU detected. Installing standard PyTorch for CPU..." -ForegroundColor Green
    python -m pip install torch
}

# 4. Install Dependencies
Write-Host "`n[4/6] Installing dependencies and LessonLingo..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

# 5. Check FFmpeg
Write-Host "`n[5/6] Checking for FFmpeg..." -ForegroundColor Yellow
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "[*] FFmpeg is installed and available." -ForegroundColor Green
} else {
    Write-Warning "FFmpeg not found in PATH."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "[*] Installing FFmpeg via winget..." -ForegroundColor Green
        winget install ffmpeg --accept-package-agreements --accept-source-agreements
    } else {
        Write-Warning "Please install FFmpeg manually from https://ffmpeg.org/ or run 'winget install ffmpeg'."
    }
}

# 6. Hugging Face Login and Download
Write-Host "`n[6/6] Model Download and Hugging Face Setup" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "IndicTrans2 models require free access approval on Hugging Face:"
Write-Host "  1. https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M"
Write-Host "  2. https://huggingface.co/ai4bharat/indictrans2-en-indic-1B"
Write-Host "============================================================" -ForegroundColor Cyan

$prompt = Read-Host "`nDo you want to log in and download models now? (Y/N)"
if ($prompt -match "^[Yy]") {
    Write-Host "[*] Starting model setup..." -ForegroundColor Green
    python -m lessonlingo.cli setup
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[*] Verifying offline cache..." -ForegroundColor Green
        python -m lessonlingo.cli verify
    }
} else {
    Write-Host "[*] Skipped. You can run 'lessonlingo setup' anytime later." -ForegroundColor Yellow
}

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "                    SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "You can start LessonLingo by running: start.bat or lessonlingo app --offline" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Green
