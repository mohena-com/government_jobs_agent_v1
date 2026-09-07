import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ScrapeStore:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scraped_jobs (
                url TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                last_date TEXT,
                scraped_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def has_scraped(self, url):
        row = self.connection.execute(
            "SELECT 1 FROM scraped_jobs WHERE url = ?",
            (url,),
        ).fetchone()
        return row is not None

    def mark_scraped(self, listing):
        self.connection.execute(
            """
            INSERT OR IGNORE INTO scraped_jobs (url, title, last_date, scraped_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                listing["url"],
                listing.get("title", ""),
                listing.get("last_date"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.connection.commit()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
