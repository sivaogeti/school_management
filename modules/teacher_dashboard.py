# modules/teacher_dashboard.py
# ASCII-safe, consolidated, and de-duplicated.

import os
from datetime import date, timedelta
import streamlit as st
import pandas as pd

# ---------- Optional dependencies ----------
try:
    from db import get_connection
except Exception:
    get_connection = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# ---------- Theme + layout CSS (ASCII safe) ----------
_UI_CSS = """
<style>
:root {
  --brand-bg: #111213;
  --brand-surface: #1f2229;
  --brand-primary: #22c55e;
  --brand-border: #2a3a2c;
}
html, body, [data-testid="stAppViewContainer"] { background: var(--brand-bg) !important; color: #e5e7eb; }
.dashboard-top-bar { display:flex; justify-content:space-between; align-items:center; padding:8px 12px;
  background:#1f2922; border-radius:10px; margin-bottom:8px; border:1px solid var(--brand-border); }
.dashboard-logo img{ height:120px; }
.breadcrumbs{ display:flex; gap:6px; align-items:center; font-size:0.95rem; margin:6px 0 12px; }
.breadcrumbs .crumb{ padding:2px 8px; border:1px solid var(--brand-border); border-radius:999px; background:#1f2922; color:#86efac; font-weight:600; }
.breadcrumbs .sep{ color:#9ca3af; }
.nav-card{ border:1px solid var(--brand-border); border-radius:10px; padding:14px; background:var(--brand-surface); }
.nav-title{ font-weight:800; font-size:1.05rem; margin-bottom:6px; color:#d1fae5; }
.group-pill{ display:inline-flex; align-items:center; gap:8px; font-weight:700; color:#d1fae5; padding:8px 10px; border-radius:999px; background:#1f2922; border:1px solid var(--brand-border); margin:8px 0; }
.subchips-wrap{ display:grid; grid-template-columns: repeat(auto-fill, minmax(240px,1fr)); gap:10px; margin:6px 0 12px; }
.subchip{ display:flex; align-items:center; justify-content:space-between; gap:10px; border-radius:10px; background:var(--brand-surface); padding:8px 10px; border:1px solid var(--brand-border); }
.class-tabs{ display:flex; gap:6px; align-items:flex-end; padding:8px 6px; background:#2a2d33; border:1px solid #3a3d45; overflow-x:auto; white-space:nowrap; }
.class-tab{ padding:10px 12px; background:#5b6168; border-radius:2px 2px 0 0; color:#e5e7eb; font-weight:700; border:1px solid #3a3d45; }
.lesson-list{ border:1px solid #3a3d45; border-top:2px solid #7cc67e; background:#2f3136; padding:10px; }
.lesson-item{ font-size:1.05rem; font-weight:800; padding:10px 6px; border-bottom:1px dashed #42464f; }
</style>
"""

# ---------- Global config ----------
NEW_TEACHER_DASH_ENABLED = True

# Top cards (order exactly as requested)
SECTIONS = [
    ("🎓 Academics", "academics"),
    ("👥 Student Management", "students"),
    ("📢 Communication", "comms"),
    ("📑 Reports & Analytics", "reports"),
    ("⚙️ Settings", "settings"),
]

# Sub-groups for each top card
GROUPS = {
    # 1) Academics
    "🎓 Academics": [
        "📅 Year Planner",
        "📚 Lesson Plans",
        "📊 Chapter-wise Learning Insights",
    ],

    # 2) Student Management
    "👥 Student Management": [
        "👥 View Students",
        "🕒 Attendance",
        "📝 Todays Logs",
        "🏠 Homework Given",
        "🧪 Correction Homework - Homework",
        "📓 Correction Homework - Classwork",
        "📘 Correction Homework - TextBook work",
        "🧩 Assignment & Projects",
        "🧮 Marks",
    ],

    # 3) Communication
    "📢 Communication": [
        "💬 Messages",
        "🟢 Whatsapp Logs",
        "📝 Complaints & Suggestions",
        "🎂 Birthday Reminders",
        "🖼️ Gallery",
        "🗓️ Self Leave System",
        "🗓️ Student Leaves",
    ],

    # 4) Reports & Analytics
    "📑 Reports & Analytics": [
        "📈 Attendance Trends",
        "🏆 Top & Low Performers List",
        "⬇️ Download reports - Exams",
        "⬇️ Download reports - Attendance",
    ],

    # 5) Settings
    "⚙️ Settings": [
        "👤 Profile",
        "🔐 Change Password",
    ],
}

# Which group(s) show under each top card
SECTION_TO_GROUPS = {
    "academics": ["🎓 Academics"],
    "students": ["👥 Student Management"],
    "comms": ["📢 Communication"],
    "reports": ["📑 Reports & Analytics"],
    "settings": ["⚙️ Settings"],
}



# ---------- Session state helpers ----------
def _ensure_state():
    st.session_state.setdefault("td_active", None)
    st.session_state.setdefault("td_sub", None)
    st.session_state.setdefault("lp_selected_class", None)
    st.session_state.setdefault("lp_selected_lesson", None)
    st.session_state.setdefault("lp_generated_md", "")
    st.session_state.setdefault("lp_view_lesson", None)
    st.session_state.setdefault("lp_last_debug", "")
    #fallback cache: {(class,subject,chapter,email): {"status": "draft"/"submitted", "content_md": "..."}}
    st.session_state.setdefault("lp_fallback", {})
    st.session_state.setdefault("yp_selected_class", None)
    st.session_state.setdefault("yp_selected_month", None)
    st.session_state.setdefault("yp_generated_md", "")
    st.session_state.setdefault("yp_view_month", None)
    st.session_state.setdefault("yp_last_debug", "")
    st.session_state.setdefault("yp_fallback", {})  # {(class,subject,month,acad_year,email): {...}}

#Helper to build the key
def _lp_key(class_label, subject, chapter, email):
    return (class_label or "").strip().lower(), (subject or "").strip().lower(), (chapter or "").strip().lower(), (email or "").strip().lower()


def _norm_status(s):
    return (s or "").strip().lower()

