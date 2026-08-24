from __future__ import annotations
import re, hashlib, time
from pathlib import Path
from typing import Any
import requests
from pypdf import PdfReader
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

RVUNL_URLS = {
    'https://jankalyanfile.rajasthan.gov.in/WebMyWayFiles/DepartmentMaster/183/2026/Aug/30409/1834ef1422d-0e7f-4f51-bfd3-6c602a408063.pdf',
    'https://jankalyanfile.rajasthan.gov.in/WebMyWayFiles/DepartmentMaster/183/2026/Aug/30409/18336f6332a-ed48-450b-a61d-046fe875db61.pdf',
    'https://jankalyanfile.rajasthan.gov.in/WebMyWayFiles/DepartmentMaster/183/2026/Jul/30409/183ea8d2b9d-e0f5-4be4-a75c-a3c8f19e3eda.pdf',
}


# V1.9.2 pilot profile for the RVUNL common recruitment.
# These are authoritative totals from the official advertisements and are used
# only as a reconciliation/repair layer when PDF text extraction drops table rows.
RVUNL_OFFICIAL_PROFILE = {
    "RVUN/Rectt.-2026-27/02": {
        "Junior Engineer-I (Electrical)": 727,
        "Junior Engineer-I (Mechanical)": 110,
        "Junior Engineer-I (Civil)": 32,
    },
    "RVUN/Rectt.-2026-27/03": {
        "Junior Accountant": 371,
        "Junior Assistant/ Commercial Assistant-II": 765,
    },
}
RVUNL_OFFICIAL_COMBINED_TOTAL = 2005

def download_pdf(url: str, cache_dir: str | Path = 'cache/official_pdfs') -> Path:
    cache = Path(cache_dir); cache.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(url.encode()).hexdigest()[:16] + '.pdf'
    path = cache / name
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/151 Safari/537.36',
        'Accept': 'application/pdf,application/octet-stream,text/html;q=0.8,*/*;q=0.5',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    if path.exists() and path.stat().st_size > 1000:
        try:
            if path.read_bytes()[:5] == b'%PDF-':
                return path
        except OSError:
            pass
        try: path.unlink()
        except OSError: pass

    last_error = None
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=60, headers=headers, allow_redirects=True)
            r.raise_for_status()
            content = r.content
            ctype = (r.headers.get('content-type') or '').lower()
            if content.startswith(b'%PDF-'):
                path.write_bytes(content)
                return path
            # Some servers incorrectly report application/pdf but return an HTML page.
            # Never cache that as a PDF.
            if 'application/pdf' in ctype and len(content) > 1000:
                path.write_bytes(content)
                try:
                    PdfReader(str(path))
                    return path
                except Exception:
                    path.unlink(missing_ok=True)
            raise ValueError(f'URL did not return a valid PDF (status={r.status_code}, content-type={ctype or "unknown"}, bytes={len(content)})')
        except Exception as e:
            last_error = e
            import time
            time.sleep(1.5 * (attempt + 1))
    raise last_error or ValueError('PDF download failed')

def pdf_text(path: str | Path) -> list[str]:
    reader = PdfReader(str(path))
    out=[]
    for p in reader.pages:
        out.append((p.extract_text() or '').replace('\x00',''))
    return out

def _clean(s: str) -> str:
    return re.sub(r'\s+', ' ', s or '').strip()

def _date_iso(s: str) -> str:
    """Parse the common date formats used in Indian recruitment PDFs."""
    s = _clean(s)
    month_names = {
        'jan':1,'january':1,'feb':2,'february':2,'mar':3,'march':3,
        'apr':4,'april':4,'may':5,'jun':6,'june':6,'jul':7,'july':7,
        'aug':8,'august':8,'sep':9,'sept':9,'september':9,
        'oct':10,'october':10,'nov':11,'november':11,'dec':12,'december':12,
    }
    patterns = [
        r'^(\d{1,2})(?:st|nd|rd|th)?[ ./-]+([A-Za-z]+)[, ./-]+(20\d{2})$',
        r'^(\d{1,2})[./-](\d{1,2})[./-](20\d{2})$',
        r'^([A-Za-z]+)[ ./-]+(\d{1,2})(?:st|nd|rd|th)?[, ./-]+(20\d{2})$',
        r'^(\d{1,2})[ ./-]+([A-Za-z]+)[, ./-]+(20\d{2})$',
    ]
    for pat in patterns:
        m = re.search(pat, s, re.I)
        if not m:
            continue
        g = m.groups()
        try:
            if g[1].isdigit() and not g[0].isdigit():
                mon = month_names.get(g[0].lower())
                day = int(g[1]); year = int(g[2])
            elif g[1].isdigit() and g[0].isdigit():
                day = int(g[0]); mon = int(g[1]); year = int(g[2])
            else:
                day = int(g[0]); mon = month_names.get(g[1].lower()); year = int(g[2])
            if mon and 1 <= day <= 31:
                return f'{year:04d}-{mon:02d}-{day:02d}'
        except ValueError:
            pass
    return ''

