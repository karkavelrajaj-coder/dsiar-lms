import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.db import courses_col, enrollments_col, lessons_col, modules_col, progress_col

user = require_role("student", "instructor", "admin")

st.title("🎓 My learning")

enrollments = list(enrollments_col().find({"user_id": user["id"]}))

if not enrollments:
    st.info("You haven't enrolled in any courses yet. Head to the Course Catalog to get started.")
    st.stop()

for e in enrollments:
    course = courses_col().find_one({"_id": ObjectId(e["course_id"])})
    if not course:
        continue

    module_ids = [m["_id"] for m in modules_col().find({"course_id": e["course_id"]})]
    lesson_ids = [
        l["_id"] for l in lessons_col().find({"module_id": {"$in": [str(m) for m in module_ids]}})
    ]
    total = len(lesson_ids)
    done = progress_col().count_documents(
        {"user_id": user["id"], "lesson_id": {"$in": [str(l) for l in lesson_ids]}, "completed": True}
    )
    pct = (done / total) if total else 0

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader(course["title"])
            st.progress(pct, text=f"{done}/{total} lessons completed")
        with c2:
            st.session_state["_selected_course_id"] = str(course["_id"])
            if st.button("Open course ▶", key=f"open_{course['_id']}", use_container_width=True):
                st.session_state["active_course_id"] = str(course["_id"])
                st.switch_page("views/course_player.py")
