from src.llm.ollama_client import parse_json_content


def test_parse_json_content():
    assert parse_json_content('{"slides": []}') == {"slides": []}
    assert parse_json_content('```json\n{"slides": []}\n```') == {"slides": []}
from src.llm.validator import validate_slide_plan


def test_numeric_guardrail():
    facts = {"vacancies": "94", "deadline": "24/08/2026"}
    plan = {"slides": [{"headline": "94 posts", "bullets": ["24/08/2026"]}]}
    assert validate_slide_plan(plan, facts) == []


def test_numeric_guardrail_flags_hallucination():
    facts = {"vacancies": "94"}
    plan = {"slides": [{"headline": "95 posts", "bullets": []}]}
    warnings = validate_slide_plan(plan, facts)
    assert any("95" in x for x in warnings)
