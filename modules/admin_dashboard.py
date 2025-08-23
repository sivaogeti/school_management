# modules/admin_dashboard.py
import streamlit as st
import pandas as pd
import db
from modules.teacher_dashboard import _UI_CSS  # reuse unified CSS
from modules.ui_theme import apply_theme
apply_theme()
from datetime import datetime
from modules.ui_helpers import render_card as _render_card, end_card as _end_card
from modules.competitions_repo import (
    load_items, upsert_items, clear_items, DEFAULT_COLUMNS,
    load_meta, save_meta, ensure_competitions_meta_schema, ensure_competitions_meta_columns
)
# from wherever you put the renderer:
from modules.student_helpers import render_guidelines_html, GUIDELINES_CSS  # or inline where you placed it

from modules.key_guidelines_repo import load_guidelines, save_guidelines
import datetime as dt

#📌 Key Guidelines
def _acad_year_default():
    today = dt.date.today()
    start = today.year if today.month >= 4 else today.year - 1
    return f"{start}-{str(start+1)[-2:]}"

def render_key_guidelines_admin(conn):
    
    _render_card("🗝️ Key Guidelines", "Admin — enter text below; students see a styled version")

    year = st.selectbox("Academic Year", ["2025-26", "2024-25"], index=0, key="kg_admin_year")

    existing = load_guidelines(conn, year) or (
        "# KEY GUIDELINES\n"
        "Use the blocks below. Copy/paste from PDF (p.11) and adjust:\n\n"
        "[!IMPORTANT] School Timings\n"
        "Students must arrive 10 minutes before the first bell.\n\n"
        "[!WARNING] ID Cards\n"
        "ID card is mandatory every day.\n\n"
        "## Dress Code\n"
        "- Proper uniform on all working days\n"
        "- White canvas shoes on PT days\n\n"
        "[!TIP] Communication\n"
        "Use the parent portal for messages & circulars.\n"
    )

    content = st.text_area("Guidelines (Markdown-ish + [!IMPORTANT]/[!WARNING]/[!TIP]/[!INFO]/[!NOTE])",
                           value=existing, height=300, key=f"kg_text_{year}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save", use_container_width=True, key=f"kg_save_{year}"):
            save_guidelines(conn, year, content)
            st.toast("Guidelines saved.")
    with col2:
        st.caption("Paste from PDF page 11; use headings, lists, and callouts.")

    with st.expander("🔎 Live Preview", expanded=True):
        st.markdown(GUIDELINES_CSS, unsafe_allow_html=True)
        html = render_guidelines_html(content)
        st.markdown(f"<div class='kg-wrap'>{html}</div>", unsafe_allow_html=True)

    _end_card()

#Contact Directory
def render_contacts_admin(conn):
    import streamlit as st
    import pandas as pd
    from db import ensure_contacts_schema
    from modules.contacts_repo import load_contacts_admin, upsert_contacts, COLUMNS

    ensure_contacts_schema(conn)
    _render_card("📞 Contacts Directory", "Admin — one-time entry & edits")

    st.caption("Fill the table below. Use order_no to control display order. Toggle is_active to hide/show.")

    df = load_contacts_admin(conn)
    if df.empty:
        df = pd.DataFrame(columns=COLUMNS)
    edited = st.data_editor(
        df, num_rows="dynamic", hide_index=True, use_container_width=True,
        column_config={
            "order_no": st.column_config.NumberColumn("Order", help="Display order", width="small"),
            "category": "Category",
            "title": "Card Title",
            "contact_name": "Contact Name",
            "designation": "Designation",
            "phone_primary": st.column_config.TextColumn("Phone (primary)"),
            "phone_alt": st.column_config.TextColumn("Phone (alt)"),
            "notes": st.column_config.TextColumn("Notes"),
            "is_active": st.column_config.CheckboxColumn("Active"),
        },
        key="contacts_editor"
    )

    if st.button("💾 Save Contacts", use_container_width=True):
        upsert_contacts(conn, edited)
        st.toast("Contacts saved.")

    _end_card()


