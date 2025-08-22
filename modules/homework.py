# modules/homework.py
import streamlit as st
from db import get_connection

def homework_view(user):
    conn = get_connection()
    cur = conn.cursor()
    if user.get("role") in ("Teacher","Admin"):
        st.subheader("Assign Homework")
        cls = st.text_input("Class")
        sec = st.text_input("Section")
        subject = st.text_input("Subject")
        desc = st.text_area("Description")
        due = st.date_input("Due date")
        if st.button("Assign"):
            cur.execute("INSERT INTO homework (class, section, subject, description, due_date, assigned_by) VALUES (?, ?, ?, ?, ?, ?)",
                        (cls, sec, subject, desc, due.isoformat(), user.get("email")))
            conn.commit()
            st.success("Homework assigned.")
    st.subheader("Homework for you")
    if user.get("class"):
        cur.execute("SELECT subject, description, due_date, assigned_by FROM homework WHERE class=? AND section=? ORDER BY timestamp DESC",
                    (user.get("class"), user.get("section")))
        for subj, desc, due, by in cur.fetchall():
            st.markdown(f"**{subj}** — due {due} (by {by})")
            st.write(desc)
    conn.close()
