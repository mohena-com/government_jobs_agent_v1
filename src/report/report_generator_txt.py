
import re
from pathlib import Path


SOCIAL_GARBAGE = {
    "telegram", "join us", "whatsapp", "instagram",
    "follow", "x", "image",
}


def clean_report_value(value):
    if value is None:
        return ""

    cleaned_lines = []

    for raw_line in str(value).splitlines():
        line = raw_line.strip()
        if not line:
            continue

        line = line.lstrip("·•*- ").strip()
        if not line:
            continue

        low = line.lower()

        if low in SOCIAL_GARBAGE:
            continue

        if (
            ("telegram" in low or "whatsapp" in low or "instagram" in low)
            and len(line) < 100
        ):
            continue

        if (
            (low.startswith("join us") or low.startswith("follow"))
            and len(line) < 100
        ):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def _clean_section_lines(text):
    if not text:
        return []

    lines = []

    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            continue

        line = line.lstrip("·•*- ").strip()
        line = clean_report_value(line)

        if line:
            lines.append(line)

    return lines


def _compact_label_value_lines(lines):
    result = []
    i = 0

    while i < len(lines):
        current = lines[i].strip()

        if current.endswith(":") and i + 1 < len(lines):
            nxt = lines[i + 1].strip()

            if nxt and not nxt.endswith(":"):
                result.append(
                    current.rstrip(":").strip() + ": " + nxt
                )
                i += 2
                continue

        result.append(current)
        i += 1

    return result


def _safe_filename(text, max_len=90):
    text = clean_report_value(text) or "Recruitment"
    text = re.sub(r"[^\w\s.-]", "", text)
    text = re.sub(r"\s+", "_", text).strip("_")
    return text[:max_len] or "Recruitment"


def _write_section(lines, title, value, mode="lines"):
    lines.append("")
    lines.append(title.upper())
    lines.append("-" * len(title))

    section_lines = _clean_section_lines(value)

    if not section_lines:
        lines.append("Not found")
        return

    for line in _compact_label_value_lines(section_lines):
        line = line.replace("**", "").replace("__", "").strip()
        line = clean_report_value(line)
        if not line:
            continue
        if mode == "bullets":
            lines.append(f"- {line}")
        else:
            lines.append(line)


def _build_job_text(job, index=None):
    listing = job.get("listing", {})

    title = (
        job.get("post_title")
        or listing.get("title")
        or "Recruitment Notice"
    )

    organisation = clean_report_value(
        job.get("organisation")
    ) or "Organisation not identified"

    deadline = (
        job.get("application_end")
        or listing.get("last_date")
        or "Not found"
    )

    lines = [
        title,
        "=" * len(title),
        f"Organisation: {organisation}",
        f"Application Deadline: {clean_report_value(deadline)}",
        "",
        "KEY INFORMATION",
        "---------------",
        f"Advertisement / Reference No.: {clean_report_value(job.get('advertisement_number')) or 'Not found'}",
        f"Published / Updated: {clean_report_value(job.get('post_update')) or 'Not found'}",
        f"Total Vacancies: {clean_report_value(job.get('total_vacancies')) or 'Not found'}",
        f"Application Start: {clean_report_value(job.get('application_start')) or 'Not found'}",
        f"Application End: {clean_report_value(job.get('application_end')) or 'Not found'}",
        f"Age Limit: {clean_report_value(job.get('age_limit')) or 'Not found'}",
    ]

    _write_section(lines, "Important Dates", job.get("important_dates_raw"))
    _write_section(lines, "Application Fee", job.get("application_fee"))

    lines.append("")
    lines.append("VACANCY DETAILS")
    lines.append("---------------")
    vacancy_rows = job.get("vacancy_rows", [])
    if vacancy_rows:
        for row in vacancy_rows:
            post = clean_report_value(row.get("post_name")) or "Not found"
            vacancies = clean_report_value(row.get("vacancies")) or "Not found"
            lines.append(f"- {post}: {vacancies}")
    else:
        lines.append("No structured vacancy table detected.")

    _write_section(lines, "Eligibility", job.get("eligibility"), mode="eligibility")
    _write_section(lines, "Selection Process", job.get("selection_process"), mode="bullets")
    _write_section(lines, "Pay / Salary", job.get("pay_scale"), mode="bullets")
    _write_section(lines, "How to Apply", job.get("how_to_apply"), mode="bullets")

    lines.append("")
    lines.append("OFFICIAL LINKS")
    lines.append("--------------")

    links = []
    for link in job.get("application_links", []):
        url = link.get("url")
        if url:
            links.append(("Apply Online", url))

    for link in job.get("notification_links", []):
        url = link.get("url")
        if url:
            links.append(("Official Notification", url))

    existing_urls = {url for _, url in links}
    for link in job.get("official_candidates", []):
        url = link.get("url")
        if url and url not in existing_urls:
            links.append((link.get("text") or "Official Website", url))
            existing_urls.add(url)

    seen = set()
    for label, url in links:
        key = (label, url)
        if key not in seen:
            seen.add(key)
            lines.append(f"{label}: {url}")

    if not seen:
        lines.append("No external application/notification link detected.")

    lines.append("")
    lines.append("SOURCE")
    lines.append("------")
    detail_url = job.get("detail_url", "")
    lines.append(f"SarkariResult detail page: {detail_url or 'Not found'}")

    return "\n".join(lines).strip() + "\n"


