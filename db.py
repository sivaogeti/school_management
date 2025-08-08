import sqlite3
import os
import hashlib
import random
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "school.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


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

    # Marks
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

    # Attendance
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

    # Timetable
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

    # Notices
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Fees
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT UNIQUE,
        total_fee REAL
    )
    """)

    # Payments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        amount REAL,
        date TEXT DEFAULT CURRENT_TIMESTAMP,
        method TEXT
    )
    """)

    # Assignments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT,
        section TEXT,
        subject TEXT,
        description TEXT,
        due_date TEXT,
        assigned_by TEXT
    )
    """)

    # Exam Schedule
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT,
        section TEXT,
        subject TEXT,
        exam_date TEXT,
        exam_time TEXT,
        exam_type TEXT,
        assigned_by TEXT
    )
    """)


    # Add these inside init_db() in db.py after existing table creations

    # Subjects Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT,
        section TEXT,
        subject_name TEXT
    )
    """)

    # WhatsApp Logs
    cur.execute("""
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
    
    # Inside init_db() in db.py after other table creations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id TEXT,
        receiver_id TEXT,
        sender_role TEXT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP        
    )
    """)
    
    # Notices table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            message TEXT,
            class TEXT,
            section TEXT,
            created_by TEXT,
            expiry_date TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    
    conn.commit()
    conn.close()


# -------------------------
# Helper Functions
# -------------------------
def add_mark(student_id, subject, marks, submitted_by, class_name, section):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO marks(student_id, subject, marks, class, section, submitted_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, subject, marks, class_name, section, submitted_by))
    conn.commit()
    conn.close()


def add_payment(student_id, amount, method="Cash"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO payments(student_id, amount, method)
        VALUES (?, ?, ?)
    """, (student_id, amount, method))
    conn.commit()
    conn.close()


# -------------------------
# Auto-seeding Functions
# -------------------------
def seed_default_fees():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM fees")
    if cur.fetchone()[0] == 0:
        for cls in range(1, 11):
            total_fee = 10000 + cls * 500
            cur.execute("INSERT INTO fees(class, total_fee) VALUES (?, ?)", (str(cls), total_fee))
        conn.commit()
        print("✅ Default fee structure created for Classes 1–10.")
    conn.close()


def seed_sample_students():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE role='Student'")
    if cur.fetchone()[0] == 0:
        for cls in range(1, 11):
            for sec in ["A", "B"]:
                for idx in range(1, 6):
                    student_id = f"S{cls}{sec}{idx:02d}"
                    student_name = f"Student_{cls}{sec}{idx:02d}"
                    email = f"{student_id.lower()}@school.com"
                    password = hashlib.sha256("student123".encode()).hexdigest()

                    cur.execute("""
                        INSERT INTO users
                        (student_id, student_name, email, password, role, class, section, student_phone, parent_phone)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        student_id, student_name, email, password, "Student",
                        str(cls), sec, f"9000000{idx:03d}", f"9001000{idx:03d}"
                    ))
        conn.commit()
        print("✅ Sample students created for Classes 1–10 (Sections A & B).")
    conn.close()


def seed_default_users():
    conn = get_connection()
    cur = conn.cursor()

    # Admin
    cur.execute("SELECT COUNT(*) FROM users WHERE role='Admin'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO users (student_id, student_name, email, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            None, "Admin User", "admin@school.com",
            hashlib.sha256("admin123".encode()).hexdigest(),
            "Admin"
        ))
        print("✅ Default Admin created: admin@school.com / admin123")

    # Teachers
    cur.execute("SELECT COUNT(*) FROM users WHERE role='Teacher'")
    if cur.fetchone()[0] == 0:
        for idx in range(1, 4):
            email = f"teacher{idx}@school.com"
            cur.execute("""
                INSERT INTO users (student_id, student_name, email, password, role, class, section)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                None, f"Teacher {idx}", email,
                hashlib.sha256("teacher123".encode()).hexdigest(),
                "Teacher", str(idx), "A"
            ))
        print("✅ 3 Default Teachers created: teacher1@school.com / teacher123 etc.")

    conn.commit()
    conn.close()


