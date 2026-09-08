"""Helpers for live session scheduling: room naming, timing windows, and
the embedded room itself.

Uses Daily.co (see utils/daily_video.py) instead of Jitsi's free public
server. Rooms are created with a private, server-side API key that never
reaches the browser — students and hosts alike just get a URL and join
directly, with no login screen for anyone.
"""

import uuid
from datetime import datetime, timedelta, timezone

JOIN_OPENS_MINUTES_BEFORE = 10
JOIN_STAYS_OPEN_MINUTES_AFTER_END = 30
ROOM_LIFETIME_BUFFER_HOURS = 6  # auto-cleanup safety net if a host forgets to end it


def generate_room_name() -> str:
    """A random, unguessable room name — Daily room names must be URL-safe
    (lowercase letters, numbers, hyphens), so no uppercase/underscores."""
    return f"dsiar-{uuid.uuid4().hex[:16]}"


def session_status(scheduled_at: datetime, duration_minutes: int) -> str:
    """Returns 'upcoming', 'live', or 'ended' relative to now — a display
    label only, independent of the actual started_at/ended_at gating."""
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
    (tracked via started_at) — not just because the scheduled time has
    arrived. This keeps students from sitting alone in an empty room.
    """
    if session.get("ended_at"):
        return False, "This session has been marked finished by the host."
    if not join_window_open(session["scheduled_at"], session["duration_minutes"]):
        return False, "🔒 Join opens 10 minutes before the scheduled start time."
    if not session.get("started_at"):
        return False, "⏳ Waiting for the host to start this session — check back shortly."
    if not session.get("room_url"):
        return False, "Session isn't ready yet — try again in a moment."
    return True, ""


def room_expiry_for(scheduled_at: datetime, duration_minutes: int) -> datetime:
    """When Daily should auto-delete the room if nobody explicitly ends it."""
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    return scheduled_at + timedelta(minutes=duration_minutes, hours=ROOM_LIFETIME_BUFFER_HOURS)


def render_room(room_url: str):
    """Embeds the Daily.co room inline on the page. No login required for
    anyone — the room URL itself is the access credential (kept
    unguessable), same trust model as the certificate IDs and enrollment
    links elsewhere in the app.

    Screen sharing and chat are enabled on every room by default. To
    record, the host can use free local screen recording software (e.g.
    OBS Studio) and upload the result as a lesson afterward.
    """
    import streamlit as st
    import streamlit.components.v1 as components

    st.caption(
        "🎙️ Screen sharing and chat are built into the call — no login needed for anyone. "
        "Hosts: record locally (e.g. OBS Studio) and add the upload as a lesson afterward."
    )
    components.iframe(room_url, height=650)
