# V1.9.5 — Post-wise Structured Fact Extraction

Builds on V1.9.4. Main change: official PDF facts are now segmented by individual post before being exposed to downstream Qwen generation.

## Fixes
- Separates RVUNL Electrical / Mechanical / Civil qualification text.
- Adds `post_facts[]` with post, advertisement, vacancy, qualification, experience and source URL.
- Cleans RVUNL fee extraction into a compact canonical value.
- Keeps raw parser totals and official reconciliation audit trail.
- Qwen receives `post_facts` as an authoritative field.

## Test
```bash
pytest -q
```

## RVUNL diagnostic
```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --quality-gate-only \
  --job-index 1 \
  --qwen-output social/qwen_v195
```
