from __future__ import annotations
PRESENTATION_FALLBACKS = {
    "total_vacancies": "See Official Notification",
    "eligibility": "Refer to Official Notification",
    "age_limit": "Refer to Official Notification",
    "pay_scale": "See Official Notification",
    "application_fee": "See Official Notification",
    "selection_process": "See Official Notification",
}

def _presentation_fallback(field):
    """Return safe copy when a source field is unavailable.
    Never invent a factual value.
    """
    return PRESENTATION_FALLBACKS.get(field, "See Official Notification")

import json
import re
from pathlib import Path

from src.docx.reader import read_docx, to_locked_facts
from src.docx.quality_gate import quality_gate
from src.llm.ollama_client import OllamaClient
from src.llm.validator import validate_slide_plan
from src.llm.slide_quality_gate import slide_quality_gate
from src.llm.presentation_sanitizer import sanitize_slide_plan
from src.llm.allowed_facts import build_allowed_facts, fatal_generation_errors
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


def _prepare_presentation_facts(locked_facts):
    """Build a complete presentation bundle without fabricating facts."""
    facts = dict(locked_facts or {})
    fallbacks = {}
    for field, fallback in PRESENTATION_FALLBACKS.items():
        value = facts.get(field)
        if value in (None, "", [], {}, "N/A", "NA", "Unknown", "unknown"):
            fallbacks[field] = fallback
    return facts, fallbacks



def _date_tokens(text: str) -> list[str]:
    import re
    from datetime import date
    months = {m.lower(): i for i, m in enumerate((
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ), 1)}
    out = []
    for m in re.finditer(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](20\d{2})(?!\d)", text or ""):
        try: out.append(date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat())
        except ValueError: pass
    for m in re.finditer(r"(?<!\d)(20\d{2})-(\d{1,2})-(\d{1,2})(?!\d)", text or ""):
        try: out.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat())
        except ValueError: pass
    for m in re.finditer(r"(?<!\d)(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})(?!\d)", text or "", re.I):
        try: out.append(date(int(m.group(3)), months[m.group(2).lower()], int(m.group(1))).isoformat())
        except (ValueError, KeyError): pass
    return list(dict.fromkeys(out))

def _crosscheck_application_dates(facts: dict, job: dict) -> dict:
    """V1.9.33: bind application dates to semantic fields and verify them against DOCX evidence."""
    evidence_parts = [
        job.get("opening_deadline_display", ""),
        (job.get("fields") or {}).get("important_dates", ""),
        (job.get("fields") or {}).get("how_to_apply", ""),
        job.get("application_date_evidence", ""),
    ]
    evidence = "\n".join(str(x or "") for x in evidence_parts)
    allowed = set(_date_tokens(evidence))
    start = str(facts.get("application_start") or "").strip()
    end = str(facts.get("application_end") or "").strip()
    start_dates = set(_date_tokens(start))
    end_dates = set(_date_tokens(end))
    result = {"status": "PASS", "document_evidence": evidence, "allowed_application_dates": sorted(allowed), "errors": [], "warnings": []}

    if start_dates and allowed and not start_dates.issubset(allowed):
        result["errors"].append(f"application_start {start!r} is not supported by DOCX date evidence")
    if end_dates and allowed and not end_dates.issubset(allowed):
        result["errors"].append(f"application_end {end!r} is not supported by DOCX date evidence")

    if result["errors"]:
        result["status"] = "FAIL"
        # Do not allow an unverified generated date to reach Qwen.
        facts["application_start"] = ""
        facts["application_end"] = ""
        facts["application_dates_crosscheck_error"] = result["errors"]
    else:
        facts["application_dates_crosscheck"] = {
            "status": "PASS",
            "document_evidence": evidence,
            "allowed_application_dates": sorted(allowed),
        }
    return result



