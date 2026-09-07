import argparse
from pathlib import Path

from src.sarkariresult.pipeline import crawl
from src.report.report_generator_txt import make_report

p = argparse.ArgumentParser(description="SarkariResult latest jobs crawler and text report generator")
p.add_argument("--reports-dir", default="reports", help="External directory for generated reports")
p.add_argument("--max-jobs", type=int, default=None)
p.add_argument("--only", default=None)
p.add_argument("--published-today", action="store_true", help="Crawl only jobs whose Published/Updated date is today (IST)")

args = p.parse_args()

from datetime import datetime
from zoneinfo import ZoneInfo
published_on = datetime.now(ZoneInfo("Asia/Kolkata")).date() if args.published_today else None
today, results = crawl(max_jobs=args.max_jobs, only=args.only, published_on=published_on)
base_report = Path(args.reports_dir) / f"SarkariResult_LatestJobs_{today.isoformat()}"
summary_path, job_files = make_report(today, results, base_report)

print("Source: https://www.sarkariresult.com/latestjob/")
print(f"Date (IST): {today}")
print(f"Future listings crawled: {len(results)}")
print(f"Summary Report: {summary_path}")
print(f"Job Detail Reports: {len(job_files)}")
