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
    "actual detail-page fields",
    "important dates",
    "application fee",
    "vacancy details",
    "eligibility",
    "how to fill / apply",
    "selection process",
    "pay scale / salary",
    "official links",
    "source",
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
        for alias in aliases:
            if n == _norm_label(alias):
                return key
    return None


def _iter_blocks(doc: Document) -> Iterator[tuple[str, Any]]:
    """Yield paragraphs/tables in document order."""
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table, _Cell
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


def _looks_like_job_title(text: str) -> bool:
    low = text.lower()
    return bool(text) and (
        "recruitment" in low or "online form" in low or "vacancy" in low
        or "post" in low and len(text) > 15
    )


def _parse_job_blocks(doc: Document) -> list[dict]:
    """Parse both the consolidated deep report and individual job reports."""
    jobs: list[dict] = []
    current: dict | None = None
    current_section = ""

    def ensure_job(title=""):
        nonlocal current
        if current is None:
            current = {
                "title": title,
                "organisation": "",
                "fields": {},
                "vacancy_rows": [],
                "links": [],
                "source": {},
            }
        elif title and not current.get("title"):
            current["title"] = title

    def flush():
        nonlocal current
        if current and (current.get("title") or current.get("fields") or current.get("vacancy_rows")):
            jobs.append(current)
        current = None

    for kind, block in _iter_blocks(doc):
        if kind == "paragraph":
            text = _clean(block.text)
            if not text:
                continue

            style = ""
            low = text.lower()

            # Job title markers from the current report format.
            if text.startswith("RC") or " Recruitment " in text or " Online Form " in text or " Apply Online " in text:
                if not current:
                    if current and current.get("title") and text != current.get("title"):
                        flush()
                    ensure_job(text)
                    continue

            if low in {x.lower() for x in SECTION_NAMES} or low.startswith("actual detail-page fields"):
                current_section = low
                ensure_job()
                continue

            # Report paragraphs such as "Post / title: ...".
            if ":" in text:
                label, value = text.split(":", 1)
                key = _field_key(label)
                if key:
                    ensure_job()
                    current["fields"][key] = _clean(value)
                    continue

            if low.startswith("sarkariresult detail page:"):
                ensure_job()
                current["source"]["detail_page_text"] = text.split(":", 1)[-1].strip()
                continue

            if current_section == "source" and text:
                current["source"]["text"] = text

        else:
            rows = _table_rows(block)
            if not rows:
                continue

            # Index table: don't create jobs from it; detail tables do that.
            header = [r.lower() for r in rows[0]]
            if "job" in header and "last date" in header:
                continue

            # Key information / job identity table. These reports commonly
            # start each job with rows such as Name Of Post, Post Date / Update
            # and Short Information rather than a conventional header row.
            row_keys = [(_field_key(row[0].rstrip(":")) if row else None) for row in rows]
            has_name_of_post = bool(rows and _norm_label(rows[0][0]).startswith("name of post"))
            if has_name_of_post:
                new_title = rows[0][1] if len(rows[0]) >= 2 else ""
                if current and current.get("title") and new_title and current.get("title") != new_title:
                    flush()
                ensure_job(new_title)

            if has_name_of_post or any(k for k in row_keys):
                ensure_job()
                for row, key in zip(rows, row_keys):
                    if len(row) >= 2 and key:
                        current["fields"][key] = row[1]
                    elif len(row) >= 2 and _norm_label(row[0]) == "name of post":
                        current["title"] = row[1]
                    elif len(row) >= 2 and _norm_label(row[0]) == "short information":
                        current["short_information"] = row[1]
                continue

            # Vacancy table.
            if any("post name" in x for x in header) and any("total post" in x or "vacancies" in x for x in header):
                ensure_job()
                post_idx = next((i for i, x in enumerate(header) if "post name" in x or x == "post"), 0)
                vac_idx = next((i for i, x in enumerate(header) if "total post" in x or "vacancies" in x), 1)
                for row in rows[1:]:
                    if len(row) > max(post_idx, vac_idx):
                        post = _clean(row[post_idx])
                        vac = _clean(row[vac_idx])
                        if post and vac and post.lower() not in {"total", "post name"}:
                            current["vacancy_rows"].append({"post_name": post, "vacancies": vac})
                continue

            # Links table.
            if any("url" in x for x in header) and any("type" in x for x in header):
                ensure_job()
                for row in rows[1:]:
                    if len(row) >= 2 and row[1].startswith("http"):
                        current["links"].append({"label": row[0], "url": row[1]})
                continue

    flush()

    # Consolidated reports may not have clean title boundaries. Rebuild from
    # the repeated "Name Of Post" table rows when possible.
    if not jobs:
        jobs = _parse_from_key_tables(doc)

    return jobs


def _parse_from_key_tables(doc: Document) -> list[dict]:
    jobs = []
    for kind, block in _iter_blocks(doc):
        if kind != "table":
            continue
        rows = _table_rows(block)
        if len(rows) < 2:
            continue
        first = rows[0][0].lower() if rows[0] else ""
        if "name of post" not in first:
            continue
        job = {"title": "", "organisation": "", "fields": {}, "vacancy_rows": [], "links": [], "source": {}}
        for row in rows[:5]:
            if len(row) < 2:
                continue
            key = _field_key(row[0].rstrip(":"))
            if key:
                job["fields"][key] = row[1]
            elif _norm_label(row[0]) == "name of post":
                job["title"] = row[1]
            elif _norm_label(row[0]) == "short information":
                job["short_information"] = row[1]
        if job["title"]:
            jobs.append(job)
    return jobs


def read_docx(path: str | Path) -> dict:
    """Read a recruitment report DOCX into source-derived structured records."""
    path = Path(path)
    doc = Document(path)
    jobs = _parse_job_blocks(doc)

    # De-duplicate repeated job records by title + advertisement/reference.
    unique = []
    seen = set()
    for job in jobs:
        key = (
            _clean(job.get("title")).lower(),
            _clean(job.get("fields", {}).get("advertisement_number")).lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)

    return {
        "path": str(path),
        "job_count": len(unique),
        "jobs": unique,
    }


def to_locked_facts(job: dict) -> dict:
    """Convert reader output into the fact payload sent to Qwen."""
    fields = job.get("fields", {})
    facts = {
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
    }
    return facts
