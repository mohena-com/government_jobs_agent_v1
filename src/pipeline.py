import os,yaml
from pathlib import Path
from datetime import datetime,timedelta,timezone
from dotenv import load_dotenv
from src.discovery.sources import build_sources
from src.extraction.pdf import extract_pdf_text
from src.extraction.deterministic import extract
from src.extraction.ai import extract_with_openai
from src.database.db import connect,init_db,upsert,all_recruitments
from src.reporting.docx_report import build_report
from src.verification.verifier import verify
from src.utils.http import get,is_pdf_response,safe_filename,sha256_bytes
load_dotenv()
def run(report_only=False):
    with open('config/sources.yaml') as f:cfg=yaml.safe_load(f)
    with open('config/settings.yaml') as f:settings=yaml.safe_load(f)
    c=connect(os.getenv('DATABASE_PATH','data/recruitment.db'));init_db(c)
    if not report_only:
        now=datetime.now(timezone.utc);since=now-timedelta(hours=int(os.getenv('LOOKBACK_HOURS','24')))
        for s in build_sources(cfg):
            try:cands=s.discover(since,now)
            except Exception as e:print('[WARN]',s.config['name'],e);continue
            for cand in cands:
                text='';doc_hash='';doc_path=''
                if cand.notification_url:
                    try:
                        r=get(cand.notification_url);r.raise_for_status()
                        if is_pdf_response(r):
                            Path(os.getenv('DOCUMENT_DIR','data/documents')).mkdir(parents=True,exist_ok=True);doc_path=str(Path(os.getenv('DOCUMENT_DIR','data/documents'))/safe_filename(r.url));Path(doc_path).write_bytes(r.content);doc_hash=sha256_bytes(r.content);text=extract_pdf_text(doc_path)
                    except Exception as e:print('[WARN] document',e)
                rec=extract(text,cand)
                if text and os.getenv('OPENAI_API_KEY'):
                    try: rec=extract_with_openai(text,cand)
                    except Exception as e:print('[WARN] AI extraction',e)
                rec.notification_url=rec.notification_url or cand.notification_url;rec.application_url=rec.application_url or cand.application_url;rec.official_source_url=rec.official_source_url or cand.source_url;rec.source_document=doc_path;rec.document_hash=doc_hash;rec=verify(rec,settings.get('additional_trusted_domains',[]),settings.get('trusted_suffixes',[]));upsert(c,rec)
    records=all_recruitments(c);path=Path(os.getenv('REPORT_DIR','reports'))/f"Government_Jobs_Report_{datetime.now().strftime('%Y-%m-%d')}.docx";build_report(records,path);print('REPORT=',path);print('RECORDS=',len(records));return path
