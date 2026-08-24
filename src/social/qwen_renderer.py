from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

try:
    import qrcode
except ImportError:  # pragma: no cover
    qrcode = None

# Instagram portrait / 4:5
W, H = 1080, 1350

# V1.9.18 visual system — inspired by professional recruitment posters,
# but generated from structured facts rather than copied artwork.
NAVY = (13, 48, 96)
BLUE = (24, 78, 145)
BLUE_2 = (42, 103, 173)
YELLOW = (248, 188, 28)
GOLD = (238, 161, 19)
RED = (190, 50, 50)
GREEN = (27, 123, 86)
DARK = (22, 30, 43)
MUTED = (92, 105, 122)
WHITE = (255, 255, 255)
BG = (246, 249, 253)
PALE_BLUE = (233, 242, 252)
PALE_YELLOW = (255, 248, 220)
PALE_GREEN = (232, 246, 239)
PALE_RED = (253, 237, 237)
BORDER = (201, 215, 232)
LIGHT_LINE = (226, 233, 242)


def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        p = Path(candidate)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


F_HERO = _font(72, True)
F_HERO_2 = _font(54, True)
F_TITLE = _font(47, True)
F_H1 = _font(35, True)
F_H2 = _font(28, True)
F_BODY_B = _font(25, True)
F_BODY = _font(23, False)
F_SMALL_B = _font(19, True)
F_SMALL = _font(18, False)
F_TINY_B = _font(15, True)
F_TINY = _font(14, False)


INTERNAL_PATTERNS = [
    r"\bstatus\s*:\s*(?:pass|fail)\b",
    r"\bquality\s*gate\s*:\s*(?:pass|fail)\b",
    r"\bslide\s*quality\s*gate\s*:\s*(?:pass|fail)\b",
    r"\bv(?:alidation|erification)\s*(?:status|result)\s*:\s*(?:pass|fail)\b",
    r"\bvacancy\s+reconciliation\b",
    r"\bextraction\s+repairs?\b",
    r"\bparsed\s+vacancies?\s*:\s*\d+\b",
    r"\bauthoritative\s+vacancies?\s*:\s*\d+\b",
    r"\b(?:locked|verified)\s+facts?\b",
    r"\bsource\s+(?:method|text|document)\b",
    r"\bpdf\s+extraction\b",
    r"\bqwen(?:3)?\b",
    r"\bfacts?_used\b",
]


def _clean(text: Any) -> str:
    if text is None:
        return ""
    s = str(text).replace("\r", "\n")
    # Never expose raw URLs or markdown links in artwork.
    s = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", s)
    s = re.sub(r"https?://\S+", "", s, flags=re.I)
    for p in INTERNAL_PATTERNS:
        s = re.sub(p, "", s, flags=re.I)
    lines = []
    for raw in s.splitlines():
        line = re.sub(r"^[•·●*\-]+\s*", "", raw.strip())
        line = re.sub(r"\s+", " ", line).strip(" -:;,")
        if not line:
            continue
        low = line.lower()
        if low in {"not found", "n/a", "na", "none", "null", "unknown", "organisation not identified"}:
            continue
        if any(x in low for x in ("telegram", "whatsapp", "instagram", "join us", "follow us")) and len(line) < 120:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _first(*values: Any) -> str:
    for value in values:
        text = _clean(value)
        if text:
            return text
    return ""


def _wrap(draw, text: str, font, width: int, max_lines: int | None = None):
    text = _clean(text)
    if not text:
        return []
    # Make slash-separated category labels breakable without changing the
    # displayed text semantics (e.g. EWS/BC/MBC/SC/ST/PwBD).
    text = re.sub(r"/(?=\S)", "/ ", text)
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= width:
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


def _text(draw, text, x, y, font, fill=DARK, width=900, gap=7, max_lines=None):
    for line in _wrap(draw, text, font, width, max_lines):
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + gap
    return y


def _card(draw, x, y, w, h, fill=WHITE, outline=BORDER, radius=22, width=2):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill, outline=outline, width=width)


def _pill(draw, text, x, y, fill=YELLOW, color=NAVY, pad_x=18, pad_y=9):
    text = _clean(text)
    box = draw.textbbox((0, 0), text, font=F_SMALL_B)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.rounded_rectangle((x, y, x + tw + pad_x * 2, y + th + pad_y * 2), radius=18, fill=fill)
    draw.text((x + pad_x, y + pad_y - 1), text, font=F_SMALL_B, fill=color)
    return x + tw + pad_x * 2


def _initials(org: str) -> str:
    text = _clean(org)
    if not text:
        return "GJ"
    m = re.search(r"\(([A-Z]{2,8})\)", text)
    if m:
        return m.group(1)[:4]
    words = [w for w in re.split(r"\s+", text) if w and w.lower() not in {"ltd", "limited", "of", "the", "and"}]
    if len(words) >= 2:
        return "".join(w[0] for w in words[:4]).upper()
    return text[:4].upper()


def _short_org(org: str) -> str:
    text = _clean(org)
    m = re.search(r"\(([A-Z]{2,8})\)", text)
    if m:
        return m.group(1)
    return text[:34]


