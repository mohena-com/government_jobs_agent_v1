from datetime import date
from src.sarkariresult.parser import parse_date

def test_future_date_parser():
    assert parse_date("RCFL Management Trainee Online Form 2026 | Last Date : 24/08/2026") == date(2026,8,24)
