import re
from datetime import datetime
from src.models import Recruitment, Reservation, Provenance

def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()

def first(patterns, text):
    for p in patterns:
        m = re.search(p, text, re.I | re.S)
        if m:
            if m.lastindex and m.lastindex >= 2 and ("pay\\s+level" in p or p.startswith("(pay")):
                return clean("Level-" + m.group(2))
            return clean(m.group(1))
    return ""

def number_after(label, text):
    m = re.search(label + r".{0,100}?(\d[\d,]*)", text, re.I | re.S)
    return int(m.group(1).replace(",", "")) if m else None

def parse_reservation(text):
    r = Reservation()
    for key, attr in [("UR","ur"),("EWS","ews"),("OBC","obc"),("SC","sc"),("ST","st"),("PwBD","pwbd")]:
        m = re.search(rf"\b{key}\s*[-:]\s*(\d+)", text, re.I)
        if m:
            setattr(r, attr, int(m.group(1)))
    return r

def extract_segment(seg, advt_no, pdf_url):
    t = seg["text"]
    r = Recruitment(
        advertisement_no=advt_no,
        vacancy_no=seg["vacancy_no"],
        notification_url=pdf_url,
        pages_start=seg["start_page"],
        pages_end=seg["end_page"],
    )

    r.post_title = first([
        r"post\s*[:\-]\s*(.+?)(?:\n|$)",
        r"post\s+of\s+(.+?)(?:\n|$)",
        r"^\s*(?:\d+[\.\)]\s*)?(?:.*?vacancy\s+no\.[^\n]+)\n(.+?)(?:\n|$)"
    ], t)

    r.total_vacancies = (
        number_after(r"(?:total\s+)?(?:number\s+of\s+)?vacancies", t)
        or number_after(r"(?<!\w)(\d+)\s+vacancies?", t)
        or number_after(r"(?<!\w)(\d+)\s+vacanc(?:y|ies)", t)
    )

    r.ministry = first([
        r"ministry\s*(?:of)?\s*[:\-]\s*(.+?)(?:\n|$)",
        r"department\s+of\s+(.+?)(?:,\s*ministry|$)"
    ], t)

    r.department = first([
        r"department\s*[:\-]\s*(.+?)(?:\n|$)",
        r"department\s+of\s+(.+?)(?:,\s*ministry|$)"
    ], t)

    r.classification = first([r"classification\s*[:\-]\s*(.+?)(?:\n|$)"], t)
    r.service_status = first([r"(?:whether\s+permanent|status)\s*[:\-]\s*(.+?)(?:\n|$)"], t)
    r.pay_level = first([r"(pay\s+level\s*[-–:]\s*)(\d+)", r"pay\s+level\s*[:\-]?\s*(.+?)(?:\n|$)", r"(pay\s+)?level\s*[-–:]\s*(\d+)"], t)
    r.pay_scale = first([r"pay\s+scale\s*[:\-]\s*(.+?)(?:\n|$)"], t)

    r.age_limit = first([
        r"(?:age\s+limit|maximum\s+age)\s*[:\-]\s*(.+?)(?:\n|$)",
        r"age\s+not\s+exceeding\s*(.+?)(?:\n|$)"
    ], t)

    r.age_relaxation = first([
        r"age\s+relaxation\s*[:\-]\s*(.+?)(?:\n|$)",
        r"relaxation\s+in\s+age\s+limit\s*[:\-]?\s*(.+?)(?:\n|$)"
    ], t)

    r.essential_qualification = first([
        r"essential\s+qualifications?\s*[:\-]?\s*(.+?)(?=\n\s*(?:ii|desirable|experience|duties|age|pay)\b)",
        r"essential\s+qualification\s*[:\-]?\s*(.+?)(?=\n\s*[A-Z][A-Za-z ]{2,30}\s*:)"
    ], t)

    r.desirable_qualification = first([
        r"desirable\s+qualifications?\s*[:\-]?\s*(.+?)(?=\n\s*(?:experience|duties|age|pay)\b)"
    ], t)

    r.essential_experience = first([
        r"essential\s+experience\s*[:\-]?\s*(.+?)(?=\n\s*(?:desirable|duties|age|pay)\b)",
        r"experience\s*[:\-]\s*(.+?)(?=\n\s*(?:desirable|duties|age|pay)\b)"
    ], t)

    r.desirable_experience = first([
        r"desirable\s+experience\s*[:\-]?\s*(.+?)(?=\n\s*(?:duties|age|pay)\b)"
    ], t)

    r.duties = first([
        r"duties\s*[:\-]?\s*(.+?)(?=\n\s*(?:headquarters|probation|age|pay|selection)\b)"
    ], t)

    r.headquarters = first([r"headquarters\s*[:\-]?\s*(.+?)(?:\n|$)"], t)
    r.posting = first([r"place\s+of\s+posting\s*[:\-]?\s*(.+?)(?:\n|$)", r"posting\s*[:\-]?\s*(.+?)(?:\n|$)"], t)
    r.probation = first([r"probation\s*[:\-]?\s*(.+?)(?:\n|$)"], t)
    r.service_liability = first([r"service\s+liability\s*[:\-]?\s*(.+?)(?:\n|$)"], t)
    r.pwbd_suitability = first([r"(?:suitable|suitability).*?PwBD.*?[:\-]\s*(.+?)(?:\n|$)"], t)

    r.application_start = first([
        r"applications?\s+can\s+be\s+made\s+from\s+(.+?)(?:\n|$)",
        r"online\s+application.*?from\s+(.+?)(?:\n|$)"
    ], t)

    r.application_end = first([
        r"last\s+date.*?application.*?[:\-]\s*(.+?)(?:\n|$)",
        r"closing\s+date.*?[:\-]\s*(.+?)(?:\n|$)"
    ], t)

    r.application_fee = first([
        r"application\s+fee\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"fee\s*[:\-]?\s*(.+?)(?:\n|$)"
    ], t)

    r.selection_process = first([
        r"method\s+of\s+recruitment\s*[:\-]?\s*(.+?)(?=\n\s*(?:age|qualification|experience)\b)",
        r"selection\s+process\s*[:\-]?\s*(.+?)(?=\n\s*[A-Z])"
    ], t)

    r.important_instructions = first([
        r"important\s+instructions?\s*[:\-]?\s*(.+?)(?=\n\s*(?:NOTE|Annexure|$))"
    ], t)

    r.reservation = parse_reservation(t)

    # Confidence is deliberately conservative. Missing critical fields generate warnings.
    critical = [r.post_title, r.total_vacancies, r.essential_qualification, r.age_limit, r.pay_level]
    r.confidence = sum(bool(x) for x in critical) / len(critical)

    for name, value in [
        ("post_title", r.post_title),
        ("total_vacancies", str(r.total_vacancies or "")),
        ("essential_qualification", r.essential_qualification),
        ("age_limit", r.age_limit),
        ("pay_level", r.pay_level),
    ]:
        if value:
            r.provenance.append(Provenance(
                field=name,
                page_start=seg["start_page"],
                page_end=seg["end_page"],
                evidence=clean(t[:700])
            ))

    return r
