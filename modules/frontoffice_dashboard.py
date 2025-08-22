import streamlit as st

# ======================
# Config
# ======================
BG_COLOR = "#fff8e7"  # soft pastel yellow for front office
GROUPS = {
    "📝 Admissions": [
        "New Enquiries",
        "Pending Applications",
        "Confirmed Admissions"
    ],
    "💳 Fee Management": [
        "Pending Fees",
        "Collected Fees",
        "Defaulters List"
    ],
    "📅 Scheduling": [
        "Parent Appointments",
        "Visitor Appointments"
    ],
    "📦 Inventory": [
        "Stationery Stock",
        "Office Supplies",
        "Low Stock Alerts"
    ],
    "📞 Communication": [
        "Parent Queries",
        "Circulars/Notices"
    ]
}

# ======================
# Render sub-items
# ======================
def render_sub_item(group, item):
    st.markdown(f"### {item}")
    if group == "📝 Admissions":
        if item == "New Enquiries":
            st.info("12 new enquiries this week")
        elif item == "Pending Applications":
            st.warning("5 applications pending review")
        elif item == "Confirmed Admissions":
            st.success("8 new students admitted")
    elif group == "💳 Fee Management":
        if item == "Pending Fees":
            st.warning("₹1.2L pending")
        elif item == "Collected Fees":
            st.success("₹12.5L collected")
        elif item == "Defaulters List":
            st.error("3 students in defaulters list")
    elif group == "📅 Scheduling":
        if item == "Parent Appointments":
            st.info("6 appointments today")
        elif item == "Visitor Appointments":
            st.info("3 visitor appointments")
    elif group == "📦 Inventory":
        if item == "Stationery Stock":
            st.info("Stock: 250 notebooks, 120 pens")
        elif item == "Office Supplies":
            st.info("Printer ink, paper sufficient")
        elif item == "Low Stock Alerts":
            st.warning("Markers, chart papers running low")
    elif group == "📞 Communication":
        if item == "Parent Queries":
            st.info("15 new parent queries logged")
        elif item == "Circulars/Notices":
            st.info("2 new circulars sent this week")

# ======================
# Main Dashboard
# ======================
def render_front_office_dashboard(user):
    # Background + CSS
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {BG_COLOR};
        }}
        .top-bar {{
            display: flex; justify-content: space-between;
            align-items: center; padding: 10px 20px;
            background: transparent;
        }}
        .logo {{
            font-size: 28px; font-weight: bold;
        }}
        .groups-row {{
            display: flex; flex-wrap: wrap; gap: 12px; margin: 20px 0;
        }}
        .group-btn {{
            padding: 10px 18px; border-radius: 12px;
            background: #2563eb; color: white; font-weight: 600;
            cursor: pointer; text-align: center;
        }}
        .active {{
            background: #1e40af !important;
        }}
        .sub-items {{
            display: flex; flex-wrap: wrap; gap: 14px; margin-top: 12px;
        }}
        .sub-item {{
            flex: 1 1 calc(33% - 10px);
            background: white; padding: 16px; border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,.08);
            cursor: pointer;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # Top bar
    st.markdown(
        f"""
        <div class="top-bar">
            <div>Welcome, {user.get('front_office_name', user.get('email','Front Office'))}</div>
            <div class="logo">🏢 Front Office Dashboard</div>
            <form action="/logout" method="get">
                <button style="padding:6px 14px; border-radius:8px; background:#ef4444; color:white; border:none; cursor:pointer;">
                    Logout
                </button>
            </form>
        </div>
        """,
        unsafe_allow_html=True
    )

    # State init
    if "active_group" not in st.session_state:
        st.session_state.active_group = None
    if "active_item" not in st.session_state:
        st.session_state.active_item = None

    # Groups row
    st.markdown('<div class="groups-row">', unsafe_allow_html=True)
    for group in GROUPS.keys():
        active_class = "active" if st.session_state.active_group == group else ""
        if st.button(group, key=f"group_{group}"):
            st.session_state.active_group = group
            st.session_state.active_item = None
        st.markdown(f'<div class="group-btn {active_class}">{group}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Sub-items (if group selected)
    if st.session_state.active_group:
        st.subheader(st.session_state.active_group)
        st.markdown('<div class="sub-items">', unsafe_allow_html=True)
        for item in GROUPS[st.session_state.active_group]:
            if st.button(item, key=f"item_{item}"):
                st.session_state.active_item = item
            st.markdown(f'<div class="sub-item">{item}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Render selected sub-item
    if st.session_state.active_item:
        render_sub_item(st.session_state.active_group, st.session_state.active_item)
