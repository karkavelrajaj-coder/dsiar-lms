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


def ensure_indexes():
    """Call once at startup to create useful indexes (idempotent)."""
    users_col().create_index("email", unique=True)
    modules_col().create_index("course_id")
    lessons_col().create_index("module_id")
    enrollments_col().create_index([("user_id", 1), ("course_id", 1)], unique=True)
    progress_col().create_index([("user_id", 1), ("lesson_id", 1)], unique=True)
    submissions_col().create_index([("assignment_id", 1), ("user_id", 1)])
