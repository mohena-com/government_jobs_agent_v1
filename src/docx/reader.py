from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator

from docx import Document

FIELD_ALIASES = {
    "advertisement_number": ["advertisement / reference no.", "advertisement / reference number", "advertisement no.", "advertisement number"],
    "published_date": ["published / updated", "post date / update", "published / updated on"],
    "total_vacancies": ["total vacancies", "vacancies", "total vacancy"],
    "application_start": ["application start", "application begin"],
    "application_end": ["application end", "application deadline", "last date"],
    "age_limit": ["age limit"],
    "application_fee": ["application fee", "exam fee"],
    "pay_scale": ["pay / salary", "pay scale / salary", "pay scale", "salary"],
    "eligibility": ["eligibility", "educational qualification", "qualification"],
    "selection_process": ["selection process"],
    "how_to_apply": ["how to apply", "how to fill / apply"],
    "important_dates": ["important dates"],
}

SECTION_NAMES = {
    "key information", "important dates", "application fee", "vacancy details",
    "eligibility", "how to fill / apply", "how to apply", "selection process", "pay / salary",
    "official links", "source", "pay scale / salary",
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r", "\n")
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def _norm_label(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()


def _field_key(label: str) -> str | None:
    n = _norm_label(label)
    for key, aliases in FIELD_ALIASES.items():
        if any(n == _norm_label(alias) for alias in aliases):
            return key
    return None


def _iter_blocks(doc: Document) -> Iterator[tuple[str, Any]]:
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    parent = doc.part.element.body
    for child in parent.iterchildren():
        if isinstance(child, CT_P):
            yield "paragraph", Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield "table", Table(child, parent)


def _table_rows(table) -> list[list[str]]:
    rows = []
    for row in table.rows:
        vals = [_clean(cell.text) for cell in row.cells]
        if any(vals):
            rows.append(vals)
    return rows


def _is_heading(text: str) -> bool:
    return _norm_label(text) in {_norm_label(x) for x in SECTION_NAMES}


def _extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s<>\"]+", text or "")


def _title_candidate(text: str) -> bool:
    low = text.lower()
    return len(text) > 20 and any(x in low for x in ("recruitment", "apply online", "online form", "vacancy"))


def _title_vacancy_candidate(title: str) -> str:
    m = re.search(r"(?:for|with|apply online for)?\s*(\d[\d,]*)\s+(?:posts?|post|vacancies?)\b", title or "", re.I)
    return m.group(1).replace(",", "") if m else ""


def _suspicious_age(value: str) -> bool:
    if not value:
        return False
    low = value.lower()
    bad_markers = ("advt. no", "recruitment online form", "short details of notification", "selection procedure", "pay scale")
    return any(x in low for x in bad_markers) or len(value) > 400



def _extract_advertisement_from_text(*texts: str) -> str:
    for text in texts:
        m = re.search(r"\bAdvt\.?\s*No\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9/._-]*(?:\s+[0-9][A-Z0-9/._-]*)?)", text or "", re.I)
        if m:
            return m.group(1).strip()
        m = re.search(r"\bAdvertisement\s*(?:No\.?|Number)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/._-]*(?:\s+[0-9][A-Z0-9/._-]*)?)", text or "", re.I)
        if m:
            return m.group(1).strip()
    return ""


def _extract_organisation_from_text(*texts: str) -> str:
    patterns = [
        r"(Rajasthan\s+Rajya\s+Vidyut\s+Utpadan\s+Nigam\s+Ltd\.?\s*\(RVUNL\))",
        r"(Rajasthan\s+Rajya\s+Vidyut\s+Utpadan\s+Nigam\s+Limited\s*\(RVUNL\))",
    ]
    for text in texts:
        for pat in patterns:
            m = re.search(pat, text or "", re.I)
            if m:
                return _clean(m.group(1))
    return ""




_MONTHS = {m.lower(): i for i, m in enumerate((
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
), 1)}

def _normalise_date_token(day: str, month: str, year: str) -> str:
    try:
        if month.isdigit():
            dt = __import__("datetime").date(int(year), int(month), int(day))
        else:
            dt = __import__("datetime").date(int(year), _MONTHS[month.lower()], int(day))
        return dt.strftime("%d %B %Y")
    except Exception:
        return ""

def _extract_date_values(text: str) -> list[str]:
    """Extract only explicit calendar dates; ignore standalone years/numbers."""
    text = text or ""
    found: list[str] = []
    patterns = [
        r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](20\d{2})(?!\d)",
        r"(?<!\d)(20\d{2})-(\d{1,2})-(\d{1,2})(?!\d)",
        r"(?<!\d)(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})(?!\d)",
    ]
    for m in re.finditer(patterns[0], text, re.I):
        value = _normalise_date_token(m.group(1), m.group(2), m.group(3))
        if value: found.append(value)
    for m in re.finditer(patterns[1], text, re.I):
        value = _normalise_date_token(m.group(3), m.group(2), m.group(1))
        if value: found.append(value)
    for m in re.finditer(patterns[2], text, re.I):
        value = _normalise_date_token(m.group(1), m.group(2), m.group(3))
        if value: found.append(value)
    return list(dict.fromkeys(found))

