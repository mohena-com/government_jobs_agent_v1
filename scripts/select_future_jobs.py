#!/usr/bin/env python3
"""V1.9.23 compatibility selector: strictly future application/last date, no history."""
from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
import json, re, sys
try:
    from src.docx.reader import read_docx
except Exception:
    read_docx = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def get_last_date(record):
    value = (record or {}).get("application_end") or (record or {}).get("last_date") or ""
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})", text)
    if m:
        try:
            return datetime.strptime(m.group(0), "%d %B %Y").date()
        except ValueError:
            pass
    return date.min

def select_future(records, today=None):
    today = today or date.today()
    return [r for r in records if get_last_date(r) > today]

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", default="social/today_jobs.json")
    ap.add_argument("--output", default="social/today_jobs_selected.json")
    args=ap.parse_args()
    data=json.loads(Path(args.input).read_text(encoding="utf-8"))
    records=data.get("jobs", data if isinstance(data,list) else data.get("records",[]))
    selected=select_future(records)
    out={"version":"1.9.23","selection_rule":"application/last date > today","duplicate_filtering":False,"selected_count":len(selected),"jobs":selected}
    Path(args.output).write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"Future-deadline jobs selected: {len(selected)}")

if __name__=="__main__":
    main()
