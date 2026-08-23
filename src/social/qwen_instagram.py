from __future__ import annotations

import json
from pathlib import Path

from src.docx.reader import read_docx, to_locked_facts
from src.docx.quality_gate import quality_gate
from src.llm.ollama_client import OllamaClient
from src.llm.validator import validate_slide_plan
from src.llm.slide_quality_gate import slide_quality_gate
from src.llm.presentation_sanitizer import sanitize_slide_plan
from src.verify_official import verify_urls, apply_to_job


def _attach_verified_links(plan: dict, facts: dict) -> dict:
    """Attach verified URLs as structured metadata to the final slide.

    URLs never become slide text. The renderer turns these into human-friendly
    labels and QR codes. This also prevents Qwen from mangling long PDF URLs.
    """
    slides = plan.get("slides") if isinstance(plan, dict) else None
    if not isinstance(slides, list) or not slides:
        return plan
    links = []
    verification_links = (facts.get("official_verification") or {}).get("official_links", [])
    for item in facts.get("official_links") or verification_links:
        if isinstance(item, dict) and item.get("url"):
            label = item.get("label") or "Official Notification"
            links.append({"label": str(label), "url": str(item["url"]).strip()})
    # Include an explicitly verified application URL if present in how_to_apply.
    how = facts.get("how_to_apply")
    if isinstance(how, str):
        import re
        for url in re.findall(r"https?://[^\s)]+", how):
            if url not in {x["url"] for x in links}:
                links.insert(0, {"label": "Apply Online", "url": url.rstrip(".,")})
    if links:
        slides[-1]["links"] = links[:4]
        slides[-1]["link_note"] = "Scan a QR code for the official notification/application link."
    return plan


