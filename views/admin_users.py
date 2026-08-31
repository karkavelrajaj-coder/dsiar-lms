import pandas as pd
import streamlit as st
from bson import ObjectId

from utils.auth import ROLES, hash_password, require_role
from utils.db import users_col

user = require_role("admin")

st.title("👥 Manage users")
st.caption("Only admins can create instructor/admin accounts or change roles.")

with st.expander("➕ Create instructor or admin account"):
    with st.form("new_staff"):
        name = st.text_input("Full name")
        email = st.text_input("Email")
        password = st.text_input("Temporary password", type="password")
        role = st.selectbox("Role", ["instructor", "admin"])
        if st.form_submit_button("Create account"):
            if not name or not email or not password:
                st.error("Fill in every field.")
            elif users_col().find_one({"email": email.strip().lower()}):
                st.error("A user with this email already exists.")
            else:
                users_col().insert_one(
                    {
                        "name": name.strip(),
                        "email": email.strip().lower(),
                        "password_hash": hash_password(password),
                        "role": role,
                    }
                )
                st.success(f"{role.title()} account created for {name}.")
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
