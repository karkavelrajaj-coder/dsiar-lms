from datetime import datetime, time, timezone

import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.db import courses_col, live_sessions_col
from utils.live_sessions import generate_room_name, render_room, session_status

user = require_role("admin", "instructor")

st.title("🎥 Manage live sessions")
st.caption("Admins schedule for every course. Instructors only schedule for courses assigned to them.")

# --- Scope courses by role, same pattern as Manage Courses -------------------
if user["role"] == "admin":
    courses = list(courses_col().find())
else:
    courses = list(courses_col().find({"instructor_id": user["id"]}))

course_map = {c["title"]: str(c["_id"]) for c in courses}

if not course_map:
    st.info("No courses available yet.")
    st.stop()

# --- Schedule a new session ---------------------------------------------------
with st.expander("➕ Schedule a new live session"):
    with st.form("new_live_session"):
        course_name = st.selectbox("Course", list(course_map.keys()))
        title = st.text_input("Session title", placeholder="e.g. Live Q&A: Neural Networks")
        description = st.text_area("What will this session cover? (optional)")
        col1, col2 = st.columns(2)
        with col1:
            session_date = st.date_input("Date")
        with col2:
            session_time = st.time_input("Start time", value=time(18, 0))
        duration_minutes = st.number_input("Duration (minutes)", min_value=15, max_value=300, value=60, step=15)

        if st.form_submit_button("Schedule session"):
            if not title:
                st.error("Give the session a title.")
            else:
                scheduled_at = datetime.combine(session_date, session_time).replace(tzinfo=timezone.utc)
                live_sessions_col().insert_one(
                    {
                        "course_id": course_map[course_name],
                        "title": title,
                        "description": description,
                        "scheduled_at": scheduled_at,
                        "duration_minutes": int(duration_minutes),
                        "room_name": generate_room_name(),
                        "host_id": user["id"],
                        "host_name": user["name"],
                        "created_at": datetime.now(timezone.utc),
                    }
                )
                st.success("Session scheduled.")
                st.rerun()

st.divider()
st.markdown("##### Scheduled sessions")

sessions = list(
    live_sessions_col().find({"course_id": {"$in": list(course_map.values())}}).sort("scheduled_at", -1)
)
course_id_to_name = {v: k for k, v in course_map.items()}

if not sessions:
    st.info("No live sessions scheduled yet.")

status_badge = {"upcoming": "🔵 Upcoming", "live": "🔴 Live now", "ended": "⚪ Ended"}

for s in sessions:
    sid = str(s["_id"])
    status = session_status(s["scheduled_at"], s["duration_minutes"])

    with st.container(border=True):
        head_col1, head_col2, head_col3 = st.columns([4, 1, 1])
        with head_col1:
            st.markdown(f"**{s['title']}**  ·  {status_badge[status]}")
            st.caption(
                f"Course: {course_id_to_name.get(s['course_id'], 'Unknown')} · "
                f"Host: {s.get('host_name', 'Unknown')} · "
                f"{s['scheduled_at'].strftime('%b %d, %Y at %I:%M %p UTC')} · "
                f"{s['duration_minutes']} min"
            )
            if s.get("description"):
                st.write(s["description"])
        with head_col2:
            if st.button("✏️ Edit", key=f"editsess_btn_{sid}"):
                st.session_state[f"editing_sess_{sid}"] = not st.session_state.get(f"editing_sess_{sid}", False)
                st.rerun()
        with head_col3:
            if st.button("🗑 Delete", key=f"delsess_{sid}"):
                live_sessions_col().delete_one({"_id": s["_id"]})
                st.rerun()

        if st.session_state.get(f"editing_sess_{sid}", False):
            with st.form(f"edit_sess_form_{sid}"):
                e_title = st.text_input("Session title", value=s["title"], key=f"est_{sid}")
                e_desc = st.text_area("Description", value=s.get("description", ""), key=f"esd_{sid}")
                col1, col2 = st.columns(2)
                with col1:
                    e_date = st.date_input("Date", value=s["scheduled_at"].date(), key=f"esdate_{sid}")
                with col2:
                    e_time = st.time_input("Start time", value=s["scheduled_at"].time(), key=f"estime_{sid}")
                e_duration = st.number_input(
                    "Duration (minutes)", min_value=15, max_value=300,
                    value=s["duration_minutes"], step=15, key=f"esdur_{sid}",
                )
                save_col, cancel_col = st.columns(2)
                with save_col:
                    if st.form_submit_button("Save changes", use_container_width=True):
                        new_scheduled_at = datetime.combine(e_date, e_time).replace(tzinfo=timezone.utc)
                        live_sessions_col().update_one(
                            {"_id": s["_id"]},
                            {
                                "$set": {
                                    "title": e_title,
                                    "description": e_desc,
                                    "scheduled_at": new_scheduled_at,
                                    "duration_minutes": int(e_duration),
                                }
                            },
                        )
                        st.session_state[f"editing_sess_{sid}"] = False
                        st.success("Saved.")
                        st.rerun()
                with cancel_col:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state[f"editing_sess_{sid}"] = False
                        st.rerun()

        started_at = s.get("started_at")
        ended_at = s.get("ended_at")

        if ended_at:
            st.caption(f"✅ Marked finished by host at {ended_at.strftime('%I:%M %p UTC')}.")
        elif started_at:
            st.caption(f"🟢 Started at {started_at.strftime('%I:%M %p UTC')} — students can now join.")
        else:
            st.caption("⏳ Not started yet — students won't see an active Join button until you start it.")

        st.caption(f"Room: `{s['room_name']}` (share only with enrolled students — this link isn't public)")

        hostjoin_key = f"hostjoined_{sid}"
        if not st.session_state.get(hostjoin_key, False):
            join_label = "▶️ Start / rejoin session" if not ended_at else "▶️ Reopen session"
            if st.button(join_label, key=f"hostjoin_{sid}"):
                if not started_at:
                    live_sessions_col().update_one(
                        {"_id": s["_id"]}, {"$set": {"started_at": datetime.now(timezone.utc)}}
                    )
                if ended_at:
                    # Reopening after marking finished — clear the finished flag.
                    live_sessions_col().update_one({"_id": s["_id"]}, {"$unset": {"ended_at": ""}})
                st.session_state[hostjoin_key] = True
                st.rerun()
        else:
            render_room(s["room_name"], user["name"], show_end_button=True)
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Leave (keep session open)", key=f"hostleave_{sid}"):
                    st.session_state[hostjoin_key] = False
                    st.rerun()
            with btn_col2:
                if st.button("🏁 Mark session as finished", key=f"hostfinish_{sid}"):
                    live_sessions_col().update_one(
                        {"_id": s["_id"]}, {"$set": {"ended_at": datetime.now(timezone.utc)}}
                    )
                    st.session_state[hostjoin_key] = False
                    st.success("Marked finished. Students will no longer be able to join this session.")
                    st.rerun()
            st.caption(
                "Use the red '🔴 End session for everyone' button above to disconnect everyone from the "
                "video call itself, then '🏁 Mark session as finished' here so students stop seeing an "
                "active Join button too — they're two separate things."
            )
