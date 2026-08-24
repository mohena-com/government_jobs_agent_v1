from src.llm.slide_quality_gate import slide_quality_gate


def facts():
    return {
        "organisation": "Rajasthan Rajya Vidyut Utpadan Nigam Ltd. (RVUNL)",
        "post": "RVUNL Recruitment 2026-27",
        "advertisement_number": "RVUN/Rectt.-2026-27/02; RVUN/Rectt.-2026-27/03",
        "published_date": "2026-08-04",
        "total_vacancies": "2005",
        "application_start": "2026-08-05",
        "application_end": "2026-08-25",
        "age_limit": "18-43 years",
        "eligibility": "Graduation / Senior Secondary as post-specific",
        "pay_scale": "Level-10 and Level-5",
        "selection_process": "Computer based competitive examination; Junior Assistant includes a typing test.",
        "application_fee": "General: ₹1000; EWS/BC/MBC/SC/ST/PwBD: ₹500",
        "official_links": [{"url": "https://example.gov.in/a.pdf"}],
        "post_vacancies": [
            {"post": "Junior Engineer-I (Electrical)", "vacancies": 727},
            {"post": "Junior Engineer-I (Mechanical)", "vacancies": 110},
            {"post": "Junior Engineer-I (Civil)", "vacancies": 32},
            {"post": "Junior Accountant", "vacancies": 371},
            {"post": "Junior Assistant/ Commercial Assistant-II", "vacancies": 765},
        ],
    }


def test_blocks_unsupported_document_verification_claim():
    plan = {"slides": [{"number": 1, "type": "selection", "headline": "Selection Process", "subtitle": "", "bullets": ["Final selection is based on written exam and document verification"], "facts_used": []}]}
    result = slide_quality_gate(plan, facts())
    assert result["status"] == "FAIL"
    assert any("document verification" in e.lower() for e in result["errors"])


def test_blocks_stale_ended_wording_before_deadline():
    plan = {"slides": [{"number": 1, "type": "content", "headline": "Application Details", "subtitle": "", "bullets": ["Application ended on August 25, 2026."], "facts_used": []}]}
    result = slide_quality_gate(plan, facts())
    assert result["status"] == "FAIL"
    assert any("stale application-status" in e.lower() for e in result["errors"])


def test_allows_verified_vacancy_numbers_and_2026_27_identifier():
    slides = [
        {"number": 1, "type": "job_details", "headline": "JOB DETAILS", "subtitle": "Vacancy & eligibility", "bullets": [
            "Junior Engineer-I (Electrical): 727", "Junior Engineer-I (Mechanical): 110", "Junior Engineer-I (Civil): 32",
            "Junior Accountant: 371", "Junior Assistant/ Commercial Assistant-II: 765", "Total vacancies: 2005",
            "Age: 18-43 years; Selection: Computer based competitive examination; typing test for Junior Assistant"], "facts_used": []},
        {"number": 2, "type": "at_a_glance", "headline": "AT A GLANCE", "subtitle": "Pay, fee & dates", "bullets": [
            "Qualification: Graduation / Senior Secondary as post-specific", "Pay: Level-10 and Level-5",
            "Application fee: ₹500-₹1000", "Applications: 05 August 2026 to 25 August 2026",
            "Read the official notification before applying"],
            "links": [{"label": "Official Notification", "url": "https://example.gov.in/a.pdf"}], "facts_used": []},
    ]
    result = slide_quality_gate({"slides": slides}, facts())
    assert result["status"] == "PASS"