def make_summary_report(today, results, out):
    """Create the summary/index TXT file."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"Government Jobs Report — {today:%d %B %Y}",
        "Source: SarkariResult Latest Jobs | Future last-date listings only",
        "",
        "INDEX",
        "=====",
        "",
    ]

    for i, job in enumerate(results, 1):
        listing = job.get("listing", {})
        organisation = job.get("organisation") or "Not identified"
        post = job.get("post_title") or listing.get("title", "")
        last_date = job.get("application_end") or listing.get("last_date", "")

        lines.extend([
            f"{i}. Organisation: {organisation}",
            f"   Post: {post}",
            f"   Last Date: {last_date or 'Not found'}",
            "",
        ])

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _summary_from_job_reports(today, jobs_dir, out):
    entries = []
    seen_urls = set()
    for path in sorted(Path(jobs_dir).glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        source = re.search(r"^SarkariResult detail page:\s*(.+)$", text, re.MULTILINE)
        source_url = source.group(1).strip() if source else ""
        if source_url and source_url in seen_urls:
            continue
        if source_url:
            seen_urls.add(source_url)
        title = text.splitlines()[0].strip() if text.splitlines() else path.stem
        organisation = re.search(r"^Organisation:\s*(.+)$", text, re.MULTILINE)
        deadline = re.search(r"^Application Deadline:\s*(.+)$", text, re.MULTILINE)
        entries.append({
            "post_title": title,
            "organisation": organisation.group(1).strip() if organisation else "Not identified",
            "application_end": deadline.group(1).strip() if deadline else "",
        })

    return make_summary_report(today, entries, out)


def make_job_reports(today, results, output_dir):
    """Create one TXT file per recruitment."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = []

    for i, job in enumerate(results, 1):
        listing = job.get("listing", {})
        title = (
            job.get("post_title")
            or listing.get("title")
            or f"Recruitment_{i}"
        )

        filename = (
            f"{i:02d}_"
            f"{_safe_filename(title)}_"
            f"{today.isoformat()}.txt"
        )

        path = output_dir / filename
        path.write_text(_build_job_text(job, i), encoding="utf-8")
        files.append(path)

    return files


def make_report(today, results, out):
    """
    TXT report output:

        reports/
        ├── SarkariResult_LatestJobs_YYYY-MM-DD_Summary.txt
        └── jobs/
            ├── 01_....txt
            ├── 02_....txt
            └── ...
    """
    out = Path(out)

    summary_out = out.with_name(
        out.stem + "_Summary" + ".txt"
    )

    jobs_dir = out.parent / "jobs"

    if results or not summary_out.exists():
        summary_path = make_summary_report(
            today,
            results,
            summary_out,
        )
    elif any(jobs_dir.glob("*.txt")):
        summary_path = _summary_from_job_reports(today, jobs_dir, summary_out)
    else:
        summary_path = summary_out

    job_files = make_job_reports(
        today,
        results,
        jobs_dir,
    )

    return summary_path, job_files
