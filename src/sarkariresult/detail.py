import re
from urllib.parse import urljoin, urldefrag, urlparse
import requests
from bs4 import BeautifulSoup

from .parser import HEADERS

OFFICIAL_DOMAIN_SUFFIXES = (
    ".gov.in", ".nic.in", ".ac.in", ".edu.in", ".org.in", ".res.in"
)

LINK_KEYWORDS = (
    "apply online", "apply now", "online form", "official website",
    "notification", "advertisement", "download notification",
    "official notification", "pdf", "application form", "registration"
)

SECTION_HINTS = (
    "important date", "application fee", "vacancy", "eligibility",
    "qualification", "age limit", "selection", "salary", "pay scale",
    "how to apply", "important instruction", "exam", "syllabus",
    "notification", "job location", "post name", "total post"
)

def fetch_detail(url):
    r = requests.get(url, headers=HEADERS, timeout=45, allow_redirects=True)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    return soup, r.url, r.text

def clean_visible_text(soup):
    clone = BeautifulSoup(str(soup), "lxml")
    for tag in clone(["script", "style", "noscript", "svg"]):
        tag.decompose()
    lines = []
    for line in clone.get_text("\n").splitlines():
        line = " ".join(line.split())
        if line:
            lines.append(line)
    return "\n".join(lines)

def extract_tables(soup):
    tables = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [" ".join(c.get_text(" ", strip=True).split())
                     for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables

def classify_domain(url):
    host = urlparse(url).hostname or ""
    host = host.lower()
    if host == "sarkariresult.com" or host.endswith(".sarkariresult.com"):
        return "sarkariresult"
    if host.endswith(OFFICIAL_DOMAIN_SUFFIXES):
        return "likely_official_government_or_institution"
    return "third_party"

def extract_links(soup, base_url):
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        href = a.get("href", "").strip()
        url = urljoin(base_url, href)
        url, _ = urldefrag(url)
        if not url or url in seen:
            continue

        low = text.lower()
        # Also inspect href because many pages have image/icon links with
        # weak visible text.
        href_low = href.lower()
        if any(k in low or k in href_low for k in LINK_KEYWORDS):
            seen.add(url)
            links.append({
                "text": text,
                "url": url,
                "domain_class": classify_domain(url),
            })
    return links

def find_best_official_links(links):
    official = [x for x in links
                if x["domain_class"] == "likely_official_government_or_institution"]
    notifications = [
        x for x in official
        if any(k in x["text"].lower() for k in ("notification", "advertisement", "pdf", "download"))
        or x["url"].lower().endswith(".pdf")
    ]
    applications = [
        x for x in official
        if any(k in x["text"].lower() for k in ("apply", "online form", "application", "registration"))
    ]
    return {
        "official_links": official,
        "notification_links": notifications,
        "application_links": applications,
    }

def extract_detail(url, listing):
    soup, final_url, raw_html = fetch_detail(url)
    text = clean_visible_text(soup)
    tables = extract_tables(soup)
    links = extract_links(soup, final_url)
    classified = find_best_official_links(links)

    return {
        "listing": listing,
        "detail_url": final_url,
        "detail_text": text,
        "tables": tables,
        "links": links,
        **classified,
        "detail_ok": len(text) > 300,
    }
