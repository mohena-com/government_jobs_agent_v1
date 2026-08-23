import fitz
from src.models import Page

def read_pages(path: str) -> list[Page]:
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text", sort=True)
        pages.append(Page(number=i, text=text))
    return pages
