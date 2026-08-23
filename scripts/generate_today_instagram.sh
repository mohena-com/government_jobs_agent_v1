#!/usr/bin/env bash
set -euo pipefail

# V1.9.18 — one-command daily Instagram generation.
# IST date → today's unique listings → exclude yesterday-used jobs →
# official verification → Qwen → slide QA → rendering.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export TZ="Asia/Kolkata"
export TODAY="$(date +%F)"
TODAY_LABEL="$(date '+%d %B %Y')"

PYTHON_BIN="${PYTHON_BIN:-python3}"
OLLAMA_HOST="${OLLAMA_HOST:-http://webmaster-ai.local:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"
CRAWL_MAX_JOBS="${CRAWL_MAX_JOBS:-1000}"

SELECTED_JSON="social/today_jobs.json"
QWEN_ROOT="social/qwen_today_${TODAY}"
RENDER_ROOT="social/rendered_today_${TODAY}"
HISTORY="social/agent_usage_history.jsonl"
RUN_REPORT="social/daily_generation_${TODAY}.json"
export QWEN_ROOT RENDER_ROOT TODAY

mkdir -p "$QWEN_ROOT" "$RENDER_ROOT" "social"

echo "============================================================"
echo "Government Jobs → Instagram | $TODAY_LABEL"
echo "============================================================"

echo "[1/4] Crawling jobs published/updated today..."
"$PYTHON_BIN" main.py --published-today --max-jobs "$CRAWL_MAX_JOBS"

echo "[2/4] Selecting unique today's jobs and excluding yesterday-used jobs..."
"$PYTHON_BIN" scripts/select_today_jobs.py \
  --today "$TODAY" \
  --history "$HISTORY" \
  --output "$SELECTED_JSON"

COUNT="$($PYTHON_BIN - <<'PY'
import json
p='social/today_jobs.json'
print(json.load(open(p, encoding='utf-8')).get('selected_count', 0))
PY
)"

if [[ "$COUNT" == "0" ]]; then
  cat > "$RUN_REPORT" <<JSON
{
  "date": "$TODAY",
  "selected_count": 0,
  "success_count": 0,
  "failure_count": 0,
  "jobs": []
}
JSON
  echo "No new government jobs published today require Instagram generation."
  exit 0
fi

echo "[3/4] Running official verification + Qwen + rendering for $COUNT job(s)..."
"$PYTHON_BIN" - <<'PY'
import json
import os
import re
import subprocess
from pathlib import Path

selected = json.load(open('social/today_jobs.json', encoding='utf-8'))['jobs']
history = Path('social/agent_usage_history.jsonl')
qwen_root = Path(os.environ['QWEN_ROOT'])
render_root = Path(os.environ['RENDER_ROOT'])
host = os.environ.get('OLLAMA_HOST', 'http://webmaster-ai.local:11434')
model = os.environ.get('OLLAMA_MODEL', 'qwen3:8b')
py = os.environ.get('PYTHON_BIN', 'python3')
today = os.environ.get('TODAY', '')


def safe(s):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', s or 'job')[:70].strip('_') or 'job'

results = []
for n, row in enumerate(selected, 1):
    title = row.get('title') or f'job_{n}'
    slug = f'{n:02d}_{safe(title)}'
    qout = qwen_root / slug
    rout = render_root / slug
    item = {
        'job_index': n,
        'title': title,
        'docx': row.get('docx'),
        'status': 'FAILED',
        'qwen_output': str(qout),
        'render_output': str(rout),
    }
    print(f'\n--- {n}/{len(selected)}: {title} ---')
    try:
        cmd = [
            py, 'main.py', '--docx', row['docx'], '--qwen', '--verify-official',
            '--job-index', '1', '--ollama-host', host, '--ollama-model', model,
            '--slide-count', '6', '--qwen-output', str(qout),
        ]
        subprocess.run(cmd, check=True)
        plan = qout / 'qwen_instagram_plans.json'
        summary = json.load(open(plan, encoding='utf-8'))
        job = (summary.get('jobs') or [{}])[0]
        item['action'] = job.get('action')
        item['presentation_ready'] = job.get('presentation_ready')
        if job.get('presentation_ready') is not True:
            item['error'] = 'Presentation quality gate failed'
            results.append(item)
            print(f"BLOCKED: presentation gate failed for {title}; continuing to next job")
            continue

        subprocess.run([
            py, 'main.py', '--render-qwen', str(plan),
            '--render-output', str(rout), '--job-index', '1',
        ], check=True)
        item['status'] = 'SUCCESS'
        results.append(item)

        keys = row.get('keys') or []
        with history.open('a', encoding='utf-8') as f:
            f.write(json.dumps({
                'used_date': today,
                'title': title,
                'docx': row['docx'],
                'keys': keys,
                'qwen_output': str(qout),
                'render_output': str(rout),
                'action': job.get('action'),
            }, ensure_ascii=False) + '\n')
    except subprocess.CalledProcessError as exc:
        item['error'] = f'Command failed with exit code {exc.returncode}'
        results.append(item)
        print(f'ERROR: {title}; continuing to next job')
    except Exception as exc:
        item['error'] = str(exc)
        results.append(item)
        print(f'ERROR: {title}: {exc}; continuing to next job')

Path(os.environ['RENDER_ROOT']).parent.mkdir(parents=True, exist_ok=True)
report = {
    'date': today,
    'selected_count': len(selected),
    'success_count': sum(x['status'] == 'SUCCESS' for x in results),
    'failure_count': sum(x['status'] != 'SUCCESS' for x in results),
    'jobs': results,
}
Path(f'social/daily_generation_{today}.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'
)
PY

echo "[4/4] Done."
echo "Rendered slides: $RENDER_ROOT"
echo "Qwen plans:       $QWEN_ROOT"
echo "Run report:       $RUN_REPORT"
