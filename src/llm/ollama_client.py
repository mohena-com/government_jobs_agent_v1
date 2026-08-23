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
        """Create a complete, job-seeker-focused Instagram recruitment post.

        Qwen is an editorial layer only. The supplied verified fact bundle is
        the sole source of truth. Internal audit/reconciliation information is
        explicitly excluded from presentation copy.
        """
        if slide_count != 6:
            raise ValueError("V1.9.14 presentation mode requires exactly 6 slides")

        schema = {
            "type": "object",
            "properties": {
                "slides": {
                    "type": "array",
                    "minItems": 6,
                    "maxItems": 6,
                    "items": {
                        "type": "object",
                        "properties": {
                            "number": {"type": "integer"},
                            "type": {
                                "type": "string",
                                "enum": ["title", "vacancies", "eligibility", "age_pay_fee", "dates_selection", "apply_links"],
                            },
                            "headline": {"type": "string"},
                            "subtitle": {"type": "string"},
                            "bullets": {"type": "array", "items": {"type": "string"}},
                            "facts_used": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["number", "type", "headline", "subtitle", "bullets", "facts_used"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["slides"],
            "additionalProperties": False,
        }

        system = """
You are a professional Indian government-recruitment content editor.
Create a COMPLETE, factual, job-seeker-focused Instagram recruitment carousel.

SOURCE OF TRUTH
The LOCKED_FACTS supplied by the user are the ONLY source of truth.
Never invent, infer, estimate, generalize, or correct a missing fact.
Never change verified numbers, dates, post names, qualifications, fees, pay,
age limits, selection stages, or URLs.
If a fact is unavailable, omit it rather than guessing.

CRITICAL SEPARATION
The Instagram audience is a JOB SEEKER, not a data-engineering auditor.
NEVER expose internal pipeline information such as:
- status / PASS / FAIL
- quality gate / slide quality gate
- validation / verification status
- parsed vacancies / authoritative vacancies
- vacancy reconciliation
- extraction repairs
- PDF extraction problems
- facts_used
- locked facts
- source methods
- parser/debug information

These are internal audit metadata and must NEVER appear in headline, subtitle, or bullets.

CONTENT GOAL
The six slides together must provide the important information a job seeker
needs before applying. Prioritize useful recruitment facts over generic prose.
Do not use generic filler such as "great opportunity", "secure your future",
"all vacancies are announced through official channels", or similar promotional text.

EXACT SIX-SLIDE STRUCTURE
1. type=title
   - Recruitment name / organisation
   - Total vacancies
   - Major posts
   - Application deadline

2. type=vacancies
   - COMPLETE post-wise vacancy breakdown from verified facts
   - Include every verified post and the total

3. type=eligibility
   - Post-specific educational qualification
   - Computer/skill/experience requirements where verified
   - Keep wording concise but do not collapse distinct post requirements

4. type=age_pay_fee
   - Age limit and relaxation where verified
   - Pay/salary/pay level where verified
   - Application fee by category where verified

5. type=dates_selection
   - Application start/end dates
   - Other verified important dates
   - Exact selection process, including post-specific differences

6. type=apply_links
   - How to apply, only if verified
   - Important application instructions
   - DO NOT print URLs in bullets.
   - Official links are attached by the application after generation.
   - If no application URL is verified, say only that the official notification
     should be consulted; do not invent an application website.

PRESENTATION STYLE
- Clear, professional, concise Indian recruitment language.
- Use human-readable dates such as "05 August 2026".
- Use "Last Date to Apply" for a future deadline; never say "application ended"
  unless the locked facts establish that it has actually ended.
- No raw URLs or Markdown links in slide text.
- Do not put QA/status language in the slide copy.
- Do not put internal source references in the slide copy.

OUTPUT
Return JSON only using the required schema.
The facts_used field is for internal audit only and will not be rendered.
"""

        user = {
            "task": "Create exactly six complete Instagram recruitment slides from the verified facts.",
            "requirements": {
                "preserve_every_verified_post": True,
                "preserve_exact_vacancy_numbers": True,
                "include_eligibility": True,
                "include_age_pay_fee": True,
                "include_dates": True,
                "include_selection": True,
                "include_application_information": True,
                "never_render_internal_audit_text": True,
                "never_render_raw_urls": True,
            },
            "LOCKED_FACTS": facts,
        }

        data = self.chat(
            [
                {"role": "system", "content": system.strip()},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            think=False,
            temperature=0.10,
            format_schema=schema,
        )
        return parse_json_content(data["message"]["content"])


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