def _set_lp_debug(msg: str):
    st.session_state["lp_last_debug"] = msg

def _get_lp_debug():
    return st.session_state.get("lp_last_debug", "")

def _yp_key(class_label, subject, month, acad_year, email):
    return (
        (class_label or "").strip().lower(),
        (subject or "").strip().lower(),
        (month or "").strip().lower(),
        (acad_year or "").strip().lower(),
        (email or "").strip().lower(),
    )

def _set_yp_debug(msg: str):
    st.session_state["yp_last_debug"] = msg

def _get_yp_debug():
    return st.session_state.get("yp_last_debug", "")

def _ensure_year_plans_table():
    if not get_connection or not callable(get_connection):
        return False
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS year_plans(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_label   TEXT NOT NULL,
                subject       TEXT NOT NULL,
                month         TEXT NOT NULL,           -- e.g., 'June', 'Jul', 'Sept'
                acad_year     TEXT NOT NULL,           -- e.g., '2025-26'
                content_md    TEXT,
                teacher_email TEXT NOT NULL,
                status        TEXT,                    -- 'draft' | 'submitted'
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_yp_unique
            ON year_plans(
                lower(trim(class_label)),
                lower(trim(subject)),
                lower(trim(month)),
                lower(trim(acad_year)),
                lower(trim(teacher_email))
            )
        """)
        conn.commit(); conn.close()
        return True
    except Exception:
        return False


def get_year_plan_record(class_label: str, subject: str, month: str, acad_year: str, teacher_email: str):
    # DB first
    if get_connection and callable(get_connection):
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("""
                SELECT id, class_label, subject, month, acad_year, content_md, teacher_email, status
                  FROM year_plans
                 WHERE lower(trim(class_label))   = lower(trim(?))
                   AND lower(trim(subject))       = lower(trim(?))
                   AND lower(trim(month))         = lower(trim(?))
                   AND lower(trim(acad_year))     = lower(trim(?))
                   AND lower(trim(teacher_email)) = lower(trim(?))
                 ORDER BY id DESC LIMIT 1
            """, (class_label, subject, month, acad_year, teacher_email))
            row = cur.fetchone(); conn.close()
            if row:
                keys = ["id","class_label","subject","month","acad_year","content_md","teacher_email","status"]
                return dict(zip(keys, row))
        except Exception:
            pass
    # Fallback
    rec = st.session_state["yp_fallback"].get(_yp_key(class_label, subject, month, acad_year, teacher_email))
    if rec:
        return {
            "id": None,
            "class_label": class_label,
            "subject": subject,
            "month": month,
            "acad_year": acad_year,
            "content_md": rec.get("content_md", ""),
            "teacher_email": teacher_email,
            "status": rec.get("status", "draft"),
        }
    return None


def upsert_year_plan_draft(class_label: str, subject: str, month: str, acad_year: str, content_md: str, teacher_email: str):
    """
    UPDATE-by-keys else INSERT (no ON CONFLICT).
    Also writes a session fallback + debug on DB failure.
    """
    if not _ensure_year_plans_table():
        st.session_state["yp_fallback"][_yp_key(class_label, subject, month, acad_year, teacher_email)] = {
            "status": "draft", "content_md": content_md
        }
        _set_yp_debug("UPSERT(YR) ok=True (fallback) | post.status='draft' | db=unavailable")
        return True
    try:
        cl = (class_label or "").strip()
        sb = (subject or "").strip()
        mo = (month or "").strip()
        ay = (acad_year or "").strip()
        em = (teacher_email or "").strip()

        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            UPDATE year_plans
               SET content_md = ?, status = 'draft', updated_at = CURRENT_TIMESTAMP
             WHERE lower(trim(class_label))   = lower(trim(?))
               AND lower(trim(subject))       = lower(trim(?))
               AND lower(trim(month))         = lower(trim(?))
               AND lower(trim(acad_year))     = lower(trim(?))
               AND lower(trim(teacher_email)) = lower(trim(?))
        """, (content_md, cl, sb, mo, ay, em))
        if cur.rowcount == 0:
            cur.execute("""
                INSERT INTO year_plans
                    (class_label, subject, month, acad_year, content_md, teacher_email, status, created_at, updated_at)
                VALUES
                    (?, ?, ?, ?, ?, ?, 'draft', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (cl, sb, mo, ay, content_md, em))
        conn.commit()

        # probe + db path
        cur.execute("""
            SELECT status FROM year_plans
             WHERE lower(trim(class_label))   = lower(trim(?))
               AND lower(trim(subject))       = lower(trim(?))
               AND lower(trim(month))         = lower(trim(?))
               AND lower(trim(acad_year))     = lower(trim(?))
               AND lower(trim(teacher_email)) = lower(trim(?))
             ORDER BY id DESC LIMIT 1
        """, (cl, sb, mo, ay, em))
        row = cur.fetchone()
        try:
            cur.execute("PRAGMA database_list;")
            db_path = next((file for _, name, file in cur.fetchall() if name == "main"), "unknown")
        except Exception:
            db_path = "unknown"
        conn.close()

        _set_yp_debug(f"UPSERT(YR) ok=True | post.status={_norm_status(row[0]) if row else None} | db={db_path}")
        return True
    except Exception as e:
        st.session_state["yp_fallback"][_yp_key(class_label, subject, month, acad_year, teacher_email)] = {
            "status": "draft", "content_md": content_md
        }
        _set_yp_debug(f"UPSERT(YR) ok=False | error={type(e).__name__}: {e} | used=fallback")
        try: conn.close()
        except Exception: pass
        return False


def submit_year_plan_by_keys(class_label: str, subject: str, month: str, acad_year: str, teacher_email: str, content_md: str):
    if not _ensure_year_plans_table():
        st.session_state["yp_fallback"][_yp_key(class_label, subject, month, acad_year, teacher_email)] = {
            "status": "submitted", "content_md": content_md
        }
        _set_yp_debug("SUBMIT(YR) ok=True (fallback) | post.status='submitted' | db=unavailable")
        return True
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            UPDATE year_plans
               SET content_md = ?, status = 'submitted', updated_at = CURRENT_TIMESTAMP
             WHERE lower(trim(class_label))   = lower(trim(?))
               AND lower(trim(subject))       = lower(trim(?))
               AND lower(trim(month))         = lower(trim(?))
               AND lower(trim(acad_year))     = lower(trim(?))
               AND lower(trim(teacher_email)) = lower(trim(?))
        """, (content_md, class_label, subject, month, acad_year, teacher_email))
        if cur.rowcount == 0:
            cur.execute("""
                INSERT INTO year_plans
                    (class_label, subject, month, acad_year, content_md, teacher_email, status, created_at, updated_at)
                VALUES
                    (?, ?, ?, ?, ?, ?, 'submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (class_label, subject, month, acad_year, content_md, teacher_email))
        conn.commit(); conn.close()
        _set_yp_debug("SUBMIT(YR) ok=True | db=main")
        return True
    except Exception as e:
        st.session_state["yp_fallback"][_yp_key(class_label, subject, month, acad_year, teacher_email)] = {
            "status": "submitted", "content_md": content_md
        }
        _set_yp_debug(f"SUBMIT(YR) ok=False | error={type(e).__name__}: {e} | used=fallback")
        return False


def _academic_year_options():
    # Build simple AY labels: '2024-25', '2025-26', etc.
    import datetime as _dt
    y = _dt.date.today().year
    # Offer previous, current, next AY
    return [f"{y-1}-{str(y)[-2:]}", f"{y}-{str(y+1)[-2:]}", f"{y+1}-{str(y+2)[-2:]}"]

def _months_for_planner():
    # Adjust to your school calendar if needed
    return ["June","July","August","September","October","November","December","January","February","March","April","May"]

def page_year_planner_v1(user):
    _ensure_state()
    st.subheader("📅 Year Planner")
    yp_dbg = _get_yp_debug()
    if yp_dbg:
        st.caption(yp_dbg)

    email = user.get("email", "teacher@example.com")
    classes = get_teacher_classes(email)

    # Planner settings
    c1, c2 = st.columns([1,1])
    with c1:
        acad_year = st.selectbox("Academic Year", _academic_year_options(), index=1, key="yp_ay")
    with c2:
        detail_level = st.selectbox("Detail level", ["concise","standard","detailed"], index=1, key="yp_dl")

    # Class tabs
    st.markdown("<div class='class-tabs'>", unsafe_allow_html=True)
    for idx, c in enumerate(classes):
        if st.button(c["label"][:14] + (".." if len(c["label"]) > 14 else ""), key=f"class_tab_yp_{idx}"):
            st.session_state["yp_selected_class"] = idx
            st.session_state["yp_selected_month"] = None
            st.session_state["yp_generated_md"] = ""
            st.session_state["yp_view_month"] = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    sel_idx = st.session_state.get("yp_selected_class")
    if sel_idx is None:
        st.info("Select a class to plan months.")
        return

    sel = classes[sel_idx]
    months = _months_for_planner()

    # Months list
    st.markdown("<div class='lesson-list'>", unsafe_allow_html=True)
    for i, month in enumerate(months):
        col1, col2, col3 = st.columns([5,1,1])
        with col1:
            st.markdown(f"<div class='lesson-item'>{month}</div>", unsafe_allow_html=True)

        rec = get_year_plan_record(sel["class"], sel["subject"], month, acad_year, email)
        status = _norm_status(rec.get("status")) if rec else None

        with col2:
            if status is None:
                if st.button("Generate", key=f"yp_gen_{i}"):
                    # Seed a monthly plan using your generator as scaffolding
                    grade = "".join(ch for ch in sel["class"] if ch.isdigit()) or "9"
                    md = generate_lesson_plan(
                        grade=grade,
                        subject=sel["subject"],
                        chapter=f"{month} plan",
                        detail_level=st.session_state.get("yp_dl","standard"),
                        include_examples=True,
                    )
                    ok = upsert_year_plan_draft(sel["class"], sel["subject"], month, acad_year, md, email)
                    probe = get_year_plan_record(sel["class"], sel["subject"], month, acad_year, email)
                    _set_yp_debug(f"UPSERT(YR) ok={ok} | probe.status={_norm_status(probe.get('status')) if probe else None} | keys=({sel['class']!r},{sel['subject']!r},{month!r},{acad_year!r},{email!r})")
                    st.session_state["yp_selected_month"] = month
                    st.session_state["yp_generated_md"] = md
                    st.session_state["yp_view_month"] = None
                    st.rerun()
            else:
                st.button("Locked", key=f"yp_locked_{i}", disabled=True)

        with col3:
            if status == "draft":
                if st.button("Open", key=f"yp_open_{i}"):
                    st.session_state["yp_selected_month"] = month
                    st.session_state["yp_view_month"] = None
                    st.rerun()
            elif status == "submitted":
                if st.button("View", key=f"yp_view_{i}"):
                    st.session_state["yp_view_month"] = month
                    st.session_state["yp_selected_month"] = None
                    st.rerun()
            else:
                st.button("Open", key=f"yp_open_{i}", disabled=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Editor (draft only)
    month_sel = st.session_state.get("yp_selected_month")
    if month_sel:
        st.session_state["yp_view_month"] = None
        rec = get_year_plan_record(sel["class"], sel["subject"], month_sel, acad_year, email)
        status = _norm_status(rec.get("status")) if rec else None
        if status == "submitted":
            st.session_state["yp_view_month"] = month_sel
            st.session_state["yp_selected_month"] = None
            st.rerun()

        st.markdown(f"### Edit Month Plan: *{month_sel}*  ({acad_year})")
        prefill_md = (rec.get("content_md") if rec else st.session_state.get("yp_generated_md","")) or ""
        editor_key = f"yp_editor_md__{sel['class']}__{sel['subject']}__{acad_year}__{month_sel}"

        left, right = st.columns([3,1])
        with left:
            with st.form(f"yp_form__{editor_key}", clear_on_submit=False):
                md_val = st.text_area("Month Plan (Markdown)", value=prefill_md, key=editor_key, height=420)
                c1, c2 = st.columns([1,1])
                with c1: st.form_submit_button("Regenerate AI", disabled=True)
                with c2: submitted = st.form_submit_button("Submit Plan")
        with right:
            st.download_button("Download .md", data=md_val,
                               file_name=f"{sel['class']}_{sel['subject']}_{acad_year}_{month_sel}.md",
                               use_container_width=True, key=f"yp_dl__{editor_key}")

        if submitted:
            submit_year_plan_by_keys(sel["class"], sel["subject"], month_sel, acad_year, email, md_val)
            st.success("Month plan submitted.")
            st.session_state["yp_selected_month"] = None
            st.session_state["yp_generated_md"] = ""
            st.session_state["yp_view_month"] = month_sel
            st.rerun()

    # Viewer (submitted only)
    if st.session_state.get("yp_view_month") and not st.session_state.get("yp_selected_month"):
        v_month = st.session_state["yp_view_month"]
        v_rec = get_year_plan_record(sel["class"], sel["subject"], v_month, acad_year, email)
        v_md = (v_rec or {}).get("content_md","")
        st.markdown(f"### View Month Plan (Submitted): *{v_month}*  ({acad_year})")
        st.markdown(v_md)
        _, v_right = st.columns([3,1])
        with v_right:
            st.download_button("Download .md", data=v_md,
                               file_name=f"{sel['class']}_{sel['subject']}_{acad_year}_{v_month}.md",
                               use_container_width=True, key=f"yp_dl_view__{sel['class']}__{sel['subject']}__{acad_year}__{v_month}")
        if st.button("Close", key=f"yp_close_view__{sel['class']}__{sel['subject']}__{acad_year}__{v_month}"):
            st.session_state["yp_view_month"] = None
            st.rerun()


# ---------- DB helpers for Lesson Plans ----------
def _ensure_lesson_plans_table():
    if not get_connection or not callable(get_connection):
        return False
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lesson_plans(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_label   TEXT NOT NULL,
                subject       TEXT NOT NULL,
                chapter       TEXT NOT NULL,
                content_md    TEXT,
                teacher_email TEXT NOT NULL,
                status        TEXT,
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_lp_unique
            ON lesson_plans(
                lower(trim(class_label)),
                lower(trim(subject)),
                lower(trim(chapter)),
                lower(trim(teacher_email))
            )
        """)
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

