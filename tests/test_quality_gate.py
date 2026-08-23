from src.docx.quality_gate import quality_gate


def test_quality_gate_passes_complete_record():
    facts = {
        "organisation": "Rajasthan Rajya Vidyut Utpadan Nigam Ltd. (RVUNL)",
        "post": "Rajasthan RVUNL Recruitment 2026",
        "advertisement_number": "BULUN/Rectt 3036-27/01",
        "published_date": "05 August 2026",
        "total_vacancies": "2005",
        "application_start": "10 August 2026",
        "application_end": "25 August 2026",
        "age_limit": "18-40 years",
        "eligibility": "As per notification",
        "official_links": [{"label": "Official Notification", "url": "https://example.gov.in/a.pdf"}],
        "title_vacancy_candidate": "2005",
        "derived_vacancy_sum": 2005,
    }
    result = quality_gate({}, facts)
    assert result["status"] == "PASS"
    assert result["errors"] == []


def test_quality_gate_blocks_rvunl_like_bad_record():
    facts = {
        "organisation": "",
        "post": "Rajasthan RVUNL for JE, Junior Accountant & Junior Assistant/ Commercial Assistant-II Common Recruitment 2026 Apply Online for 2005 Post",
        "advertisement_number": "Not found",
        "published_date": "05 August 2026 | 11:13 PM",
        "total_vacancies": "Not found",
        "application_start": "Not found",
        "application_end": "Not found",
        "age_limit": "Advt. No. BULUN/Rectt 3036-27/01 : Short Details of Notification",
        "eligibility": "",
        "official_links": [{"label": "Official Notification", "url": "https://example.gov.in/a.pdf"}],
        "title_vacancy_candidate": "2005",
    }
    result = quality_gate({}, facts)
    assert result["status"] == "FAIL"
    assert "organisation" in result["missing_required"]
    assert "total_vacancies" in result["missing_required"]
    assert "age_limit" in result["suspicious_fields"]
