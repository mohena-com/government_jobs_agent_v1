import os, json
from src.models import Recruitment

SYSTEM = """You validate an extraction from an official UPSC recruitment advertisement.
Do not invent facts. Return corrected structured values only when directly supported
by the supplied text. Preserve the vacancy number. If uncertain, keep the original
value and add a warning."""

def ai_validate(recruitment, segment_text):
    if not os.getenv("OPENAI_API_KEY"):
        return recruitment

    from openai import OpenAI
    client = OpenAI()
    model = os.getenv("OPENAI_MODEL") or "gpt-5.6"

    prompt = f"""CURRENT EXTRACTION:
{recruitment.model_dump_json()}

SOURCE SEGMENT:
{segment_text[:60000]}
"""

    response = client.responses.create(
        model=model,
        instructions=SYSTEM,
        input=prompt,
        text={"format": {
            "type": "json_schema",
            "name": "upsc_recruitment",
            "strict": True,
            "schema": Recruitment.model_json_schema()
        }}
    )
    return Recruitment.model_validate(json.loads(response.output_text))