def _bind_canonical_application_dates(facts: dict, job: dict, verification: dict | None = None) -> dict:
    """V1.9.35: create one canonical application-date fact pair.

    Priority is deliberately deterministic:
      1. semantic dates recovered from the Job Detail DOCX
      2. explicit document deadline/window evidence
      3. verified official-source dates
      4. otherwise leave the fields empty for presentation fallback

    A generic verifier must never overwrite a document-supported application
    window with an unrelated, stale, or differently-scoped date.
    """
    fields = job.get("fields") or {}
    doc_start = str(fields.get("application_start") or "").strip()
    doc_end = str(fields.get("application_end") or "").strip()
    doc_evidence = str(job.get("application_date_evidence") or "").strip()

    # If an older Job Detail DOCX has not populated the semantic fields yet,
    # recover a date pair directly from its preserved evidence. This is still
    # document-derived; it is not model-generated.
    evidence_dates = _date_tokens(doc_evidence)
    if not doc_start and evidence_dates:
        doc_start = evidence_dates[0]
    if not doc_end and len(evidence_dates) >= 2:
        doc_end = evidence_dates[-1]

    verified_start = str((verification or {}).get("application_start") or "").strip()
    verified_end = str((verification or {}).get("application_end") or "").strip()

    # Document evidence wins whenever it contains an explicit application
    # window. This is the critical protection against stale verifier output.
    canonical_start = doc_start or verified_start
    canonical_end = doc_end or verified_end
    source = "DOCX_SEMANTIC_EVIDENCE" if (doc_start or doc_end) else ("OFFICIAL_VERIFICATION" if (verified_start or verified_end) else "UNAVAILABLE")

    if canonical_start:
        facts["application_start"] = canonical_start
    if canonical_end:
        facts["application_end"] = canonical_end

    facts["application_dates_canonical"] = {
        "application_start": canonical_start,
        "application_end": canonical_end,
        "source": source,
        "document_evidence": doc_evidence,
        "verified_start": verified_start,
        "verified_end": verified_end,
    }
    facts["application_date_evidence"] = doc_evidence
    return facts


def _format_date_pair(start: str, end: str) -> str:
    if start and end:
        return f"Application: {start} → {end}"
    if end:
        return f"Application Deadline: {end}"
    if start:
        return f"Application Start: {start}"
    return "Application Dates: Refer to Official Notification"


