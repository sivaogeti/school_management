import os
import pandas as pd
import streamlit as st
from datetime import datetime
from db import get_connection
from gupshup_sender import (
    notify_attendance,
    notify_student_mark_bulk,
    send_gupshup_whatsapp,
    send_in_app_and_whatsapp_to_student,
    send_in_app_and_whatsapp,
    send_file_upload_alert,
)

# ------------------------- Paths -------------------------
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# ===============  CENTRALIZED THEME (CSS)  ===============
# =========================================================
_UI_CSS = """
<style>
:root{
  --bg: #0f141a;
  --card: #1a1f27;
  --card-2: #141a21;
  --text: #e7edf3;
  --muted: #9fb0c0;
  --brand: #7c5cff;
  --brand-2:#5dd39e;
  --danger:#ff6b6b;
  --warn:#ffb020;
  --accent:#4cc9f0;
  --shadow: 0 10px 30px rgba(0,0,0,.35);
  --radius: 16px;
}
html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg);
  color: var(--text);
}
.sidebar-title{
  font-weight: 700; font-size: .9rem; letter-spacing:.04em;
  color: var(--muted); margin: 0.6rem 0 .3rem;
}
.nav-btn{
  width:100%; border:1px solid rgba(255,255,255,.06);
  background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(0,0,0,.12));
  color: var(--text);
  padding:.65rem .8rem; border-radius:12px; margin-bottom:.35rem;
  text-align:left; cursor:pointer; transition:.2s ease;
}
.nav-btn:hover{ transform: translateY(-1px); border-color: rgba(255,255,255,.12); }
.nav-btn.active{
  border-color: var(--brand); box-shadow: 0 0 0 2px rgba(124,92,255,.25) inset;
  background: linear-gradient(180deg, rgba(124,92,255,.15), rgba(0,0,0,.1));
}

.card{
  border-radius: var(--radius);
  background: linear-gradient(180deg, var(--card), var(--card-2));
  border: 1px solid rgba(255,255,255,.06);
  box-shadow: var(--shadow);
  padding: 20px 18px;
}
.card + .card{ margin-top: 14px; }
.card-title{
  font-size: 1.15rem; font-weight: 700; letter-spacing:.01em; margin-bottom:.25rem;
}
.card-subtle{ color: var(--muted); font-size:.95rem; margin-bottom: .75rem; }

.btn-row{ display:flex; gap:.5rem; flex-wrap:wrap; }
.btn{
  border-radius: 12px; padding:.6rem .9rem; border:1px solid transparent;
  cursor:pointer; font-weight:600;
  background: rgba(255,255,255,.06); color: var(--text);
}
.btn:hover{ filter: brightness(1.08); transform: translateY(-1px); }
.btn-primary{ background: linear-gradient(180deg, var(--brand), #6b4cff); }
.btn-success{ background: linear-gradient(180deg, var(--brand-2), #44c387); }
.btn-danger{ background: linear-gradient(180deg, var(--danger), #ff5252); }
.btn-ghost { background: rgba(255,255,255,.06); }

.metric-grid{ display:grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap:12px; }
.metric{ background: rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.06); padding:14px;
         border-radius:14px;}
.metric .label{ color: var(--muted); font-size:.85rem; }
.metric .value{ font-size:1.6rem; font-weight:700; margin-top: 6px; }

.table-wrap{
  overflow:auto; border-radius:12px; border:1px solid rgba(255,255,255,.08);
}
.styled-table{
  border-collapse: collapse; width: 100%; min-width: 520px;
  background: rgba(255,255,255,.02); color: var(--text);
}
.styled-table th, .styled-table td{
  padding:10px 12px; border-bottom:1px solid rgba(255,255,255,.06); text-align:left;
}
.styled-table thead th{ background: rgba(255,255,255,.06); font-size:.9rem; }
.empty{
  color: var(--muted); padding:.6rem 0;
}
.small{ font-size:.88rem; color: var(--muted); }
.header-row{
  display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:10px;
}
.header-chip{
  font-size:.85rem; color: var(--text);
  background: rgba(76,201,240,.15); border:1px solid rgba(76,201,240,.35);
  padding:.35rem .55rem; border-radius:999px;
}
/* Make all form labels (selectbox, text input, textarea, number input) more visible */
.stSelectbox label,
.stTextInput label,
.stTextArea label,
.stNumberInput label,
.stDateInput label,
.stFileUploader label,
.stCheckbox label {
  color: var(--text) !important;
  font-size: 1rem !important;   /* slightly larger */
  font-weight: 600 !important;  /* bold */
}
/* Force checkbox label text to be visible */
.stCheckbox div[data-testid="stMarkdownContainer"] {
  color: var(--text) !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
}
</style>
"""

