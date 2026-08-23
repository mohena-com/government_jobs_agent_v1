import re
import requests
from datetime import datetime, date
from urllib.parse import urljoin, urldefrag
from bs4 import BeautifulSoup

LATEST_URL = "https://www.sarkariresult.com/latestjob/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36 GovernmentJobsAgent/2.0"
    )
}

DATE_PATTERNS = [
    r"last\s*date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
    r"last\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
    r"last\s*date\s*:?\s*(\d{1,2}-\d{1,2}-\d{4})",
    r"last\s*:?\s*(\d{1,2}-\d{1,2}-\d{4})",
    r"last\s*date\s*:?\s*(\d{1,2}\.\d{1,2}\.\d{4})",
]

def parse_date(text):
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

def normalise_url(url, base):
    if not url:
        return ""
    url = urljoin(base, url)
    url, _ = urldefrag(url)
    return url

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=45, allow_redirects=True)
    r.raise_for_status()
    return r.text, r.url, r.headers.get("content-type", "")

def find_latest_listings(today=None):
    today = today or date.today()
    html, final_url, _ = fetch(LATEST_URL)
    soup = BeautifulSoup(html, "lxml")

    rows = []
    seen = set()

    # IMPORTANT: do not search only for anchors whose visible text contains
    # "Last Date". We inspect every anchor in the All Latest Jobs section.
    container = soup.find(id=re.compile("latest|job", re.I))
    anchors = soup.find_all("a", href=True)

    for a in anchors:
        title = " ".join(a.get_text(" ", strip=True).split())
        if not title:
            continue

        last_date = parse_date(title)
        if not last_date:
            continue

        # Strictly future.
        if last_date <= today:
            continue

        url = normalise_url(a.get("href"), final_url)
        if not url or url in seen:
            continue

        # Ignore navigation links and keep job-like entries.
        low = title.lower()
        if not any(k in low for k in (
            "online form", "recruitment", "vacancy", "apprentice",
            "post", "officer", "engineer", "assistant", "teacher",
            "scientist", "manager", "clerk", "trainee", "admit"
        )):
            continue

        seen.add(url)
        rows.append({
            "title": title,
            "url": url,
            "last_date": last_date.isoformat(),
            "extended": "extended" in low,
            "discovery_source": LATEST_URL,
        })

    rows.sort(key=lambda x: (x["last_date"], x["title"].lower()))
    return rows
