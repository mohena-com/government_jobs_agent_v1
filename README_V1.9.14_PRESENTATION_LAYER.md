# V1.9.15 — Complete Presentation Layer

V1.9.15 is the presentation-focused release built on V1.9.13.

## What changed

- Replaced the Qwen prompt with a complete job-seeker-focused six-slide specification.
- Fixed six slide roles:
  1. Recruitment hook
  2. Complete post-wise vacancies
  3. Eligibility
  4. Age + pay + application fee
  5. Dates + selection process
  6. How to apply + official links
- Added a completeness gate so a factually correct but incomplete carousel is blocked.
- Internal audit information is explicitly forbidden in Qwen output.
- Sanitizer removes audit/debug leakage including reconciliation/extraction text.
- Official URLs are attached by the application as structured metadata after Qwen generation.
- Raw URLs and Markdown links are never rendered as slide text.
- Last slide renders human-friendly labels, official domains, and QR codes.
- The complete audit JSON still retains official URLs and quality-gate metadata.

## RVUNL expected result

The carousel should contain job-seeker information, not pipeline diagnostics. In particular,
"Vacancy Reconciliation", "Extraction Repairs", "Parsed Vacancies", "Authoritative Vacancies",
and "Status: PASS" must never appear in artwork.

## Generate

```bash
python3 main.py \
  --docx "reports/jobs/03_Rajasthan_RVUNL_for_JE_Junior_Accountant_Junior_Assistant_Commercial_Assistant-II_Common_R_2026-08-23.docx" \
  --qwen \
  --verify-official \
  --job-index 1 \
  --ollama-host http://webmaster-ai.local:11434 \
  --ollama-model qwen3:8b \
  --slide-count 6 \
  --qwen-output social/qwen_v1914
```

## Render

```bash
python3 main.py \
  --render-qwen social/qwen_v1914/qwen_instagram_plans.json \
  --render-output social/rendered_v1914 \
  --job-index 1
```

The presentation-facing file is:

```text
social/qwen_v1914/instagram_presentation_ready.json
```

The audit file remains:

```text
social/qwen_v1914/qwen_instagram_plans.json
```
