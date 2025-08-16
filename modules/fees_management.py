import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_connection

def render_fees_management(user):
    """
    Fee management for Teachers:
    - Record student fee payments
    - View history
    - Generate simple receipts
    """
    st.title("💰 Fee Management")

    conn = get_connection()
    cur = conn.cursor()

    # Ensure required tables exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class TEXT,
            total_fee REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            amount REAL,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            method TEXT
        )
    """)
    conn.commit()

    # -------------------------
    # Sidebar Navigation
    # -------------------------
    menu = st.radio(
        "Fee Management Options",
        ["Record Payment", "View Payments & Receipts"],
        horizontal=True,
        key="fees_menu"
    )

    # -------------------------
    # 1️⃣ Record Fee Payment
    # -------------------------
    if menu == "Record Payment":
        st.subheader("📝 Record New Fee Payment")

        # Fetch students list
        cur.execute("""
            SELECT student_id, student_name, class, section
            FROM users
            WHERE role='Student'
            ORDER BY class, section, student_name
        """)
        students = cur.fetchall()
        if not students:
            st.warning("⚠️ No students found.")
            conn.close()
            return

        student_map = {f"{s[1]} ({s[0]}) [Class {s[2]}-{s[3]}]": s[0] for s in students}
        selected_student = st.selectbox("Select Student", list(student_map.keys()), key="fees_student")
        student_id = student_map[selected_student]

        # Get fee structure
        cur.execute("SELECT class, section FROM users WHERE student_id=?", (student_id,))
        row = cur.fetchone()
        student_class = row[0] if row else None

        total_fee = None
        if student_class:
            cur.execute("SELECT total_fee FROM fees WHERE class=?", (student_class,))
            fee_row = cur.fetchone()
            if fee_row:
                total_fee = fee_row[0]
                st.info(f"💡 Total Fee for Class {student_class}: ₹{total_fee:,.2f}")
            else:
                st.warning(f"⚠️ No fee structure defined for Class {student_class}")

        amount = st.number_input("Payment Amount (₹)", min_value=0.0, step=100.0, key="fees_amount")
        method = st.selectbox("Payment Method", ["Cash", "UPI", "Bank Transfer", "Other"], key="fees_method")

        if st.button("✅ Record Payment", key="fees_record_btn"):
            if amount <= 0:
                st.error("❌ Enter a valid amount")
            else:
                cur.execute("""
                    INSERT INTO payments(student_id, amount, method)
                    VALUES (?, ?, ?)
                """, (student_id, amount, method))
                conn.commit()
                st.success(f"✅ Payment of ₹{amount:,.2f} recorded for {selected_student}")

                # Generate receipt preview
                st.write("---")
                st.subheader("🧾 Receipt Preview")
                receipt = {
                    "Student": selected_student,
                    "Amount Paid": f"₹{amount:,.2f}",
                    "Method": method,
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Recorded By": user["email"]
                }
                st.json(receipt)
                st.write("*(Use this as a digital receipt or print if needed)*")

    # -------------------------
    # 2️⃣ View Payments & Receipts
    # -------------------------
    elif menu == "View Payments & Receipts":
        st.subheader("📋 All Recorded Payments")

        cur.execute("""
            SELECT student_id, amount, date, method
            FROM payments
            ORDER BY date DESC
        """)
        rows = cur.fetchall()

        if rows:
            df = pd.DataFrame(rows, columns=["Student ID", "Amount (₹)", "Date", "Method"])
            st.dataframe(df, use_container_width=True)

            total = df["Amount (₹)"].sum()
            st.success(f"💰 **Total Collected:** ₹{total:,.2f}")

            # Download CSV for record
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇ Download Payment Report (CSV)",
                data=csv,
                file_name="payments_report.csv",
                mime="text/csv"
            )
        else:
            st.info("No payments recorded yet.")

    conn.close()
