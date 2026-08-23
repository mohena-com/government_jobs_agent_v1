# SarkariResult Latest Jobs — V1.9.6

V1.9.6 adds a **hard post-specific eligibility quality gate** on top of V1.9.5.

Pipeline:

DOCX → official PDF verification → canonical vacancy reconciliation → deep official fact extraction → post-fact quality gate → Qwen

Qwen remains blocked until the quality gate passes.

## New V1.9.4 capabilities

- Post-wise educational qualification extraction from official notification text.
- Post-wise experience extraction where explicitly present.
- Official selection-process extraction.
- Official application-fee extraction.
- Official how-to-apply/application-procedure extraction.
- Canonical `post_vacancies` remains the only downstream vacancy source.
- `raw_post_vacancies` remains audit-only.
- Contaminated SarkariResult boilerplate is never restored after official verification.
- Quality gate rejects a PASS when official verification succeeds but no post-wise eligibility can be extracted.

## RVUNL pilot

Expected reconciled total:

727 + 110 + 32 + 371 + 765 = 2,005

Known parser losses remain visible as repairs (Mechanical 6→110 and Junior Assistant/Commercial Assistant-II 583→765), while the repaired canonical values are used downstream.

## Test

```bash
PYTHONPATH=. pytest -q
```

Expected: 25 passed.

## RVUNL run

First run verification only:

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --quality-gate-only \
  --job-index 1 \
  --qwen-output social/qwen_v194
```

Only after `quality_gate_status: PASS` should Qwen generation be enabled.

## Note

Official PDF downloads require network access from the machine running the agent. If the government PDF host is temporarily unreachable, the verifier records a download error and blocks Qwen rather than fabricating facts.


## V1.9.6 quality gate

V1.9.6 blocks Qwen when official verification passes but critical post-wise
eligibility facts are still generic, page-window based, unknown, or missing.

For verified jobs:

- `RVUNL_POST_BOUNDARY` is accepted as a post-specific source method.
- `GENERIC_BOUNDARY`, `GENERIC`, `PAGE_WINDOW`, and `UNKNOWN` are rejected.
- Every canonical `post_vacancies` entry must have a corresponding post-specific
  qualification fact.
- Empty post-specific qualification is rejected.
- The canonical reconciled vacancy list remains the downstream source of truth.
