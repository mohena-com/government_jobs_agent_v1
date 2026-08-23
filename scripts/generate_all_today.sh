#!/usr/bin/env bash
set -uo pipefail

# ============================================================
# Government Jobs → DOCX → Qwen JSON → Instagram Slides
# ============================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3.1}"
OLLAMA_HOST="${OLLAMA_HOST:-http://webmaster-ai.local:11434}"
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
# 1. Crawl + generate ALL Job Detail DOCX files
# ------------------------------------------------------------

echo
echo "[1/3] Crawling jobs and generating Job Detail DOCX files..."
echo

"$PYTHON_BIN" main.py --max-jobs 1000

CRAWL_RC=$?

if [[ $CRAWL_RC -ne 0 ]]; then
    echo
    echo "ERROR: Job crawler failed."
    exit $CRAWL_RC
fi

# ------------------------------------------------------------
# Find DOCX files generated TODAY
# ------------------------------------------------------------

echo
echo "Finding today's Job Detail DOCX files..."

mapfile -t JOB_DOCXS < <(
    find "$DOCX_DIR" -type f -name "*.docx" \
        -newermt "${TODAY} 00:00:00" \
        ! -name "*Summary.docx" \
        | sort
)

JOB_COUNT="${#JOB_DOCXS[@]}"

echo "Job Detail DOCX files found: ${JOB_COUNT}"

if [[ "$JOB_COUNT" -eq 0 ]]; then
    echo
    echo "ERROR: No Job Detail DOCX files found."
    exit 1
fi

# ------------------------------------------------------------
# 2. Qwen JSON generation for EVERY DOCX
# ------------------------------------------------------------

echo
echo "============================================================"
echo "[2/3] Generating Qwen JSON for every job"
echo "============================================================"

SUCCESS_QWEN=0
FAILED_QWEN=0

declare -a QWEN_PLANS=()

JOB_NO=0

for DOCX in "${JOB_DOCXS[@]}"; do

    JOB_NO=$((JOB_NO + 1))

    BASENAME="$(basename "$DOCX" .docx)"

    # Safe output folder
    JOB_QWEN_DIR="${QWEN_DIR}/${JOB_NO}"
    mkdir -p "$JOB_QWEN_DIR"

    echo
    echo "------------------------------------------------------------"
    echo "[${JOB_NO}/${JOB_COUNT}] Qwen"
    echo "DOCX: ${DOCX}"
    echo "------------------------------------------------------------"

    # IMPORTANT:
    # Each DOCX is processed as job-index 1 because the DOCX contains
    # the single job we are sending to Qwen.
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

    if [[ $RC -eq 0 && -f "$PLAN" ]]; then

        # Confirm that the job actually passed presentation QA.
        READY="$(
            "$PYTHON_BIN" - "$PLAN" <<'PY'
import json
import sys

p = sys.argv[1]

try:
    with open(p, encoding="utf-8") as f:
        d = json.load(f)

    jobs = d.get("jobs", [])

    if not jobs:
        print("false")
        raise SystemExit

    j = jobs[0]

    gate = j.get("slide_quality_gate") or {}
    ready = j.get("presentation_ready") is True
    passed = gate.get("status") == "PASS"

    print("true" if ready and passed else "false")

except Exception:
    print("false")
PY
    )"

        if [[ "$READY" == "true" ]]; then
            echo "QWEN: PASS"
            SUCCESS_QWEN=$((SUCCESS_QWEN + 1))
            QWEN_PLANS+=("$PLAN")
        else
            echo "QWEN: FAIL — presentation not ready"
            FAILED_QWEN=$((FAILED_QWEN + 1))
        fi

    else
        echo "QWEN: FAIL"
        FAILED_QWEN=$((FAILED_QWEN + 1))
    fi

done

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

for PLAN in "${QWEN_PLANS[@]}"; do

    PLAN_NO=$((PLAN_NO + 1))

    JOB_FOLDER="$(basename "$(dirname "$PLAN")")"

    JOB_RENDER_DIR="${RENDER_DIR}/${JOB_FOLDER}"

    mkdir -p "$JOB_RENDER_DIR"

    echo
    echo "------------------------------------------------------------"
    echo "[${PLAN_NO}/${#QWEN_PLANS[@]}] Rendering"
    echo "JSON: ${PLAN}"
    echo "OUTPUT: ${JOB_RENDER_DIR}"
    echo "------------------------------------------------------------"

    "$PYTHON_BIN" main.py \
        --render-qwen "$PLAN" \
        --render-output "$JOB_RENDER_DIR" \
        --job-index 1

    RC=$?

    # Count actual PNG files.
    PNG_COUNT="$(
        find "$JOB_RENDER_DIR" \
            -type f \
            \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" \) \
            | wc -l \
            | tr -d ' '
    )"

    if [[ $RC -eq 0 && "$PNG_COUNT" -ge 6 ]]; then

        echo "RENDER: PASS"
        echo "Slides: ${PNG_COUNT}"

        RENDER_SUCCESS=$((RENDER_SUCCESS + 1))
        TOTAL_SLIDES=$((TOTAL_SLIDES + PNG_COUNT))

    else

        echo "RENDER: FAIL"
        echo "PNG files produced: ${PNG_COUNT}"

        RENDER_FAILED=$((RENDER_FAILED + 1))

    fi

done

# ------------------------------------------------------------
# Final report
# ------------------------------------------------------------

"$PYTHON_BIN" - "$REPORT" "$JOB_COUNT" "$SUCCESS_QWEN" "$FAILED_QWEN" "$RENDER_SUCCESS" "$RENDER_FAILED" "$TOTAL_SLIDES" <<'PY'
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
    "selection_rule": "DOCX files generated by crawler for listings with LAST DATE > TODAY",
    "duplicate_filtering": False,
    "job_detail_docx_count": int(job_count),
    "qwen_success": int(qwen_success),
    "qwen_failed": int(qwen_failed),
    "render_success": int(render_success),
    "render_failed": int(render_failed),
    "slides_rendered": int(slides),
}

with open(report, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
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