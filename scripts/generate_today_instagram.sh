#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"
TODAY="${TODAY:-$(date '+%Y-%m-%d')}"

echo "============================================================"
echo "Government Jobs → Instagram | ${TODAY}"
echo "Rule: LAST DATE > TODAY | duplicate filtering OFF"
echo "============================================================"

echo "[1/4] Crawling future-deadline listings + generating Job Detail DOCX..."
"$PYTHON_BIN" main.py --max-jobs 1000

echo "[2/4] Selecting every crawler-selected future-deadline job..."
"$PYTHON_BIN" scripts/select_today_jobs.py \
  --input social/today_jobs.json \
  --output social/today_jobs_selected.json

COUNT="$("$PYTHON_BIN" - <<'PY'
import json
p="social/today_jobs_selected.json"
d=json.load(open(p,encoding="utf-8"))
print(d.get("selected_count", len(d.get("jobs",[]))))
PY
)"

if [[ "$COUNT" == "0" ]]; then
  echo "No future-deadline government jobs found."
  exit 0
fi

OUT="social/rendered_today_${TODAY}"
QOUT="social/qwen_today_${TODAY}"
mkdir -p "$OUT" "$QOUT"

echo "[3/4] Official verification + Qwen + slide QA..."
"$PYTHON_BIN" scripts/process_selected_jobs.py \
  --input social/today_jobs_selected.json \
  --qwen-output "$QOUT" \
  --ollama-host "$OLLAMA_HOST" \
  --ollama-model "$OLLAMA_MODEL" \
  --slide-count 6 \
  --verify-official

echo "[4/4] Daily Instagram generation complete."
echo "Rendered output: $OUT"
echo "============================================================"
