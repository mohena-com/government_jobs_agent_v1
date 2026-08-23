from src.social.qwen_renderer import _compact_age, _compact_pay, _compact_fee, _compact_qualification


def test_compact_age_strips_boilerplate():
    assert _compact_age("RVUNL/Rectt.2026-27/02: 21–43 years (upper age 43 as on 01.01.2026)") == "21–43 years"


def test_compact_pay_strips_advertisement_prefix():
    value = _compact_pay("RVUNL/Rectt.2026-27/02: Junior Engineer-I: Level-10; Basic Pay: ₹56,100")
    assert "Level-10" in value
    assert "Basic Pay: ₹56,100" in value
    assert "RVUNL/Rectt" not in value


def test_compact_fee_keeps_amounts():
    value = _compact_fee("Application Fees General /: 1000/- EWS / BC / MBC SC / ST / PH: 500/- Pay online only")
    assert "1000" in value
    assert "500" in value


def test_compact_qualification_removes_legal_boilerplate():
    value = _compact_qualification("Full Time four years’ Graduation Degree in Engineering as a regular student or AMIE in Electrical/Electrical & Electronics Engineering from a University/Institution established by Law in India and recognized equivalent to full time degree")
    assert len(value) <= 205
    assert "4-year full-time" in value
    assert "University/Institution established by Law" not in value
