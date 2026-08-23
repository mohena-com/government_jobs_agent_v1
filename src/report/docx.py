from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def hyperlink(paragraph, text, url):
    if not url: return
    part = paragraph.part
    rid = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rid)
    run = OxmlElement("w:r")
    t = OxmlElement("w:t"); t.text = text
    run.append(t); link.append(run); paragraph._p.append(link)

def add_field(doc, label, value):
    p = doc.add_paragraph()
    p.add_run(label + ": ").bold = True
    p.add_run(str(value or "Not stated"))

def make_report(advt, records, out):
    doc = Document()
    doc.styles["Normal"].font.name = "Aptos"
    doc.styles["Normal"].font.size = Pt(9)

    doc.add_heading(f"UPSC Recruitment Deep Report — Advertisement {advt}", 0)
    doc.add_paragraph("Generated from the official UPSC recruitment advertisement PDF. Each vacancy is treated as a separate recruitment record.")

    table = doc.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, x in zip(table.rows[0].cells, ["#", "Vacancy No.", "Post", "Vacancies", "Confidence"]):
        c.text = x

    for i, r in enumerate(records, 1):
        cells = table.add_row().cells
        cells[0].text = str(i)
        cells[1].text = r.vacancy_no
        cells[2].text = r.post_title or "Not extracted"
        cells[3].text = str(r.total_vacancies or "Not extracted")
        cells[4].text = f"{r.confidence:.0%}"

    for r in records:
        doc.add_page_break()
        doc.add_heading(r.post_title or "UPSC Recruitment", 1)
        for label, value in [
            ("Advertisement No.", r.advertisement_no),
            ("Vacancy No.", r.vacancy_no),
            ("Ministry", r.ministry),
            ("Department", r.department),
            ("Organisation", r.organisation),
            ("Total vacancies", r.total_vacancies),
            ("Reservation", r.reservation.model_dump(exclude_none=True)),
            ("Classification", r.classification),
            ("Service status", r.service_status),
            ("Pay level", r.pay_level),
            ("Pay scale", r.pay_scale),
            ("Age limit", r.age_limit),
            ("Age relaxation", r.age_relaxation),
            ("Essential qualification", r.essential_qualification),
            ("Desirable qualification", r.desirable_qualification),
            ("Essential experience", r.essential_experience),
            ("Desirable experience", r.desirable_experience),
            ("Duties", r.duties),
            ("Headquarters", r.headquarters),
            ("Posting", r.posting),
            ("Probation", r.probation),
            ("Service liability", r.service_liability),
            ("PwBD suitability", r.pwbd_suitability),
            ("Selection process", r.selection_process),
            ("Application start", r.application_start),
            ("Application end", r.application_end),
            ("Application fee", r.application_fee),
            ("Important instructions", r.important_instructions),
        ]:
            add_field(doc, label, value)

        p = doc.add_paragraph()
        p.add_run("Application: ").bold = True
        hyperlink(p, "UPSC ORA", r.application_url)

        p = doc.add_paragraph()
        p.add_run("Official notification: ").bold = True
        hyperlink(p, "UPSC PDF", r.notification_url)

        add_field(doc, "Source pages", f"{r.pages_start}–{r.pages_end}")
        add_field(doc, "Extraction confidence", f"{r.confidence:.0%}")

        if r.warnings:
            add_field(doc, "Warnings", " | ".join(r.warnings))

        if r.provenance:
            doc.add_heading("Field provenance", 2)
            for pinfo in r.provenance:
                add_field(doc, pinfo.field, f"PDF pages {pinfo.page_start}–{pinfo.page_end}")

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
