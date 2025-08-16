# modules/frontoffice_dashboard.py
import os
from datetime import datetime, date
import streamlit as st
import pandas as pd
from db import get_connection
from gupshup_sender import send_gupshup_whatsapp, send_file_upload_alert
from db import insert_notice
from modules.teacher_dashboard import _UI_CSS  # reuse same CSS

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------
# Ensure DB tables exist
# --------------------------
def _ensure_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT, date TEXT, status TEXT, submitted_by TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, message TEXT, created_by TEXT,
        class TEXT, section TEXT, expiry_date TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT, title TEXT, file_path TEXT,
        uploaded_by TEXT, class TEXT, section TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS fees (class TEXT PRIMARY KEY, total_fee REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT, amount REAL, paid_on TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS transport_routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_name TEXT, driver_name TEXT, driver_contact TEXT,
        vehicle_number TEXT, stops TEXT, timing TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS student_transport (
        student_id TEXT, route_id INTEGER, pickup_point TEXT, drop_point TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id TEXT, recipient_group TEXT, message TEXT,
        attachment_path TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS library_books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, author TEXT, isbn TEXT, available INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS library_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER, student_id TEXT,
        issue_date TEXT, return_date TEXT, returned INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS visitor_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, purpose TEXT, in_time TEXT, out_time TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS enquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, contact TEXT, query TEXT, follow_up_date TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS website_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_name TEXT, content_html TEXT, last_updated TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS student_health (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT, student_name TEXT, blood_group TEXT,
        checkup_date TEXT, height REAL, weight REAL,
        notes TEXT, doctor_name TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS admissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, dob TEXT, contact TEXT,
        applied_class TEXT, status TEXT, documents_path TEXT)""")
    conn.commit()
    conn.close()

# --------------------------
# Sidebar (grouped like teacher_dashboard)
# --------------------------
MENU_GROUPS = {
    "📆 Attendance": ["📆 Mark Attendance"],
    "📰 Communication": ["📰 Publish Notices", "📨 Messages"],
    "📂 Documents": ["📂 File Uploads"],
    "💰 Finance": ["💰 Manage Fees"],
    "🚌 Transport": ["🚌 Transport Management"],
    "📚 Library": ["📚 Library Management"],
    "🏢 Visitors": ["🏢 Visitor Log", "📞 Enquiries"],
    "📝 Admissions": ["📝 Admission Management"],
    "🏥 Health": ["🏥 Student Health Records"],
    "🌐 Website": ["🌐 Website Management"],
    "🍔 Cafeteria": ["🍔 Cafeteria"],
}

# Map visible sidebar labels -> internal route keys already used below
ROUTE_ALIASES = {
    "📆 Mark Attendance": "attendance",
    "📰 Publish Notices": "notices",
    "📨 Messages": "Messages",
    "📂 File Uploads": "files",
    "💰 Manage Fees": "Fees",
    "🚌 Transport Management": "transport",
    "📚 Library Management": "library",
    "🏢 Visitor Log": "Visitors",
    "📞 Enquiries": "enquiries",
    "📝 Admission Management": "admissions",
    "🏥 Student Health Records": "health",
    "🌐 Website Management": "website",
    "🍔 Cafeteria": "cafeteria",
}


# --------------------------
# Sidebar (grouped like teacher_dashboard)
# --------------------------
def grouped_sidebar():
    st.sidebar.markdown(_UI_CSS, unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-title'>MENU</div>", unsafe_allow_html=True)
    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = "📆 Mark Attendance"

    for group, items in MENU_GROUPS.items():
        st.sidebar.markdown(f"<div class='sidebar-title'>{group}</div>", unsafe_allow_html=True)
        for item in items:
            if st.sidebar.button(item, key=f"nav_{item}", use_container_width=True):
                st.session_state.selected_menu = item
        st.sidebar.markdown("<div style='height:.2rem'></div>", unsafe_allow_html=True)

    return st.session_state.selected_menu

# --------------------------
# Main dashboard
# --------------------------
def render_frontoffice_dashboard(user=None):    
    st.markdown(_UI_CSS, unsafe_allow_html=True)  # ensure same styling
    st.title("🏢 Front Office Dashboard")
    _ensure_tables()

    conn = get_connection()
    cur = conn.cursor()
    choice = grouped_sidebar()

    if not choice:
        st.info("Select an option from the menu.")
        return
        
    route = ROUTE_ALIASES.get(choice, choice)  # normalize the label to your old keys
    
    # --------------------------
    # now use emoji-matched routes
    # --------------------------
    # --------------------------
    # 📆 Mark Attendance
    # --------------------------
    if route == "attendance":
        st.subheader("📆 Mark Attendance (Today)")
        today = date.today().isoformat()
        cur.execute("SELECT student_id, student_name, class, section FROM users WHERE role='Student' ORDER BY class, section, student_name")
        students = cur.fetchall()
        if not students:
            st.info("No students found.")
        else:
            for sid, sname, cls, sec in students:
                key = f"att_{sid}"
                status = st.selectbox(f"{sname} ({cls}-{sec})", ["Present", "Absent", "Late"], key=key)
                if st.button(f"Save {sname}", key=f"btn_{sid}"):
                    cur.execute("""
                        INSERT INTO attendance (student_id, date, status, submitted_by)
                        VALUES (?, ?, ?, ?)
                    """, (sid, today, status, user or "frontoffice"))
                    conn.commit()
                    st.success(f"Saved attendance for {sname}.")

    # --------------------------
    # 📰 Publish Notices
    # --------------------------
    elif route == "notices":
        st.subheader("📰 Publish Notices")
        with st.form("notice_form"):
            title = st.text_input("Title")
            message = st.text_area("Message")
            target_class = st.selectbox("Class (leave blank for all)", [""] + [str(i) for i in range(1, 13)])
            target_section = st.selectbox("Section (leave blank for all)", ["", "A", "B"])
            expiry = st.date_input("Expiry date (optional)", value=None)
            submit = st.form_submit_button("Publish Notice and Broadcast")
        if submit:
            if not message.strip():
                st.error("Message cannot be empty.")
            else:
                # use helper if available
                try:
                    insert_notice(title or "Notice", message.strip(), created_by=(user or "Front Office"),
                                  class_name=(target_class or None),
                                  section=(target_section or None),
                                  expiry_date=(expiry.isoformat() if expiry else None))
                except Exception:
                    # fallback insert
                    cur.execute("""
                        INSERT INTO notices (title, message, created_by, class, section, expiry_date)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (title or "Notice", message.strip(), (user or "Front Office"),
                          target_class or None, target_section or None, expiry.isoformat() if expiry else None))
                    conn.commit()

                st.success("Notice saved.")
                q = "SELECT student_id, student_phone, parent_phone FROM users WHERE role='Student'"
                params = []
                if target_class:
                    q += " AND class=?"
                    params.append(target_class)
                if target_section:
                    q += " AND section=?"
                    params.append(target_section)
                cur.execute(q, params)
                rows = cur.fetchall()
                msg_full = f"📢 {title}\n\n{message.strip()}"
                for sid, sphone, pphone in rows:
                    if sphone:
                        send_gupshup_whatsapp(sphone, msg_full, sid)
                    if pphone:
                        send_gupshup_whatsapp(pphone, "👨‍👩‍👦 Parent Alert: " + msg_full, sid)
                st.success(f"Broadcast attempted to {len(rows)} students (check logs).")

        st.subheader("All Notices")
        cur.execute("SELECT title, message, created_by, class, section, expiry_date, timestamp FROM notices ORDER BY timestamp DESC")
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Title", "Message", "Created By", "Class", "Section", "Expiry", "Published On"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No notices yet.")

    # --------------------------
    # 📂 File Uploads
    # --------------------------
    # 📂 File Uploads
    elif route == "files":
        st.subheader("📂 File Uploads")
        st.markdown('<div class="card"><div class="card-title">➕ Upload File</div>', unsafe_allow_html=True)
        category = st.selectbox("Category", ["gallery","homework","syllabus"])
        title = st.text_input("Title")
        file = st.file_uploader("Choose a file")
        ...
        st.markdown('</div>', unsafe_allow_html=True)

    # 💰 Manage Fees
    elif route == "Fees":
        st.subheader("💰 Manage Fees")
        ...
        st.markdown('<div class="card"><div class="card-title">➕ Add/Update Fee per Class</div>', unsafe_allow_html=True)
        fee_class = st.text_input("Class")
        total_fee = st.number_input("Total Fee (₹)",min_value=0.0,step=100.0)
        if st.button("Save Fee"): ...
        st.markdown('</div>', unsafe_allow_html=True)

    # 🚌 Transport → wrap Add Route and Assign Student in cards
    elif route == "transport":
        st.subheader("🚍 Transport Management")
        ...
        st.markdown('<div class="card"><div class="card-title">➕ Add New Route</div>', unsafe_allow_html=True)
        route_name = st.text_input("Route Name")
        ...
        if st.button("Add Route"): ...
        st.markdown('</div>', unsafe_allow_html=True)

    # 📨 Messages
    elif route == "Messages":
        st.subheader("📨 Messages")
        ...
        st.markdown('<div class="card"><div class="card-title">📩 Send Message</div>', unsafe_allow_html=True)
        sender_id = st.text_input("Sender ID", value=(user or "frontoffice"))
        ...
        if st.button("Send"): ...
        st.markdown('</div>', unsafe_allow_html=True)

    # 📚 Library (already card styled in your file)
    elif route == "library":
        ...

    # 🏢 Visitor Log
    elif route == "Visitors":
        st.subheader("🏢 Visitor Log")
        st.markdown('<div class="card"><div class="card-title">➕ Add Visitor</div>', unsafe_allow_html=True)
        name = st.text_input("Visitor Name")
        ...
        if st.button("Save Visitor"): ...
        st.markdown('</div>', unsafe_allow_html=True)
        ...

    # 📞 Enquiries
    elif route == "enquiries":
        st.subheader("📞 Enquiries")
        st.markdown('<div class="card"><div class="card-title">➕ Add Enquiry</div>', unsafe_allow_html=True)
        name = st.text_input("Name")
        ...
        if st.button("Save Enquiry"): ...
        st.markdown('</div>', unsafe_allow_html=True)
        ...

    # 📝 Admissions
    elif route == "admissions":
        st.subheader("📝 Admission Management")
        st.markdown('<div class="card"><div class="card-title">➕ Add New Admission</div>', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        ...
        if st.button("Add Admission", use_container_width=True): ...
        st.markdown('</div>', unsafe_allow_html=True)
        ...

    # 🏥 Health
    elif route == "health":
        st.subheader("🏥 Student Health Records")
        st.markdown('<div class="card"><div class="card-title">➕ Add / Update Health Record</div>', unsafe_allow_html=True)
        student_id = st.text_input("Student ID")
        ...
        if st.button("Save Health Record"): ...
        st.markdown('</div>', unsafe_allow_html=True)
        ...

    # 🌐 Website Management
    elif route == "website":
        st.subheader("🌐 Website Management")
        ...
        st.markdown('<div class="card"><div class="card-title">📝 Edit/Add Page</div>', unsafe_allow_html=True)
        page_name = st.text_input("Page Name")
        ...
        if st.button("Save Page"): ...
        st.markdown('</div>', unsafe_allow_html=True)

    # 🍔 Cafeteria
    elif route == "cafeteria":
        st.subheader("🍔 Cafeteria")
        st.info("Cafeteria module coming soon.")

    conn.close()