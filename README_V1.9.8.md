# V1.9.8 — Full Workspace

V1.9.8 is a complete runnable workspace, not a patch-only ZIP.

## Main changes

- Integrates the V1.9.7 hard quality-gate behavior into the actual pipeline.
- Official PDF verification remains authoritative for vacancies/dates.
- Canonical post facts are required before Qwen can run.
- Fixes RVUNL Advertisement 03 qualification extraction using the dedicated
  official `3. Educational qualification` table.
- Junior Accountant and Junior Assistant/Commercial Assistant-II are extracted
  independently and tagged `RVUNL_EDUCATION_TABLE`.
- Contaminated text such as Disqualification, Character and Physical Fitness is
  excluded from post qualification facts.
- `verification_required` can no longer be reset to false after a post-fact
  quality failure.
- Qwen remains blocked until the quality gate passes.

## RVUNL canonical posts

- Junior Engineer-I (Electrical): 727
- Junior Engineer-I (Mechanical): 110
- Junior Engineer-I (Civil): 32
- Junior Accountant: 371
- Junior Assistant/ Commercial Assistant-II: 765
- Combined: 2,005

## Test

Run from the workspace root:

```bash
pytest -q
```

The RVUNL-specific V1.9.8 tests are in `tests/test_v198_structured.py`.

## RVUNL diagnostic run

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --quality-gate-only \
  --job-index 1 \
  --qwen-output social/qwen_v198
```

Inspect `social/qwen_v198/qwen_instagram_plans.json` before enabling actual
Qwen generation.
