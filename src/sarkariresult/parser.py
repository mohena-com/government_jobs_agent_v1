from __future__ import annotations
import re
from datetime import date, datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

LATEST_URL = "https://www.sarkariresult.com/latestjob/"
HEADERS = {"User-Agent": "GovernmentJobsAgent/1.2 (+responsible automated monitoring)"}

DATE_PATTERNS = [
    r"last\s*date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
    r"last\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
    r"last\s*date\s*:?\s*(\d{1,2}\.\d{1,2}\.\d{4})",
]

def parse_date(text: str):
    for pat in DATE_PATTERNS:
        m = re.search(pat, text or "", re.I)
        if not m:
            continue
        raw = m.group(1)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                pass
    return None

def fetch_latest():
    r = requests.get(LATEST_URL, headers=HEADERS, timeout=45)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml"), r.url

def scan_latest_jobs(today: date | None = None):
    """Return only listings with a provable future closing date.

    A missing/ambiguous date is excluded rather than guessed.
    """
    today = today or date.today()
    soup, base_url = fetch_latest()
    rows, seen = [], set()

    for a in soup.find_all("a", href=True):
        title = " ".join(a.get_text(" ", strip=True).split())
        if not title:
            continue
        low = title.lower()
        if "last date" not in low and "last :" not in low:
            continue

        last_date = parse_date(title)
        if last_date is None or last_date <= today:
            continue

        url = urljoin(base_url, a["href"])
        if url in seen:
            continue
        seen.add(url)
        rows.append({
            "title": title,
            "url": url,
            "last_date": last_date,
            "date_extended": "extended" in low,
            "source": LATEST_URL,
        })

    return sorted(rows, key=lambda r: (r["last_date"], r["title"].lower()))
