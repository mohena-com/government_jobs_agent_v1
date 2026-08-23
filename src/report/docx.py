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
    t = OxmlElement("w:t")
    t.text = text
    r.append(t)
    h.append(r)
    paragraph._p.append(h)

def add_label(p, label, value):
    p.add_run(label + ": ").bold = True
    p.add_run(str(value or "Not found"))

def make_report(today, results, out):
    doc = Document()
    doc.styles["Normal"].font.name = "Aptos"
    doc.styles["Normal"].font.size = Pt(9)

    doc.add_heading(f"Government Jobs — Deep SarkariResult Crawl — {today:%d %B %Y}", 0)
    doc.add_paragraph(
        "SarkariResult is used only for discovery. Each future-dated listing is "
        "followed to its individual detail page. Official links are separately identified."
    )

    # Index
    doc.add_heading("Index", 1)
    table = doc.add_table(rows=1, cols=6)
    for c, label in zip(table.rows[0].cells,
                        ["#", "Listing", "Last Date", "Detail Page", "Official Notification", "Official Application"]):
        c.text = label

    for i, r in enumerate(results, 1):
        row = table.add_row().cells
        row[0].text = str(i)
        row[1].text = r["listing"]["title"]
        row[2].text = r["listing"]["last_date"]

        p = row[3].paragraphs[0]
        add_hyperlink(p, "Open", r["detail_url"])

        p = row[4].paragraphs[0]
        if r.get("notification_links"):
            add_hyperlink(p, "Notification", r["notification_links"][0]["url"])
        else:
            p.add_run("Not found")

        p = row[5].paragraphs[0]
        if r.get("application_links"):
            add_hyperlink(p, "Apply", r["application_links"][0]["url"])
        else:
            p.add_run("Not found")

    for r in results:
        doc.add_page_break()
        doc.add_heading(r["listing"]["title"], 1)

        add_label(doc.add_paragraph(), "Last Date", r["listing"]["last_date"])
        add_label(doc.add_paragraph(), "Date Extended", r["listing"]["extended"])

        p = doc.add_paragraph()
        p.add_run("SarkariResult detail page: ").bold = True
        add_hyperlink(p, "Open detail", r["detail_url"])

        if r.get("notification_links"):
            p = doc.add_paragraph()
            p.add_run("Official notification: ").bold = True
            add_hyperlink(p, r["notification_links"][0]["url"], r["notification_links"][0]["url"])
        else:
            add_label(doc.add_paragraph(), "Official notification", "Not found on detail page")

        if r.get("application_links"):
            p = doc.add_paragraph()
            p.add_run("Official application: ").bold = True
            add_hyperlink(p, r["application_links"][0]["url"], r["application_links"][0]["url"])
        else:
            add_label(doc.add_paragraph(), "Official application", "Not found on detail page")

        doc.add_heading("Discovered links", 2)
        for link in r.get("links", []):
            p = doc.add_paragraph(style=None)
            p.add_run(f"[{link['domain_class']}] ").bold = True
            add_hyperlink(p, link["text"] or link["url"], link["url"])

        doc.add_heading("Detail-page content", 2)
        if r.get("detail_text"):
            # Keep the actual source content. This is the material the next
            # structured extraction layer will parse.
            for line in r["detail_text"].splitlines():
                if line:
                    doc.add_paragraph(line)
        else:
            doc.add_paragraph("Detail page could not be retrieved.")

        if r.get("tables"):
            doc.add_heading("Tables detected on detail page", 2)
            for table_data in r["tables"]:
                t = doc.add_table(rows=0, cols=max(len(x) for x in table_data))
                for rowdata in table_data:
                    cells = t.add_row().cells
                    for j, value in enumerate(rowdata):
                        cells[j].text = value

        if r.get("error"):
            add_label(doc.add_paragraph(), "Crawler error", r["error"])

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return out
