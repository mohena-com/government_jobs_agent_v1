from src.llm.ollama_client import OllamaClient


def test_v1927_schema_replaces_two_slide_contract_with_six_slide_contract():
    schema = OllamaClient._six_slide_schema()
    assert len(schema["properties"]) == 6
    assert "slide_1" in schema["properties"] and "slide_6" in schema["properties"]
