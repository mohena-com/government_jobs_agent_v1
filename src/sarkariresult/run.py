from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from .parser import scan_latest_jobs
from .detail import fetch_detail, extract_detail_links, extract_pdf_links
from .report import build

IST=ZoneInfo("Asia/Kolkata")

def run(deep=False):
    today=datetime.now(IST).date()
    rows=scan_latest_jobs(today)
    if deep:
        for row in rows:
            try:
                soup, final_url=fetch_detail(row["url"])
                row["detail_url"]=final_url
                row["candidate_links"]=extract_detail_links(soup,final_url)
                row["pdf_links"]=extract_pdf_links(soup,final_url)
                row["official_candidates"]=[x for x in row["candidate_links"] if x["official_candidate"]]
            except Exception as e:
                row["detail_error"]=str(e)
    out=Path("reports")/f"SarkariResult_Future_Jobs_{today.isoformat()}.docx"
    build(rows,out,today)
    print(f"SarkariResult future listings: {len(rows)}")
    print(f"Report: {out}")
    if deep:
        for r in rows:
            print(f"\n{r['last_date']} | {r['title']}")
            for x in r.get("official_candidates",[])[:10]: print("  OFFICIAL?",x["text"],"=>",x["url"])
            for x in r.get("pdf_links",[])[:5]: print("  PDF",x)
    return rows
