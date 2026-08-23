# V1.9.10 — Verified Fact Bundle → Qwen Pipeline Fix

## Purpose

V1.9.10 fixes the final V1.9.9 pipeline blocker discovered during the RVUNL pilot.

The official verifier could correctly reconcile the RVUNL facts, but its `How to Apply`
section extractor could land on the preceding company/area-of-operation table. That
contaminated optional field then caused the quality gate to fail even though the
required facts and official verification had passed.

## Fix

- Officially extracted `how_to_apply` is now sanitised before entering `locked_facts`.
- Known RVUNL company/area boilerplate is cleared rather than propagated downstream.
- A verification note is retained when the field is intentionally cleared.
- Qwen continues to receive only the frozen `locked_facts` bundle.
- No manual JSON override is used.
- The hard quality gate remains active for required facts and canonical post eligibility.

## Expected RVUNL state

```text
Official verification      PASS
Combined vacancies         2005
Application dates          05 Aug 2026 → 25 Aug 2026
Canonical posts            5
Post eligibility           verified
Contaminated how_to_apply  cleared
Quality gate               PASS
Qwen                       allowed
```

## Test

```bash
PYTHONPATH=. pytest -q
```

The V1.9.10 regression suite includes the contaminated `How to Apply` case.
