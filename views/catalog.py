from datetime import datetime, timezone

import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.db import courses_col, enrollments_col

user = require_role("student", "instructor", "admin")

st.title("📚 Course catalog")
st.caption("Practical, hands-on courses in AI, ML, cybersecurity, and emerging technologies.")

courses = list(courses_col().find().sort("order", 1))
my_enrollments = {
    e["course_id"] for e in enrollments_col().find({"user_id": user["id"]})
}

if not courses:
    st.info("No courses published yet — check back soon.")

cols = st.columns(3)
for i, course in enumerate(courses):
    cid = str(course["_id"])
    with cols[i % 3]:
        with st.container(border=True):
            if course.get("thumbnail_url"):
                try:
                    st.image(course["thumbnail_url"], use_container_width=True)
                except Exception:
                    st.caption("⚠️ Thumbnail couldn't be loaded — check the URL in Manage Courses.")
            st.subheader(course["title"])
            st.caption(course.get("category", ""))
            st.write(course.get("description", ""))

            if cid in my_enrollments:
                st.success("Enrolled")
            elif user["role"] == "student":
                st.caption("🔒 Not enrolled — contact D'siar Tech to purchase access.")
            else:
                # Admins/instructors can self-enroll to preview course content.
                if st.button("Enroll (preview)", key=f"enroll_{cid}", use_container_width=True):
                    enrollments_col().insert_one(
                        {
                            "user_id": user["id"],
                            "course_id": cid,
                            "enrolled_at": datetime.now(timezone.utc),
                        }
                    )
                    st.rerun()