# =========================================================
# ===============  SMALL RENDERING HELPERS  ===============
# =========================================================
def render_card(title: str, subtitle: str = "", right=None):
    st.markdown('<div class="card">', unsafe_allow_html=True)    
    right_html = f'<div class="header-chip">{right}</div>' if right else ""
    subtitle_html = f'<div class="card-subtle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="header-row"><div><div class="card-title">{title}</div>'
        f'{subtitle_html}</div>{right_html}</div>',
        unsafe_allow_html=True,
    )

def end_card():
    st.markdown("</div>", unsafe_allow_html=True)

def metric_row(metrics):
    st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
    for label, value in metrics:
        st.markdown(
            f'<div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{value}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

def table_card(columns, rows):
    st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
    th = "".join([f"<th>{c}</th>" for c in columns])
    trs = []
    for r in rows:
        tds = "".join([f"<td>{'' if v is None else v}</td>" for v in r])
        trs.append(f"<tr>{tds}</tr>")
    st.markdown(
        f"<table class='styled-table'><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

def empty_state(text="Nothing to show yet."):
    st.markdown(f"<div class='empty'>{text}</div>", unsafe_allow_html=True)

# =========================================================
# ======================  DATA HELPERS  ===================
# =========================================================
def get_subjects_for_class(cur, class_name, section):
    cur.execute(
        "SELECT subject_name FROM subjects WHERE class=? AND section=? ORDER BY id",
        (class_name, section),
    )
    rows = [r[0] for r in cur.fetchall()]
    return rows if rows else ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]

def safe_unread_count(cur, email):
    try:
        cur.execute("SELECT COUNT(*) FROM messages WHERE receiver_email=? AND COALESCE(is_read,0)=0", (email,))
        return cur.fetchone()[0]
    except Exception:
        try:
            cur.execute("SELECT COUNT(*) FROM messages WHERE receiver_email=?", (email,))
            return cur.fetchone()[0]
        except Exception:
            return 0

# =========================================================
# ======================  HOME OVERVIEW  ==================
# =========================================================
def render_home_page(email, class_name, section):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM assignments WHERE class=? AND section=? AND reviewed=0",
        (class_name, section),
    )
    pending_reviews = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM exam_schedule WHERE class=? AND section=? AND exam_date>=?",
        (class_name, section, datetime.today().strftime("%Y-%m-%d")),
    )
    upcoming_exams = cur.fetchone()[0]

    unread_messages = safe_unread_count(cur, email)

    cur.execute(
        "SELECT COUNT(*) FROM users WHERE class=? AND section=? AND role='Student'",
        (class_name, section),
    )
    student_count = cur.fetchone()[0]

    st.markdown(_UI_CSS, unsafe_allow_html=True)

    lcol, rcol = st.columns([2, 1])
    with lcol:
        render_card("📌 Assign a New Homework?", "The next homework is ready to be assigned to students.")
        assign_clicked = st.button("Assign Now", key="btn_assign_now", help="Go to Homework →", type="primary")
        st.markdown('<div class="small">Click to jump directly to the Homework tab.</div>', unsafe_allow_html=True)
        end_card()
        if assign_clicked:
            st.session_state.selected_menu = "🗂️ Homework / Syllabus / Gallery"
            st.rerun()

    with rcol:
        render_card("⚡ Quick Actions", "To level up your class")
        metric_row(
            [
                ("Pending Reviews", pending_reviews),
                ("Upcoming Exams", upcoming_exams),
                ("Unread Messages", unread_messages),
            ]
        )
        end_card()

    render_card("📊 Class Insights", right=f"Class {class_name}{section}")
    metric_row(
        [
            ("Total Students", student_count),
            ("Assignments Pending", pending_reviews),
            ("Exams Scheduled", upcoming_exams),
        ]
    )
    end_card()
    conn.close()

