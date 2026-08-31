import streamlit as st

from utils.auth import log_in, sign_up

st.title("🎓 D'siar Tech LMS")
st.caption("Bridging academia and industry — sign in to continue.")

tab_login, tab_signup = st.tabs(["Log in", "Sign up (students)"])

with tab_login:
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

with tab_signup:
    st.caption(
        "This creates a **student** account. Instructor and admin accounts "
        "are set up by the D'siar Tech admin team."
    )
    with st.form("signup_form"):
        name = st.text_input("Full name")
        s_email = st.text_input("Email", key="signup_email")
        s_password = st.text_input("Password", type="password", key="signup_pw")
        s_confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            if not name or not s_email or not s_password:
                st.error("Fill in all fields.")
            elif s_password != s_confirm:
                st.error("Passwords don't match.")
            elif len(s_password) < 8:
                st.error("Password must be at least 8 characters.")
            else:
                try:
                    sign_up(name, s_email, s_password, role="student")
                    st.success("Account created! Switch to the Log in tab.")
                except ValueError as e:
                    st.error(str(e))
