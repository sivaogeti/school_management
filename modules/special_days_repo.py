# modules/special_days_repo.py
from __future__ import annotations
import pandas as pd

DEFAULT_COLUMNS = ["DATE", "DAY", "EXAMS", "SPECIAL DAYS", "CELEBRATION", "HOLIDAYS"]

def _conform_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Force EXACTLY the 6 PDF headers in this order
    if df.shape[1] < 6:
        for _ in range(6 - df.shape[1]):
            df[f"COL{df.shape[1]+1}"] = ""
    df = df.iloc[:, :6].copy()
    df.columns = DEFAULT_COLUMNS
    for c in df.columns:
        df[c] = df[c].fillna("").astype(str)
    return df


def load_month_df(conn, month: str, year: int) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(
        "SELECT col1, col2, col3, col4, col5, col6 "
        "FROM special_days WHERE month=? AND year=? ORDER BY row_order ASC",
        (month, year),
    )
    rows = cur.fetchall()
    if not rows:
        return pd.DataFrame(columns=DEFAULT_COLUMNS)
    df = pd.DataFrame(rows, columns=DEFAULT_COLUMNS)
    return _conform_columns(df)

def upsert_month_df(conn, month: str, year: int, df: pd.DataFrame) -> None:
    df = _conform_columns(df).reset_index(drop=True)
    cur = conn.cursor()
    upsert_sql = """
    INSERT INTO special_days (month, year, row_order, col1, col2, col3, col4, col5, col6)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(month, year, row_order) DO UPDATE SET
        col1=excluded.col1,
        col2=excluded.col2,
        col3=excluded.col3,
        col4=excluded.col4,
        col5=excluded.col5,
        col6=excluded.col6
    """
    for i, row in df.iterrows():
        cur.execute(
            upsert_sql,
            (month, year, i, row.iloc[0], row.iloc[1], row.iloc[2], row.iloc[3], row.iloc[4], row.iloc[5]),
        )
    # trim deleted rows
    cur.execute(
        "DELETE FROM special_days WHERE month=? AND year=? AND row_order>=?",
        (month, year, len(df)),
    )
    conn.commit()

def clear_month(conn, month: str, year: int) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM special_days WHERE month=? AND year=?", (month, year))
    conn.commit()

