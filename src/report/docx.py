def add_field(doc, label, value):

    p = doc.add_paragraph()

    p.add_run(
        label + ": "
    ).bold = True

    if value:

        p.add_run(
            str(value)
        )

    else:

        p.add_run(
            "Not found"
        )


def add_job_to_doc(doc, job):

    doc.add_heading(
        job.get("post_title")
        or job["listing"]["title"],
        level=1
    )

    add_field(
        doc,
        "Organisation",
        job.get("organisation")
    )

    add_field(
        doc,
        "Advertisement Number",
        job.get("advertisement_number")
    )

    add_field(
        doc,
        "Post Date / Update",
        job.get("post_update")
    )

    add_field(
        doc,
        "Total Vacancies",
        job.get("total_vacancies")
    )

    add_field(
        doc,
        "Application Start",
        job.get("application_start")
    )

    add_field(
        doc,
        "Application End",
        job.get("application_end")
    )

    add_field(
        doc,
        "Application Fee",
        job.get("application_fee")
    )

    add_field(
        doc,
        "Age Limit",
        job.get("age_limit")
    )

    doc.add_heading(
        "Vacancy-wise Posts",
        level=2
    )

    rows = job.get(
        "vacancy_rows",
        []
    )

    if rows:

        table = doc.add_table(
            rows=1,
            cols=2
        )

        table.rows[0].cells[0].text = "Post"
        table.rows[0].cells[1].text = "Vacancies"

        for row in rows:

            cells = table.add_row().cells

            cells[0].text = row[
                "post_name"
            ]

            cells[1].text = str(
                row["vacancies"]
            )

    else:

        doc.add_paragraph(
            "No vacancy table detected."
        )

    doc.add_heading(
        "Eligibility",
        level=2
    )

    doc.add_paragraph(
        job.get(
            "eligibility"
        )
        or "Not found"
    )

    doc.add_heading(
        "Important Dates",
        level=2
    )

    doc.add_paragraph(
        job.get(
            "important_dates_raw"
        )
        or "Not found"
    )

    doc.add_heading(
        "Application Fee",
        level=2
    )

    doc.add_paragraph(
        job.get(
            "application_fee"
        )
        or "Not found"
    )

    doc.add_heading(
        "Age Limit",
        level=2
    )

    doc.add_paragraph(
        job.get(
            "age_limit"
        )
        or "Not found"
    )

    doc.add_heading(
        "How to Apply",
        level=2
    )

    doc.add_paragraph(
        job.get(
            "how_to_apply"
        )
        or "Not found"
    )

    doc.add_heading(
        "Selection Process",
        level=2
    )

    doc.add_paragraph(
        job.get(
            "selection_process"
        )
        or "Not found"
    )

    doc.add_heading(
        "Pay / Salary",
        level=2
    )

    doc.add_paragraph(
        job.get(
            "pay_scale"
        )
        or "Not found"
    )