import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.db import assignments_col, courses_col, submissions_col, users_col

user = require_role("admin", "instructor")

st.title("📥 Assignments & grading")

if user["role"] == "admin":
    courses = list(courses_col().find())
else:
    courses = list(courses_col().find({"instructor_id": user["id"]}))

course_map = {c["title"]: str(c["_id"]) for c in courses}

if not course_map:
    st.info("No courses available yet.")
    st.stop()

with st.expander("➕ Post a new assignment"):
    with st.form("new_assignment"):
        course_name = st.selectbox("Course", list(course_map.keys()))
        title = st.text_input("Assignment title")
        description = st.text_area("Description / instructions")
        due_date = st.date_input("Due date")
        if st.form_submit_button("Post assignment"):
            if not title:
                st.error("Title is required.")
            else:
                assignments_col().insert_one(
                    {
                        "course_id": course_map[course_name],
                        "title": title,
                        "description": description,
                        "due_date": str(due_date),
                    }
                )
                st.success("Assignment posted.")
                st.rerun()

st.divider()
st.markdown("##### Submissions to grade")

assignments = list(assignments_col().find({"course_id": {"$in": list(course_map.values())}}))

for a in assignments:
    subs = list(submissions_col().find({"assignment_id": str(a["_id"])}))
    if not subs:
        continue
    st.markdown(f"**{a['title']}**")
    for s in subs:
        student = users_col().find_one({"_id": ObjectId(s["user_id"])})
        with st.container(border=True):
            st.write(f"Student: {student['name'] if student else 'Unknown'}")
            st.write(f"Submission: {s['link_or_text']}")
            with st.form(f"grade_{s['_id']}"):
                grade = st.number_input(
                    "Grade (0-100)", min_value=0, max_value=100,
                    value=int(s["grade"]) if s.get("grade") is not None else 0,
                    key=f"g_{s['_id']}",
                )
                feedback = st.text_area("Feedback", value=s.get("feedback", ""), key=f"f_{s['_id']}")
                if st.form_submit_button("Save grade"):
                    submissions_col().update_one(
                        {"_id": s["_id"]}, {"$set": {"grade": grade, "feedback": feedback}}
                    )
                    st.success("Grade saved.")
                    st.rerun()
