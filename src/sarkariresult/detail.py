from __future__ import annotations
import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "GovernmentJobsAgent/1.2 (+responsible automated monitoring)"}
OFFICIAL_SUFFIXES = (".gov.in", ".nic.in", ".ac.in", ".edu.in")
KNOWN_OFFICIAL_DOMAINS = {
    "upsc.gov.in", "upsconline.nic.in", "ssc.gov.in", "rrbapply.gov.in",
    "indianrailways.gov.in", "isro.gov.in", "drdo.gov.in", "ncs.gov.in",
    "iocl.com", "aai.aero", "sbi.co.in", "ibps.in"
}

def fetch_detail(url):
    r = requests.get(url, headers=HEADERS, timeout=45)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml"), r.url

def domain(url):
    return urlparse(url).netloc.lower().split(":")[0]

def is_probably_official(url):
    d = domain(url)
    return d in KNOWN_OFFICIAL_DOMAINS or d.endswith(OFFICIAL_SUFFIXES)

def extract_detail_links(soup, base_url):
    """Extract candidate official/application/notification links.

    SarkariResult is discovery only. A link is marked official_candidate when
    its destination matches configured government/institution domains.
    """
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        href = urljoin(base_url, a["href"])
        if href in seen:
            continue
        low = text.lower()
        if not any(k in low for k in (
            "apply online", "online form", "official website", "notification",
            "advertisement", "download", "official site", "registration"
        )):
            continue
        seen.add(href)
        out.append({
            "text": text,
            "url": href,
            "domain": domain(href),
            "official_candidate": is_probably_official(href),
        })
    return out

def extract_pdf_links(soup, base_url):
    out=[]
    for a in soup.find_all("a", href=True):
        href=urljoin(base_url,a["href"])
        if ".pdf" in href.lower():
            out.append(href)
    return list(dict.fromkeys(out))

def extract_detail_text(soup):
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return "\n".join(x.strip() for x in soup.get_text("\n").splitlines() if x.strip())
