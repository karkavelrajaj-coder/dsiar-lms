from datetime import datetime, timezone

import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.certificates import course_lessons_complete
from utils.db import (
    assignments_col,
    courses_col,
    enrollments_col,
    lessons_col,
    modules_col,
    progress_col,
    submissions_col,
)

user = require_role("student", "instructor", "admin")

st.title("📝 Assignments")

enrolled_course_ids = [e["course_id"] for e in enrollments_col().find({"user_id": user["id"]})]

if not enrolled_course_ids:
    st.info("Enroll in a course to see its assignments here.")
    st.stop()

assignments = list(assignments_col().find({"course_id": {"$in": enrolled_course_ids}}))

if not assignments:
    st.info("No assignments posted yet.")

for a in assignments:
    course = courses_col().find_one({"_id": ObjectId(a["course_id"])})
    course_title = course["title"] if course else "Unknown"

    # Assignments only unlock for students once every lesson in the course is
    # watched. Admins/instructors always see it, so they can preview/manage.
    lessons_done = course_lessons_complete(user["id"], a["course_id"])
    if user["role"] == "student" and not lessons_done:
        module_ids = [str(m["_id"]) for m in modules_col().find({"course_id": a["course_id"]})]
        lesson_ids = [str(l["_id"]) for l in lessons_col().find({"module_id": {"$in": module_ids}})]
        done_count = progress_col().count_documents(
            {"user_id": user["id"], "lesson_id": {"$in": lesson_ids}, "completed": True}
        )
        with st.container(border=True):
            st.subheader(a["title"])
            st.caption(f"Course: {course_title}")
            st.warning(
                f"🔒 Locked — finish all the lessons in **{course_title}** to unlock this assignment "
                f"({done_count}/{len(lesson_ids)} lessons completed)."
            )
        continue

    existing = submissions_col().find_one({"assignment_id": str(a["_id"]), "user_id": user["id"]})

    with st.container(border=True):
        st.subheader(a["title"])
        st.caption(f"Course: {course_title} · Due: {a.get('due_date', 'No deadline')}")
        st.write(a.get("description", ""))

        if existing:
            st.success("Submitted")
            st.write(f"Your submission: {existing['link_or_text']}")
            status = existing.get("status", "pending")
            if status == "approved":
                st.success(f"✅ Approved — Grade: {existing.get('grade', '—')}  \nFeedback: {existing.get('feedback', '')}")
            elif status == "rejected":
                st.error(f"❌ Needs revision — Grade: {existing.get('grade', '—')}  \nFeedback: {existing.get('feedback', '')}")
            else:
                st.caption("⏳ Submitted — moved to evaluation. Awaiting grading.")
        else:
            with st.form(f"submit_{a['_id']}"):
                submission = st.text_area("Paste your project link (GitHub/Colab/Drive) or answer")
                if st.form_submit_button("Submit assignment"):
                    if not submission.strip():
                        st.error("Add a link or answer before submitting.")
                    else:
                        submissions_col().insert_one(
                            {
                                "assignment_id": str(a["_id"]),
                                "user_id": user["id"],
                                "link_or_text": submission.strip(),
                                "submitted_at": datetime.now(timezone.utc),
                                "grade": None,
                                "feedback": "",
                                "status": "pending",
                            }
                        )
                        st.rerun()
