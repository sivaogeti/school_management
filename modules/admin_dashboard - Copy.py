# modules/admin_dashboard.py
import os
import streamlit as st
import pandas as pd
from db import get_connection
from modules.ui_theme import apply_theme, render_card, end_card, metric_row, table_card, empty_state


# --------------------------------------------------
# Ensure tables needed by the Admin board exist
# (Academic + HR focused)
# --------------------------------------------------
def _ensure_tables():
    conn = get_connection()
    c = conn.cursor()

    # USERS
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            student_name TEXT,
            role TEXT,            -- 'Student' | 'Teacher' | 'Admin'
            class TEXT,
            section TEXT,
            student_phone TEXT,
            parent_phone TEXT
        )
    """)

    # MARKS
    c.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            subject TEXT,
            marks REAL,
            class TEXT,
            section TEXT,
            submitted_by TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ATTENDANCE
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            date TEXT,              -- ISO date
            status TEXT,            -- 'Present' | 'Absent' | 'Late'
            submitted_by TEXT
        )
    """)

    # TIMETABLE
    c.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class TEXT,
            section TEXT,
            day TEXT,
            period INTEGER,
            subject TEXT,
            teacher TEXT,
            UNIQUE(class, section, day, period)
        )
    """)

    # ASSIGNMENTS (includes optional description)
    c.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            subject TEXT,
            class TEXT,
            section TEXT,
            file_path TEXT,
            due_date TEXT,
            description TEXT
        )
    """)

    # EXAMINATIONS (used by both Admin + Principal)
    c.execute("""
        CREATE TABLE IF NOT EXISTS examinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_name TEXT,
            subject TEXT,
            date TEXT,
            max_marks INTEGER
        )
    """)

    # STAFF (HR-style schema)
    c.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            staff_id TEXT PRIMARY KEY,
            name TEXT,
            role TEXT,
            phone TEXT,
            email TEXT,
            join_date TEXT,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()


