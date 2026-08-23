# V1.7 — Local Qwen / Ollama DOCX Instagram Editor

V1.7 builds directly on `sarkariresult_latest_jobs_v1_6_instagram_curated_workspace.zip`.
The existing SarkariResult crawler and Pillow Instagram renderer are preserved.

The new path is:

```text
existing recruitment DOCX
        ↓
Python DOCX reader
        ↓
source-derived LOCKED_FACTS
        ↓
Ollama / Qwen3 8B
        ↓
structured slide JSON
        ↓
numeric/date/URL guardrail
```

Qwen is an **editorial layer**, not the source of truth.

## Your setup

You have Qwen3 8B running on `webmaster-ai` through Ollama and reachable from
another machine at:

```text
http://webmaster-ai.local:11434
```

The default model is:

```text
qwen3:8b
```

## Install

Use the same virtual environment as V1.6, then:

```bash
pip install -r requirements.txt
```

No Alibaba Cloud SDK is required.

## Step 1 — test the DOCX reader only

```bash
python main.py --docx /path/to/your/recruitment_report.docx
```

This does not call Qwen. It prints the jobs detected by the reader.

## Step 2 — test ONE job with Qwen

Start with one job so you can inspect the output before processing an entire
report:

```bash
python main.py \
  --docx /path/to/your/recruitment_report.docx \
  --qwen \
  --job-index 1 \
  --ollama-host http://webmaster-ai.local:11434 \
  --ollama-model qwen3:8b \
  --slide-count 6 \
  --qwen-output social/qwen
```

Output:

```text
social/qwen/
  01_<job>_slide_plan.json
  qwen_instagram_plans.json
```

The JSON contains:

- source job record
- locked facts sent to Qwen
- Qwen slide plan
- validation warnings

## Step 3 — process all jobs

Once the first job looks good:

```bash
python main.py \
  --docx /path/to/your/recruitment_report.docx \
  --qwen \
  --ollama-host http://webmaster-ai.local:11434 \
  --ollama-model qwen3:8b \
  --slide-count 6
```

## Important design decision

The reader does not ask Qwen to discover facts. It extracts what is already in
the DOCX and labels that payload `LOCKED_FACTS`.

The Qwen prompt explicitly forbids invention of:

- dates / years
- vacancy counts
- advertisement numbers
- post names
- qualifications
- salary / pay
- fees
- URLs
- application status

The Ollama call uses `think=false` because this is a short editorial
transformation rather than a reasoning task.

## Current limitation

V1.7 produces **slide JSON**, not final PNGs from Qwen output. The existing
Pillow renderer remains unchanged. This separation is intentional: first
validate that Qwen produces accurate slide content; then connect the validated
JSON to the renderer.

## Tests

```bash
python -m pytest -q
```

V1.7 currently includes unit tests for the DOCX reader, JSON parsing and
numeric hallucination guardrails.
