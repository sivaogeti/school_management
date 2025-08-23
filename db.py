# db.py — Legacy-compatible + normalized (multi-tenant) schema
# - Preserves original columns (class, section, student_id, etc.)
# - Adds fk_* columns for normalized relations
# - Includes all original tables + indexes
# - Seeds demo data with plain-text passwords for convenience
# - Ensures every table gets at least 2–3 seed rows
# - Enforces foreign key constraints via PRAGMA foreign_keys = ON

import sqlite3
import os
import random
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "school.db")

import sqlite3

def init_db():
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()

    # Create students table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        parent_phone TEXT,
        student_phone TEXT,
        class TEXT,
        section TEXT
    )
    """)
    
    conn.commit()
    conn.close()


import sqlite3

def get_student_details(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT student_id, student_name, parent_phone, student_phone, class, section
        FROM users
        WHERE student_id = ? AND role='Student'
        """,
        (student_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "parent_phone": row[2],
            "student_phone": row[3],
            "class": row[4],
            "section": row[5],
        }
    return None



# -------------------------
# Connection
# -------------------------
def get_connection():
    """
    Create a SQLite connection with foreign keys enforced.
    """
    conn = sqlite3.connect(DB_PATH)
    # IMPORTANT: Enforce FK constraints in SQLite (off by default)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# -------------------------
