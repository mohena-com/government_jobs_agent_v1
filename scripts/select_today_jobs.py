#!/usr/bin/env python3
"""Select unique jobs published today and exclude jobs already used by the agent yesterday."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from src.docx.reader import read_docx


def norm(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def parse_date(value: str):
    text = str(value or "").strip().split("|")[0].strip()
    for fmt in ("%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y"):
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


def job_keys(job: dict):
    title = norm(job.get("title"))
    source = job.get("source") or {}
    url = str(source.get("detail_page_text") or "").strip().lower()
    advt = norm((job.get("fields") or {}).get("advertisement_number"))
    return {k for k in (title, url, advt) if k}


def read_history(history_path: Path, yesterday: date):
    used = set()
    if history_path.exists():
        for line in history_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("used_date") == yesterday.isoformat():
                used.update(row.get("keys") or [])

    # Bootstrap yesterday's history from existing Qwen outputs. This means the
    # first run does not require a manual migration of old agent outputs.
    for p in Path("social").glob("qwen*/qwen_instagram_plans.json"):
        try:
            if datetime.fromtimestamp(p.stat().st_mtime).date() != yesterday:
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for job in data.get("jobs", []):
            source = job.get("source_job") or {}
            used.update(job_keys(source))
    return used


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", required=True)
    ap.add_argument("--reports-dir", default="reports/jobs")
    ap.add_argument("--history", default="social/agent_usage_history.jsonl")
    ap.add_argument("--output", default="social/today_jobs.json")
    args = ap.parse_args()

    today = date.fromisoformat(args.today)
    yesterday = today - timedelta(days=1)
    used_yesterday = read_history(Path(args.history), yesterday)

    selected = []
    seen = set()
    for path in sorted(Path(args.reports_dir).glob(f"*_{today.isoformat()}.docx")):
        try:
            parsed = read_docx(path)
        except Exception as exc:
            print(f"WARN: cannot read {path}: {exc}")
            continue
        for job in parsed.get("jobs", []):
            published = parse_date((job.get("fields") or {}).get("published_date"))
            if published != today:
                continue
            keys = job_keys(job)
            identity = next(iter(sorted(keys)), str(path))
            if keys & used_yesterday:
                print(f"SKIP yesterday-used: {job.get('title', path.name)}")
                continue
            if keys & seen:
                print(f"SKIP duplicate-today: {job.get('title', path.name)}")
                continue
            seen.update(keys)
            selected.append({
                "docx": str(path),
                "title": job.get("title", ""),
                "published_date": today.isoformat(),
                "keys": sorted(keys),
            })

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "today": today.isoformat(),
        "yesterday": yesterday.isoformat(),
        "selected_count": len(selected),
        "jobs": selected,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Selected today's unique jobs: {len(selected)}")
    for row in selected:
        print(f"  {row['docx']} :: {row['title']}")


if __name__ == "__main__":
    main()
