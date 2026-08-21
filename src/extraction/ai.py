import os,json
from src.models import Recruitment

def extract_with_openai(text,candidate=None):
    if not os.getenv('OPENAI_API_KEY'): return None
    from openai import OpenAI
    client=OpenAI(api_key=os.environ['OPENAI_API_KEY']); model=os.getenv('OPENAI_MODEL') or 'gpt-5.6'
    prompt='''Extract only facts explicitly present in this Indian government recruitment notification. Never invent values. Return JSON matching the schema.''' + '\nDISCOVERY:\n' + (candidate.model_dump_json() if candidate else '{}') + '\nDOCUMENT:\n' + text[:120000]
    resp=client.responses.create(model=model,instructions=prompt,input=prompt,text={'format':{'type':'json_schema','name':'recruitment','strict':True,'schema':Recruitment.model_json_schema()}})
    return Recruitment.model_validate(json.loads(resp.output_text))