# Schema
# -------------------------
def init_db():
    """
    Create all tables (legacy + normalized) and helpful indexes.
    """
    conn = get_connection()
    cur = conn.cursor()

    # ========= CORE (Multi-tenant / normalized lookups) =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS schools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        address TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER NOT NULL,
        class_name TEXT NOT NULL,                  -- legacy-compatible value like "1", "10"
        section TEXT,                              -- legacy-compatible value like "A", "B"
        UNIQUE(fk_school_id, class_name, section),
        FOREIGN KEY(fk_school_id) REFERENCES schools(id) ON DELETE CASCADE
    );
    """)

    # Users (superset of your two legacy 'users' versions)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER NOT NULL,
        fk_class_id INTEGER,                       -- normalized link to classes
        -- legacy/compat fields
        student_id TEXT UNIQUE,                    -- your business/student code (e.g., S1A01)
        student_name TEXT,                         -- legacy name field
        name TEXT,                                 -- alt legacy name field
        email TEXT UNIQUE,
        password TEXT,                             -- PLAIN TEXT for seeding convenience
        role TEXT,                                 -- Student / Teacher / Admin / Parent / Staff
        class TEXT,                                -- legacy: keep 'class'
        section TEXT,                              -- legacy: keep 'section'
        student_phone TEXT,
        parent_phone TEXT,
        contact TEXT,                              -- legacy alt field
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(fk_school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_class_id)  REFERENCES classes(id) ON DELETE SET NULL
    );
    """)
    
    #----------------------------------special_days----------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS special_days (
        month TEXT NOT NULL,
        year INTEGER NOT NULL,
        row_order INTEGER NOT NULL,
        col1 TEXT,
        col2 TEXT,
        col3 TEXT,
        col4 TEXT,
        col5 TEXT,
        col6 TEXT,
        PRIMARY KEY (month, year, row_order)
    );
    """)
    
    #competitions_meta 
    cur.execute("""
    CREATE TABLE IF NOT EXISTS competitions_meta (
        academic_year TEXT PRIMARY KEY,
        title TEXT
    );
    """)
    
    #competitions_enrichment
    cur.execute("""
    CREATE TABLE IF NOT EXISTS competitions_enrichment (
        academic_year TEXT NOT NULL,            -- e.g., '2025-26'
        row_order     INTEGER NOT NULL,
        col1          TEXT,   -- MONTH
        col2          TEXT,   -- COMPETITION / WORKSHOP
        col3          TEXT,   -- THEME
        PRIMARY KEY (academic_year, row_order)
    );
    """)
    
    #Key Guide Lines
    cur.execute("""
    CREATE TABLE IF NOT EXISTS key_guidelines (
        academic_year TEXT PRIMARY KEY,
        content_md    TEXT,
        updated_at    TEXT
    );
    """)
    
    #Complaints & Suggestions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS complaints_suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,     -- foreign key to users/students
        category TEXT,                -- 'Complaint' or 'Suggestion'
        message TEXT NOT NULL,        -- full text
        status TEXT DEFAULT 'Open',   -- Open, In Progress, Resolved
        remarks TEXT,                 -- admin notes/response
        created_at TEXT,              -- timestamp
        updated_at TEXT
    )
    """)

    # ========= ACADEMICS =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_class_id INTEGER,
        class TEXT,                -- legacy passthrough
        section TEXT,              -- legacy passthrough
        subject_name TEXT,
        FOREIGN KEY(fk_school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_class_id)  REFERENCES classes(id) ON DELETE SET NULL
    );
    """)
    
    #TimeTable 
    cur.execute("""
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_name TEXT NOT NULL,
        section TEXT NOT NULL,
        day_of_week INTEGER NOT NULL,   -- 1=Mon … 7=Sun
        period_no INTEGER NOT NULL,     -- 1..N
        start_time TEXT,
        end_time TEXT,
        slot_type TEXT DEFAULT 'TEACHING',  -- TEACHING / BREAK / LUNCH
        label TEXT,                         -- "Period 1", "Lunch" etc
        subject TEXT,
        teacher TEXT,
        room TEXT,
        notes TEXT,
        UNIQUE(class_name, section, day_of_week, period_no)
    );
    """)
    
    #Marks Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_student_id INTEGER,                 -- normalized
        fk_class_id INTEGER,                   -- normalized
        fk_submitted_by_id INTEGER,            -- normalized (teacher)
        
        exam_type TEXT,                        -- PT1, PT2, Term1, Weekly Test etc
        exam_date DATE,                        -- actual test/term date
        
        subject TEXT,
        total_marks INTEGER DEFAULT 100,       -- default max marks
        secured_marks INTEGER,                 -- actual student score

        -- legacy passthrough
        student_id TEXT,
        class TEXT,
        section TEXT,
        submitted_by TEXT,
        
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY(fk_student_id)      REFERENCES users(id)   ON DELETE CASCADE,
        FOREIGN KEY(fk_class_id)        REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(fk_submitted_by_id) REFERENCES users(id)   ON DELETE SET NULL
    );
    """)

 
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_student_id INTEGER,               -- normalized
        fk_class_id INTEGER,                 -- normalized
        fk_marked_by_id INTEGER,             -- normalized (teacher)
        -- legacy passthrough
        student_id TEXT,
        date TEXT,
        status TEXT,
        submitted_by TEXT,
        UNIQUE(student_id, date),            -- legacy constraint retained
        FOREIGN KEY(fk_student_id) REFERENCES users(id)   ON DELETE CASCADE,
        FOREIGN KEY(fk_class_id)   REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(fk_marked_by_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)
    
    #cafeteria_menu table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cafeteria_menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        price REAL NOT NULL,
        available INTEGER DEFAULT 1
    )
    """)
    
    
    # Transport
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transport_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT,
            driver_name TEXT,
            driver_contact TEXT,
            vehicle_number TEXT,
            stops TEXT,
            timing TEXT,
            fk_school_id INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS student_transport (
            student_id INTEGER PRIMARY KEY,
            fk_route_id INTEGER,
            fk_student_id INT,
            route_name TEXT,
            pickup_point TEXT,
            drop_point TEXT,
            driver_name TEXT,
            driver_phone TEXT,
            bus_lat REAL,
            bus_lon REAL
        );
    """)
    
    #Econnect_resources table 
    cur.execute("""
        CREATE TABLE IF NOT EXISTS econnect_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            file_url TEXT,
            link_url TEXT,
            uploaded_by TEXT,
            timestamp TEXT
        )
    """)
    
    #misc_fees table 
    cur.execute("""
        CREATE TABLE IF NOT EXISTS misc_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            date DATE,
            payment_item TEXT,
            amount DECIMAL(10,2),
            mode TEXT,
            late_fine DECIMAL(10,2),
            transaction_id TEXT,
            status TEXT
        )
    """)
    
    
    #receipts table 
    cur.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            receipt_no TEXT,
            student_id TEXT,
            date DATE,
            payment_item TEXT,
            amount DECIMAL(10,2),
            mode TEXT CHECK (mode IN ('Cash','Online','Cheque','DD')),
            late_fine DECIMAL(10,2),
            transaction_id TEXT,
            status TEXT CHECK (status IN ('Live','Cancelled')) DEFAULT 'Live'
        )
    """)
    
        
    # fee_schedule
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fee_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,          -- changed to TEXT
        academic_year TEXT,
        month TEXT,
        tuition_due INTEGER,
        bus_due INTEGER,
        food_due INTEGER,
        books_due INTEGER,
        uniform_due INTEGER,
        hostel_due INTEGER,
        misc_due INTEGER
    );
    """)


    # Homework
    cur.execute("""
    CREATE TABLE IF NOT EXISTS homework (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_class_id INTEGER,
        fk_assigned_by_id INTEGER,
        -- legacy
        class TEXT NOT NULL,
        section TEXT NOT NULL,
        subject TEXT NOT NULL,
        description TEXT,
        due_date TEXT,
        file_url TEXT,
        assigned_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(fk_school_id)     REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_class_id)      REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(fk_assigned_by_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    # Syllabus
    cur.execute("""
    CREATE TABLE IF NOT EXISTS syllabus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_class_id INTEGER,
        fk_uploaded_by_id INTEGER,
        -- legacy
        class TEXT NOT NULL,
        section TEXT NOT NULL,
        subject TEXT NOT NULL,
        syllabus_text TEXT,
        file_url TEXT,
        uploaded_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(fk_school_id)      REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_class_id)       REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(fk_uploaded_by_id) REFERENCES users(id)   ON DELETE SET NULL
    );
    """)

    
    
        
    

    
    

    # ========= EXAMS =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS examinations (
        exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_class_id INTEGER,
        exam_name TEXT NOT NULL,     -- e.g., "Mid Term 2025"
        subject TEXT NOT NULL,       -- e.g., "Mathematics"
        class TEXT,                  -- legacy
        section TEXT,                -- legacy
        date TEXT NOT NULL,
        time TEXT,
        max_marks INTEGER NOT NULL,
        FOREIGN KEY(fk_school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_class_id)  REFERENCES classes(id) ON DELETE SET NULL
    );
    """)
    #Exam Schedule
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_schedule (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      class_name TEXT NOT NULL,
      section    TEXT NOT NULL,
      exam_name  TEXT,          -- e.g., "Term 1", "UT-2"
      subject    TEXT,
      exam_date  DATE,
      start_time TEXT,
      end_time   TEXT,
      venue      TEXT,
      syllabus   TEXT,
      notes      TEXT,
      exam_type  TEXT DEFAULT 'EXAM',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    #PTM schedule
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ptm_schedule (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      class_name   TEXT NOT NULL,
      section      TEXT NOT NULL,
      meeting_date DATE,
      start_time   TEXT,
      end_time     TEXT,
      venue        TEXT,
      agenda       TEXT,
      notes        TEXT,
      created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    
    
    
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_exam_id INTEGER,
        fk_student_id INTEGER,
        -- legacy
        student_id TEXT,
        subject TEXT,
        marks INTEGER,
        grade TEXT,
        FOREIGN KEY(fk_exam_id)   REFERENCES examinations(exam_id) ON DELETE CASCADE,
        FOREIGN KEY(fk_student_id) REFERENCES users(id)            ON DELETE CASCADE
    );
    """)

    # ========= FEES  =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_class_id INTEGER,
        class TEXT UNIQUE,          -- keep legacy contract; one row per class string
        total_fee REAL,
        FOREIGN KEY(fk_school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_class_id)  REFERENCES classes(id) ON DELETE SET NULL
    );
    """)
    
    #payments table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_student_id INTEGER,
        student_id TEXT,          -- keep TEXT for consistency
        amount REAL,
        date TEXT DEFAULT CURRENT_TIMESTAMP,
        method TEXT,
        FOREIGN KEY(fk_school_id)  REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_student_id) REFERENCES users(id)   ON DELETE CASCADE
    );
    """)

    # ========= NOTICES / MESSAGES / WHATSAPP =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_class_id INTEGER,
        fk_created_by_id INTEGER,
        -- legacy
        title TEXT,
        message TEXT,
        class TEXT,
        section TEXT,
        created_by TEXT,
        expiry_date TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(fk_school_id)     REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_class_id)      REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(fk_created_by_id) REFERENCES users(id)   ON DELETE SET NULL
    );
    """)

    # one flexible messages table (superset of both of your originals)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_sender_id INTEGER,
        fk_receiver_id INTEGER,        -- nullable: direct messages
        fk_school_id INTEGER,
        -- legacy compatible fields
        sender_id TEXT,
        receiver_id TEXT,              -- for legacy APIs
        recipient_group TEXT,          -- for group/broadcasts
        sender_role TEXT,
        message TEXT,
        attachment_path TEXT,
        sender_email TEXT,
        receiver_email TEXT,
        read INTEGER DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(fk_sender_id)  REFERENCES users(id)   ON DELETE SET NULL,
        FOREIGN KEY(fk_receiver_id) REFERENCES users(id)  ON DELETE SET NULL,
        FOREIGN KEY(fk_school_id)  REFERENCES schools(id) ON DELETE CASCADE
    );
    """)
    
    #lesson_plans
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lesson_plans (
        id INTEGER PRIMARY KEY,
        subject TEXT,
        chapter TEXT,
        notes TEXT,
        video_url TEXT,
        file_url TEXT,
        class TEXT,
        section TEXT,
        timestamp TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS whatsapp_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_student_id INTEGER,
        -- legacy
        student_id TEXT,
        phone_number TEXT,
        message TEXT,
        status TEXT,
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(fk_school_id)  REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_student_id) REFERENCES users(id)   ON DELETE CASCADE
    );
    """)

    # ========= ASSIGNMENTS (superset) =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_class_id INTEGER,
        fk_assigned_by_id INTEGER,
        -- legacy superset (you had two definitions; keep both shapes)
        title TEXT,                -- (second version)
        subject TEXT,
        class TEXT,
        section TEXT,
        file_path TEXT,            -- (second version)
        description TEXT,          -- (first version)
        due_date TEXT,
        assigned_by TEXT,
        reviewed INTEGER,
        student_id TEXT,
        timestamp TEXT,
        FOREIGN KEY(fk_school_id)      REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_class_id)       REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(fk_assigned_by_id) REFERENCES users(id)   ON DELETE SET NULL
    );
    """)
    
    # ========= Assignment Submissions =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assignment_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER,
        student_id INTEGER,
        file_path TEXT,
        ai_feedback TEXT,
        submitted_at TEXT
    );
    """)
    
    # ========= CONTENT / EVENTS / GALLERY =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_created_by_id INTEGER,
        title TEXT,
        description TEXT,
        date TEXT,
        target_audience TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by TEXT,
        FOREIGN KEY(fk_school_id)   REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_created_by_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS digital_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_target_class_id INTEGER,
        fk_uploaded_by_id INTEGER,
        title TEXT,
        description TEXT,
        file_url TEXT,
        content_type TEXT,
        target_class TEXT,   -- legacy
        uploaded_by TEXT,    -- legacy
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(fk_school_id)      REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_target_class_id) REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(fk_uploaded_by_id) REFERENCES users(id)   ON DELETE SET NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_uploaded_by_id INTEGER,
        title TEXT NOT NULL,
        image_url TEXT,
        category TEXT,
        uploaded_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(fk_school_id)      REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_uploaded_by_id) REFERENCES users(id)   ON DELETE SET NULL
    );
    """)

    # ========= TRANSPORT =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transport_routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        route_name TEXT,
        driver_name TEXT,
        driver_contact TEXT,
        vehicle_number TEXT,
        stops TEXT,
        timing TEXT,
        incharge_name  TEXT,
        incharge_phone TEXT,
        FOREIGN KEY(fk_school_id) REFERENCES schools(id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS student_transport (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_route_id INTEGER,
        fk_student_id INTEGER,
        student_id TEXT,     -- legacy
        pickup_point TEXT,
        drop_point TEXT,
        FOREIGN KEY(fk_route_id)  REFERENCES transport_routes(id) ON DELETE SET NULL,
        FOREIGN KEY(fk_student_id) REFERENCES users(id)           ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS library_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_book_id INTEGER,         -- normalized foreign key
        fk_student_id INTEGER,      -- normalized foreign key
        issue_date DATE,
        due_date DATE,
        return_date DATE,
        FOREIGN KEY(fk_book_id) REFERENCES library_books(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_student_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)


    # ========= HEALTH / ADMISSIONS / LEAVE =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS library_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_book_id INTEGER,
        fk_student_id INTEGER,
        issue_date DATE,
        due_date DATE,
        return_date DATE,
        FOREIGN KEY(fk_book_id) REFERENCES library_books(id),
        FOREIGN KEY(fk_student_id) REFERENCES users(id)
    );
    """)


    cur.execute("""
    CREATE TABLE IF NOT EXISTS admissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        fk_student_id INTEGER,
        student_id TEXT,      -- legacy
        student_name TEXT,    -- legacy
        dob TEXT,
        contact TEXT,
        applied_class TEXT,
        status TEXT,
        date_applied TEXT,
        documents_path TEXT,
        FOREIGN KEY(fk_school_id)  REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_student_id) REFERENCES users(id)   ON DELETE SET NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_student_id INTEGER,
        fk_reviewed_by_id INTEGER,
        student_id TEXT,      -- legacy
        from_date TEXT,
        to_date TEXT,
        reason TEXT,
        status TEXT DEFAULT 'Pending',
        reviewed_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(fk_student_id)     REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_reviewed_by_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    # ========= STAFF =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        name TEXT,
        role TEXT,
        phone TEXT,
        email TEXT,
        join_date TEXT,
        FOREIGN KEY(fk_school_id) REFERENCES schools(id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS staff_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_staff_id INTEGER,
        staff_id INTEGER,     -- legacy passthrough
        date TEXT,
        status TEXT,
        FOREIGN KEY(fk_staff_id) REFERENCES staff(staff_id) ON DELETE CASCADE
    );
    """)

    # ========= SCHOOL CONFIG / FRONT OFFICE / CMS / PRINCIPAL =========
    cur.execute("""
    CREATE TABLE IF NOT EXISTS school_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS visitor_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        student_name TEXT,
        student_phone TEXT,
        purpose TEXT,
        photo_path TEXT,
        in_time TEXT,
        out_time TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS enquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        contact TEXT,
        query TEXT,
        follow_up_date TEXT
    );
    """)
    
    #FAQs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)


    cur.execute("""
    CREATE TABLE IF NOT EXISTS website_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_school_id INTEGER,
        page_name TEXT,
        content_html TEXT,
        last_updated TEXT,
        FOREIGN KEY(fk_school_id) REFERENCES schools(id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_student_id INTEGER,
        student_id TEXT,    -- legacy
        title TEXT,
        description TEXT,
        date TEXT,
        issued_by TEXT,
        date_awarded TEXT,
        awarded_by TEXT,
        file_url TEXT,
        timestamp TEXT,
        fk_issued_by_id INTEGER,
        date_awarded TEXT,
        awarded_by TEXT,
        file_url TEXT,
        timestamp TEXT,
        FOREIGN KEY(fk_student_id)    REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(fk_issued_by_id)  REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS principal_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    #contacts_directory
    cur.execute("""
    CREATE TABLE IF NOT EXISTS contacts_directory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no INTEGER NOT NULL DEFAULT 0,     -- display order
        category TEXT,                           -- e.g., Academic Queries
        title TEXT,                              -- short heading shown on card
        contact_name TEXT,                       -- e.g., Mrs. Rekha Phulekar
        designation TEXT,                        -- e.g., Principal
        phone_primary TEXT,                      -- e.g., 9133356771
        phone_alt TEXT,                          -- optional second number
        notes TEXT,                              -- optional
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """)

    # ========= INDEXES (original + helpful safe additions) =========
    # original ones mentioned
    cur.execute("CREATE INDEX IF NOT EXISTS idx_homework_class_section ON homework (class, section);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_syllabus_class_section ON syllabus (class, section);")

    # helpful additions (do NOT break legacy)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_student_id ON users(student_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_school_id ON users(fk_school_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_classes_school_id ON classes(fk_school_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_marks_fk_student_id ON marks(fk_student_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_fk_student_id ON attendance(fk_student_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_fk_student_id ON payments(fk_student_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notices_class_section ON notices(class, section);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_assignments_class_section ON assignments(class, section);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exam_lookup ON exam_schedule (upper(class_name), upper(section), exam_date, upper(exam_type));")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ptm_lookup ON ptm_schedule (upper(class_name), upper(section), meeting_date);")

    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_subjects_class_section ON subjects(class, section);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_issues_book ON library_issues(fk_book_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_issues_student ON library_issues(fk_student_id);")
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cs_student_id ON complaints_suggestions (student_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cs_created_at ON complaints_suggestions (created_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_student_id ON users (student_id);")
    

    

    

    conn.commit()
    conn.close()


# -------------------------
# Helper utilities
# -------------------------
def _get_class_id(cur, school_id, class_name, section):
    """
    Resolve a (school, class_name, section) to classes.id
    """
    cur.execute("""
        SELECT id FROM classes
        WHERE fk_school_id=? AND class_name=? AND ifnull(section,'')=ifnull(?, '')
    """, (school_id, str(class_name), section))
    row = cur.fetchone()
    return row[0] if row else None


def _get_user_id_by_student_code(cur, student_code):
    """
    Resolve users.id by legacy student_id code (e.g., 'S1A01' or 'T01')
    """
    cur.execute("SELECT id FROM users WHERE student_id = ?", (student_code,))
    row = cur.fetchone()
    return row[0] if row else None


def add_mark(student_id_code, subject, marks, submitted_by_code=None, class_name=None, section=None):
    """
    Public helper to insert a mark with both normalized FKs and legacy passthrough columns.
    """
    conn = get_connection()
    cur = conn.cursor()
    student_fk = _get_user_id_by_student_code(cur, student_id_code)
    submitted_fk = _get_user_id_by_student_code(cur, submitted_by_code) if submitted_by_code else None

    # try to derive class fk if provided
    fk_class_id = None
    if class_name is not None and section is not None and student_fk:
        cur.execute("SELECT fk_school_id FROM users WHERE id=?", (student_fk,))
        r = cur.fetchone()
        if r:
            fk_class_id = _get_class_id(cur, r[0], class_name, section)

    cur.execute("""
        INSERT INTO marks(
            fk_student_id, fk_class_id, fk_submitted_by_id,
            student_id, subject, marks, class, section, submitted_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_fk, fk_class_id, submitted_fk,
          student_id_code, subject, marks, class_name, section, submitted_by_code))
    conn.commit()
    conn.close()


