# V1.9.30 — Verification-to-Generation Decoupling Hotfix

## Fixed
A missing official post-level eligibility row no longer fails the source quality gate.

Example:
- Official notification contains a post in `post_vacancies`.
- Structured eligibility extraction does not contain that post.

Previous behavior:
- quality gate ERROR
- presentation generation could be blocked

V1.9.30 behavior:
- quality gate WARNING
- missing field remains unavailable
- presentation-safe facts use a controlled fallback
- Qwen is allowed to generate
- slide QA remains authoritative for the final presentation

## Safety
Direct factual reconciliation conflicts remain fatal. This hotfix does not permit invented recruitment facts.

## Intended flow
verified facts -> allowed facts
missing/unreadable facts -> fallback
allowed facts + fallbacks -> Qwen
Qwen -> slide QA -> renderer