def generate_from_docx(
    docx_path: str | Path,
    output_dir: str | Path,
    *,
    host: str = "http://localhost:11434",
    model: str = "qwen3:8b",
    slide_count: int = 6,
    job_index: int | None = None,
    quality_gate_only: bool = False,
    fail_on_quality_gate: bool = True,
    verify_official: bool = False,
):
    parsed = read_docx(docx_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = list(enumerate(parsed["jobs"], 1))
    if job_index is not None:
        selected = [(i, j) for i, j in selected if i == job_index]
        if not selected:
            raise IndexError(f"job_index {job_index} is outside 1..{parsed['job_count']}")

    client = None if quality_gate_only else OllamaClient(host=host, model=model)
    generated = []
    any_failed = False

    for idx, job in selected:
        facts = to_locked_facts(job)
        verification = None
        if verify_official:
            urls = [x.get("url") for x in job.get("links", []) if isinstance(x, dict) and x.get("url")]
            verification = verify_urls(urls)
            verified_facts, _ = apply_to_job(job, verification)
            # Official verification is authoritative for the fields it owns.
            # In particular, an empty verified value must be able to clear
            # contaminated/untrusted DOCX boilerplate (e.g. selection_process).
            authoritative_keys = {
                'organisation', 'advertisement_number', 'published_date',
                'total_vacancies', 'application_start', 'application_end',
                'age_limit', 'pay_scale', 'eligibility', 'selection_process',
                'how_to_apply', 'important_dates', 'official_links',
                'official_verification', 'post_vacancies', 'raw_post_vacancies',
                'derived_vacancy_sum', 'post_eligibility', 'post_facts', 'experience',
            }
            for k, v in verified_facts.items():
                if k in authoritative_keys or v not in ("", None, []):
                    facts[k] = v
            facts["official_verification"] = verification
        gate = quality_gate(job, facts)
        if verify_official:
            gate["official_verification_status"] = verification.get("status") if verification else "NOT_RUN"
            gate["verification_required"] = False if verification and verification.get("status") == "PASS" else True
            if verification and verification.get("status") != "PASS":
                gate["errors"].append("Official notification verification failed; Qwen generation is blocked")
                gate["status"] = "FAIL"
            elif verification and verification.get("status") == "PASS":
                gate["status"] = "PASS" if not gate.get("errors") else "FAIL"
        any_failed = any_failed or gate["status"] == "FAIL"

        record = {
            "job_index": idx,
            "source_job": job,
            "locked_facts": facts,
            "quality_gate": gate,
            "official_verification": verification,
        }

        if quality_gate_only or gate["status"] == "FAIL":
            record["slide_plan"] = None
            record["validation_warnings"] = []
            if gate["status"] == "FAIL":
                record["action"] = "BLOCKED: fix source extraction before sending facts to Qwen"
        else:
            attempts = []
            raw_plan = client.generate_slide_plan(facts, slide_count=slide_count)
            plan = sanitize_slide_plan(raw_plan)
            plan = _attach_verified_links(plan, facts)
            warnings = validate_slide_plan(plan, facts)
            slide_gate = slide_quality_gate(plan, facts)
            attempts.append({"attempt": 1, "gate": slide_gate, "plan": plan})

            # V1.9.15: automatically repair a failed Qwen plan once using the
            # exact deterministic gate errors. Never manually override facts.
            if slide_gate["status"] == "FAIL":
                repaired_raw = client.repair_slide_plan(
                    facts, plan, slide_gate.get("errors", []), slide_count=slide_count
                )
                repaired = sanitize_slide_plan(repaired_raw)
                repaired = _attach_verified_links(repaired, facts)
                repaired_warnings = validate_slide_plan(repaired, facts)
                repaired_gate = slide_quality_gate(repaired, facts)
                attempts.append({"attempt": 2, "gate": repaired_gate, "plan": repaired})
                if repaired_gate["status"] == "PASS":
                    raw_plan = repaired_raw
                    plan = repaired
                    warnings = repaired_warnings
                    slide_gate = repaired_gate

            record["qwen_attempts"] = [
                {"attempt": a["attempt"], "status": a["gate"].get("status"), "errors": a["gate"].get("errors", []), "warnings": a["gate"].get("warnings", [])}
                for a in attempts
            ]
            record["raw_slide_plan"] = raw_plan
            record["slide_plan"] = plan
            record["validation_warnings"] = warnings
            record["slide_quality_gate"] = slide_gate
            record["presentation_ready"] = slide_gate["status"] == "PASS"
            if slide_gate["status"] == "FAIL":
                record["action"] = "BLOCKED: slide-level quality gate failed after automatic repair"
                any_failed = True
            elif len(attempts) > 1:
                record["action"] = "QWEN_GENERATED_AFTER_AUTOMATIC_REPAIR_AND_SLIDE_GATE_PASSED"
            else:
                record["action"] = "QWEN_GENERATED_AND_SLIDE_GATE_PASSED"

        generated.append(record)
        title = job.get("title") or f"job_{idx}"
        safe = "".join(c if c.isalnum() else "_" for c in title).strip("_")[:80]
        (output_dir / f"{idx:02d}_{safe}_slide_plan.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    summary = {
        "source_docx": str(docx_path),
        "model": model,
        "ollama_host": host,
        "job_count": len(generated),
        "slide_count": slide_count,
        "quality_gate_only": quality_gate_only,
        "quality_gate_status": "FAIL" if any_failed else "PASS",
        "jobs": generated,
    }
    summary_path = output_dir / "qwen_instagram_plans.json"
    # V1.9.15: presentation-ready copy is separated from audit metadata.
    if generated:
        ready = [
            {"job_index": r["job_index"], "slides": r.get("slide_plan", {}).get("slides", [])}
            for r in generated
            if r.get("presentation_ready")
        ]
        (output_dir / "instagram_presentation_ready.json").write_text(
            json.dumps({"version": "1.9.15", "jobs": ready}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # In diagnostic/quality-gate-only mode, return the report normally so callers
    # can inspect the exact extraction and verification failures.
    if fail_on_quality_gate and any_failed and not quality_gate_only:
        raise RuntimeError("Quality gate failed. Review qwen output JSON; Qwen generation was blocked for failed jobs.")

    return summary_path, generated
