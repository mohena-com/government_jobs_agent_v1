import re
from datetime import datetime
from src.models import Recruitment
DATE=r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
def parse(raw):
    for f in ('%d/%m/%Y','%d-%m-%Y','%d/%m/%y','%d-%m-%y'):
        try:return datetime.strptime(raw,f).date()
        except ValueError:pass
def first(text,labels):
    for lab in labels:
        m=re.search(lab+r'.{0,100}?'+DATE,text,re.I|re.S)
        if m:return parse(m.group(1))
def extract(text,c=None):
    r=Recruitment(source_name=c.source_name if c else '',official_source_url=c.source_url if c else '',organisation=c.organisation if c else '',post_title=(c.post or c.title) if c else '',notification_url=c.notification_url if c else '',application_url=c.application_url if c else '')
    m=re.search(r'(?:Advt\.?|Advertisement|Notification)\s*(?:No\.?|Number)?\s*[:\-]?\s*([A-Za-z0-9./()_-]{3,40})',text,re.I); r.advertisement_number=m.group(1) if m else ''
    m=re.search(r'(\d[\d,]*)\s+(?:vacancies|posts|positions)',text,re.I); r.vacancies_total=int(m.group(1).replace(',','')) if m else None
    r.application_start_date=first(text,[r'application(?:s)?\s+(?:will\s+)?start',r'online\s+application(?:s)?\s+(?:will\s+)?start'])
    r.application_end_date=first(text,[r'last\s+date',r'closing\s+date',r'application(?:s)?\s+(?:close|end)'])
    for attr,pat,n in [('age_limit',r'(?:age\s+limit|maximum\s+age).{0,100}',500),('qualification',r'(?:educational\s+qualification|essential\s+qualification|qualification).{0,1200}',1500),('experience',r'(?:experience|work\s+experience).{0,1200}',1500),('application_fee',r'(?:application\s+fee|fee\s+for\s+application).{0,500}',700)]:
        m=re.search(pat,text,re.I|re.S)
        if m:setattr(r,attr,' '.join(m.group(0).split())[:n])
    r.extraction_confidence=.45
    return r
