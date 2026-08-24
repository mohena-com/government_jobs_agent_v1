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
    def _two_slide_schema() -> dict:
        """Fixed two-slide schema matching the presentation prompt."""
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
            "properties": {
                "slide_1": slide_schema(1, "job_details"),
                "slide_2": slide_schema(2, "at_a_glance"),
            },
            "required": ["slide_1", "slide_2"],
            "additionalProperties": False,
        }

    @staticmethod
    def _fixed_two_slide_to_array(data: dict) -> dict:
        slides = []
        for key in ("slide_1", "slide_2"):
            value = data.get(key)
            if not isinstance(value, dict):
                raise ValueError(f"Missing structured response property: {key}")
            slides.append(value)
        return {"slides": slides}

    def generate_slide_plan(self, facts: dict, slide_count: int = 2) -> dict:
        """Create a concise two-slide job-seeker Instagram presentation.

        The attached presentation prompt is implemented as the model contract:
        slide 1 contains cards 1-3, slide 2 contains cards 4-7, with the same
        header/quick-info/footer treatment handled by the renderer.
        """
        if slide_count != 2:
            raise ValueError("Presentation mode requires exactly 2 slides")
        schema = self._two_slide_schema()
        system = """
You are an expert Graphic Designer and Visual Content Strategist specializing
in government/corporate recruitment infographics for Instagram.

GOAL
Analyze LOCKED_FACTS and create exactly TWO applicant-facing Instagram
recruitment slides. The renderer will supply the common visual header,
quick-info bar, and footer. You supply concise card content only.

SOURCE RULES
- LOCKED_FACTS is the ONLY source of truth.
- Never invent, infer, estimate, generalize, or silently change facts.
- Do not use third-party boilerplate as if it were an official fact.
- If a field is unavailable, say "Refer to Official Notification" rather than inventing it.
- Never output raw URLs or Markdown links in bullets/headlines.
- Do not expose QA/debug/audit language: PASS, FAIL, quality gate,
  validation, reconciliation, parsed vacancies, authoritative vacancies,
  extraction repairs, locked facts, facts_used, source methods, PDF extraction,
  verification status, or internal processing details.
- facts_used is audit metadata only and is not rendered.

EXACT TWO-SLIDE CONTRACT

SLIDE 1 — type job_details
Headline: "JOB DETAILS" or a similarly concise applicant-facing title.
Subtitle: short, useful context.
Cards/content represented in bullets:
1. VACANCY & ELIGIBILITY BREAKDOWN
   - Every verified post and exact vacancy count where available.
   - Essential educational qualification per post.
   - Condense long qualifications to short applicant-facing phrases.
   - Preserve material degree/discipline, marks, computer/skill/language,
     and experience requirements when verified.
2. AGE LIMIT
   - Minimum/maximum age or other verified age condition.
   - Age-as-on date and important relaxation note if available.
3. SELECTION PROCESS
   - Only verified selection stages and important post-specific differences.
   - Remove legal/administrative boilerplate.

SLIDE 2 — type at_a_glance
Headline: "AT A GLANCE" or similarly concise.
Subtitle: short context.
Cards/content represented in bullets:
4. PAY & SALARY
   - Training stipend, basic pay, pay scale/level, or salary range if verified.
5. APPLICATION FEE
   - Category-wise fees and payment/refundability note if verified.
6. IMPORTANT DATES
   - Notification date, application start, deadline, and other critical dates.
7. REQUIRED DOCUMENTS / INSTRUCTIONS
   - Only the most important explicit documents/instructions; keep concise.
   - How-to-apply instructions may be included as short actionable points.

CONTENT-FIT RULES
- This is a visual poster, not the notification.
- Aggressively condense long source prose while preserving meaning.
- Prefer short phrases, compact bullets, and post-wise mini-table style text.
- Never truncate a sentence halfway merely to fit.
- Never compensate for excess content with unreadably small text.
- If content cannot fit, remove repetitive boilerplate and use
  "Refer to Official Notification" for secondary detail.
- Do not duplicate the same information across both slides unless it is a
  key header-level fact.
- No promotional filler.
- Use human-readable dates.

Return JSON only, matching the fixed two-property schema exactly.
""".strip()
        user = {
            "task": "Create exactly two concise Instagram job-post slides from LOCKED_FACTS.",
            "slide_contract": {
                "slide_1": "job_details: vacancy+eligibility, age, selection",
                "slide_2": "at_a_glance: pay+salary, fee, dates, documents/instructions",
            },
            "requirements": {
                "exactly_two_slides": True,
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
        return self._fixed_two_slide_to_array(parse_json_content(data["message"]["content"]))

    def repair_slide_plan(self, facts: dict, previous_plan: dict, gate_errors: list[str], slide_count: int = 2) -> dict:
        if slide_count != 2:
            raise ValueError("Presentation mode requires exactly 2 slides")
        schema = self._two_slide_schema()
        system = """
Repair a two-slide government-recruitment Instagram presentation.
LOCKED_FACTS is the only source of truth. Return JSON only.

FIXED SLOTS:
slide_1 = job_details: vacancy & eligibility + age + selection
slide_2 = at_a_glance: pay/salary + application fee + important dates + documents/instructions

Resolve every gate error without inventing facts. Condense content rather than
shrinking it or omitting a verified post. Remove source/audit/debug boilerplate.
Never print raw URLs or Markdown links. facts_used is audit-only.
The renderer supplies the same header, quick-info bar and footer on both slides.
""".strip()
        user = {"task": "Repair the two-slide plan and keep it concise enough to render cleanly.", "gate_errors": gate_errors, "previous_plan": previous_plan, "LOCKED_FACTS": facts}
        data = self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
            think=False, temperature=0.02, format_schema=schema,
        )
        return self._fixed_two_slide_to_array(parse_json_content(data["message"]["content"]))

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
