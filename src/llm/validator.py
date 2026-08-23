from __future__ import annotations

import re
from typing import Any


def _flatten_strings(value: Any) -> list[str]:
    out = []
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        out.append(str(value))
    elif isinstance(value, dict):
        for v in value.values():
            out.extend(_flatten_strings(v))
    elif isinstance(value, list):
        for v in value:
            out.extend(_flatten_strings(v))
    return out


def _tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"\d+(?:[.,/]\d+)*", text or "") if x}


def validate_slide_plan(plan: dict, facts: dict) -> list[str]:
    """Conservative factual guardrail.

    It flags numeric/date/url claims that do not appear in the locked source
    facts. It does not attempt to prove prose semantics.
    """
    source = " ".join(_flatten_strings(facts))
    generated = " ".join(_flatten_strings(plan))
    warnings = []

    source_numbers = _tokens(source)
    for token in sorted(_tokens(generated)):
        # Ignore slide numbering and common formatting numbers.
        if token in {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10"}:
            continue
        if token not in source_numbers:
            warnings.append(f"Generated numeric token not found in locked facts: {token}")

    urls = re.findall(r"https?://[^\s\"\'}]+", generated)
    source_urls = {u.rstrip(".,);]}\"") for u in re.findall(r"https?://[^\s\"\'}]+", source)}
    for url in urls:
        normalized = url.rstrip(".,);]}\"")
        if normalized not in source_urls:
            warnings.append(f"Generated URL not found in locked facts: {normalized}")

    return warnings
