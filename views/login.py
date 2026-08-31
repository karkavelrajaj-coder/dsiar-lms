import streamlit as st

from utils.auth import log_in

st.title("🎓 D'siar Tech LMS")
st.caption("Bridging academia and industry — sign in to continue.")

st.info(
    "Accounts are created by the D'siar Tech team once enrollment is confirmed. "
    "If you've paid for a course but don't have login details yet, contact us."
)

with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Log in", use_container_width=True)
    if submitted:
        if not email or not password:
            st.error("Enter both email and password.")
        else:
            try:
                log_in(email, password)
                st.rerun()
            except ValueError as e:
                st.error(str(e))
