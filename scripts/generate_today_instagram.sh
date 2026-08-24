#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
PYTHON_BIN="${PYTHON_BIN:-python3.1}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"
TODAY="${TODAY:-$(date '+%Y-%m-%d')}"

echo "============================================================"
echo "Government Jobs → Instagram | ${TODAY}"
echo "Rule: LAST DATE > TODAY | duplicate_filtering=false"
echo "============================================================"

echo "[1/3] Crawling future-deadline listings + generating Job Detail DOCX..."
"$PYTHON_BIN" main.py --max-jobs 1000 || exit $?

echo "[2/3] Future-date selector (no history / duplicate filtering)..."
# Kept as the canonical selector API for compatibility. The crawler has already
# applied the same strict future-date rule; this selector is used only for the
# machine-readable audit list and does not gate the DOCX hand-off.
if [ -f social/today_jobs.json ]; then
  "$PYTHON_BIN" scripts/select_future_jobs.py \
    --input social/today_jobs.json \
    --output social/today_jobs_selected.json || true
fi

echo "[3/3] Use scripts/generate_all_today.sh for the complete DOCX → Qwen → render batch."
echo "============================================================"
