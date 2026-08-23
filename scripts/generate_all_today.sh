#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

PYTHON_BIN="${PYTHON_BIN:-python3.1}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"

TODAY="$(date '+%Y-%m-%d')"

DOCX_DIR="reports/jobs"
QWEN_DIR="social/qwen_today_${TODAY}"
RENDER_DIR="social/rendered_today_${TODAY}"
REPORT="social/daily_generation_${TODAY}.json"

mkdir -p "$QWEN_DIR"
mkdir -p "$RENDER_DIR"

echo "============================================================"
echo " Government Jobs → Instagram"
echo " Date: ${TODAY}"
echo " Rule: LAST DATE > TODAY"
echo " Duplicate filtering: OFF"
echo "============================================================"

# ------------------------------------------------------------
# 1. Crawl + generate Job Detail DOCX files
# ------------------------------------------------------------

echo
echo "[1/3] Crawling jobs and generating Job Detail DOCX files..."
echo

"$PYTHON_BIN" main.py --max-jobs 1000

CRAWL_RC=$?

if [ "$CRAWL_RC" -ne 0 ]; then
    echo
    echo "ERROR: crawler failed."
    exit "$CRAWL_RC"
fi

# ------------------------------------------------------------
# Find today's generated DOCX files
# macOS-compatible: NO mapfile
# ------------------------------------------------------------

echo
echo "Finding today's Job Detail DOCX files..."

JOB_COUNT=0
JOB_DOCXS=""

while IFS= read -r DOCX
do
    if [ -n "$DOCX" ]; then
        JOB_COUNT=$((JOB_COUNT + 1))
        JOB_DOCXS="${JOB_DOCXS}
${DOCX}"
    fi
done <<EOF
$(find "$DOCX_DIR" \
    -type f \
    -name "*.docx" \
    -newermt "${TODAY} 00:00:00" \
    ! -name "*Summary.docx" \
    | sort)
EOF

echo "Job Detail DOCX files found: ${JOB_COUNT}"

if [ "$JOB_COUNT" -eq 0 ]; then
    echo
    echo "ERROR: No Job Detail DOCX files found."
    exit 1
fi

# ------------------------------------------------------------
# 2. Generate Qwen JSON for every DOCX
# ------------------------------------------------------------

echo
echo "============================================================"
echo "[2/3] Generating Qwen JSON for every job"
echo "============================================================"

SUCCESS_QWEN=0
FAILED_QWEN=0

# Use a temporary list because macOS Bash has no mapfile.
QWEN_LIST="${QWEN_DIR}/_successful_plans.txt"
rm -f "$QWEN_LIST"
touch "$QWEN_LIST"

JOB_NO=0

while IFS= read -r DOCX
do
    [ -z "$DOCX" ] && continue

    JOB_NO=$((JOB_NO + 1))

    JOB_QWEN_DIR="${QWEN_DIR}/${JOB_NO}"
    mkdir -p "$JOB_QWEN_DIR"

    echo
    echo "------------------------------------------------------------"
    echo "[${JOB_NO}/${JOB_COUNT}] Qwen"
    echo "DOCX: ${DOCX}"
    echo "------------------------------------------------------------"

    "$PYTHON_BIN" main.py \
        --docx "$DOCX" \
        --qwen \
        --verify-official \
        --job-index 1 \
        --ollama-host "$OLLAMA_HOST" \
        --ollama-model "$OLLAMA_MODEL" \
        --slide-count 6 \
        --qwen-output "$JOB_QWEN_DIR"

    RC=$?

    PLAN="${JOB_QWEN_DIR}/qwen_instagram_plans.json"

    if [ "$RC" -eq 0 ] && [ -f "$PLAN" ]; then

        READY="$(
            "$PYTHON_BIN" - "$PLAN" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as f:
        d = json.load(f)

    jobs = d.get("jobs", [])

    if not jobs:
        print("false")
        raise SystemExit

    job = jobs[0]

    ready = job.get("presentation_ready") is True
    gate = job.get("slide_quality_gate") or {}
    gate_pass = gate.get("status") == "PASS"

    print("true" if ready and gate_pass else "false")

except Exception:
    print("false")
