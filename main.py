import argparse
from pathlib import Path

from src.sarkariresult.pipeline import crawl
from src.report.docx import make_report
from src.social.instagram import generate_instagram_assets
from src.social.qwen_instagram import generate_from_docx
from src.social.qwen_renderer import render_qwen_plan

p = argparse.ArgumentParser(description="SarkariResult crawler + local Qwen Instagram editor")
p.add_argument("--max-jobs", type=int, default=None)
p.add_argument("--only", default=None)
p.add_argument("--instagram", action="store_true")
p.add_argument("--social-dir", default="social/instagram")

# New local-LLM mode.
p.add_argument("--docx", help="Existing recruitment DOCX to read instead of crawling")
p.add_argument("--qwen", action="store_true", help="Send DOCX-derived locked facts to local/LAN Ollama Qwen")
p.add_argument("--ollama-host", default="http://localhost:11434")
p.add_argument("--ollama-model", default="qwen3:8b")
p.add_argument("--slide-count", type=int, default=6)
p.add_argument("--qwen-output", default="social/qwen")
p.add_argument("--job-index", type=int, default=None, help="1-based job number to send to Qwen (useful for testing)")
p.add_argument("--quality-gate-only", action="store_true", help="Extract facts and run the quality gate without calling Qwen")
p.add_argument("--allow-qwen-on-failed-gate", action="store_true", help="Do not block Qwen when the quality gate fails (not recommended)")
p.add_argument("--verify-official", action="store_true", help="Download and verify official notification PDFs before Qwen")
p.add_argument("--render-qwen", help="Render a Qwen JSON plan after it passes the slide-level gate")
p.add_argument("--render-output", default="social/rendered", help="Directory for rendered Qwen Instagram slides")
p.add_argument("--published-today", action="store_true", help="Crawl only jobs whose Published/Updated date is today (IST)")

args = p.parse_args()

if args.render_qwen:
    assets = render_qwen_plan(args.render_qwen, args.render_output, job_index=args.job_index)
    print(f"Rendered Instagram slides: {len(assets)}")
    for asset in assets:
        print(asset)
    raise SystemExit(0)

if args.docx:
    if not args.qwen and not args.quality_gate_only:
        from src.docx.reader import read_docx
        parsed = read_docx(args.docx)
        print(f"DOCX: {args.docx}")
        print(f"Jobs detected: {parsed['job_count']}")
        for i, job in enumerate(parsed["jobs"], 1):
            print(f"  {i:02d}. {job.get('title') or 'Untitled'}")
        raise SystemExit(0)

    summary, records = generate_from_docx(
        args.docx,
        args.qwen_output,
        host=args.ollama_host,
        model=args.ollama_model,
        slide_count=args.slide_count,
        job_index=args.job_index,
        quality_gate_only=args.quality_gate_only,
        fail_on_quality_gate=not args.allow_qwen_on_failed_gate,
        verify_official=args.verify_official,
    )
    print(f"DOCX: {args.docx}")
    print(f"Ollama: {args.ollama_host}")
    print(f"Model: {args.ollama_model}")
    print(f"Jobs processed: {len(records)}")
    print(f"Qwen output: {summary}")
    raise SystemExit(0)

# Existing V1.6 crawler path remains intact.
from datetime import datetime
from zoneinfo import ZoneInfo
published_on = datetime.now(ZoneInfo("Asia/Kolkata")).date() if args.published_today else None
today, results = crawl(max_jobs=args.max_jobs, only=args.only, published_on=published_on)
base_report = Path("reports") / f"SarkariResult_LatestJobs_{today.isoformat()}.docx"
summary_path, job_files = make_report(today, results, base_report)

print("Source: https://www.sarkariresult.com/latestjob/")
print(f"Date (IST): {today}")
print(f"Future listings crawled: {len(results)}")
print(f"Summary Report: {summary_path}")
print(f"Job Detail Reports: {len(job_files)}")

if args.instagram:
    assets = generate_instagram_assets(results, Path(args.social_dir))
    print(f"Instagram carousels generated: {len(assets)}")
