# V1.9.19 — Daily Batch Reliability Fix

## Fixes

- Fixed `scripts/select_today_jobs.py` when executed directly from the repository root: it now adds the workspace root to `sys.path`, eliminating `ModuleNotFoundError: No module named 'src'`.
- Fixed `--published-today` discovery so `--max-jobs` no longer truncates the latest-job list before publication-date filtering. The crawler now filters by publication/update date first and applies the maximum to matching jobs.
- Hardened SarkariResult `Post Date / Update` extraction to support both same-line and two-line page layouts.
- Kept yesterday-used and duplicate-today selection logic unchanged.

## Intended command

```bash
PYTHON_BIN=python3.1 \\
OLLAMA_HOST=http://webmaster-ai.local:11434 \\
OLLAMA_MODEL=qwen3:8b \\
./scripts/generate_today_instagram.sh
```