# =========================================================
# =====================  LESSON PLANS  ====================
# =========================================================
def render_lesson_plans(email, class_name, section):
    conn = get_connection()
    cur = conn.cursor()

    st.markdown(_UI_CSS, unsafe_allow_html=True)
    render_card("📚 Lesson Plans", "Subject-wise plans for your class", right=f"Class {class_name}{section}")
    ay = st.selectbox("Academic Year", ["AY 25-26", "AY 24-25"])
    subjects = get_subjects_for_class(cur, class_name, section)
    tabs = st.tabs(subjects)
    end_card()

    for idx, sub in enumerate(subjects):
        with tabs[idx]:
            render_card(f"📕 {sub}", "Planned topics")
            cur.execute(
                """SELECT topic, description FROM lesson_plans
                   WHERE class=? AND section=? AND subject=?""",
                (class_name, section, sub),
            )
            topics = cur.fetchall()
            if topics:
                cols = ["Topic", "Description"]
                table_card(cols, topics)
            else:
                empty_state("No lesson plans available for this subject.")
            end_card()
    conn.close()

# =========================================================
# =====================  SIDEBAR (GROUPED)  ===============
# =========================================================
_GROUPS = {
    "🏠 Overview": ["🏠 Home Overview"],
    "📄 Assignments": ["📄 View Submissions", "✅ Review Assignments"],
    "📅 Exams": ["📅 Upcoming Exams"],
    "✏️ Marks & Attendance": ["📆 Mark Attendance", "✏️ Submit Marks"],
    "💸 Fees": ["💸 View Fee Payments", "💰 Add Misc Fee"],
    "📚 Class": ["📚 View Class Students", "📚 Lesson Plans"],
    "🗂️ Content": ["🗂️ Homework / Syllabus / Gallery", "🏆 Add Achievements", "🌐 Upload E-Connect Resource"],
    "🚍 Transport": ["🚍 Manage Transport"],
    "📢 Communication": ["📢 WhatsApp Logs", "📨 Messages"],
}

