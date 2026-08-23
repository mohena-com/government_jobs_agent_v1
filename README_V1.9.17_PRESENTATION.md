# V1.9.17 Presentation Layer

V1.9.17 is the creative/presentation upgrade for the government-jobs Instagram
pipeline. It is intentionally separate from fact extraction and official PDF
verification.

## Six-slide visual contract

| Slide | Role | Visual treatment |
|---|---|---|
| 1 | title | Recruitment hero, vacancy/deadline badges, CTA |
| 2 | vacancies | Poster-style vacancy table |
| 3 | eligibility | Post-specific qualification cards |
| 4 | age_pay_fee | Three stat cards + important notes |
| 5 | dates_selection | Timeline + selection panel |
| 6 | apply_links | Three-step CTA + QR link cards |

## Important design rule

Qwen decides the wording; the Python renderer decides the visual design. The
renderer also reads verified/locked facts directly for vacancy, date, age, pay,
fee and post-specific qualification content. This reduces the chance that a
small language model's prose formatting damages high-risk numbers.

## URL handling

Raw URLs are not rendered. Official links are displayed as:

- OFFICIAL NOTIFICATION
- OFFICIAL APPLICATION
- OFFICIAL SOURCE

with the verified domain and a QR code. The underlying URL remains in the audit
JSON and structured slide metadata.

## QA text handling

The renderer strips internal pipeline/debug terms before artwork is produced.
This includes PASS/FAIL, quality gate, reconciliation, extraction repairs,
parsed/authoritative vacancy labels, locked-facts language, PDF extraction
notes and similar implementation details.

## V1.9.18 daily generation

Run the complete daily workflow with:

```bash
./scripts/generate_today_instagram.sh
```

Optional overrides:

```bash
PYTHON_BIN=python3.1 OLLAMA_HOST=http://webmaster-ai.local:11434 OLLAMA_MODEL=qwen3:8b ./scripts/generate_today_instagram.sh
```

Outputs:
- `social/today_jobs.json` — today's unique, not-yesterday-used selection
- `social/qwen_today_<YYYY-MM-DD>/` — Qwen plans
- `social/rendered_today_<YYYY-MM-DD>/` — rendered Instagram PNGs
- `social/agent_usage_history.jsonl` — successful presentation history
- `social/daily_generation_<YYYY-MM-DD>.json` — run summary
