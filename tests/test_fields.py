from src.extract.fields import extract_segment

def test_basic_extraction():
    seg = {
        "vacancy_no": "26070901525",
        "start_page": 1,
        "end_page": 2,
        "text": """(Vacancy No. 26070901525)
        Agricultural Engineer
        1 vacancy
        Pay Level - 7
        Age limit: 35 years
        Essential Qualification: Degree in Engineering
        """
    }
    r = extract_segment(seg, "09/2026", "https://www.upsc.gov.in/sites/default/files/test.pdf")
    assert r.vacancy_no == "26070901525"
    assert r.total_vacancies == 1
    assert "Level" in r.pay_level
