import streamlit as st
import hashlib
import sqlite3
import os

DB_FILE = os.path.join(os.getcwd(), "school.db")

# =========================
# 🔹 Ensure DB Initialization
# =========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
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
            period INTEGER,
            subject TEXT,
            teacher_email TEXT
        )
    """)

    # ✅ Insert default admin if not exists
    cur.execute("SELECT 1 FROM users WHERE role='Admin' LIMIT 1")
    if not cur.fetchone():
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        cur.execute("""
            INSERT INTO users (student_name, email, password, role)
            VALUES ('Admin User', 'admin@school.com', ?, 'Admin')
        """, (admin_pw,))
        print("✅ Default admin created: admin@school.com / admin123")

    conn.commit()
    conn.close()


# =========================
# 🔹 DB Connection
# =========================
def get_connection():
    return sqlite3.connect(DB_FILE)


# =========================
# 🔹 Streamlit App
# =========================
st.set_page_config(page_title="School Management", layout="wide")

# Auto-initialize DB
init_db()

def login():
    st.title("🎓 School Management Login")

    role_choice = st.radio("Login as", ["Admin", "Teacher", "Student"])
    
    if role_choice == "Student":
        user_id = st.text_input("Student ID")
    else:
        user_id = st.text_input("Email")

    password = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = get_connection()
        cur = conn.cursor()
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

        if role_choice == "Student":
            cur.execute(
                "SELECT * FROM users WHERE student_id=? AND password=? AND role='Student'",
                (user_id, hashed_pw)
            )
        else:
            cur.execute(
                "SELECT * FROM users WHERE email=? AND password=? AND role=?",
                (user_id, hashed_pw, role_choice)
            )

        user = cur.fetchone()
        conn.close()

        if user:
            st.session_state["user"] = {
                "student_id": user[1],
                "student_name": user[2],
                "email": user[3],
                "role": user[5],
                "class": user[6],
                "section": user[7],
            }
            st.success(f"✅ Logged in as {role_choice}")
            st.switch_page(f"pages/{role_choice}_Dashboard.py")
        else:
            st.error("❌ Invalid credentials")


if "user" not in st.session_state:
    login()
else:
    role = st.session_state["user"]["role"]
    st.switch_page(f"pages/{role}_Dashboard.py")
