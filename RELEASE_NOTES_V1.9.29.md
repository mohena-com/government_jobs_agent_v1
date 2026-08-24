# V1.9.29 — Verification-to-Generation Decoupling

- Verified/extracted values remain exact.
- Missing/unreadable/contaminated presentation fields are blanked from the Qwen fact payload and exposed through explicit fallbacks.
- Qwen can generate when source verification is partial; source verification remains an audit signal.
- Only direct numerical reconciliation conflicts are generation blockers.
- Six-slide structured contract and V1.9.28 professional design prompt remain intact.
