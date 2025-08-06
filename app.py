import streamlit as st
import os, hashlib
from db import get_connection, init_db

# Import dashboards
from modules.admin_dashboard import render_admin_dashboard
from modules.teacher_dashboard import render_teacher_dashboard
from modules.student_dashboard import render_student_dashboard

st.set_page_config(page_title="🏫 School Management", layout="wide")

DB_FILE = os.path.join(os.path.dirname(__file__), "data", "school.db")

# =========================
# Helpers
# =========================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(identifier: str, password: str, role: str):
    """Mixed login: Students by student_id, others by email"""
    conn = get_connection()
    cur = conn.cursor()

    if role == "Student":
        cur.execute(
            "SELECT * FROM users WHERE student_id=? AND password=? AND role=?",
            (identifier, hash_password(password), role)
        )
    else:
        cur.execute(
            "SELECT * FROM users WHERE email=? AND password=? AND role=?",
            (identifier, hash_password(password), role)
        )

    user = cur.fetchone()
    conn.close()
    return user

def create_default_admin():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO users (student_id, student_name, email, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "ADMIN001", "Super Admin", "admin@school.com",
            hash_password("admin123"), "Admin"
        ))
        conn.commit()
        st.sidebar.success("✅ Default admin created: admin@school.com / admin123")
    conn.close()

# =========================
# Init
# =========================
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
init_db()
create_default_admin()

# =========================
# Login Sidebar
# =========================
st.sidebar.title("🔐 Login")

if "user" not in st.session_state:
    with st.sidebar.form("login_form"):
        identifier = st.text_input("Email (Admin/Teacher) or Student ID")
        password = st.text_input("Password", type="password")
        role_choice = st.selectbox("Role", ["Admin", "Teacher", "Student"])
        login_btn = st.form_submit_button("Login")

    if login_btn:
        user = check_password(identifier.strip(), password.strip(), role_choice)
        if user:
            st.session_state["user"] = {
                "id": user[0],
                "student_id": user[1],
                "student_name": user[2],
                "email": user[3],
                "role": user[5],
                "class": user[6],       # ✅ Added
                "section": user[7]      # ✅ Added
            }
            st.sidebar.success(f"✅ Logged in as {role_choice}")
            st.rerun()
        else:
            st.sidebar.error("❌ Invalid credentials")
else:
    user = st.session_state["user"]
    st.sidebar.success(f"👋 Welcome {user['student_name'] or user['email']} ({user['role']})")
    if st.sidebar.button("Logout", key="logout_btn"):
        st.session_state.clear()
        st.experimental_set_query_params()  # Redirect to base
        st.rerun()

# =========================
# Main Content
# =========================
if "user" not in st.session_state:
    st.title("🏫 School Management System")
    st.info("Please login from the sidebar to continue.")
else:
    role = st.session_state["user"]["role"]
    if role == "Admin":
        render_admin_dashboard()
    elif role == "Teacher":
        render_teacher_dashboard(st.session_state["user"])
    elif role == "Student":
        render_student_dashboard(st.session_state["user"])
