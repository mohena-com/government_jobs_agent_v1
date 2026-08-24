#!/usr/bin/env bash
set -u

JOB_COUNT="${JOB_COUNT:-3}"

PYTHON_BIN="${PYTHON_BIN:-python3.1}"
OLLAMA_HOST="${OLLAMA_HOST:-http://webmaster-ai.local:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"

echo "=============================================="
echo " MULTI-JOB END-TO-END TEST"
echo " Jobs: ${JOB_COUNT}"
echo "=============================================="

echo
echo "[1] Generate Job Detail DOCX files"

"$PYTHON_BIN" main.py --max-jobs "$JOB_COUNT" || exit 1

DOCX_LIST="$(ls -t reports/jobs/*.docx 2>/dev/null | grep -v 'Summary.docx' | head -n "$JOB_COUNT")"

if [ -z "$DOCX_LIST" ]; then
    echo "ERROR: No Job Detail DOCX files found."
    exit 1
fi

ACTUAL_COUNT="$(printf '%s\n' "$DOCX_LIST" | sed '/^$/d' | wc -l | tr -d ' ')"
echo "Job Detail DOCX files found: ${ACTUAL_COUNT}"

if [ "$ACTUAL_COUNT" -ne "$JOB_COUNT" ]; then
    echo "ERROR: Expected ${JOB_COUNT} DOCX files but found ${ACTUAL_COUNT}."
    exit 1
fi

echo
echo "[2] Generate Qwen plans and render each job"

rm -rf social/qwen_test social/rendered_test
mkdir -p social/qwen_test social/rendered_test

INDEX=1
TOTAL_PNG=0
FAILED=0

while IFS= read -r DOCX; do
    [ -z "$DOCX" ] && continue

    JOB_DIR="social/qwen_test/job_${INDEX}"
    RENDER_DIR="social/rendered_test/job_${INDEX}"

    mkdir -p "$JOB_DIR" "$RENDER_DIR"

    echo
    echo "--------------------------------------------------"
    echo "JOB ${INDEX}/${JOB_COUNT}"
    echo "DOCX: ${DOCX}"
    echo "--------------------------------------------------"

    if ! "$PYTHON_BIN" main.py \
        --docx "$DOCX" \
        --qwen \
        --verify-official \
        --job-index 1 \
        --ollama-host "$OLLAMA_HOST" \
        --ollama-model "$OLLAMA_MODEL" \
        --slide-count 6 \
        --qwen-output "$JOB_DIR"; then
        echo "ERROR: Qwen generation failed for job ${INDEX}."
        FAILED=$((FAILED + 1))
        INDEX=$((INDEX + 1))
        continue
    fi

    PLAN="${JOB_DIR}/qwen_instagram_plans.json"

    if [ ! -f "$PLAN" ]; then
        echo "ERROR: Qwen JSON was not created for job ${INDEX}."
        FAILED=$((FAILED + 1))
        INDEX=$((INDEX + 1))
        continue
    fi

    if ! "$PYTHON_BIN" main.py \
        --render-qwen "$PLAN" \
        --render-output "$RENDER_DIR" \
        --job-index 1; then
        echo "ERROR: Rendering failed for job ${INDEX}."
        FAILED=$((FAILED + 1))
        INDEX=$((INDEX + 1))
        continue
    fi

    COUNT="$(find "$RENDER_DIR" -type f -name '*.png' | wc -l | tr -d ' ')"
    echo "Rendered slides for job ${INDEX}: ${COUNT}"

    TOTAL_PNG=$((TOTAL_PNG + COUNT))
    INDEX=$((INDEX + 1))
done <<EOF
$DOCX_LIST
EOF

chmod -R 777 social/qwen_test social/rendered_test 2>/dev/null || true

echo
echo "=============================================="
echo " TEST COMPLETE"
echo "=============================================="
echo "Jobs requested : ${JOB_COUNT}"
echo "Jobs failed    : ${FAILED}"
echo "PNG slides      : ${TOTAL_PNG}"
echo "=============================================="

if [ "$FAILED" -gt 0 ]; then
    echo "WARNING: ${FAILED} job(s) failed."
    exit 1
fi

EXPECTED_PNG=$((JOB_COUNT * 6))

if [ "$TOTAL_PNG" -lt "$EXPECTED_PNG" ]; then
    echo "WARNING: Expected at least ${EXPECTED_PNG} PNGs but found ${TOTAL_PNG}."
    exit 1
fi

echo "SUCCESS: ${JOB_COUNT} jobs completed with ${TOTAL_PNG} slides."
