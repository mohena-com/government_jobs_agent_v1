from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class OllamaClient:
    """Small Ollama HTTP client for a local or LAN Ollama server."""

    host: str = "http://localhost:11434"
    model: str = "qwen3:8b"
    timeout: int = 300

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

    def generate_slide_plan(self, facts: dict, slide_count: int = 6) -> dict:
        """Turn locked source facts into Instagram slide copy.

        Qwen is an editorial layer only. It receives factual data and is told
        not to invent missing values. The caller should still validate output.
        """
        schema = {
            "type": "object",
            "properties": {
                "slides": {
                    "type": "array",
                    "minItems": slide_count,
                    "maxItems": slide_count,
                    "items": {
                        "type": "object",
                        "properties": {
                            "number": {"type": "integer"},
                            "type": {"type": "string"},
                            "headline": {"type": "string"},
                            "subtitle": {"type": "string"},
                            "bullets": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "facts_used": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["number", "type", "headline", "subtitle", "bullets", "facts_used"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["slides"],
            "additionalProperties": False,
        }

        system = (
            "You are a factual Instagram government-jobs content editor. "
            "You are NOT the source of truth. You may only transform the supplied "
            "LOCKED_FACTS into concise slide copy. Never invent, infer, or change "
            "dates, years, vacancy counts, advertisement numbers, post names, "
            "qualifications, salaries, fees, URLs, or application status. "
            "If information is absent, do not create a factual claim. "
            "Do not use 'Apply Now', 'LIVE', 'Don't Miss Out' or similar urgency "
            "claims unless the supplied facts explicitly establish that status. "
            "Return JSON only. Keep each slide readable and factual."
        )
        user = {
            "task": f"Create exactly {slide_count} Instagram carousel slides.",
            "slide_guidance": [
                "cover/hook",
                "organisation, post and vacancies",
                "eligibility and experience",
                "age, pay and reservation where available",
                "application dates, fee and application method",
                "important instructions and official source/application links",
            ],
            "LOCKED_FACTS": facts,
        }

        data = self.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            think=False,
            temperature=0.15,
            format_schema=schema,
        )
        content = data["message"]["content"]
        return parse_json_content(content)


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
