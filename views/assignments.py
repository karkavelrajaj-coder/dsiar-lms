from datetime import datetime, timezone

import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.db import assignments_col, courses_col, enrollments_col, submissions_col

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
    existing = submissions_col().find_one({"assignment_id": str(a["_id"]), "user_id": user["id"]})

    with st.container(border=True):
        st.subheader(a["title"])
        st.caption(f"Course: {course['title'] if course else 'Unknown'} · Due: {a.get('due_date', 'No deadline')}")
        st.write(a.get("description", ""))

        if existing:
            st.success("Submitted")
            st.write(f"Your submission: {existing['link_or_text']}")
            if existing.get("grade") is not None:
                st.info(f"Grade: {existing['grade']}  \nFeedback: {existing.get('feedback', '')}")
            else:
                st.caption("Awaiting grading.")
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
                            }
                        )
                        st.rerun()
