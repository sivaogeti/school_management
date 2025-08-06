import streamlit as st
import hashlib
from db import get_connection

st.set_page_config(page_title="School Management", layout="wide")

# ======================
# LOGIN FUNCTION
# ======================
def login():
    st.title("🎓 School Management Login")

    role_choice = st.radio("Login as", ["Admin", "Teacher", "Student"])
    
    # Student logs in with Student ID, others with email
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
            # user tuple → (id, student_id, student_name, email, password, role, class, section)
            st.session_state["user"] = {
                "student_id": user[1],
                "student_name": user[2],
                "email": user[3],
                "role": user[5],
                "class": user[6],
                "section": user[7],
            }
            st.success(f"✅ Logged in as {role_choice}")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

# ======================
# PAGE ROUTING
# ======================
if "user" not in st.session_state:
    login()
else:
    role = st.session_state["user"]["role"]
    
    # Route to dashboards
    if role == "Admin":
        st.switch_page("pages/Admin_Dashboard.py")
    elif role == "Teacher":
        st.switch_page("pages/Teacher_Dashboard.py")
    else:
        st.switch_page("pages/Student_Dashboard.py")
