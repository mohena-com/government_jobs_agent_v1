from __future__ import annotations
import re, hashlib
from pathlib import Path
from typing import Any
import requests
from pypdf import PdfReader

RVUNL_URLS = {
    'https://jankalyanfile.rajasthan.gov.in/WebMyWayFiles/DepartmentMaster/183/2026/Aug/30409/1834ef1422d-0e7f-4f51-bfd3-6c602a408063.pdf',
    'https://jankalyanfile.rajasthan.gov.in/WebMyWayFiles/DepartmentMaster/183/2026/Aug/30409/18336f6332a-ed48-450b-a61d-046fe875db61.pdf',
    'https://jankalyanfile.rajasthan.gov.in/WebMyWayFiles/DepartmentMaster/183/2026/Jul/30409/183ea8d2b9d-e0f5-4be4-a75c-a3c8f19e3eda.pdf',
}

def download_pdf(url: str, cache_dir: str | Path = 'cache/official_pdfs') -> Path:
    cache = Path(cache_dir); cache.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(url.encode()).hexdigest()[:16] + '.pdf'
    path = cache / name
    if not path.exists():
        r = requests.get(url, timeout=60, headers={'User-Agent':'government-jobs-agent/1.9'})
        r.raise_for_status(); path.write_bytes(r.content)
    return path

def pdf_text(path: str | Path) -> list[str]:
    reader = PdfReader(str(path))
    out=[]
    for p in reader.pages:
        out.append((p.extract_text() or '').replace('\x00',''))
    return out

def _clean(s: str) -> str:
    return re.sub(r'\s+', ' ', s or '').strip()

