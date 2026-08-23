import re
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def add_hyperlink(paragraph, text, url):
    if not url:
        return
    rid = paragraph.part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rid)

    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    rPr.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rPr.append(underline)
    run.append(rPr)

    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    link.append(run)
    paragraph._p.append(link)


def set_cell_text(cell, text, bold=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(str(text or "Not found"))
    r.bold = bold
    r.font.size = Pt(8.5)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)


def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def set_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = tblPr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tblPr.append(borders)

    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "B7B7B7")


def add_section_heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text.upper())
    r.bold = True
    r.font.size = Pt(10)
    return p


def add_key_value_table(doc, rows):
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for label, value in rows:
        cells = table.add_row().cells
        set_cell_text(cells[0], label, True)
        set_cell_text(cells[1], value or "Not found")
        set_cell_shading(cells[0], "EDEDED")
    set_table_borders(table)
    retur
def _clean_section_lines(text):
    """Remove social/navigation artefacts and empty lines."""
    if not text:
        return []

    blocked = {
        "telegram", "join us", "whatsapp", "instagram",
        "follow", "x", "image"
    }

    lines = []
    for raw in str(text).splitlines():
        line = " ".join(raw.split()).strip()
        if not line:
            continue

        low = line.lower().strip("·-* ")

        # Remove exact social/navigation words.
        if low in blocked:
            continue

        # Remove combined forms such as "Telegram Join Us".
        if any(
            re.search(rf"\b{re.escape(word)}\b", low)
            for word in blocked
        ) and len(low) < 45:
            continue

        lines.append(line)

    return lines


def _compact_label_value_lines(lines):
    """
    Combine source lines such as:

        Pay Exam Fee Last Date :
        24/08/2026

    into:

        Pay Exam Fee Last Date: 24/08/2026

    Also handles:
        General / OBC / EWS :
        1000/-

    """
    result = []
    i = 0

    label_re = re.compile(
        r"^(.*?)(?:\s*:\s*)$"
    )

    while i < len(lines):
        current = lines[i].strip()

        # A line ending in ':' is a label. Combine it with the next line.
        if current.endswith(":") and i + 1 < len(lines):
            nxt = lines[i + 1].strip()

            # Do not combine a new heading with another heading.
            if nxt and not nxt.endswith(":"):
                result.append(
                    current.rstrip(":").strip() + ": " + nxt
                )
                i += 2
                continue

        # Handle "Label : Value" already on one line.
        result.append(current)
        i += 1

    return result


def add_compact_section(doc, text, mode="lines"):
    """
    Render section content compactly.

    For date/fee sections, label/value pairs are put on the SAME line.
    Long explanatory instructions remain as bullets.
    """
    lines = _clean_section_lines(text)

    if not lines:
        doc.add_paragraph("Not found")
        return

    compact = _compact_label_value_lines(lines)

    for line in compact:
        # Remove Markdown emphasis markers that otherwise make the report noisy.
        line = line.replace("**", "").replace("__", "").strip()

        if mode == "bullets":
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.left_indent = Inches(0.18)
            p.add_run(line)
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.keep_together = True
            p.add_run(line)

def add_vacancy_table(doc, rows):
    if not rows:
        doc.add_paragraph("No structured vacancy table detected.")
        return

    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    set_cell_text(hdr.cells[0], "Post", True)
    set_cell_text(hdr.cells[1], "Vacancies", True)
    set_cell_shading(hdr.cells[0], "D9EAF7")
    set_cell_shading(hdr.cells[1], "D9EAF7")

    for row in rows:
        cells = table.add_row().cells
        set_cell_text(cells[0], row.get("post_name", ""))
        set_cell_text(cells[1], row.get("vacancies", ""))

    set_table_borders(table)