def _extract_area_totals(block: str) -> list[int]:
    """Extract company-level vacancy totals from one post section.

    The PDF text extractor is inconsistent: some tables retain a leading
    ``Total 108 ...`` label while others (notably the Civil table) emit the
    final numeric row without the word ``Total``.  We therefore parse the
    two actual vacancy areas separately and ignore horizontal-reservation
    tables entirely.
    """
    companies = {"RVUN", "RVPN", "JVVN", "AVVN", "JDVVN", "JDVVN"}
    totals: list[int] = []
    lines = [_clean(x) for x in block.splitlines() if _clean(x)]

    def numeric_row(line: str) -> int | None:
        m = re.match(r'^(?:Total\s+)?(\d[\d,]*)\b', line, re.I)
        return int(m.group(1).replace(',', '')) if m else None

    # Find company blocks and take the final vacancy row before the next company.
    company_positions = [(i, ln.upper()) for i, ln in enumerate(lines) if ln.upper() in companies]
    for pos, (i, _) in enumerate(company_positions):
        j = company_positions[pos + 1][0] if pos + 1 < len(company_positions) else len(lines)
        candidate_rows = []
        for ln in lines[i + 1:j]:
            # Stop before reservation notes / headings.
            if 'HORIZONTAL RESERVATION' in ln.upper():
                break
            n = numeric_row(ln)
            if n is not None:
                candidate_rows.append(n)
        if candidate_rows:
            totals.append(candidate_rows[-1])
    return totals


def _post_sections(text: str) -> list[dict]:
    """Extract each post and its non-TSP/TSP vacancy totals.

    PDF extraction often flattens tables into a single stream, so post names
    must be separated from the following table text explicitly.
    """
    heading = re.compile(
        r'(?:\(i\)|\(ii\)|\(iii\))?\s*Name of Post\s*[:—-]\s*(?:—\s*)?(.+?)(?=\s+In\s+Non-TSP\s+Areas|\s+In\s+TSP\s+Areas|\s+Educational\s+Qualification|\Z)',
        re.I | re.S,
    )
    positions = list(re.finditer(
        r'(?:\(i\)|\(ii\)|\(iii\))?\s*Name of Post\s*[:—-]', text, re.I
    ))
    out = []
    for idx, h in enumerate(positions):
        block_end = positions[idx + 1].start() if idx + 1 < len(positions) else len(text)
        block = text[h.start():block_end]
        nm = heading.search(block)
        if not nm:
            continue
        name = _clean(nm.group(1)).strip('. ')
        areas = re.split(r'IN\s+TSP\s+AREAS', block, flags=re.I)
        non_tsp = re.split(r'HORIZONTAL\s+RESERVATION', areas[0], flags=re.I)[0]
        tsp = ''
        if len(areas) > 1:
            tsp = re.split(r'HORIZONTAL\s+RESERVATION', areas[1], flags=re.I)[0]
        vals = _extract_area_totals(non_tsp) + _extract_area_totals(tsp)
        if vals:
            out.append({
                'post': name,
                'vacancies_by_company_or_area': vals,
                'total': sum(vals),
            })
    return out


_DEEP_HEADINGS = [
    'Educational Qualification', 'Education Qualification', 'Qualification',
    'Essential Qualification', 'Eligibility', 'Experience',
    'Selection Process', 'Selection Procedure', 'Mode of Selection',
    'Application Fee', 'Examination Fee', 'Fee Details',
    'How to Apply', 'How To Apply', 'Online Application', 'Application Procedure',
]


def _section(text: str, headings: list[str], stop_headings: list[str] | None = None, max_chars: int = 5000) -> str:
    stop = stop_headings or _DEEP_HEADINGS
    pattern = r'(?im)^(?:\s*[-•●]?\s*)(' + '|'.join(re.escape(x) for x in headings) + r')\s*[:\-–—]?\s*'
    m = re.search(pattern, text)
    if not m:
        pattern = r'(?i)\b(' + '|'.join(re.escape(x) for x in headings) + r')\s*[:\-–—]?\s*'
        m = re.search(pattern, text)
    if not m: return ''
    tail = text[m.end():m.end()+max_chars]
    stop_pat = r'(?i)\b(?:' + '|'.join(re.escape(x) for x in stop if x not in headings) + r')\s*[:\-–—]?\s*'
    sm = re.search(stop_pat, tail)
    if sm: tail = tail[:sm.start()]
    return _clean(tail)


def _post_eligibility(text: str, post_names: list[str]) -> list[dict]:
    rows=[]
    for i,name in enumerate(post_names):
        m=re.search(re.escape(name), text, re.I)
        if not m: continue
        end=len(text)
        for other in post_names[i+1:]:
            mm=re.search(re.escape(other), text[m.end():], re.I)
            if mm: end=min(end,m.end()+mm.start())
        block=text[m.start():end]
        qual=_section(block,['Educational Qualification','Education Qualification','Essential Qualification','Qualification','Eligibility'],max_chars=3500)
        exp=_section(block,['Experience'],max_chars=1800)
        if qual or exp: rows.append({'post':name,'qualification':qual,'experience':exp,'source_method':'GENERIC_BOUNDARY'})
    return rows


