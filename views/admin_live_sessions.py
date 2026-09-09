from datetime import datetime, time, timezone

import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.db import courses_col, live_sessions_col
from utils.digital_samba_video import create_room, end_room_now, generate_join_link
from utils.live_sessions import generate_room_name, render_host_room, room_expiry_for, session_status

user = require_role("admin", "instructor")

st.title("🎥 Manage live sessions")
st.caption("Admins schedule for every course. Instructors only schedule for courses assigned to them.")

if "DIGITALSAMBA_TEAM_ID" not in st.secrets or "DIGITALSAMBA_DEVELOPER_KEY" not in st.secrets:
    st.error(
        "DIGITALSAMBA_TEAM_ID / DIGITALSAMBA_DEVELOPER_KEY aren't set in secrets yet. "
        "Sign up free at https://dashboard.digitalsamba.com/signup (no card needed), "
        "find both values under the Team tab, and add them to Streamlit secrets."
    )
    st.stop()

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
                # The actual Digital Samba room is created lazily when the host
                # starts it, not here — avoids piling up unused rooms for
                # sessions that get rescheduled or cancelled.
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
            st.caption(f"✅ Ended at {ended_at.strftime('%I:%M %p UTC')}.")
        elif started_at:
            st.caption(f"🟢 Started at {started_at.strftime('%I:%M %p UTC')} — students can now join.")
        else:
            st.caption("⏳ Not started yet — students won't see an active Join button until you start it.")

        hostjoin_key = f"hostjoined_{sid}"
        if not st.session_state.get(hostjoin_key, False):
            btn_label = "🔁 Start a new session" if ended_at else "▶️ Start / rejoin session"
            if st.button(btn_label, key=f"hostjoin_{sid}"):
                try:
                    room_name = s["room_name"]
                    if ended_at:
                        # Previous room was deleted when ended — make a fresh one.
                        room_name = generate_room_name()
                        live_sessions_col().update_one({"_id": s["_id"]}, {"$set": {"room_name": room_name}})
                    if ended_at or not started_at:
                        expiry = room_expiry_for(s["scheduled_at"], s["duration_minutes"])
                        create_room(room_name, expiry)
                        live_sessions_col().update_one(
                            {"_id": s["_id"]},
                            {"$set": {"started_at": datetime.now(timezone.utc)}, "$unset": {"ended_at": ""}},
                        )
                    st.session_state[hostjoin_key] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't create the video room: {e}")
        else:
            current = live_sessions_col().find_one({"_id": s["_id"]})
            try:
                join_link = generate_join_link(current["room_name"], user["name"], role="teacher")
                render_host_room(join_link)
            except Exception as e:
                st.error(f"Couldn't generate your join link: {e}")

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Leave (keep session open)", key=f"hostleave_{sid}"):
                    st.session_state[hostjoin_key] = False
                    st.rerun()
            with btn_col2:
                if st.button("🔴 End session for everyone", key=f"hostend_{sid}"):
                    try:
                        end_room_now(current["room_name"])
                    except Exception as e:
                        st.warning(f"Room may already be closed ({e}) — marking it finished anyway.")
                    live_sessions_col().update_one(
                        {"_id": s["_id"]}, {"$set": {"ended_at": datetime.now(timezone.utc)}}
                    )
                    st.session_state[hostjoin_key] = False
                    st.success("Session ended for everyone — all participants have been disconnected.")
                    st.rerun()
