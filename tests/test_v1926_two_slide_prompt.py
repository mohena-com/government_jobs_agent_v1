from src.llm.ollama_client import OllamaClient


def test_v1926_schema_is_exactly_two_slides():
    schema = OllamaClient._two_slide_schema()
    assert list(schema["properties"]) == ["slide_1", "slide_2"]
    assert schema["properties"]["slide_1"]["properties"]["type"]["enum"] == ["job_details"]
    assert schema["properties"]["slide_2"]["properties"]["type"]["enum"] == ["at_a_glance"]
