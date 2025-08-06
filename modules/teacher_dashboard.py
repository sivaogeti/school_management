import streamlit as st
import pandas as pd
from datetime import date
from db import get_connection, add_mark
import os

def render_teacher_dashboard(user):
    st.title("👩‍🏫 Teacher Dashboard")

    conn = get_connection()
    cur = conn.cursor()

    # ---------------------
    # Sidebar menu (unique key to avoid clashes)
    # ---------------------
    st.sidebar.subheader("Teacher Options")
    option = st.sidebar.radio(
        "Choose Action",
        ["Submit Marks", "Mark Attendance", "My Submissions"],
        key="teacher_menu_radio"
    )

    # ---------------------
    # Dynamic class & section lists
    # ---------------------
    cur.execute("SELECT DISTINCT class FROM users WHERE role='Student' ORDER BY class")
    classes = [row[0] for row in cur.fetchall() if row[0]]

    if not classes:
        st.warning("⚠️ No students found. Please add students first in Admin Dashboard.")
        conn.close()
        return

    class_choice = st.selectbox("Select Class", classes, key="teacher_class_select")

    cur.execute(
        "SELECT DISTINCT section FROM users WHERE role='Student' AND class=? ORDER BY section",
        (class_choice,),
    )
    sections = [row[0] for row in cur.fetchall() if row[0]]
    if not sections:
        st.warning("⚠️ No sections available for this class.")
        conn.close()
        return

    section_choice = st.selectbox("Select Section", sections, key="teacher_section_select")

    # ---------------------
    # 1️⃣ Submit Marks
    # ---------------------
    if option == "Submit Marks":
        st.subheader("📝 Submit Marks")

        cur.execute("""
            SELECT student_id, student_name 
            FROM users 
            WHERE role='Student' AND class=? AND section=? 
            ORDER BY student_name
        """, (class_choice, section_choice))
        students = cur.fetchall()

        if not students:
            st.warning("⚠️ No students in this Class & Section.")
            conn.close()
            return

        student_choice = st.selectbox(
            "Select Student",
            [f"{s[1]} ({s[0]})" for s in students],
            key="teacher_student_select"
        )
        student_id = student_choice.split("(")[-1].replace(")", "").strip()

        # Load subjects dynamically
        subjects_file = os.path.join(os.path.dirname(__file__), "..", "data", "subjects.txt")
        if os.path.exists(subjects_file):
            with open(subjects_file, "r") as f:
                subjects = [line.strip() for line in f if line.strip()]
        else:
            subjects = ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]

        subject_choice = st.selectbox("Select Subject", subjects, key="teacher_subject_select")
        marks = st.number_input("Enter Marks", 0, 100, key="teacher_marks_input")

        if st.button("✅ Submit Marks", key="teacher_submit_marks_btn"):
            cur.execute("""
                SELECT 1 FROM marks 
                WHERE student_id=? AND subject=? AND submitted_by=?
            """, (student_id, subject_choice, user["email"]))
            
            if cur.fetchone():
                st.warning("⚠️ Marks already submitted by you for this student & subject.")
            else:
                add_mark(student_id, subject_choice, marks, user["email"], class_choice, section_choice)
                st.success(f"✅ Marks submitted for {student_choice} in {subject_choice}: {marks}")

                # Optional WhatsApp Notification
                try:
                    from gupshup_sender import notify_student_mark
                    notify_student_mark(student_id, subject_choice, marks)
                except ImportError:
                    pass  # safe fallback

    # ---------------------
    # 2️⃣ Attendance
    # ---------------------
    elif option == "Mark Attendance":
        st.subheader("📅 Mark Attendance")
        attendance_date = st.date_input("Select Date", value=date.today(), key="teacher_att_date")

        cur.execute("""
            SELECT student_id, student_name 
            FROM users 
            WHERE role='Student' AND class=? AND section=? 
            ORDER BY student_name
        """, (class_choice, section_choice))
        students = cur.fetchall()

        if not students:
            st.warning("⚠️ No students to mark attendance.")
            conn.close()
            return

        attendance_status = {}
        for sid, sname in students:
            attendance_status[sid] = st.selectbox(
                f"{sname} ({sid})",
                ["Present", "Absent", "Late"],
                key=f"teacher_att_{sid}_{attendance_date}"
            )

        if st.button("✅ Submit Attendance", key="teacher_submit_attendance_btn"):
            for sid, status in attendance_status.items():
                cur.execute("""
                    INSERT OR REPLACE INTO attendance(student_id, date, status, submitted_by)
                    VALUES (?, ?, ?, ?)
                """, (sid, attendance_date.isoformat(), status, user["email"]))

                # Optional WhatsApp notify parents if Absent
                if status == "Absent":
                    try:
                        from gupshup_sender import notify_attendance
                        notify_attendance(sid, status, attendance_date.isoformat())
                    except ImportError:
                        pass

            conn.commit()
            st.success(f"✅ Attendance marked for {attendance_date}")

    # ---------------------
    # 3️⃣ My Submissions
    # ---------------------
    elif option == "My Submissions":
        st.subheader("📋 Marks Submitted by You")
        cur.execute("""
            SELECT student_id, subject, marks, class, section, timestamp
            FROM marks
            WHERE submitted_by=?
            ORDER BY timestamp DESC
        """, (user["email"],))
        marks_data = cur.fetchall()
        df = pd.DataFrame(marks_data, columns=["Student ID", "Subject", "Marks", "Class", "Section", "Submitted On"])
        st.dataframe(df, use_container_width=True)

        st.subheader("📋 Attendance Submitted by You")
        cur.execute("""
            SELECT student_id, date, status
            FROM attendance
            WHERE submitted_by=?
            ORDER BY date DESC
        """, (user["email"],))
        att_data = cur.fetchall()
        df = pd.DataFrame(att_data, columns=["Student ID", "Date", "Status"])
        st.dataframe(df, use_container_width=True)

    conn.close()