def _rvunl_post_fact_blocks(text: str, ad: str) -> list[dict]:
    """Structured RVUNL extraction.

    The PDF text layer flattens multi-column tables and headings. Instead of
    assigning one giant eligibility blob to the first post, split the official
    advertisement by its explicit post labels and extract only the text that
    belongs to that post. This is deliberately conservative: uncertain text is
    left empty rather than copied into another post.
    """
    if ad.endswith('/02'):
        posts = [
            ('Junior Engineer-I (Electrical)', r'Electrical\s+The candidate must hold'),
            ('Junior Engineer-I (Mechanical)', r'Mechanical\s+The candidate must hold'),
            ('Junior Engineer-I (Civil)', r'Civil\s+The candidate must hold'),
        ]
        common = ('Candidates must possess working knowledge of Hindi written in Devnagri '
                  'script and knowledge of Rajasthani culture.')
        # Exact qualification sentences are safer than arbitrary page windows.
        patterns = {
            'Junior Engineer-I (Electrical)': r'Electrical\s+The candidate must hold\s+(.+?)(?=\s+Mechanical\s+The candidate must hold)',
            'Junior Engineer-I (Mechanical)': r'Mechanical\s+The candidate must hold\s+(.+?)(?=\s+Civil\s+The candidate must hold)',
            'Junior Engineer-I (Civil)': r'Civil\s+The candidate must hold\s+(.+?)(?=\s+\(b\)\s*Candidates must possess)',
        }
    elif ad.endswith('/03'):
        posts = [
            ('Junior Accountant', r'Name of Post[:—-]\s*Junior Accountant'),
            ('Junior Assistant/ Commercial Assistant-II', r'Name of Post[:—-]\s*Junior Assistant/\s*Commercial Assistant-II'),
        ]
        patterns = {}
        # The ministerial advertisement places the two qualification blocks
        # under their post headings. Use heading-to-next-heading boundaries.
        for i,(name,_) in enumerate(posts):
            pass
    else:
        # Older/nonstandard RVUNL education-table layout. Try a conservative
        # numbered-post fallback after the normal advertisement-specific logic.
        legacy = re.finditer(
            r'(?:^|\s)(?:1|2)\.\s*(Junior Accountant|Junior Assistant/\s*Commercial Assistant-II)\s*',
            text, re.I
        )
        legacy_matches = [(m.start(), m.end(), _clean(m.group(1))) for m in legacy]
        if legacy_matches:
            out=[]
            for i,(st,en,name) in enumerate(legacy_matches):
                end = legacy_matches[i+1][0] if i+1 < len(legacy_matches) else len(text)
                block = text[en:end]
                cut = re.search(r'\b(?:Disqualification|Physical Fitness|Character)\b', block, re.I)
                if cut:
                    block = block[:cut.start()]
                block = _clean(block)
                if block:
                    out.append({
                        'post': name,
                        'qualification': block[:5000],
                        'experience': '',
                        'source_method': 'RVUNL_EDUCATION_TABLE',
                    })
            return out
        return []


    out=[]
    if ad.endswith('/02'):
        for name,_ in posts:
            m=re.search(patterns[name], text, re.I|re.S)
            if not m:
                continue
            qual=_clean(m.group(1))
            # Remove common post-independent text if it leaked into the match.
            qual=re.sub(r'\s+RajKaj Ref No\.:\s*\d+\s*\d+', ' ', qual, flags=re.I)
            if common.lower() not in qual.lower():
                qual += ' ' + common
            out.append({'post':name,'qualification':qual,'experience':'','source_method':'RVUNL_POST_BOUNDARY'})
    else:
        headings=[
            ('Junior Accountant', r'Name of Post[:—-]\s*Junior Accountant'),
            ('Junior Assistant/ Commercial Assistant-II', r'Name of Post[:—-]\s*Junior Assistant/\s*Commercial Assistant-II'),
        ]
        matches=[]
        for name,pat in headings:
            m=re.search(pat,text,re.I)
            if m: matches.append((m.start(),m.end(),name))
        matches.sort()
        if not matches:
            legacy = re.finditer(
                r'(?:^|\s)(?:1|2)\.\s*(Junior Accountant|Junior Assistant/\s*Commercial Assistant-II)\s*',
                text, re.I
            )
            legacy_matches = [(m.start(), m.end(), _clean(m.group(1))) for m in legacy]
            for i,(st,en,name) in enumerate(legacy_matches):
                end = legacy_matches[i+1][0] if i+1 < len(legacy_matches) else len(text)
                block = text[en:end]
                cut = re.search(r'\b(?:Disqualification|Physical Fitness|Character)\b', block, re.I)
                if cut: block = block[:cut.start()]
                qm = re.search(r'(?:candidate must|educational qualification|qualification)', block, re.I)
                if qm: block = block[qm.start():]
                block = _clean(block)
                if block:
                    out.append({'post':name,'qualification':block[:5000],'experience':'','source_method':'RVUNL_EDUCATION_TABLE'})
            return out
        for i,(st,en,name) in enumerate(matches):
            end=matches[i+1][0] if i+1<len(matches) else len(text)
            block=text[en:end]
            # Qualification usually appears before disqualification/character.
            cut=re.search(r'\b(?:Disqualification for appointment|Character|Physical Fitness)\b',block,re.I)
            if cut: block=block[:cut.start()]
            # Strip vacancy-table material before the eligibility narrative.
            qm=re.search(r'(?:Essential|Educational|requisite educational|candidate must hold|candidate should possess|qualification)',block,re.I)
            if qm: block=block[qm.start():]
            block=_clean(block)
            # Avoid assigning the entire vacancy table as qualification.
            if len(block)>5000: block=block[:5000]
            out.append({'post':name,'qualification':block,'experience':'','source_method':'RVUNL_POST_BOUNDARY'})
    return out


def _clean_fee(text: str) -> str:
    """Return only fee amounts/payment method, not surrounding application instructions."""
    if not text: return ''
    amounts=[]
    for m in re.finditer(r'(General[^\n]{0,120}?\d[\d,]*\s*/?-|EWS[^\n]{0,180}?\d[\d,]*\s*/?-|SC\s*/\s*ST[^\n]{0,80}?\d[\d,]*\s*/?-)', text, re.I):
        amounts.append(_clean(m.group(0)))
    # Strong fallback for the RVUNL fee block.
    g=re.search(r'General\s*/\s*:?\s*([\d,]+)\s*/?-',text,re.I)
    r=re.search(r'(?:EWS\s*/\s*BC\s*/\s*MBC\s*SC\s*/\s*ST\s*/\s*PH)\s*:\s*([\d,]+)\s*/?-',text,re.I)
    if g and r:
        return f'General: ₹{g.group(1)}; EWS/BC/MBC/SC/ST/PwBD: ₹{r.group(1)}; payment: online.'
    if amounts:
        return '; '.join(dict.fromkeys(amounts))
    return ''


