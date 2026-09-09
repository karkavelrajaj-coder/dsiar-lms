"""Shared timezone utilities.

Every stored datetime in this app stays in UTC internally — correct
practice for a database. These helpers exist purely at the human-facing
edges: converting what a person types into UTC for storage, and
converting stored UTC back into whichever zone a given viewer wants —
either the zone a session was originally scheduled in, or a viewer's own
saved preference.

Each live session stores BOTH scheduled_at (UTC, for all comparisons/
gating) AND scheduled_tz (the zone it was scheduled in, so editing later
defaults back to that zone rather than guessing).

Each user can save their own preferred viewing timezone (users.timezone),
defaulting to IST for anyone who hasn't set one.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, available_timezones

from bson import ObjectId

from utils.db import users_col

DEFAULT_TIMEZONE = "Asia/Kolkata"

# A curated shortlist covering the regions this platform is realistically
# used from — shown first in any picker, before the full global list.
CURATED_TIMEZONES = [
    "Asia/Kolkata",
    "Asia/Dubai",
    "Asia/Singapore",
    "Asia/Hong_Kong",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Karachi",
    "Asia/Dhaka",
    "Asia/Bangkok",
    "Asia/Jakarta",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Madrid",
    "Europe/Rome",
    "Europe/Amsterdam",
    "Europe/Moscow",
    "Africa/Johannesburg",
    "Africa/Cairo",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "America/Sao_Paulo",
    "America/Mexico_City",
    "Australia/Sydney",
    "Australia/Perth",
    "Pacific/Auckland",
    "UTC",
]


def all_timezones() -> list[str]:
    """Every valid IANA zone, alphabetically — a fallback for anyone whose
    specific city isn't in the curated shortlist."""
    zones = [z for z in available_timezones() if "/" in z and not z.startswith(("Etc/", "SystemV/"))]
    return sorted(zones)


def timezone_options() -> list[str]:
    """Curated common zones first, then everything else — used to build
    picker dropdowns. Streamlit's selectbox is searchable by typing, so a
    long list is still easy to use."""
    rest = [z for z in all_timezones() if z not in CURATED_TIMEZONES]
    return CURATED_TIMEZONES + rest


def tz_display_label(tz_name: str, at: datetime | None = None) -> str:
    """e.g. 'Asia/Kolkata — UTC+05:30 (IST)', for a clear dropdown label."""
    at = at or datetime.now(timezone.utc)
    local = at.astimezone(ZoneInfo(tz_name))
    offset = local.strftime("%z") or "+0000"
    offset_fmt = f"{offset[:3]}:{offset[3:]}"
    abbr = local.tzname()
    return f"{tz_name} — UTC{offset_fmt} ({abbr})"


def local_input_to_utc(local_date, local_time, tz_name: str) -> datetime:
    """Takes plain date/time values (as typed by someone in tz_name) and
    returns the correct UTC-aware datetime to store."""
    naive = datetime.combine(local_date, local_time)
    local_aware = naive.replace(tzinfo=ZoneInfo(tz_name))
    return local_aware.astimezone(timezone.utc)


def utc_to_tz(dt_utc: datetime, tz_name: str) -> datetime:
    """Converts a stored UTC datetime into the given zone — for display,
    or for pre-filling an edit form's date/time widgets."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(ZoneInfo(tz_name))


def format_in_tz(dt_utc: datetime, tz_name: str) -> str:
    """Human-readable display string for a stored UTC datetime, converted
    into tz_name, e.g. 'Sep 09, 2026 at 05:20 PM IST'."""
    local = utc_to_tz(dt_utc, tz_name)
    return f"{local.strftime('%b %d, %Y at %I:%M %p')} {local.tzname()}"


def get_user_timezone(user_id: str) -> str:
    """A user's saved viewing-timezone preference, defaulting to IST if
    they've never set one (covers every existing account automatically)."""
    user = users_col().find_one({"_id": ObjectId(user_id)})
    if user and user.get("timezone"):
        return user["timezone"]
    return DEFAULT_TIMEZONE


def set_user_timezone(user_id: str, tz_name: str) -> None:
    users_col().update_one({"_id": ObjectId(user_id)}, {"$set": {"timezone": tz_name}})
