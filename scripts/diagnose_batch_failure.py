import json
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "social/qwen_test")
for p in sorted(root.glob("job_*/qwen_instagram_plans.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    for j in d.get("jobs", []):
        print(f"{p.parent.name}: action={j.get('action')} ready={j.get('presentation_ready')}")
        print("  source_gate:", (j.get("quality_gate") or {}).get("status"))
        print("  source_errors:", (j.get("quality_gate") or {}).get("errors"))
        print("  slide_gate:", (j.get("slide_quality_gate") or {}).get("status"))
        print("  slide_errors:", (j.get("slide_quality_gate") or {}).get("errors"))
        print("  warnings:", j.get("validation_warnings"))
