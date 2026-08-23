# V1.9.3 — Canonical Reconciled Facts + Placeholder Gate

Changes from V1.9.2:

1. `official_verification.post_vacancies` is now the canonical reconciled vacancy list for downstream consumers.
2. `raw_post_vacancies` is retained only for audit/debugging.
3. `apply_to_job()` exports canonical `post_vacancies`, `raw_post_vacancies`, and `derived_vacancy_sum`.
4. Officially verified empty fields are allowed to overwrite contaminated DOCX values. This prevents generic `selection_process` boilerplate from leaking into Qwen facts.
5. The quality gate validates the canonical vacancy sum against both `total_vacancies` and `authoritative_expected_total` when available.
6. Generic selection/eligibility boilerplate such as `Read the notification...` and `post information, selection procedure...` is rejected.
7. Added regression tests for canonical vacancy reconciliation and selection placeholder rejection.

Test result: 23 passed.
