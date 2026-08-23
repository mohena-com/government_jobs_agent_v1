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
        "post_facts": [
            {"post": "Junior Engineer-I (Electrical)", "qualification": "Verified"},
            {"post": "Junior Engineer-I (Mechanical)", "qualification": "Verified"},
            {"post": "Junior Engineer-I (Civil)", "qualification": "Verified"},
            {"post": "Junior Accountant", "qualification": "Verified"},
            {"post": "Junior Assistant/ Commercial Assistant-II", "qualification": "Verified"},
        ],
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

def test_quality_gate_blocks_unverified_title_vacancy():
    job = {"title": "RVUNL Recruitment 2026 Apply Online for 2005 Post"}
    facts = {
        "organisation": "Rajasthan Rajya Vidyut Utpadan Nigam Ltd. (RVUNL)",
        "post": job["title"],
        "published_date": "05 August 2026",
        "official_links": [{"label": "Official Notification", "url": "https://example.gov.in/n.pdf"}],
        "total_vacancies": "",
        "total_vacancies_candidate": "2005",
        "title_vacancy_candidate": "2005",
        "application_start": "",
        "application_end": "",
        "application_end_candidate": "25 August 2026",
        "age_limit": "",
        "eligibility": "",
    }
    result = quality_gate(job, facts)
    assert result["status"] == "FAIL"
    assert result["verification_required"] is True
    assert any("2005" in x for x in result["verification_items"])


def test_quality_gate_accepts_canonical_reconciled_post_vacancies():
    facts = {
        "organisation": "Rajasthan Rajya Vidyut Utpadan Nigam Ltd. (RVUNL)",
        "post": "RVUNL Common Recruitment 2026",
        "advertisement_number": "RVUN/Rectt.-2026-27/02; RVUN/Rectt.-2026-27/03",
        "published_date": "04 August 2026",
        "total_vacancies": "2005",
        "application_start": "2026-08-05",
        "application_end": "2026-08-25",
        "age_limit": "Advertisement-specific age rules",
        "eligibility": "Verified from official advertisements",
        "official_links": [{"url": "https://example.gov.in/a.pdf"}],
        "post_vacancies": [
            {"post": "JE Electrical", "vacancies": 727},
            {"post": "JE Mechanical", "vacancies": 110},
            {"post": "JE Civil", "vacancies": 32},
            {"post": "Junior Accountant", "vacancies": 371},
            {"post": "Junior Assistant/ Commercial Assistant-II", "vacancies": 765},
        ],
        "official_verification": {"authoritative_expected_total": 2005},
        "derived_vacancy_sum": 2005,
        "selection_process": "",
        "post_facts": [
            {"post": "Junior Engineer-I (Electrical)", "qualification": "Verified"},
            {"post": "Junior Engineer-I (Mechanical)", "qualification": "Verified"},
            {"post": "Junior Engineer-I (Civil)", "qualification": "Verified"},
            {"post": "Junior Accountant", "qualification": "Verified"},
            {"post": "Junior Assistant/ Commercial Assistant-II", "qualification": "Verified"},
        ],
    }
    result = quality_gate({}, facts)
    assert result["status"] == "PASS"
    assert result["errors"] == []


def test_quality_gate_blocks_generic_selection_placeholder():
    facts = {
        "organisation": "RVUNL", "post": "Recruitment", "advertisement_number": "A/1",
        "published_date": "04 August 2026", "total_vacancies": "10",
        "application_start": "2026-08-05", "application_end": "2026-08-25",
        "age_limit": "18-40", "eligibility": "Graduation",
        "official_links": [{"url": "https://example.gov.in/a.pdf"}],
        "selection_process": ". Read the notification for RVUNL eligibility, post information, selection procedure, Details, age limit, pay scale and all other information.",
    }
    result = quality_gate({}, facts)
    assert result["status"] == "FAIL"
    assert "selection_process" in result["suspicious_fields"]
