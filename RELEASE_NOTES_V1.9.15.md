# V1.9.15 — Automatic Presentation Repair

V1.9.15 fixes the V1.9.14 failure mode where Qwen could return six slides but duplicate the vacancies slide and omit eligibility, age/pay/fee, selection, or apply/links content.

## Changes
- Fixed six-slide contract is now enforced as a gate error, not a warning.
- Qwen gets a deterministic second repair pass when the first slide plan fails.
- Repair receives the exact gate errors and the locked verified facts.
- No manual JSON override and no fact mutation are performed.
- A successful repair is recorded as `QWEN_GENERATED_AFTER_AUTOMATIC_REPAIR_AND_SLIDE_GATE_PASSED`.
- Audit JSON records both attempts and their gate results.
- Presentation-ready JSON remains free of audit metadata.
- The existing source/official verification gates remain unchanged.