def seed_random_marks_attendance_payments():
    conn = get_connection()
    cur = conn.cursor()

    subjects = ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]
    cur.execute("SELECT student_id, class, section FROM users WHERE role='Student'")
    students = cur.fetchall()

    for sid, cls, sec in students:
        # Random marks for 3 subjects
        for subj in random.sample(subjects, 3):
            cur.execute("""
                INSERT OR IGNORE INTO marks(student_id, subject, marks, class, section, submitted_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sid, subj, random.randint(40, 100), cls, sec, "auto_seed"))

        # Attendance for last 5 days
        for i in range(5):
            date_str = (datetime.today() - timedelta(days=i)).strftime("%Y-%m-%d")
            status = random.choice(["Present", "Absent", "Late"])
            cur.execute("""
                INSERT OR IGNORE INTO attendance(student_id, date, status, submitted_by)
                VALUES (?, ?, ?, ?)
            """, (sid, date_str, status, "auto_seed"))

        # Partial payment
        cur.execute("""
            INSERT INTO payments(student_id, amount, method)
            VALUES (?, ?, ?)
        """, (sid, random.randint(1000, 5000), random.choice(["Cash", "UPI", "Bank Transfer"])))

    conn.commit()
    conn.close()
    print("✅ Random marks, attendance, and payments seeded.")


def seed_notices_and_timetable():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM notices")
    if cur.fetchone()[0] == 0:
        for msg in ["Welcome back to school!", "PTM this Saturday", "Submit homework on time"]:
            cur.execute("INSERT INTO notices(message) VALUES (?)", (msg,))
        print("✅ Notices seeded.")

    cur.execute("SELECT COUNT(*) FROM timetable")
    if cur.fetchone()[0] == 0:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        periods = ["Telugu", "English", "Maths", "Science", "Social", "Games", "Library"]
        for cls in range(1, 4):
            for sec in ["A", "B"]:
                for day in days:
                    row = random.sample(periods, 7)
                    cur.execute("""
                        INSERT INTO timetable(class, section, day, period1, period2, period3, period4, period5, period6, period7)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (str(cls), sec, day, *row))
        print("✅ Timetable seeded.")

    conn.commit()
    conn.close()


def seed_assignments_and_exams():
    conn = get_connection()
    cur = conn.cursor()

    # Assignments
    cur.execute("SELECT COUNT(*) FROM assignments")
    if cur.fetchone()[0] == 0:
        for cls in range(1, 4):
            for sec in ["A", "B"]:
                for subj in ["English", "Maths", "Science"]:
                    due_date = (datetime.today() + timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d")
                    cur.execute("""
                        INSERT INTO assignments(class, section, subject, description, due_date, assigned_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (str(cls), sec, subj, f"{subj} Homework", due_date, f"teacher{cls}@school.com"))
        print("✅ Assignments seeded.")

    # Exams
    cur.execute("SELECT COUNT(*) FROM exam_schedule")
    if cur.fetchone()[0] == 0:
        for cls in range(1, 4):
            for sec in ["A", "B"]:
                for subj in ["English", "Maths", "Science"]:
                    exam_date = (datetime.today() + timedelta(days=random.randint(3, 10))).strftime("%Y-%m-%d")
                    exam_time = random.choice(["09:00 AM", "11:00 AM"])
                    exam_type = random.choice(["Unit Test", "Midterm"])
                    cur.execute("""
                        INSERT INTO exam_schedule(class, section, subject, exam_date, exam_time, exam_type, assigned_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (str(cls), sec, subj, exam_date, exam_time, exam_type, f"teacher{cls}@school.com"))
        print("✅ Exam schedule seeded.")

    conn.commit()
    conn.close()

def seed_default_subjects():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subjects")
    if cur.fetchone()[0] == 0:
        default = ["Telugu","Hindi","English","Maths","Science","Social"]
        for cls in range(1, 11):
            for sec in ["A","B"]:
                for s in default:
                    cur.execute("INSERT INTO subjects (class, section, subject_name) VALUES (?, ?, ?)", (str(cls), sec, s))
        conn.commit()
    conn.close()

def create_notice(title, message, class_name, section, created_by, expiry_date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO notices (title, message, class, section, created_by, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, message, class_name, section, created_by, expiry_date))
    conn.commit()
    conn.close()




# -------------------------
# Initialize DB & Seed All
# -------------------------
if not os.path.exists(DB_PATH):
    open(DB_PATH, "w").close()

init_db()
seed_default_fees()
seed_sample_students()
seed_default_users()
seed_random_marks_attendance_payments()
seed_notices_and_timetable()
seed_assignments_and_exams()
seed_default_subjects()