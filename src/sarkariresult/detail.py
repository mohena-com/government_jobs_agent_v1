import re
from urllib.parse import urljoin, urldefrag, urlparse
import requests
from bs4 import BeautifulSoup

from .parser import HEADERS

LINK_KEYWORDS = (
    "apply online", "apply now", "online form", "official website",
    "notification", "advertisement", "download notification",
    "official notification", "pdf", "application form", "registration",
    "click here to apply", "click here"
)

SECTION_HEADINGS = {
    "important_dates": ["important dates"],
    "application_fee": ["application fee", "exam fee"],
    "age_limit": ["age limit"],
    "vacancy_details": ["vacancy details", "vacancy detail"],
    "eligibility": ["eligibility", "educational qualification", "qualification"],
    "how_to_apply": ["how to fill", "how to apply"],
    "selection_process": ["selection process", "selection procedure"],
    "pay_scale": ["pay scale", "salary", "pay level"],
    "important_instructions": ["important instruction", "important note", "instructions"],
}

def fetch_detail(url):
    r = requests.get(url, headers=HEADERS, timeout=45, allow_redirects=True)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    return soup, r.url, r.text

def clean(s):
    return " ".join((s or "").split()).strip()

def clean_visible_text(soup):
    clone = BeautifulSoup(str(soup), "lxml")
    for tag in clone(["script", "style", "noscript", "svg"]):
        tag.decompose()
    lines = []
    for line in clone.get_text("\n").splitlines():
        line = clean(line)
        if line:
            lines.append(line)
    return "\n".join(lines)

def extract_tables(soup):
    tables = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [clean(c.get_text(" ", strip=True))
                     for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables

def classify_domain(url):
    host = (urlparse(url).hostname or "").lower()
    if host == "sarkariresult.com" or host.endswith(".sarkariresult.com"):
        return "sarkariresult"
    if host.endswith(".gov.in") or host.endswith(".nic.in") or host.endswith(".ac.in"):
        return "likely_official"
    # Known official PSU/company domain examples are not automatically declared
    # authoritative here; they are simply separated from SarkariResult.
    return "third_party"

def extract_links(soup, base_url):
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        text = clean(a.get_text(" ", strip=True))
        href = a.get("href", "").strip()
        url = urljoin(base_url, href)
        url, _ = urldefrag(url)
        if not url or url in seen:
            continue
        low = (text + " " + href).lower()
        # Capture ALL useful job-action links, including image/button anchors.
        if any(k in low for k in LINK_KEYWORDS):
            seen.add(url)
            links.append({
                "text": text or "(button/image link)",
                "url": url,
                "domain_class": classify_domain(url),
            })
    return links

def _section_text(full_text, headings):
    lines = full_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        low = line.lower().strip()
        if any(h in low for h in headings):
            start = i
            break
    if start is None:
        return ""
    stop_words = [
        "sarkari result", "important dates", "application fee",
        "age limit", "vacancy details", "how to fill",
        "selection process", "important instruction"
    ]
    out = []
    for line in lines[start:]:
        low = line.lower().strip()
        if len(out) > 0 and any(w in low for w in stop_words) and low not in [x.lower() for x in headings]:
            break
        out.append(line)
    return "\n".join(out).strip()

def extract_structured_page(soup, text):
    # These are intentionally page-level fields, not official-notification
    # enrichment. They prove that we have reached and parsed the detail page.
    result = {
        "post_title": "",
        "post_update": "",
        "short_information": "",
        "important_dates": "",
        "application_fee": "",
        "age_limit": "",
        "vacancy_details": "",
        "eligibility": "",
        "how_to_apply": "",
        "selection_process": "",
        "pay_scale": "",
        "important_instructions": "",
    }

    # H1/title is more reliable than the listing anchor.
    h1 = soup.find("h1")
    if h1:
        result["post_title"] = clean(h1.get_text(" ", strip=True))

    # Common SarkariResult metadata labels. The site has appeared in both
    # two-line and same-line forms, e.g.
    #   Post Date / Update: 23 August 2026
    #   Post Date / Update\n    #   23 August 2026
    lines = text.splitlines()
    for i, line in enumerate(lines):
        low = line.lower().strip()
        if "post date / update" in low:
            tail = re.split(r"post\s*date\s*/\s*update\s*[:\-]?", line, maxsplit=1, flags=re.I)
            if len(tail) == 2 and tail[1].strip():
                result["post_update"] = tail[1].strip()
            elif i + 1 < len(lines):
                result["post_update"] = lines[i + 1].strip()
        if "short information" in low:
            # The short paragraph usually follows the label and before social links.
            vals = []
            for x in lines[i + 1:i + 12]:
                xl = x.lower()
                if any(k in xl for k in ("telegram", "whatsapp", "instagram", "twitter", "join us", "follow")):
                    break
                if x.strip():
                    vals.append(x)
            result["short_information"] = " ".join(vals).strip()

    for key, headings in SECTION_HEADINGS.items():
        result[key] = _section_text(text, headings)

    return result

def find_best_links(links):
    notification = []
    application = []
    official_candidates = []

    for x in links:
        low = x["text"].lower() + " " + x["url"].lower()
        if any(k in low for k in ("notification", "advertisement", "download notification")) or x["url"].lower().endswith(".pdf"):
            notification.append(x)
        if any(k in low for k in ("apply online", "apply now", "online form", "application form", "registration", "click here to apply")):
            application.append(x)
        if x["domain_class"] != "sarkariresult":
            official_candidates.append(x)

    return {
        "notification_links": notification,
        "application_links": application,
        "external_candidates": official_candidates,
    }

def extract_detail(url, listing):
    soup, final_url, raw_html = fetch_detail(url)
    text = clean_visible_text(soup)
    tables = extract_tables(soup)
    links = extract_links(soup, final_url)
    structured = extract_structured_page(soup, text)
    best = find_best_links(links)

    return {
        "listing": listing,
        "detail_url": final_url,
        "detail_text": text,
        "tables": tables,
        "links": links,
        **structured,
        **best,
        "detail_ok": len(text) > 300,
    }
