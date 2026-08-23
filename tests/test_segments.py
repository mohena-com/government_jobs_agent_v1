from src.extract.segments import find_segments
from src.models import Page

def test_segments():
    pages = [
        Page(number=1, text="1. (Vacancy No. 26070901525)\nAgricultural Engineer\n1 vacancy"),
        Page(number=2, text="2. (Vacancy No. 26070902125)\nMedical Officer\n4 vacancies"),
        Page(number=3, text="end")
    ]
    s = find_segments(pages)
    assert len(s) == 2
    assert s[0]["vacancy_no"] == "26070901525"
    assert s[0]["start_page"] == 1
    assert s[1]["start_page"] == 2
