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

            new_instructor_id = course.get("instructor_id")
            if user["role"] == "admin":
                instructors = list(users_col().find({"role": "instructor"}))
                options = {"— Unassigned (admin managed) —": None}
                options.update({i["name"]: str(i["_id"]) for i in instructors})
                current_id = course.get("instructor_id")
                id_to_name = {v: k for k, v in options.items()}
                current_label = id_to_name.get(current_id, "— Unassigned (admin managed) —")
                labels = list(options.keys())
                chosen = st.selectbox(
                    "Assign to instructor",
                    labels,
                    index=labels.index(current_label) if current_label in labels else 0,
                    key=f"instr_{cid}",
                )
                new_instructor_id = options[chosen]

            if st.form_submit_button("Save changes"):
                update = {"title": title, "description": description, "thumbnail_url": thumbnail_url}
                if user["role"] == "admin":
                    update["instructor_id"] = new_instructor_id
                courses_col().update_one({"_id": course["_id"]}, {"$set": update})
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
            mod_col1, mod_col2, mod_col3 = st.columns([4, 1, 1])
            with mod_col1:
                st.markdown(f"**{module['title']}**")
            with mod_col2:
                if st.button("✏️ Edit", key=f"editmod_btn_{mid}"):
                    st.session_state[f"editing_mod_{mid}"] = not st.session_state.get(f"editing_mod_{mid}", False)
                    st.rerun()
            with mod_col3:
                if st.button("🗑 Delete", key=f"delmod_{mid}"):
                    lessons_col().delete_many({"module_id": mid})
                    modules_col().delete_one({"_id": module["_id"]})
                    st.rerun()

            if st.session_state.get(f"editing_mod_{mid}", False):
                with st.form(f"edit_module_form_{mid}"):
                    new_mod_title = st.text_input("Module title", value=module["title"], key=f"modtitle_{mid}")
                    save_col, cancel_col = st.columns(2)
                    with save_col:
                        if st.form_submit_button("Save module", use_container_width=True):
                            modules_col().update_one({"_id": module["_id"]}, {"$set": {"title": new_mod_title}})
                            st.session_state[f"editing_mod_{mid}"] = False
                            st.rerun()
                    with cancel_col:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state[f"editing_mod_{mid}"] = False
                            st.rerun()

            lessons = list(lessons_col().find({"module_id": mid}).sort("order", 1))
            for lesson in lessons:
                lid = str(lesson["_id"])
                les_col1, les_col2, les_col3 = st.columns([4, 1, 1])
                with les_col1:
                    st.caption(f"• {lesson['title']} — youtube: {lesson.get('youtube_id', '—')}")
                with les_col2:
                    if st.button("✏️", key=f"editlesson_btn_{lid}", help="Edit this lesson"):
                        st.session_state[f"editing_lesson_{lid}"] = not st.session_state.get(f"editing_lesson_{lid}", False)
                        st.rerun()
                with les_col3:
                    if st.button("🗑", key=f"dellesson_{lid}", help="Delete this lesson"):
                        lessons_col().delete_one({"_id": lesson["_id"]})
                        st.rerun()

                if st.session_state.get(f"editing_lesson_{lid}", False):
                    with st.form(f"edit_lesson_form_{lid}"):
                        e_title = st.text_input("Lesson title", value=lesson["title"], key=f"elt_{lid}")
                        e_yt = st.text_input(
                            "YouTube video ID (the part after v=)",
                            value=lesson.get("youtube_id", ""),
                            key=f"eyt_{lid}",
                        )
                        e_ppt = st.text_input(
                            "Slides link (PPT/Drive/GitHub)", value=lesson.get("ppt_link", ""), key=f"eppt_{lid}"
                        )
                        e_colab = st.text_input(
                            "Colab notebook link", value=lesson.get("colab_link", ""), key=f"ecolab_{lid}"
                        )
                        e_dataset = st.text_input(
                            "Dataset link", value=lesson.get("dataset_link", ""), key=f"eds_{lid}"
                        )
                        save_col, cancel_col = st.columns(2)
                        with save_col:
                            if st.form_submit_button("Save lesson", use_container_width=True):
                                lessons_col().update_one(
                                    {"_id": lesson["_id"]},
                                    {
                                        "$set": {
                                            "title": e_title,
                                            "youtube_id": e_yt.strip(),
                                            "ppt_link": e_ppt.strip(),
                                            "colab_link": e_colab.strip(),
                                            "dataset_link": e_dataset.strip(),
                                        }
                                    },
                                )
                                st.session_state[f"editing_lesson_{lid}"] = False
                                st.rerun()
                        with cancel_col:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                st.session_state[f"editing_lesson_{lid}"] = False
                                st.rerun()

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
