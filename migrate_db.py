# migrate_db.py
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "data", "school.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def table_has_column(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols

def ensure_table(cur, sql):
    cur.execute(sql)

def safe_add_column(cur, table, column_defs):
    # column_defs is list of (colname, sql_type_and_constraints)
    cur.execute(f"PRAGMA table_info({table})")
    existing = {r[1] for r in cur.fetchall()}
    for col, coldef in column_defs:
        if col not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")

def main():
    if not os.path.exists(DB_PATH):
        print("DB file not found. Create DB first by running your app once.")
        return

    conn = get_conn()
    cur = conn.cursor()

    # === 1) New/updated tables (CREATE IF NOT EXISTS) ===
    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_email TEXT,
        receiver_email TEXT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS whatsapp_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        phone_number TEXT,
        message TEXT,
        status TEXT,
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT,
        section TEXT,
        subject_name TEXT
    )
    """)

    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        title TEXT,
        description TEXT,
        date TEXT,
        issued_by TEXT
    )
    """)

    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS homework (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT,
        section TEXT,
        subject TEXT,
        description TEXT,
        due_date TEXT,
        file_url TEXT,
        assigned_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS syllabus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT,
        section TEXT,
        subject TEXT,
        syllabus_text TEXT,
        file_url TEXT,
        uploaded_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        image_url TEXT,
        category TEXT,
        uploaded_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        from_date TEXT,
        to_date TEXT,
        reason TEXT,
        status TEXT DEFAULT 'Pending',
        reviewed_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        date TEXT,
        target_audience TEXT, -- e.g. 'All' or 'Class:5' or 'Class:5:Section:A'
        created_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS digital_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        file_url TEXT,
        content_type TEXT,
        target_class TEXT,
        uploaded_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # === 2) Expand notices table with richer fields if missing ===
    # - if notices doesn't exist, create it newly
    ensure_table(cur, """
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        message TEXT,
        created_by TEXT,
        class TEXT,
        section TEXT,
        expiry_date TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # If older notices table existed without columns, ALTER won't work with IF NOT EXISTS,
    # so only add missing columns (safe).
    # (This uses ALTER TABLE ADD COLUMN which SQLite supports.)
    try:
        safe_add_column(cur, "notices", [
            ("title", "TEXT"),
            ("created_by", "TEXT"),
            ("class", "TEXT"),
            ("section", "TEXT"),
            ("expiry_date", "TEXT")
        ])
    except Exception as e:
        print("Couldn't ALTER notices table:", e)

    # === 3) Subjects default seed (only if empty) ===
    cur.execute("SELECT COUNT(*) FROM subjects")
    if cur.fetchone()[0] == 0:
        default = ["Telugu","Hindi","English","Maths","Science","Social"]
        for cls in range(1, 13):
            for sec in ["A","B"]:
                for s in default:
                    cur.execute("INSERT INTO subjects (class, section, subject_name) VALUES (?, ?, ?)",
                                (str(cls), sec, s))

    # === 4) Seed achievements/homework/syllabus sample (optional small sample) ===
    cur.execute("SELECT COUNT(*) FROM achievements")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO achievements (student_id, title, description, date, issued_by) VALUES (?, ?, ?, ?, ?)",
                    ("S1A01", "Excellent Attendance", "Perfect attendance for July", datetime.now().strftime("%Y-%m-%d"), "Admin"))

    # commit and close
    conn.commit()
    conn.close()
    print("✅ Migration complete. Database updated safely.")

if __name__ == "__main__":
    main()
