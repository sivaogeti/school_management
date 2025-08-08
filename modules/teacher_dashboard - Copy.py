import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_connection
from gupshup_sender import (
    notify_attendance,
    notify_student_mark_bulk,
    send_gupshup_whatsapp,
    send_in_app_and_whatsapp_to_student
)

# --------------------
# Helper: fetch subjects dynamically
# --------------------
def get_subjects_for_class(cur, class_name, section):
    cur.execute(
        "SELECT subject_name FROM subjects WHERE class=? AND section=? ORDER BY id",
        (class_name, section)
    )
    rows = [r[0] for r in cur.fetchall()]
    return rows if rows else ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]

# --------------------
# Main Teacher Dashboard
# --------------------
def render_teacher_dashboard(user):
    email = user.get("email")
    conn = get_connection()
    cur = conn.cursor()

    # Get teacher info
    cur.execute("SELECT class, section FROM users WHERE email = ?", (email,))
    teacher_info = cur.fetchone()
    if not teacher_info:
        st.error("Teacher not found.")
        return

    class_name, section = teacher_info
    st.title(f"👩‍🏫 Teacher Dashboard — Class {class_name}{section}")

    # Sidebar Menu
    selected = st.sidebar.radio("📋 Menu", [
        "📄 View Submissions",
        "✅ Review Assignments",
        "📅 Upcoming Exams",
        "💸 View Fee Payments",
        "📚 View Class Students",
        "📆 Mark Attendance",
        "✏️ Submit Marks",
        "📢 WhatsApp Logs",
        "📨 Messages"  
    ])

    # Count pending reviews (keeps previous behavior)
    cur.execute("""
        SELECT COUNT(*) FROM assignments 
        WHERE class=? AND section=? AND reviewed=0
    """, (class_name, section))
    pending_count = cur.fetchone()[0]

    if selected in ["📄 View Submissions", "✅ Review Assignments"]:
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

    # -------------------
    # View Submissions
    # -------------------
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
        for sub_id, sid, name, subject, date, reviewed in submissions:
            with st.expander(f"{name} ({sid}) — {subject}"):
                st.write(f"📅 Submitted on: {date}")
                st.write(f"✅ Reviewed: {'Yes' if reviewed else 'No'}")

    # -------------------
    # Review Assignments
    # -------------------
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
            for aid, sid, name, subject, date in pending:
                with st.form(f"review_form_{aid}"):
                    st.markdown(f"**{name} ({sid}) — {subject}**")
                    st.write(f"📅 Submitted on: {date}")
                    remarks = st.text_area("Remarks", key=f"remarks_{aid}")
                    if st.form_submit_button("Mark as Reviewed ✅"):
                        cur.execute("UPDATE assignments SET reviewed=1 WHERE id=?", (aid,))
                        conn.commit()
                        st.success("Marked as reviewed.")
                        st.rerun()

    # -------------------
    # Upcoming Exams
    # -------------------
    elif selected == "📅 Upcoming Exams":
        st.subheader("📅 Exam Schedule")
        cur.execute("""
            SELECT subject, exam_date 
            FROM exam_schedule 
            WHERE class=? AND section=?
            ORDER BY exam_date
        """, (class_name, section))
        exams = cur.fetchall()
        if not exams:
            st.info("No upcoming exams scheduled.")
        else:
            for subject, ex_date in exams:
                st.markdown(f"📘 **{subject}** — 🗓️ {ex_date}")

    # -------------------
    # Fee Payments
    # -------------------
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

    # -------------------
    # Class Students
    # -------------------
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

    # -------------------
    # Mark Attendance
    # -------------------
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
                status = st.selectbox(f"{name} ({sid})", ["Present", "Absent"], key=f"att_{sid}")
                attendance_data[sid] = status

            if st.form_submit_button("📅 Submit Attendance"):
                for sid, status in attendance_data.items():
                    cur.execute("SELECT status FROM attendance WHERE student_id=? AND date=?", (sid, today))
                    existing = cur.fetchone()
                    cur.execute("""
                        INSERT OR REPLACE INTO attendance (student_id, date, status, submitted_by)
                        VALUES (?, ?, ?, ?)
                    """, (sid, today, status, email))
                    conn.commit()
                    if status == "Absent":
                        if not existing or (existing and existing[0] != "Absent"):
                            notify_attendance(sid, status, today)
                st.success("✅ Attendance marked successfully!")

    # -------------------
    # Submit Marks
    # -------------------
    elif selected == "✏️ Submit Marks":
        st.subheader("✏️ Submit Marks for a Student")

        cur.execute("""
            SELECT student_id, student_name FROM users
            WHERE class=? AND section=? AND role='Student'
            ORDER BY student_id
        """, (class_name, section))
        students = cur.fetchall()
        if not students:
            st.warning("No students found for your class/section.")
        else:
            student_options = [f"{name} ({sid})" for sid, name in students]
            chosen = st.selectbox("Select Student", student_options)
            if chosen:
                sid = chosen.split("(")[-1].replace(")", "").strip()
                display_name = chosen.split("(")[0].strip()

                subjects = get_subjects_for_class(cur, class_name, section)

                marks_inputs = {}
                with st.form("submit_marks_form_student"):
                    for sub in subjects:
                        cur.execute("SELECT marks FROM marks WHERE student_id=? AND subject=?", (sid, sub))
                        row = cur.fetchone()
                        default_val = int(row[0]) if row and row[0] is not None else 0
                        marks_inputs[sub] = st.number_input(f"{sub}", 0, 100, default_val, key=f"{sid}_{sub}")

                    preview_lines = "\n".join([f"{sub}: {marks_inputs[sub]}" for sub in subjects])
                    st.markdown("**Preview WhatsApp message:**")
                    st.code(f"📚 Marks Update for {display_name} ({sid}):\n{preview_lines}")

                    if st.form_submit_button("Submit Marks & Send WhatsApp"):
                        for sub, score in marks_inputs.items():
                            cur.execute("SELECT id FROM marks WHERE student_id=? AND subject=?", (sid, sub))
                            existing = cur.fetchone()
                            if existing:
                                cur.execute("""
                                    UPDATE marks
                                    SET marks=?, class=?, section=?, submitted_by=?, timestamp=CURRENT_TIMESTAMP
                                    WHERE student_id=? AND subject=?
                                """, (score, class_name, section, email, sid, sub))
                            else:
                                cur.execute("""
                                    INSERT INTO marks(student_id, subject, marks, class, section, submitted_by)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (sid, sub, score, class_name, section, email))
                        conn.commit()
                        notify_student_mark_bulk(sid, marks_inputs)
                        st.success(f"✅ Marks saved and WhatsApp sent to {display_name} ({sid}).")

    # -------------------
    # WhatsApp Logs
    # -------------------
    elif selected == "📢 WhatsApp Logs":
        st.subheader("📢 WhatsApp Logs (Class)")
        df = pd.read_sql_query("""
            SELECT w.* FROM whatsapp_logs w
            LEFT JOIN users u ON w.student_id = u.student_id
            WHERE u.class=? AND u.section=?
            ORDER BY w.timestamp DESC
        """, conn, params=(class_name, section))
        if df.empty:
            st.info("No WhatsApp logs for this class yet.")
        else:
            st.dataframe(df, use_container_width=True)
            failed = df[df['status'] != 'SUCCESS']
            if not failed.empty:
                st.markdown("### ⚠ Failed / Non-success messages")
                for _, row in failed.iterrows():
                    st.write(f"ID: {row['id']} • {row['student_id']} • {row['phone_number']} • status: {row['status']} • {row['timestamp']}")
                    st.write(row['message'])
                    if st.button("Resend", key=f"resend_{row['id']}"):
                        send_gupshup_whatsapp(row['phone_number'], row['message'], row['student_id'])
                        st.success("Resend requested — check logs.")
                        st.rerun()

    # -------------------
    # Messaging Tab (NEW — 2-way chat)
    # -------------------
    elif selected == "📨 Messages":
        st.subheader("📨 Message a Student/Parent")

        cur.execute("""
            SELECT student_name, student_id, email
            FROM users
            WHERE role='Student' AND class=? AND section=?
            ORDER BY student_name
        """, (class_name, section))
        students = cur.fetchall()

        if not students:
            st.info("No students found for your class.")
        else:
            student_map = {name: (sid, email) for name, sid, email in students}
            student_choice = st.selectbox("Select Student", list(student_map.keys()))
            sid, student_email = student_map[student_choice]

            message_text = st.text_area("Enter your message to student/parent")
            if st.button("Send Message"):
                if message_text.strip():
                    send_in_app_and_whatsapp_to_student(email, sid, message_text.strip())
                    st.success(f"✅ Message sent to {student_choice} (Student + Parent via WhatsApp)")
                else:
                    st.error("Please enter a message before sending.")

            st.write(f"### 📜 Message History with {student_choice}")
            cur.execute("""
                SELECT sender_email, message, timestamp
                FROM messages
                WHERE (sender_email=? AND receiver_email=?)
                   OR (sender_email=? AND receiver_email=?)
                ORDER BY timestamp DESC
            """, (email, student_email, student_email, email))
            msgs = cur.fetchall()
            if msgs:
                for sender, msg, ts in msgs:
                    st.markdown(f"**{sender}** ({ts}): {msg}")
            else:
                st.info("No conversation history found.")

    conn.close()