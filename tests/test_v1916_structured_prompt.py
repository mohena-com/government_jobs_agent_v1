from src.llm.ollama_client import OllamaClient
from src.llm.slide_quality_gate import _norm

def test_fixed_schema_has_positional_slide_types():
    schema = OllamaClient._six_slide_schema()
    assert list(schema["properties"]) == ["slide_1","slide_2","slide_3","slide_4","slide_5","slide_6"]
    expected = ["title","vacancies","eligibility","age_pay_fee","dates_selection","apply_links"]
    for key, kind in zip(schema["properties"], expected):
        assert schema["properties"][key]["properties"]["type"]["enum"] == [kind]

def test_post_name_normalization_handles_slash_spacing():
    assert _norm("Junior Assistant/Commercial Assistant-II") == _norm("Junior Assistant / Commercial Assistant-II")
