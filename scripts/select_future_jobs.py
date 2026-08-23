#!/usr/bin/env python3
"""Select every crawled recruitment whose last/application date is still in the future.

V1.9.20 deliberately does NOT perform duplicate suppression or history checks.
The daily batch is driven only by the future closing date.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.docx.reader import read_docx


def parse_date(value: str):
    text = str(value or "").strip()
    if "|" in text:
        text = text.split("|", 1)[0].strip()
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})", text)
    if m:
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(m.group(0), fmt).date()
            except ValueError:
                pass
    return None


def get_last_date(job: dict):
    listing = job.get("listing") or {}
    candidates = [
        job.get("application_end"),
        listing.get("last_date"),
        (job.get("fields") or {}).get("application_end"),
    ]
    for value in candidates:
        parsed = parse_date(value)
        if parsed:
            return parsed
    return None


def main():
    ap = argparse.ArgumentParser(description="Select all jobs with future application closing dates.")
    ap.add_argument("--today", required=True)
    ap.add_argument("--reports-dir", default="reports/jobs")
    ap.add_argument("--output", default="social/today_jobs.json")
    args = ap.parse_args()

    today = date.fromisoformat(args.today)
    selected = []

    for path in sorted(Path(args.reports_dir).glob(f"*_{today.isoformat()}.docx")):
        try:
            parsed = read_docx(path)
        except Exception as exc:
            print(f"WARN: cannot read {path}: {exc}")
            continue

        for job in parsed.get("jobs", []):
            last_date = get_last_date(job)
            if not last_date or last_date <= today:
                continue

            listing = job.get("listing") or {}
            selected.append({
                "docx": str(path),
                "title": job.get("title") or job.get("post_title") or listing.get("title", ""),
                "published_date": job.get("published_date") or (job.get("fields") or {}).get("published_date", ""),
                "last_date": last_date.isoformat(),
            })

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "today": today.isoformat(),
        "selection_rule": "last/application date is strictly after today",
        "duplicate_filtering": False,
        "selected_count": len(selected),
        "jobs": selected,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Future-deadline jobs selected: {len(selected)}")
    for row in selected:
        print(f"  {row['last_date']} :: {row['docx']} :: {row['title']}")


if __name__ == "__main__":
    main()
