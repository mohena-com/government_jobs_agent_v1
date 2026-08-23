from src.sarkariresult.detail import classify_domain

def test_domain_classification():
    assert classify_domain("https://www.sarkariresult.com/foo") == "sarkariresult"
    assert classify_domain("https://upsc.gov.in/foo") == "likely_official"
    assert classify_domain("https://example.com/foo") == "third_party"
