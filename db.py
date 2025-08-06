import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "school.db")


def get_connection():
    return sqlite3.connect(DB_FILE)


def init_db():
    conn = sqlite3.connect(DB_FILE)
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

    # ✅ Timetable table
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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO marks (student_id, subject, marks, class, section, submitted_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, subject, marks, student_class, section, submitted_by))
    conn.commit()
    conn.close()


# Optional: Initialize DB on import
if __name__ == "__main__":
    init_db()
