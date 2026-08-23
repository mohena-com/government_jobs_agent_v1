# V1.9.20 — Future Last-Date Batch Selection

## Change requested
Duplicate/history filtering has been removed for now.

The daily Instagram batch now selects **every crawled job whose application/last date is strictly after today**.

## Daily command

```bash
PYTHON_BIN=python3.1 \
OLLAMA_HOST=http://webmaster-ai.local:11434 \
OLLAMA_MODEL=qwen3:8b \
./scripts/generate_today_instagram.sh
```

## Selection rule

- `last/application date > today` → selected
- `last/application date == today` → excluded
- `last/application date < today` → excluded
- missing/unparseable last date → excluded
- duplicate/history filtering → **OFF**

The crawler already filters SarkariResult latest-job listings to strictly future `last_date` values, and the selector applies the same rule to the generated DOCX records as a second safety check.

## Output

`social/today_jobs.json` records the selected jobs and their last dates.
`social/daily_generation_YYYY-MM-DD.json` records batch results.

No usage-history file is consulted or updated in this version.