PY
)"

        if [ "$READY" = "true" ]; then
            echo "QWEN: PASS"

            SUCCESS_QWEN=$((SUCCESS_QWEN + 1))

            printf '%s\n' "$PLAN" >> "$QWEN_LIST"

        else
            echo "QWEN: FAIL — presentation not ready"
            FAILED_QWEN=$((FAILED_QWEN + 1))
        fi

    else
        echo "QWEN: FAIL"
        FAILED_QWEN=$((FAILED_QWEN + 1))
    fi

done <<EOF
$JOB_DOCXS
EOF

# ------------------------------------------------------------
# 3. Render every successful Qwen JSON
# ------------------------------------------------------------

echo
echo "============================================================"
echo "[3/3] Rendering Instagram slides"
echo "============================================================"

RENDER_SUCCESS=0
RENDER_FAILED=0
TOTAL_SLIDES=0

PLAN_NO=0
PLAN_COUNT="$SUCCESS_QWEN"

while IFS= read -r PLAN
do
    [ -z "$PLAN" ] && continue

    PLAN_NO=$((PLAN_NO + 1))

    JOB_FOLDER="$(basename "$(dirname "$PLAN")")"

    JOB_RENDER_DIR="${RENDER_DIR}/${JOB_FOLDER}"

    mkdir -p "$JOB_RENDER_DIR"

    echo
    echo "------------------------------------------------------------"
    echo "[${PLAN_NO}/${PLAN_COUNT}] Rendering"
    echo "JSON: ${PLAN}"
    echo "OUTPUT: ${JOB_RENDER_DIR}"
    echo "------------------------------------------------------------"

    "$PYTHON_BIN" main.py \
        --render-qwen "$PLAN" \
        --render-output "$JOB_RENDER_DIR" \
        --job-index 1

    RC=$?

    PNG_COUNT=$(
        find "$JOB_RENDER_DIR" \
            -type f \
            -name "*.png" \
            | wc -l \
            | tr -d ' '
    )

    if [ "$RC" -eq 0 ] && [ "$PNG_COUNT" -ge 6 ]; then

        echo "RENDER: PASS"
        echo "Slides: ${PNG_COUNT}"

        RENDER_SUCCESS=$((RENDER_SUCCESS + 1))
        TOTAL_SLIDES=$((TOTAL_SLIDES + PNG_COUNT))

    else

        echo "RENDER: FAIL"
        echo "PNG files produced: ${PNG_COUNT}"

        RENDER_FAILED=$((RENDER_FAILED + 1))
    fi

done < "$QWEN_LIST"

# ------------------------------------------------------------
# Final report
# ------------------------------------------------------------

"$PYTHON_BIN" - "$REPORT" \
    "$JOB_COUNT" \
    "$SUCCESS_QWEN" \
    "$FAILED_QWEN" \
    "$RENDER_SUCCESS" \
    "$RENDER_FAILED" \
    "$TOTAL_SLIDES" <<'PY'

import json
import sys
from datetime import datetime

(
    report,
    job_count,
    qwen_success,
    qwen_failed,
    render_success,
    render_failed,
    slides
) = sys.argv[1:]

data = {
    "version": "1.9.22",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "selection_rule": "crawler-selected listings with LAST DATE > TODAY",
    "duplicate_filtering": False,

    "job_detail_docx_count": int(job_count),

    "qwen_success": int(qwen_success),
    "qwen_failed": int(qwen_failed),

    "render_success": int(render_success),
    "render_failed": int(render_failed),

    "slides_rendered": int(slides),
}

with open(report, "w", encoding="utf-8") as f:
    json.dump(
        data,
        f,
        indent=2,
        ensure_ascii=False
    )
PY

echo
echo "============================================================"
echo " DAILY GENERATION COMPLETE"
echo "============================================================"

echo "Job Detail DOCX : ${JOB_COUNT}"
echo "Qwen PASS        : ${SUCCESS_QWEN}"
echo "Qwen FAIL        : ${FAILED_QWEN}"
echo "Render PASS      : ${RENDER_SUCCESS}"
echo "Render FAIL      : ${RENDER_FAILED}"
echo "Slides rendered  : ${TOTAL_SLIDES}"

echo
echo "DOCX:"
echo "  ${DOCX_DIR}/"

echo
echo "Qwen JSON:"
echo "  ${QWEN_DIR}/"

echo
echo "Instagram:"
echo "  ${RENDER_DIR}/"

echo
echo "Report:"
echo "  ${REPORT}"

echo "============================================================"