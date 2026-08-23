from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
BG = (247, 249, 252)
NAVY = (13, 48, 96)
BLUE = (24, 78, 145)
YELLOW = (248, 188, 28)
DARK = (22, 30, 43)
MUTED = (92, 105, 122)
WHITE = (255, 255, 255)
BORDER = (205, 216, 230)
RED = (190, 50, 50)


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


def _card(draw, x, y, w, h, fill=WHITE):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=24, fill=fill, outline=BORDER, width=2)


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(text or "slides"))[:70].strip("_") or "slides"


def _strip_internal_metadata(text: str) -> str:
    # Defense-in-depth: renderer never displays audit/QA language.
    patterns = [r"status\s*:\s*(?:pass|fail)", r"quality\s*gate\s*:\s*(?:pass|fail)"]
    out = str(text or "")
    for p in patterns:
        out = re.sub(p, "", out, flags=re.I)
    return re.sub(r"\s{2,}", " ", out).strip()


def render_slide(slide: dict[str, Any], organisation: str, number: int, total: int, path: Path):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 112), fill=NAVY)
    if organisation:
        _draw_wrapped(draw, organisation, 55, 26, F_H2, WHITE, 760, 2, 1)
    draw.text((W - 125, 36), f"{number}/{total}", font=F_SMALL_B, fill=WHITE)
    draw.text((55, 82), "GOVERNMENT RECRUITMENT", font=F_SMALL, fill=(215, 228, 244))

    headline = _strip_internal_metadata(slide.get("headline", ""))
    subtitle = _strip_internal_metadata(slide.get("subtitle", ""))
    bullets = [_strip_internal_metadata(x) for x in slide.get("bullets", []) if _strip_internal_metadata(x)]

    y = 160
    _draw_wrapped(draw, headline, 55, y, F_XL if len(headline) < 50 else F_TITLE, NAVY, 970, 10, 4)
    y += 150 if len(headline) < 50 else 190
    if subtitle:
        y = _draw_wrapped(draw, subtitle, 58, y, F_H2, MUTED, 930, 8, 3) + 25

    for bullet in bullets[:6]:
        if y > H - 180:
            break
        _card(draw, 55, y, 970, 105, WHITE)
        draw.ellipse((82, y + 39, 96, y + 53), fill=YELLOW)
        _draw_wrapped(draw, bullet, 120, y + 27, F_BODY_B if len(bullet) < 75 else F_BODY, DARK, 860, 7, 2)
        y += 125

    draw.rectangle((0, H - 62, W, H), fill=NAVY)
    draw.text((55, H - 43), "Verify eligibility, dates and conditions in the official notification.", font=F_SMALL, fill=WHITE)
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
