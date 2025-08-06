import streamlit as st
import pandas as pd
import sqlite3
import os
from db import get_connection, init_db

from db import init_db
init_db()  # Ensure tables exist

# =========================
# 🔹 Admin Role Check
# =========================
if "user" not in st.session_state:
    st.error("❌ Please login first!")
    st.stop()
elif st.session_state["user"]["role"] != "Admin":
    st.error("⛔ Access Denied: Admins only")
    st.stop()

st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("🛠️ Admin Dashboard")

# =========================
# 🔹 Sidebar Menu
# =========================
menu = st.sidebar.radio("📌 Navigation", ["User Management", "Timetable Upload", "Logout"])

# =========================
# 🔹 Logout
# =========================
if menu == "Logout":
    st.session_state.clear()
    st.success("✅ Logged out successfully!")
    st.rerun()

# =========================
# 🔹 User Management
# =========================
elif menu == "User Management":
    st.subheader("👥 Manage Users")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT student_id, student_name, email, role, class, section FROM users ORDER BY role, student_name")
    data = cur.fetchall()
    conn.close()

    if data:
        df = pd.DataFrame(data, columns=["Student ID", "Name", "Email", "Role", "Class", "Section"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("ℹ️ No users found in the system.")

# =========================
# 🔹 Timetable Upload
# =========================
elif menu == "Timetable Upload":
    st.subheader("📅 Upload Class Timetable")

    st.write("Upload a CSV/Excel file with columns:")
    st.code("class,section,day,period1,period2,period3,period4,period5,period6,period7")

    uploaded_file = st.file_uploader("Upload Timetable File", type=["csv", "xlsx"])

    if uploaded_file is not None:
        # Read file into DataFrame
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.write("Preview of Uploaded File:")
        st.dataframe(df.head(), use_container_width=True)

        if st.button("✅ Save to Database"):
            conn = get_connection()
            cur = conn.cursor()

            inserted = 0
            for _, row in df.iterrows():
                cur.execute("""
                    INSERT INTO timetable(class, section, day, period1, period2, period3, period4, period5, period6, period7)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['class'], row['section'], row['day'],
                    row['period1'], row['period2'], row['period3'], row['period4'],
                    row['period5'], row['period6'], row['period7']
                ))
                inserted += 1

            conn.commit()
            conn.close()
            st.success(f"✅ Timetable uploaded successfully with {inserted} rows.")
