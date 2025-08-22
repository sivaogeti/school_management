import streamlit as st
from db import get_connection

HELPER_CSS = """
<style>
.help-button {
  position: fixed;
  bottom: 30px;
  right: 30px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 50%;
  padding: 18px;
  font-size: 22px;
  cursor: pointer;
  box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
  z-index: 9999;
}
.help-card {
  position: fixed;
  bottom: 90px;
  right: 30px;
  width: 320px;
  max-height: 400px;
  background: white;
  border-radius: 12px;
  box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
  padding: 15px;
  overflow-y: auto;
  z-index: 9999;
}
</style>
"""

def render_help_widget():
    st.markdown(HELPER_CSS, unsafe_allow_html=True)

    if "help_open" not in st.session_state:
        st.session_state.help_open = False

    # Floating button
    col1, col2, col3 = st.columns([8,1,1])
    with col3:
        if st.button("❓", key="help_btn", help="Need help?"):
            st.session_state.help_open = not st.session_state.help_open

    if st.session_state.help_open:
        st.markdown('<div class="help-card">', unsafe_allow_html=True)
        st.markdown("### 🤖 May I Help You?")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT question, answer FROM faqs ORDER BY created_at DESC")
        faqs = cur.fetchall()
        conn.close()

        if not faqs:
            st.info("No FAQs available yet.")
        else:
            for q, a in faqs:
                if st.button(q, key=q):
                    st.info(a)

        st.markdown('</div>', unsafe_allow_html=True)
