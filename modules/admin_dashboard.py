# modules/admin_dashboard.py
import streamlit as st
import pandas as pd
from db import get_connection
from modules.teacher_dashboard import _UI_CSS  # reuse unified CSS
from modules.ui_theme import apply_theme
apply_theme()


# --------------------------------------------------
# Ensure tables needed by the Admin board exist
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
            role TEXT,
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
            date TEXT,
            status TEXT,
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

    # ASSIGNMENTS
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

    # EXAMINATIONS
    c.execute("""
        CREATE TABLE IF NOT EXISTS examinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_name TEXT,
            subject TEXT,
            date TEXT,
            max_marks INTEGER
        )
    """)

    # STAFF
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

    # SETTINGS
    c.execute("""
        CREATE TABLE IF NOT EXISTS school_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()


# --------------------------------------------------
# Sidebar grouping
# --------------------------------------------------
MENU_GROUPS = {
    "📊 Academics": [
        "📊 View Marks",
        "📅 Attendance Reports",
        "📆 Timetable Management",
        "📘 Homework / Assignments",
        "🧾 Examination Management",
    ],
    "👨‍💼 HR & Staff": [
        "👨‍🏫 Staff Management",
        "👥 User Management",
    ],
    "⚙️ Configuration": [
        "⚙️ School Configuration",
    ],
}

ROUTE_ALIASES = {
    "📊 View Marks": "marks",
    "📅 Attendance Reports": "attendance",
    "📆 Timetable Management": "timetable",
    "📘 Homework / Assignments": "assignments",
    "🧾 Examination Management": "exams",
    "👨‍🏫 Staff Management": "staff",
    "👥 User Management": "users",
    "⚙️ School Configuration": "settings",
}


def grouped_sidebar():
    st.sidebar.markdown(_UI_CSS, unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-title'>MENU</div>", unsafe_allow_html=True)

    if "selected_menu_admin" not in st.session_state:
        st.session_state.selected_menu_admin = "📊 View Marks"

    for group, items in MENU_GROUPS.items():
        st.sidebar.markdown(f"<div class='sidebar-title'>{group}</div>", unsafe_allow_html=True)
        for item in items:
            if st.sidebar.button(item, key=f"admin_{item}", use_container_width=True):
                st.session_state.selected_menu_admin = item
        st.sidebar.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    return st.session_state.selected_menu_admin


# --------------------------------------------------
# Render Dashboard
# --------------------------------------------------
def render_admin_dashboard():
    st.markdown(_UI_CSS, unsafe_allow_html=True)
    st.title("👑 Admin Dashboard")

    _ensure_tables()
    conn = get_connection()
    cur = conn.cursor()

    choice = grouped_sidebar()
    route = ROUTE_ALIASES.get(choice, choice)

    # --------------------------
    # 📊 View Marks
    # --------------------------
    if route == "marks":
        st.markdown('<div class="card"><div class="card-title">📊 Student Marks</div>', unsafe_allow_html=True)
        cur.execute("SELECT DISTINCT class FROM marks")
        class_list = [r[0] for r in cur.fetchall() if r[0]]
        if not class_list:
            st.info("No marks in DB yet.")
        else:
            selected_class = st.selectbox("Select Class", class_list)
            cur.execute("SELECT DISTINCT section FROM marks WHERE class=?", (selected_class,))
            section_list = [r[0] for r in cur.fetchall() if r[0]]
            if section_list:
                selected_section = st.selectbox("Select Section", section_list)
                cur.execute("SELECT DISTINCT subject FROM marks WHERE class=? AND section=?", (selected_class, selected_section))
                subject_list = [r[0] for r in cur.fetchall() if r[0]]
                selected_subject = st.selectbox("Select Subject", ["All"] + subject_list)

                if selected_subject == "All":
                    cur.execute("""SELECT student_id, subject, marks, class, section, submitted_by, timestamp
                                   FROM marks WHERE class=? AND section=? ORDER BY timestamp DESC""",
                                (selected_class, selected_section))
                else:
                    cur.execute("""SELECT student_id, subject, marks, class, section, submitted_by, timestamp
                                   FROM marks WHERE class=? AND section=? AND subject=? ORDER BY timestamp DESC""",
                                (selected_class, selected_section, selected_subject))

                rows = cur.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=["Student ID", "Subject", "Marks", "Class", "Section", "Submitted By", "Submitted On"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No marks found.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------
    # 📅 Attendance Reports
    # --------------------------
    elif route == "attendance":
        st.markdown('<div class="card"><div class="card-title">📅 Attendance Records</div>', unsafe_allow_html=True)
        cur.execute("SELECT DISTINCT class FROM users WHERE role='Student'")
        class_list = [r[0] for r in cur.fetchall() if r[0]]
        if not class_list:
            st.info("No students in DB.")
        else:
            selected_class = st.selectbox("Select Class", class_list)
            cur.execute("SELECT DISTINCT section FROM users WHERE class=? AND role='Student'", (selected_class,))
            section_list = [r[0] for r in cur.fetchall() if r[0]]
            if section_list:
                selected_section = st.selectbox("Select Section", section_list)
                cur.execute("""SELECT a.student_id, a.date, a.status, a.submitted_by, u.class, u.section
                               FROM attendance a JOIN users u ON a.student_id = u.student_id
                               WHERE u.class=? AND u.section=? ORDER BY a.date DESC""",
                            (selected_class, selected_section))
                rows = cur.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=["Student ID", "Date", "Status", "Submitted By", "Class", "Section"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No attendance records found.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------
    # 📆 Timetable Management
    # --------------------------
    elif route == "timetable":
        st.markdown('<div class="card"><div class="card-title">📆 Class Timetable Management</div>', unsafe_allow_html=True)
        cur.execute("SELECT DISTINCT class FROM users WHERE role='Student' ORDER BY class")
        classes = [row[0] for row in cur.fetchall() if row[0]]
        if not classes:
            st.warning("⚠️ No classes found.")
        else:
            class_choice = st.selectbox("Select Class", classes)
            cur.execute("SELECT DISTINCT section FROM users WHERE role='Student' AND class=? ORDER BY section", (class_choice,))
            sections = [row[0] for row in cur.fetchall() if row[0]]
            if sections:
                section_choice = st.selectbox("Select Section", sections)
                st.subheader("Current Timetable")
                cur.execute("""SELECT day, period, subject, teacher
                               FROM timetable WHERE class=? AND section=?
                               ORDER BY CASE day
                                   WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
                                   WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 END, period""",
                            (class_choice, section_choice))
                rows = cur.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=["Day", "Period", "Subject", "Teacher"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No timetable yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------
    # 📘 Homework / Assignments
    # --------------------------
    elif route == "assignments":
        st.markdown('<div class="card"><div class="card-title">📘 Homework & Assignments</div>', unsafe_allow_html=True)
        cur.execute("SELECT id, title, subject, class, section, due_date, file_path, description FROM assignments ORDER BY due_date DESC")
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["ID", "Title", "Subject", "Class", "Section", "Due Date", "File", "Description"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No assignments found.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------
    # 🧾 Examination Management
    # --------------------------
    elif route == "exams":
        st.markdown('<div class="card"><div class="card-title">🧾 Examination Records</div>', unsafe_allow_html=True)
        cur.execute("SELECT exam_name, subject, date, max_marks FROM examinations ORDER BY date DESC")
        exams = cur.fetchall()
        if exams:
            df_exams = pd.DataFrame(exams, columns=["Exam Name", "Subject", "Date", "Max Marks"])
            st.dataframe(df_exams, use_container_width=True)
        else:
            st.info("No examinations found.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------
    # 👨‍🏫 Staff Management
    # --------------------------
    elif route == "staff":
        st.markdown('<div class="card"><div class="card-title">👨‍🏫 Staff Management</div>', unsafe_allow_html=True)
        cur.execute("SELECT staff_id, name, role, phone, email, join_date, status FROM staff ORDER BY name ASC")
        staff_data = cur.fetchall()
        if staff_data:
            df_staff = pd.DataFrame(staff_data, columns=["Staff ID", "Name", "Role", "Phone", "Email", "Join Date", "Status"])
            st.dataframe(df_staff, use_container_width=True)
        else:
            st.info("No staff records found.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------
    # 👥 User Management
    # --------------------------
    elif route == "users":
        st.markdown('<div class="card"><div class="card-title">👥 User Management</div>', unsafe_allow_html=True)
        cur.execute("SELECT student_id, student_name, role, class, section, student_phone, parent_phone FROM users")
        rows = cur.fetchall()
        if rows:
            df_users = pd.DataFrame(rows, columns=["Student ID", "Name", "Role", "Class", "Section", "Student Phone", "Parent Phone"])
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("No users found.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------
    # ⚙️ School Configuration
    # --------------------------
    elif route == "settings":
        st.markdown('<div class="card"><div class="card-title">⚙️ School Settings</div>', unsafe_allow_html=True)
        cur.execute("SELECT key, value FROM school_settings")
        rows = cur.fetchall()
        if rows:
            df_settings = pd.DataFrame(rows, columns=["Setting", "Value"])
            st.dataframe(df_settings, use_container_width=True)
        else:
            st.info("No settings found.")
        st.markdown('</div>', unsafe_allow_html=True)

    conn.close()
