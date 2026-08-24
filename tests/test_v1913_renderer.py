import json
from src.social.qwen_renderer import render_qwen_plan


def test_qwen_renderer_creates_six_images_without_qa_text(tmp_path):
    plan = {
        "jobs": [{
            "job_index": 1,
            "presentation_ready": True,
            "locked_facts": {
                "organisation": "RVUNL", "total_vacancies": "2005",
                "application_start": "2026-08-05", "application_end": "2026-08-25",
                "age_limit": "18-43 years", "pay_scale": "Level-10 and Level-5",
                "application_fee": "General: ₹1000; reserved: ₹500",
                "post_vacancies": [
                    {"post": "Junior Engineer-I (Electrical)", "vacancies": 727},
                    {"post": "Junior Engineer-I (Mechanical)", "vacancies": 110},
                ],
            },
            "slide_plan": {"slides": [
                {"number": 1, "type": "title", "headline": "RECRUITMENT 2026", "subtitle": "RVUNL", "bullets": ["Total vacancies: 2005"], "facts_used": []},
                {"number": 2, "type": "vacancies", "headline": "VACANCY BREAKDOWN", "subtitle": "Post-wise", "bullets": ["Junior Engineer-I (Electrical): 727"], "facts_used": []},
                {"number": 3, "type": "eligibility", "headline": "WHO CAN APPLY?", "subtitle": "Qualification", "bullets": ["Engineering degree required"], "facts_used": []},
                {"number": 4, "type": "age_pay_fee", "headline": "AT A GLANCE", "subtitle": "Age, pay and fee", "bullets": ["Age: 18-43 years", "Pay: Level-10 and Level-5", "Application fee: ₹500-₹1000"], "facts_used": []},
                {"number": 5, "type": "dates_selection", "headline": "IMPORTANT DATES", "subtitle": "Dates and selection", "bullets": ["Application: 05 August 2026 to 25 August 2026", "Selection: Computer based examination"], "facts_used": []},
                {"number": 6, "type": "apply_links", "headline": "READY TO APPLY", "subtitle": "Apply online", "bullets": ["Read the official notification", "Apply online before 25 August 2026"], "links": [{"label": "Official Notification", "url": "https://example.gov.in/a.pdf"}], "facts_used": []},
            ]},
        }]
    }
    src = tmp_path / "plan.json"
    src.write_text(json.dumps(plan), encoding="utf-8")
    assets = render_qwen_plan(src, tmp_path / "out")
    assert len(assets) == 6
    assert all(p.exists() for p in assets)
