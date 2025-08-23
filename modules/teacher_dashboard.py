# modules/teacher_dashboard.py

import base64
import streamlit as st
import pandas as pd
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import base64
import pytesseract
from PIL import Image
import fitz  # PyMuPDF for PDFs
from db import get_connection
from datetime import datetime
from gupshup_sender import (
    notify_attendance,
    notify_student_marks_bulk,
    send_in_app_and_whatsapp_to_student,
    send_in_app_and_whatsapp,          # <-- needed for E-Connect
    send_file_upload_alert,
)

from openai import OpenAI
import os

api_key = st.secrets.get("OPENAI_API_KEY")

#OpenAI(api_key=api_key)


#client = OpenAI(
#    api_key=os.getenv("OPENAI_API_KEY"),
#    project="proj_FbqpY7CkwcT3ubju7iMeorRu"  # <-- replace with your real Project ID
#)

# --- Helpers ---
def encode_image_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def extract_text_from_pdf(file_path):
    """Extracts text from PDF, if possible"""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        print("PDF extract failed:", e)
    return text.strip()


def get_ai_feedback(desc, title, file_path):
    """
    Handles PDFs (extract text) and Images (vision model).
    Returns AI feedback as polished text for teachers.
    """
    # --- PDF case ---
    if file_path.lower().endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
        if not text.strip():
            return "⚠️ Could not extract text from the PDF."
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a teacher reviewing student homework submissions. Correct and polish the text into proper English before reviewing."},
                {"role": "user", "content": f"Assignment: {desc or title}. Please review this submission:\n\n{text}"}
            ]
        )
        return completion.choices[0].message.content

    # --- Image case ---
    elif file_path.lower().endswith((".jpg", ".jpeg", ".png")):
        encoded_img = encode_image_base64(file_path)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a teacher. First transcribe and polish the handwritten submission into proper English. Then provide review/feedback as if evaluating the work."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Assignment: {desc or title}. Please transcribe, correct, and review this submission."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
                    ]
                }
            ]
        )
        return completion.choices[0].message.content

    # --- Unsupported file type ---
    return "⚠️ Unsupported file type for AI review."





# this is for -> 📥 Review Assignments (Teacher View)
def extract_text_from_file(file_path):
    try:
        if file_path.lower().endswith(".pdf"):
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text.strip()
        elif file_path.lower().endswith((".jpg", ".jpeg", ".png")):
            img = Image.open(file_path)
            return pytesseract.image_to_string(img).strip()
    except Exception as e:
        return ""
    return ""


# ---------------- Active / Inactive colors ----------------
ACTIVE_COLOR = "#3b82f6"   # not used for styling directly now, kept for future
INACTIVE_COLOR = "#f3f4f6"

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- CSS ----------------
_UI_CSS = """
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: #e6f4ea !important; 
    color: #111827;
}
.dashboard-top-bar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.5rem 1rem; background: #d1f0d1; border-radius: 10px; margin-bottom: 1rem;
}
.dashboard-logo { text-align:center; flex:1; }
.dashboard-logo img { height:120px; }
.dashboard-welcome { font-weight:600; color:#165B33; }
.card{
    border-radius: 16px; background:#ffffff; padding:20px; margin-bottom:14px; box-shadow:0 4px 12px rgba(0,0,0,.1);
}
.card-title{ font-size:1.15rem; font-weight:700; margin-bottom:.25rem; }
.card-subtle{ color:#555; font-size:.95rem; margin-bottom:.75rem; }
</style>
"""

# ---------------- Groups & Sub-items (PLAIN ROUTE NAMES) ----------------
GROUPS = {
    "🏠 Overview": ["Home Overview"],
    "📄 Assignments": ["View Submissions", "Review Assignments", "Chapter-wise Learning Insights"],
    "📅 Exams": ["Upcoming Exams"],
    "✏️ Marks & Attendance": ["Mark Attendance", "Submit Marks"],
    "📚 Class": ["View Students", "Lesson Plans"],
    "🗂️ Content": ["Homework / Syllabus / Gallery", "Add Achievements", "E-Connect"],
    "💸 Fees": ["View Payments", "Add Misc Fee"],
    "🚍 Transport": ["Manage Transport"],
    "📢 Communication": ["WhatsApp Logs", "Messages"]
}

