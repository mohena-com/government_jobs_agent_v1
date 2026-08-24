# SarkariResult Latest Jobs — V1.9.4

V1.9.4 adds **Official PDF Deep Fact Extraction** on top of V1.9.3.

Pipeline:

DOCX → official PDF verification → canonical vacancy reconciliation → deep official fact extraction → quality gate → Qwen

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
## Run

```bash
python3.1 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3.1 main.py --max-jobs 3
```
## Test

```bash
python3.1PATH=. pytest -q
```

Expected: 25 passed.

## RVUNL run

First run verification only:

```bash
python3.1 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --quality-gate-only \
  --job-index 1 \
  --qwen-output social/qwen_v199
```

Only after `quality_gate_status: PASS` should Qwen generation be enabled.

## Note

Official PDF downloads require network access from the machine running the agent. If the government PDF host is temporarily unreachable, the verifier records a download error and blocks Qwen rather than fabricating facts.


## V1.9.23
See `V1.9.23_CHANGELOG.md`. Daily end-to-end runner: `scripts/generate_all_today.sh`.
