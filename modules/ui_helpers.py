import streamlit as st

def render_card(title: str, subtitle: str | None = None):
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)

def end_card():
    pass