def add_links(doc, job):
    links = []

    # Prefer application links and notification links detected by the crawler.
    for link in job.get("application_links", []):
        links.append(("Apply Online", link.get("url")))

    for link in job.get("notification_links", []):
        links.append(("Official Notification", link.get("url")))

    # De-duplicate.
    seen = set()
    links = [
        x for x in links
        if x[1] and not (x[0], x[1]) in seen and not seen.add((x[0], x[1]))
    ]

    # Official candidates as secondary links.
    for link in job.get("official_candidates", []):
        url = link.get("url")
        if url and url not in {x[1] for x in links}:
            label = link.get("text") or "Official Website"
            links.append((label, url))

    if not links:
        doc.add_paragraph("No external application/notification link detected.")
        return

    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for label, url in links[:6]:
        cells = table.add_row().cells
        set_cell_text(cells[0], label, True)
        cells[1].text = ""
        p = cells[1].paragraphs[0]
        add_hyperlink(p, "Open link", url)

    set_table_borders(table)


def add_job(doc, job, index):
    listing = job.get("listing", {})
    title = job.get("post_title") or listing.get("title") or "Recruitment Notice"

    if index > 1:
        doc.add_page_break()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title)
    r.bold = True
    r.font.size = Pt(15)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(job.get("organisation") or "Organisation not identified")
    r.bold = True
    r.font.size = Pt(10)

    # Deadline banner.
    deadline = job.get("application_end") or listing.get("last_date") or "Not found"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"APPLICATION DEADLINE: {deadline}")
    r.bold = True
    r.font.size = Pt(10)

    add_section_heading(doc, "Key Information")
    add_key_value_table(doc, [
        ("Advertisement / Reference No.", job.get("advertisement_number")),
        ("Published / Updated", job.get("post_update")),
        ("Total Vacancies", job.get("total_vacancies")),
        ("Application Start", job.get("application_start")),
        ("Application End", job.get("application_end")),
        ("Age Limit", job.get("age_limit")),
    ])

    add_section_heading(doc, "Important Dates")
    add_compact_section(doc, job.get("important_dates_raw"), mode="compact")

    add_section_heading(doc, "Application Fee")
    add_compact_section(doc, job.get("application_fee"), mode="compact")

    add_section_heading(doc, "Vacancy Details")
    add_vacancy_table(doc, job.get("vacancy_rows", []))

    add_section_heading(doc, "Eligibility")
    add_compact_section(doc, job.get("eligibility"), mode="bullets")

    add_section_heading(doc, "Selection Process")
    add_compact_section(doc, job.get("selection_process"), mode="bullets")

    add_section_heading(doc, "Pay / Salary")
    add_compact_section(doc, job.get("pay_scale"), mode="bullets")

    add_section_heading(doc, "How to Apply")
    add_compact_section(doc, job.get("how_to_apply"), mode="bullets")

    add_section_heading(doc, "Official Links")
    add_links(doc, job)

    add_section_heading(doc, "Source")
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.add_run("SarkariResult detail page: ").bold = True
    add_hyperlink(p, "Open source page", job.get("detail_url", ""))

    # No raw HTML/text is inserted into the report.


def make_report(today, results, out):
    doc = Document()

    section = doc.sections[0]
    section.top_margin = Inches(0.45)
    section.bottom_margin = Inches(0.45)
    section.left_margin = Inches(0.55)
    section.right_margin = Inches(0.55)

    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(8.5)

    # Cover / index
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"Government Jobs Report — {today:%d %B %Y}")
    r.bold = True
    r.font.size = Pt(18)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(
        "Source: SarkariResult Latest Jobs | Future last-date listings only"
    ).font.size = Pt(9)

    add_section_heading(doc, "Index")

    table = doc.add_table(rows=1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for cell, label in zip(
        hdr.cells,
        ["#", "Organisation", "Post", "Last Date"]
    ):
        set_cell_text(cell, label, True)
        set_cell_shading(cell, "D9EAF7")

    for i, job in enumerate(results, 1):
        listing = job.get("listing", {})
        cells = table.add_row().cells
        set_cell_text(cells[0], i)
        set_cell_text(
            cells[1],
            job.get("organisation") or "Not identified"
        )
        set_cell_text(
            cells[2],
            job.get("post_title") or listing.get("title", "")
        )
        set_cell_text(
            cells[3],
            job.get("application_end") or listing.get("last_date", "")
        )

    set_table_borders(table)

    for i, job in enumerate(results, 1):
        add_job(doc, job, i)

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return out
