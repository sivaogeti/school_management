import streamlit as st
import sqlite3
import pandas as pd
from db import get_connection

# =========================
# 🔹 Student Role Check
# =========================
if "user" not in st.session_state:
    st.error("❌ Please login first!")
    st.stop()
elif st.session_state["user"]["role"] != "Student":
    st.error("⛔ Access Denied: Students only")
    st.stop()

st.set_page_config(page_title="Student Dashboard", layout="wide")
st.title("🎓 Student Dashboard")

# =========================
# 🔹 Sidebar Navigation
# =========================
st.sidebar.title("🎓 Student Panel")
menu = st.sidebar.radio(
    "Navigation",
    [
        "My Marks",
        "My Attendance"
    ]
)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.success("Logged out successfully!")
    st.rerun()

# =========================
# 🔹 DB Connection
# =========================
conn = get_connection()
cur = conn.cursor()

student_id = st.session_state["user"]["student_id"]

# =========================
# 🔹 1. My Marks
# =========================
if menu == "My Marks":
    st.subheader("📚 My Marks")

    cur.execute("""
        SELECT subject, marks, class, section, submitted_by, timestamp
        FROM marks
        WHERE student_id=?
        ORDER BY timestamp DESC
    """, (student_id,))
    marks_data = cur.fetchall()

    if marks_data:
        df_marks = pd.DataFrame(
            marks_data,
            columns=["Subject", "Marks", "Class", "Section", "Submitted By", "Submitted On"]
        )
        st.dataframe(df_marks, use_container_width=True)
    else:
        st.info("ℹ️ No marks submitted yet.")

# =========================
# 🔹 2. My Attendance
# =========================
elif menu == "My Attendance":
    st.subheader("📅 My Attendance Records")

    cur.execute("""
        SELECT date, status, submitted_by
        FROM attendance
        WHERE student_id=?
        ORDER BY date DESC
    """, (student_id,))
    attendance_data = cur.fetchall()

    if attendance_data:
        df_attendance = pd.DataFrame(
            attendance_data,
            columns=["Date", "Status", "Marked By"]
        )
        st.dataframe(df_attendance, use_container_width=True)
    else:
        st.info("ℹ️ No attendance records found.")

# =========================
# 🔹 Close DB
# =========================
conn.close()
