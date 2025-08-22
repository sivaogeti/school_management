# modules/ui_theme.py
import streamlit as st

# =============================
# Centralized Dark Theme CSS
# =============================
_UI_CSS = """
<style>
:root{
  --bg: #0f141a;
  --card: #1a1f27;
  --card-2: #141a21;
  --text: #e7edf3;
  --muted: #9fb0c0;
  --brand: #7c5cff;
  --brand-2:#5dd39e;
  --danger:#ff6b6b;
  --warn:#ffb020;
  --accent:#4cc9f0;
  --shadow: 0 10px 30px rgba(0,0,0,.35);
  --radius: 16px;
}
html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg);
  color: var(--text);
}
.sidebar-title{
  font-weight: 700; font-size: .9rem; letter-spacing:.04em;
  color: var(--muted); margin: 0.6rem 0 .3rem;
}
.nav-btn{
  width:100%; border:1px solid rgba(255,255,255,.06);
  background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(0,0,0,.12));
  color: var(--text);
  padding:.65rem .8rem; border-radius:12px; margin-bottom:.35rem;
  text-align:left; cursor:pointer; transition:.2s ease;
}
.nav-btn:hover{ transform: translateY(-1px); border-color: rgba(255,255,255,.12); }
.nav-btn.active{
  border-color: var(--brand); box-shadow: 0 0 0 2px rgba(124,92,255,.25) inset;
  background: linear-gradient(180deg, rgba(124,92,255,.15), rgba(0,0,0,.1));
}

.card{
  border-radius: var(--radius);
  background: linear-gradient(180deg, var(--card), var(--card-2));
  border: 1px solid rgba(255,255,255,.06);
  box-shadow: var(--shadow);
  padding: 20px 18px;
}
.card + .card{ margin-top: 14px; }
.card-title{
  font-size: 1.15rem; font-weight: 700; letter-spacing:.01em; margin-bottom:.25rem;
}
.card-subtle{ color: var(--muted); font-size:.95rem; margin-bottom: .75rem; }

.btn-row{ display:flex; gap:.5rem; flex-wrap:wrap; }
.btn{
  border-radius: 12px; padding:.6rem .9rem; border:1px solid transparent;
  cursor:pointer; font-weight:600;
  background: rgba(255,255,255,.06); color: var(--text);
}
.btn:hover{ filter: brightness(1.08); transform: translateY(-1px); }
.btn-primary{ background: linear-gradient(180deg, var(--brand), #6b4cff); }
.btn-success{ background: linear-gradient(180deg, var(--brand-2), #44c387); }
.btn-danger{ background: linear-gradient(180deg, var(--danger), #ff5252); }
.btn-ghost { background: rgba(255,255,255,.06); }

.metric-grid{ display:grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap:12px; }
.metric{ background: rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.06); padding:14px;
         border-radius:14px; text-align:center;}
.metric .label{ color: var(--muted); font-size:.85rem; margin-top:4px; }
.metric .value{ font-size:1.6rem; font-weight:700; }

.table-wrap{
  overflow:auto; border-radius:12px; border:1px solid rgba(255,255,255,.08);
}
.styled-table{
  border-collapse: collapse; width: 100%; min-width: 520px;
  background: rgba(255,255,255,.02); color: var(--text);
}
.styled-table th, .styled-table td{
  padding:10px 12px; border-bottom:1px solid rgba(255,255,255,.06); text-align:left;
}
.styled-table thead th{ background: rgba(255,255,255,.06); font-size:.9rem; }
.empty{
  color: var(--muted); padding:.6rem 0;
}
.small{ font-size:.88rem; color: var(--muted); }
.header-row{
  display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:10px;
}
.header-chip{
  font-size:.85rem; color: var(--text);
  background: rgba(76,201,240,.15); border:1px solid rgba(76,201,240,.35);
  padding:.35rem .55rem; border-radius:999px;
}

/* ✅ Unified button styling for all Streamlit buttons */
.stButton>button, .stDownloadButton>button, .stFormSubmitButton>button {
    width: 100% !important;
    padding: 0.6rem 1rem !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    background: linear-gradient(180deg, var(--brand), #6b4cff) !important;
    color: white !important;
    border: none !important;
    box-shadow: var(--shadow);
}
.stButton>button:hover, .stDownloadButton>button:hover, .stFormSubmitButton>button:hover {
    filter: brightness(1.08);
    transform: translateY(-1px);
}
/* Fix button visibility */
.stButton > button {
    background-color: #2E86C1 !important;   /* blue */
    color: white !important;
    border-radius: 8px !important;
    padding: 0.4rem 1rem !important;
    border: none !important;
    font-weight: 500 !important;
    margin-top: 0.3rem !important;
}
.stButton > button:hover {
    background-color: #1A5276 !important;   /* darker blue */
    color: white !important;
}
</style>
"""

