from src.llm.ollama_client import OllamaClient
from src.llm.slide_quality_gate import _norm

def test_fixed_schema_has_two_positional_slide_types():
    schema = OllamaClient._two_slide_schema()
    assert list(schema["properties"]) == ["slide_1", "slide_2"]
    expected = ["job_details", "at_a_glance"]
    for key, kind in zip(schema["properties"], expected):
        assert schema["properties"][key]["properties"]["type"]["enum"] == [kind]

def test_post_name_normalization_handles_slash_spacing():
    assert _norm("Junior Assistant/Commercial Assistant-II") == _norm("Junior Assistant / Commercial Assistant-II")
