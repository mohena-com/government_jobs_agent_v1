import json, sqlite3
from pathlib import Path

def save(path, advt, records):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE IF NOT EXISTS recruitments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        advertisement_no TEXT,
        vacancy_no TEXT,
        data_json TEXT,
        UNIQUE(advertisement_no, vacancy_no)
    )""")
    for r in records:
        con.execute("""INSERT INTO recruitments(advertisement_no,vacancy_no,data_json)
                       VALUES(?,?,?)
                       ON CONFLICT(advertisement_no,vacancy_no)
                       DO UPDATE SET data_json=excluded.data_json""",
                    (advt, r.vacancy_no, r.model_dump_json()))
    con.commit()
    con.close()
