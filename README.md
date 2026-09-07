# SarkariResult Latest Jobs Text Reports

The crawler reads future listings from `https://www.sarkariresult.com/latestjob/`, fetches each detail page, and writes plain-text reports.

## Run

```bash
python3.1 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3.1 main.py --max-jobs 3
```

Reports are written under `../reports/` by default:

- `SarkariResult_LatestJobs_<date>_Summary.txt`
- `jobs/<number>_<title>_<date>.txt`

Useful options are `--max-jobs`, `--only`, `--published-today`, and `--reports-dir`.

Default runtime settings are in `app_config.yaml`. Command-line options override
the matching YAML values. Install dependencies with `pip install -r requirements.txt`.

Successfully scraped listing URLs are stored separately in `../data/scraped_jobs.sqlite3`.
Listings already in that database are skipped on later runs; failed detail-page
requests are not recorded and will be retried. Deleting or archiving files under
`../reports/jobs/` does not remove this scrape history.