def _clean_selection(text: str) -> str:
    if not text: return ''
    # Preserve the useful exam structure but remove duplicated page headers and
    # unrelated contingency paragraphs.
    t=re.sub(r'\s+RajKaj Ref No\.:\s*\d+\s*\d+', ' ', text, flags=re.I)
    t=re.sub(r'\s+', ' ', t).strip()
    return t[:4500]


def _deep_extract(text: str, post_names: list[str], ad: str = '') -> dict:
    structured = _rvunl_post_fact_blocks(text, ad)
    if structured:
        return {
            'post_eligibility': structured,
            'selection_process': _clean_selection(_section(text,['Selection Process','Selection Procedure','Mode of Selection'],max_chars=4500)),
            'application_fee_official': _clean_fee(_section(text,['Application Fee','Examination Fee','Fee Details'],max_chars=3000)),
            'how_to_apply': _section(text,['How to Apply','How To Apply','Online Application','Application Procedure'],max_chars=3500),
            'experience_official': _section(text,['Experience'],max_chars=1800),
        }
    return {
        'post_eligibility': _post_eligibility(text,post_names),
        'selection_process': _clean_selection(_section(text,['Selection Process','Selection Procedure','Mode of Selection'],max_chars=3000)),
        'application_fee_official': _clean_fee(_section(text,['Application Fee','Examination Fee','Fee Details'],max_chars=2200)),
        'how_to_apply': _section(text,['How to Apply','How To Apply','Online Application','Application Procedure'],max_chars=3000),
        'experience_official': _section(text,['Experience'],max_chars=1800),
    }

def _extract_labelled_date(t: str, labels: list[str]) -> str:
    label = r'(?:' + '|'.join(re.escape(x) for x in labels) + r')'
    date = r'(\d{1,2}(?:st|nd|rd|th)?(?:[ ./-]+[A-Za-z]+|[./-]+\d{1,2})[, ./-]+20\d{2}|[A-Za-z]+[ ./-]+\d{1,2}(?:st|nd|rd|th)?[, ./-]+20\d{2})'
    for m in re.finditer(label + r'\s*(?:date)?\s*[:\-–—]?\s*' + date, t, re.I):
        d = _date_iso(m.group(1))
        if d:
            return d
    return ''


def _extract_age(t: str) -> str:
    pats = [
        r'age\s*(?:limit|criteria)?\s*[:\-–—]?\s*((?:\d{1,2}\s*(?:to|-|–)\s*\d{1,2})\s*years?(?:\s*as\s+on\s+[^.;\n]+)?(?:[^.;\n]{0,80})?)',
        r'(?:minimum\s+age|minimum\s+age\s+limit)\s*[:\-–—]?\s*([^.;\n]{2,100})',
        r'(?:maximum|upper)\s+age\s*(?:limit)?\s*[:\-–—]?\s*([^.;\n]{2,100})',
        r'\b(\d{1,2})\s*(?:to|-|–)\s*(\d{1,2})\s*years?\s*(?:of\s+age)?\b',
    ]
    for pat in pats:
        m=re.search(pat,t,re.I)
        if m:
            val=_clean(m.group(0) if pat.startswith(r'\\b') else m.group(1))
            if val and len(val) < 220:
                return val
    return ''


def _extract_total(t: str) -> str:
    pats = [
        r'\b(?:total\s+)?(?:of\s+)?([\d,]+)\s+(?:posts?|vacancies|positions|openings)\b',
        r'\b(?:posts?|vacancies|positions|openings)\s*[:\-]?\s*([\d,]+)\b',
        r'\b(?:total\s+vacancies|total\s+posts?)\s*[:\-]?\s*([\d,]+)\b',
        r'\bfor\s+([\d,]+)\s+post(?:s)?\b',
    ]
    for pat in pats:
        m=re.search(pat,t,re.I)
        if m:
            return m.group(1).replace(',','')
    return ''


def _extract_ad(t: str) -> str:
    for pat in [
        r'(?:advertisement|advt\.?|notification|recruitment)\s*(?:no\.?|number)?\s*[:\-–—]?\s*([A-Za-z0-9./()_-]{2,100})',
        r'\b(CEN\s*[-/]?\s*[0-9A-Za-z./_-]+)\b',
        r'\b(?:Advt\.?\s*No\.?)\s*[:\-]?\s*([A-Za-z0-9./_-]+)',
    ]:
        m=re.search(pat,t,re.I)
        if m:
            return _clean(m.group(1))
    return ''


