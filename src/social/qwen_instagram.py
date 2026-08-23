from __future__ import annotations

import json
from pathlib import Path

from src.docx.reader import read_docx, to_locked_facts
from src.llm.ollama_client import OllamaClient
from src.llm.validator import validate_slide_plan


def generate_from_docx(
    docx_path: str | Path,
    output_dir: str | Path,
    *,
    host: str = "http://localhost:11434",
    model: str = "qwen3:8b",
    slide_count: int = 6,
    job_index: int | None = None,
):
    parsed = read_docx(docx_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    client = OllamaClient(host=host, model=model)

    generated = []
    selected = list(enumerate(parsed["jobs"], 1))
    if job_index is not None:
        selected = [(i, j) for i, j in selected if i == job_index]
        if not selected:
            raise IndexError(f"job_index {job_index} is outside 1..{parsed["job_count"]}")

    for idx, job in selected:
        facts = to_locked_facts(job)
        plan = client.generate_slide_plan(facts, slide_count=slide_count)
        warnings = validate_slide_plan(plan, facts)

        record = {
            "job_index": idx,
            "source_job": job,
            "locked_facts": facts,
            "slide_plan": plan,
            "validation_warnings": warnings,
        }
        generated.append(record)

        title = job.get("title") or f"job_{idx}"
        safe = "".join(c if c.isalnum() else "_" for c in title).strip("_")[:80]
        (output_dir / f"{idx:02d}_{safe}_slide_plan.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    summary = {
        "source_docx": str(docx_path),
        "model": model,
        "ollama_host": host,
        "job_count": len(generated),
        "slide_count": slide_count,
        "jobs": generated,
    }
    summary_path = output_dir / "qwen_instagram_plans.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary_path, generated
