#!/usr/bin/env bash
set -e

# Change to the script's directory
cd "$(dirname "$0")"

echo "============================================================"
echo "               LessonLingo - Setup Wizard"
echo "    Free lessons in your language. Offline once set up."
echo "============================================================"
echo ""

# 1. Detect Python 3.11
echo "[1/6] Checking for Python 3.11..."
PYTHON_BIN=""

if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
elif command -v python3 >/dev/null 2>&1; then
    PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
    if [[ "$PY_VER" == 3.11* ]]; then
        PYTHON_BIN="python3"
    fi
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[!] Python 3.11 was not found on your system."
    OS="$(uname -s)"
    if [ "$OS" = "Darwin" ]; then
        if command -v brew >/dev/null 2>&1; then
            echo "[*] Homebrew detected. Installing Python 3.11..."
            brew install python@3.11
            PYTHON_BIN="$(brew --prefix)/opt/python@3.11/bin/python3.11"
        else
            echo "[ERROR] Please install Python 3.11 via Homebrew (brew install python@3.11) or python.org."
            exit 1
        fi
    elif [ "$OS" = "Linux" ]; then
        echo "[ERROR] Please install Python 3.11 (e.g., sudo apt install python3.11 python3.11-venv)."
        exit 1
    else
        echo "[ERROR] Please install Python 3.11."
        exit 1
    fi
fi

echo "[*] Using Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

# 2. Virtual Environment
echo ""
echo "[2/6] Preparing Python virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    echo "[*] Creating .venv..."
    "$PYTHON_BIN" -m venv .venv
else
    echo "[*] Existing virtual environment found."
fi

source .venv/bin/activate
echo "[*] Upgrading pip..."
python -m pip install --upgrade pip

# 3. Configure PyTorch
echo ""
echo "[3/6] Configuring PyTorch..."
OS="$(uname -s)"
if [ "$OS" = "Linux" ] && command -v nvidia-smi >/dev/null 2>&1; then
    echo "[*] NVIDIA GPU detected on Linux. Installing PyTorch with CUDA 12.4..."
    python -m pip install torch --index-url https://download.pytorch.org/whl/cu124
else
    echo "[*] Installing PyTorch..."
    python -m pip install torch
fi

# 4. Install Dependencies & LessonLingo
echo ""
echo "[4/6] Installing dependencies and LessonLingo..."
python -m pip install -r requirements.txt

# 5. Check FFmpeg
echo ""
echo "[5/6] Checking for FFmpeg..."
if command -v ffmpeg >/dev/null 2>&1; then
    echo "[*] FFmpeg is installed."
else
    echo "[!] FFmpeg not detected."
    if [ "$OS" = "Darwin" ]; then
        echo "    Install with: brew install ffmpeg"
    elif [ "$OS" = "Linux" ]; then
        echo "    Install with: sudo apt install ffmpeg"
    fi
fi

# 6. Hugging Face Login and Model Download
echo ""
echo "[6/6] Model Download and Hugging Face Setup"
echo "============================================================"
echo "IndicTrans2 models require free access approval on Hugging Face:"
echo "  1. https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M"
echo "  2. https://huggingface.co/ai4bharat/indictrans2-en-indic-1B"
echo ""
echo "Please ensure you have accepted both agreements in your browser."
echo "============================================================"
echo ""

read -p "Do you want to log in and download models now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "[*] Starting Hugging Face login & download..."
    python -m lessonlingo.cli setup
    echo "[*] Verifying offline cache..."
    python -m lessonlingo.cli verify
else
    echo "[*] Skipped. You can download models anytime later using: lessonlingo setup"
fi

echo ""
echo "============================================================"
echo "                    SETUP COMPLETE!"
echo "============================================================"
echo "Launch LessonLingo anytime using: ./start.sh"
echo "============================================================"
echo ""