ITEM_ICONS = {
    "Home Overview":"🏠","View Submissions":"📄","Review Assignments":"✅",
    "Chapter-wise Learning Insights":"📚",
    "Upcoming Exams":"📅","Mark Attendance":"📆","Submit Marks":"✏️",
    "View Students":"📚","Lesson Plans":"📚","Homework / Syllabus / Gallery":"🗂️",
    "Add Achievements":"🏆","E-Connect":"🌐","View Payments":"💸","Add Misc Fee":"💰",
    "Manage Transport":"🚍","WhatsApp Logs":"📢","Messages":"📨"
}

# ---------------- Small UI helpers ----------------
def render_card(title, subtitle=""):
    st.markdown(
        f'<div class="card"><div class="card-title">{title}</div>'
        f'<div class="card-subtle">{subtitle}</div>',
        unsafe_allow_html=True
    )
def end_card():
    st.markdown("</div>", unsafe_allow_html=True)

def empty_state(text="Nothing to show yet."):
    st.markdown(f"<div style='color:#6b7280'>{text}</div>", unsafe_allow_html=True)

def table_card(columns, rows):
    render_card("", "")
    df = pd.DataFrame(rows, columns=columns)
    st.dataframe(df, use_container_width=True, hide_index=True)
    end_card()

def get_subjects_for_class(cur, class_name, section):
    try:
        cur.execute(
            "SELECT subject_name FROM subjects WHERE class=? AND section=? ORDER BY id",
            (class_name, section),
        )
        rows = [r[0] for r in cur.fetchall()]
        return rows if rows else ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]
    except Exception:
        return ["Telugu", "Hindi", "English", "Maths", "Science", "Social"]

# ---------------- Top bar ----------------
def draw_top_bar(user_name):
    left, center, right = st.columns([1,2,1])
    with left:
        st.markdown(f"<div class='dashboard-welcome'>Welcome, {user_name}</div>", unsafe_allow_html=True)
    with center:
        try:
            logo_b64 = base64.b64encode(open("dps_banner.png","rb").read()).decode()
            st.markdown(f"<div class='dashboard-logo'><img src='data:image/png;base64,{logo_b64}'/></div>", unsafe_allow_html=True)
        except Exception:
            st.markdown("<div class='dashboard-logo'><h3>DPS Narasaraopet</h3></div>", unsafe_allow_html=True)
    with right:
        if st.button("🚪 Logout", key="logout_btn_teacher", type="secondary"):
            st.session_state.clear()
            st.rerun()

# ---------------- Menus ----------------
def draw_groups():
    st.write("### Groups")
    cols = st.columns(len(GROUPS))
    for i, group_name in enumerate(GROUPS.keys()):
        active = st.session_state.get("group") == group_name
        with cols[i]:
            if st.button(group_name, key=f"group_{group_name}", type=("primary" if active else "secondary")):
                st.session_state.group = group_name
                st.session_state.item = None  # reset sub-item

def draw_subitems():
    group = st.session_state.get("group")
    if not group:
        return
    items = GROUPS[group]
    st.write("### Sub-Items")
    cols = st.columns(len(items))
    for i, item in enumerate(items):
        active = st.session_state.get("item") == item
        label = f"{ITEM_ICONS.get(item,'•')} {item}"
        with cols[i]:
            if st.button(label, key=f"sub_{item}", type=("primary" if active else "secondary")):
                st.session_state.item = item

# ---------------- Pages ----------------
def render_home_page(email, class_name, section, cur):
    # very small overview
    cur.execute("SELECT COUNT(*) FROM users WHERE role='Student' AND class=? AND section=?", (class_name, section))
    student_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM assignments WHERE class=? AND section=? AND reviewed=0", (class_name, section))
    pending_reviews = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM exam_schedule WHERE class=? AND section=? AND exam_date>=?",
                (class_name, section, datetime.today().strftime("%Y-%m-%d")))
    upcoming_exams = cur.fetchone()[0]

    render_card("🏠 Home Overview", f"Class {class_name}{section}")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Students", student_count)
    with c2: st.metric("Pending Reviews", pending_reviews)
    with c3: st.metric("Upcoming Exams", upcoming_exams)
    end_card()

