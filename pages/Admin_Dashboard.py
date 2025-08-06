import streamlit as st
import sqlite3
import pandas as pd
from db import get_connection
from datetime import datetime

# =========================
# 🔹 Admin Role Check
# =========================
if "user" not in st.session_state:
    st.error("❌ Please login first!")
    st.stop()
elif st.session_state["user"]["role"] != "Admin":
    st.error("⛔ Access Denied: Admins only")
    st.stop()

st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("🛠️ Admin Dashboard")

# =========================
# 🔹 Sidebar Navigation
# =========================
st.sidebar.title("🛠️ Admin Panel")
menu = st.sidebar.radio(
    "Navigation",
    [
        "Manage Users",
        "View Marks",
        "View Attendance",
        "Broadcast Notices"
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

# =========================
# 🔹 1. Manage Users
# =========================
if menu == "Manage Users":
    st.subheader("👥 Manage Users")

    cur.execute("SELECT id, student_id, student_name, email, role, class, section, student_phone, parent_phone FROM users ORDER BY role, class, section, student_name")
    users_data = cur.fetchall()

    if users_data:
        df_users = pd.DataFrame(
            users_data,
            columns=["ID", "Student ID", "Student Name", "Email", "Role", "Class", "Section", "Student Phone", "Parent Phone"]
        )
        st.dataframe(df_users, use_container_width=True)
    else:
        st.info("ℹ️ No users found in the system.")

    st.markdown("---")
    st.subheader("➕ Add New Student")
    student_id = st.text_input("Student ID (e.g., STU004)")
    student_name = st.text_input("Student Name")
    student_email = st.text_input("Student Email")
    student_class = st.text_input("Class (e.g., 6)")
    student_section = st.text_input("Section (e.g., A)")
    student_phone = st.text_input("Student WhatsApp No (+91...)")
    parent_phone = st.text_input("Parent WhatsApp No (+91...)")

    if st.button("✅ Add Student"):
        if not all([student_id, student_name, student_class, student_section]):
            st.warning("⚠️ Please fill all required fields.")
        else:
            try:
                cur.execute("""
                    INSERT INTO users (student_id, student_name, email, role, class, section, student_phone, parent_phone, password)
                    VALUES (?, ?, ?, 'Student', ?, ?, ?, ?, ?)
                """, (student_id, student_name, student_email or None, student_class, student_section, student_phone, parent_phone, "student123"))
                conn.commit()
                st.success(f"✅ Student {student_name} ({student_id}) added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error adding student: {e}")

# =========================
# 🔹 2. View Marks
# =========================
elif menu == "View Marks":
    st.subheader("📚 View All Marks")

    cur.execute("""
        SELECT student_id, subject, marks, class, section, submitted_by, timestamp
        FROM marks
        ORDER BY timestamp DESC
    """)
    marks_data = cur.fetchall()

    if marks_data:
        df_marks = pd.DataFrame(
            marks_data,
            columns=["Student ID", "Subject", "Marks", "Class", "Section", "Submitted By", "Submitted On"]
        )
        st.dataframe(df_marks, use_container_width=True)
    else:
        st.info("ℹ️ No marks data found.")

# =========================
# 🔹 3. View Attendance
# =========================
elif menu == "View Attendance":
    st.subheader("📅 View Attendance Records")

    cur.execute("""
        SELECT student_id, date, status, submitted_by
        FROM attendance
        ORDER BY date DESC
    """)
    attendance_data = cur.fetchall()

    if attendance_data:
        df_attendance = pd.DataFrame(
            attendance_data,
            columns=["Student ID", "Date", "Status", "Marked By"]
        )
        st.dataframe(df_attendance, use_container_width=True)
    else:
        st.info("ℹ️ No attendance data found.")

# =========================
# 🔹 4. Broadcast Notices
# =========================
elif menu == "Broadcast Notices":
    st.subheader("📢 Broadcast a School Notice")
    notice_title = st.text_input("Notice Title")
    notice_message = st.text_area("Notice Message")

    if st.button("📨 Send Notice to All"):
        if not notice_title or not notice_message:
            st.warning("⚠️ Please enter both title and message.")
        else:
            try:
                from gupshup_sender import broadcast_notice
                broadcast_notice(notice_title, notice_message)
                st.success("✅ Notice broadcasted to all students & parents via WhatsApp.")
            except Exception as e:
                st.error(f"❌ Error sending notice: {e}")

# =========================
# 🔹 Close DB
# =========================
conn.close()