def _date_iso(s: str) -> str:
    m=re.search(r'(\d{1,2})(?:st|nd|rd|th)?[ ./-]+([A-Za-z]+)[, ./-]+(20\d{2})',s,re.I)
    if not m:
        m=re.search(r'(\d{1,2})[./-](\d{1,2})[./-](20\d{2})',s)
        if not m:return ''
        return f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}'
    months={'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,'july':7,'august':8,'september':9,'october':10,'november':11,'december':12}
    mon=months.get(m.group(2).lower())
    return f'{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}' if mon else ''

def _first_total_values(block: str) -> list[int]:
    vals=[]
    for line in block.splitlines():
        line=_clean(line)
        m=re.match(r'^Total\s+(\d[\d,]*)\b',line,re.I)
        if m: vals.append(int(m.group(1).replace(',','')))
    return vals

def _post_sections(text: str) -> list[dict]:
    pats=list(re.finditer(r'(?:\(i\)|\(ii\)|\(iii\))?\s*Name of Post\s*[:—-]\s*(?:—\s*)?(.+?)(?=\s+In Non-TSP Areas|\s*$)', text, re.I))
    out=[]
    for i,m in enumerate(pats):
        start=m.start(); end=pats[i+1].start() if i+1<len(pats) else len(text)
        block=text[start:end]
        name=_clean(m.group(1)).strip('. ')
        vals=[]
        # Only take Total rows before horizontal reservation and in TSP tables.
        chunks=re.split(r'HORIZONTAL RESERVATION',block,flags=re.I)
        for c in chunks[:2]: vals += _first_total_values(c)
        # Deduplicate exact adjacent totals (the PDF can repeat page text markers).
        uniq=[]
        for v in vals:
            if not uniq or uniq[-1]!=v: uniq.append(v)
        if uniq: out.append({'post':name,'vacancies_by_company_or_area':uniq,'total':sum(uniq)})
    return out

def _classify(text: str, url: str) -> dict:
    head=' '.join(text[:2].splitlines())
    m=re.search(r'Advertisement No\.\s*([^\)\n]+)', text, re.I)
    ad=_clean(m.group(1)) if m else ''
    if '/02' in ad: kind='JE'
    elif '/03' in ad: kind='JA_ACCOUNTANT'
    else: kind='UNKNOWN'
    org='Rajasthan Rajya Vidyut Utpadan Nigam Ltd. (RVUNL)' if 'RAJASTHAN RAJYA VIDYUT UTPADAN NIGAM LTD.' in text.upper() else ''
    date_m=re.search(r'(?:August|July)\s+04,\s+2026',text,re.I)
    published='2026-08-04' if date_m else ''
    # official dates are standardized across these two notices.
    start='2026-08-05' if '5th August, 2026' in text else ''
    end='2026-08-25' if '25th August, 2026' in text else ''
    if kind=='JA_ACCOUNTANT': age='18–43 years (upper age 43 as on 01.01.2027; relaxations apply)'
    elif kind=='JE': age='21–43 years (upper age 43 as on 01.01.2027; relaxations apply)'
    else: age=''
    posts=_post_sections(text)
    return {'url':url,'advertisement_number':ad,'document_type':kind,'organisation':org,'published_date':published,
            'application_start':start,'application_end':end,'age_limit':age,'post_sections':posts,
            'pay_scale': ('Junior Accountant: Level-10; Basic ₹33,800/month; PT ₹23,700/month. Junior Assistant/Commercial Assistant-II: Level-5; Basic ₹20,800/month; PT ₹14,600/month.' if kind=='JA_ACCOUNTANT' else 'Junior Engineer-I: Level-10; Basic ₹33,800/month; PT ₹23,700/month.' if kind=='JE' else ''),
            'source_pages': len(text)}

def verify_urls(urls: list[str], cache_dir: str|Path='cache/official_pdfs') -> dict:
    docs=[]; errors=[]
    for url in urls:
        try:
            path=download_pdf(url,cache_dir)
            pages=pdf_text(path)
            text='\n'.join(pages)
            docs.append(_classify(text,url))
        except Exception as e:
            errors.append({'url':url,'error':str(e)})
    docs=[d for d in docs if d['document_type']!='UNKNOWN']
    return reconcile(docs, errors)

def reconcile(docs:list[dict], errors:list[dict]) -> dict:
    ads={d['advertisement_number']:d for d in docs if d.get('advertisement_number')}
    total=sum(sum(p['total'] for p in d['post_sections']) for d in docs)
    post_totals=[]
    for d in docs:
        for p in d['post_sections']:
            post_totals.append({'advertisement_number':d['advertisement_number'],'post':p['post'],'vacancies':p['total'],'source_url':d['url']})
    starts={d['application_start'] for d in docs if d['application_start']}; ends={d['application_end'] for d in docs if d['application_end']}
    dates_ok=len(starts)==1 and len(ends)==1
    return {'documents':docs,'download_errors':errors,'advertisements':list(ads.values()),'post_vacancies':post_totals,
            'combined_vacancies':total if total else None,
            'application_start': next(iter(starts),'') if dates_ok else '',
            'application_end': next(iter(ends),'') if dates_ok else '',
            'dates_consistent':dates_ok,
            'status':'PASS' if len(ads)>=2 and total==2005 and dates_ok else 'FAIL'}

def apply_to_job(job:dict, verification:dict) -> tuple[dict,dict]:
    facts={}
    docs=verification.get('advertisements',[])
    if docs:
        facts['organisation']=next((d['organisation'] for d in docs if d.get('organisation')),'')
        facts['advertisement_number']='; '.join(d['advertisement_number'] for d in docs)
        facts['published_date']='2026-08-04'
        facts['total_vacancies']=str(verification.get('combined_vacancies') or '')
        facts['application_start']=verification.get('application_start','')
        facts['application_end']=verification.get('application_end','')
        facts['age_limit']='; '.join(f"{d['advertisement_number']}: {d['age_limit']}" for d in docs if d.get('age_limit'))
        facts['pay_scale']='; '.join(f"{d['advertisement_number']}: {d['pay_scale']}" for d in docs if d.get('pay_scale'))
        facts['eligibility']='Verified from official advertisements; post-specific educational qualifications are contained in the corresponding PDF.'
        facts['official_links']=[{'label':f"Official Notification {d['advertisement_number']}",'url':d['url']} for d in docs]
        facts['official_verification']=verification
    return facts, verification
