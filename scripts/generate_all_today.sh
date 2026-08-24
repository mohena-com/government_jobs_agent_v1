#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

PYTHON_BIN="${PYTHON_BIN:-python3.1}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"
TODAY="${TODAY:-$(date '+%Y-%m-%d')}"

DOCX_DIR="reports/jobs"
QWEN_DIR="social/qwen_today_${TODAY}"
RENDER_DIR="social/rendered_today_${TODAY}"
REPORT="social/daily_generation_${TODAY}.json"

mkdir -p "$QWEN_DIR" "$RENDER_DIR"

echo "============================================================"
echo " Government Jobs → Instagram | V1.9.23"
echo " Date: ${TODAY}"
echo " Rule: LAST DATE > TODAY"
echo " Duplicate filtering: OFF"
echo "============================================================"

echo
echo "[1/3] Crawling jobs and generating Job Detail DOCX files..."
echo

"$PYTHON_BIN" main.py --max-jobs 1000
RC=$?
if [ "$RC" -ne 0 ]; then
    echo "ERROR: crawler failed."
    exit "$RC"
fi

echo
echo "Finding today's Job Detail DOCX files..."

JOB_COUNT=0
JOB_DOCXS=""

while IFS= read -r DOCX
do
    [ -z "$DOCX" ] && continue
    JOB_COUNT=$((JOB_COUNT + 1))
    JOB_DOCXS="${JOB_DOCXS}
${DOCX}"
done <<EOF
$(find "$DOCX_DIR" -type f -name "*.docx" \
    -newermt "${TODAY} 00:00:00" \
    ! -name "*Summary.docx" | sort)
EOF

echo "Job Detail DOCX files found: ${JOB_COUNT}"

if [ "$JOB_COUNT" -eq 0 ]; then
    echo "ERROR: No Job Detail DOCX files found."
    exit 1
fi

echo
echo "============================================================"
echo "[2/3] Official PDF verification + Qwen + slide QA"
echo "============================================================"

SUCCESS_QWEN=0
FAILED_QWEN=0
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
    echo "[${JOB_NO}/${JOB_COUNT}] ${DOCX}"
    echo "------------------------------------------------------------"

    # Each Job Detail DOCX is intentionally treated as one input job.
    # --batch-mode prevents a failed job from aborting the batch, while the
    # diagnostic JSON is still written for audit/debugging.
    "$PYTHON_BIN" main.py \
        --docx "$DOCX" \
        --qwen \
        --verify-official \
        --job-index 1 \
        --batch-mode \
        --ollama-host "$OLLAMA_HOST" \
        --ollama-model "$OLLAMA_MODEL" \
        --slide-count 6 \
        --qwen-output "$JOB_QWEN_DIR"

    RC=$?
    PLAN="${JOB_QWEN_DIR}/qwen_instagram_plans.json"

    if [ "$RC" -eq 0 ] && [ -f "$PLAN" ]; then
        READY="$(
            "$PYTHON_BIN" - "$PLAN" <<'PY'
import json, sys
try:
    d=json.load(open(sys.argv[1], encoding="utf-8"))
    jobs=d.get("jobs", [])
    j=jobs[0] if jobs else {}
    gate=j.get("slide_quality_gate") or {}
    print("true" if j.get("presentation_ready") is True and gate.get("status") == "PASS" else "false")
except Exception:
    print("false")
PY
        )"

        if [ "$READY" = "true" ]; then
            echo "QWEN/SLIDE QA: PASS"
            SUCCESS_QWEN=$((SUCCESS_QWEN + 1))
            printf '%s\n' "$PLAN" >> "$QWEN_LIST"
        else
            echo "QWEN/SLIDE QA: BLOCKED"
            FAILED_QWEN=$((FAILED_QWEN + 1))
        fi
    else
        echo "QWEN: PROCESS ERROR"
        FAILED_QWEN=$((FAILED_QWEN + 1))
    fi

done <<EOF
$JOB_DOCXS
EOF

echo
echo "============================================================"
echo "[3/3] Rendering presentation-ready Qwen JSONs"
echo "============================================================"

RENDER_SUCCESS=0
RENDER_FAILED=0
TOTAL_SLIDES=0
PLAN_NO=0

while IFS= read -r PLAN
do
    [ -z "$PLAN" ] && continue
    PLAN_NO=$((PLAN_NO + 1))

    JOB_FOLDER="$(basename "$(dirname "$PLAN")")"
    JOB_RENDER_DIR="${RENDER_DIR}/${JOB_FOLDER}"
    mkdir -p "$JOB_RENDER_DIR"

    echo
    echo "------------------------------------------------------------"
    echo "[${PLAN_NO}/${SUCCESS_QWEN}] ${PLAN}"
    echo "------------------------------------------------------------"

    "$PYTHON_BIN" main.py \
        --render-qwen "$PLAN" \
        --render-output "$JOB_RENDER_DIR" \
        --job-index 1

    RENDER_RC=$?

    PNG_COUNT=$(
        find "$JOB_RENDER_DIR" -type f -name "*.png" | wc -l | tr -d ' '
    )

    if [ "$RENDER_RC" -eq 0 ] && [ "$PNG_COUNT" -ge 6 ]; then
        echo "RENDER: PASS (${PNG_COUNT} slides)"
        RENDER_SUCCESS=$((RENDER_SUCCESS + 1))
        TOTAL_SLIDES=$((TOTAL_SLIDES + PNG_COUNT))
    else
        echo "RENDER: FAIL (${PNG_COUNT} PNGs)"
        RENDER_FAILED=$((RENDER_FAILED + 1))
    fi
done < "$QWEN_LIST"

"$PYTHON_BIN" - "$REPORT" "$JOB_COUNT" "$SUCCESS_QWEN" "$FAILED_QWEN" \
    "$RENDER_SUCCESS" "$RENDER_FAILED" "$TOTAL_SLIDES" <<'PY'
import json, sys
from datetime import datetime
p,j,qs,qf,rs,rf,s = sys.argv[1:]
data={
    "version":"1.9.23",
    "date":datetime.now().strftime("%Y-%m-%d"),
    "selection_rule":"crawler-selected listings with LAST DATE > TODAY",
    "duplicate_filtering":False,
    "job_detail_docx_count":int(j),
    "qwen_success":int(qs),
    "qwen_failed":int(qf),
    "render_success":int(rs),
    "render_failed":int(rf),
    "slides_rendered":int(s),
}
with open(p,"w",encoding="utf-8") as f:
    json.dump(data,f,indent=2,ensure_ascii=False)
PY

echo
echo "============================================================"
echo " DAILY GENERATION COMPLETE | V1.9.23"
echo "============================================================"
echo "Job Detail DOCX : ${JOB_COUNT}"
echo "Qwen PASS        : ${SUCCESS_QWEN}"
echo "Qwen BLOCKED     : ${FAILED_QWEN}"
echo "Render PASS      : ${RENDER_SUCCESS}"
echo "Render FAIL      : ${RENDER_FAILED}"
echo "Slides rendered  : ${TOTAL_SLIDES}"
echo
echo "DOCX     : ${DOCX_DIR}/"
echo "Qwen JSON: ${QWEN_DIR}/"
echo "Slides   : ${RENDER_DIR}/"
echo "Report   : ${REPORT}"
echo "============================================================"
