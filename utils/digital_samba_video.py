"""Digital Samba (digitalsamba.com) REST API wrapper.

Confirmed free tier: 10,000 participation-minutes/month, renews monthly,
NO credit card required to sign up or use it (verified directly against
their own dashboard and docs, Sep 2026).

Auth: HTTP Basic, username = Team ID, password = Developer Key — both are
private, server-side only values, never sent to a student's or host's
browser (stored in Streamlit secrets, same trust model as MONGO_URI).

Rooms are created 'private', meaning nobody can join without a signed,
per-person token. Each person — host or student — gets their OWN token
generated fresh when they click Join, carrying their real name and the
correct role ('teacher' for host, 'student' for learners) as recognized
natively by Digital Samba's own permission system. This is more precise
than anything we had with Jitsi or Daily: role is an explicit, signed
fact issued by our backend, not inferred from who happened to click first.

Setup: sign up free at https://dashboard.digitalsamba.com/signup (no card),
find your Team ID and Developer Key under the 'Team' tab, add both to
Streamlit secrets as DIGITALSAMBA_TEAM_ID and DIGITALSAMBA_DEVELOPER_KEY.
"""

from datetime import datetime

import requests
import streamlit as st

API_BASE = "https://api.digitalsamba.com/api/v1"


def _auth():
    return (st.secrets["DIGITALSAMBA_TEAM_ID"], st.secrets["DIGITALSAMBA_DEVELOPER_KEY"])


def create_room(room_name: str, expires_at: datetime) -> str:
    """Creates a private Digital Samba room. Returns the room's friendly_url
    (used afterwards to generate tokens or to end/delete the room).

    expires_at: Digital Samba auto-deletes the room at this time even if
    nobody explicitly ends it — a safety net if a host forgets to.
    """
    payload = {
        "friendly_url": room_name,
        "privacy": "private",  # nobody joins without a signed per-person token
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
    resp = requests.post(f"{API_BASE}/rooms", json=payload, auth=_auth(), timeout=10)
    resp.raise_for_status()
    return resp.json()["friendly_url"]


def generate_join_link(room_name: str, display_name: str, role: str) -> str:
    """Generates a fresh, signed, per-person join link for one specific
    participant. role should be 'teacher' (host) or 'student' (learner) —
    these are Digital Samba's own built-in permission presets, matching
    our app's roles directly.
    """
    payload = {"u": display_name, "role": role}
    resp = requests.post(f"{API_BASE}/rooms/{room_name}/token", json=payload, auth=_auth(), timeout=10)
    resp.raise_for_status()
    return resp.json()["link"]


def end_room_now(room_name: str) -> None:
    """Force-ends a session for everyone right now by deleting the room.
    Digital Samba's own docs confirm: if the room is in use, deleting it
    immediately disconnects every participant and ends the call — a
    reliable server-side action, not dependent on in-call moderator status.
    """
    resp = requests.delete(f"{API_BASE}/rooms/{room_name}", auth=_auth(), timeout=10)
    if resp.status_code not in (200, 204, 404):  # 404 = already gone, treat as success
        resp.raise_for_status()
