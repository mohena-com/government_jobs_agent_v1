from datetime import datetime
from zoneinfo import ZoneInfo

from .parser import find_latest_listings
from .detail import extract_detail

IST = ZoneInfo("Asia/Kolkata")

def crawl(max_jobs=None, only=None):
    today = datetime.now(IST).date()
    listings = find_latest_listings(today)

    if only:
        keys = [x.strip().lower() for x in only.split(",") if x.strip()]
        listings = [
            x for x in listings
            if any(k in x["title"].lower() for k in keys)
        ]

    if max_jobs:
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

    return today, results
