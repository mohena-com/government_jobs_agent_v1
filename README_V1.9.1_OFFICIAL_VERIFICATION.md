# V1.9.1 — Official PDF Verification + Reconciliation Fix

## Why 1.9.1

The first V1.9 run against the real RVUNL PDFs returned a false 1,993 total. The problem was **not the official notifications**; the PDF table parser was accidentally counting rows from horizontal-reservation tables and missing the Civil TSP/non-TSP total structure.

The real detailed-notification totals are:

- Junior Engineer-I (Electrical): 727
- Junior Engineer-I (Mechanical): 110
- Junior Engineer-I (Civil): 32
- Junior Accountant: 371
- Junior Assistant / Commercial Assistant-II: 765
- Combined: **2,005**

The July short notice is also classified separately as Advertisement No. `RVUN/Rectt.-2026-27/01` and its 2,005 total is retained as provenance. The later August detailed advertisements are the authoritative post-wise verification layer.

## Fixes

1. Correctly classify `/01` short notice.
2. Preserve short-notice vacancy total separately.
3. Parse non-TSP and TSP vacancy tables separately.
4. Exclude horizontal-reservation tables from vacancy totals.
5. Handle PDF layouts where the Civil table's final numeric row has no `Total` label.
6. Correct post names so table text is not included in the post field.
7. Report actual PDF page counts instead of character counts.
8. Reconcile detailed advertisements against the short notice.
9. PASS official verification when both detailed advertisements are present, dates agree, and the detailed vacancy total is coherent.

## Expected RVUNL verification

```text
Advt 01 short notice: 2005
Advt 02 detailed JE: 869
Advt 03 detailed JA/Accountant: 1136
Combined detailed total: 2005
Application: 2026-08-05 through 2026-08-25
Official verification: PASS
```

## Run

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --quality-gate-only \
  --job-index 1 \
  --qwen-output social/qwen_v191
```

Then inspect:

```bash
python3 -m json.tool social/qwen_v191/qwen_instagram_plans.json
```

Qwen remains blocked by `--quality-gate-only`; the purpose of this run is to establish the verified fact layer first.
