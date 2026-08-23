import re
from src.models import Page

# UPSC direct-recruitment advertisements use vacancy-number headings such as:
# "(Vacancy No. 26070901525)"
VACANCY_RE = re.compile(r"\(Vacancy\s+No\.?\s*([0-9A-Za-z/-]+)\)", re.I)

def find_segments(pages: list[Page]):
    hits = []
    for p in pages:
        for m in VACANCY_RE.finditer(p.text):
            hits.append((m.group(1), p.number, m.start()))

    if not hits:
        return []

    segments = []
    for i, (vacancy_no, start_page, start_pos) in enumerate(hits):
        if i + 1 < len(hits):
            next_page = hits[i+1][1]
            end_page = next_page
        else:
            end_page = pages[-1].number

        text_parts = []
        for p in pages:
            if start_page <= p.number <= end_page:
                if p.number == start_page:
                    text_parts.append(p.text[start_pos:])
                else:
                    text_parts.append(p.text)
        segments.append({
            "vacancy_no": vacancy_no,
            "start_page": start_page,
            "end_page": end_page,
            "text": "\n".join(text_parts)
        })
    return segments
