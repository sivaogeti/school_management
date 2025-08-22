import streamlit as st
import pandas as pd
import plotly.express as px
from modules.teacher_dashboard import metric_row


def render_md_dashboard(user=None):
    st.title("📱 Managing Director Dashboard")
    st.caption("Demo Mode – layout preview with dummy data")

    # ======================
    # 1. Top KPI Cards
    # ======================
    metric_row([
        ("🎓 Students", "1200"),
        ("👩‍🏫 Staff", "85"),
        ("💰 Tuition Fee Collected", "₹450,000"),
        ("📉 Attendance", "92%"),
        ("🍴 Cafeteria Fee", "₹80,000"),
        ("🏷️ Expenditure", "₹3,20,000"),
    ])

    st.markdown("---")

    # ======================
    # 2. Finance Graphs
    # ======================
    st.subheader("💰 Finance Overview")

    df_fin = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
        "Fee Collection": [400000, 420000, 450000, 470000, 480000],
        "Expenditure": [350000, 360000, 400000, 420000, 430000],
    })
    fig_line = px.line(df_fin, x="Month", y=["Fee Collection", "Expenditure"], markers=True)
    st.plotly_chart(fig_line, use_container_width=True)

    exp_dist = pd.DataFrame({
        "Category": ["Salaries", "Cafeteria", "Transport", "Utilities", "Academic Materials"],
        "Amount": [200000, 50000, 30000, 25000, 15000]
    })
    fig_pie = px.pie(exp_dist, names="Category", values="Amount", title="Expenditure Distribution")
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # ======================
    # 3. Student Section
    # ======================
    st.subheader("🎓 Student Overview")

    df_admissions = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
        "Admissions": [50, 60, 55, 70, 65],
        "Withdrawals": [5, 7, 6, 4, 8]
    })
    fig_bar = px.bar(df_admissions, x="Month", y=["Admissions", "Withdrawals"], barmode="group")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # ======================
    # 4. HR Section
    # ======================
    st.subheader("👩‍🏫 HR Overview")

    df_hr = pd.DataFrame({
        "Day": list(range(1, 31)),
        "Attendance %": [90 + (i % 5) for i in range(30)]
    })
    fig_hr = px.line(df_hr, x="Day", y="Attendance %", title="Teacher Attendance Trend (Last 30 Days)")
    st.plotly_chart(fig_hr, use_container_width=True)

    st.markdown("---")

    # ======================
    # 5. Quick Actions
    # ======================
    st.subheader("⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.button("📊 Reports")
    with col2: st.button("✅ Approvals")
    with col3: st.button("📢 Notices")
    with col4: st.button("📦 Stock")
