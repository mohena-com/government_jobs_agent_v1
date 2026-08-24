# V1.9.33 — Semantic Date Binding & Cross-Check

## Purpose
Prevent incorrect application dates from reaching Qwen or the rendered Instagram slides.

## Changes
- Recover application start/end dates from semantic DOCX evidence, including:
  - `APPLICATION DEADLINE`
  - `HOW TO APPLY` date ranges
  - `IMPORTANT DATES`
  - explicit application start/end labels
- Keep fee-payment, exam, notification and admit-card dates separate from the application window.
- Normalize supported date formats to unambiguous display values such as `28 July 2026`.
- Cross-check extracted application dates against the source DOCX before building the Qwen presentation payload.
- Withhold application dates that fail the source-document cross-check; use the controlled presentation fallback instead of inventing dates.
- Add slide-level semantic date QA: dates used near application/last-date language must match locked `application_start` / `application_end` facts.
- Tell Qwen explicitly that application dates are semantic locked fields and must not be substituted with unrelated dates.
- Preserve V1.9.32 resilient fallback behavior for genuinely missing fields.

## Example fixed case
For Patna High Court Ex-Cadre Assistant Group C Recruitment 2026:
- Application start: `28 July 2026`
- Application end: `27 August 2026`
- Fee-payment last date: `30 August 2026` (kept separate)

A generated `27 July 2007` application deadline now fails semantic presentation QA and is repaired/rejected rather than rendered.