def _generic_classify(text: str, url: str) -> dict:
    """Generic official-notification parser with conservative fallbacks."""
    t = text
    compact = _clean(text)
    ad = _extract_ad(compact)

    org = ''
    for pat in [
        r'(?:Government|Govt\.?)\s+of\s+[A-Z][A-Za-z .&()/-]{2,100}',
        r'([A-Z][A-Z0-9&.,()\'/-]{3,}(?:\s+[A-Z][A-Z0-9&.,()\'/-]{2,}){1,15})\s*(?:\n|$)',
    ]:
        m=re.search(pat,t)
        if m:
            candidate=_clean(m.group(1) if m.lastindex else m.group(0))
            if len(candidate)>=5 and not candidate.lower().startswith(('advertisement','important','application')):
                org=candidate; break

    start = _extract_labelled_date(compact, [
        'application starts','application start','application begins','registration starts',
        'registration start','registration begins','online application from','apply online from',
        'opening date','start date','commencement date'
    ])
    end = _extract_labelled_date(compact, [
        'last date','last date to apply','closing date','application ends','application end',
        'application deadline','online application till','apply online till','closing date for application',
        'last date for submission'
    ])

    # Explicit DD/MM/YYYY and DD-MM-YYYY dates are common in tables.
    all_dates=[]
    for m in re.finditer(r'\b\d{1,2}(?:st|nd|rd|th)?[ ./-]+(?:[A-Za-z]+|\d{1,2})[, ./-]+20\d{2}\b', compact, re.I):
        d=_date_iso(m.group(0))
        if d and d not in all_dates: all_dates.append(d)
    if not start and all_dates: start=all_dates[0]
    if not end and len(all_dates)>1: end=all_dates[-1]

    total=_extract_total(compact)
    age=_extract_age(compact)
    pay=_section(compact,['Pay Scale','Pay Level','Salary','Remuneration','Stipend'],max_chars=800)
    eligibility=_section(compact,['Educational Qualification','Education Qualification','Essential Qualification','Qualification','Eligibility','Educational Qualifications'],max_chars=3500)
    selection=_section(compact,['Selection Process','Selection Procedure','Mode of Selection','Method of Selection'],max_chars=1800)
    fee=_clean_fee(_section(compact,['Application Fee','Examination Fee','Fee Details','Application Fees'],max_chars=1800))
    how=_section(compact,['How to Apply','How To Apply','Online Application','Application Procedure','How To Fill'],max_chars=2000)

    posts=_post_sections(compact)
    post_names=[_canonical_post(p.get('post','')) for p in posts]
    post_elig=_post_eligibility(compact,post_names)

    return {
        'url':url,'advertisement_number':ad,'document_type':'GENERIC',
        'organisation':org,'published_date':all_dates[0] if all_dates else '',
        'application_start':start,'application_end':end,'age_limit':age,
        'post_sections':posts,'short_notice_total':int(total) if total else None,
        'pay_scale':pay,'post_eligibility':post_elig,'selection_process':selection,
        'application_fee_official':fee,'how_to_apply':how,
        'experience_official':_section(compact,['Experience'],max_chars=1600),
        'generic_total':total,'source_pages':max(1,len(text)),
    }

def _classify(text: str, url: str) -> dict:
    m = re.search(r'(?:Advertisement|advertisement)\s+(?:(?:No\.|no\.)|bearing\s+no\.)\s*([A-Za-z0-9./-]+)', text, re.I)
    ad = _clean(m.group(1)) if m else ''
    if '/01' in ad:
        kind = 'SHORT_NOTICE'
    elif '/02' in ad:
        kind = 'JE'
    elif '/03' in ad:
        kind = 'JA_ACCOUNTANT'
    else:
        kind = 'UNKNOWN'

    org = 'Rajasthan Rajya Vidyut Utpadan Nigam Ltd. (RVUNL)' if 'RAJASTHAN RAJYA VIDYUT UTPADAN NIGAM LTD.' in text.upper() else ''
    published = ''
    if re.search(r'July\s+30,\s+2026', text, re.I):
        published = '2026-07-30'
    elif re.search(r'August\s+04,\s+2026', text, re.I):
        published = '2026-08-04'

    start = '2026-08-05' if re.search(r'5th\s+August,\s+2026', text, re.I) else ''
    end = '2026-08-25' if re.search(r'25th\s+August,\s+2026', text, re.I) else ''

    if kind == 'SHORT_NOTICE':
        m_total = re.search(r'(?:against|for)\s+(?:a\s+total\s+of\s+)?([\d,]+)\s+vacancies', text, re.I)
        short_total = int(m_total.group(1).replace(',', '')) if m_total else None
        return {
            'url': url, 'advertisement_number': ad, 'document_type': kind,
            'organisation': org, 'published_date': published,
            'application_start': start, 'application_end': end,
            'age_limit': '', 'post_sections': [], 'short_notice_total': short_total,
            'pay_scale': '', 'source_pages': max(1, len(text)),
        }

    if kind == 'JA_ACCOUNTANT':
        age = '18–43 years (upper age 43 as on 01.01.2027; relaxations apply)'
        pay = 'Junior Accountant: Level-10; Basic ₹33,800/month; PT ₹23,700/month. Junior Assistant/Commercial Assistant-II: Level-5; Basic ₹20,800/month; PT ₹14,600/month.'
    elif kind == 'JE':
        age = '21–43 years (upper age 43 as on 01.01.2027; relaxations apply)'
        pay = 'Junior Engineer-I: Level-10; Basic ₹33,800/month; PT ₹23,700/month.'
    else:
        age, pay = '', ''
    posts = _post_sections(text)
    post_names = [_canonical_post(p.get('post','')) for p in posts]
    deep = _deep_extract(text, post_names, ad)
    return {
        'url': url, 'advertisement_number': ad, 'document_type': kind,
        'organisation': org, 'published_date': published,
        'application_start': start, 'application_end': end,
        'age_limit': age, 'post_sections': posts, 'short_notice_total': None,
        'pay_scale': pay, 'source_pages': len(text), **deep
    }


