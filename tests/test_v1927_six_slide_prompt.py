from src.llm.ollama_client import OllamaClient


def test_v1927_schema_is_exactly_six_slides():
    schema = OllamaClient._six_slide_schema()
    assert list(schema["properties"]) == [f"slide_{i}" for i in range(1, 7)]
    expected = ["title", "vacancies", "eligibility", "age_pay_fee", "dates_selection", "apply_links"]
    for i, kind in enumerate(expected, 1):
        assert schema["properties"][f"slide_{i}"]["properties"]["type"]["enum"] == [kind]