def _section_bar(draw, title: str, x: int, y: int, w: int = 970, accent: tuple[int,int,int] = BLUE, sub: str = ""):
    """Professional blue section bar with a yellow sub-bar highlight."""
    draw.rounded_rectangle((x, y, x + w, y + 58), radius=14, fill=accent)
    draw.rectangle((x, y + 51, x + min(210, w), y + 58), fill=YELLOW)
    draw.text((x + 18, y + 14), _clean(title).upper(), font=F_SMALL_B, fill=WHITE)
    if sub:
        draw.text((x + w - 18, y + 15), _clean(sub), font=F_TINY_B, fill=WHITE, anchor="ra")
    return y + 72


def _header(img, draw, org: str, number: int, total: int, kicker="GOVERNMENT RECRUITMENT"):
    # Strong poster-like masthead.
    draw.rectangle((0, 0, W, 116), fill=NAVY)
    draw.ellipse((34, 18, 96, 80), fill=WHITE)
    initials = _initials(org)
    box = draw.textbbox((0, 0), initials, font=F_TINY_B)
    draw.text((65 - (box[2] - box[0]) / 2, 39), initials, font=F_TINY_B, fill=NAVY)
    _text(draw, _short_org(org) or "Government Jobs", 115, 23, F_H2, WHITE, 720, 3, 1)
    draw.text((115, 76), kicker, font=F_TINY_B, fill=(218, 231, 246))
    draw.text((W - 115, 34), f"{number}/{total}", font=F_SMALL_B, fill=WHITE)
    # layered brand bars: blue base + yellow accent
    draw.rectangle((0, 112, W, 122), fill=BLUE)
    draw.rectangle((0, 122, int(W * 0.34), 128), fill=YELLOW)


def _footer(draw, text="READ THE OFFICIAL NOTIFICATION BEFORE APPLYING"):
    draw.rectangle((0, H - 68, W, H), fill=NAVY)
    draw.rectangle((0, H - 68, int(W * 0.32), H - 62), fill=YELLOW)
    draw.text((50, H - 46), text, font=F_TINY_B, fill=WHITE)
    draw.text((W - 130, H - 46), "• GOVT JOB", font=F_TINY_B, fill=YELLOW)


def _fact_rows(facts: dict, key: str) -> list[dict]:
    rows = facts.get(key) or []
    return [x for x in rows if isinstance(x, dict)]


def _vacancies(facts: dict) -> list[tuple[str, str]]:
    rows = []
    for row in facts.get("post_vacancies") or facts.get("raw_post_vacancies") or []:
        post = _clean(row.get("post") or row.get("post_name"))
        number = _clean(row.get("vacancies") or row.get("total"))
        if post and number:
            rows.append((post, number))
    return rows


def _eligibility_rows(facts: dict) -> list[dict]:
    rows = facts.get("post_facts") or facts.get("post_eligibility") or []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        post = _clean(row.get("post"))
        qual = _clean(row.get("qualification") or row.get("eligibility"))
        exp = _clean(row.get("experience"))
        if post and (qual or exp):
            out.append({"post": post, "qualification": qual, "experience": exp})
    return out


def _slide_bullets(slide: dict) -> list[str]:
    return [_clean(x) for x in (slide.get("bullets") or []) if _clean(x)]


def _compact_qualification(text: str, max_chars: int = 190) -> str:
    """Presentation-only condensation; never changes locked facts."""
    s = _clean(text)
    if not s:
        return "Qualification as per official notification."
    replacements = [
        (r"full\s*time\s+four\s+years[’']?\s+graduation\s+degree\s+in", "4-year full-time degree in"),
        (r"full\s*time\s+four\s+years[’']?\s+graduation\s+degree", "4-year full-time degree"),
        (r"as\s+a\s+regular\s+student\s+or\s+AMIE\s+in", "or AMIE in"),
        (r"as\s+a\s+regular\s+student\s+or\s+AMIE", "or AMIE"),
        (r"from\s+a\s+University\s*/?\s*Institution.*?(?:recognized|equivalent)", "from a recognized institution"),
        (r"established\s+by\s+Law\s+in\s+India\s+and\s+recognized", "recognized"),
        (r"the\s+date\s+of\s+declaration\s+of\s+result.*", "qualification must be valid by document verification"),
        (r"including\s+computer\s+qualification\s*\(if\s+prescribed\)\s*", "Computer qualification where prescribed. "),
        (r"at\s+the\s+time\s+fixed\s+for\s+documents\s+verification.*", ""),
    ]
    for pat, repl in replacements:
        s = re.sub(pat, repl, s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" .;:")
    if len(s) > max_chars:
        # Prefer a complete sentence/phrase boundary over arbitrary truncation.
        cut = s[:max_chars]
        boundary = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(", "))
        if boundary >= int(max_chars * 0.60):
            cut = cut[:boundary]
        s = cut.rstrip(" .;,") + "…"
    return s


def _compact_age(text: str) -> str:
    s = _clean(text)
    if not s:
        return "See official notification."
    ranges = re.findall(r"\b(?:18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|40|41|42|43|44|45|46|47|48|49|50|51|52|53|54|55|56|57|58|59|60)\s*(?:-|–|—|to)\s*(?:18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|40|41|42|43|44|45|46|47|48|49|50|51|52|53|54|55|56|57|58|59|60)\s*years?", s, flags=re.I)
    maxes = re.findall(r"(?:maximum|max\.?\s*age)\s*[:\-]?\s*(\d{2})\s*years?", s, flags=re.I)
    mins = re.findall(r"(?:minimum|min\.?\s*age)\s*[:\-]?\s*(\d{2})\s*years?", s, flags=re.I)
    if ranges:
        return ranges[0]
    if mins and maxes:
        return f"{mins[0]}–{maxes[0]} years"
    if maxes:
        return f"Max {maxes[0]} years"
    m = re.search(r"\b\d{2}\s*years?\b", s, re.I)
    return m.group(0) if m else "See official notification."


