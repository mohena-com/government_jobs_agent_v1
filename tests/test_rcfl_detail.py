from bs4 import BeautifulSoup
from src.sarkariresult.detail import clean_visible_text, extract_structured_page

def test_rcfl_detail_fields():
    html = """
    <h1>RCFL Management Trainee Recruitment 2026 Apply Online for 94 Post</h1>
    <p>Post Date / Update :</p><p>08 August 2026 | 12:25 PM</p>
    <h2>Important Dates</h2>
    <p>Application Begin : 08/08/2026</p>
    <p>Last Date for Apply Online : 24/08/2026 upto 05 PM</p>
    <h2>Application Fee</h2>
    <p>General / OBC / EWS: 1000/-</p>
    <h2>Age Limit</h2>
    <p>Maximum Age : 27 Years</p>
    <h2>Vacancy Details Total : 94 Post</h2>
    <table><tr><th>Post Name</th><th>Total Post</th></tr>
    <tr><td>Management Trainee (Chemical)</td><td>32</td></tr></table>
    <h2>How to Fill RCF Management Trainee Online Form 2026</h2>
    <p>Candidate Read the Notification Before Apply.</p>
    """
    soup = BeautifulSoup(html, "lxml")
    text = clean_visible_text(soup)
    data = extract_structured_page(soup, text)
    assert "94 Post" in data["vacancy_details"]
    assert "27 Years" in data["age_limit"]
    assert "1000/-" in data["application_fee"]
    assert "24/08/2026" in data["important_dates"]
    assert data["post_title"].startswith("RCFL Management Trainee")
    assert len(data["short_information"]) >= 0
