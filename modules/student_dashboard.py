import streamlit as st
import pandas as pd
import requests
import webbrowser
from db import get_connection

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
        "💰 My Fees & Payments"
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
        cur.execute("SELECT message, timestamp FROM notices ORDER BY timestamp DESC")
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Notice", "Published On"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No notices published yet.")

    # ---------------------------
    # 4️⃣ My Timetable
    # ---------------------------
    elif menu == "📆 My Timetable":
        if not user.get("class") or not user.get("section"):
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
            """, (user["class"], user["section"]))
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

        # 1. Show payment history
        cur.execute("""
            SELECT amount, date, method
            FROM payments
            WHERE student_id=?
            ORDER BY date DESC
        """, (user["student_id"],))
        payments = cur.fetchall()

        # 2. Fetch fee structure for this class
        cur.execute("SELECT total_fee FROM fees WHERE class=?", (user["class"],))
        row = cur.fetchone()
        total_fee = row[0] if row else 0

        paid_amount = sum(p[0] for p in payments)
        pending_due = max(total_fee - paid_amount, 0)

        # Show fee summary in table
        st.write("### Fee Summary")
        fee_summary_df = pd.DataFrame([{
            "Total Fee (₹)": f"{total_fee:,.2f}",
            "Total Paid (₹)": f"{paid_amount:,.2f}",
            "Pending Due (₹)": f"{pending_due:,.2f}"
        }])
        st.dataframe(fee_summary_df, use_container_width=True)

        # Payment History Table
        if payments:
            df = pd.DataFrame(payments, columns=["Amount (₹)", "Date", "Method"])
            st.write("### Payment History")
            st.dataframe(df, use_container_width=True)
            st.download_button("⬇️ Download Receipt", data=df.to_csv(index=False), file_name="payment_receipt.csv", mime="text/csv")
        else:
            st.info("No payments recorded yet.")

        # Razorpay Integration – Pay Now button only if due > 0
        # if pending_due > 0:
            # st.markdown("---")
            # st.subheader("💳 Pay Pending Fee Now")
            # if st.button("Pay Now via Razorpay"):
                # with st.spinner("Creating payment order..."):
                    # try:
                        # response = requests.post("http://localhost:5001/create-order", json={
                            # "amount": pending_due,
                            # "student_id": user["student_id"]
                        # })
                        # response.raise_for_status()
                        # data = response.json()
                        # payment_url = f"https://api.razorpay.com/v1/checkout/embedded?order_id={data['order_id']}&key_id={data['key']}"
                        # st.success("Redirecting to Razorpay payment page...")
                        # webbrowser.open_new_tab(payment_url)

                        # # Simulate WhatsApp Notification
                        # st.toast(f"WhatsApp alert sent to parent for ₹{pending_due:,.2f} payment.")
                    # except Exception as e:
                        # st.error(f"Payment initiation failed: {e}")

    conn.close()
