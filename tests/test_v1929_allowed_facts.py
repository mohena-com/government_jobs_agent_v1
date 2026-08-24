from src.llm.allowed_facts import build_allowed_facts, fatal_generation_errors


def test_missing_fields_become_fallbacks_without_fabricating_values():
    facts = {
        "organisation": "Example Board",
        "post": "Assistant",
        "advertisement_number": "",
        "eligibility": "Read the notification for eligibility",
        "application_end": "2026-09-01",
        "total_vacancies": "",
    }
    allowed, fallbacks = build_allowed_facts(facts)
    assert allowed["advertisement_number"] == ""
    assert allowed["total_vacancies"] == ""
    assert allowed["eligibility"] == ""
    assert fallbacks["advertisement_number"] == "Refer to Official Notification"
    assert fallbacks["total_vacancies"] == "Refer to Official Notification"
    assert "source" not in allowed


def test_only_direct_vacancy_conflicts_are_fatal():
    assert fatal_generation_errors({"errors": ["Canonical post_vacancies sum 10 differs from total_vacancies 12"]})
    assert fatal_generation_errors({"errors": ["Missing required fact: age_limit"]}) == []
    assert fatal_generation_errors({"errors": ["Unverified placeholder content in eligibility"]}) == []
