# modules/ui_theme.py
import streamlit as st

# =============================
# Centralized Dark Theme CSS
# =============================
import streamlit as st

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
         border-radius:14px;}
.metric .label{ color: var(--muted); font-size:.85rem; }
.metric .value{ font-size:1.6rem; font-weight:700; margin-top: 6px; }

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
</style>
"""

def apply_theme():
    st.markdown(_UI_CSS, unsafe_allow_html=True)



def apply_theme():
    """Apply the global CSS theme."""
    st.markdown(_UI_CSS, unsafe_allow_html=True)


# =============================
# UI Helpers
# =============================

def render_card(title: str, subtitle: str = None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<p>{subtitle}</p>", unsafe_allow_html=True)

def end_card():
    st.markdown("</div>", unsafe_allow_html=True)

def metric_row(metrics: list):
    """metrics = [(label, value)]"""
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.markdown(
            f"<div class='metric'><h4>{value}</h4><p>{label}</p></div>",
            unsafe_allow_html=True
        )

def table_card(headers, rows):
    render_card("Table")
    st.table({h: [r[i] for r in rows] for i, h in enumerate(headers)})
    end_card()

def empty_state(msg="No records found."):
    st.info(msg)


def grouped_sidebar(menu_dict):
    st.sidebar.markdown("### 📑 MENU")

    selection = None
    for section, items in menu_dict.items():
        st.sidebar.markdown(f"**{section}**")
        for label, icon in items:
            if st.sidebar.button(f"{icon} {label}"):
                selection = label
        st.sidebar.markdown("---")
    return selection