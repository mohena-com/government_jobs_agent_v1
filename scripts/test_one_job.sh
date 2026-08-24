#!/usr/bin/env bash
set -u

JOB_COUNT=3

PYTHON_BIN="${PYTHON_BIN:-python3.1}"
OLLAMA_HOST="${OLLAMA_HOST:-http://webmaster-ai.local:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"

echo "=============================================="
echo " ONE JOB END-TO-END TEST"
echo "=============================================="

echo
echo "[1] Generate one job DOCX"

"$PYTHON_BIN" main.py --max-jobs ${JOB_COUNT} || exit 1

DOCX="$(ls -t reports/jobs/*.docx | grep -v 'Summary.docx' | head -1)"

if [ -z "$DOCX" ]; then
    echo "ERROR: No Job Detail DOCX found."
    exit 1
fi

echo "DOCX: $DOCX"

echo
echo "[2] Generate Qwen 6-slide plan"

rm -rf social/qwen_test social/rendered_test

"$PYTHON_BIN" main.py \
    --docx "$DOCX" \
    --qwen \
    --verify-official \
    --job-index ${JOB_COUNT} \
    --ollama-host "$OLLAMA_HOST" \
    --ollama-model "$OLLAMA_MODEL" \
    --slide-count 6 \
    --qwen-output social/qwen_test

if [ ! -f social/qwen_test/qwen_instagram_plans.json ]; then
    echo "ERROR: Qwen JSON was not created."
    exit 1
fi

echo
echo "[3] Render six Instagram slides"

"$PYTHON_BIN" main.py \
    --render-qwen social/qwen_test/qwen_instagram_plans.json \
    --render-output social/rendered_test \
    --job-index ${JOB_COUNT}

PNG_COUNT="$(find social/rendered_test -type f -name '*.png' | wc -l | tr -d ' ')"

echo
echo "=============================================="
echo " TEST COMPLETE"
echo "=============================================="
echo "DOCX : $DOCX"
echo "JSON : social/qwen_test/qwen_instagram_plans.json"
echo "PNGs : $PNG_COUNT"
echo "=============================================="

if [ "$PNG_COUNT" -lt 6 ]; then
    echo "WARNING: fewer than 6 slides were rendered."
    exit 1
fi