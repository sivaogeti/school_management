# modules/chairman_dashboard.py

import os
import streamlit as st
import pandas as pd
import base64
from modules.help_widget import render_help_widget

def render_chairman_dashboard(user):
    # ---------------- CSS ----------------
    import streamlit as st, base64

    st.markdown("""
    <style>
    /* background */
    html, body, [data-testid="stAppViewContainer"], .main, .block-container {
        background: #e6f4ea !important;
    }

    /* top bar row */
    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 16px;   /* keeps items aligned, but no big box */
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }


    /* left welcome */
    .dashboard-welcome {
        font-weight: 600;
        font-size: 18px;
        color: #165B33;
        flex: 1;
        text-align: left;
    }

    /* center logo */
    .dashboard-logo {
        flex: 1;
        text-align: center;
    }
    .dashboard-logo img {
        height: 120px;   /* adjust logo size */
    }

    /* right logout */
    .dashboard-logout {
        flex: 1;
        text-align: right;
    }
    .logout-btn {
        background: #ef4444;
        color: white;
        border: none;
        padding: 6px 14px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)


    # ================= Top Bar =================
    user = st.session_state.get("user", {"student_name": "Chairman", "email": "chairman@school.com"})

    # try to load logo
    try:
        logo_b64 = base64.b64encode(open("dps_banner.png", "rb").read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_b64}'/>"
    except:
        logo_html = "<h3>🏛️</h3>"

    # build entire top row in one go
    st.markdown(
        f"""
        <div class='top-bar'>
            <div class='dashboard-welcome'>Welcome, {user.get('student_name') or user.get('email')}</div>
            <div class='dashboard-logo'>{logo_html}</div>
            <div class='dashboard-logout'>
                <form action='/logout' method='get'>
                    <button class='logout-btn'>Logout</button>
                </form>
            </div>
        </div>
        """, unsafe_allow_html=True
    )

    
    # ---------------- Data Structures ----------------
    GROUPS = {
        "📊 Academic Overview": ["📈 Student Performance", "📉 Class Performance", "🏫 Teacher Reports"],
        "👥 Staff Management": ["🧑‍🏫 Teacher Directory", "🗓️ Staff Attendance"],
        "💰 Finance": ["💰 Fees Overview", "📊 Expenditure Reports"],
        "📢 Communication": ["📰 Notices", "💬 Feedback"],
    }

    ITEM_ICONS = {
        "📈 Student Performance": "📈", "📉 Class Performance": "📉", "🏫 Teacher Reports": "🏫",
        "🧑‍🏫 Teacher Directory": "🧑‍🏫", "🗓️ Staff Attendance": "🗓️",
        "💰 Fees Overview": "💰", "📊 Expenditure Reports": "📊",
        "📰 Notices": "📰", "💬 Feedback": "💬"
    }

    GROUP_COLORS = {
        "📊 Academic Overview": "#3b82f6",
        "👥 Staff Management": "#f97316",
        "💰 Finance": "#10b981",
        "📢 Communication": "#8b5cf6"
    }

    # ---------------- Session State ----------------
    if "group" not in st.session_state:
        st.session_state.group = None
    if "item" not in st.session_state:
        st.session_state.item = None

    # ---------------- Top Groups Navigation ----------------
    top_cols = st.columns(len(GROUPS))
    for i, (g, items) in enumerate(GROUPS.items()):
        active = st.session_state.group == g
        with top_cols[i]:
            if st.button(g, key=f"group_{g}"):
                st.session_state.group = g
                st.session_state.item = None

    # ---------------- Sub-items Navigation ----------------
    if st.session_state.group:
        sub_items = GROUPS[st.session_state.group]
        sub_cols = st.columns(len(sub_items))
        for i, item in enumerate(sub_items):
            col = sub_cols[i]
            active = st.session_state.item == item
            icon = ITEM_ICONS.get(item, "❓")

            if col.button(f"{icon} {item}", key=f"sub_{item}"):
                st.session_state.item = item

    # ---------------- Dashboard Content ----------------
    if st.session_state.item:
        item = st.session_state.item
        if item == "📈 Student Performance":
            st.subheader("📈 Student Performance Overview")
            st.info("Charts and metrics about student performance will be displayed here.")
        elif item == "📉 Class Performance":
            st.subheader("📉 Class Performance")
            st.info("Aggregate class performance reports.")
        elif item == "🏫 Teacher Reports":
            st.subheader("🏫 Teacher Reports")
            st.info("Teacher-related academic reports.")
        elif item == "🧑‍🏫 Teacher Directory":
            st.subheader("🧑‍🏫 Teacher Directory")
            st.info("List of all teachers with details.")
        elif item == "🗓️ Staff Attendance":
            st.subheader("🗓️ Staff Attendance")
            st.info("Attendance data of staff.")
        elif item == "💰 Fees Overview":
            st.subheader("💰 Fees Overview")
            st.info("Summary of fee collection and dues.")
        elif item == "📊 Expenditure Reports":
            st.subheader("📊 Expenditure Reports")
            st.info("School expenditure reports.")
        elif item == "📰 Notices":
            st.subheader("📰 Notices")
            st.info("School-wide notices for all stakeholders.")
        elif item == "💬 Feedback":
            st.subheader("💬 Feedback")
            st.info("Feedback received from students, parents, and staff.")

        render_help_widget()
