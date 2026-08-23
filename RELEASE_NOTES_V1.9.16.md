# V1.9.16 — Positional Qwen Presentation Contract

## Problem fixed
Qwen3:8B could ignore the six-slide contract and repeat the vacancies slide even after an automatic repair pass.

## Fix
- Replaced the free-form six-item slide array schema with six fixed JSON properties (`slide_1` … `slide_6`).
- Each property has a single allowed slide type, preventing slide-type drift/reordering at the structured-output layer.
- Repair pass uses the identical positional schema and cannot change slide types.
- Improved post-name normalization so slash/spacing variants are recognized by completeness checks.
- Existing source verification and slide quality gates remain strict; no manual override is introduced.
- Audit metadata remains in `qwen_instagram_plans.json`; presentation output remains sanitized.

## Expected RVUNL result
The model should produce: title → vacancies → eligibility → age/pay/fee → dates/selection → apply/links.
