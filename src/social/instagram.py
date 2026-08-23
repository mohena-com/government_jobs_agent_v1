
from pathlib import Path
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont


W, H = 1080, 1350

BG = (248, 250, 252)
DARK = (20, 30, 45)
MUTED = (85, 96, 110)
BLUE = (25, 87, 166)
LIGHT_BLUE = (225, 238, 250)
GREEN = (22, 130, 90)
LIGHT_GREEN = (224, 245, 237)
RED = (190, 55, 55)
LIGHT_RED = (252, 231, 231)
WHITE = (255, 255, 255)
BORDER = (210, 218, 228)


def _font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf"
        if bold else "/Library/Fonts/Arial.ttf",
    ]

    for path in candidates:
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size)

    return ImageFont.load_default()


FONT_XL = _font(64, True)
FONT_L = _font(46, True)
FONT_M = _font(32, True)
FONT_BODY = _font(28, False)
FONT_BODY_BOLD = _font(28, True)
FONT_SMALL = _font(22, False)
FONT_SMALL_BOLD = _font(22, True)


def clean_text(value):
    if value is None:
        return ""

    blocked = {
        "telegram", "join us", "whatsapp", "instagram",
        "follow", "x", "image",
    }

    lines = []

    for raw in str(value).splitlines():
        line = raw.strip()
        line = re.sub(r"^[·•*\-]+\s*", "", line)
        if not line:
            continue

        low = line.lower()

        if low in blocked:
            continue

        if any(x in low for x in ("telegram", "whatsapp", "instagram")) and len(line) < 100:
            continue

        if (low.startswith("join us") or low.startswith("follow")) and len(line) < 100:
            continue

        lines.append(line)

    return "\n".join(lines).strip()


def title_font_for(text):
    n = len(text or "")
    if n <= 45:
        return FONT_XL
    if n <= 75:
        return FONT_L
    return FONT_M


def draw_wrapped(draw, text, xy, font, fill=DARK, max_width=900,
                 line_gap=12, max_lines=None):
    text = clean_text(text)
    if not text:
        return xy[1]

    words = text.split()
    lines = []
    current = ""

    for word in words:
        trial = f"{current} {word}".strip()

        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    if max_lines:
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            if lines:
                lines[-1] = lines[-1].rstrip(". ") + "..."

    y = xy[1]

    for line in lines:
        draw.text((xy[0], y), line, font=font, fill=fill)
        bbox = draw.textbbox((xy[0], y), line, font=font)
        y = bbox[3] + line_gap

    return y


def card(draw, x, y, w, h, fill=WHITE, outline=BORDER, radius=24):
    draw.rounded_rectangle(
        (x, y, x + w, y + h),
        radius=radius,
        fill=fill,
        outline=outline,
        width=2,
    )


def label_value(draw, x, y, label, value, width=900):
    draw.text(
        (x, y),
        clean_text(label),
        font=FONT_SMALL_BOLD,
        fill=MUTED,
    )

    y += 32

    y = draw_wrapped(
        draw,
        value or "Not found",
        (x, y),
        FONT_BODY_BOLD,
        DARK,
        max_width=width,
        line_gap=8,
        max_lines=3,
    )

    return y + 18


def header(draw, slide_no, total, organisation):
    draw.text(
        (60, 45),
        "GOVERNMENT JOB ALERT",
        font=FONT_SMALL_BOLD,
        fill=BLUE,
    )

    draw.text(
        (60, 85),
        clean_text(organisation) or "Government Recruitment",
        font=FONT_SMALL,
        fill=MUTED,
    )

    draw.text(
        (W - 150, 50),
        f"{slide_no}/{total}",
        font=FONT_SMALL_BOLD,
        fill=MUTED,
    )


def footer(draw):
    draw.text(
        (60, H - 70),
        "Source: SarkariResult • Verify details in official notification",
        font=FONT_SMALL,
        fill=MUTED,
    )


