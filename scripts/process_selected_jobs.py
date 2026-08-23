#!/usr/bin/env python3
"""
V1.9.22 end-to-end per-job processor.

Consumes the crawler-selected job records and their generated DOCX files.
Does NOT perform another date filter. Every selected crawler record is processed.

The script is deliberately failure-isolated: one job failure does not abort the batch.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run(cmd):
    print("$", " ".join(map(str, cmd)))
    return subprocess.run(cmd, cwd=ROOT, check=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="social/today_jobs_selected.json")
    ap.add_argument("--qwen-output", required=True)
    ap.add_argument("--ollama-host", required=True)
    ap.add_argument("--ollama-model", required=True)
    ap.add_argument("--slide-count", type=int, default=6)
    ap.add_argument("--verify-official", action="store_true")
    ap.add_argument("--render-output")
    args = ap.parse_args()

    d = json.loads(Path(args.input).read_text(encoding="utf-8"))
    jobs = d.get("jobs", [])
    today = __import__("datetime").date.today().isoformat()

    render_root = Path(args.render_output or f"social/rendered_today_{today}")
    qroot = Path(args.qwen_output)
    render_root.mkdir(parents=True, exist_ok=True)
    qroot.mkdir(parents=True, exist_ok=True)

    results = []
    for n, job in enumerate(jobs, 1):
        docx = job.get("docx") or job.get("detail_docx") or job.get("docx_path")
        if not docx:
            # Try common crawler convention by job index.
            idx = job.get("job_index") or n
            candidates = sorted(Path("reports/jobs").glob(f"{int(idx):02d}_*.docx"))
            docx = str(candidates[-1]) if candidates else None

        if not docx or not Path(docx).exists():
            results.append({
                "job_index": job.get("job_index", n),
                "status": "FAIL",
                "stage": "DOCX",
                "error": f"Job detail DOCX not found: {docx}",
            })
            print(f"[{n}/{len(jobs)}] FAIL DOCX:", docx)
            continue

        idx = int(job.get("job_index") or n)
        qdir = qroot / f"{idx:02d}"
        rdir = render_root / f"{idx:02d}"
        qdir.mkdir(parents=True, exist_ok=True)
        rdir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable, "main.py",
            "--docx", str(docx),
            "--qwen",
            "--job-index", str(idx),
            "--ollama-host", args.ollama_host,
            "--ollama-model", args.ollama_model,
            "--slide-count", str(args.slide_count),
            "--qwen-output", str(qdir),
        ]
        if args.verify_official:
            cmd.append("--verify-official")

        rc = run(cmd)
        if rc.returncode != 0:
            results.append({
                "job_index": idx,
                "status": "FAIL",
                "stage": "QWEN_OR_VERIFY",
                "docx": str(docx),
                "returncode": rc.returncode,
            })
            print(f"[{n}/{len(jobs)}] FAIL QWEN/VERIFY job {idx}")
            continue

        plan = qdir / "qwen_instagram_plans.json"
        if not plan.exists():
            results.append({
                "job_index": idx,
                "status": "FAIL",
                "stage": "QWEN_OUTPUT",
                "docx": str(docx),
                "error": f"Missing {plan}",
            })
            continue

        render_cmd = [
            sys.executable, "main.py",
            "--render-qwen", str(plan),
            "--render-output", str(rdir),
            "--job-index", "1",
        ]
        rr = run(render_cmd)
        if rr.returncode != 0:
            results.append({
                "job_index": idx,
                "status": "FAIL",
                "stage": "RENDER",
                "docx": str(docx),
                "returncode": rr.returncode,
            })
            print(f"[{n}/{len(jobs)}] FAIL RENDER job {idx}")
            continue

        pngs = list(rdir.rglob("*.png"))
        results.append({
            "job_index": idx,
            "status": "PASS",
            "docx": str(docx),
            "qwen_plan": str(plan),
            "render_dir": str(rdir),
            "slides_rendered": len(pngs),
        })
        print(f"[{n}/{len(jobs)}] PASS job {idx} | {len(pngs)} PNGs")

    report = {
        "version": "1.9.22",
        "selection_rule": d.get("selection_rule"),
        "duplicate_filtering": False,
        "selected_jobs": len(jobs),
        "successful_jobs": sum(x["status"] == "PASS" for x in results),
        "failed_jobs": sum(x["status"] == "FAIL" for x in results),
        "slides_rendered": sum(x.get("slides_rendered", 0) for x in results),
        "results": results,
    }
    rp = Path(f"social/daily_generation_{today}.json")
    rp.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "selected_jobs": report["selected_jobs"],
        "successful_jobs": report["successful_jobs"],
        "failed_jobs": report["failed_jobs"],
        "slides_rendered": report["slides_rendered"],
        "report": str(rp),
    }, indent=2))


if __name__ == "__main__":
    main()
