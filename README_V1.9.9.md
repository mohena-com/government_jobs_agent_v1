# V1.9.9 — Immutable Verified Fact Bundle

V1.9.9 is a full workspace release built from V1.9.8.

## Main fix

The official verification pass and Qwen generation path now use the **same frozen fact bundle**. Qwen never re-reads or reconstructs facts from raw DOCX extraction after verification.

`verified_fact_bundle.json` is written before Qwen generation.

## RVUNL reconciliation hardening

The authoritative RVUNL pilot profile now:
- repairs extracted totals that differ from the official profile;
- adds canonical rows if PDF text extraction omits them;
- tolerates minor post-label spacing differences;
- keeps an audit trail of every repair/addition.

Expected RVUNL post totals:
- Junior Engineer-I (Electrical): 727
- Junior Engineer-I (Mechanical): 110
- Junior Engineer-I (Civil): 32
- Junior Accountant: 371
- Junior Assistant/ Commercial Assistant-II: 765
- Combined: 2,005

## Qwen safety

Qwen is blocked if:
- official verification fails;
- canonical vacancy totals do not reconcile;
- any canonical post lacks clean post-specific eligibility;
- contaminated how-to-apply/selection fields are detected.

## Run quality gate only

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --quality-gate-only \
  --job-index 1 \
  --qwen-output social/qwen_v199
```

## Run actual Qwen

Only after the quality-gate-only output is PASS:

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --job-index 1 \
  --ollama-host http://webmaster-ai.local:11434 \
  --ollama-model qwen3:8b \
  --slide-count 6 \
  --qwen-output social/qwen_v199
```
