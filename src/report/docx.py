from pathlib import Path
from docx import Document
from docx.shared import Pt

def add_hyperlink(paragraph, text, url):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    if not url:
        return
    rid = paragraph.part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True
    )
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rid)
    r = OxmlElement("w:r")
    t = OxmlElement("w:t"); t.text = text
    r.append(t); h.append(r); paragraph._p.append(h)

def field(doc, label, value):
    p = doc.add_paragraph()
    p.add_run(label + ": ").bold = True
    p.add_run(str(value or "Not found"))
    return p

def make_report(today, results, out):
    doc = Document()
    doc.styles["Normal"].font.name = "Aptos"
    doc.styles["Normal"].font.size = Pt(9)

    doc.add_heading(f"SarkariResult Latest Jobs — Deep Detail Crawl — {today:%d %B %Y}", 0)
    doc.add_paragraph(
        "Scope: https://www.sarkariresult.com/latestjob/ only. "
        "Only listings with Last Date strictly later than today are included. "
        "Each retained listing is followed to its individual SarkariResult detail page."
    )

    doc.add_heading("Index", 1)
    table = doc.add_table(rows=1, cols=4)
    for c, label in zip(table.rows[0].cells, ["#", "Job", "Last Date", "Detail"]):
        c.text = label

    for i, r in enumerate(results, 1):
        cells = table.add_row().cells
        cells[0].text = str(i)
        cells[1].text = r["listing"]["title"]
        cells[2].text = r["listing"]["last_date"]
        add_hyperlink(cells[3].paragraphs[0], "Open detail", r["detail_url"])

    for r in results:
        doc.add_page_break()
        doc.add_heading(r.get("post_title") or r["listing"]["title"], 1)

        field(doc, "Last Date", r["listing"]["last_date"])
        field(doc, "Date Extended", r["listing"]["extended"])

        p = doc.add_paragraph()
        p.add_run("SarkariResult detail page: ").bold = True
        add_hyperlink(p, "Open detail", r["detail_url"])

        doc.add_heading("Actual detail-page fields", 2)
        field(doc, "Post / title", r.get("post_title"))
        field(doc, "Post Date / Update", r.get("post_update"))
        field(doc, "Short Information", r.get("short_information"))
        field(doc, "Important Dates", r.get("important_dates"))
        field(doc, "Application Fee", r.get("application_fee"))
        field(doc, "Age Limit", r.get("age_limit"))
        field(doc, "Vacancy Details", r.get("vacancy_details"))
        field(doc, "Eligibility", r.get("eligibility"))
        field(doc, "How to Fill / Apply", r.get("how_to_apply"))
        field(doc, "Selection Process", r.get("selection_process"))
        field(doc, "Pay Scale / Salary", r.get("pay_scale"))
        field(doc, "Important Instructions", r.get("important_instructions"))

        doc.add_heading("Action / notification links found on detail page", 2)
        if not r.get("links"):
            doc.add_paragraph("No matching action links found.")
        for x in r.get("links", []):
            p = doc.add_paragraph()
            p.add_run(f"[{x['domain_class']}] ").bold = True
            add_hyperlink(p, x["text"], x["url"])

        doc.add_heading("Detected tables", 2)
        if not r.get("tables"):
            doc.add_paragraph("No HTML tables detected.")
        for rows in r.get("tables", []):
            t = doc.add_table(rows=0, cols=max(len(row) for row in rows))
            for row in rows:
                cells = t.add_row().cells
                for j, value in enumerate(row):
                    cells[j].text = value

        doc.add_heading("Raw detail-page content", 2)
        if r.get("detail_text"):
            # Keep a bounded copy in the report; structured fields above are the
            # important output, while raw content makes debugging possible.
            for line in r["detail_text"].splitlines():
                if line:
                    doc.add_paragraph(line)
        else:
            doc.add_paragraph("Detail page could not be retrieved.")

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return out
