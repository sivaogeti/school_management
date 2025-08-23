# modules/key_guidelines_repo.py
from __future__ import annotations
import datetime as dt

def load_guidelines(conn, academic_year: str) -> str:
    cur = conn.cursor()
    cur.execute("SELECT content_md FROM key_guidelines WHERE academic_year=?", (academic_year,))
    row = cur.fetchone()
    return row[0] if row and row[0] else ""

def save_guidelines(conn, academic_year: str, content: str) -> None:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO key_guidelines (academic_year, content_md, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(academic_year) DO UPDATE SET
            content=excluded.content,
            updated_at=excluded.updated_at
    """, (academic_year, content, dt.datetime.now().isoformat(timespec="seconds")))
    conn.commit()
