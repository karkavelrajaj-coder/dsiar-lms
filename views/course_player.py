from datetime import datetime, timezone

import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.certificates import ensure_certificate
from utils.db import courses_col, enrollments_col, lessons_col, modules_col, progress_col

user = require_role("student", "instructor", "admin")

course_id = st.session_state.get("active_course_id")
if not course_id:
    st.info("Open a course from **My Learning** or the **Course Catalog** first.")
    st.stop()

course = courses_col().find_one({"_id": ObjectId(course_id)})
if not course:
    st.error("Course not found.")
    st.stop()

is_enrolled = enrollments_col().find_one({"user_id": user["id"], "course_id": course_id})
if not is_enrolled and user["role"] == "student":
    st.warning("Enroll in this course from the Course Catalog to access the content.")
    st.stop()

st.title(f"▶ {course['title']}")

modules = list(modules_col().find({"course_id": course_id}).sort("order", 1))

for module in modules:
    with st.expander(module["title"], expanded=True):
        lessons = list(lessons_col().find({"module_id": str(module["_id"])}).sort("order", 1))
        for lesson in lessons:
            lid = str(lesson["_id"])
            already_done = bool(
                progress_col().find_one({"user_id": user["id"], "lesson_id": lid, "completed": True})
            )
            title = lesson["title"] + (" ✅" if already_done else "")
            st.markdown(f"#### {title}")

            if lesson.get("youtube_id"):
                st.video(f"https://www.youtube.com/watch?v={lesson['youtube_id']}")

            tabs = st.tabs(["📊 Slides", "💻 Colab", "📁 Dataset"])
            with tabs[0]:
                if lesson.get("ppt_link"):
                    st.link_button("Open slides", lesson["ppt_link"])
                else:
                    st.caption("No slides for this lesson.")
            with tabs[1]:
                if lesson.get("colab_link"):
                    st.link_button("Open Colab notebook", lesson["colab_link"])
                else:
                    st.caption("No notebook for this lesson.")
            with tabs[2]:
                if lesson.get("dataset_link"):
                    st.link_button("Download dataset", lesson["dataset_link"])
                else:
                    st.caption("No dataset for this lesson.")

            if not already_done:
                if st.button("Mark as complete", key=f"complete_{lid}"):
                    progress_col().update_one(
                        {"user_id": user["id"], "lesson_id": lid},
                        {
                            "$set": {
                                "user_id": user["id"],
                                "lesson_id": lid,
                                "completed": True,
                                "completed_at": datetime.now(timezone.utc),
                            }
                        },
                        upsert=True,
                    )
                    cert = ensure_certificate(user["id"], course_id)
                    if cert:
                        st.balloons()
                        st.success("🎓 Course complete and assignment approved — your certificate is ready! Check My Learning.")
                    st.rerun()
            st.divider()
