# SarkariResult Latest Jobs — Focused V1

This version intentionally contains **only one source**:

https://www.sarkariresult.com/latestjob/

UPSC, SSC, RRB, Employment News, NCS and other sources are NOT included.

## Current scope

1. Open SarkariResult Latest Jobs.
2. Discover job listing links.
3. Parse each listing's Last Date.
4. Keep only listings with Last Date strictly later than today's date in IST.
5. Follow each retained listing to its individual SarkariResult detail URL.
6. Extract the detail page's visible text, HTML tables and relevant hyperlinks.
7. Identify candidate Notification / Apply Online / Official Website links.
8. Classify links as SarkariResult, likely official government/institution, or third-party.
9. Generate a report showing the actual detail-page content and discovered links.

**No enrichment of qualification, age, salary, vacancies, etc. is attempted yet.**
That is intentional. First we prove that the crawler reliably goes from the
latest-job index to every individual job-detail page.

## Run

```bash
python3.1 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3.1 main.py --max-jobs 3
```

For targeted debugging:

```bash
python3.1 main.py --only "RCFL,AAI,UPSC"
```

The `--only` option is only a test filter; UPSC is NOT a separate source.

## Output

```text
reports/SarkariResult_LatestJobs_YYYY-MM-DD.docx
```

The report should contain, per job:

- SarkariResult listing title
- Last date
- SarkariResult detail-page URL
- full visible detail-page content
- tables detected on the detail page
- discovered links
- candidate official notification
- candidate official application

If an official link cannot be found, it says `Not found`; it is never invented.

## Next phase

Only after this source traversal is working reliably will we add structured
field extraction and then official-notification crawling.


Without Instagram:

python3.1 main.py --max-jobs 3

With Instagram slides:

python3.1 main.py --max-jobs 3 --instagram