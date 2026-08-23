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

CONDITIONAL_CLAIMS = {
    "document verification": "document verification",
    "typing test": "typing",
    "final selection is based on": "selection_process",
    "apply now": "application status",
    "application is live": "application status",
    "recruitment is live": "application status",
    "don't miss out": "application status",
}

EXPECTED_TYPES = ["title", "vacancies", "eligibility", "age_pay_fee", "dates_selection", "apply_links"]


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


def _post_names(facts: dict) -> list[str]:
    names = []
    for item in facts.get("post_vacancies") or facts.get("raw_post_vacancies") or []:
        if isinstance(item, dict) and item.get("post"):
            names.append(str(item["post"]))
    if not names:
        for item in facts.get("post_facts") or facts.get("post_eligibility") or []:
            if isinstance(item, dict) and item.get("post"):
                names.append(str(item["post"]))
    return list(dict.fromkeys(names))


def _combined_text(slides: list[dict]) -> str:
    parts = []
    for s in slides:
        parts.extend([str(s.get("headline") or ""), str(s.get("subtitle") or "")])
        parts.extend(str(x) for x in (s.get("bullets") or []))
    return _norm(" ".join(parts))


def _available_link_count(facts: dict) -> int:
    return sum(1 for x in (facts.get("official_links") or []) if isinstance(x, dict) and x.get("url"))


def slide_quality_gate(plan: dict, facts: dict, *, today: date | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    slides = _generated_slides(plan)
    source = _source_text(facts)

    if not slides:
        return {"status": "FAIL", "errors": ["No slides generated"], "warnings": [], "slide_count": 0, "slide_results": []}

    if len(slides) != 6:
        errors.append(f"Expected 6 presentation slides, generated {len(slides)}")

    numbers = _numeric_tokens(source)
    slide_results = []

    for pos, slide in enumerate(slides, 1):
        headline = str(slide.get("headline") or "")
        subtitle = str(slide.get("subtitle") or "")
        bullets = slide.get("bullets") or []
        generated_text = _norm(" ".join([headline, subtitle] + [str(x) for x in bullets]))
        slide_errors: list[str] = []
        slide_warnings: list[str] = []
        expected_type = EXPECTED_TYPES[pos - 1] if pos <= len(EXPECTED_TYPES) else None

        if not headline.strip():
            slide_errors.append("Missing headline")
        if not isinstance(bullets, list):
            slide_errors.append("bullets must be an array")
        if len(bullets) > 6:
            slide_errors.append("Too many bullets for Instagram slide")
        if expected_type and _norm(slide.get("type")) != expected_type:
            slide_errors.append(f"Expected slide type '{expected_type}', got '{slide.get('type')}'")

        for phrase, label in CONDITIONAL_CLAIMS.items():
            if phrase in generated_text and label not in source:
                slide_errors.append(f"Unsupported claim: '{phrase}' is not supported by locked facts")

        for filler in GENERIC_FILLER:
            if filler in generated_text:
                slide_warnings.append(f"Generic filler: '{filler}'")

        for token in _numeric_tokens(generated_text):
            if token in {str(i) for i in range(1, 13)}:
                continue
            if token == "27" and re.search(r"2026\s*[-/]\s*27", generated_text):
                continue
            if token not in numbers:
                slide_warnings.append(f"Generated numeric token not found in locked facts: {token}")

        end_date = _date_end(facts)
        if end_date:
            check_date = today or date.today()
            if end_date >= check_date and any(x in generated_text for x in ("application ended", "applications ended", "deadline passed")):
                slide_errors.append(f"Stale application-status wording: deadline is {end_date.isoformat()}, not ended as of {check_date.isoformat()}")

        if pos == 6:
            links = slide.get("links") or []
            if _available_link_count(facts) and not links:
                slide_errors.append("Slide 6 must contain structured official links; raw URLs must not be rendered as text")
            for link in links:
                if not isinstance(link, dict) or not link.get("url"):
                    slide_errors.append("Malformed structured link on slide 6")

        if slide_errors:
            errors.extend([f"Slide {pos}: {e}" for e in slide_errors])
        warnings.extend([f"Slide {pos}: {w}" for w in slide_warnings])
        slide_results.append({"slide": pos, "status": "FAIL" if slide_errors else "PASS", "errors": slide_errors, "warnings": slide_warnings})

    # Completeness: require all verified core facts to appear somewhere in the presentation.
    all_text = _combined_text(slides)
    total = str(facts.get("total_vacancies") or facts.get("combined_vacancies") or "")
    if total and re.sub(r"\D", "", total) not in re.sub(r"\D", "", all_text):
        errors.append(f"Completeness: total vacancies {total} missing from presentation")

    for post in _post_names(facts):
        # Compare normalized key phrase, tolerating minor punctuation differences.
        key = _norm(post).replace("/", " ")
        if key and key not in all_text.replace("/", " "):
            # Require the distinctive post label rather than exact long prose.
            distinctive = _norm(post.split("(")[0]).strip()
            if distinctive and distinctive not in all_text:
                errors.append(f"Completeness: verified post missing from presentation: {post}")

    if facts.get("eligibility") or facts.get("post_eligibility") or facts.get("post_facts"):
        if not any(k in all_text for k in ("eligib", "qualification", "degree", "diploma", "secondary")):
            errors.append("Completeness: eligibility/qualification information missing")

    if facts.get("age_limit"):
        if not any(k in all_text for k in ("age", "years")):
            errors.append("Completeness: age-limit information missing")

    if facts.get("pay_scale"):
        if not any(k in all_text for k in ("pay", "salary", "level")):
            errors.append("Completeness: pay/salary information missing")

    if facts.get("application_fee"):
        if not any(k in all_text for k in ("fee", "₹", "rs.", "rs ")):
            errors.append("Completeness: application-fee information missing")

    if facts.get("application_start") and facts.get("application_end"):
        if not ("application" in all_text and ("august" in all_text or "january" in all_text or "february" in all_text or "march" in all_text or "april" in all_text or "may" in all_text or "june" in all_text or "july" in all_text or "september" in all_text or "october" in all_text or "november" in all_text or "december" in all_text)):
            errors.append("Completeness: application dates missing")

    if facts.get("selection_process") and "selection" not in all_text and "exam" not in all_text and "written" not in all_text:
        errors.append("Completeness: selection-process information missing")

    validator_warnings = validate_slide_plan(plan, facts)
    for warning in validator_warnings:
        if warning == "Generated numeric token not found in locked facts: 27":
            continue
        warnings.append(warning)

    status = "PASS" if not errors else "FAIL"
    return {"status": status, "errors": errors, "warnings": warnings, "slide_count": len(slides), "slide_results": slide_results}
