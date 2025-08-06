import sqlite3
import os

# ✅ Always use absolute path for Streamlit Cloud
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "school.db")


def get_connection():
    """Return a SQLite connection compatible with Streamlit."""
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
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

    # ✅ Ensure a default admin user exists
    cur.execute("SELECT COUNT(*) FROM users WHERE role='Admin'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
        INSERT INTO users (student_id, student_name, email, password, role)
        VALUES (NULL, 'Administrator', 'admin@school.com', 'admin123', 'Admin')
        """)
        print("✅ Default admin user created: admin@school.com / admin123")

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


# ✅ Auto-init DB and print debug info on import
init_db()
print(f"✅ Database initialized at: {DB_FILE}")

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("✅ Tables in DB:", [row[0] for row in cur.fetchall()])
conn.close()
