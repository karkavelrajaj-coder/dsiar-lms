import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.db import courses_col, enrollments_col, live_sessions_col
from utils.live_sessions import can_student_join, render_room, session_status

user = require_role("student", "instructor", "admin")

st.title("🎥 Live sessions")

enrolled_course_ids = [e["course_id"] for e in enrollments_col().find({"user_id": user["id"]})]

if not enrolled_course_ids:
    st.info("Enroll in a course to see its live sessions here.")
    st.stop()

sessions = list(
    live_sessions_col().find({"course_id": {"$in": enrolled_course_ids}}).sort("scheduled_at", -1)
)

if not sessions:
    st.info("No live sessions scheduled yet for your courses.")
    st.stop()

status_badge = {"upcoming": "🔵 Upcoming", "live": "🔴 Live now", "ended": "⚪ Ended"}

for s in sessions:
    sid = str(s["_id"])
    course = courses_col().find_one({"_id": ObjectId(s["course_id"])})
    status = session_status(s["scheduled_at"], s["duration_minutes"])

    with st.container(border=True):
        st.markdown(f"**{s['title']}**  ·  {status_badge[status]}")
        st.caption(
            f"Course: {course['title'] if course else 'Unknown'} · "
            f"Host: {s.get('host_name', 'Unknown')} · "
            f"{s['scheduled_at'].strftime('%b %d, %Y at %I:%M %p UTC')} · "
            f"{s['duration_minutes']} min"
        )
        if s.get("description"):
            st.write(s["description"])

        joined_key = f"joined_{sid}"
        can_join, reason = can_student_join(s)

        if not st.session_state.get(joined_key, False):
            if can_join:
                if st.button("🔴 Join session", key=f"join_{sid}", use_container_width=True):
                    st.session_state[joined_key] = True
                    st.rerun()
            else:
                st.caption(reason)
        else:
            render_room(s["room_name"], user["name"])
            if st.button("Leave session", key=f"leave_{sid}"):
                st.session_state[joined_key] = False
                st.rerun()