#get_plan_record
def get_plan_record(class_label: str, subject: str, chapter: str, teacher_email: str):
    # Try DB first (unchanged)
    if get_connection and callable(get_connection):
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("""
                SELECT id, class_label, subject, chapter, content_md, teacher_email, status
                  FROM lesson_plans
                 WHERE lower(trim(class_label))   = lower(trim(?))
                   AND lower(trim(subject))       = lower(trim(?))
                   AND lower(trim(chapter))       = lower(trim(?))
                   AND lower(trim(teacher_email)) = lower(trim(?))
                 ORDER BY id DESC LIMIT 1
            """, (class_label, subject, chapter, teacher_email))
            row = cur.fetchone(); conn.close()
            if row:
                keys = ["id","class_label","subject","chapter","content_md","teacher_email","status"]
                return dict(zip(keys, row))
        except Exception:
            pass
    # Fallback (session)
    rec = st.session_state["lp_fallback"].get(_lp_key(class_label, subject, chapter, teacher_email))
    if rec:
        return {
            "id": None,
            "class_label": class_label,
            "subject": subject,
            "chapter": chapter,
            "content_md": rec.get("content_md",""),
            "teacher_email": teacher_email,
            "status": rec.get("status","draft"),
        }
    return None



#upsert_lesson_plan_draft
def upsert_lesson_plan_draft(class_label: str, subject: str, chapter: str, content_md: str, teacher_email: str):
    """
    Robust upsert without ON CONFLICT.
    1) UPDATE by natural keys (case/space-insensitive)
    2) If no row updated, INSERT a new draft
    Also writes a session fallback if DB fails, and emits a detailed debug line.
    """
    if not _ensure_lesson_plans_table():
        # DB unavailable — use fallback so UI still works
        st.session_state["lp_fallback"][_lp_key(class_label, subject, chapter, teacher_email)] = {
            "status": "draft", "content_md": content_md
        }
        _set_lp_debug("UPSERT ok=True (fallback) | post.status='draft' | db=unavailable")
        return True

    try:
        cl = (class_label or "").strip()
        sb = (subject or "").strip()
        ch = (chapter or "").strip()
        em = (teacher_email or "").strip()

        conn = get_connection()
        cur = conn.cursor()

        # Try UPDATE first
        cur.execute("""
            UPDATE lesson_plans
               SET content_md = ?, status = 'draft', updated_at = CURRENT_TIMESTAMP
             WHERE lower(trim(class_label))   = lower(trim(?))
               AND lower(trim(subject))       = lower(trim(?))
               AND lower(trim(chapter))       = lower(trim(?))
               AND lower(trim(teacher_email)) = lower(trim(?))
        """, (content_md, cl, sb, ch, em))

        if cur.rowcount == 0:
            # No row — do INSERT (NOTE: param order: content_md then teacher_email)
            cur.execute("""
                INSERT INTO lesson_plans
                    (class_label, subject, chapter, content_md, teacher_email, status, created_at, updated_at)
                VALUES
                    (?, ?, ?, ?, ?, 'draft', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (cl, sb, ch, content_md, em))

        conn.commit()

        # Probe + db path
        cur.execute("""
            SELECT status FROM lesson_plans
             WHERE lower(trim(class_label))   = lower(trim(?))
               AND lower(trim(subject))       = lower(trim(?))
               AND lower(trim(chapter))       = lower(trim(?))
               AND lower(trim(teacher_email)) = lower(trim(?))
             ORDER BY id DESC LIMIT 1
        """, (cl, sb, ch, em))
        row = cur.fetchone()

        try:
            cur.execute("PRAGMA database_list;")
            db_path = next((file for _, name, file in cur.fetchall() if name == "main"), "unknown")
        except Exception:
            db_path = "unknown"

        conn.close()
        _set_lp_debug(f"UPSERT ok=True | post.status={_norm_status(row[0]) if row else None} | db={db_path}")
        return True

    except Exception as e:
        # Record to fallback so UI continues, and show error + db path
        st.session_state["lp_fallback"][_lp_key(class_label, subject, chapter, teacher_email)] = {
            "status": "draft", "content_md": content_md
        }
        try:
            cur.execute("PRAGMA database_list;")
            db_path = next((file for _, name, file in cur.fetchall() if name == "main"), "unknown")
        except Exception:
            db_path = "unknown"
        try:
            conn.close()
        except Exception:
            pass
        _set_lp_debug(f"UPSERT ok=False | error={type(e).__name__}: {e} | db={db_path} | used=fallback")
        return False



#submit_lesson_plan_by_keys
def submit_lesson_plan_by_keys(class_label: str, subject: str, chapter: str, teacher_email: str, content_md: str):
    if not _ensure_lesson_plans_table():
        st.session_state["lp_fallback"][_lp_key(class_label, subject, chapter, teacher_email)] = {
            "status": "submitted", "content_md": content_md
        }
        _set_lp_debug("SUBMIT ok=True (fallback) | post.status='submitted' | db=unavailable")
        return True

    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            UPDATE lesson_plans
               SET content_md = ?, status = 'submitted', updated_at = CURRENT_TIMESTAMP
             WHERE lower(trim(class_label))   = lower(trim(?))
               AND lower(trim(subject))       = lower(trim(?))
               AND lower(trim(chapter))       = lower(trim(?))
               AND lower(trim(teacher_email)) = lower(trim(?))
        """, (content_md, class_label, subject, chapter, teacher_email))
        if cur.rowcount == 0:
            cur.execute("""
                INSERT INTO lesson_plans
                    (class_label, subject, chapter, content_md, teacher_email, status, created_at, updated_at)
                VALUES
                    (?, ?, ?, ?, ?, 'submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (class_label, subject, chapter, content_md, teacher_email))
        conn.commit(); conn.close()
        _set_lp_debug("SUBMIT ok=True | db=main")
        return True
    except Exception as e:
        st.session_state["lp_fallback"][_lp_key(class_label, subject, chapter, teacher_email)] = {
            "status": "submitted", "content_md": content_md
        }
        _set_lp_debug(f"SUBMIT ok=False | error={type(e).__name__}: {e} | used=fallback")
        return False



# ---------- Data helpers ----------
def _db_df(sql, params=()):
    if not get_connection or not callable(get_connection):
        return None
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute(sql, params); rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except Exception:
        return None

def get_teacher_classes(user_email: str):
    classes = []
    df = _db_df("SELECT class, section, subjects FROM users WHERE email=?", (user_email,))
    if df is not None and not df.empty:
        for _, r in df.iterrows():
            subjects = (r.get("subjects") or "").split(",")
            for s in [x.strip() for x in subjects if x.strip()]:
                label = f"{r.get('class','')}-{r.get('section','')} - {s}"
                classes.append({"label": label, "class": str(r.get("class","")), "section": str(r.get("section","")), "subject": s})
    if not classes:
        df2 = _db_df("SELECT class, section, subject FROM timetable WHERE teacher_email=?", (user_email,))
        if df2 is not None and not df2.empty:
            for _, r in df2.iterrows():
                label = f"{r.get('class','')}-{r.get('section','')} - {r.get('subject','')}"
                classes.append({"label": label, "class": str(r.get("class","")), "section": str(r.get("section","")), "subject": str(r.get("subject",""))})
    if not classes:
        classes = [
            {"label":"9-A - Chemistry", "class":"9-A", "section":"A", "subject":"Chemistry"},
            {"label":"9-A - Physics", "class":"9-A", "section":"A", "subject":"Physics"},
            {"label":"9-A - Mathematics", "class":"9-A", "section":"A", "subject":"Mathematics"},
            {"label":"9-C - Social", "class":"9-C", "section":"C", "subject":"Social"},
        ]
    return classes

def get_lessons_for_class(class_label: str, subject: str):
    for table in ["chapter_insights", "chapters", "syllabus"]:
        probe = _db_df(f"SELECT * FROM {table} LIMIT 1")
        if probe is None or probe.empty:
            continue
        cols = probe.columns.tolist()
        title_col = "chapter" if "chapter" in cols else ("title" if "title" in cols else cols[0])
        subject_col = "subject" if "subject" in cols else None
        class_col = "class" if "class" in cols else ("grade" if "grade" in cols else None)
        where, params = [], []
        if subject_col: where.append(f"{subject_col}=?"); params.append(subject)
        if class_col:   where.append(f"{class_col}=?");   params.append(class_label.split("-")[0])
        sql = f"SELECT DISTINCT {title_col} AS chapter FROM {table}"
        if where: sql += " WHERE " + " AND ".join(where)
        df = _db_df(sql, tuple(params))
        if df is not None and not df.empty:
            return [str(x) for x in df["chapter"].tolist()]
    if subject.lower().startswith("chem"):
        return ["Matter in Our Surroundings", "Atoms and Molecules", "Structure of the Atom", "Is Matter Around Us Pure?"]
    return [f"Lesson {i+1}" for i in range(6)]


# ---------- AI generator (ASCII-only markdown output, safe fallback) ----------
def _ai_client():
    if OpenAI is None:
        return None
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        return OpenAI(api_key=key)
    except Exception:
        return None

def generate_lesson_plan(grade: str, subject: str, chapter: str, detail_level: str = "detailed", include_examples: bool = True):
    client = _ai_client()
    bullets = {"concise": 3, "standard": 4, "detailed": 6}.get(detail_level, 6)
    words = {"concise": 10, "standard": 14, "detailed": 18}.get(detail_level, 18)
    ex_line = "Provide worked examples and sample questions in each relevant section." if include_examples else "Avoid long worked examples; keep explanations focused."

    if client:
        try:
            prompt = f"""You are an expert {subject} teacher. Create a classroom-ready 45-60 minute lesson plan for Grade {grade} on "{chapter}".
Write ONLY Markdown using ASCII punctuation.

# Title
{subject}: {chapter} - Lesson Plan (Grade {grade})

## Learning Objectives
- Provide {bullets} measurable objectives; each about {words}+ words.

## Prior Knowledge
- {bullets} bullet points; each {words}+ words explaining prerequisite understanding.

## Teaching Aids & Resources
- Concrete items: textbook pages, slides/visuals, lab apparatus, handouts/worksheets, URLs (if any). At least {bullets} items.

## Lesson Flow (Timeline)
- A block-by-block timeline with minute ranges and teacher moves and student actions. At least 5 blocks.
{ex_line}

## Activities
- 2-3 activities. For each: Goal, Materials, Steps (numbered, 4+), Expected Outcome, and one differentiation variation.

## Evaluation Tools
- Formative checks (3-5), an Exit Ticket (2-3 items with expected answers), and a small rubric table.

## Differentiation
- Support strategies (3+) and Extension strategies (2+).

## Homework (optional)
- 1 short task aligned with objectives.
"""
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role":"system","content":"You produce detailed, classroom-ready lesson plans in Markdown only."},
                    {"role":"user","content":prompt},
                ],
                temperature=0.4,
            )
            md = resp.choices[0].message.content
            if md:
                return md
        except Exception:
            pass

    # Fallback template
    return f"""# {subject}: {chapter} - Lesson Plan (Grade {grade})

## Learning Objectives
- Objective 1: description about {words}+ words explaining the action and outcome.
- Objective 2: description about {words}+ words focusing on skill or concept mastery.
- Objective 3: description about {words}+ words connecting to assessment evidence.

## Prior Knowledge
- Prior topic or idea with {words}+ words context.
- Vocabulary or formula students should recall with {words}+ words context.
- Common misconception to address with {words}+ words context.

## Teaching Aids & Resources
- Textbook chapter "{chapter}", board and markers, projector, worksheet.

## Lesson Flow (Timeline)
- 0-5 min | Warm-up and activation of prior knowledge.
- 5-20 min | Teach and model key idea with checks.
- 20-35 min | Guided practice in pairs.
- 35-50 min | Activity (see Activities).
- 50-55 min | Exit ticket.
- 55-60 min | Wrap-up and homework.

## Activities
1) Think-Pair-Share
   - Goal: activate prior knowledge.
   - Materials: board, timer.
   - Steps: Think -> Pair -> Share -> Scribe ideas.
   - Outcome: list of key ideas and misconceptions.