def apply_theme():
    """Apply the global CSS theme."""
    st.markdown(_UI_CSS, unsafe_allow_html=True)

# =============================
# UI Helpers
# =============================

def render_card(title: str, subtitle: str = None):
    st.markdown(f"<div class='card'><div class='card-title'>{title}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div class='card-subtle'>{subtitle}</div>", unsafe_allow_html=True)

def end_card():
    st.markdown("</div>", unsafe_allow_html=True)

def metric_row(metrics: list):
    """metrics = [(label, value)]"""
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.markdown(
            f"<div class='metric'><div class='value'>{value}</div><div class='label'>{label}</div></div>",
            unsafe_allow_html=True
        )

def table_card(headers, rows):
    render_card("Table")
    st.table({h: [r[i] for r in rows] for i, h in enumerate(headers)})
    end_card()

def empty_state(msg="No records found."):
    st.info(msg)

def grouped_sidebar(menu_dict, default=None):
    st.sidebar.markdown("<div class='sidebar-title'>MENU</div>", unsafe_allow_html=True)
    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = default or list(menu_dict.values())[0][0][0]

    for section, items in menu_dict.items():
        st.sidebar.markdown(f"<div class='sidebar-title'>{section}</div>", unsafe_allow_html=True)
        for label, icon in items:
            btn_key = f"nav_{label}"
            if st.sidebar.button(f"{icon} {label}", key=btn_key, use_container_width=True):
                st.session_state.selected_menu = label
        st.sidebar.markdown("<div style='height:.2rem'></div>", unsafe_allow_html=True)

    return st.session_state.selected_menu




def grouped_topnav(menu_dict, default=None):
    """
    Render top navigation cards using your current _GROUPS dict structure,
    with Logout button on the top-right corner.
    """
    import streamlit as st

    # Initialize session state
    if "selected_group" not in st.session_state:
        st.session_state.selected_group = list(menu_dict.keys())[0]
    if "selected_menu" not in st.session_state:
        first_group = list(menu_dict.keys())[0]
        st.session_state.selected_menu = menu_dict[first_group][0]

    # Top row: empty space + Logout button on the right
    cols = st.columns([9, 1])  # adjust ratio: left 9 parts, right 1 part
    with cols[1]:
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    # Render top nav group buttons below logout
    group_names = list(menu_dict.keys())
    for group in group_names:
        st.markdown(f"<div style='font-weight:700; margin-top:10px'>{group}</div>", unsafe_allow_html=True)
        item_cols = st.columns(len(menu_dict[group]))
        for i, item in enumerate(menu_dict[group]):
            with item_cols[i]:
                active = (st.session_state.selected_menu == item)
                btn_class = "btn btn-primary" if active else "btn btn-ghost"
                if st.button(item, key=f"topnav_{item}", use_container_width=True):
                    st.session_state.selected_group = group
                    st.session_state.selected_menu = item

    st.markdown("<div style='margin:0.6rem 0'></div>", unsafe_allow_html=True)
    return st.session_state.selected_menu
