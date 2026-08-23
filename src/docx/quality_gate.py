from __future__ import annotations

import re
from typing import Any

REQUIRED = [
    "organisation", "post", "advertisement_number", "published_date",
    "total_vacancies", "application_start", "application_end",
    "age_limit", "eligibility",
]

OPTIONAL = ["application_fee", "pay_scale", "selection_process", "how_to_apply", "important_dates"]


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _is_missing(v: Any) -> bool:
    s = _norm(v).lower()
    return not s or s in {"not found", "n/a", "na", "unknown", "none"}


def _numeric(v: Any) -> int | None:
    m = re.search(r"(?<!\d)([\d,]+)(?!\d)", _norm(v))
    return int(m.group(1).replace(",", "")) if m else None


def quality_gate(job: dict, facts: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    suspicious: list[str] = []

    for field in REQUIRED:
        if _is_missing(facts.get(field)):
            errors.append(f"Missing required fact: {field}")

    for field in OPTIONAL:
        if _is_missing(facts.get(field)):
            warnings.append(f"Optional fact not extracted: {field}")

    age = _norm(facts.get("age_limit"))
    if age and any(x in age.lower() for x in ("advt. no", "recruitment online form", "short details of notification", "selection procedure", "pay scale")):
        errors.append("Suspicious age_limit content; field appears contaminated")
        suspicious.append("age_limit")

    title_candidate = _numeric(facts.get("title_vacancy_candidate"))
    total = _numeric(facts.get("total_vacancies"))
    derived = facts.get("derived_vacancy_sum")
    if title_candidate is not None:
        if total is None:
            warnings.append(f"Title contains candidate vacancy count {title_candidate}; verify against official vacancy table")
        elif total != title_candidate:
            warnings.append(f"Title vacancy count {title_candidate} differs from extracted total {total}")
    if derived is not None and total is not None and derived != total:
        warnings.append(f"Vacancy-row sum {derived} differs from total_vacancies {total}")

    links = facts.get("official_links") or []
    if not links:
        errors.append("No official links extracted")
    elif not any("http" in _norm(x.get("url")) for x in links if isinstance(x, dict)):
        errors.append("Official links are present but no usable URL was extracted")

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "suspicious_fields": suspicious,
        "required_fields": REQUIRED,
        "missing_required": [f for f in REQUIRED if _is_missing(facts.get(f))],
        "optional_missing": [f for f in OPTIONAL if _is_missing(facts.get(f))],
    }
