import argparse
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import load_config
from src.sarkariresult.pipeline import crawl
from src.report.report_generator_txt import make_report

config = load_config()
p = argparse.ArgumentParser(description="SarkariResult latest jobs crawler and text report generator")
p.add_argument("--reports-dir", default=None, help="External directory for generated reports")
p.add_argument("--max-jobs", type=int, default=None)
p.add_argument("--only", default=None)
p.add_argument("--published-today", action="store_true", help="Crawl only jobs whose Published/Updated date is today (IST)")

args = p.parse_args()

reports_dir = args.reports_dir or config.get("reports_dir", "../reports")
max_jobs = args.max_jobs if args.max_jobs is not None else config.get("max_jobs")
only = args.only if args.only is not None else config.get("only")
published_today = args.published_today or config.get("published_today", False)
timezone = config.get("timezone", "Asia/Kolkata")
published_on = datetime.now(ZoneInfo(timezone)).date() if published_today else None
today, results = crawl(
	max_jobs=max_jobs,
	only=only,
	published_on=published_on,
	config=config,
)
base_report = Path(reports_dir) / f"SarkariResult_LatestJobs_{today.isoformat()}"
summary_path, job_files = make_report(today, results, base_report)

print("Source: https://www.sarkariresult.com/latestjob/")
print(f"Date (IST): {today}")
print(f"Future listings crawled: {len(results)}")
print(f"Summary Report: {summary_path}")
print(f"Job Detail Reports: {len(job_files)}")