def _compact_pay(text: str) -> str:
    s = _clean(text)
    if not s:
        return "See official notification."
    parts = []
    for value in re.findall(r"(?:Pay\s*Level|Level)[-:\s]*([0-9]+)", s, re.I):
        label = f"Level-{value}"
        if label not in parts:
            parts.append(label)
    for pat in [r"Basic(?: Pay)?\s*[:\-]?\s*(?:₹\s*)?[\d,]+(?:\s*[–-]\s*(?:₹\s*)?[\d,]+)?", r"₹\s*[\d,]+(?:\s*[–-]\s*₹\s*[\d,]+)?(?:\s*(?:per month|/month))?"]:
        for m in re.finditer(pat, s, re.I):
            value = m.group(0).strip()
            if value not in parts:
                parts.append(value)
    if parts:
        return " • ".join(parts[:3])
    return _compact_qualification(s, 100)


def _compact_fee(text: str) -> str:
    s = _clean(text)
    if not s:
        return "See official notification."
    # Preserve category amounts while dropping source boilerplate.
    hits = re.findall(r"(?:General|GEN|UR|EWS|OBC|BC|MBC|SC|ST|PwBD|PH|Ex[- ]?Servicemen)[^\n;:]*?(?:₹\s*)?[\d,]+\s*/?-?", s, re.I)
    if hits:
        return " • ".join(re.sub(r"\s+", " ", h).strip(" .") for h in hits[:5])
    amounts = re.findall(r"₹\s*[\d,]+", s)
    return " / ".join(amounts[:4]) if amounts else _compact_qualification(s, 90)


def _post_match(a: str, b: str) -> bool:
    na, nb = re.sub(r"[^a-z0-9]+", " ", a.lower()).strip(), re.sub(r"[^a-z0-9]+", " ", b.lower()).strip()
    return na == nb or na in nb or nb in na


def _date_label(value: Any) -> str:
    text = _clean(value)
    if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", text):
        y, m, d = text.split("-")
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        return f"{int(d):02d} {months[int(m)-1]} {y}"
    return text


def _stat_card(draw, x, y, w, h, label, value, accent=BLUE, fill=WHITE, icon=None):
    _card(draw, x, y, w, h, fill, BORDER, 20, 2)
    draw.rectangle((x, y, x + 8, y + h), fill=accent)
    if icon:
        draw.ellipse((x + 22, y + 20, x + 62, y + 60), fill=accent)
        draw.text((x + 33, y + 27), icon, font=F_SMALL_B, fill=WHITE)
        tx = x + 76
    else:
        tx = x + 24
    draw.text((tx, y + 20), label.upper(), font=F_TINY_B, fill=accent)
    _text(draw, value, tx, y + 53, F_BODY_B if len(value) < 38 else F_SMALL_B, DARK, w - (tx - x) - 22, 5, 3)


def _draw_bullets(draw, bullets, x, y, w, bottom_y, accent=BLUE, max_items=6, font=F_BODY, text_fill=DARK):
    items = [b for b in bullets if b][:max_items]
    for item in items:
        if y > bottom_y - 50:
            break
        draw.ellipse((x, y + 8, x + 12, y + 20), fill=accent)
        y = _text(draw, item, x + 28, y, font, text_fill, w - 28, 6, 3) + 10
    return y


