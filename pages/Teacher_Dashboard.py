import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import date
from db import get_connection, add_mark

# =========================
# 🔹 Teacher Role Check
# =========================
if "user" not in st.session_state:
    st.error("❌ Please login first!")
    st.stop()
elif st.session_state["user"]["role"] != "Teacher":
    st.error("⛔ Access Denied: Teachers only")
    st.stop()

st.set_page_config(page_title="Teacher Dashboard", layout="wide")
st.title("👩‍🏫 Teacher Dashboard")

# =========================
# 🔹 Sidebar Navigation
# =========================
st.sidebar.title("👩‍🏫 Teacher Panel")
menu = st.sidebar.radio(
    "Navigation",
    ["Marks Update", "Attendance Update"]
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
# 🔹 Load Subjects Dynamically
# =========================
subjects_file = os.path.join(os.path.dirname(__file__), "..", "data", "subjects.txt")
if os.path.exists(subjects_file):
    with open(subjects_file, "r") as f:
        subjects = [line.strip() for line in f if line.strip()]
else:
    subjects = ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]

# =========================
# 🔹 Common: Fetch Class & Section for Dropdowns
# =========================
cur.execute("SELECT DISTINCT class FROM users WHERE role='Student' ORDER BY class")
classes = [row[0] for row in cur.fetchall() if row[0]]

if not classes:
    st.warning("⚠️ No students found. Please add students first in Admin Dashboard.")
    st.stop()

class_choice = st.selectbox("Select Class", classes, key="class_choice")

cur.execute("SELECT DISTINCT section FROM users WHERE role='Student' AND class=? ORDER BY section", (class_choice,))
sections = [row[0] for row in cur.fetchall() if row[0]]

if sections:
    section_choice = st.selectbox("Select Section", sections, key="section_choice")
else:
    section_choice = None
    st.warning("⚠️ No sections available for this class.")
    st.stop()

# =========================
# 🔹 Menu 1: Marks Update
# =========================
if menu == "Marks Update":

    # Fetch students
    cur.execute("""
        SELECT student_id, student_name 
        FROM users 
        WHERE role='Student' AND class=? AND section=? 
        ORDER BY student_name
    """, (class_choice, section_choice))
    students = cur.fetchall()

    if not students:
        st.warning("⚠️ No students found in this Class & Section.")
        st.stop()

    student_names = [f"{s[1]} ({s[0]})" for s in students]
    student_choice = st.selectbox("Select Student", student_names, key="student_choice")

    student_id = student_choice.split("(")[-1].replace(")", "").strip()

    # Select Subject & Enter Marks
    subject_choice = st.selectbox("Select Subject", subjects, key="subject_choice")
    marks = st.number_input("Enter Marks", 0, 100, key="marks_input")

    # Submit Marks
    if st.button("✅ Submit Marks"):
        # Check duplicate marks
        cur.execute("""
            SELECT 1 FROM marks 
            WHERE student_id=? AND subject=? AND submitted_by=?
        """, (student_id, subject_choice, st.session_state["user"]["email"]))
        
        if cur.fetchone():
            st.warning("⚠️ Marks for this student & subject already submitted by you.")
        else:
            # Insert mark
            add_mark(student_id, subject_choice, marks, st.session_state["user"]["email"], class_choice, section_choice)
            st.success(f"✅ Marks submitted for {student_choice} in {subject_choice}: {marks}")

            # WhatsApp notification
            try:
                from gupshup_sender import notify_student_mark
                notify_student_mark(student_id, subject_choice, marks)
            except Exception as e:
                st.info(f"ℹ️ WhatsApp notification skipped: {e}")

            # Auto-clear form
            for key in ["student_choice", "subject_choice", "marks_input"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # View Marks Submitted
    st.subheader("📋 Marks Submitted by You")
    cur.execute("""
        SELECT student_id, subject, marks, class, section, timestamp
        FROM marks
        WHERE submitted_by=?
        ORDER BY timestamp DESC
    """, (st.session_state["user"]["email"],))
    marks_data = cur.fetchall()

    if marks_data:
        marks_df = pd.DataFrame(
            marks_data,
            columns=["Student ID", "Subject", "Marks", "Class", "Section", "Submitted On"]
        )
        st.dataframe(marks_df, use_container_width=True)
    else:
        st.info("ℹ️ No marks submitted yet.")


# =========================
# 🔹 Menu 2: Attendance Update
# =========================
elif menu == "Attendance Update":

    st.subheader("📅 Mark Attendance")
    attendance_date = st.date_input("Select Date", value=date.today(), key="attendance_date")

    # Fetch students for selected class & section
    cur.execute("""
        SELECT student_id, student_name 
        FROM users 
        WHERE role='Student' AND class=? AND section=? 
        ORDER BY student_name
    """, (class_choice, section_choice))
    attendance_students = cur.fetchall()

    if attendance_students:
        st.write("Select attendance for each student:")
        attendance_status = {}
        for sid, sname in attendance_students:
            attendance_status[sid] = st.selectbox(
                f"{sname} ({sid})",
                ["Present", "Absent", "Late"],
                key=f"att_{sid}_{attendance_date}"
            )

        if st.button("✅ Submit Attendance"):
            for sid, status in attendance_status.items():
                try:
                    cur.execute("""
                        INSERT OR REPLACE INTO attendance(student_id, date, status, submitted_by)
                        VALUES (?, ?, ?, ?)
                    """, (sid, attendance_date.isoformat(), status, st.session_state["user"]["email"]))
                    
                    # Notify parents if Absent
                    if status == "Absent":
                        try:
                            from gupshup_sender import notify_attendance
                            notify_attendance(sid, status, attendance_date.isoformat())
                        except Exception as e:
                            st.info(f"ℹ️ WhatsApp notification skipped: {e}")
                
                except Exception as e:
                    st.error(f"❌ Error saving attendance for {sid}: {e}")

            conn.commit()
            st.success(f"✅ Attendance marked for {attendance_date}")
           st.rerun()
    else:
        st.warning("⚠️ No students found for this Class & Section.")

# =========================
# 🔹 Close DB
# =========================
conn.close()
