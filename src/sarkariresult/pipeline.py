from datetime import datetime, date
from zoneinfo import ZoneInfo

from .parser import find_latest_listings
from .detail import extract_detail

IST = ZoneInfo("Asia/Kolkata")

def _published_date(value):
    if not value:
        return None
    text = str(value).strip()
    # SarkariResult commonly uses: "05 August 2026 | 11:13 PM"
    for fmt in ("%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text.split("|")[0].strip(), fmt).date()
        except ValueError:
            pass
    return None

def crawl(max_jobs=None, only=None, published_on: date | None = None):
    today = datetime.now(IST).date()
    listings = find_latest_listings(today)

    if only:
        keys = [x.strip().lower() for x in only.split(",") if x.strip()]
        listings = [
            x for x in listings
            if any(k in x["title"].lower() for k in keys)
        ]

    # When filtering by publication date, do NOT truncate the discovery list
    # before fetching details. The first N listings may be older jobs with later
    # deadlines, which previously caused --published-today to return zero even
    # when newer listings existed further down the page.
    if max_jobs and published_on is None:
        listings = listings[:max_jobs]

    results = []
    for listing in listings:
        try:
            detail = extract_detail(listing["url"], listing)
        except Exception as e:
            detail = {
                "listing": listing,
                "detail_url": listing["url"],
                "detail_text": "",
                "tables": [],
                "links": [],
                "official_links": [],
                "notification_links": [],
                "application_links": [],
                "detail_ok": False,
                "error": str(e),
            }
        results.append(detail)

    if published_on is not None:
        filtered = []
        for item in results:
            published = _published_date(item.get("post_update"))
            if published == published_on:
                filtered.append(item)
        results = filtered
        if max_jobs:
            results = results[:max_jobs]

    return today, results
