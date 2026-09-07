"""MongoDB Atlas connection layer for the D'siar Tech LMS."""

import streamlit as st
from pymongo import MongoClient
from pymongo.server_api import ServerApi


@st.cache_resource(show_spinner=False)
def get_client():
    uri = st.secrets["MONGO_URI"]
    client = MongoClient(uri, server_api=ServerApi("1"))
    return client


def get_db():
    client = get_client()
    db_name = st.secrets.get("DB_NAME", "dsiar_lms")
    return client[db_name]


# --- Convenience collection accessors -------------------------------------

def users_col():
    return get_db()["users"]


def courses_col():
    return get_db()["courses"]


def modules_col():
    return get_db()["modules"]


def lessons_col():
    return get_db()["lessons"]


def assignments_col():
    return get_db()["assignments"]


def submissions_col():
    return get_db()["submissions"]


def progress_col():
    return get_db()["progress"]


def enrollments_col():
    return get_db()["enrollments"]


def certificates_col():
    return get_db()["certificates"]


def ensure_indexes():
    """Call once at startup to create useful indexes (idempotent).

    Wrapped in try/except so a leftover duplicate from a previous failed
    startup (e.g. a network blip during the very first boot) can't crash
    the whole app on every subsequent run. If index creation fails, the app
    still starts; fix the underlying duplicate data in Atlas when you can.
    """
    from pymongo.errors import DuplicateKeyError, OperationFailure

    index_specs = [
        (users_col, "email", {"unique": True}),
        (modules_col, "course_id", {}),
        (lessons_col, "module_id", {}),
        (enrollments_col, [("user_id", 1), ("course_id", 1)], {"unique": True}),
        (progress_col, [("user_id", 1), ("lesson_id", 1)], {"unique": True}),
        (submissions_col, [("assignment_id", 1), ("user_id", 1)], {}),
        (certificates_col, [("user_id", 1), ("course_id", 1)], {"unique": True}),
    ]
    for col_fn, keys, kwargs in index_specs:
        try:
            col_fn().create_index(keys, **kwargs)
        except (DuplicateKeyError, OperationFailure):
            # Existing duplicate data is blocking a unique index build.
            # Skip it for now rather than crash the app; clean up the
            # duplicates in Atlas Data Explorer and reboot to retry.
            pass
