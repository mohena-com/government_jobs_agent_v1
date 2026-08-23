
import argparse
from pathlib import Path

from src.sarkariresult.pipeline import crawl
from src.report.docx import make_report


p = argparse.ArgumentParser(
    description=(
        "SarkariResult Latest Jobs only — "
        "future-date discovery and detail-page crawl"
    )
)

p.add_argument(
    "--max-jobs",
    type=int,
    default=None,
)

p.add_argument(
    "--only",
    default=None,
    help="Optional comma-separated title keywords for testing",
)

args = p.parse_args()


today, results = crawl(
    max_jobs=args.max_jobs,
    only=args.only,
)


base_report = (
    Path("reports")
    / f"SarkariResult_LatestJobs_{today.isoformat()}.docx"
)


summary_path, job_files = make_report(
    today,
    results,
    base_report,
)


print(
    "Source: "
    "https://www.sarkariresult.com/latestjob/"
)

print(
    f"Date (IST): {today}"
)

print(
    f"Future listings crawled: {len(results)}"
)

print(
    f"Summary Report: {summary_path}"
)

print(
    f"Job Detail Reports: {len(job_files)}"
)

for path in job_files:
    print(
        f"  JOB REPORT: {path}"
    )


for r in results:

    notification = (
        r["notification_links"][0]["url"]
        if r.get("notification_links")
        else "NOT FOUND"
    )

    application = (
        r["application_links"][0]["url"]
        if r.get("application_links")
        else "NOT FOUND"
    )

    print(
        "\nJOB:",
        r["listing"]["title"],
    )

    print(
        "DETAIL:",
        r["detail_url"],
    )

    print(
        "OFFICIAL NOTIFICATION:",
        notification,
    )

    print(
        "OFFICIAL APPLICATION:",
        application,
    )

    print(
        "DETAIL OK:",
        r["detail_ok"],
    )
