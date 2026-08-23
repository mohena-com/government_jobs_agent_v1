from src.llm.ollama_client import OllamaClient


def test_client_defaults():
    c = OllamaClient(host="http://webmaster-ai.local:11434", model="qwen3:8b")
    assert c.host == "http://webmaster-ai.local:11434"
    assert c.model == "qwen3:8b"
