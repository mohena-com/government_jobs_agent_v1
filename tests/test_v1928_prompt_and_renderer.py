from pathlib import Path

from src.llm.ollama_client import OllamaClient
from src.social.qwen_renderer import _section_bar

def test_prompt_file_exists_and_contains_creative_direction():
    text = Path("prompts_instagram_v1.9.28.txt").read_text(encoding="utf-8")
    assert "NAVY/BLUE" in text
    assert "YELLOW/GOLD" in text
    assert "EXACT SIX-SLIDE CONTRACT" in text

def test_prompt_loader_uses_active_file():
    client = OllamaClient(prompt_path="prompts_instagram_v1.9.28.txt")
    prompt = client._load_slide_prompt()
    assert "trained senior Instagram recruitment creative director" in prompt
