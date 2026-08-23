# UPSC Deep Recruitment Agent — Pilot V1

This pilot is deliberately limited to UPSC.

It does NOT treat the UPSC recruitment listing as the recruitment data.
It follows:

UPSC Recruitment Advertisements -> official advertisement PDF -> page-level
document parsing -> recruitment-section segmentation -> structured extraction
-> validation -> provenance -> DOCX report.

## Pilot advertisements

- Advertisement No. 09/2026
  https://www.upsc.gov.in/sites/default/files/AdvtNo-09-2026-Engl-240726.pdf
- Advertisement No. 51/2026 (Special)
  https://www.upsc.gov.in/sites/default/files/AdvtNo-51-2026-Special-Engl-240726.pdf

The discovery page is:
https://www.upsc.gov.in/recruitment/recruitment-advertisement

## Design principles

1. Official UPSC PDF is the authority.
2. Every extracted field should have page provenance.
3. No value is invented when absent.
4. Vacancy counts are post-specific, not just advertisement-level.
5. Tables are parsed separately from running text.
6. Recruitment sections are segmented before LLM extraction.
7. Deterministic extraction runs first; AI is a validator/enricher.
8. Corrigenda can supersede original dates and instructions.
9. Third-party sites are never the final authority.

## Install

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

## Run

python main.py --advt 09
python main.py --advt 51

The first run downloads the official PDF, parses it, extracts recruitment
sections, validates the result and creates a DOCX report.

If OPENAI_API_KEY is not configured, deterministic extraction still runs.
AI validation is optional.

## Why this is different from the previous V1

The old version scraped anchor text from a landing page.
This version treats the landing page only as a discovery index and performs
deep document processing on the actual UPSC advertisement PDF.

## SarkariResult discovery added to the UPSC agent

The project now includes SarkariResult as a **discovery layer**, while retaining the UPSC deep-document engine.

### Future-date filtering

`https://www.sarkariresult.com/latestjob/` is scanned and only listings with a parseable **Last Date strictly later than today's date in `Asia/Kolkata`** are retained. Listings with no parseable last date are excluded rather than guessed.

For example, on 23 August 2026, 24 August 2026 and later are future dates; 23 August and earlier are excluded.

### Detail-page crawl

Use:

```bash
python main.py --source sarkariresult --deep-sarkariresult
```

The agent follows each retained SarkariResult listing and collects candidate:
- official website links
- application links
- notification/advertisement links
- PDF links

The SarkariResult page remains a discovery source. A destination is only a candidate official source when its domain matches the configured government/institution rules. It is not treated as authoritative simply because SarkariResult links to it.

### Combined run

```bash
python main.py --source both --advt 09 --deep-sarkariresult
```

This runs the existing UPSC deep extractor and the SarkariResult future-job discovery in the same project.
