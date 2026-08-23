from src.docx.quality_gate import quality_gate


def _base():
    return {
        "organisation": "Rajasthan Rajya Vidyut Utpadan Nigam Ltd. (RVUNL)",
        "post": "RVUNL Common Recruitment 2026",
        "advertisement_number": "RVUN/Rectt.-2026-27/02; RVUN/Rectt.-2026-27/03",
        "published_date": "2026-08-04",
        "total_vacancies": "2005",
        "application_start": "2026-08-05",
        "application_end": "2026-08-25",
        "age_limit": "Advertisement-specific age rules",
        "eligibility": "Verified from official advertisements",
        "official_links": [{"url": "https://example.gov.in/a.pdf"}],
        "post_vacancies": [
            {"post": "Junior Engineer-I (Electrical)", "vacancies": 727},
            {"post": "Junior Engineer-I (Mechanical)", "vacancies": 110},
            {"post": "Junior Engineer-I (Civil)", "vacancies": 32},
            {"post": "Junior Accountant", "vacancies": 371},
            {"post": "Junior Assistant/ Commercial Assistant-II", "vacancies": 765},
        ],
        "derived_vacancy_sum": 2005,
        "official_verification": {
            "status": "PASS",
            "authoritative_expected_total": 2005,
        },
    }


def test_v196_blocks_generic_boundary_eligibility_after_official_verification():
    facts = _base()
    facts["post_facts"] = [
        {
            "post": "Junior Engineer-I (Electrical)",
            "qualification": "Four year engineering degree in Electrical Engineering.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
        {
            "post": "Junior Engineer-I (Mechanical)",
            "qualification": "Four year engineering degree in Mechanical Engineering.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
        {
            "post": "Junior Engineer-I (Civil)",
            "qualification": "Four year engineering degree in Civil Engineering.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
        {
            "post": "Junior Accountant",
            "qualification": "Bachelor Degree in Commerce.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
        {
            "post": "Junior Assistant/ Commercial Assistant-II",
            "qualification": "Read the notification for eligibility.",
            "source_method": "GENERIC_BOUNDARY",
        },
    ]
    result = quality_gate({}, facts)
    assert result["status"] == "FAIL"
    assert "post_eligibility" in result["suspicious_fields"]
    assert any("Junior Assistant" in x for x in result["errors"])


def test_v196_passes_when_all_canonical_posts_have_explicit_post_boundary_facts():
    facts = _base()
    facts["post_facts"] = [
        {
            "post": "Junior Engineer-I (Electrical)",
            "qualification": "Four year engineering degree in Electrical Engineering.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
        {
            "post": "Junior Engineer-I (Mechanical)",
            "qualification": "Four year engineering degree in Mechanical Engineering.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
        {
            "post": "Junior Engineer-I (Civil)",
            "qualification": "Four year engineering degree in Civil Engineering.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
        {
            "post": "Junior Accountant",
            "qualification": "Bachelor Degree in Commerce.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
        {
            "post": "Junior Assistant/ Commercial Assistant-II",
            "qualification": "10+2 Intermediate and computer qualification.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
    ]
    result = quality_gate({}, facts)
    assert result["status"] == "PASS"
    assert result["errors"] == []


def test_v196_blocks_partial_post_fact_coverage():
    facts = _base()
    facts["post_facts"] = [
        {
            "post": "Junior Engineer-I (Electrical)",
            "qualification": "Engineering degree.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
        {
            "post": "Junior Engineer-I (Mechanical)",
            "qualification": "Engineering degree.",
            "source_method": "RVUNL_POST_BOUNDARY",
        },
    ]
    result = quality_gate({}, facts)
    assert result["status"] == "FAIL"
    assert "post_eligibility" in result["suspicious_fields"]
    assert any("Missing post-specific eligibility" in x for x in result["errors"])
