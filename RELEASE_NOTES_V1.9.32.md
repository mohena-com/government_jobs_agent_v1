# V1.9.32 — Field-Aware Presentation QA + Resilient Extraction

## Policy
A missing required source field no longer blocks slide generation by itself.

The system now separates:
1. factual contradictions — still fatal
2. unavailable/missing facts — non-fatal, replaced with explicit presentation fallbacks
3. presentation/design copy — allowed independently of locked facts

## Safe fallbacks
- Vacancy: See Official Notification
- Eligibility: Refer to Official Notification
- Age: Refer to Official Notification
- Pay/Salary: See Official Notification
- Application Fee: See Official Notification
- Selection Process: See Official Notification

No numerical or factual value is fabricated.

## Slide completeness
A slide should never be left incomplete simply because source extraction missed a field.
Long content should be compressed to fit; unavailable content should use a concise fallback.

## CTA handling
Generic presentation CTAs such as "APPLY NOW" are not treated as factual claims.
