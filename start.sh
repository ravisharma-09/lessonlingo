#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "============================================================"
echo "                    Starting LessonLingo"
echo "============================================================"
echo ""

if [ ! -f ".venv/bin/activate" ]; then
    echo "[ERROR] Virtual environment (.venv) not found."
    echo "Please run ./setup.sh first to complete installation."
    exit 1
fi

source .venv/bin/activate

echo "[*] Opening LessonLingo in your browser at http://127.0.0.1:7860..."
if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:7860" &
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:7860" &
fi

echo "[*] Starting LessonLingo server (warm light model, offline mode)..."
echo "Press Ctrl+C to stop LessonLingo."
echo ""

lessonlingo app --warm light --offline
