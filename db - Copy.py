# db.py
# Merged: original legacy schema (keeps all original tables) +
# Fully-normalized multi-tenant schema (new *_mt tables + schools/classes)
# Seeds demo data into both legacy and normalized tables so nothing looks missing.

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
    conn = sqlite3.connect(DB_PATH)
    # enforce foreign keys for normalized tables
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # ------------------------
    # LEGACY TABLES (unchanged)
    # ------------------------
    # Users table (legacy)
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

    # Marks (legacy)
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

    # Attendance (legacy)
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

    # Notices (legacy — detailed)
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

    # Fees (legacy)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT UNIQUE,
        total_fee REAL
    )
    """)

    # Payments (legacy)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        amount REAL,
        date TEXT DEFAULT CURRENT_TIMESTAMP,
        method TEXT
    )
    """)

    # Assignments (legacy)
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

    # Exam Schedule (legacy)
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

    # Subjects (legacy)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT,
        section TEXT,
        subject_name TEXT
    )
    """)

    # WhatsApp Logs (legacy)
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

    # messages (legacy)
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

    # Homework (legacy)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class TEXT NOT NULL,
            section TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            file_url TEXT,
            assigned_by TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Syllabus (legacy)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS syllabus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class TEXT NOT NULL,
            section TEXT NOT NULL,
            subject TEXT NOT NULL,
            syllabus_text TEXT,
            file_url TEXT,
            uploaded_by TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Gallery (legacy)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            image_url TEXT,
            category TEXT,
            uploaded_by TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Optional indices (legacy)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_homework_class_section ON homework (class, section)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_syllabus_class_section ON syllabus (class, section)
    """)

    # Achievements (legacy)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            title TEXT,
            description TEXT,
            date TEXT,
            issued_by TEXT
        )
    """)

    # Calendar events (legacy)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            date TEXT,
            target_audience TEXT,
            created_by TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Digital content (legacy)
    cur.execute("""
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

    # Leave requests (legacy)
    cur.execute("""
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

    # Transport legacy
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transport_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT,
            driver_name TEXT,
            driver_contact TEXT,
            vehicle_number TEXT,
            stops TEXT,
            timing TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS student_transport (
            student_id TEXT,
            route_id INTEGER,
            pickup_point TEXT,
            drop_point TEXT
        )
    """)

    # Communication legacy (recipient_group variant)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages_legacy_recipient (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id TEXT,
        recipient_group TEXT,
        message TEXT,
        attachment_path TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Library (legacy)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS library_books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        author TEXT,
        isbn TEXT,
        status TEXT,
        location TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS library_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER,
        student_id TEXT,
        issue_date TEXT,
        due_date TEXT,
        return_date TEXT
    )
    """)

    # School config (legacy)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS school_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Visitor log & enquiries (legacy)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS visitor_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        purpose TEXT,
        in_time TEXT,
        out_time TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS enquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        contact TEXT,
        query TEXT,
        follow_up_date TEXT
    )
    """)

    # Website pages (legacy)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS website_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_name TEXT,
        content_html TEXT,
        last_updated TEXT
    )
    """)

    # Assignments (legacy duplicate kept earlier; keep also a generic one)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assignments_generic (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        subject TEXT,
        class TEXT,
        section TEXT,
        file_path TEXT,
        due_date TEXT
    )
    """)

    # Student health (legacy)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS student_health (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        student_name TEXT,
        blood_group TEXT,
        height REAL,
        weight REAL,
        notes TEXT,
        doctor_name TEXT,
        checkup_date TEXT
    )
    """)

    # Admissions (legacy)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        student_name TEXT,
        dob TEXT,
        contact TEXT,
        applied_class TEXT,
        status TEXT,
        date_applied TEXT,
        documents_path TEXT
    )
    """)

    # Exams (legacy)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_schedule_legacy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class TEXT,
            section TEXT,
            subject TEXT,
            date TEXT,
            time TEXT,
            max_marks INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_results_legacy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            subject TEXT,
            marks INTEGER,
            grade TEXT
        )
    """)

    # Staff legacy
    cur.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        role TEXT,
        phone TEXT,
        email TEXT,
        join_date TEXT
    )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER,
            date TEXT,
            status TEXT
        )
    """)

    # Principal notes (legacy)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS principal_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ------------------------
    # NORMALIZED / MULTI-TENANT TABLES
    # (new tables for future / multi-school)
    # ------------------------
    # Schools (multi-tenant root)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS schools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        address TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Classes normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER NOT NULL,
        class_name TEXT NOT NULL,
        section TEXT,
        UNIQUE(school_id, class_name, section),
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)

    # Subjects normalized (per school/class optionally)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subjects_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        class_id INTEGER,
        subject_name TEXT NOT NULL,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE
    )
    """)

    # Users normalized (multi-tenant)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER NOT NULL,
        class_id INTEGER,
        business_id TEXT UNIQUE,
        student_id TEXT,      -- optional legacy string
        full_name TEXT,
        role TEXT NOT NULL,
        email TEXT UNIQUE,
        password TEXT,
        phone TEXT,
        parent_phone TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE SET NULL
    )
    """)

    # Fees normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fees_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        total_fee REAL,
        UNIQUE(school_id, class_id),
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE
    )
    """)

    # Marks normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS marks_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        student_fk INTEGER,
        legacy_student_id TEXT,
        subject_id INTEGER,
        subject TEXT,
        marks INTEGER,
        submitted_by_fk INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(subject_id) REFERENCES subjects_mt(id) ON DELETE SET NULL,
        FOREIGN KEY(submitted_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    # Attendance normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        student_fk INTEGER,
        legacy_student_id TEXT,
        date TEXT NOT NULL,
        status TEXT,
        submitted_by_fk INTEGER,
        UNIQUE(student_fk, date),
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(submitted_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    # Payments normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        student_fk INTEGER,
        legacy_student_id TEXT,
        amount REAL,
        date TEXT DEFAULT CURRENT_TIMESTAMP,
        method TEXT,
        recorded_by_fk INTEGER,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(recorded_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    # Assignments / Homework / syllabus normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assignments_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        class_id INTEGER,
        subject_id INTEGER,
        title TEXT,
        description TEXT,
        file_path TEXT,
        due_date TEXT,
        assigned_by_fk INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(subject_id) REFERENCES subjects_mt(id) ON DELETE SET NULL,
        FOREIGN KEY(assigned_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS homework_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        class_id INTEGER,
        subject_id INTEGER,
        description TEXT,
        due_date TEXT,
        file_url TEXT,
        assigned_by_fk INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(subject_id) REFERENCES subjects_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(assigned_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS syllabus_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        class_id INTEGER,
        subject_id INTEGER,
        syllabus_text TEXT,
        file_url TEXT,
        uploaded_by_fk INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(subject_id) REFERENCES subjects_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(uploaded_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    # Gallery normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gallery_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        title TEXT NOT NULL,
        image_url TEXT,
        category TEXT,
        uploaded_by_fk INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(uploaded_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    # Notices normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notices_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        class_id INTEGER,
        title TEXT,
        message TEXT,
        created_by_fk INTEGER,
        expiry_date TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(created_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    # Exams normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS examinations_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        date TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_schedule_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        class_id INTEGER,
        subject_id INTEGER,
        exam_date TEXT,
        exam_time TEXT,
        exam_type TEXT,
        assigned_by_fk INTEGER,
        FOREIGN KEY(exam_id) REFERENCES examinations_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(subject_id) REFERENCES subjects_mt(id) ON DELETE SET NULL,
        FOREIGN KEY(assigned_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_results_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER,
        student_fk INTEGER,
        subject_id INTEGER,
        subject TEXT,
        marks INTEGER,
        grade TEXT,
        FOREIGN KEY(exam_id) REFERENCES examinations_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(subject_id) REFERENCES subjects_mt(id) ON DELETE SET NULL
    )
    """)

    # Achievements / calendar / digital content normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS achievements_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        student_fk INTEGER,
        title TEXT,
        description TEXT,
        date TEXT,
        issued_by_fk INTEGER,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(issued_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS calendar_events_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        title TEXT,
        description TEXT,
        date TEXT,
        target_audience TEXT,
        created_by_fk INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(created_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS digital_content_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        title TEXT,
        description TEXT,
        file_url TEXT,
        content_type TEXT,
        target_class_id INTEGER,
        uploaded_by_fk INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(target_class_id) REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(uploaded_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    # Leave requests normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leave_requests_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        student_fk INTEGER,
        from_date TEXT,
        to_date TEXT,
        reason TEXT,
        status TEXT DEFAULT 'Pending',
        reviewed_by_fk INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(reviewed_by_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    # Transport normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transport_routes_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        route_name TEXT,
        driver_name TEXT,
        driver_contact TEXT,
        vehicle_number TEXT,
        stops TEXT,
        timing TEXT,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS student_transport_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        student_fk INTEGER,
        route_id INTEGER,
        pickup_point TEXT,
        drop_point TEXT,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(route_id) REFERENCES transport_routes_mt(id) ON DELETE SET NULL
    )
    """)

    # Communication normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        sender_fk INTEGER,
        receiver_fk INTEGER,
        sender_role TEXT,
        message TEXT,
        attachment_path TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(sender_fk) REFERENCES users_mt(id) ON DELETE SET NULL,
        FOREIGN KEY(receiver_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS whatsapp_logs_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        student_fk INTEGER,
        phone_number TEXT,
        message TEXT,
        status TEXT,
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE
    )
    """)

    # Library normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS library_books_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        title TEXT,
        author TEXT,
        isbn TEXT,
        status TEXT,
        location TEXT,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS library_issues_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        book_id INTEGER,
        student_fk INTEGER,
        issue_date TEXT,
        due_date TEXT,
        return_date TEXT,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(book_id) REFERENCES library_books_mt(id) ON DELETE SET NULL,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE
    )
    """)

    # Student health & admissions normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS student_health_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        student_fk INTEGER,
        student_name TEXT,
        blood_group TEXT,
        height REAL,
        weight REAL,
        notes TEXT,
        doctor_name TEXT,
        checkup_date TEXT,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admissions_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        student_fk INTEGER,
        student_name TEXT,
        dob TEXT,
        contact TEXT,
        applied_class_id INTEGER,
        status TEXT,
        date_applied TEXT,
        documents_path TEXT,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(student_fk) REFERENCES users_mt(id) ON DELETE CASCADE,
        FOREIGN KEY(applied_class_id) REFERENCES classes(id) ON DELETE SET NULL
    )
    """)

    # Website / settings / principal notes normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS website_pages_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        page_name TEXT,
        content_html TEXT,
        last_updated TEXT,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS school_settings_mt (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS principal_notes_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        note TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)

    # Timetable normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS timetable_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        class_id INTEGER,
        day TEXT,
        period INTEGER,
        subject_id INTEGER,
        subject TEXT,
        teacher_fk INTEGER,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(subject_id) REFERENCES subjects_mt(id) ON DELETE SET NULL,
        FOREIGN KEY(teacher_fk) REFERENCES users_mt(id) ON DELETE SET NULL
    )
    """)

    # Staff normalized
    cur.execute("""
    CREATE TABLE IF NOT EXISTS staff_mt (
        staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER,
        name TEXT,
        role TEXT,
        phone TEXT,
        email TEXT,
        join_date TEXT,
        FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS staff_attendance_mt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_id INTEGER,
        date TEXT,
        status TEXT,
        FOREIGN KEY(staff_id) REFERENCES staff_mt(staff_id) ON DELETE CASCADE
    )
    """)

    # ------------------------
    # Indexes to speed common lookups
    # ------------------------
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_legacy_student_id ON users(student_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_mt_business_id ON users_mt(business_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_mt_school ON users_mt(school_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_classes_school ON classes(school_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_subjects_mt_school ON subjects_mt(school_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_marks_mt_student ON marks_mt(student_fk);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_mt_student ON attendance_mt(student_fk);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_mt_student ON payments_mt(student_fk);")

    conn.commit()
    conn.close()


# -------------------------
# Helpers
# -------------------------
def hash_pw(plain):
    return hashlib.sha256(plain.encode()).hexdigest()


# Convenience to get id by business id in normalized users
def get_mt_user_id(cur, business_id):
    cur.execute("SELECT id FROM users_mt WHERE business_id = ?", (business_id,))
    r = cur.fetchone()
    return r[0] if r else None


# -------------------------
# Demo seeding
# -------------------------
def seed_demo():
    conn = get_connection()
    cur = conn.cursor()

    # --- create Demo School in normalized table if missing
    cur.execute("SELECT id FROM schools WHERE name = ?", ("Demo School",))
    row = cur.fetchone()
    if row:
        school_id = row[0]
    else:
        cur.execute("INSERT INTO schools(name, address) VALUES (?, ?)", ("Demo School", "Demo Address"))
        school_id = cur.lastrowid

    # --- create normalized classes 1..3 A,B
    cur.execute("SELECT COUNT(*) FROM classes WHERE school_id = ?", (school_id,))
    if cur.fetchone()[0] == 0:
        for cls in range(1, 4):
            for sec in ("A", "B"):
                cur.execute("INSERT INTO classes(school_id, class_name, section) VALUES (?, ?, ?)",
                            (school_id, str(cls), sec))

    # --- create subjects_mt per class
    cur.execute("SELECT COUNT(*) FROM subjects_mt WHERE school_id = ?", (school_id,))
    if cur.fetchone()[0] == 0:
        default_subjects = ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]
        cur.execute("SELECT id FROM classes WHERE school_id = ?", (school_id,))
        class_rows = cur.fetchall()
        for (cid,) in class_rows:
            for sub in default_subjects:
                cur.execute("INSERT INTO subjects_mt(school_id, class_id, subject_name) VALUES (?, ?, ?)",
                            (school_id, cid, sub))

    # --- seed legacy subjects table to mirror (so legacy code sees subjects)
    cur.execute("SELECT COUNT(*) FROM subjects")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT class_name, section FROM classes WHERE school_id = ?", (school_id,))
        for class_name, section in cur.fetchall():
            for sub in ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]:
                cur.execute("INSERT INTO subjects (class, section, subject_name) VALUES (?, ?, ?)",
                            (class_name, section, sub))

    # --- create legacy users and normalized users_mt
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'Student'")
    legacy_students_missing = cur.fetchone()[0] == 0

    cur.execute("SELECT COUNT(*) FROM users_mt WHERE role = 'Student' OR role = 'Teacher' OR role = 'Admin'")
    mt_users_count = cur.fetchone()[0]

    if legacy_students_missing or mt_users_count == 0:
        # pick one class id to assign students (first)
        cur.execute("SELECT id, class_name, section FROM classes WHERE school_id = ? ORDER BY id LIMIT 1", (school_id,))
        first = cur.fetchone()
        if first:
            first_class_id, first_class_name, first_section = first
        else:
            first_class_id, first_class_name, first_section = None, "1", "A"

        # Legacy: insert sample students into old 'users' table and normalized 'users_mt'
        for cls_row in cur.execute("SELECT id, class_name, section FROM classes WHERE school_id = ?", (school_id,)).fetchall():
            cid, clsname, sec = cls_row
            for idx in range(1, 6):  # 5 students per class
                legacy_student_id = f"S{clsname}{sec}{idx:02d}"
                legacy_student_name = f"Student_{clsname}{sec}{idx:02d}"
                legacy_email = f"{legacy_student_id.lower()}@school.com"
                legacy_pw = hash_pw("student123")

                # insert into legacy users (if not exists)
                cur.execute("SELECT id FROM users WHERE student_id = ?", (legacy_student_id,))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO users (student_id, student_name, email, password, role, class, section, student_phone, parent_phone)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (legacy_student_id, legacy_student_name, legacy_email, legacy_pw, "Student", clsname, sec,
                          f"9000000{idx:03d}", f"9001000{idx:03d}"))

                # insert into normalized users_mt
                cur.execute("SELECT id FROM users_mt WHERE business_id = ?", (legacy_student_id,))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO users_mt (school_id, class_id, business_id, student_id, full_name, role, email, password, phone, parent_phone)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (school_id, cid, legacy_student_id, legacy_student_id, legacy_student_name, "Student",
                          legacy_email, legacy_pw, f"9000000{idx:03d}", f"9001000{idx:03d}"))

        # Teachers (3) and Admin (1)
        for t in range(1, 4):
            biz = f"T{t:02d}"
            name = f"Teacher {t}"
            email = f"teacher{t}@demo.com"
            pw = hash_pw("teacher123")

            # legacy users
            cur.execute("SELECT id FROM users WHERE email = ?", (email,))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (student_id, student_name, email, password, role, class, section)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (None, name, email, pw, "Teacher", "N/A", "N/A"))

            # normalized users_mt
            cur.execute("SELECT id FROM users_mt WHERE business_id = ?", (biz,))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users_mt (school_id, business_id, full_name, role, email, password, phone)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (school_id, biz, name, "Teacher", email, pw, f"9002000{t:03d}"))

        # admin
        admin_email = "admin@demo.com"
        admin_pw = hash_pw("admin123")
        cur.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO users (student_id, student_name, email, password, role)
                VALUES (?, ?, ?, ?, ?)
            """, (None, "Admin User", admin_email, admin_pw, "Admin"))
        cur.execute("SELECT id FROM users_mt WHERE business_id = ?", ("ADMIN01",))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO users_mt (school_id, business_id, full_name, role, email, password)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (school_id, "ADMIN01", "Admin User", "Admin", admin_email, admin_pw))

    # --- seed marks/attendance/payments into both legacy and mt tables
    cur.execute("SELECT id, business_id FROM users_mt WHERE role = 'Student' AND school_id = ?", (school_id,))
    mt_students = cur.fetchall()
    subjects_all = ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]

    for biz_id, mt_id in mt_students:
        # normalized marks/attendance/payments
        for subj in random.sample(subjects_all, 3):
            cur.execute("INSERT INTO marks_mt (school_id, student_fk, subject, marks) VALUES (?, ?, ?, ?)",
                        (school_id, mt_id, subj, random.randint(40, 100)))
        for i in range(5):
            date_str = (datetime.today() - timedelta(days=i)).strftime("%Y-%m-%d")
            cur.execute("INSERT OR IGNORE INTO attendance_mt (school_id, student_fk, date, status) VALUES (?, ?, ?, ?)",
                        (school_id, mt_id, date_str, random.choice(["Present", "Absent", "Late"])))
        cur.execute("INSERT INTO payments_mt (school_id, student_fk, amount, method) VALUES (?, ?, ?, ?)",
                    (school_id, mt_id, random.randint(1000, 5000), random.choice(["Cash", "UPI", "Bank Transfer"])))

        # legacy marks/attendance/payments: attempt to find legacy student_id
        cur.execute("SELECT student_id, id FROM users WHERE student_id = ?", (biz_id,))
        r = cur.fetchone()
        if r:
            legacy_student_id = r[0]
            # legacy marks
            for subj in random.sample(subjects_all, 3):
                cur.execute("INSERT INTO marks (student_id, subject, marks, class, section, submitted_by) VALUES (?, ?, ?, ?, ?, ?)",
                            (legacy_student_id, subj, random.randint(40, 100), "N/A", "N/A", "auto_seed"))
            # legacy attendance
            for i in range(5):
                date_str = (datetime.today() - timedelta(days=i)).strftime("%Y-%m-%d")
                cur.execute("INSERT OR IGNORE INTO attendance (student_id, date, status, submitted_by) VALUES (?, ?, ?, ?)",
                            (legacy_student_id, date_str, random.choice(["Present", "Absent", "Late"]), "auto_seed"))
            # legacy payment
            cur.execute("INSERT INTO payments (student_id, amount, method) VALUES (?, ?, ?)",
                        (legacy_student_id, random.randint(1000, 5000), random.choice(["Cash", "UPI", "Bank Transfer"])))

    # --- seed a few notices (both legacy and normalized)
    cur.execute("SELECT COUNT(*) FROM notices")
    if cur.fetchone()[0] == 0:
        legacy_notices = [
            ("Welcome back to school!", "Welcome back to school!", None, None, "System"),
            ("PTM this Saturday", "Parent Teacher Meeting Saturday 10 AM", None, None, "System"),
            ("Submit homework on time", "Please submit homework on time.", None, None, "System")
        ]
        for title, msg, cls, sec, by in legacy_notices:
            cur.execute("INSERT INTO notices (title, message, class, section, created_by, expiry_date, timestamp) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                        (title, msg, cls, sec, by, None))

    cur.execute("SELECT COUNT(*) FROM notices_mt WHERE school_id = ?", (school_id,))
    if cur.fetchone()[0] == 0:
        for title, msg, _, _, by in legacy_notices:
            # find admin in users_mt if present
            cur.execute("SELECT id FROM users_mt WHERE role = 'Admin' AND school_id = ?", (school_id,))
            admin_row = cur.fetchone()
            admin_fk = admin_row[0] if admin_row else None
            cur.execute("INSERT INTO notices_mt (school_id, class_id, title, message, created_by_fk, expiry_date) VALUES (?, ?, ?, ?, ?, ?)",
                        (school_id, None, title, msg, admin_fk, None))

    # --- seed a bit of timetable (legacy and normalized)
    cur.execute("SELECT COUNT(*) FROM timetable_mt WHERE school_id = ?", (school_id,))
    if cur.fetchone()[0] == 0:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        cur.execute("SELECT id FROM classes WHERE school_id = ?", (school_id,))
        class_rows = cur.fetchall()
        for (cid,) in class_rows:
            for day in days:
                for period in range(1, 6):
                    subj = random.choice(subjects_all)
                    # normalized
                    cur.execute("INSERT INTO timetable_mt (school_id, class_id, day, period, subject) VALUES (?, ?, ?, ?, ?)",
                                (school_id, cid, day, period, subj))
                    # legacy (class/section text): try get class_name/section
                    cur.execute("SELECT class_name, section FROM classes WHERE id = ?", (cid,))
                    clsname, sec = cur.fetchone()
                    cur.execute("INSERT INTO timetable (class, section, day, period, subject, teacher) VALUES (?, ?, ?, ?, ?, ?)",
                                (clsname, sec, day, period, subj, "Teacher_X"))

    conn.commit()
    conn.close()
    print("✅ Demo seeded (legacy + normalized).")


# -------------------------
# Initialize DB & Seed All
# -------------------------
if not os.path.exists(DB_PATH):
    open(DB_PATH, "w").close()

init_db()
seed_demo()
