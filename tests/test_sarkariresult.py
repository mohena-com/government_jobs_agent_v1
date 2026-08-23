from datetime import date
from src.sarkariresult.parser import parse_date

def test_parse_dates():
    assert parse_date("GIMS Staff Nurse Online Form 2026 | Last Date : 07/09/2026")==date(2026,9,7)
    assert parse_date("Date Extended | Last Date : 10/09/2026")==date(2026,9,10)
    assert parse_date("No closing date") is None
