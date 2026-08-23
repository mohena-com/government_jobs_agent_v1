import re
from urllib.parse import urljoin, urldefrag, urlparse

import requests
from bs4 import BeautifulSoup

from .parser import HEADERS


# ---------------------------------------------------------
# HTTP
# ---------------------------------------------------------

def fetch_detail(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=45,
        allow_redirects=True,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    return soup, response.url


# ---------------------------------------------------------
# TEXT HELPERS
# ---------------------------------------------------------

def clean_text(value):
    if not value:
        return ""

    return " ".join(str(value).split()).strip()


def visible_text(soup):
    """
    Extract visible text from the SarkariResult job page.
    """

    clone = BeautifulSoup(str(soup), "lxml")

    for tag in clone([
        "script",
        "style",
        "noscript",
        "svg",
        "iframe",
    ]):
        tag.decompose()

    lines = []

    for line in clone.get_text("\n").splitlines():

        line = clean_text(line)

        if line:
            lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------
# HEADING / SECTION EXTRACTION
# ---------------------------------------------------------

SECTION_ALIASES = {

    "important_dates": [
        "important dates",
    ],

    "application_fee": [
        "application fee",
        "exam fee",
        "application fees",
    ],

    "age_limit": [
        "age limit",
        "age limit as on",
    ],

    "vacancy_details": [
        "vacancy details",
        "vacancy detail",
    ],

    "eligibility": [
        "eligibility",
        "educational qualification",
        "qualification",
    ],

    "selection_process": [
        "selection process",
        "selection procedure",
    ],

    "pay_scale": [
        "pay scale",
        "salary",
        "pay level",
    ],

    "how_to_apply": [
        "how to fill",
        "how to apply",
    ],

    "important_instructions": [
        "important instruction",
        "important instructions",
        "important note",
    ],
}


def find_section(lines, aliases):

    start = None

    for i, line in enumerate(lines):

        low = line.lower().strip()

        for alias in aliases:

            if alias in low:

                start = i
                break

        if start is not None:
            break

    if start is None:
        return ""

    result = []

    for i in range(start, len(lines)):

        line = lines[i]

        if i > start:

            low = line.lower().strip()

            # Stop when another major section begins.
            for other_aliases in SECTION_ALIASES.values():

                if other_aliases == aliases:
                    continue

                if any(
                    low.startswith(alias)
                    for alias in other_aliases
                ):
                    return "\n".join(result).strip()

        result.append(line)

    return "\n".join(result).strip()


# ---------------------------------------------------------
# POST TITLE
# ---------------------------------------------------------

def extract_post_title(soup, lines):

    # Preferred: H1
    h1 = soup.find("h1")

    if h1:

        title = clean_text(h1.get_text(" ", strip=True))

        if title:
            return title

    # Fallback: first heading
    for tag in soup.find_all(["h1", "h2", "h3"]):

        title = clean_text(tag.get_text(" ", strip=True))

        if title and "sarkari" not in title.lower():

            return title

    return ""


# ---------------------------------------------------------
# POST DATE / UPDATE
# ---------------------------------------------------------

def extract_post_update(lines):

    for i, line in enumerate(lines):

        if "post date / update" in line.lower():

            # Sometimes date is in the next line.
            if i + 1 < len(lines):

                return clean_text(lines[i + 1])

            return clean_text(line)

    return ""


# ---------------------------------------------------------
# SHORT INFORMATION
# ---------------------------------------------------------

def extract_short_information(lines):

    start = None

    for i, line in enumerate(lines):

        if "short information" in line.lower():

            start = i + 1
            break

    if start is None:
        return ""

    result = []

    stop_words = [
        "telegram",
        "whatsapp",
        "instagram",
        "twitter",
        "join us",
        "follow",
    ]

    for line in lines[start:start + 20]:

        low = line.lower()

        if any(x in low for x in stop_words):
            break

        if line.strip():
            result.append(line)

    return " ".join(result).strip()


# ---------------------------------------------------------
# ORGANISATION
# ---------------------------------------------------------

def extract_organisation(soup, lines):

    # Look for headings.
    for tag in soup.find_all(["h2", "h3", "h4"]):

        text = clean_text(tag.get_text(" ", strip=True))

        if not text:
            continue

        if any(
            x in text.lower()
            for x in [
                "management trainee recruitment",
                "recruitment 2026",
                "online form",
                "vacancy details",
            ]
        ):
            continue

        # Often the organisation is the heading immediately before
        # the recruitment title.
        if len(text) > 5 and len(text) < 150:

            return text

    # Fallback: search for common organisation wording.
    for line in lines:

        low = line.lower()

        if any(
            x in low
            for x in [
                "limited",
                "university",
                "commission",
                "corporation",
                "authority",
                "board",
                "department",
                "ministry",
            ]
        ):

            if len(line) < 200:

                return line

    return ""


# ---------------------------------------------------------
# ADVERTISEMENT NUMBER
# ---------------------------------------------------------

def extract_advertisement_number(text):

    patterns = [

        r"advt\.?\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Za-z0-9./\-]+)",

        r"advertisement\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Za-z0-9./\-]+)",

        r"adv\.?\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Za-z0-9./\-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:

            return match.group(1).strip()

    return ""


# ---------------------------------------------------------
# TOTAL VACANCIES
# ---------------------------------------------------------

def extract_total_vacancies(text):

    patterns = [

        r"vacancy\s+details.*?total\s*[:\-]?\s*([\d,]+)\s*post",

        r"vacancy\s+details.*?total\s*[:\-]?\s*([\d,]+)\s*posts",

        r"total\s*[:\-]?\s*([\d,]+)\s*post",

        r"total\s+vacanc(?:y|ies)\s*[:\-]?\s*([\d,]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I | re.S
        )

        if match:

            return int(
                match.group(1).replace(",", "")
            )

    return None


# ---------------------------------------------------------
# APPLICATION DATES
# ---------------------------------------------------------

def extract_application_dates(section):

    result = {
        "application_start": "",
        "application_end": "",
    }

    if not section:
        return result

    start_patterns = [
        r"application\s+begin\s*[:\-]\s*([^\n]+)",
        r"start\s+date\s*[:\-]\s*([^\n]+)",
        r"apply\s+online\s+from\s*[:\-]\s*([^\n]+)",
    ]

    end_patterns = [
        r"last\s+date\s+for\s+apply\s+online\s*[:\-]\s*([^\n]+)",
        r"last\s+date\s*[:\-]\s*([^\n]+)",
        r"closing\s+date\s*[:\-]\s*([^\n]+)",
    ]

    for pattern in start_patterns:

        match = re.search(
            pattern,
            section,
            re.I
        )

        if match:

            result["application_start"] = clean_text(
                match.group(1)
            )

            break

    for pattern in end_patterns:

        match = re.search(
            pattern,
            section,
            re.I
        )

        if match:

            result["application_end"] = clean_text(
                match.group(1)
            )

            break

    return result


# ---------------------------------------------------------
# APPLICATION FEE
# ---------------------------------------------------------

def extract_fee(section):

    if not section:
        return ""

    return section.strip()


# ---------------------------------------------------------
# AGE
# ---------------------------------------------------------

def extract_age(section):

    if not section:
        return ""

    return section.strip()


# ---------------------------------------------------------
# VACANCY TABLES
# ---------------------------------------------------------

def extract_tables(soup):

    tables = []

    for table in soup.find_all("table"):

        rows = []

        for tr in table.find_all("tr"):

            cells = []

            for cell in tr.find_all([
                "th",
                "td",
            ]):

                value = clean_text(
                    cell.get_text(
                        " ",
                        strip=True
                    )
                )

                cells.append(value)

            if cells:

                rows.append(cells)

        if rows:

            tables.append(rows)

    return tables


# ---------------------------------------------------------
# CONVERT VACANCY TABLE INTO RECORDS
# ---------------------------------------------------------

def extract_vacancy_rows(tables):

    vacancy_rows = []

    for table in tables:

        for row in table:

            if len(row) < 2:
                continue

            first = row[0]
            second = row[1]

            # Detect rows such as:
            #
            # Management Trainee (Chemical) | 32
            #
            match = re.search(
                r"(\d[\d,]*)",
                second
            )

            if match:

                vacancy_rows.append({
                    "post_name": first,
                    "vacancies": int(
                        match.group(1).replace(",", "")
                    ),
                    "raw_row": row,
                })

    return vacancy_rows


# ---------------------------------------------------------
# LINKS
# ---------------------------------------------------------

LINK_KEYWORDS = [

    "apply online",
    "apply now",
    "online form",
    "official website",
    "notification",
    "advertisement",
    "download notification",
    "official notification",
    "application form",
    "registration",
    "click here",
]


def classify_domain(url):

    host = (
        urlparse(url).hostname
        or ""
    ).lower()

    if (
        host == "sarkariresult.com"
        or host.endswith(".sarkariresult.com")
    ):
        return "sarkariresult"

    if (
        host.endswith(".gov.in")
        or host.endswith(".nic.in")
        or host.endswith(".ac.in")
    ):
        return "likely_official"

    return "third_party"


def extract_links(soup, base_url):

    links = []

    seen = set()

    for a in soup.find_all(
        "a",
        href=True
    ):

        text = clean_text(
            a.get_text(
                " ",
                strip=True
            )
        )

        href = a.get(
            "href",
            ""
        ).strip()

        url = urljoin(
            base_url,
            href
        )

        url, _ = urldefrag(url)

        if not url:
            continue

        if url in seen:
            continue

        combined = (
            text + " " + href
        ).lower()

        if any(
            keyword in combined
            for keyword in LINK_KEYWORDS
        ):

            seen.add(url)

            links.append({
                "text": text or "(button/link)",
                "url": url,
                "domain_class": classify_domain(url),
            })

    return links


# ---------------------------------------------------------
# BEST LINKS
# ---------------------------------------------------------

def classify_links(links):

    notification_links = []

    application_links = []

    official_candidates = []

    for link in links:

        text = (
            link["text"]
            + " "
            + link["url"]
        ).lower()

        if (
            "notification" in text
            or "advertisement" in text
            or link["url"].lower().endswith(".pdf")
        ):

            notification_links.append(
                link
            )

        if any(
            x in text
            for x in [
                "apply online",
                "apply now",
                "online form",
                "application form",
                "registration",
            ]
        ):

            application_links.append(
                link
            )

        if (
            link["domain_class"]
            != "sarkariresult"
        ):

            official_candidates.append(
                link
            )

    return {
        "notification_links": notification_links,
        "application_links": application_links,
        "official_candidates": official_candidates,
    }


# ---------------------------------------------------------
# MAIN DETAIL EXTRACTION
# ---------------------------------------------------------

def extract_detail(
    url,
    listing
):

    soup, final_url = fetch_detail(url)

    text = visible_text(soup)

    lines = text.splitlines()

    # Sections
    sections = {}

    for field_name, aliases in SECTION_ALIASES.items():

        sections[field_name] = find_section(
            lines,
            aliases
        )

    # Tables
    tables = extract_tables(
        soup
    )

    vacancy_rows = extract_vacancy_rows(
        tables
    )

    # Basic fields
    post_title = extract_post_title(
        soup,
        lines
    )

    organisation = extract_organisation(
        soup,
        lines
    )

    post_update = extract_post_update(
        lines
    )

    short_information = extract_short_information(
        lines
    )

    advertisement_number = extract_advertisement_number(
        text
    )

    total_vacancies = extract_total_vacancies(
        text
    )

    dates = extract_application_dates(
        sections["important_dates"]
    )

    links = extract_links(
        soup,
        final_url
    )

    link_groups = classify_links(
        links
    )

    # -----------------------------------------------------
    # Structured recruitment record
    # -----------------------------------------------------

    job = {

        "organisation": organisation,

        "post_title": post_title,

        "advertisement_number":
            advertisement_number,

        "post_update":
            post_update,

        "short_information":
            short_information,

        "application_start":
            dates["application_start"],

        "application_end":
            dates["application_end"],

        "application_fee":
            extract_fee(
                sections["application_fee"]
            ),

        "age_limit":
            extract_age(
                sections["age_limit"]
            ),

        "total_vacancies":
            total_vacancies,

        "vacancy_rows":
            vacancy_rows,

        "eligibility":
            sections["eligibility"],

        "selection_process":
            sections["selection_process"],

        "pay_scale":
            sections["pay_scale"],

        "how_to_apply":
            sections["how_to_apply"],

        "important_instructions":
            sections["important_instructions"],

        "important_dates_raw":
            sections["important_dates"],

        "vacancy_details_raw":
            sections["vacancy_details"],

        "detail_url":
            final_url,

        "notification_links":
            link_groups["notification_links"],

        "application_links":
            link_groups["application_links"],

        "official_candidates":
            link_groups["official_candidates"],

        "all_links":
            links,

        "raw_text":
            text,

        "tables":
            tables,

        # Keep the original discovery record.
        "listing":
            listing,
    }

    return job