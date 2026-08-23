
from pathlib import Path
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont


# Instagram portrait: 4:5
W, H = 1080, 1350

NAVY = (13, 48, 96)
BLUE = (24, 78, 145)
MID_BLUE = (55, 103, 165)
PALE_BLUE = (235, 243, 252)
YELLOW = (248, 188, 28)
PALE_YELLOW = (255, 248, 220)
GREEN = (23, 125, 88)
PALE_GREEN = (231, 246, 239)
RED = (190, 50, 50)
PALE_RED = (253, 235, 235)
DARK = (22, 30, 43)
MUTED = (92, 105, 122)
WHITE = (255, 255, 255)
BORDER = (205, 216, 230)
LIGHT = (247, 249, 252)


SOCIAL_GARBAGE = {
    "telegram", "join us", "whatsapp", "instagram",
    "follow", "x", "image", "click here",
}

GENERIC_GARBAGE = {
    "not found",
    "n/a",
    "na",
    "none",
    "null",
    "unknown",
    "organisation not identified",
    "no structured vacancy table detected.",
    "no external application/notification link detected.",
}


def _font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf"
        if bold else "/Library/Fonts/Arial.ttf",
    ]
    for p in candidates:
        path = Path(p)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


F_XL = _font(64, True)
F_TITLE = _font(48, True)
F_H1 = _font(36, True)
F_H2 = _font(28, True)
F_BODY = _font(25, False)
F_BODY_B = _font(25, True)
F_SMALL = _font(19, False)
F_SMALL_B = _font(19, True)
F_TINY = _font(16, False)


def clean_value(value):
    """
    Final presentation filter. Never turns missing data into a
    visible 'Not found' field.
    """
    if value is None:
        return ""

    text = str(value).replace("\r", "\n")
    out = []

    for raw in text.splitlines():
        line = raw.strip()
        line = re.sub(r"^[·•*\-]+\s*", "", line)
        line = re.sub(r"\s+", " ", line).strip()

        if not line:
            continue

        low = line.lower()

        if low in SOCIAL_GARBAGE or low in GENERIC_GARBAGE:
            continue

        # Social/navigation contamination.
        if any(x in low for x in ("telegram", "whatsapp", "instagram")) and len(line) < 120:
            continue
        if low.startswith("join us") and len(line) < 120:
            continue
        if low.startswith("follow") and len(line) < 120:
            continue

        # Source boilerplate that is not useful on an Instagram slide.
        boilerplate = (
            "sarkari result official",
            "always visit sarkariresult",
            "candidate read the notification before",
            "kindly ready scan document",
            "kindly check and collect",
            "before submit the application form",
            "take a print out of final submitted form",
        )
        if any(x in low for x in boilerplate):
            continue

        out.append(line)

    return "\n".join(out).strip()


def first_value(*values):
    for value in values:
        cleaned = clean_value(value)
        if cleaned:
            return cleaned
    return ""


def is_url(value):
    value = clean_value(value)
    return bool(re.match(r"^https?://", value, re.I))


def safe_filename(text):
    text = clean_value(text) or "Recruitment"
    text = re.sub(r"[^\w\s.-]", "", text)
    text = re.sub(r"\s+", "_", text).strip("_")
    return text[:75] or "Recruitment"


def wrap_lines(draw, text, font, max_width, max_lines=None):
    text = clean_value(text)
    if not text:
        return []

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

    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .") + "…"

    return lines