def add_payment(student_id_code, amount, method="Cash"):
    """
    Public helper to insert a payment (FK + legacy columns).
    """
    conn = get_connection()
    cur = conn.cursor()
    student_fk = _get_user_id_by_student_code(cur, student_id_code)
    fk_school_id = None
    if student_fk:
        cur.execute("SELECT fk_school_id FROM users WHERE id=?", (student_fk,))
        r = cur.fetchone()
        fk_school_id = r[0] if r else None
    cur.execute("""
        INSERT INTO payments(fk_school_id, fk_student_id, student_id, amount, method)
        VALUES (?, ?, ?, ?, ?)
    """, (fk_school_id, student_fk, student_id_code, amount, method))
    conn.commit()
    conn.close()


def insert_notice(title, message, created_by=None, class_name=None, section=None, expiry_date=None):
    """
    Public helper to insert a notice with optional targeting and expiry.
    """
    conn = get_connection()
    cur = conn.cursor()

    fk_created_by_id = _get_user_id_by_student_code(cur, created_by) if created_by else None
    fk_school_id = None
    fk_class_id = None

    if class_name is not None and section is not None:
        # pick any school (demo-friendly)
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        sch = cur.fetchone()
        if sch:
            fk_school_id = sch[0]
            fk_class_id = _get_class_id(cur, fk_school_id, class_name, section)

    cur.execute("""
        INSERT INTO notices(
            fk_school_id, fk_class_id, fk_created_by_id,
            title, message, class, section, created_by, expiry_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (fk_school_id, fk_class_id, fk_created_by_id,
          title, message, class_name, section, created_by, expiry_date))
    conn.commit()
    conn.close()


def fetch_notices_for(class_name=None, section=None, include_expired=False):
    """
    Query helper for notices, honoring legacy columns and optional expiry filtering.
    """
    conn = get_connection()
    cur = conn.cursor()
    if include_expired:
        cur.execute("""
            SELECT title, message, expiry_date, timestamp, class, section, created_by
            FROM notices
            WHERE (class IS NULL OR class=?)
              AND (section IS NULL OR section=?)
            ORDER BY timestamp DESC
        """, (class_name, section))
    else:
        cur.execute("""
            SELECT title, message, expiry_date, timestamp, class, section, created_by
            FROM notices
            WHERE (class IS NULL OR class=?)
              AND (section IS NULL OR section=?)
              AND (expiry_date IS NULL OR expiry_date >= date('now'))
            ORDER BY timestamp DESC
        """, (class_name, section))
    rows = cur.fetchall()
    conn.close()
    return rows


# -------------------------
# Seeding helpers: core data
# -------------------------
def _ensure_demo_school_and_classes():
    """
    Ensure a demo school and the 1..10 (A/B) classes exist.
    Returns the school_id.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM schools WHERE name=?", ("Demo School",))
    row = cur.fetchone()
    if row:
        school_id = row[0]
    else:
        cur.execute("INSERT INTO schools(name, address) VALUES (?, ?)", ("Demo School", "Demo Address"))
        school_id = cur.lastrowid

    # classes 1..10, A/B
    cur.execute("SELECT COUNT(*) FROM classes WHERE fk_school_id=?", (school_id,))
    if cur.fetchone()[0] == 0:
        for cls in range(1, 11):
            for sec in ("A", "B"):
                cur.execute("""
                    INSERT INTO classes(fk_school_id, class_name, section) VALUES (?, ?, ?)
                """, (school_id, str(cls), sec))
    conn.commit()
    conn.close()
    return school_id


def seed_default_fees(school_id):
    """
    One fee row per class string (legacy constraint: class is UNIQUE).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM fees")
    if cur.fetchone()[0] == 0:
        # create fee rows for each class string legacy style
        for cls in range(1, 11):
            class_str = str(cls)
            # pick the first matching class row (fees per class, not section)
            cur.execute("""
                SELECT id FROM classes WHERE fk_school_id=? AND class_name=? LIMIT 1
            """, (school_id, class_str))
            r = cur.fetchone()
            fk_class_id = r[0] if r else None
            total_fee = 10000 + cls * 500
            cur.execute("""
                INSERT OR IGNORE INTO fees(fk_school_id, fk_class_id, class, total_fee)
                VALUES (?, ?, ?, ?)
            """, (school_id, fk_class_id, class_str, total_fee))
        conn.commit()
        print("✅ Default fee structure created for Classes 1–10.")
    conn.close()


def seed_sample_users(school_id):
    """
    Create sample students (1..10 A/B, 5 per section), 3 teachers, and 1 admin.
    """
    conn = get_connection()
    cur = conn.cursor()

    # students
    cur.execute("SELECT COUNT(*) FROM users WHERE role='Student' AND fk_school_id=?", (school_id,))
    if cur.fetchone()[0] == 0:
        for cls in range(1, 11):
            for sec in ("A", "B"):
                # lookup fk_class_id
                fk_class_id = _get_class_id(cur, school_id, str(cls), sec)
                for idx in range(1, 6):
                    sid = f"S{cls}{sec}{idx:02d}"
                    student_name = f"Student_{cls}{sec}{idx:02d}"
                    email = f"{sid.lower()}@school.com"
                    password = "student123"  # plain text (requested)

                    cur.execute("""
                        INSERT INTO users(
                            fk_school_id, fk_class_id,
                            student_id, student_name, name, email, password, role,
                            class, section, student_phone, parent_phone
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        school_id, fk_class_id,
                        sid, student_name, student_name, email, password, "Student",
                        str(cls), sec, f"9000000{idx:03d}", f"9001000{idx:03d}"
                    ))
        print("✅ Sample students created for Classes 1–10 (A & B).")

    # 3 teachers + 1 admin
    cur.execute("SELECT COUNT(*) FROM users WHERE role='Teacher' AND fk_school_id=?", (school_id,))
    if cur.fetchone()[0] == 0:
        for t in range(1, 4):
            email = f"teacher{t}@school.com"
            password = "teacher123"
            cur.execute("""
                INSERT INTO users(
                    fk_school_id, student_id, student_name, name, email, password, role, class, section
                ) VALUES (?, ?, ?, ?, ?, ?, 'Teacher', ?, ?)
            """, (
                school_id, f"T{t:02d}", f"Teacher {t}", f"Teacher {t}",
                email, password, str(t), "A"
            ))
        print("✅ Default teachers created: teacher1..3@school.com / teacher123")

    conn.commit()
    conn.close()