def make_slide_1(job, out, slide_no, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    organisation = job.get("organisation") or "Government Recruitment"
    listing = job.get("listing", {})
    title = job.get("post_title") or listing.get("title") or "Recruitment Notice"
    deadline = job.get("application_end") or listing.get("last_date") or "Not found"

    header(d, slide_no, total, organisation)

    y = 190

    d.rounded_rectangle(
        (60, y, W - 60, y + 180),
        radius=28,
        fill=BLUE,
    )

    draw_wrapped(
        d,
        "NEW GOVERNMENT JOB",
        (95, y + 35),
        FONT_M,
        WHITE,
        max_width=880,
    )

    y = 420

    y = draw_wrapped(
        d,
        title,
        (60, y),
        title_font_for(title),
        DARK,
        max_width=960,
        line_gap=14,
        max_lines=4,
    )

    y += 35

    card(
        d,
        60,
        y,
        960,
        190,
        fill=LIGHT_RED,
        outline=(238, 190, 190),
    )

    d.text(
        (95, y + 30),
        "APPLICATION DEADLINE",
        font=FONT_SMALL_BOLD,
        fill=RED,
    )

    draw_wrapped(
        d,
        str(deadline),
        (95, y + 78),
        FONT_L,
        RED,
        max_width=850,
        line_gap=8,
    )

    total_vacancies = job.get("total_vacancies")
    if total_vacancies:
        d.text(
            (95, y + 140),
            f"Vacancies: {total_vacancies}",
            font=FONT_BODY_BOLD,
            fill=DARK,
        )

    footer(d)
    img.save(out, quality=95)


def make_slide_2(job, out, slide_no, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    organisation = job.get("organisation") or "Government Recruitment"
    header(d, slide_no, total, organisation)

    d.text(
        (60, 170),
        "KEY INFORMATION",
        font=FONT_L,
        fill=DARK,
    )

    rows = [
        ("Advertisement / Reference No.", job.get("advertisement_number")),
        ("Published / Updated", job.get("post_update")),
        ("Total Vacancies", job.get("total_vacancies")),
        ("Application Start", job.get("application_start")),
        ("Application End", job.get("application_end")),
        ("Age Limit", job.get("age_limit")),
    ]

    y = 250

    for label, value in rows:
        card(d, 60, y, 960, 125)
        label_value(d, 90, y + 20, label, value, width=870)
        y += 145

        if y > 1170:
            break

    footer(d)
    img.save(out, quality=95)


def make_slide_3(job, out, slide_no, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    organisation = job.get("organisation") or "Government Recruitment"
    header(d, slide_no, total, organisation)

    d.text(
        (60, 170),
        "VACANCY DETAILS",
        font=FONT_L,
        fill=DARK,
    )

    rows = job.get("vacancy_rows", [])

    if not rows:
        draw_wrapped(
            d,
            "Detailed vacancy table was not available in the extracted data.",
            (60, 250),
            FONT_BODY,
            MUTED,
            max_width=900,
        )
    else:
        y = 250

        # Header
        card(d, 60, y, 960, 70, fill=LIGHT_BLUE, outline=LIGHT_BLUE, radius=12)
        d.text((90, y + 20), "POST", font=FONT_SMALL_BOLD, fill=DARK)
        d.text((820, y + 20), "VACANCIES", font=FONT_SMALL_BOLD, fill=DARK)
        y += 85

        for row in rows:
            post = row.get("post_name", "")
            vacancies = row.get("vacancies", "")

            card(d, 60, y, 960, 78, fill=WHITE, radius=12)

            draw_wrapped(
                d,
                post,
                (90, y + 15),
                FONT_SMALL,
                DARK,
                max_width=690,
                line_gap=5,
                max_lines=2,
            )

            d.text(
                (850, y + 22),
                clean_text(vacancies),
                font=FONT_BODY_BOLD,
                fill=BLUE,
            )

            y += 90

            if y > 1170:
                break

    footer(d)
    img.save(out, quality=95)


def make_slide_4(job, out, slide_no, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    organisation = job.get("organisation") or "Government Recruitment"
    header(d, slide_no, total, organisation)

    d.text(
        (60, 160),
        "ELIGIBILITY & FEES",
        font=FONT_L,
        fill=DARK,
    )

    # Fee
    card(d, 60, 235, 960, 250, fill=LIGHT_GREEN, outline=(190, 225, 210))

    d.text(
        (90, 265),
        "APPLICATION FEE",
        font=FONT_M,
        fill=GREEN,
    )

    fee = clean_text(job.get("application_fee")) or "Not found"

    draw_wrapped(
        d,
        fee,
        (90, 325),
        FONT_BODY,
        DARK,
        max_width=880,
        line_gap=8,
        max_lines=5,
    )

    # Eligibility
    card(d, 60, 525, 960, 570)

    d.text(
        (90, 555),
        "ELIGIBILITY",
        font=FONT_M,
        fill=BLUE,
    )

    eligibility = clean_text(job.get("eligibility")) or "Not found"

    draw_wrapped(
        d,
        eligibility,
        (90, 615),
        FONT_BODY,
        DARK,
        max_width=880,
        line_gap=10,
        max_lines=16,
    )

    footer(d)
    img.save(out, quality=95)


def make_slide_5(job, out, slide_no, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    organisation = job.get("organisation") or "Government Recruitment"
    header(d, slide_no, total, organisation)

    d.text(
        (60, 165),
        "IMPORTANT LINKS",
        font=FONT_L,
        fill=DARK,
    )

    links = []

    for link in job.get("application_links", []):
        url = link.get("url")
        if url:
            links.append(("APPLY ONLINE", url))

    for link in job.get("notification_links", []):
        url = link.get("url")
        if url:
            links.append(("OFFICIAL NOTIFICATION", url))

    if not links:
        links.append(("APPLICATION / NOTIFICATION", "Not found"))

    y = 250

    for label, url in links[:3]:
        card(d, 60, y, 960, 230)

        d.text(
            (90, y + 30),
            label,
            font=FONT_M,
            fill=BLUE,
        )

        draw_wrapped(
            d,
            url,
            (90, y + 95),
            FONT_SMALL,
            DARK,
            max_width=870,
            line_gap=8,
            max_lines=5,
        )

        y += 265

    # Source
    card(d, 60, min(y, 930), 960, 180, fill=LIGHT_BLUE, outline=LIGHT_BLUE)

    d.text(
        (90, min(y, 930) + 30),
        "SOURCE",
        font=FONT_M,
        fill=BLUE,
    )

    draw_wrapped(
        d,
        job.get("detail_url") or "Not found",
        (90, min(y, 930) + 90),
        FONT_SMALL,
        DARK,
        max_width=870,
        line_gap=8,
        max_lines=3,
    )

    footer(d)
    img.save(out, quality=95)


def generate_job_carousel(job, output_dir):
    """
    Generate a 5-slide Instagram carousel for one recruitment.
    Canvas: 1080 x 1350 (4:5 Instagram portrait).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    title = (
        job.get("post_title")
        or job.get("listing", {}).get("title")
        or "Recruitment"
    )

    safe = re.sub(r"[^\w\s.-]", "", title)
    safe = re.sub(r"\s+", "_", safe).strip("_")[:80]

    slides = []

    for i, maker in enumerate(
        [
            make_slide_1,
            make_slide_2,
            make_slide_3,
            make_slide_4,
            make_slide_5,
        ],
        1,
    ):
        path = output_dir / f"{i:02d}_{safe}.png"
        maker(job, path, i, 5)
        slides.append(path)

    return slides


def generate_instagram_assets(results, output_root):
    """
    Generate one Instagram carousel folder per job.

    Output:
        social/instagram/
          01_<job>/
            01_*.png
            ...
            05_*.png
          02_<job>/
            ...
    """
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    all_assets = []

    for index, job in enumerate(results, 1):
        title = (
            job.get("post_title")
            or job.get("listing", {}).get("title")
            or f"Recruitment_{index}"
        )

        safe = re.sub(r"[^\w\s.-]", "", title)
        safe = re.sub(r"\s+", "_", safe).strip("_")[:70]

        job_dir = output_root / f"{index:02d}_{safe}"

        slides = generate_job_carousel(
            job,
            job_dir,
        )

        all_assets.append(
            {
                "job": title,
                "directory": job_dir,
                "slides": slides,
            }
        )

    return all_assets
