import sqlite3
import os

# ✅ Ensure DB is stored in the data folder
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)  # Auto-create data folder if missing

DB_FILE = os.path.join(DATA_DIR, "school.db")


def get_connection():
    """Return a SQLite connection compatible with Streamlit."""
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    """Initialize all tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE,
        student_name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT,
        class TEXT,
        section TEXT,
        student_phone TEXT,
        parent_phone TEXT
    )
    """)

    # Marks table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        subject TEXT,
        marks INTEGER,
        class TEXT,
        section TEXT,
        submitted_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Attendance table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        date TEXT,
        status TEXT,
        submitted_by TEXT,
        UNIQUE(student_id, date)
    )
    """)

    # Timetable table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT,
        section TEXT,
        day TEXT,
        period1 TEXT,
        period2 TEXT,
        period3 TEXT,
        period4 TEXT,
        period5 TEXT,
        period6 TEXT,
        period7 TEXT
    )
    """)

    conn.commit()
    conn.close()


def add_mark(student_id, subject, marks, submitted_by, student_class, section):
    """Insert a new mark record."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO marks (student_id, subject, marks, class, section, submitted_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, subject, marks, student_class, section, submitted_by))
    conn.commit()
    conn.close()


# ✅ Auto-init DB on import (for Streamlit Cloud)
init_db()

if __name__ == "__main__":
    print(f"✅ Database ready at: {DB_FILE}")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print("Tables in DB:", [row[0] for row in cur.fetchall()])
    conn.close()
