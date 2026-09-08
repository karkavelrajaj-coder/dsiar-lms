"""Daily.co REST API wrapper.

Rooms are created server-side using a private API key (stored in Streamlit
secrets, never exposed to the browser). Once created, a room is just a
plain URL — anyone who has it can join directly with zero login, for
either the host or students. This is the opposite of Jitsi's free public
server, which now requires the host to log into a Google/Facebook/
Microsoft account before a room will even start.

Ending a session for everyone is also a server-side action here (updating
the room's expiry), not a fragile client-side JS command that depends on
who happened to join first.

Setup: sign up free at https://dashboard.daily.co (no credit card needed),
go to Developers, copy the API key into DAILY_API_KEY in Streamlit secrets.
"""

from datetime import datetime, timedelta, timezone

import requests
import streamlit as st

API_BASE = "https://api.daily.co/v1"


def _headers():
    return {
        "Authorization": f"Bearer {st.secrets['DAILY_API_KEY']}",
        "Content-Type": "application/json",
    }


def create_room(room_name: str, expires_at: datetime) -> str:
    """Creates a Daily room and returns its joinable URL.

    expires_at: when Daily should auto-delete the room even if nobody
    explicitly ends it — keeps free-tier room count from growing forever
    if a host forgets to clean up.
    """
    payload = {
        "name": room_name,
        "privacy": "public",  # anyone with the URL can join — no login
        "properties": {
            "exp": int(expires_at.timestamp()),
            "eject_at_room_exp": True,
            "enable_screenshare": True,
            "enable_chat": True,
            "start_video_off": False,
            "start_audio_off": False,
        },
    }
    resp = requests.post(f"{API_BASE}/rooms", json=payload, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()["url"]


def end_room_now(room_name: str) -> None:
    """Force-ends a session for everyone right now, by expiring the room.
    This is a plain server-side call — no dependency on who's the
    in-call 'moderator', unlike the Jitsi approach."""
    payload = {"properties": {"exp": int(datetime.now(timezone.utc).timestamp()), "eject_at_room_exp": True}}
    resp = requests.post(f"{API_BASE}/rooms/{room_name}", json=payload, headers=_headers(), timeout=10)
    resp.raise_for_status()


def room_exists(room_name: str) -> bool:
    resp = requests.get(f"{API_BASE}/rooms/{room_name}", headers=_headers(), timeout=10)
    return resp.status_code == 200