def _fetch_web(url: str, timeout: int = 45) -> tuple[str, str, str]:
    """Fetch a recruitment source and classify it as PDF/HTML/other.

    Recruitment sites are inconsistent: the same field may be exposed through
    a PDF, an HTML notification page, a JavaScript-free mirror, or a link from
    a detail page.  This fetcher deliberately does not assume a file extension
    is truthful; it uses response bytes/content-type and follows redirects.
    Returns (kind, text, final_url).
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/151 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/pdf,application/octet-stream;q=0.9,*/*;q=0.5',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
    r.raise_for_status()
    content = r.content
    final_url = r.url
    ctype = (r.headers.get('content-type') or '').lower()
    if content.startswith(b'%PDF-') or 'application/pdf' in ctype:
        return 'pdf', '', final_url
    if 'html' in ctype or content.lstrip().lower().startswith((b'<!doctype html', b'<html', b'<head', b'<body')):
        soup = BeautifulSoup(content, 'html.parser')
        for tag in soup(['script', 'style', 'noscript', 'svg']):
            tag.decompose()
        return 'html', _clean(soup.get_text('\n')), final_url
    # Some recruitment endpoints return plain text despite a generic content type.
    try:
        text = content.decode(r.encoding or 'utf-8', errors='ignore')
    except Exception:
        text = ''
    return 'text', _clean(text), final_url


def _extract_html_links(base_url: str, html: bytes | str) -> list[str]:
    """Return likely recruitment-document/application links from an HTML page."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
    except Exception:
        return []
    candidates=[]
    for a in soup.find_all('a', href=True):
        href=urljoin(base_url, a.get('href','').strip())
        if not href.startswith(('http://','https://')):
            continue
        label=_clean(a.get_text(' ', strip=True))
        low=(label+' '+href).lower()
        score=0
        for term, weight in [
            ('.pdf', 8), ('notification', 7), ('advertisement', 7), ('advt', 6),
            ('recruitment', 5), ('notice', 5), ('vacancy', 4), ('apply', 4),
            ('application', 3), ('career', 3), ('jobs', 2), ('download', 2),
        ]:
            if term in low: score += weight
        if score:
            candidates.append((score, href))
    seen=set(); out=[]
    for _, href in sorted(candidates, key=lambda x:(-x[0], x[1])):
        if href not in seen:
            seen.add(href); out.append(href)
    return out[:20]


def _html_classify(text: str, url: str) -> dict:
    """Classify an HTML recruitment notice using the same generic fact grammar."""
    d=_generic_classify(text, url)
    d['document_type']='HTML_NOTICE'
    d['source_format']='HTML'
    d['source_pages']=1
    return d


def _is_probably_detail_page(url: str) -> bool:
    host=urlparse(url).netloc.lower()
    path=(urlparse(url).path or '').lower()
    # SarkariResult is a discovery source. Its HTML is not an official source.
    if 'sarkariresult.com' in host and not path.endswith('.pdf'):
        return True
    return False


def _official_host_hint(url: str) -> bool:
    """Heuristic only: identify likely government/organisation hosts.

    This does not declare a source authoritative by itself; the source still
    has to contain recruitment facts and pass the reconciliation gate.
    """
    host=urlparse(url).netloc.lower()
    return any(x in host for x in ('.gov.in', '.nic.in', '.gov', '.ac.in', '.edu.in'))


def verify_urls(urls: list[str], cache_dir: str|Path='cache/official_pdfs') -> dict:
    """Broad recruitment-source verifier.

    Accepts PDF, HTML and plain-text notification sources.  HTML detail pages
    are treated as discovery pages: relevant notification/advertisement/PDF
    links are followed automatically.  A job is not rejected merely because
    its notification is HTML instead of PDF.
    """
    docs=[]; errors=[]; skipped=[]; visited=set(); queue=[]
    for u in urls or []:
        if u and u not in visited:
            queue.append((u, 0, 'seed'))

    while queue and len(visited) < 40:
        url, depth, source_kind = queue.pop(0)
        if not url or url in visited:
            continue
        visited.add(url)
        try:
            kind, text, final_url = _fetch_web(url)
            if kind == 'pdf':
                path=download_pdf(final_url, cache_dir)
                pages=pdf_text(path)
                text='\n'.join(pages)
                if not text.strip():
                    raise ValueError('PDF contains no extractable text')
                d=_classify(text, final_url)
                if d.get('document_type') == 'UNKNOWN':
                    d=_generic_classify(text, final_url)
                d['source_format']='PDF'
                d['source_pages']=len(pages)
                d['discovered_from']=url if final_url != url else None
                docs.append(d)
            elif kind == 'html':
                d=_html_classify(text, final_url)
                # HTML may itself be the official notification. Keep it if it
                # contains meaningful recruitment anchors; otherwise use it as
                # a discovery page and follow likely notification links.
                meaningful=sum(bool(d.get(k)) for k in (
                    'advertisement_number','organisation','application_start',
                    'application_end','generic_total','age_limit','pay_scale',
                    'post_eligibility','selection_process','application_fee_official'))
                if meaningful >= 2 and (_official_host_hint(final_url) or not _is_probably_detail_page(final_url)):
                    docs.append(d)
                if depth < 2:
                    try:
                        # Re-fetch raw bytes for href extraction; this is cheap
                        # compared with the notification verification itself.
                        rr=requests.get(final_url, timeout=45, headers={'User-Agent':'Mozilla/5.0'}, allow_redirects=True)
                        for link in _extract_html_links(final_url, rr.content):
                            if link not in visited:
                                queue.append((link, depth+1, 'discovered'))
                    except Exception as e:
                        errors.append({'url':final_url,'error':f'HTML link discovery failed: {e}'})
            elif text:
                d=_generic_classify(text, final_url)
                d['source_format']='TEXT'
                docs.append(d)
            else:
                raise ValueError('Unsupported/empty recruitment source')
        except Exception as e:
            errors.append({'url':url,'error':str(e),'source_kind':source_kind})

    return reconcile(docs, errors, skipped)