def _draw_title(img, draw, slide, facts, number, total):
    org = _clean(facts.get("organisation"))
    _header(img, draw, org, number, total, "GOVERNMENT RECRUITMENT • 2026")
    y = 155
    draw.text((55, y), "RECRUITMENT", font=F_HERO, fill=NAVY)
    # Derive the recruitment year from locked facts instead of hardcoding a cycle.
    year_match = re.search(r"20\d{2}", " ".join([_clean(facts.get("published_date")), _clean(facts.get("application_start")), _clean(facts.get("application_end")), _clean(facts.get("post"))]))
    year_text = year_match.group(0) if year_match else ""
    if year_text:
        draw.text((55, y + 76), year_text, font=F_HERO_2, fill=BLUE)
    y += 150

    title = _clean(facts.get("post") or slide.get("headline") or "Government Recruitment")
    # Prefer a compact post line over a giant source title.
    rows = _vacancies(facts)
    names = [p for p, _ in rows]
    if names:
        compact = " • ".join(names[:3])
        if len(names) > 3:
            compact += f" • +{len(names)-3} more posts"
    else:
        compact = _clean(slide.get("subtitle") or title)

    _pill(draw, "APPLICATION WINDOW", 55, y, PALE_YELLOW, NAVY)
    y += 67
    _text(draw, compact, 55, y, F_H1, DARK, 970, 8, 4)
    y += min(170, max(90, len(_wrap(draw, compact, F_H1, 970, 4)) * 42 + 30))

    total_v = _clean(facts.get("total_vacancies") or facts.get("combined_vacancies"))
    deadline = _date_label(facts.get("application_end"))
    start = _date_label(facts.get("application_start"))

    if total_v:
        _card(draw, 55, y, 470, 190, NAVY, NAVY, 24, 2)
        draw.text((85, y + 28), "TOTAL VACANCIES", font=F_SMALL_B, fill=(214, 228, 245))
        draw.text((82, y + 66), total_v, font=F_HERO, fill=YELLOW)
        draw.text((85, y + 145), "verified recruitment posts", font=F_SMALL, fill=WHITE)

    if deadline:
        _card(draw, 545, y, 480, 190, PALE_RED, (236, 192, 192), 24, 2)
        draw.text((575, y + 28), "APPLICATION DEADLINE", font=F_SMALL_B, fill=RED)
        _text(draw, deadline, 575, y + 69, F_H1, DARK, 420, 6, 2)
        if start:
            draw.text((575, y + 140), f"Opens: {start}", font=F_SMALL_B, fill=MUTED)

    y += 220
    # CTA ribbon
    _card(draw, 55, y, 970, 130, WHITE, BORDER, 22, 2)
    draw.rectangle((55, y, 65, y + 130), fill=YELLOW)
    draw.text((90, y + 23), "JOB SEEKER CHECKLIST", font=F_SMALL_B, fill=BLUE)
    _draw_bullets(draw, [
        "Check the post-wise qualification before applying.",
        "Use only the official notification/application links.",
    ], 90, y + 55, 900, y + 118, BLUE, 2, F_SMALL)
    _footer(draw)


