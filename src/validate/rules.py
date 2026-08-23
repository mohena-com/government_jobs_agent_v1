from collections import Counter

def validate(recruitments):
    warnings = []
    if not recruitments:
        warnings.append("No vacancy sections detected. PDF structure may have changed or OCR may be required.")
        return warnings

    vacancy_nos = [r.vacancy_no for r in recruitments if r.vacancy_no]
    dupes = [x for x,c in Counter(vacancy_nos).items() if c > 1]
    if dupes:
        warnings.append(f"Duplicate vacancy numbers detected: {dupes}")

    for r in recruitments:
        if not r.post_title:
            r.warnings.append("Post title not confidently extracted.")
        if r.total_vacancies is None:
            r.warnings.append("Total vacancy count not confidently extracted.")
        if not r.essential_qualification:
            r.warnings.append("Essential qualification not confidently extracted.")
        if not r.age_limit:
            r.warnings.append("Age limit not confidently extracted.")
        if not r.pay_level:
            r.warnings.append("Pay level/pay scale not confidently extracted.")
        if not r.notification_url.startswith("https://www.upsc.gov.in/"):
            r.warnings.append("Notification URL is not an official UPSC domain.")
    return warnings
