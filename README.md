# Government Jobs Agent V1

Python MVP for daily Indian government recruitment monitoring.

Pipeline: Employment News + UPSC + SSC + NCS discovery -> PDF download -> PyMuPDF extraction -> optional OpenAI structured extraction -> official-domain verification -> SQLite deduplication -> clickable DOCX report.

## Run
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py

Report-only: `python main.py --report-only`
Tests: `pytest -q`

## Schedule
GitHub Actions runs at 23:30 UTC = 05:00 IST. GitHub may delay scheduled jobs slightly.

## V1 note
Google Drive/email notifications are intentionally left as the next integration layer. The core agent is local/cloud-runner friendly and produces a DOCX artifact.
"# government_jobs_agent_v1" 
