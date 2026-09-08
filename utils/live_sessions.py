"""Helpers for live session scheduling: room name generation and the join
time window (when the 'Join' button should actually be clickable)."""

import uuid
from datetime import datetime, timedelta, timezone

JOIN_OPENS_MINUTES_BEFORE = 10
JOIN_STAYS_OPEN_MINUTES_AFTER_END = 30


def generate_room_name() -> str:
    """A random, unguessable Jitsi room name — never derived from the
    course or session title, so it can't be guessed or brute-forced."""
    return f"dsiar-{uuid.uuid4().hex[:16]}"


def session_status(scheduled_at: datetime, duration_minutes: int) -> str:
    """Returns 'upcoming', 'live', or 'ended' relative to now."""
    now = datetime.now(timezone.utc)
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    end = scheduled_at + timedelta(minutes=duration_minutes)
    if now < scheduled_at:
        return "upcoming"
    if now <= end:
        return "live"
    return "ended"


def join_window_open(scheduled_at: datetime, duration_minutes: int) -> bool:
    """Whether the Join button would be time-eligible right now (ignores
    whether the host has actually started — see can_student_join for that)."""
    now = datetime.now(timezone.utc)
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    opens_at = scheduled_at - timedelta(minutes=JOIN_OPENS_MINUTES_BEFORE)
    closes_at = scheduled_at + timedelta(minutes=duration_minutes + JOIN_STAYS_OPEN_MINUTES_AFTER_END)
    return opens_at <= now <= closes_at


def can_student_join(session: dict) -> tuple[bool, str]:
    """Whether a student should see an active Join button right now, and a
    human-readable reason if not.

    Students can only join once the HOST has actually started the session
    (tracked via started_at, set the moment the host opens the room) — not
    just because the scheduled time has arrived. This matters both so
    students never sit alone in an empty room, and so the host reliably
    holds Jitsi's moderator role (meet.jit.si assigns it to whoever's
    browser joins first).
    """
    if session.get("ended_at"):
        return False, "This session has been marked finished by the host."
    if not join_window_open(session["scheduled_at"], session["duration_minutes"]):
        return False, "🔒 Join opens 10 minutes before the scheduled start time."
    if not session.get("started_at"):
        return False, "⏳ Waiting for the host to start this session — check back shortly."
    return True, ""


def render_room(room_name: str, display_name: str, show_end_button: bool = False):
    """Renders the embedded Jitsi room inline on the current page, using
    Jitsi's JavaScript IFrame API (not a plain <iframe src=...>) so that,
    for the host, an 'End session for everyone' button can be shown that
    calls the real endConference command — this disconnects every
    participant, not just the person who clicked it.

    Caveat: on the free public meet.jit.si (no login), Jitsi assigns
    "moderator" to whoever's browser joins the room first — not necessarily
    whoever our app considers the host. The host should join first in
    practice. If the button doesn't take effect (non-moderator), a fallback
    message tells them to use Jitsi's own "End meeting for all" option in
    the call's "..." menu instead, which requires the same moderator role
    but is Jitsi's native control, not ours.

    Screen sharing and the whiteboard are available in the call itself, no
    extra setup needed. To record, the host can use free local screen
    recording software (e.g. OBS Studio) and upload the result as a lesson
    afterward — avoiding any need to expose a YouTube stream key.
    """
    import json

    import streamlit as st
    import streamlit.components.v1 as components

    st.caption(
        "🎙️ Screen sharing and the whiteboard are built into the call. "
        "Hosts: record locally (e.g. OBS Studio) and add the upload as a lesson afterward."
    )

    safe_room = json.dumps(room_name).replace("</", "<\\/")
    safe_name = json.dumps(display_name).replace("</", "<\\/")

    end_button_html = ""
    end_button_js = ""
    if show_end_button:
        end_button_html = """
        <button id="dsiar-end-btn" style="margin-top:10px;padding:9px 18px;
            background:#b91c1c;color:white;border:none;border-radius:6px;
            font-size:14px;cursor:pointer;">
            🔴 End session for everyone
        </button>
        <div id="dsiar-end-note" style="margin-top:6px;font-size:12px;color:#888;"></div>
        """
        end_button_js = """
        document.getElementById('dsiar-end-btn').addEventListener('click', function () {
            if (confirm('End this session for everyone? All participants will be disconnected.')) {
                try {
                    api.executeCommand('endConference');
                } catch (e) {
                    document.getElementById('dsiar-end-note').innerText =
                        "Couldn't end it from here (you may not hold the in-call moderator role). " +
                        "Use the \\"End meeting for all\\" option in the call's ••• menu instead.";
                }
            }
        });
        """

    html = f"""
    <div id="dsiar-jitsi-container" style="height:620px;"></div>
    {end_button_html}
    <script src="https://meet.jit.si/external_api.js"></script>
    <script>
        const api = new JitsiMeetExternalAPI("meet.jit.si", {{
            roomName: {safe_room},
            parentNode: document.getElementById('dsiar-jitsi-container'),
            width: "100%",
            height: 620,
            userInfo: {{ displayName: {safe_name} }}
        }});
        {end_button_js}
    </script>
    """
    components.html(html, height=720)
