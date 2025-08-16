# modules/achievements.py (stub)
import streamlit as st
from db import get_connection

def achievements_view(user):
    conn = get_connection()
    cur = conn.cursor()
    if user.get("role") == "Teacher" or user.get("role") == "Admin":
        st.subheader("Award Achievement")
        student_id = st.text_input("Student ID")
        title = st.text_input("Title")
        desc = st.text_area("Description")
        if st.button("Add Achievement"):
            cur.execute("INSERT INTO achievements (student_id, title, description, date, issued_by) VALUES (?, ?, ?, ?, ?)",
                        (student_id, title, desc, datetime.now().strftime("%Y-%m-%d"), user.get("email")))
            conn.commit()
            st.success("Added.")
    st.subheader("Recent Achievements")
    cur.execute("SELECT student_id, title, description, date, issued_by FROM achievements ORDER BY date DESC")
    rows = cur.fetchall()
    for sid, title, desc, date, by in rows:
        st.markdown(f"**{title}** — {sid} ({date})")
        st.write(desc)
    conn.close()