def _extract_application_window(*texts: str) -> dict[str, str]:
    """Recover application start/end from semantic application-window evidence.

    Priority is explicit application/deadline language, then HOW TO APPLY /
    IMPORTANT DATES ranges. Fee-payment dates are deliberately excluded.
    """
    evidence = "\n".join(t for t in texts if t)
    start = end = ""
    source = ""

    # A date range in a How-to-Apply/Important-Dates section is the strongest
    # document-level evidence for the application window.
    range_patterns = [
        r"(?<!\d)(\d{1,2}[/-]\d{1,2}[/-]20\d{2})\s*(?:to|[-–—])\s*(\d{1,2}[/-]\d{1,2}[/-]20\d{2})(?!\d)",
        r"(?<!\d)(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2})\s*(?:to|[-–—])\s*(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2})(?!\d)",
    ]
    for pattern in range_patterns:
        m = re.search(pattern, evidence, re.I)
        if m:
            vals = _extract_date_values(m.group(0))
            if len(vals) >= 2:
                start, end = vals[0], vals[1]
                source = m.group(0).strip()
                break

    # Explicit application deadline is authoritative for the end date.
    deadline = _extract_date_from_deadline(next((t for t in texts if t), ""))
    if deadline:
        vals = _extract_date_values(deadline)
        if vals:
            end = vals[0]
            source = source or deadline

    # Explicit labels can fill gaps, but never use fee-payment dates as the
    # application end date.
    label_patterns = [
        ("start", r"(?:application\s+start|application\s+begin|opening\s+date)\s*[:\-]?\s*([^\n]+)"),
        ("end", r"(?:application\s+end|last\s+date\s+to\s+apply|application\s+deadline|closing\s+date)\s*[:\-]?\s*([^\n]+)"),
    ]
    for kind, pattern in label_patterns:
        m = re.search(pattern, evidence, re.I)
        if m:
            vals = _extract_date_values(m.group(1))
            if vals:
                if kind == "start" and not start: start = vals[0]
                if kind == "end" and not end: end = vals[0]
                source = source or m.group(0).strip()

    return {"application_start": start, "application_end": end, "evidence": source}

def _extract_date_from_deadline(text: str) -> str:
    m = re.search(r"APPLICATION\s+DEADLINE\s*:\s*(.+)$", text or "", re.I)
    return _clean(m.group(1)) if m else ""


