# V1.9.12 — Slide-Level Quality Gate

Adds a second quality layer after official fact verification and Qwen generation.

## Pipeline

DOCX extraction → official PDF verification/reconciliation → source quality gate → Qwen → **slide-level quality gate** → renderer

Qwen remains an editorial layer; the locked/official fact bundle remains authoritative.

## What the new gate checks

- unsupported process claims such as `document verification` when not present in locked selection facts
- stale application-status wording such as `application ended` while the deadline has not passed
- unsupported numeric claims
- malformed/empty slides
- excessive bullets
- generic filler that makes a slide less useful
- selection-specific claims against the verified selection process
- ignores the `27` fragment in identifiers such as `2026-27` as a standalone numeric fact

A failed slide gate blocks downstream publishing/rendering.

## Run

The existing Qwen command remains the same:

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --job-index 1 \
  --ollama-host http://webmaster-ai.local:11434 \
  --ollama-model qwen3:8b \
  --slide-count 6 \
  --qwen-output social/qwen_v1912
```

Inspect:

```bash
python3 -m json.tool social/qwen_v1912/qwen_instagram_plans.json
```

Look for:

```json
"slide_quality_gate": {
  "status": "PASS"
}
```

Only when that status is `PASS` should the slide renderer be allowed to publish images.
