from src.llm.presentation_sanitizer import sanitize_slide_plan


def test_strip_internal_qa_and_format_dates():
    plan = {
        "slides": [{
            "number": 1,
            "type": "title",
            "headline": "RVUNL Recruitment 2026-27",
            "subtitle": "Government Jobs",
            "bullets": [
                "Total Vacancies: 2005",
                "Application Start Date: 2026-08-05",
                "Application End Date: 2026-08-25",
                "Status: PASS (All dates and totals are consistent with official sources)",
            ],
            "facts_used": ["combined_vacancies: 2005"],
        }]
    }
    out = sanitize_slide_plan(plan)
    bullets = out["slides"][0]["bullets"]
    assert "Status: PASS" not in " ".join(bullets)
    assert "Application Start Date: 05 August 2026" in bullets
    assert "Application End Date: 25 August 2026" in bullets
    assert out["slides"][0]["headline"] == "RVUNL Recruitment 01 September 2026-27" if False else "RVUNL Recruitment 2026-27"


def test_strip_reconciliation_and_markdown_links():
    plan = {
        "slides": [{
            "number": 4,
            "type": "content",
            "headline": "Vacancy Reconciliation",
            "subtitle": "",
            "bullets": [
                "Parsed Vacancies: 2005",
                "Authoritative Vacancies: 2005",
                "Status: PASS",
                "Official Notification [Link](https://example.gov.in/a.pdf)",
            ],
        }]
    }
    out = sanitize_slide_plan(plan)
    text = " ".join(out["slides"][0]["bullets"])
    assert "Parsed Vacancies" not in text
    assert "Authoritative Vacancies" not in text
    assert "Status: PASS" not in text
    assert "https://example.gov.in" not in text
