import streamlit as st
from bson import ObjectId

from utils.auth import require_role
from utils.db import courses_col, lessons_col, modules_col, users_col

user = require_role("admin", "instructor")

st.title("🛠️ Manage courses & content")
st.caption(
    "Admins manage every course. Instructors only manage courses assigned to them."
)

# --- Scope courses by role ---------------------------------------------------
if user["role"] == "admin":
    query = {}
else:
    query = {"instructor_id": user["id"]}

courses = list(courses_col().find(query).sort("order", 1))

# --- Create a new course -----------------------------------------------------
with st.expander("➕ Add a new course"):
    with st.form("new_course"):
        title = st.text_input("Title")
        category = st.text_input("Category (e.g. Artificial Intelligence)")
        description = st.text_area("Description")
        thumbnail_url = st.text_input("Thumbnail image URL")
        is_free = st.checkbox("Free course", value=True)

        instructor_id = user["id"]
        if user["role"] == "admin":
            instructors = list(users_col().find({"role": "instructor"}))
            options = {"— Unassigned (admin managed) —": None}
            options.update({i["name"]: str(i["_id"]) for i in instructors})
            chosen = st.selectbox("Assign to instructor", list(options.keys()))
            instructor_id = options[chosen]

        if st.form_submit_button("Create course"):
            if not title:
                st.error("Title is required.")
            else:
                courses_col().insert_one(
                    {
                        "title": title,
                        "category": category,
                        "description": description,
                        "thumbnail_url": thumbnail_url,
                        "is_free": is_free,
                        "instructor_id": instructor_id,
                        "order": courses_col().count_documents({}) + 1,
                    }
                )
                st.success("Course created.")
                st.rerun()

st.divider()

# --- Manage existing courses --------------------------------------------------
if not courses:
    st.info("No courses to manage yet.")

for course in courses:
    cid = str(course["_id"])
    with st.expander(f"📘 {course['title']}"):
        with st.form(f"edit_{cid}"):
            title = st.text_input("Title", value=course["title"], key=f"t_{cid}")
            description = st.text_area("Description", value=course.get("description", ""), key=f"d_{cid}")
            thumbnail_url = st.text_input("Thumbnail URL", value=course.get("thumbnail_url", ""), key=f"th_{cid}")
            if st.form_submit_button("Save changes"):
                courses_col().update_one(
                    {"_id": course["_id"]},
                    {"$set": {"title": title, "description": description, "thumbnail_url": thumbnail_url}},
                )
                st.success("Saved.")
                st.rerun()

        if st.button("🗑 Delete course", key=f"del_{cid}"):
            courses_col().delete_one({"_id": course["_id"]})
            module_ids = [str(m["_id"]) for m in modules_col().find({"course_id": cid})]
            lessons_col().delete_many({"module_id": {"$in": module_ids}})
            modules_col().delete_many({"course_id": cid})
            st.rerun()

        st.markdown("##### Modules & lessons")

        with st.form(f"new_module_{cid}"):
            m_title = st.text_input("New module title", key=f"mt_{cid}")
            if st.form_submit_button("Add module"):
                if m_title:
                    modules_col().insert_one(
                        {
                            "course_id": cid,
                            "title": m_title,
                            "order": modules_col().count_documents({"course_id": cid}) + 1,
                        }
                    )
                    st.rerun()

        modules = list(modules_col().find({"course_id": cid}).sort("order", 1))
        for module in modules:
            mid = str(module["_id"])
            st.markdown(f"**{module['title']}**")
            lessons = list(lessons_col().find({"module_id": mid}).sort("order", 1))
            for lesson in lessons:
                st.caption(f"• {lesson['title']} — youtube: {lesson.get('youtube_id', '—')}")

            with st.form(f"new_lesson_{mid}"):
                l_title = st.text_input("Lesson title", key=f"lt_{mid}")
                yt_id = st.text_input("YouTube video ID (the part after v=)", key=f"yt_{mid}")
                ppt = st.text_input("Slides link (PPT/Drive/GitHub)", key=f"ppt_{mid}")
                colab = st.text_input("Colab notebook link", key=f"colab_{mid}")
                dataset = st.text_input("Dataset link", key=f"ds_{mid}")
                if st.form_submit_button("Add lesson"):
                    if l_title:
                        lessons_col().insert_one(
                            {
                                "module_id": mid,
                                "title": l_title,
                                "youtube_id": yt_id.strip(),
                                "ppt_link": ppt.strip(),
                                "colab_link": colab.strip(),
                                "dataset_link": dataset.strip(),
                                "order": lessons_col().count_documents({"module_id": mid}) + 1,
                            }
                        )
                        st.rerun()
