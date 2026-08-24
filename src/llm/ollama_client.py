from __future__ import annotations

import json
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class OllamaClient:
    """Small Ollama HTTP client for a local or LAN Ollama server."""

    host: str = "http://localhost:11434"
    model: str = "qwen3:8b"
    timeout: int = 300
    prompt_path: str | None = None

    def __post_init__(self):
        self.host = self.host.rstrip("/")

    def tags(self) -> dict:
        r = requests.get(f"{self.host}/api/tags", timeout=30)
        r.raise_for_status()
        return r.json()

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        think: bool = False,
        temperature: float = 0.2,
        format_schema: Optional[dict] = None,
    ) -> dict:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": think,
            "options": {"temperature": temperature},
        }
        if format_schema:
            payload["format"] = format_schema

        r = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        if "message" not in data or "content" not in data["message"]:
            raise RuntimeError(f"Unexpected Ollama response: {data}")
        return data

    @staticmethod
    def _six_slide_schema() -> dict:
        """Fixed six-slide schema for the presentation layer."""
        kinds = ["title", "vacancies", "eligibility", "age_pay_fee", "dates_selection", "apply_links"]
        def slide_schema(number: int, kind: str) -> dict:
            return {
                "type": "object",
                "properties": {
                    "number": {"type": "integer", "enum": [number]},
                    "type": {"type": "string", "enum": [kind]},
                    "headline": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
                    "facts_used": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["number", "type", "headline", "subtitle", "bullets", "facts_used"],
                "additionalProperties": False,
            }
        return {
            "type": "object",
            "properties": {f"slide_{i}": slide_schema(i, kind) for i, kind in enumerate(kinds, 1)},
            "required": [f"slide_{i}" for i in range(1, 7)],
            "additionalProperties": False,
        }

    @staticmethod
    def _fixed_six_slide_to_array(data: dict) -> dict:
        return {"slides": [data[f"slide_{i}"] for i in range(1, 7)]}

    def _load_slide_prompt(self) -> str:
        candidates = []
        if self.prompt_path:
            candidates.append(Path(self.prompt_path))
        candidates.append(Path("prompts_instagram_v1.9.28.txt"))
        for path in candidates:
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        raise FileNotFoundError("Instagram prompt file not found")

    def generate_slide_plan(self, facts: dict, slide_count: int = 6) -> dict:
        """Create a six-slide, applicant-facing Instagram recruitment carousel."""
        if slide_count != 6:
            raise ValueError("Presentation mode requires exactly 6 slides")
        schema = self._six_slide_schema()
        system = self._load_slide_prompt()
        user = {
            "task": "Create exactly six concise Instagram recruitment slides from LOCKED_FACTS.",
            "slide_contract": {
                "1": "hero recruitment",
                "2": "post-wise vacancies",
                "3": "post-wise eligibility",
                "4": "age + pay/salary + application fee",
                "5": "important dates + selection process",
                "6": "documents + how to apply + official links + deadline CTA",
            },
            "requirements": {
                "exactly_six_slides": True,
                "preserve_every_verified_post": True,
                "preserve_exact_vacancy_numbers": True,
                "condense_long_qualifications": True,
                "fit_content_for_instagram": True,
                "no_raw_urls": True,
                "no_internal_audit_text": True,
            },
            "LOCKED_FACTS": facts,
        }
        data = self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
            think=False, temperature=0.05, format_schema=schema,
        )
        return self._fixed_six_slide_to_array(parse_json_content(data["message"]["content"]))

    def repair_slide_plan(self, facts: dict, previous_plan: dict, gate_errors: list[str], slide_count: int = 6) -> dict:
        if slide_count != 6:
            raise ValueError("Presentation mode requires exactly 6 slides")
        schema = self._six_slide_schema()
        system = r"""
Repair a six-slide government-recruitment Instagram presentation. LOCKED_FACTS is the only source of truth. Return JSON only.

FIXED SLOTS:
1 title = hero recruitment
2 vacancies = every verified post + exact vacancy count
3 eligibility = concise post-wise qualifications
4 age_pay_fee = age + pay/salary + application fee
5 dates_selection = dates + selection process
6 apply_links = documents/instructions + official links + deadline CTA

Resolve every gate error without inventing facts. Condense content rather than omitting verified posts or shrinking text. Remove source/audit/debug boilerplate. Never print raw URLs. Keep each bullet short and applicant-facing.
""".strip()
        user = {"task": "Repair the six-slide plan for factual completeness and visual fit.", "gate_errors": gate_errors, "previous_plan": previous_plan, "LOCKED_FACTS": facts}
        data = self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
            think=False, temperature=0.02, format_schema=schema,
        )
        return self._fixed_six_slide_to_array(parse_json_content(data["message"]["content"]))

def parse_json_content(content: str) -> dict:
    """Parse JSON even if a model accidentally surrounds it with markdown."""
    text = (content or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise
