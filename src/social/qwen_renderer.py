from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

try:
    import qrcode
except ImportError:  # pragma: no cover - optional until rendering links
    qrcode = None

W, H = 1080, 1350
BG = (247, 249, 252)
NAVY = (13, 48, 96)
BLUE = (24, 78, 145)
YELLOW = (248, 188, 28)
DARK = (22, 30, 43)
MUTED = (92, 105, 122)
WHITE = (255, 255, 255)
BORDER = (205, 216, 230)
GREEN = (33, 115, 76)


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


F_XL = _font(62, True)
F_TITLE = _font(48, True)
F_H2 = _font(31, True)
F_BODY = _font(27, False)
F_BODY_B = _font(28, True)
F_SMALL = _font(20, False)
F_SMALL_B = _font(20, True)
F_LINK = _font(24, True)
F_QR = _font(22, True)


def _wrap(draw, text: str, font, width: int, max_lines: int | None = None):
    words = str(text or "").split()
    lines, current = [], ""
    for word in words:
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


def _draw_wrapped(draw, text, x, y, font, fill=DARK, width=940, gap=9, max_lines=None):
    for line in _wrap(draw, text, font, width, max_lines):
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + gap
    return y


def _card(draw, x, y, w, h, fill=WHITE, outline=BORDER):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=24, fill=fill, outline=outline, width=2)


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(text or "slides"))[:70].strip("_") or "slides"


def _strip_internal_metadata(text: str) -> str:
    patterns = [
        r"status\s*:\s*(?:pass|fail)",
        r"quality\s*gate\s*:\s*(?:pass|fail)",
        r"slide\s*quality\s*gate\s*:\s*(?:pass|fail)",
        r"vacancy\s+reconciliation",
        r"extraction\s+repairs",
        r"parsed\s+vacancies\s*:\s*\d+",
        r"authoritative\s+vacancies\s*:\s*\d+",
    ]
    out = str(text or "")
    for p in patterns:
        out = re.sub(p, "", out, flags=re.I)
    out = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", out)
    return re.sub(r"\s{2,}", " ", out).strip(" -:;,")


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "") or "Official source"
    except Exception:
        return "Official source"


def _make_qr(url: str, size: int = 210):
    if qrcode is None:
        return None
    qr = qrcode.QRCode(version=None, box_size=7, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size))


def _draw_header(draw, organisation: str, number: int, total: int):
    draw.rectangle((0, 0, W, 112), fill=NAVY)
    if organisation:
        _draw_wrapped(draw, organisation, 55, 26, F_H2, WHITE, 760, 2, 1)
    draw.text((W - 125, 36), f"{number}/{total}", font=F_SMALL_B, fill=WHITE)
    draw.text((55, 82), "GOVERNMENT RECRUITMENT", font=F_SMALL, fill=(215, 228, 244))


def _draw_footer(draw):
    draw.rectangle((0, H - 62, W, H), fill=NAVY)
    draw.text((55, H - 43), "Verify eligibility, dates and conditions in the official notification.", font=F_SMALL, fill=WHITE)


def _draw_standard(draw, slide, y):
    headline = _strip_internal_metadata(slide.get("headline", ""))
    subtitle = _strip_internal_metadata(slide.get("subtitle", ""))
    bullets = [_strip_internal_metadata(x) for x in slide.get("bullets", []) if _strip_internal_metadata(x)]
    y = _draw_wrapped(draw, headline, 55, y, F_XL if len(headline) < 50 else F_TITLE, NAVY, 970, 10, 4)
    y += 34
    if subtitle:
        y = _draw_wrapped(draw, subtitle, 58, y, F_H2, MUTED, 930, 8, 3) + 20
    for bullet in bullets[:6]:
        if y > H - 190:
            break
        _card(draw, 55, y, 970, 105, WHITE)
        draw.ellipse((82, y + 39, 96, y + 53), fill=YELLOW)
        _draw_wrapped(draw, bullet, 120, y + 27, F_BODY_B if len(bullet) < 75 else F_BODY, DARK, 860, 7, 2)
        y += 125


def _draw_links(img, draw, slide, y):
    headline = _strip_internal_metadata(slide.get("headline") or "Official Links")
    subtitle = _strip_internal_metadata(slide.get("subtitle") or "Use the QR codes to open the official recruitment documents.")
    y = _draw_wrapped(draw, headline, 55, y, F_XL if len(headline) < 50 else F_TITLE, NAVY, 970, 10, 2)
    y += 25
    y = _draw_wrapped(draw, subtitle, 58, y, F_H2, MUTED, 930, 8, 2) + 18

    links = [x for x in (slide.get("links") or []) if isinstance(x, dict) and x.get("url")]
    # Do not render raw URLs. Human-friendly labels + domain + QR are rendered instead.
    if not links:
        _card(draw, 55, y, 970, 150)
        _draw_wrapped(draw, "See the official notification for the application procedure.", 85, y + 35, F_BODY_B, DARK, 900, 8, 3)
        return

    card_w = 300
    gap = 25
    x_positions = [55, 55 + card_w + gap, 55 + 2 * (card_w + gap)]
    for i, link in enumerate(links[:3]):
        x = x_positions[i]
        _card(draw, x, y, card_w, 370, WHITE)
        qr = _make_qr(str(link["url"]), 205)
        if qr is not None:
            img_x = x + (card_w - 205) // 2
            img.paste(qr, (img_x, y + 28))
        else:
            draw.text((x + 80, y + 100), "QR unavailable", font=F_SMALL_B, fill=MUTED)
        label = _strip_internal_metadata(link.get("label") or f"Official Link {i + 1}")
        if label.lower() == "official notification":
            label = f"Official Notification {i + 1}"
        _draw_wrapped(draw, label, x + 18, y + 245, F_LINK, DARK, card_w - 36, 5, 2)
        _draw_wrapped(draw, _domain(str(link["url"])), x + 18, y + 315, F_SMALL, MUTED, card_w - 36, 5, 1)

    note_y = y + 395
    note = _strip_internal_metadata(slide.get("link_note") or "Scan a QR code to open the official source.")
    _draw_wrapped(draw, note, 58, note_y, F_BODY_B, GREEN, 930, 8, 2)


def render_slide(slide: dict[str, Any], organisation: str, number: int, total: int, path: Path):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    _draw_header(draw, organisation, number, total)

    slide_type = str(slide.get("type") or "").lower()
    if slide_type == "apply_links" or slide.get("links"):
        _draw_links(img, draw, slide, 160)
    else:
        _draw_standard(draw, slide, 160)

    _draw_footer(draw)
    img.save(path, quality=95)


def render_qwen_plan(plan_path: str | Path, output_dir: str | Path, job_index: int | None = None) -> list[Path]:
    data = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []

    jobs = data.get("jobs", [])
    for job in jobs:
        if job_index is not None and job.get("job_index") != job_index:
            continue
        if job.get("presentation_ready") is False:
            continue
        plan = job.get("slide_plan") or {}
        slides = plan.get("slides") or []
        if not slides:
            continue
        facts = job.get("locked_facts") or {}
        organisation = str(facts.get("organisation") or "")
        stem = _safe(organisation or f"job_{job.get('job_index', 1)}")
        job_dir = output / f"{int(job.get('job_index', 1)):02d}_{stem}"
        job_dir.mkdir(parents=True, exist_ok=True)
        for pos, slide in enumerate(slides, 1):
            path = job_dir / f"{pos:02d}_{stem}.png"
            render_slide(slide, organisation, pos, len(slides), path)
            rendered.append(path)
    return rendered
