import argparse, os, yaml
from pathlib import Path
from dotenv import load_dotenv

from src.pdf.download import download_pdf
from src.pdf.pages import read_pages
from src.extract.segments import find_segments
from src.extract.fields import extract_segment
from src.extract.ai_validate import ai_validate
from src.validate.rules import validate
from src.report.docx import make_report
from src.db.store import save

load_dotenv()

def load_cfg():
    with open("config/upsc.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run(advt):
    cfg = load_cfg()
    spec = cfg["advertisements"][str(advt)]
    data_dir = Path(os.getenv("DATA_DIR", "data"))

    pdf_path = data_dir / "raw" / f"UPSC_Advt_{advt}_2026.pdf"
    _, sha = download_pdf(spec["pdf_url"], pdf_path)

    pages = read_pages(pdf_path)
    segments = find_segments(pages)

    records = []
    for seg in segments:
        r = extract_segment(seg, spec["number"], spec["pdf_url"])
        # AI is a second-pass validator, not the primary parser.
        try:
            r = ai_validate(r, seg["text"])
        except Exception as e:
            r.warnings.append(f"AI validation unavailable: {e}")
        records.append(r)

    global_warnings = validate(records)
    for r in records:
        r.warnings.extend(global_warnings)

    save(data_dir / "upsc.sqlite", spec["number"], records)

    report = Path(os.getenv("REPORT_DIR", "reports")) / f"UPSC_Advt_{advt}_2026_Deep_Report.docx"
    make_report(spec["number"], records, report)

    print(f"Advertisement: {spec['number']}")
    print(f"PDF SHA256: {sha}")
    print(f"Pages: {len(pages)}")
    print(f"Recruitment sections detected: {len(records)}")
    print(f"Report: {report}")
    for i, r in enumerate(records, 1):
        print(f"{i:02d}. {r.vacancy_no} | {r.post_title or 'NOT EXTRACTED'} | {r.total_vacancies or '?'} | {r.confidence:.0%}")

    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--advt", default="09", choices=["09","51"])
    args = parser.parse_args()
    run(args.advt)
