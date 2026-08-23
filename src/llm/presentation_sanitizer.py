from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
from typing import Any

QA_PATTERNS = [
    re.compile(r"^\s*(?:status|quality\s*gate|slide\s*quality\s*gate)\s*:\s*(?:pass|fail)\b.*$", re.I),
    re.compile(r"^\s*(?:all\s+)?(?:dates|totals|facts|numbers).*\b(?:consistent|verified|validated)\b.*(?:official|source|facts).*$", re.I),
    re.compile(r"^\s*(?:verified|verification|validation|validated|quality\s+check|quality-check)\b.*(?:official|source|facts|pass|fail).*$", re.I),
    re.compile(r"^\s*(?:facts?[_ ]?used|validation[_ ]?warnings?|verification[_ ]?items?)\s*[:=].*$", re.I),
    re.compile(r"^\s*(?:vacancy\s+reconciliation|extraction\s+repairs|parsed\s+vacancies|authoritative\s+vacancies)\b.*$", re.I),
    re.compile(r"^\s*(?:issues?\s+with\s+pdf|pdf\s+extraction|extraction\s+dropped\s+rows)\b.*$", re.I),
]

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


def _is_qa_line(text: str) -> bool:
    t = str(text or "").strip()
    if not t:
        return False
    return any(p.match(t) for p in QA_PATTERNS)


def _format_date(value: str) -> str:
    m = re.fullmatch(r"\s*(20\d{2})-(\d{2})-(\d{2})\s*", str(value or ""))
    if not m:
        return str(value)
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").strftime("%d %B %Y")
    except ValueError:
        return str(value)


def _clean_text(text: str) -> str:
    text = str(text or "").strip()
    # Never render markdown hyperlinks as text. Links are carried separately as structured data.
    text = MARKDOWN_LINK_RE.sub(r"\1", text)
    text = re.sub(r"\b20\d{2}-\d{2}-\d{2}\b", lambda m: _format_date(m.group(0)), text)
    text = re.sub(r"\s*\(?status\s*:\s*(?:pass|fail)\)?\s*$", "", text, flags=re.I)
    text = re.sub(r"\s*\(?quality\s*gate\s*:\s*(?:pass|fail)\)?\s*$", "", text, flags=re.I)
    return re.sub(r"\s{2,}", " ", text).strip()


def sanitize_slide_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Create presentation-facing copy while retaining structured links separately."""
    out = deepcopy(plan or {})
    slides = out.get("slides")
    if not isinstance(slides, list):
        return out

    for slide in slides:
        if not isinstance(slide, dict):
            continue
        for key in ("headline", "subtitle"):
            if isinstance(slide.get(key), str):
                cleaned = _clean_text(slide[key])
                if _is_qa_line(cleaned):
                    cleaned = ""
                slide[key] = cleaned

        bullets = slide.get("bullets")
        if isinstance(bullets, list):
            cleaned_bullets = []
            for bullet in bullets:
                text = _clean_text(bullet)
                if text and not _is_qa_line(text):
                    cleaned_bullets.append(text)
            slide["bullets"] = cleaned_bullets

        # facts_used remains audit metadata and is never rendered.
        if isinstance(slide.get("facts_used"), list):
            slide["facts_used"] = [str(x) for x in slide["facts_used"]]

        # Normalize structured links; never turn them into artwork text.
        links = slide.get("links")
        if isinstance(links, list):
            normalized = []
            for link in links:
                if isinstance(link, dict) and link.get("url"):
                    normalized.append({
                        "label": _clean_text(link.get("label") or "Official Link"),
                        "url": str(link["url"]).strip(),
                    })
            slide["links"] = normalized

    return out