def _clean_section_contamination(value: str, section: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    # V1.6 reports can accidentally carry the next page's title/notification teaser
    # into a section. Stop at known contamination markers while preserving the useful prefix.
    markers = [
        "Rajasthan RVUNL Various Post Notification 2026",
        "Rajasthan Energy Various Post Recruitment Online Form 2026",
        "Advt. No. BULUN/Rectt",
        "Short Details of Notification",
    ]
    for marker in markers:
        pos = text.lower().find(marker.lower())
        if pos > 0:
            text = text[:pos].strip()
    return _clean(text)


def _is_missing_value(value: str) -> bool:
    return _norm_label(value) in {"", "not found", "n/a", "na", "unknown", "none"}

def _new_job(title: str = "") -> dict:
    return {
        "title": title,
        "organisation": "",
        "fields": {},
        "vacancy_rows": [],
        "links": [],
        "source": {},
        "title_vacancy_candidate": _title_vacancy_candidate(title),
        "extraction_notes": [],
    }


def _parse_report_doc(doc: Document) -> list[dict]:
    """Parse the DOCX layout generated by src.report.docx.add_job()."""
    blocks = list(_iter_blocks(doc))
    jobs: list[dict] = []

    # The V1.6/V1.7 individual job DOCX has a predictable opening:
    # title paragraph, organisation paragraph, deadline paragraph, then sections.
    # Consolidated documents can contain multiple repetitions; use heading/table boundaries.
    current: dict | None = None
    section = ""
    saw_key_info = False

    def ensure(title: str = ""):
        nonlocal current
        if current is None:
            current = _new_job(title)
        elif title and not current.get("title"):
            current["title"] = title
            current["title_vacancy_candidate"] = _title_vacancy_candidate(title)

    def flush():
        nonlocal current, section, saw_key_info
        if current and (current.get("title") or current.get("fields") or current.get("vacancy_rows")):
            jobs.append(current)
        current = None
        section = ""
        saw_key_info = False

    # Opening paragraphs are easier to parse with a small state machine.
    opening_paragraphs: list[str] = []
    for kind, block in blocks:
        if kind == "paragraph":
            text = _clean(block.text)
            if not text:
                continue
            low = _norm_label(text)

            if not _is_heading(text) and not opening_paragraphs:
                opening_paragraphs.append(text)
                ensure(text)
                continue
            if current and len(opening_paragraphs) == 1 and not _is_heading(text):
                # Second opening paragraph is organisation in our V1.6/V1.7 report format.
                current["organisation"] = text
                opening_paragraphs.append(text)
                continue
            if current and len(opening_paragraphs) == 2 and low.startswith("application deadline"):
                current["opening_deadline_display"] = text
                opening_paragraphs.append(text)
                continue

            if _is_heading(text):
                section = low
                if section == "key information":
                    saw_key_info = True
                continue

            # Explicit section values are retained verbatim; no heuristic reassignment.
            if ":" in text:
                label, value = text.split(":", 1)
                key = _field_key(label)
                if key:
                    ensure()
                    current["fields"][key] = _clean(value)
                    continue

            if section == "source":
                urls = _extract_urls(text)
                if urls:
                    current["source"]["detail_page_text"] = urls[0]
                elif text:
                    current["source"]["text"] = text
                continue

            # Section text such as important dates / fee / eligibility is collected
            # in dedicated buffers and assigned only to its own field.
            if section in {"important dates", "application fee", "eligibility", "selection process", "pay / salary", "how to fill / apply", "how to apply"}:
                ensure()
                current.setdefault("section_text", {}).setdefault(section, []).append(text)
                continue

            if _title_candidate(text) and current and text != current.get("title") and not saw_key_info:
                # A second job may start in a consolidated document.
                flush()
                ensure(text)
                opening_paragraphs = [text]

        else:
            rows = _table_rows(block)
            if not rows:
                continue
            ensure()
            header = [_norm_label(x) for x in rows[0]]

            # Key Information table from V1.6 report.
            key_rows = False
            for row in rows:
                if len(row) >= 2 and _field_key(row[0].rstrip(":")):
                    key_rows = True
                    break
            if key_rows:
                for row in rows:
                    if len(row) >= 2:
                        key = _field_key(row[0].rstrip(":"))
                        if key:
                            current["fields"][key] = _clean(row[1])
                continue

            # Vacancy table from V1.6 report.
            if any("post" in x for x in header) and any("vacanc" in x or "total post" in x for x in header):
                post_idx = next((i for i, x in enumerate(header) if "post" in x), 0)
                vac_idx = next((i for i, x in enumerate(header) if "vacanc" in x or "total post" in x), 1)
                for row in rows[1:]:
                    if len(row) <= max(post_idx, vac_idx):
                        continue
                    post = _clean(row[post_idx])
                    vac = _clean(row[vac_idx])
                    if post and vac and _norm_label(post) != "total":
                        current["vacancy_rows"].append({"post_name": post, "vacancies": vac})
                continue

            # Official Links table generated by V1.6 report.
            if any("type" == x or "type" in x for x in header) and any("url" in x for x in header):
                type_idx = next((i for i, x in enumerate(header) if "type" in x), 0)
                url_idx = next((i for i, x in enumerate(header) if "url" in x), 1)
                for row in rows[1:]:
                    if len(row) > max(type_idx, url_idx) and row[url_idx].startswith("http"):
                        current["links"].append({"label": row[type_idx], "url": row[url_idx]})
                continue

    flush()

    # Assign section buffers to their exact fields.
    mapping = {
        "important dates": "important_dates",
        "application fee": "application_fee",
        "eligibility": "eligibility",
        "selection process": "selection_process",
        "pay / salary": "pay_scale",
        "how to fill / apply": "how_to_apply",
        "how to apply": "how_to_apply",
    }
    for job in jobs:
        for sec, key in mapping.items():
            lines = job.get("section_text", {}).get(sec, [])
            if lines:
                job["fields"].setdefault(key, _clean("\n".join(lines)))
        job.pop("section_text", None)

        if _suspicious_age(job.get("fields", {}).get("age_limit", "")):
            job["extraction_notes"].append("age_limit appears suspicious and was not trusted")
            job["fields"]["age_limit"] = ""

        # If vacancy table has a numeric sum, preserve it as a derived check,
        # never overwrite the source total-vacancies field.
        nums = []
        for row in job.get("vacancy_rows", []):
            m = re.fullmatch(r"\s*([\d,]+)\s*", row.get("vacancies", ""))
            if m:
                nums.append(int(m.group(1).replace(",", "")))
        if nums:
            job["derived_vacancy_sum"] = sum(nums)

        # Recovery from imperfect V1.6 reports: the report may have lost structured
        # values while retaining them in the title/deadline/section teaser. These
        # are explicitly marked as candidates and must be verified against the
        # official notification before Qwen is allowed to publish them.
        combined = "\n".join([
            job.get("title", ""),
            job.get("organisation", ""),
            job.get("fields", {}).get("eligibility", ""),
            job.get("fields", {}).get("selection_process", ""),
            job.get("fields", {}).get("application_fee", ""),
        ])
        org = _extract_organisation_from_text(combined)
        if not job.get("organisation") or job.get("organisation") == "Organisation not identified":
            if org:
                job["organisation"] = org
                job["extraction_notes"].append("organisation recovered from document text; verify against official notification")

        existing_advt = job.get("fields", {}).get("advertisement_number", "")
        advt = existing_advt if not _is_missing_value(existing_advt) else _extract_advertisement_from_text(combined + "\n" + "\n".join(job.get("fields", {}).get("eligibility", "").splitlines()))
        if advt and _is_missing_value(advt):
            advt = ""
        if advt:
            job["fields"]["advertisement_number"] = advt
            if "advertisement number recovered from document text" not in job["extraction_notes"]:
                job["extraction_notes"].append("advertisement number recovered from document text; verify against official notification")

        deadline_candidate = _extract_date_from_deadline(job.get("opening_deadline_display", ""))
        if deadline_candidate and _is_missing_value(job.get("fields", {}).get("application_end", "")):
            job["application_end_candidate"] = deadline_candidate

        # Preserve title vacancy as a candidate, never silently promote it to verified total.
        if job.get("title_vacancy_candidate"):
            job["total_vacancies_candidate"] = job["title_vacancy_candidate"]

        for sec_key in ("application_fee", "eligibility", "selection_process", "important_dates", "pay_scale", "how_to_apply"):
            if sec_key in job.get("fields", {}):
                cleaned = _clean_section_contamination(job["fields"][sec_key], sec_key)
                job["fields"][sec_key] = cleaned

        # V1.9.33: semantic application-date recovery. The report can contain
        # correct dates outside the structured IMPORTANT DATES block. Recover
        # them from the application/deadline/how-to-apply evidence before the
        # quality gate and before Qwen sees the facts. Fee-payment dates are not
        # promoted to application_end.
        date_info = _extract_application_window(
            job.get("opening_deadline_display", ""),
            job.get("fields", {}).get("important_dates", ""),
            job.get("fields", {}).get("how_to_apply", ""),
            job.get("fields", {}).get("application_start", ""),
            job.get("fields", {}).get("application_end", ""),
        )
        # V1.9.33 hotfix: semantic evidence outranks an unverified structured
        # value. The previous implementation only filled missing fields, which
        # allowed stale/wrong dates (for example 27 July 2007) to survive.
        # When an explicit application window/deadline is recovered from the
        # document, bind those values to the semantic fields.
        if date_info.get("application_start"):
            old_start = str(job["fields"].get("application_start") or "").strip()
            if old_start != date_info["application_start"]:
                job["fields"]["application_start"] = date_info["application_start"]
                job["extraction_notes"].append(
                    "application_start bound to semantic document evidence"
                )
        if date_info.get("application_end"):
            old_end = str(job["fields"].get("application_end") or "").strip()
            if old_end != date_info["application_end"]:
                job["fields"]["application_end"] = date_info["application_end"]
                job["extraction_notes"].append(
                    "application_end bound to semantic document evidence"
                )
        job["application_date_evidence"] = date_info.get("evidence", "")

    return jobs


def _fallback_legacy_parse(doc: Document) -> list[dict]:
    """Minimal compatibility parser for older/non-V1.6 report layouts."""
    jobs: list[dict] = []
    current = None
    for kind, block in _iter_blocks(doc):
        if kind != "paragraph":
            continue
        text = _clean(block.text)
        if not text:
            continue
        if _title_candidate(text):
            if current:
                jobs.append(current)
            current = _new_job(text)
        elif current and ":" in text:
            label, value = text.split(":", 1)
            key = _field_key(label)
            if key:
                current["fields"][key] = _clean(value)
    if current:
        jobs.append(current)
    return jobs


def read_docx(path: str | Path) -> dict:
    path = Path(path)
    doc = Document(path)
    jobs = _parse_report_doc(doc)
    if not jobs:
        jobs = _fallback_legacy_parse(doc)

    unique = []
    seen = set()
    for job in jobs:
        key = (_clean(job.get("title")).lower(), _clean(job.get("fields", {}).get("advertisement_number")).lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)

    return {"path": str(path), "job_count": len(unique), "jobs": unique}


def to_locked_facts(job: dict) -> dict:
    fields = job.get("fields", {})
    return {
        "organisation": job.get("organisation", ""),
        "post": job.get("title", ""),
        "advertisement_number": fields.get("advertisement_number", ""),
        "published_date": fields.get("published_date", ""),
        "total_vacancies": fields.get("total_vacancies", ""),
        "application_start": fields.get("application_start", ""),
        "application_end": fields.get("application_end", ""),
        "age_limit": fields.get("age_limit", ""),
        "application_fee": fields.get("application_fee", ""),
        "pay_scale": fields.get("pay_scale", ""),
        "eligibility": fields.get("eligibility", ""),
        "selection_process": fields.get("selection_process", ""),
        "how_to_apply": fields.get("how_to_apply", ""),
        "important_dates": fields.get("important_dates", ""),
        "vacancy_rows": job.get("vacancy_rows", []),
        "official_links": job.get("links", []),
        "source": job.get("source", {}),
        "title_vacancy_candidate": job.get("title_vacancy_candidate", ""),
        "total_vacancies_candidate": job.get("total_vacancies_candidate", ""),
        "application_end_candidate": job.get("application_end_candidate", ""),
        "application_date_evidence": job.get("application_date_evidence", ""),
        "extraction_notes": job.get("extraction_notes", []),
        "derived_vacancy_sum": job.get("derived_vacancy_sum", None),
    }