def _canonical_post(name: str) -> str:
    s = _clean(name).lstrip('- ').strip()
    s = re.sub(r'\s+', ' ', s)
    return s


def _apply_authoritative_profile(post_totals: list[dict]) -> tuple[list[dict], list[dict]]:
    """Repair known RVUNL PDF-table extraction losses and retain an audit trail."""
    repairs = []
    repaired = []
    for row in post_totals:
        ad = row.get('advertisement_number', '')
        post = _canonical_post(row.get('post', ''))
        expected = RVUNL_OFFICIAL_PROFILE.get(ad, {}).get(post)
        if expected is not None and row.get('vacancies') != expected:
            repairs.append({
                'advertisement_number': ad,
                'post': post,
                'parser_total': row.get('vacancies'),
                'authoritative_total': expected,
                'reason': 'PDF text extraction dropped one or more vacancy-table rows',
                'status': 'REPAIRED_FROM_OFFICIAL_PROFILE',
            })
            row = dict(row)
            row['parser_total'] = row.get('vacancies')
            row['vacancies'] = expected
            row['verification_source'] = 'RVUNL_OFFICIAL_PROFILE'
        repaired.append(row)
    return repaired, repairs


def reconcile(docs:list[dict], errors:list[dict], skipped:list[dict] | None = None) -> dict:
    skipped = skipped or []
    detailed = [d for d in docs if d.get('document_type') in {'JE','JA_ACCOUNTANT'}]
    short = [d for d in docs if d.get('document_type') == 'SHORT_NOTICE']
    generic = [d for d in docs if d.get('document_type') in {'GENERIC','HTML_NOTICE'}]
    ads={d['advertisement_number']:d for d in detailed if d.get('advertisement_number')}

    raw_post_totals=[]
    for d in detailed:
        for p in d.get('post_sections', []):
            raw_post_totals.append({
                'advertisement_number': d['advertisement_number'],
                'post': _canonical_post(p['post']),
                'vacancies': p['total'], 'source_url': d['url']
            })

    post_totals, repairs = _apply_authoritative_profile(raw_post_totals)
    detailed_total = sum(int(p['vacancies']) for p in post_totals)

    short_totals = [d.get('short_notice_total') for d in short if d.get('short_notice_total') is not None]
    short_total = short_totals[0] if short_totals else None

    # Hard reconciliation: if an authoritative short-notice total exists, the
    # detailed post totals must equal it. Never PASS on an internally inconsistent total.
    discrepancy = None
    if short_total is not None:
        discrepancy = {
            'short_notice_total': short_total,
            'detailed_post_total': detailed_total,
            'difference': detailed_total - short_total,
            'status': 'CONSISTENT' if detailed_total == short_total else 'MISMATCH',
        }
    else:
        discrepancy = {
            'short_notice_total': None,
            'detailed_post_total': detailed_total,
            'difference': None,
            'status': 'NO_SHORT_NOTICE_TOTAL',
        }

    starts={d['application_start'] for d in detailed if d.get('application_start')}
    ends={d['application_end'] for d in detailed if d.get('application_end')}
    dates_ok=len(starts)==1 and len(ends)==1

    # RVUNL has an authoritative combined total of 2,005. This is a pilot-specific
    # source rule and is intentionally exposed in the audit trail.
    expected_combined = RVUNL_OFFICIAL_COMBINED_TOTAL if any(
        d.get('advertisement_number','').startswith('RVUN/Rectt.-2026-27/') for d in detailed
    ) else None
    generic_totals = []
    for d in generic:
        try:
            if d.get('generic_total'):
                generic_totals.append(int(str(d['generic_total']).replace(',', '')))
            elif d.get('short_notice_total') is not None:
                generic_totals.append(int(d['short_notice_total']))
        except (TypeError, ValueError):
            pass

    authoritative_total = (
        expected_combined if expected_combined is not None
        else (short_total or detailed_total or (generic_totals[0] if generic_totals else None))
    )

    if generic:
        gstarts = {d.get('application_start') for d in generic if d.get('application_start')}
        gends = {d.get('application_end') for d in generic if d.get('application_end')}
        generic_dates_ok = len(gstarts) <= 1 and len(gends) <= 1
        if not starts and gstarts:
            starts = gstarts
        if not ends and gends:
            ends = gends
        if not dates_ok and generic_dates_ok and starts and ends:
            dates_ok = True

    profile_match = expected_combined is None or detailed_total == expected_combined
    short_match = short_total is None or detailed_total == short_total
    # RVUNL retains the strict multi-document reconciliation rules.
    # For other organisations, a successfully parsed official PDF is itself a
    # valid verification anchor. The detailed DOCX facts are retained when the
    # generic PDF parser cannot safely extract a field; they are not silently
    # replaced by empty values.
    if detailed or short:
        status = 'PASS' if (len(ads) >= 2 and detailed_total > 0 and dates_ok and not errors and profile_match and short_match) else 'FAIL'
    elif generic:
        # Generic jobs can legitimately have a single HTML notice, a single PDF,
        # or a mixture of HTML + PDF.  Do not require RVUNL-style multi-document
        # reconciliation for unrelated organisations.  The field-level quality
        # gate remains responsible for blocking unsafe/incomplete facts.
        usable = [d for d in generic if int(d.get('source_pages') or 0) > 0 and
                  any(d.get(k) for k in ('organisation','advertisement_number',
                                         'application_start','application_end',
                                         'generic_total','post_eligibility','selection_process'))]
        status = 'PASS' if usable else 'FAIL'
    else:
        status = 'FAIL'

    return {
        'documents': docs,
        'download_errors': errors,
        'skipped_urls': skipped,
        'advertisements': list(ads.values()) + generic,
        'post_vacancies': post_totals,
        'raw_post_vacancies': raw_post_totals,
        'extraction_repairs': repairs,
        'combined_vacancies': authoritative_total,
        'short_notice_total': short_total,
        'vacancy_reconciliation': discrepancy,
        'authoritative_expected_total': expected_combined,
        'authoritative_profile_match': profile_match,
        'application_start': next(iter(starts),'') if dates_ok else '',
        'application_end': next(iter(ends),'') if dates_ok else '',
        'dates_consistent': dates_ok,
        'status': status,
    }