def render_lesson_plans(email, class_name, section, cur):
    render_card("📚 Lesson Plans", f"Subject-wise plans for Class {class_name}{section}")
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
                table_card(["Topic", "Description"], topics)
            else:
                empty_state("No lesson plans available for this subject.")
            end_card()

# ---------------- Router ----------------
def render_dashboard_content(email, class_name, section):
    conn = get_connection()
    cur = conn.cursor()

    item = st.session_state.get("item")

    if item == "Home Overview":
        render_home_page(email, class_name, section, cur)

    elif item == "View Submissions":
        render_card("📄 Assignment Submissions", f"Class {class_name}{section}")
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

    # 📥 Review Assignments (Teacher View)
    elif item == "Review Assignments":
        render_card(f"{ITEM_ICONS[item]} {item}")

        # --- Teacher Filters ---
        st.subheader("🔍 Filters")       
        

        cur.execute("SELECT DISTINCT subject FROM assignments")
        subjects = [r[0] for r in cur.fetchall() if r[0]]

        cur.execute("SELECT DISTINCT class FROM assignments")
        classes = [r[0] for r in cur.fetchall() if r[0]]

        cur.execute("SELECT DISTINCT section FROM assignments")
        sections = [r[0] for r in cur.fetchall() if r[0]]

        f_subject = st.selectbox("📘 Subject", ["All"] + subjects, key="f_subject")
        f_class   = st.selectbox("🏫 Class", ["All"] + classes, key="f_class")
        f_section = st.selectbox("👥 Section", ["All"] + sections, key="f_section")
        col1, col2 = st.columns(2)
        with col1:
            f_start = st.date_input("📅 Start Date", value=None, key="f_start")
        with col2:
            f_end = st.date_input("📅 End Date", value=None, key="f_end")

        # --- Base Query ---
        query = """
            SELECT s.id, s.assignment_id, s.student_id, s.file_path, s.ai_feedback, s.submitted_at,
                   a.subject, a.description, a.title, a.class, a.section,
                   u.name
            FROM assignment_submissions s
            JOIN assignments a ON s.assignment_id = a.id
            JOIN users u ON s.student_id = u.id
            WHERE 1=1
        """
        params = []

        if f_subject != "All":
            query += " AND a.subject=?"
            params.append(f_subject)
        if f_class != "All":
            query += " AND a.class=?"
            params.append(f_class)
        if f_section != "All":
            query += " AND a.section=?"
            params.append(f_section)
        if f_start:
            query += " AND date(s.submitted_at) >= date(?)"
            params.append(str(f_start))
        if f_end:
            query += " AND date(s.submitted_at) <= date(?)"
            params.append(str(f_end))

        query += " ORDER BY s.submitted_at DESC"
        cur.execute(query, params)
        submissions = cur.fetchall()

        # --- Render Submissions ---
        if submissions:
            for sid, aid, stud_id, file_path, ai_fb, submitted_at, subj, desc, title, cls, sec, stud_name in submissions:
                with st.expander(f"{stud_name} — {cls}{sec} | {subj} ({title or 'Homework'}) | {submitted_at}"):

                    st.markdown(f"**📖 Homework:** {desc or '(no description)'}")
                    st.markdown(f"**👤 Student:** {stud_name} ({cls}-{sec})")
                    st.markdown(f"**📅 Submitted:** {submitted_at}")

                    if file_path and os.path.exists(file_path):
                        if file_path.lower().endswith((".jpg", ".jpeg", ".png")):
                            st.image(file_path, caption="Student submission")
                        else:
                            st.download_button(
                                "📂 Download submission",
                                open(file_path, "rb"),
                                file_name=os.path.basename(file_path)
                            )

                    # --- AI Feedback (teacher only) ---
                    with st.expander("🤖 AI Feedback (hidden from student)"):
                        if not ai_fb or ai_fb.strip() == "AI review not available.":
                            st.warning("No AI feedback yet. Generating now...")
                            
                            ai_fb = None
                            if file_path.lower().endswith(".pdf"):
                                extracted_text = extract_text_from_pdf(file_path)
                                if extracted_text:
                                    ai_fb = get_ai_feedback_text(desc, title, extracted_text)

                            if not ai_fb and file_path and os.path.exists(file_path):
                                ai_fb = get_ai_feedback(desc, title, file_path)

                                # Save back to DB
                                cur2 = conn.cursor()
                                cur2.execute(
                                    "UPDATE assignment_submissions SET ai_feedback=? WHERE id=?",
                                    (ai_fb, sid)
                                )
                                conn.commit()

                        # show whatever feedback is in DB
                        st.info(ai_fb or "⚠️ Could not generate AI feedback.")

                        # 👇 Add this regenerate button here
                        if st.button(f"🔄 Regenerate AI Feedback - {stud_name}", key=f"regen_{sid}"):
                            ai_fb = get_ai_feedback(desc, title, file_path)
                            cur2 = conn.cursor()
                            cur2.execute(
                                "UPDATE assignment_submissions SET ai_feedback=? WHERE id=?",
                                (ai_fb, sid)
                            )
                            conn.commit()
                            st.success("✅ AI feedback regenerated!")
                            st.rerun()

                            
                            
                    # --- Teacher Review ---
                    cur.execute("SELECT teacher_feedback FROM assignment_reviews WHERE submission_id=?", (sid,))
                    existing_review = cur.fetchone()

                    review_text = st.text_area(
                        "✍️ Teacher Review",
                        value=existing_review[0] if existing_review else "",
                        key=f"review_{sid}"
                    )

                    if st.button(f"💾 Save Review - {stud_name}", key=f"save_{sid}"):
                        conn2 = get_connection()
                        cur2 = conn2.cursor()
                        cur2.execute("""
                            INSERT INTO assignment_reviews (submission_id, teacher_id, teacher_feedback, reviewed_at)
                            VALUES (?, ?, ?, datetime('now'))
                            ON CONFLICT(submission_id) DO UPDATE SET
                                teacher_feedback=excluded.teacher_feedback,
                                reviewed_at=datetime('now')
                        """, (sid, user.get("id"), review_text))
                        conn2.commit()
                        conn2.close()
                        st.success("✅ Review saved!")
                        st.rerun()
        else:
            st.info("No submissions match the current filters.")

        end_card()


    
    # 📅 Exam Schedule
    elif item == "Upcoming Exams":
        render_card("📅 Exam Schedule", f"Class {class_name}{section}")
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

    elif item == "View Students":
        render_card("📚 Students in Class", f"Class {class_name}{section}")
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

    elif item == "Mark Attendance":
        render_card("📆 Mark Attendance", datetime.today().strftime("%Y-%m-%d"))
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
                    st.rerun()
        end_card()

    elif item == "Submit Marks":
        render_card("✏️ Submit Marks", f"Class {class_name}{section}")
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
                    notify_student_marks_bulk(sid, marks_inputs)
                    st.success("Marks saved and WhatsApp sent.")
                    st.rerun()
        end_card()

    elif item == "Homework / Syllabus / Gallery":
        render_card("🗂️ Homework / Syllabus / Gallery", f"Class {class_name}{section}")
        tabs = st.tabs(["Homework", "Syllabus", "Gallery"])
        end_card()

        # Homework
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

        # Syllabus
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

        # Gallery
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

    elif item == "Add Achievements":
        render_card("🏆 Add Student Achievement", f"Class {class_name}{section}")
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

    elif item == "Manage Transport":
        render_card("🚍 Assign/Update Student Transport", f"Class {class_name}{section}")
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

    elif item == "E-Connect":
        render_card("🌐 E-Connect Resource", f"Class {class_name}{section}")
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

    elif item == "View Payments":
        render_card("💸 Fee Payments", f"Class {class_name}{section}")
        df = pd.read_sql_query(
            """
            SELECT p.student_id, u.student_name, p.amount, p.method, p.date
            FROM payments p JOIN users u ON p.student_id=u.student_id
            WHERE u.class=? AND u.section=? ORDER BY p.date DESC
            """,
            conn,
            params=(class_name, section),
        )
        if df.empty:
            empty_state("No payments found.")
        else:
            table_card(list(df.columns), df.values.tolist())
        end_card()

    elif item == "Add Misc Fee":
        render_card("💰 Miscellaneous Fee", f"Class {class_name}{section}")
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

    elif item == "WhatsApp Logs":
        render_card("📢 WhatsApp Logs", f"Class {class_name}{section}")
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

    elif item == "Chapter-wise Learning Insights":
        st.markdown("### 📚 Chapter-wise Learning Insights")

        # --- Step 1: Select Class & Subject ---
        cur.execute("SELECT DISTINCT class, section FROM users WHERE role='Student'")
        classes = cur.fetchall()
        class_section = st.selectbox("Select Class & Section", [f"{c[0]}-{c[1]}" for c in classes])
        cls, sec = class_section.split("-")

        cur.execute("SELECT DISTINCT subject FROM chapter_practice")
        subjects = [row[0] for row in cur.fetchall()]
        subject = st.selectbox("Select Subject", subjects)

        # --- Step 2: Overview of Chapters ---
        query = """
            SELECT cp.chapter,
                   AVG(cp.is_correct) * 100.0 AS avg_score,
                   COUNT(DISTINCT cp.student_id) AS students_attempted
            FROM chapter_practice cp
            JOIN users u ON cp.student_id = u.student_id
            WHERE u.class = ? AND u.section = ? AND cp.subject = ?
            GROUP BY cp.chapter
        """

        df = pd.read_sql(query, conn, params=(cls, sec, subject))

        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)

            # --- Bar Chart: Avg Score per Chapter ---
            fig, ax = plt.subplots()
            ax.bar(df["chapter"], df["avg_score"])
            ax.set_ylabel("Average % Score")
            ax.set_title(f"Performance in {subject}")
            plt.xticks(rotation=30)
            st.pyplot(fig)

            # --- Step 3: Drill Down ---
            chapter = st.selectbox("Select Chapter for Details", df["chapter"].tolist())
            detail_q = """
                SELECT u.student_name,
                       cp.question,
                       cp.student_answer,
                       cp.correct_answer,
                       cp.is_correct
                FROM chapter_practice cp
                JOIN users u ON cp.student_id = u.student_id
                WHERE u.class = ? AND u.section = ? AND cp.subject = ? AND cp.chapter = ?
            """

            detail_df = pd.read_sql(detail_q, conn, params=(cls, sec, subject, chapter))

            if not detail_df.empty:
                st.markdown(f"### 📖 {chapter} - Student Responses")
                st.dataframe(detail_df, use_container_width=True, hide_index=True)

                # --- Pie Chart: Correct vs Incorrect ---
                counts = detail_df["is_correct"].value_counts()
                fig, ax = plt.subplots()
                ax.pie(counts, labels=["Correct","Incorrect"], autopct="%1.1f%%")
                st.pyplot(fig)
        else:
            st.info("No quiz data found for this class/subject yet.")

    
    elif item == "Messages":
        render_card("📨 Message a Student", f"Class {class_name}{section}")
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

# ---------------- Main ----------------
def render_teacher_dashboard(user):
    # init session
    st.session_state.setdefault("group", None)
    st.session_state.setdefault("item", None)

    # theming
    st.markdown(_UI_CSS, unsafe_allow_html=True)

    # resolve teacher context (email -> class/section)
    email = user.get("email")
    teacher_name = user.get("teacher_name", "Teacher")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT class, section FROM users WHERE email=?", (email,))
    row = cur.fetchone()
    conn.close()
    if not row:
        st.error("Teacher not found or class/section not assigned.")
        return
    class_name, section = row

    # UI
    draw_top_bar(teacher_name)
    draw_groups()
    draw_subitems()
    render_dashboard_content(email, class_name, section)
