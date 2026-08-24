from src.verify_official import _generic_classify, reconcile

GENERIC_TEXT = """
BANK OF BARODA
RECRUITMENT OF SPECIALIST OFFICERS
Advertisement No. BOB/HR/2026/123
Applications open from 05 August 2026
Last date to apply: 26 August 2026
Total 206 Posts
Age Limit: 21 to 35 years
Pay Scale: Pay Level 10
Educational Qualification: Bachelor's Degree in Engineering from a recognized university.
Selection Process: Online Examination and Interview.
Application Fee: General: Rs. 850/-; SC/ST: Rs. 175/-.
How to Apply: Apply online through the official website.
"""

def test_v1923_generic_official_pdf_is_not_unknown():
    d = _generic_classify(GENERIC_TEXT, "https://bank.example.gov/notice.pdf")
    assert d["document_type"] == "GENERIC"
    assert d["application_end"] == "2026-08-26"
    assert d["generic_total"] == "206"
    assert d["age_limit"]
    assert d["pay_scale"]

def test_v1923_generic_verification_can_pass_with_valid_pdf():
    d = _generic_classify(GENERIC_TEXT, "https://bank.example.gov/notice.pdf")
    r = reconcile([d], [])
    assert r["status"] == "PASS"
    assert r["advertisements"]

def test_v1923_bad_auxiliary_url_does_not_invalidate_good_pdf():
    d = _generic_classify(GENERIC_TEXT, "https://bank.example.gov/notice.pdf")
    r = reconcile([d], [{"url":"https://example.invalid/bad","error":"not a pdf"}], [])
    # The valid official PDF remains a usable verification anchor; the
    # auxiliary failure stays in download_errors for audit.
    assert r["status"] == "PASS"
    assert r["download_errors"]

HTML_NOTICE = """
<html><head><title>Bank Recruitment 2026</title></head><body>
<h1>Bank of Baroda Specialist Officer Recruitment 2026</h1>
<p>Advertisement No. BOB/HR/2026/123</p>
<p>Applications open from 05 August 2026</p>
<p>Last date to apply: 26 August 2026</p>
<p>Total 206 Posts</p>
<p>Age Limit: 21 to 35 years</p>
<p>Educational Qualification: Bachelor's Degree in Engineering from a recognized university.</p>
<p>Selection Process: Online Examination and Interview.</p>
<p>Application Fee: General: Rs. 850/-; SC/ST: Rs. 175/-.</p>
</body></html>
"""

def test_v1925_html_notice_is_supported():
    from src.verify_official import _html_classify
    d = _html_classify(HTML_NOTICE, "https://bank.gov.in/recruitment/notice")
    assert d["document_type"] == "HTML_NOTICE"
    assert d["application_end"] == "2026-08-26"
    assert d["generic_total"] == "206"
    assert d["age_limit"]
    assert d["selection_process"]


def test_v1925_html_notification_is_a_valid_generic_anchor():
    from src.verify_official import _html_classify
    d = _html_classify(HTML_NOTICE, "https://bank.gov.in/recruitment/notice")
    r = reconcile([d], [])
    assert r["status"] == "PASS"
    assert r["advertisements"]
