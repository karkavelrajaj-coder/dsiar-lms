"""Authentication + Role-Based Access Control (RBAC) for the D'siar Tech LMS.

Three roles, checked everywhere content or actions are gated:

- "admin"      : full control -> manage users/roles, all courses, all content,
                 all submissions, analytics.
- "instructor" : the general "staff / user" role -> can create & edit content
                 for courses they are assigned to, and grade submissions for
                 those courses. Cannot manage other users or see other
                 instructors' courses.
- "student"    : the learner role -> browse catalog, enroll, watch lessons,
                 track progress, submit assignments.
"""

from datetime import datetime, timezone

import bcrypt
import streamlit as st

from utils.db import users_col

ROLES = ["admin", "instructor", "student"]


# --- Password helpers -------------------------------------------------------

def hash_password(raw_password: str) -> bytes:
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())


def verify_password(raw_password: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8"), hashed)
    except (ValueError, TypeError):
        return False


# --- Session lifecycle -------------------------------------------------------

def init_session():
    if "user" not in st.session_state:
        st.session_state.user = None
    _seed_first_admin()


def _seed_first_admin():
    """Create the initial admin account from secrets, only if no admin exists yet."""
    col = users_col()
    if col.find_one({"role": "admin"}):
        return
    email = st.secrets.get("SEED_ADMIN_EMAIL")
    password = st.secrets.get("SEED_ADMIN_PASSWORD")
    name = st.secrets.get("SEED_ADMIN_NAME", "Admin")
    if not email or not password:
        return
    if col.find_one({"email": email}):
        col.update_one({"email": email}, {"$set": {"role": "admin"}})
        return
    col.insert_one(
        {
            "name": name,
            "email": email,
            "password_hash": hash_password(password),
            "role": "admin",
            "created_at": datetime.now(timezone.utc),
        }
    )


def sign_up(name: str, email: str, password: str, role: str = "student"):
    """Public sign-up. Only 'student' is allowed from the public form.

    Instructor and admin accounts are created/promoted by an existing admin
    from the Admin Panel, never through public sign-up.
    """
    email = email.strip().lower()
    if role not in ("student",):
        role = "student"
    if users_col().find_one({"email": email}):
        raise ValueError("An account with this email already exists.")
    doc = {
        "name": name.strip(),
        "email": email,
        "password_hash": hash_password(password),
        "role": role,
        "created_at": datetime.now(timezone.utc),
    }
    users_col().insert_one(doc)
    return doc


def log_in(email: str, password: str):
    email = email.strip().lower()
    user = users_col().find_one({"email": email})
    if not user or not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid email or password.")
    st.session_state.user = {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
    }
    return st.session_state.user


def log_out():
    st.session_state.user = None
    st.rerun()


def current_user():
    return st.session_state.get("user")


def require_login():
    if not current_user():
        st.warning("Please log in to continue.")
        st.stop()


def require_role(*allowed_roles):
    """Stop rendering the page unless the current user has one of allowed_roles."""
    require_login()
    user = current_user()
    if user["role"] not in allowed_roles:
        st.error("You don't have permission to view this page.")
        st.stop()
    return user
