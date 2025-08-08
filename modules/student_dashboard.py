# modules/student_dashboard.py
import streamlit as st
import pandas as pd
from db import get_connection
from gupshup_sender import send_in_app_and_whatsapp  # handles DB-insert + WhatsApp send

def render_student_dashboard(user):
    st.title(f"🎓 Welcome, {user.get('student_name','Student')}")

    conn = get_connection()
    cur = conn.cursor()

    # Sidebar Menu
    menu = st.sidebar.radio("📋 Menu", [
        "📊 My Marks",
        "🗕️ My Attendance",
        "📰 School Notices",
        "📆 My Timetable",
        "💰 My Fees & Payments",
        "📢 Message History",
        "📨 Messages"
    ])

    # ---------------------------
    # 1️⃣ My Marks
    # ---------------------------
    if menu == "📊 My Marks":
        cur.execute("""
            SELECT subject, marks, class, section
            FROM marks
            WHERE student_id=?
            ORDER BY ROWID DESC
        """, (user["student_id"],))
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Subject", "Marks", "Class", "Section"])
            st.dataframe(df, use_container_width=True)
            st.download_button("⬇️ Export to CSV", data=df.to_csv(index=False), file_name="my_marks.csv", mime="text/csv")
        else:
            st.info("No marks recorded yet.")

    # ---------------------------
    # 2️⃣ My Attendance
    # ---------------------------
    elif menu == "🗕️ My Attendance":
        cur.execute("""
            SELECT date, status
            FROM attendance
            WHERE student_id=?
            ORDER BY date DESC
        """, (user["student_id"],))
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Date", "Status"])
            st.dataframe(df, use_container_width=True)
            st.download_button("⬇️ Export to CSV", data=df.to_csv(index=False), file_name="my_attendance.csv", mime="text/csv")
            summary = df["Status"].value_counts()
            st.write("### Attendance Summary")
            st.write(summary)
        else:
            st.info("No attendance records yet.")

    # ---------------------------
    # 3️⃣ School Notices
    # ---------------------------
    elif menu == "📰 School Notices":
        # show only active notices for student's class/section
        cur.execute("""
            SELECT title, message, expiry_date, timestamp, class, section
            FROM notices
            WHERE (class IS NULL OR class=?)
              AND (section IS NULL OR section=?)
              AND (expiry_date IS NULL OR expiry_date >= date('now'))
            ORDER BY timestamp DESC
        """, (user.get("class"), user.get("section")))
        rows = cur.fetchall()
        if rows:
            for title, message, expiry, ts, cls, sec in rows:
                st.markdown(f"### {title}")
                st.write(message)
                meta = f"📅 Posted: {ts}"
                if expiry:
                    meta += f" • Expires: {expiry}"
                if cls:
                    meta += f" • Class: {cls}"
                if sec:
                    meta += f" • Section: {sec}"
                st.caption(meta)
                st.markdown("---")
        else:
            st.info("No active notices.")

    # ---------------------------
    # 4️⃣ My Timetable
    # ---------------------------
    elif menu == "📆 My Timetable":
        class_name = user.get("class")
        section = user.get("section")
        if not class_name or not section:
            st.warning("⚠️ Your class & section info is missing.")
        else:
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
            """, (class_name, section))
            rows = cur.fetchall()
            if rows:
                df = pd.DataFrame(rows, columns=[
                    "Day", "Period 1", "Period 2", "Period 3",
                    "Period 4", "Period 5", "Period 6", "Period 7"
                ])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No timetable assigned yet.")

    # ---------------------------
    # 5️⃣ My Fees & Payments
    # ---------------------------
    elif menu == "💰 My Fees & Payments":
        st.subheader("💵 Payment History & Pending Dues")

        cur.execute("""
            SELECT amount, date, method
            FROM payments
            WHERE student_id=?
            ORDER BY date DESC
        """, (user["student_id"],))
        payments = cur.fetchall()

        cur.execute("SELECT total_fee FROM fees WHERE class=?", (user.get("class"),))
        row = cur.fetchone()
        total_fee = row[0] if row else 0

        paid_amount = sum(p[0] for p in payments)
        pending_due = max(total_fee - paid_amount, 0)

        st.write("### Fee Summary")
        fee_summary_df = pd.DataFrame([{
            "Total Fee (₹)": f"{total_fee:,.2f}",
            "Total Paid (₹)": f"{paid_amount:,.2f}",
            "Pending Due (₹)": f"{pending_due:,.2f}"
        }])
        st.dataframe(fee_summary_df, use_container_width=True)

        if payments:
            df = pd.DataFrame(payments, columns=["Amount (₹)", "Date", "Method"])
            st.write("### Payment History")
            st.dataframe(df, use_container_width=True)
            st.download_button("⬇️ Download Receipt", data=df.to_csv(index=False), file_name="payment_receipt.csv", mime="text/csv")
        else:
            st.info("No payments recorded yet.")

    # ---------------------------
    # 6️⃣ WhatsApp Message History
    # ---------------------------
    elif menu == "📢 Message History":
        st.subheader("📢 WhatsApp Message History")
        df = pd.read_sql_query("""
            SELECT id, phone_number, message, status, response, timestamp
            FROM whatsapp_logs
            WHERE student_id=?
            ORDER BY timestamp DESC
        """, conn, params=(user["student_id"],))
        if df.empty:
            st.info("No message history available.")
        else:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False)
            st.download_button("⬇️ Export Message History", data=csv, file_name="message_history.csv", mime="text/csv")

    # ---------------------------
    # 7️⃣ Messaging tab - send to teacher (in-app + WhatsApp)
    # ---------------------------
    elif menu == "📨 Messages":
        st.subheader("📨 Message My Teacher")

        class_name = user.get("class")
        section = user.get("section")

        if not class_name or not section:
            st.warning("⚠️ Your class & section info is missing. Contact admin.")
        else:
            # Load teachers for this class & section
            cur.execute("""
                SELECT student_name, email
                FROM users
                WHERE role='Teacher' AND class=? AND section=?
            """, (class_name, section))
            teachers = cur.fetchall()

            if not teachers:
                st.info("No teacher assigned to your class yet.")
            else:
                teacher_map = {name: email for name, email in teachers}
                teacher_choice = st.selectbox("Select Teacher", list(teacher_map.keys()))

                message_text = st.text_area("Enter your message")
                if st.button("Send Message"):
                    if message_text.strip():
                        # This helper inserts into messages table and sends WhatsApp to receiver (teacher) if phone present
                        send_in_app_and_whatsapp(user["email"], teacher_map[teacher_choice], message_text.strip())
                        st.success(f"✅ Message sent to {teacher_choice} (also on WhatsApp)")
                    else:
                        st.error("Please enter a message before sending.")

            # Show conversation history (in-app only)
            st.write("### 📜 Message History")
            cur.execute("""
                SELECT sender_email, receiver_email, message, timestamp
                FROM messages
                WHERE sender_email=? OR receiver_email=?
                ORDER BY timestamp DESC
            """, (user["email"], user["email"]))
            msgs = cur.fetchall()
            if msgs:
                for sender, receiver, msg, ts in msgs:
                    who = "You" if sender == user.get("email") else sender
                    st.markdown(f"**{who}** → **{receiver}** ({ts}): {msg}")
            else:
                st.info("No conversation history found.")

    conn.close()
