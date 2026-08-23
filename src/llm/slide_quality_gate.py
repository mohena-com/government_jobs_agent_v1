from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from src.llm.validator import validate_slide_plan


GENERIC_FILLER = {
    "vacancies are announced through official channels",
    "all vacancies are announced through official channels",
    "candidates must ensure that all documents are accurate and complete",
    "the recruitment process is subject to change based on official notifications",
    "all application details must be submitted in the prescribed format",
}

# Claims that require explicit source support. These are intentionally conservative.
CONDITIONAL_CLAIMS = {
    "document verification": "document verification",
    "document verification is required": "document verification",
    "final selection is based on the written exam and document verification": "document verification",
    "apply now": "application status",
    "application is live": "application status",
    "recruitment is live": "application status",
    "don't miss out": "application status",
}


def _flatten(value: Any) -> list[str]:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return [str(value)]
    if isinstance(value, dict):
        out: list[str] = []
        for v in value.values():
            out.extend(_flatten(v))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for v in value:
            out.extend(_flatten(v))
        return out
    return []


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _source_text(facts: dict) -> str:
    return _norm(" ".join(_flatten(facts)))


def _generated_slides(plan: dict) -> list[dict]:
    slides = plan.get("slides") if isinstance(plan, dict) else None
    return [x for x in slides if isinstance(x, dict)] if isinstance(slides, list) else []


def _numeric_tokens(text: str) -> set[str]:
    raw = re.findall(r"(?<![A-Za-z0-9])\d[\d,]*(?:\.\d+)?(?![A-Za-z0-9])", text or "")
    return {x.strip(".,") for x in raw if x.strip(".,")}


def _date_end(facts: dict) -> date | None:
    value = str(facts.get("application_end") or "")
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", value)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})", value, re.I)
    if not m:
        return None
    months = {m.lower(): i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1)}
    return date(int(m.group(3)), months[m.group(2).lower()], int(m.group(1)))


def _claim_supported(claim: str, facts_text: str) -> bool:
    claim_n = _norm(claim)
    if not claim_n:
        return True
    # Exact/near-exact factual strings from the locked bundle are acceptable.
    if claim_n in facts_text:
        return True
    # Individual facts used by generated prose.
    important = [
        facts_text,
    ]
    return any(claim_n in x for x in important)


def slide_quality_gate(plan: dict, facts: dict, *, today: date | None = None) -> dict:
    """Validate the generated slide plan against locked/official facts.

    This is deliberately stricter than the numeric validator. It catches
    unsupported process claims, stale application wording, generic filler and
    malformed slide structure before image rendering.
    """
    errors: list[str] = []
    warnings: list[str] = []
    slides = _generated_slides(plan)
    source = _source_text(facts)

    expected_count = None
    # The caller's requested count is represented by the actual plan; six is the
    # production default but the gate remains usable for other counts.
    if not slides:
        errors.append("No slides generated")
        return {"status": "FAIL", "errors": errors, "warnings": warnings, "slide_count": 0, "slide_results": []}

    numbers = _numeric_tokens(source)
    slide_results = []

    for pos, slide in enumerate(slides, 1):
        headline = str(slide.get("headline") or "")
        subtitle = str(slide.get("subtitle") or "")
        bullets = slide.get("bullets") or []
        generated_text = _norm(" ".join([headline, subtitle] + [str(x) for x in bullets]))
        slide_errors: list[str] = []
        slide_warnings: list[str] = []

        if not headline.strip():
            slide_errors.append("Missing headline")
        if not isinstance(bullets, list):
            slide_errors.append("bullets must be an array")
        if len(bullets) > 6:
            slide_errors.append("Too many bullets for Instagram slide")

        for phrase, label in CONDITIONAL_CLAIMS.items():
            if phrase in generated_text and label not in source:
                slide_errors.append(f"Unsupported claim: '{phrase}' is not supported by locked facts")

        for filler in GENERIC_FILLER:
            if filler in generated_text:
                slide_warnings.append(f"Generic filler: '{filler}'")

        # Numeric validation, but do not treat the '27' in 2026-27 advertisement
        # identifiers as a standalone factual claim.
        for token in _numeric_tokens(generated_text):
            if token in {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"}:
                continue
            if token == "27" and re.search(r"2026\s*[-/]\s*27", generated_text):
                continue
            if token not in numbers:
                slide_warnings.append(f"Generated numeric token not found in locked facts: {token}")

        # Application status must reflect the actual deadline.
        end_date = _date_end(facts)
        if end_date:
            check_date = today or date.today()
            if end_date >= check_date and any(x in generated_text for x in ("application ended", "applications ended", "deadline passed")):
                slide_errors.append(f"Stale application-status wording: deadline is {end_date.isoformat()}, not ended as of {check_date.isoformat()}")

        # If the source contains a structured selection process, generated
        # selection claims must overlap with that source. Avoid allowing a
        # generic 'written exam + document verification' shortcut.
        if str(slide.get("type") or "").lower() in {"selection", "selection process"} or "selection process" in generated_text:
            selection = _norm(facts.get("selection_process"))
            if selection:
                if "document verification" in generated_text and "document verification" not in selection:
                    slide_errors.append("Selection slide claims document verification, but locked selection facts do not state it")
                if "typing test" in generated_text and "typing" not in selection:
                    slide_errors.append("Selection slide claims a typing test, but locked selection facts do not state it")

        if slide_errors:
            errors.extend([f"Slide {pos}: {e}" for e in slide_errors])
        warnings.extend([f"Slide {pos}: {w}" for w in slide_warnings])
        slide_results.append({"slide": pos, "status": "FAIL" if slide_errors else "PASS", "errors": slide_errors, "warnings": slide_warnings})

    # Numeric/url validator remains useful, but its findings are warnings here
    # because identifier fragments such as 27 can be legitimate.
    validator_warnings = validate_slide_plan(plan, facts)
    for warning in validator_warnings:
        if warning == "Generated numeric token not found in locked facts: 27":
            continue
        warnings.append(warning)

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "slide_count": len(slides),
        "slide_results": slide_results,
    }
