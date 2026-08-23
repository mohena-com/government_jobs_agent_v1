# SarkariResult Latest Jobs Agent V1.2

## Scope

V1.2 intentionally monitors only:

https://www.sarkariresult.com/latestjob/

It filters listings whose last application date is in the future, follows each listing
to its individual SarkariResult detail page, extracts structured recruitment information,
and generates a clean Word report.

## Major change from V1.1

The report generator no longer inserts the complete raw SarkariResult page into the
Word document. This removes repeated navigation, social links, footer content, repeated
tables, and huge page counts.

The report is generated from structured fields:

- Organisation
- Post / recruitment title
- Advertisement number
- Published / updated date
- Application start/end
- Total vacancies
- Age limit
- Important dates
- Application fee
- Vacancy table
- Eligibility
- Selection process
- Pay / salary
- How to apply
- External notification/application links
- SarkariResult source link

Raw source text remains available internally for debugging but is not included in the
user-facing DOCX.

## Test

Run:

```bash
python -m pytest -q
```

Then:

```bash
python main.py --max-jobs 3
```

For a focused RCFL test, if supported by your current CLI:

```bash
python main.py --only RCFL --max-jobs 1
```

## Next planned layer

After V1.2 formatting and structured extraction are validated, the next enhancement
should follow the official notification/application links and resolve actual official
PDFs and application portals.


## V1.3 report cleanup

The report generator now removes social/navigation artefacts such as:
Telegram, Join Us, WhatsApp, Instagram, Follow, X and image placeholders.

Important Dates and Application Fee are rendered compactly. Source pairs such
as `Pay Exam Fee Last Date :` followed by `24/08/2026` are rendered as
`Pay Exam Fee Last Date: 24/08/2026` on one line.

Long eligibility/instruction content remains readable as bullets.


## V1.4 — Split Report Output

The Word output is now split into:

1. A summary/index document:
   `reports/SarkariResult_LatestJobs_YYYY-MM-DD_Summary.docx`

2. One detailed Word document per recruitment:
   `reports/jobs/01_....docx`
   `reports/jobs/02_....docx`
   etc.

The summary contains only the title, source, and recruitment index table.
Each job detail file contains the complete structured recruitment details.

This avoids a large combined document and makes it easier to distribute or
archive individual recruitment notices.
