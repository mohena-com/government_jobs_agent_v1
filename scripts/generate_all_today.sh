#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

PYTHON_BIN="${PYTHON_BIN:-python3.1}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"
TODAY="${TODAY:-$(date '+%Y-%m-%d')}"
REPORTS_DIR="${1:-${REPORTS_DIR:-../reports}}"

DOCX_DIR="${REPORTS_DIR}/jobs"
QWEN_DIR="social/qwen_today_${TODAY}"
RENDER_DIR="social/rendered_today_${TODAY}"
REPORT="social/daily_generation_${TODAY}.json"

mkdir -p "$QWEN_DIR" "$RENDER_DIR"

echo "============================================================"
echo " Government Jobs → Instagram | V1.9.27"
echo " Date: ${TODAY}"
echo " Rule: LAST DATE > TODAY"
echo " Duplicate filtering: OFF"
echo "============================================================"

echo
echo "[1/1] Crawling jobs and generating Job Detail DOCX files..."
echo

"$PYTHON_BIN" main.py --max-jobs 1000 --reports-dir "$REPORTS_DIR" 
RC=$?
if [ "$RC" -ne 0 ]; then
    echo "ERROR: crawler failed."
    exit "$RC"
fi



