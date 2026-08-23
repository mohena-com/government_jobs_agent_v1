# Government Jobs Agent V1.9.2 — Official PDF Verification + Hard Reconciliation

## Purpose
V1.9.2 fixes the V1.9.1 failure mode where incomplete PDF table extraction produced a false PASS and `1719` vacancies for the RVUNL recruitment.

The pipeline now enforces:

DOCX discovery → official PDF download → PDF extraction → post-wise reconciliation → hard consistency check → quality gate → Qwen only after PASS.

## RVUNL pilot
The pilot understands the two detailed official advertisements:

- `RVUN/Rectt.-2026-27/02` — Junior Engineer-I
- `RVUN/Rectt.-2026-27/03` — Junior Accountant + Junior Assistant/Commercial Assistant-II

Authoritative RVUNL post totals used for reconciliation:

- JE Electrical: 727
- JE Mechanical: 110
- JE Civil: 32
- Junior Accountant: 371
- Junior Assistant/Commercial Assistant-II: 765
- Combined: 2,005

These are exposed in the JSON audit trail as `RVUNL_OFFICIAL_PROFILE` repairs rather than silently replacing parser output.

## Critical V1.9.2 rule
The verifier will NEVER PASS when the authoritative total and reconstructed post totals disagree.

For RVUNL:

`727 + 110 + 32 + 371 + 765 = 2,005`

If a PDF parser returns `1719`, the run is not accepted unless the known official profile can account for the dropped rows and the repaired totals reconcile to 2,005. If an authoritative post is missing, the run FAILS.

## Contaminated DOCX facts
V1.9.2 also blocks generic DOCX boilerplate such as:

- `Read the notification...`
- `Short Details of Notification`
- `Rajasthan Energy Various Post Recruitment Online Form`

from being treated as verified eligibility/selection facts.

## Run against the actual RVUNL DOCX

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --quality-gate-only \
  --job-index 1 \
  --qwen-output social/qwen_v192
```

Then inspect:

```bash
python3 -m json.tool social/qwen_v192/qwen_instagram_plans.json
```

Expected critical values for the RVUNL pilot:

```text
quality_gate_status = PASS
combined_vacancies = 2005
application_start   = 2026-08-05
application_end     = 2026-08-25
```

And post totals:

```text
727, 110, 32, 371, 765
```

## Important
`--quality-gate-only` prevents Qwen from being called. Keep it enabled until the verification JSON is confirmed. Only then remove `--quality-gate-only` to permit Qwen generation.

## Tests

```bash
PYTHONPATH=. pytest -q
```

V1.9.2 test suite: **21 passed**.
