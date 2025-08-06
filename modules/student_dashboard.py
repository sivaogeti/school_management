import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from db import get_connection

def render_student_dashboard(user):
    st.title("🎓 Student Dashboard")

    # =========================
    # 1️⃣ Persistent Menu
    # =========================
    menu = st.radio(
        "Select an option",
        ["My Marks", "My Attendance", "School Notices", "My Timetable"],
        key="student_menu"
    )

    # =========================
    # 2️⃣ Manual Refresh Button
    # =========================
    if st.button("🔄 Refresh Data", key="refresh_btn"):
        st.session_state["refresh_trigger"] = True
        st.rerun()

    # =========================
    # 3️⃣ Auto-Refresh Every 60s
    # =========================
    # Streamlit doesn’t have st.autorefresh, use st.empty with time check
    refresh_placeholder = st.empty()
    current_time = datetime.now().strftime("%H:%M:%S")
    refresh_placeholder.caption(f"⏳ Last refreshed at {current_time}")
    # Note: True auto-refresh via rerun is tricky; here we show last refresh time

    conn = get_connection()
    cur = conn.cursor()

    # =========================
    # 4️⃣ My Marks
    # =========================
    if menu == "My Marks":
        st.subheader("📊 My Marks")
        cur.execute("""
            SELECT subject, marks, class, section, timestamp
            FROM marks
            WHERE student_id=?
            ORDER BY timestamp DESC
        """, (user["student_id"],))
        rows = cur.fetchall()

        if rows:
            df = pd.DataFrame(rows, columns=["Subject", "Marks", "Class", "Section", "Submitted On"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("ℹ️ No marks available yet.")

    # =========================
    # 5️⃣ My Attendance
    # =========================
    elif menu == "My Attendance":
        st.subheader("🗓 My Attendance")
        cur.execute("""
            SELECT date, status, submitted_by
            FROM attendance
            WHERE student_id=?
            ORDER BY date DESC
        """, (user["student_id"],))
        rows = cur.fetchall()

        if rows:
            df = pd.DataFrame(rows, columns=["Date", "Status", "Marked By"])
            st.dataframe(df, use_container_width=True)

            # Attendance summary
            present_count = sum(1 for r in rows if r[1] == "Present")
            absent_count = sum(1 for r in rows if r[1] == "Absent")
            total_days = len(rows)

            st.metric("Total Days", total_days)
            st.metric("Present", present_count)
            st.metric("Absent", absent_count)
        else:
            st.info("ℹ️ No attendance records yet.")

    # =========================
    # 6️⃣ School Notices
    # =========================
    elif menu == "School Notices":
        st.subheader("📢 School Notices")

        # Optional: Only show notices for student's class/section
        try:
            cur.execute("""
                SELECT title, message, timestamp
                FROM notices
                ORDER BY timestamp DESC
            """)
            rows = cur.fetchall()

            if rows:
                for title, message, ts in rows:
                    st.markdown(f"### 📌 {title}")
                    st.markdown(f"{message}")
                    st.caption(f"Published on {ts}")
                    st.markdown("---")
            else:
                st.info("ℹ️ No notices yet.")
        except sqlite3.OperationalError:
            st.warning("⚠️ Notices table not found in DB.")

    # =========================
    # 7️⃣ My Timetable
    # =========================
    elif menu == "My Timetable":
        st.subheader("📅 My Class Timetable")

        if "class" not in user or "section" not in user:
            st.error("❌ Class and Section info not found for this student.")
        else:
            try:
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
                            WHEN 'Sunday' THEN 7
                        END
                """, (user["class"], user["section"]))
                rows = cur.fetchall()

                if rows:
                    df = pd.DataFrame(
                        rows,
                        columns=["Day", "Period 1", "Period 2", "Period 3", "Period 4",
                                 "Period 5", "Period 6", "Period 7"]
                    )
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("ℹ️ Timetable not yet uploaded for your class.")
            except sqlite3.OperationalError:
                st.warning("⚠️ Timetable table not found in DB.")

    conn.close()
