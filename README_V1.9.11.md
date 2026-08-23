# V1.9.11 — Qwen Instagram Pipeline Fix

V1.9.11 fixes the false-positive numeric validation seen after official PDF verification and tightens Qwen slide generation.

## Changes
- Validator checks numbers against the complete nested authoritative fact bundle.
- Verified vacancy counts such as 727, 110, 32, 371, 765 and total 2005 are accepted.
- Qwen is forbidden from inferring unsupported application method/URL/fee/selection facts.
- Six-slide guidance is fact-dense: hook, vacancies, eligibility, age/pay, dates/fee, selection/source.
- Generic filler is discouraged.
- No manual JSON override is required.

## Recommended command
```bash
python3 main.py \\
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \\
  --qwen \\
  --job-index 1 \\
  --verify-official \\
  --ollama-host http://webmaster-ai.local:11434 \\
  --ollama-model qwen3:8b \\
  --slide-count 6 \\
  --qwen-output social/qwen_v1911
```

A PASS means the facts are verified and Qwen may generate copy. Review the slide plan before publishing.
