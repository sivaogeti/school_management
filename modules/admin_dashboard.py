import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_connection
from gupshup_sender import broadcast_notice  # NEW: WhatsApp broadcast

def render_admin_dashboard():
    st.title("👑 Admin Dashboard")

    conn = get_connection()
    cur = conn.cursor()
    
    # Sidebar Menu
    menu = st.sidebar.radio("📋 Menu", [
        "📊 View Marks",
        "📅 View Attendance",
        "📰 Manage Notices",
        "📆 Manage Timetable",
        "💰 Fee Overview"
    ])

    # --------------------------
    # 1️⃣ View Marks
    # --------------------------
    if menu == "📊 View Marks":
        st.subheader("📊 Student Marks")

        # Filters
        cur.execute("SELECT DISTINCT class FROM marks")
        class_list = [r[0] for r in cur.fetchall()]
        selected_class = st.selectbox("Select Class", class_list)

        cur.execute("SELECT DISTINCT section FROM marks WHERE class=?", (selected_class,))
        section_list = [r[0] for r in cur.fetchall()]
        selected_section = st.selectbox("Select Section", section_list)

        cur.execute("SELECT DISTINCT subject FROM marks WHERE class=? AND section=?", (selected_class, selected_section))
        subject_list = [r[0] for r in cur.fetchall()]
        selected_subject = st.selectbox("Select Subject", ["All"] + subject_list)

        # Query with filters
        if selected_subject == "All":
            cur.execute("""
                SELECT student_id, subject, marks, class, section, submitted_by, timestamp
                FROM marks
                WHERE class=? AND section=?
                ORDER BY timestamp DESC
            """, (selected_class, selected_section))
        else:
            cur.execute("""
                SELECT student_id, subject, marks, class, section, submitted_by, timestamp
                FROM marks
                WHERE class=? AND section=? AND subject=?
                ORDER BY timestamp DESC
            """, (selected_class, selected_section, selected_subject))

        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=[
                "Student ID", "Subject", "Marks", "Class", "Section", "Submitted By", "Submitted On"
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No marks found for selection.")

    # --------------------------
    # 2️⃣ View Attendance
    # --------------------------
    elif menu == "📅 View Attendance":
        st.subheader("📅 Attendance Records")

        # Filters
        cur.execute("SELECT DISTINCT class FROM users WHERE role='Student'")
        class_list = [r[0] for r in cur.fetchall()]
        selected_class = st.selectbox("Select Class", class_list)

        cur.execute("SELECT DISTINCT section FROM users WHERE class=? AND role='Student'", (selected_class,))
        section_list = [r[0] for r in cur.fetchall()]
        selected_section = st.selectbox("Select Section", section_list)

        cur.execute("""
            SELECT a.student_id, a.date, a.status, a.submitted_by, u.class, u.section
            FROM attendance a
            JOIN users u ON a.student_id = u.student_id
            WHERE u.class=? AND u.section=?
            ORDER BY a.date DESC
        """, (selected_class, selected_section))

        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Student ID", "Date", "Status", "Submitted By", "Class", "Section"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No attendance records found.")

    # --------------------------
    # 3️⃣ Manage Notices (UPDATED for WhatsApp)
    # --------------------------
    elif menu == "📰 Manage Notices":
        st.subheader("Add New Notice")

        title = st.text_input("Notice Title")
        new_notice = st.text_area("Enter Notice Message")
        expiry_date = st.date_input("Expiry Date", value=datetime.today())

        if st.button("📢 Publish Notice", key="admin_publish_notice"):
            if new_notice.strip():
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS notices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        message TEXT,
                        created_by TEXT,
                        expiry_date DATE,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    INSERT INTO notices (title, message, created_by, expiry_date)
                    VALUES (?, ?, ?, ?)
                """, (title.strip(), new_notice.strip(), "Admin", expiry_date))
                conn.commit()

                st.success("✅ Notice published!")

                # Send to WhatsApp via broadcast
                broadcast_notice(title.strip(), new_notice.strip())

                st.info("📢 Notice sent via WhatsApp to all students & parents.")
            else:
                st.warning("Please enter a notice message.")

        st.subheader("All Notices")
        cur.execute("SELECT title, message, expiry_date, timestamp FROM notices ORDER BY timestamp DESC")
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Title", "Notice", "Expiry Date", "Published On"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No notices yet.")

    # --------------------------
    # 4️⃣ Manage Timetable
    # --------------------------
    elif menu == "📆 Manage Timetable":
        st.subheader("Class Timetable Management")

        cur.execute("SELECT DISTINCT class FROM users WHERE role='Student' ORDER BY class")
        classes = [row[0] for row in cur.fetchall() if row[0]]
        if not classes:
            st.warning("⚠️ No classes found. Add students first.")
        else:
            class_choice = st.selectbox("Select Class", classes, key="admin_tt_class")

            cur.execute(
                "SELECT DISTINCT section FROM users WHERE role='Student' AND class=? ORDER BY section",
                (class_choice,),
            )
            sections = [row[0] for row in cur.fetchall() if row[0]]
            if sections:
                section_choice = st.selectbox("Select Section", sections, key="admin_tt_section")

                st.subheader("Current Timetable")
                cur.execute("""
                    SELECT day, period1, period2, period3, period4, period5, period6, period7
                    FROM timetable
                    WHERE class=? AND section=?
                    ORDER BY 
                        CASE day
                            WHEN 'Monday' THEN 1
                            WHEN 'Tuesday' THEN 2
                            WHEN 'Wednesday' THEN 3
                            WHEN 'Thursday' THEN 4
                            WHEN 'Friday' THEN 5
                            WHEN 'Saturday' THEN 6
                        END
                """, (class_choice, section_choice))
                rows = cur.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=[
                        "Day", "Period 1", "Period 2", "Period 3",
                        "Period 4", "Period 5", "Period 6", "Period 7"
                    ])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No timetable set yet for this Class & Section.")

                st.subheader("Add / Update Timetable")
                with st.form("update_tt_form"):
                    day = st.selectbox("Select Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
                    periods = []
                    for i in range(1, 8):
                        periods.append(st.text_input(f"Period {i}", key=f"p{i}_tt"))
                    submitted = st.form_submit_button("📂 Save Timetable")
                    if submitted:
                        cur.execute("""
                            INSERT OR REPLACE INTO timetable
                            (id, class, section, day, period1, period2, period3, period4, period5, period6, period7)
                            VALUES (
                                COALESCE(
                                    (SELECT id FROM timetable WHERE class=? AND section=? AND day=?),
                                    NULL
                                ),
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                            )
                        """, (
                            class_choice, section_choice, day,
                            class_choice, section_choice, day, *periods
                        ))
                        conn.commit()
                        st.success(f"✅ Timetable updated for {day}")

    # --------------------------
    # 5️⃣ Fee Overview
    # --------------------------
    elif menu == "💰 Fee Overview":
        st.subheader("Fee Management Overview")

        cur.execute("SELECT class, total_fee FROM fees ORDER BY class")
        fee_rows = cur.fetchall()
        fee_df = pd.DataFrame(fee_rows, columns=["Class", "Total Fee"]) if fee_rows else pd.DataFrame(columns=["Class","Total Fee"])
        st.write("### 1️⃣ Current Fee Structure")
        if not fee_df.empty:
            st.dataframe(fee_df, use_container_width=True)
        else:
            st.info("No fee structure defined yet.")

        st.write("### 2️⃣ Class-wise Collection & Dues Summary")
        summary_data = []
        for cls, total_fee in fee_rows:
            cur.execute("SELECT COUNT(*) FROM users WHERE role='Student' AND class=?", (cls,))
            total_students = cur.fetchone()[0]

            cur.execute("SELECT student_id FROM users WHERE role='Student' AND class=?", (cls,))
            student_ids = [r[0] for r in cur.fetchall()]

            collected = 0
            for sid in student_ids:
                cur.execute("SELECT SUM(amount) FROM payments WHERE student_id=?", (sid,))
                amt = cur.fetchone()[0]
                collected += amt or 0

            total_due = max(total_students * total_fee - collected, 0)
            summary_data.append([cls, total_students, total_fee, collected, total_due])

        if summary_data:
            summary_df = pd.DataFrame(summary_data, columns=[
                "Class", "Total Students", "Fee per Student (₹)", "Collected (₹)", "Due (₹)"
            ])
            st.dataframe(summary_df, use_container_width=True)
            st.write(f"**Grand Total Collected:** ₹{summary_df['Collected (₹)'].sum():,.2f}")
            st.write(f"**Grand Total Due:** ₹{summary_df['Due (₹)'].sum():,.2f}")
        else:
            st.info("No fee data to summarize yet.")

    conn.close()
