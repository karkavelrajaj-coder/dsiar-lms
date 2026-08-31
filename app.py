import streamlit as st

from utils.auth import current_user, init_session, log_out
from utils.db import ensure_indexes

st.set_page_config(page_title="D'siar Tech LMS", page_icon="🎓", layout="wide")

init_session()
ensure_indexes()

user = current_user()

if not user:
    pg = st.navigation([st.Page("views/login.py", title="Log in", icon="🔑")])
    pg.run()
    st.stop()

# --- Sidebar: identity + logout ---------------------------------------------
with st.sidebar:
    st.markdown(f"**{user['name']}**")
    st.caption(f"{user['email']} · {user['role'].title()}")
    if st.button("Log out", use_container_width=True):
        log_out()

# --- Build the page list for this role --------------------------------------
student_pages = [
    st.Page("views/catalog.py", title="Course Catalog", icon="📚", default=(user["role"] == "student")),
    st.Page("views/my_learning.py", title="My Learning", icon="🎓"),
    st.Page("views/course_player.py", title="Course Player", icon="▶️"),
    st.Page("views/assignments.py", title="Assignments", icon="📝"),
]

instructor_pages = [
    st.Page("views/admin_courses.py", title="Manage Courses", icon="🛠️", default=(user["role"] == "instructor")),
    st.Page("views/admin_submissions.py", title="Assignments & Grading", icon="📥"),
]

admin_only_pages = [
    st.Page("views/admin_users.py", title="Manage Users", icon="👥", default=(user["role"] == "admin")),
]

if user["role"] == "student":
    pages = student_pages
elif user["role"] == "instructor":
    pages = instructor_pages + student_pages  # instructors can also preview as a learner
else:  # admin
    pages = admin_only_pages + instructor_pages + student_pages

pg = st.navigation(pages)
pg.run()
