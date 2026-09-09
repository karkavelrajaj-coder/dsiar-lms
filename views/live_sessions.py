import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.db import courses_col, enrollments_col, live_sessions_col
from utils.digital_samba_video import generate_join_link
from utils.live_sessions import can_student_join, render_room, session_status
from utils.timezones import (
    DEFAULT_TIMEZONE,
    format_in_tz,
    get_user_timezone,
    set_user_timezone,
    timezone_options,
    tz_display_label,
)

user = require_role("student", "instructor", "admin")

st.title("🎥 Live sessions")

# --- This viewer's own display timezone, saved so it's remembered next visit -
tz_opts = timezone_options()
saved_view_tz = get_user_timezone(user["id"])
if saved_view_tz not in tz_opts:
    tz_opts = [saved_view_tz] + tz_opts

view_tz = st.selectbox(
    "🌐 View times in",
    tz_opts,
    index=tz_opts.index(saved_view_tz),
    format_func=lambda z: tz_display_label(z),
    key="student_view_tz",
)
if view_tz != saved_view_tz:
    set_user_timezone(user["id"], view_tz)
    st.rerun()

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
    original_tz = s.get("scheduled_tz", DEFAULT_TIMEZONE)

    with st.container(border=True):
        st.markdown(f"**{s['title']}**  ·  {status_badge[status]}")
        time_line = format_in_tz(s["scheduled_at"], view_tz)
        if view_tz != original_tz:
            time_line += f"  (scheduled in {tz_display_label(original_tz)})"
        st.caption(
            f"Course: {course['title'] if course else 'Unknown'} · "
            f"Host: {s.get('host_name', 'Unknown')} · "
            f"{time_line} · "
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
            if not s.get("room_id"):
                st.error("This session needs to be restarted by the host before it can be joined (bug fix in progress).")
            else:
                try:
                    join_link = generate_join_link(s["room_id"], user["name"], role="student")
                    render_room(join_link)
                except Exception as e:
                    st.error(f"Couldn't join right now: {e}")
            if st.button("Leave session", key=f"leave_{sid}"):
                st.session_state[joined_key] = False
                st.rerun()
