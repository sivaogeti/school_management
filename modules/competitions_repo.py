# modules/competitions_repo.py
from __future__ import annotations
import pandas as pd

DEFAULT_COLUMNS = ["MONTH", "COMPETITION / WORKSHOP", "THEME"]

def _conform_columns(df: pd.DataFrame) -> pd.DataFrame:
    # exactly 3 columns with our headers, string-typed & NaNs->""
    if df.shape[1] < 3:
        for _ in range(3 - df.shape[1]):
            df[f"COL{df.shape[1]+1}"] = ""
    df = df.iloc[:, :3].copy()
    df.columns = DEFAULT_COLUMNS
    for c in df.columns:
        df[c] = df[c].fillna("").astype(str)
    return df

def load_items(conn, academic_year: str) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute("""
        SELECT col1, col2, col3
        FROM competitions_enrichment
        WHERE academic_year=?
        ORDER BY row_order ASC
    """, (academic_year,))
    rows = cur.fetchall()
    if not rows:
        return pd.DataFrame(columns=DEFAULT_COLUMNS)
    df = pd.DataFrame(rows, columns=DEFAULT_COLUMNS)
    return _conform_columns(df)

def upsert_items(conn, academic_year: str, df: pd.DataFrame) -> None:
    df = _conform_columns(df).reset_index(drop=True)
    cur = conn.cursor()
    upsert_sql = """
        INSERT INTO competitions_enrichment
            (academic_year, row_order, col1, col2, col3)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(academic_year, row_order) DO UPDATE SET
            col1=excluded.col1,
            col2=excluded.col2,
            col3=excluded.col3
    """
    for i, row in df.iterrows():
        cur.execute(upsert_sql, (academic_year, i, row.iloc[0], row.iloc[1], row.iloc[2]))
    # trim removed rows
    cur.execute(
        "DELETE FROM competitions_enrichment WHERE academic_year=? AND row_order>=?",
        (academic_year, len(df))
    )
    conn.commit()

def clear_items(conn, academic_year: str) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM competitions_enrichment WHERE academic_year=?", (academic_year,))
    conn.commit()

# --- META (hero + title) ------------------------------------
def ensure_competitions_meta_schema(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS competitions_meta (
            academic_year TEXT PRIMARY KEY,
            table_title   TEXT,
            hero_heading  TEXT,
            hero_subtitle TEXT,
            bullet1       TEXT,
            bullet2       TEXT,
            bullet3       TEXT
        )
    """)
    conn.commit()
    

def _meta_cols(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(competitions_meta)")
    return {row[1] for row in cur.fetchall()}

def ensure_competitions_meta_columns(conn):
    # Backward-compatible: add any new columns if table existed earlier
    have = _meta_cols(conn)
    to_add = []
    for col, typ in [
        ("table_title","TEXT"),
        ("hero_heading","TEXT"),
        ("hero_subtitle","TEXT"),
        ("bullet1","TEXT"),
        ("bullet2","TEXT"),
        ("bullet3","TEXT"),
    ]:
        if col not in have:
            to_add.append((col, typ))
    if to_add:
        cur = conn.cursor()
        for col, typ in to_add:
            cur.execute(f"ALTER TABLE competitions_meta ADD COLUMN {col} {typ}")
        conn.commit()

def load_meta(conn, academic_year: str) -> dict:
    ensure_competitions_meta_schema(conn)
    ensure_competitions_meta_columns(conn)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_title, hero_heading, hero_subtitle, bullet1, bullet2, bullet3
        FROM competitions_meta WHERE academic_year=?
    """, (academic_year,))
    row = cur.fetchone()
    keys = ["table_title","hero_heading","hero_subtitle","bullet1","bullet2","bullet3"]
    if not row:
        return {k: "" for k in keys}
    return dict(zip(keys, row))

def save_meta(conn, academic_year: str, meta: dict) -> None:
    ensure_competitions_meta_schema(conn)
    ensure_competitions_meta_columns(conn)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO competitions_meta
            (academic_year, table_title, hero_heading, hero_subtitle, bullet1, bullet2, bullet3)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(academic_year) DO UPDATE SET
            table_title=excluded.table_title,
            hero_heading=excluded.hero_heading,
            hero_subtitle=excluded.hero_subtitle,
            bullet1=excluded.bullet1,
            bullet2=excluded.bullet2,
            bullet3=excluded.bullet3
    """, (
        academic_year,
        meta.get("table_title",""),
        meta.get("hero_heading",""),
        meta.get("hero_subtitle",""),
        meta.get("bullet1",""),
        meta.get("bullet2",""),
        meta.get("bullet3",""),
    ))
    conn.commit()
    

def load_title(conn, academic_year: str) -> str:
    cur = conn.cursor()
    cur.execute("SELECT title FROM competitions_meta WHERE academic_year=?", (academic_year,))
    row = cur.fetchone()
    return row[0] if row and row[0] else ""

def save_title(conn, academic_year: str, title: str) -> None:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO competitions_meta (academic_year, title)
        VALUES (?, ?)
        ON CONFLICT(academic_year) DO UPDATE SET title=excluded.title
    """, (academic_year, title))
    conn.commit()
