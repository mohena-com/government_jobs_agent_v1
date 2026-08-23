from datetime import date
from pathlib import Path
import json
import sys


def test_selector_script_can_import_workspace_src(monkeypatch):
    # Simulate direct execution where sys.path initially contains scripts/, not root.
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "select_today_jobs.py"
    namespace = {"__file__": str(script), "__name__": "not_main"}
    code = compile(script.read_text(encoding="utf-8"), str(script), "exec")
    exec(code, namespace)
    assert "read_docx" in namespace


def test_published_today_does_not_truncate_before_filter(monkeypatch):
    from src.sarkariresult import pipeline

    listings = [
        {"title": f"Older {i}", "url": f"https://example.com/{i}", "last_date": "2026-12-01"}
        for i in range(5)
    ]
    listings.append({"title": "Fresh Recruitment", "url": "https://example.com/fresh", "last_date": "2026-12-01"})

    monkeypatch.setattr(pipeline, "find_latest_listings", lambda today: listings)
    monkeypatch.setattr(pipeline, "extract_detail", lambda url, listing: {
        "listing": listing,
        "post_update": "23 August 2026 | 10:00 AM" if listing["title"] == "Fresh Recruitment" else "22 August 2026 | 10:00 AM",
    })

    _, results = pipeline.crawl(max_jobs=1, published_on=date(2026, 8, 23))
    assert len(results) == 1
    assert results[0]["listing"]["title"] == "Fresh Recruitment"


def test_detail_same_line_post_date_update():
    from bs4 import BeautifulSoup
    from src.sarkariresult.detail import extract_structured_page

    soup = BeautifulSoup("<html><body><h1>Test Recruitment</h1></body></html>", "lxml")
    result = extract_structured_page(soup, "Post Date / Update: 23 August 2026 | 09:30 AM\nShort Information\nTest")
    assert result["post_update"] == "23 August 2026 | 09:30 AM"
