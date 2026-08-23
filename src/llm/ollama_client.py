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

    @staticmethod
    def _six_slide_schema() -> dict:
        """Use six fixed object properties so Qwen cannot reorder/reuse slide types.

        An array item with an enum still lets a small model choose the wrong type
        for a position. Fixed properties make the JSON contract positional.
        """
        slide_types = [
            ("slide_1", 1, "title"),
            ("slide_2", 2, "vacancies"),
            ("slide_3", 3, "eligibility"),
            ("slide_4", 4, "age_pay_fee"),
            ("slide_5", 5, "dates_selection"),
            ("slide_6", 6, "apply_links"),
        ]
        def slide_schema(number: int, kind: str) -> dict:
            return {
                "type": "object",
                "properties": {
                    "number": {"type": "integer", "enum": [number]},
                    "type": {"type": "string", "enum": [kind]},
                    "headline": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
                    "facts_used": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["number", "type", "headline", "subtitle", "bullets", "facts_used"],
                "additionalProperties": False,
            }
        return {
            "type": "object",
            "properties": {name: slide_schema(number, kind) for name, number, kind in slide_types},
            "required": [name for name, _, _ in slide_types],
            "additionalProperties": False,
        }

    @staticmethod
    def _fixed_plan_to_array(data: dict) -> dict:
        """Convert the fixed six-property model response to the renderer's slide array."""
        slides = []
        for key in ("slide_1", "slide_2", "slide_3", "slide_4", "slide_5", "slide_6"):
            value = data.get(key)
            if not isinstance(value, dict):
                raise ValueError(f"Missing structured response property: {key}")
            slides.append(value)
        return {"slides": slides}

    def generate_slide_plan(self, facts: dict, slide_count: int = 6) -> dict:
        """Create a complete job-seeker-focused six-slide recruitment carousel.

        V1.9.16 uses a positional structured-output schema instead of asking a
        small model to choose slide types in an array. This prevents the common
        failure where Qwen repeats the vacancies slide for slides 3/4/5/6.
        """
        if slide_count != 6:
            raise ValueError("V1.9.16 presentation mode requires exactly 6 slides")

        schema = self._six_slide_schema()
        system = """
You are a professional Indian government-recruitment content editor.
Create a COMPLETE six-slide Instagram recruitment carousel for JOB SEEKERS.

The LOCKED_FACTS object is the ONLY source of truth. Never invent, infer,
estimate, generalize, or silently change any fact. Do not use the source DOCX
boilerplate when a verified fact is absent.

ABSOLUTE OUTPUT CONTRACT
You MUST return six fixed JSON properties: slide_1, slide_2, slide_3,
slide_4, slide_5, slide_6. Their types are fixed by the JSON schema and MUST
NOT be changed. Never return an array of arbitrary slide types.

SLIDE 1 — title
Include organisation/recruitment name, total vacancies, main posts, and the
application deadline when verified.

SLIDE 2 — vacancies
Include EVERY verified post and its EXACT vacancy count, plus the total.
Do not omit a post merely because the name is long.

SLIDE 3 — eligibility
Include the verified post-specific educational qualifications and computer,
skill, language, or experience requirements. This is an Instagram slide, not
the notification: give ONLY the essential qualification in a SHORT phrase for
each post, ideally 1–2 lines. Remove legal boilerplate, institution-recognition boilerplate, document-verification wording, and repeated phrases while retaining
material degree/discipline/computer/experience requirements. Do not omit a verified post.

SLIDE 4 — age_pay_fee
Include ONLY concise verified values: age range/maximum age and important
relaxation note; pay level/basic pay/salary range; category-wise application fee.
Do not repeat advertisement numbers, notification identifiers, source titles,
or long explanatory paragraphs. Aim for short card-friendly phrases.

SLIDE 5 — dates_selection
Include application start/end and other verified dates, then the exact
selection process. Include post-specific selection differences if verified.

SLIDE 6 — apply_links
Include verified how-to-apply instructions and important application notes.
Do NOT print URLs or Markdown links. The application will attach structured
official URLs and render QR codes separately.

PRESENTATION RULES
- This is a job post, not an audit report.
- Never include PASS, FAIL, quality gate, validation, reconciliation, parsed
  vacancies, authoritative vacancies, extraction repairs, source methods,
  locked facts, facts_used, PDF extraction notes, or verification status in
  headline/subtitle/bullets.
- Do not duplicate the vacancy breakdown into slides 3–6.
- Use human-readable dates such as "05 August 2026".
- Never call a future deadline "ended" or "passed".
- Never invent an application URL, salary, age, qualification, selection stage,
  or category fee.
- Avoid promotional filler such as "great opportunity" or "secure your future".
- The facts_used field is audit-only and will not be rendered.

Return JSON only.
""".strip()
        user = {
            "task": "Create the complete six-slide job post from LOCKED_FACTS. Follow the fixed slide contract exactly.",
            "slide_contract": {
                "slide_1": "title",
                "slide_2": "vacancies",
                "slide_3": "eligibility",
                "slide_4": "age_pay_fee",
                "slide_5": "dates_selection",
                "slide_6": "apply_links",
            },
            "requirements": {
                "preserve_every_verified_post": True,
                "preserve_exact_vacancy_numbers": True,
                "include_eligibility": True,
                "include_age_pay_fee": True,
                "include_dates_and_selection": True,
                "include_application_information": True,
                "no_internal_audit_text": True,
                "no_raw_urls": True,
            },
            "LOCKED_FACTS": facts,
        }
        data = self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
            think=False, temperature=0.05, format_schema=schema,
        )
        return self._fixed_plan_to_array(parse_json_content(data["message"]["content"]))

    def repair_slide_plan(self, facts: dict, previous_plan: dict, gate_errors: list[str], slide_count: int = 6) -> dict:
        """Repair a failed plan using the same fixed positional schema.

        V1.9.16 deliberately does not ask Qwen to choose slide types during
        repair. The repair pass can only rewrite the content of each fixed slot.
        """
        if slide_count != 6:
            raise ValueError("V1.9.16 presentation mode requires exactly 6 slides")
        schema = self._six_slide_schema()
        system = """
You are repairing a failed government-recruitment Instagram carousel.
LOCKED_FACTS is the only source of truth. Return JSON only.

The six slide slots are FIXED and cannot be changed:
slide_1 = title
slide_2 = vacancies
slide_3 = eligibility
slide_4 = age_pay_fee
slide_5 = dates_selection
slide_6 = apply_links

Rewrite the content so ALL listed gate errors are resolved.
Do not create another vacancies slide. Do not omit any verified post.
Do not omit available eligibility, age, pay, fee, dates, selection, or
application information.
Do not invent missing facts.
Do not print raw URLs or Markdown links in slide text.
Never expose audit/debug information such as PASS, FAIL, quality gate,
verification status, parsed/authoritative vacancies, reconciliation,
extraction repairs, facts_used, source methods, or PDF extraction notes.
The facts_used field is audit-only.

Content requirements:
- slide_1: recruitment, organisation, total vacancies, deadline
- slide_2: every post + exact vacancy + total
- slide_3: every verified post + essential qualification only; concise 1–2 line summaries
- slide_4: concise age + pay + fee values only; no advertisement/source boilerplate
- slide_5: application dates + exact selection process
- slide_6: how to apply + important instructions; URLs are attached separately

Return the same six fixed JSON properties required by the schema.
""".strip()
        user = {
            "task": "Repair every gate error while preserving all verified facts.",
            "gate_errors": gate_errors,
            "previous_plan": previous_plan,
            "LOCKED_FACTS": facts,
        }
        data = self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
            think=False, temperature=0.02, format_schema=schema,
        )
        return self._fixed_plan_to_array(parse_json_content(data["message"]["content"]))

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