def _normalize_application_date_claims(plan: dict, facts: dict) -> dict:
    """V1.9.36: deterministically rewrite application-date claims.

    Qwen may put an application window inside ordinary prose (for example,
    'the link remains active from 31.08.2026 to 26.09.2026').  Replacing only
    labelled bullets is insufficient.  We therefore rewrite dates only when
    the surrounding text is semantically about applying/opening/deadline.
    Fee-payment, exam, notification and admit-card dates are left untouched.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("slides"), list):
        return plan

    start = str(facts.get("application_start") or "").strip()
    end = str(facts.get("application_end") or "").strip()
    if not (start or end):
        return plan

    date_pattern = re.compile(
        r"(?<!\d)(?:\d{1,2}[/-]\d{1,2}[/-]20\d{2}|20\d{2}-\d{1,2}-\d{1,2}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2})(?!\d)",
        re.I,
    )
    app_context = re.compile(
        r"(application|apply|applying|opens?|opening|deadline|last\s+date|closing\s+date|online\s+form|link\s+(?:shall\s+)?remains?\s+active)",
        re.I,
    )

    def replace_text(value: str) -> str:
        text = str(value or "")
        low = text.lower()
        if not app_context.search(text):
            return text

        # Explicit semantic labels always win.
        if re.search(r"application\s+(?:start|opens?|opening)", low):
            return re.sub(date_pattern, start or end or "Refer to Official Notification", text, count=0) if not end else re.sub(date_pattern, start, text, count=1)
        if re.search(r"application\s+(?:deadline|end)|last\s+date\s+to\s+apply|closing\s+date", low):
            return re.sub(date_pattern, end or start or "Refer to Official Notification", text, count=1)

        matches = list(date_pattern.finditer(text))
        if len(matches) >= 2 and start and end:
            # Application-window prose: replace the two dates in order.
            pieces=[]; last=0
            for i,m in enumerate(matches):
                pieces.append(text[last:m.start()])
                pieces.append(start if i == 0 else end if i == 1 else m.group(0))
                last=m.end()
            pieces.append(text[last:])
            return "".join(pieces)
        if matches and end:
            # Single application/deadline date in prose -> canonical end.
            m=matches[0]
            return text[:m.start()] + end + text[m.end():]
        return text

    for slide in plan["slides"]:
        if not isinstance(slide, dict):
            continue
        if isinstance(slide.get("headline"), str):
            slide["headline"] = replace_text(slide["headline"])
        if isinstance(slide.get("subtitle"), str):
            slide["subtitle"] = replace_text(slide["subtitle"])
        if isinstance(slide.get("bullets"), list):
            slide["bullets"] = [replace_text(x) for x in slide["bullets"]]
    return plan


def _compact_fact_text(value: str, max_chars: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0].strip()
    return cut + "…"


def _enforce_presentation_contract(plan: dict, facts: dict) -> dict:
    """V1.9.36: final deterministic completeness pass before QA.

    Missing presentation coverage is repaired with source-backed compact facts
    or the configured fallback. This is deliberately after Qwen + repair so a
    single model omission cannot block an otherwise safe presentation.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("slides"), list):
        return plan
    slides=plan["slides"]
    while len(slides) < 6:
        slides.append({"type": ["title","vacancies","eligibility","age_pay_fee","dates_selection","apply_links"][len(slides)], "headline":"", "subtitle":"", "bullets":[]})

    def text_of(slide):
        return " ".join([str(slide.get("headline") or ""), str(slide.get("subtitle") or "")] + [str(x) for x in (slide.get("bullets") or [])]).lower()

    # Slide 3: verified eligibility must be represented, but keep it compact.
    s3=slides[2]; t3=text_of(s3)
    elig=str(facts.get("eligibility") or "").strip()
    rows=facts.get("post_eligibility") or facts.get("post_facts") or []
    s3_body=" ".join([str(s3.get("subtitle") or "")] + [str(x) for x in (s3.get("bullets") or [])]).lower()
    if elig and not any(k in s3_body for k in ("eligib", "qualification", "degree", "diploma", "marks")):
        compact=[]
        for row in rows[:4]:
            if isinstance(row, dict):
                q=str(row.get("qualification") or row.get("eligibility") or "").strip()
                post=str(row.get("post") or "").strip()
                if q:
                    compact.append(f"{post}: {_compact_fact_text(q, 155)}" if post else _compact_fact_text(q, 175))
        if not compact:
            compact=[f"Qualification: {_compact_fact_text(elig, 180)}"]
        s3["bullets"] = list(s3.get("bullets") or []) + compact[:3]

    # Slide 4: verified age/pay/fee coverage.
    s4=slides[3]; t4=text_of(s4); b4=list(s4.get("bullets") or [])
    for field,label,keys in (("age_limit","Age",("age",)), ("pay_scale","Pay / Salary",("pay","salary","level")), ("application_fee","Application Fee",("fee",))):
        val=str(facts.get(field) or "").strip()
        if val and not any(k in t4 for k in keys):
            b4.append(f"{label}: {_compact_fact_text(val, 150)}")
    s4["bullets"]=b4[:8]

    # Slide 5: canonical dates and selection.
    s5=slides[4]; t5=text_of(s5); b5=list(s5.get("bullets") or [])
    start=str(facts.get("application_start") or "").strip(); end=str(facts.get("application_end") or "").strip()
    if start and end and not (start.lower() in t5 and end.lower() in t5):
        b5.append(f"Application: {start} → {end}")
    elif not start and not end and "official notification" not in t5:
        b5.append("Application Dates: Refer to Official Notification")
    sel=str(facts.get("selection_process") or "").strip()
    if sel and not any(k in t5 for k in ("selection","exam","written","test","interview")):
        b5.append(f"Selection: {_compact_fact_text(sel, 180)}")
    s5["bullets"]=b5[:8]

    # Slide 6: generic CTA is presentation copy, but ensure the slide has a
    # factual instruction even if Qwen omitted it.
    s6=slides[5]; t6=text_of(s6); b6=list(s6.get("bullets") or [])
    if not any(k in t6 for k in ("apply","application","notification","official","document")):
        b6.append("Read the Official Notification before applying.")
    s6["bullets"]=b6[:8]

    plan["slides"]=slides[:6]
    return _normalize_application_date_claims(plan, facts)