def draw_sidebar():
    st.sidebar.markdown(_UI_CSS, unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-title'>MENU</div>", unsafe_allow_html=True)
    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = "🏠 Home Overview"

    for group, items in _GROUPS.items():
        st.sidebar.markdown(f"<div class='sidebar-title'>{group}</div>", unsafe_allow_html=True)
        for item in items:
            if st.sidebar.button(item, key=f"nav_{item}", use_container_width=True):
                st.session_state.selected_menu = item
        st.sidebar.markdown("<div style='height:.15rem'></div>", unsafe_allow_html=True)
    return st.session_state.selected_menu


def render_teacher_dashboard(user):
    st.markdown(_UI_CSS, unsafe_allow_html=True)

    email = user.get("email")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT class, section FROM users WHERE email=?", (email,))
    info = cur.fetchone()
    if not info:
        st.error("Teacher not found or class/section not assigned.")
        conn.close()
        return
    class_name, section = info
    conn.close()

    selected = draw_sidebar()
    conn = get_connection()
    cur = conn.cursor()

    # ---------------- ROUTES ----------------
    if selected == "🏠 Home Overview":
        render_home_page(email, class_name, section)

    elif selected == "📚 Lesson Plans":
        render_lesson_plans(email, class_name, section)

    elif selected == "📄 View Submissions":
        render_card("📄 Assignment Submissions", right=f"Class {class_name}{section}")
        cur.execute(
            """
            SELECT a.id, a.student_id, u.student_name, a.subject, a.timestamp, a.reviewed
            FROM assignments a JOIN users u ON a.student_id=u.student_id
            WHERE a.class=? AND a.section=?
            ORDER BY a.timestamp DESC
            """,
            (class_name, section),
        )
        rows = cur.fetchall()
        if not rows:
            empty_state("No submissions yet.")
        else:
            columns = ["ID", "Student ID", "Student Name", "Subject", "Submitted On", "Reviewed"]
            data = [(i, sid, name, sub, ts, "✅" if rev else "❌") for i, sid, name, sub, ts, rev in rows]
            table_card(columns, data)
        end_card()

    elif selected == "✅ Review Assignments":
        render_card("📝 Review Pending Assignments", right=f"Class {class_name}{section}")
        cur.execute(
            """
            SELECT a.id, a.student_id, u.student_name, a.subject, a.timestamp
            FROM assignments a JOIN users u ON a.student_id=u.student_id
            WHERE a.class=? AND a.section=? AND a.reviewed=0
            ORDER BY a.timestamp ASC
            """,
            (class_name, section),
        )
        pend = cur.fetchall()
        if not pend:
            empty_state("All assignments reviewed. 🎉")
        else:
            for aid, sid, name, subj, ts in pend:
                with st.expander(f"{name} ({sid}) — {subj} — {ts}"):
                    remarks = st.text_area("Remarks", key=f"rmk_{aid}")
                    if st.button("Mark as Reviewed", key=f"btn_rev_{aid}"):
                        cur.execute("UPDATE assignments SET reviewed=1 WHERE id=?", (aid,))
                        conn.commit()
                        st.success("Marked reviewed.")
                        st.rerun()
        end_card()

    elif selected == "📅 Upcoming Exams":
        render_card("📅 Exam Schedule", "For your class", right=f"Class {class_name}{section}")
        cur.execute(
            "SELECT subject, exam_date, exam_time, exam_type FROM exam_schedule WHERE class=? AND section=? ORDER BY exam_date",
            (class_name, section),
        )
        rows = cur.fetchall()
        if rows:
            table_card(["Subject", "Date", "Time", "Type"], rows)
        else:
            empty_state("No upcoming exams.")
        end_card()

    elif selected == "💸 View Fee Payments":
        render_card("💸 Fee Payments", right=f"Class {class_name}{section}")
        cur.execute(
            """
            SELECT p.student_id, u.student_name, p.amount, p.method, p.date
            FROM payments p JOIN users u ON p.student_id=u.student_id
            WHERE u.class=? AND u.section=? ORDER BY p.date DESC
            """,
            (class_name, section),
        )
        rows = cur.fetchall()
        if rows:
            table_card(["Student ID", "Student Name", "Amount (₹)", "Method", "Date"], rows)
        else:
            empty_state("No payments found.")
        end_card()

    elif selected == "📚 View Class Students":
        render_card("📚 Students in Class", right=f"Class {class_name}{section}")
        cur.execute(
            """
            SELECT student_id, student_name, email, student_phone, parent_phone
            FROM users WHERE role='Student' AND class=? AND section=? ORDER BY student_id
            """,
            (class_name, section),
        )
        rows = cur.fetchall()
        if rows:
            table_card(["Student ID", "Student Name", "Email", "Phone", "Parent Phone"], rows)
        else:
            empty_state("No students found.")
        end_card()

    elif selected == "📆 Mark Attendance":
        render_card("📆 Mark Attendance", right=datetime.today().strftime("%Y-%m-%d"))
        cur.execute(
            "SELECT student_id, student_name FROM users WHERE role='Student' AND class=? AND section=? ORDER BY student_id",
            (class_name, section),
        )
        students = cur.fetchall()
        if not students:
            empty_state("No students.")
        else:
            attendance = {}
            with st.form("attform"):
                for sid, name in students:
                    attendance[sid] = st.selectbox(f"{name} ({sid})", ["Present", "Absent"], key=f"att_{sid}")
                if st.form_submit_button("Submit Attendance"):
                    for sid, status in attendance.items():
                        cur.execute(
                            "INSERT OR REPLACE INTO attendance (student_id, date, status, submitted_by) VALUES (?, ?, ?, ?)",
                            (sid, datetime.today().strftime("%Y-%m-%d"), status, email),
                        )
                        conn.commit()
                        if status == "Absent":
                            notify_attendance(sid, status, datetime.today().strftime("%Y-%m-%d"))
                    st.success("Attendance saved.")
        end_card()

    elif selected == "✏️ Submit Marks":
        render_card("✏️ Submit Marks", right=f"Class {class_name}{section}")
        cur.execute(
            "SELECT student_name, student_id FROM users WHERE role='Student' AND class=? AND section=? ORDER BY student_name",
            (class_name, section),
        )
        students = cur.fetchall()
        if not students:
            empty_state("No students.")
        else:
            student_map = {f"{name} ({sid})": sid for name, sid in students}
            choice = st.selectbox("Select Student", list(student_map.keys()))
            sid = student_map[choice]
            subjects = get_subjects_for_class(cur, class_name, section)
            marks_inputs = {}
            with st.form("marks_form"):
                for sub in subjects:
                    cur.execute("SELECT marks FROM marks WHERE student_id=? AND subject=?", (sid, sub))
                    r = cur.fetchone()
                    default_val = int(r[0]) if r else 0
                    marks_inputs[sub] = st.number_input(sub, min_value=0, max_value=100, value=default_val)
                if st.form_submit_button("Submit Marks & Send WhatsApp"):
                    for sub, score in marks_inputs.items():
                        cur.execute(
                            """INSERT OR REPLACE INTO marks(student_id, subject, marks, class, section, submitted_by)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (sid, sub, score, class_name, section, email),
                        )
                    conn.commit()
                    notify_student_mark_bulk(sid, marks_inputs)
                    st.success("Marks saved and WhatsApp sent.")
        end_card()

    elif selected == "🗂️ Homework / Syllabus / Gallery":
        render_card("🗂️ Homework / Syllabus / Gallery", right=f"Class {class_name}{section}")
        tabs = st.tabs(["Homework", "Syllabus", "Gallery"])
        end_card()

        # Homework tab
        with tabs[0]:
            render_card("📌 Assign Homework")
            subj = st.text_input("Subject")
            desc = st.text_area("Description")
            due = st.date_input("Due date")
            file = st.file_uploader("Attach file", type=["pdf", "docx", "png", "jpg"])
            if st.button("Assign Homework", key="assign_hw_btn"):
                filename = None
                if file:
                    filename = f"homework_{int(datetime.now().timestamp())}_{file.name}"
                    with open(os.path.join(UPLOAD_DIR, filename), "wb") as fh:
                        fh.write(file.getbuffer())
                cur.execute(
                    """
                    INSERT INTO homework (class, section, subject, description, due_date, file_url, assigned_by, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (class_name, section, subj, desc, due.isoformat(), filename, email, datetime.now().isoformat()),
                )
                conn.commit()
                send_file_upload_alert("Homework", subj, class_name, section)
                st.success("Homework assigned & WhatsApp alert sent.")
            end_card()

        # Syllabus tab
        with tabs[1]:
            render_card("📚 Upload Syllabus")
            subj = st.text_input("Syllabus Subject")
            file = st.file_uploader("Syllabus file", type=["pdf", "docx"])
            if st.button("Upload Syllabus", key="upload_syl_btn"):
                if file:
                    filename = f"syllabus_{int(datetime.now().timestamp())}_{file.name}"
                    with open(os.path.join(UPLOAD_DIR, filename), "wb") as fh:
                        fh.write(file.getbuffer())
                    cur.execute(
                        """
                        INSERT INTO syllabus (class, section, subject, syllabus_text, file_url, uploaded_by, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (class_name, section, subj, None, filename, email, datetime.now().isoformat()),
                    )
                    conn.commit()
                    send_file_upload_alert("Syllabus", subj, class_name, section)
                    st.success("Syllabus uploaded & WhatsApp alert sent.")
                else:
                    st.error("Please select a file.")
            end_card()

        # Gallery tab
        with tabs[2]:
            render_card("🖼️ Upload to Gallery")
            title = st.text_input("Title")
            image = st.file_uploader("Image", type=["png", "jpg", "jpeg"])
            cat = st.selectbox("Category", ["General", "Event", "Sports", "Art"])
            if st.button("Upload Image", key="upload_img_btn"):
                if image:
                    filename = f"gallery_{int(datetime.now().timestamp())}_{image.name}"
                    with open(os.path.join(UPLOAD_DIR, filename), "wb") as fh:
                        fh.write(image.getbuffer())
                    cur.execute(
                        """
                        INSERT INTO gallery (title, image_url, category, uploaded_by, timestamp, class, section)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (title, filename, cat, email, datetime.now().isoformat(), class_name, section),
                    )
                    conn.commit()
                    send_file_upload_alert("Gallery", title, class_name, section)
                    st.success("Image uploaded & WhatsApp alert sent.")
                else:
                    st.error("Please select an image.")
            end_card()


    elif selected == "🏆 Add Achievements":
        render_card("🏆 Add Student Achievement", right=f"Class {class_name}{section}")
        cur.execute(
            "SELECT student_name, student_id FROM users WHERE role='Student' AND class=? AND section=? ORDER BY student_name",
            (class_name, section),
        )
        students = cur.fetchall()
        if not students:
            empty_state("No students found in your class.")
        else:
            student_map = {f"{name} ({sid})": sid for name, sid in students}
            choice = st.selectbox("Select Student", list(student_map.keys()))
            sid = student_map[choice]
            title = st.text_input("Title")
            desc = st.text_area("Description")
            date_awarded = st.date_input("Date Awarded", datetime.today())
            file = st.file_uploader("Upload Certificate (optional)", type=["pdf", "jpg", "png"])
            if st.button("Save Achievement & Send WhatsApp", key="save_ach_btn"):
                filename = None
                if file:
                    filename = f"achievement_{int(datetime.now().timestamp())}_{file.name}"
                    with open(os.path.join(UPLOAD_DIR, filename), "wb") as fh:
                        fh.write(file.getbuffer())
                cur.execute(
                    """
                    INSERT INTO achievements (student_id, title, description, date_awarded, awarded_by, file_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (sid, title, desc, date_awarded.isoformat(), email, filename),
                )
                conn.commit()
                send_in_app_and_whatsapp_to_student(email, sid, f"🏆 Achievement added: {title} — {desc}")
                st.success("Achievement saved & WhatsApp alert sent.")
        end_card()

    elif selected == "🚍 Manage Transport":
        render_card("🚍 Assign/Update Student Transport", right=f"Class {class_name}{section}")
        cur.execute(
            "SELECT student_name, student_id FROM users WHERE role='Student' AND class=? AND section=? ORDER BY student_name",
            (class_name, section),
        )
        students = cur.fetchall()
        if not students:
            empty_state("No students found.")
        else:
            student_map = {f"{name} ({sid})": sid for name, sid in students}
            choice = st.selectbox("Select Student", list(student_map.keys()))
            sid = student_map[choice]
            route_name = st.text_input("Route Name")
            pickup_point = st.text_input("Pickup Point")
            driver_name = st.text_input("Driver Name")
            driver_phone = st.text_input("Driver Phone")
            if st.button("Save Transport Info", key="save_transport_btn"):
                cur.execute(
                    """INSERT OR REPLACE INTO transport(student_id, route_name, pickup_point, driver_name, driver_phone)
                       VALUES (?, ?, ?, ?, ?)""",
                    (sid, route_name, pickup_point, driver_name, driver_phone),
                )
                conn.commit()
                send_in_app_and_whatsapp_to_student(email, sid, f"🚍 Transport info updated: {route_name} - {pickup_point}")
                st.success("Transport info saved & WhatsApp alert sent.")
        end_card()

    elif selected == "🌐 Upload E-Connect Resource":
        render_card("🌐 E-Connect Resource", right=f"Class {class_name}{section}")
        # Resource upload — not tied to individual student, no student_map required
        title = st.text_input("Title")
        desc = st.text_area("Description")
        file = st.file_uploader("Upload File (optional)", type=["pdf", "docx", "jpg", "png"])
        link = st.text_input("External Link (optional)")
        if st.button("Upload Resource", key="upload_econnect_btn"):
            filename = None
            if file:
                filename = f"econnect_{int(datetime.now().timestamp())}_{file.name}"
                with open(os.path.join(UPLOAD_DIR, filename), "wb") as fh:
                    fh.write(file.getbuffer())
            cur.execute(
                """INSERT INTO econnect_resources(title, description, file_url, link_url, uploaded_by, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (title, desc, filename, link, email, datetime.now().isoformat()),
            )
            conn.commit()
            send_in_app_and_whatsapp(email, f"🌐 New E-Connect resource: {title}")
            st.success("E-Connect resource uploaded & WhatsApp alert sent.")
        end_card()

    elif selected == "💰 Add Misc Fee":
        render_card("💰 Miscellaneous Fee", right=f"Class {class_name}{section}")
        cur.execute(
            "SELECT student_name, student_id FROM users WHERE role='Student' AND class=? AND section=? ORDER BY student_name",
            (class_name, section),
        )
        students = cur.fetchall()
        if not students:
            empty_state("No students found.")
        else:
            student_map = {f"{name} ({sid})": sid for name, sid in students}
            choice = st.selectbox("Select Student", list(student_map.keys()))
            sid = student_map[choice]
            desc = st.text_input("Fee Description")
            amount = st.number_input("Amount (₹)", min_value=0.0, step=0.01)
            due_date = st.date_input("Due Date")
            paid = st.checkbox("Mark as Paid")
            paid_on = datetime.today().strftime("%Y-%m-%d") if paid else None
            if st.button("Save Fee Record", key="save_fee_btn"):
                cur.execute(
                    """INSERT INTO misc_fees(student_id, description, amount, due_date, paid, paid_on)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (sid, desc, amount, due_date.isoformat(), int(paid), paid_on),
                )
                conn.commit()
                send_in_app_and_whatsapp_to_student(email, sid, f"💰 New fee: {desc} — ₹{amount}")
                st.success("Misc fee saved & WhatsApp alert sent.")
        end_card()

    elif selected == "📢 WhatsApp Logs":
        render_card("📢 WhatsApp Logs", right=f"Class {class_name}{section}")
        df = pd.read_sql_query(
            """
            SELECT w.* FROM whatsapp_logs w
            JOIN users u ON w.student_id=u.student_id
            WHERE u.class=? AND u.section=?
            ORDER BY w.timestamp DESC
            """,
            conn,
            params=(class_name, section),
        )
        if df.empty:
            empty_state("No WhatsApp logs found.")
        else:
            table_card(list(df.columns), df.values.tolist())
        end_card()

    elif selected == "📨 Messages":
        render_card("📨 Message a Student", right=f"Class {class_name}{section}")
        cur.execute(
            "SELECT student_name, student_id, email FROM users WHERE role='Student' AND class=? AND section=?",
            (class_name, section),
        )
        students = cur.fetchall()
        if students:
            student_map = {f"{name} ({sid})": (sid, stud_email) for name, sid, stud_email in students}
            choice = st.selectbox("Select Student", list(student_map.keys()))
            sid, stud_email = student_map[choice]
            msg = st.text_area("Message")
            if st.button("Send Message", key="send_msg_btn"):
                if msg.strip():
                    send_in_app_and_whatsapp_to_student(email, sid, msg.strip())
                    st.success("Message sent.")
                else:
                    st.warning("Please type a message.")
        else:
            empty_state("No students found in your class.")
        end_card()

    conn.close()
