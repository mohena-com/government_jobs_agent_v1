# V1.9.13 — Final Instagram Presentation Sanitizer

V1.9.13 is the complete workspace release built on V1.9.12.

## New behavior

Pipeline:

DOCX → official PDF verification → reconciliation → source quality gate → Qwen → presentation sanitizer → slide-level quality gate → presentation-ready JSON.

The sanitizer removes internal QA/validation/status text from artwork-facing fields while retaining audit metadata in the full `qwen_instagram_plans.json` record.

Examples removed from presentation copy:

- `Status: PASS`
- `Quality Gate: PASS`
- `Verified against official sources`
- `facts_used: ...`
- validation-only messages

ISO dates are formatted as `05 August 2026` rather than `2026-08-05`.

## Output

After a successful run, inspect:

- `social/qwen_v1913/qwen_instagram_plans.json` — complete audit record
- `social/qwen_v1913/instagram_presentation_ready.json` — presentation-facing slide content
- `social/qwen_v1913/01_*_slide_plan.json` — per-job audit record

`presentation_ready` is true only when the slide-level gate passes after sanitization.

## Command

```bash
python3 main.py \\
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \\
  --qwen \\
  --verify-official \\
  --job-index 1 \\
  --ollama-host http://webmaster-ai.local:11434 \\
  --ollama-model qwen3:8b \\
  --slide-count 6 \\
  --qwen-output social/qwen_v1913
```

The official verification flag remains mandatory for production use.

## Render the approved Instagram slides

After `qwen_instagram_plans.json` reports `presentation_ready: true`, run:

```bash
python3 main.py \\
  --render-qwen social/qwen_v1913/qwen_instagram_plans.json \\
  --render-output social/rendered_v1913 \\
  --job-index 1
```

The PNG files are written under `social/rendered_v1913/`.
