"""Helpers for live session scheduling: room naming, timing windows, and
the embedded room itself.

Uses Digital Samba (see utils/digital_samba_video.py). Rooms are private —
every participant, host or student, gets their OWN signed join link
generated fresh by our backend at the moment they click Join, carrying
their real name and correct role ('teacher' or 'student'). No login
screen for anyone, and no shared secret ever reaches the browser.
"""

import uuid
from datetime import datetime, timedelta, timezone

JOIN_OPENS_MINUTES_BEFORE = 10
JOIN_STAYS_OPEN_MINUTES_AFTER_END = 30
ROOM_LIFETIME_BUFFER_HOURS = 6  # auto-cleanup safety net if a host forgets to end it

# Timezone conversion (scheduling in any zone, viewing in any zone) lives in
# utils/timezones.py — this file only handles timezone-agnostic session
# logic, working entirely in UTC internally.


def generate_room_name() -> str:
    """A random, unguessable room name — Digital Samba's friendly_url must
    be URL-safe (lowercase letters, numbers, hyphens)."""
    return f"dsiar-{uuid.uuid4().hex[:16]}"


def session_status(scheduled_at: datetime, duration_minutes: int, ended_at: datetime | None = None) -> str:
    """Returns 'upcoming', 'live', or 'ended' relative to now — a display
    label. If the host has explicitly ended the session (ended_at set),
    that always wins over the scheduled time window — a host ending a
    session 20 minutes early should immediately show as 'ended', not
    'live' just because the originally scheduled window hasn't elapsed."""
    if ended_at:
        return "ended"
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
    if not session.get("room_id"):
        return False, "Session isn't ready yet — try again in a moment."
    return True, ""


def room_expiry_for(scheduled_at: datetime, duration_minutes: int) -> datetime:
    """When Digital Samba should auto-delete the room if nobody explicitly
    ends it — a safety net, not the primary end mechanism."""
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    return scheduled_at + timedelta(minutes=duration_minutes, hours=ROOM_LIFETIME_BUFFER_HOURS)


def render_room(join_link: str):
    """Embeds a Digital Samba room inline on the page using a per-person
    join link (already carries that person's name and role — teacher or
    student — signed by our backend). No login required for anyone.

    Screen sharing and the whiteboard are available in the call itself. To
    record, the host can use free local screen recording software (e.g.
    OBS Studio) and upload the result as a lesson afterward — or use
    render_host_room() below for Digital Samba's built-in cloud recording
    (free up to 60 minutes/month).
    """
    import streamlit as st
    import streamlit.components.v1 as components

    st.caption(
        "🎙️ Screen sharing and the whiteboard are built into the call — no login needed for anyone. "
        "Hosts: record locally (e.g. OBS Studio) and add the upload as a lesson afterward."
    )
    components.iframe(join_link, height=650)


def render_host_room(join_link: str):
    """Host-only variant with in-call Start/Stop cloud recording buttons,
    using Digital Samba's official embedded-sdk (confirmed pattern:
    DigitalSambaEmbedded.createControl({url, root}).load()). Free plan
    includes 60 cloud recording minutes/month; beyond that, fall back to
    free local recording (OBS Studio etc.) instead, since local recording
    has no cap at all.

    Ending the session for everyone is handled separately, server-side,
    via digital_samba_video.end_room_now() — not through this embed.
    """
    import json

    import streamlit as st
    import streamlit.components.v1 as components

    st.caption(
        "🎙️ Screen sharing and the whiteboard are built into the call — no login needed for anyone. "
        "⏱️ Free-plan cloud recordings auto-stop at 15 minutes each (60 free minutes total per month, "
        "and deleting a recording later does NOT refund used minutes). For full-length sessions, record "
        "locally with OBS Studio instead — no cap — and add it as a lesson afterward."
    )

    safe_link = json.dumps(join_link).replace("</", "<\\/")

    html = f"""
    <style>
        #dsiar-samba-container {{
            width: 100%;
            height: 620px;
            position: relative;
            background: #000;
        }}
        #dsiar-samba-container iframe {{
            width: 100% !important;
            height: 100% !important;
            position: absolute;
            top: 0;
            left: 0;
            border: none;
        }}
    </style>
    <div id="dsiar-samba-container"></div>
    <div style="margin-top:10px; display:flex; gap:10px; align-items:center;">
        <button id="dsiar-rec-start" style="padding:9px 16px;background:#16a34a;color:white;
            border:none;border-radius:6px;font-size:14px;cursor:pointer;">⏺ Start cloud recording</button>
        <button id="dsiar-rec-stop" style="padding:9px 16px;background:#6b7280;color:white;
            border:none;border-radius:6px;font-size:14px;cursor:pointer;" disabled>⏹ Stop recording</button>
        <span id="dsiar-rec-timer" style="font-family:monospace;font-size:16px;font-weight:bold;color:#b91c1c;"></span>
    </div>
    <div id="dsiar-rec-note" style="margin-top:6px;font-size:12px;color:#888;"></div>

    <script crossorigin src="https://unpkg.com/@digitalsamba/embedded-sdk"></script>
    <script>
        const sambaFrame = DigitalSambaEmbedded.createControl({{
            url: {safe_link},
            root: document.getElementById('dsiar-samba-container')
        }});
        sambaFrame.load();

        const startBtn = document.getElementById('dsiar-rec-start');
        const stopBtn = document.getElementById('dsiar-rec-stop');
        const note = document.getElementById('dsiar-rec-note');
        const timerEl = document.getElementById('dsiar-rec-timer');

        const RECORDING_CAP_SECONDS = 15 * 60;
        let secondsLeft = RECORDING_CAP_SECONDS;
        let countdownInterval = null;

        function formatTime(totalSeconds) {{
            const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
            const s = Math.floor(totalSeconds % 60).toString().padStart(2, '0');
            return m + ':' + s;
        }}

        function stopCountdown() {{
            if (countdownInterval) {{
                clearInterval(countdownInterval);
                countdownInterval = null;
            }}
            timerEl.innerText = '';
        }}

        sambaFrame.on('recordingStarted', () => {{
            note.innerText = '🔴 Recording — auto-stops at 15:00, counts toward your 60 free min/month.';
            startBtn.disabled = true;
            stopBtn.disabled = false;

            secondsLeft = RECORDING_CAP_SECONDS;
            timerEl.innerText = formatTime(secondsLeft);
            countdownInterval = setInterval(() => {{
                secondsLeft -= 1;
                if (secondsLeft <= 0) {{
                    timerEl.innerText = '00:00';
                    stopCountdown();
                }} else {{
                    timerEl.innerText = formatTime(secondsLeft);
                    if (secondsLeft <= 60) {{
                        timerEl.style.color = '#b91c1c';
                    }}
                }}
            }}, 1000);
        }});
        sambaFrame.on('recordingStopped', () => {{
            stopCountdown();
            note.innerText = 'Recording stopped. Find it in your Digital Samba dashboard under Recordings once processed.';
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }});
        sambaFrame.on('appError', (e) => {{
            stopCountdown();
            note.innerText = 'Recording error: ' + (e && e.message ? e.message : 'unknown — recording may be unavailable right now.');
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }});

        startBtn.addEventListener('click', () => sambaFrame.startRecording());
        stopBtn.addEventListener('click', () => sambaFrame.stopRecording());
    </script>
    """
    components.html(html, height=740)
