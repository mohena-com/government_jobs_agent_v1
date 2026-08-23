# V1.9.18 — Daily job generation + compact Instagram presentation

## Daily automation
- Added `scripts/generate_today_instagram.sh` for a one-command daily crawl, deduplication, official verification, Qwen generation, QA and rendering workflow.
- Uses IST for the run date.
- Selects jobs whose Published/Updated date is today.
- Deduplicates today's listings using title, detail URL and advertisement number.
- Excludes jobs already successfully used by the agent yesterday.
- Bootstraps yesterday's exclusion set from prior Qwen outputs when history is not yet populated.
- Continues processing after an individual job fails and writes `social/daily_generation_<date>.json`.
- Successful presentations are recorded in `social/agent_usage_history.jsonl`.
- `PYTHON_BIN`, `OLLAMA_HOST`, `OLLAMA_MODEL`, and `CRAWL_MAX_JOBS` are configurable environment variables.

## Presentation content
- Slide 3 qualification text is condensed for Instagram display only.
- Every verified post remains represented, but long legal/notification boilerplate is removed from the artwork.
- Slide 4 extracts concise age, pay and fee values instead of rendering advertisement identifiers or long source text.
- The complete verified facts remain unchanged in the underlying job/fact bundle.
- Qwen is explicitly instructed to create short, card-friendly content for slides 3 and 4.

## Safety and QA
- Official PDF verification remains mandatory when `--verify-official` is used.
- Source and slide quality gates remain enforced.
- No manual JSON override is introduced.
- URLs remain structured metadata and are rendered as user-friendly labels/QR codes rather than long raw URLs.
