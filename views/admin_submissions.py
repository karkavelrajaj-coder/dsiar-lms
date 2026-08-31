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
st.markdown("##### All assignments")

assignments = list(assignments_col().find({"course_id": {"$in": list(course_map.values())}}))
course_id_to_name = {v: k for k, v in course_map.items()}

if not assignments:
    st.info("No assignments posted yet.")

for a in assignments:
    aid = str(a["_id"])
    with st.container(border=True):
        head_col1, head_col2, head_col3 = st.columns([4, 1, 1])
        with head_col1:
            st.markdown(f"**{a['title']}**")
            st.caption(
                f"Course: {course_id_to_name.get(a['course_id'], 'Unknown')} · "
                f"Due: {a.get('due_date') or 'No deadline'}"
            )
        with head_col2:
            if st.button("✏️ Edit", key=f"editassign_btn_{aid}"):
                st.session_state[f"editing_assign_{aid}"] = not st.session_state.get(f"editing_assign_{aid}", False)
                st.rerun()
        with head_col3:
            if st.button("🗑 Delete", key=f"delassign_{aid}"):
                submissions_col().delete_many({"assignment_id": aid})
                assignments_col().delete_one({"_id": a["_id"]})
                st.rerun()

        if st.session_state.get(f"editing_assign_{aid}", False):
            with st.form(f"edit_assign_form_{aid}"):
                e_title = st.text_input("Assignment title", value=a["title"], key=f"eat_{aid}")
                e_desc = st.text_area(
                    "Description / instructions", value=a.get("description", ""), key=f"ead_{aid}"
                )
                due_val = a.get("due_date") or ""
                e_due = st.text_input(
                    "Due date (YYYY-MM-DD)", value=due_val, key=f"eadue_{aid}"
                )
                save_col, cancel_col = st.columns(2)
                with save_col:
                    if st.form_submit_button("Save assignment", use_container_width=True):
                        assignments_col().update_one(
                            {"_id": a["_id"]},
                            {"$set": {"title": e_title, "description": e_desc, "due_date": e_due}},
                        )
                        st.session_state[f"editing_assign_{aid}"] = False
                        st.success("Saved.")
                        st.rerun()
                with cancel_col:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state[f"editing_assign_{aid}"] = False
                        st.rerun()
        else:
            st.write(a.get("description", ""))

        subs = list(submissions_col().find({"assignment_id": aid}))
        if not subs:
            st.caption("No submissions yet.")
        else:
            st.markdown("###### Submissions to grade")
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
