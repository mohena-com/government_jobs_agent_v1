from __future__ import annotations

from copy import deepcopy
from typing import Any

MISSING = {"", "not found", "unknown", "n/a", "na", "none", "null"}

FALLBACKS = {
    "advertisement_number": "Refer to Official Notification",
    "total_vacancies": "Refer to Official Notification",
    "application_start": "Refer to Official Notification",
    "application_end": "Refer to Official Notification",
    "age_limit": "Refer to Official Notification",
    "eligibility": "Refer to Official Notification",
    "pay_scale": "Refer to Official Notification",
    "application_fee": "Refer to Official Notification",
    "selection_process": "Refer to Official Notification",
    "how_to_apply": "Refer to Official Notification",
    "important_dates": "Refer to Official Notification",
}

CONTAMINATED_MARKERS = (
    "short details of notification",
    "read the notification",
    "post information, selection procedure",
    "selection procedure, details, age limit",
    "rajasthan energy various post recruitment online form",
)


def _missing(value: Any) -> bool:
    if value is None:
        return True
    return str(value).strip().lower() in MISSING


def build_allowed_facts(facts: dict) -> tuple[dict, dict]:
    """Return presentation-safe facts and explicit fallbacks.

    Exact extracted/verified values are preserved. Missing or known contaminated
    fields are blanked in the presentation payload and mapped to a fallback label.
    Candidate-only and audit/provenance fields are not exposed to Qwen.
    """
    allowed = deepcopy(facts)
    fallbacks: dict[str, str] = {}

    for field, fallback in FALLBACKS.items():
        value = allowed.get(field)
        low = str(value or "").strip().lower()
        if _missing(value) or any(marker in low for marker in CONTAMINATED_MARKERS):
            allowed[field] = ""
            fallbacks[field] = fallback

    for key in list(allowed):
        if key.endswith("_candidate") or key.endswith("_source"):
            allowed.pop(key, None)

    for key in (
        "official_verification", "verification_items", "verification_required",
        "derived_vacancy_sum", "extraction_notes", "raw_post_vacancies", "source",
        "application_date_evidence", "application_dates_crosscheck",
        "application_dates_crosscheck_error", "application_dates_canonical",
    ):
        allowed.pop(key, None)

    allowed["presentation_fallbacks"] = fallbacks
    allowed["presentation_rule"] = (
        "Use exact available facts. When a field is unavailable, omit it or use "
        "the corresponding presentation_fallback. Never invent a value. Application "
        "start/end dates are semantically locked and must never be replaced by fee, "
        "exam, notification, or other dates."
    )
    return allowed, fallbacks


def fatal_generation_errors(gate: dict) -> list[str]:
    """Only direct numerical reconciliation conflicts are generation blockers."""
    fatal = []
    for err in gate.get("errors") or []:
        low = str(err).lower()
        if "differs from total_vacancies" in low:
            fatal.append(err)
        elif "differs from authoritative total" in low:
            fatal.append(err)
        elif "vacancy-row sum" in low and "differs" in low:
            fatal.append(err)
    return fatal