def seed_random_marks_attendance_payments():
    """
    Seed:
      - Marks: 3 random subjects per student
      - Attendance: last 5 days per student
      - Payments: 1 partial payment per student
    """
    conn = get_connection()
    cur = conn.cursor()

    subjects = ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]
    cur.execute("SELECT id, student_id, class, section FROM users WHERE role='Student'")
    students = cur.fetchall()

    for user_id, sid, cls, sec in students:
        # marks (3 random subjects)
        for subj in random.sample(subjects, 3):
            cur.execute("""
                INSERT INTO marks(
                fk_student_id, fk_class_id, fk_submitted_by_id,
                student_id, subject, secured_marks, class, section, submitted_by
            )
            VALUES (?, (SELECT fk_class_id FROM users WHERE id=?), NULL, ?, ?, ?, ?, ?, ?)
        """, (user_id, user_id, sid, subj, random.randint(40, 100), cls, sec, "auto_seed"))

        # last 5 days attendance
        for i in range(5):
            date_str = (datetime.today() - timedelta(days=i)).strftime("%Y-%m-%d")
            status = random.choice(["Present", "Absent", "Late"])
            cur.execute("""
                INSERT OR IGNORE INTO attendance(
                    fk_student_id, fk_class_id, fk_marked_by_id,
                    student_id, date, status, submitted_by
                )
                VALUES (?, (SELECT fk_class_id FROM users WHERE id=?), NULL, ?, ?, ?, ?)
            """, (user_id, user_id, sid, date_str, status, "auto_seed"))

        # partial payment
        cur.execute("""
            INSERT INTO payments(fk_school_id, fk_student_id, student_id, amount, method)
            SELECT fk_school_id, id, ?, ?, ?
            FROM users WHERE id=?
        """, (sid, random.randint(1000, 5000), random.choice(["Cash", "UPI", "Bank Transfer"]), user_id))

    conn.commit()
    conn.close()
    print("✅ Random marks, attendance, and payments seeded.")


