#!/usr/bin/env python3
import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "social/qwen_test")

if not root.exists():
    print(f"ERROR: {root} does not exist")
    raise SystemExit(1)

plans = sorted(root.glob("job_*/qwen_instagram_plans.json"))

if not plans:
    print(f"No Qwen JSON files found under {root}")
    raise SystemExit(1)

for p in plans:
    print("\n" + "=" * 70)
    print(p)

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("JSON ERROR:", e)
        continue

    for job in data.get("jobs", []):
        source = job.get("quality_gate") or {}
        slide = job.get("slide_quality_gate") or {}

        print("ACTION:", job.get("action"))
        print("PRESENTATION READY:", job.get("presentation_ready"))
        print("SOURCE GATE:", source.get("status"))
        print("SOURCE ERRORS:", source.get("errors", []))
        print("SLIDE GATE:", slide.get("status"))
        print("SLIDE ERRORS:", slide.get("errors", []))
        print("SLIDE WARNINGS:", slide.get("warnings", []))
        print("VALIDATION WARNINGS:", job.get("validation_warnings", []))
        print("PRESENTATION FALLBACKS:", job.get("presentation_fallbacks", {}))
        print("SLIDES:", len((job.get("slide_plan") or {}).get("slides", [])))