def _enforce_application_dates_on_plan(plan: dict, facts: dict) -> dict:
    """Backward-compatible wrapper for the final deterministic presentation pass."""
    return _enforce_presentation_contract(plan, facts)

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
    batch_mode: bool = False,
    prompt_path: str | Path | None = None,
):
    parsed = read_docx(docx_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = list(enumerate(parsed["jobs"], 1))
    if job_index is not None:
        selected = [(i, j) for i, j in selected if i == job_index]
        if not selected:
            raise IndexError(f"job_index {job_index} is outside 1..{parsed['job_count']}")

    client = None if quality_gate_only else OllamaClient(host=host, model=model, prompt_path=str(prompt_path) if prompt_path else None)
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

        # V1.9.35: bind one canonical application-date pair AFTER official
        # verification. This prevents generic verifier output from overwriting
        # dates already supported by the Job Detail DOCX.
        facts = _bind_canonical_application_dates(facts, job, verification)

        # Cross-check the canonical values before Qwen sees them.
        date_crosscheck = _crosscheck_application_dates(facts, job)
        facts["application_dates_crosscheck"] = date_crosscheck
        if date_crosscheck.get("status") == "FAIL":
            facts["extraction_notes"] = list(facts.get("extraction_notes") or []) + [
                "V1.9.33 withheld application dates because they failed DOCX semantic cross-check"
            ]

        gate = quality_gate(job, facts)
        if verify_official:
            gate["official_verification_status"] = verification.get("status") if verification else "NOT_RUN"
            gate["verification_required"] = False if verification and verification.get("status") == "PASS" else True
            if verification and verification.get("status") != "PASS":
                # Source verification is an audit signal, not a global Qwen kill-switch.
                # Missing/unreadable source fields are represented in LOCKED_FACTS and the
                # prompt instructs Qwen to omit them or say "Refer to Official Notification".
                gate["warnings"].append("Official notification verification did not fully pass; presentation constrained to extracted facts")
                gate["status"] = "FAIL" if gate.get("errors") else "WARN"
            elif verification and verification.get("status") == "PASS":
                gate["status"] = "PASS" if not gate.get("errors") else "FAIL"
        presentation_facts, presentation_fallbacks = build_allowed_facts(facts)
        fatal_errors = fatal_generation_errors(gate)
        any_failed = any_failed or bool(fatal_errors)

        record = {
            "job_index": idx,
            "source_job": job,
            "locked_facts": facts,
            "presentation_facts": presentation_facts,
            "presentation_fallbacks": presentation_fallbacks,
            "quality_gate": gate,
            "fatal_generation_errors": fatal_errors,
            "official_verification": verification,
            "application_dates_crosscheck": date_crosscheck,
            "application_dates_canonical": facts.get("application_dates_canonical", {}),
        }

        # V1.9.29: verification-to-generation decoupling. Missing/unreadable
        # fields are presentation fallbacks; only direct factual contradictions
        # are generation blockers. Source QA remains fully auditable.
        source_gate_failed = gate["status"] in {"FAIL", "WARN"}

        if quality_gate_only:
            record["slide_plan"] = None
            record["validation_warnings"] = []
            record["action"] = "SOURCE_QA_ONLY"
        elif fatal_errors and not batch_mode and fail_on_quality_gate:
            record["slide_plan"] = None
            record["validation_warnings"] = []
            record["action"] = "BLOCKED: fatal factual reconciliation conflict"
        else:
            attempts = []
            raw_plan = client.generate_slide_plan(presentation_facts, slide_count=slide_count)
            plan = sanitize_slide_plan(raw_plan)
            plan = _enforce_application_dates_on_plan(plan, presentation_facts)
            plan = _attach_verified_links(plan, facts)
            warnings = validate_slide_plan(plan, presentation_facts)
            slide_gate = slide_quality_gate(plan, presentation_facts)
            attempts.append({"attempt": 1, "gate": slide_gate, "plan": plan})

            if slide_gate["status"] == "FAIL":
                repaired_raw = client.repair_slide_plan(
                    presentation_facts, plan, slide_gate.get("errors", []), slide_count=slide_count
                )
                repaired = sanitize_slide_plan(repaired_raw)
                repaired = _enforce_application_dates_on_plan(repaired, presentation_facts)
                repaired = _attach_verified_links(repaired, facts)
                repaired_warnings = validate_slide_plan(repaired, presentation_facts)
                repaired_gate = slide_quality_gate(repaired, presentation_facts)
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
            elif source_gate_failed or presentation_fallbacks:
                record["action"] = (
                    "QWEN_GENERATED_WITH_FALLBACKS_AND_SOURCE_WARNINGS_AND_SLIDE_GATE_PASSED"
                    if len(attempts) == 1
                    else "QWEN_GENERATED_AFTER_AUTOMATIC_REPAIR_WITH_FALLBACKS_AND_SOURCE_WARNINGS_AND_SLIDE_GATE_PASSED"
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
            json.dumps({"version": "1.9.35", "jobs": ready}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # In diagnostic/quality-gate-only mode, return the report normally so callers
    # can inspect the exact extraction and verification failures.
    if fail_on_quality_gate and any_failed and not quality_gate_only and not batch_mode:
        raise RuntimeError("Fatal factual reconciliation conflict. Review qwen output JSON; Qwen generation was blocked.")

    return summary_path, generated


# V1.9.33 prompt policy
'\nPRESENTATION COMPLETENESS POLICY:\n- Never invent missing recruitment facts.\n- Never leave a required presentation section blank.\n- If a factual field is unavailable, use the supplied presentation fallback,\n  such as "See Official Notification" or "Refer to Official Notification".\n- Compress long content to fit the slide; prioritize the most decision-useful facts.\n- A slide may omit secondary detail only when the omitted detail is safely covered\n  by a concise fallback or "See Official Notification".\n- Generic design CTAs such as "APPLY NOW", "CHECK DETAILS", and "READ NOTIFICATION"\n  are presentation copy, not factual claims.\n'
