import streamlit as st
import pandas as pd
from db import get_connection
import hashlib

def render_admin_dashboard():
    st.title("👨‍💼 Admin Dashboard")

    st.sidebar.subheader("Admin Options")
    choice = st.sidebar.radio(
        "Select Option",
        ["Manage Users", "View Marks", "View Attendance", "Upload Timetable"],
        key="admin_radio"
    )

    conn = get_connection()
    cur = conn.cursor()

    # ---------------------
    # 1️⃣ Manage Users
    # ---------------------
    if choice == "Manage Users":
        st.subheader("➕ Add New User")
        with st.form("add_user_form"):
            role = st.selectbox("Role", ["Student", "Teacher"])
            student_id = st.text_input("Student ID (Leave blank for teachers)")
            student_name = st.text_input("Full Name")
            email = st.text_input("Email (Teachers only, optional for students)")
            password = st.text_input("Password", type="password")
            student_class = st.text_input("Class (Students only)")
            section = st.text_input("Section (Students only)")
            student_phone = st.text_input("Student Phone")
            parent_phone = st.text_input("Parent Phone")
            submit_btn = st.form_submit_button("Add User")

        if submit_btn:
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            try:
                cur.execute("""
                    INSERT INTO users (student_id, student_name, email, password, role, class, section, student_phone, parent_phone)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    student_id or None,
                    student_name,
                    email or None,
                    hashed_pw,
                    role,
                    student_class or None,
                    section or None,
                    student_phone or None,
                    parent_phone or None
                ))
                conn.commit()
                st.success(f"✅ {role} added successfully!")
            except Exception as e:
                st.error(f"❌ Error adding user: {e}")

        # Display current users
        st.subheader("👥 Current Users")
        cur.execute("SELECT student_id, student_name, email, role, class, section FROM users ORDER BY role, student_name")
        df = pd.DataFrame(cur.fetchall(), columns=["Student ID", "Name", "Email", "Role", "Class", "Section"])
        st.dataframe(df, use_container_width=True)

    # ---------------------
    # 2️⃣ View Marks
    # ---------------------
    elif choice == "View Marks":
        st.subheader("📊 All Marks")
        cur.execute("SELECT student_id, subject, marks, class, section, submitted_by, timestamp FROM marks ORDER BY timestamp DESC")
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=["Student ID", "Subject", "Marks", "Class", "Section", "Submitted By", "Submitted On"])
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("ℹ️ No marks submitted yet.")

    # ---------------------
    # 3️⃣ View Attendance
    # ---------------------
    elif choice == "View Attendance":
        st.subheader("📅 Attendance Records")
        cur.execute("SELECT student_id, date, status, submitted_by FROM attendance ORDER BY date DESC")
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=["Student ID", "Date", "Status", "Submitted By"])
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("ℹ️ No attendance data yet.")

    # ---------------------
    # 4️⃣ Upload Timetable
    # ---------------------
    elif choice == "Upload Timetable":
        st.subheader("📤 Upload Timetable (CSV/Excel)")
        uploaded_file = st.file_uploader("Upload Timetable File", type=["csv", "xlsx"])
        
        if uploaded_file:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.write("Preview of uploaded file:")
            st.dataframe(df.head())

            if st.button("✅ Save Timetable to DB", key="save_timetable"):
                for _, row in df.iterrows():
                    cur.execute("""
                        INSERT INTO timetable (class, section, day, period1, period2, period3, period4, period5, period6, period7)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, tuple(row))
                conn.commit()
                st.success("✅ Timetable uploaded successfully!")

    conn.close()
