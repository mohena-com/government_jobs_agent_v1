# V1.9.14 Release Notes

## Purpose

V1.9.14 is the real presentation-layer release. It keeps the official PDF verification and source quality gates from V1.9.13, but changes the editorial and rendering layer so the final output is a useful job-seeker carousel rather than an extraction/audit report.

## Major changes

### 1. Complete job-post Qwen prompt
Qwen is now instructed to create exactly six job-seeker-focused sections:

1. Recruitment hook
2. Complete post-wise vacancies
3. Eligibility
4. Age + pay + application fee
5. Dates + selection process
6. How to apply + official links

### 2. Internal metadata separation
The following must never appear in artwork:

- PASS / FAIL
- quality gate
- verification status
- parsed vacancies
- authoritative vacancies
- vacancy reconciliation
- extraction repairs
- PDF extraction diagnostics
- facts_used
- source methods

### 3. Completeness gate
The slide-level gate now checks that the carousel contains available verified information for:

- total vacancies
- every verified post
- eligibility/qualification
- age
- pay where available
- application fee where available
- application dates
- selection process
- official links

### 4. Friendly links
Raw URLs and Markdown links are no longer rendered as text. Verified URLs are attached to slide 6 as structured metadata and rendered as:

- human-friendly link labels
- official domain
- QR code

The audit JSON still retains the original URLs.

### 5. Presentation sanitizer
The sanitizer now removes extraction/reconciliation leakage and Markdown links from slide copy, while retaining audit metadata separately.

## Recommended commands

Generate:

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

Render:

```bash
python3 main.py \
  --render-qwen social/qwen_v1914/qwen_instagram_plans.json \
  --render-output social/rendered_v1914 \
  --job-index 1
```

## Validation

Regression suite: **33 passed**.