def draw_text(draw, text, x, y, font, fill=DARK, width=900,
              line_gap=8, max_lines=None):
    lines = wrap_lines(draw, text, font, width, max_lines)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def rounded_card(draw, x, y, w, h, fill=WHITE, outline=BORDER, radius=24, width=2):
    draw.rounded_rectangle(
        (x, y, x + w, y + h),
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def pill(draw, text, x, y, fill=YELLOW, text_fill=NAVY, pad_x=22, pad_y=11):
    bbox = draw.textbbox((0, 0), text, font=F_SMALL_B)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.rounded_rectangle(
        (x, y, x + tw + 2 * pad_x, y + th + 2 * pad_y),
        radius=18,
        fill=fill,
    )
    draw.text(
        (x + pad_x, y + pad_y - 1),
        text,
        font=F_SMALL_B,
        fill=text_fill,
    )
    return x + tw + 2 * pad_x


def topbar(draw, organisation, slide, total):
    draw.rectangle((0, 0, W, 110), fill=NAVY)

    org = clean_value(organisation)
    if org:
        draw_text(
            draw, org, 55, 25, F_H2, WHITE,
            width=790, line_gap=3, max_lines=1
        )

    draw.text(
        (W - 125, 32),
        f"{slide}/{total}",
        font=F_SMALL_B,
        fill=WHITE,
    )

    draw.text(
        (55, 79),
        "GOVERNMENT RECRUITMENT • 2026",
        font=F_TINY,
        fill=(215, 228, 244),
    )


def footer(draw):
    draw.rectangle((0, H - 62, W, H), fill=NAVY)
    draw.text(
        (55, H - 43),
        "Verify eligibility, dates and conditions in the official notification.",
        font=F_TINY,
        fill=WHITE,
    )


def add_field_card(draw, x, y, w, h, label, value, fill=WHITE, accent=BLUE):
    rounded_card(draw, x, y, w, h, fill=fill)
    draw.text(
        (x + 24, y + 18),
        label.upper(),
        font=F_SMALL_B,
        fill=accent,
    )
    draw_text(
        draw,
        value,
        x + 24,
        y + 52,
        F_BODY_B,
        DARK,
        width=w - 48,
        line_gap=6,
        max_lines=4,
    )


def get_basic(job):
    listing = job.get("listing", {}) or {}

    title = first_value(
        job.get("post_title"),
        listing.get("title"),
    )

    organisation = first_value(
        job.get("organisation"),
        job.get("recruiting_organisation"),
    )

    deadline = first_value(
        job.get("application_end"),
        listing.get("last_date"),
    )

    vacancies = first_value(
        job.get("total_vacancies"),
    )

    start = first_value(
        job.get("application_start"),
    )

    published = first_value(
        job.get("post_update"),
        job.get("published_date"),
    )

    advt = first_value(
        job.get("advertisement_number"),
        job.get("advertisement_no"),
    )

    age = first_value(
        job.get("age_limit"),
    )

    pay = first_value(
        job.get("pay_scale"),
        job.get("salary"),
    )

    fee = first_value(
        job.get("application_fee"),
    )

    eligibility = first_value(
        job.get("eligibility"),
    )

    selection = first_value(
        job.get("selection_process"),
    )

    dates = first_value(
        job.get("important_dates_raw"),
    )

    how_to_apply = first_value(
        job.get("how_to_apply"),
    )

    return {
        "title": title,
        "organisation": organisation,
        "deadline": deadline,
        "vacancies": vacancies,
        "start": start,
        "published": published,
        "advt": advt,
        "age": age,
        "pay": pay,
        "fee": fee,
        "eligibility": eligibility,
        "selection": selection,
        "dates": dates,
        "how_to_apply": how_to_apply,
    }


def vacancy_rows(job):
    rows = []
    for row in job.get("vacancy_rows", []) or []:
        post = clean_value(row.get("post_name"))
        number = clean_value(row.get("vacancies"))
        if post and number:
            rows.append((post, number))
    return rows


def useful_links(job):
    links = []

    for link in job.get("application_links", []) or []:
        url = clean_value(link.get("url"))
        if is_url(url):
            links.append(("APPLY ONLINE", url))

    for link in job.get("notification_links", []) or []:
        url = clean_value(link.get("url"))
        if is_url(url):
            links.append(("OFFICIAL NOTIFICATION", url))

    # Do not expose generic official_candidates as a separate
    # card unless it is genuinely a usable URL.
    seen = set()
    result = []
    for label, url in links:
        if url not in seen:
            seen.add(url)
            result.append((label, url))

    source = clean_value(job.get("detail_url"))
    if is_url(source) and source not in seen:
        result.append(("SOURCE PAGE", source))

    return result


def make_cover(job, path, slide, total):
    d = ImageDraw.Draw(Image.new("RGB", (W, H), LIGHT))
    img = Image.new("RGB", (W, H), LIGHT)
    d = ImageDraw.Draw(img)

    b = get_basic(job)
    topbar(d, b["organisation"], slide, total)

    y = 155

    if b["deadline"]:
        pill(d, f"LAST DATE: {b['deadline']}", 55, y, PALE_RED, RED)
        y += 82

    y = draw_text(
        d,
        b["title"] or "Government Recruitment",
        55, y, F_XL if len(b["title"]) < 60 else F_TITLE,
        NAVY, width=970, line_gap=10, max_lines=4
    )

    y += 28

    if b["organisation"]:
        y = draw_text(
            d,
            b["organisation"],
            58, y, F_H2, MUTED, width=930,
            line_gap=5, max_lines=2
        )
        y += 20

    # Only show facts that actually exist.
    facts = []
    if b["vacancies"]:
        facts.append(("TOTAL VACANCIES", b["vacancies"]))
    if b["start"]:
        facts.append(("APPLICATION START", b["start"]))
    if b["advt"]:
        facts.append(("ADVERTISEMENT NO.", b["advt"]))

    if facts:
        cols = min(3, len(facts))
        gap = 18
        cw = (970 - gap * (cols - 1)) / cols

        for i, (label, value) in enumerate(facts):
            x = 55 + i * (cw + gap)
            add_field_card(
                d, x, y, cw, 145,
                label, value,
                fill=WHITE,
                accent=BLUE,
            )

        y += 175

    # Optional short description only if real extracted data exists.
    desc = first_value(job.get("short_information"))
    if desc:
        rounded_card(d, 55, y, 970, 250, fill=PALE_BLUE, outline=(190, 211, 234))
        draw_text(
            d, desc, 85, y + 30, F_BODY,
            DARK, width=910, line_gap=9, max_lines=8
        )

    footer(d)
    img.save(path, quality=95)


def make_info_slide(job, path, slide, total):
    img = Image.new("RGB", (W, H), LIGHT)
    d = ImageDraw.Draw(img)

    b = get_basic(job)
    topbar(d, b["organisation"], slide, total)

    d.text((55, 145), "KEY INFORMATION", font=F_TITLE, fill=NAVY)

    fields = []
    for label, value in [
        ("Published / Updated", b["published"]),
        ("Application Start", b["start"]),
        ("Application End", b["deadline"]),
        ("Age Limit", b["age"]),
        ("Pay / Salary", b["pay"]),
        ("Application Fee", b["fee"]),
    ]:
        if value:
            fields.append((label, value))

    y = 220
    for i in range(0, len(fields), 2):
        pair = fields[i:i + 2]
        cw = 465

        for j, (label, value) in enumerate(pair):
            add_field_card(
                d,
                55 + j * 495,
                y,
                cw,
                180,
                label,
                value,
                fill=WHITE,
                accent=BLUE,
            )

        y += 205

    footer(d)
    img.save(path, quality=95)


def make_vacancy_slide(job, path, slide, total):
    img = Image.new("RGB", (W, H), LIGHT)
    d = ImageDraw.Draw(img)

    b = get_basic(job)
    topbar(d, b["organisation"], slide, total)

    rows = vacancy_rows(job)

    d.text((55, 145), "VACANCIES", font=F_TITLE, fill=NAVY)

    if b["vacancies"]:
        pill(
            d,
            f"TOTAL: {b['vacancies']}",
            55,
            210,
            PALE_YELLOW,
            NAVY,
        )

    y = 300

    for index, (post, number) in enumerate(rows, 1):
        h = 92

        rounded_card(
            d, 55, y, 970, h,
            fill=WHITE,
            outline=BORDER,
            radius=15,
        )

        d.text(
            (80, y + 29),
            str(index),
            font=F_SMALL_B,
            fill=BLUE,
        )

        draw_text(
            d,
            post,
            130,
            y + 20,
            F_BODY_B,
            DARK,
            width=700,
            line_gap=4,
            max_lines=2,
        )

        d.text(
            (890, y + 27),
            number,
            font=F_H2,
            fill=RED,
        )

        y += 105

        if y > H - 130:
            break

    footer(d)
    img.save(path, quality=95)


def make_eligibility_slide(job, path, slide, total):
    img = Image.new("RGB", (W, H), LIGHT)
    d = ImageDraw.Draw(img)

    b = get_basic(job)
    topbar(d, b["organisation"], slide, total)

    d.text((55, 145), "ELIGIBILITY", font=F_TITLE, fill=NAVY)

    eligibility = b["eligibility"]

    if eligibility:
        rounded_card(
            d, 55, 215, 970, 780,
            fill=WHITE,
            outline=BORDER,
        )

        draw_text(
            d,
            eligibility,
            85,
            250,
            F_BODY,
            DARK,
            width=910,
            line_gap=10,
            max_lines=28,
        )

    # Show selection only when it exists.
    if b["selection"]:
        rounded_card(
            d, 55, 1025, 970, 210,
            fill=PALE_BLUE,
            outline=(190, 211, 234),
        )

        d.text(
            (85, 1055),
            "SELECTION PROCESS",
            font=F_H2,
            fill=BLUE,
        )

        draw_text(
            d,
            b["selection"],
            85,
            1105,
            F_BODY,
            DARK,
            width=900,
            line_gap=8,
            max_lines=5,
        )

    footer(d)
    img.save(path, quality=95)


def make_links_slide(job, path, slide, total):
    img = Image.new("RGB", (W, H), LIGHT)
    d = ImageDraw.Draw(img)

    b = get_basic(job)
    topbar(d, b["organisation"], slide, total)

    d.text((55, 150), "OFFICIAL LINKS", font=F_TITLE, fill=NAVY)

    links = useful_links(job)

    y = 240

    if links:
        for label, url in links:
            rounded_card(
                d, 55, y, 970, 205,
                fill=WHITE,
                outline=BORDER,
            )

            d.text(
                (85, y + 28),
                label,
                font=F_H2,
                fill=BLUE,
            )

            draw_text(
                d,
                url,
                85,
                y + 85,
                F_SMALL,
                DARK,
                width=900,
                line_gap=8,
                max_lines=5,
            )

            y += 230

            if y > 1080:
                break

    footer(d)
    img.save(path, quality=95)


def build_slide_plan(job):
    """
    Dynamic slide selection.

    No slide is created merely because a schema field exists.
    A slide/section is created only when useful source-derived
    content is actually available.
    """
    b = get_basic(job)
    rows = vacancy_rows(job)
    links = useful_links(job)

    plan = ["cover"]

    info_available = any([
        b["published"], b["start"], b["deadline"],
        b["age"], b["pay"], b["fee"],
    ])
    if info_available:
        plan.append("info")

    if rows:
        plan.append("vacancy")

    if b["eligibility"] or b["selection"]:
        plan.append("eligibility")

    if links:
        plan.append("links")

    # Avoid pointless 5-slide output for sparse jobs.
    return plan


def generate_job_carousel(job, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    title = (
        job.get("post_title")
        or job.get("listing", {}).get("title")
        or "Recruitment"
    )
    safe = safe_filename(title)

    plan = build_slide_plan(job)
    total = len(plan)

    makers = {
        "cover": make_cover,
        "info": make_info_slide,
        "vacancy": make_vacancy_slide,
        "eligibility": make_eligibility_slide,
        "links": make_links_slide,
    }

    slides = []

    for number, kind in enumerate(plan, 1):
        path = output_dir / f"{number:02d}_{safe}.png"
        makers[kind](job, path, number, total)
        slides.append(path)

    return slides


def generate_instagram_assets(results, output_root):
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    all_assets = []

    for index, job in enumerate(results, 1):
        title = (
            job.get("post_title")
            or job.get("listing", {}).get("title")
            or f"Recruitment_{index}"
        )

        job_dir = output_root / f"{index:02d}_{safe_filename(title)}"

        slides = generate_job_carousel(job, job_dir)

        all_assets.append({
            "job": title,
            "directory": job_dir,
            "slides": slides,
        })

    return all_assets