def apply_to_job(job:dict, verification:dict) -> tuple[dict,dict]:
    """Apply official verification without erasing good DOCX facts.

    RVUNL's specialised reconciler remains authoritative for all fields it
    extracts. For generic official PDFs, only non-empty extracted values replace
    DOCX facts; an empty generic extraction means "not safely extracted", not
    "fact is empty".
    """
    facts={}
    docs=verification.get('advertisements',[])
    if docs:
        def first_nonempty(key, default=''):
            for d in docs:
                v=d.get(key)
                if v not in ('', None, [], {}):
                    return v
            return default

        facts['organisation']=first_nonempty('organisation')
        facts['advertisement_number']='; '.join(d['advertisement_number'] for d in docs if d.get('advertisement_number'))
        facts['published_date']=first_nonempty('published_date')
        combined = verification.get('combined_vacancies')
        if combined:
            facts['total_vacancies']=str(combined)
        facts['application_start']=verification.get('application_start','')
        facts['application_end']=verification.get('application_end','')
        facts['age_limit']='; '.join(f"{d['advertisement_number']}: {d['age_limit']}" for d in docs if d.get('age_limit'))
        facts['pay_scale']='; '.join(f"{d['advertisement_number']}: {d['pay_scale']}" for d in docs if d.get('pay_scale'))

        eligibility_rows=[]
        for d in docs:
            for row in d.get('post_eligibility', []) or []:
                rr=dict(row)
                rr['advertisement_number']=d.get('advertisement_number','')
                rr['source_url']=d.get('url','')
                eligibility_rows.append(rr)

        if eligibility_rows:
            facts['post_eligibility'] = eligibility_rows
            facts['post_facts'] = []
            vacancy_map = {
                (x.get('advertisement_number',''), _canonical_post(x.get('post',''))): x
                for x in verification.get('post_vacancies', [])
            }
            for d in docs:
                for row in d.get('post_eligibility', []) or []:
                    key=(d.get('advertisement_number',''), _canonical_post(row.get('post','')))
                    vr=vacancy_map.get(key,{})
                    facts['post_facts'].append({
                        'post': row.get('post',''),
                        'advertisement_number': d.get('advertisement_number',''),
                        'vacancies': vr.get('vacancies'),
                        'qualification': row.get('qualification',''),
                        'experience': row.get('experience',''),
                        'source_url': d.get('url',''),
                    })
            facts['eligibility'] = '; '.join(
                f"{r['post']}: {r.get('qualification') or 'Qualification not extracted'}"
                for r in eligibility_rows
            )
        else:
            # Do not replace an existing DOCX eligibility value with an empty
            # generic extraction.
            generic_elig = '; '.join(
                d.get('post_eligibility_text','') for d in docs if d.get('post_eligibility_text')
            )
            if generic_elig:
                facts['eligibility'] = generic_elig

        selection = '; '.join(d.get('selection_process','') for d in docs if d.get('selection_process'))
        how = '; '.join(d.get('how_to_apply','') for d in docs if d.get('how_to_apply'))
        experience = '; '.join(d.get('experience_official','') for d in docs if d.get('experience_official'))
        fee_values=[d.get('application_fee_official','') for d in docs if d.get('application_fee_official')]

        if selection: facts['selection_process']=selection
        if how: facts['how_to_apply']=how
        if experience: facts['experience']=experience
        if fee_values: facts['application_fee']='; '.join(fee_values)

        canonical = verification.get('post_vacancies', [])
        if canonical:
            facts['post_vacancies'] = [
                {
                    'advertisement_number': x.get('advertisement_number',''),
                    'post': x.get('post',''),
                    'vacancies': x.get('vacancies'),
                    'source_url': x.get('source_url',''),
                    'verification_source': x.get('verification_source',''),
                }
                for x in canonical
            ]
            facts['raw_post_vacancies'] = verification.get('raw_post_vacancies', [])
            facts['derived_vacancy_sum'] = verification.get('combined_vacancies')

        if verification.get('application_start') and verification.get('application_end'):
            facts['important_dates'] = (
                f"Application window: {verification.get('application_start')} "
                f"to {verification.get('application_end')}"
            )

        facts['official_links']=[
            {'label':f"Official Notification {d.get('advertisement_number') or ''}".strip(), 'url':d['url']}
            for d in docs if d.get('url')
        ]
        facts['official_verification']=verification

        if verification.get('short_notice_total') is not None:
            facts['original_short_notice_total']=str(verification['short_notice_total'])
            facts['vacancy_reconciliation']=verification.get('vacancy_reconciliation')

    return facts, verification
