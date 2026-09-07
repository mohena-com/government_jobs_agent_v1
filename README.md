# SarkariResult Latest Jobs Text Reports

The crawler reads future listings from `https://www.sarkariresult.com/latestjob/`, fetches each detail page, and writes plain-text reports.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py --max-jobs 3
```

Reports are written under `reports/`:

- `SarkariResult_LatestJobs_<date>_Summary.txt`
- `jobs/<number>_<title>_<date>.txt`

Useful options are `--max-jobs`, `--only`, `--published-today`, and `--reports-dir`.
