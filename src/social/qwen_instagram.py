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
    slide_count: int = 2,
    job_index: int | None = None,
    quality_gate_only: bool = False,
    fail_on_quality_gate: bool = True,
    verify_official: bool = False,
    batch_mode: bool = False,
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
            verification_docs = (verification or {}).get("advertisements", [])
            has_rvunl_authoritative_docs = any(
                d.get("document_type") in {"JE", "JA_ACCOUNTANT", "SHORT_NOTICE"}
                for d in verification_docs
            )
            for k, v in verified_facts.items():
                # Specialised RVUNL verification is authoritative even when a
                # field is deliberately empty. Generic verification is
                # conservative: empty extraction means "not safely extracted"
                # and must not erase a good DOCX fact.
                if has_rvunl_authoritative_docs:
                    if k in authoritative_keys or v not in ("", None, []):
                        facts[k] = v
                else:
                    if v not in ("", None, []):
                        facts[k] = v
            # V1.9.24: generic official PDFs are verification anchors, not
            # all-or-nothing field extractors. When at least one official PDF
            # was successfully downloaded and parsed, safely recover candidate
            # values already present in the source DOCX. The candidate is only
            # promoted when the official document itself is the verification
            # anchor; we never invent a value.
            if verify_official and verification and verification.get("status") == "PASS":
                if not facts.get("total_vacancies") and facts.get("total_vacancies_candidate"):
                    facts["total_vacancies"] = str(facts["total_vacancies_candidate"])
                    facts["total_vacancies_source"] = "DOCX_TITLE_CANDIDATE_WITH_OFFICIAL_PDF_ANCHOR"
                if not facts.get("application_end") and facts.get("application_end_candidate"):
                    facts["application_end"] = str(facts["application_end_candidate"])
                    facts["application_end_source"] = "DOCX_DEADLINE_CANDIDATE_WITH_OFFICIAL_PDF_ANCHOR"
                elif not facts.get("application_end"):
                    facts["application_end"] = "See official notification for application/last date."
                    facts["application_end_source"] = "OFFICIAL_PDF_AVAILABLE_BUT_FIELD_NOT_EXTRACTED"
                # If the DOCX contains a usable advertisement number, retain it.
                if (not facts.get("advertisement_number") or facts.get("advertisement_number") == "Not found"):
                    cand = (job.get("fields") or {}).get("advertisement_number")
                    if cand and str(cand).lower() not in {"not found", "unknown"}:
                        facts["advertisement_number"] = str(cand)
                # Placeholder eligibility is not usable. If the official PDF
                # parser has no structured qualification, use a truthful fallback
                # instead of sending SarkariResult boilerplate to Qwen.
                elig = str(facts.get("eligibility") or "").strip()
                if not elig or "read the official notification" in elig.lower() or "read the notification" in elig.lower():
                    verified_elig = []
                    for d in verification.get("advertisements", []):
                        for row in d.get("post_eligibility", []) or []:
                            q = str(row.get("qualification") or "").strip()
                            if q:
                                verified_elig.append(f"{row.get('post')}: {q}")
                    if verified_elig:
                        facts["eligibility"] = "; ".join(verified_elig)
                    else:
                        facts["eligibility"] = "See official notification for post-wise educational qualification and experience requirements."
                        facts["eligibility_source"] = "OFFICIAL_PDF_AVAILABLE_BUT_FIELD_NOT_EXTRACTED"
                if not facts.get("age_limit"):
                    # Do not invent an age. Preserve an explicit instruction to
                    # consult the verified notification when the PDF does not
                    # expose a machine-readable age field.
                    facts["age_limit"] = "As specified in the official notification; check post/category-wise limits and relaxations."
                    facts["age_limit_source"] = "OFFICIAL_PDF_AVAILABLE_BUT_FIELD_NOT_EXTRACTED"
                if not facts.get("application_start"):
                    if verification.get("application_start"):
                        facts["application_start"] = verification["application_start"]
                    else:
                        facts["application_start"] = "See official notification for application start date."
                        facts["application_start_source"] = "OFFICIAL_PDF_AVAILABLE_BUT_FIELD_NOT_EXTRACTED"
                if not facts.get("advertisement_number") or facts.get("advertisement_number") == "Not found":
                    facts["advertisement_number"] = "See official notification for advertisement/reference number."
                    facts["advertisement_number_source"] = "OFFICIAL_PDF_AVAILABLE_BUT_FIELD_NOT_EXTRACTED"
                if not facts.get("organisation") or facts.get("organisation") == "Organisation not identified":
                    org = (job.get("organisation") or "").strip()
                    if org and org.lower() != "organisation not identified":
                        facts["organisation"] = org
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

        # V1.9.26: source QA and presentation QA are separate layers.
        # In batch/presentation mode a source-quality failure is recorded in
        # the audit metadata but does not prevent Qwen from producing a
        # source-constrained presentation. Qwen receives only LOCKED_FACTS and
        # the slide gate still rejects invented/unsupported content.
        source_gate_failed = gate["status"] == "FAIL"
        presentation_mode = batch_mode or not fail_on_quality_gate

        if quality_gate_only:
            record["slide_plan"] = None
            record["validation_warnings"] = []
            if source_gate_failed:
                record["action"] = "BLOCKED: source quality gate only"
        elif source_gate_failed and not presentation_mode:
            record["slide_plan"] = None
            record["validation_warnings"] = []
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
                record["presentation_ready"] = False
                any_failed = True
            elif source_gate_failed:
                record["action"] = (
                    "QWEN_GENERATED_WITH_SOURCE_WARNINGS_AND_SLIDE_GATE_PASSED"
                    if len(attempts) == 1
                    else "QWEN_GENERATED_AFTER_AUTOMATIC_REPAIR_WITH_SOURCE_WARNINGS_AND_SLIDE_GATE_PASSED"
                )
                record["presentation_ready"] = True
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
            json.dumps({"version": "1.9.26", "jobs": ready}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # In diagnostic/quality-gate-only mode, return the report normally so callers
    # can inspect the exact extraction and verification failures.
    if fail_on_quality_gate and any_failed and not quality_gate_only and not batch_mode:
        raise RuntimeError("Quality gate failed. Review qwen output JSON; Qwen generation was blocked for failed jobs.")

    return summary_path, generated
