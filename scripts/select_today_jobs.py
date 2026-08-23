#!/usr/bin/env python3
"""
V1.9.22 daily selector.

Important design decision:
The crawler is the single authority for "future last date" selection.
This script does NOT re-parse dates from the generated DOCX files.

It reads the crawler's machine-readable output (today_jobs.json) when available.
If the crawler output is already a future-deadline list, every record is selected.
Duplicate/history filtering is intentionally OFF in V1.9.22.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_records(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Selection input not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for key in ("jobs", "records", "listings", "selected_jobs"):
            if isinstance(data.get(key), list):
                return data[key]
        if isinstance(data.get("job_details"), list):
            return data["job_details"]
    if isinstance(data, list):
        return data
    raise ValueError(f"Unsupported selection JSON structure: {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="social/today_jobs.json")
    ap.add_argument("--output", default="social/today_jobs_selected.json")
    args = ap.parse_args()

    src = Path(args.input)
    records = load_records(src)

    # V1.9.22: crawler already applied LAST DATE > TODAY.
    selected = []
    for i, r in enumerate(records, 1):
        if not isinstance(r, dict):
            continue
        x = dict(r)
        x.setdefault("daily_selection_reason", "crawler_selected_future_last_date")
        x.setdefault("daily_duplicate_filtering", False)
        selected.append(x)

    out = {
        "version": "1.9.22",
        "selection_rule": "crawler-selected listings whose last/application date is strictly after today",
        "duplicate_filtering": False,
        "input": str(src),
        "selected_count": len(selected),
        "jobs": selected,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps(out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Future-deadline jobs selected: {len(selected)}")


if __name__ == "__main__":
    main()
