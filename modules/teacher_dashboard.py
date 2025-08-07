import streamlit as st
import sqlite3
import os
from datetime import datetime
import random
import pandas as pd
from gupshup_sender import notify_attendance

# --------------------
# DB Connection Helper
# --------------------
def get_connection():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # goes up one level
    db_path = os.path.join(base_dir, "data", "school.db")
    return sqlite3.connect(db_path, check_same_thread=False)


# --------------------
# Main Teacher Dashboard
# --------------------
def render_teacher_dashboard(user):
    st.title("👩‍🏫 Teacher Dashboard")

    email = user["email"]  # ✅ fix: extract string from dict
    teacher_class = user["class"]
    section = user["section"]

    conn = get_connection()
    cur = conn.cursor()

    # Get teacher info
    cur.execute("SELECT class, section FROM users WHERE email = ?", (email,))
    teacher_info = cur.fetchone()
    if not teacher_info:
        st.error("Teacher not found.")
        return

    class_name, section = teacher_info

    st.title(f"👨‍🏫 Teacher Dashboard — Class {class_name}{section}")

    # Sidebar Menu
    selected = st.sidebar.radio("📋 Menu", [
        "📄 View Submissions",
        "✅ Review Assignments",
        "📅 Upcoming Exams",
        "💸 View Fee Payments",
        "📚 View Class Students",
        "📆 Mark Attendance"
    ])

    # Count pending reviews
    cur.execute("""
        SELECT COUNT(*) FROM assignments 
        WHERE class=? AND section=? AND reviewed=0
    """, (class_name, section))
    pending_count = cur.fetchone()[0]

    if selected in ["\ud83d\udcc4 View Submissions", "\u2705 Review Assignments"]:
        badge_html = f"""
            <div style='background-color:#FF4B4B; color:white; 
            border-radius:12px; padding:4px 8px; display:inline-block;
            font-weight:bold; animation: pop 0.3s ease-out;'>
                {pending_count}
            </div>
            <style>
            @keyframes pop {{
                0% {{ transform: scale(1.2); }}
                100% {{ transform: scale(1); }}
            }}
            </style>
        """
        st.markdown(f"📬 Pending Reviews: {badge_html}", unsafe_allow_html=True)

    # Option 1 — View Submissions
    if selected == "📄 View Submissions":
        cur.execute("""
            SELECT a.id, a.student_id, u.student_name, a.subject, a.timestamp, a.reviewed 
            FROM assignments a 
            JOIN users u ON a.student_id = u.student_id 
            WHERE a.class=? AND a.section=?
            ORDER BY a.timestamp DESC
        """, (class_name, section))
        submissions = cur.fetchall()

        st.subheader("📄 Assignment Submissions")
        for sub in submissions:
            sub_id, sid, name, subject, date, reviewed = sub
            with st.expander(f"{name} ({sid}) — {subject}"):
                st.write(f"📅 Submitted on: {date}")
                st.write(f"✅ Reviewed: {'Yes' if reviewed else 'No'}")

    # Option 2 — Review Assignments
    elif selected == "✅ Review Assignments":
        st.subheader("🗘️ Review Pending Assignments")
        cur.execute("""
            SELECT a.id, a.student_id, u.student_name, a.subject, a.timestamp 
            FROM assignments a 
            JOIN users u ON a.student_id = u.student_id 
            WHERE a.class=? AND a.section=? AND a.reviewed=0
            ORDER BY a.timestamp ASC
        """, (class_name, section))
        pending = cur.fetchall()

        if not pending:
            st.success("🎉 All assignments reviewed!")
        else:
            for item in pending:
                aid, sid, name, subject, date = item
                with st.form(f"review_form_{aid}"):
                    st.markdown(f"**{name} ({sid}) — {subject}**")
                    st.write(f"📅 Submitted on: {date}")
                    remarks = st.text_area("Remarks", key=f"remarks_{aid}")
                    if st.form_submit_button("Mark as Reviewed ✅"):
                        cur.execute("UPDATE assignments SET reviewed=1 WHERE id=?", (aid,))
                        conn.commit()
                        st.success("Marked as reviewed.")
                        st.experimental_rerun()  # refresh

    # Option 3 — View Upcoming Exams
    elif selected == "📅 Upcoming Exams":
        st.subheader("📅 Exam Schedule")
        cur.execute("""
            SELECT subject, exam_date 
            FROM exams 
            WHERE class=? AND section=?
            ORDER BY exam_date
        """, (class_name, section))
        exams = cur.fetchall()

        if not exams:
            st.info("No upcoming exams scheduled.")
        else:
            for ex in exams:
                subject, ex_date = ex
                st.markdown(f"📘 **{subject}** — 🗓️ {ex_date}")

    # Option 4 — View Fee Payments
    elif selected == "💸 View Fee Payments":
        st.subheader("💸 Fee Payments by Students")
        cur.execute("""
            SELECT p.student_id, u.student_name, p.amount, p.method, p.date 
            FROM payments p
            JOIN users u ON p.student_id = u.student_id
            WHERE u.class=? AND u.section=? AND u.role='Student'
            ORDER BY p.date DESC
        """, (class_name, section))
        payments = cur.fetchall()

        if payments:
            df = pd.DataFrame(payments, columns=[
                "Student ID", "Student Name", "Amount (₹)", "Method", "Date"
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No payments found for your class.")

    # Option 5 — View Class Students
    elif selected == "📚 View Class Students":
        st.subheader("📚 Students in Your Class")
        cur.execute("""
            SELECT student_id, student_name, email, student_phone, parent_phone 
            FROM users 
            WHERE class=? AND section=? AND role='Student'
            ORDER BY student_id 
        """, (class_name, section))
        students = cur.fetchall()

        if students:
            df_students = pd.DataFrame(students, columns=[
                "Student ID", "Student Name", "Email", "Phone", "Parent Phone"
            ])
            st.dataframe(df_students, use_container_width=True)
        else:
            st.info("No students found in your class.")

    # Option 6 — Mark Attendance
    elif selected == "📆 Mark Attendance":
        st.subheader("📆 Mark Today's Attendance")
        today = datetime.today().strftime("%Y-%m-%d")
        st.write(f"Date: {today}")

        cur.execute("""
            SELECT student_id, student_name FROM users 
            WHERE class=? AND section=? AND role='Student'
            ORDER BY student_id
        """, (class_name, section))
        students = cur.fetchall()

        attendance_data = {}
        with st.form("attendance_form"):
            for sid, name in students:
                status = st.selectbox(
                    f"{name} ({sid})",
                    ["Present", "Absent"],
                    key=f"att_{sid}"
                )
                attendance_data[sid] = status
            if st.form_submit_button("📅 Submit Attendance"):
                for sid, status in attendance_data.items():
                    cur.execute("""
                        INSERT OR REPLACE INTO attendance (student_id, date, status, submitted_by)
                        VALUES (?, ?, ?, ?)
                    """, (sid, today, status, email))
                    conn.commit()

                    if status == "Absent":
                        #st.info("Whatsapp1- Calling whatsapp for student absent")
                        notify_attendance(sid, status, today)
                        #st.info("Whatsapp2- Calling whatsapp completed for student absent")

                st.success("✅ Attendance marked successfully!")

    conn.close()
