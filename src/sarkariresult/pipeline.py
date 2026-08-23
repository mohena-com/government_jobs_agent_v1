from datetime import datetime
from zoneinfo import ZoneInfo

from .parser import find_latest_listings
from .detail import extract_detail


IST = ZoneInfo("Asia/Kolkata")


def crawl(max_jobs=None, only=None):

    today = datetime.now(
        IST
    ).date()

    listings = find_latest_listings(
        today
    )

    # Optional debugging filter
    if only:

        keys = [
            x.strip().lower()
            for x in only.split(",")
            if x.strip()
        ]

        listings = [
            x
            for x in listings
            if any(
                key in x["title"].lower()
                for key in keys
            )
        ]

    if max_jobs:

        listings = listings[
            :max_jobs
        ]

    results = []

    for listing in listings:

        print(
            f"\nProcessing: {listing['title']}"
        )

        try:

            job = extract_detail(
                listing["url"],
                listing
            )

            results.append(
                job
            )

            print(
                "  Post:",
                job["post_title"]
            )

            print(
                "  Organisation:",
                job["organisation"]
            )

            print(
                "  Vacancies:",
                job["total_vacancies"]
            )

            print(
                "  Application:",
                job["application_start"],
                "->",
                job["application_end"]
            )

            print(
                "  Vacancy rows:",
                len(job["vacancy_rows"])
            )

        except Exception as exc:

            print(
                "  ERROR:",
                exc
            )

            results.append({

                "listing": listing,

                "detail_url":
                    listing["url"],

                "post_title":
                    "",

                "organisation":
                    "",

                "total_vacancies":
                    None,

                "vacancy_rows":
                    [],

                "error":
                    str(exc),
            })

    return today, results