def _draw_vacancies(img, draw, slide, facts, number, total):
    org = _clean(facts.get("organisation"))
    _header(img, draw, org, number, total, "RECRUITMENT • POST-WISE VACANCIES")
    headline = _clean(slide.get("headline") or "VACANCY BREAKDOWN")
    total_value = _clean(facts.get("total_vacancies") or facts.get("combined_vacancies"))
    _section_bar(draw, headline, 55, 145, 970, BLUE, "01")
    if total_value:
        _pill(draw, f"TOTAL VACANCIES: {total_value}", 55, 215, PALE_YELLOW, NAVY)
        y = 285
    else:
        y = 225

    rows = _vacancies(facts)
    if not rows:
        bullets = _slide_bullets(slide)
        _draw_bullets(draw, bullets, 70, y, 930, 1150, BLUE, 6, F_BODY_B)
    else:
        # Poster-like table.
        _card(draw, 45, y, 990, 62, NAVY, NAVY, 14, 1)
        draw.text((70, y + 20), "POST", font=F_SMALL_B, fill=WHITE)
        draw.text((930, y + 20), "VACANCIES", font=F_SMALL_B, fill=WHITE, anchor="ra")
        y += 70
        visible_rows = min(len(rows), 8)
        available_h = 760
        row_h = max(68, min(96, int(available_h / max(visible_rows, 1)) - 8))
        for idx, (post, count) in enumerate(rows[:visible_rows], 1):
            fill = WHITE if idx % 2 else PALE_BLUE
            _card(draw, 45, y, 990, row_h, fill, BORDER, 14, 1)
            draw.ellipse((68, y + (row_h-34)//2, 102, y + (row_h-34)//2 + 34), fill=YELLOW)
            draw.text((85, y + row_h//2 - 1), str(idx), font=F_TINY_B, fill=NAVY, anchor="mm")
            _text(draw, post, 120, y + 12, F_SMALL_B if len(post) < 48 else F_TINY_B, DARK, 730, 4, 2)
            draw.text((970, y + row_h//2 - 1), str(count), font=F_H2, fill=RED, anchor="ra")
            y += row_h + 7
        if len(rows) > visible_rows:
            _pill(draw, f"+{len(rows)-visible_rows} additional post(s) • SEE OFFICIAL NOTIFICATION", 55, 1060, PALE_YELLOW, NAVY)
        elif total_value:
            _card(draw, 45, 1055, 990, 75, NAVY, NAVY, 16, 1)
            draw.text((75, 1078), "TOTAL", font=F_SMALL_B, fill=WHITE)
            draw.text((970, 1072), total_value, font=F_H1, fill=YELLOW, anchor="ra")
    _footer(draw)


def _draw_eligibility(img, draw, slide, facts, number, total):
    org = _clean(facts.get("organisation"))
    _header(img, draw, org, number, total, "WHO CAN APPLY?")
    _section_bar(draw, "WHO CAN APPLY?", 55, 145, 970, BLUE, "03")
    draw.text((58, 210), "Essential qualification by post", font=F_H2, fill=MUTED)

    eligibility = _eligibility_rows(facts)
    vacancies = _vacancies(facts)
    # Drive card count from verified vacancy rows so every verified post gets a
    # visual slot, even when the qualification extraction missed one row.
    ordered = []
    if vacancies:
        for post, _ in vacancies:
            match = next((r for r in eligibility if _post_match(post, r.get("post", ""))), None)
            ordered.append({
                "post": post,
                "qualification": (match or {}).get("qualification", ""),
                "experience": (match or {}).get("experience", ""),
            })
    else:
        ordered = eligibility[:6] or [{"post": "Qualification", "qualification": b, "experience": ""} for b in _slide_bullets(slide)[:6]]

    y = 270
    gap = 18
    card_w = (970 - gap) // 2
    card_h = 190
    for i, row in enumerate(ordered[:6]):
        col = i % 2
        row_y = y + (i // 2) * (card_h + 16)
        x = 55 + col * (card_w + gap)
        _card(draw, x, row_y, card_w, card_h, WHITE, BORDER, 18, 2)
        draw.rectangle((x, row_y, x + card_w, row_y + 9), fill=YELLOW if i % 2 == 0 else BLUE)
        _text(draw, row["post"], x + 20, row_y + 20, F_SMALL_B, NAVY, card_w - 40, 4, 2)
        qual = _compact_qualification(row.get("qualification") or "Qualification details in official notification.", 205)
        _text(draw, qual, x + 20, row_y + 72, F_TINY if len(qual) > 150 else F_SMALL, DARK, card_w - 40, 4, 4)
        if row.get("experience"):
            exp = _compact_qualification("Experience: " + row["experience"], 100)
            _text(draw, exp, x + 20, row_y + 150, F_TINY, MUTED, card_w - 40, 3, 2)

    _pill(draw, "ONLY ESSENTIAL REQUIREMENTS SHOWN • SEE NOTIFICATION FOR FULL CONDITIONS", 55, 1095, PALE_YELLOW, NAVY)
    _footer(draw)

def _draw_age_pay_fee(img, draw, slide, facts, number, total):
    org = _clean(facts.get("organisation"))
    _header(img, draw, org, number, total, "AGE • PAY • APPLICATION FEE")
    _section_bar(draw, "AT A GLANCE", 55, 145, 970, BLUE, "04")

    age = _compact_age(facts.get("age_limit"))
    pay = _compact_pay(facts.get("pay_scale") or facts.get("salary"))
    fee = _compact_fee(facts.get("application_fee"))

    _stat_card(draw, 55, 225, 300, 220, "AGE LIMIT", age, BLUE, PALE_BLUE, "A")
    _stat_card(draw, 390, 225, 300, 220, "PAY / SALARY", pay, GREEN, PALE_GREEN, "₹")
    _stat_card(draw, 725, 225, 300, 220, "APPLICATION FEE", fee, RED, PALE_RED, "₹")

    # Use the remaining space for only a few useful, compact conditions.
    _card(draw, 55, 480, 970, 480, WHITE, BORDER, 24, 2)
    draw.text((85, 515), "KEY CONDITIONS", font=F_H2, fill=NAVY)
    bullets = []
    for item in _slide_bullets(slide):
        low = item.lower()
        if any(k in low for k in ("age", "pay", "salary", "fee", "advertisement", "rectt", "notification")):
            continue
        item = _compact_qualification(item, 150)
        if item and item not in bullets:
            bullets.append(item)
    if not bullets:
        bullets = ["Category-wise age relaxation applies as specified in the official notification."]
    _draw_bullets(draw, bullets[:4], 90, 585, 900, 875, BLUE, 4, F_BODY)
    _pill(draw, "VERIFY CATEGORY-WISE CONDITIONS", 55, 1000, PALE_YELLOW, NAVY)
    _footer(draw)

def _draw_dates_selection(img, draw, slide, facts, number, total):
    org = _clean(facts.get("organisation"))
    _header(img, draw, org, number, total, "DATES • SELECTION PROCESS")
    draw.text((55, 150), "IMPORTANT DATES", font=F_TITLE, fill=NAVY)

    start = _date_label(facts.get("application_start"))
    end = _date_label(facts.get("application_end"))
    y = 235
    # Timeline
    draw.line((115, y + 42, 115, y + 260), fill=BLUE, width=6)
    for cy, label, value, accent in [
        (y, "APPLICATION OPENS", start, GREEN),
        (y + 180, "LAST DATE TO APPLY", end, RED),
    ]:
        draw.ellipse((91, cy + 18, 139, cy + 66), fill=accent)
        draw.ellipse((104, cy + 31, 126, cy + 53), fill=WHITE)
        _text(draw, label, 165, cy + 8, F_SMALL_B, accent, 320, 4, 1)
        _text(draw, value or "See official notification", 165, cy + 43, F_H2, DARK, 470, 5, 2)

    _card(draw, 55, 555, 970, 485, NAVY, NAVY, 24, 2)
    draw.text((85, 590), "SELECTION PROCESS", font=F_H2, fill=YELLOW)
    selection = _clean(facts.get("selection_process"))
    if not selection:
        selection = next((b for b in _slide_bullets(slide) if "selection" in b.lower() or "exam" in b.lower() or "test" in b.lower()), "See official notification for selection stages.")
    _draw_bullets(draw, [selection] + [b for b in _slide_bullets(slide) if b != selection], 90, 645, 900, 1000, WHITE, 5, F_BODY, WHITE)
    _pill(draw, "SELECTION MAY DIFFER BY POST", 55, 1085, PALE_YELLOW, NAVY)
    _footer(draw)


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "") or "Official source"
    except Exception:
        return "Official source"


def _make_qr(url: str, size=205):
    if qrcode is None:
        return None
    qr = qrcode.QRCode(version=None, box_size=7, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return image.resize((size, size))


def _draw_apply_links(img, draw, slide, facts, number, total):
    org = _clean(facts.get("organisation"))
    _header(img, draw, org, number, total, "READY TO APPLY?")
    draw.text((55, 150), "APPLY THE RIGHT WAY", font=F_TITLE, fill=NAVY)
    draw.text((58, 212), "Read → Check → Apply", font=F_H2, fill=MUTED)

    # Three-step CTA strip.
    labels = [("01", "CHECK ELIGIBILITY"), ("02", "READ NOTIFICATION"), ("03", "APPLY ONLINE")]
    x = 55
    for i, (num, label) in enumerate(labels):
        w = 305 if i < 2 else 306
        _card(draw, x, 275, w, 112, NAVY if i == 2 else WHITE, NAVY if i == 2 else BORDER, 18, 2)
        draw.text((x + 22, 298), num, font=F_H1, fill=YELLOW if i == 2 else BLUE)
        _text(draw, label, x + 82, 301, F_SMALL_B, WHITE if i == 2 else DARK, w - 105, 4, 2)
        x += w + 18

    links = [x for x in (slide.get("links") or facts.get("official_links") or []) if isinstance(x, dict) and x.get("url")]
    # Deduplicate and prioritize application link if label indicates it.
    unique = []
    seen = set()
    for link in links:
        url = str(link.get("url")).strip()
        if url and url not in seen:
            seen.add(url)
            unique.append({"label": _clean(link.get("label") or "Official Link"), "url": url})
    links = unique[:2]

    y = 435
    if links:
        card_w = 465
        for i, link in enumerate(links):
            xx = 55 + i * 495
            _card(draw, xx, y, card_w, 480, WHITE, BORDER, 22, 2)
            qr = _make_qr(link["url"], 220)
            if qr is not None:
                img.paste(qr, (xx + (card_w - 220) // 2, y + 32))
            label = link["label"] or "Official Link"
            if "notification" in label.lower():
                label = "OFFICIAL NOTIFICATION"
            elif "apply" in label.lower():
                label = "OFFICIAL APPLICATION"
            else:
                label = "OFFICIAL SOURCE"
            draw.text((xx + 30, y + 275), label, font=F_H2, fill=NAVY)
            draw.text((xx + 30, y + 320), _domain(link["url"]), font=F_SMALL_B, fill=BLUE)
            draw.text((xx + 30, y + 362), "SCAN TO OPEN", font=F_TINY_B, fill=MUTED)
            draw.line((xx + 30, y + 405, xx + card_w - 30, y + 405), fill=LIGHT_LINE, width=2)
            draw.text((xx + 30, y + 423), "Use only the official source", font=F_SMALL, fill=DARK)
    else:
        _card(draw, 55, y, 970, 360, PALE_BLUE, BORDER, 22, 2)
        _text(draw, "Official application / notification links are provided in the post data. Open the official notification before submitting an application.", 90, y + 50, F_BODY_B, DARK, 900, 8, 6)

    _card(draw, 55, 955, 970, 155, NAVY, NAVY, 22, 2)
    draw.text((85, 985), "FINAL CHECK", font=F_SMALL_B, fill=YELLOW)
    _draw_bullets(draw, [
        "Match your qualification and age with the official notification.",
        "Keep required documents ready before submitting the form.",
    ], 90, 1025, 900, 1090, WHITE, 2, F_SMALL, WHITE)
    _footer(draw, "SCAN THE OFFICIAL SOURCE • DO NOT RELY ON THIRD-PARTY LINKS")



def _common_two_slide_header(draw, facts, number, total, section):
    """Identical masthead + quick-info strip for both two-slide layouts."""
    org = _clean(facts.get("organisation"))
    _header(None, draw, org, number, total, "GOVERNMENT RECRUITMENT")
    # Main recruitment line.
    title = _clean(facts.get("post") or "RECRUITMENT 2026")
    draw.text((55, 145), "RECRUITMENT", font=F_TITLE, fill=NAVY)
    # Highlighted compact designation line.
    rows = _vacancies(facts)
    names = [p for p, _ in rows]
    if names:
        sub = " • ".join(names[:3]) + (f" • +{len(names)-3} more" if len(names) > 3 else "")
    else:
        sub = title
    _text(draw, sub, 55, 205, F_H2, DARK, 700, 5, 2)
    total_v = _clean(facts.get("total_vacancies") or facts.get("combined_vacancies"))
    _card(draw, 790, 142, 235, 120, NAVY, NAVY, 18, 2)
    draw.text((810, 160), "TOTAL VACANCIES", font=F_TINY_B, fill=(214, 228, 245))
    draw.text((810, 190), total_v or "Not specified", font=F_H2, fill=YELLOW)
    # Quick-info bar.
    y = 285
    _card(draw, 35, y, 1010, 88, WHITE, BORDER, 16, 2)
    facts4 = [
        ("LOCATION", _first(facts.get("job_location"), facts.get("location"), "Not specified"), BLUE),
        ("ORGANISATION", _short_org(org) or "Not specified", BLUE),
        ("APP START", _date_label(facts.get("application_start")) or "Not specified", GREEN),
        ("APP END", _date_label(facts.get("application_end")) or "Not specified", RED),
    ]
    widths = [245, 245, 245, 245]
    x = 45
    for i, (label, value, accent) in enumerate(facts4):
        if i:
            draw.line((x, y + 13, x, y + 75), fill=LIGHT_LINE, width=2)
        draw.text((x + 14, y + 13), label, font=F_TINY_B, fill=accent)
        _text(draw, value, x + 14, y + 40, F_SMALL_B, DARK, widths[i] - 28, 3, 2)
        x += widths[i]
    draw.text((55, 390), section, font=F_H1, fill=NAVY)


def _draw_two_job_details(img, draw, slide, facts, number, total):
    _common_two_slide_header(draw, facts, number, total, "JOB DETAILS")
    rows = _vacancies(facts)
    elig = _eligibility_rows(facts)
    ordered = []
    for post, count in rows:
        match = next((r for r in elig if _post_match(post, r.get("post", ""))), None)
        ordered.append((post, count, (match or {}).get("qualification", ""), (match or {}).get("experience", "")))
    if not ordered:
        for r in elig:
            ordered.append((r.get("post", "Qualification"), "", r.get("qualification", ""), r.get("experience", "")))
    # Vacancy + qualification grid.
    x, y, w = 45, 425, 990
    _card(draw, x, y, w, 62, NAVY, NAVY, 14, 1)
    draw.text((70, y + 22), "POST", font=F_TINY_B, fill=WHITE)
    draw.text((275, y + 22), "VACANCY", font=F_TINY_B, fill=WHITE)
    draw.text((365, y + 22), "ESSENTIAL QUALIFICATION", font=F_TINY_B, fill=WHITE)
    y += 68
    max_rows = min(len(ordered), 7)
    row_h = 84 if max_rows <= 5 else 76
    for i, (post, count, qual, exp) in enumerate(ordered[:max_rows]):
        fill = WHITE if i % 2 == 0 else PALE_BLUE
        _card(draw, x, y, w, row_h, fill, BORDER, 12, 1)
        _text(draw, post, x + 18, y + 13, F_SMALL_B, NAVY, 185, 3, 2)
        draw.text((300, y + 25), count or "—", font=F_H2, fill=RED, anchor="mm")
        q = _compact_qualification(qual or "Refer to Official Notification", 285)
        _text(draw, q, x + 320, y + 10, F_TINY if len(q) > 150 else F_SMALL, DARK, 640, 3, 3)
        y += row_h + 7
    if len(ordered) > max_rows:
        _pill(draw, f"+{len(ordered)-max_rows} more verified posts • SEE NOTIFICATION FOR FULL POST-WISE DETAILS", 55, y + 2, PALE_YELLOW, NAVY)
        y += 48
    # Age + selection compact bottom row.
    bottom = min(y + 12, 1030)
    card_h = 170
    left_w = 465
    _card(draw, 45, bottom, left_w, card_h, PALE_BLUE, BORDER, 18, 2)
    draw.text((70, bottom + 18), "AGE LIMIT", font=F_SMALL_B, fill=BLUE)
    _text(draw, _compact_age(facts.get("age_limit")), 70, bottom + 52, F_H2, DARK, 410, 4, 2)
    _text(draw, "Relaxation: as specified in the official notification.", 70, bottom + 100, F_SMALL, MUTED, 410, 3, 2)
    _card(draw, 535, bottom, 500, card_h, WHITE, BORDER, 18, 2)
    draw.text((560, bottom + 18), "SELECTION PROCESS", font=F_SMALL_B, fill=GREEN)
    selection = _clean(facts.get("selection_process")) or "Refer to Official Notification"
    _text(draw, _compact_qualification(selection, 210), 560, bottom + 52, F_BODY_B if len(selection) < 100 else F_SMALL, DARK, 450, 4, 4)
    _footer(draw)


def _draw_two_at_a_glance(img, draw, slide, facts, number, total):
    _common_two_slide_header(draw, facts, number, total, "AT A GLANCE")
    age = _compact_age(facts.get("age_limit"))
    pay = _compact_pay(facts.get("pay_scale") or facts.get("salary"))
    fee = _compact_fee(facts.get("application_fee"))
    _stat_card(draw, 45, 425, 305, 165, "AGE LIMIT", age, BLUE, PALE_BLUE, "A")
    _stat_card(draw, 387, 425, 305, 165, "PAY / SALARY", pay, GREEN, PALE_GREEN, "₹")
    _stat_card(draw, 729, 425, 306, 165, "APPLICATION FEE", fee, RED, PALE_RED, "₹")

    # Dates card.
    _card(draw, 45, 615, 470, 430, WHITE, BORDER, 20, 2)
    draw.text((70, 645), "IMPORTANT DATES", font=F_H2, fill=NAVY)
    dates = [
        ("Notification", _date_label(facts.get("published_date"))),
        ("Application Start", _date_label(facts.get("application_start"))),
        ("Application Deadline", _date_label(facts.get("application_end"))),
    ]
    extra = facts.get("important_dates")
    if isinstance(extra, list):
        for item in extra:
            if isinstance(item, dict):
                label = _clean(item.get("label") or item.get("name"))
                value = _date_label(item.get("date") or item.get("value"))
                if label and value and not any(label.lower() == d[0].lower() for d in dates):
                    dates.append((label, value))
    yy = 705
    for label, value in dates[:5]:
        draw.ellipse((75, yy + 7, 87, yy + 19), fill=BLUE)
        draw.text((105, yy), label, font=F_SMALL_B, fill=NAVY)
        _text(draw, value or "Refer to Official Notification", 105, yy + 30, F_SMALL, DARK, 360, 3, 2)
        yy += 82

    # Documents/instructions card.
    _card(draw, 545, 615, 490, 430, WHITE, BORDER, 20, 2)
    draw.text((570, 645), "DOCUMENTS / HOW TO APPLY", font=F_H2, fill=NAVY)
    bullets = _slide_bullets(slide)
    # Keep only short applicant-facing instructions; avoid duplicated audit/source text.
    cleaned = []
    for b in bullets:
        low = b.lower()
        if any(k in low for k in ("quality gate", "validation", "parsed vacancies", "authoritative vacancies", "pdf extraction")):
            continue
        if not any(k in low for k in ("document", "photo", "signature", "id proof", "certificate", "marksheet", "apply", "application", "submit", "read the official", "notification", "keep required", "experience", "eligibility")):
            continue
        b = _compact_qualification(b, 130)
        if b and b not in cleaned:
            cleaned.append(b)
    if not cleaned:
        cleaned = ["Keep required documents ready.", "Check post-wise eligibility and experience.", "Submit the online application within the given dates."]
    _draw_bullets(draw, cleaned[:6], 575, 705, 425, 1010, GREEN, 6, F_SMALL)

    # Official source CTA: structured links are shown as short labels/QRs, never raw URLs.
    links = [x for x in (slide.get("links") or facts.get("official_links") or []) if isinstance(x, dict) and x.get("url")]
    unique, seen = [], set()
    for link in links:
        url = str(link.get("url")).strip()
        if url and url not in seen:
            seen.add(url)
            unique.append({"label": _clean(link.get("label") or "Official Source"), "url": url})
    if unique and qrcode is not None:
        qr = _make_qr(unique[0]["url"], 125)
        if qr:
            img.paste(qr, (565, 900))
        draw.text((710, 910), "OFFICIAL SOURCE", font=F_SMALL_B, fill=BLUE)
        draw.text((710, 945), _domain(unique[0]["url"]), font=F_SMALL_B, fill=DARK)
        draw.text((710, 978), "SCAN TO OPEN", font=F_TINY_B, fill=MUTED)

    deadline = _date_label(facts.get("application_end")) or "the deadline"
    _card(draw, 45, 1070, 990, 115, NAVY, NAVY, 18, 2)
    draw.text((75, 1092), "APPLY ONLINE ONLY THROUGH THE OFFICIAL WEBSITE", font=F_SMALL_B, fill=YELLOW)
    _text(draw, f"Before {deadline}", 75, 1128, F_H2, WHITE, 880, 4, 1)
    _footer(draw)

def render_slide(slide: dict[str, Any], facts: dict, number: int, total: int, path: Path):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    slide_type = str(slide.get("type") or "").lower()
    if slide_type == "job_details":
        _draw_two_job_details(img, draw, slide, facts, number, total)
    elif slide_type == "at_a_glance":
        _draw_two_at_a_glance(img, draw, slide, facts, number, total)
    elif slide_type == "title":
        _draw_title(img, draw, slide, facts, number, total)
    elif slide_type == "vacancies":
        _draw_vacancies(img, draw, slide, facts, number, total)
    elif slide_type == "eligibility":
        _draw_eligibility(img, draw, slide, facts, number, total)
    elif slide_type == "age_pay_fee":
        _draw_age_pay_fee(img, draw, slide, facts, number, total)
    elif slide_type == "dates_selection":
        _draw_dates_selection(img, draw, slide, facts, number, total)
    elif slide_type == "apply_links":
        _draw_apply_links(img, draw, slide, facts, number, total)
    else:
        # Safe fallback retains the creative masthead and never exposes QA text.
        _header(img, draw, str(facts.get("organisation") or ""), number, total)
        draw.text((55, 155), _clean(slide.get("headline") or "Recruitment Details"), font=F_TITLE, fill=NAVY)
        _draw_bullets(draw, _slide_bullets(slide), 70, 245, 930, 1160, BLUE, 6, F_BODY_B)
        _footer(draw)
    img.save(path, quality=95)


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(text or "slides"))[:70].strip("_") or "slides"


def render_qwen_plan(plan_path: str | Path, output_dir: str | Path, job_index: int | None = None) -> list[Path]:
    data = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []

    for job in data.get("jobs", []):
        if job_index is not None and job.get("job_index") != job_index:
            continue
        # V1.9.26: rendering is a separate delivery layer. A job may have
        # source/slide QA warnings and still be renderable when it has a
        # complete two-slide plan. The QA result remains in the JSON audit;
        # rendering must not silently discard the job.
        plan = job.get("slide_plan") or {}
        slides = plan.get("slides") or []
        if not slides or len(slides) != 6:
            continue
        facts = job.get("locked_facts") or {}
        organisation = _clean(facts.get("organisation"))
        stem = _safe(organisation or f"job_{job.get('job_index', 1)}")
        job_dir = output / f"{int(job.get('job_index', 1)):02d}_{stem}"
        job_dir.mkdir(parents=True, exist_ok=True)
        for pos, slide in enumerate(slides, 1):
            path = job_dir / f"{pos:02d}_{stem}.png"
            render_slide(slide, facts, pos, len(slides), path)
            rendered.append(path)
    return rendered