2) Group Task
   - Goal: apply concept in context.
   - Materials: worksheet.
   - Steps: groups of 4 -> tasks 1-4 -> gallery walk -> feedback.
   - Outcome: completed worksheet.

## Evaluation Tools
- Formative: mini-quiz, cold-call question, quick write.
- Exit Ticket: 2 short questions aligned to objectives.
- Rubric: Accuracy, Reasoning, Presentation (0-2 scale).

## Differentiation
- Support: sentence starters, worked examples, hints.
- Extension: challenge problem, research prompt.

## Homework (optional)
- Read pages X-Y; attempt problems M-N.
"""


# ---------- Top bar, breadcrumbs, nav ----------
def draw_top_bar(user_name: str = "Teacher"):
    left, center, right = st.columns([1,2,1])
    with left:
        st.markdown(f"<div class='dashboard-top-bar'><div>Welcome, {user_name}</div></div>", unsafe_allow_html=True)
    with center:
        shown = False
        for p in ["dps_banner.png", "static/dps_banner.png"]:
            if os.path.exists(p):
                st.image(p); shown = True; break
        if not shown:
            st.markdown("<div class='dashboard-logo'><h3>DPS Narasaraopet</h3></div>", unsafe_allow_html=True)
    with right:
        if st.button("Logout", key="logout_btn_teacher"):
            st.session_state.clear(); st.rerun()

def _breadcrumbs():
    crumbs = []
    if st.session_state["td_active"] is None:
        crumbs = [("Home", None)]
    else:
        sec = st.session_state["td_active"]
        label = next((t for (t,k) in SECTIONS if k == sec), sec)
        crumbs = [("Home", None), (label, "section")]
        if st.session_state["td_sub"]:
            _, item = st.session_state["td_sub"]
            crumbs.append((item, "sub"))
    st.markdown("<div class='breadcrumbs'>", unsafe_allow_html=True)
    for i, (label, kind) in enumerate(crumbs):
        if kind is None:
            if st.button(label, key="crumb_home"):
                st.session_state["td_active"] = None
                st.session_state["td_sub"] = None
                st.session_state["lp_selected_class"] = None
                st.session_state["lp_selected_lesson"] = None
                st.session_state["lp_view_lesson"] = None
                st.rerun()
        elif kind == "section":
            if st.button(label, key="crumb_section"):
                st.session_state["td_sub"] = None
                st.session_state["lp_selected_lesson"] = None
                st.session_state["lp_view_lesson"] = None
                st.rerun()
        else:
            st.markdown(f"<span class='crumb'>{label}</span>", unsafe_allow_html=True)
        if i < len(crumbs) - 1:
            st.markdown("<span class='sep'>/</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def _nav_card(title: str, key: str):
    st.markdown(f"<div class='nav-card'><div class='nav-title'>{title}</div></div>", unsafe_allow_html=True)
    if st.button("Open", key=f"open_{key}", use_container_width=True):
        st.session_state["td_active"] = key
        st.session_state["td_sub"] = None
        st.rerun()

def draw_top_cards():
    rows = [SECTIONS[i:i+3] for i in range(0, len(SECTIONS), 3)]
    for row in rows:
        cols = st.columns(len(row))
        for i, (title, key) in enumerate(row):
            with cols[i]:
                _nav_card(title, key)

def draw_subitem_chips(section_key: str):
    groups = SECTION_TO_GROUPS.get(section_key, [])
    for grp in groups:
        st.markdown(f"<div class='group-pill'>{grp}</div>", unsafe_allow_html=True)
        st.markdown("<div class='subchips-wrap'>", unsafe_allow_html=True)
        for item in GROUPS.get(grp, []):
            st.markdown(f"<div class='subchip'><div class='label'>{item}</div><div class='hint'>Open</div></div>", unsafe_allow_html=True)
            if st.button(f"Open -> {item}", key=f"chip_{section_key}_{grp}_{item}", use_container_width=True):
                st.session_state["td_sub"] = (grp, item); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ---------- Student Management pages ----------
def page_students_profiles():
    st.subheader("a) Student Profiles - Name, Roll No, Contact")
    df = pd.DataFrame([
        {"id":1,"roll_no":"6A-01","name":"Anika","contact":"9999990001"},
        {"id":2,"roll_no":"6A-02","name":"Ravi","contact":"9999990002"},
        {"id":3,"roll_no":"6A-03","name":"Neeraj","contact":"9999990003"},
    ])
    st.dataframe(df, use_container_width=True)

def page_students_attendance_entry():
    st.subheader("e) Attendance Entry")
    st.caption("Present / Absent / Late. Auto-sync with student app can be wired here.")
    roster = pd.DataFrame([{"roll_no":"6A-01","name":"Anika"},{"roll_no":"6A-02","name":"Ravi"}])
    for _, r in roster.iterrows():
        c1, c2, c3 = st.columns([2,3,3])
        with c1: st.text_input("Roll No", value=r["roll_no"], key=f"roll_{r['roll_no']}", disabled=True)
        with c2: st.text_input("Name",    value=r["name"],    key=f"name_{r['roll_no']}", disabled=True)
        with c3: st.selectbox("Status", ["Present","Absent","Late"], key=f"status_{r['roll_no']}")


# ---------- Lesson Plans (v2, robust) ----------
def page_lesson_plans_v2(user):
    _ensure_state()
    

    st.subheader("📚 Lesson Plans")
    dbg = _get_lp_debug()
    if dbg:
        st.caption(dbg)

    email = user.get("email", "teacher@example.com")
    classes = get_teacher_classes(email)

    st.caption("Generation settings")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.selectbox("Detail level", ["concise", "standard", "detailed"], index=2, key="lp_dl")
    with c2:
        st.checkbox("Include worked examples and sample questions", value=True, key="lp_ex")

    # Class tabs
    st.markdown("<div class='class-tabs'>", unsafe_allow_html=True)
    for idx, c in enumerate(classes):
        if st.button(c["label"][:12] + (".." if len(c["label"]) > 12 else ""), key=f"class_tab2_{idx}"):
            st.session_state["lp_selected_class"] = idx
            st.session_state["lp_selected_lesson"] = None
            st.session_state["lp_generated_md"] = ""
            st.session_state["lp_view_lesson"] = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    sel_idx = st.session_state.get("lp_selected_class")
    if sel_idx is None:
        st.info("Select a class to view its lessons.")
        return

    sel = classes[sel_idx]
    lessons = get_lessons_for_class(sel["class"], sel["subject"])

    st.markdown("<div class='lesson-list'>", unsafe_allow_html=True)
    for i, chapter in enumerate(lessons):
        col1, col2, col3 = st.columns([5, 1, 1])
        with col1:
            st.markdown(f"<div class='lesson-item'>{chapter}</div>", unsafe_allow_html=True)

        rec = get_plan_record(sel["class"], sel["subject"], chapter, email)
        status = _norm_status(rec.get("status")) if rec else None
        st.caption(f"keys(list)={sel['class']!r},{sel['subject']!r},{chapter!r},{email!r}")

        with col2:
            if status is None:
                if st.button("Generate", key=f"gen2_{i}"):
                    grade = "".join(ch for ch in sel["class"] if ch.isdigit()) or "9"
                    md = generate_lesson_plan(
                        grade=grade,
                        subject=sel["subject"],
                        chapter=chapter,
                        detail_level=st.session_state.get("lp_dl", "detailed"),
                        include_examples=st.session_state.get("lp_ex", True),
                    )
                    ok = upsert_lesson_plan_draft(sel["class"].strip(), sel["subject"].strip(), chapter.strip(), md, email.strip())
                    probe = get_plan_record(sel["class"], sel["subject"], chapter, email)
                    _set_lp_debug(f"UPSERT ok={ok} | probe.status={_norm_status(probe.get('status')) if probe else None} | keys=({sel['class']!r}, {sel['subject']!r}, {chapter!r}, {email!r})")
                    st.session_state["lp_selected_lesson"] = chapter
                    st.session_state["lp_generated_md"] = md
                    st.session_state["lp_view_lesson"] = None
                    st.rerun()
            else:
                st.button("Locked", key=f"locked2_{i}", disabled=True)

        with col3:
            if status == "draft":
                if st.button("Open", key=f"open2_{i}"):
                    st.session_state["lp_selected_lesson"] = chapter
                    st.session_state["lp_view_lesson"] = None
                    st.rerun()
            elif status == "submitted":
                if st.button("View", key=f"view2_{i}"):
                    st.session_state["lp_view_lesson"] = chapter
                    st.session_state["lp_selected_lesson"] = None
                    st.rerun()
            else:
                st.button("Open", key=f"open2_{i}", disabled=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Editor (draft only)
    chapter_sel = st.session_state.get("lp_selected_lesson")
    if chapter_sel:
        st.session_state["lp_view_lesson"] = None
        rec = get_plan_record(sel["class"], sel["subject"], chapter_sel, email)
        status = _norm_status(rec.get("status")) if rec else None
        if status == "submitted":
            st.session_state["lp_view_lesson"] = chapter_sel
            st.session_state["lp_selected_lesson"] = None
            st.rerun()

        st.markdown(f"### Edit Lesson Plan: *{chapter_sel}*")
        prefill_md = (rec.get("content_md") if rec else st.session_state.get("lp_generated_md", "")) or ""
        editor_key = f"lp_editor_md__{sel['class']}__{sel['subject']}__{chapter_sel}"

        left, right = st.columns([3, 1])
        with left:
            with st.form(f"lesson_plan_form__{editor_key}", clear_on_submit=False):
                md_val = st.text_area("Lesson Plan (Markdown)", value=prefill_md, key=editor_key, height=420)
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.form_submit_button("Regenerate AI", disabled=True, help="Disabled after first generation.")
                with c2:
                    submitted = st.form_submit_button("Submit Plan")
        with right:
            st.download_button("Download .md", data=md_val, file_name=f"{sel['class']}_{sel['subject']}_{chapter_sel}.md", use_container_width=True, key=f"lp_download_btn__{editor_key}")

        if submitted:
            submit_lesson_plan_by_keys(sel["class"], sel["subject"], chapter_sel, email, md_val)
            st.success("Plan submitted.")
            st.session_state["lp_selected_lesson"] = None
            st.session_state["lp_generated_md"] = ""
            st.session_state["lp_view_lesson"] = chapter_sel
            st.rerun()

    # Viewer (submitted only)
    if st.session_state.get("lp_view_lesson") and not st.session_state.get("lp_selected_lesson"):
        v_chapter = st.session_state["lp_view_lesson"]
        v_rec = get_plan_record(sel["class"], sel["subject"], v_chapter, email)
        v_md = (v_rec or {}).get("content_md", "")
        st.markdown(f"### View Lesson Plan (Submitted): *{v_chapter}*")
        st.markdown(v_md)
        _, v_right = st.columns([3, 1])
        with v_right:
            st.download_button("Download .md", data=v_md, file_name=f"{sel['class']}_{sel['subject']}_{v_chapter}.md", use_container_width=True, key=f"download_submitted_{sel['class']}_{sel['subject']}_{v_chapter}")
        if st.button("Close", key=f"close_view_{sel['class']}_{sel['subject']}_{v_chapter}"):
            st.session_state["lp_view_lesson"] = None
            st.rerun()


# ---------- Routing ----------
def route_students_subitem(user, grp: str, item: str):
    # View Students (new label) or legacy
    if "View Students" in item:
        page_students_profiles()
        return

    # Attendance (new) or legacy "Mark Attendance"
    if "Attendance" in item or "Mark Attendance" in item:
        page_students_attendance_entry()
        return

    if "Todays Logs" in item:
        st.info("Today's Logs: quick notes/events per class for today.")
        return

    if "Homework Given" in item:
        st.info("Homework Given: create and track homework for today.")
        return

    if "Correction Homework" in item:
        st.info("Correction: record checked Homework/Classwork/TextBook work.")
        return

    if "Assignment & Projects" in item:
        st.info("Assignments & Projects: create/track submissions and grading.")
        return

    if item.endswith("Marks") or "Marks" in item:
        st.info("Marks: enter/view marks; hook to your marks DB.")
        return

    # Academics crossover in Student group (safety)
    if "Lesson Plans" in item:
        page_lesson_plans_v2(user)
        return

    st.info("This Student Management item is not wired yet.")


def route_academics_subitem(user, item: str):
    # Use this for Year planner 
    if "Year Planner" in item:
        page_year_planner_v1(user)
        return
    
    # Reuse your Lesson Plans screen
    elif "Lesson Plans" in item:
        page_lesson_plans_v2(user)
    elif "Year Planner" in item:
        st.info("Year Planner: wire your planner view/editor here.")
    elif "Chapter-wise Learning Insights" in item:
        st.info("Chapter-wise Learning Insights: plug the existing student-dash render here.")
    else:
        st.info("This Academics item is not wired yet.")

def route_communication_subitem(user, item: str):
    if "Messages" in item:
        st.info("Messages: embed your messaging UI here.")
    elif "Whatsapp Logs" in item:
        st.info("WhatsApp logs: show your WA delivery/status table here.")
    elif "Complaints & Suggestions" in item:
        st.info("Complaints & Suggestions: build a simple inbox with filters.")
    elif "Birthday Reminders" in item:
        st.info("Birthday Reminders: show upcoming birthdays; send wishes.")
    elif "Gallery" in item:
        st.info("Gallery: upload and display class photos/albums.")
    elif "Self Leave System" in item:
        st.info("Self Leave System: teacher self-leave requests/approvals.")
    elif "Student Leaves" in item:
        st.info("Student Leaves: approve/track student leave applications.")
    else:
        st.info("This Communication item is not wired yet.")

def route_reports_subitem(user, item: str):
    if "Attendance Trends" in item:
        st.info("Attendance Trends: render weekly/monthly charts here.")
    elif "Top & Low Performers" in item:
        st.info("Top & Low Performers: list by last test or rolling average.")
    elif "Download reports - Exams" in item:
        st.info("Download Exams report: hook your export to CSV/XLSX/PDF.")
    elif "Download reports - Attendance" in item:
        st.info("Download Attendance report: hook your export engine here.")
    else:
        st.info("This Reports item is not wired yet.")

def route_settings_subitem(user, item: str):
    if "Profile" in item:
        st.info("Profile: reuse your teacher profile form here.")
    elif "Change Password" in item:
        st.info("Change Password: reuse your password change form here.")
    else:
        st.info("This Settings item is not wired yet.")


# ---------- Public entrypoint ----------
def render_teacher_dashboard(user: dict):
    _ensure_state()
    st.markdown(_UI_CSS, unsafe_allow_html=True)
    teacher_name = (user or {}).get("teacher_name", "Teacher")
    draw_top_bar(teacher_name)
    _breadcrumbs()

    if st.session_state["td_active"] is None:
        st.markdown("## Teacher Dashboard")
        st.caption("Select a card to continue")
        draw_top_cards()
        return

    section_key = st.session_state["td_active"]
    if st.session_state["td_sub"] is None:
        draw_subitem_chips(section_key)
        return

    grp, item = st.session_state["td_sub"]
    st.markdown(f"#### {grp} -> {item}")

    if section_key == "academics":
        route_academics_subitem(user, item)
    elif section_key == "students":
        route_students_subitem(user, grp, item)
    elif section_key == "comms":
        route_communication_subitem(user, item)
    elif section_key == "reports":
        route_reports_subitem(user, item)
    elif section_key == "settings":
        route_settings_subitem(user, item)
    else:
        st.info("Implementation pending for this section.")

# Local test
if __name__ == "__main__":
    render_teacher_dashboard({"teacher_name": "Teacher", "email": "teacher@example.com"})
