import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import date
from db import get_connection, add_mark

# =========================
# 🔹 Role Check
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
menu = st.sidebar.radio(
    "📌 Navigation",
    ["Marks Update", "Attendance Update", "Timetable", "Logout"]
)

# =========================
# 🔹 Logout
# =========================
if menu == "Logout":
    st.session_state.clear()
    st.success("✅ Logged out successfully!")
    st.rerun()

# =========================
# 🔹 DB Connection
# =========================
conn = get_connection()
cur = conn.cursor()

# =========================
# 🔹 Common: Fetch Class & Section
# =========================
cur.execute("SELECT DISTINCT class FROM users WHERE role='Student' ORDER BY class")
classes = [row[0] for row in cur.fetchall() if row[0]]

if not classes:
    st.warning("⚠️ No students found. Please add students first in Admin Dashboard.")
    st.stop()

class_choice = st.selectbox("Select Class", classes, key="class_choice")

cur.execute(
    "SELECT DISTINCT section FROM users WHERE role='Student' AND class=? ORDER BY section",
    (class_choice,),
)
sections = [row[0] for row in cur.fetchall() if row[0]]

if sections:
    section_choice = st.selectbox("Select Section", sections, key="section_choice")
else:
    section_choice = None
    st.warning("⚠️ No sections available for this class.")
    st.stop()

# =========================
# 🔹 Marks Update
# =========================
if menu == "Marks Update":
    subjects_file = os.path.join(os.path.dirname(__file__), "..", "data", "subjects.txt")
    if os.path.exists(subjects_file):
        with open(subjects_file, "r") as f:
            subjects = [line.strip() for line in f if line.strip()]
    else:
        subjects = ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]

    cur.execute(
        """
        SELECT student_id, student_name 
        FROM users 
        WHERE role='Student' AND class=? AND section=? 
        ORDER BY student_name
        """,
        (class_choice, section_choice),
    )
    students = cur.fetchall()

    if not students:
        st.warning("⚠️ No students found in this Class & Section.")
        st.stop()

    student_names = [f"{s[1]} ({s[0]})" for s in students]
    student_choice = st.selectbox("Select Student", student_names, key="student_choice")

    student_id = student_choice.split("(")[-1].replace(")", "").strip()

    subject_choice = st.selectbox("Select Subject", subjects, key="subject_choice")
    marks = st.number_input("Enter Marks", 0, 100, key="marks_input")

    if st.button("✅ Submit Marks"):
        cur.execute(
            """
            SELECT 1 FROM marks 
            WHERE student_id=? AND subject=? AND submitted_by=?
            """,
            (student_id, subject_choice, st.session_state["user"]["email"]),
        )

        if cur.fetchone():
            st.warning("⚠️ Marks for this student & subject already submitted by you.")
        else:
            add_mark(
                student_id,
                subject_choice,
                marks,
                st.session_state["user"]["email"],
                class_choice,
                section_choice,
            )
            st.success(f"✅ Marks submitted for {student_choice} in {subject_choice}: {marks}")

            try:
                from gupshup_sender import notify_student_mark

                notify_student_mark(student_id, subject_choice, marks)
            except Exception as e:
                st.info(f"ℹ️ WhatsApp notification skipped: {e}")

            st.rerun()

    # View Marks
    st.subheader("📋 Marks Submitted by You")
    cur.execute(
        """
        SELECT student_id, subject, marks, class, section, timestamp
        FROM marks
        WHERE submitted_by=?
        ORDER BY timestamp DESC
        """,
        (st.session_state["user"]["email"],),
    )
    marks_data = cur.fetchall()

    if marks_data:
        marks_df = pd.DataFrame(
            marks_data,
            columns=["Student ID", "Subject", "Marks", "Class", "Section", "Submitted On"],
        )
        st.dataframe(marks_df, use_container_width=True)
    else:
        st.info("ℹ️ No marks submitted yet.")

# =========================
# 🔹 Attendance Update
# =========================
elif menu == "Attendance Update":
    st.subheader("📅 Mark Attendance")
    attendance_date = st.date_input("Select Date", value=date.today(), key="attendance_date")

    cur.execute(
        """
        SELECT student_id, student_name 
        FROM users 
        WHERE role='Student' AND class=? AND section=? 
        ORDER BY student_name
        """,
        (class_choice, section_choice),
    )
    attendance_students = cur.fetchall()

    if attendance_students:
        st.write("Select attendance for each student:")
        attendance_status = {}
        for sid, sname in attendance_students:
            attendance_status[sid] = st.selectbox(
                f"{sname} ({sid})",
                ["Present", "Absent", "Late"],
                key=f"att_{sid}_{attendance_date}",
            )

        if st.button("✅ Submit Attendance"):
            for sid, status in attendance_status.items():
                try:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO attendance(student_id, date, status, submitted_by)
                        VALUES (?, ?, ?, ?)
                        """,
                        (sid, attendance_date.isoformat(), status, st.session_state["user"]["email"]),
                    )

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
# 🔹 Timetable View
# =========================
elif menu == "Timetable":
    st.subheader("🗓️ View Timetable")

    cur.execute(
        """
        SELECT day, period1, period2, period3, period4, period5, period6, period7
        FROM timetable
        WHERE class=? AND section=?
        ORDER BY 
            CASE day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                ELSE 7
            END
        """,
        (class_choice, section_choice),
    )
    tt_data = cur.fetchall()

    if tt_data:
        columns = ["Day", "Period 1", "Period 2", "Period 3", "Period 4", "Period 5", "Period 6", "Period 7"]
        tt_df = pd.DataFrame(tt_data, columns=columns)
        st.dataframe(tt_df, use_container_width=True)
    else:
        st.info("ℹ️ No timetable uploaded for this Class & Section yet.")

conn.close()
