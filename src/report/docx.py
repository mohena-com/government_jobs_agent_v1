# =========================================================
# REMOVE SOCIAL / NAVIGATION GARBAGE
# =========================================================

SOCIAL_GARBAGE = {
    "telegram",
    "join us",
    "whatsapp",
    "instagram",
    "follow",
    "x",
    "image",
}


def clean_report_value(value):
    """
    Remove social-media/navigation artefacts that sometimes
    leak from SarkariResult HTML into structured fields.

    This is applied at report-generation time as a final
    safety layer.
    """

    if value is None:
        return ""

    text = str(value)

    cleaned_lines = []

    for raw_line in text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # Remove source bullet characters.
        line = line.lstrip("·•*- ").strip()

        # Exact garbage line.
        if line.lower() in SOCIAL_GARBAGE:
            continue

        # Remove lines containing only social/navigation text.
        low = line.lower()

        if (
            "telegram" in low
            or "whatsapp" in low
            or "instagram" in low
        ) and len(line) < 80:
            continue

        if (
            low.startswith("join us")
            or low.startswith("follow")
        ) and len(line) < 80:
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()