def seed_notices_homework_syllabus_timetable():
    """
    Seed notices (3+), timetable (full week), homework (3+), syllabus (3+).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Notices (at least 3)
    cur.execute("SELECT COUNT(*) FROM notices")
    if cur.fetchone()[0] == 0:
        notices = [
            ("Welcome back to school!", "System"),
            ("PTM this Saturday", "System"),
            ("Submit homework on time", "System")
        ]
        # pick any school/class for fk convenience
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        sch = cur.fetchone()
        fk_school_id = sch[0] if sch else None

        # try class 1A if exists
        fk_class_id = None
        if fk_school_id:
            fk_class_id = _get_class_id(cur, fk_school_id, "1", "A")

        for msg, created_by in notices:
            cur.execute("""
                INSERT INTO notices(
                    fk_school_id, fk_class_id, fk_created_by_id,
                    title, message, class, section, created_by, expiry_date, timestamp
                ) VALUES (?, ?, NULL, ?, ?, NULL, NULL, ?, NULL, datetime('now'))
            """, (fk_school_id, fk_class_id, msg, msg, created_by))
        print("✅ Notices seeded.")

    

    # Homework (3+)
    cur.execute("SELECT COUNT(*) FROM homework")
    if cur.fetchone()[0] == 0:
        # choose 3 random classes and subjects
        cur.execute("SELECT id, fk_school_id, class_name, section FROM classes LIMIT 3")
        for cls_id, school_id, class_name, section in cur.fetchall():
            for subj in ["English", "Maths", "Science"]:
                due_date = (datetime.today() + timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d")
                cur.execute("""
                    INSERT INTO homework(
                        fk_school_id, fk_class_id, fk_assigned_by_id,
                        class, section, subject, description, due_date, file_url, assigned_by
                    ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, NULL, ?)
                """, (school_id, cls_id, class_name, section, subj, f"{subj} chapter practice", due_date, "teacher@school.com"))
        print("✅ Homework seeded.")

    # Syllabus (3+)
    cur.execute("SELECT COUNT(*) FROM syllabus")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, fk_school_id, class_name, section FROM classes LIMIT 3")
        for cls_id, school_id, class_name, section in cur.fetchall():
            for subj in ["English", "Maths", "Science"]:
                cur.execute("""
                    INSERT INTO syllabus(
                        fk_school_id, fk_class_id, fk_uploaded_by_id,
                        class, section, subject, syllabus_text, file_url, uploaded_by
                    ) VALUES (?, ?, NULL, ?, ?, ?, ?, NULL, ?)
                """, (school_id, cls_id, class_name, section, subj, f"Syllabus outline for {subj} ({class_name}{section})", "teacher@school.com"))
        print("✅ Syllabus seeded.")

    conn.commit()
    conn.close()


def seed_assignments_exams_and_results():
    """
    Seed assignments (3 per sampled class), exam_schedule (3 per class), examinations + exam_results (2–3).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Assignments
    cur.execute("SELECT COUNT(*) FROM assignments")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, fk_school_id, class_name, section FROM classes")
        for cls_id, school_id, class_name, section in cur.fetchall():
            for subj in ["English", "Maths", "Science"]:
                due_date = (datetime.today() + timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d")
                cur.execute("""
                    INSERT INTO assignments(
                        fk_school_id, fk_class_id, fk_assigned_by_id,
                        title, subject, class, section, file_path, description, due_date, assigned_by
                    ) VALUES (?, ?, NULL, ?, ?, ?, ?, NULL, ?, ?, ?)
                """, (school_id, cls_id, f"{subj} Homework", subj, class_name, section, f"{subj} Homework", due_date, "teacher@school.com"))
        print("✅ Assignments seeded.")

    # Examinations + Exam Schedule + Results
    cur.execute("SELECT COUNT(*) FROM examinations")
    empty_exams = cur.fetchone()[0] == 0
    if empty_exams:
        # Create 3 example exams for Class 1A
        cur.execute("SELECT id, fk_school_id, class_name, section FROM classes WHERE class_name='1' AND section='A' LIMIT 1")
        row = cur.fetchone()
        if row:
            cls_id, school_id, class_name, section = row
            exams = [
                ("Unit Test 1", "Maths", "09:00 AM", 50),
                ("Unit Test 1", "English", "11:00 AM", 50),
                ("Mid Term", "Science", "10:00 AM", 100),
            ]
            exam_ids = []
            for name, subj, time_str, max_marks in exams:
                ex_date = (datetime.today() + timedelta(days=random.randint(3, 10))).strftime("%Y-%m-%d")
                cur.execute("""
                    INSERT INTO examinations(
                        fk_school_id, fk_class_id, exam_name, subject, class, section, date, time, max_marks
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (school_id, cls_id, name, subj, class_name, section, ex_date, time_str, max_marks))
                exam_ids.append(cur.lastrowid)

            # Create schedule entries referencing these exams
            for ex_id in exam_ids:
                cur.execute("""
                    INSERT INTO exam_schedule(
                        fk_school_id, fk_class_id, fk_assigned_by_id, fk_exam_id,
                        class, section, subject, exam_date, exam_time, exam_type, assigned_by
                    )
                    SELECT fk_school_id, id, NULL, ?, class_name, section, 'Auto',
                           (SELECT date FROM examinations WHERE exam_id=?),
                           (SELECT time FROM examinations WHERE exam_id=?),
                           'Scheduled', 'teacher@school.com'
                    FROM classes WHERE id=?
                """, (ex_id, ex_id, ex_id, cls_id))

            # Create exam_results for 2–3 students for the first exam
            cur.execute("SELECT id, student_id FROM users WHERE fk_class_id=? AND role='Student' LIMIT 3", (cls_id,))
            students = cur.fetchall()
            for ex_id in exam_ids[:2]:
                for uid, sid in students:
                    cur.execute("""
                        INSERT INTO exam_results(
                            fk_exam_id, fk_student_id, student_id, subject, marks, grade
                        )
                        SELECT ?, ?, ?, (SELECT subject FROM examinations WHERE exam_id=?),
                               ?, CASE
                                      WHEN ? >= 90 THEN 'A'
                                      WHEN ? >= 75 THEN 'B'
                                      WHEN ? >= 60 THEN 'C'
                                      WHEN ? >= 40 THEN 'D'
                                      ELSE 'F'
                                  END
                    """, (ex_id, uid, sid, ex_id,
                          random.randint(30, 100),
                          100, 100, 100, 100))
        print("✅ Examinations, exam schedule, and exam results seeded.")

    conn.commit()
    conn.close()


def seed_default_subjects():
    """
    Seed a default subject set for every class (if empty).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subjects")
    if cur.fetchone()[0] == 0:
        default = ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]
        cur.execute("SELECT id, fk_school_id, class_name, section FROM classes")
        for cls_id, school_id, class_name, section in cur.fetchall():
            for s in default:
                cur.execute("""
                    INSERT INTO subjects(fk_school_id, fk_class_id, class, section, subject_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (school_id, cls_id, class_name, section, s))
        conn.commit()
        print("✅ Default subjects seeded.")
    conn.close()


# -------------------------
# Seeding helpers: everything else (2–3+ rows each)
# -------------------------
def seed_messages_and_whatsapp_logs():
    """
    Seed direct/group messages and WhatsApp logs.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Messages (2–3)
    cur.execute("SELECT COUNT(*) FROM messages")
    if cur.fetchone()[0] == 0:
        # Find two students and one teacher
        cur.execute("SELECT id, student_id, fk_school_id FROM users WHERE role='Student' LIMIT 2")
        students = cur.fetchall()
        cur.execute("SELECT id, student_id, fk_school_id FROM users WHERE role='Teacher' LIMIT 1")
        teacher = cur.fetchone()
        if len(students) >= 2 and teacher:
            s1_id, s1_code, sch1 = students[0]
            s2_id, s2_code, _ = students[1]
            t_id, t_code, sch_t = teacher

            msgs = [
                (t_id, s1_id, sch_t, t_code, s1_code, None, "Teacher", "Please submit your assignment by Friday.", None),
                (s1_id, t_id, sch1, s1_code, t_code, None, "Student", "Okay, I will.", None),
                (t_id, None, sch_t, t_code, None, "Class 1A", "Teacher", "Reminder: PTM on Saturday", None),
            ]
            cur.executemany("""
                INSERT INTO messages(
                    fk_sender_id, fk_receiver_id, fk_school_id,
                    sender_id, receiver_id, recipient_group, sender_role, message, attachment_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, msgs)
        print("✅ Messages seeded.")

    # WhatsApp Logs (2–3)
    cur.execute("SELECT COUNT(*) FROM whatsapp_logs")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, student_id, fk_school_id, student_phone FROM users WHERE role='Student' LIMIT 3")
        rows = cur.fetchall()
        for uid, sid, sch_id, phone in rows:
            cur.execute("""
                INSERT INTO whatsapp_logs(
                    fk_school_id, fk_student_id, student_id, phone_number, message, status, response
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sch_id, uid, sid, phone or "9999999999", "Fee reminder", random.choice(["SENT", "DELIVERED"]), "OK"))
        print("✅ WhatsApp logs seeded.")

    conn.commit()
    conn.close()


def seed_gallery_content_events_website():
    """
    Seed gallery, digital content, calendar events, and website pages.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Gallery (3)
    cur.execute("SELECT COUNT(*) FROM gallery")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        sch = cur.fetchone()
        school_id = sch[0] if sch else None
        cur.execute("SELECT id FROM users WHERE role='Teacher' LIMIT 1")
        teacher = cur.fetchone()
        uploader_id = teacher[0] if teacher else None
        items = [
            (school_id, uploader_id, "Science Fair", "https://example.com/img1.jpg", "Events", "teacher1@school.com"),
            (school_id, uploader_id, "Sports Day", "https://example.com/img2.jpg", "Sports", "teacher2@school.com"),
            (school_id, uploader_id, "Art Exhibition", "https://example.com/img3.jpg", "Art", "teacher3@school.com")
        ]
        cur.executemany("""
            INSERT INTO gallery(fk_school_id, fk_uploaded_by_id, title, image_url, category, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, items)
        print("✅ Gallery seeded.")

    # Digital Content (3)
    cur.execute("SELECT COUNT(*) FROM digital_content")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        school_id = cur.fetchone()[0]
        cur.execute("SELECT id, class_name, section FROM classes LIMIT 1")
        row = cur.fetchone()
        class_id = row[0] if row else None
        contents = [
            (school_id, class_id, None, "Maths – Fractions Video", "Intro video on fractions", "https://example.com/fractions.mp4", "video", "1", "teacher@school.com"),
            (school_id, class_id, None, "English – Poem PDF", "Poem: The Road Not Taken", "https://example.com/poem.pdf", "pdf", "1", "teacher@school.com"),
            (school_id, class_id, None, "Science – Photosynthesis", "Slides on photosynthesis", "https://example.com/photosynthesis.pptx", "slides", "1", "teacher@school.com"),
        ]
        cur.executemany("""
            INSERT INTO digital_content(
                fk_school_id, fk_target_class_id, fk_uploaded_by_id,
                title, description, file_url, content_type, target_class, uploaded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, contents)
        print("✅ Digital content seeded.")

    # Calendar Events (3)
    cur.execute("SELECT COUNT(*) FROM calendar_events")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        sch_id = cur.fetchone()[0]
        events = [
            (sch_id, None, "PTM", "Parent-Teacher Meeting", (datetime.today()+timedelta(days=2)).strftime("%Y-%m-%d"), "All", "System"),
            (sch_id, None, "Sports Day", "Annual sports day", (datetime.today()+timedelta(days=10)).strftime("%Y-%m-%d"), "All", "System"),
            (sch_id, None, "Science Fair", "Exhibit your projects", (datetime.today()+timedelta(days=15)).strftime("%Y-%m-%d"), "All", "System"),
        ]
        cur.executemany("""
            INSERT INTO calendar_events(
                fk_school_id, fk_created_by_id, title, description, date, target_audience, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, events)
        print("✅ Calendar events seeded.")

    # Website Pages (3)
    cur.execute("SELECT COUNT(*) FROM website_pages")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        sch_id = cur.fetchone()[0]
        pages = [
            (sch_id, "Home", "<h1>Welcome to Demo School</h1>", datetime.today().strftime("%Y-%m-%d")),
            (sch_id, "About", "<p>About our school...</p>", datetime.today().strftime("%Y-%m-%d")),
            (sch_id, "Contact", "<p>Contact us at admin@school.com</p>", datetime.today().strftime("%Y-%m-%d")),
        ]
        cur.executemany("""
            INSERT INTO website_pages(fk_school_id, page_name, content_html, last_updated)
            VALUES (?, ?, ?, ?)
        """, pages)
        print("✅ Website pages seeded.")

    conn.commit()
    conn.close()


def seed_transport():
    """
    Seed transport routes and student_transport mappings (2–3 rows).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Routes (3)
    cur.execute("SELECT COUNT(*) FROM transport_routes")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        sch_id = cur.fetchone()[0]
        routes = [
            (sch_id, "Route 1", "Ramesh", "9000000001", "AP09 AB 1234", "Stop1,Stop2,Stop3", "7:30-8:30"),
            (sch_id, "Route 2", "Suresh", "9000000002", "AP09 CD 5678", "StopA,StopB,StopC", "7:45-8:45"),
            (sch_id, "Route 3", "Mahesh", "9000000003", "AP09 EF 9012", "StopX,StopY,StopZ", "7:15-8:15"),
        ]
        cur.executemany("""
            INSERT INTO transport_routes(
                fk_school_id, route_name, driver_name, driver_contact, vehicle_number, stops, timing
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, routes)
        print("✅ Transport routes seeded.")

    # Student transport (at least 2–3) — map first few students
    cur.execute("SELECT COUNT(*) FROM student_transport")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM transport_routes ORDER BY id")
        route_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id, student_id FROM users WHERE role='Student' LIMIT 5")
        students = cur.fetchall()
        if route_ids and students:
            pairs = []
            for i, (uid, sid) in enumerate(students):
                route_id = route_ids[i % len(route_ids)]
                pairs.append((route_id, uid, sid, f"Pickup {i+1}", f"Drop {i+1}"))
            cur.executemany("""
                INSERT INTO student_transport(
                    fk_route_id, fk_student_id, student_id, pickup_point, drop_point
                ) VALUES (?, ?, ?, ?, ?)
            """, pairs)
        print("✅ Student transport seeded.")

    conn.commit()
    conn.close()


def seed_library():
    """
    Seed library_books (3+) and library_issues (2–3).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Books (3+)
    cur.execute("SELECT COUNT(*) FROM library_books")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        sch_id = cur.fetchone()[0]
        books = [
            (sch_id, "Mathematics Grade 5", "R.D. Sharma", "ISBN0001", "Available", "Shelf A1"),
            (sch_id, "Science Fundamentals", "HC Verma", "ISBN0002", "Available", "Shelf B2"),
            (sch_id, "English Literature", "Wren & Martin", "ISBN0003", "Available", "Shelf C3"),
            (sch_id, "Hindi Stories", "Premchand", "ISBN0004", "Available", "Shelf D4"),
        ]
        cur.executemany("""
            INSERT INTO library_books(fk_school_id, title, author, isbn, status, location)
            VALUES (?, ?, ?, ?, ?, ?)
        """, books)
        print("✅ Library books seeded.")

    # Issues (2–3)
    cur.execute("SELECT COUNT(*) FROM library_issues")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, isbn FROM library_books LIMIT 3")
        book_rows = cur.fetchall()
        cur.execute("SELECT id, student_id FROM users WHERE role='Student' LIMIT 3")
        student_rows = cur.fetchall()
        for (book_id, _), (stu_id, stu_code) in zip(book_rows, student_rows):
            issue_date = datetime.today().strftime("%Y-%m-%d")
            due_date = (datetime.today() + timedelta(days=7)).strftime("%Y-%m-%d")
            cur.execute("""
                INSERT INTO library_issues (
                    fk_book_id, fk_student_id, issue_date, due_date, return_date
                ) VALUES (?, ?, ?, ?, ?)
            """, (book_id, stu_id, issue_date, due_date, None))
        print("✅ Library issues seeded.")

    conn.commit()
    conn.close()


def seed_health_admissions_leave():
    """
    Seed student health, admissions, and leave requests (2–3 rows each).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Student health (3)
    cur.execute("SELECT COUNT(*) FROM student_health")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, student_id, student_name FROM users WHERE role='Student' LIMIT 3")
        for uid, sid, sname in cur.fetchall():
            cur.execute("""
                INSERT INTO student_health(
                    fk_student_id, student_id, student_name, blood_group, height, weight, notes, doctor_name, checkup_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, sid, sname, random.choice(["A+", "B+", "O+", "AB+"]), 140+random.randint(0,40), 35+random.randint(0,15),
                  "General check-up", "Dr. Rao", datetime.today().strftime("%Y-%m-%d")))
        print("✅ Student health seeded.")

    # Admissions (3)
    cur.execute("SELECT COUNT(*) FROM admissions")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        sch_id = cur.fetchone()[0]
        applicants = [
            ("APP001", "Ravi Kumar", "2014-05-10", "9001110001", "5", "Under Review"),
            ("APP002", "Sita Devi", "2013-07-20", "9001110002", "6", "Approved"),
            ("APP003", "Aman Singh", "2015-09-01", "9001110003", "4", "Rejected"),
        ]
        for app_id, name, dob, contact, applied_class, status in applicants:
            cur.execute("""
                INSERT INTO admissions(
                    fk_school_id, fk_student_id, student_id, student_name, dob, contact, applied_class, status, date_applied, documents_path
                ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, date('now'), NULL)
            """, (sch_id, app_id, name, dob, contact, applied_class, status))
        print("✅ Admissions seeded.")

    # Leave requests (3)
    cur.execute("SELECT COUNT(*) FROM leave_requests")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, student_id FROM users WHERE role='Student' LIMIT 3")
        students = cur.fetchall()
        cur.execute("SELECT id, student_id FROM users WHERE role='Teacher' LIMIT 1")
        reviewer = cur.fetchone()
        reviewer_id = reviewer[0] if reviewer else None
        reviewer_code = reviewer[1] if reviewer else None
        for uid, sid in students:
            from_d = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
            to_d = (datetime.today() + timedelta(days=2)).strftime("%Y-%m-%d")
            cur.execute("""
                INSERT INTO leave_requests(
                    fk_student_id, fk_reviewed_by_id, student_id, from_date, to_date, reason, status, reviewed_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, reviewer_id, sid, from_d, to_d, "Medical", random.choice(["Pending", "Approved", "Rejected"]), reviewer_code))
        print("✅ Leave requests seeded.")

    conn.commit()
    conn.close()


def seed_staff_and_attendance():
    """
    Seed staff (3) and staff attendance (2–3 rows).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Staff (3)
    cur.execute("SELECT COUNT(*) FROM staff")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        sch_id = cur.fetchone()[0]
        staff_rows = [
            (sch_id, "Anil Kumar", "Clerk", "9002220001", "clerk1@school.com", (datetime.today()-timedelta(days=400)).strftime("%Y-%m-%d")),
            (sch_id, "Sunita Rani", "Librarian", "9002220002", "lib1@school.com", (datetime.today()-timedelta(days=300)).strftime("%Y-%m-%d")),
            (sch_id, "Manoj Verma", "Peon", "9002220003", "peon1@school.com", (datetime.today()-timedelta(days=200)).strftime("%Y-%m-%d")),
        ]
        cur.executemany("""
            INSERT INTO staff(fk_school_id, name, role, phone, email, join_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, staff_rows)
        print("✅ Staff seeded.")

    # Staff attendance (3 for first staff)
    cur.execute("SELECT COUNT(*) FROM staff_attendance")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT staff_id FROM staff ORDER BY staff_id LIMIT 1")
        row = cur.fetchone()
        if row:
            stf_id = row[0]
            days = [0, 1, 2]
            for d in days:
                date_str = (datetime.today()-timedelta(days=d)).strftime("%Y-%m-%d")
                cur.execute("""
                    INSERT INTO staff_attendance(fk_staff_id, staff_id, date, status)
                    VALUES (?, ?, ?, ?)
                """, (stf_id, stf_id, date_str, random.choice(["Present", "Absent", "On Leave"])))
        print("✅ Staff attendance seeded.")

    conn.commit()
    conn.close()


def seed_school_front_office():
    """
    Seed school_settings, visitor_log, and enquiries (2–3 rows).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Settings (3)
    cur.execute("SELECT COUNT(*) FROM school_settings")
    if cur.fetchone()[0] == 0:
        settings = [
            ("school_name", "Demo School"),
            ("session_year", "2024-2025"),
            ("contact_email", "admin@school.com"),
        ]
        cur.executemany("INSERT OR REPLACE INTO school_settings(key, value) VALUES (?, ?)", settings)
        print("✅ School settings seeded.")

    # Visitor log (3)
    cur.execute("SELECT COUNT(*) FROM visitor_log")
    if cur.fetchone()[0] == 0:
        now = datetime.now()
        rows = [
            ("Parent - Ravi", "Meeting", now.strftime("%Y-%m-%d 09:00"), now.strftime("%Y-%m-%d 09:30")),
            ("Vendor - Books", "Delivery", now.strftime("%Y-%m-%d 10:15"), now.strftime("%Y-%m-%d 10:45")),
            ("Guest Speaker", "Seminar", now.strftime("%Y-%m-%d 12:00"), now.strftime("%Y-%m-%d 13:00")),
        ]
        cur.executemany("""
            INSERT INTO visitor_log(name, purpose, in_time, out_time)
            VALUES (?, ?, ?, ?)
        """, rows)
        print("✅ Visitor log seeded.")

    # Enquiries (3)
    cur.execute("SELECT COUNT(*) FROM enquiries")
    if cur.fetchone()[0] == 0:
        rows = [
            ("Sanjay", "9003330001", "Admission for Class 3", (datetime.today()+timedelta(days=2)).strftime("%Y-%m-%d")),
            ("Priya", "9003330002", "Transport facility details", (datetime.today()+timedelta(days=1)).strftime("%Y-%m-%d")),
            ("Kiran", "9003330003", "Fee structure enquiry", (datetime.today()+timedelta(days=3)).strftime("%Y-%m-%d")),
        ]
        cur.executemany("""
            INSERT INTO enquiries(name, contact, query, follow_up_date)
            VALUES (?, ?, ?, ?)
        """, rows)
        print("✅ Enquiries seeded.")

    conn.commit()
    conn.close()


def seed_achievements_and_principal_notes():
    """
    Seed achievements (2–3 rows) and principal notes (2–3).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Achievements (3)
    cur.execute("SELECT COUNT(*) FROM achievements")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, student_id FROM users WHERE role='Student' LIMIT 3")
        students = cur.fetchall()
        for uid, sid in students:
            cur.execute("""
                INSERT INTO achievements(
                    fk_student_id, student_id, title, description, date, issued_by, fk_issued_by_id
                ) VALUES (?, ?, ?, ?, ?, ?, NULL)
            """, (uid, sid, "Merit Certificate", "Outstanding performance", datetime.today().strftime("%Y-%m-%d"), "School"))
        print("✅ Achievements seeded.")

    # Principal notes (3)
    cur.execute("SELECT COUNT(*) FROM principal_notes")
    if cur.fetchone()[0] == 0:
        notes = [
            ("Maintain discipline and punctuality.",),
            ("Encourage reading habits among students.",),
            ("Upcoming cultural fest preparations underway.",),
        ]
        cur.executemany("INSERT INTO principal_notes(note) VALUES (?)", notes)
        print("✅ Principal notes seeded.")

    conn.commit()
    conn.close()

def seed_notices_homework_syllabus_timetable():
    """
    Seed notices (3+), timetable (full week), homework (3+), syllabus (3+),
    plus exam & PTM schedules for testing.
    """
    conn = get_connection()
    cur = conn.cursor()

    # -------------------
    # Notices (at least 3)
    # -------------------
    cur.execute("SELECT COUNT(*) FROM notices")
    if cur.fetchone()[0] == 0:
        notices = [
            ("Welcome back to school!", "System"),
            ("PTM this Saturday", "System"),
            ("Submit homework on time", "System")
        ]
        cur.execute("SELECT id FROM schools ORDER BY id LIMIT 1")
        sch = cur.fetchone()
        fk_school_id = sch[0] if sch else None
        fk_class_id = None
        if fk_school_id:
            fk_class_id = _get_class_id(cur, fk_school_id, "1", "A")

        for msg, created_by in notices:
            cur.execute("""
                INSERT INTO notices(
                    fk_school_id, fk_class_id, fk_created_by_id,
                    title, message, class, section, created_by, expiry_date, timestamp
                ) VALUES (?, ?, NULL, ?, ?, NULL, NULL, ?, NULL, datetime('now'))
            """, (fk_school_id, fk_class_id, msg, msg, created_by))
        print("✅ Notices seeded.")

    # -------------------
    # Homework (3+)
    # -------------------
    cur.execute("SELECT COUNT(*) FROM homework")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, fk_school_id, class_name, section FROM classes LIMIT 3")
        for cls_id, school_id, class_name, section in cur.fetchall():
            for subj in ["English", "Maths", "Science"]:
                due_date = (datetime.today() + timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d")
                cur.execute("""
                    INSERT INTO homework(
                        fk_school_id, fk_class_id, fk_assigned_by_id,
                        class, section, subject, description, due_date, file_url, assigned_by
                    ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, NULL, ?)
                """, (school_id, cls_id, class_name, section, subj,
                      f"{subj} chapter practice", due_date, "teacher@school.com"))
        print("✅ Homework seeded.")

    # -------------------
    # Syllabus (3+)
    # -------------------
    cur.execute("SELECT COUNT(*) FROM syllabus")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, fk_school_id, class_name, section FROM classes LIMIT 3")
        for cls_id, school_id, class_name, section in cur.fetchall():
            for subj in ["English", "Maths", "Science"]:
                cur.execute("""
                    INSERT INTO syllabus(
                        fk_school_id, fk_class_id, fk_uploaded_by_id,
                        class, section, subject, syllabus_text, file_url, uploaded_by
                    ) VALUES (?, ?, NULL, ?, ?, ?, ?, NULL, ?)
                """, (school_id, cls_id, class_name, section, subj,
                      f"Syllabus outline for {subj} ({class_name}{section})", "teacher@school.com"))
        print("✅ Syllabus seeded.")




    conn.commit()
    conn.close()


# ensure you have a hash_password() same as elsewhere in your codebase
def _hash(pw: str) -> str:
    import hashlib
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def seed_default_admin(school_id: int):
    email = "admin@school.com"
    default_pw = _hash("admin123")  # hash to match your existing scheme
    
    conn = get_connection()
    cur = conn.cursor()

    # 1) If this email already exists for this school, just ensure role is Admin
    cur.execute("SELECT id, role FROM users WHERE fk_school_id=? AND email=?", (school_id, email))
    row = cur.fetchone()
    if row:
        user_id, role = row
        # If role differs, promote to Admin (don’t clobber name/id unless you want to)
        if role != "Admin":
            cur.execute("UPDATE users SET role='Admin' WHERE id=?", (user_id,))
        # (optional) reset password:
        # cur.execute("UPDATE users SET password=? WHERE id=?", (default_pw, user_id))
        print(f"ℹ️ Using existing '{email}' as Admin (user_id={user_id}).")
        return

    # 2) Otherwise insert a fresh Admin
    cur.execute("""
        INSERT INTO users(
            fk_school_id, student_id, student_name, name, email, password, role
        ) VALUES (?, ?, ?, ?, ?, ?, 'Admin')
    """, (school_id, "ADMIN01", "Admin User", "Admin User", email, default_pw))
    print("✅ Default admin created: admin@school.com / admin123")
    
    conn.commit()
    conn.close()

def _romanize(cls: str) -> str:
    to_roman = {"1":"I","2":"II","3":"III","4":"IV","5":"V","6":"VI","7":"VII","8":"VIII","9":"IX","10":"X"}
    c = str(cls or "").strip().upper().replace("CLASS ","")
    return to_roman.get(c, c)



# -------------------------
# Bootstrap
# -------------------------
# Create the DB file if it doesn't exist (so SQLite can open it)
if not os.path.exists(DB_PATH):
    open(DB_PATH, "w").close()

# 1) Create schema
init_db()

# 2) Seed everything (idempotent-ish: most run only if empty)
_demo_school_id = _ensure_demo_school_and_classes()
seed_default_fees(_demo_school_id)
seed_sample_users(_demo_school_id)
seed_default_subjects()

# Academic + fee/attendance-related bulk demo data
seed_random_marks_attendance_payments()

# Notices / homework / syllabus / timetable
seed_notices_homework_syllabus_timetable()

# Assignments / exams / results
seed_assignments_exams_and_results()

# The rest: make sure every table has 2–3+ rows
seed_messages_and_whatsapp_logs()
seed_gallery_content_events_website()
seed_transport()
seed_library()
seed_health_admissions_leave()
seed_staff_and_attendance()
seed_school_front_office()
seed_achievements_and_principal_notes()
seed_default_admin(_demo_school_id)
seed_notices_homework_syllabus_timetable()
# End of file
