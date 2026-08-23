# V1.9.13 Release Notes

## Purpose
Final presentation-ready workspace for the local Qwen government-jobs Instagram pipeline.

## Changes from V1.9.12

1. Added `src/llm/presentation_sanitizer.py`.
2. Qwen output is preserved as `raw_slide_plan` for audit.
3. Presentation copy is sanitized before slide-level quality validation.
4. Internal QA/status phrases are removed from artwork-facing headline/subtitle/bullets.
5. ISO dates in presentation copy are converted to readable dates such as `05 August 2026`.
6. Added `instagram_presentation_ready.json` containing only approved slide content.
7. Added `src/social/qwen_renderer.py` to render the approved Qwen slide plan to 1080×1350 PNG files.
8. Added `--render-qwen` and `--render-output` CLI options.
9. Renderer has defense-in-depth removal of QA/status text.
10. URL validation normalizes trailing JSON punctuation.
11. Added regression tests for sanitizer and renderer.

## Validation

`pytest`: **32 passed**.

## Production command

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --job-index 1 \
  --ollama-host http://webmaster-ai.local:11434 \
  --ollama-model qwen3:8b \
  --slide-count 6 \
  --qwen-output social/qwen_v1913
```

Then render only if `presentation_ready` is true:

```bash
python3 main.py \
  --render-qwen social/qwen_v1913/qwen_instagram_plans.json \
  --render-output social/rendered_v1913 \
  --job-index 1
```
