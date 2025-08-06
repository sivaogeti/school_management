import streamlit as st
import sqlite3
import hashlib

DB_PATH = "data/school.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def create_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users(
                    email TEXT PRIMARY KEY,
                    password TEXT,
                    role TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS marks(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_email TEXT,
                    subject TEXT,
                    marks INTEGER,
                    submitted_by TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS notices(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    message TEXT,
                    created_by TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login():
    create_tables()
    st.sidebar.header("Login")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT role, password FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        conn.close()
        if row and row[1] == hash_password(password):
            st.session_state["user"] = {"email": email, "role": row[0].capitalize()}
            st.rerun()
        else:
            st.sidebar.error("Invalid credentials")

    if "user" in st.session_state:
        role = st.session_state["user"]["role"]
        st.success(f"Logged in as {role}")
        if role == "Admin":
            st.switch_page("pages/Admin_Dashboard.py")
        elif role == "Teacher":
            st.switch_page("pages/Teacher_Dashboard.py")
        else:
            st.switch_page("pages/Student_Dashboard.py")
