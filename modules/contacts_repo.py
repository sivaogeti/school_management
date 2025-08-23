# modules/contacts_repo.py
from __future__ import annotations
import pandas as pd

COLUMNS = [
    "order_no","category","title","contact_name","designation",
    "phone_primary","phone_alt","notes","is_active"
]

def load_contacts(conn) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute("""
        SELECT order_no, category, title, contact_name, designation,
               phone_primary, phone_alt, COALESCE(notes,''), is_active
        FROM contacts_directory
        WHERE is_active=1
        ORDER BY order_no ASC, id ASC
    """)
    rows = cur.fetchall()
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(rows, columns=COLUMNS)

def load_contacts_admin(conn) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute("""
        SELECT order_no, category, title, contact_name, designation,
               phone_primary, phone_alt, COALESCE(notes,''), is_active
        FROM contacts_directory
        ORDER BY order_no ASC, id ASC
    """)
    rows = cur.fetchall()
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(rows, columns=COLUMNS)

def upsert_contacts(conn, df: pd.DataFrame):
    df = df.fillna("")
    if "is_active" in df.columns:
        df["is_active"] = df["is_active"].apply(lambda x: 1 if str(x).strip().lower() not in ("0","false","no") else 0)
    else:
        df["is_active"] = 1

    cur = conn.cursor()
    # easiest: clear and insert (one-time data, tiny size)
    cur.execute("DELETE FROM contacts_directory")
    insert_sql = """
        INSERT INTO contacts_directory
        (order_no, category, title, contact_name, designation,
         phone_primary, phone_alt, notes, is_active)
        VALUES (?,?,?,?,?,?,?,?,?)
    """
    for _, r in df.iterrows():
        cur.execute(insert_sql, (
            int(r.get("order_no") or 0),
            r.get("category",""), r.get("title",""),
            r.get("contact_name",""), r.get("designation",""),
            r.get("phone_primary",""), r.get("phone_alt",""),
            r.get("notes",""), int(r.get("is_active") or 1)
        ))
    conn.commit()
