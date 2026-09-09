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
correct role ('teacher' for host, 'student' for learners).

IMPORTANT: the /rooms/{room}/token and DELETE /rooms/{room} endpoints
require the room's internal UUID `id` — NOT the human-readable
`friendly_url` we choose when creating it. create_room() returns both;
callers must store and reuse the `id` for every call after creation, and
only ever use `friendly_url` as a label.

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


def _raise_with_body(resp: requests.Response):
    """Re-raises HTTP errors with the actual response body included, so
    error messages shown in the app are immediately diagnosable instead of
    a bare '400 Bad Request' with no explanation."""
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise requests.HTTPError(f"{e} — response body: {resp.text}") from None


def create_room(room_name: str, expires_at: datetime) -> dict:
    """Creates a private Digital Samba room. Returns {'id': ..., 'friendly_url': ...}.

    `id` (a UUID) is what every subsequent call — token generation, ending
    the room — must use. `friendly_url` is just the readable label we chose;
    it is NOT accepted by those other endpoints.

    A room does NOT automatically allow every role that exists at the team
    level (attendee/moderator/speaker/student/teacher) — it defaults to
    just moderator/speaker/attendee unless you explicitly list which roles
    this specific room accepts. We need 'teacher' and 'student', so both
    are passed here, with 'student' as the safe default for anyone whose
    token somehow omits a role.

    expires_at: Digital Samba auto-deletes the room at this time even if
    nobody explicitly ends it — a safety net if a host forgets to.
    """
    payload = {
        "friendly_url": room_name,
        "privacy": "private",  # nobody joins without a signed per-person token
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        "roles": ["teacher", "student"],
        "default_role": "student",
    }
    resp = requests.post(f"{API_BASE}/rooms", json=payload, auth=_auth(), timeout=10)
    _raise_with_body(resp)
    data = resp.json()
    return {"id": data["id"], "friendly_url": data.get("friendly_url", room_name)}


def generate_join_link(room_id: str, display_name: str, role: str) -> str:
    """Generates a fresh, signed, per-person join link for one specific
    participant. room_id MUST be the room's UUID `id` from create_room(),
    not its friendly_url. role should be 'teacher' (host) or 'student'
    (learner) — Digital Samba's own built-in permission presets.
    """
    payload = {"u": display_name, "role": role}
    resp = requests.post(f"{API_BASE}/rooms/{room_id}/token", json=payload, auth=_auth(), timeout=10)
    _raise_with_body(resp)
    return resp.json()["link"]


def end_room_now(room_id: str) -> None:
    """Force-ends a session for everyone right now by deleting the room.
    room_id MUST be the room's UUID `id`, not its friendly_url. Digital
    Samba's own docs confirm: if the room is in use, deleting it
    immediately disconnects every participant — a reliable server-side
    action, not dependent on in-call moderator status."""
    resp = requests.delete(f"{API_BASE}/rooms/{room_id}", auth=_auth(), timeout=10)
    if resp.status_code not in (200, 204, 404):  # 404 = already gone, treat as success
        _raise_with_body(resp)
