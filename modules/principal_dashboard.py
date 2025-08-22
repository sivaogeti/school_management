# modules/principal_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from db import get_connection
#from modules.teacher_dashboard import _UI_CSS  # reuse unified CSS

# Try to use your shared UI helpers; provide a safe fallback for metric_row if not available.
try:
    from modules.ui_theme import metric_row
except Exception:
    def metric_row(items):
        cols = st.columns(len(items))
        for col, (label, value) in zip(cols, items):
            with col:
                st.markdown(
                    '<div class="card"><div class="card-title">{}</div>'
                    '<div style="font-size:2rem;font-weight:700">{}</div></div>'.format(label, value),
                    unsafe_allow_html=True
                )

# --------------------------
# Helpers
# --------------------------
def _get_scalar(cur, query, args=()):
    cur.execute(query, args)
    row = cur.fetchone()
    return row[0] if row and row[0] is not None else 0

def _ensure_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS examinations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_name TEXT, subject TEXT, date TEXT, max_marks INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS principal_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note TEXT, created_at TEXT DEFAULT (DATE('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT, amount REAL, paid_on TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS misc_fees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT, amount REAL, paid INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT, student_name TEXT, role TEXT, class TEXT, section TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT, date TEXT, status TEXT, submitted_by TEXT
    )""")
    conn.commit()
    conn.close()

# --------------------------
# Sidebar (match frontoffice style)
# --------------------------
MENU_GROUPS = {
    "📊 Overview": ["📊 School Overview", "✅ Attendance Analytics", "💰 Fees Analytics"],
    "📅 Academics": ["🧾 Upcoming Exams"],
    "📝 Notes": ["📝 Principal Notes"],
}

ROUTE_ALIASES = {
    "📊 School Overview": "overview",
    "✅ Attendance Analytics": "attendance",
    "💰 Fees Analytics": "fees",
    "🧾 Upcoming Exams": "exams",
    "📝 Principal Notes": "notes",
}

def grouped_sidebar():
    st.sidebar.markdown(_UI_CSS, unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-title'>MENU</div>", unsafe_allow_html=True)
    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = "📊 School Overview"

    for group, items in MENU_GROUPS.items():
        st.sidebar.markdown(f"<div class='sidebar-title'>{group}</div>", unsafe_allow_html=True)
        for item in items:
            if st.sidebar.button(item, key=f"nav_{item}", use_container_width=True):
                st.session_state.selected_menu = item
        st.sidebar.markdown("<div style='height:.2rem'></div>", unsafe_allow_html=True)

    return st.session_state.selected_menu

# --------------------------
# Dashboard
# --------------------------
def render_principal_dashboard(user=None):
    st.markdown(_UI_CSS, unsafe_allow_html=True)
    st.title("🎓 Principal Dashboard — Overview & Analytics")

    _ensure_tables()
    conn = get_connection()
    cur = conn.cursor()

    choice = grouped_sidebar()
    route = ROUTE_ALIASES.get(choice, choice)

    # 📊 School Overview
    if route == "overview":
        st.markdown('<div class="card"><div class="card-title">📊 School Overview</div>', unsafe_allow_html=True)

        total_students = _get_scalar(cur, "SELECT COUNT(*) FROM users WHERE role='Student'")
        total_teachers = _get_scalar(cur, "SELECT COUNT(*) FROM users WHERE role='Teacher'")
        pending_admissions = _get_scalar(cur, "SELECT COUNT(*) FROM admissions WHERE status='Pending'")

        metric_row([
            ("Students", total_students),
            ("Teachers", total_teachers),
            ("Pending Admissions", pending_admissions),
        ])
        st.markdown('</div>', unsafe_allow_html=True)

    # ✅ Attendance Analytics
    elif route == "attendance":
        att_date = st.sidebar.date_input("Attendance Date", value=date.today())
        st.markdown(
            f'<div class="card"><div class="card-title">✅ Attendance Summary ({att_date.isoformat()})</div>',
            unsafe_allow_html=True
        )

        present_today = _get_scalar(cur,
            "SELECT COUNT(*) FROM attendance WHERE date = ? AND status='Present'",
            (att_date.isoformat(),))
        total_marked_today = _get_scalar(cur,
            "SELECT COUNT(*) FROM attendance WHERE date = ?",
            (att_date.isoformat(),))
        pct = round((present_today / total_marked_today) * 100, 1) if total_marked_today else 0.0

        metric_row([
            ("Attendance %", f"{pct}%"),
            ("Present", present_today),
            ("Marked", total_marked_today),
        ])

        # Donut (Present vs Absent/Late)
        cur.execute("""
            SELECT status, COUNT(*) as cnt
            FROM attendance
            WHERE date = ?
            GROUP BY status
        """, (att_date.isoformat(),))
        rows = cur.fetchall()
        if rows:
            df_pie = pd.DataFrame(rows, columns=["Status", "Count"])
            fig_pie = px.pie(df_pie, names="Status", values="Count", hole=0.55, title="Present vs Absent")
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No attendance records found.")

        # Class-wise %
        cur.execute("""
            SELECT u.class, u.section,
                   AVG(CASE WHEN a.status='Present' THEN 1.0 ELSE 0.0 END) * 100.0 AS pct_present
            FROM attendance a
            JOIN users u ON u.student_id = a.student_id
            WHERE a.date = ? AND u.role='Student'
            GROUP BY u.class, u.section
            ORDER BY u.class, u.section
        """, (att_date.isoformat(),))
        rows = cur.fetchall()
        if rows:
            df_bar = pd.DataFrame(rows, columns=["Class", "Section", "% Present"])
            df_bar["Class-Section"] = df_bar["Class"].astype(str) + "-" + df_bar["Section"].astype(str)
            fig_bar = px.bar(df_bar, x="Class-Section", y="% Present", title="Class-wise Attendance %")
            fig_bar.update_layout(yaxis=dict(range=[0, 100]))
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # 💰 Fees Analytics
    elif route == "fees":
        st.markdown('<div class="card"><div class="card-title">💰 Fees Summary</div>', unsafe_allow_html=True)

        collected = float(_get_scalar(cur, "SELECT COALESCE(SUM(amount),0) FROM payments"))
        pending_misc = float(_get_scalar(cur, "SELECT COALESCE(SUM(amount),0) FROM misc_fees WHERE paid=0"))

        metric_row([
            ("Collected (₹)", f"{collected:,.2f}"),
            ("Pending (misc) (₹)", f"{pending_misc:,.2f}"),
        ])

        df = pd.DataFrame({"Type": ["Collected", "Pending (misc)"], "Amount": [collected, pending_misc]})
        if df["Amount"].sum() > 0:
            fig = px.pie(df, names="Type", values="Amount", hole=0.55, title="Fees Collected vs Pending")
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No fee data found.")

        st.markdown('</div>', unsafe_allow_html=True)

    # 🧾 Upcoming Exams
    elif route == "exams":
        st.markdown('<div class="card"><div class="card-title">📅 Upcoming Exams</div>', unsafe_allow_html=True)

        cur.execute("""
            SELECT exam_name, subject, date, max_marks
            FROM examinations
            WHERE date >= DATE('now')
            ORDER BY date ASC
            LIMIT 20
        """)
        upcoming_exams = cur.fetchall()
        if upcoming_exams:
            df_upcoming = pd.DataFrame(upcoming_exams, columns=["Exam Name", "Subject", "Date", "Max Marks"])
            st.dataframe(df_upcoming, use_container_width=True)
        else:
            st.info("No upcoming exams.")

        st.markdown('</div>', unsafe_allow_html=True)

    # 📝 Principal Notes
    elif route == "notes":
        st.markdown('<div class="card"><div class="card-title">📝 Principal Notes</div>', unsafe_allow_html=True)

        cur.execute("SELECT note, created_at FROM principal_notes ORDER BY created_at DESC, id DESC")
        notes = cur.fetchall()
        if notes:
            for note, created_at in notes:
                st.markdown(f"**{created_at}** — {note}")
        else:
            st.info("No notes yet.")

        new_note = st.text_area("Add Note")
        if st.button("Save Note"):
            cur.execute("INSERT INTO principal_notes (note, created_at) VALUES (?, DATE('now'))", (new_note,))
            conn.commit()
            st.success("Note saved.")
            st.experimental_rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    conn.close()
