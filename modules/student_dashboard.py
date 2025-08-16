import os
import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_connection
from streamlit_autorefresh import st_autorefresh

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")

# =========================================================
# ===============  LIGHT THEME (CSS)  =====================
# =========================================================
_UI_CSS_STUDENT = """
<style>
:root{
  --bg: #f9fafb;
  --card: #ffffff;
  --card-2: #f3f4f6;
  --text: #111827;
  --muted: #6b7280;
  --brand: #3b82f6;
  --brand-2:#10b981;
  --danger:#ef4444;
  --warn:#f59e0b;
  --accent:#6366f1;
  --shadow: 0 6px 16px rgba(0,0,0,.08);
  --radius: 14px;
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
  width:100%; border:1px solid #e5e7eb;
  background: linear-gradient(180deg, #ffffff, #f3f4f6);
  color: var(--text);
  padding:.55rem .8rem; border-radius:10px; margin-bottom:.35rem;
  text-align:left; cursor:pointer; transition:.2s ease;
}
.nav-btn:hover{ transform: translateY(-1px); border-color: var(--brand); }
.nav-btn.active{
  border-color: var(--brand); box-shadow: 0 0 0 2px rgba(59,130,246,.25) inset;
  background: linear-gradient(180deg, rgba(59,130,246,.1), #f3f4f6);
}

.card{
  border-radius: var(--radius);
  background: var(--card);
  border: 1px solid #e5e7eb;
  box-shadow: var(--shadow);
  padding: 18px 16px;
  margin-bottom: 14px;
}
.card-title{
  font-size: 1.1rem; font-weight: 700; margin-bottom:.25rem;
}
.card-subtle{ color: var(--muted); font-size:.9rem; margin-bottom:.75rem; }

.small{ font-size:.85rem; color: var(--muted); }

.stDataFrame { border-radius: var(--radius); overflow: hidden; }

/* Improve form labels */
.stSelectbox label,
.stTextInput label,
.stTextArea label,
.stNumberInput label,
.stDateInput label,
.stFileUploader label,
.stCheckbox div[data-testid="stMarkdownContainer"] {
  color: var(--text) !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
}

/* Checkbox accent */
.stCheckbox input[type="checkbox"] {
  accent-color: var(--brand-2);
}

/* Buttons */
.stButton button{
  border-radius: 10px;
  padding:.5rem 1rem;
  font-weight:600;
  border: none;
  cursor:pointer;
  background: var(--brand);
  color: #fff;
  box-shadow: var(--shadow);
}
.stButton button:hover{ filter: brightness(1.05); }
</style>
"""

# =========================================================
# ===============  SMALL RENDERING HELPERS  ===============
# =========================================================
def render_card(title: str, subtitle: str = ""):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if title:
        st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="card-subtle">{subtitle}</div>', unsafe_allow_html=True)

def end_card():
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ===============  SIDEBAR MENU GROUPS  ===================
# =========================================================
_GROUPS = {
    "📚 Academics": ["📊 My Marks", "✅ My Attendance", "📆 My Timetable", "🗂️ Homework / Syllabus / Gallery"],
    "📢 Communication": ["📰 School Notices", "📢 Message History", "📨 Messages"],
    "💰 Finance": ["💰 My Fees & Payments", "💰 Misc Fees"],
    "🎓 Student Life": ["📄 Apply Leave", "🏆 Achievements", "🍔 My Cafeteria", "🚌 Transport Info", "📅 School Visit", "🌐 E-Connect"]
}