#Complaints & Suggestions
def render_complaints_admin(conn):
    import streamlit as st
    import pandas as pd
    from datetime import datetime

    # ensure table exists
    cur = conn.cursor()    

    _render_card("💬 Complaints & Suggestions", "Admin — Manage Submissions")

    # Load rows joined with users for names/class/section
    cur = conn.cursor()
    cur.execute("""
        SELECT 
          cs.id,
          cs.student_id,
          cs.category,
          cs.message,
          cs.status,
          cs.remarks,
          cs.created_at,
          u.id           AS user_id,
          u.student_id   AS admission_no,
          u.student_name AS full_name,
          u.name         AS alt_name,
          u.class        AS class_txt,
          u.section      AS section
        FROM complaints_suggestions cs
        LEFT JOIN users u
          ON (
               (CAST(cs.student_id AS INTEGER) = u.id)
               OR
               (u.student_id = cs.student_id)
             )
        ORDER BY cs.created_at DESC
    """)
    rows = cur.fetchall()

    if not rows:
        st.info("No complaints/suggestions yet.")
        _end_card()
        return

    cols = [
        "ID","student_id","Type","Message","Status","Admin Remarks","Created At",
        "user_id","Admission No","Full Name","Alt Name","Class","Section"
    ]
    df = pd.DataFrame(rows, columns=cols)

    # Pretty "Student" column
    def fmt_student(r):
        name = (r["Full Name"] or r["Alt Name"] or "-").strip()
        cls  = (r["Class"] or "").strip()
        sec  = (r["Section"] or "").strip()
        cs   = f"{cls}-{sec}" if (cls or sec) else ""
        adm  = (r["Admission No"] or "").strip()
        parts = [name]
        if cs:  parts.append(f"({cs})")
        if adm: parts.append(f"[{adm}]")
        return " ".join(parts).strip()

    df["Student"] = df.apply(fmt_student, axis=1)

    st.dataframe(
        df[["ID","Student","Type","Message","Status","Admin Remarks","Created At"]],
        use_container_width=True, hide_index=True
    )

    st.markdown("### Update Complaint/Suggestion")
    sel_id = st.selectbox("Select entry ID", df["ID"].tolist(), key="cs_admin_sel_id")

    if sel_id:
        row = df[df["ID"] == sel_id].iloc[0]
        st.caption(f"Selected: {row['Student']}")
        status_options = ["Open","In Progress","Resolved"]
        new_status = st.selectbox(
            "Status", status_options,
            index=status_options.index(row["Status"]) if row["Status"] in status_options else 0,
            key="cs_admin_status"
        )
        new_remarks = st.text_area("Admin Remarks", value=row["Admin Remarks"] or "", key="cs_admin_remarks")

        if st.button("Update Entry", use_container_width=True, key="cs_admin_update"):
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE complaints_suggestions
                SET status=?, remarks=?, updated_at=?
                WHERE id=?
                """,
                (new_status, new_remarks, datetime.utcnow().isoformat(), int(sel_id))
            )
            conn.commit()
            st.success("Updated successfully!")

    _end_card()



#Competitions & Enrichment Program 
def render_competitions_admin(conn):
    import streamlit as st
    import pandas as pd
 
    ensure_competitions_meta_schema(conn)
    ensure_competitions_meta_columns(conn)

    _render_card("🏆 Competitions & Enrichment Programs", "Admin — Interhouse Competitions & Workshops")

    year = st.selectbox("Academic Year", ["2025-26", "2024-25"], index=0, key="comp_admin_year")

    # --- HERO + TITLE (admin editable) ---
    meta = load_meta(conn, year)
    with st.expander("Header/Text (shown to students)", expanded=True):
        col1, col2 = st.columns([2, 3])
        with col1:
            hero_heading  = st.text_input("Hero Heading",  value=meta.get("hero_heading") or "House of Excellence: Interhouse Competitions & Enrichment Programs")
            hero_subtitle = st.text_input("Hero Subtitle", value=meta.get("hero_subtitle") or "Explore exciting opportunities for students to shine in:")
        with col2:
            b1 = st.text_input("Bullet 1", value=meta.get("bullet1") or "Interhouse Competitions")
            b2 = st.text_input("Bullet 2", value=meta.get("bullet2") or "Skill-building Workshops")
            b3 = st.text_input("Bullet 3", value=meta.get("bullet3") or "Leadership Activities")
        table_title = st.text_input("Table Title", value=meta.get("table_title") or "INTERHOUSE COMPETITIONS & WORKSHOPS – GRADE I–II")

        if st.button("💾 Save Header/Text", use_container_width=True):
            save_meta(conn, year, {
                "hero_heading": hero_heading,
                "hero_subtitle": hero_subtitle,
                "bullet1": b1, "bullet2": b2, "bullet3": b3,
                "table_title": table_title
            })
            st.toast("Header/text saved.")

    st.markdown("---")

    # --- ROWS (editable) ---
    df = load_items(conn, year)
    if df.empty:
        df = pd.DataFrame(columns=DEFAULT_COLUMNS)

    st.caption("Enter rows: MONTH · COMPETITION / WORKSHOP · THEME")
    edited = st.data_editor(
        df, use_container_width=True, hide_index=True, num_rows="dynamic",
        key=f"comp_enrich_editor_{year}"
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Save Rows", use_container_width=True, key=f"save_rows_{year}"):
            upsert_items(conn, year, edited)
            st.toast(f"Saved rows for {year}.")
    with c2:
        if st.button("🧹 Clear Rows", type="secondary", use_container_width=True, key=f"clear_rows_{year}"):
            clear_items(conn, year)
            st.toast(f"Cleared rows for {year}.")

    _end_card()

        

# --------------------------------------------------
# Ensure tables needed by the Admin board exist
# --------------------------------------------------
def _ensure_tables():
    conn = db.get_connection()
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
        "📝 Exam & PTM Schedule",
        "🎉 Special Days Management",
        "🏆 Competitions & Enrichment Programs (Admin)", 
        "📌 Key Guidelines (Admin)",
        "💬 Complaints & Suggestions (Admin)",
        "📞 Contacts Directory (Admin)",
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
    "📝 Exam & PTM Schedule": "exam_ptm",   # <— NEW
    "🎉 Special Days Management": "special_days_admin",   # <— NEW
    "🏆 Competitions & Enrichment Programs (Admin)": "competitions_admin",
    "👨‍🏫 Staff Management": "staff",
    "👥 User Management": "users",
    "📌 Key Guidelines (Admin)": "key_guidelines_admin",
    "💬 Complaints & Suggestions (Admin)": "complaints_admin",
    "📞 Contacts Directory (Admin)": "contacts_admin",
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

# modules/admin_dashboard.py (snippet)
import datetime as dt
import streamlit as st
import pandas as pd
from typing import List
from modules.special_days_repo import load_month_df, upsert_month_df, clear_month, DEFAULT_COLUMNS

MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]

def _month_selector(label="Month"):
    default_month = MONTHS[dt.date.today().month - 1]
    return st.selectbox(label, options=MONTHS, index=MONTHS.index(default_month))

def _year_selector(label="Year"):
    this_year = dt.date.today().year
    years = list(range(this_year - 1, this_year + 3))
    return st.selectbox(label, options=years, index=years.index(this_year))
    
def _autofill_day(df: pd.DataFrame) -> pd.DataFrame:
    import pandas as pd
    from datetime import datetime
    def day_name(val: str) -> str:
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(val.strip(), fmt).strftime("%A").upper()
            except Exception:
                pass
        return val  # leave as-is if not parseable
    df["DAY"] = [day_name(x) if x and x.strip() else "" for x in df["DATE"]]    

def render_special_days_admin(conn):
    st.markdown("### 🎉 Special Days Management")
    st.caption("Admin — Month-at-a-Glance")

    c1, c2 = st.columns([2,1])
    with c1:
        month_choice = _month_selector("Month")
    with c2:
        year_choice  = _year_selector("Year")

    df = load_month_df(conn, month_choice, year_choice)
    if df.empty:
        df = pd.DataFrame(columns=DEFAULT_COLUMNS)

    with st.expander("Column headers (exactly 6)"):
        cur_cols = list(df.columns) if not df.empty else DEFAULT_COLUMNS
        cols = st.columns(6)
        new_cols: List[str] = [cols[i].text_input(f"Col {i+1}", value=cur_cols[i]) for i in range(6)]
        if df.empty:
            df = pd.DataFrame(columns=new_cols)
        else:
            df.columns = new_cols

    st.caption("Enter Month-at-a-Glance items below (add/remove rows as needed).")
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=f"special_days_editor_{month_choice}_{year_choice}",
    )

    b1, b2 = st.columns(2)
    with b1:
        if st.button("💾 Save", use_container_width=True):
            # before saving:
            edited = _autofill_day(edited)
            upsert_month_df(conn, month_choice, year_choice, edited)
            st.toast(f"Saved {month_choice} {year_choice}.")
    with b2:
        if st.button("🧹 Clear month", type="secondary", use_container_width=True):
            clear_month(conn, month_choice, year_choice)
            st.toast(f"Cleared {month_choice} {year_choice}.")

    _end_card()


# --------------------------------------------------
# Render Dashboard
# --------------------------------------------------
def render_admin_dashboard():
    st.markdown(_UI_CSS, unsafe_allow_html=True)
    st.title("👑 Admin Dashboard")

    _ensure_tables()
    conn = db.get_connection()
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
        from datetime import datetime
        import pandas as pd

        st.markdown('<div class="card"><div class="card-title">📆 Class Timetable Management</div>', unsafe_allow_html=True)

        DAY_LABELS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        DAY_MAP    = {"MONDAY":1,"TUESDAY":2,"WEDNESDAY":3,"THURSDAY":4,"FRIDAY":5,"SATURDAY":6,"SUNDAY":7}
        DAY_IDX    = {"Monday":1,"Tuesday":2,"Wednesday":3,"Thursday":4,"Friday":5,"Saturday":6}

        connM = db.get_connection()
        curM  = connM.cursor()

        # Helpful index (safe if already exists)
        curM.execute("""CREATE INDEX IF NOT EXISTS idx_tt_lookup
                        ON timetable (class_name, section, day_of_week, period_no)""")
        connM.commit()

        # --- Step 0: Choose Class & Section first ---
        st.subheader("Select Class & Section to Edit")

        curM.execute("SELECT DISTINCT class FROM users WHERE role='Student' ORDER BY class")
        class_options = [r[0] for r in curM.fetchall() if r[0]]
        if not class_options:
            st.warning("⚠️ No classes found in USERS table. Please add students first.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

        selected_class = st.selectbox("Class", class_options, key="tt_class_select")

        curM.execute("SELECT DISTINCT section FROM users WHERE class=? AND role='Student' ORDER BY section", (selected_class,))
        section_options = [r[0] for r in curM.fetchall() if r[0]]
        if not section_options:
            st.warning("⚠️ No sections found for this class.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

        selected_section = st.selectbox("Section", section_options, key="tt_section_select")
        st.info(f"✏️ You are editing timetable for **Class {selected_class} – Section {selected_section}**")

        st.divider()

        # --- 1) Define slots (periods + breaks/lunch)
        st.subheader("Define Slots (Periods / Break / Lunch)")

        # current max period_no to suggest a default
        curM.execute("""SELECT MAX(period_no) FROM timetable
                        WHERE class_name=? AND section=?""",
                     (str(selected_class).upper(), str(selected_section).upper()))
        current_max = curM.fetchone()[0] or 0

        with st.form("slots_form"):
            total = st.number_input("Total slots (teaching + breaks + lunch)", 1, 12, value=max(current_max, 9))
            rows = []
            for p in range(1, int(total)+1):
                c1, c2, c3, c4, c5 = st.columns([0.7, 1.1, 1.1, 1, 1.2])
                c1.markdown(f"**Slot {p}**")

                # try to fetch an existing definition (any day) for defaults
                curM.execute("""SELECT start_time, end_time, slot_type, label
                                FROM timetable
                                WHERE class_name=? AND section=? AND period_no=? 
                                ORDER BY day_of_week LIMIT 1""",
                             (str(selected_class).upper(), str(selected_section).upper(), p))
                exist = curM.fetchone()
                st_val = exist[0] if exist else ""
                en_val = exist[1] if exist else ""
                ty_val = exist[2] if exist else "TEACHING"
                lb_val = exist[3] if exist else ( "Break" if ty_val=="BREAK" else "Lunch" if ty_val=="LUNCH" else f"Period {p}" )

                stime = c2.text_input(f"Start {p}", value=st_val, key=f"sl_st_{p}")
                etime = c3.text_input(f"End {p}",   value=en_val, key=f"sl_en_{p}")
                slot_type = c4.selectbox(f"Type {p}", ["TEACHING","BREAK","LUNCH"],
                                         index=["TEACHING","BREAK","LUNCH"].index(ty_val if ty_val in ("TEACHING","BREAK","LUNCH") else "TEACHING"),
                                         key=f"sl_ty_{p}")
                label = c5.text_input(f"Label {p}", value=lb_val, key=f"sl_lb_{p}")
                rows.append((p, stime.strip(), etime.strip(), slot_type, label.strip()))

            remove_extra = st.checkbox("If reduced slot count, delete rows with period_no beyond the new count", value=True)

            if st.form_submit_button("Save Slots"):
                cls = str(selected_class).upper()
                sec = str(selected_section).upper()

                # Ensure a row for each day+period exists (fill subject later)
                for pno, stime, etime, slot_type, label in rows:
                    for dow in range(1, 7):  # Mon..Sat
                        curM.execute("""
                            INSERT OR IGNORE INTO timetable (class_name, section, day_of_week, period_no)
                            VALUES (?, ?, ?, ?)
                        """, (cls, sec, dow, pno))
                        curM.execute("""
                            UPDATE timetable
                            SET start_time=?, end_time=?, slot_type=?, label=?
                            WHERE class_name=? AND section=? AND day_of_week=? AND period_no=?
                        """, (stime or None, etime or None, slot_type, label or None, cls, sec, dow, pno))

                # Delete any rows > total (to avoid orphaned periods)
                if remove_extra:
                    curM.execute("""DELETE FROM timetable
                                    WHERE class_name=? AND section=? AND period_no>?""",
                                 (cls, sec, int(total)))
                connM.commit()
                st.success("Slots saved.")

        st.divider()

        # --- 2) Grid Editor (subjects for teaching slots)
        st.subheader("Grid Editor (Week View – Subjects)")

        cls = str(selected_class).upper()
        sec = str(selected_section).upper()

        # Load TEACHING slots (columns)
        curM.execute("""SELECT DISTINCT period_no, COALESCE(label,''), COALESCE(start_time,''), COALESCE(end_time,'')
                        FROM timetable
                        WHERE class_name=? AND section=? AND slot_type='TEACHING'
                        ORDER BY period_no""", (cls, sec))
        teaching = curM.fetchall()

        if not teaching:
            st.info("Define at least one TEACHING slot above.")
        else:
            col_labels = []
            for pno, lbl, stt, ent in teaching:
                disp = (lbl or f"Period {int(pno)}")
                if stt or ent:
                    disp += f"\n{stt}-{ent}"
                col_labels.append((int(pno), disp))

            # Build grid (Mon..Sat)
            grid = pd.DataFrame(index=list(DAY_IDX.keys()),
                                columns=[lbl for _, lbl in col_labels])
            grid[:] = ""

            # Prefill existing subjects
            curM.execute("""SELECT day_of_week, period_no, COALESCE(subject,'')
                            FROM timetable
                            WHERE class_name=? AND section=? AND slot_type='TEACHING'""", (cls, sec))
            for dow, pno, subj in curM.fetchall():
                day_name = DAY_LABELS[int(dow)-1]
                plbl = dict(col_labels).get(int(pno))
                if day_name in grid.index and plbl in grid.columns:
                    grid.loc[day_name, plbl] = subj

            edited = st.data_editor(grid, use_container_width=True, num_rows="fixed", key="tt_grid_editor")

            # Non-teaching as caption (nice to show)
            curM.execute("""SELECT DISTINCT label, start_time, end_time
                            FROM timetable
                            WHERE class_name=? AND section=? AND slot_type IN ('BREAK','LUNCH')
                            ORDER BY period_no""", (cls, sec))
            nt = curM.fetchall()
            if nt:
                st.caption("Non-teaching slots: " + "; ".join([f"{(r[0] or 'Break/Lunch')} ({r[1] or ''}–{r[2] or ''})" for r in nt]))

            if st.button("Save Grid"):
                # Write back subjects for TEACHING slots
                pmap = {lbl: pno for pno, lbl in col_labels}
                for dname in edited.index:
                    dow = DAY_IDX[dname]
                    for col in edited.columns:
                        pno = pmap[col]
                        subj = str(edited.loc[dname, col]).strip()
                        # ensure row exists then update subject
                        curM.execute("""
                            INSERT OR IGNORE INTO timetable (class_name, section, day_of_week, period_no, slot_type, label)
                            VALUES (?, ?, ?, ?, 'TEACHING', ?)
                        """, (cls, sec, dow, int(pno), col.split("\n")[0]))
                        curM.execute("""
                            UPDATE timetable
                            SET subject=?
                            WHERE class_name=? AND section=? AND day_of_week=? AND period_no=? AND slot_type='TEACHING'
                        """, (subj or None, cls, sec, dow, int(pno)))
                connM.commit()
                st.success("Grid saved.")

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
    # 📝 Exam & PTM Schedule
    # --------------------------
    elif route == "exam_ptm":
        st.markdown('<div class="card"><div class="card-title">📝 Exam & PTM Schedule Management</div>', unsafe_allow_html=True)

        tabs = st.tabs(["📘 Exams", "👨‍👩‍👧 PTM"])

        # ---------------- Exams ----------------
        with tabs[0]:
            st.subheader("Add Exam")
            cls = st.text_input("Class", "I")
            sec = st.text_input("Section", "A")
            exam_name = st.text_input("Exam Name", "Term 1")
            subject = st.text_input("Subject", "English")
            exam_date = st.date_input("Exam Date")
            start = st.time_input("Start Time")
            end = st.time_input("End Time")
            venue = st.text_input("Venue", "Room 101")
            syllabus = st.text_area("Syllabus")
            notes = st.text_area("Notes")

            exam_type = st.selectbox(
                "Type",
                ["EXAM", "PT", "TERM", "OLYMPIAD", "INDIANTALENT", "NATIONALCOMPETITION"],
                index=0,
            )

            if st.button("➕ Add Exam"):
                try:
                    cur.execute("""
                        INSERT INTO exam_schedule
                          (class_name, section, exam_name, subject, exam_date, start_time, end_time, venue, syllabus, notes, exam_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cls.upper().strip(),
                        sec.upper().strip(),
                        exam_name.strip(),
                        subject.strip(),
                        str(exam_date),
                        start.strftime("%H:%M"),
                        end.strftime("%H:%M"),
                        venue.strip(),
                        syllabus.strip(),
                        notes.strip(),
                        exam_type.strip().upper(),
                    ))
                    conn.commit()
                    st.success("✅ Exam added.")
                except Exception as e:
                    st.error(f"Insert failed: {e}")

            st.divider()
            st.subheader("All Exams")
            cur.execute("""
                SELECT id, class_name, section, exam_name, subject, exam_date, start_time, end_time, venue, exam_type
                FROM exam_schedule
                ORDER BY date(exam_date), class_name, section, subject
            """)
            exams = cur.fetchall()

            if exams:
                df = pd.DataFrame(
                    exams,
                    columns=["ID", "Class", "Section", "Exam", "Subject", "Date", "Start", "End", "Venue", "Type"],
                )
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.caption("Edit rows below and click Save Changes.")
                edited = st.data_editor(df, num_rows="fixed", key="edit_exams")

                if st.button("💾 Save Changes"):
                    try:
                        for _, row in edited.iterrows():
                            cur.execute("""
                                UPDATE exam_schedule
                                   SET class_name=?,
                                       section=?,
                                       exam_name=?,
                                       subject=?,
                                       exam_date=?,
                                       start_time=?,
                                       end_time=?,
                                       venue=?,
                                       exam_type=?
                                 WHERE id=?
                            """, (
                                str(row["Class"]).upper().strip(),
                                str(row["Section"]).upper().strip(),
                                str(row["Exam"]).strip(),
                                str(row["Subject"]).strip(),
                                str(row["Date"]).strip(),
                                str(row["Start"]).strip(),
                                str(row["End"]).strip(),
                                str(row["Venue"]).strip(),
                                str(row["Type"]).strip().upper(),
                                int(row["ID"]),
                            ))
                        conn.commit()
                        st.success("✅ Exam schedule updated.")
                    except Exception as e:
                        st.error(f"Update failed: {e}")

                del_id = st.number_input("Delete Exam ID", min_value=0, step=1)
                if st.button("🗑️ Delete Exam"):
                    try:
                        cur.execute("DELETE FROM exam_schedule WHERE id=?", (int(del_id),))
                        conn.commit()
                        st.warning(f"Exam ID {int(del_id)} deleted.")
                    except Exception as e:
                        st.error(f"Delete failed: {e}")
            else:
                st.info("No exams scheduled yet.")

        # ---------------- PTMs ----------------
        with tabs[1]:
            st.subheader("Add PTM")
            cls = st.text_input("Class ", "I", key="ptm_cls")
            sec = st.text_input("Section ", "A", key="ptm_sec")
            meeting_date = st.date_input("Meeting Date")
            start = st.time_input("Start Time", key="ptm_start")
            end = st.time_input("End Time", key="ptm_end")
            venue = st.text_input("Venue", "Auditorium", key="ptm_venue")
            agenda = st.text_area("Agenda", key="ptm_agenda")
            notes = st.text_area("Notes", key="ptm_notes")

            if st.button("➕ Add PTM"):
                try:
                    cur.execute("""
                        INSERT INTO ptm_schedule
                          (class_name, section, meeting_date, start_time, end_time, venue, agenda, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cls.upper().strip(),
                        sec.upper().strip(),
                        str(meeting_date),
                        start.strftime("%H:%M"),
                        end.strftime("%H:%M"),
                        venue.strip(),
                        agenda.strip(),
                        notes.strip(),
                    ))
                    conn.commit()
                    st.success("✅ PTM added.")
                except Exception as e:
                    st.error(f"Insert failed: {e}")

            st.divider()
            st.subheader("All PTMs")
            cur.execute("""
                SELECT id, class_name, section, meeting_date, start_time, end_time, venue, agenda
                FROM ptm_schedule
                ORDER BY date(meeting_date), class_name, section
            """)
            ptms = cur.fetchall()

            if ptms:
                df_ptm = pd.DataFrame(
                    ptms, columns=["ID", "Class", "Section", "Date", "Start", "End", "Venue", "Agenda"]
                )
                st.dataframe(df_ptm, use_container_width=True, hide_index=True)

                st.caption("Edit rows below and click Save Changes.")
                edited_ptm = st.data_editor(df_ptm, num_rows="fixed", key="edit_ptm")

                if st.button("💾 Save PTM Changes"):
                    try:
                        for _, row in edited_ptm.iterrows():
                            cur.execute("""
                                UPDATE ptm_schedule
                                   SET class_name=?,
                                       section=?,
                                       meeting_date=?,
                                       start_time=?,
                                       end_time=?,
                                       venue=?,
                                       agenda=?
                                 WHERE id=?
                            """, (
                                str(row["Class"]).upper().strip(),
                                str(row["Section"]).upper().strip(),
                                str(row["Date"]).strip(),
                                str(row["Start"]).strip(),
                                str(row["End"]).strip(),
                                str(row["Venue"]).strip(),
                                str(row["Agenda"]).strip(),
                                int(row["ID"]),
                            ))
                        conn.commit()
                        st.success("✅ PTM schedule updated.")
                    except Exception as e:
                        st.error(f"Update failed: {e}")

                del_id = st.number_input("Delete PTM ID", min_value=0, step=1, key="ptm_del")
                if st.button("🗑️ Delete PTM"):
                    try:
                        cur.execute("DELETE FROM ptm_schedule WHERE id=?", (int(del_id),))
                        conn.commit()
                        st.warning(f"PTM ID {int(del_id)} deleted.")
                    except Exception as e:
                        st.error(f"Delete failed: {e}")
            else:
                st.info("No PTMs scheduled yet.")

        st.markdown('</div>', unsafe_allow_html=True)
        
     # --------------------------
    # 🏆 Competitions & Enrichment Programs (Admin)
    # --------------------------
    elif route == "competitions_admin":        
        ensure_competitions_meta_schema(conn)
        render_competitions_admin(conn)
        
    # --------------------------
    # 👨Special Days Management
    # --------------------------
    elif route == "special_days_admin":
        render_special_days_admin(conn)
    
    # --------------------------
    # 💬 Complaints & Suggestions (Admin)
    # --------------------------
    elif route == "complaints_admin":
        render_complaints_admin(conn)   

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
    # 📞 Contacts Directory 
    # --------------------------
    elif route == "contacts_admin":
        render_contacts_admin(conn)
    
    # --------------------------
    # 📌 Key Guidelines
    # --------------------------
    elif route == "key_guidelines_admin":
        render_key_guidelines_admin(conn)

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
