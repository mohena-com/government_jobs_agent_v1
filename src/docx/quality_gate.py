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



CANONICAL_POSTS = (
    "junior engineer-i (electrical)",
    "junior engineer-i (mechanical)",
    "junior engineer-i (civil)",
    "junior accountant",
    "junior assistant/ commercial assistant-ii",
)


def _post_key(v: Any) -> str:
    return " ".join(str(v or "").lower().replace("–", "-").replace("—", "-").split())


def _post_fact_quality(facts: dict, errors: list[str], suspicious: list[str], verification: list[str]) -> None:
    """V1.9.8 hard gate: every canonical post must have clean eligibility."""
    rows = facts.get("post_facts") or facts.get("post_eligibility") or []
    by_post = {_post_key(r.get("post")): r for r in rows if isinstance(r, dict)}
    missing = []
    bad = []
    for post in CANONICAL_POSTS:
        row = by_post.get(post)
        if not row:
            missing.append(post)
            continue
        qual = _norm(row.get("qualification"))
        method = _norm(row.get("source_method")).upper()
        if _is_missing(qual):
            bad.append(post)
        if method in {"GENERIC_BOUNDARY", "GENERIC", "PAGE_WINDOW", "UNKNOWN"}:
            bad.append(post)
        low = qual.lower()
        if any(x in low for x in ("disqualification for appointment", "physical fitness", "character of candidate", "read the notification")):
            bad.append(post)
    if missing:
        errors.append("Missing post-specific eligibility facts for canonical posts: " + ", ".join(missing))
    if bad:
        unique = list(dict.fromkeys(bad))
        errors.append("Unusable/contaminated post-specific eligibility facts for canonical posts: " + ", ".join(unique))
    if missing or bad:
        suspicious.append("post_eligibility")
        verification.append("Verify clean post-specific educational qualification for every canonical post")

def quality_gate(job: dict, facts: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    suspicious: list[str] = []
    verification: list[str] = []

    # A job cannot be sent to Qwen unless the core factual fields are present.
    required = [
        "organisation", "post", "advertisement_number", "published_date",
        "total_vacancies", "application_start", "application_end",
        "age_limit", "eligibility",
    ]

    for field in required:
        if _is_missing(facts.get(field)):
            errors.append(f"Missing required fact: {field}")

    for field in OPTIONAL:
        if _is_missing(facts.get(field)):
            warnings.append(f"Optional fact not extracted: {field}")

    links = facts.get("official_links") or []
    if not links:
        errors.append("No official notification link extracted")
    elif not any(str(x.get("url", "")).startswith("http") for x in links if isinstance(x, dict)):
        errors.append("Official notification links are present but no usable URL was extracted")

    total = _numeric(facts.get("total_vacancies"))
    title_candidate = _numeric(facts.get("total_vacancies_candidate") or facts.get("title_vacancy_candidate"))
    derived = facts.get("derived_vacancy_sum")

    # If official verification supplied canonical reconciled post vacancies,
    # validate that canonical list and never trust raw parser totals downstream.
    canonical = facts.get("post_vacancies")
    official = facts.get("official_verification") or {}
    if canonical:
        canonical_sum = sum(int(x.get("vacancies") or 0) for x in canonical if isinstance(x, dict))
        if total is not None and canonical_sum != total:
            errors.append(f"Canonical post_vacancies sum {canonical_sum} differs from total_vacancies {total}")
        expected = official.get("authoritative_expected_total")
        if expected is not None and canonical_sum != int(expected):
            errors.append(f"Canonical post_vacancies sum {canonical_sum} differs from authoritative total {expected}")

    if total is None and title_candidate is not None:
        warnings.append(f"Title contains candidate vacancy count {title_candidate}; verify against official vacancy table")
        verification.append(f"Verify total vacancies against official vacancy table; title candidate={title_candidate}")
    elif total is None:
        verification.append("Verify total vacancies from official notification")

    if derived is not None and total is not None and derived != total:
        errors.append(f"Vacancy-row sum {derived} differs from total_vacancies {total}")
    elif derived is None and total is not None:
        warnings.append("No post-wise vacancy table total was derived from DOCX; verify against official notification")
        verification.append("Verify post-wise vacancy total against official notification")

    # Candidates recovered from the document are never silently promoted to verified facts.
    if _is_missing(facts.get("advertisement_number")):
        verification.append("Verify advertisement/reference number from official notification")
    if _is_missing(facts.get("application_start")):
        verification.append("Verify application start date from official notification")
    if _is_missing(facts.get("application_end")):
        candidate = facts.get("application_end_candidate")
        if not _is_missing(candidate):
            warnings.append(f"Application end candidate detected: {candidate}; verify against official notification")
        verification.append("Verify application end date from official notification")
    if _is_missing(facts.get("age_limit")):
        verification.append("Verify age limit from official notification")
    if _is_missing(facts.get("eligibility")):
        verification.append("Verify educational qualification/experience from official notification")

    age = _norm(facts.get("age_limit"))
    if age and any(x in age.lower() for x in ("advt. no", "recruitment online form", "short details of notification", "selection procedure", "pay scale")):
        errors.append("Suspicious age_limit content; field appears contaminated")
        suspicious.append("age_limit")

    for field in ("application_fee", "eligibility", "selection_process", "pay_scale", "important_dates", "how_to_apply"):
        value = _norm(facts.get(field))
        low = value.lower()
        if value and ("short details of notification" in low or "rajasthan energy various post recruitment online form" in low):
            errors.append(f"Contaminated {field} field detected")
            suspicious.append(field)

    # Generic DOCX placeholders are not verified eligibility/selection facts.
    for field in ("eligibility", "selection_process"):
        value = _norm(facts.get(field))
        low = value.lower()
        if value and ("read the notification" in low or "post information, selection procedure" in low or "selection procedure, details, age limit" in low):
            errors.append(f"Unverified placeholder content in {field}")
            suspicious.append(field)

    # V1.9.8: post-specific eligibility is a hard safety requirement.
    _post_fact_quality(facts, errors, suspicious, verification)

    # If every required field is verified and the vacancy table reconciles, PASS.
    # Otherwise the gate blocks Qwen. Candidates and missing fields remain verification work.
    verification_required = bool(verification)
    status = "PASS" if not errors and not verification_required else "FAIL"
    if verification_required and not errors:
        warnings.append("Official-notification verification is required before Qwen generation")

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "suspicious_fields": sorted(set(suspicious)),
        "verification_required": verification_required,
        "verification_items": verification,
        "required_fields": required,
        "missing_required": [f for f in required if _is_missing(facts.get(f))],
        "optional_missing": [f for f in OPTIONAL if _is_missing(facts.get(f))],
    }