def draw_sidebar():
    st.sidebar.markdown(_UI_CSS_STUDENT, unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-title'>MENU</div>", unsafe_allow_html=True)
    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = "📊 My Marks"

    for group, items in _GROUPS.items():
        st.sidebar.markdown(f"<div class='sidebar-title'>{group}</div>", unsafe_allow_html=True)
        for item in items:
            active = "active" if st.session_state.selected_menu == item else ""
            if st.sidebar.button(item, key=f"nav_{item}", use_container_width=True):
                st.session_state.selected_menu = item
        st.sidebar.markdown("<div style='height:.15rem'></div>", unsafe_allow_html=True)
    return st.session_state.selected_menu


def render_student_dashboard(user):
    st.markdown(_UI_CSS_STUDENT, unsafe_allow_html=True)
    st.title("🎓 Student Dashboard")

    sid = user.get("student_id")
    email = user.get("email")
    conn = get_connection()
    cur = conn.cursor()

    selected = draw_sidebar()

    # --- The rest of your dashboard routes remain same as before (cards wrapping sections) ---
    # For brevity, reuse the same logic you already have with render_card / end_card for each section.


    if selected == "📊 My Marks":
        render_card("📊 My Marks")
        st_autorefresh(interval=10000, key="marks_autorefresh")
        cur.execute("SELECT subject, marks, timestamp FROM marks WHERE student_id=? ORDER BY subject", (sid,))
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Subject", "Marks", "Last Updated"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No marks available yet.")
        end_card()

    elif selected == "✅ My Attendance":
        render_card("✅ My Attendance")
        cur.execute("SELECT date, status FROM attendance WHERE student_id=? ORDER BY date DESC", (sid,))
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Date", "Status"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No attendance records found.")
        end_card()

    elif selected == "📰 School Notices":
        render_card("📰 School Notices")
        today = datetime.today().strftime("%Y-%m-%d")
        cur.execute("""SELECT title, message, created_by, timestamp FROM notices 
                       WHERE expiry_date IS NULL OR expiry_date>=? ORDER BY timestamp DESC""", (today,))
        rows = cur.fetchall()
        if rows:
            for title, msg, creator, ts in rows:
                with st.expander(f"{title} — {ts}"):
                    st.write(msg)
                    st.caption(f"Posted by {creator}")
        else:
            st.info("No active notices.")
        end_card()

    elif selected == "📆 My Timetable":
        render_card("📆 My Timetable")
        cur.execute("SELECT day, period, subject, teacher FROM timetable WHERE class=? AND section=? ORDER BY day, period", (user.get("class"), user.get("section")))
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Day", "Period", "Subject", "Teacher"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No timetable found.")
        end_card()

    elif selected == "💰 My Fees & Payments":
        render_card("💰 My Fees & Payments")
        cur.execute("SELECT amount, method, date FROM payments WHERE student_id=? ORDER BY date DESC", (sid,))
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Amount (₹)", "Method", "Date"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No payment history found.")
        end_card()

    elif selected == "🗂️ Homework / Syllabus / Gallery":
        render_card("🗂️ Homework / Syllabus / Gallery")
        tabs = st.tabs(["Homework", "Syllabus", "Gallery"])
        end_card()

        with tabs[0]:
            render_card("📌 Homework")
            cur.execute("SELECT subject, description, due_date, file_url, assigned_by, timestamp FROM homework WHERE class=? AND section=? ORDER BY timestamp DESC", (user.get("class"), user.get("section")))
            rows = cur.fetchall()
            if rows:
                for subj, desc, due, fname, assigned_by, ts in rows:
                    with st.expander(f"{subj} — Due: {due} — {ts}"):
                        st.write(desc)
                        if fname:
                            st.download_button("Download File", open(os.path.join(UPLOAD_DIR, fname), "rb"), file_name=fname)
                        st.caption(f"Assigned by {assigned_by}")
            else:
                st.info("No homework posted.")
            end_card()

        with tabs[1]:
            render_card("📚 Syllabus")
            cur.execute("SELECT subject, file_url, uploaded_by, timestamp FROM syllabus WHERE class=? AND section=? ORDER BY timestamp DESC", (user.get("class"), user.get("section")))
            rows = cur.fetchall()
            if rows:
                for subj, fname, uploaded_by, ts in rows:
                    with st.expander(f"{subj} — {ts}"):
                        if fname:
                            st.download_button("Download Syllabus", open(os.path.join(UPLOAD_DIR, fname), "rb"), file_name=fname)
                        st.caption(f"Uploaded by {uploaded_by}")
            else:
                st.info("No syllabus uploaded.")
            end_card()

        with tabs[2]:
            render_card("🖼️ Gallery")
            cur.execute("""
                SELECT title, image_url, category, uploaded_by, timestamp 
                FROM gallery ORDER BY timestamp DESC
            """)
            rows = cur.fetchall()
            if rows:
                for title, fname, cat, uploaded_by, ts in rows:
                    with st.expander(f"{title} ({cat}) — {ts}"):
                        if fname:
                            if fname.startswith("http://") or fname.startswith("https://"):
                                st.image(fname)  # load from URL
                            else:
                                file_path = os.path.join(UPLOAD_DIR, fname)
                                if os.path.exists(file_path):
                                    st.image(file_path)
                        st.caption(f"Uploaded by {uploaded_by}")
            else:
                st.info("No gallery images uploaded.")
            end_card()


    elif selected == "📄 Apply Leave":
        render_card("📄 Apply Leave")
        reason = st.text_area("Reason")
        start = st.date_input("Start Date")
        end = st.date_input("End Date")
        if st.button("Submit Leave Request"):
            cur.execute("INSERT INTO leaves (student_id, class, section, reason, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?)", (sid, user.get("class"), user.get("section"), reason, start.isoformat(), end.isoformat()))
            conn.commit()
            st.success("Leave request submitted.")
        end_card()

    elif selected == "🏆 Achievements":
        render_card("🏆 Achievements")
        cur.execute("SELECT title, description, date_awarded, awarded_by, file_url FROM achievements WHERE student_id=? ORDER BY timestamp DESC", (sid,))
        rows = cur.fetchall()
        if rows:
            for title, desc, date_awarded, awarded_by, fname in rows:
                with st.expander(f"{title} — {date_awarded}"):
                    st.write(desc)
                    if fname:
                        file_path = os.path.join(UPLOAD_DIR, fname)
                        if os.path.exists(file_path):
                            st.download_button("Download Certificate", open(file_path, "rb"), file_name=fname)
                    st.caption(f"Awarded by {awarded_by}")
        else:
            st.info("No achievements found.")
        end_card()

    elif selected == "🍔 My Cafeteria":
        render_card("🍔 My Cafeteria")
        cur.execute("SELECT item_name, price FROM cafeteria_menu WHERE available=1")
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Item", "Price (₹)"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No menu items available.")
        end_card()

    elif selected == "🚌 Transport Info":
        render_card("🚌 Transport Info")
        cur.execute("SELECT route_name, pickup_point, driver_name, driver_phone FROM student_transport WHERE student_id=?", (sid,))
        row = cur.fetchone()
        if row:
            st.write(f"**Route:** {row[0]}")
            st.write(f"**Pickup Point:** {row[1]}")
            st.write(f"**Driver:** {row[2]} ({row[3]})")
        else:
            st.info("No transport details found.")
        end_card()

    elif selected == "📅 School Visit":
        render_card("📅 School Visit")
        purpose = st.text_input("Purpose")
        visit_date = st.date_input("Visit Date")
        if st.button("Submit Visit Request"):
            cur.execute("INSERT INTO school_visits (visitor_name, purpose, visit_date) VALUES (?, ?, ?)", (user.get("name"), purpose, visit_date.isoformat()))
            conn.commit()
            st.success("Visit request submitted.")
        end_card()

    elif selected == "🌐 E-Connect":
        render_card("🌐 E-Connect")
        cur.execute("SELECT title, description, file_url, link_url, uploaded_by, timestamp FROM econnect_resources ORDER BY timestamp DESC")
        rows = cur.fetchall()
        if rows:
            for title, desc, fname, link, uploaded_by, ts in rows:
                with st.expander(f"{title} — {ts}"):
                    st.write(desc)
                    if fname:
                        file_path = os.path.join(UPLOAD_DIR, fname)
                        if os.path.exists(file_path):
                            st.download_button("Download Resource", open(file_path, "rb"), file_name=fname)
                    if link:
                        st.markdown(f"[Open Link]({link})")
                    st.caption(f"Uploaded by {uploaded_by}")
        else:
            st.info("No resources available.")
        end_card()

    elif selected == "💰 Misc Fees":
        render_card("💰 Misc Fees")
        cur.execute("SELECT description, amount, due_date, paid, paid_on FROM misc_fees WHERE student_id=? ORDER BY due_date DESC", (sid,))
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Description", "Amount (₹)", "Due Date", "Paid", "Paid On"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No miscellaneous fees found.")
        end_card()

    elif selected == "📢 Message History":
        render_card("📢 Message History")
        cur.execute("SELECT sender_email, receiver_email, message, timestamp FROM messages WHERE receiver_email=? OR sender_email=? ORDER BY timestamp DESC", (email, email))
        rows = cur.fetchall()
        if rows:
            for sender, receiver, msg, ts in rows:
                st.markdown(f"**{sender}** → **{receiver}** ({ts}): {msg}")
        else:
            st.info("No messages yet.")
        end_card()

    elif selected == "📨 Messages":
        render_card("📨 Messages")
        cur.execute("SELECT DISTINCT sender_email FROM messages WHERE receiver_email=?", (email,))
        senders = [row[0] for row in cur.fetchall()]
        if senders:
            choice = st.selectbox("Select sender", senders)
            cur.execute("""SELECT sender_email, message, timestamp FROM messages 
                           WHERE (sender_email=? AND receiver_email=?) OR (sender_email=? AND receiver_email=?) 
                           ORDER BY timestamp DESC""", (choice, email, email, choice))
            rows = cur.fetchall()
            for sender, msg, ts in rows:
                st.markdown(f"**{sender}** ({ts}): {msg}")
        else:
            st.info("No conversations found.")
        end_card()

    conn.close()
