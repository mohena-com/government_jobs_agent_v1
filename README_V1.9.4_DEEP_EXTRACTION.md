# V1.9.4 — Official PDF Deep Fact Extraction

V1.9.4 builds on V1.9.3 and adds a conservative, non-LLM extraction layer for facts that must come from the official recruitment notification before Qwen is allowed to generate social content.

## New fields

- `post_eligibility[]`
  - post
  - qualification
  - experience
  - advertisement_number
  - source_url
- `selection_process`
- `application_fee_official`
- `how_to_apply`
- `experience`

## Important rule

The official PDF remains authoritative. The extractor does not invent missing facts. If a section cannot be reliably extracted, it remains empty and the quality gate can block Qwen.

The reconciled `post_vacancies` remains canonical. `raw_post_vacancies` is retained only for audit/debugging.

## RVUNL expected canonical vacancy total

727 + 110 + 32 + 371 + 765 = 2,005.

The known PDF text-extraction losses (Mechanical 6 vs 110; Junior Assistant 583 vs 765) remain visible in `extraction_repairs` while the canonical reconciled values are used downstream.

## Test

Run:

```bash
pytest -q
```

For RVUNL quality gate:

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --quality-gate-only \
  --job-index 1 \
  --qwen-output social/qwen_v194
```

Qwen should only be enabled after the quality gate passes.