def render_admin_dashboard():
    apply_theme()
    st.title("👑 Admin Dashboard")
    _ensure_tables()
    conn = get_connection()
    cur = conn.cursor()

    menu = st.sidebar.radio("📋 Menu", [
        "📊 View Marks",
        "📅 Attendance Reports",
        "📆 Timetable Management",
        "📘 Homework / Assignments",
        "🧾 Examination Management",
        "👨‍🏫 Staff Management",
        "👥 User Management",
        "⚙️ School Configuration"
    ])

    # --------------------------
    # 📊 View Marks
    # --------------------------
    if menu == "📊 View Marks":
        st.subheader("📊 Student Marks")
        cur.execute("SELECT DISTINCT class FROM marks")
        class_list = [r[0] for r in cur.fetchall() if r[0]]
        if not class_list:
            st.info("No marks in DB yet.")
        else:
            selected_class = st.selectbox("Select Class", class_list)
            cur.execute("SELECT DISTINCT section FROM marks WHERE class=?", (selected_class,))
            section_list = [r[0] for r in cur.fetchall() if r[0]]
            if not section_list:
                st.info("No sections for this class.")
            else:
                selected_section = st.selectbox("Select Section", section_list)
                cur.execute("SELECT DISTINCT subject FROM marks WHERE class=? AND section=?", (selected_class, selected_section))
                subject_list = [r[0] for r in cur.fetchall() if r[0]]
                selected_subject = st.selectbox("Select Subject", ["All"] + subject_list)

                if selected_subject == "All":
                    cur.execute("""
                        SELECT student_id, subject, marks, class, section, submitted_by, timestamp
                        FROM marks
                        WHERE class=? AND section=?
                        ORDER BY timestamp DESC
                    """, (selected_class, selected_section))
                else:
                    cur.execute("""
                        SELECT student_id, subject, marks, class, section, submitted_by, timestamp
                        FROM marks
                        WHERE class=? AND section=? AND subject=?
                        ORDER BY timestamp DESC
                    """, (selected_class, selected_section, selected_subject))

                rows = cur.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=[
                        "Student ID", "Subject", "Marks", "Class", "Section", "Submitted By", "Submitted On"
                    ])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No marks found for selection.")

    # --------------------------
    # 📅 Attendance Reports
    # --------------------------
    elif menu == "📅 Attendance Reports":
        st.subheader("📅 Attendance Records")
        cur.execute("SELECT DISTINCT class FROM users WHERE role='Student'")
        class_list = [r[0] for r in cur.fetchall() if r[0]]
        if not class_list:
            st.info("No students in DB.")
        else:
            selected_class = st.selectbox("Select Class", class_list)
            cur.execute("SELECT DISTINCT section FROM users WHERE class=? AND role='Student'", (selected_class,))
            section_list = [r[0] for r in cur.fetchall() if r[0]]
            if not section_list:
                st.info("No sections for this class.")
            else:
                selected_section = st.selectbox("Select Section", section_list)
                cur.execute("""
                    SELECT a.student_id, a.date, a.status, a.submitted_by, u.class, u.section
                    FROM attendance a
                    JOIN users u ON a.student_id = u.student_id
                    WHERE u.class=? AND u.section=?
                    ORDER BY a.date DESC
                """, (selected_class, selected_section))
                rows = cur.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=["Student ID", "Date", "Status", "Submitted By", "Class", "Section"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No attendance records found.")

    # --------------------------
    # 📆 Timetable Management
    # --------------------------
    elif menu == "📆 Timetable Management":
        st.subheader("Class Timetable Management")
        cur.execute("SELECT DISTINCT class FROM users WHERE role='Student' ORDER BY class")
        classes = [row[0] for row in cur.fetchall() if row[0]]
        if not classes:
            st.warning("⚠️ No classes found. Add students first.")
        else:
            class_choice = st.selectbox("Select Class", classes, key="admin_tt_class")
            cur.execute("SELECT DISTINCT section FROM users WHERE role='Student' AND class=? ORDER BY section", (class_choice,))
            sections = [row[0] for row in cur.fetchall() if row[0]]
            if sections:
                section_choice = st.selectbox("Select Section", sections, key="admin_tt_section")
                st.subheader("Current Timetable")
                cur.execute("""
                    SELECT day, period, subject, teacher
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
                        END, period
                """, (class_choice, section_choice))
                rows = cur.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=["Day", "Period", "Subject", "Teacher"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No timetable set yet for this Class & Section.")
                with st.form("update_tt_form"):
                    day = st.selectbox("Select Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
                    period = st.number_input("Period Number", min_value=1, max_value=10, step=1)
                    subject = st.text_input("Subject")
                    teacher = st.text_input("Teacher Name")
                    if st.form_submit_button("Save Timetable Entry"):
                        cur.execute("""
                            INSERT OR REPLACE INTO timetable (id, class, section, day, period, subject, teacher)
                            VALUES (
                                COALESCE((SELECT id FROM timetable WHERE class=? AND section=? AND day=? AND period=?), NULL),
                                ?, ?, ?, ?, ?, ?
                            )
                        """, (class_choice, section_choice, day, period,
                              class_choice, section_choice, day, period, subject, teacher))
                        conn.commit()
                        st.success(f"Timetable updated: {day} Period {period} → {subject}")

    # --------------------------
    # 📘 Homework / Assignments
    # --------------------------
    elif menu == "📘 Homework / Assignments":
        st.subheader("📘 Homework & Assignments")
        cur.execute("SELECT id, title, subject, class, section, due_date, file_path, description FROM assignments ORDER BY due_date DESC")
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["ID", "Title", "Subject", "Class", "Section", "Due Date", "File", "Description"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No assignments found.")
        with st.expander("➕ Add New Assignment"):
            title = st.text_input("Title")
            subject = st.text_input("Subject")
            class_name = st.text_input("Class")
            section = st.text_input("Section")
            due_date = st.date_input("Due Date")
            description = st.text_area("Description (optional)")
            file = st.file_uploader("Attachment", type=["pdf", "docx", "png", "jpg"])
            if st.button("Add Assignment"):
                file_path = file.name if file else None
                cur.execute("""
                    INSERT INTO assignments (title, subject, class, section, due_date, file_path, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (title, subject, class_name or None, section or None, due_date.isoformat(), file_path, description or None))
                conn.commit()
                st.success("Assignment added successfully.")
                st.experimental_rerun()

    # --------------------------
    # 🧾 Examination Management
    # --------------------------
    elif menu == "🧾 Examination Management":
        st.subheader("🧾 Examination Records")
        cur.execute("SELECT exam_id, exam_name, subject, date, max_marks FROM examinations ORDER BY date DESC")
        exams = cur.fetchall()
        if exams:
            df_exams = pd.DataFrame(exams, columns=["Exam ID", "Exam Name", "Subject", "Date", "Max Marks"])
            st.dataframe(df_exams, use_container_width=True)
        else:
            st.info("No examinations found.")
        with st.expander("➕ Add New Exam"):
            exam_name = st.text_input("Exam Name")
            subject = st.text_input("Subject")
            date = st.date_input("Exam Date")
            max_marks = st.number_input("Max Marks", min_value=0)
            if st.button("Add Exam"):
                cur.execute("""
                    INSERT INTO examinations (exam_name, subject, date, max_marks)
                    VALUES (?, ?, ?, ?)
                """, (exam_name, subject, date.isoformat(), int(max_marks)))
                conn.commit()
                st.success("Exam added successfully.")
                st.experimental_rerun()

    # --------------------------
    # 👨‍🏫 Staff Management
    # --------------------------
    elif menu == "👨‍🏫 Staff Management":
        st.subheader("👨‍🏫 Staff Management")
        cur.execute("SELECT staff_id, name, role, phone, email, join_date FROM staff ORDER BY name ASC")
        staff_data = cur.fetchall()
        if staff_data:
            df_staff = pd.DataFrame(staff_data, columns=["Staff ID", "Name", "Role", "Phone", "Email", "Join Date"])
            st.dataframe(df_staff, use_container_width=True)
        else:
            st.info("No staff records found.")
        st.markdown("---")
        with st.expander("➕ Add New Staff"):
            staff_id = st.text_input("Staff ID")
            name = st.text_input("Full Name")
            role = st.selectbox("Role", ["Teacher", "Administrator", "Accountant", "Librarian", "Other"])
            phone = st.text_input("Phone Number")
            email = st.text_input("Email")
            join_date = st.date_input("Joining Date")
            status = st.selectbox("Status", ["Active", "Inactive"])
            if st.button("Add Staff"):
                cur.execute("""
                    INSERT INTO staff (staff_id, name, role, phone, email, join_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (staff_id, name, role, phone, email, join_date.isoformat(), status))
                conn.commit()
                st.success(f"Staff member '{name}' added successfully.")
                st.experimental_rerun()
        with st.expander("✏️ Edit Staff"):
            edit_id = st.text_input("Enter Staff ID to Edit")
            if st.button("Fetch Staff Details"):
                cur.execute("SELECT name, role, phone, email, join_date, status FROM staff WHERE staff_id = ?", (edit_id,))
                record = cur.fetchone()
                if record:
                    name_edit = st.text_input("Full Name", record[0])
                    role_edit = st.selectbox("Role", ["Teacher", "Administrator", "Accountant", "Librarian", "Other"],
                                             index=["Teacher", "Administrator", "Accountant", "Librarian", "Other"].index(record[1]))
                    phone_edit = st.text_input("Phone Number", record[2])
                    email_edit = st.text_input("Email", record[3])
                    join_date_edit = st.date_input("Joining Date", pd.to_datetime(record[4]))
                    status_edit = st.selectbox("Status", ["Active", "Inactive"],
                                               index=["Active", "Inactive"].index(record[5]))
                    if st.button("Update Staff"):
                        cur.execute("""
                            UPDATE staff SET name=?, role=?, phone=?, email=?, join_date=?, status=? WHERE staff_id=?
                        """, (name_edit, role_edit, phone_edit, email_edit, join_date_edit.isoformat(), status_edit, edit_id))
                        conn.commit()
                        st.success("Staff details updated successfully.")
                        st.experimental_rerun()
                else:
                    st.error("No staff found with that ID.")
        with st.expander("🗑 Delete Staff"):
            delete_id = st.text_input("Enter Staff ID to Delete")
            if st.button("Delete Staff"):
                cur.execute("DELETE FROM staff WHERE staff_id = ?", (delete_id,))
                conn.commit()
                st.success(f"Staff ID '{delete_id}' deleted successfully.")
                st.experimental_rerun()

    # --------------------------
    # 👥 User Management
    # --------------------------
    elif menu == "👥 User Management":
        st.subheader("👥 User Management")
        cur.execute("SELECT student_id, student_name, role, class, section, student_phone, parent_phone FROM users")
        users_data = cur.fetchall()
        if users_data:
            df_users = pd.DataFrame(users_data, columns=["Student ID", "Name", "Role", "Class", "Section", "Student Phone", "Parent Phone"])
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("No users found.")
        with st.expander("➕ Add New User"):
            student_id = st.text_input("Student/Staff ID")
            name = st.text_input("Name")
            role = st.selectbox("Role", ["Student", "Teacher", "Admin"])
            user_class = st.text_input("Class", placeholder="for Students")
            section = st.text_input("Section", placeholder="for Students")
            s_phone = st.text_input("Student Phone")
            p_phone = st.text_input("Parent Phone")
            if st.button("Add User"):
                cur.execute("""
                    INSERT INTO users (student_id, student_name, role, class, section, student_phone, parent_phone)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (student_id, name, role, user_class or None, section or None, s_phone or None, p_phone or None))
                conn.commit()
                st.success("User added successfully.")
                st.experimental_rerun()

    # --------------------------
    # ⚙️ School Configuration
    # --------------------------
    elif menu == "⚙️ School Configuration":
        st.subheader("⚙️ School Settings")
        cur.execute("CREATE TABLE IF NOT EXISTS school_settings (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("SELECT key, value FROM school_settings")
        settings = cur.fetchall()
        if settings:
            df_settings = pd.DataFrame(settings, columns=["Setting", "Value"])
            st.dataframe(df_settings, use_container_width=True)
        else:
            st.info("No settings found.")
        with st.expander("⚙️ Update Setting"):
            setting_key = st.text_input("Setting Key")
            setting_value = st.text_input("Setting Value")
            if st.button("Save Setting"):
                cur.execute("""
                    INSERT OR REPLACE INTO school_settings (key, value) VALUES (?, ?)
                """, (setting_key, setting_value))
                conn.commit()
                st.success("Setting saved.")

    conn.close()
