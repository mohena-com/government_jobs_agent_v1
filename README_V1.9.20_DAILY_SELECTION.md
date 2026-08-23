# V1.9.20 Daily Selection

The daily batch currently ignores duplicate/history suppression and selects all jobs with a future closing date.

Run:

```bash
PYTHON_BIN=python3.1 \
OLLAMA_HOST=http://webmaster-ai.local:11434 \
OLLAMA_MODEL=qwen3:8b \
./scripts/generate_today_instagram.sh
```
