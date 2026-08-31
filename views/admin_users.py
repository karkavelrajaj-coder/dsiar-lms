from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from bson import ObjectId

from utils.auth import ROLES, hash_password, require_role
from utils.db import courses_col, enrollments_col, users_col

user = require_role("admin")

st.title("👥 Manage users")
st.caption(
    "Only admins create accounts and enroll students. There's no public sign-up — "
    "this keeps course access tied to confirmed payment."
)

# --- Create any account, including students -----------------------------------
with st.expander("➕ Create a new account"):
    with st.form("new_account"):
        name = st.text_input("Full name")
        email = st.text_input("Email")
        password = st.text_input("Temporary password", type="password")
        role = st.selectbox("Role", ["student", "instructor", "admin"])
        if st.form_submit_button("Create account"):
            if not name or not email or not password:
                st.error("Fill in every field.")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters.")
            elif users_col().find_one({"email": email.strip().lower()}):
                st.error("A user with this email already exists.")
            else:
                users_col().insert_one(
                    {
                        "name": name.strip(),
                        "email": email.strip().lower(),
                        "password_hash": hash_password(password),
                        "role": role,
                        "created_at": datetime.now(timezone.utc),
                    }
                )
                st.success(f"{role.title()} account created for {name}.")
                st.rerun()

st.divider()

# --- Enroll a student into a specific (paid) course -----------------------------
with st.expander("🎓 Enroll a student in a course"):
    students = list(users_col().find({"role": "student"}))
    courses = list(courses_col().find())

    if not students:
        st.info("No student accounts yet — create one above first.")
    elif not courses:
        st.info("No courses exist yet — create one in Manage Courses first.")
    else:
        student_options = {f"{s['name']} ({s['email']})": str(s["_id"]) for s in students}
        course_options = {c["title"]: str(c["_id"]) for c in courses}

        chosen_student = st.selectbox("Student", list(student_options.keys()))
        chosen_course = st.selectbox("Course (they've paid for this)", list(course_options.keys()))

        if st.button("Enroll student"):
            student_id = student_options[chosen_student]
            course_id = course_options[chosen_course]
            existing = enrollments_col().find_one({"user_id": student_id, "course_id": course_id})
            if existing:
                st.warning("This student is already enrolled in that course.")
            else:
                enrollments_col().insert_one(
                    {
                        "user_id": student_id,
                        "course_id": course_id,
                        "enrolled_at": datetime.now(timezone.utc),
                    }
                )
                st.success(f"Enrolled {chosen_student.split(' (')[0]} in {chosen_course}.")
                st.rerun()

    st.markdown("##### Current enrollments")
    all_enrollments = list(enrollments_col().find())
    if not all_enrollments:
        st.caption("No enrollments yet.")
    else:
        rows = []
        for e in all_enrollments:
            s = users_col().find_one({"_id": ObjectId(e["user_id"])})
            c = courses_col().find_one({"_id": ObjectId(e["course_id"])})
            rows.append(
                {
                    "Student": s["name"] if s else "Unknown",
                    "Email": s["email"] if s else "—",
                    "Course": c["title"] if c else "Unknown",
                    "Enrolled": e.get("enrolled_at", ""),
                    "_eid": str(e["_id"]),
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df.drop(columns=["_eid"]), use_container_width=True, hide_index=True)

        remove_label = st.selectbox(
            "Remove an enrollment",
            ["—"] + [f"{r['Student']} — {r['Course']}" for r in rows],
        )
        if remove_label != "—" and st.button("Remove selected enrollment"):
            match = next(r for r in rows if f"{r['Student']} — {r['Course']}" == remove_label)
            enrollments_col().delete_one({"_id": ObjectId(match["_eid"])})
            st.success("Enrollment removed.")
            st.rerun()

st.divider()
st.markdown("##### All users")

all_users = list(users_col().find())
if not all_users:
    st.info("No users yet.")
else:
    df = pd.DataFrame(
        [{"Name": u["name"], "Email": u["email"], "Role": u["role"], "_id": str(u["_id"])} for u in all_users]
    )
    st.dataframe(df.drop(columns=["_id"]), use_container_width=True, hide_index=True)

    st.markdown("##### Change a user's role")
    id_map = {f"{u['Name']} ({u['Email']})": u["_id"] for u in df.to_dict("records")}
    chosen = st.selectbox("Select user", list(id_map.keys()))
    new_role = st.selectbox("New role", ROLES)
    if st.button("Update role"):
        target_id = id_map[chosen]
        if target_id == user["id"] and new_role != "admin":
            st.error("You can't demote your own account.")
        else:
            users_col().update_one({"_id": ObjectId(target_id)}, {"$set": {"role": new_role}})
            st.success("Role updated.")
            st.rerun()
