
from src.social.instagram import (
    clean_value,
    build_slide_plan,
    useful_links,
)


def test_clean_value_removes_social_garbage():
    text = """
    Telegram
    Join Us
    WhatsApp
    Instagram
    Follow
    X
    General / OBC / EWS: 1000/-
    """
    cleaned = clean_value(text)
    assert "Telegram" not in cleaned
    assert "Join Us" not in cleaned
    assert "WhatsApp" not in cleaned
    assert "Instagram" not in cleaned
    assert "Follow" not in cleaned
    assert "General / OBC / EWS: 1000/-" in cleaned


def test_empty_fields_do_not_create_sections():
    job = {
        "post_title": "Example Recruitment",
        "listing": {"title": "Example Recruitment"},
    }
    plan = build_slide_plan(job)
    assert plan == ["cover"]


def test_links_only_uses_real_urls():
    job = {
        "post_title": "Example Recruitment",
        "application_links": [{"url": "https://example.gov.in/apply"}],
        "notification_links": [],
    }
    links = useful_links(job)
    assert links[0] == ("APPLY ONLINE", "https://example.gov.in/apply")
