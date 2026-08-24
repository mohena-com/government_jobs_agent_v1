from src.docx.reader import read_docx, to_locked_facts
from src.social.qwen_instagram import _crosscheck_application_dates
from src.llm.slide_quality_gate import slide_quality_gate


def test_patan_docx_recovers_application_window():
    path = "/mnt/data/00d62238-b8b6-46e1-b0b6-9c9054a0ad13.docx"
    data = read_docx(path)
    assert data["job_count"] == 1
    job = data["jobs"][0]
    facts = to_locked_facts(job)
    assert facts["application_start"] == "28 July 2026"
    assert facts["application_end"] == "27 August 2026"
    assert _crosscheck_application_dates(facts, job)["status"] == "PASS"


def test_wrong_application_date_fails_slide_gate():
    facts = {
        "application_start": "28 July 2026",
        "application_end": "27 August 2026",
        "selection_process": "Online Test, Interview",
        "official_links": [],
    }
    slides = []
    kinds = ["title", "vacancies", "eligibility", "age_pay_fee", "dates_selection", "apply_links"]
    for i, kind in enumerate(kinds, 1):
        bullets = []
        if i == 5:
            bullets = ["Application Start: 6 August 2026", "Deadline: 27 July 2007", "Selection: Online Test"]
        slides.append({"number": i, "type": kind, "headline": kind, "subtitle": "", "bullets": bullets})
    result = slide_quality_gate({"slides": slides}, facts)
    assert result["status"] == "FAIL"
    assert any("not supported by locked application dates" in x for x in result["errors"])
