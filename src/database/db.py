import sqlite3,hashlib,json
from pathlib import Path
FIELDS=[x for x in '''organisation ministry_department recruiting_body post_title vacancies_total advertisement_number notification_number publication_date updated_date application_start_date application_end_date qualification experience age_limit age_relaxation pay_scale pay_level salary category_requirements application_fee application_url notification_url official_source_url official_domain important_instructions selection_process job_location source_name source_verified extraction_confidence fingerprint document_hash source_document notes'''.split()]
def connect(p): Path(p).parent.mkdir(parents=True,exist_ok=True); return sqlite3.connect(p)
def init_db(c):
    types={f:'INTEGER' if f=='vacancies_total' else 'REAL' if f=='extraction_confidence' else 'INTEGER' if f=='source_verified' else 'TEXT' for f in FIELDS}
    c.execute('CREATE TABLE IF NOT EXISTS recruitments (id INTEGER PRIMARY KEY AUTOINCREMENT,'+','.join(f'"{f}" {types[f]}' for f in FIELDS)+',created_at TEXT,updated_at TEXT)'); c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_fp ON recruitments(fingerprint)'); c.commit()
def fingerprint(r):
    raw='|'.join(str(x or '').strip().lower() for x in [r.organisation,r.advertisement_number,r.post_title,r.publication_date]); return hashlib.sha256(raw.encode()).hexdigest()
def upsert(c,r):
    r.fingerprint=r.fingerprint or fingerprint(r); d=r.as_dict(); d['important_instructions']=json.dumps(d['important_instructions'],ensure_ascii=False); import datetime; now=datetime.datetime.utcnow().isoformat(); old=c.execute('SELECT id FROM recruitments WHERE fingerprint=?',(r.fingerprint,)).fetchone()
    if old:
        c.execute('UPDATE recruitments SET '+','.join(f'"{f}"=?' for f in FIELDS)+',updated_at=? WHERE id=?',[d.get(f) for f in FIELDS]+[now,old[0]])
    else:
        c.execute('INSERT INTO recruitments ('+','.join(FIELDS)+',created_at,updated_at) VALUES ('+','.join('?' for _ in range(len(FIELDS)+2))+')',[d.get(f) for f in FIELDS]+[now,now])
    c.commit()
def all_recruitments(c):
    rows=c.execute('SELECT '+','.join(FIELDS)+' FROM recruitments ORDER BY application_end_date ASC,organisation ASC').fetchall(); out=[]
    for row in rows:
        d=dict(zip(FIELDS,row))
        try:d['important_instructions']=json.loads(d['important_instructions'] or '[]')
        except:d['important_instructions']=[]
        out.append(d)
    return out
