# V1.9.36 — Canonical Presentation Contract Hotfix

This release addresses the regressions exposed by the first V1.9.35 three-job run.

## Fixes

### 1. Application dates are deterministic everywhere
- Canonical `application_start` / `application_end` remain authoritative.
- Application-date prose such as `link remains active from X to Y` is rewritten to the canonical pair.
- LLM-generated application dates cannot survive if they conflict with the canonical pair.
- Fee-payment, exam, notification and admit-card dates are not treated as application dates.

### 2. Eligibility cannot disappear from Slide 3
- A final presentation-contract pass runs after Qwen generation and automatic repair.
- If verified eligibility is missing from the plan, a compact source-backed qualification bullet is inserted.
- If the source field is unavailable, the normal notification fallback is used.

### 3. `APPLY NOW` is presentation CTA, not a factual claim
- Removed `apply now` from the hard factual conditional-claim list.
- This prevents a generic design CTA from triggering a false factual reconciliation failure.

### 4. Missing presentation fields are repaired before QA
- Age, pay/salary, fee, selection and application-date coverage receive compact source-backed content or safe fallbacks.
- This keeps slides complete without inventing facts.

### 5. Batch robustness
- One problematic Qwen field must not create a fatal reconciliation failure when it can be safely normalized or replaced with a fallback.

## Validation

66 tests pass.
