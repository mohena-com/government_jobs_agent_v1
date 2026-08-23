from src.llm.validator import validate_slide_plan


def test_verified_nested_vacancy_numbers_are_accepted():
    facts = {
        "total_vacancies": "2005",
        "post_facts": [
            {"post": "Junior Engineer-I (Electrical)", "vacancies": 727},
            {"post": "Junior Engineer-I (Mechanical)", "vacancies": 110},
            {"post": "Junior Engineer-I (Civil)", "vacancies": 32},
            {"post": "Junior Accountant", "vacancies": 371},
            {"post": "Junior Assistant/ Commercial Assistant-II", "vacancies": 765},
        ],
        "official_verification": {"combined_vacancies": 2005},
    }
    plan = {"slides": [{"number": 3, "headline": "Vacancies", "subtitle": "2005 posts", "bullets": ["Electrical 727", "Mechanical 110", "Civil 32", "Accountant 371", "Assistant 765"], "facts_used": []}]}
    assert validate_slide_plan(plan, facts) == []
